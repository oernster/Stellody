"""What a library holds that can tell two artists of one name apart. FR-D09.

A name reaching several artists in a catalogue used to end there: choosing
between them on a listener's behalf would file one discography under another
artist's name, silently. Measured on 2026-09-27, that left 36 of a library's
source artists unasked, Anyma, Bonobo and Max Cooper among them, because
somebody somewhere else once used the same name.

**The library already says which one it means.** An album held under that
name (or a track credited to it) is something only one of the namesakes made.
Asking a catalogue who is credited on that title answers the question with
the listener's own shelf rather than with a ranking, so it is evidence and not
a guess. Nothing here asks anything: it gathers what can be asked about.

Pure: no I/O, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from stellody.domain.album import Album
from stellody.domain.text import (
    bare_title,
    catalogue_key,
    comparison_key,
    credit_parts,
    is_various_artists,
)


class EvidenceKind(StrEnum):
    """What a piece of evidence is a title of, which decides what is searched."""

    ALBUM = "album"
    TRACK = "track"


@dataclass(frozen=True, slots=True)
class Evidence:
    """One title the library holds under an artist's name."""

    kind: EvidenceKind
    title: str
    artist: str

    @property
    def question(self) -> str:
        """How the catalogue's answer about this is remembered.

        By the catalogue's reading of the name, since that is what it is asked
        and two spellings of one name get one answer.
        """
        return f"{self.kind}|{catalogue_key(self.artist)}|{comparison_key(self.title)}"


EvidenceIndex = dict[str, tuple[Evidence, ...]]


def _added(
    into: dict[str, dict[tuple[EvidenceKind, str], Evidence]], found: Evidence
) -> None:
    """File one piece under its artist, once per title of each kind."""
    pieces = into.setdefault(comparison_key(found.artist), {})
    pieces.setdefault((found.kind, comparison_key(found.title)), found)


def evidence_by_artist(albums: tuple[Album, ...]) -> EvidenceIndex:
    """Every title held under each artist's name, albums before tracks.

    Built once for a run, as `held_by_artist` is. Albums first because an
    album is filed by the listener and so is the stronger statement; tracks
    after, since an artist met only through a compilation has nothing else.
    An album or a track is filed under its whole artist and under each part
    of it, since FR-D53 may have taken that name apart to find the one being
    settled.
    """
    by_album: dict[str, dict[tuple[EvidenceKind, str], Evidence]] = {}
    by_track: dict[str, dict[tuple[EvidenceKind, str], Evidence]] = {}
    for album in albums:
        artist = album.identity.album_artist
        if not is_various_artists(artist):
            title = bare_title(album.identity.title)
            for name in (artist, *credit_parts(artist)):
                _added(by_album, Evidence(EvidenceKind.ALBUM, title, name))
        for track in album.tracks:
            title = bare_title(track.title)
            for credit in track.artists:
                for name in (credit, *credit_parts(credit)):
                    _added(by_track, Evidence(EvidenceKind.TRACK, title, name))
    return {
        key: tuple(by_album.get(key, {}).values())
        + tuple(by_track.get(key, {}).values())
        for key in by_album.keys() | by_track.keys()
    }


def evidence_for(index: EvidenceIndex, artist: str) -> tuple[Evidence, ...]:
    """What the library holds under this artist's name, however it is spelled."""
    return index.get(comparison_key(artist), ())


def settled_by(
    identifiers: tuple[str, ...], credited: tuple[str, ...]
) -> frozenset[str]:
    """Which of the namesakes a catalogue credited on a held title."""
    return frozenset(identifiers) & frozenset(credited)
