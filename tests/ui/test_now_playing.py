"""What is playing is marked in both views and named along the foot.

Reproduced offscreen on 2026-09-13 in the real window: once another track was
clicked while one played, the playing row carried no background in the list or
in the album open under the sleeves, so nothing on screen said what was
playing. The status bar went on saying "Playing Track 1" after Next and after a
track played out, because only a double click wrote it.

The model marks the row, since both views draw from the one model through the
one delegate; the foot names the track on every change, however it came about.
"""

from __future__ import annotations

from playback_support import album_index, player, track_index, window
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem
from recording_player import RecordingPlayer

from stellody.ui.main_window import MainWindow
from stellody.ui.theme import palette_for

__all__ = ["player", "window"]

FIRST = 0
SECOND = 1
THIRD = 2
# A canvas big enough to hold one row and read a pixel out of the middle.
PAINT_PX = 40
# Anything a delegate could not have painted by accident.
CANVAS = "#ff00ff"


def marks(window: MainWindow, row: int) -> list[str | None]:
    """The background the model gives every cell of one track row."""
    model = window._model
    parent = album_index(window)
    return [
        None if brush is None else brush.color().name()
        for brush in (
            model.data(model.index(row, column, parent), Qt.ItemDataRole.BackgroundRole)
            for column in range(model.columnCount(parent))
        )
    ]


def marked(window: MainWindow) -> list[str]:
    """Every cell of a row marked as playing, in the appearance on show."""
    parent = album_index(window)
    columns = window._model.columnCount(parent)
    return [palette_for(window.theme_mode).playing] * columns


def unmarked(window: MainWindow) -> list[None]:
    """Every cell of a row left to the style."""
    return [None] * window._model.columnCount(album_index(window))


def painted(delegate, index) -> str:
    """The colour a delegate leaves in the middle of a SELECTED row."""
    option = QStyleOptionViewItem()
    delegate.initStyleOption(option, index)
    option.rect = QRect(0, 0, PAINT_PX, PAINT_PX)
    option.state |= QStyle.StateFlag.State_Selected
    canvas = QPixmap(PAINT_PX, PAINT_PX)
    canvas.fill(QColor(CANVAS))
    painter = QPainter(canvas)
    delegate.paint(painter, option, index)
    painter.end()
    return canvas.toImage().pixelColor(PAINT_PX // 2, PAINT_PX // 2).name()


def started(window: MainWindow, row: int = FIRST) -> None:
    """Play one track from the list, the way a double click does."""
    window.activate(track_index(window, row))
    window._poll_transport()


def test_the_playing_row_is_marked_after_another_is_clicked(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The reported case: the highlight moves away, the mark must not."""
    started(window)
    window._tree.setCurrentIndex(track_index(window, SECOND))
    assert marks(window, FIRST) == marked(window)
    assert marks(window, SECOND) == unmarked(window)


def test_the_list_paints_the_mark_even_while_selected(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """A role returned is not a row painted; Qt skips it on a selected row."""
    started(window)
    delegate = window._tree.itemDelegate()
    colour = painted(delegate, track_index(window, FIRST))
    assert colour == palette_for(window.theme_mode).playing


def test_the_album_under_the_sleeves_paints_the_mark(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The other view, which is where the second half of the report was."""
    window.toggle_view()
    window.open_album_at(album_index(window))
    started(window)
    delegate = window._album_pane.columns[0].itemDelegate()
    colour = painted(delegate, track_index(window, FIRST))
    assert colour == palette_for(window.theme_mode).playing


def test_next_moves_the_mark(window: MainWindow, player: RecordingPlayer) -> None:
    """One row marked at a time, the one the transport has moved to."""
    started(window)
    window.next_track()
    assert marks(window, FIRST) == unmarked(window)
    assert marks(window, SECOND) == marked(window)


def test_a_track_playing_out_moves_the_mark(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """No button is pressed at a play-out; the poll is what notices."""
    started(window)
    player.finished = True
    window._poll_transport()
    assert marks(window, FIRST) == unmarked(window)
    assert marks(window, SECOND) == marked(window)


def test_pausing_keeps_the_mark(window: MainWindow, player: RecordingPlayer) -> None:
    """A paused track is still the track in hand."""
    started(window)
    window.toggle_playback()
    assert marks(window, FIRST) == marked(window)


def test_stopping_clears_the_mark_and_the_name(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """A stop gives the device back, so nothing is playing to be named."""
    started(window)
    window.stop_playback()
    assert marks(window, FIRST) == unmarked(window)
    assert window._now_playing.text() == ""


def test_the_foot_names_what_is_playing_on_every_change(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """A double click, a Next and a play-out each change what it says."""
    started(window)
    assert window._now_playing.text() == "Playing: Track 1, Holst"
    window.next_track()
    assert window._now_playing.text() == "Playing: Track 2, Holst"
    player.finished = True
    window._poll_transport()
    assert window._now_playing.text() == "Playing: Track 3, Holst"


def test_the_mark_follows_the_appearance(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Each appearance carries its own pink, readable behind its own text."""
    started(window)
    window.toggle_theme()
    assert marks(window, FIRST) == marked(window)


def test_a_flash_shows_over_the_mark_then_gives_it_back(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """A search pulsing the playing row wins while it pulses, then lets go."""
    started(window)
    found = palette_for(window.theme_mode).found
    window._flash.start(track_index(window, FIRST), found)
    assert marks(window, FIRST)[0] == found
    window._flash.stop()
    assert marks(window, FIRST) == marked(window)
