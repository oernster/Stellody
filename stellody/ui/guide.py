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

It is deliberately short. Anything a control says for itself through its own
tooltip is left to the control; what is here is what hovering cannot tell you.
"""

from __future__ import annotations

import pathlib

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.auto_scroller import AutoScroller
from stellody.ui.dialogs import FirstStopDialog, close_row
from stellody.ui.widgets import ReadingPane

DIALOG_WIDTH_PX = 720
DIALOG_HEIGHT_PX = 620

# Bigger than the words around it on purpose. This screen is read to tell one
# picture from another rather than to skim a sentence; the artwork here is
# detailed enough that at body-text size two icons somebody is trying to
# separate read as the same smudge.
INLINE_ICON_PX = 30


def _img(path: pathlib.Path | None, px: int = INLINE_ICON_PX) -> str:
    """One bundled icon as an inline image; nothing at all when it is absent.

    Empty rather than a placeholder: the line still reads without its picture
    and a missing asset must never stop the guide opening.

    Centred on the line rather than sat on its baseline, since at this size a
    baseline-aligned picture hangs below the words it leads and reads as a row
    that has slipped.
    """
    if path is None:
        return ""
    return (
        f'<img src="file:///{str(path).replace(chr(92), "/")}" '
        f'width="{px}" height="{px}" style="vertical-align: middle"> '
    )


def _row(path: pathlib.Path | None, name: str, text: str) -> str:
    """One control's line, led by the picture its button actually draws."""
    return f"<p>{_img(path)}<b>{name}</b>: {text}</p>"


def _top_tray_html() -> str:
    """The tray along the top, in the order it is drawn."""
    return (
        "<h3>The tray along the top</h3>"
        + _row(
            resources.choose_folder_icon_path(),
            "Choose music folder",
            "point it at your music once; it remembers.",
        )
        + _row(
            resources.filter_icon_path(),
            "Filter",
            "narrow the library to the genres you tick. It stays pressed in "
            "while it is holding something back, because a narrowed library "
            "looks exactly like a small one.",
        )
        + _row(
            resources.search_icon_path(),
            "Search",
            "opens a box; typing narrows as you go. Press Return to ask the "
            "same phrase again once you have moved off what it found.",
        )
        + "<p>"
        + _img(resources.previous_icon_path())
        + _img(resources.play_icon_path())
        + _img(resources.stop_icon_path())
        + _img(resources.next_icon_path())
        + "The transport sits in the middle. Back goes to the start of the "
        "song first, then to the one before it, the way a CD player does.</p>"
        + "<p>"
        + _img(resources.volume_icon_path())
        + _img(resources.unmute_icon_path())
        + _img(resources.light_mode_icon_path())
        + _img(resources.info_icon_path())
        + "volume, mute, the light or dark appearance, then Help.</p>"
    )


def _bottom_tray_html() -> str:
    """The strip along the foot, in the order it is drawn."""
    return (
        "<h3>The strip along the foot</h3>"
        + _row(
            resources.donate_icon_path(),
            "Donate",
            "hands an address to your web browser and nothing more. It sits "
            "on its own at the left, ruled off, so it is not pressed by "
            "accident.",
        )
        + _row(
            resources.rescan_icon_path(),
            "Rescan",
            "reads what has changed rather than starting again, so adding one "
            "album costs one folder.",
        )
        + _row(
            resources.library_health_icon_path(),
            "Repair",
            "opens what was worked around: muddled numbers, disagreeing disc "
            "numbers, a file that could not be read. Accepting a correction "
            "keeps it, so it stops being reported at every start.",
        )
        + "<p>"
        + _img(resources.view_icon_path())
        + _img(resources.medium_grid_icon_path())
        + _img(resources.equaliser_icon_path())
        + "switch between the list and the sleeves, change the sleeve size, "
        "open the equalizer.</p>"
        + "<p>"
        + _img(resources.shuffle_icon_path())
        + _img(resources.repeat_icon_path())
        + "shuffle and repeat, at the right end. Repeat has three settings: "
        "off, the album, then the one song. Every switch shows what pressing "
        "it would DO rather than what it is doing now.</p>"
    )


def _reading_html() -> str:
    """The parts of the window that are not buttons."""
    return (
        "<h3>What else the window is telling you</h3>"
        "<p>The <b>waveform</b> along the bottom is the whole of the playing "
        "track, loud parts and quiet. Click anywhere on it to jump there. The "
        "small bars below it move with the sound and can change nothing: they "
        "watch it after it has already gone to your speakers.</p>"
        "<p>The <b>stars</b> at the bottom right follow whatever row you have "
        "selected rather than whatever is playing, so you can rate something "
        "without listening to it first. Press the star a rating already sits "
        "on to clear it.</p>"
        "<p>The <b>status line</b> says how much was found; it also says plainly "
        "when a song will not play and why.</p>"
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
