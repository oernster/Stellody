"""How the guide draws a picture beside its words, for every section of it.

Split out of `guide.py` on 2026-09-13 when the discovery section moved into a
module of its own: both draw pictures the same way, so the one rule for doing it
lives here rather than in either.
"""

from __future__ import annotations

import pathlib

# Bigger than the words around it on purpose. This screen is read to tell one
# picture from another rather than to skim a sentence; the artwork here is
# detailed enough that at body-text size two icons somebody is trying to
# separate read as the same smudge.
INLINE_ICON_PX = 30


def img(path: pathlib.Path | None, px: int = INLINE_ICON_PX) -> str:
    """One bundled icon as an inline image; nothing at all when it is absent.

    Empty rather than a placeholder: the line still reads without its picture
    and a missing asset must never stop the guide opening.

    Centred on the line rather than sat on its baseline, since at this size a
    baseline-aligned picture hangs below the words it leads and reads as a row
    that has slipped.
    """
    if path is None:
        return ""
    return (
        f'<img src="file:///{str(path).replace(chr(92), "/")}" '
        f'width="{px}" height="{px}" style="vertical-align: middle"> '
    )


def row(path: pathlib.Path | None, name: str, text: str) -> str:
    """One control's line, led by the picture its button actually draws."""
    return f"<p>{img(path)}<b>{name}</b>: {text}</p>"
