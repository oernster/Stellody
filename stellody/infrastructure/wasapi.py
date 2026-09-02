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

CANDIDATE_DTYPES = ("int32", "int16")
SHARED_DTYPE = "float32"
DTYPE_BIT_DEPTHS = {"int16": 16, "int32": 32, "float32": 32}
MIXER_BIT_DEPTH = DTYPE_BIT_DEPTHS[SHARED_DTYPE]
NO_EXCLUSIVE_FORMAT = "the device offers no exclusive format at this rate"
NO_STATED_DEPTH = "the file states no bit depth, so nothing can be bit perfect"


WASAPI_API_NAME = "WASAPI"
NO_DEVICE = -1


class OutputUnavailableError(RuntimeError):
    """Raised when no stream at all could be opened for a request."""


def default_device() -> int | None:
    """The WASAPI host API's own default output device; None when there is none.

    Measured; it is why nothing played at all. Sounddevice's global default
    output resolves through MME on this machine, so handing WASAPI settings to
    an MME stream fails outright with "Incompatible host API specific stream
    info" (PaErrorCode -9984). Every route into playback died there. This module
    speaks WASAPI, so it has to ask WASAPI which device it means.

    Resolved per stream rather than once at startup, so headphones plugged in
    after the application opened are the ones it plays through.
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


def _open_exclusive(
    device: int | None, request: OutputRequest, dtype: str
) -> sounddevice.OutputStream:
    """A stream straight to the hardware, with no conversion permitted."""
    return sounddevice.OutputStream(
        device=device,
        samplerate=request.sample_rate,
        channels=request.channels,
        dtype=dtype,
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
        extra_settings=sounddevice.WasapiSettings(exclusive=False, auto_convert=True),
    )


def _shared_result(
    device: int | None, request: OutputRequest, reason: str
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the mixer path, recording why it was taken when it was a fallback."""
    try:
        stream = _open_shared(device, request)
    except Exception as error:  # reported, never swallowed
        raise OutputUnavailableError(
            f"no output at {request.sample_rate} Hz: {error}"
        ) from error
    report = OutputReport(
        request=request,
        mode=OutputMode.SHARED,
        sample_rate=request.sample_rate,
        bit_depth=MIXER_BIT_DEPTH,
        fallback_reason=reason,
    )
    return stream, report, SHARED_DTYPE


def open_output(
    request: OutputRequest, device: int | None = None
) -> tuple[sounddevice.OutputStream, OutputReport, str]:
    """Open the best stream for `request`, with the report and the feed dtype.

    Raises OutputUnavailableError only when even the mixer path fails, which
    means there is no usable output device at all.
    """
    device = default_device() if device is None else device
    if request.mode is not OutputMode.EXCLUSIVE:
        return _shared_result(device, request, "")
    # Refused here rather than left to fail at the format search, so the
    # reason names the file instead of blaming the device. A lossy source has
    # no depth to hand an exclusive stream; an exclusive stream carrying a
    # decoder's output is not bit perfect however well it opens.
    if not request.states_depth:
        return _shared_result(device, request, NO_STATED_DEPTH)
    dtype = native_dtype(device, request)
    if dtype is None:
        return _shared_result(device, request, NO_EXCLUSIVE_FORMAT)
    try:
        stream = _open_exclusive(device, request, dtype)
    except Exception as error:  # noqa: BLE001 - a refusal is a fallback
        return _shared_result(device, request, str(error))
    report = OutputReport(
        request=request,
        mode=OutputMode.EXCLUSIVE,
        sample_rate=request.sample_rate,
        bit_depth=DTYPE_BIT_DEPTHS[dtype],
    )
    return stream, report, dtype
