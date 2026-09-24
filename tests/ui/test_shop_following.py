"""The shops dialog following the ticks behind it. FR-S44.

The dialog stays open (FR-S07) while the results behind it can still be
ticked and unticked. Reported by Oliver on 2026-09-24: an album unticked after
a shop was chosen went on opening; every press of the shops control left
one more dialog standing, so the tabs piled up. Each test here fails on the
code as it stood then.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from results_support import gaps_with
from test_shop_choosing import QOBUZ, albums_in, with_shopping

from stellody.ui.results_ticks import TICKED

UNTICKED = Qt.CheckState.Unchecked


def ticked_one_then_the_other(dialog) -> None:
    """Tick the first album, open the shops, then swap the tick to the second."""
    first, second = albums_in(dialog)
    first.setCheckState(0, TICKED)
    dialog.open_shops()
    first.setCheckState(0, UNTICKED)
    second.setCheckState(0, TICKED)


def test_a_dialog_left_open_opens_what_is_ticked_now(application) -> None:
    """An album unticked since the dialog opened is not sent anywhere."""
    dialog, opener, _clipboard = with_shopping((gaps_with(albums=2),))
    ticked_one_then_the_other(dialog)
    dialog.shops.chose(QOBUZ)
    assert opener.opened == ["https://q/?q=U2%20Album%201"]


def test_the_count_follows_the_ticks(application) -> None:
    """What the dialog says it is about is what a press would open."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    ticked_one_then_the_other(dialog)
    albums_in(dialog)[0].setCheckState(0, TICKED)
    assert "2 albums" in dialog.shops.counted.text()


def test_a_second_press_brings_back_the_one_dialog(application) -> None:
    """Pressing again, open or closed, never stands up a second dialog."""
    dialog, opener, _clipboard = with_shopping((gaps_with(albums=2),))
    ticked_one_then_the_other(dialog)
    first = dialog.shops
    first.reject()
    dialog.open_shops()
    assert dialog.shops is first
    assert dialog.shops.isVisible()
    dialog.shops.chose(QOBUZ)
    assert opener.opened == ["https://q/?q=U2%20Album%201"]


def test_nothing_ticked_leaves_no_shop_to_choose(application) -> None:
    """A press that could open nothing is prevented, as FR-S04 does below."""
    dialog, opener, _clipboard = with_shopping((gaps_with(albums=2),))
    first, _second = albums_in(dialog)
    first.setCheckState(0, TICKED)
    dialog.open_shops()
    first.setCheckState(0, UNTICKED)
    assert not dialog.shops.shop_buttons["Qobuz"].isEnabled()
    first.setCheckState(0, TICKED)
    assert dialog.shops.shop_buttons["Qobuz"].isEnabled()
    assert opener.opened == []


def test_what_was_said_about_the_last_press_goes_with_the_ticks(
    application,
) -> None:
    """The line about the last press described albums no longer counted."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    first, second = albums_in(dialog)
    first.setCheckState(0, TICKED)
    dialog.open_shops()
    dialog.shops.chose(QOBUZ)
    assert dialog.shops.said.text()
    second.setCheckState(0, TICKED)
    assert dialog.shops.said.text() == ""
