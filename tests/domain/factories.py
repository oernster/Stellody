"""Shared factories for the domain suite."""

from __future__ import annotations

from stellody.domain.track import CD_SAMPLE_RATE, Track, TrackSource


def make_track(**overrides: object) -> Track:
    """A valid track, with named fields overridden for a given case."""
    fields: dict[str, object] = {
        "source": TrackSource(path="a.flac"),
        "disc_number": 1,
        "track_number": 1,
        "title": "Mars",
        "artists": ("Holst",),
        "duration_ms": 1000,
        "sample_rate": CD_SAMPLE_RATE,
        "bit_depth": 16,
    }
    fields.update(overrides)
    return Track(**fields)  # type: ignore[arg-type]
