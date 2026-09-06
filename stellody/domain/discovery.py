"""What the library is missing, worked out from what it holds.

Pure: no I/O, no framework, no clock. Everything a catalogue said arrives here
as values and leaves as values, so a whole run can be exercised with no source,
no network and no library on disk.

**The gap is the whole point.** An offer of a record already on the shelf spends
the listener's attention and teaches them to distrust the rest of the list, so
nothing held is ever offered back. That rule is worth more than completeness:
where the two conflict, the offer goes.

**Genre scopes both ends.** It decides which artists are asked about, which is
what keeps a run naming a subset somebody chose rather than an inventory of
everything they own; it also decides what is kept from the answers. A candidate
stating no genre at all is kept regardless: dropping what a catalogue failed to
describe would quietly narrow discovery to the well-catalogued, which is the
opposite of finding what is missing.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.genres import chosen_in
from stellody.domain.matching import ReleaseKind, ReleaseMatch, matched
from stellody.domain.narrowing import Narrowing, narrowed_to
from stellody.domain.overrides import AlbumField
from stellody.domain.text import comparison_key

# The kinds worth offering. A plain album states none of them, so an empty set
# is the ordinary case. A record whose kinds are not all in here is left alone:
# a hits package or a mixed set by an artist already held is noise rather than
# a discovery; an unrecognised kind is excluded by the same test rather
# than needing a list of its own.
OFFERED_KINDS = frozenset({ReleaseKind.LIVE, ReleaseKind.REMIX, ReleaseKind.DEMO})


@dataclass(frozen=True, slots=True)
class ReleaseGroup:
    """An album a catalogue says an artist made.

    `genres` holds what the catalogue stated, in its own words. Reading them
    into the catalogue happens here rather than at the boundary, so a source
    that states nothing and a source that states something unrecognised are the
    same case and are handled once.
    """

    title: str
    kinds: tuple[ReleaseKind, ...] = ()
    genres: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("an offered album needs a title")

    @property
    def match(self) -> ReleaseMatch:
        """How this album is compared against the ones already held."""
        return matched(self.title, self.kinds)

    @property
    def is_offered(self) -> bool:
        """Whether this kind of record is one worth putting in front of anybody."""
        return set(self.kinds) <= OFFERED_KINDS

    @property
    def states_no_genre(self) -> bool:
        """True where the catalogue described this album with nothing usable."""
        return not catalogue_genres(self.genres)


@dataclass(frozen=True, slots=True)
class SimilarArtist:
    """An artist a catalogue considers similar to one already held."""

    name: str
    identifier: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a similar artist needs a name")


@dataclass(frozen=True, slots=True)
class Gaps:
    """What one source artist turned out to be missing."""

    artist: str
    albums: tuple[ReleaseGroup, ...] = ()
    artists: tuple[SimilarArtist, ...] = ()

    @property
    def is_empty(self) -> bool:
        """True where this artist yielded nothing worth writing down."""
        return not self.albums and not self.artists


def catalogue_genres(stated: tuple[str, ...]) -> tuple[str, ...]:
    """What the catalogue's own genre names mean here, in catalogue order.

    Each stated name is read on its own rather than joined into one string,
    since a catalogue hands over a list and joining it would invent a separator
    the rules would then have to split back out.
    """
    named: set[str] = set()
    for value in stated:
        named.update(chosen_in(value))
    return tuple(sorted(named))


def wanted_by(stated: tuple[str, ...], ticked: tuple[str, ...]) -> bool:
    """Whether a thing described like this is one of the genres asked for.

    Something the catalogue could not describe is wanted whatever was ticked,
    which is the deliberate asymmetry: a gap nobody has catalogued is still a
    gap; it is the listener rather than this rule who can tell.
    """
    named = catalogue_genres(stated)
    if not named:
        return True
    return any(name in named for name in ticked)


def source_artists(
    albums: tuple[Album, ...], ticked: tuple[str, ...]
) -> tuple[str, ...]:
    """The album artists a run will ask about, in the library's own order.

    Narrowing already answers "which albums name any of these genres", using
    the resolved genre the listener sees rather than the tag underneath it, so
    that question is asked of it rather than answered a second time here.

    Nothing ticked means nothing to ask about. The dialog does not offer a run
    in that state, so this never happens by accident; it is stated anyway,
    because narrowing reads an empty ask as no narrowing at all and would
    otherwise hand back the whole library.
    """
    if not ticked:
        return ()
    narrowing = Narrowing(field=AlbumField.GENRE, wanted=ticked)
    found: list[str] = []
    for album in narrowed_to(albums, narrowing):
        artist = album.identity.album_artist
        if artist not in found:
            found.append(artist)
    return tuple(found)


def held_matches(albums: tuple[Album, ...]) -> frozenset[ReleaseMatch]:
    """How every album in this collection is compared, as one set."""
    return frozenset(matched(album.identity.title) for album in albums)


def albums_missing(
    held: frozenset[ReleaseMatch],
    offered: tuple[ReleaseGroup, ...],
    ticked: tuple[str, ...],
) -> tuple[ReleaseGroup, ...]:
    """The offered albums that are worth showing and are not already held.

    Order is the catalogue's own, since it arrived in whatever order the
    catalogue thought best and this has no better opinion.
    """
    return tuple(
        group
        for group in offered
        if group.is_offered
        and group.match not in held
        and wanted_by(group.genres, ticked)
    )


def artists_missing(
    held: tuple[str, ...], offered: tuple[SimilarArtist, ...]
) -> tuple[SimilarArtist, ...]:
    """The similar artists the library does not already hold.

    Compared on the same normalisation albums are compared on, so an artist
    held as `The Police` is not offered back as `the police`. A catalogue
    naming one twice offers it once.
    """
    known = {comparison_key(name) for name in held}
    found: list[SimilarArtist] = []
    seen: set[str] = set()
    for artist in offered:
        key = comparison_key(artist.name)
        if key in known or key in seen:
            continue
        seen.add(key)
        found.append(artist)
    return tuple(found)
