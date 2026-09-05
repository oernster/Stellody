"""The genres an album can be stated to carry: main categories with styles.

Two levels rather than one flat list, because one level was a lie. Dance,
Trance, Drum n Bass and Jungle are all kinds of electronic music;
Alternative Rock, Heavy Metal and Punk are all kinds of rock. A flat list put
them beside their own parents as though they were peers, so a listener asking
for everything electronic could not have it.

**Discogs' vocabulary and Discogs' shape, curated to this library.** Discogs
runs 15 genres over 1,159 styles and publishes both under CC0; MusicBrainz
offers several thousand genres with no hierarchy at all and Last.fm offers
folksonomy tags rather than genres. So the two levels and the exact spellings
come from Discogs, which means a later lookup there maps one to one with no
translation. What is NOT taken is the vocabulary entire: 1,159 styles is a
taxonomy, not a list somebody chooses from. Only what the library needs is
here, which is also why Footwork is absent (see below).

Four of the fifteen mains are left out because nothing here belongs under one:
Brass & Military, Children's, Latin and Non-Music. Comedy takes the place of
the last of those as a main of its own; see the ruling below. So there are
twelve mains here, eleven of them Discogs' own.

Reggae was left out too and put back: no tag in the library says reggae, which
is a fact about the tags. Finley Quaye's
`Maverick A Strike` is tagged `Hip-Hop/Rap` on all thirteen tracks and `Much
More Than Much Love` is tagged `Pop`; both are reggae records. Absence
from the tags is the wrong test, which is the same ground Punk stands on.

**A main with one style is one name, not two.** Ruled by Oliver on 2026-09-05:
Stage & Screen holding Soundtrack alone says the same thing twice; a level that
never divides anything is a level nobody needs. Four pairs collapsed, each
to the name the library actually uses, measured over 6,462 files that day:
Stage & Screen (0 files) to Soundtrack (62); Folk, World, & Country (0) to Folk
(30); Funk / Soul (0) to Contemporary R&B (49, as `R&B` and `R&B/Soul`).
Classical collapses the other way, to Classical (175) rather than to Modern
Classical (0), since keeping the style's name there would call 175 records
modern when none of them is. Each name that went is kept as an alias, so a
genre stated before the collapse still reads back as what was meant.

Two of those collapses are exceptions, because neither name says one thing.

Folk, World, & Country is the first. Folk, world music and country are three
genres; the only real umbrella over them is Roots, which conventionally means
folk, blues and country, so it would swallow Blues and misfile world music
besides. Ruled by
Oliver on 2026-09-05: the three stand as mains of their own. Country carries no
tag in the library and is offered anyway, on the ground Punk already stands on.
The umbrella name itself is NOT kept as an alias: it never said which of the
three an album was, so any reading of it would invent that. A value carrying it
is reported by the panel as unmatched, which is what an ambiguous name deserves.

Funk / Soul is the second. Ruled by Oliver on the same day: funk and soul are
two genres and neither is Contemporary R&B, which is the modern kind and the
one the library's `R&B` tags mean. All three stand as mains. The Discogs name
needs no alias either: nothing matches it whole, so it splits on its solidus and
reaches Funk and Soul, which is both halves of what it says.

**Where a style hangs is a ruling too.** Both of these were Discogs' filing and
both were overruled by Oliver on 2026-09-05. Britpop is a kind of pop and sits
under Pop, not under Rock. Punk answers to nothing above it and is a main of its
own, so asking for rock no longer hands somebody punk records.

That leaves Pop carrying one style, which is NOT the case the collapse rule
above is about: that rule is for a main and a style saying the same thing, as
Stage & Screen and Soundtrack did. Pop is not Britpop; 1,310 files say Pop
against one that says Britpop, so the two levels there both mean something.

**A style states its main.** Ticking Trance states Electronic too, on writing
and on reading alike, so a filter for Electronic finds every kind of it
without knowing what the kinds are. A main can be stated alone, which is what
the bare `dance` tag on 873 files gets: Discogs has no Dance style;
inventing one to hold a tag that says no more than "electronic" would be
stating something the file never said.

Measured against the library on 2026-09-05: 6,462 audio files, 5,756 carrying
a genre tag and 705 carrying none, in 43 distinct strings and 38 once case is
folded. Every one of those strings reaches the catalogue.

Some names are here on a ruling rather than on a count.

Punk is the one no measurement asked for at all. No file carries a Punk tag,
which is a fact about the tags rather than about the music: the one Green Day
album in the library is tagged Rock alone and is plainly both.

Jungle is the second. 35 files carry `JUNGLE / FOOTWORK`; they are three LTJ
Bukem albums, which are atmospheric jungle and drum and bass from the mid-90s.
Footwork is a real genre; it is a real Discogs style; it is not this one. It is
Chicago, roughly fifteen years later, so the word is simply wrong on these
records. It is therefore left out of the catalogue rather than aliased, so the
JUNGLE half names the genre and the other half reaches nothing, which is what
a wrong word should do.

Reggae is the third and the clearest case of the rule: nothing here is tagged
with it, two albums are it. See above.

Comedy is the fourth and the one place this catalogue leaves Discogs' shape.
One file carries it, The Lonely Island's `Incredibad`; nothing else here is
anywhere near it. Discogs files Comedy under Non-Music, a main for spoken word,
field recordings and interviews. Ruled by Oliver on 2026-09-05: the record in
question is music, so filing it under a heading that says it is not would be
wrong about the one album the name exists for. Comedy is a main here and
Non-Music is gone. The spelling is still Discogs', so a lookup there still maps;
what differs is only where it hangs.

An album carries any number of these, so what is held is a set rather than a
value. It is written down as one string because that is what an album's stated
fields are: keeping a list would mean a second shape in the store for one field
alone. The separator is chosen here so the two ends cannot come to disagree.
"""

from __future__ import annotations

import re

# The catalogue: each main category with the styles kept under it, both in the
# order they are offered. Alphabetical throughout, because that is the order
# they are read in and any other order is an opinion about music that a list of
# names has no business holding.
#
# A main with no styles is not an omission. Blues, Hip Hop, Jazz and Pop are
# each carried by a bare tag in this library and nothing here divides them
# further; a style is added when a tag asks for one.
CATALOGUE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Blues", ()),
    ("Classical", ()),
    ("Comedy", ()),
    ("Contemporary R&B", ()),
    ("Country", ()),
    (
        "Electronic",
        (
            "Acid House",
            "Deep House",
            "Disco",
            "Drum n Bass",
            "Electro",
            "House",
            "Jungle",
            "Progressive House",
            "Tech House",
            "Techno",
            "Trance",
        ),
    ),
    ("Folk", ()),
    ("Funk", ()),
    ("Hip Hop", ()),
    ("Jazz", ()),
    ("Pop", ("Britpop",)),
    ("Punk", ()),
    ("Reggae", ()),
    (
        "Rock",
        (
            "Alternative Metal",
            "Alternative Rock",
            "Hard Rock",
            "Heavy Metal",
        ),
    ),
    ("Soul", ()),
    ("Soundtrack", ()),
    ("World", ()),
)

# Every name the catalogue offers, in the order it offers them: each main
# followed by its own styles. One order, derived from the catalogue rather
# than stated beside it, so the two cannot drift apart.
GENRES: tuple[str, ...] = tuple(
    name for main, styles in CATALOGUE for name in (main, *styles)
)

# Which main each style belongs to. A style states its main, so this is what
# turns one tick into the two things it means.
MAIN_OF: dict[str, str] = {
    style: main for main, styles in CATALOGUE for style in styles
}

# The main categories on their own, for a caller that wants the top level.
MAINS: tuple[str, ...] = tuple(main for main, _styles in CATALOGUE)

# How several genres are written as one stored value.
SEPARATOR = "; "

# What separates one genre from another. The semicolon and nothing else,
# because that is what this application writes; a tag somebody else wrote is
# tried whole first and split only where the whole names nothing.
#
# The comma was here and had to go: `Folk, World, & Country` is one name that
# holds two of them, so splitting on a comma broke a catalogue name into
# pieces that then matched other names. Measured across the library, no file
# tag contains a comma or a semicolon at all, so the split bought nothing and
# cost that name. An ampersand and a solidus are likewise absent, since names
# hold those too; the solidus is handled as a fallback in `_named_by`.
_PIECES = re.compile(r";")

# Tags the library carries now or once carried, naming a catalogue genre in
# other words.
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
    # Spellings of a catalogue name that the name itself does not match.
    "hip-hop/rap": ("Hip Hop",),  # 415 files
    "hip hop / rap": ("Hip Hop",),  # 26 files
    "drum & bass": ("Drum n Bass",),  # 14 files
    # The bare tag says electronic and no more, so that is what it states.
    # Discogs has no Dance style and one is not invented to hold this.
    "dance": ("Electronic",),  # 873 files
    # `Alternative` alone is the rock kind here, which is what every album
    # carrying it is.
    "alternative": ("Alternative Rock",),  # 479 files
    "r&b": ("Contemporary R&B",),  # 39 files, ruled: the modern kind
    "r&b/soul": ("Contemporary R&B",),  # 10 files
    # One person's private sub-taxonomy, `dance-<style>` and `house-<style>`,
    # across three albums and a single: 56 files that reached nothing at all
    # before the styles existed to hold them. Each names its style outright
    # once the catalogue has two levels; each states Electronic through it.
    "dance-trance": ("Trance",),  # 16 files
    "house-melodic": ("House",),  # 9 files
    "dance-house": ("House",),  # 8 files
    "dance-house-progressive": ("Progressive House",),  # 7 files
    "dance-techno": ("Techno",),  # 3 files
    "house-progressive house": ("Progressive House",),  # 2 files
    # The whole value is `dance-house-tech / minimal`, which splits in two.
    # Minimal names nothing here and is left to, as an unknown word should be;
    # the album still reaches the catalogue through the other half.
    "dance-house-tech": ("Tech House",),  # the half of 2 files
    "dance-house-deep": ("Deep House",),  # 2 files
    "dance-house-acid": ("Acid House",),  # 2 files
    "dance-house-disco": ("Disco",),  # 1 file
    "dance-electro": ("Electro",),  # 1 file
    # Ruled by Oliver: the album it sits on is house, which is what the rest
    # of its tags say; Discogs has no Indie Dance style to reach for.
    "indie dance": ("House",),  # 3 files
    # Ruled by Oliver: crossover is classical meeting popular music, so it
    # states both mains rather than asking for a name of its own. The album it
    # sits on agrees, its only other tagged track carrying `pop`.
    "classical crossover": ("Classical", "Pop"),  # 1 file
    # Names the catalogue used to carry, kept so a genre stated before the
    # catalogue gained its second level still reads back as what was meant.
    "metal": ("Heavy Metal",),
    # Mains that held one style each and collapsed into it; Classical went the
    # other way and swallowed its own. Kept so a genre stated before the
    # collapse still reads back as what was meant.
    "stage & screen": ("Soundtrack",),
    "modern classical": ("Classical",),
    # Comedy hung under this until it was made a main of its own, so a genre
    # stated while it did still reads back as what was meant.
    "non-music": ("Comedy",),
    "r&b & soul": ("Contemporary R&B",),
}

# One place a tag piece is looked up, whether it names a genre outright or
# names one in other words.
_BY_KEY: dict[str, tuple[str, ...]] = {
    name.casefold(): (name,) for name in GENRES
} | ALIASES


def pieces_of(value: str) -> tuple[str, ...]:
    """The separate genres inside one tag value, in the order they appear.

    A tag is written by whoever wrote it, so `JUNGLE / FOOTWORK` holds two
    names and `Rock; Pop` holds two more. Splitting them is what lets a value
    be recognised at all; a piece nobody recognises is still returned, since
    dropping it would lose what the file says.
    """
    found = [piece.strip() for piece in _PIECES.split(value)]
    return tuple(piece for piece in found if piece)


def _named_by(piece: str) -> tuple[str, ...]:
    """Every catalogue name one piece of a tag names, if any.

    A piece is matched on its name, ignoring case; failing that, through
    `ALIASES`, where somebody has ruled what a tag means. Failing both, the
    piece is split again on a solidus and each half asked in turn, which is
    how `JUNGLE / FOOTWORK` reaches Jungle while a name that holds a solidus
    of its own, `Funk / Soul`, is still matched whole.
    """
    key = piece.casefold()
    if key in _BY_KEY:
        return _BY_KEY[key]
    if "/" not in piece:
        return ()
    halves = (half.strip().casefold() for half in piece.split("/"))
    return tuple(name for half in halves for name in _BY_KEY.get(half, ()))


def with_mains(names: tuple[str, ...]) -> tuple[str, ...]:
    """Those names plus the main of every style among them, in order.

    A style states its main: an album marked Trance IS electronic, so a filter
    for Electronic must find it without being told what the kinds of it are.
    Done here, once, rather than at every place a genre is read.
    """
    wanted = set(names)
    wanted |= {MAIN_OF[name] for name in names if name in MAIN_OF}
    return tuple(name for name in GENRES if name in wanted)


def chosen_in(value: str) -> tuple[str, ...]:
    """The catalogue genres a stored value names, in catalogue order.

    Nothing is inferred beyond a name, a ruling and the main a style belongs
    to: a piece is never read as a genre merely because it contains one, since
    ticking a box on somebody's behalf leaves them unable to tell which ticks
    were theirs. `classical crossover` reaches Classical and Pop only because
    it was ruled to, never because the word Classical is in it.

    The WHOLE value is tried before it is split, so a catalogue name holding
    a separator of its own is matched as itself rather than broken up.

    A piece naming nothing is passed over rather than guessed at. Where that
    leaves nothing at all, the panel says what the tag was instead of showing
    an empty grid and no reason for it.
    """
    whole = _named_by(value.strip())
    if whole:
        return with_mains(tuple(name for name in GENRES if name in set(whole)))
    named = {name for piece in pieces_of(value) for name in _named_by(piece)}
    return with_mains(tuple(name for name in GENRES if name in named))


def stated_as(genres: tuple[str, ...]) -> str:
    """One stored value naming these genres, in catalogue order.

    Ordered here rather than by the order somebody ticked them, so stating the
    same two genres twice cannot produce two different values that then fail
    to compare equal. A style carries its main into the value, so what is
    stored says both things a tick meant.
    """
    chosen = {genre.casefold() for genre in genres}
    kept = tuple(name for name in GENRES if name.casefold() in chosen)
    return SEPARATOR.join(with_mains(kept))
