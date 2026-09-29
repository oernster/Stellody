"""FR-D74, FR-D75: a series on screen; a heading with nothing under it.

Real widgets on the offscreen platform; nothing is shown.
"""

from __future__ import annotations

from results_support import gaps_with, made, rows_under

from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.text import VARIOUS_ARTISTS
from stellody.ui.results_ticks import album_on
from stellody.ui.results_words import LEGEND_SOURCE, SERIES, source_row

ADAPT = "Global Underground: Adapt"


def adapt_with(count: int) -> Gaps:
    """The Adapt series with this many missing volumes."""
    return Gaps(
        artist=ADAPT,
        albums=tuple(ReleaseGroup(title=f"{ADAPT} #{n + 3}") for n in range(count)),
        series=True,
    )


def test_a_series_heading_says_it_is_one(application) -> None:
    """The FR-D74 acceptance."""
    dialog = made((adapt_with(4),))
    assert dialog.sources[0].text(0) == f"{ADAPT} (series, 4 albums)"
    assert source_row(adapt_with(4)) == dialog.sources[0].text(0)
    assert rows_under(dialog.sources[0])[0] == f"{ADAPT} #3"


def test_an_artist_heading_is_unchanged(application) -> None:
    assert SERIES not in source_row(gaps_with(albums=2, artist="Giza Djs"))


def test_a_series_entry_goes_to_the_shops_under_various_artists(application) -> None:
    """A series names nobody; the catalogue credits its entries to Various."""
    dialog = made((adapt_with(1),))
    wanted = album_on(dialog.sources[0].child(0))
    assert (wanted.artist, wanted.title) == (VARIOUS_ARTISTS, f"{ADAPT} #3")


def test_an_empty_heading_is_left_out(application) -> None:
    """The FR-D75 acceptance."""
    empty = Gaps(artist="Global Underground")
    dialog = made((empty, gaps_with(albums=3, artist="Giza Djs")))
    assert [source.text(0) for source in dialog.sources] == [
        source_row(gaps_with(albums=3, artist="Giza Djs"))
    ]


def test_the_key_names_a_series_too() -> None:
    assert "series" in LEGEND_SOURCE
