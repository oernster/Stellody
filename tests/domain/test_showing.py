"""FR-D86: the results filter's "Show:" row, as a pure rule."""

from __future__ import annotations

from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.domain.showing import EVERYTHING, Showing, shown

MIX = ReleaseGroup(title="Involver", kinds=(ReleaseKind.DJ_MIX,))
ALBUM = ReleaseGroup(title="Airdrawndagger")
LIKE = SimilarArtist(name="Digweed", identifier="jd")
SASHA = Gaps(artist="Sasha", albums=(MIX, ALBUM), artists=(LIKE,))
ADAPT = Gaps(
    artist="Global Underground: Adapt",
    albums=(ReleaseGroup(title="Adapt #3", kinds=(ReleaseKind.DJ_MIX,)),),
    series=True,
)
ANSWER = (SASHA, ADAPT)


def titles(gaps: tuple[Gaps, ...]) -> dict[str, tuple[str, ...]]:
    """Each heading with what is under it, albums then artists."""
    return {
        gap.artist: tuple(a.title for a in gap.albums)
        + tuple(a.name for a in gap.artists)
        for gap in gaps
    }


def test_every_box_ticked_shows_the_answer_untouched() -> None:
    assert shown(ANSWER, EVERYTHING) == ANSWER


def test_series_left_out_hides_the_whole_heading() -> None:
    assert titles(shown(ANSWER, Showing(series=False))) == {
        "Sasha": ("Involver", "Airdrawndagger", "Digweed")
    }


def test_mixes_and_albums_answer_to_their_own_boxes() -> None:
    """Under an artist a mix is a mix; a series keeps its mixes regardless."""
    assert titles(shown(ANSWER, Showing(mixes=False))) == {
        "Sasha": ("Airdrawndagger", "Digweed"),
        "Global Underground: Adapt": ("Adapt #3",),
    }
    assert titles(shown(ANSWER, Showing(albums=False, artists=False))) == {
        "Sasha": ("Involver",),
        "Global Underground: Adapt": ("Adapt #3",),
    }


def test_a_heading_left_empty_is_not_shown() -> None:
    """FR-D75: nothing under a heading is nothing to act on."""
    only_series = Showing(albums=False, mixes=False, artists=False)
    assert titles(shown(ANSWER, only_series)) == {
        "Global Underground: Adapt": ("Adapt #3",)
    }
