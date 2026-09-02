"""Ports: the interfaces the application layer needs the world to satisfy.

Every one is a Protocol, so infrastructure satisfies it structurally and the
test suite can supply a hand-written fake without a mocking library.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Protocol

from stellody.application.values import (
    AudioProperties,
    FolderListing,
    FolderRecord,
    ReleaseInfo,
)
from stellody.domain.equalising import Equalisation
from stellody.domain.listening import Listening
from stellody.domain.overrides import Override
from stellody.domain.playback import (
    OutputReport,
    OutputRequest,
    PlaybackPosition,
    PlaybackState,
)
from stellody.domain.track import TrackSource
from stellody.domain.waveform import Envelope

# Asked between one unit of slow work and the next: True means stop. It lives
# here rather than beside one of its callers because two ports now take one,
# the scan and the measurement; a type describing a port belongs with the
# ports.
CancelledCheck = Callable[[], bool]
# Handed the shape as far as it has been read, so slow work can be watched
# rather than waited on.
ShapeSoFar = Callable[[Envelope], None]


class LibraryWalker(Protocol):
    """Finds the folders of a music library. Never opens an audio file."""

    def walk(self, root: str) -> Iterable[FolderListing]:
        """Yield one listing per folder containing audio."""
        ...

    def count(self, root: str) -> int:
        """How many folders the walk will yield, counted without reading one.

        A scan cannot say how far through it is without knowing how far there
        is to go; the walk itself only knows that once it has finished.
        """
        ...


class MediaProbe(Protocol):
    """Reads properties and tags out of one audio file."""

    def read(self, path: str) -> AudioProperties | None:
        """Properties of the file; None when it cannot be read."""
        ...


class TextReader(Protocol):
    """Reads a small text file, such as a cue sheet."""

    def read(self, path: str) -> str | None:
        """The file's text; None when it cannot be read."""
        ...


class SettingsStore(Protocol):
    """Small persistent preferences: appearance, library root, close behaviour."""

    def get_setting(self, key: str, default: str = "") -> str:
        """The stored value for a key; the default when it has never been set."""
        ...

    def set_setting(self, key: str, value: str) -> None:
        """Store a value against a key."""
        ...


class LibraryStore(Protocol):
    """Stellody's own persistent state. The only thing it ever writes."""

    def all_overrides(self) -> tuple[Override, ...]:
        """Every correction a listener has accepted.

        The whole set at once, since resolution needs all of it to assemble
        anything and it holds only what somebody has actually accepted.
        """
        ...

    def accept_overrides(self, accepted: tuple[Override, ...]) -> None:
        """Record corrections as accepted, replacing any already standing."""
        ...

    def discard_overrides(self, unwanted: tuple[Override, ...]) -> None:
        """Take corrections back, so the automatic rules show through again."""
        ...

    def file_signatures(self) -> Mapping[str, tuple[int, int]]:
        """Every known audio file against its recorded size and mtime."""
        ...

    def load_folders(self) -> tuple[FolderRecord, ...]:
        """Every folder record currently held."""
        ...

    def save_folder(self, record: FolderRecord) -> None:
        """Replace one folder's record with a freshly scanned one."""
        ...

    def mark_absent(self, seen_paths: frozenset[str]) -> int:
        """Flag files no longer on disk. Never deletes their metadata."""
        ...


class ClosableStore(LibraryStore, Protocol):
    """A store that holds a handle of its own and must give it back.

    The scan opens its own store on its own thread, so something has to close
    it when the thread is done.
    """

    def close(self) -> None:
        """Release the handle."""
        ...


class ListeningStore(Protocol):
    """Where a rating and a play count are kept, which is never the music."""

    def all_listening(self) -> Mapping[str, Listening]:
        """Every track anybody has rated or played, by its handle."""

    def set_listening(self, handle: str, path: str, record: Listening) -> None:
        """Write one track's record, replacing whatever was there.

        The path is recorded beside the handle so a row can be traced back to
        a file by hand. Nothing reads it: the handle is what a record is found
        by, since a path is the one thing about a track that does not survive
        the folder being renamed.
        """


class WaveformPort(Protocol):
    """Measures how loud a file is all the way along, then remembers it.

    Measuring is a decode of the whole file, so the two questions are kept
    apart: one is instant and may know nothing, the other is slow and settles
    it. Nothing here raises for a file that cannot be read; a picture that
    cannot be drawn is not a reason to stop a track playing.
    """

    def remembered(self, path: str) -> Envelope | None:
        """The shape of this file if it has been measured; None otherwise."""
        ...

    def measure(
        self, path: str, cancelled: CancelledCheck | None = None
    ) -> Envelope | None:
        """The shape of this file, measuring it if need be; None if it cannot be.

        Slow. Belongs off the interface thread. A measurement asked to stop
        gives up at the next block it reads and answers None, keeping nothing:
        half a file is not a shape and would be wrong on every redraw after.
        """
        ...

    def frames_in(self, path: str) -> int | None:
        """How many frames the whole file holds; None when it cannot be read.

        A track takes its share of a file's shape by frame, so the share
        cannot be worked out without this.
        """
        ...


class PlaybackPort(Protocol):
    """Turns a track source into sound. The only thing that touches a device.

    Every method is safe to call in any state, so the application never has to
    guard a transport command with a state check.
    """

    @property
    def state(self) -> PlaybackState:
        """Where the transport is right now."""
        ...

    def load(self, source: TrackSource, request: OutputRequest) -> OutputReport:
        """Open `source` on a device and report what was actually opened.

        Stops whatever was playing first. Raises when the source cannot be
        decoded at all; a device refusing the requested mode is a fallback
        recorded in the report, not an error.
        """
        ...

    def queue_next(self, source: TrackSource | None) -> bool:
        """Line up what follows, opened before the current track needs it.

        Answers whether it can actually follow without a seam. A source the
        open device cannot carry has to wait for a new one, which is a gap
        however it is arranged, so the answer is honest rather than hopeful.
        None clears whatever was lined up.
        """
        ...

    @property
    def crossings(self) -> int:
        """How many lined-up sources the device has run into by itself.

        A count rather than a signal, so a caller that was not looking at the
        moment it happened still learns about it. It belongs to the loaded
        session, so it starts again from nothing at every load.
        """
        ...

    def play(self) -> None:
        """Start or resume. Does nothing when no source is loaded."""
        ...

    def pause(self) -> None:
        """Hold position without releasing the device."""
        ...

    def stop(self) -> None:
        """End playback and release the device."""
        ...

    def seek(self, frame: int) -> None:
        """Move to a frame offset within the loaded source, clamped to it."""
        ...

    def position(self) -> PlaybackPosition | None:
        """How far the DECODE has reached; None when nothing is loaded.

        This runs ahead of what is coming out of the speakers, by whatever is
        sitting in the buffer. Use `Transport.position` for a figure fit to
        show somebody.
        """
        ...

    @property
    def lead_frames(self) -> int:
        """How far the decode runs ahead of what is audible, in frames.

        A property of the device the port opened rather than of the track, so
        the port is the only thing that can answer it.
        """
        ...

    @property
    def finished(self) -> bool:
        """Whether the loaded source has played all the way through.

        A track reaching its end is not a state the transport is in, it is an
        event nothing was told about: the device is still open and the position
        has simply stopped moving. Something has to ask.
        """
        ...

    def set_equalisation(self, equalisation: Equalisation) -> None:
        """Shape what is heard, else leave it exactly as the file holds it.

        A flat setting must cost nothing in the signal path rather than
        little, so an implementation applies no arithmetic at all there.
        """
        ...

    def set_volume(self, level: float) -> None:
        """Set output gain, where 0.0 is silence and 1.0 is unattenuated."""
        ...

    @property
    def levels(self) -> tuple[float, ...]:
        """How loud each of the equalizer's bands was in the last block out.

        One height per band, from 0.0 to 1.0. Read by whatever is drawing
        rather than pushed to it, so an implementation is never waiting on a
        painter and a reader that falls behind misses measurements instead of
        holding up the sound.
        """
        ...

    def set_visualising(self, on: bool) -> None:
        """Start or stop measuring what goes out.

        Off must cost nothing rather than little, the same bargain the
        equalizer makes: nobody watching means no measurement taken.
        """
        ...

    def close(self) -> None:
        """Release every resource. The port is unusable afterwards."""
        ...


class EmbeddedPicturePort(Protocol):
    """Reads a cover picture out of an audio file; nothing else.

    Kept apart from the store that keeps covers so that the module opening
    music files and the module writing to disk are never the same module.
    """

    def picture(self, path: str) -> bytes | None:
        """The cover embedded in this file; None when it holds none."""
        ...


class ArtworkPort(Protocol):
    """Reads an album's cover, then remembers it at the size it is drawn.

    Reading decodes an image; an embedded cover means opening the audio
    file to reach it, so the two questions are kept apart exactly as they are
    for a waveform: one is instant and may know nothing, the other is slow and
    settles it. Nothing here raises for a file that cannot be read; an album
    without a cover shows a placeholder rather than an error.
    """

    def remembered(self, key: str) -> bytes | None:
        """The cover kept for this album; None when none is kept."""
        ...

    def read(
        self, key: str, sidecars: tuple[str, ...], audio: tuple[str, ...]
    ) -> bytes | None:
        """The cover from the first candidate that yields one; None if none does.

        Files beside the music are tried before pictures inside the audio,
        since reading a file is cheaper than opening a decoder. Slow. It
        belongs off the interface thread.
        """
        ...

    def keep_chosen(self, key: str, data: bytes) -> bytes | None:
        """Keep a picture somebody chose; the kept copy, else None.

        Kept apart from what a read keeps, because a chosen cover has no file
        beside the music to be checked against. It therefore outlives a rescan
        and is preferred to whatever the folder holds, which is the whole
        point of having chosen it.
        """
        ...


class ReleaseSource(Protocol):
    """Where the newest published release is read from."""

    def latest_release(self) -> ReleaseInfo | None:
        """The newest published release; None when it could not be read.

        None covers every way the question can go unanswered: no network, a
        refusal, a body that does not parse. The caller cannot tell them apart
        and has no use for the difference, since all of them mean ask again
        later rather than tell the listener anything.
        """
        ...
