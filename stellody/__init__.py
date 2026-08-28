"""Stellody: a calm, local-first FLAC music player."""

from __future__ import annotations

__all__ = ["main"]


def main() -> int:
    """Entry point for the application."""
    from stellody.ui.launcher import launch

    return launch()
