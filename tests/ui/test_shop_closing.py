"""Closing the shops dialog clears every tick behind it. FR-S45.

Reported by Oliver on 2026-09-25: after a shopping round the ticks stayed, so
each one had to be unticked by hand before the next. Worse, a tick under
an artist rolled up could not be seen at all yet was still there for the
next press; so was a tick on an album a filter was holding out of sight.
Each test here fails on the code as it stood then.
"""

from __future__ import annotations

from results_support import gaps_with
from test_results_filter import HOUSE, POWER_UP, REMOTE_PLACES, filterable, tick
from test_shop_choosing import albums_in, shopping, with_shopping

from stellody.ui.results_ticks import TICKED, every_row_across, is_tickable


def ticks_left(dialog) -> list:
    """Every row still ticked, whether its artist is open or rolled up."""
    return [
        row
        for row in every_row_across(dialog.pages.trees)
        if is_tickable(row) and row.checkState(0) is TICKED
    ]


def test_closing_the_shops_clears_every_tick(application) -> None:
    """Close, then nothing ticked and nothing left to take to a shop."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    for album in albums_in(dialog):
        album.setCheckState(0, TICKED)
    dialog.open_shops()
    dialog.shops.reject()
    assert ticks_left(dialog) == []
    assert not dialog.shops_button.isEnabled()
    assert not dialog.copy_button.isEnabled()


def test_the_title_bar_close_clears_them_too(application) -> None:
    """The window's own close is a way out like any other."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    albums_in(dialog)[0].setCheckState(0, TICKED)
    dialog.open_shops()
    dialog.shops.close()
    assert ticks_left(dialog) == []


def test_a_tick_under_a_rolled_up_artist_goes(application) -> None:
    """A tick nobody can see is the one that would be sent by surprise."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    albums_in(dialog)[0].setCheckState(0, TICKED)
    dialog.sources[0].setExpanded(False)
    dialog.open_shops()
    dialog.shops.reject()
    assert ticks_left(dialog) == []


def test_a_tick_the_filter_holds_back_goes(application) -> None:
    """Cleared out of sight as well, so clearing the filter brings none back."""
    use_case, _opener, _clipboard = shopping()
    dialog = filterable(use_case)
    tick(dialog, POWER_UP)
    tick(dialog, REMOTE_PLACES)
    dialog.filter_to(HOUSE)
    dialog.open_shops()
    dialog.shops.reject()
    dialog.filter_to(())
    assert dialog.ticked() == ()


def test_ticking_again_after_closing_starts_afresh(application) -> None:
    """The next round is about what is ticked for it, nothing from before."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    first, second = albums_in(dialog)
    first.setCheckState(0, TICKED)
    dialog.open_shops()
    dialog.shops.reject()
    second.setCheckState(0, TICKED)
    dialog.open_shops()
    assert "1 album " in dialog.shops.counted.text()
    assert [album.title for album in dialog.ticked()] == [second.text(0)]
