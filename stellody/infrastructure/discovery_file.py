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

from stellody.application.carrying_over import carried_over
from stellody.application.values import RunReport
from stellody.domain.discovery import Gaps, LastRun
from stellody.infrastructure import journal, paths
from stellody.infrastructure.atomic import written as _written
from stellody.infrastructure.file_shapes import (
    CREDITS,
    EARLIEST,
    INCLUDING,
    LATEST,
    MIXES,
    SERIES,
    YEARS,
    _listed,
    album_as,
    album_from,
    artist_as,
    artist_from,
    including_from,
    years_from,
)

DISCOVERY_NAME = "discovered.json"
# Renamed whenever the rule in `domain/genre_votes.py` changes, so what was
# kept under the old rule is never read again and each candidate is asked
# anew: `artist-genres.json` held single-vote strays (2026-10-01);
# `candidate-genres.json` held genres under half the leading votes (2026-10-02).
CACHE_NAME = "candidate-genres-2.json"
CACHE_JOURNAL_NAME = "candidate-genres-2.record"


def discovery_path() -> pathlib.Path:
    """Where the answer belongs, whether or not it is there yet."""
    return paths.data_dir() / DISCOVERY_NAME


def cache_path() -> pathlib.Path:
    """Where what was learned about candidates is kept between runs."""
    return paths.data_dir() / CACHE_NAME


def cache_journal_path() -> pathlib.Path:
    """Where a candidate's answer is noted, until the cache catches up."""
    return paths.data_dir() / CACHE_JOURNAL_NAME


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
                "albums": [album_as(group) for group in gaps.albums],
                "artists": [artist_as(artist) for artist in gaps.artists],
                SERIES: gaps.series,
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
        # The genres the run was scoped to, so the file says what it was asked
        # as well as what it found. Without them a file is an answer to a
        # question nobody wrote down, which is exactly what the results screen
        # was reported as failing to say.
        "ticked": list(report.ticked),
        YEARS: {EARLIEST: report.years.earliest, LATEST: report.years.latest},
        INCLUDING: {
            CREDITS: report.including.credits,
            SERIES: report.including.series,
            MIXES: report.including.mixes,
        },
    }


def write(report: RunReport) -> pathlib.Path:
    """Replace the discovery file with this run's answer; where it went.

    A report with nothing to say is refused rather than written, so a cancelled
    run cannot quietly replace a good file with an empty one.

    What the file already holds is read first, so an artist this run could not
    reach keeps the answer the last run got for it. A run may add to what is
    known and may correct it; it may not take an artist away because a service
    refused to talk about it.

    **An answer with a hole in it is written, with the hole named in it.**
    This refused to write at all until 2026-09-09, when Oliver ran his whole
    library twice and was shown nothing both times. Measured from the second
    run's own diary: 327 artists, 843 requests, 54 minutes, with ONE artist,
    Opeth, refused twice and then timed out. That one hole threw away the
    answer for the other 326.

    The rule it replaces was his and it was right about the thing it was
    aimed at: a file holding whichever artists a service felt like answering
    about is a different file every time. What has changed is that the file
    no longer has to be silent about it. What could not be answered for is
    written down beside what was, the results screen says how much is missing
    and names who, then a later run fills those artists in without asking
    about anybody else. An answer that says where its holes are is not
    the answer that was being guarded against.
    """
    if not report.is_writable:
        raise ValueError("this run has nothing to write")
    settled = carried_over(report, read())
    where = discovery_path()
    _written(where, _as_written(settled))
    return where


def read() -> LastRun:
    """What the last run found and what it was asked; empty where neither.

    Order is the file's own, which is artist order since `write` sorts by it.
    Anything the file carries that cannot be read as a gap is passed over
    rather than raising: a results screen missing one album is worth more than
    no results screen.

    The genres come back in the same reading as the gaps, so a file replaced
    between two reads cannot put one run's question above another run's
    answer. A file written before they were recorded carries none, which is an
    empty tuple rather than a failure.
    """
    try:
        held = json.loads(discovery_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return LastRun()
    gaps = held.get("gaps") if isinstance(held, dict) else None
    if not isinstance(gaps, dict):
        return LastRun()
    ticked = tuple(str(genre) for genre in _listed(held, "ticked") if str(genre))
    found: list[Gaps] = []
    for artist, entry in gaps.items():
        if not isinstance(entry, dict) or not str(artist).strip():
            continue
        found.append(
            Gaps(
                artist=str(artist),
                albums=tuple(
                    album
                    for album in (album_from(one) for one in _listed(entry, "albums"))
                    if album is not None
                ),
                artists=tuple(
                    candidate
                    for candidate in (
                        artist_from(one) for one in _listed(entry, "artists")
                    )
                    if candidate is not None
                ),
                series=entry.get(SERIES) is True,
            )
        )
    return LastRun(
        gaps=tuple(found),
        ticked=ticked,
        years=years_from(held),
        including=including_from(held),
    )


class FileDiscoveryResults:
    """What the last completed run wrote, read back when it is wanted.

    A thin object over `read` for the same reason `FileGenreMemory` is one
    over its pair: what a window needs is somewhere to read from; the file
    is already that.
    """

    def last_run(self) -> LastRun:
        """What the last run found and looked in; empty where there is neither."""
        return read()


def _cached() -> dict[str, tuple[str, ...]]:
    """What the cache file holds; empty where it holds nothing usable."""
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


def remembered() -> dict[str, tuple[str, ...]]:
    """What earlier runs learned about candidates, the cache plus the record.

    A cache that cannot be read is a cache that costs a few more requests,
    which is not worth failing a run over.

    The running record is read on top of the cache rather than instead of it.
    Asking about candidates is the long half of a run, so a run that died
    inside it had learned a great deal that the cache below never saw.
    """
    known = _cached()
    for entry in journal.replayed(cache_journal_path()):
        identifier, genres = entry.get("identifier"), entry.get("genres")
        if isinstance(identifier, str) and isinstance(genres, list):
            known[identifier] = tuple(str(name) for name in genres)
    return known


def note(identifier: str, genres: tuple[str, ...]) -> None:
    """Write one candidate's answer down now, so a run that dies keeps it."""
    journal.note(
        cache_journal_path(), {"identifier": identifier, "genres": list(genres)}
    )


def remember(known: dict[str, tuple[str, ...]]) -> None:
    """Keep what this run learned, so the next one asks about less.

    A cache that cannot be written is not worth reporting either: the next run
    simply asks again. The running record is dropped only once the cache holds
    what it held, since a record cleared beside a cache that was never written
    would throw away the answers it exists to protect.
    """
    try:
        _written(cache_path(), {name: list(genres) for name, genres in known.items()})
    except OSError:
        return
    journal.cleared(cache_journal_path())


class FileGenreMemory:
    """What earlier runs learned about candidates, kept beside the answer.

    A thin object over the two functions above rather than a store of its own:
    what a run needs is somewhere to read from and somewhere to write to;
    the file is already both.
    """

    def remembered(self) -> dict[str, tuple[str, ...]]:
        """What is already known about candidate artists."""
        return remembered()

    def note(self, identifier: str, genres: tuple[str, ...]) -> None:
        """Write this one candidate's answer down now."""
        note(identifier, genres)

    def remember(self, known: dict[str, tuple[str, ...]]) -> None:
        """Keep what this run learned for the next one."""
        remember(known)
