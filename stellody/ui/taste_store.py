"""Where taste profiles are kept: one setting, read back every time. FR-D93.

Kept as JSON, a list of objects holding `name`, `genres`, `including` and
`years`, so the store holds a line a person could read and genre names that
contain the folds' separator cannot split a profile in two. A profile saved
before profiles held the Include boxes and the years reads with the defaults.

Read forgivingly: text that is not a list of profiles reads as none, never as
an error, since a dialog that will not open over a damaged setting costs a
whole run while an empty list costs a choice. An entry missing its name or
holding something malformed is passed over and the rest are kept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from stellody.application.ports import SettingsStore
from stellody.domain.including import OWN_ALBUMS, Including
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.taste import TasteProfile, ordered, usable_name
from stellody.ui.settings_keys import SETTING_TASTE_PROFILES

NAME = "name"
GENRES = "genres"
INCLUDING = "including"
YEARS = "years"
# The fields of the two values a profile holds besides its genres, named once.
BOXES = ("credits", "series", "mixes")
BOUNDS = ("earliest", "latest")


def _including(stored: object) -> Including | None:
    """The Include boxes as stored; the defaults where none were; else None."""
    if stored is None:
        return OWN_ALBUMS
    if not isinstance(stored, dict):
        return None
    boxes = {key: stored.get(key, getattr(OWN_ALBUMS, key)) for key in BOXES}
    if not all(isinstance(value, bool) for value in boxes.values()):
        return None
    return Including(**boxes)


def _years(stored: object) -> ReleaseYears | None:
    """The years as stored; every year where none were; else None."""
    if stored is None:
        return ANY_YEAR
    if not isinstance(stored, dict):
        return None
    bounds = [stored.get(key) for key in BOUNDS]
    if not all(bound is None or type(bound) is int for bound in bounds):
        return None
    try:
        return ReleaseYears(*bounds)
    except ValueError:
        return None


def _profile(entry: object) -> TasteProfile | None:
    """One stored entry as a profile; None where it is not one.

    A profile kept before profiles held the Include boxes and the years reads
    with the dialog's defaults for both, rather than being lost.
    """
    if not isinstance(entry, dict):
        return None
    name, genres = entry.get(NAME), entry.get(GENRES)
    if not isinstance(name, str) or usable_name(name) is None:
        return None
    if not isinstance(genres, list) or not all(isinstance(g, str) for g in genres):
        return None
    including, years = _including(entry.get(INCLUDING)), _years(entry.get(YEARS))
    if including is None or years is None:
        return None
    return TasteProfile(name.strip(), tuple(genres), including, years)


def _stored(profile: TasteProfile) -> dict:
    """One profile as the setting holds it."""
    return {
        NAME: profile.name,
        GENRES: list(profile.genres),
        INCLUDING: {key: getattr(profile.including, key) for key in BOXES},
        YEARS: {key: getattr(profile.years, key) for key in BOUNDS},
    }


@dataclass(frozen=True, slots=True)
class TasteStore:
    """The saved profiles, over the application's settings store."""

    settings: SettingsStore

    def profiles(self) -> tuple[TasteProfile, ...]:
        """Every readable profile, in the list's order."""
        try:
            stored = json.loads(self.settings.get_setting(SETTING_TASTE_PROFILES, ""))
        except ValueError:
            return ()
        if not isinstance(stored, list):
            return ()
        found = (_profile(entry) for entry in stored)
        return ordered(tuple(profile for profile in found if profile is not None))

    def keep(self, profiles: tuple[TasteProfile, ...]) -> None:
        """Write these profiles as the whole of what is saved."""
        self.settings.set_setting(
            SETTING_TASTE_PROFILES,
            json.dumps([_stored(profile) for profile in profiles]),
        )
