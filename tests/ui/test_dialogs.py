"""The dialogs: the licence viewer sized to its text; what About states."""

from __future__ import annotations

import pathlib

import pytest
from PySide6.QtWidgets import QApplication, QTextBrowser

from stellody.shared import version
from stellody.shared.version import (
    APP_AUTHOR,
    COPYRIGHT_NOTICE,
    COPYRIGHT_YEAR,
)
from stellody.ui import dialogs
from stellody.ui.dialogs import AboutDialog, LicenceDialog

WIDE_SCREEN_PX = 4000
NARROW_SCREEN_PX = 400
# A real licence is hard wrapped near this width, so it is what the dialog has
# to fit. A far longer line would be pathological, which the cap exists to stop.
LICENCE_LINE = "x" * 76


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


def test_the_licence_is_measured_in_the_font_it_will_be_drawn_in(
    application: QApplication,
    licence: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression: a fresh widget carries the fallback font until polish.

    Sizing the dialog before the stylesheet reaches the body measured a
    proportional face and drew a monospace one, so the right of every line fell
    off the moment it was shown.
    """
    monkeypatch.setattr(dialogs, "_available_width", lambda _dialog: WIDE_SCREEN_PX)
    previous = application.styleSheet()
    application.setStyleSheet(
        "QTextBrowser { font-family: 'Consolas', monospace; font-size: 20px; }"
    )
    try:
        dialog = LicenceDialog("Licence", licence)
        assert dialog._body.font().family() == "Consolas"
        dialog.show()
        application.processEvents()
        assert dialog._body.horizontalScrollBar().maximum() == 0
        dialog.close()
    finally:
        application.setStyleSheet(previous)


def test_about_states_the_copyright_with_its_symbol_and_year(
    application: QApplication,
) -> None:
    """The year is written down rather than worked out, so it cannot drift."""
    body = dialogs.about_html()
    assert COPYRIGHT_NOTICE in body
    assert "©" in body, "the symbol itself, not the word or (c)"
    assert COPYRIGHT_YEAR in body
    assert APP_AUTHOR in COPYRIGHT_NOTICE


def test_the_copyright_year_is_written_down_not_worked_out() -> None:
    """A year that moves with the machine's date is a claim about nothing.

    Two machines with different clocks would otherwise disagree about the same
    build, so the module that holds the year is read to prove it asks nothing.
    """
    source = pathlib.Path(version.__file__).read_text(encoding="utf-8")
    assert COPYRIGHT_YEAR.isdigit()
    for reach in ("datetime", "date.today", "time.", "now()"):
        assert reach not in source, f"the year must not come from {reach}"


def test_the_about_dialog_draws_that_notice(application: QApplication) -> None:
    """Built from the same html, so the dialog cannot quietly say something else."""
    dialog = AboutDialog()
    shown = dialog.findChild(QTextBrowser)
    assert shown is not None
    assert COPYRIGHT_NOTICE in shown.toPlainText()
