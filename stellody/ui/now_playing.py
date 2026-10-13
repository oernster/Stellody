"""Saying what is playing: a mark on its row and its name along the foot.

Both follow the transport rather than a gesture. The status bar used to say
"Playing" only when a track was double clicked, for six seconds, so after Next
or a track playing out it went on naming the one before. Reproduced on
2026-09-13. The name is now a permanent widget, written from the transport on
every change however the change came about, then emptied by a stop.

**A paused track is still in hand.** Only a stop gives the device back, so the
mark and the name stay through a pause, the same line `PlaybackState.is_active`
draws.

**The name takes you to its album.** Rolling the pane up leaves nothing on
screen saying which sleeve the music came from, so finding it again meant
hunting for the right cover. Clicking the name along the foot goes there and
opens the album on the track in hand; Go to playing album on the View menu
does the same from the keyboard, since the name itself takes no focus (Oliver's
ruling of 2026-10-14: no new picture button for it). An album hidden by the
search or the genre filter is left hidden and the foot says so, rather than
the filter being thrown away to reach it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QLabel

from stellody.domain.track import Track
from stellody.ui.playing_mark import PlayingMark, handle_for
from stellody.ui.settings_keys import STATUS_TIMEOUT_MS
from stellody.ui.theme import Mode, palette_for

NOW_PLAYING = "Playing: {title}, {artists}"
# A track whose tags credit nobody is named by its title alone, rather than
# with a comma left hanging where the artists would have gone.
NOW_PLAYING_UNCREDITED = "Playing: {title}"
GO_TO_PLAYING_LABEL = "Go to &playing album"
GO_TO_PLAYING_SHORTCUT = "Ctrl+J"
GO_TO_PLAYING_TOOLTIP = f"Show the album playing ({GO_TO_PLAYING_SHORTCUT})"
PLAYING_HIDDEN = (
    "The album playing is hidden by the search or the genre filter; "
    "clear it to see the album."
)


def now_playing_line(track: Track | None) -> str:
    """What the foot says about this track; nothing where none is in hand."""
    if track is None:
        return ""
    if not track.artist_text:
        return NOW_PLAYING_UNCREDITED.format(title=track.title)
    return NOW_PLAYING.format(title=track.title, artists=track.artist_text)


class PlayingLine(QLabel):
    """The name along the foot, which a click takes to its album.

    Words until the pointer rests on them, then underlined under a pointing
    hand, the way a link says it can be followed. Never a stop on the ring:
    the menu entry is the keyboard's way there.
    """

    clicked = Signal()

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(GO_TO_PLAYING_TOOLTIP)

    def _underline(self, on: bool) -> None:
        font = self.font()
        font.setUnderline(on)
        self.setFont(font)

    def enterEvent(self, event) -> None:
        """Underline while the pointer rests here."""
        self._underline(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Plain words again once it leaves."""
        self._underline(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """A left click let go over the name follows it.

        An empty name needs no check of its own here: it is empty because
        nothing is in hand, which `show_playing_album` already answers.
        """
        inside = self.rect().contains(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and inside:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class NowPlaying:
    """The window's half of saying what is playing."""

    def start_now_playing(self) -> None:
        """Build the mark, the name along the foot and the way back to it."""
        self._mark = PlayingMark(self._model)
        self._now_playing = PlayingLine(self)
        self._now_playing.clicked.connect(self.show_playing_album)
        self.statusBar().addPermanentWidget(self._now_playing)
        # Made here rather than with the menus, because the transport decides
        # whether it can act; the View menu only carries it. A disabled action
        # also refuses its shortcut, so the two cannot disagree.
        self.go_to_playing_action = QAction(GO_TO_PLAYING_LABEL, self)
        self.go_to_playing_action.setShortcut(QKeySequence(GO_TO_PLAYING_SHORTCUT))
        self.go_to_playing_action.triggered.connect(self.show_playing_album)
        self.go_to_playing_action.setEnabled(False)

    def _in_hand(self) -> Track | None:
        """The track the transport holds while it is playing or paused."""
        return self._transport.current if self._transport.state.is_active else None

    def show_now_playing(self) -> None:
        """Mark and name the track in hand; clear both once nothing is."""
        in_hand = self._in_hand()
        # The album goes with it, because the mark is held by handle rather
        # than by the track object: see `playing_mark.py`.
        self._mark.show(self._transport.album, in_hand)
        self._now_playing.setText(now_playing_line(in_hand))
        self.go_to_playing_action.setEnabled(in_hand is not None)

    @Slot()
    def show_playing_album(self) -> None:
        """Go to the album playing, opened on the track in hand.

        Found by handle, as the mark is, so a track from before a reload still
        finds its row. Missing from the model means a search or the genre
        filter is hiding it, which is said rather than undone.
        """
        handle = handle_for(self._transport.album, self._in_hand())
        if handle is None:
            return
        where = self._model.index_for_handle(handle)
        if not where.isValid():
            self.statusBar().showMessage(PLAYING_HIDDEN, STATUS_TIMEOUT_MS)
            return
        self._carry_to_view(self._model.track_at(where))

    def show_mark_appearance(self, mode: Mode) -> None:
        """Mark in the pink belonging to this appearance."""
        self._mark.wear(palette_for(mode).playing)
