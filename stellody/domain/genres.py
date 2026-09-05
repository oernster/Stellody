"""The genres an album can be stated to carry.

A fixed list rather than a reading of the library; the two reasons behind that
pull in opposite directions on purpose. The names are chosen from what the library
actually holds, so nothing here is offered that nobody would ever tick; the
list is not DERIVED from it, because the whole point of stating a genre is to
say what the tags failed to say. A catalogue read from the files could only
ever repeat them.

Re-measured 2026-09-05 over 6,462 audio files: 5,756 carry a genre tag and 705
carry none; the tags are 43 distinct strings, 38 once case is folded, of which
4,913 files name a catalogue genre outright. The long tail was one private
sub-taxonomy, `dance-<style>` and `house-<style>` over four folders, which
having more than one genre answers without a name of its own: those all read
as Dance and Electronic through the table below. Every tag the library carries
now reaches the catalogue, which was not so before 2026-09-05: 62 files across
16 strings reached nothing at all.

Three of the nineteen are here on a ruling rather than on a count.

Punk is the one no measurement asked for at all. No file carries a Punk tag,
which is a fact about the tags rather than about the music: the one Green Day
album in the library is tagged Rock alone and is plainly both.

Jungle is the other. 35 files carry `JUNGLE / FOOTWORK`; they are three LTJ
Bukem albums, which are atmospheric jungle and drum and bass from the mid-90s.
Footwork is a real genre and is not this one; it is Chicago, roughly fifteen
years later, so the word is simply wrong on these records. The tag is therefore
not aliased: the JUNGLE half of it names the genre outright and the
other half is left to reach nothing, which is what a wrong word should do.
Jungle is kept apart from Drum & Bass because a listener hears the
difference, which is reason enough for a name.

Comedy is the third. One file carries it, The Lonely Island's `Incredibad`;
nothing else in the catalogue is anywhere near it: a comedy record is not
Pop that happens to be funny. A count of one is not the measure here, since the
question a catalogue answers is whether a listener could state what a record
is; without this name they could not state that one at all.

An album carries any number of these, so what is held is a set rather than a
value. It is written down as one string because that is what an album's stated
fields are: keeping a list would mean a second shape in the store for one field
alone. The separator is chosen here so the two ends cannot come to disagree.
"""

from __future__ import annotations

import re

# Alphabetical, because that is the order they are read in and any other order
# is an opinion about music that a list of names has no business holding.
GENRES: tuple[str, ...] = (
    "Alternative",
    "Blues",
    "Classical",
    "Comedy",
    "Dance",
    "Drum & Bass",
    "Electronic",
    "Folk",
    "Hip Hop",
    "Jazz",
    "Jungle",
    "Metal",
    "Pop",
    "Punk",
    "R&B & Soul",
    "Rock",
    "Soundtrack",
    "Trance",
    "World",
)

# How several genres are written as one stored value.
SEPARATOR = "; "

# What separates one genre from another in a tag somebody else wrote. An
# ampersand is deliberately absent: two of the names above contain one, so
# splitting on it would turn Drum & Bass into a Drum nobody has heard of.
_PIECES = re.compile(r"[;/,]")

# Tags the library carries that name a catalogue genre in other words.
#
# Every entry is a RULING rather than a rule: the list grows only when somebody
# says a particular tag means a particular genre. Nothing is inferred from a
# name merely containing another, because ticking a box on somebody's behalf
# leaves them unable to tell which ticks were theirs. A tag that resolves to
# nothing is visibly reported by the panel rather than silently dropped.
#
# Keyed on the folded form, so a tag is matched however it was cased.
# One tag can mean more than one genre, so each names however many it names.
# The count beside each is how many files in the reference library carry a tag
# that reaches the catalogue through it, so a ruling can be weighed rather than
# argued about.
ALIASES: dict[str, tuple[str, ...]] = {
    "heavy metal": ("Metal",),  # 231 files
    "hard rock": ("Rock",),  # 20 files
    "hip-hop": ("Hip Hop",),  # 416, tagged `Hip-Hop/Rap`
    "r&b": ("R&B & Soul",),  # 39 tagged `R&B`, 12 tagged `R&B/Soul`
    "alternative metal": ("Alternative", "Metal"),  # 6 files
    # One person's private sub-taxonomy, `dance-<style>` and `house-<style>`,
    # across three albums and a single: 56 files that reached nothing at all.
    # Every one of them is Dance and Electronic together, which is the ruling
    # PLAN.md already carried and the reason none of these styles is offered a
    # name of its own. The styles inside them are real distinctions; they are
    # distinctions between kinds of dance music, which is what having both
    # names on the album already says.
    # One of the cluster names a genre the catalogue already offers in its
    # style half and was ruled to reach it, so a Paul van Dyk album is
    # findable under the thing it actually is. The rest name styles no
    # catalogue name covers and stop at the two. Techno is the near miss and
    # was ruled AGAINST a name of its own: it is a kind of electronic music,
    # which the pair already says, and a catalogue that named every kind would
    # be a taxonomy rather than a list somebody can read.
    "dance-trance": ("Dance", "Electronic", "Trance"),  # 16 files
    "house-melodic": ("Dance", "Electronic"),  # 9 files
    "dance-house": ("Dance", "Electronic"),  # 8 files
    "dance-house-progressive": ("Dance", "Electronic"),  # 7 files
    "house": ("Dance", "Electronic"),  # 3 files
    "dance-techno": ("Dance", "Electronic"),  # 3 files
    "house-progressive house": ("Dance", "Electronic"),  # 2 files
    # The whole value is `dance-house-tech / minimal`, which splits in two.
    # Minimal names nothing here and is left to, as a wrong or unknown word
    # should be; the album still reaches the catalogue through the other half.
    "dance-house-tech": ("Dance", "Electronic"),  # 2 files
    "dance-house-deep": ("Dance", "Electronic"),  # 2 files
    "dance-house-acid": ("Dance", "Electronic"),  # 2 files
    "dance-house-disco": ("Dance", "Electronic"),  # 1 file
    "dance-electro": ("Dance", "Electronic"),  # 1 file
    # Ruled by Oliver to be alternative dance, which is those two names.
    "indie dance": ("Alternative", "Dance"),  # 3 files
    # Ruled a subgenre of Pop rather than a name of its own.
    "britpop": ("Pop",),  # 1 file
    # Ruled to be those two together rather than a name of its own: crossover
    # IS classical meeting popular music, so the pair says it. The album it
    # sits on agrees, its only other tagged track carrying `pop`. This is the
    # one tag the module used to hold up as the example of not reading a genre
    # out of a word that contains one; the example is now `Progressive Rock`,
    # which nobody has ruled on.
    "classical crossover": ("Classical", "Pop"),  # 1 file
}

# One place a tag piece is looked up, whether it names a genre outright or
# names one in other words.
_BY_KEY: dict[str, tuple[str, ...]] = {
    name.casefold(): (name,) for name in GENRES
} | ALIASES


def pieces_of(value: str) -> tuple[str, ...]:
    """The separate genres inside one tag value, in the order they appear.

    A tag is written by whoever wrote it, so `Hip-Hop/Rap` and `R&B/Soul` each
    hold two names and `JUNGLE / FOOTWORK` holds two more. Splitting them is
    what lets a value be recognised at all; a piece nobody recognises is still
    returned, since dropping it would lose what the file says.
    """
    found = [piece.strip() for piece in _PIECES.split(value)]
    return tuple(piece for piece in found if piece)


def chosen_in(value: str) -> tuple[str, ...]:
    """The catalogue genres a stored value names, in catalogue order.

    A piece is matched on its name, ignoring case; failing that, through
    `ALIASES`, where somebody has ruled what a tag means. One piece can name
    more than one genre that way: `Alternative Metal` was ruled to be both,
    which is a thing the tag says and a single-valued table could not have
    recorded.

    Nothing beyond those two routes is inferred: a name is never read as a
    genre merely because it contains one, since ticking a box on somebody's
    behalf leaves them unable to tell which ticks were theirs. `Alternative
    Metal` reaches both only because it was ruled to, never because the words
    are in it.

    A piece naming nothing is passed over rather than guessed at. Where that
    leaves nothing at all, the panel says what the tag was instead of showing
    an empty grid and no reason for it.
    """
    keys = {piece.casefold() for piece in pieces_of(value)}
    named = {name for key in keys if key in _BY_KEY for name in _BY_KEY[key]}
    return tuple(name for name in GENRES if name in named)


def stated_as(genres: tuple[str, ...]) -> str:
    """One stored value naming these genres, in catalogue order.

    Ordered here rather than by the order somebody ticked them, so stating the
    same two genres twice cannot produce two different values that then fail
    to compare equal.
    """
    chosen = {genre.casefold() for genre in genres}
    return SEPARATOR.join(name for name in GENRES if name.casefold() in chosen)
