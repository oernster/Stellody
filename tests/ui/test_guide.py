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
        [
            resources.choose_folder_icon_path,
            resources.filter_icon_path,
            resources.search_icon_path,
            resources.previous_icon_path,
            resources.play_icon_path,
            resources.stop_icon_path,
            resources.next_icon_path,
            resources.volume_icon_path,
            resources.unmute_icon_path,
            resources.info_icon_path,
            resources.donate_icon_path,
            resources.rescan_icon_path,
            resources.library_health_icon_path,
            resources.view_icon_path,
            resources.equaliser_icon_path,
            resources.shuffle_icon_path,
            resources.repeat_icon_path,
        ],
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


# Every icon the window can draw, so the guide is checked against the app
# rather than against a list kept beside it.
_ICON_GETTERS = tuple(
    getattr(resources, name)
    for name in dir(resources)
    if name.endswith("_icon_path") and callable(getattr(resources, name))
)
