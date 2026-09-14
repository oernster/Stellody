"""A value typed in the tag editor for one track of a cue album reaches that track.

A cue album is one audio file cut into slices, so every track of it shares a
path and only the address tells them apart. Resolution looks a pin up by
address (`applied`, the function a load lays pins on with), so a pin the tag
editor records has to be written against the address as well. A whole file
addresses as its bare path, so its pins, including any already stored by path,
are found exactly as before.
"""

from __future__ import annotations

from stellody.application.editing import TagEditing
from stellody.domain.overrides import Override, OverrideField, applied, index
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource

ALBUM = "c0ffee"
ONE_FILE = "H:/Music/Portishead/Dummy.flac"
WHOLE_FILE = "H:/Music/Portishead/Glory Box.flac"
SLICES = 3
PICKED = 1
STATED_NUMBER = 9
STATED_TITLE = "Sour Times"


def a_track(source: TrackSource, number: int) -> Track:
    """One track, numbered and titled after its place."""
    return Track(
        source=source,
        disc_number=1,
        track_number=number,
        title=f"Track {number}",
        artists=("Portishead",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


def cue_album() -> tuple[Track, ...]:
    """Three tracks cut out of one file, a second of it each."""
    return tuple(
        a_track(
            TrackSource(
                path=ONE_FILE,
                start_frame=place * CD_SAMPLE_RATE,
                end_frame=(place + 1) * CD_SAMPLE_RATE,
            ),
            place + 1,
        )
        for place in range(SLICES)
    )


def stated(tracks: tuple[Track, ...], chosen: Track, field, value: str):
    """The tracks as a load would lay them after the editor states one value."""
    edits = TagEditing.edits_for(ALBUM, (chosen,), {field: value})
    return applied(tracks, ALBUM, index(edits))


def test_a_number_stated_for_one_slice_reaches_that_slice() -> None:
    tracks = cue_album()
    laid = stated(
        tracks, tracks[PICKED], OverrideField.TRACK_NUMBER, str(STATED_NUMBER)
    )
    assert laid[PICKED].track_number == STATED_NUMBER


def test_it_reaches_no_other_slice_of_the_same_file() -> None:
    tracks = cue_album()
    laid = stated(tracks, tracks[PICKED], OverrideField.TITLE, STATED_TITLE)
    others = [place for place in range(SLICES) if place != PICKED]
    assert [laid[place] for place in others] == [tracks[place] for place in others]
    assert laid[PICKED].title == STATED_TITLE


def test_a_whole_file_still_takes_what_is_stated_for_it() -> None:
    whole = (a_track(TrackSource(path=WHOLE_FILE), 1),)
    laid = stated(whole, whole[0], OverrideField.TITLE, STATED_TITLE)
    assert laid[0].title == STATED_TITLE


def test_a_pin_already_stored_by_path_still_reaches_a_whole_file() -> None:
    """Pins written before any change hold a bare path; a whole file matches it."""
    whole = (a_track(TrackSource(path=WHOLE_FILE), 1),)
    kept = (Override(ALBUM, OverrideField.TITLE, STATED_TITLE, WHOLE_FILE),)
    assert applied(whole, ALBUM, index(kept))[0].title == STATED_TITLE
