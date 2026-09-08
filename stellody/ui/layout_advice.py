"""How a library wants laying out, said once and read in two places.

The guide explains it at length; the note shown before somebody picks a folder
for the first time says the short version and points at the guide. Both read
these words rather than each keeping a copy, since two statements of one rule
are two chances for them to come to disagree.

**Every line here is something the code does, not something it intends.** The
folder rule comes from `domain/grouping.py`, the joining rule from
`domain/folding.py`, the cue rules from `domain/cue.py` and `application/scan.py`,
the duplicate rule from `domain/duplicates.py`. A guide describing behaviour the
code does not have is worse than none, because it is believed.

The note is shown BEFORE the folder is chosen rather than after. Told afterwards
that a layout matters, somebody has already picked; told first, they can go and
look at what they have.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from stellody.shared.version import APP_NAME
from stellody.ui.dialogs import FirstStopDialog

NOTE_WIDTH_PX = 560

READ_THE_GUIDE = "Read the guide"
CHOOSE_ANYWAY = "Choose a folder"

HEADING = "How to lay a library out"


def layout_html() -> str:
    """The whole of the folder advice, as the guide shows it."""
    return (
        f"<h3>{HEADING}</h3>"
        f"<p>{APP_NAME} reads what it finds rather than asking you to file it "
        "a particular way. These are the rules it reads BY, so a collection "
        "laid out along them comes out looking the way you expect.</p>"
        "<p><b>One album to a folder.</b> The folder is what groups; the tags "
        "say what the album is called. Where the tags are silent the folder "
        "name answers.</p>"
        "<p><b>Discs of one release sit side by side.</b> Sibling folders "
        "named CD1 and CD2 become one album; so does one ending in (Disc 2). "
        "A disc stated in the folder name wins over a DISCNUMBER tag, because "
        "a person wrote the folder name. A bonus folder that names no number "
        "is placed after the album's last disc.</p>"
        "<p><b>Two folders naming the same album become one.</b> Where the "
        "album artist AND the album title agree, the folders join, wherever "
        "they sit on disk. That is how a release split in two is put back "
        "together. It is also the one thing to watch: two rips that name "
        "nothing agree with each other, so they join as well.</p>"
        "<p><b>Name a rip the disc could not identify.</b> A ripper that "
        "cannot place a disc writes Unknown Artist and Unknown Title. Those "
        "are read as saying nothing, so the file's own tags answer instead; "
        "where those are empty too, the album has no name to be told apart "
        "by. Giving such a folder a real album artist and title is the single "
        "most useful thing you can do to a collection.</p>"
        "<p><b>One file plus a cue sheet is an album.</b> The sheet is read "
        "only where the folder holds exactly one audio file. A folder holding "
        "a cue sheet beside separate tracks is read as the tracks.</p>"
        "<p><b>A lossless copy wins.</b> Where a lossy file and a lossless "
        "one in the same folder are the same track, the lossy one is passed "
        "over rather than shown twice.</p>"
        "<p><b>A compilation wants Various Artists.</b> Put it in the album "
        "artist and the album groups as one rather than splitting by "
        "performer.</p>"
    )


NOTE_HTML = (
    f"<p><b>Before you choose.</b> {APP_NAME} reads a library the way it "
    "finds it. Two things matter most:</p>"
    "<ul>"
    "<li>One album to a folder, with discs of one release side by side.</li>"
    "<li>Give any rip your ripper could not identify a real album artist and "
    "title. Rips that name nothing are read as naming the same album, so they "
    "arrive as one.</li>"
    "</ul>"
    "<p>The guide says the rest. You can read it now or carry on.</p>"
)


class LayoutAdviceDialog(FirstStopDialog):
    """The short note, shown once before a first folder is chosen.

    It answers whether the guide was asked for rather than whether it was
    dismissed, since both buttons carry on to the folder picker: this exists
    to inform a choice, never to stand in the way of one.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(HEADING)
        self.setMinimumWidth(NOTE_WIDTH_PX)
        self.wants_guide = False
        layout = QVBoxLayout(self)
        words = QLabel(NOTE_HTML, self)
        words.setWordWrap(True)
        layout.addWidget(words)
        # Carrying on leads, so the control this opens focused is also the one
        # Enter presses. Focused on one button while Enter worked another, the
        # ring would be pointing at something the keyboard was not doing.
        self.choose_button = QPushButton(CHOOSE_ANYWAY, self)
        self.choose_button.setDefault(True)
        self.choose_button.clicked.connect(self.accept)
        layout.addWidget(self.choose_button)
        self.guide_button = QPushButton(READ_THE_GUIDE, self)
        self.guide_button.clicked.connect(self._ask_for_the_guide)
        layout.addWidget(self.guide_button)

    def _ask_for_the_guide(self) -> None:
        """Say the guide was wanted, then let the folder picker follow."""
        self.wants_guide = True
        self.accept()
