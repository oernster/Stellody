"""The bottom strip: the two switches, the two library errands and donate.

Split out of the switch tests because it is its own strip with its own rules.
What is asserted here is that each control reaches the transport or the window,
that it shows its own state and that a switch is there again next time the
application opens. A switch doing two of those and not the third is the one
that gets reported as a bug.

Shuffle and repeat keep one picture and light the button, so what is asserted
is the button's own state and which artwork it is wearing. Repeat is the only
control on either strip holding three states, which is why its tooltip names
the control rather than the next press; the picture still names the press.

The donate button is the one thing here that leaves the application, so what is
asserted is the address handed outward, through a seam of our own rather than
by mocking Qt or by opening a browser in the middle of a test run.
"""

from __future__ import annotations

import pytest
from conftest import RecordingPlayer
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build, picture, strip_plain, strip_struck

from stellody.domain.playback import RepeatMode
from stellody.shared import resources
from stellody.shared.version import DONATE_URL
from stellody.ui import menus as window_module
from stellody.ui.bottom_tray import REPEAT_TOOLTIP, BottomTray
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import FALSE, SETTING_REPEAT, SETTING_SHUFFLE, TRUE

# Wide enough that both outer columns have room to take an equal share.
WIDE_STRIP_PX = 1400
# One pixel of rounding where the width is odd; no more than that.
CENTRE_SLACK_PX = 1
# Down to a window narrower than anything worth using.
NARROWING_PX = (1600, 1400, 1100, 1000, 900, 800, 700)

# Written out rather than read from the source it is checking. Comparing the
# constant against itself passes whatever it is changed to, which for a payment
# address is the one change that must never happen quietly.
EXPECTED_DONATE_URL = "https://www.paypal.com/ncp/payment/QGC2XK2Z5WNUW"


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


def test_the_repeat_tooltip_names_the_control_in_every_state(
    window: MainWindow,
) -> None:
    """Three states, so naming only the next press reads as a stuck switch.

    Checked in all three rather than in one, since the wording is now meant to
    be the thing that does NOT move as the button is pressed.
    """
    button = window._bottom_tray.repeat_button
    for _ in RepeatMode:
        assert button.toolTip() == REPEAT_TOOLTIP
        window.toggle_repeat()
    assert window._transport.repeat is RepeatMode.OFF, "a full cycle, back to off"


def test_the_shuffle_switch_reaches_the_transport_and_shows_the_next_press(
    window: MainWindow,
) -> None:
    """The picture offers the state a press would reach, as the tooltip does."""
    button = window._bottom_tray.shuffle_button
    art = resources.shuffle_icon_path()
    assert button.isChecked() is False
    assert picture(button) == strip_plain(art), "off, so a press would scatter"
    window.toggle_shuffle()
    assert window._transport.shuffled is True
    assert button.isChecked() is True
    assert button.toolTip() == "Turn shuffle off"
    assert picture(button) == strip_struck(art), "on, so a press would stop it"
    window.toggle_shuffle()
    assert window._transport.shuffled is False
    assert button.isChecked() is False
    assert picture(button) == strip_plain(art)


def test_the_repeat_switch_reaches_the_transport_and_lights_while_it_is_on(
    window: MainWindow,
) -> None:
    button = window._bottom_tray.repeat_button
    wheel = resources.repeat_icon_path()
    one_track = resources.repeat_one_icon_path()
    assert button.isChecked() is False
    assert picture(button) == strip_plain(wheel), "a press would repeat the album"

    window.toggle_repeat()
    assert window._transport.repeat is RepeatMode.ALBUM
    assert button.isChecked() is True
    assert picture(button) == strip_plain(one_track), "the numbered wheel next"

    window.toggle_repeat()
    assert window._transport.repeat is RepeatMode.ONE
    assert button.isChecked() is True, "holding one track is still repeating"
    assert picture(button) == strip_struck(wheel), "the cross offers to stop"

    window.toggle_repeat()
    assert window._transport.repeat is RepeatMode.OFF
    assert button.isChecked() is False
    assert picture(button) == strip_plain(wheel), "back where it started"


def test_the_repeat_switch_writes_down_which_state_it_is_in(
    window: MainWindow, store: RememberingStore
) -> None:
    """Repeat holds three states, so a boolean could not say where it is."""
    for expected in (RepeatMode.ALBUM, RepeatMode.ONE, RepeatMode.OFF):
        window.toggle_repeat()
        assert store.get_setting(SETTING_REPEAT) == expected.value


def test_a_reopened_window_finds_the_repeat_mode_it_was_left_in(
    application: QApplication, player: RecordingPlayer
) -> None:
    """Every mode round-trips, not only the boolean an older store held."""
    for mode in RepeatMode:
        reopened = build(RememberingStore({SETTING_REPEAT: mode.value}), player)
        assert reopened._transport.repeat is mode
        assert reopened._bottom_tray.repeat_button.isChecked() is mode.repeats


def test_a_reopened_window_finds_shuffle_as_it_was_left(
    application: QApplication, player: RecordingPlayer
) -> None:
    """Both ways round, so a switch stuck on would pass half of this."""
    for shuffled, stored in ((True, TRUE), (False, FALSE)):
        reopened = build(RememberingStore({SETTING_SHUFFLE: stored}), player)
        assert reopened._transport.shuffled is shuffled
        assert reopened._bottom_tray.shuffle_button.isChecked() is shuffled


def test_the_donate_button_sits_outside_everything_else(window: MainWindow) -> None:
    """It belongs to nothing on screen, so it sits where nothing else is."""
    window.show()
    tray = window._bottom_tray

    # Read off where things are DRAWN rather than off the top layout's own
    # children: the strip is laid in three columns holding rows of their own,
    # so the outer layout no longer names each control directly.
    def across(widget) -> int:
        return widget.mapTo(tray, widget.rect().center()).x()

    others = [
        across(stop) for stop in tray.ring_stops() if stop is not tray.donate_button
    ]
    assert across(tray.donate_button) < min(others), "left of everything else"
    assert (
        across(tray.donate_button) < across(tray.separator) < min(others)
    ), "ruled off from what follows it"
    assert tray.donate_button in tray.ring_stops()
    assert tray.donate_button.isEnabled(), "unlike the repair control, this works"
    assert "opens your browser" in tray.donate_button.toolTip()


def test_pressing_donate_asks_the_desktop_for_that_one_address(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam is stood in front of, so no browser opens in a test run."""
    asked: list[str] = []
    monkeypatch.setattr(
        window_module, "open_externally", lambda address: asked.append(address) or True
    )
    window._bottom_tray.donate_button.click()
    assert asked == [EXPECTED_DONATE_URL]
    assert DONATE_URL == EXPECTED_DONATE_URL, "the address changed"
    assert DONATE_URL.startswith("https://"), "never handed out over plain http"


def test_a_desktop_that_will_not_open_a_browser_says_so(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Silence would leave a button that appears to do nothing at all."""
    monkeypatch.setattr(window_module, "open_externally", lambda address: False)
    window._bottom_tray.donate_button.click()
    assert "Could not open a browser" in window.statusBar().currentMessage()


def test_repair_follows_rescan_on_the_bottom_strip(window: MainWindow) -> None:
    """Repair is the answer to what a rescan finds, so it follows rescan.

    Both sit on the bottom strip rather than in the tray above. They are
    errands about what the library holds rather than about what is playing,
    so they belong among the things that outlast a track.
    """
    window.show()
    tray = window._bottom_tray

    def across(widget) -> int:
        return widget.mapTo(tray, widget.rect().center()).x()

    assert across(tray.rescan_button) < across(tray.repair_button)
    assert across(tray.repair_button) < across(tray.visualiser), "on the left"
    assert tray.repair_button in tray.ring_stops()
    assert not hasattr(window._tray, "rescan_button"), "one home, not two"
    assert not hasattr(window._tray, "repair_button"), "one home, not two"


def test_the_repair_button_names_the_press_and_waits_to_be_told(
    window: MainWindow,
) -> None:
    """Drawn, disabled until a window is told there is something to act on.

    A window built without the repair service offers nothing, which is what this
    one is. The tooltip names what THIS press does, which is open the screen,
    rather than what a control inside that screen does; it is shaped like the
    rescan beside it, the two being a pair.

    It also carries the promise. Repair is the one control on this strip
    that sounds like it changes somebody's files; the whole application
    exists because another player did exactly that, so the
    answer is given where the gesture is offered rather than only inside
    the screen it opens.
    """
    button = window._bottom_tray.repair_button
    assert not button.isEnabled()
    assert button.toolTip() == "Repair the library (your music files are never changed)"
    assert not button.icon().isNull(), "drawn, not merely reserved"


class TestTheStripKeepsItsShapeAsTheWindowNarrows:
    """The strip gained three controls, so what it does for room is settled.

    A window nobody has to maximise is the case that matters: the tray above
    was getting crowded, which is why they moved down here at all.
    """

    def test_a_rule_stands_between_the_errands_and_what_is_shown(
        self, window: MainWindow
    ) -> None:
        """Rescanning the library is a different errand from drawing it."""
        window.show()
        tray = window._bottom_tray
        where = tray.showing_separator.mapTo(
            tray, tray.showing_separator.rect().center()
        )
        repair = tray.repair_button.mapTo(tray, tray.repair_button.rect().center())
        first = tray.showing.stops()[0]
        drawn = first.mapTo(tray, first.rect().center())
        assert repair.x() < where.x() < drawn.x()

    def test_the_visualiser_sits_at_the_middle_of_a_wide_strip(
        self, application: QApplication
    ) -> None:
        """Not the middle of what the two groups leave over, which is not the
        same thing once one group is wider than the other.

        Built on its own rather than inside a window: the offscreen platform
        will not grow a window past the screen it reports, so a strip measured
        through one is only ever measured at that width.
        """
        tray = BottomTray(None)
        try:
            tray.resize(WIDE_STRIP_PX, tray.sizeHint().height())
            tray.show()
            application.processEvents()
            middle = tray.visualiser.geometry().center().x()
            assert abs(middle - WIDE_STRIP_PX // 2) <= CENTRE_SLACK_PX
        finally:
            tray.deleteLater()

    def test_nothing_is_ever_sat_on_however_narrow_it_gets(
        self, application: QApplication
    ) -> None:
        """Laying all three in one cell centres it exactly and overlaps the
        errands below about 1100 pixels, measured. Three columns give way
        instead: the visualiser drifts rather than being covered."""
        tray = BottomTray(None)
        try:
            tray.show()
            for width in NARROWING_PX:
                tray.resize(width, tray.sizeHint().height())
                application.processEvents()
                seen = tray.visualiser.geometry()
                left = tray.showing.geometry()
                right = tray.shuffle_button.geometry()
                assert left.right() < seen.left(), f"the errands clear it at {width}"
                assert seen.right() < right.left(), f"the settings clear it at {width}"
        finally:
            tray.deleteLater()
