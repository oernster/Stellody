"""How an album the library lacks turns into a shop's own search address.

The whole of stage two's arithmetic, which is small on purpose: a shop is a
name and a template, an address is that template with the artist and the album
put into it; a line of text is what somebody pastes where no template
exists. Nothing here opens anything. SHOPS.md FR-S10, FR-S11 and NFR-S-PRIV-001.

**Two placeholders rather than one.** Measured on 2026-09-07: Boomkat's search
answered nothing for "Autechre Amber" and 85 results including Amber for
"Autechre" alone. A shop that searches badly on two terms is given one, which
is only possible where the template says which term goes where.

**Spaces are `%20` rather than `+`.** Measured the same day: HDtracks shows a
literal plus sign in its own search box, while Qobuz, Bandcamp, Boomkat, Bleep,
Beatport and ProStudioMasters all accepted `%20`. One encoding for every shop
beats a rule per shop.

**The encoding is written out rather than imported.** `urllib.parse.quote`
would do it in one call and cannot be used: `urllib` is a networking package,
which the domain may not import and the offline guard watches for everywhere
outside four named modules. Percent encoding is nine lines and the standard
defines the unreserved set, so there is nothing here to get subtly wrong.
"""

from __future__ import annotations

import string
from dataclasses import dataclass

ARTIST_PLACEHOLDER = "{artist}"
ALBUM_PLACEHOLDER = "{album}"
# RFC 3986's unreserved set: everything else in a value is percent encoded,
# which is what makes a title holding a slash, an ampersand or a space safe to
# put inside somebody else's address.
UNRESERVED = frozenset(string.ascii_letters + string.digits + "-._~")
PERCENT = "%{value:02X}"
# What separates the two halves of a copied line. A hyphen rather than a dash,
# by the house rule; also the shape a paste into any search box wants.
COPIED_LINE = "{artist} - {title}"


def encoded(value: str) -> str:
    """One value, safe to sit inside an address.

    Encoded from UTF-8 bytes rather than from characters, since a percent
    escape names a byte: an accented letter is two escapes, not one.
    """
    out: list[str] = []
    for letter in value:
        if letter in UNRESERVED:
            out.append(letter)
            continue
        out.extend(PERCENT.format(value=byte) for byte in letter.encode("utf-8"))
    return "".join(out)


@dataclass(frozen=True, slots=True)
class WantedAlbum:
    """One album somebody has ticked, with the artist it belongs to.

    Its own type rather than a pair of strings, because the artist beside the
    title is the whole content of this feature: an address built from a title
    alone finds the wrong record; a copied line without the artist is not
    something anybody can paste.
    """

    artist: str
    title: str

    def __post_init__(self) -> None:
        if not self.artist.strip():
            raise ValueError("a wanted album needs an artist")
        if not self.title.strip():
            raise ValueError("a wanted album needs a title")

    @property
    def as_text(self) -> str:
        """The line put on the clipboard for this album. FR-S14."""
        return COPIED_LINE.format(artist=self.artist, title=self.title)


@dataclass(frozen=True, slots=True)
class Shop:
    """One shop: what it is called and how its search is addressed.

    A template naming neither placeholder is refused here rather than filtered
    out later, so there is one rule in one place: whatever holds a Shop holds a
    shop that can actually be searched. FR-S11.
    """

    name: str
    template: str
    note: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a shop needs a name")
        if not self.template.strip():
            raise ValueError("a shop needs a search address")
        if not self.names_a_placeholder:
            raise ValueError(
                "a shop's address must name {artist} or {album}, "
                "else every album opens the same page"
            )

    @property
    def names_a_placeholder(self) -> bool:
        """Whether this template puts anything of the album into the address."""
        return ARTIST_PLACEHOLDER in self.template or (
            ALBUM_PLACEHOLDER in self.template
        )

    def address_for(self, wanted: WantedAlbum) -> str:
        """This shop's search for that album.

        Both placeholders are replaced whether or not both appear, since a
        template naming one of them is the ordinary case rather than an error:
        Boomkat's row deliberately carries the artist alone.
        """
        return self.template.replace(
            ARTIST_PLACEHOLDER, encoded(wanted.artist)
        ).replace(ALBUM_PLACEHOLDER, encoded(wanted.title))


def addresses_at(shop: Shop, wanted: tuple[WantedAlbum, ...]) -> tuple[str, ...]:
    """One search address per ticked album, in the order they were ticked.

    One address per album rather than one for all of them, because no shop
    searches for several albums at once. FR-S06.
    """
    return tuple(shop.address_for(album) for album in wanted)


def copied_text(wanted: tuple[WantedAlbum, ...]) -> str:
    """The ticked albums as lines somebody can paste anywhere. FR-S14."""
    return "\n".join(album.as_text for album in wanted)
