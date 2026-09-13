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
"""

from __future__ import annotations

import pathlib

from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.about_credits import NO_SHOP_AFFILIATION
from stellody.ui.auto_scroller import AutoScroller
from stellody.ui.dialogs import CLOSE_ICON, FirstStopDialog, close_row
from stellody.ui.discovery_dialog import FIND_LABEL, SELECT_ALL_ICON
from stellody.ui.layout_advice import layout_html
from stellody.ui.results_foot import (
    COPY_ICON,
    COPY_LABEL,
    SHOP_ICON,
    SHOPS_LABEL,
)
from stellody.ui.results_pager import NEXT_ICON as NEXT_PAGE_ICON
from stellody.ui.results_pager import PREVIOUS_ICON as PREVIOUS_PAGE_ICON
from stellody.ui.results_words import NEXT_PAGE, PREVIOUS_PAGE
from stellody.ui.shop_rows import (
    ADD_ICON,
    ADD_LABEL,
    DELETE_ICON,
    DRAG_ICON,
    EDIT_ICON,
    PUT_BACK_LABEL,
)
from stellody.ui.tray_metrics import DISCOVER_TOOLTIP, STOP_DISCOVERY_TOOLTIP
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
        + _row(
            resources.discover_icon_path(),
            "Discover",
            "looks for music you do not own yet, in the genres you tick. It "
            "sits to the left of the volume control, with its progress bars "
            "beside it while a run is going. The procedure is below.",
        )
        + "<p>"
        + _img(resources.volume_icon_path())
        + _img(resources.unmute_icon_path())
        + _img(resources.light_mode_icon_path())
        + _img(resources.info_icon_path())
        + "volume, mute, the light or dark appearance, then Help. Help opens "
        "a menu carrying this guide, About and a check for a new version.</p>"
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


def _discovery_html() -> str:
    """The one feature with a procedure rather than a button to press.

    It is the only thing in this window that takes minutes, reaches outside the
    machine and then hands somebody a second screen to act on, so naming its
    button explains nothing on its own. What the guide owes here is the ORDER
    of it, which is what hovering cannot tell anybody.
    """
    return (
        "<h3>Finding music you do not own</h3>"
        "<p>"
        + _img(resources.discover_icon_path())
        + f"Press the button whose tooltip reads <b>{DISCOVER_TOOLTIP}</b>, tick "
        f"the genres worth looking in, then press <b>{FIND_LABEL}</b>. The dialog "
        "closes: a run takes minutes and is watched from the toolbar rather "
        "than from a dialog sat over everything.</p>"
        "<p><b>While it runs.</b> Two bars appear beside the button, one for "
        "each half of the run: the first asks what the artists you already "
        "hold have released and who resembles them, the second asks what each "
        "of those suggested artists plays. Hover the pair to see who is being "
        "asked about and how many are left; the right hand end of the bar "
        "says roughly how long remains, as does the line along the foot of "
        "the window. Nothing about you is sent, only artist names.</p>"
        "<p>"
        + _img(resources.find_asset(SELECT_ALL_ICON))
        + "The catalogue holds 34 boxes, so the control at the foot of that "
        "dialog ticks every one of them in a single press. It says which of "
        "the two things a press would do, offering to clear them all once "
        "everything is ticked.</p>"
        f"<p><b>Stopping.</b> While a run is going the button wears a cross "
        f"and its tooltip reads <b>{STOP_DISCOVERY_TOOLTIP}</b>. One press "
        "stops it there and then, with nothing to confirm; the request in "
        "flight is dropped rather than waited out. The last run's results are "
        "left exactly as they were. What the catalogues had already answered "
        "is kept rather than thrown away, so starting again asks only for "
        "what is still missing.</p>"
        "<p><b>What it found.</b> Every run that finishes opens its answer, "
        "including one that found nothing: an empty screen still says which "
        "genres were looked in, which a line along the top names. A "
        "<b>blue</b> name is an artist you hold, with albums by them you do "
        "not underneath. An <b>amber</b> name is an artist you hold nothing "
        "by; open one and its albums are fetched then, which takes a few "
        "seconds, so the strip at the top says who is being asked about. "
        "Every other line is an album title. Nothing in the list is ever a "
        "track.</p>"
        "<p><b>Where a name could not be answered for</b>, a button beside "
        "the message at the foot of the window carries the count of those "
        "artists. Pressing it lists them under what went wrong: the "
        "catalogue refused; it knew nobody by that name; it knew several and "
        "none of your tags says which is yours.</p>"
        "<p>"
        + _img(resources.find_asset(PREVIOUS_PAGE_ICON))
        + _img(resources.find_asset(NEXT_PAGE_ICON))
        + "<b>Turning the answer.</b> A whole library answers with hundreds "
        "of artists, so the answer is dealt across the width of the screen "
        f"and turned a page at a time. <b>{PREVIOUS_PAGE}</b> and "
        f"<b>{NEXT_PAGE}</b> sit under it with the page you are on between "
        "them; the direction that leads nowhere wears its picture struck "
        "through. Albums you tick stay ticked as you turn the pages, so a "
        "whole answer can go to a shop together.</p>"
        "<p>"
        + _img(resources.find_asset(SHOP_ICON))
        + _img(resources.find_asset(COPY_ICON))
        + f"<b>Getting hold of it.</b> Tick any albums you want, then press "
        f"<b>{SHOPS_LABEL}</b> to choose a shop: your browser opens that "
        "shop's own search for each ticked album, one tab apiece; more than "
        "five asks you first. The shops screen stays open so prices can "
        f"be compared across several. <b>{COPY_LABEL}</b> puts the ticked "
        "albums on the clipboard instead, one line each, for anywhere else "
        "you want to paste them.</p>"
        "<p>"
        + _img(resources.find_asset(ADD_ICON))
        + _img(resources.find_asset(EDIT_ICON))
        + _img(resources.find_asset(DELETE_ICON))
        + _img(resources.find_asset(DRAG_ICON))
        + f"<b>Changing the shops.</b> <b>{ADD_LABEL}</b> puts a shop of your "
        "own at the bottom of the list. The edit picture beside a shop opens it "
        "in a form; the delete picture removes it once you have said yes. Drag "
        "the grip beside a shop to move it; Ctrl+Up and Ctrl+Down do the same. "
        "<b>Try</b> in the form opens its search for the first album you "
        "ticked, so you can see it works before saving. A line that cannot "
        "search is shown greyed out with the reason, ready to mend. "
        f"<b>{PUT_BACK_LABEL}</b> restores the shops {APP_NAME} came with while "
        f"keeping your own. A new version of {APP_NAME} adds any shop it has "
        "gained, never one you deleted.</p>"
        "<p>"
        + _img(resources.find_asset(CLOSE_ICON))
        + "Every screen here is left by the control wearing that picture, "
        "which is the same Close on every dialog in the application.</p>"
        f"<p>{NO_SHOP_AFFILIATION}</p>"
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
        f"{_discovery_html()}<hr>"
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
