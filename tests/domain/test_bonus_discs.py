"""A bonus disc is a disc, even where its folder names no number.

"Ether Song (Bonus Disc)" sitting beside "Ether Song" is one album in two
folders. It used to be two albums with the same name and artist, one above the
other in the library, because the folder marker the grouping recognised
required a digit and this one has none.

Measured against the reference library: three pairs fold this way and nothing
else moves. The folders naming an EDITION rather than a disc, "[Bonus Track]",
"(Bonus Track Version)", "[Bonus DVD]", "[UK Bonus Edition]", stay their own
albums, which is why the word CD, Disc or Disk is still required.
"""

from __future__ import annotations

import pytest

from stellody.domain.grouping import (
    SourceEntry,
    assemble_albums,
    folder_base_and_disc,
    is_unnumbered_bonus,
)
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource

RATE = 44100
PARENT = "H:/FLACMusic/Turin Brakes"


def entry(folder_name: str, file_name: str, **overrides: object) -> SourceEntry:
    """One source entry under the Turin Brakes folder."""
    candidate = TrackCandidate(
        file_name=file_name,
        source=TrackSource(path=f"{PARENT}/{folder_name}/{file_name}"),
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
        tag_disc=overrides.pop("tag_disc", None),  # type: ignore[arg-type]
        tag_track=overrides.pop("tag_track", None),  # type: ignore[arg-type]
        tag_title=overrides.pop("tag_title", file_name),  # type: ignore[arg-type]
        artists=("Turin Brakes",),
    )
    fields: dict[str, object] = {
        "folder_name": folder_name,
        "parent_path": PARENT,
        "parent_name": "Turin Brakes",
        "candidate": candidate,
        "album": "Ether Song",
        "album_artist": "Turin Brakes",
    }
    fields.update(overrides)
    return SourceEntry(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Ether Song (Bonus Disc)", ("Ether Song", None)),
        ("Come Away With Me (Bonus CD)", ("Come Away With Me", None)),
        ("The Ecleftic - Bonus Disc", ("The Ecleftic", None)),
        ("Album [Extra CD]", ("Album", None)),
        ("Ether Song (Bonus Disc 2)", ("Ether Song", 2)),
        # An edition, not a disc: these keep their own album.
        ("Angel Dust [Bonus Track]", ("Angel Dust [Bonus Track]", None)),
        ("X&Y [Bonus DVD]", ("X&Y [Bonus DVD]", None)),
        (
            "In Our Nature (Bonus Track Version)",
            ("In Our Nature (Bonus Track Version)", None),
        ),
        # The word Disc alone says nothing, so nothing is inferred from it.
        ("Compact Disc", ("Compact Disc", None)),
        ("Bonus Disc", ("Bonus Disc", None)),
    ],
)
def test_a_bonus_marker_is_split_off_only_when_it_names_a_disc(
    name: str, expected: tuple[str, int | None]
) -> None:
    assert folder_base_and_disc(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Ether Song (Bonus Disc)", True),
        ("Ether Song (Bonus Disc 2)", False),
        ("White Album (Disc 2)", False),
        ("Angel Dust [Bonus Track]", False),
        ("Ether Song", False),
    ],
)
def test_only_a_bonus_folder_with_no_number_leaves_the_disc_open(
    name: str, expected: bool
) -> None:
    """A numbered one is an ordinary disc folder and the number is believed."""
    assert is_unnumbered_bonus(name) is expected


class TestFoldingTheFolderIn:
    def test_a_bonus_folder_joins_the_album_beside_it(self) -> None:
        albums, _ = assemble_albums(
            (
                entry("Ether Song", "01. Blue Hour.flac", tag_track=1),
                entry("Ether Song", "02. Average Man.flac", tag_track=2),
                entry(
                    "Ether Song (Bonus Disc)",
                    "01. 5 Mile.flac",
                    tag_track=1,
                    tag_disc=2,
                ),
            )
        )
        assert len(albums) == 1, "one album, not two of the same name"
        album = albums[0]
        assert album.identity.title == "Ether Song"
        assert album.disc_count == 2
        assert album.track_count == 3

    def test_the_tags_say_which_disc_when_the_folder_does_not(self) -> None:
        albums, _ = assemble_albums(
            (
                entry("Ether Song", "01. Blue Hour.flac", tag_track=1),
                entry(
                    "Ether Song (Bonus Disc)",
                    "01. 5 Mile.flac",
                    tag_track=1,
                    tag_disc=3,
                ),
            )
        )
        assert [disc.number for disc in albums[0].discs] == [1, 3]

    def test_a_bonus_disc_the_tags_are_silent_about_goes_after_the_rest(
        self,
    ) -> None:
        """Both would otherwise be track one of disc one, which collides."""
        albums, issues = assemble_albums(
            (
                entry("Ether Song", "01. Blue Hour.flac", tag_track=1),
                entry("Ether Song", "02. Average Man.flac", tag_track=2),
                entry("Ether Song (Bonus Disc)", "01. 5 Mile.flac", tag_track=1),
                entry("Ether Song (Bonus Disc)", "02. The Boss.flac", tag_track=2),
            )
        )
        assert [disc.number for disc in albums[0].discs] == [1, 2]
        assert [len(disc.tracks) for disc in albums[0].discs] == [2, 2]
        assert issues == (), "no duplicate track numbers were reported"

    def test_it_goes_after_every_disc_the_album_already_holds(self) -> None:
        albums, _ = assemble_albums(
            (
                entry("Ether Song CD1", "01. One.flac", tag_track=1),
                entry("Ether Song CD2", "01. Two.flac", tag_track=1),
                entry("Ether Song CD3", "01. Three.flac", tag_track=1),
                entry("Ether Song (Bonus Disc)", "01. Four.flac", tag_track=1),
            )
        )
        assert [disc.number for disc in albums[0].discs] == [1, 2, 3, 4]

    def test_a_bonus_edition_folder_is_not_read_as_a_second_disc(self) -> None:
        """It names a different pressing, so its tracks do not become disc 2.

        The two folders do end up in one album, because both are tagged Ether
        Song and folders naming one album are folded together. What this holds
        is the narrower point the bonus-disc rule is about: a folder saying
        "[Bonus Track]" rather than "(Bonus Disc)" is not a disc of its own,
        so nothing here invents one.
        """
        albums, _ = assemble_albums(
            (
                entry("Ether Song", "01. Blue Hour.flac", tag_track=1),
                entry(
                    "Ether Song [Bonus Track]",
                    "01. Blue Hour.flac",
                    tag_track=1,
                ),
            )
        )
        assert len(albums) == 1
        assert [disc.number for disc in albums[0].discs] == [1]

    def test_a_bonus_folder_standing_alone_is_still_one_album(self) -> None:
        """Nothing to join, so it keeps its tracks and loses only the marker."""
        albums, _ = assemble_albums(
            (
                entry("Ether Song (Bonus Disc)", "01. 5 Mile.flac", tag_track=1),
                entry("Ether Song (Bonus Disc)", "02. The Boss.flac", tag_track=2),
            )
        )
        assert len(albums) == 1
        assert albums[0].track_count == 2
