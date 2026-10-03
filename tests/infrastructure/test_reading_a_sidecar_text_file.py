"""Reading a cue sheet written in whichever encoding its ripper chose.

Some rippers write UTF-16 with a byte order mark. Read by the byte encodings
alone, the last of which accepts anything, such a sheet came back as text with
a nul between every letter: no command in it matched, so the album played as
one long track and nothing said why.
"""

from __future__ import annotations

import pathlib

import pytest

from stellody.infrastructure.textfile import SidecarTextReader

SHEET = (
    'PERFORMER "Björk"\n'
    'TITLE "Début"\n'
    'FILE "whole.flac" WAVE\n'
    "  TRACK 01 AUDIO\n"
    '    TITLE "Human Behaviour"\n'
    "    INDEX 01 00:00:00\n"
)


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_a_utf16_sheet_with_its_byte_order_mark_reads_as_written(
    tmp_path: pathlib.Path, encoding: str
) -> None:
    sheet = tmp_path / "whole.cue"
    sheet.write_bytes("﻿".encode(encoding) + SHEET.encode(encoding))
    assert SidecarTextReader().read(str(sheet)) == SHEET


def test_a_utf8_sheet_still_reads_as_written(tmp_path: pathlib.Path) -> None:
    sheet = tmp_path / "whole.cue"
    sheet.write_text(SHEET, encoding="utf-8")
    assert SidecarTextReader().read(str(sheet)) == SHEET


def test_a_cp1252_sheet_still_reads_as_written(tmp_path: pathlib.Path) -> None:
    sheet = tmp_path / "whole.cue"
    sheet.write_bytes(SHEET.encode("cp1252"))
    assert SidecarTextReader().read(str(sheet)) == SHEET


def test_a_sheet_that_is_not_there_is_nothing(tmp_path: pathlib.Path) -> None:
    assert SidecarTextReader().read(str(tmp_path / "absent.cue")) is None
