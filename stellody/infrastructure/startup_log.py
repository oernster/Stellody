"""Why Stellody could not start, written down where somebody can read it.

A packaged build has no console, so an exception on the way up goes nowhere
at all: the application simply does not appear, which from the outside is
indistinguishable from never having been started. That happened once after an
install and left nothing to go on but the setup program's own log, which had
already said it started something.

**It is kept in Stellody's own data directory, beside the diary.** Ruled by
Oliver on 2026-09-09, the same ruling that moved the diary. It was written to
the system's temporary directory so that it would land beside the setup
program's own log; what that overlooked is the packaging Stellody actually
ships on Linux. A flatpak gets a private temporary filesystem, discarded when
the process ends, so the one report explaining why an application never
appeared was written where the person who ran it could not read it and was
then thrown away. A report nobody can reach is the same as no report, which is
the state this module exists to end.

The setup program's log is on Windows, where the two directories are both
readable anyway; the account of a failed start now sits with the account of a
normal one, which is the pair somebody actually reads together.

Nothing here may raise, which is why the guard is wider than a write: this runs
while the application is already on its way down; asking where the data
directory is can itself fail on a machine with no resolvable home.
"""

from __future__ import annotations

import pathlib

from stellody.infrastructure.paths import data_location

LOG_NAME = "stellody-startup.log"


def location() -> pathlib.Path:
    """Where the report belongs, whether or not it is there."""
    return data_location() / LOG_NAME


def report_failure(trace: str) -> pathlib.Path | None:
    """Write down why Stellody could not start; None when even that failed.

    Nothing here may raise. It runs while the application is already on its
    way down; a reporter that throws would replace the fault being reported
    with one of its own. That is why the directory is made here rather than
    assumed: a start that failed may well have failed before anything else
    made it.
    """
    try:
        report = location()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(trace, encoding="utf-8")
    except (OSError, RuntimeError):
        return None
    return report


def clear() -> None:
    """Drop any earlier report, so what is there is about the run in hand."""
    try:
        location().unlink(missing_ok=True)
    except (OSError, RuntimeError):
        return
