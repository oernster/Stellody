"""The guide's section on finding music you do not own.

The one feature with a procedure rather than a button to press. It is the only
thing in this window that takes minutes, reaches outside the machine and then
hands somebody a second screen to act on, so naming its button explains nothing
on its own. What the guide owes here is the ORDER of it, which is what hovering
cannot tell anybody.

Its own module since 2026-09-13, when the guide reached the 381 to 400 danger
band: the procedure is a section with a clean edge, drawn with the pictures and
the words of the screens it walks through, read from those screens rather than
typed again here.
"""

from __future__ import annotations

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.about_credits import NO_SHOP_AFFILIATION
from stellody.ui.dialogs import CLOSE_ICON
from stellody.ui.discovery_dialog import (
    FIND_LABEL,
    INCLUDE_COMPILATIONS_LABEL,
    SELECT_ALL_ICON,
)
from stellody.ui.guide_pictures import img
from stellody.ui.results_foot import (
    COPY_ICON,
    COPY_LABEL,
    FILTER_LABEL,
    SHOP_ICON,
    SHOPS_LABEL,
)
from stellody.ui.results_pager import NEXT_ICON as NEXT_PAGE_ICON
from stellody.ui.results_pager import PREVIOUS_ICON as PREVIOUS_PAGE_ICON
from stellody.ui.results_words import NEXT_PAGE, PREVIOUS_PAGE
from stellody.ui.shop_form import SAVE_ICON, SAVE_LABEL, TRY_ICON, TRY_LABEL
from stellody.ui.shop_rows import (
    ADD_ICON,
    ADD_LABEL,
    DELETE_ICON,
    DRAG_ICON,
    EDIT_ICON,
    PUT_BACK_ICON,
    PUT_BACK_LABEL,
)
from stellody.ui.tray_metrics import DISCOVER_TOOLTIP, STOP_DISCOVERY_TOOLTIP


def _asking_html() -> str:
    """Starting a run, what it asks about and how to stop it."""
    return (
        "<h3>Finding music you do not own</h3>"
        "<p>"
        + img(resources.discover_icon_path())
        + f"Press the button whose tooltip reads <b>{DISCOVER_TOOLTIP}</b>, tick "
        f"the genres worth looking in, then press <b>{FIND_LABEL}</b>. The dialog "
        "closes: a run takes minutes and is watched from the toolbar rather "
        "than from a dialog sat over everything.</p>"
        "<p><b>Compilations.</b> An album filed under Various Artists is left "
        f"out unless <b>{INCLUDE_COMPILATIONS_LABEL}</b> is ticked, when the "
        "artists on its tracks are asked about instead. The line beneath the "
        "box says how many of them have not been looked up before and roughly "
        "what that adds; the first time, it can be many minutes.</p>"
        "<p><b>While it runs.</b> Two bars appear beside the button, one for "
        "each half of the run: the first asks what the artists you already "
        "hold have released and who resembles them, the second asks what each "
        "of those suggested artists plays. Hover the pair to see who is being "
        "asked about and how many are left; the right hand end of the bar "
        "says roughly how long remains, as does the line along the foot of "
        "the window. Nothing about you is sent, only artist names.</p>"
        "<p>"
        + img(resources.find_asset(SELECT_ALL_ICON))
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
    )


def _answer_html() -> str:
    """Reading the answer, turning it and narrowing it."""
    return (
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
        + img(resources.find_asset(PREVIOUS_PAGE_ICON))
        + img(resources.find_asset(NEXT_PAGE_ICON))
        + "<b>Turning the answer.</b> A whole library answers with hundreds "
        "of artists, so the answer is dealt across the width of the screen "
        f"and turned a page at a time. <b>{PREVIOUS_PAGE}</b> and "
        f"<b>{NEXT_PAGE}</b> sit under it with the page you are on between "
        "them; the direction that leads nowhere wears its picture struck "
        "through. Albums you tick stay ticked as you turn the pages, so a "
        "whole answer can go to a shop together.</p>"
        "<p>"
        + img(resources.filter_icon_path())
        + f"<b>Narrowing the answer.</b> <b>{FILTER_LABEL}</b>, at the left "
        "of the row beneath the answer, offers the genres that run looked in. "
        "Tick some to see only the artists you hold with an album of your own "
        "filed under one of them, plus the similar artists an earlier run "
        "found playing one; the button stays pressed in while it is on. In "
        f"the chooser, <b>{FILTER_LABEL}</b> waits until a genre is ticked; "
        "where a filter is already on, clearing every tick then pressing it "
        "takes the filter off. A similar artist whose genre was never found is "
        "left out, with a line at the top saying how many. Ticks are kept "
        f"through it all, while Copy and <b>{SHOPS_LABEL}</b> act only on "
        "ticked albums you can see.</p>"
    )


def _shops_html() -> str:
    """Taking the ticked albums to a shop, then changing the shops."""
    return (
        "<p>"
        + img(resources.find_asset(SHOP_ICON))
        + img(resources.find_asset(COPY_ICON))
        + f"<b>Getting hold of it.</b> Tick any albums you want, then press "
        f"<b>{SHOPS_LABEL}</b> to choose a shop: your browser opens that "
        "shop's own search for each ticked album, one tab apiece; more than "
        "five asks you first. The shops screen stays open so prices can "
        f"be compared across several. <b>{COPY_LABEL}</b> puts the ticked "
        "albums on the clipboard instead, one line each, for anywhere else "
        "you want to paste them.</p>"
        "<p>"
        + img(resources.find_asset(ADD_ICON))
        + img(resources.find_asset(EDIT_ICON))
        + img(resources.find_asset(DELETE_ICON))
        + img(resources.find_asset(DRAG_ICON))
        + img(resources.find_asset(TRY_ICON))
        + img(resources.find_asset(SAVE_ICON))
        + img(resources.find_asset(PUT_BACK_ICON))
        + f"<b>Changing the shops.</b> <b>{ADD_LABEL}</b> puts a shop of your "
        "own at the bottom of the list. The edit picture beside a shop opens it "
        "in a form; the delete picture removes it once you have said yes. Drag "
        "the grip beside a shop to move it, to any place from first to last, "
        "and the others make room as it goes; Ctrl+Up and Ctrl+Down do the "
        f"same. <b>{TRY_LABEL}</b> in the form opens its search for the first "
        "album you ticked, so you can see it works before "
        f"<b>{SAVE_LABEL}</b> keeps it. A line that cannot search is shown "
        f"greyed out with the reason, ready to mend. <b>{PUT_BACK_LABEL}</b> "
        f"restores the shops {APP_NAME} came with while keeping your own. A new "
        f"version of {APP_NAME} adds any shop it has gained, never one you "
        "deleted.</p>"
        "<p>"
        + img(resources.find_asset(CLOSE_ICON))
        + "Close wears that picture on every dialog in the application. In the "
        "two genre filters Clear wears it too, unticking every box without "
        "leaving; Cancel beside it wears the filter picture struck through.</p>"
        f"<p>{NO_SHOP_AFFILIATION}</p>"
    )


def discovery_html() -> str:
    """The whole procedure, in the order somebody meets it."""
    return f"{_asking_html()}{_answer_html()}{_shops_html()}"
