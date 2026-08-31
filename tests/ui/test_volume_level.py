"""The level itself: where it starts, what is remembered and what is shown.

Its appearance is asserted next door in test_volume_appearance.py; this file is
only about the number. A level that reaches the device but is never written
down is the failure a user reports as the application forgetting itself
between runs; so is one written down and never read back.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import SETTING_VOLUME
from stellody.ui.volume import DEFAULT_PERCENT, HALF, MAXIMUM_PERCENT

# A level that is neither the default nor an end of the range.
QUIET_PERCENT = 30


@pytest.fixture
def store() -> RememberingStore:
    """A store that starts with nothing remembered."""
    return RememberingStore()


@pytest.fixture
def player() -> RecordingPlayer:
    """A device that records what it was asked for."""
    return RecordingPlayer()


@pytest.fixture
def window(
    application: QApplication, store: RememberingStore, player: RecordingPlayer
) -> MainWindow:
    """A window over that store and that device."""
    return build(store, player)


def test_the_volume_starts_at_the_default_when_none_was_ever_chosen(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Full is startling on a first run; three quarters leaves room to go up."""
    assert window._transport.volume == DEFAULT_PERCENT / MAXIMUM_PERCENT
    assert player.volume == DEFAULT_PERCENT / MAXIMUM_PERCENT
    assert f"{DEFAULT_PERCENT}%" in window._tray.volume_button.toolTip()


def test_a_chosen_volume_is_written_down(
    window: MainWindow, store: RememberingStore
) -> None:
    window.set_volume(QUIET_PERCENT)
    assert store.get_setting(SETTING_VOLUME) == str(QUIET_PERCENT)


def test_the_volume_comes_back_as_it_was_left(
    application: QApplication, player: RecordingPlayer
) -> None:
    """The whole point of writing it down."""
    reopened = build(RememberingStore({SETTING_VOLUME: str(QUIET_PERCENT)}), player)
    assert reopened._transport.volume == QUIET_PERCENT / MAXIMUM_PERCENT
    assert f"{QUIET_PERCENT}%" in reopened._tray.volume_button.toolTip()


def test_a_stored_volume_that_is_not_a_number_falls_back_to_the_default(
    application: QApplication, player: RecordingPlayer
) -> None:
    """Silence and full are both a worse surprise than the first-run level."""
    reopened = build(RememberingStore({SETTING_VOLUME: "not a number"}), player)
    assert reopened._transport.volume == DEFAULT_PERCENT / MAXIMUM_PERCENT


def test_the_popup_shows_the_level_as_a_number_above_the_slider(
    window: MainWindow,
) -> None:
    """A slider says roughly; a number says which."""
    window.show()
    window._tray.volume_button.click()
    popup = window._tray._popup
    column = popup.layout()
    widgets = [column.itemAt(index).widget() for index in range(column.count())]
    assert widgets.index(popup.reading) < widgets.index(popup.slider), "above it"
    assert popup.reading.text() == f"{DEFAULT_PERCENT}%"
    popup.slider.setValue(QUIET_PERCENT)
    assert popup.reading.text() == f"{QUIET_PERCENT}%", "driven by the slider"


def press_over(popup, where: QPoint) -> None:
    """A press inside the popup's window at a point given on the screen."""
    QTest.mousePress(popup, Qt.MouseButton.LeftButton, pos=popup.mapFromGlobal(where))


def test_the_volume_button_puts_the_slider_up_and_takes_it_down(
    window: MainWindow,
) -> None:
    window.show()
    tray = window._tray
    QTest.mouseClick(tray.volume_button, Qt.MouseButton.LeftButton)
    assert tray._popup.isVisible() is True
    QTest.mouseClick(tray.volume_button, Qt.MouseButton.LeftButton)
    assert tray._popup.isVisible() is False, "the same button puts it away"


def test_the_press_that_closes_the_slider_does_not_reopen_it(
    window: MainWindow,
) -> None:
    """Windows replays a dismissing press to whatever is under the cursor.

    That replay reached the volume button, which reopened what its own press
    had just closed: measured as a slider that would not go away, doing so
    only sometimes, since the replay is what decides it.
    """
    window.show()
    tray = window._tray
    tray._open()
    assert tray._popup.isVisible() is True
    press_over(tray._popup, tray.volume_button.mapToGlobal(QPoint(0, 0)))
    assert tray._popup.isVisible() is False, "the press closed it"
    tray._open()
    assert tray._popup.isVisible() is False, "and the replayed click left it down"
    tray._open()
    assert tray._popup.isVisible() is True, "while a fresh press puts it back up"


def test_a_press_anywhere_else_closes_it_without_swallowing_the_next(
    window: MainWindow,
) -> None:
    """Only a press on the button itself is ever replayed onto the button."""
    window.show()
    tray = window._tray
    tray._open()
    press_over(tray._popup, window.mapToGlobal(window.rect().topLeft()))
    assert tray._popup.isVisible() is False
    tray._open()
    assert tray._popup.isVisible() is True, "the next press is a fresh one"


class TestWhereItSits:
    """Volume sits immediately left of mute. The two are one thought: how
    loud, then whether at all, so they read as a pair rather than as one
    control at each end of the window.
    """

    def test_it_is_laid_out_directly_before_mute(self, window: MainWindow) -> None:
        """Asked of the layout as well as of the drawing, since a widget left
        out of the layout sits at nothing, which a comparison of positions
        alone reports as a pass."""
        window.show()
        tray = window._tray
        row = tray.layout()
        widgets = [row.itemAt(position).widget() for position in range(row.count())]
        assert tray.volume_button in widgets, "it is actually laid out"
        assert widgets.index(tray.volume_button) + 1 == widgets.index(
            tray.mute_button
        ), "with nothing between the two"

    def test_it_is_drawn_to_the_left_of_mute(self, window: MainWindow) -> None:
        window.show()
        tray = window._tray
        here = tray.volume_button.mapTo(tray, tray.volume_button.rect().center())
        mute = tray.mute_button.mapTo(tray, tray.mute_button.rect().center())
        assert here.x() < mute.x()

    def test_the_ring_reaches_it_just_before_mute(self, window: MainWindow) -> None:
        stops = window._tray.ring_stops()
        assert stops.index(window._tray.volume_button) + 1 == stops.index(
            window._tray.mute_button
        )

    def test_the_bottom_strip_no_longer_carries_it(self, window: MainWindow) -> None:
        """One home for it, so the two strips cannot both claim to hold it."""
        assert not hasattr(window._bottom_tray, "volume_button")
        assert window._bottom_tray.switch_stops() == (
            window._bottom_tray.shuffle_button,
            window._bottom_tray.repeat_button,
        )


class TestWhereTheSliderOpens:
    """Above the button where there is room and below where there is not.

    Always above was right while the button lived on the bottom strip. From
    the tray at the top of the window it would put the slider off the top of
    the screen, so the rule is asked of the room rather than assumed.
    """

    def _room(self, window: MainWindow) -> int:
        """How tall the slider wants to be, once it exists to be asked."""
        return window._tray._popup.sizeHint().height()

    @pytest.fixture(autouse=True)
    def _take_it_down(self, window: MainWindow):
        """A popup grabs the keyboard, so one left up walks the next test's
        ring for it. Taken down here rather than at the end of each test,
        since a failure part way through would skip that."""
        yield
        window._tray._popup.hide()

    def _sides(self, window: MainWindow) -> tuple[int, int]:
        """Where the slider sits and where the button does, down the screen.

        Read as centres rather than as edges. Which side of the button it is
        on is the behaviour; an edge landing on the exact pixel of the other
        is a window manager's business rather than this rule's.
        """
        button = window._tray.volume_button
        popup = window._tray._popup
        return (
            popup.y() + popup.height() // HALF,
            button.mapToGlobal(button.rect().center()).y(),
        )

    def test_it_opens_below_a_button_with_nothing_above_it(
        self, window: MainWindow
    ) -> None:
        window.show()
        window.move(0, 0)
        window._tray._open()
        slider, button = self._sides(window)
        assert slider > button

    def test_it_opens_above_a_button_with_room_over_it(
        self, window: MainWindow
    ) -> None:
        window.show()
        window.move(0, self._room(window) + window._tray.volume_button.height())
        window._tray._open()
        slider, button = self._sides(window)
        assert slider < button
