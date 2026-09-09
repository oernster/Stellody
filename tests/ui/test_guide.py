"""The guide: what it shows; that it keeps showing it.

The guard worth having here is not that the text reads well. It is that the
guide stays honest as the window changes: an icon added to a tray with no line
here leaves somebody looking at a picture the guide does not explain, which is
the one failure a help screen can have that is worse than not existing.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
import re

import pytest
from PySide6.QtWidgets import QApplication

from stellody.shared import resources
from stellody.shared.version import APP_NAME
from stellody.ui.discovery_dialog import FIND_LABEL
from stellody.ui.guide import INLINE_ICON_PX, GuideDialog, guide_html
from stellody.ui.results_foot import COPY_LABEL, SHOPS_LABEL
from stellody.ui.tray_metrics import DISCOVER_TOOLTIP, STOP_DISCOVERY_TOOLTIP


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

# The getters above are only half of the artwork. A dialog reaches its pictures
# by NAME through `resources.find_asset`, which no getter mentions, so the
# sweep could not see one: the two page controls, the sweep that ticks every
# genre, the two shop controls and the Close every dialog wears were all
# outside it. Reported by Oliver on 2026-09-09, who asked why the guide said
# nothing about the paging.
#
# That is the same failure the getter sweep was written to end, arriving by a
# route the getter sweep does not cover. So the second half is discovered the
# same way: every picture NAMED in the interface layer, read out of the source
# rather than listed here, must be one the guide draws.
_UI_SOURCE = pathlib.Path(inspect.getfile(GuideDialog)).parent


def _named_pictures() -> set[str]:
    """Every image file the interface layer names for itself."""
    found: set[str] = set()
    for module in sorted(_UI_SOURCE.glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            named = isinstance(node, ast.Constant) and isinstance(node.value, str)
            if named and node.value.endswith(".png"):
                found.add(node.value)
    return found


class TestWhatItNames:
    def test_it_leads_with_the_application_by_name(self) -> None:
        """Read from APP_NAME, so a rename reaches the guide too."""
        assert f"A guide to {APP_NAME}" in guide_html()

    def test_every_picture_it_draws_is_one_the_window_draws(self) -> None:
        """A guide showing an icon the window does not is worse than none.

        Every source is checked against the resource lookup rather than
        against a list written here, since a list would be one more thing to
        keep in step. The window reaches its artwork two ways, so both are the
        universe: the getters on `resources` plus the files the interface
        names for itself.
        """
        drawn = {
            path.name
            for path in (getter() for getter in _ICON_GETTERS)
            if path is not None
        } | _named_pictures()
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

    def test_every_picture_the_dialogs_name_is_explained_too(self) -> None:
        """The other half of the sweep: artwork reached by name, not by getter.

        A dialog asks `find_asset` for a file, so nothing in `resources`
        mentions it and the getter sweep above cannot see it. The paging
        controls lived in exactly that gap and the guide said nothing about
        them until Oliver asked. Read out of the source, so a picture named by
        a dialog written next year is explained by default.
        """
        drawn = _sources(guide_html())
        missing = sorted(name for name in _named_pictures() if name not in drawn)
        assert not missing, f"named in the interface, absent from the guide: {missing}"

    def test_the_interface_really_does_name_pictures_this_way(self) -> None:
        """Guard the guard: a scan finding nothing would pass the test above."""
        assert len(_named_pictures()) >= 6, "the source scan found nothing to check"

    @pytest.mark.parametrize(
        "wording",
        [
            DISCOVER_TOOLTIP,
            STOP_DISCOVERY_TOOLTIP,
            FIND_LABEL,
            SHOPS_LABEL,
            COPY_LABEL,
        ],
        ids=["discover", "stop", "find", "shops", "copy"],
    )
    def test_every_control_it_names_is_named_as_the_window_names_it(
        self, wording: str
    ) -> None:
        """A word the guide quotes is read from the control, never retyped.

        Reported on 2026-09-08: the guide said the discovery button reads
        "Stop looking" while it reads "Stop discovery". The string had been
        copied out of the specification, which was stale itself, so the guide
        was quoting a document rather than the window it exists to explain.

        Checked against the constants the controls use, so a reworded button
        reaches this screen instead of leaving it quietly wrong. It is the
        icon rule in a different medium: never a description where the real
        thing is available.
        """
        assert wording in guide_html()

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
