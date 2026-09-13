"""Taking back everything accepted in one album, in a single press.

Decided with Oliver on 2026-09-13: the screen could reset one group of files or
the whole library, while what a listener thinks in is an album. A rule that
guessed wrong about one record is fixed by taking that record back, not by
finding each of its fields one row at a time.

Two damaged albums rather than the one the repair suite is built on, since
"only that album" means nothing over a library of one.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QWidget
from repair_support import (  # noqa: F401  the fixtures register by import
    RATE,
    MemoryStore,
    buttons,
    labelled,
    never_really_ask,
    never_really_report,
)

from stellody.application.loading import LibraryView
from stellody.application.repairs import Repairs
from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.ordering import TrackCandidate
from stellody.domain.track import TrackSource
from stellody.ui.repairing import RepairDialog

MUSIC = "H:/Music"
DURATION_MS = 1000
BIT_DEPTH = 16
# Both claim track one and neither names an album artist, which is the damage
# the repair suite's own album carries.
COLLIDING_TRACK = 1
ALBUM_RESET = "Reset album"


def colliding(artist: str, folder: str) -> tuple[SourceEntry, ...]:
    """One album whose two tracks both claim to be the first."""
    parent = f"{MUSIC}/{artist}"
    return tuple(
        SourceEntry(
            folder_name=folder,
            parent_path=parent,
            parent_name=artist,
            candidate=TrackCandidate(
                file_name=f"{title}.flac",
                source=TrackSource(path=f"{parent}/{folder}/{title}.flac"),
                duration_ms=DURATION_MS,
                sample_rate=RATE,
                bit_depth=BIT_DEPTH,
                tag_track=COLLIDING_TRACK,
                tag_title=title,
                artists=(artist,),
            ),
            album=folder,
        )
        for title in ("First", "Second")
    )


LIBRARY = colliding("Portishead", "Dummy") + colliding("Massive Attack", "Mezzanine")
ALBUMS = len({entry.folder_name for entry in LIBRARY})


def opened(service: Repairs) -> RepairDialog:
    """The repair screen over both albums, reloaded against what is accepted."""

    def reload() -> LibraryView:
        albums, issues = assemble_albums(LIBRARY, service._store.all_overrides())
        return LibraryView(albums=albums, issues=issues)

    return RepairDialog(service, reload, None)


def everything_accepted() -> tuple[Repairs, RepairDialog]:
    """Both albums' corrections accepted, the screen redrawn to show them."""
    repairs = Repairs(MemoryStore())
    dialog = opened(repairs)
    labelled(dialog, "Accept everything").click()
    # Guards the fixture: every test here would pass over nothing accepted.
    assert len(accepted_albums(repairs)) == ALBUMS
    return repairs, dialog


def label_of(dialog: RepairDialog, album: str) -> str:
    """How an album is named to a reader, read off the library it loaded."""
    return next(
        found.identity.label
        for found in dialog._view.albums
        if found.identity.handle == album
    )


def accepted_albums(repairs: Repairs) -> set[str]:
    """Every album something has been accepted in."""
    return {group.album for group in repairs.accepted()}


def album_resets(dialog: RepairDialog) -> list[QPushButton]:
    """Every album's own reset, in the order the albums are listed."""
    return [
        button for button in buttons(dialog) if button.text().startswith(ALBUM_RESET)
    ]


def caption_of(button: QPushButton) -> str:
    """The words on the row a button acts on."""
    row: QWidget = button.parentWidget()
    return row.findChild(QLabel).text()


def album_of(dialog: RepairDialog, repairs: Repairs, button: QPushButton) -> str:
    """Which album a reset's row names."""
    return next(
        album
        for album in accepted_albums(repairs)
        if label_of(dialog, album) in caption_of(button)
    )


def test_each_album_accepted_in_offers_one_reset_naming_its_count(
    application,
) -> None:
    """The count is every file accepted in that album, across its fields."""
    repairs, dialog = everything_accepted()
    offered = album_resets(dialog)
    assert len(offered) == len(accepted_albums(repairs))
    for button in offered:
        album = album_of(dialog, repairs, button)
        held = sum(group.count for group in repairs.accepted() if group.album == album)
        assert button.text() == f"{ALBUM_RESET} ({held})"
    dialog.deleteLater()


def test_resetting_an_album_takes_back_that_album_alone(application) -> None:
    """The other album's corrections are left exactly as they were accepted."""
    repairs, dialog = everything_accepted()
    first = album_resets(dialog)[0]
    taken = album_of(dialog, repairs, first)
    kept = tuple(group for group in repairs.accepted() if group.album != taken)
    first.click()
    assert repairs.accepted() == kept
    reported = {issue.album_key for issue in repairs.acceptable(dialog._view.issues)}
    assert reported == {taken}
    dialog.deleteLater()


def test_resetting_an_album_does_not_ask(
    application, never_really_ask  # noqa: F811
) -> None:
    """Bounded to one record, as a group's reset is; only the lot asks first."""
    _repairs, dialog = everything_accepted()
    album_resets(dialog)[0].click()
    assert never_really_ask == []
    dialog.deleteLater()


def test_the_rows_under_an_album_do_not_repeat_its_name(application) -> None:
    """The album is named once, on the row whose button takes all of it back."""
    repairs, dialog = everything_accepted()
    for album in accepted_albums(repairs):
        label = label_of(dialog, album)
        naming = [
            found.text()
            for found in dialog.findChildren(QLabel)
            if label in found.text()
        ]
        assert len(naming) == 1, (label, naming)
    dialog.deleteLater()
