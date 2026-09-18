"""Opening a WASAPI output stream, then reporting honestly what was opened.

Measured on the reference machine, which is why the two paths below differ so
sharply:

- Shared mode refuses every sample rate except the one the Windows mixer is
  configured for, unless `auto_convert` is set. With it set, every rate opened
  on every device tried. So shared mode always passes it; shared mode is
  therefore never bit perfect, because the mixer is resampling.
- Exclusive mode accepts whatever the driver supports, which on the onboard
  device was 44.1, 48, 96 and 192 kHz. Its native sample format at every one of
  those rates is 16 bit, so the format is probed rather than assumed and a
  24 bit file is reported as reaching a 16 bit endpoint.

A device that refuses exclusive mode is not an error. It is a fallback; the
report says so rather than the caller discovering it from silence.
"""

from __future__ import annotations

import sounddevice

from stellody.domain.playback import OutputMode, OutputReport, OutputRequest
from stellody.infrastructure.buffering import buffer_seconds
from stellody.infrastructure.portaudio import (
    DTYPE_BIT_DEPTHS,
    NO_STATED_DEPTH,
    SHARED_DTYPE,
    opened_shared,
)

CANDIDATE_DTYPES = ("int32", "int16")
# The rates a listener's music is actually in, asked of a device to find
# out what it will take exclusively. Every rate a CD, a download or a
# studio master arrives at, which is what makes an empty answer mean the
# device offers nothing rather than that the list was too short.
CANDIDATE_RATES = (44100, 48000, 88200, 96000, 176400, 192000)
# What the probe asks WITH. A rate is offered or it is not; the depth of
# the file asking does not change the driver's answer, so one stands for
# all of them and the probe costs six questions rather than twelve.
PROBE_DEPTH = 16
NO_EXCLUSIVE_FORMAT = "the device offers no exclusive format at this rate"


WASAPI_API_NAME = "WASAPI"
NO_DEVICE = -1


def default_device() -> int | None:
    """The WASAPI host API's own default output device; None when there is none.

    Measured; it is why nothing played at all. Sounddevice's global default
    output resolves through MME on this machine, so handing WASAPI settings to
    an MME stream fails outright with "Incompatible host API specific stream
    info" (PaErrorCode -9984). Every route into playback died there. This module
    speaks WASAPI, so it has to ask WASAPI which device it means.

    Resolved per stream rather than once at startup. That alone does not
    follow headphones plugged in after the application opened: measured on
    2026-09-14, PortAudio's own list is taken once, so this kept naming the
    device that was the default at launch. `output_devices.OutputDevices` has
    the list taken again after a move, before the stream that asks here.
    """
    try:
        apis = sounddevice.query_hostapis()
    except Exception:  # noqa: BLE001 - no host APIs is an absent device, not a fault
        return None
    for api in apis:
        if WASAPI_API_NAME in api.get("name", ""):
            device = api.get("default_output_device", NO_DEVICE)
            return None if device == NO_DEVICE else device
    return None


def native_dtype(device: int | None, request: OutputRequest) -> str | None:
    """The deepest sample type the device accepts exclusively at this rate.

    None when the device will not take exclusive mode there at all. This asks
    the driver rather than opening a stream, so it costs milliseconds and makes
    no sound.
    """
    for dtype in CANDIDATE_DTYPES:
        try:
            sounddevice.check_output_settings(
                device=device,
                samplerate=request.sample_rate,
                channels=request.channels,
                dtype=dtype,
                extra_settings=sounddevice.WasapiSettings(
                    exclusive=True, explicit_sample_format=True
                ),
            )
        except Exception:  # noqa: BLE001, S112 - a refusal is the answer
            continue
        return dtype
    return None


def exclusive_rates(device: int | None = None) -> tuple[int, ...]:
    """Every rate this device will take exclusively; empty where none.

    Asked of the driver rather than of a stream, so it opens nothing and
    makes no sound. Measured on the reference machine on 2026-09-18: the
    onboard Realtek speakers answer 44100, 48000, 96000 and 192000, while
    a Bluetooth headphone answers 48000 alone. That difference is the
    whole reason this exists: a listener whose device takes one rate is
    owed that fact rather than a refusal they cannot act on.
    """
    device = default_device() if device is None else device
    return tuple(
        rate
        for rate in CANDIDATE_RATES
        if native_dtype(
            device,
            OutputRequest(
                sample_rate=rate,
                bit_depth=PROBE_DEPTH,
                mode=OutputMode.EXCLUSIVE,
            ),
        )
        is not None
    )


def _open_exclusive(
    device: int | None, request: OutputRequest, dtype: str
) -> sounddevice.OutputStream:
    """A stream straight to the hardware, with no conversion permitted."""
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=dtype,
        latency=buffer_seconds(request.sample_rate),
        extra_settings=sounddevice.WasapiSettings(
            exclusive=True, explicit_sample_format=True
        ),
    )


def _open_shared(
    device: int | None, request: OutputRequest
) -> sounddevice.OutputStream:
    """A stream through the mixer, which will resample to reach the device."""
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=SHARED_DTYPE,
        latency=buffer_seconds(request.sample_rate),
        extra_settings=sounddevice.WasapiSettings(exclusive=False, auto_convert=True),
    )


def open_output(
    request: OutputRequest, device: int | None = None
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the best stream for `request`, with the report and the feed dtype.

    Raises OutputUnavailableError only when even the mixer path fails, which
    means there is no usable output device at all.
    """
    device = default_device() if device is None else device
    if request.mode is not OutputMode.EXCLUSIVE:
        return opened_shared(_open_shared, device, request, "")
    # Refused here rather than left to fail at the format search, so the
    # reason names the file instead of blaming the device. A lossy source has
    # no depth to hand an exclusive stream; an exclusive stream carrying a
    # decoder's output is not bit perfect however well it opens.
    if not request.states_depth:
        return opened_shared(_open_shared, device, request, NO_STATED_DEPTH)
    dtype = native_dtype(device, request)
    if dtype is None:
        return opened_shared(_open_shared, device, request, NO_EXCLUSIVE_FORMAT)
    try:
        stream = _open_exclusive(device, request, dtype)
    except Exception as error:  # noqa: BLE001 - a refusal is a fallback
        return opened_shared(_open_shared, device, request, str(error))
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=request.sample_rate,
        bit_depth=DTYPE_BIT_DEPTHS[dtype],
    )
    return stream, report, dtype
