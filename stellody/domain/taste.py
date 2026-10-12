"""Taste profiles: named sets of genres, kept so a selection can be put back.

`DISCOVERY.md` FR-D87 to FR-D93. The rules about them are here, with nothing
installed: what makes two selections the same profile, what makes two names
the same name, the order the list shows them in and what saving or deleting
leaves behind. Where they are kept is another layer's business; so is the
dialog that offers them.

**A selection is a set, not a sequence.** Ticking Jazz then Rock is the same
choice as Rock then Jazz, so profiles are compared by the genres they hold
whatever the order (FR-D90).

**A name is compared ignoring case and the space around it.** "Jazz" and
" jazz " are one profile, so saving the second replaces the first once that is
confirmed (FR-D91); the list orders them the same way (FR-D88).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TasteProfile:
    """One named selection of genres."""

    name: str
    genres: tuple[str, ...]


def usable_name(text: str) -> str | None:
    """The name typed, trimmed; None where nothing is left once trimmed."""
    trimmed = text.strip()
    return trimmed or None


def _key(name: str) -> str:
    """What two names are compared by."""
    return name.strip().casefold()


def ordered(profiles: tuple[TasteProfile, ...]) -> tuple[TasteProfile, ...]:
    """The profiles alphabetically, ignoring case. FR-D88."""
    return tuple(sorted(profiles, key=lambda profile: _key(profile.name)))


def holding(
    profiles: tuple[TasteProfile, ...], genres: tuple[str, ...]
) -> TasteProfile | None:
    """The profile holding exactly these genres, in any order; else None."""
    wanted = frozenset(genres)
    for profile in profiles:
        if frozenset(profile.genres) == wanted:
            return profile
    return None


def named(profiles: tuple[TasteProfile, ...], name: str) -> TasteProfile | None:
    """The profile going by this name, ignoring case; else None."""
    for profile in profiles:
        if _key(profile.name) == _key(name):
            return profile
    return None


def saved(
    profiles: tuple[TasteProfile, ...], name: str, genres: tuple[str, ...]
) -> tuple[TasteProfile, ...]:
    """The profiles with this one saved, replacing any going by the same name."""
    kept = without(profiles, name)
    return ordered((*kept, TasteProfile(name=name.strip(), genres=genres)))


def without(profiles: tuple[TasteProfile, ...], name: str) -> tuple[TasteProfile, ...]:
    """The profiles with the one going by this name taken out."""
    return tuple(profile for profile in profiles if _key(profile.name) != _key(name))
