"""The row beneath the answer: the pager on the middle of the dialog. FR-D49.

Asked for by Oliver on 2026-09-24. The pager stood centred between the
controls on the left and Close, so once Filter joined the left it sat well to
the right of the dialog's middle: measured offscreen, 143 pixels right in a
dialog 720 wide. The two sides now share the spare width equally.

Every width here is worked out from what the controls ask for rather than
stated. How wide a button asks to be follows the style in force, which an
earlier test in the same session can change: measured on 2026-09-24, Find in
shops asked for 219 pixels alone and 237 after the suite before it.
"""

from __future__ import annotations

from results_support import gaps_with, made

from stellody.ui.theme import HALF

# Where the pager may stand from the true middle and still read as on it:
# half a pixel of rounding either way, twice over for the two edges it spans.
WITHIN_PX = 1
# Room beyond the least that centring needs, so the check is not made on the
# very edge of where centring becomes possible.
SPARE_PX = 100


def _pager_middle(dialog) -> float:
    """The middle of what the pager draws, in the dialog's own coordinates."""
    pager = dialog.pager
    parts = (pager.previous_button, pager.position, pager.next_button)
    left = min(part.mapTo(dialog, part.rect().topLeft()).x() for part in parts)
    right = max(part.mapTo(dialog, part.rect().topRight()).x() for part in parts)
    return (left + right) / HALF


def _foot(dialog):
    """The row holding the pager, then its left side and its right side."""
    outer = dialog.layout()
    for at in range(outer.count()):
        row = outer.itemAt(at).layout()
        if row is None:
            continue
        for place in range(row.count()):
            if row.itemAt(place).widget() is dialog.pager:
                before = row.itemAt(place - 1).layout()
                return row, before, row.itemAt(place + 1).layout()
    raise AssertionError("no row holds the pager")


def _needs(application, dialog) -> tuple[int, int, int, int]:
    """What the left side, the pager and the right side ask for, then the rest.

    The rest is the dialog's margins plus the row's two gaps, read off the
    dialog as laid out rather than assumed.
    """
    dialog.show()
    application.processEvents()
    row, left, right = _foot(dialog)
    around = dialog.width() - row.geometry().width() + HALF * row.spacing()
    return (
        left.sizeHint().width(),
        dialog.pager.sizeHint().width(),
        right.sizeHint().width(),
        around,
    )


def _at(application, dialog, width: int) -> None:
    """Lay the dialog out at this width."""
    dialog.resize(width, dialog.height())
    application.processEvents()


def test_the_pager_stands_on_the_middle_of_the_dialog(application) -> None:
    """Wherever there is room for it: both sides fit in half of what is left."""
    dialog = made((gaps_with(albums=40),))
    left, pager, right, around = _needs(application, dialog)
    enough = HALF * max(left, right) + pager + around + SPARE_PX
    for width in (enough, HALF * enough):
        _at(application, dialog, width)
        assert abs(_pager_middle(dialog) - dialog.width() / HALF) <= WITHIN_PX, width


def test_short_of_room_the_controls_keep_their_width(application) -> None:
    """Centring never squeezes a control: the pager moves along instead."""
    dialog = made((gaps_with(albums=40),))
    left, pager, right, around = _needs(application, dialog)
    assert left > right, "the left side is the wider, which is the whole case"
    _at(application, dialog, left + pager + right + around + (left - right) // HALF)
    for control in (dialog.filter_button, dialog.copy_button, dialog.shops_button):
        assert control.width() >= control.sizeHint().width(), control.text()
    shops_end = dialog.shops_button.mapTo(
        dialog, dialog.shops_button.rect().topRight()
    ).x()
    previous = dialog.pager.previous_button
    assert previous.mapTo(dialog, previous.rect().topLeft()).x() > shops_end
    assert _pager_middle(dialog) > dialog.width() / HALF, "as near as it can be"
