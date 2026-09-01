"""The library tree highlights whatever is playing, however it came to play.

Reported as three separate faults and they are one: the tray buttons, the right
click menu and a track ending all move the transport; none of them moved the
highlight, so the library went on pointing at whatever was last clicked. The
highlight is how a listener finds their place.

The same rule inside the grid's open album lives in
`test_follows_playback_in_the_grid.py`.
"""

from __future__ import annotations

from conftest import RecordingPlayer
from playback_support import (
    POLLS,
    TRACK_COUNT,
    album,
    album_index,
    highlighted,
    player,
    track,
    track_index,
    window,
)
from PySide6.QtCore import QModelIndex, QPoint

from stellody.domain.album import Album
from stellody.domain.identity import AlbumIdentity
from stellody.ui.main_window import MainWindow

__all__ = [
    "POLLS",
    "TRACK_COUNT",
    "album",
    "album_index",
    "highlighted",
    "player",
    "track",
    "track_index",
    "window",
]


def test_activating_a_track_leaves_the_highlight_on_it(window: MainWindow) -> None:
    """The starting point: what is played is what is pointed at."""
    window.activate(track_index(window, 0))
    assert highlighted(window) is window._transport.current


def test_the_next_button_carries_the_highlight_with_it(window: MainWindow) -> None:
    window.activate(track_index(window, 0))
    window.next_track()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_the_previous_button_carries_the_highlight_with_it(
    window: MainWindow,
) -> None:
    window.activate(track_index(window, 2))
    window.previous_track()
    window.previous_track()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_a_track_playing_out_carries_the_highlight_to_the_next_one(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Nobody pressed anything, so this is the one that matters most."""
    window.activate(track_index(window, 0))
    player.finished = True
    window._poll_transport()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current


def test_jumping_across_the_album_carries_the_highlight(window: MainWindow) -> None:
    """Activating a track well away from the highlight moves it there."""
    window.activate(track_index(window, 0))
    window.activate(track_index(window, 2))
    assert window._transport.current.title == "Track 3"
    assert highlighted(window) is window._transport.current


def test_the_highlight_follows_a_shuffled_queue_rather_than_the_rows(
    window: MainWindow,
) -> None:
    """Shuffle changes what comes next, so the highlight has to be looked up."""
    window.activate(track_index(window, 0))
    window.toggle_shuffle()
    window.next_track()
    assert highlighted(window) is window._transport.current


def test_stopping_leaves_the_highlight_where_the_music_stopped(
    window: MainWindow,
) -> None:
    """Stop gives the device back; it does not move anybody's place."""
    window.activate(track_index(window, 1))
    stopped = window._transport.current
    window.stop_playback()
    assert highlighted(window) is stopped


def test_a_poll_that_changes_nothing_leaves_the_highlight_alone(
    window: MainWindow,
) -> None:
    """Four polls a second must not drag the listener back from browsing."""
    window.activate(track_index(window, 0))
    window._tree.setCurrentIndex(track_index(window, 2))
    for _ in range(POLLS):
        window._poll_transport()
    assert window._transport.current.title == "Track 1", "nothing finished"
    assert highlighted(window).title == "Track 3", "the browse position stood"


def test_the_right_click_menu_carries_the_highlight_too(window: MainWindow) -> None:
    """The menu was reported separately; it is the same wiring underneath."""
    window.activate(track_index(window, 0))
    window.show_transport_menu(QPoint(0, 0))
    actions = {action.text(): action for action in window._menu.actions()}
    actions["Next track"].trigger()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current
    window.show_transport_menu(QPoint(0, 0))
    actions = {action.text(): action for action in window._menu.actions()}
    actions["Previous track"].trigger()
    actions["Previous track"].trigger()
    assert window._transport.current.title == "Track 1"
    assert highlighted(window) is window._transport.current


def test_a_track_inside_a_collapsed_album_is_shown_before_it_is_highlighted(
    window: MainWindow,
) -> None:
    """A highlight on a hidden row is a highlight nobody can see."""
    window._tree.collapse(album_index(window))
    window.activate(track_index(window, 1))
    assert window._tree.isExpanded(album_index(window))
    assert highlighted(window) is window._transport.current


def played_out(window: MainWindow, player: RecordingPlayer, steps: int) -> list[str]:
    """The titles heard as the poll carries one track into the next.

    Driven through the window's own timer slot rather than the transport, so
    what is asserted is what a listener sitting in front of it would hear.
    """
    heard = [window._transport.current.title]
    for _ in range(steps):
        player.finished = True
        window._poll_transport()
        heard.append(window._transport.current.title)
    return heard


def test_an_album_left_to_play_out_stops_at_its_end(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Without repeat the end is the end, which is what repeat is measured on."""
    window.activate(track_index(window, 0))
    heard = played_out(window, player, 4)
    assert heard == ["Track 1", "Track 2", "Track 3", "Track 3", "Track 3"]
    assert window._transport.playing is False


def test_a_repeating_album_starts_again_rather_than_stopping(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The album until repeat is turned off, never one track over and over."""
    window.activate(track_index(window, 0))
    window.toggle_repeat()
    heard = played_out(window, player, 5)
    assert heard == ["Track 1", "Track 2", "Track 3", "Track 1", "Track 2", "Track 3"]


def test_a_repeating_shuffled_album_is_scattered_again_for_the_next_time_round(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The order is asked for once a time round, with the whole album given."""
    asked: list[int] = []
    window._transport._ordering = lambda given: asked.append(len(given)) or given
    window.activate(track_index(window, 0))
    window.toggle_shuffle()
    window.toggle_repeat()
    scattered_when_switched_on = len(asked)
    heard = played_out(window, player, 3)
    assert len(asked) == scattered_when_switched_on + 1, "once, at the join"
    assert set(heard) == {"Track 1", "Track 2", "Track 3"}


def five_track_album(window: MainWindow):
    """An album long enough to reach its end and come round again."""
    album = Album(
        identity=AlbumIdentity(album_artist="Holst", title="The Planets"),
        tracks=tuple(track(number) for number in range(1, 6)),
    )
    window._model.set_albums((album,))
    window.show()
    window._tree.expandAll()
    return album


def test_the_highlight_comes_round_with_a_repeating_album(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The album starts again, so the highlight goes back to its first track."""
    five_track_album(window)
    album_index = window._model.index(0, 0)
    window.activate(window._model.index(0, 0, album_index))
    window.toggle_repeat()
    for _ in range(5):
        player.finished = True
        window._poll_transport()
    assert window._transport.current.title == "Track 1", "round to the beginning"
    assert highlighted(window) is window._transport.current, "and so is the highlight"


def test_a_placement_that_does_not_happen_is_tried_again(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Measured after a repeat came round with the highlight left behind.

    What was remembered as followed was set before the highlight moved, so a
    placement that did not happen was remembered as one that had and every
    later poll agreed there was nothing left to do.
    """
    five_track_album(window)
    album_index = window._model.index(0, 0)
    window.activate(window._model.index(0, 0, album_index))
    placing = window._model.index_for
    misses = [1]

    def sometimes(track):
        if misses:
            misses.pop()
            return QModelIndex()
        return placing(track)

    window._model.index_for = sometimes
    player.finished = True
    window._poll_transport()
    assert highlighted(window) is not window._transport.current, "it missed"
    window._poll_transport()
    assert highlighted(window) is window._transport.current, "and tried again"


def test_the_highlight_stays_where_the_listener_moved_it(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """Browsing during playback is the reason following is not unconditional."""
    five_track_album(window)
    album_index = window._model.index(0, 0)
    window.activate(window._model.index(0, 0, album_index))
    elsewhere = window._model.index(3, 0, album_index)
    window._tree.setCurrentIndex(elsewhere)
    window._poll_transport()
    assert highlighted(window) is window._model.track_at(elsewhere), "left alone"
    player.finished = True
    window._poll_transport()
    assert highlighted(window) is window._transport.current, "until the track changes"


def test_a_gapless_crossing_carries_the_highlight_to_the_next_track(
    window: MainWindow, player: RecordingPlayer
) -> None:
    """The engine crossed the seam on its own, so nothing was asked for."""
    window.activate(track_index(window, 0))
    player.cross()
    window._poll_transport()
    assert window._transport.current.title == "Track 2"
    assert highlighted(window) is window._transport.current
