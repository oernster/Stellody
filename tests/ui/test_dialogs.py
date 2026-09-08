"""The dialogs: the licence viewer sized to its text; what About states."""

from __future__ import annotations

import pathlib
import urllib.parse

import pytest
from PySide6.QtWidgets import QApplication, QTextBrowser

from stellody.infrastructure import catalogue, cover_search, similarity
from stellody.shared import version
from stellody.shared.version import (
    APP_AUTHOR,
    COPYRIGHT_NOTICE,
    COPYRIGHT_YEAR,
)
from stellody.ui import dialogs
from stellody.ui.about_credits import SOURCES
from stellody.ui.dialogs import AboutDialog, LicenceDialog, about_html

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


def test_about_credits_every_service_the_application_asks_anything_of() -> None:
    """Read off the clients rather than off a list somebody maintains.

    A credits box is exactly the thing that goes stale in silence: a source
    added to the code owes an acknowledgement that nothing else would notice
    was missing. So the hosts are taken from the modules that actually open
    the connections; every one of them has to be named.
    """
    hosts = {
        urllib.parse.urlparse(url).hostname
        for module in (catalogue, similarity, cover_search)
        for name, url in vars(module).items()
        if name.endswith("_URL") and isinstance(url, str)
    }
    assert hosts, "the clients name no hosts, so this test would prove nothing"
    body = about_html()
    named = " ".join(name for name, _terms, _purpose in SOURCES)
    for host in hosts:
        # musicbrainz.org and labs.api.listenbrainz.org both reduce to the
        # project's own name, which is what a person is owed rather than a
        # domain: coverartarchive.org is the Cover Art Archive.
        project = host.split(".")[-2]
        assert project.lower() in named.lower().replace(" ", ""), host
    for name, terms, purpose in SOURCES:
        assert name in body
        assert terms in body
        assert purpose in body


def test_about_keeps_the_services_apart_from_the_libraries() -> None:
    """Ruled on 2026-09-07: a different kind of debt, so its own section."""
    body = about_html()
    assert "Open source credits" in body
    assert "Where the information comes from" in body
    assert body.index("Open source credits") < body.index(
        "Where the information comes from"
    )


def test_about_states_the_musicbrainz_terms_that_ask_for_credit() -> None:
    """Genres are supplementary data, which is the half that is not CC0.

    Read from the MusicBrainz data licence page on 2026-09-07: core data is
    CC0 and supplementary data is CC BY-NC-SA 3.0, which asks to be credited
    by name. Written down here so a later tidy of the wording cannot quietly
    drop the licence that actually carries an obligation.
    """
    terms = {name: terms for name, terms, _purpose in SOURCES}
    assert "CC0" in terms["MusicBrainz"]
    assert "CC BY-NC-SA 3.0" in terms["MusicBrainz"]
