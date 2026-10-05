"""The count a picture wears in its corner, read back off the pixels.

The unanswered button carries its count as a red badge with a white figure,
the way a chat app's icon does, because the text button it replaced was not
read as a button at all.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from stellody.shared import resources
from stellody.ui.icons import BADGE_MOST, BADGE_SHARE, badge_figure, badged
from stellody.ui.palette import DARK, LIGHT
from stellody.ui.tray_metrics import ICON_PX


def _image(count: int, path=None):
    """The badged picture at the tray's size, in the light appearance."""
    return (
        badged(path, count, LIGHT.badge, LIGHT.on_badge, ICON_PX)
        .pixmap(ICON_PX, ICON_PX)
        .toImage()
    )


def test_a_count_is_said_as_it_is() -> None:
    """Fifty-three reads as 53."""
    assert badge_figure(53) == "53"


def test_a_count_past_the_most_is_capped() -> None:
    """The tooltip carries the exact count; the corner cannot."""
    assert badge_figure(BADGE_MOST) == str(BADGE_MOST)
    assert badge_figure(BADGE_MOST + 1) == f"{BADGE_MOST}+"


def test_the_badge_is_red_in_the_top_right_corner(application: QApplication) -> None:
    """Sampled just inside the pill's round end, where the fill is solid."""
    image = _image(53, resources.discover_icon_path())
    height = round(ICON_PX * BADGE_SHARE)
    inside = image.pixelColor(ICON_PX - height // 2, 2)
    assert inside == QColor(LIGHT.badge)


def test_the_figure_is_drawn_in_white(application: QApplication) -> None:
    """Some pixel of the pill carries the figure's colour."""
    image = _image(8)
    height = round(ICON_PX * BADGE_SHARE)
    pill = (
        image.pixelColor(x, y)
        for x in range(ICON_PX - height, ICON_PX)
        for y in range(height)
    )
    ink = QColor(LIGHT.on_badge)
    assert any(colour == ink for colour in pill)


def test_missing_artwork_still_leaves_the_badge(application: QApplication) -> None:
    """The count is the part that says anything is there at all."""
    assert not badged(None, 3, DARK.badge, DARK.on_badge, ICON_PX).isNull()
