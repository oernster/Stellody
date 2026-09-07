"""Where a discovery run's answer is written down, plus what it learned.

Two files, both inside Stellody's own directory beside the database and never
anywhere near the music. Ruled on 2026-09-06: one discovery file, replaced by
every completed run, rather than a directory of dated ones that becomes a thing
to tidy up. A run states what is missing at the moment it finished, which is
the only claim it can honestly make.

**Replaced atomically, so a failed write leaves the last good answer intact.**
Written beside the target and moved over it: a half-written file never exists
under the name anything reads.

**The genre cache is the other half of affording the result filter.** The
similarity catalogue names artists without saying what they play, so each has
to be asked about separately; that is the expensive part of a run. What was
learned is kept so the next run does not ask again, since the well-connected
artists recur constantly.
"""

from __future__ import annotations

import json
import os
import pathlib

from stellody.application.values import RunReport
from stellody.infrastructure import paths

DISCOVERY_NAME = "discovered.json"
CACHE_NAME = "artist-genres.json"
# Written beside the file it replaces, so the move is on one filesystem and
# cannot half happen.
PENDING_SUFFIX = ".writing"


def discovery_path() -> pathlib.Path:
    """Where the answer belongs, whether or not it is there yet."""
    return paths.data_dir() / DISCOVERY_NAME


def cache_path() -> pathlib.Path:
    """Where what was learned about candidates is kept between runs."""
    return paths.data_dir() / CACHE_NAME


def _written(where: pathlib.Path, content: object) -> None:
    """Put this where that is, atomically, else leave what is there alone."""
    pending = where.with_suffix(where.suffix + PENDING_SUFFIX)
    pending.write_text(
        json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(pending, where)


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
