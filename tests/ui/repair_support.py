"""The scaffolding the repair screen's tests are driven from.

Split out of the tests themselves when the file passed the line cap: what
stands in for a store and what counts as a damaged album is one concern;
the behaviour being checked is another.
"""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from stellody.application.repairs import Repairs
from stellody.application.scan import LibraryView
from stellody.domain.grouping import SourceEntry, assemble_albums
from stellody.domain.ordering import TrackCandidate
from stellody.domain.overrides import Override
from stellody.domain.track import TrackSource
from stellody.ui.repairing import RepairDialog

PARENT = "H:/Music/Portishead"
FOLDER = "Dummy"
RATE = 44100


def _entry(file_name: str, title: str) -> SourceEntry:
    """One source whose track number collides with its neighbour's.

    Both claim track one and neither names an album artist, which is the damage
    the reference library actually carries.
    """
    return SourceEntry(
        folder_name=FOLDER,
        parent_path=PARENT,
        parent_name="Portishead",
        candidate=TrackCandidate(
            file_name=file_name,
            source=TrackSource(path=f"{PARENT}/{FOLDER}/{file_name}"),
            duration_ms=1000,
            sample_rate=RATE,
            bit_depth=16,
            tag_track=1,
            tag_title=title,
            artists=("Portishead",),
        ),
        album="Dummy",
    )


COLLIDING = (
    _entry("01 Mysterons.flac", "Mysterons"),
    _entry("02 Sour Times.flac", "Sour Times"),
)


class MemoryStore:
    """A store that keeps what it is told, which is all this needs of one."""

    def __init__(self) -> None:
        self.held: tuple[Override, ...] = ()

    def all_overrides(self) -> tuple[Override, ...]:
        return self.held

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        keys = {(item.album, item.path, item.field) for item in accepted}
        self.held = (
            tuple(
                item
                for item in self.held
                if (item.album, item.path, item.field) not in keys
            )
            + accepted
        )

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        keys = {(item.album, item.path, item.field) for item in unwanted}
        self.held = tuple(
            item
            for item in self.held
            if (item.album, item.path, item.field) not in keys
        )


def load(service: Repairs):
    """A reload that assembles the damaged album against what is accepted."""

    def reload() -> LibraryView:
        albums, issues = assemble_albums(COLLIDING, service._store.all_overrides())
        return LibraryView(albums=albums, issues=issues)

    return reload


def buttons(dialog: RepairDialog) -> list[QPushButton]:
    """Every button on the screen, in the order they were put there."""
    return dialog.findChildren(QPushButton)


def labelled(dialog: RepairDialog, text: str) -> QPushButton:
    """The one button whose text starts with this.

    Never used for a word that is also the start of another control's: "Reset"
    is the start of "Reset everything"; reaching the wrong one opened a
    real modal that hung the whole run.
    """
    found = [button for button in buttons(dialog) if button.text().startswith(text)]
    assert found, f"no button starting {text!r}"
    return found[0]


def exactly(dialog: RepairDialog, text: str) -> QPushButton:
    """The one button whose text is exactly this, for the ambiguous words."""
    found = [button for button in buttons(dialog) if button.text() == text]
    assert found, f"no button reading {text!r}"
    return found[0]


def opened(service: Repairs, parent) -> RepairDialog:
    """The dialog over a library with one damaged album."""
    return RepairDialog(service, load(service), parent)
