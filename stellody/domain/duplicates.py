"""Two copies of one recording: which of them is the one to use.

A collection built over years holds the same album twice: a lossless rip made
from the disc and a lossy one bought or ripped years earlier. Until M4A could
be decoded the second copy was invisible, so this question never arose. It
arises now, in two shapes.

**Inside one folder**, both rips sit side by side and each track appears twice.
Measured on the reference library, Fleetwood Mac's The Dance holds 17 FLAC and
17 M4A of the same performance, paired exactly on track number; the titles are
not the same text, since the M4A rip suffixes every one with "(Live)", so a
title is not what pairs them and a number is.

**Across two folders**, one album resolves twice and the two are told apart by
where they were found. That is right where tags genuinely cannot separate two
recordings, a symphony under two conductors being the case it was written for.
It is wrong when one of the two is simply a lossy copy of the other: they are
not two recordings, they are one recording twice; the lossless one is the
one a listener means. It also had a cost. Telling both apart moved the handle
of the album that was already there, so its cover, its album rating and every
track rating under it were orphaned by the arrival of a worse copy.

**A stated bit depth is what separates the two kinds**, rather than a list of
file extensions. The probe reports no depth for a file whose format states
none, which is exactly the lossy ones, so the distinction this module needs is
one the library already draws and already tests.
"""

from __future__ import annotations

from collections.abc import Sequence

from stellody.domain.album import FIRST_DISC
from stellody.domain.ordering import TrackCandidate


def is_lossless(candidates: Sequence[TrackCandidate]) -> bool:
    """Whether every track here states a stored depth.

    An album with nothing in it is not lossless: there is no evidence either
    way; answering true would let an empty group claim to be the copy worth
    keeping.
    """
    return bool(candidates) and all(item.bit_depth > 0 for item in candidates)


def kept_against_lossless(candidates: Sequence[TrackCandidate]) -> tuple[int, ...]:
    """Which of these to keep, dropping a lossy copy of a track already here.

    A file is dropped only where a lossless file in the same folder claims the
    same disc and track number. Everything else stays, which is what keeps this
    from quietly removing music:

    - a lossy file whose number nothing lossless claims is a track the lossless
      rip does not have, so it is kept;
    - a file with no track number is paired with nothing, so it is kept. The two
      untagged WAVs sitting beside one M4A in the reference library's copy of
      The Bends are that case; dropping either would have lost a recording
      to a rule about duplicates.
    """
    claimed = {
        _place(item)
        for item in candidates
        if item.bit_depth > 0 and item.tag_track is not None
    }
    if not claimed:
        return tuple(range(len(candidates)))
    return tuple(
        position
        for position, item in enumerate(candidates)
        if item.bit_depth > 0 or item.tag_track is None or _place(item) not in claimed
    )


def _place(item: TrackCandidate) -> tuple[int, int]:
    """Where a track sits, with a missing disc number read as the first disc.

    Measured on the reference library and it is the whole reason the pairing
    needs saying: the FLAC rip of The Dance states no disc number at all while
    the M4A rip beside it states disc 1. Compared as written, every one of the
    seventeen pairs missed each other and the album listed all thirty four.
    A file that names no disc is on the only disc there is.
    """
    return (item.tag_disc or FIRST_DISC, item.tag_track or 0)


def canonical_place(
    places: Sequence[tuple[str, str]],
    candidates_at: dict[tuple[str, str], Sequence[TrackCandidate]],
) -> tuple[str, str] | None:
    """Which of several albums resolving alike keeps the plain handle.

    Exactly one lossless copy among them means the others are lossy copies of
    it, so it is the one a listener means and it keeps the handle it already
    had. Anything else, none lossless or several, is left alone: those may be
    genuinely different recordings that tags cannot separate; every one of
    them is told apart by where it was found exactly as before.

    Answering None is therefore not a failure. It is the statement that this
    rule has nothing to say about these albums, which is the case that must not
    change, since changing it would move a handle that has been settled for as
    long as the library has existed.
    """
    lossless = [place for place in places if is_lossless(candidates_at[place])]
    return lossless[0] if len(lossless) == 1 else None
