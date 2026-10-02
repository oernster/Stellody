"""FR-D86: the "Show:" row above the genres in the results filter."""

from __future__ import annotations

from test_results_filter import NOBODY_HELD, POWER_UP, REMOTE_PLACES, filterable, shown

from stellody.domain.showing import EVERYTHING, Showing
from stellody.ui.discovery_dialog import MIXES_LABEL
from stellody.ui.results_filter import (
    ALBUMS_LABEL,
    ARTISTS_LABEL,
    SHOW_SERIES_LABEL,
    ResultsFilterDialog,
)


def kinds(dialog: ResultsFilterDialog) -> list:
    """The four boxes, in the order drawn."""
    return [dialog.albums, dialog.mixes, dialog.series, dialog.artists]


def test_every_kind_starts_shown(application) -> None:
    dialog = ResultsFilterDialog(("House",))
    assert [box.text() for box in kinds(dialog)] == [
        ALBUMS_LABEL,
        MIXES_LABEL,
        SHOW_SERIES_LABEL,
        ARTISTS_LABEL,
    ]
    assert dialog.showing() == EVERYTHING


def test_a_kind_left_out_is_enough_to_filter_by(application) -> None:
    """No genre ticked, one kind clear: the press changes something."""
    dialog = ResultsFilterDialog(("House",))
    assert not dialog.filter_button.isEnabled()
    dialog.artists.setChecked(False)
    assert dialog.filter_button.isEnabled()


def test_clear_takes_every_filter_off(application) -> None:
    """No genre ticked and every kind shown, which is no filter at all."""
    dialog = ResultsFilterDialog(("House",), ("House",), showing=Showing(series=False))
    dialog.clear()
    assert dialog.picked() == ()
    assert dialog.showing() == EVERYTHING


def test_it_opens_holding_the_kinds_already_left_out(application) -> None:
    dialog = ResultsFilterDialog(("House",), showing=Showing(mixes=False))
    assert dialog.showing() == Showing(mixes=False)


def test_the_answer_is_shown_as_the_kinds_leave_it(application) -> None:
    """Similar artists left out: the heading holding nothing else goes."""
    dialog = filterable()
    dialog.filter_to((), Showing(artists=False))
    assert NOBODY_HELD not in shown(dialog)
    assert REMOTE_PLACES.artist in shown(dialog)
    assert POWER_UP.artist in shown(dialog)
    assert dialog.filter_button.isChecked()
    dialog.filter_to((), EVERYTHING)
    assert NOBODY_HELD in shown(dialog)
    assert not dialog.filter_button.isChecked()
