"""The licence viewer: sized to the text, never cutting it off horizontally."""

from __future__ import annotations

import pathlib

import pytest
from PySide6.QtWidgets import QApplication, QTextBrowser

from stellody.ui import dialogs
from stellody.ui.dialogs import LicenceDialog

WIDE_SCREEN_PX = 4000
NARROW_SCREEN_PX = 400
# A real licence is hard wrapped near this width, so it is what the dialog has
# to fit. A far longer line would be pathological, which the cap exists to stop.
LICENCE_LINE = "x" * 76


@pytest.fixture(scope="session")
def application() -> QApplication:
    """One real QApplication for the whole session. Qt is never mocked."""
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture
def licence(tmp_path: pathlib.Path) -> pathlib.Path:
    """A licence file hard wrapped well beyond a narrow display."""
    path = tmp_path / "LICENCE.txt"
    path.write_text("\n".join([LICENCE_LINE] * 40), encoding="utf-8")
    return path


def test_a_wide_display_takes_the_licences_own_wrapping(
    application: QApplication,
    licence: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dialogs, "_available_width", lambda _dialog: WIDE_SCREEN_PX)
    dialog = LicenceDialog("Licence", licence)
    dialog.show()
    application.processEvents()
    assert dialog._body.lineWrapMode() == QTextBrowser.LineWrapMode.NoWrap
    assert dialog._body.horizontalScrollBar().maximum() == 0
    dialog.close()


def test_a_narrow_display_wraps_rather_than_cutting_lines_off(
    application: QApplication,
    licence: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dialogs, "_available_width", lambda _dialog: NARROW_SCREEN_PX)
    dialog = LicenceDialog("Licence", licence)
    dialog.show()
    application.processEvents()
    assert dialog._body.lineWrapMode() == QTextBrowser.LineWrapMode.WidgetWidth
    assert dialog._body.horizontalScrollBar().maximum() == 0
    dialog.close()


def test_a_missing_licence_explains_itself_rather_than_showing_nothing(
    application: QApplication,
) -> None:
    dialog = LicenceDialog("Licence", None)
    assert "could not be located" in dialog._body.toPlainText()
    dialog.close()


def test_the_licence_reads_itself(
    application: QApplication, licence: pathlib.Path
) -> None:
    """A surface to read through wears the auto-scroll cycle."""
    dialog = LicenceDialog("Licence", licence)
    assert dialog.scroller.timer.isActive()
    dialog.close()
