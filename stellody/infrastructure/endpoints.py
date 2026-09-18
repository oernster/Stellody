"""The playback devices Windows lists, in Windows' own order, with identities.

Measured on 2026-09-18 (`OUTPUTS.md`, Amendment 2): PortAudio's WASAPI outputs
arrive in exactly the order `IMMDeviceEnumerator::EnumAudioEndpoints` gives
them, so this order is what tells two devices of one name apart. Qt lists the
same devices in another order (the default first), which is why Qt's list is
not used on Windows.

Plain ctypes over COM rather than a COM library, the same choice the rest of
the application makes for the platform: nothing is added to the install for
four interface calls. Windows only; `output_list.py` asks it nowhere else.
"""

from __future__ import annotations

import ctypes
from ctypes import (
    HRESULT,
    POINTER,
    WINFUNCTYPE,
    byref,
    c_uint,
    c_ulong,
    c_ushort,
    c_void_p,
    c_wchar_p,
)

from stellody.domain.outputs import OutputDevice

# The COM identities involved, as Windows publishes them in mmdeviceapi.h and
# functiondiscoverykeys_devpkey.h.
CLSID_MM_DEVICE_ENUMERATOR = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
IID_IMM_DEVICE_ENUMERATOR = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
PKEY_DEVICE_FRIENDLY_NAME = "{A45C254E-DF1C-4EFD-8020-67D146A850E0}"
FRIENDLY_NAME_PID = 14
E_RENDER = 0
DEVICE_STATE_ACTIVE = 1
CLSCTX_ALL = 23
STGM_READ = 0
COINIT_APARTMENTTHREADED = 2
# Returned when the thread's COM is already set up another way, as it is on
# Qt's thread; the thread can use COM regardless, so it is not a fault.
RPC_E_CHANGED_MODE = -2147417850

# Places in each interface's table of methods, after the three every COM
# interface starts with.
RELEASE = 2
ENUM_AUDIO_ENDPOINTS = 3
COLLECTION_GET_COUNT = 3
COLLECTION_ITEM = 4
DEVICE_OPEN_PROPERTY_STORE = 4
DEVICE_GET_ID = 5
STORE_GET_VALUE = 5


class GUID(ctypes.Structure):
    _fields_ = [
        ("data1", c_ulong),
        ("data2", c_ushort),
        ("data3", c_ushort),
        ("data4", ctypes.c_ubyte * 8),
    ]


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", c_ulong)]


class PROPVARIANT(ctypes.Structure):
    """The variant a property arrives in; only its string pointer is read."""

    _fields_ = [
        ("vt", c_ushort),
        ("reserved1", c_ushort),
        ("reserved2", c_ushort),
        ("reserved3", c_ushort),
        ("value", c_void_p),
        ("padding", c_void_p),
    ]


def _guid(text: str) -> GUID:
    guid = GUID()
    ctypes.oledll.ole32.CLSIDFromString(c_wchar_p(text), byref(guid))
    return guid


def _call(obj: c_void_p, index: int, *args, argtypes=()) -> int:
    """Call method `index` of a COM object; a failure raises OSError."""
    table = ctypes.cast(obj, POINTER(POINTER(c_void_p)))[0]
    method = WINFUNCTYPE(HRESULT, c_void_p, *argtypes)(table[index])
    return method(obj, *args)


def _release(obj: c_void_p) -> None:
    table = ctypes.cast(obj, POINTER(POINTER(c_void_p)))[0]
    WINFUNCTYPE(c_ulong, c_void_p)(table[RELEASE])(obj)


def render_endpoints() -> tuple[OutputDevice, ...]:
    """Every active playback device, in Windows' order. Raises OSError.

    COM is set up for the calling thread where it is not already, then taken
    down again after; a thread that already has it keeps it as it was.
    """
    ole32 = ctypes.oledll.ole32
    try:
        ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        started = True
    except OSError as error:
        if error.winerror != RPC_E_CHANGED_MODE:
            raise
        started = False
    try:
        return _enumerated(ole32)
    finally:
        if started:
            ctypes.windll.ole32.CoUninitialize()


def _enumerated(ole32) -> tuple[OutputDevice, ...]:
    enumerator = c_void_p()
    ole32.CoCreateInstance(
        byref(_guid(CLSID_MM_DEVICE_ENUMERATOR)),
        None,
        CLSCTX_ALL,
        byref(_guid(IID_IMM_DEVICE_ENUMERATOR)),
        byref(enumerator),
    )
    try:
        collection = c_void_p()
        _call(
            enumerator,
            ENUM_AUDIO_ENDPOINTS,
            E_RENDER,
            DEVICE_STATE_ACTIVE,
            byref(collection),
            argtypes=(c_uint, c_uint, POINTER(c_void_p)),
        )
        try:
            count = c_uint()
            _call(
                collection,
                COLLECTION_GET_COUNT,
                byref(count),
                argtypes=(POINTER(c_uint),),
            )
            return tuple(_item(collection, at) for at in range(count.value))
        finally:
            _release(collection)
    finally:
        _release(enumerator)


def _item(collection: c_void_p, at: int) -> OutputDevice:
    device = c_void_p()
    _call(
        collection,
        COLLECTION_ITEM,
        at,
        byref(device),
        argtypes=(c_uint, POINTER(c_void_p)),
    )
    try:
        return OutputDevice(identity=_identity(device), name=_friendly_name(device))
    finally:
        _release(device)


def _identity(device: c_void_p) -> str:
    text = c_wchar_p()
    _call(device, DEVICE_GET_ID, byref(text), argtypes=(POINTER(c_wchar_p),))
    try:
        return text.value or ""
    finally:
        ctypes.windll.ole32.CoTaskMemFree(text)


def _friendly_name(device: c_void_p) -> str:
    store = c_void_p()
    _call(
        device,
        DEVICE_OPEN_PROPERTY_STORE,
        STGM_READ,
        byref(store),
        argtypes=(c_uint, POINTER(c_void_p)),
    )
    try:
        key = PROPERTYKEY(_guid(PKEY_DEVICE_FRIENDLY_NAME), FRIENDLY_NAME_PID)
        value = PROPVARIANT()
        _call(
            store,
            STORE_GET_VALUE,
            byref(key),
            byref(value),
            argtypes=(POINTER(PROPERTYKEY), POINTER(PROPVARIANT)),
        )
        try:
            return ctypes.wstring_at(value.value) if value.value else ""
        finally:
            ctypes.oledll.ole32.PropVariantClear(byref(value))
    finally:
        _release(store)
