"""FR-D54 to FR-D56: narrowing the results to some of the genres a run looked in.

Driven through the dialog itself over a library held in memory, so what is
shown, what is said and what a press acts on are read off the screen. Which
artists a filter keeps is the domain's rule and has its own suite in
`tests/domain/test_discovery_filter.py`; this is where that rule is put in
front of somebody.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog
from results_support import rows_under
from tray_support import track

from stellody.application.shopping import Shopping
from stellody.domain.album import Album
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.identity import AlbumIdentity
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.ui.palette import Mode
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.results_filter import ResultsFilterDialog
from stellody.ui.results_ticks import TICKED, every_row_across, is_tickable
from stellody.ui.results_words import where_in_the_answer, withheld

LOOKED_IN = ("House", "Rock")
HOUSE = ("House",)
HOUSE_ACT = SimilarArtist(name="Lane 8", identifier="a-house-act")
# Two candidates the catalogue memory knows nothing about, under one artist.
QUIET = SimilarArtist(name="Nobody Knows", identifier="unremembered")
SILENT = SimilarArtist(name="Nor Them", identifier="also-unremembered")
UNJUDGED = 2
REMEMBERED = {HOUSE_ACT.identifier: ("house",)}
POWER_UP = WantedAlbum(artist="AC/DC", title="Power Up")
REMOTE_PLACES = WantedAlbum(artist="Tinlicker", title="Remote Places")
SOURCES = (REMOTE_PLACES.artist, POWER_UP.artist)


def held(artist: str, genre: str) -> Album:
    """An album in the library, filed under this artist in this genre."""
    return Album(
        identity=AlbumIdentity(album_artist=artist, title=f"{artist} Album"),
        tracks=(track(1),),
        genre=genre,
    )


LIBRARY = (held(REMOTE_PLACES.artist, "House"), held(POWER_UP.artist, "Rock"))
ANSWER = (
    Gaps(
        artist=REMOTE_PLACES.artist,
        albums=(ReleaseGroup(title=REMOTE_PLACES.title),),
        artists=(HOUSE_ACT,),
    ),
    Gaps(
        artist=POWER_UP.artist,
        albums=(ReleaseGroup(title=POWER_UP.title),),
        artists=(QUIET, SILENT),
    ),
)


class Clipboard:
    """A clipboard that keeps everything put on it."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def put(self, text: str) -> None:
        """Keep it, in the order it arrived."""
        self.said.append(text)


class Nowhere:
    """No shops, plus an opener that opens nothing."""

    def shops(self) -> tuple[Shop, ...]:
        """None at all; copying needs no shop."""
        return ()

    def open(self, address: str) -> bool:
        """Say it worked without doing anything."""
        return True


def filterable(shopping: Shopping | None = None) -> ResultsDialog:
    """The dialog over a House artist and a Rock one, ready to filter."""
    return ResultsDialog(
        ANSWER,
        shopping=shopping,
        mode=Mode.DARK,
        ticked=LOOKED_IN,
        library=LIBRARY,
        remembered=REMEMBERED,
    )


def tick(dialog: ResultsDialog, wanted: WantedAlbum) -> None:
    """Tick every row showing this album, the way a click would."""
    for row in every_row_across(dialog.pages.trees):
        if is_tickable(row) and row.text(0) == wanted.title:
            row.setCheckState(0, TICKED)


def shown(dialog: ResultsDialog) -> tuple[str, ...]:
    """Which source artists head the answer now, in the order they head it."""
    return tuple(
        next(name for name in SOURCES if name in source.text(0))
        for source in dialog.sources
    )


def test_only_the_genres_looked_in_are_offered(application) -> None:
    """A genre the run never looked in could only ever filter to nothing."""
    # Held, since the chooser belongs to the dialog: a dialog nobody keeps a
    # name for is collected, taking the chooser's boxes with it.
    dialog = filterable()
    chooser = dialog.filter_dialog()
    offered = {name for name, box in chooser.grid.boxes.items() if not box.isHidden()}
    assert offered == set(LOOKED_IN)


def test_the_filter_stays_pressed_in_while_on(application, monkeypatch) -> None:
    """Held down while filtering, the way the library's own filter is held."""
    dialog = filterable()
    assert dialog.filter_button.isCheckable()
    dialog.filter_to(HOUSE)
    assert dialog.filter_button.isChecked()

    def cancelled(_chooser: ResultsFilterDialog) -> int:
        """Stand in for somebody closing the chooser without filtering."""
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(ResultsFilterDialog, "exec", cancelled)
    dialog.filter_button.click()
    assert dialog.filter_button.isChecked(), "a cancelled press changes nothing"
    dialog.filter_to(())
    assert not dialog.filter_button.isChecked()


def test_a_press_that_picks_a_genre_filters(application, monkeypatch) -> None:
    """The whole path from the button, through the chooser, to the answer."""
    dialog = filterable()

    def picked_house(chooser: ResultsFilterDialog) -> int:
        """Stand in for somebody ticking House and pressing Filter."""
        chooser.grid.boxes["House"].setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ResultsFilterDialog, "exec", picked_house)
    dialog.filter_button.click()
    assert shown(dialog) == (REMOTE_PLACES.artist,)
    assert dialog.filter_button.isChecked()


def test_the_pages_are_dealt_from_what_is_shown(application) -> None:
    """Filtered to House, only the House artist is dealt; cleared, both are."""
    dialog = filterable()
    dialog.filter_to(HOUSE)
    assert shown(dialog) == (REMOTE_PLACES.artist,)
    assert dialog.pager.position.text() == where_in_the_answer(
        0, len(dialog.pages.pages)
    )
    dialog.filter_to(())
    assert shown(dialog) == SOURCES


def test_a_fetched_candidate_keeps_its_albums_across_a_filter(application) -> None:
    """A candidate already asked about is not asked again, so its rows are owed
    the answer that came back rather than opening onto nothing for ever."""
    dialog = filterable()
    dialog.show_releases(HOUSE_ACT.identifier, (ReleaseGroup(title="Everything"),))
    dialog.filter_to(HOUSE)
    source = dialog.sources[0]
    assert rows_under(source.child(source.childCount() - 1)) == ("Everything",)


def test_the_withheld_count_is_said_while_filtering(application) -> None:
    """Rows that vanish without a word read as rows that were never found."""
    dialog = filterable()
    assert dialog.top.withheld.isHidden()
    dialog.filter_to(HOUSE)
    assert not dialog.top.withheld.isHidden()
    assert dialog.top.withheld.text() == withheld(UNJUDGED)
    dialog.filter_to(())
    assert dialog.top.withheld.isHidden()


def test_a_withheld_tick_is_left_out_of_copy(application) -> None:
    """Nothing out of sight is sent anywhere."""
    clipboard = Clipboard()
    dialog = filterable(
        Shopping(shops=Nowhere(), opener=Nowhere(), clipboard=clipboard)
    )
    tick(dialog, POWER_UP)
    tick(dialog, REMOTE_PLACES)
    dialog.filter_to(HOUSE)
    dialog.copy_ticked()
    assert dialog.ticked() == (REMOTE_PLACES,)
    assert POWER_UP.title not in clipboard.said[0]
    assert REMOTE_PLACES.title in clipboard.said[0]


def test_a_tick_survives_the_filter_being_cleared(application) -> None:
    """A tick is somebody's decision; a filter is only where they are looking."""
    dialog = filterable()
    tick(dialog, POWER_UP)
    dialog.filter_to(HOUSE)
    dialog.filter_to(())
    assert dialog.ticked() == (POWER_UP,)


def test_with_nothing_to_judge_by_the_filter_is_there_and_disabled(
    application,
) -> None:
    """The same shape as a window with no cover chooser: present, not dead."""
    dialog = ResultsDialog(ANSWER, mode=Mode.DARK, ticked=LOOKED_IN)
    assert not dialog.filter_button.isEnabled()
