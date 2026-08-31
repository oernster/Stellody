"""A button says what it is almost as soon as somebody looks at it.

Qt holds a tooltip back for the better part of a second, which on a strip of
picture buttons means guessing at what each one does. The wait is a style hint
rather than a setting, so the only way to shorten it is a style that answers
that one question differently and every other question as before.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStyle, QStyleFactory

from stellody.composition import configure
from stellody.ui.tips import WAKE_UP_MS, QuickTips, show_tips_quickly

WAKE_UP = QStyle.StyleHint.SH_ToolTip_WakeUpDelay
FALL_ASLEEP = QStyle.StyleHint.SH_ToolTip_FallAsleepDelay


class _RememberingApplication:
    """Stands in for the application, to keep the real one's style alone.

    It answers everything the start of a launch asks of an application, so
    that the one call this is about can be watched for without a second real
    QApplication being made to hold a style nobody wants afterwards.
    """

    def __init__(self, style: QStyle) -> None:
        self._style = style
        self.given: QStyle | None = None

    def style(self) -> QStyle:
        return self._style

    def setStyle(self, style: QStyle) -> None:
        self.given = style

    def setApplicationName(self, name: str) -> None:
        """Absorbed: identity is not what this is about."""

    def setApplicationDisplayName(self, name: str) -> None:
        """Absorbed."""

    def setApplicationVersion(self, version: str) -> None:
        """Absorbed."""

    def setOrganizationName(self, name: str) -> None:
        """Absorbed."""

    def setQuitOnLastWindowClosed(self, quit_on_close: bool) -> None:
        """Absorbed."""

    def setWindowIcon(self, icon: object) -> None:
        """Absorbed."""


def _base() -> QStyle:
    """A real style to sit underneath, built fresh so nothing is shared."""
    return QStyleFactory.create(QStyleFactory.keys()[0])


def _quick() -> QuickTips:
    """The style under test, over a base of its own."""
    return QuickTips(_base().name())


class TestTheWait:
    def test_a_tip_waits_barely_at_all(self, application: QApplication) -> None:
        assert _quick().styleHint(WAKE_UP) == WAKE_UP_MS

    def test_that_is_far_less_than_qt_would_wait(
        self, application: QApplication
    ) -> None:
        """The point of it, stated against the wait it replaces."""
        base = _base()
        assert WAKE_UP_MS < base.styleHint(WAKE_UP)

    def test_every_other_question_is_answered_as_before(
        self, application: QApplication
    ) -> None:
        """Only the one hint moves, so nothing about the drawing changes."""
        base = _base()
        quick = _quick()
        for hint in (FALL_ASLEEP, QStyle.StyleHint.SH_ToolTip_Mask):
            assert quick.styleHint(hint) == base.styleHint(hint)


class TestPuttingItInFront:
    def test_the_application_is_given_the_quicker_style(
        self, application: QApplication
    ) -> None:
        standing_in = _RememberingApplication(_base())
        show_tips_quickly(standing_in)
        assert isinstance(standing_in.given, QuickTips)

    def test_it_keeps_the_style_that_was_there_underneath(
        self, application: QApplication
    ) -> None:
        """A proxy answers from the style underneath it, so that has to be
        the one already in use rather than whatever the default happens to
        be. It is named rather than handed over, since the application
        destroys the style it replaces.
        """
        was = _base()
        standing_in = _RememberingApplication(was)
        show_tips_quickly(standing_in)
        assert standing_in.given.baseStyle().name() == was.name()


class TestAtStartup:
    def test_the_launch_asks_for_them(self, application: QApplication) -> None:
        """Where it is asked for, since a style nobody installs changes nothing."""
        standing_in = _RememberingApplication(_base())
        configure(standing_in)
        assert isinstance(standing_in.given, QuickTips)
