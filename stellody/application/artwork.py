"""Finding an album's cover among the files a scan already recorded.

A cover sits in one of two places: a file beside the music, which the walk
ranked with the likeliest name first, else a picture inside the audio itself.
Measured over the reference library, 395 folders of 510 carry a file beside
the music, 114 more carry only an embedded picture and exactly one carries
neither. The embedded case is a main path rather than a fallback, so it is
gathered here rather than left to a later milestone.

An album can span several folders, since sibling disc folders merge into one
album, so candidates are gathered across every folder its tracks live in and
offered in the order the tracks are in. A folder is only asked for its audio
when the scan recorded a picture inside it, which keeps an album of fifteen
tracks from being opened fifteen times to learn there is nothing there.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from stellody.application.ports import ArtworkPort, FolderRecord
from stellody.domain.album import Album


@dataclass(frozen=True, slots=True)
class AlbumArtSources:
    """Where one album's cover might be found, likeliest first."""

    key: str
    sidecars: tuple[str, ...] = ()
    audio: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("art sources need an album to belong to")


def sources_for(
    albums: tuple[Album, ...], records: tuple[FolderRecord, ...]
) -> tuple[AlbumArtSources, ...]:
    """Each album's cover candidates, gathered across the folders it spans."""
    by_folder = {record.folder: record for record in records}
    gathered = []
    for album in albums:
        sidecars: list[str] = []
        audio: list[str] = []
        seen: set[str] = set()
        for track in album.tracks:
            path = track.source.path
            record = by_folder.get(os.path.dirname(path))
            if record is None:
                continue
            if record.folder not in seen:
                seen.add(record.folder)
                if record.art_path:
                    sidecars.append(record.art_path)
            if record.has_embedded_art and path not in audio:
                audio.append(path)
        gathered.append(
            AlbumArtSources(
                key=album.identity.art_key,
                sidecars=tuple(sidecars),
                audio=tuple(audio),
            )
        )
    return tuple(gathered)


class AlbumArt:
    """An album's cover, read once and kept at the size it is drawn.

    Two answers rather than one, for the same reason a waveform has two:
    reading a cover decodes an image and an embedded one opens the audio file
    to get at it, which is too slow to do while a library is being drawn.
    `remembered` is instant and may be nothing; `reading` is slow and settles
    it.
    """

    def __init__(self, artwork: ArtworkPort) -> None:
        self._artwork = artwork

    def remembered(self, sources: AlbumArtSources) -> bytes | None:
        """This album's cover if one is already kept; None otherwise.

        Never decodes, so it is safe to ask while drawing.
        """
        return self._artwork.remembered(sources.key)

    def reading(self, sources: AlbumArtSources) -> bytes | None:
        """This album's cover, reading it when it is not already kept.

        Slow. It belongs off the interface thread. None when nothing is kept
        and nothing there yields an image, which is not an error: an album
        without a cover shows a placeholder.

        **The store is asked whatever the candidates say.** An album with
        nowhere local to look was once answered here without asking, on the
        reasoning that opening nothing is cheaper than asking a decoder to
        open nothing. That is the only album a chooser is ever offered for;
        a chosen picture has no file beside the music to be found by, so the
        saving cost every chosen cover its next restart.
        """
        return self._artwork.read(sources.key, sources.sidecars, sources.audio)
