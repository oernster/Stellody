"""How long a discovery run has left, taken from the pace it has kept.

**The pace is measured, never assumed.** The gap the terms ask for says what a
request costs at best; a run meets refusals, each costing up to three attempts
with a lengthening wait between them. An estimate built on the configured gap
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
# which is why these two numbers are used only as a RATIO between the stages
# and never as a cost in seconds.
REQUESTS_PER_SOURCE_ARTIST = 2
REQUESTS_PER_CANDIDATE = 1
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
    done: int, total: int, elapsed_s: float, candidates_seen: int
) -> float | None:
    """Seconds left in the WHOLE run while the first stage is under way.

    Both halves in one number: the artists still to look up, plus the candidates
    the run has yet to meet and will then have to ask about. The second half is
    priced from the first half's own pace, scaled by the ratio of what each unit
    costs the catalogue, since no second-stage unit has happened to measure.
    """
    each = pace(done, elapsed_s)
    if each is None:
        return None
    first = max(total - done, 0) * each
    expected = projected_candidates(candidates_seen, done, total)
    second = expected * each * REQUESTS_PER_CANDIDATE / REQUESTS_PER_SOURCE_ARTIST
    return first + second


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
