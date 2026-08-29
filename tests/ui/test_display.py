"""Paths are written the way the machine showing them writes a path."""

from __future__ import annotations

import os

from stellody.ui.display import native_path

WINDOWS = os.sep == "\\"


def test_a_chosen_folder_is_written_in_the_native_form() -> None:
    """Qt's dialog answers in forward slashes on every platform."""
    written = native_path("H:/FLACMusic")
    assert written == (r"H:\FLACMusic" if WINDOWS else "H:/FLACMusic")


def test_a_walked_folder_keeps_the_form_the_walk_gave_it() -> None:
    """The walk already joins with the native separator, so it is unchanged."""
    walked = os.path.join("H:" + os.sep + "FLACMusic", "Sasha", "Involver")
    assert native_path(walked) == walked


def test_one_path_never_shows_two_kinds_of_separator() -> None:
    """The status line showed a chosen root and a walked folder side by side."""
    mixed = "H:/FLACMusic" + os.sep + "Sasha"
    written = native_path(mixed)
    assert "/" not in written or not WINDOWS


def test_nothing_chosen_stays_nothing() -> None:
    """normpath answers the current directory for an empty path."""
    assert native_path("") == ""
