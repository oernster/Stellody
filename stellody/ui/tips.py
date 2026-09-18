"""How long a button waits before it says what it is.

Qt holds a tooltip back for the better part of a second. That is right for a
dense form somebody is reading through and wrong for a strip of picture
buttons, where the picture is the only name a button has: waiting to be told
what one does means guessing at it; the wait is long enough that most
people move on rather than sit through it.

The delay is a style hint rather than a setting, so the one place to say
otherwise is a style of our own. Everything else is answered by the style
underneath exactly as before, so nothing about how the application is drawn
changes with it.

A tip also shows whichever application has focus. Reported by Oliver on
2026-09-18 on the installed build: tooltips came and went, because Qt shows one
only while its window is the active window. Hovering Stellody while another
application held focus showed nothing, which reads as a button with no name.
`WA_AlwaysShowToolTips` lifts that, read from the window a widget sits in. The
style is given every widget as it is polished, so it marks each window there:
the main window and every dialog, including one written after this, with no
list of windows to keep up to date.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle, QWidget

# Short enough to read as the button answering rather than as a wait, long
# enough that crossing a row of them does not leave a trail behind.
WAKE_UP_MS = 100


class QuickTips(QProxyStyle):
    """Every style question answered as before, bar when a tip is shown."""

    def polish(self, target, /):
        """Polished as before; a window also shows its tips without focus.

        `polish` is overloaded for a widget, a palette and the application,
        so anything other than a widget passes straight through.
        """
        if isinstance(target, QWidget) and target.isWindow():
            target.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        return super().polish(target)

    def styleHint(self, hint, option=None, widget=None, data=None) -> int:
        """Ours for the wake-up delay; the style underneath for the rest."""
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return WAKE_UP_MS
        return super().styleHint(hint, option, widget, data)


def show_tips_quickly(application: QApplication) -> None:
    """Put the shortened delay in front of whatever style is in use.

    Named rather than handed the style object itself. A proxy takes ownership
    of the style it is given and the application destroys the style it is
    replacing, which is the same one, so handing it over left the proxy
    holding something already deleted. A name has it build its own.
    """
    application.setStyle(QuickTips(application.style().name()))
