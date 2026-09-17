"""A guide to the window: what the pictures are, then what they cannot say.

Two jobs, in this order. It NAMES the furniture, each entry carrying the real
icon the tray actually draws, so a picture somebody has just met can be
identified. Then it states the handful of rules the library depends on that no
screen can state for itself: what decides an album, what is never written and
what a rating is attached to.

Every entry carries the REAL icon, resolved through the same lookup the trays
use. Never a description in words where a picture is what is on screen; never
an emoji standing in for artwork. A guide showing something other than the
icon is worse than no guide, because it teaches the wrong picture.

**The same rule governs the WORDS a control wears.** Every control this names
by its label or its tooltip reads that string from wherever the control reads
it, never a copy typed here. Reported on 2026-09-08: the stopping paragraph
said the button reads "Stop looking" when it reads "Stop discovery". It had
been copied out of the specification, which was itself stale, so a guide
written to explain the window was quoting a document instead of the window.
That is the icon rule again in a different medium.

It is deliberately short. Anything a control says for itself through its own
tooltip is left to the control; what is here is what hovering cannot tell you.
The discovery procedure is its own module, `guide_discovery`; the way a picture
is drawn beside the words is `guide_pictures`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.auto_scroller import AutoScroller
from stellody.ui.dialogs import FirstStopDialog, close_row
from stellody.ui.guide_discovery import discovery_html
from stellody.ui.guide_pictures import img, row
from stellody.ui.layout_advice import layout_html
from stellody.ui.widgets import ReadingPane

DIALOG_WIDTH_PX = 720
DIALOG_HEIGHT_PX = 620


def _top_tray_html() -> str:
    """The tray along the top, in the order it is drawn."""
    return (
        "<h3>The tray along the top</h3>"
        + row(
            resources.choose_folder_icon_path(),
            "Choose music folder",
            "point it at your music once; it remembers.",
        )
        + row(
            resources.filter_icon_path(),
            "Filter",
            "narrow the library to the genres you tick. It stays pressed in "
            "while it is holding something back, because a narrowed library "
            "looks exactly like a small one. Show in its dialog waits until "
            "something is ticked, unless a filter is already on.",
        )
        + row(
            resources.search_icon_path(),
            "Search",
            "opens a box; typing narrows as you go. Press Return to ask the "
            "same phrase again once you have moved off what it found.",
        )
        + "<p>"
        + img(resources.previous_icon_path())
        + img(resources.play_icon_path())
        + img(resources.stop_icon_path())
        + img(resources.next_icon_path())
        + "The transport sits in the middle. Back goes to the start of the "
        "song first, then to the one before it, the way a CD player does.</p>"
        + row(
            resources.discover_icon_path(),
            "Discover",
            "looks for music you do not own yet, in the genres you tick. It "
            "sits at the right end, with its progress bars beside it while a "
            "run is going. The procedure is below.",
        )
        + "<p>"
        + img(resources.light_mode_icon_path())
        + img(resources.info_icon_path())
        + "the light or dark appearance, then Help. Help opens the same menu "
        "as Help on the menu bar: this guide, Library health, the two "
        "licences, About and a check for a new version.</p>"
    )


def _bottom_tray_html() -> str:
    """The strip along the foot, in the order it is drawn."""
    return (
        "<h3>The strip along the foot</h3>"
        + row(
            resources.donate_icon_path(),
            "Donate",
            "hands an address to your web browser and nothing more. It sits "
            "on its own at the left, ruled off, so it is not pressed by "
            "accident.",
        )
        + row(
            resources.rescan_icon_path(),
            "Rescan",
            "reads what has changed rather than starting again, so adding one "
            "album costs one folder.",
        )
        + row(
            resources.library_health_icon_path(),
            "Repair",
            "opens what was worked around: muddled numbers, disagreeing disc "
            "numbers, a file that could not be read. Accepting a correction "
            "keeps it, so it stops being reported at every start. The same "
            "screen takes accepted corrections back for one group of files, "
            "one whole album in a single press or everything at once.",
        )
        + "<p>"
        + img(resources.view_icon_path())
        + img(resources.medium_grid_icon_path())
        + "switch between the list and the sleeves; change the sleeve size.</p>"
        + "<p>"
        + img(resources.volume_icon_path())
        + img(resources.unmute_icon_path())
        + img(resources.exclusive_icon_path())
        + img(resources.equaliser_icon_path())
        + img(resources.shuffle_icon_path())
        + img(resources.repeat_icon_path())
        + "volume, mute, exclusive output, the equalizer, then shuffle and "
        "repeat, at the right end. Repeat has three settings: "
        "off, the album, then the one song. Every switch shows what pressing "
        "it would DO rather than what it is doing now.</p>"
        + "<p><b>Exclusive output</b> asks the sound device for the track "
        "exactly as the file holds it, with the system mixer out of the way. "
        "The mixer resamples everything it is given, so shared output is "
        "never bit perfect; exclusive output is, as long as the volume is at "
        "100% and the equalizer is off, since either one alters the samples "
        "on the way out. A device another application is holding will refuse: "
        "the music carries on through the mixer and the foot of the window "
        "says so. It is offered where the platform has a route past its "
        "mixer, which today means Windows.</p>"
    )


def _reading_html() -> str:
    """The parts of the window that are not buttons."""
    return (
        "<h3>What else the window is telling you</h3>"
        "<p>The <b>waveform</b> along the bottom is the whole of the playing "
        "track, loud parts and quiet. Click anywhere on it to jump there. The "
        "small bars below it move with the sound and can change nothing: they "
        "watch it after it has already gone to your speakers.</p>"
        "<p>The <b>stars</b> sit in a column on every song's row, beside its "
        "plays, so you can rate something without listening to it first. "
        "Press a star to rate the song; press the star a rating already sits "
        "on to clear it. With a song highlighted, the number keys 1 to 5 rate "
        "it and 0 clears it.</p>"
        "<p>The row of the track <b>playing</b> is painted pink, in the list "
        "and in an album open under the sleeves, whichever row you have "
        "selected.</p>"
        "<p>The <b>status line</b> names the track playing at its right hand "
        "end until it is stopped; it also says how much was found and says "
        "plainly when a song will not play and why.</p>"
    )


def _rules_html() -> str:
    """The rules the screens depend on and cannot state for themselves."""
    return (
        "<h3>Four rules behind what you see</h3>"
        f"<p><b>Your files are only ever read.</b> {APP_NAME} never writes to "
        "a music file. Everything it works out or you tell it lives in its "
        "own store, so a correction can always be taken back out and nothing "
        "you have collected is altered on disk. That is enforced by a test "
        "rather than intended.</p>"
        "<p><b>Folders group, tags name.</b> Which files make an album is "
        "decided by the folder they sit in, because a person filed them "
        "there; what the album is CALLED comes from the tags. Grouping by "
        "tags alone was tried against a real collection and split one "
        "classical recording five ways.</p>"
        "<p><b>A correction and a stated tag are different things.</b> "
        "Accepting a correction keeps the answer that was worked out for you. "
        "Stating a tag says what the album IS, over both the file and any "
        "rule, which is also how two folders of one release are joined into "
        "one album.</p>"
        "<p><b>Ratings follow the album, not the file.</b> They are held "
        "against what the album is rather than where it sits, so renaming or "
        "moving a folder keeps them. Only a song played to the end counts as "
        "a play.</p>"
    )


def guide_html() -> str:
    """The whole guide, resolving the real icons at the moment it opens."""
    return (
        f"<h2>A guide to {APP_NAME}</h2>"
        "<p>Every picture below is the one the window actually draws. Hover "
        "any button to see its name.</p>"
        f"{_top_tray_html()}<hr>"
        f"{_bottom_tray_html()}<hr>"
        f"{_reading_html()}<hr>"
        f"{discovery_html()}<hr>"
        f"{layout_html()}<hr>"
        f"{_rules_html()}"
    )


class GuideDialog(FirstStopDialog):
    """The guide, read rather than acted on."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guide")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        layout = QVBoxLayout(self)
        body = QTextBrowser(self)
        body.setHtml(guide_html())
        layout.addWidget(body)
        layout.addLayout(close_row(self))
        # It reads itself gently, as the licences and the About screen do; it
        # gives up the moment somebody scrolls it by hand.
        self.scroller = AutoScroller(body)
        self.pane = ReadingPane(body)
