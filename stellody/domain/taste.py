"""Taste profiles: named selections, kept so a whole selection can be put back.

`DISCOVERY.md` FR-D87 to FR-D93. A profile holds everything the Discover
dialog asks: the genres ticked, the three Include boxes and the years (Oliver's
ruling, 2026-10-12, amending one that held the genres alone). The rules about
them are here, with nothing installed: what makes two selections the same,
what makes two names the same name, the order the list shows them in and what
saving or deleting leaves behind. Where they are kept is another layer's
business; so is the dialog that offers them.

**Genres are a set, not a sequence.** Ticking Jazz then Rock is the same
choice as Rock then Jazz, so the genres are compared whatever their order; the
Include boxes and the years must match as well (FR-D90). A genre filter asks
about genres and years, never what to include, so what it offers is held by
any profile with the same genres and years, whatever that profile includes
(FR-D98, FR-D99).

**A name is compared ignoring case and the space around it.** "Jazz" and
" jazz " are one profile, so saving the second replaces the first once that is
confirmed (FR-D91); the list orders them the same way (FR-D88).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from stellody.domain.including import OWN_ALBUMS, Including
from stellody.domain.release_years import ANY_YEAR, ReleaseYears


@dataclass(frozen=True, slots=True)
class TasteProfile:
    """One named selection: genres, what else to include and which years."""

    name: str
    genres: tuple[str, ...]
    including: Including = OWN_ALBUMS
    years: ReleaseYears = ANY_YEAR


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


def _same_genres(one: tuple[str, ...], other: tuple[str, ...]) -> bool:
    """Whether two lists of genres are the same choice, whatever the order."""
    return frozenset(one) == frozenset(other)


def _same_selection(one: TasteProfile, other: TasteProfile) -> bool:
    """Whether two profiles hold the same choices, whatever they are called."""
    return (
        _same_genres(one.genres, other.genres)
        and one.including == other.including
        and one.years == other.years
    )


def holding(
    profiles: tuple[TasteProfile, ...], wanted: TasteProfile
) -> TasteProfile | None:
    """The saved profile holding exactly this selection; else None."""
    for profile in profiles:
        if _same_selection(profile, wanted):
            return profile
    return None


def holding_filter(
    profiles: tuple[TasteProfile, ...], genres: tuple[str, ...], years: ReleaseYears
) -> TasteProfile | None:
    """A saved profile holding exactly these genres and years, whatever it
    includes; else None. A genre filter asks nothing about what to include.
    FR-D98."""
    for profile in profiles:
        if _same_genres(profile.genres, genres) and profile.years == years:
            return profile
    return None


def named(profiles: tuple[TasteProfile, ...], name: str) -> TasteProfile | None:
    """The profile going by this name, ignoring case; else None."""
    for profile in profiles:
        if _key(profile.name) == _key(name):
            return profile
    return None


def saved(
    profiles: tuple[TasteProfile, ...], name: str, selection: TasteProfile
) -> tuple[TasteProfile, ...]:
    """The profiles with this selection saved under the name, replacing any
    going by the same name."""
    kept = without(profiles, name)
    return ordered((*kept, replace(selection, name=name.strip())))


def without(profiles: tuple[TasteProfile, ...], name: str) -> tuple[TasteProfile, ...]:
    """The profiles with the one going by this name taken out."""
    return tuple(profile for profile in profiles if _key(profile.name) != _key(name))
