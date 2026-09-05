"""Narrowing the library to the albums somebody asked for by a stated field.

Pure; separate from `searching` on purpose: a phrase is typed and answers
about text anywhere in an album, while this answers about ONE field taking
values from a settled list. The two compose rather than compete, so a filtered
library can still be searched and a search can still be filtered.

**A field plus the values wanted, never a genre specifically.** Genre is the
only field the interface offers today; artist and year are stated in the same
editor and answer the same question, so they arrive by being passed here rather
than by this module learning about them.

**Any, not all.** An album matches when it carries ANY of the values asked for,
so each tick widens what is on screen. Ruled by Oliver on 2026-09-05, against a
library where an album carries one genre string: asking for Rock and Jazz at
once would otherwise hold nothing at all, which is a filter that punishes the
second tick.

**A style is not its main here.** `chosen_in` already states the main of every
style an album carries, so an album marked Trance answers to Electronic without
this knowing what a style is. What it must NOT do is widen the ASK: ticking
Trance means trance, not everything electronic, which is why the dialog that
feeds this leaves the main alone as a style is ticked.

**"Not stated" is not a genre.** More than a tenth of the library carries no
genre tag at all, so a filter that could not reach those albums would hide them
behind a field nobody had filled in. It also covers an album whose tag names
nothing in the catalogue, since no tick could ever reach one of those either:
to somebody looking at the dialog the two are the same album, one nothing here
can say anything about.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.genres import chosen_in
from stellody.domain.overrides import AlbumField


def stated_values(album: Album, field: AlbumField) -> tuple[str, ...]:
    """What an album says for one field, as the set of values it holds.

    A set rather than a value, because genre is many: an album is Rock and
    Alternative Rock at once. Every other field holds one thing, which is a
    set of one; an empty string is a set of none, which is what "not stated"
    reads.
    """
    if field is AlbumField.GENRE:
        return chosen_in(album.genre)
    if field is AlbumField.ALBUM_ARTIST:
        return _held(album.identity.album_artist)
    if field is AlbumField.TITLE:
        return _held(album.identity.title)
    return _held(album.identity.date)


def _held(value: str) -> tuple[str, ...]:
    """One value where there is one; nothing where the field is empty."""
    trimmed = value.strip()
    return (trimmed,) if trimmed else ()


@dataclass(frozen=True, slots=True)
class Narrowing:
    """What the library is being narrowed to, for one stated field.

    Immutable and comparable, so the window can hold what was asked for and
    tell whether a fresh answer changes anything.
    """

    field: AlbumField = AlbumField.GENRE
    wanted: tuple[str, ...] = ()
    unstated: bool = False

    @property
    def is_open(self) -> bool:
        """True while nothing is being asked for, so everything survives."""
        return not self.wanted and not self.unstated

    def keeps(self, album: Album) -> bool:
        """True while this album is one of the ones asked for."""
        if self.is_open:
            return True
        held = stated_values(album, self.field)
        if not held:
            return self.unstated
        return any(value in held for value in self.wanted)


def narrowed_to(albums: tuple[Album, ...], narrowing: Narrowing) -> tuple[Album, ...]:
    """The albums that survive, in the order they arrived.

    The order is the library's own. Narrowing answers which albums are on
    screen and nothing whatever about how they are arranged.
    """
    return tuple(album for album in albums if narrowing.keeps(album))
