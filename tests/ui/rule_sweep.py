"""Run in a process of its own: which tray rules draw nothing at some width.

Qt reads its scale once, as the application is built, so a sweep at the nine
tenths every window is drawn at needs a process started at that scale. The
suite's own application runs at one, where a rule a pixel wide always lands on
a pixel and the fault this looks for cannot happen.

Prints one line per rule that drew nothing: the width, then the rule's name.
Nothing printed means every rule drew at every width.
"""

from __future__ import annotations

import pathlib
import sys

from PySide6.QtWidgets import QApplication, QFrame

# Run as a script, so the repository and the test helpers are put on the path
# by hand before anything of Stellody's is imported; the imports wait in main.
HERE = pathlib.Path(__file__).resolve().parent
ROOTS = (HERE, HERE.parent, HERE.parents[1])

# A rule a device pixel wide at nine tenths moves through ten positions before
# the pattern repeats, so ten widths in a row put every rule on every one.
FIRST_WIDTH = 3812
WIDTHS = 10
HEIGHT = 1543
RULE_NAME = "TraySeparator"
# Either side of a rule's centre, in device pixels, where its line may land.
REACH = 3


def drew(window, rule: QFrame, colour: str) -> bool:
    """True where the rule's colour appears on the row through its middle."""
    image = window.grab().toImage()
    ratio = image.devicePixelRatio()
    centre = rule.mapTo(window, rule.rect().center())
    y = int(centre.y() * ratio)
    x = int(centre.x() * ratio)
    return any(
        image.pixelColor(column, y).name() == colour
        for column in range(x - REACH, x + REACH + 1)
    )


def main() -> None:
    """Build a window, sweep it across the widths and name what drew nothing."""
    sys.path[:0] = [str(root) for root in ROOTS]
    from recording_player import RecordingPlayer
    from tray_support import RememberingStore, build

    from stellody.ui.palette import Mode, palette_for
    from stellody.ui.theme import stylesheet

    application = QApplication(sys.argv)
    application.setStyleSheet(stylesheet(Mode.DARK))

    window = build(RememberingStore(), RecordingPlayer())
    window.show()
    colour = palette_for(Mode.DARK).border
    rules = window.findChildren(QFrame, RULE_NAME)
    print("rules", len(rules), flush=True)
    for width in range(FIRST_WIDTH, FIRST_WIDTH + WIDTHS):
        window.resize(width, HEIGHT)
        application.processEvents()
        for index, rule in enumerate(rules):
            if not drew(window, rule, colour):
                print("missing", width, index, flush=True)


if __name__ == "__main__":
    main()
