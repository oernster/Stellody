"""The picture, drawn where the library was, with black around it.

It keeps the shape the file was made in rather than filling the space, because
a concert film stretched to the width of a library window is worse than one
with a margin. The black is deliberate: a picture sitting on the application's
own background reads as a panel with a picture in it, while black reads as the
picture being the thing on screen.

Nothing here is a stop on the keyboard ring. It is a surface rather than a
control: there is nothing to press on it and nothing to type into it, which is
the rule every pane in this application already follows.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from stellody.domain.picture import Picture
from stellody.ui.picture_controls import SizeButton

BLACK = QColor(0, 0, 0)

# How far in from the corner the size button sits.
BUTTON_MARGIN_PX = 12

# How long the button stays up after the mouse stops moving over a picture
# filling the window. Long enough to reach, short enough that it is not left
# sitting over the picture it exists to get out of the way of.
HOVER_HOLD_MS = 2500


class PictureSurface(QWidget):
    """Draws the last frame it was given, centred and in its own shape."""

    size_toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)
        self._image: QImage | None = None
        self.size_button = SizeButton(self)
        self.size_button.clicked.connect(self.size_toggled)
        # Tracked so the button can be brought back by a movement rather than
        # by a press, which is the gesture somebody makes when they want a
        # control they cannot currently see.
        self.setMouseTracking(True)
        self._hiding = QTimer(self)
        self._hiding.setSingleShot(True)
        self._hiding.setInterval(HOVER_HOLD_MS)
        self._hiding.timeout.connect(self._hide_button_while_filling)

    def set_filling(self, filling: bool) -> None:
        """Say which way the button points, plus how it behaves.

        At the ordinary size the button stays up: it sits on a picture that is
        already sharing the window, so it takes nothing away. Filling the
        window, it goes after a moment and comes back on a movement, because
        there the whole point is that nothing is over the picture.
        """
        self.size_button.set_filling(filling)
        self.size_button.setVisible(True)
        self._place_button()
        if filling:
            self._hiding.start()
        else:
            self._hiding.stop()

    def _hide_button_while_filling(self) -> None:
        """Take the button away, unless the pointer is sitting on it."""
        if self.size_button.underMouse():
            self._hiding.start()
            return
        self.size_button.setVisible(False)

    def _place_button(self) -> None:
        """Bottom right of the surface, inside the margin."""
        self.size_button.move(
            self.width() - self.size_button.width() - BUTTON_MARGIN_PX,
            self.height() - self.size_button.height() - BUTTON_MARGIN_PX,
        )

    def resizeEvent(self, event) -> None:
        """Keep the button in its corner however the surface changes."""
        super().resizeEvent(event)
        self._place_button()

    def mouseMoveEvent(self, event) -> None:
        """Any movement over the picture brings the button back."""
        super().mouseMoveEvent(event)
        if self.size_button.filling:
            self.size_button.setVisible(True)
            self._place_button()
            self._hiding.start()

    def show_picture(self, picture: Picture) -> None:
        """Take one frame and ask for a repaint.

        The image is COPIED. A QImage built over a buffer does not own it, while
        the bytes here belong to a picture the caller is free to drop the
        moment this returns; drawing from a freed buffer is not an error that
        announces itself.
        """
        image = QImage(
            picture.data,
            picture.width,
            picture.height,
            picture.bytes_per_row,
            QImage.Format.Format_RGB888,
        )
        self._image = image.copy()
        self.update()

    def clear(self) -> None:
        """Forget the frame, so nothing of one track is left over another."""
        self._image = None
        self.update()

    @property
    def has_picture(self) -> bool:
        """True while there is a frame to draw."""
        return self._image is not None

    def picture_rect(self) -> QRect:
        """Where the frame is drawn: as large as fits, centred, in shape."""
        if self._image is None:
            return QRect()
        size = self._image.size().scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio
        )
        return QRect(
            (self.width() - size.width()) // 2,
            (self.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )

    def paintEvent(self, event) -> None:
        """Black everywhere, then the frame over it."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), BLACK)
        if self._image is None:
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self.picture_rect(), self._image)
