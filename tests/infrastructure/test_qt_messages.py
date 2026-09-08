"""Qt's own complaints reaching the diary, without taking the console with them.

The handler is installed for real and Qt is asked to write a message, rather
than the function being called directly with made-up arguments: what is being
checked is that Qt's messages arrive here at all, which calling it by hand
would assume rather than show.
"""

from __future__ import annotations

import pathlib

import pytest
from PySide6.QtCore import QtMsgType, qInstallMessageHandler, qWarning

from stellody.infrastructure import diary, qt_messages


@pytest.fixture
def diary_at(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """A diary somewhere a test may write; Qt's handler put back after."""
    where = tmp_path / "diary.log"
    monkeypatch.setattr(diary, "location", lambda: where)
    before = qInstallMessageHandler(None)
    yield where
    qInstallMessageHandler(before)


def said(where: pathlib.Path) -> str:
    """Everything the diary holds; empty where it holds nothing."""
    return where.read_text(encoding="utf-8") if where.exists() else ""


class TestWhatReachesTheDiary:
    def test_a_warning_qt_writes_is_written_down(self, diary_at) -> None:
        """The reported case: a message seen once and impossible to place."""
        qt_messages.listen()
        qWarning("device not open")
        assert "device not open" in said(diary_at)

    def test_the_line_says_which_kind_of_message_it_was(self, diary_at) -> None:
        """A warning and a fatal read alike otherwise."""
        qt_messages.listen()
        qWarning("something")
        assert "Qt warning" in said(diary_at)

    def test_the_line_says_which_thread_was_running(self, diary_at) -> None:
        """Half the question with these: the run has a thread of its own."""
        qt_messages.listen()
        qWarning("something")
        assert "on MainThread" in said(diary_at)

    def test_a_kind_with_no_name_is_still_written_down(self, diary_at) -> None:
        """A message nobody anticipated is the one worth keeping."""
        qt_messages.written(object(), None, "from nowhere")
        assert "Qt message" in said(diary_at)
        assert "from nowhere" in said(diary_at)


class TestWhatItDoesNotBreak:
    def test_the_console_still_gets_the_message(self, diary_at, capsys) -> None:
        """Qt's own handler is replaced by installing one, measured 2026-09-08.

        Whoever runs from source reads these on the console, so a diagnostic
        that quietly took them away would be a step backwards.
        """
        qt_messages.listen()
        qWarning("still spoken aloud")
        assert "still spoken aloud" in capsys.readouterr().err

    def test_a_handler_already_in_place_is_still_called(self, diary_at) -> None:
        """Whatever was handling these keeps handling them."""
        heard: list[str] = []
        qInstallMessageHandler(lambda _kind, _context, message: heard.append(message))
        qt_messages.listen()
        qWarning("passed along")
        assert heard == ["passed along"]

    def test_a_diary_that_fails_costs_the_line_and_nothing_else(
        self, diary_at, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """This runs on every message Qt writes, including during a crash."""

        def refuse(_message: str) -> None:
            raise OSError("no room")

        monkeypatch.setattr(qt_messages.diary, "note", refuse)
        qt_messages.written(QtMsgType.QtWarningMsg, None, "unwritable")

    def test_a_console_that_will_not_take_it_is_not_an_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A packaged copy has no console; a closed one raises on write."""

        class Closed:
            def write(self, _text: str) -> None:
                raise ValueError("closed")

            def flush(self) -> None:
                """Nothing to do."""

        monkeypatch.setattr(qt_messages.sys, "stderr", Closed())
        qt_messages._said_aloud("into the void")


class TestWhereItCameFrom:
    def test_a_place_qt_named_is_carried_through(self, diary_at) -> None:
        """Qt fills these in for code built with them."""

        class Somewhere:
            file = "widget.cpp"
            line = 42

        qt_messages.written(QtMsgType.QtWarningMsg, Somewhere(), "there")
        assert "at widget.cpp:42" in said(diary_at)

    def test_no_place_is_left_out_rather_than_padded(self, diary_at) -> None:
        """The ordinary case: a warning from inside Qt's network stack."""

        class Nowhere:
            file = None
            line = 0

        qt_messages.written(QtMsgType.QtWarningMsg, Nowhere(), "here")
        assert " at " not in said(diary_at)
