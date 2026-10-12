"""Where taste profiles are kept: one setting, read back every time. FR-D93.

Kept as JSON, a list of `{"name": ..., "genres": [...]}`, so the store holds a
line a person could read and genre names that contain the folds' separator
cannot split a profile in two. Read forgivingly: text that is not a list of
profiles reads as none, never as an error, since a dialog that will not open
over a damaged setting costs a whole run while an empty list costs a choice.
An entry missing its name or holding something other than genre names is
passed over and the rest are kept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from stellody.application.ports import SettingsStore
from stellody.domain.taste import TasteProfile, ordered, usable_name
from stellody.ui.settings_keys import SETTING_TASTE_PROFILES

NAME = "name"
GENRES = "genres"


def _profile(entry: object) -> TasteProfile | None:
    """One stored entry as a profile; None where it is not one."""
    if not isinstance(entry, dict):
        return None
    name, genres = entry.get(NAME), entry.get(GENRES)
    if not isinstance(name, str) or usable_name(name) is None:
        return None
    if not isinstance(genres, list) or not all(isinstance(g, str) for g in genres):
        return None
    return TasteProfile(name=name.strip(), genres=tuple(genres))


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
            json.dumps(
                [
                    {NAME: profile.name, GENRES: list(profile.genres)}
                    for profile in profiles
                ]
            ),
        )
