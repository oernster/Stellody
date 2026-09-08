"""The two sentence chores every report on this screen has.

Both were written out three times over: `health`, `scan_summary` and the run
shortfall each needed a title made safe for markup and a count given the word
that suits it. Three identical bodies are three chances for one of them to
drift, so they live here once and are imported rather than repeated.

Neither touches a widget, so what a report says can be checked without a
screen; that is the same reason the reports themselves are built as text apart
from the dialogs that show them.
"""

from __future__ import annotations

# What separates the singular from the plural. Named rather than written into
# the comparison, since it is a fact about the English and not arithmetic.
ONE = 1


def escaped(value: str) -> str:
    """Make a title or a filename safe to place inside a report's markup.

    A library holds whatever somebody's tags hold, so an album called `<b>`
    reaches a report exactly as typed. Rendering it as markup would let a tag
    change the shape of the page it is being listed on.
    """
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plural(count: int, one: str, many: str) -> str:
    """A count with the word that suits it, so nothing reads as 1 albums."""
    return f"{count} {one if count == ONE else many}"
