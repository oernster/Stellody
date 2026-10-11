"""Whether looking an artist up will go to the network or be answered at once.

A run's time is measured from the artists it has actually had to ask about,
since an answer read from memory costs nothing worth timing (see
`domain/estimating.py`). That needs both halves known: which finished artists
were asked, plus how many still to come will be. Both are read here off the
same memory the run answers from, before the artist is looked up, so the
prediction and the answer cannot consult two different recollections.

The prediction follows the questions the artist stage asks, in its order: who
the name is, then that artist's releases and similar artists. A name that
reached several artists is settled from the library's own titles by questions
of its own, so it is counted as asked rather than traced question by question;
that errs towards a longer wait rather than a shorter one.
"""

from __future__ import annotations

from dataclasses import dataclass

from stellody.application.artist_stage import SIMILAR_WANTED
from stellody.application.remembering import (
    ALBUMS,
    IDENTIFIERS,
    SIMILAR,
    Clock,
    Recollection,
    similar_key,
)


@dataclass(frozen=True, slots=True)
class Foreseen:
    """Answers whether one artist will cost a run any asking."""

    kept: Recollection
    now: Clock

    def __call__(self, artist: str) -> bool:
        """True where any question about this artist will go to the network."""
        when = self.now()
        kept = self.kept
        if not kept.holds(IDENTIFIERS, artist, kept.identifiers, when):
            return True
        identifiers = kept.identifiers[artist]
        if not identifiers:
            # Nobody under that name, already known: nothing more is asked.
            return False
        if len(identifiers) > 1:
            return True
        found = identifiers[0]
        return not (
            kept.holds(ALBUMS, found, kept.albums, when)
            and kept.holds(
                SIMILAR, similar_key(found, SIMILAR_WANTED), kept.similar, when
            )
        )
