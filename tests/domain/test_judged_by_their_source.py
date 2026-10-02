"""FR-D78: a candidate with no recognised genre judged by who it was suggested for.

Ruled by Oliver on 2026-10-01. Of 1,996 similar artists in his whole-library
answer, 615 had no genre at all on MusicBrainz, so a genre filter withheld every
one of them. Such a candidate now takes the genres the library holds for the
heading it sits under; only where that heading's albums name no catalogue genre
either is it withheld and counted.
"""

from __future__ import annotations

from factories import make_track

from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.discovery_filter import filtered_answer
from stellody.domain.identity import AlbumIdentity

HOUSE = ("House",)
VARIOUS = "Various Artists"
# MusicBrainz gave this candidate no genre at all, so the cache holds nothing.
UNTAGGED = SimilarArtist(name="Nobody Knows", identifier="unremembered")
NOTHING_REMEMBERED: dict[str, tuple[str, ...]] = {}


def held(
    artist: str, genre: str, title: str = "", credits: tuple[str, ...] = ()
) -> Album:
    """An album in the library, under this artist, in this genre."""
    track = make_track(artists=credits) if credits else make_track()
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=title or f"{artist} LP"),
        tracks=(track,),
        genre=genre,
    )


def test_an_untagged_candidate_shows_under_a_house_source() -> None:
    """Suggested for a house artist, so a House filter keeps them."""
    library = (held("Tinlicker", "House"),)
    answer = (Gaps(artist="Tinlicker", artists=(UNTAGGED,)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == answer
    assert shown.unjudged == 0


def test_an_untagged_candidate_under_a_rock_source_is_filtered_out() -> None:
    """Judged; judged not House: dropped like any judged candidate rather
    than counted as one the filter could not judge."""
    library = (held("AC/DC", "Rock"),)
    answer = (Gaps(artist="AC/DC", artists=(UNTAGGED,)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == ()
    assert shown.unjudged == 0


def test_judged_per_heading_where_one_candidate_sits_under_two() -> None:
    """Each heading judges the candidate on its own albums."""
    library = (held("Tinlicker", "House"), held("AC/DC", "Rock"))
    answer = (
        Gaps(artist="Tinlicker", artists=(UNTAGGED,)),
        Gaps(artist="AC/DC", artists=(UNTAGGED,)),
    )
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == (answer[0],)
    assert shown.unjudged == 0


def test_counted_unjudged_where_the_source_names_no_genre_either() -> None:
    """The source's albums state nothing the catalogue recognises."""
    library = (held("Tinlicker", "Skiffle"), held("Quiet One", ""))
    answer = (
        Gaps(artist="Tinlicker", artists=(UNTAGGED,)),
        Gaps(artist="Quiet One", artists=(UNTAGGED,)),
    )
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == ()
    assert shown.unjudged == 1


def test_a_series_heading_is_judged_by_the_volumes_held() -> None:
    """A series heading names a series stem, so its held volumes judge."""
    library = (
        held(VARIOUS, "House", title="Global Underground #7 / Unmixed"),
        held(VARIOUS, "Rock", title="Rock Anthems Volume 2"),
    )
    answer = (
        Gaps(artist="Global Underground", artists=(UNTAGGED,), series=True),
        Gaps(artist="Rock Anthems", artists=(UNTAGGED,), series=True),
    )
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == (answer[0],)
    assert shown.unjudged == 0


def test_an_album_titled_only_a_number_judges_for_its_artist_alone() -> None:
    """A title of `1999` names no series, so it counts for its artist alone."""
    library = (held("Tinlicker", "House", title="1999"),)
    answer = (Gaps(artist="Tinlicker", artists=(UNTAGGED,)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == answer


def test_a_track_credit_on_a_compilation_judges_too() -> None:
    """An artist reached through a compilation credit holds that album's
    genres, just as the run reached them through it."""
    library = (held(VARIOUS, "House", credits=("Lane 8",)),)
    answer = (Gaps(artist="Lane 8", artists=(UNTAGGED,)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == answer
    assert shown.unjudged == 0


def test_a_heading_split_from_a_joint_credit_judges_by_that_credit() -> None:
    """Reported by Oliver on 2026-10-02: 115 held back under 43 headings, every
    one an artist held only inside a joint credit. The run asks about each
    part of `Moat, Kyozo, & DJ Tennis`, so the filter credits each part too."""
    library = (held("Moat, Kyozo, & DJ Tennis", "House"),)
    answer = (Gaps(artist="DJ Tennis", artists=(UNTAGGED,)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == answer
    assert shown.unjudged == 0


def test_a_heading_split_from_a_joint_credit_keeps_its_albums() -> None:
    """The same split decides who the run asked about, so a heading reached
    through a joint credit is a source artist and keeps its albums."""
    library = (held("CamelPhat & ARTBAT", "House"),)
    answer = (Gaps(artist="ARTBAT", albums=(ReleaseGroup(title="Horizon"),)),)
    shown = filtered_answer(answer, library, NOTHING_REMEMBERED, HOUSE)
    assert shown.gaps == answer


def test_a_recognised_genre_of_its_own_still_judges_first() -> None:
    """The heading is asked only where MusicBrainz gave nothing recognised."""
    library = (held("Tinlicker", "House"),)
    rock = SimilarArtist(name="Airbourne", identifier="a-rock-act")
    answer = (Gaps(artist="Tinlicker", artists=(rock,)),)
    shown = filtered_answer(answer, library, {"a-rock-act": ("rock",)}, HOUSE)
    assert shown.gaps == ()
