"""FR-D74, FR-D75: a series on screen; a heading with nothing under it.

Real widgets on the offscreen platform; nothing is shown.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget
from results_support import gaps_with, made, rows_under

from stellody.application.values import PERCENT, DiscoveryProgress, DiscoveryStage
from stellody.domain.discovery import Gaps, ReleaseGroup
from stellody.domain.text import VARIOUS_ARTISTS
from stellody.ui.discovery_progress import DiscoveryBars
from stellody.ui.results_ticks import album_on
from stellody.ui.results_words import LEGEND_SOURCE, SERIES, source_row
from stellody.ui.tray_metrics import BUTTON_PX

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


def test_the_series_stage_has_a_bar_of_its_own(application) -> None:
    """FR-D83, ruled on 2026-10-02. Before it, series borrowed the first bar,
    which Oliver reported on 2026-10-01 read as a run gone back to nothing."""
    holder = QWidget()
    bars = DiscoveryBars(holder, BUTTON_PX)
    bars.show_progress(DiscoveryProgress(artist="Dilby", done=9, total=10))
    bars.show_progress(
        DiscoveryProgress(artist=ADAPT, done=0, total=40, stage=DiscoveryStage.SERIES)
    )
    assert bars.looking_up.wanted == "Looking up 100%"
    assert bars.checking_series.wanted == "Checking series 0%"
    assert not bars.checking_styles.wanted.endswith("%")


def test_a_run_checking_no_series_leaves_its_bar_at_rest(application) -> None:
    """Compilations left out: a full series bar would claim work never done."""
    holder = QWidget()
    bars = DiscoveryBars(holder, BUTTON_PX)
    bars.show_progress(DiscoveryProgress(artist="Dilby", done=9, total=10))
    bars.show_progress(
        DiscoveryProgress(artist="x", done=0, total=5, stage=DiscoveryStage.NARROWING)
    )
    assert bars.looking_up.value() == PERCENT
    assert not bars.checking_series.started
    assert bars.checking_series.wanted == "Checking series"
