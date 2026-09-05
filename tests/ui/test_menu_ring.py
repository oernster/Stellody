"""The menu titles as stops on the keyboard ring, one press each.

The model wants Tab and the horizontal arrows to walk File, View, Sound and
Help, a title to be highlighted as the ring passes over it, then Down to open
the one under the cursor. Qt gives none of that: a menu bar takes no tab focus
at all; asking for an active action OPENS the menu rather than lighting it.
So the cursor is the bar's own and this says what it does.

Driven with real key presses rather than `focusNextChild`, which asks the
WINDOW to move focus and never consults the focused widget. Measured: a Tab
press arrives at the bar's own key handler, so a walk driven off the window
steps straight past the titles and reports a pass while proving nothing.
"""

from __future__ import annotations

import contextlib
import pathlib
import tempfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from stellody.composition import build_window
from stellody.infrastructure.store import SqliteLibraryStore
from stellody.ui.menu_bar import NOWHERE
from stellody.ui.settings_keys import SETTING_ROOT

TITLES = ("&File", "&View", "&Sound", "&Help")
# The one entry chosen by these tests, reached with two Down presses in the
# View menu. It is picked because it toggles and nothing else: choosing an
# appearance would restyle the window under the test and move the focus.
HARMLESS = "Sort &Z to A"
STEPS_TO_HARMLESS = 2
# One more press than there are titles, so the walk is seen to LEAVE the bar
# rather than stopping at the last one.
PAST_THE_END = len(TITLES) + 1


@contextlib.contextmanager
def a_window(application: QApplication):
    """The real window over a throwaway store, pointed at a folder."""
    folder = pathlib.Path(tempfile.mkdtemp())
    store = SqliteLibraryStore(str(folder / "t.sqlite3"))
    store.set_setting(SETTING_ROOT, str(folder))
    made = build_window(store)
    made.show()
    application.processEvents()
    try:
        yield made
    finally:
        made.close()
        store.close()


@pytest.fixture
def window(application: QApplication):
    with a_window(application) as made:
        yield made


def press(application: QApplication, key: Qt.Key) -> None:
    """One key, at whatever currently holds focus."""
    QTest.keyClick(application.focusWidget(), key)


def opened(window) -> list[str]:
    """Every menu popup showing."""
    return [menu.title() for menu in window.findChildren(QMenu) if menu.isVisible()]


class TestWalkingTheTitles:
    def test_the_ring_enters_at_the_first_title(self, window) -> None:
        window.focusNextChild()
        assert window.menuBar().cursor_at == 0

    def test_arriving_opens_nothing(self, window) -> None:
        """Passing over a title is not asking for it."""
        window.focusNextChild()
        assert opened(window) == []

    @pytest.mark.parametrize("key", (Qt.Key.Key_Tab, Qt.Key.Key_Right))
    def test_forward_walks_every_title_then_leaves(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        """Tab and the right arrow are the same key at every stop."""
        window.focusNextChild()
        bar = window.menuBar()
        seen = [bar.cursor_at]
        for _ in range(PAST_THE_END):
            press(application, key)
            seen.append(bar.cursor_at)
        assert seen[: len(TITLES)] == list(range(len(TITLES)))
        assert seen[len(TITLES)] == NOWHERE, "and the ring moves on"
        assert application.focusWidget() is not bar

    @pytest.mark.parametrize("key", (Qt.Key.Key_Backtab, Qt.Key.Key_Left))
    def test_back_from_the_first_title_leaves_rather_than_wrapping(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        """A wrapping walk here would trap the ring on the bar for ever."""
        window.focusNextChild()
        bar = window.menuBar()
        assert bar.cursor_at == 0
        press(application, key)
        assert bar.cursor_at == NOWHERE
        assert application.focusWidget() is not bar

    def test_the_arrows_step_back_through_the_titles(
        self, application: QApplication, window
    ) -> None:
        window.focusNextChild()
        bar = window.menuBar()
        for _ in range(2):
            press(application, Qt.Key.Key_Right)
        assert bar.cursor_at == 2
        press(application, Qt.Key.Key_Left)
        assert bar.cursor_at == 1

    def test_coming_back_enters_at_the_last_title(
        self, application: QApplication, window
    ) -> None:
        """The ring enters at the end it arrives from, never beside where the
        cursor happened to be left; a pass would then reach one side only."""
        window.focusNextChild()
        bar = window.menuBar()
        for _ in range(len(TITLES)):
            press(application, Qt.Key.Key_Tab)
        assert application.focusWidget() is not bar
        press(application, Qt.Key.Key_Backtab)
        assert bar.cursor_at == len(TITLES) - 1

    def test_the_cursor_is_put_out_when_the_keyboard_moves_on(
        self, application: QApplication, window
    ) -> None:
        """A title left lit says focus is somewhere it is not."""
        window.focusNextChild()
        for _ in range(PAST_THE_END):
            press(application, Qt.Key.Key_Tab)
        assert window.menuBar().cursor_at == NOWHERE


class TestOpeningOne:
    @pytest.mark.parametrize(
        "key",
        (Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space),
    )
    def test_it_opens_the_title_under_the_cursor(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        """Down is the model's own; Enter and Space are the activate pair,
        neither of which Qt gives a menu bar title natively."""
        window.focusNextChild()
        press(application, Qt.Key.Key_Right)
        assert window.menuBar().cursor_at == 1
        QTest.keyClick(window.menuBar(), key)
        assert opened(window) == [TITLES[1]]

    def test_nothing_opens_where_the_ring_is_not_on_the_bar(self, window) -> None:
        bar = window.menuBar()
        assert bar.cursor_at == NOWHERE
        assert bar.open_current() is False
        assert opened(window) == []


class TestWhatIsDrawn:
    def test_the_ring_is_drawn_on_the_title_the_cursor_is_over(
        self, application: QApplication, window
    ) -> None:
        """Rendered rather than reasoned about: the rule is painted by the bar
        rather than named in the stylesheet, so only the drawing can say it."""
        bar = window.menuBar()

        def drawn():
            picture = QPixmap(bar.size())
            picture.fill()
            bar.render(picture)
            return picture.toImage()

        window.focusNextChild()
        on_first = drawn()
        bar.clear_cursor()
        assert drawn() != on_first, "a cursor on a title changes what is drawn"

    def test_moving_the_cursor_changes_what_is_drawn(
        self, application: QApplication, window
    ) -> None:
        bar = window.menuBar()

        def drawn():
            picture = QPixmap(bar.size())
            picture.fill()
            bar.render(picture)
            return picture.toImage()

        window.focusNextChild()
        on_first = drawn()
        press(application, Qt.Key.Key_Right)
        assert drawn() != on_first, "the ring moved with the cursor"

    def test_the_colour_comes_from_the_palette(self, window) -> None:
        """Handed down by the stylesheet, so the palette stays its one home."""
        assert window.menuBar().ringColour.startswith("#")


class TestATitleThatCannotBeUsed:
    def test_a_disabled_title_is_passed_over(
        self, application: QApplication, window
    ) -> None:
        """A dead stop is skipped rather than stalled on, so the walk lands on
        the title beyond it. Planted, since the application disables none."""
        bar = window.menuBar()
        bar.actions()[1].setEnabled(False)
        try:
            window.focusNextChild()
            assert bar.cursor_at == 0
            press(application, Qt.Key.Key_Right)
            assert bar.cursor_at == 2, "View was skipped"
        finally:
            bar.actions()[1].setEnabled(True)

    def test_a_disabled_first_title_is_not_where_the_ring_enters(
        self, application: QApplication, window
    ) -> None:
        bar = window.menuBar()
        bar.actions()[0].setEnabled(False)
        try:
            window.focusNextChild()
            assert bar.cursor_at == 1
        finally:
            bar.actions()[0].setEnabled(True)


def harmless_in(menu: QMenu):
    """The one entry these tests are willing to choose."""
    for action in menu.actions():
        if action.text() == HARMLESS:
            return action
    raise AssertionError(f"{HARMLESS} has left the View menu")


def live(window) -> QMenu | None:
    """Whichever menu is down, if one is."""
    showing = [menu for menu in window.findChildren(QMenu) if menu.isVisible()]
    return showing[0] if showing else None


class TestWhileOneIsDown:
    """An open menu owns the keyboard, so the bar never sees these presses.

    Measured on Qt 6.11.2 before any of this was written: with a popup down
    the horizontal arrows and Tab did nothing whatever, so the ring stopped
    dead at the first title opened. Space did nothing at any point in a menu
    either, since the Windows styles answer SH_Menu_SpaceActivatesItem with 0.
    """

    def opened_first(self, application: QApplication, window) -> QMenu:
        window.focusNextChild()
        press(application, Qt.Key.Key_Down)
        return live(window)

    def test_a_menu_comes_down_on_its_first_item(
        self, application: QApplication, window
    ) -> None:
        """Qt opens a popup with nothing highlighted; the model does not."""
        menu = self.opened_first(application, window)
        assert menu.activeAction() is menu.actions()[0]

    def test_a_dead_first_item_is_not_where_it_comes_down(
        self, application: QApplication, window
    ) -> None:
        """Planted, since the File menu disables none of its own."""
        window.focusNextChild()
        first = window.menuBar().actions()[0].menu().actions()[0]
        first.setEnabled(False)
        try:
            press(application, Qt.Key.Key_Down)
            menu = live(window)
            assert menu.activeAction() is not first
            assert menu.activeAction().isEnabled()
        finally:
            first.setEnabled(True)

    @pytest.mark.parametrize("key", (Qt.Key.Key_Right, Qt.Key.Key_Tab))
    def test_stepping_on_brings_the_next_title_down_too(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        """A menu already down says the bar is being read, so the title the
        ring steps to arrives open rather than asking a second time."""
        menu = self.opened_first(application, window)
        QTest.keyClick(menu, key)
        application.processEvents()
        assert opened(window) == [TITLES[1]]
        assert window.menuBar().cursor_at == 1

    @pytest.mark.parametrize("key", (Qt.Key.Key_Left, Qt.Key.Key_Backtab))
    def test_stepping_back_brings_the_previous_title_down_too(
        self, application: QApplication, window, key: Qt.Key
    ) -> None:
        menu = self.opened_first(application, window)
        QTest.keyClick(menu, Qt.Key.Key_Right)
        application.processEvents()
        QTest.keyClick(live(window), key)
        application.processEvents()
        assert opened(window) == [TITLES[0]]
        assert window.menuBar().cursor_at == 0

    def test_running_out_shuts_the_menu_and_hands_the_ring_on(
        self, application: QApplication, window
    ) -> None:
        """The bar is bounded here as everywhere; it never traps the ring."""
        bar = window.menuBar()
        self.opened_first(application, window)
        for _ in range(len(TITLES)):
            menu = live(window)
            if menu is None:
                break
            QTest.keyClick(menu, Qt.Key.Key_Right)
            application.processEvents()
        assert opened(window) == []
        assert bar.cursor_at == NOWHERE
        assert application.focusWidget() is not bar

    def test_space_chooses_the_highlighted_item(
        self, application: QApplication, window
    ) -> None:
        """Qt gives Space to a menu item nowhere, so the bar gives it."""
        window.focusNextChild()
        press(application, Qt.Key.Key_Right)
        press(application, Qt.Key.Key_Down)
        menu = live(window)
        for _ in range(STEPS_TO_HARMLESS):
            QTest.keyClick(menu, Qt.Key.Key_Down)
        chosen = menu.activeAction()
        assert chosen.text() == HARMLESS
        was = chosen.isChecked()
        QTest.keyClick(menu, Qt.Key.Key_Space)
        application.processEvents()
        assert chosen.isChecked() is not was, "the item acted"

    def test_space_leaves_exactly_what_enter_leaves(
        self, application: QApplication
    ) -> None:
        """Measured on Enter first: the menu shut, the cursor still on its
        title and the bar's active action cleared. Space is the same key by
        another name, so it lands in the same state.

        A window each, because the two have to be compared like with like:
        measured with Enter on BOTH passes, the first choosing made in a
        freshly shown window leaves the cursor cleared and the second does
        not, so one window would report a difference the keys never made.
        """

        def choose_with(key: Qt.Key) -> tuple:
            with a_window(application) as window:
                bar = window.menuBar()
                window.focusNextChild()
                press(application, Qt.Key.Key_Right)
                press(application, Qt.Key.Key_Down)
                menu = live(window)
                # Said outright rather than walked to, so what is under test
                # is the choosing rather than where Down presses land.
                menu.setActiveAction(harmless_in(menu))
                QTest.keyClick(menu, key)
                application.processEvents()
                return (opened(window), bar.cursor_at, bar.activeAction())

        assert choose_with(Qt.Key.Key_Space) == choose_with(Qt.Key.Key_Return)
