"""Ticking albums in the results, then copying them or taking them to a shop.

The screen half of SHOPS.md. What an address looks like is settled in the
domain suite and what happens to it in the application one; this is about the
boxes, the two controls and what they are given.
"""

from __future__ import annotations

from results_support import Asking, candidate_in, gaps_with, made, rows_under

from stellody.application.shopping import Shopping
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.ui.dialogs import CONTROL_ICON_PX
from stellody.ui.results_foot import COPIED, COPY_LABEL
from stellody.ui.results_ticks import TICKED, is_tickable

QOBUZ = Shop(name="Qobuz", template="https://q/?q={artist}%20{album}")


class Shops:
    """A shop list holding whatever the test handed it."""

    def __init__(self, *shops: Shop) -> None:
        self._shops = shops or (QOBUZ,)

    def shops(self) -> tuple[Shop, ...]:
        """What this fake was told."""
        return self._shops


class Opener:
    """An opener that records rather than opening anything."""

    def __init__(self, refuse: bool = False) -> None:
        self.opened: list[str] = []
        self._refuse = refuse

    def open(self, address: str) -> bool:
        """Take the address, unless this one was told to refuse."""
        self.opened.append(address)
        return not self._refuse


class Clipboard:
    """A clipboard that only remembers."""

    def __init__(self) -> None:
        self.holds: list[str] = []

    def put(self, text: str) -> None:
        """Keep what it was given."""
        self.holds.append(text)


def shopping(*shops: Shop, refuse: bool = False):
    """The use case over three stand-ins, all three answered back."""
    opener, clipboard = Opener(refuse), Clipboard()
    return Shopping(Shops(*shops), opener, clipboard), opener, clipboard


def dialog_over(gaps, **shops):
    """A results dialog with the shopping wired in."""
    use_case, opener, clipboard = shopping(**shops)
    return made(gaps, asking=Asking()), use_case, opener, clipboard


def with_shopping(gaps, asking=None, **shops):
    """A results dialog built the way the window builds one."""
    from stellody.ui.palette import Mode
    from stellody.ui.results_dialog import ResultsDialog

    use_case, opener, clipboard = shopping(**shops)
    dialog = ResultsDialog(gaps, asking=asking, shopping=use_case, mode=Mode.DARK)
    return dialog, opener, clipboard


def albums_in(dialog):
    """Every row that can be ticked, in the order they are drawn."""
    source = dialog.sources[0]
    return [
        source.child(at)
        for at in range(source.childCount())
        if is_tickable(source.child(at))
    ]


def test_every_album_row_can_be_ticked(application) -> None:
    """FR-S01: a box is a state that survives focus moving elsewhere."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    boxes = albums_in(dialog)
    assert len(boxes) == 2
    for box in boxes:
        assert box.checkState(0) is not TICKED


def test_an_artist_row_carries_no_tick_box(application) -> None:
    """FR-S02: an artist is not something a shop sells."""
    dialog, _opener, _clipboard = with_shopping(
        (gaps_with(albums=1, artists=1),), asking=Asking()
    )
    source = dialog.sources[0]
    assert not is_tickable(source)
    assert not is_tickable(source.child(source.childCount() - 1))


def test_fetched_albums_can_be_ticked_too(application) -> None:
    """FR-S03: the albums least likely to be held arrive after the build."""
    dialog, _opener, _clipboard = with_shopping(
        (gaps_with(artists=1),), asking=Asking()
    )
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_releases("id-0", (ReleaseGroup(title="Firewood"),))
    assert rows_under(candidate) == ("Firewood",)
    assert is_tickable(candidate.child(0))


def test_the_shops_control_waits_for_a_tick(application) -> None:
    """FR-S04: a press that can only report emptiness is worth preventing."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=1),))
    assert not dialog.shops_button.isEnabled()
    assert not dialog.copy_button.isEnabled()
    albums_in(dialog)[0].setCheckState(0, TICKED)
    assert dialog.shops_button.isEnabled()
    assert dialog.copy_button.isEnabled()


def test_a_dialog_with_no_shopping_offers_neither_control(application) -> None:
    """The house shape: there and disabled rather than there and dead."""
    dialog = made((gaps_with(albums=1),))
    assert not dialog.shops_button.isEnabled()
    assert not dialog.copy_button.isEnabled()


def test_what_is_ticked_carries_its_artist(application) -> None:
    """A title alone finds the wrong record, so the row remembers the name."""
    dialog, _opener, _clipboard = with_shopping(
        (Gaps(artist="Kate Bush", albums=(ReleaseGroup(title="Aerial"),)),)
    )
    albums_in(dialog)[0].setCheckState(0, TICKED)
    assert dialog.ticked() == (WantedAlbum(artist="Kate Bush", title="Aerial"),)


def test_a_fetched_album_belongs_to_the_candidate_it_came_from(application) -> None:
    """The artist of a candidate's albums is the candidate, not the source."""
    found = Gaps(
        artist="Blues Pills",
        artists=(SimilarArtist(name="Witchcraft", identifier="id-wc"),),
    )
    dialog, _opener, _clipboard = with_shopping((found,), asking=Asking())
    candidate = candidate_in(dialog)
    candidate.setExpanded(True)
    dialog.show_releases("id-wc", (ReleaseGroup(title="Firewood"),))
    candidate.child(0).setCheckState(0, TICKED)
    assert dialog.ticked() == (WantedAlbum(artist="Witchcraft", title="Firewood"),)


def test_the_ticked_albums_come_back_in_reading_order(application) -> None:
    """A list in click order is one nobody can check against the screen."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=3),))
    boxes = albums_in(dialog)
    boxes[2].setCheckState(0, TICKED)
    boxes[0].setCheckState(0, TICKED)
    assert [album.title for album in dialog.ticked()] == ["Album 0", "Album 2"]


def test_copy_puts_the_ticked_albums_on_the_clipboard(application) -> None:
    """FR-S14: the fallback for every shop nobody has configured."""
    dialog, _opener, clipboard = with_shopping(
        (Gaps(artist="Kate Bush", albums=(ReleaseGroup(title="Aerial"),)),)
    )
    albums_in(dialog)[0].setCheckState(0, TICKED)
    dialog.copy_ticked()
    assert clipboard.holds == ["Kate Bush - Aerial"]


def test_copying_says_it_copied(application) -> None:
    """A press that changes nothing visible is a press nobody saw work."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=1),))
    albums_in(dialog)[0].setCheckState(0, TICKED)
    assert dialog.copy_button.text() == COPY_LABEL
    dialog.copy_ticked()
    assert dialog.copy_button.text() == COPIED


def test_changing_the_ticks_puts_the_copy_control_back(application) -> None:
    """Said about the last list, so it goes when the list changes."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=2),))
    boxes = albums_in(dialog)
    boxes[0].setCheckState(0, TICKED)
    dialog.copy_ticked()
    boxes[1].setCheckState(0, TICKED)
    assert dialog.copy_button.text() == COPY_LABEL


def test_the_shops_control_opens_the_shops(application) -> None:
    """FR-S05: the press that leads to everything the shops dialog does."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=1),))
    albums_in(dialog)[0].setCheckState(0, TICKED)
    dialog.open_shops()
    assert dialog.shops is not None
    assert dialog.shops.isVisible()
    dialog.shops.reject()


def test_the_shops_dialog_is_given_exactly_what_was_ticked(application) -> None:
    """What is offered is the list on screen rather than everything found."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=3),))
    albums_in(dialog)[1].setCheckState(0, TICKED)
    dialog.open_shops()
    assert [album.title for album in dialog.shops._wanted] == ["Album 1"]
    dialog.shops.reject()


def test_the_ticks_and_the_controls_are_stops_on_the_ring(application) -> None:
    """FR-S15: a control reachable only with a mouse is half a control."""
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=1),))
    for control in (dialog.copy_button, dialog.shops_button, dialog.close_button):
        assert control.focusPolicy() is not control.focusPolicy().NoFocus
    assert (
        dialog.pages.trees[0].focusPolicy()
        is not dialog.pages.trees[0].focusPolicy().NoFocus
    )


def test_the_controls_wear_their_artwork_at_the_size_the_trays_use(
    application,
) -> None:
    """Reported 2026-09-08: the shop picture arrived far too small to notice.

    Qt draws an icon at its own small default unless a button is told
    otherwise; nothing here told it. The size is read from the bottom strip
    rather than stated again, so the two cannot drift apart.
    """
    dialog, _opener, _clipboard = with_shopping((gaps_with(albums=1),))
    for control in (dialog.copy_button, dialog.shops_button):
        assert control.iconSize().width() == CONTROL_ICON_PX, control.text()
        assert control.iconSize().height() == CONTROL_ICON_PX, control.text()
        assert not control.icon().isNull(), control.text()


class TestADialogWithNoShoppingWiredIn:
    """A results dialog can be built without stage two, so it is.

    `shopping` carries a default of None, which every caller that predates
    the shops used and every test that only wants the tree still uses. Both
    controls are disabled in that state, so nobody can reach these by
    pressing anything; what they answer is a call made in code.
    """

    def test_the_controls_are_disabled_rather_than_dead(self, application) -> None:
        """The state is visible on screen instead of being a surprise later."""
        dialog = made((gaps_with(albums=1),), asking=Asking())
        assert not dialog.copy_button.isEnabled()
        assert not dialog.shops_button.isEnabled()

    def test_copying_does_nothing_and_leaves_the_control_reading_copy(
        self, application
    ) -> None:
        """The label only changes where something was actually copied."""
        dialog = made((gaps_with(albums=1),), asking=Asking())
        dialog.copy_ticked()
        assert dialog.copy_button.text() == COPY_LABEL

    def test_asking_for_the_shops_opens_no_dialog(self, application) -> None:
        """There is nothing to offer, so nothing is put on screen."""
        dialog = made((gaps_with(albums=1),), asking=Asking())
        dialog.open_shops()
        assert dialog.shops is None
