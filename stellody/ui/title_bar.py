"""Asking Windows which monitor a window's title bar is on.

Windows maximises a window onto the monitor holding the LARGEST SHARE of it,
never onto the one its title bar is on. Measured on 2026-09-13 across four
monitors of mixed scaling: a window maximised on a 300 percent panel, then
dragged by its title bar onto the 100 percent screen above it, arrived still
sized for 250 percent at 4518 by 2258 pixels against a screen 1440 tall. Most
of it hung over the panels below. Windows therefore went on treating it as
theirs; a double click on a title bar sitting squarely on the top screen
maximised the window onto a panel beneath.

Only Windows can say where its title bar is, so this module asks it and does
nothing else. It is imported on Windows alone.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

# The name Qt gives an ordinary Windows message when it offers one to a window.
WINDOWS_MESSAGE = b"windows_generic_MSG"
# From WinUser.h. A double click on a title bar arrives as this system command,
# as does Maximise from the window menu.
WM_SYSCOMMAND = 0x0112
SC_MAXIMIZE = 0xF030
# Windows keeps the low four bits of a system command for its own use.
SYSCOMMAND_MASK = 0xFFF0
MONITOR_DEFAULTTONEAREST = 2
# CCHILDREN_TITLEBAR from WinUser.h, plus one for the title bar itself.
TITLE_BAR_STATES = 6


class _TitleBarInfo(ctypes.Structure):
    """TITLEBARINFO: where the title bar is, with the state of its parts."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcTitleBar", wintypes.RECT),
        ("rgstate", wintypes.DWORD * TITLE_BAR_STATES),
    ]


class _MonitorInfo(ctypes.Structure):
    """MONITORINFO: a monitor's whole rectangle and the part windows may use."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def is_maximise_command(event_type: bytes, message: int) -> bool:
    """Whether a message Qt offers the window is Windows about to maximise it.

    `message` is the address of the MSG Qt was handed, which is the only form
    the message reaches Python in.
    """
    if event_type != WINDOWS_MESSAGE:
        return False
    msg = wintypes.MSG.from_address(message)
    command = msg.wParam & SYSCOMMAND_MASK
    return msg.message == WM_SYSCOMMAND and command == SC_MAXIMIZE


def title_bar_monitor(window: int) -> tuple[int, int] | None:
    """The top left corner of the monitor holding most of the title bar.

    None when Windows will not say, which leaves the maximise to Windows. The
    library is loaded afresh rather than shared, so the argument types stated
    here belong to this call alone rather than to every caller of user32.
    """
    user32 = ctypes.WinDLL("user32")
    user32.GetTitleBarInfo.argtypes = [wintypes.HWND, ctypes.POINTER(_TitleBarInfo)]
    user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
    user32.MonitorFromRect.restype = wintypes.HMONITOR
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo)]
    bar = _TitleBarInfo(cbSize=ctypes.sizeof(_TitleBarInfo))
    if not user32.GetTitleBarInfo(window, ctypes.byref(bar)):
        return None
    monitor = user32.MonitorFromRect(
        ctypes.byref(bar.rcTitleBar), MONITOR_DEFAULTTONEAREST
    )
    found = _MonitorInfo(cbSize=ctypes.sizeof(_MonitorInfo))
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(found)):
        return None
    return (found.rcMonitor.left, found.rcMonitor.top)
