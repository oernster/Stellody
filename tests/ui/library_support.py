"""One small library, shared by the tests that search it and open it.

Two albums with real titles, since a title is what a search reads and what a
pane shows. Kept here rather than in each test module so the two halves of
the search story, narrowing the rows and the pane underneath them, are asking
about the same library rather than two that could quietly diverge.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from tray_support import RememberingStore, build

from stellody.application.artwork import AlbumArtSources
from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource
from stellody.ui.models import Column


def track(title: str, number: int, disc: int = 1) -> Track:
    """One track carrying a real title, since a title is what is searched."""
    return Track(
        source=TrackSource(path=f"{number:02d} {title}.flac"),
        disc_number=disc,
        track_number=number,
        title=title,
        artists=("Holst",),
        duration_ms=1000,
        sample_rate=CD_SAMPLE_RATE,
        bit_depth=16,
    )


PLANETS = Album(
    identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
    tracks=(track("Venus", 1), track("Mars", 2)),
)
SIMPLE = Album(
    identity=AlbumIdentity(album_artist="Zero 7", title="Simple Things"),
    tracks=(track("Destiny", 1),),
)
ART = (
    AlbumArtSources(key=PLANETS.identity.art_key, sidecars=("planets.jpg",)),
    AlbumArtSources(key=SIMPLE.identity.art_key, sidecars=("simple.jpg",)),
)


def library_window(application: QApplication):
    """A real window holding both albums, reached the way a load reaches them."""
    made = build(RememberingStore(), RecordingPlayer())
    made.show_library((PLANETS, SIMPLE), ART)
    application.processEvents()
    yield made
    made.close()


def titles(window) -> list[str]:
    """The album titles the tree is showing, top to bottom."""
    model = window._model
    return [
        model.data(model.index(row, Column.TITLE, QModelIndex()))
        for row in range(model.rowCount(QModelIndex()))
    ]
