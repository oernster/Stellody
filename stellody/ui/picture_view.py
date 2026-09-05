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

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from stellody.domain.picture import Picture

BLACK = QColor(0, 0, 0)


class PictureSurface(QWidget):
    """Draws the last frame it was given, centred and in its own shape."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)
        self._image: QImage | None = None

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
