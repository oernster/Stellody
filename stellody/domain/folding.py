"""One album is not always one folder: what a folder holds; how folders join.

The group a scan accumulates lives here beside the rule that folds two of them
into one, because the two are the same idea seen twice: a group is a pile of
tracks that answer to one name; folding is what happens when two piles turn
out to answer to the same one.

**Measured on the reference library, which is why this exists.** An album's
audio sits under Compilations while the bonus videos belonging to it sit under
the artist; nine separate single folders each carry one track tagged with one
album name. Kept as folders, each is a tile of its own, so the library shows
several albums with one name, one cover and no way to tell which is which.

**The cost, stated rather than discovered later.** Two recordings of one work,
tagged alike, now become one album and share a cover, a rating and any accepted
correction. Keeping every such collision apart was the previous rule and it is
what these three cases paid for. The owner chose this way round.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.ordering import TrackCandidate
from stellody.domain.text import comparison_key


def most_common(values: list[str]) -> str:
    """The most frequent non-empty value, ties broken alphabetically."""
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda name: (counts[name], name))


@dataclass(slots=True)
class Group:
    """One album's worth of entries, accumulated by folder."""

    base_name: str
    parent_name: str
    candidates: list[TrackCandidate]
    albums: list[str]
    artists: list[str]
    dates: list[str]
    genres: list[str]
    tagged_artists: int
    disc_conflicts: list[str]
    # Where in `candidates` a folder calling itself a bonus disc landed without
    # saying which disc it is.
    bonus_positions: list[int]


def merge_key(group: Group) -> tuple[str, str] | None:
    """What two folders must agree on to be one album; None where tags are silent.

    The date is deliberately left out. One album's parts routinely disagree
    about it: measured on the reference library, an album's audio is dated 2008
    where the video track beside it says 2009; both are right about their
    own release. Keying on the year would leave those two apart, which is the
    whole fault this exists to remove.

    A group whose tags name no album or no album artist is never folded. Its
    identity falls back to the folder it was found in, while folder names collide
    across a library for reasons that say nothing about the music: two parents
    can both hold a folder called Live.
    """
    album = most_common(group.albums)
    artist = most_common(group.artists)
    if not album or not artist:
        return None
    return (comparison_key(artist), comparison_key(album))


def absorb(into: Group, other: Group) -> None:
    """Take one folder's entries into another's group.

    The bonus positions are indexes into `candidates`, so they move by however
    many candidates are already there. Getting that wrong would mark the wrong
    tracks as a bonus disc, silently and in the middle of somebody's album.
    """
    moved = len(into.candidates)
    into.bonus_positions.extend(moved + position for position in other.bonus_positions)
    into.candidates.extend(other.candidates)
    into.albums.extend(other.albums)
    into.artists.extend(other.artists)
    into.dates.extend(other.dates)
    into.genres.extend(other.genres)
    into.tagged_artists += other.tagged_artists
    into.disc_conflicts.extend(other.disc_conflicts)


def fold_by_tags(
    groups: dict[tuple[str, str], Group],
) -> dict[tuple[str, str], Group]:
    """Fold folders that name the same album into one group.

    Folded here rather than at collection, so everything that reads a FOLDER
    still sees folders: the disc a folder name states, a folder calling itself
    a bonus disc, a folder whose stated disc contradicts its tags. Those are
    settled per folder, then the folders are joined.

    The first folder to name an album keeps its place in the order, so a
    library does not reshuffle itself because a second folder was found.
    """
    folded: dict[tuple[str, str], tuple[str, str]] = {}
    kept: dict[tuple[str, str], Group] = {}
    for place, group in groups.items():
        key = merge_key(group)
        if key is None:
            kept[place] = group
            continue
        first = folded.get(key)
        if first is None:
            folded[key] = place
            kept[place] = group
            continue
        absorb(kept[first], group)
    return kept
