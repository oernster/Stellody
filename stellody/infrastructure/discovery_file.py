"""Where a discovery run's answer is written down, plus what it learned.

Two files, both inside Stellody's own directory beside the database and never
anywhere near the music. Ruled on 2026-09-06: one discovery file, replaced by
every completed run, rather than a directory of dated ones that becomes a thing
to tidy up. A run states what is missing at the moment it finished, which is
the only claim it can honestly make.

**Replaced atomically, so a failed write leaves the last good answer intact.**
Written beside the target and moved over it: a half-written file never exists
under the name anything reads.

**What was written is read back rather than kept in hand.** A run's answer is
shown from this file rather than from the report still in memory when the run
ended, so one thing is authoritative and showing a past run's answer on some
later day costs nothing extra. FR-D28.

**A file that cannot be read is no results rather than no application.** The
same judgement the genre cache makes below: an answer nobody can show is a
disappointment, while an exception on the way out of a run that took eleven
minutes is worse.

**The genre cache is the other half of affording the result filter.** The
similarity catalogue names artists without saying what they play, so each has
to be asked about separately; that is the expensive part of a run. What was
learned is kept so the next run does not ask again, since the well-connected
artists recur constantly.
"""

from __future__ import annotations

import json
import pathlib

from stellody.application.values import RunReport
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.matching import ReleaseKind
from stellody.infrastructure import paths
from stellody.infrastructure.atomic import written as _written

DISCOVERY_NAME = "discovered.json"
CACHE_NAME = "artist-genres.json"


def discovery_path() -> pathlib.Path:
    """Where the answer belongs, whether or not it is there yet."""
    return paths.data_dir() / DISCOVERY_NAME


def cache_path() -> pathlib.Path:
    """Where what was learned about candidates is kept between runs."""
    return paths.data_dir() / CACHE_NAME


def _as_written(report: RunReport) -> dict:
    """The report in the shape the file carries it.

    The gaps are keyed by the artist they were found for, which is what makes
    the file usable as the resource a later stage reads. What could not be
    answered is carried beside them rather than dropped, since an artist
    nobody could look up is exactly the one somebody would otherwise read as
    complete.
    """
    return {
        "gaps": {
            gaps.artist: {
                "albums": [
                    {
                        "title": group.title,
                        "kinds": [str(kind) for kind in group.kinds],
                        "genres": list(group.genres),
                    }
                    for group in gaps.albums
                ],
                "artists": [
                    {"name": artist.name, "identifier": artist.identifier}
                    for artist in gaps.artists
                ],
            }
            for gaps in report.gaps
        },
        "unresolved": list(report.unresolved),
        "ambiguous": [
            {"artist": entry.artist, "identifiers": list(entry.identifiers)}
            for entry in report.ambiguous
        ],
        "failed": [
            {"artist": entry.artist, "reason": entry.reason} for entry in report.failed
        ],
    }


def write(report: RunReport) -> pathlib.Path:
    """Replace the discovery file with this run's answer; where it went.

    A report with nothing to say is refused rather than written, so a cancelled
    run cannot quietly replace a good file with an empty one.
    """
    if not report.is_writable:
        raise ValueError("this run has nothing to write")
    where = discovery_path()
    _written(where, _as_written(report))
    return where


def _listed(entry: dict, key: str) -> list:
    """The list under this key; empty where it is anything else."""
    found = entry.get(key)
    return found if isinstance(found, list) else []


def _kind_of(name: str) -> ReleaseKind:
    """The kind this name means; OTHER for one this version does not know.

    The same rule the catalogue client applies on the way in, so a file
    written by a later Stellody is read by an earlier one without a kind it
    has never heard of being mistaken for a plain album.
    """
    try:
        return ReleaseKind(name)
    except ValueError:
        return ReleaseKind.OTHER


def _album(entry: object) -> ReleaseGroup | None:
    """One album as the file carries it; None where it carries nothing usable.

    A title is required rather than defaulted, since the domain refuses an
    album without one and a record nobody can name is not one to offer.
    """
    if not isinstance(entry, dict):
        return None
    title = str(entry.get("title") or "").strip()
    if not title:
        return None
    return ReleaseGroup(
        title=title,
        kinds=tuple(_kind_of(str(kind)) for kind in _listed(entry, "kinds")),
        genres=tuple(str(genre) for genre in _listed(entry, "genres")),
    )


def _artist(entry: object) -> SimilarArtist | None:
    """One candidate artist as the file carries it; None where unusable."""
    if not isinstance(entry, dict):
        return None
    name = str(entry.get("name") or "").strip()
    if not name:
        return None
    return SimilarArtist(name=name, identifier=str(entry.get("identifier") or ""))


def read() -> tuple[Gaps, ...]:
    """What the last run found; empty where there is nothing to show.

    Order is the file's own, which is the order the run met the artists in.
    Anything the file carries that cannot be read as a gap is passed over
    rather than raising: a results screen missing one album is worth more than
    no results screen.
    """
    try:
        held = json.loads(discovery_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    gaps = held.get("gaps") if isinstance(held, dict) else None
    if not isinstance(gaps, dict):
        return ()
    found: list[Gaps] = []
    for artist, entry in gaps.items():
        if not isinstance(entry, dict) or not str(artist).strip():
            continue
        found.append(
            Gaps(
                artist=str(artist),
                albums=tuple(
                    album
                    for album in (_album(one) for one in _listed(entry, "albums"))
                    if album is not None
                ),
                artists=tuple(
                    candidate
                    for candidate in (_artist(one) for one in _listed(entry, "artists"))
                    if candidate is not None
                ),
            )
        )
    return tuple(found)


class FileDiscoveryResults:
    """What the last completed run wrote, read back when it is wanted.

    A thin object over `read` for the same reason `FileGenreMemory` is one
    over its pair: what a window needs is somewhere to read from; the file
    is already that.
    """

    def last_run(self) -> tuple[Gaps, ...]:
        """What the last run found; empty where there is nothing to show."""
        return read()


def remembered() -> dict[str, tuple[str, ...]]:
    """What earlier runs learned about candidate artists; empty when unusable.

    A cache that cannot be read is a cache that costs a few more requests,
    which is not worth failing a run over.
    """
    try:
        held = json.loads(cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(held, dict):
        return {}
    return {
        str(identifier): tuple(str(name) for name in genres)
        for identifier, genres in held.items()
        if isinstance(genres, list)
    }


def remember(known: dict[str, tuple[str, ...]]) -> None:
    """Keep what this run learned, so the next one asks about less.

    A cache that cannot be written is not worth reporting either: the next run
    simply asks again.
    """
    try:
        _written(cache_path(), {name: list(genres) for name, genres in known.items()})
    except OSError:
        return


class FileGenreMemory:
    """What earlier runs learned about candidates, kept beside the answer.

    A thin object over the two functions above rather than a store of its own:
    what a run needs is somewhere to read from and somewhere to write to;
    the file is already both.
    """

    def remembered(self) -> dict[str, tuple[str, ...]]:
        """What is already known about candidate artists."""
        return remembered()

    def remember(self, known: dict[str, tuple[str, ...]]) -> None:
        """Keep what this run learned for the next one."""
        remember(known)
