"""Launch does nothing to the music folder; quitting mid-scan lets go.

Both were felt rather than seen: opening the application walked a large library
every time; quitting during that walk left the window frozen while Qt
waited for a scan it had no way to interrupt.

Qt is never mocked. The store and the walker are hand-written fakes, so what is
asserted is what the window asked them for.
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication

from stellody.application.ports import FolderListing, FolderRecord, SourceRecord
from stellody.application.scan import LoadLibrary, ScanLibrary
from stellody.ui.main_window import MainWindow
from stellody.ui.settings_keys import FALSE, SETTING_ROOT, SETTING_SCAN_FINISHED, TRUE
from stellody.ui.worker import ScanRunner

ROOT = "H:/FLACMusic"
# More folders than a cancelled scan will get through; more than the test is
# willing to wait for one that ignores the ask.
FOLDERS_IN_A_LONG_SCAN = 200_000
PATIENCE_S = 5.0
FOLDER = f"{ROOT}/Sasha/Involver"


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


class SpyWalker:
    """A walker that refuses to be used, remembering every ask."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def walk(self, root: str):
        """Record the ask. Launch must never reach here."""
        self.calls.append(f"walk {root}")
        return iter(())

    def count(self, root: str) -> int:
        """Record the ask. Launch must never reach here either."""
        self.calls.append(f"count {root}")
        return 0


class FakeStore:
    """A store holding one remembered folder, plus the settings."""

    def __init__(self, records: tuple[FolderRecord, ...], settings: dict) -> None:
        self.records = records
        self.settings = dict(settings)

    def load_folders(self) -> tuple[FolderRecord, ...]:
        """What the last scan wrote down."""
        return self.records

    def file_signatures(self) -> dict[str, tuple[int, int]]:
        """Nothing on record, so every folder would be read afresh."""
        return {}

    def save_folder(self, record: FolderRecord) -> None:
        """A scan that reaches here in these tests has already gone wrong."""
        raise AssertionError("no folder should be read")

    def mark_absent(self, seen_paths: frozenset[str]) -> int:
        """Nothing goes missing in these tests."""
        return 0

    def get_setting(self, key: str, default: str = "") -> str:
        """One stored setting."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        """Store one setting."""
        self.settings[key] = value

    def close(self) -> None:
        """Nothing to release."""


def remembered() -> tuple[FolderRecord, ...]:
    """One folder of two tracks, as a completed scan would have left it."""
    sources = tuple(
        SourceRecord(
            path=f"{FOLDER}/0{number}.flac",
            file_name=f"0{number}.flac",
            duration_ms=1000,
            sample_rate=44100,
            bit_depth=16,
            album="Involver",
            album_artist="Sasha",
            title=f"Track {number}",
            track=number,
        )
        for number in (1, 2)
    )
    return (FolderRecord(folder=FOLDER, sources=sources),)


def window(
    application: QApplication, store: FakeStore, walker: SpyWalker
) -> MainWindow:
    """A window over fakes, with nothing behind the walker but a spy."""

    def session():
        return ScanLibrary(walker, None, None, store), store

    return MainWindow(scan_session=session, loader=LoadLibrary(store), settings=store)


def test_launch_reads_the_store_and_never_the_music_folder(
    application: QApplication,
) -> None:
    walker = SpyWalker()
    store = FakeStore(remembered(), {SETTING_ROOT: ROOT, SETTING_SCAN_FINISHED: TRUE})
    made = window(application, store, walker)
    made.load_remembered()
    assert walker.calls == []
    assert made._model.rowCount() == 1
    assert "1 albums" in made.statusBar().currentMessage()
    made.close()


def test_a_scan_that_never_finished_says_so_rather_than_looking_short(
    application: QApplication,
) -> None:
    walker = SpyWalker()
    store = FakeStore(remembered(), {SETTING_ROOT: ROOT, SETTING_SCAN_FINISHED: FALSE})
    made = window(application, store, walker)
    made.load_remembered()
    assert "did not finish" in made.statusBar().currentMessage()
    assert walker.calls == []
    made.close()


def test_a_library_scanned_before_the_marker_existed_reads_as_finished(
    application: QApplication,
) -> None:
    """An absent setting means an older version wrote it, not an interruption."""
    walker = SpyWalker()
    store = FakeStore(remembered(), {SETTING_ROOT: ROOT})
    made = window(application, store, walker)
    made.load_remembered()
    assert "did not finish" not in made.statusBar().currentMessage()
    made.close()


def test_with_no_folder_chosen_it_asks_for_one_rather_than_scanning(
    application: QApplication,
) -> None:
    walker = SpyWalker()
    store = FakeStore((), {})
    made = window(application, store, walker)
    made.load_remembered()
    assert made.statusBar().currentMessage() == "Choose a music folder to begin."
    assert walker.calls == []
    made.close()


def test_starting_a_scan_records_that_one_is_unfinished(
    application: QApplication,
) -> None:
    """The marker is written before the walk, so a kill cannot outrun it."""
    walker = SpyWalker()
    store = FakeStore(remembered(), {SETTING_ROOT: ROOT, SETTING_SCAN_FINISHED: TRUE})
    made = window(application, store, walker)
    made.start_scan()
    assert store.settings[SETTING_SCAN_FINISHED] == FALSE
    made._runner.wait()
    made.close()


class SlowWalker:
    """A walker with more folders than a test would wait for."""

    def __init__(self, folders: int) -> None:
        self.folders = folders
        self.yielded = 0

    def count(self, root: str) -> int:
        """How many are coming."""
        return self.folders

    def walk(self, root: str):
        """Yield empty folders, counting how many were asked for."""
        for number in range(self.folders):
            self.yielded += 1
            yield FolderListing(folder=f"{root}/{number}", audio=())


def test_quitting_during_a_scan_stops_it_rather_than_waiting_it_out(
    application: QApplication,
) -> None:
    """Qt cannot interrupt a running slot, so wait() has to cancel first."""
    walker = SlowWalker(FOLDERS_IN_A_LONG_SCAN)
    store = FakeStore(remembered(), {SETTING_ROOT: ROOT})
    scanner = ScanLibrary(walker, None, None, store)
    runner = ScanRunner()
    started = time.monotonic()
    assert runner.start(lambda: (scanner, store), ROOT) is True
    runner.wait()
    assert time.monotonic() - started < PATIENCE_S
    assert walker.yielded < FOLDERS_IN_A_LONG_SCAN
