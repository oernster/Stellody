"""Accepted corrections: what may be accepted, what a pin means, what it covers.

Pure rules over pure values, so nothing here needs a store, a file or a clock.
"""

from __future__ import annotations

import pytest

from stellody.domain.health import IssueKind
from stellody.domain.overrides import (
    ALBUM_WIDE,
    FIELD_FOR_KIND,
    TRACK_FIELDS,
    Override,
    OverrideField,
    applied,
    can_be_accepted,
    covers,
    index,
    value_for,
)
from stellody.domain.track import Track, TrackSource

ALBUM = "8c3e247fcb8d4876"
OTHER_ALBUM = "d9b15e736eb46daf"
FIRST = "C:/music/Album/01 One.flac"
SECOND = "C:/music/Album/02 Two.flac"


class TestWhatMayBeAccepted:
    """Only a finding that proposes a value can be accepted."""

    @pytest.mark.parametrize("kind", sorted(FIELD_FOR_KIND))
    def test_a_kind_with_a_rule_proposes_a_value(self, kind: IssueKind) -> None:
        assert can_be_accepted(kind)

    @pytest.mark.parametrize(
        "kind",
        [
            IssueKind.NO_ARTWORK,
            IssueKind.UNREADABLE_FILE,
            IssueKind.UNPLAYABLE_FORMAT,
        ],
    )
    def test_a_kind_with_nothing_to_propose_cannot_be_accepted(
        self, kind: IssueKind
    ) -> None:
        """There is no artwork to accept where none was found."""
        assert not can_be_accepted(kind)

    def test_every_kind_is_decided_one_way_or_the_other(self) -> None:
        """No kind is left without an answer, which a new one would be."""
        for kind in IssueKind:
            assert can_be_accepted(kind) == (kind in FIELD_FOR_KIND)


class TestAnOverrideIsCheckedAsItIsBuilt:
    def test_a_track_field_pins_one_file(self) -> None:
        pinned = Override(ALBUM, OverrideField.TRACK_NUMBER, "3", FIRST)
        assert pinned.path == FIRST
        assert pinned.value == "3"

    def test_an_album_wide_field_names_no_file(self) -> None:
        pinned = Override(ALBUM, OverrideField.ALBUM_ARTIST, "Portishead")
        assert pinned.path == ALBUM_WIDE

    def test_an_override_needs_an_album(self) -> None:
        with pytest.raises(ValueError, match="album"):
            Override("", OverrideField.ALBUM_ARTIST, "Portishead")

    def test_an_override_with_no_value_pins_nothing(self) -> None:
        with pytest.raises(ValueError, match="pins nothing"):
            Override(ALBUM, OverrideField.ALBUM_ARTIST, "")

    @pytest.mark.parametrize("field", sorted(TRACK_FIELDS))
    def test_a_track_field_without_a_file_is_refused(
        self, field: OverrideField
    ) -> None:
        """Pinning a title without saying whose title is not a correction."""
        with pytest.raises(ValueError, match="one file"):
            Override(ALBUM, field, "something")

    def test_an_album_wide_field_with_a_file_is_refused(self) -> None:
        """An album artist is not a property of one of its files."""
        with pytest.raises(ValueError, match="album wide"):
            Override(ALBUM, OverrideField.ALBUM_ARTIST, "Portishead", FIRST)


class TestIndexing:
    def test_a_pin_is_found_by_album_field_and_file(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.TITLE, "One", FIRST),))
        assert value_for(accepted, ALBUM, OverrideField.TITLE, FIRST) == "One"

    def test_an_album_wide_pin_is_found_without_a_file(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.ALBUM_ARTIST, "Portishead"),))
        assert value_for(accepted, ALBUM, OverrideField.ALBUM_ARTIST) == "Portishead"

    def test_nothing_accepted_reads_as_nothing(self) -> None:
        assert value_for(index(()), ALBUM, OverrideField.TITLE, FIRST) is None

    def test_another_album_is_not_this_one(self) -> None:
        accepted = index((Override(OTHER_ALBUM, OverrideField.TITLE, "One", FIRST),))
        assert value_for(accepted, ALBUM, OverrideField.TITLE, FIRST) is None

    def test_the_later_pin_wins(self) -> None:
        """Two pins for one field cannot resolve by which was read first."""
        accepted = index(
            (
                Override(ALBUM, OverrideField.TITLE, "Early", FIRST),
                Override(ALBUM, OverrideField.TITLE, "Late", FIRST),
            )
        )
        assert value_for(accepted, ALBUM, OverrideField.TITLE, FIRST) == "Late"


class TestWhatSilencesAFinding:
    def test_a_finding_is_covered_once_every_file_it_names_is_pinned(self) -> None:
        accepted = index(
            (
                Override(ALBUM, OverrideField.TRACK_NUMBER, "1", FIRST),
                Override(ALBUM, OverrideField.TRACK_NUMBER, "2", SECOND),
            )
        )
        assert covers(accepted, ALBUM, OverrideField.TRACK_NUMBER, (FIRST, SECOND))

    def test_half_an_accepted_finding_is_still_a_finding(self) -> None:
        """Dropping it would hide the half nobody answered."""
        accepted = index((Override(ALBUM, OverrideField.TRACK_NUMBER, "1", FIRST),))
        assert not covers(accepted, ALBUM, OverrideField.TRACK_NUMBER, (FIRST, SECOND))

    def test_a_finding_naming_no_file_is_covered_by_one_pin(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.ALBUM_ARTIST, "Portishead"),))
        assert covers(accepted, ALBUM, OverrideField.ALBUM_ARTIST, ())

    def test_a_finding_naming_no_file_with_nothing_pinned_is_not_covered(self) -> None:
        assert not covers(index(()), ALBUM, OverrideField.ALBUM_ARTIST, ())


def _track(
    path: str, disc: int = 1, number: int = 1, title: str = "As Ripped"
) -> Track:
    """One resolved track, as the rules would have produced it."""
    return Track(
        source=TrackSource(path),
        disc_number=disc,
        track_number=number,
        title=title,
        artists=("Someone",),
        duration_ms=1000,
        sample_rate=44100,
        bit_depth=16,
    )


class TestTheThirdLayer:
    """Pins laid over the tracks the automatic rules produced."""

    def test_nothing_accepted_leaves_every_track_alone(self) -> None:
        tracks = (_track(FIRST),)
        assert applied(tracks, ALBUM, index(())) is tracks

    def test_a_track_nothing_pins_is_left_alone(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.TITLE, "Pinned", SECOND),))
        laid = applied((_track(FIRST),), ALBUM, accepted)
        assert laid[0].title == "As Ripped"

    def test_a_pinned_title_is_preferred_to_the_rule(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.TITLE, "Mine", FIRST),))
        laid = applied((_track(FIRST),), ALBUM, accepted)
        assert laid[0].title == "Mine"

    def test_a_pinned_track_number_is_preferred_to_the_rule(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.TRACK_NUMBER, "7", FIRST),))
        laid = applied((_track(FIRST, number=3),), ALBUM, accepted)
        assert laid[0].track_number == 7

    def test_a_pinned_disc_number_is_preferred_to_the_rule(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.DISC_NUMBER, "2", FIRST),))
        laid = applied((_track(FIRST, disc=1),), ALBUM, accepted)
        assert laid[0].disc_number == 2

    def test_the_untouched_fields_survive_a_pin(self) -> None:
        accepted = index((Override(ALBUM, OverrideField.TITLE, "Mine", FIRST),))
        laid = applied((_track(FIRST, disc=2, number=5),), ALBUM, accepted)
        assert (laid[0].disc_number, laid[0].track_number) == (2, 5)

    def test_a_pin_for_another_album_reaches_nothing(self) -> None:
        accepted = index((Override(OTHER_ALBUM, OverrideField.TITLE, "Mine", FIRST),))
        laid = applied((_track(FIRST),), ALBUM, accepted)
        assert laid[0].title == "As Ripped"

    def test_a_pin_that_is_not_a_number_is_ignored_rather_than_raised(self) -> None:
        """A hand-edited store must not cost the whole library its assembly."""
        accepted = index((Override(ALBUM, OverrideField.TRACK_NUMBER, "abc", FIRST),))
        laid = applied((_track(FIRST, number=4),), ALBUM, accepted)
        assert laid[0].track_number == 4

    def test_a_pin_no_track_could_hold_is_dropped(self) -> None:
        """Track numbers start at 1, so nought is a value no track can take."""
        accepted = index((Override(ALBUM, OverrideField.TRACK_NUMBER, "0", FIRST),))
        laid = applied((_track(FIRST, number=4),), ALBUM, accepted)
        assert laid[0].track_number == 4

    def test_accepting_what_the_rule_produced_moves_nothing(self) -> None:
        """Which is what accepting a proposal records, so the library holds still."""
        track = _track(FIRST, disc=1, number=3, title="As Ripped")
        accepted = index(
            (
                Override(ALBUM, OverrideField.TRACK_NUMBER, "3", FIRST),
                Override(ALBUM, OverrideField.TITLE, "As Ripped", FIRST),
            )
        )
        assert applied((track,), ALBUM, accepted) == (track,)
