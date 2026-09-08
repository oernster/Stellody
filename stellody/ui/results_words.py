"""What the results dialog says, kept apart from how it draws it.

Split out of `results_dialog.py` on 2026-09-07, when the dialog was reported as
unreadable: shown a tree of blue names, amber names and plain names, Oliver
asked which lines were albums and which were tracks, then whether two of the
amber names were artists at all. Nothing on screen answered any of that. The
wording is what fixes it, so the wording is worth a module: what a row SAYS and
where a row is DRAWN change for different reasons; the first is now the larger
half.

**Nothing in the results is ever a track.** A discovery run asks two catalogues
about artists and release groups; a track is never fetched, never written down
and never shown. So the legend can state that outright rather than hedging.

**A row says what kind of thing it is, rather than leaving its colour to say
it.** Colour cannot be the only carrier: it fails a reader who cannot separate
these two hues, it fails a screenshot pasted into a message and it failed the
person who wrote it. An amber row indented under a blue one looked like an
album under an artist; its own children then looked like tracks.
"""

from __future__ import annotations

from stellody.domain.discovery import Gaps

# What each kind of row is called, in the fewest words that still say it. The
# candidate's word appears on every candidate row, since that is the row that
# was mistaken for an album.
SIMILAR = "similar artist"
ALBUM = "album"
ALBUMS = "albums"
# A source artist, with what was found for it. Both counts, since a row saying
# only its albums leaves the artists beneath it unexplained.
SOURCE_ROW = "{artist} ({counts})"
CANDIDATE_ROW = "{artist} ({counts})"
COUNTS_APART = ", "
# Said against a candidate that has been opened and answered.
SIMILAR_WITH_ALBUMS = "{similar}, {albums}"

# The three lines under the title. Each is drawn in the colour it describes,
# except the last, which describes everything else.
LEGEND_SOURCE = "Blue: an artist you hold. Under it, albums by them you do not."
LEGEND_CANDIDATE = (
    "Amber: a similar artist you hold nothing by. Open one to fetch its albums."
)
LEGEND_ALBUM = "Every other line is an album title. Nothing here is a track."

# What the bar at the top says while nothing is being fetched. It doubles as
# the instruction, which is why the space is reserved rather than shown only
# when something is happening: a strip that appears would push the whole list
# down at the moment somebody clicked an arrow in it.
NOT_ASKING = "Open an amber artist to fetch its albums"
ASKING_ONE = "Asking the catalogue about {artist}"
ASKING_MANY = "Asking the catalogue about {count} artists"
# Said under a candidate whose lookup could not be made. Against that artist
# rather than in a bar, since every other entry is still usable and a message
# elsewhere would say nothing about which one failed. FR-D32.
#
# It says how to try again because trying again already works and nothing said
# so: a row that failed is asked about afresh the next time it is opened, so
# closing it and opening it is the retry. Reported by Oliver on 2026-09-08,
# who asked for a way to try again while looking at a screen that had one.
COULD_NOT_ASK = "Could not be looked up: {reason}. Close and open this row to try again"
# Said under a candidate the catalogue answered about with nothing worth
# offering. An entry that opens onto emptiness reads as one still loading.
NOTHING_OFFERED = "No albums worth offering"
# Said under a candidate that arrived without an identifier, which is a name
# the similarity catalogue gave without saying who it meant. Nobody can be
# asked about that, so the entry says why rather than opening onto nothing.
NOBODY_TO_ASK = "The catalogue did not say which artist this is"
ONE = 1

# What the run was scoped to, said above the key. The count is given as well as
# the names because the names alone read as a heading rather than as the answer
# to "why these artists": a run over eleven genres is a different thing from a
# run over one; the number says which at a glance.
GENRE = "genre"
GENRES = "genres"
GENRES_APART = ", "
LOOKED_IN = "Looked in {count}: {genres}"


def counted(count: int, single: str, several: str) -> str:
    """A count with the word for that many of them."""
    return f"{count} {single if count == ONE else several}"


def source_row(found: Gaps) -> str:
    """A source artist, with what the run turned up beneath it.

    Both counts are said, since the albums and the similar artists sit in one
    list under the name and a row explaining only the albums leaves the rest
    of its own children unaccounted for.
    """
    counts = [counted(len(found.albums), ALBUM, ALBUMS)]
    if found.artists:
        counts.append(counted(len(found.artists), SIMILAR, f"{SIMILAR}s"))
    return SOURCE_ROW.format(artist=found.artist, counts=COUNTS_APART.join(counts))


def candidate_row(name: str, albums: int | None = None) -> str:
    """A candidate artist, named as one.

    The count is absent until the catalogue has been asked, because until then
    nobody knows it: a candidate is somebody the library holds nothing by, so
    the number is whatever their whole discography turns out to be.
    """
    counts = SIMILAR
    if albums is not None:
        counts = SIMILAR_WITH_ALBUMS.format(
            similar=SIMILAR, albums=counted(albums, ALBUM, ALBUMS)
        )
    return CANDIDATE_ROW.format(artist=name, counts=counts)


def looked_in(ticked: tuple[str, ...]) -> str:
    """What the run was asked to look in; nothing at all where it is unknown.

    The genres are said in the file's own order, which is the order they were
    handed over, rather than sorted here: two orderings of one list is two
    things to keep in step for no reader's benefit.

    An empty answer yields an empty string rather than a line saying so. A file
    written before the genres were recorded is the only way that happens; a line
    reading "looked in nothing" would be worse than the absence.
    """
    if not ticked:
        return ""
    return LOOKED_IN.format(
        count=counted(len(ticked), GENRE, GENRES), genres=GENRES_APART.join(ticked)
    )


def asking_about(names: tuple[str, ...]) -> str:
    """What the bar says while these artists are being looked up."""
    if len(names) == ONE:
        return ASKING_ONE.format(artist=names[0])
    return ASKING_MANY.format(count=len(names))
