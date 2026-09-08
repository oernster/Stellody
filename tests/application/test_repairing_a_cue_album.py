"""A cue album: one audio file cut into tracks, each accepted on its own.

The reported defect, kept in its own file because it is a corner of the service
rather than the shape of it; also because the file it came out of had reached
the length a module here is allowed.

Matched by name nothing matched, since the label a cue track is reported under
is one the scan made up. Pinned by path one pin would have reached every track
in the file. Addressing the slice settles both.
"""

from __future__ import annotations

from repairs_support import FOLDER, IDENTITY, RATE, RecordingStore, issue

from stellody.application.repairs import Repairs
from stellody.application.scan import LibraryView
from stellody.domain.album import Album
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.track import Track, TrackSource


class TestACueAlbumWhereEveryTrackIsOneFile:
    """Accepting a finding about slices of one file records one pin each."""

    def _album(self) -> LibraryView:
        """Three tracks cut out of one file, as a cue sheet describes them."""
        one = f"{FOLDER}/Dummy.flac"
        return LibraryView(
            albums=(
                Album(
                    identity=IDENTITY,
                    tracks=tuple(
                        Track(
                            source=TrackSource(
                                path=one,
                                start_frame=start,
                                end_frame=start + RATE,
                            ),
                            disc_number=1,
                            track_number=number,
                            title=f"Track {number}",
                            artists=("Portishead",),
                            duration_ms=1000,
                            sample_rate=RATE,
                            bit_depth=16,
                        )
                        for number, start in enumerate((0, RATE, RATE * 2), start=1)
                    ),
                ),
            )
        )

    def _finding(self) -> LibraryIssue:
        """A duplicate-number finding naming two slices of that one file."""
        one = f"{FOLDER}/Dummy.flac"
        return issue(
            IssueKind.DUPLICATE_TRACK_NUMBER,
            ("01. Track 1", "02. Track 2"),
            addresses=(f"{one}#0", f"{one}#{RATE}"),
        )

    def test_accepting_records_something_rather_than_nothing(self) -> None:
        store = RecordingStore()
        assert Repairs(store).accept(self._album(), (self._finding(),)) == 2

    def test_each_slice_is_pinned_apart_from_the_others(self) -> None:
        """One pin a track, so no pin can reach a track it is not about."""
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(self._album(), (self._finding(),))
        assert {pin.path for pin in pins} == {
            f"{FOLDER}/Dummy.flac#0",
            f"{FOLDER}/Dummy.flac#{RATE}",
        }
        assert {pin.value for pin in pins} == {"1", "2"}

    def test_the_slice_nobody_named_is_left_alone(self) -> None:
        """The third track is not in the finding, so nothing is written for it."""
        repairs = Repairs(RecordingStore())
        pins = repairs.pins_for(self._album(), (self._finding(),))
        assert f"{FOLDER}/Dummy.flac#{RATE * 2}" not in {pin.path for pin in pins}
