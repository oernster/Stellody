"""Stellody: a calm, local-first FLAC music player."""

from __future__ import annotations

__all__ = ["main"]


def main() -> int:
    """Entry point for the application."""
    from stellody.composition import main as run

    return run()
