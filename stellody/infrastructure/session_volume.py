"""What Windows' Volume mixer is doing to one program's sound. FR-O21.

Windows keeps a volume and a mute for every program on every playback device,
remembered across runs against the program's path; everything the program
sends is multiplied by it. Measured on 2026-10-25: an installed Stellody held at
nought there played nothing at all, while its visualiser moved and the same
code run from source as `python.exe` played perfectly. Nothing in Stellody
could see it, so this reads it.

Each device keeps one audio session per program that has opened a stream on it.
Only an ACTIVE session is read: one left behind on a device not in use says
nothing about where the music is going now.

Reads only. Stellody never changes the setting, which is the listener's
(Oliver's ruling). Windows only; `output.py` asks it nowhere else.
"""

from __future__ import annotations

from ctypes import POINTER, byref, c_float, c_int, c_uint, c_void_p

from stellody.domain.playback import SystemVolume
from stellody.infrastructure.endpoints import (
    CLSCTX_ALL,
    call,
    each_render_device,
    guid,
    release,
)

# The COM identities involved, as Windows publishes them in audiopolicy.h.
IID_AUDIO_SESSION_MANAGER2 = "{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}"
IID_AUDIO_SESSION_CONTROL2 = "{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}"
IID_SIMPLE_AUDIO_VOLUME = "{87CE5498-68D6-44E5-9215-6DA47EF883D8}"
AUDIO_SESSION_STATE_ACTIVE = 1

# Places in each interface's table of methods, after the three every COM
# interface starts with; QueryInterface is the first of those three.
QUERY_INTERFACE = 0
DEVICE_ACTIVATE = 3
MANAGER_GET_SESSION_ENUMERATOR = 5
SESSIONS_GET_COUNT = 3
SESSIONS_GET_SESSION = 4
CONTROL_GET_STATE = 3
CONTROL_GET_PROCESS_ID = 14
VOLUME_GET_MASTER_VOLUME = 4
VOLUME_GET_MUTE = 6


def program_volume(pid: int) -> SystemVolume | None:
    """How the mixer holds program `pid` where it is playing; None if not.

    Where it plays on more than one device at once, a device silencing it is
    the answer, since that is the one a listener has to be told about.
    Raises OSError.
    """
    found = tuple(
        volume
        for device in each_render_device(lambda device: _sessions_of(device, pid))
        for volume in device
    )
    if not found:
        return None
    return next((volume for volume in found if volume.silences), found[0])


def _queried(obj: c_void_p, iid: str) -> c_void_p:
    """The same object seen through another of its interfaces."""
    other = c_void_p()
    call(
        obj,
        QUERY_INTERFACE,
        byref(guid(iid)),
        byref(other),
        argtypes=(c_void_p, POINTER(c_void_p)),
    )
    return other


def _sessions_of(device: c_void_p, pid: int) -> tuple[SystemVolume, ...]:
    """The volume of every active session `pid` has on this device."""
    manager = c_void_p()
    call(
        device,
        DEVICE_ACTIVATE,
        byref(guid(IID_AUDIO_SESSION_MANAGER2)),
        CLSCTX_ALL,
        None,
        byref(manager),
        argtypes=(c_void_p, c_uint, c_void_p, POINTER(c_void_p)),
    )
    try:
        sessions = c_void_p()
        call(
            manager,
            MANAGER_GET_SESSION_ENUMERATOR,
            byref(sessions),
            argtypes=(POINTER(c_void_p),),
        )
        try:
            count = c_int()
            call(sessions, SESSIONS_GET_COUNT, byref(count), argtypes=(POINTER(c_int),))
            held = (_session(sessions, at, pid) for at in range(count.value))
            return tuple(volume for volume in held if volume is not None)
        finally:
            release(sessions)
    finally:
        release(manager)


def _session(sessions: c_void_p, at: int, pid: int) -> SystemVolume | None:
    """Session `at`'s volume if it is `pid`'s and active; None otherwise."""
    control = c_void_p()
    call(
        sessions,
        SESSIONS_GET_SESSION,
        at,
        byref(control),
        argtypes=(c_int, POINTER(c_void_p)),
    )
    try:
        state = c_int()
        call(control, CONTROL_GET_STATE, byref(state), argtypes=(POINTER(c_int),))
        if state.value != AUDIO_SESSION_STATE_ACTIVE:
            return None
        if _process_of(control) != pid:
            return None
        return _volume_of(control)
    finally:
        release(control)


def _process_of(control: c_void_p) -> int:
    """Which program a session belongs to."""
    second = _queried(control, IID_AUDIO_SESSION_CONTROL2)
    try:
        pid = c_uint()
        call(second, CONTROL_GET_PROCESS_ID, byref(pid), argtypes=(POINTER(c_uint),))
        return pid.value
    finally:
        release(second)


def _volume_of(control: c_void_p) -> SystemVolume:
    """The level and mute the mixer holds a session at."""
    simple = _queried(control, IID_SIMPLE_AUDIO_VOLUME)
    try:
        level = c_float()
        muted = c_int()
        call(
            simple,
            VOLUME_GET_MASTER_VOLUME,
            byref(level),
            argtypes=(POINTER(c_float),),
        )
        call(simple, VOLUME_GET_MUTE, byref(muted), argtypes=(POINTER(c_int),))
        return SystemVolume(level=level.value, muted=bool(muted.value))
    finally:
        release(simple)
