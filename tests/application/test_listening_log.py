"""The log that holds every rating and play count, written through as it goes.

The store is a hand-written fake that records what it was asked to write, so
what is asserted is the two staying in step rather than SQLite behaving.
"""

from __future__ import annotations

from stellody.application.listening import ListeningLog
from stellody.domain.listening import Listening

TRACK = "0123456789abcdef"
OTHER = "fedcba9876543210"
PATH = "01 Mars.flac"


class RememberingStore:
    """Stands in for the store, keeping what it was told in a dictionary."""

    def __init__(self, held: dict[str, Listening] | None = None) -> None:
        self.held: dict[str, Listening] = dict(held or {})
        self.writes: list[tuple[str, str, Listening]] = []

    def all_listening(self) -> dict[str, Listening]:
        return dict(self.held)

    def set_listening(self, handle: str, path: str, record: Listening) -> None:
        self.writes.append((handle, path, record))
        self.held[handle] = record


class TestReadingIt:
    def test_a_track_nobody_has_touched_reads_as_empty(self) -> None:
        log = ListeningLog(RememberingStore())
        log.load()
        assert log.of(TRACK).is_empty

    def test_loading_takes_what_the_store_holds(self) -> None:
        store = RememberingStore({TRACK: Listening(stars=4, plays=2)})
        log = ListeningLog(store)
        log.load()
        assert log.of(TRACK) == Listening(stars=4, plays=2)

    def test_loading_again_replaces_what_was_held(self) -> None:
        """A rescan does not change these; a second library would."""
        store = RememberingStore({TRACK: Listening(stars=4)})
        log = ListeningLog(store)
        log.load()
        store.held = {OTHER: Listening(stars=1)}
        log.load()
        assert log.of(TRACK).is_empty
        assert log.of(OTHER).stars == 1

    def test_it_holds_its_own_copy(self) -> None:
        """What the store hands back is not the log's to be changed under it."""
        store = RememberingStore({TRACK: Listening(stars=4)})
        log = ListeningLog(store)
        log.load()
        store.held.clear()
        assert log.of(TRACK).stars == 4


class TestWritingIt:
    def test_rating_a_track_is_held_and_written(self) -> None:
        store = RememberingStore()
        log = ListeningLog(store)
        log.load()
        assert log.rate(TRACK, PATH, 5) == Listening(stars=5)
        assert log.of(TRACK).stars == 5
        assert store.writes == [(TRACK, PATH, Listening(stars=5))]

    def test_counting_a_play_is_held_and_written(self) -> None:
        store = RememberingStore()
        log = ListeningLog(store)
        log.load()
        assert log.count_play(TRACK, PATH) == Listening(plays=1)
        assert store.writes == [(TRACK, PATH, Listening(plays=1))]

    def test_a_rating_keeps_the_count_it_found(self) -> None:
        store = RememberingStore({TRACK: Listening(plays=7)})
        log = ListeningLog(store)
        log.load()
        assert log.rate(TRACK, PATH, 3) == Listening(stars=3, plays=7)

    def test_a_play_keeps_the_rating_it_found(self) -> None:
        store = RememberingStore({TRACK: Listening(stars=3)})
        log = ListeningLog(store)
        log.load()
        assert log.count_play(TRACK, PATH) == Listening(stars=3, plays=1)

    def test_plays_accumulate_across_calls(self) -> None:
        log = ListeningLog(RememberingStore())
        log.load()
        log.count_play(TRACK, PATH)
        log.count_play(TRACK, PATH)
        assert log.of(TRACK).plays == 2

    def test_one_track_does_not_reach_another(self) -> None:
        log = ListeningLog(RememberingStore())
        log.load()
        log.rate(TRACK, PATH, 5)
        assert log.of(OTHER).is_empty

    def test_it_writes_without_being_loaded_first(self) -> None:
        """Nothing has a save step to forget, so nothing has a load one."""
        store = RememberingStore()
        log = ListeningLog(store)
        log.rate(TRACK, PATH, 2)
        assert store.held[TRACK] == Listening(stars=2)
