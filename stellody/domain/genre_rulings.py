"""Tags ruled to name a catalogue genre in other words.

Held apart from `genres`, which is the catalogue and how a value is read and
written. This is the library's own words and what each was ruled to mean: a
table that grows by one ruling at a time, where the catalogue changes rarely.
Split out on 2026-10-01 when FR-D77 brought eighty more rulings than the one
module could hold under its line cap; `genres` still answers for `ALIASES`, so
nothing that reads it had to learn a new address.

Every entry is a RULING rather than a rule: the list grows only when somebody
says a particular tag means a particular genre. Nothing is inferred from a name
merely containing another, because ticking a box on somebody's behalf leaves
them unable to tell which ticks were theirs. A tag that resolves to nothing is
visibly reported by the panel rather than silently dropped.

Keyed on the folded form, so a tag is matched however it was cased. One tag can
mean more than one genre, so each names however many it names. The count beside
each is what the reference library held WHEN THAT RULING WAS MADE, kept so a
decision can be weighed rather than argued about. It is a record of the
evidence rather than a live measurement, so it is not updated as the library
grows: re-count before leaning on one to make a fresh ruling.
"""

from __future__ import annotations

# Every heavy metal name MusicBrainz stated for a similar artist in Oliver's
# whole-library answer of 2026-10-01, with the candidates carrying each.
_METALS = {
    "death metal": 8,
    "gothic metal": 6,
    "metalcore": 4,
    "doom metal": 3,
    "symphonic metal": 3,
    "industrial metal": 3,
    "black metal": 3,
    "thrash metal": 3,
    "melodic metalcore": 2,
    "power metal": 2,
    "technical death metal": 2,
    "mathcore": 2,
    "progressive metal": 1,
    "melodic death metal": 1,
    "old school death metal": 1,
    "brutal death metal": 1,
}
# The punk names in that answer, counted the same way.
_PUNKS = {
    "post-punk": 5,
    "post-hardcore": 5,
    "pop punk": 4,
    "emo": 4,
    "punk rock": 2,
    "melodic hardcore": 1,
    "skate punk": 1,
    "screamo": 1,
    "emo pop": 1,
    "psychobilly": 1,
    "electropunk": 1,
}
# The jazz names in that answer.
_JAZZ = {
    "acid jazz": 12,
    "nu jazz": 2,
    "flamenco jazz": 1,
    "jazz-funk": 1,
    "smooth jazz": 1,
    "swing": 1,
    "lounge": 1,
}
# The world music names in that answer.
_WORLD = {
    "mpb": 8,
    "african blues": 4,
    "bossa nova": 4,
    "desert blues": 3,
    "tropicália": 3,
    "flamenco": 2,
    "afrobeat": 2,
    "chanson française": 2,
    "mbalax": 1,
    "jùjú": 1,
    "world fusion": 1,
    "latin": 1,
}
# The hip hop names in that answer.
_HIP_HOP = {
    "grime": 5,
    "alternative hip hop": 3,
    "trap": 3,
    "experimental hip hop": 2,
    "cloud rap": 2,
    "pop rap": 1,
    "west coast hip hop": 1,
    "east coast hip hop": 1,
    "instrumental hip hop": 1,
    "horrorcore": 1,
    "memphis rap": 1,
    "trap metal": 1,
}

ALIASES: dict[str, tuple[str, ...]] = {
    # Spellings of a catalogue name that the name itself does not match.
    "hip-hop/rap": ("Hip Hop",),  # 415 files
    "hip hop / rap": ("Hip Hop",),  # 26 files
    "drum & bass": ("Drum n Bass",),  # 14 files
    # `Alternative` alone is the rock kind here, which is what every album
    # carrying it is.
    "alternative": ("Alternative Rock",),  # 479 files
    "r&b": ("Contemporary R&B",),  # 39 files, ruled: the modern kind
    "r&b/soul": ("Contemporary R&B",),  # 10 files
    # One person's private sub-taxonomy, `dance-<style>` and `house-<style>`,
    # across three albums and a single: 56 files that reached nothing at all
    # before the styles existed to hold them. Each names its style outright
    # once the catalogue has two levels; each states its main through it,
    # which since the split of 2026-10-01 (FR-D77) is House, Techno & Electro
    # or Dance rather than Electronic.
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
    # Ruled by Oliver on 2026-09-27, from what MusicBrainz states for similar
    # artists rather than from a file tag. Unrecognised, they withheld every
    # candidate stating them from a house and techno run: Dirtyloud was
    # offered nobody, since James Egbert and Noisia read as Electronic alone.
    "electro house": ("House",),  # 2 candidates
    "ambient techno": ("Techno",),  # 5 candidates, The Field among them
    # Ruled by Oliver on 2026-09-30, from the 74 similar artists a genre filter
    # withheld because MusicBrainz stated only names nothing here recognised.
    # Counts are those candidates in that run. Dubstep, UK Garage, Electronica,
    # Downtempo, Ambient and Indie Pop were ruled here too and are catalogue
    # names now (FR-D77), so they match outright and need no entry.
    "drum and bass": ("Drum n Bass",),  # 12 candidates
    "liquid funk": ("Drum n Bass",),  # 3 candidates
    "vocal trance": ("Trance",),  # 3 candidates
    "indie rock": ("Alternative Rock",),  # 6 candidates
    # Ruled Electronic alone on 2026-09-30; given the style that holds them on
    # 2026-10-01 (FR-D77) once one existed.
    "trip hop": ("Downtempo",),  # 7 candidates
    "indietronica": ("Electronica",),  # 4 candidates
    # Ruled by Oliver on 2026-10-01 (FR-D77), from the 155 similar artists his
    # whole-library answer held back because MusicBrainz stated only names
    # nothing here recognised. Counts are those candidates in that answer.
    # Dance: EDM, Eurodance, Breakbeat, Italo Dance, Dance-Pop and
    # Hi-NRG are its styles' own names and match outright.
    "nu skool breaks": ("Breakbeat",),  # 1 candidate
    "breakbeat hardcore": ("Breakbeat",),  # 1 candidate
    "future bass": ("EDM",),  # 2 candidates
    "trap edm": ("EDM",),  # 2 candidates
    "rave": ("Dance",),  # 1 candidate
    "club": ("Dance",),  # 1 candidate
    "new rave": ("Dance",),  # 1 candidate
    # Electronic, House and Techno & Electro: Big Beat, Minimal Techno and
    # EBM match outright. A ruling to House now states the House main alone.
    "electro-industrial": ("EBM",),  # 2 candidates
    "aggrotech": ("EBM",),  # 1 candidate
    "witch house": ("Electronic",),  # 1 candidate
    "detroit techno": ("Techno",),  # 1 candidate
    "microhouse": ("House",),  # 2 candidates
    "hip house": ("House",),  # 1 candidate
    "euro house": ("House",),  # 1 candidate
    "goa trance": ("Trance",),  # 1 candidate
    "electroclash": ("Electro",),  # 2 candidates
    # Pop: Synth-pop, Electropop, New Wave, Dream Pop, K-Pop and Pop Rock
    # match outright.
    "synthpop": ("Synth-pop",),  # spelled apart from the style's own name
    "futurepop": ("Synth-pop",),  # 1 candidate
    "bitpop": ("Electropop",),  # 1 candidate
    "psychedelic pop": ("Pop",),  # 2 candidates
    "folk pop": ("Pop",),  # 2 candidates
    # Kinds of a main that holds no style for them: each states its main and
    # no more. Counted in the tables above.
    **{name: ("Heavy Metal",) for name in _METALS},
    **{name: ("Punk",) for name in _PUNKS},
    **{name: ("Jazz",) for name in _JAZZ},
    **{name: ("World",) for name in _WORLD},
    **{name: ("Hip Hop",) for name in _HIP_HOP},
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
