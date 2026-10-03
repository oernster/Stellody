"""A rating or a play count the library file will not take, said on screen.

Measured against a read only database: the window showed five stars, the disk
held nothing and nothing was said, so the rating vanished at the next start.
Now the log holds nothing the store refused and the window says why.
"""

from __future__ import annotations

import pytest
from library_support import ART, PLANETS, SIMPLE
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.application.listening import ListeningUnwritable
from stellody.domain.listening import NO_STARS, album_handle, track_handle
from stellody.ui.rating import PLAY_NOT_SAVED, RATING_NOT_SAVED
from stellody.ui.row_text import STARS_ROLE, Column


class RefusingStore:
    """A listening store whose file will not take a write."""

    def all_listening(self) -> dict:
        return {}

    def set_listening(self, handle: str, path: str, record: object) -> None:
        raise ListeningUnwritable("attempt to write a readonly database")


@pytest.fixture
def window(application: QApplication, monkeypatch: pytest.MonkeyPatch):
    """A window over two albums whose ratings cannot be written down."""
    made = build(RememberingStore(), RecordingPlayer())
    made.show_library((PLANETS, SIMPLE), ART)
    monkeypatch.setattr(made._listening, "_store", RefusingStore())
    application.processEvents()
    yield made
    made.close()


def _cell(window, row: int, track_row: int):
    """The stars cell of one track row."""
    album = window._model.index(row, Column.TITLE, QModelIndex())
    return window._model.index(track_row, Column.STARS, album)


def test_a_refused_track_rating_is_said_and_not_shown(window) -> None:
    assert window.rate_track(_cell(window, 0, 0), 5)
    assert window.statusBar().currentMessage() == RATING_NOT_SAVED
    assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).is_empty
    assert _cell(window, 0, 0).data(STARS_ROLE) == NO_STARS


def test_a_refused_album_rating_is_said_and_the_stars_put_back(window) -> None:
    window.open_album_at(window._model.index(0, Column.TITLE, QModelIndex()))
    # The way a press arrives: the widget shows the stars, then reports them.
    window._album_pane.album_stars._choose(4)
    assert window.statusBar().currentMessage() == RATING_NOT_SAVED
    assert window._listening.of(album_handle(PLANETS.identity)).is_empty
    assert window._album_pane.album_stars.stars == NO_STARS


def test_a_refused_play_count_is_said(window) -> None:
    window.count_play(PLANETS, PLANETS.ordered_tracks()[0])
    assert window.statusBar().currentMessage() == PLAY_NOT_SAVED
    assert window._listening.of(track_handle(PLANETS.identity, 1, 1)).is_empty
