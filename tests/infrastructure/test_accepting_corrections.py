"""The whole loop, against a real store and a real restart.

The milestone's bar is not that a table can be written to. It is that accepting
a correction empties the report, that emptying it survives closing Stellody and
opening it again, then that resetting brings the original findings back. So this
uses the real SQLite store and the real load; the database is closed between
the accepting and the reading rather than one connection's memory being trusted.

Nothing here writes to a music file, because nothing here has one: the store
holds raw tag values and the library is assembled from them.
"""

from __future__ import annotations

import pathlib

from stellody.application.scan import LoadLibrary
from stellody.application.values import FolderRecord, SourceRecord
from stellody.domain.health import IssueKind
from stellody.domain.overrides import Override, OverrideField
from stellody.infrastructure.store import SqliteLibraryStore

FOLDER = "H:/Music/Portishead/Dummy"
FIRST = f"{FOLDER}/01 Mysterons.flac"
SECOND = f"{FOLDER}/02 Sour Times.flac"
RATE = 44100


def _source(path: str, file_name: str, title: str) -> SourceRecord:
    """One persisted source whose tags collide with its neighbour's.

    Both claim track one, which is the damage the reference library actually
    carries: 132 of its 142 findings are two files claiming one track number.
    """
    return SourceRecord(
        path=path,
        file_name=file_name,
        duration_ms=1000,
        sample_rate=RATE,
        bit_depth=16,
        album="Dummy",
        artists=("Portishead",),
        title=title,
        track=1,
    )


RECORD = FolderRecord(
    folder=FOLDER,
    sources=(
        _source(FIRST, "01 Mysterons.flac", "Mysterons"),
        _source(SECOND, "02 Sour Times.flac", "Sour Times"),
    ),
)


def _seeded(database: str) -> SqliteLibraryStore:
    """A store holding one damaged album, as a scan would have left it."""
    store = SqliteLibraryStore(database)
    store.save_folder(RECORD)
    return store


def _kinds(store: SqliteLibraryStore) -> set[IssueKind]:
    """What the library reports when it is assembled from this store."""
    return {issue.kind for issue in LoadLibrary(store).run().issues}


def _pins_for(store: SqliteLibraryStore) -> tuple[Override, ...]:
    """What accepting the whole report would record, read off the library.

    Built from the resolved tracks rather than from a value typed here, since
    accepting is a listener keeping the correction Stellody already made.
    """
    view = LoadLibrary(store).run()
    album = view.albums[0].identity.handle
    return tuple(
        Override(
            album,
            OverrideField.TRACK_NUMBER,
            str(track.track_number),
            track.source.path,
        )
        for track in view.albums[0].tracks
    ) + (Override(album, OverrideField.ALBUM_ARTIST, "Portishead"),)


def test_the_damage_is_reported_while_nothing_is_accepted(
    tmp_path: pathlib.Path,
) -> None:
    store = _seeded(str(tmp_path / "library.db"))
    try:
        assert IssueKind.DUPLICATE_TRACK_NUMBER in _kinds(store)
    finally:
        store.close()


def test_accepting_empties_the_report_and_it_stays_empty_after_a_restart(
    tmp_path: pathlib.Path,
) -> None:
    """Accepting everything the report lists, in one gesture, then a restart."""
    database = str(tmp_path / "library.db")
    store = _seeded(database)
    try:
        store.accept_overrides(_pins_for(store))
        assert _kinds(store) == set()
    finally:
        store.close()

    store = SqliteLibraryStore(database)
    try:
        assert _kinds(store) == set()
    finally:
        store.close()


def test_the_library_shows_the_same_tracks_once_the_report_is_accepted(
    tmp_path: pathlib.Path,
) -> None:
    """Accepting a correction Stellody already made must not move anything."""
    database = str(tmp_path / "library.db")
    store = _seeded(database)
    try:
        before = LoadLibrary(store).run().albums[0].tracks
        store.accept_overrides(_pins_for(store))
        assert LoadLibrary(store).run().albums[0].tracks == before
    finally:
        store.close()


def test_a_rescan_never_discards_an_accepted_correction(
    tmp_path: pathlib.Path,
) -> None:
    """A correction outliving the scan that prompted it is the whole point.

    Saving the folder again is what a rescan does to a folder it had to re-read,
    so this asks whether that write reaches the accepted set. It must not.
    """
    database = str(tmp_path / "library.db")
    store = _seeded(database)
    try:
        store.accept_overrides(_pins_for(store))
        store.save_folder(RECORD)
        assert _kinds(store) == set()
    finally:
        store.close()


def test_resetting_brings_the_original_findings_back(tmp_path: pathlib.Path) -> None:
    """There is nothing to corrupt, because the raw tags were never altered."""
    database = str(tmp_path / "library.db")
    store = _seeded(database)
    try:
        pins = _pins_for(store)
        store.accept_overrides(pins)
        assert _kinds(store) == set()
        store.discard_overrides(pins)
        assert IssueKind.DUPLICATE_TRACK_NUMBER in _kinds(store)
    finally:
        store.close()


def test_resetting_survives_a_restart_too(tmp_path: pathlib.Path) -> None:
    database = str(tmp_path / "library.db")
    store = _seeded(database)
    try:
        pins = _pins_for(store)
        store.accept_overrides(pins)
        store.discard_overrides(pins)
    finally:
        store.close()

    store = SqliteLibraryStore(database)
    try:
        assert IssueKind.DUPLICATE_TRACK_NUMBER in _kinds(store)
    finally:
        store.close()
