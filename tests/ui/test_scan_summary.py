"""What the dialog says a scan found, asserted without a screen.

The report is built as text apart from the dialog so this suite can ask what it
says rather than what it looks like. The cases worth holding are the ones where
a wrong answer would mislead rather than merely read badly: a rescan that found
nothing must not imply a discovery; albums that went away must be visible
rather than quietly dropped.
"""

from __future__ import annotations

from stellody.application.scan import ScanReport
from stellody.domain.changes import LibraryChange
from stellody.domain.identity import AlbumIdentity
from stellody.ui.scan_summary import MAX_ALBUMS_SHOWN, summary_html

# Built by code point so this file carries neither of the characters it
# forbids, which would otherwise trip the prose sweep on its own guard.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)


def _identity(title: str, artist: str = "Holst") -> AlbumIdentity:
    return AlbumIdentity(album_artist=artist, title=title)


def test_a_first_reading_leads_with_the_whole_library() -> None:
    change = LibraryChange(
        new_albums=(_identity("Planets"),),
        new_tracks=7,
        total_albums=1,
        total_tracks=7,
        previous_albums=0,
    )
    html = summary_html(change, ScanReport())
    assert "Your library is in" in html
    assert "1 album," in html, "a count of one takes the singular"
    assert "7 tracks" in html


def test_an_unchanged_library_says_so_rather_than_implying_a_find() -> None:
    change = LibraryChange(total_albums=482, total_tracks=6877, previous_albums=482)
    html = summary_html(change, ScanReport())
    assert "Nothing has changed since the last scan." in html
    assert "New albums" not in html


def test_what_arrived_is_named_rather_than_only_counted() -> None:
    change = LibraryChange(
        new_albums=(_identity("Blue", "Joni Mitchell"),),
        new_tracks=10,
        total_albums=2,
        total_tracks=17,
        previous_albums=1,
    )
    html = summary_html(change, ScanReport())
    assert "1 new album" in html
    assert "10 new tracks" in html
    assert "Blue" in html
    assert "Joni Mitchell" in html


def test_a_long_list_is_capped_with_the_rest_counted_not_cut() -> None:
    """A report that silently stopped listing would understate what arrived."""
    extra = 5
    change = LibraryChange(
        new_albums=tuple(
            _identity(f"Album {number}") for number in range(MAX_ALBUMS_SHOWN + extra)
        ),
        previous_albums=1,
    )
    html = summary_html(change, ScanReport())
    assert f"and {extra} others" in html
    assert "Album 0" in html


def test_albums_that_went_away_are_reported_and_reassured_about() -> None:
    change = LibraryChange(
        gone_albums=(_identity("Departed"),),
        gone_tracks=3,
        total_albums=1,
        previous_albums=2,
    )
    html = summary_html(change, ScanReport())
    assert "Albums no longer found" in html
    assert "Departed" in html
    assert "nothing has been deleted" in html


def test_the_totals_name_only_the_troubles_that_happened() -> None:
    quiet = summary_html(
        LibraryChange(previous_albums=1), ScanReport(folders_probed=3, files_probed=9)
    )
    assert "Files read" in quiet
    assert "could not be read" not in quiet
    assert "no longer there" not in quiet

    noisy = summary_html(
        LibraryChange(previous_albums=1),
        ScanReport(files_unreadable=2, files_absent=4),
    )
    assert "could not be read" in noisy
    assert "no longer there" in noisy


def test_labelling_issues_point_at_where_they_are_listed() -> None:
    from stellody.domain.health import IssueKind, LibraryIssue

    report = ScanReport(
        issues=(LibraryIssue(kind=IssueKind.MISSING_ALBUM_ARTIST, album="Planets"),)
    )
    html = summary_html(LibraryChange(previous_albums=1), report)
    assert "1 labelling issue" in html
    assert "Library health" in html
    assert "your files are untouched" in html


def test_the_report_carries_no_dash_and_no_styling_qt_would_drop() -> None:
    """Two things the prose sweep cannot see, since neither is a plain dash.

    A dash written as an entity renders as one on screen while reading as
    six ordinary letters in the source. Inline CSS is worse than useless here:
    Qt's rich text supports a subset that excludes opacity, so a colour set
    that way is a decision taken away from the palette and then ignored.
    """
    change = LibraryChange(
        new_albums=tuple(
            _identity(f"Album {number}") for number in range(MAX_ALBUMS_SHOWN + 1)
        ),
        gone_albums=(_identity("Departed"),),
        new_tracks=1,
        gone_tracks=1,
        previous_albums=1,
    )
    html = summary_html(change, ScanReport(files_unreadable=1, files_absent=1))
    for forbidden in ("&mdash;", "&ndash;", EM_DASH, EN_DASH, "style="):
        assert forbidden not in html, forbidden


def test_a_title_carrying_markup_is_escaped_rather_than_rendered() -> None:
    change = LibraryChange(
        new_albums=(_identity("<b>Rock</b> & Roll", "AC&DC"),), previous_albums=1
    )
    html = summary_html(change, ScanReport())
    assert "&lt;b&gt;Rock&lt;/b&gt;" in html
    assert "&amp; Roll" in html
    assert "AC&amp;DC" in html
