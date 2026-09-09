"""How much room the results screen takes and how that room is divided.

Arithmetic only: nothing here builds a widget or reads a screen. It is handed
a room and answers a size, a count of columns and which source artist belongs
in which column. That is what lets a size be tested at widths no machine
running the suite actually has, which matters here because the offscreen
platform reports an 800 square screen and every interesting case is wider.

**A share of the screen, floored and capped.** The dialog opened at a fixed
700 by 560, which on a wide monitor is a column of text somebody scrolls for
minutes while the room to show it sits unused either side. It takes a share of
the screen instead, so the same request means the same proportion of a laptop
panel and of a wide monitor.

The cap is Oliver's ruling of 2026-09-08: no bigger than a 13 inch display can
show. A share alone gives a 3096 pixel dialog on a 3440 monitor, which is a
window nobody can read across in one go and a shape that cannot be checked on
the machines this is meant to run on. The floor stays what it always was, so a
small screen still gets a dialog wide enough for an album title under an
artist under a heading.

**The columns follow the width rather than being counted out.** How many fit
is a division: the room divided by what one column has to be to stay readable.
That width is not a number of its own; it is the ceiling divided by the number
of columns a 13 inch display is meant to show, so the two cannot drift apart.
One column is the answer at the floor, three at the cap.

**The pages follow the height the same way.** Three columns of a whole library
is three lists nobody reaches the end of, so the answer is dealt a page at a
time: a page fills every one of its columns to a depth taken from the height,
exactly as the columns come from the width, so a laptop panel gets a shorter
page rather than the same page with more in it.

A column holding an artist taller than that depth scrolls. That is not the
compromise it reads as: measured from Oliver's own library on 2026-09-09, an
artist runs from 1 row to 109 against a column of 30, so a page that refused
to overflow a column could not be filled at all and drew one column where it
should have drawn three.
"""

from __future__ import annotations

from PySide6.QtCore import QSize

from stellody.domain.discovery import Gaps

# The floor, not the size it opens at. Wide enough for an album title under an
# artist under a heading without the titles wrapping; the same measurement the
# discovery dialog is built to.
DIALOG_WIDTH_PX = 700
DIALOG_HEIGHT_PX = 560
# What it opens at before the cap, as a share of the screen it opens on. Nine
# tenths rather than everything, so the window underneath still shows at the
# edges and the screen does not read as having been taken over by a dialog.
SCREEN_SHARE = 0.9
# What a 13 inch display is capable of, which is as big as this may open
# however much room it is given. Ruled by Oliver on 2026-09-08: a dialog is
# checked on the smallest screen it has to work on, so one that only fits a
# wide monitor is one nobody can vouch for.
THIRTEEN_INCH_WIDTH_PX = 1920
THIRTEEN_INCH_HEIGHT_PX = 1080
# How many columns a 13 inch display is meant to show. Ruled by Oliver on
# 2026-09-08, having seen the first two-column screen and asked for three.
#
# The width of a column follows from it rather than the other way round, so
# there is one number to argue with instead of two that can disagree.
#
# Measured off that screen shot, which is 1919 pixels wide for a 1920 pixel
# dialog and so is very nearly one to one: an album row of 47 characters draws
# 258 pixels and one of 49 characters draws 292, which is between 5.5 and 6.0
# pixels a character. The longest row this library produces is 75 characters,
# "Jools Holland & His Rhythm & Blues Orchestra (15 albums, 3 similar
# artists)", so about 450 pixels drawn. A third of the ceiling is 640, which
# holds it with room to spare.
#
# It could not be measured in the suite: the offscreen platform reports zero
# font families, so every family at every size resolves to one fallback and
# draws the same width. A pixel taken from there would be a pixel of nothing,
# which is why the figures above come from a real screen.
COLUMNS_AT_THE_CEILING = 3
COLUMN_PX = THIRTEEN_INCH_WIDTH_PX // COLUMNS_AT_THE_CEILING
# What the dialog spends on everything that is not the list: the title, the
# genres it looked in, the three line key, the strip that says what is being
# asked, the pager and the row of controls. It does not grow with the window,
# so it is taken off the height once rather than scaled.
#
# STATED RATHER THAN MEASURED; it cannot be measured here either, since the
# platform reports zero font families, so every label draws at the height of
# one fallback face. Being wrong costs a page with room to spare at the foot
# or a column that scrolls a little, which is what the whole answer did before
# it was paged at all. It is never an error, so a figure checked on a real
# screen is the right way to correct it.
FURNITURE_PX = 300
# How many rows a column shows at the ceiling. The same shape of decision as
# the columns above: the number a 13 inch display is meant to hold is stated,
# and what one row costs follows from it, so there is one number to argue with
# rather than two that can disagree.
ROWS_AT_THE_CEILING = 30
ROW_PX = (THIRTEEN_INCH_HEIGHT_PX - FURNITURE_PX) // ROWS_AT_THE_CEILING


def _between(room: int, share: float, floor: int, ceiling: int) -> int:
    """That share of the room, never under the floor nor over the ceiling.

    The floor is applied last, so a ceiling somebody sets under it still
    leaves a dialog somebody can read rather than a sliver.
    """
    return max(floor, min(int(room * share), ceiling))


def opening_size(room: QSize) -> QSize:
    """How big the dialog opens in a screen offering this much room.

    `room` is what a WHOLE window has to sit in rather than what its content
    gets, which is why the share is under one: asking for all of it would ask
    for a window wider than the screen, exactly as `geometry.fit_on_screen`
    records against the main window.
    """
    return QSize(
        _between(room.width(), SCREEN_SHARE, DIALOG_WIDTH_PX, THIRTEEN_INCH_WIDTH_PX),
        _between(
            room.height(), SCREEN_SHARE, DIALOG_HEIGHT_PX, THIRTEEN_INCH_HEIGHT_PX
        ),
    )


def columns_for(width: int) -> int:
    """How many readable columns fit across a dialog this wide.

    Never none: a dialog narrower than one column still shows its answer, in
    the one column it has room for.
    """
    return max(1, width // COLUMN_PX)


def rows_for(height: int) -> int:
    """How many rows a column can show in a dialog this tall.

    Never none, for the reason `columns_for` is never none: a dialog too short
    to hold a row still has to show its answer, so it shows one and scrolls,
    which is what every column did before there were pages at all.
    """
    return max(1, (height - FURNITURE_PX) // ROW_PX)


def height_of(found: Gaps) -> int:
    """How many rows a source artist occupies once it is opened.

    The artist's own row plus one for each album and each candidate under it,
    since the tree opens one deep and that is what the eye measures. What is
    under a candidate does not count: nothing is fetched until somebody opens
    it, so it is not on screen when the columns are dealt.
    """
    return 1 + len(found.albums) + len(found.artists)


def dealt_into_columns(
    gaps: tuple[Gaps, ...], columns: int
) -> tuple[tuple[int, ...], ...]:
    """Which source artists go in which column, as places in what was given.

    Each artist goes to whichever column is shortest at the time, so the order
    down a column is still the order the run answered in. Dealt by height
    rather than in equal counts, since one artist can carry fifteen albums
    while the next carries one: a count-by-count fill would leave one column
    twice the length of another. The same rule the genre grid deals its groups
    by.

    Answers places rather than the artists themselves, so a caller can still
    say what it holds in the order it was handed them.
    """
    dealt: list[list[int]] = [[] for _ in range(columns)]
    heights = [0] * columns
    for at, found in enumerate(gaps):
        into = _shortest(heights)
        dealt[into].append(at)
        heights[into] += height_of(found)
    return tuple(tuple(column) for column in dealt)


def _shortest(heights: list[int]) -> int:
    """Which column is shortest at the moment, by the earliest where two tie.

    Its own name because two callers make the same choice, one placing an
    artist inside a page and one asking whether a page still has room. A page
    decided by one rule and dealt by another would put an artist somewhere the
    page had not counted on.
    """
    return heights.index(min(heights))


def paged(
    gaps: tuple[Gaps, ...], columns: int, rows: int
) -> tuple[tuple[Gaps, ...], ...]:
    """The artists split into pages, each page filling every one of its columns.

    A page takes artists until EVERY column has been filled to its depth, then
    a new page starts. Since the choice of column is the one
    `dealt_into_columns` will make over the same artists in the same order,
    the page it fills is the page it counted.

    **Every page carries every column, save the tail of the last one.** Ruled
    by Oliver on 2026-09-09 against the first paged run over his whole library,
    where some pages drew three columns and others drew one.

    The cause was the rule this replaces, which ended a page as soon as the
    next artist would not fit in the shortest column. Measured from that run's
    own answer: 215 artists whose heights run from 1 row to 109, with a median
    of 23 against a column of 30. An artist taller than a column is the
    ORDINARY case in a real library rather than the exception, so a rule that
    never lets one overflow cannot be satisfied and degenerates into pages of
    one artist. Filling every column instead means a column holding a tall
    artist scrolls, which is one artist's worth of scrolling rather than the
    library's.

    Always at least one page, even an empty one: a run that found nobody must
    still be a screen rather than nothing.
    """
    pages: list[tuple[Gaps, ...]] = []
    page: list[Gaps] = []
    heights = [0] * columns
    for found in gaps:
        if page and heights[_shortest(heights)] >= rows:
            pages.append(tuple(page))
            page, heights = [], [0] * columns
        page.append(found)
        heights[_shortest(heights)] += height_of(found)
    if page:
        pages.append(tuple(page))
    return tuple(pages) or ((),)
