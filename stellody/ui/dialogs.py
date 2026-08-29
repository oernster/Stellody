"""Dialogs: a neutral-start base, the licence viewer and About."""

from __future__ import annotations

import math
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from stellody.shared import resources
from stellody.shared.version import (
    APP_AUTHOR,
    APP_NAME,
    APP_TAGLINE,
    COPYRIGHT_NOTICE,
    __version__,
)
from stellody.ui.auto_scroller import AutoScroller

ABOUT_ICON_PX = 96
ABOUT_MIN_WIDTH_PX = 560
ABOUT_BODY_MIN_HEIGHT_PX = 330
LICENCE_HEIGHT_PX = 520
# A licence arrives hard wrapped, so the dialog is fitted to the width its
# own wrapping asks for. Measured: the LGPL text wants 1009px at the setup
# program's monospace size, so the previous 900 cap cut 147px off the right
# of every line. The cap guards a pathological line rather than a real
# licence; the screen is the harder limit of the two.
LICENCE_MAX_WIDTH_PX = 1400

LICENCE_FALLBACK = (
    "The licence text could not be located beside the application. "
    "It is available in the source repository."
)

CREDITS = (
    ("PySide6 (Qt for Python)", "LGPL-3.0", "the user interface"),
    ("Python", "PSF", "the language and standard library"),
    ("mutagen", "GPL-2.0-or-later", "reading tags"),
    ("soundfile and libsndfile", "BSD-3-Clause and LGPL-2.1", "decoding audio"),
    ("sounddevice and PortAudio", "MIT", "audio output"),
    ("NumPy", "BSD-3-Clause", "sample buffers"),
    ("pytest, pytest-cov and pytest-qt", "MIT", "the test suite"),
    ("black, flake8 and ruff", "MIT", "formatting and linting"),
    ("Pillow", "HPND", "building the icon set"),
)


class _NeutralStart(QWidget):
    """A zero-size focus holder, so a dialog opens with nothing highlighted."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def focusOutEvent(self, event) -> None:
        """Leave the tab ring once focus has moved on to a real control."""
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        super().focusOutEvent(event)


class NeutralDialog(QDialog):
    """A dialog that opens with neutral focus rather than on its first control."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._neutral = _NeutralStart(self)
        self._started = False

    def showEvent(self, event) -> None:
        """Park focus on the neutral holder the first time the dialog opens."""
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._neutral.setFocus(Qt.FocusReason.OtherFocusReason)


def close_row(dialog: QDialog) -> QHBoxLayout:
    """The shared trailing row holding a single Close button."""
    row = QHBoxLayout()
    row.addStretch()
    button = QPushButton("Close", dialog)
    button.setDefault(True)
    button.clicked.connect(dialog.accept)
    row.addWidget(button)
    return row


class LicenceDialog(NeutralDialog):
    """Shows one licence text, sized to the text rather than to a guess."""

    def __init__(
        self, title: str, path: pathlib.Path | None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self._body = QTextBrowser(self)
        self._body.setObjectName("LicenceView")
        # Measured 2026-08-28: a fresh widget carries the fallback proportional
        # font until the style is applied to it; the stylesheet only reaches it
        # on polish. Sizing the dialog before that measures the wrong font
        # entirely, so the licence opened 77px too narrow and lost the right of
        # every line the moment polish switched it to the monospace face.
        self._body.ensurePolished()
        self._body.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        self._body.setPlainText(_licence_text(path))
        layout.addWidget(self._body)
        layout.addLayout(close_row(self))
        natural = self._natural_width()
        allowed = min(LICENCE_MAX_WIDTH_PX, _available_width(self))
        if natural > allowed:
            # The display cannot take the licence's own wrapping, so wrap it
            # here instead of letting every line run off the right edge.
            self._body.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.resize(min(natural, allowed), LICENCE_HEIGHT_PX)
        self.scroller = AutoScroller(self._body)

    def _natural_width(self) -> int:
        """The width the licence's own hard wrapping asks for, plus the chrome."""
        document = math.ceil(self._body.document().idealWidth())
        scrollbar = self._body.verticalScrollBar().sizeHint().width()
        frame = 2 * self._body.frameWidth()
        margins = self.layout().contentsMargins()
        return document + scrollbar + frame + margins.left() + margins.right()


def _available_width(dialog: QDialog) -> int:
    """How wide the display will actually allow, so nothing opens off screen."""
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is None:
        return LICENCE_MAX_WIDTH_PX
    return screen.availableGeometry().width()


def _licence_text(path: pathlib.Path | None) -> str:
    """The licence file's text; an explanation when it is missing."""
    if path is None:
        return LICENCE_FALLBACK
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return LICENCE_FALLBACK


def _credits_html() -> str:
    """The open source credits as list items."""
    return "".join(
        f"<li><b>{name}</b> - {licence} ({purpose}).</li>"
        for name, licence, purpose in CREDITS
    )


def about_html() -> str:
    """The whole body of the About dialog."""
    return (
        f"<h2>{APP_NAME}</h2>"
        f"<p><b>{APP_TAGLINE}</b></p>"
        f"<p><b>Version:</b> {__version__}</p>"
        f"<p><b>Author:</b> {APP_AUTHOR}</p>"
        f"<p>{COPYRIGHT_NOTICE}</p>"
        "<p>Stellody is dual licensed: the model under GPL-3.0 and the user "
        "interface under LGPL-3.0. See the Help menu for both licences.</p>"
        "<p>Stellody reads your music folder and never writes to it. Every "
        "piece of state it keeps lives in its own store.</p>"
        "<hr>"
        "<h3>Open source credits</h3>"
        f"<ul>{_credits_html()}</ul>"
        "<p>Built on the Python and Qt ecosystems, with thanks to their "
        "communities.</p>"
    )


class AboutDialog(NeutralDialog):
    """Identity, licensing and credits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(ABOUT_MIN_WIDTH_PX)
        layout = QVBoxLayout(self)
        badge = _icon_label(self)
        if badge is not None:
            layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        body = QTextBrowser(self)
        body.setOpenExternalLinks(True)
        body.setMinimumHeight(ABOUT_BODY_MIN_HEIGHT_PX)
        body.setHtml(about_html())
        layout.addWidget(body)
        layout.addLayout(close_row(self))
        self.scroller = AutoScroller(body)


def _icon_label(parent: QWidget) -> QLabel | None:
    """The application icon scaled for the About dialog, when it resolves."""
    path = resources.window_icon_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    label = QLabel(parent)
    label.setPixmap(
        pixmap.scaled(
            ABOUT_ICON_PX,
            ABOUT_ICON_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )
    return label
