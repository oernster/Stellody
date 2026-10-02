"""How long a discovery run has left, taken from the pace it has kept.

**The pace is measured, never assumed.** The gap the terms ask for says what a
request costs at best; a run meets refusals, each costing a second ask on the
spot and then a place in a later pass. An estimate built on the configured gap
would read as confident while being wrong by minutes on exactly the runs where
somebody most needs it. So nothing here knows what a request is supposed to
cost: it is handed what has happened and divides. FR-D36.

**The whole run is estimated, not the stage in hand.** The second stage asks
about every candidate the first turns up, so its size is unknown until the first
ends; it is also the longer half. An estimate naming only the first stage would
understate the wait by most of it, which is worse than saying nothing. While the
first stage runs, the second is projected from the candidates seen so far
against the artists finished so far. FR-D37.

Nothing here reads a clock. How long a run has been going is a fact about the
world, so it arrives as an argument; that is what lets every rule below be
tested with no run, no network and no waiting.
"""

from __future__ import annotations

# How many units of a stage must have finished before its pace means anything.
# A pace over one sample is wrong by a factor on any run whose first request met
# a refusal; a number that swings is trusted less than an honest silence.
# FR-D38.
MINIMUM_SAMPLES = 2
# What each kind of unit costs the catalogue in paced requests. A source artist
# is identified and then asked for its releases, both against the same host; a
# candidate is asked only what it plays. The similarity request rides a second
# host's gate and is not paced against these, so it is not counted.
#
# Approximate by design: an artist no catalogue could identify costs one request
# rather than two. That is exactly the kind of drift a measured pace absorbs,
# which is why the estimate of a run in progress uses these two numbers only as
# a RATIO between the stages and never as a cost in seconds. The price quoted
# before a run (FR-D52) does multiply by the gap, as arithmetic the dialog
# states is a floor.
REQUESTS_PER_SOURCE_ARTIST = 2
REQUESTS_PER_CANDIDATE = 1
# A series not yet looked up: a title search plus a group lookup to learn which
# series it is in, one read of that series, then one search for its stem to
# find volumes the series does not list yet. FR-D52, FR-D69, FR-D70. Measured
# against MusicBrainz on 2026-09-29 and 2026-09-30.
REQUESTS_PER_SERIES = 4
SECONDS_PER_MINUTE = 60


def pace(done: int, elapsed_s: float) -> float | None:
    """Seconds each finished unit took; None where too few have finished.

    None rather than a number, so a caller has to decide what to say when there
    is nothing to say. A zero would be a lie in the same shape as an answer.
    """
    if done < MINIMUM_SAMPLES or elapsed_s <= 0:
        return None
    return elapsed_s / done


def projected_candidates(seen: int, artists_done: int, artists_total: int) -> int:
    """How many candidates the whole first stage looks likely to turn up.

    Candidates arrive per source artist, so the rate they have arrived at is
    the best available reading of the rate they will keep arriving at. It
    overestimates where a run meets the same well-connected artists twice,
    since those are asked about once; it is a projection rather than a count
    and is replaced by the real total the moment the second stage begins.
    """
    if artists_done <= 0:
        return 0
    return round(seen / artists_done * artists_total)


def looking_up_seconds_left(
    done: int,
    total: int,
    elapsed_s: float,
    candidates_seen: int,
    series_ahead: int = 0,
) -> float | None:
    """Seconds left in the WHOLE run while the first stage is under way.

    Every stage in one number: the artists still to look up, the series still
    to look up (FR-D84), plus the candidates the run has yet to meet and will
    then have to ask about. The later stages are priced from the first stage's
    own pace, scaled by the ratio of what each unit costs the catalogue, since
    none of their units has happened to measure.
    """
    each = pace(done, elapsed_s)
    if each is None:
        return None
    first = max(total - done, 0) * each
    series = series_ahead * each * REQUESTS_PER_SERIES / REQUESTS_PER_SOURCE_ARTIST
    expected = projected_candidates(candidates_seen, done, total)
    last = expected * each * REQUESTS_PER_CANDIDATE / REQUESTS_PER_SOURCE_ARTIST
    return first + series + last


def series_seconds_left(
    done: int, total: int, elapsed_s: float, candidates_ahead: int
) -> float | None:
    """Seconds left while the series stage is under way. FR-D84.

    The series still to look up at this stage's own pace, plus the candidates
    the styles stage will ask about, known by now rather than projected and
    priced by the same ratio the first stage uses.
    """
    each = pace(done, elapsed_s)
    if each is None:
        return None
    last = candidates_ahead * each * REQUESTS_PER_CANDIDATE / REQUESTS_PER_SERIES
    return max(total - done, 0) * each + last


def narrowing_seconds_left(done: int, total: int, elapsed_s: float) -> float | None:
    """Seconds left while the second stage is under way.

    Nothing is projected here: by this point the first stage has finished and
    the number of candidates to ask about is known rather than guessed at.
    """
    each = pace(done, elapsed_s)
    if each is None:
        return None
    return max(total - done, 0) * each


def rounded_minutes(seconds: float) -> int:
    """The whole minutes to report, to the nearest one. FR-D35."""
    return round(seconds / SECONDS_PER_MINUTE)
