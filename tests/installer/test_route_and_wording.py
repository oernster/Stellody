"""Which route a run takes, then what it says.

Both are pure, so every state setup can be run in is asserted here rather than
read off a screenshot. The pairing matters: the heading, the versions and the
buttons all come from the route, so a route decided wrongly is a screen that
contradicts itself.
"""

from __future__ import annotations

from installer import wording
from installer.route import Route, route_for


def test_nothing_installed_is_an_install() -> None:
    assert route_for("", "0.2.0", False) is Route.INSTALL


def test_an_older_install_is_an_update() -> None:
    assert route_for("0.1.0", "0.2.0", False) is Route.UPDATE


def test_a_newer_install_is_a_downgrade_rather_than_a_reinstall() -> None:
    """It was announced as 'already installed', which contradicted its lead."""
    assert route_for("0.3.0", "0.2.0", False) is Route.DOWNGRADE


def test_a_matching_version_is_managed() -> None:
    assert route_for("0.2.0", "0.2.0", False) is Route.MANAGE


def test_being_asked_to_uninstall_settles_it_first() -> None:
    assert route_for("0.2.0", "0.2.0", True) is Route.UNINSTALL
    assert route_for("", "0.2.0", True) is Route.UNINSTALL


def test_the_go_ahead_names_what_it_will_do() -> None:
    assert wording.primary_label(Route.INSTALL) == "Install"
    assert wording.primary_label(Route.UPDATE) == "Update"
    assert wording.primary_label(Route.DOWNGRADE) == "Go back"
    assert wording.primary_label(Route.MANAGE) == "Repair"
    assert wording.primary_label(Route.UNINSTALL) == "Uninstall"


def test_a_single_version_goes_in_the_heading() -> None:
    assert "0.2.0" in wording.heading(Route.INSTALL, "", "0.2.0")
    assert "0.2.0 is installed" in wording.heading(Route.MANAGE, "0.2.0", "0.2.0")


def test_a_change_names_no_version_in_the_heading() -> None:
    """Two versions are in play, so the flow line carries both instead."""
    for route in (Route.UPDATE, Route.DOWNGRADE):
        heading = wording.heading(route, "0.1.0", "0.2.0")
        assert "0.1.0" not in heading
        assert "0.2.0" not in heading


def test_going_back_a_version_says_so() -> None:
    assert "older" in wording.lead(Route.DOWNGRADE)


def test_every_route_has_a_lead_of_its_own() -> None:
    leads = {wording.lead(route) for route in Route}
    assert len(leads) == len(Route)


def test_removing_promises_the_music_is_untouched() -> None:
    assert "never" in wording.lead(Route.UNINSTALL)


def test_the_forget_box_names_the_index_as_well_as_the_settings() -> None:
    """They share one database, so a box naming only one would take both."""
    assert "library index" in wording.FORGET_LABEL
    assert "music itself" in wording.FORGET_HINT


def test_the_launch_box_says_setup_will_close_itself() -> None:
    assert "close setup" in wording.LAUNCH_LABEL
