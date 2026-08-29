"""Why Stellody could not start, written down where somebody can read it.

A packaged build has no console, so an exception on the way up goes nowhere
at all: the application simply does not appear, which from the outside is
indistinguishable from never having been started. That happened once after an
install and left nothing to go on but the setup program's own log, which had
already said it started something.

This writes beside that log so one directory holds both halves of the story.
"""

from __future__ import annotations

import pathlib
import tempfile

LOG_NAME = "stellody-startup.log"


def location() -> pathlib.Path:
    """Where the report belongs, whether or not it is there."""
    return pathlib.Path(tempfile.gettempdir()) / LOG_NAME


def report_failure(trace: str) -> pathlib.Path | None:
    """Write down why Stellody could not start; None when even that failed.

    Nothing here may raise. It runs while the application is already on its
    way down; a reporter that throws would replace the fault being reported
    with one of its own.
    """
    report = location()
    try:
        report.write_text(trace, encoding="utf-8")
    except OSError:
        return None
    return report


def clear() -> None:
    """Drop any earlier report, so what is there is about the run in hand."""
    try:
        location().unlink(missing_ok=True)
    except OSError:
        return
