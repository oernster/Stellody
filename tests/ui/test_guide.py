"""The guide: what it shows; that it keeps showing it.

The guard worth having here is not that the text reads well. It is that the
guide stays honest as the window changes: an icon added to a tray with no line
here leaves somebody looking at a picture the guide does not explain, which is
the one failure a help screen can have that is worse than not existing.
"""

from __future__ import annotations

import re

import pytest
from PySide6.QtWidgets import QApplication

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.guide import INLINE_ICON_PX, GuideDialog, guide_html


def _sources(html: str) -> set[str]:
    """Every image the guide asks for, by file name."""
    return {
        source.rsplit("/", 1)[-1]
        for source in re.findall(r'<img src="file:///([^"]+)"', html)
    }


# Every icon the window can draw, so the guide is checked against the app
# rather than against a list kept beside it.
_ICON_GETTERS = tuple(
    getattr(resources, name)
    for name in dir(resources)
    if name.endswith("_icon_path") and callable(getattr(resources, name))
)

# The icons that are NOT a control of their own, each with the reason. An
# exemption is granted in front of somebody, exactly as a module is granted
# permission to open a connection: what makes this a guard rather than a list
# is that a NEW icon is explained by default and has to be argued out of it.
#
# This is the correction of a guard that was not one. The set below used to be
# written the other way round, as a hand-kept list of the getters to check, so
# the discovery button shipped with no line in the guide at all and every gate
# stayed green: whoever forgets a guide entry forgets the list entry with it,
# which is the whole reason the menu bar is swept rather than checked.
_NOT_A_CONTROL = {
    # The application's own mark, worn by the window and the About screen.
    "window_icon_path",
    "application_icon_path",
    # The second face of a control already named, rather than a second control.
    "dark_mode_icon_path",
    "pause_icon_path",
    "repeat_one_icon_path",
    "large_grid_icon_path",
    "extra_large_grid_icon_path",
    # The chevron on a heading and on an album row. Drawn by the view rather
    # than pressed as a button; explained where opening albums is.
    "expand_icon_path",
    "collapse_icon_path",
    # Composed over another picture to cross it out. Never a control alone.
    "negative_icon_path",
}

_EXPLAINED_GETTERS = tuple(
    getter for getter in _ICON_GETTERS if getter.__name__ not in _NOT_A_CONTROL
)


class TestWhatItNames:
    def test_it_leads_with_the_application_by_name(self) -> None:
        """Read from APP_NAME, so a rename reaches the guide too."""
        assert f"A guide to {APP_NAME}" in guide_html()

    def test_every_picture_it_draws_is_one_the_window_draws(self) -> None:
        """A guide showing an icon the window does not is worse than none.

        Every source is checked against the resource lookup rather than
        against a list written here, since a list would be one more thing to
        keep in step.
        """
        drawn = {
            path.name
            for path in (getter() for getter in _ICON_GETTERS)
            if path is not None
        }
        assert _sources(guide_html()) <= drawn

    @pytest.mark.parametrize(
        "getter",
        _EXPLAINED_GETTERS,
        ids=lambda getter: getter.__name__,
    )
    def test_every_control_on_a_tray_is_named(self, getter) -> None:
        """A control somebody can press has a line explaining it."""
        path = getter()
        if path is None:
            pytest.skip("that icon is not bundled in this checkout")
        assert path.name in _sources(guide_html())

    def test_it_states_the_rules_no_screen_can_state(self) -> None:
        """The half that is not an inventory."""
        html = guide_html()
        for promise in (
            "only ever read",
            "Folders group, tags name",
            "Ratings follow the album",
        ):
            assert promise in html, promise

    def test_a_missing_icon_costs_a_picture_and_not_the_guide(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unbundled asset must never stop help opening."""
        monkeypatch.setattr(resources, "donate_icon_path", lambda: None)
        html = guide_html()
        assert "buy the author" not in html.lower()
        assert "Donate" in html

    def test_the_icons_are_drawn_larger_than_the_words(self) -> None:
        """This screen is read to tell one picture from another."""
        assert f'width="{INLINE_ICON_PX}"' in guide_html()


class TestTheDialog:
    def test_it_opens_and_can_be_read(self, application: QApplication) -> None:
        dialog = GuideDialog()
        assert dialog.windowTitle() == "Guide"
        assert dialog.pane is not None
        assert dialog.scroller is not None
        dialog.deleteLater()
