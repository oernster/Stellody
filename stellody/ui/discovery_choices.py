"""The Discover dialog's three boxes, as remembered and as written down. FR-D85.

Split out of `discovering.py` when the boxes took it over the line cap. What is
here is everything about the choices that is not drawing them: where each is
kept between openings, how a choice never kept is read and how a run's choices
are said in the diary.
"""

from __future__ import annotations

from typing import Protocol

from stellody.domain.including import Including
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_DISCOVER_COMPILATIONS,
    SETTING_DISCOVER_CREDITS,
    SETTING_DISCOVER_MIXES,
    SETTING_DISCOVER_SERIES,
    TRUE,
)

# What a run took in beyond the albums, for the diary line saying it started.
TOOK_IN = "; with {parts}"
CREDITS_NOTED = "artists on compilations"
SERIES_NOTED = "other volumes of series"
NO_MIXES_NOTED = "no DJ mixes"
PARTS_JOINED = ", "


class Settings(Protocol):
    """The two things the choices need of the settings store."""

    def get_setting(self, key: str, default: str = "") -> str: ...

    def set_setting(self, key: str, value: str) -> None: ...


def included_from(settings: Settings) -> Including:
    """The three boxes as they were last left. FR-D51, FR-D85.

    A choice never written takes the one box it split from, which meant both
    artists and series; DJ mixes start offered, as FR-D80 asked.
    """
    old = settings.get_setting(SETTING_DISCOVER_COMPILATIONS, FALSE)

    def read(key: str, otherwise: str) -> bool:
        return settings.get_setting(key, otherwise) == TRUE

    return Including(
        credits=read(SETTING_DISCOVER_CREDITS, old),
        series=read(SETTING_DISCOVER_SERIES, old),
        mixes=read(SETTING_DISCOVER_MIXES, TRUE),
    )


def remember_including(settings: Settings, including: Including) -> None:
    """Keep the boxes as they were left, so the dialog opens that way."""
    for key, ticked in (
        (SETTING_DISCOVER_CREDITS, including.credits),
        (SETTING_DISCOVER_SERIES, including.series),
        (SETTING_DISCOVER_MIXES, including.mixes),
    ):
        settings.set_setting(key, TRUE if ticked else FALSE)


def widened_by(including: Including) -> str:
    """What a run took in, as the end of the diary line; empty for nothing."""
    parts = [
        words
        for words, said in (
            (CREDITS_NOTED, including.credits),
            (SERIES_NOTED, including.series),
            (NO_MIXES_NOTED, not including.mixes),
        )
        if said
    ]
    return TOOK_IN.format(parts=PARTS_JOINED.join(parts)) if parts else ""
