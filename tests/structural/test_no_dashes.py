"""No dash-like character reaches a screen, a document or a comment.

Oliver's standing rule, restated on 2026-09-09 after an em dash was seen in a
title bar during a discovery run: there are to be none, anywhere, ever. The
rule had been held by habit alone, which is exactly the arrangement that lets
one through and then argues about whether that file counted.

So it is a gate rather than a habit. It reads every file the repository ships
or writes, source, documents and site alike, then fails on any of the ten
characters below. A hyphen-minus is untouched: it is the character that is
allowed; every rewrite goes towards it or towards a comma, a colon, a
semicolon or a full stop.

What this CANNOT see, said plainly so nobody mistakes the guard for a proof:
a dash arriving in data at run time, out of a music tag or a catalogue answer,
is not in any file here and no test of the tree will ever catch it. This
governs what Stellody says; what somebody else's metadata says is a separate
question with a separate answer.
"""

from __future__ import annotations

import pathlib

import pytest
from conftest import REPO_ROOT, relative

# Every dash-like character, held as a CODE POINT rather than as itself, so
# this file obeys the rule it enforces and is not the one exception to it. A
# failure names the character instead of printing a glyph indistinguishable
# from the one that is allowed. The hyphen-minus U+002D is deliberately absent:
# that one is the point.
FORBIDDEN = {
    chr(0x2010): "U+2010 HYPHEN",
    chr(0x2011): "U+2011 NON BREAKING HYPHEN",
    chr(0x2012): "U+2012 FIGURE DASH",
    chr(0x2013): "U+2013 EN DASH",
    chr(0x2014): "U+2014 EM DASH",
    chr(0x2015): "U+2015 HORIZONTAL BAR",
    chr(0x2212): "U+2212 MINUS SIGN",
    chr(0x02D7): "U+02D7 MODIFIER LETTER MINUS SIGN",
    chr(0xFE58): "U+FE58 SMALL EM DASH",
    chr(0xFF0D): "U+FF0D FULLWIDTH HYPHEN MINUS",
}

# Where the rule applies: everything written by hand or shipped to a reader.
SEARCHED = ("*.py", "*.md", "*.html", "*.css", "*.js", "*.json", "*.ps1", "*.sh")

# Directories holding nothing anybody here wrote.
SKIPPED = {".git", "venv", "__pycache__", "node_modules", "build", "dist"}


def _searchable() -> list[pathlib.Path]:
    """Every file the rule governs, newest arrivals included."""
    found: list[pathlib.Path] = []
    for pattern in SEARCHED:
        for path in REPO_ROOT.rglob(pattern):
            if SKIPPED.isdisjoint(part for part in path.parts):
                found.append(path)
    return sorted(set(found))


def offences(text: str) -> list[str]:
    """Every forbidden character in that text, named rather than printed."""
    return [name for character, name in FORBIDDEN.items() if character in text]


def test_no_file_carries_a_dash_like_character() -> None:
    """Not one of them, in any file, of any kind."""
    guilty: list[str] = []
    for path in _searchable():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name in offences(text):
            guilty.append(f"{relative(path)}: {name}")
    assert not guilty, "dash-like characters found:\n" + "\n".join(guilty)


def test_the_guard_bites() -> None:
    """Planted, because a guard never seen to fail is not yet a guard.

    Every forbidden character is planted in turn, since a list that names ten
    and detects one would pass the test above on the day it mattered.
    """
    for character, name in FORBIDDEN.items():
        assert offences(f"a{character}b") == [name], f"{name} went unnoticed"
    assert offences("a-b") == [], "the ordinary hyphen must stay allowed"


@pytest.mark.parametrize("character", sorted(FORBIDDEN))
def test_a_planted_file_is_actually_found(
    character: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The walk finds a real file, rather than only the string check working."""
    monkeypatch.setattr("test_no_dashes.REPO_ROOT", tmp_path)
    planted = tmp_path / "planted.md"
    planted.write_text(f"a{character}b", encoding="utf-8")
    assert planted in _searchable(), "the walk missed a file it governs"
    assert offences(planted.read_text(encoding="utf-8")), "the check missed it"
