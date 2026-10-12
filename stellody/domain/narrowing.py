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
style an album carries, so an album marked Trance answers to Techno & Electro
without this knowing what a style is. What it must NOT do is widen the ASK:
ticking Trance means trance, not all of that main, which is why the dialog that
feeds this leaves the main alone as a style is ticked.

**"Not stated" is not a genre.** More than a tenth of the library carries no
genre tag at all, so a filter that could not reach those albums would hide them
behind a field nobody had filled in. It also covers an album whose tag names
nothing in the catalogue, since no tick could ever reach one of those either:
to somebody looking at the dialog the two are the same album, one nothing here
can say anything about.

**The years narrow as well, beside the field** (Oliver's ruling, 2026-10-12;
FR-D99). Read off the album's date tag, by the rule a run reads a release by:
with years set, an album whose date names no year is left out, since it
cannot be shown to fit (`ReleaseYears.admits`).
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.domain.album import Album
from stellody.domain.genres import chosen_in
from stellody.domain.overrides import AlbumField
from stellody.domain.release_years import ANY_YEAR, ReleaseYears
from stellody.domain.text import year_of


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
    years: ReleaseYears = ANY_YEAR

    @property
    def is_open(self) -> bool:
        """True while nothing is being asked for, so everything survives."""
        return self._field_open and not self.years.is_bounded

    @property
    def _field_open(self) -> bool:
        """True while nothing is asked of the field, whatever the years say."""
        return not self.wanted and not self.unstated

    def keeps(self, album: Album) -> bool:
        """True while this album is one of the ones asked for."""
        return self._field_keeps(album) and self.years.admits(
            year_of(album.identity.date)
        )

    def _field_keeps(self, album: Album) -> bool:
        """True while the field asks nothing or the album holds a value asked."""
        if self._field_open:
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
