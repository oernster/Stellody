"""Cue-sheet parsing, the path a third of the reference library takes."""

from __future__ import annotations

import pytest

from stellody.domain.cue import CueParseError, parse_cue, timestamp_to_frames

CD_RATE = 44100

SHEET = """REM GENRE Progressive House
REM DATE 2004
PERFORMER "Sasha"
TITLE "Involver"
FILE "Involver.flac" WAVE
  TRACK 01 AUDIO
    TITLE "Wavy Gravy"
    PERFORMER "Sasha; Kicks Like a Mule"
    INDEX 00 00:00:00
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Cutting Room"
    INDEX 01 00:02:00
  TRACK 03 AUDIO
    TITLE "Baby Wants to Ride"
    INDEX 01 00:04:00
"""


@pytest.mark.parametrize(
    ("stamp", "rate", "expected"),
    [
        ("00:00:00", CD_RATE, 0),
        ("00:01:00", CD_RATE, 44100),
        ("01:00:00", CD_RATE, 2646000),
        ("00:00:75", CD_RATE, 44100),
        ("00:01:00", 96000, 96000),
    ],
)
def test_timestamps_convert_to_sample_frames(
    stamp: str, rate: int, expected: int
) -> None:
    assert timestamp_to_frames(stamp, rate) == expected


@pytest.mark.parametrize("stamp", ["00:00", "aa:bb:cc", "-1:00:00"])
def test_malformed_timestamps_are_refused(stamp: str) -> None:
    with pytest.raises(CueParseError):
        timestamp_to_frames(stamp, CD_RATE)


def test_a_sample_rate_is_required() -> None:
    with pytest.raises(CueParseError, match="sample rate"):
        parse_cue(SHEET, 0)


def test_a_full_sheet_becomes_ordered_slices() -> None:
    sheet = parse_cue(SHEET, CD_RATE)
    assert sheet.album_title == "Involver"
    assert sheet.album_performer == "Sasha"
    assert sheet.date == "2004"
    assert sheet.genre == "Progressive House"
    assert sheet.file_names == ("Involver.flac",)
    assert [track.number for track in sheet.tracks] == [1, 2, 3]
    assert sheet.tracks[0].start_frame == 0
    # 00:02:00 is two seconds; the third field counts CD frames, not seconds.
    assert sheet.tracks[0].end_frame == 2 * CD_RATE
    assert sheet.tracks[1].end_frame == 4 * CD_RATE
    assert sheet.tracks[2].end_frame is None


def test_track_performers_are_split_and_album_performer_is_kept() -> None:
    sheet = parse_cue(SHEET, CD_RATE)
    assert sheet.tracks[0].performers == ("Sasha", "Kicks Like a Mule")
    assert sheet.tracks[1].performers == ()


def test_the_pregap_index_is_ignored_in_favour_of_index_one() -> None:
    sheet = parse_cue(
        'FILE "a.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 00 00:00:00\n"
        "    INDEX 01 00:00:30\n",
        CD_RATE,
    )
    # 30 CD frames of 1/75 second each.
    assert sheet.tracks[0].start_frame == 30 * CD_RATE // 75


def test_tracks_in_separate_files_do_not_bound_each_other() -> None:
    sheet = parse_cue(
        'FILE "one.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "two.flac" WAVE\n'
        "  TRACK 02 AUDIO\n"
        "    INDEX 01 00:00:00\n",
        CD_RATE,
    )
    assert sheet.file_names == ("one.flac", "two.flac")
    assert sheet.tracks[0].end_frame is None


def test_a_track_without_an_index_is_dropped() -> None:
    sheet = parse_cue(
        'FILE "a.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        "  TRACK 02 AUDIO\n",
        CD_RATE,
    )
    assert [track.number for track in sheet.tracks] == [1]


def test_a_track_without_a_title_falls_back_to_the_album_name() -> None:
    sheet = parse_cue(
        'TITLE "Involver"\nFILE "a.flac" WAVE\n'
        "  TRACK 04 AUDIO\n    INDEX 01 00:00:00\n",
        CD_RATE,
    )
    assert sheet.tracks[0].title == "Involver 4"


def test_a_titleless_sheet_falls_back_to_the_word_track() -> None:
    sheet = parse_cue(
        'FILE "a.flac" WAVE\n  TRACK 02 AUDIO\n    INDEX 01 00:00:00\n', CD_RATE
    )
    assert sheet.tracks[0].title == "Track 2"


@pytest.mark.parametrize(
    ("file_line", "expected"),
    [
        ('FILE "quoted name.flac" WAVE', "quoted name.flac"),
        ("FILE bare.flac WAVE", "bare.flac"),
        ("FILE bare.flac", "bare.flac"),
        ('FILE "unterminated.flac WAVE', '"unterminated.flac WAVE'),
    ],
)
def test_file_names_are_read_in_every_written_form(
    file_line: str, expected: str
) -> None:
    sheet = parse_cue(
        f"{file_line}\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n", CD_RATE
    )
    assert sheet.tracks[0].file_name == expected


@pytest.mark.parametrize("line", ["  TRACK AUDIO", "  TRACK", "  TRACK ZZ AUDIO"])
def test_a_malformed_track_line_is_refused(line: str) -> None:
    with pytest.raises(CueParseError, match="TRACK"):
        parse_cue(f'FILE "a.flac" WAVE\n{line}\n', CD_RATE)


def test_unknown_lines_blank_lines_and_stray_indexes_are_tolerated() -> None:
    sheet = parse_cue(
        "\n"
        "REM COMMENT something\n"
        "INDEX 01 00:00:00\n"
        'FILE "a.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    FLAGS DCP\n"
        "    INDEX\n"
        "    INDEX AA 00:00:00\n"
        "    INDEX 01 00:00:10\n",
        CD_RATE,
    )
    assert len(sheet.tracks) == 1
    assert sheet.tracks[0].start_frame == 10 * CD_RATE // 75
    assert sheet.date == ""
    assert sheet.genre == ""


UNIDENTIFIED = """PERFORMER "Unknown Artist"
TITLE "Unknown Title"
FILE "Whole Disc.flac" WAVE
  TRACK 01 AUDIO
    TITLE "Track 01"
    PERFORMER "Unknown Artist"
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    TITLE "Track 02"
    INDEX 01 00:02:00
"""


def test_an_unidentified_sheet_names_neither_album_nor_artist() -> None:
    """A ripper's stand-in must not overrule the tags in the file itself.

    A disc absent from the ripper's database is written out with these words
    in place of names. Reading them as names meant a tagged album reporting
    as unknown, since the file's own tags answer only where the sheet is
    silent and a stand-in is not silence.
    """
    sheet = parse_cue(UNIDENTIFIED, CD_RATE)
    assert sheet.album_title == ""
    assert sheet.album_performer == ""
    assert sheet.tracks[0].performers == ()


def test_a_track_named_only_by_its_number_is_no_title() -> None:
    """It states nothing the number has not already said."""
    sheet = parse_cue(UNIDENTIFIED, CD_RATE)
    assert [track.title for track in sheet.tracks] == ["Track 1", "Track 2"]


@pytest.mark.parametrize(
    "written", ["unknown artist", "UNKNOWN ARTIST", "Unknown Artist"]
)
def test_the_stand_in_is_recognised_however_it_is_cased(written: str) -> None:
    sheet = parse_cue(
        f'PERFORMER "{written}"\nFILE "a.flac" WAVE\n'
        "  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n",
        CD_RATE,
    )
    assert sheet.album_performer == ""


def test_a_real_name_holding_the_word_unknown_is_kept() -> None:
    """The match is the whole name, never a word inside one.

    Unknown Pleasures is an album and Unknown Mortal Orchestra is a band.
    Reading either as a stand-in would lose a name that was really there,
    which is the fault this exists to prevent, running the other way.
    """
    sheet = parse_cue(
        'PERFORMER "Unknown Mortal Orchestra"\nTITLE "Unknown Pleasures"\n'
        'FILE "a.flac" WAVE\n  TRACK 01 AUDIO\n    TITLE "Tracking Shot"\n'
        "    INDEX 01 00:00:00\n",
        CD_RATE,
    )
    assert sheet.album_performer == "Unknown Mortal Orchestra"
    assert sheet.album_title == "Unknown Pleasures"
    assert sheet.tracks[0].title == "Tracking Shot"


TWO_DISC = """REM DATE 2013
REM DISCNUMBER 2
REM TOTALDISCS 2
PERFORMER "Sasha"
TITLE "Invol<3r"
FILE "Sasha - Invol_3r.flac" WAVE
  TRACK 01 AUDIO
    TITLE "Growing Forehead (Sasha Beatless mix)"
    INDEX 01 00:00:00
"""


def test_a_sheet_states_which_disc_of_the_set_it_is() -> None:
    """A set spanning folders says so; throwing it away invents damage.

    Two folders of one release both number their tracks from one. Reading the
    disc each states keeps them apart; discarding it made every track of the
    second collide with the first, which was then reported as duplicate track
    numbers on an album whose tags were perfectly correct. Those findings could
    never be accepted, because there was nothing wrong to accept.
    """
    assert parse_cue(TWO_DISC, CD_RATE).disc == 2


def test_a_sheet_that_states_no_disc_says_nothing() -> None:
    """Silence leaves the file's own tag to answer."""
    assert parse_cue(SHEET, CD_RATE).disc is None


@pytest.mark.parametrize("written", ["", "one", "0", "-1", "2.5", "  "])
def test_a_disc_that_is_not_a_counting_number_is_no_disc(written: str) -> None:
    """A wrong number files the music elsewhere in silence, so it is refused."""
    sheet = parse_cue(
        f"REM DISCNUMBER {written}\n"
        'PERFORMER "A"\nTITLE "B"\nFILE "a.flac" WAVE\n'
        "  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n",
        CD_RATE,
    )
    assert sheet.disc is None


def test_the_stated_disc_survives_a_sheet_with_everything_else_on_it() -> None:
    """Read alongside the other REM values rather than instead of them."""
    sheet = parse_cue(TWO_DISC, CD_RATE)
    assert (sheet.disc, sheet.date, sheet.album_title) == (2, "2013", "Invol<3r")
