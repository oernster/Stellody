"""Switching view lands where the view left behind was.

Both views hold their own highlight: the tree keeps a current row while the
grid keeps one inside the album opened under it. Only the view on show follows
the transport, so the other one knew nothing about what was playing. A switch
then arrived at a grid with no album open at all; else at a tree still rooted
wherever it was last left.

What a switch carries is the track the old view was pointing at, since that is
what "the same place, by the other route" means. Where it was pointing at
nothing, the track playing is carried instead, so a listener who has touched
neither view still arrives at the music.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from playback_support import album_index, player, track_index, window

from stellody.ui.main_window import MainWindow

__all__ = ["album_index", "player", "track_index", "window"]

SECOND_TRACK = 1


def test_playing_in_the_list_then_switching_opens_that_album_on_its_track(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The reported case: play from the list, switch, arrive at the album."""
    window.activate(track_index(window, SECOND_TRACK))
    window._poll_transport()
    playing = window._transport.current

    window.toggle_view()

    assert window.showing_covers
    assert window._album_pane.isVisible()
    assert window._model.track_at(window.highlighted()) is playing


def test_playing_in_the_grid_then_switching_lands_on_that_track_in_the_list(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The other direction, which is the same rule read backwards."""
    window.toggle_view()
    window.open_album_at(album_index(window))
    window.activate(track_index(window, SECOND_TRACK))
    window._poll_transport()
    playing = window._transport.current

    window.toggle_view()

    assert not window.showing_covers
    assert window._model.track_at(window.highlighted()) is playing


def test_a_switch_with_nothing_playing_carries_nothing(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """A library nobody has played opens no album on a switch."""
    window.toggle_view()

    assert window.showing_covers
    assert not window._album_pane.isVisible()


def test_the_sleeve_is_picked_rather_than_the_album_merely_opened(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Arriving takes the same route a listener's own press would take.

    The grid travels to whatever is picked in it, so opening the album
    without picking its sleeve leaves an album open underneath sleeves that
    are not it, on a grid still scrolled wherever it was left.
    """
    window.activate(track_index(window, SECOND_TRACK))
    window._poll_transport()

    window.toggle_view()

    assert window._grid.currentIndex() == album_index(window)
