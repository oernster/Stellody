"""A tray rule is drawn wherever the layout happens to put it.

Reported from a real window on 2026-09-18: the rule between mute and exclusive
output was missing from a screenshot while the rule after the equalizer was
there. Every window is drawn at nine tenths, so a rule one pixel wide is nine
tenths of a device pixel; measured, one position in every ten covered no pixel
at all and the rule vanished. Which rule vanished depended only on how wide the
window was, which is why a test at one fixed width never saw it.

The sweep runs in a process of its own, started at that scale, because Qt reads
its scale once as the application is built; `rule_sweep.py` says why.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

from stellody.ui.interface_scale import INTERFACE_SCALE, SCALE_VARIABLE

SWEEP = pathlib.Path(__file__).resolve().parent / "rule_sweep.py"
# Generous against a cold start, which is most of what the sweep spends.
SWEEP_TIMEOUT_S = 120


def _sweep() -> list[str]:
    environment = dict(os.environ)
    environment[SCALE_VARIABLE] = str(INTERFACE_SCALE)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    finished = subprocess.run(
        [sys.executable, str(SWEEP)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=SWEEP_TIMEOUT_S,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    return finished.stdout.splitlines()


def test_every_rule_is_drawn_at_every_width() -> None:
    """Each rule shows its colour at each of ten widths in a row."""
    lines = _sweep()
    counted = [line for line in lines if line.startswith("rules ")]
    assert counted and int(counted[0].split()[1]) > 0, "the sweep found rules"
    missing = [line for line in lines if line.startswith("missing ")]
    assert not missing, f"rules that drew nothing (width, index): {missing}"
