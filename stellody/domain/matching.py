"""When two albums are the same album.

Used to decide whether a record offered by an outside catalogue is one the
library already holds. Pure: no I/O, no framework, no clock.

**The principle every table below follows from.** An EDITION qualifier
describes the pressing. A KIND describes the recording. The same recording in a
different pressing is the same album; a different recording is a different
album. So a remaster is the album it remasters, while a live version is its own
record.

**Deliberately not `AlbumIdentity`.** That type's handle keys the artwork
cache, the album's rating, every track rating under it and every accepted
correction, so changing what it compares on would orphan all of them. This
answers a different question and keeps its own key, built on the same
`comparison_key` so the two cannot drift apart on normalisation.

**The year is deliberately absent.** A remastered album's tag carries the
remaster's year while the catalogue carries the original's, so a key holding
the year would make every remastered album look like something the library does
not have. The artist is fixed wherever this is used, since one artist's
releases are only ever matched against that same artist's held albums.

**Both sides are reduced the same way, from different starting points.** A
catalogue states an album's kinds as data; a library only ever has the title a
ripper wrote, so its kinds are read out of the title and then taken off it. A
word that merely restates a kind already stated is noise on either side:
`Secret World (Live)` in the library and `Secret World Live` in the catalogue
are one record; they meet only once both are reduced to a key plus a kind.

**The tables were measured, not chosen.** Every entry earns its place against
the 619 album titles in the reference library, on 2026-09-06. The terminal-word
rule exists because `Tenth Anniversary Edition`, `Special Collector's Edition`,
`Deluxe Experience Edition` and `International Version` were each kept for the
sake of one unlisted word. The type markers exist because four held titles
carry `- EP` or `- Single`, which iTunes writes into a title and a catalogue
states as a type instead. The opposite design, stripping any trailing segment
unless it names a recording, was tried against the same titles and rejected: it
destroyed `L.I.F.E. (Love Is for Ever)`, `The Death of Slim Shady (Coup de
Grâce)`, four Global Underground city names and a date range.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from stellody.domain.text import comparison_key


class ReleaseKind(StrEnum):
    """What kind of record this is, beyond being an album.

    The names a catalogue uses for its secondary types. `OTHER` stands for
    every kind this version does not know, so an unrecognised one is still
    carried rather than silently read as a plain album.
    """

    LIVE = "live"
    REMIX = "remix"
    DEMO = "demo"
    COMPILATION = "compilation"
    SOUNDTRACK = "soundtrack"
    DJ_MIX = "dj-mix"
    OTHER = "other"


# A qualifier describing the PRESSING. Taking one off leaves the album it was a
# pressing of. `remix` is deliberately absent: a remix is a recording.
EDITION_WORDS = frozenset(
    {
        "remaster",
        "remastered",
        "remasters",
        "deluxe",
        "expanded",
        "edition",
        "editions",
        "version",
        "anniversary",
        "special",
        "bonus",
        "track",
        "tracks",
        "reissue",
        "digital",
        "super",
        "explicit",
        "clean",
    }
)

# A segment ending in one of these names a pressing whatever else it carries,
# so it goes without every word in it having to be known.
TERMINAL_WORDS = frozenset({"edition", "version", "remaster", "remastered", "reissue"})

# Words a qualifier may carry without earning its removal. A segment built only
# of these is not an edition qualifier, so a real edition word is still needed.
CONNECTIVES = frozenset({"the", "a", "an", "and", "of", "with", "in", "on"})

# What a ripper writes into a title that a catalogue states as a type. A title
# keeping one can never match the release it belongs to.
TYPE_MARKERS = frozenset({"ep", "single"})

# The words that name a kind, so a title stating one can be read as stating it.
KIND_WORDS: dict[str, ReleaseKind] = {
    "live": ReleaseKind.LIVE,
    "remix": ReleaseKind.REMIX,
    "remixes": ReleaseKind.REMIX,
    "remixed": ReleaseKind.REMIX,
    "demo": ReleaseKind.DEMO,
    "demos": ReleaseKind.DEMO,
    "compilation": ReleaseKind.COMPILATION,
    "soundtrack": ReleaseKind.SOUNDTRACK,
}

# A qualifier naming a different RECORDING. One of these anywhere in a segment
# stops it being read as a pressing, however the segment ends, because
# `Karaoke Version` and `Single Version` are not the album they qualify.
DISTINGUISHING = frozenset(KIND_WORDS) | frozenset(
    {
        "instrumental",
        "instrumentals",
        "karaoke",
        "acoustic",
        "mix",
        "mixes",
        "unmixed",
        "dj",
        "session",
        "sessions",
        "mono",
        "radio",
        "edit",
        "single",
        "cover",
        "tribute",
        "score",
    }
)

_BRACKETED = re.compile(r"\s*(?:\((?P<round>[^()]*)\)|\[(?P<square>[^\[\]]*)\])\s*$")
_DASHED = re.compile(r"\s+-\s+(?P<dash>[^-]+)\s*$")
_WORDS = re.compile(r"[0-9a-z]+")
_YEAR = re.compile(r"^(?:1[89]|20)\d{2}$")


@dataclass(frozen=True, slots=True)
class ReleaseMatch:
    """What two albums are compared on: a title reduced, plus its kinds.

    The kinds are held in catalogue order rather than as a set, so two matches
    naming the same kinds compare equal whatever order they arrived in.
    """

    key: str
    kinds: tuple[ReleaseKind, ...] = ()

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("an album needs something left to be matched on")


def _words_in(segment: str) -> list[str]:
    """The comparable words of a segment, punctuation and case discarded."""
    return _WORDS.findall(segment.casefold())


def _trailing(title: str) -> tuple[str, str] | None:
    """The title without its trailing qualifier, plus that qualifier.

    None where the title carries no trailing qualifier at all. A bracketed one
    is tried before a dashed one, since a title can end with both.
    """
    for pattern in (_BRACKETED, _DASHED):
        match = pattern.search(title)
        if match is not None:
            # Presence, not truthiness: `Foo ()` captures an empty segment,
            # which is a qualifier naming nothing rather than no qualifier.
            found = (v for v in match.groupdict().values() if v is not None)
            segment = next(found)
            return title[: match.start()].strip(), segment
    return None


def _is_edition(words: list[str]) -> bool:
    """Whether these words name a pressing rather than a recording."""
    if not words:
        return False
    if len(words) == 1 and words[0] in TYPE_MARKERS:
        return True
    if any(word in DISTINGUISHING for word in words):
        return False
    if words[-1] in TERMINAL_WORDS:
        return True
    allowed = EDITION_WORDS | CONNECTIVES
    if any(word not in allowed and not _YEAR.match(word) for word in words):
        return False
    return any(word in EDITION_WORDS for word in words)


def _kinds_named(words: list[str]) -> tuple[ReleaseKind, ...] | None:
    """The kinds these words name; None where they name anything else.

    Every word has to name a kind or be a connective, so `Live` is read as a
    kind while `Live at Twilo` is left alone: the venue is part of the title.
    """
    if not words:
        return None
    if any(word not in KIND_WORDS and word not in CONNECTIVES for word in words):
        return None
    named = {KIND_WORDS[word] for word in words if word in KIND_WORDS}
    return _ordered(named) if named else None


def _ordered(kinds: set[ReleaseKind]) -> tuple[ReleaseKind, ...]:
    """Kinds in catalogue order, so two matches compare on equal terms."""
    return tuple(kind for kind in ReleaseKind if kind in kinds)


def _without_editions(title: str) -> str:
    """The title with every trailing edition qualifier taken off."""
    trimmed = title.strip()
    while True:
        split = _trailing(trimmed)
        if split is None or not split[0] or not _is_edition(_words_in(split[1])):
            return trimmed
        trimmed = split[0]


def _without_stated(title: str, stated: tuple[ReleaseKind, ...]) -> str:
    """The title with any trailing word that merely restates a stated kind.

    A catalogue writes `Secret World Live` and separately states that it is a
    live record, so the word in the title says nothing the type has not said
    already. Taking it off is what lets that record meet the library's own
    `Secret World (Live)`.

    A record actually titled `Live` keeps its title. Reducing a title to
    nothing at all leaves an album that cannot be told from any other, which is
    worse than leaving a word that says the same thing twice.
    """
    trimmed = title
    while stated:
        words = _WORDS.findall(trimmed.casefold())
        if not words or KIND_WORDS.get(words[-1]) not in stated:
            return trimmed
        cut = trimmed.rstrip()
        shorter = cut[: len(cut) - len(words[-1])].strip(" -")
        if not shorter:
            return trimmed
        trimmed = shorter
    return trimmed


def matched(title: str, stated: tuple[ReleaseKind, ...] = ()) -> ReleaseMatch:
    """How this album is compared, whichever side of the question it is on.

    `stated` carries the kinds a catalogue has declared; a library states none,
    so its kinds are read out of the title instead. Either way the qualifier
    that named them comes off, leaving the two sides comparable.
    """
    trimmed = _without_editions(title)
    kinds = set(stated)
    split = _trailing(trimmed)
    if split is not None and split[0]:
        named = _kinds_named(_words_in(split[1]))
        if named is not None:
            trimmed = _without_editions(split[0])
            kinds |= set(named)
    return ReleaseMatch(
        key=comparison_key(_without_stated(trimmed, _ordered(kinds))),
        kinds=_ordered(kinds),
    )
