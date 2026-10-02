"""Which of the genres a catalogue states are worth believing.

Pure: no I/O, no framework, no clock.

**A genre tagged once is a stray, not a description.** Reported by Oliver on
2026-09-30: a filter for six house and techno styles still showed AC/DC, Adele
and 50 Cent, through similar artists such as Nirvana and Snoop Dogg. Measured
against MusicBrainz the same day, Nirvana carries grunge with 67 votes and
alternative rock with 30, beside "electronic" and "psytrance" with one vote
each; Snoop Dogg carries hip hop with 21 beside "house" and "drum and bass"
with one each. Read as equals, those single votes let almost anybody through.

**An artist tagged once throughout keeps every tag.** Dropping them all would
leave a little-tagged artist with no genre, which a filter must withhold; one
vote apiece is the best description there is of them.

**A genre far behind the artist's own is a side, not a description.**
Reported by Oliver on 2026-10-02: Lady Gaga showed under an Electronic filter.
Measured against MusicBrainz that day, she carries pop with 24 votes,
dance-pop 20 and electropop 17, beside electronic with 6. Six votes are not a
stray, so the rule above kept it. Ruled by Oliver the same day: a genre needs
at least half the votes of the artist's leading genre.
"""

from __future__ import annotations

# The fewest votes a genre needs to describe an artist or an album, where any
# of its genres reaches it. Ruled by Oliver on 2026-09-30: a single vote is a
# stray. The 1-vote measurement above is what it rests on.
FEWEST_VOTES = 2
# A genre is kept only with at least 1 / LEADING_SHARE of the votes the
# leading genre has: a half, ruled by Oliver on 2026-10-02.
LEADING_SHARE = 2


def believed(voted: tuple[tuple[str, int], ...]) -> tuple[str, ...]:
    """The genre names worth believing, in the order they were stated.

    A genre with fewer than `FEWEST_VOTES` is dropped, unless none reaches it,
    when every genre is kept rather than leaving nothing. Of the rest, a genre
    with under half the leading genre's votes is dropped too; the leading one
    always stays, so something is always kept.
    """
    if not any(count >= FEWEST_VOTES for _name, count in voted):
        return tuple(name for name, _count in voted)
    leading = max(count for _name, count in voted)
    return tuple(
        name
        for name, count in voted
        if count >= FEWEST_VOTES and count * LEADING_SHARE >= leading
    )
