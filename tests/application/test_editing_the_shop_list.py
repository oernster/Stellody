"""Changing the shop list, over a hand-written store. SHOPS.md Amendment 1."""

from __future__ import annotations

import pytest

from stellody.application.shop_editing import ShopEditing, ShopListUnwritable
from stellody.application.shopping import Shopping
from stellody.domain.shop_list import ShopBook, ShopProblem
from stellody.domain.shopping import Shop, WantedAlbum

QOBUZ = Shop("Qobuz", "https://q/?a={artist}")
BLEEP = Shop("Bleep", "https://b/?q={album}")
JUNO = Shop("Juno", "https://j/?q={artist}")
HOUNDS = WantedAlbum(artist="Kate Bush", title="Hounds of Love")


class Store:
    """A store holding one list in memory; told to refuse where a test says."""

    def __init__(self, book: ShopBook, refuse: bool = False) -> None:
        self.held = book
        self.saved: list[ShopBook] = []
        self._refuse = refuse

    def book(self) -> ShopBook:
        """What it holds."""
        return self.held

    def save(self, book: ShopBook) -> None:
        """Hold this, unless it was told to refuse."""
        if self._refuse:
            raise ShopListUnwritable("read only")
        self.saved.append(book)
        self.held = book


class Opener:
    """Records every address; refuses them all where told to."""

    def __init__(self, takes: bool = True) -> None:
        self.opened: list[str] = []
        self._takes = takes

    def open(self, address: str) -> bool:
        """Note it, then answer as told."""
        self.opened.append(address)
        return self._takes


def editing(*rows: Shop, retired=(), refuse=False, takes=True):
    """The use case over a store holding these rows, with Qobuz and Bleep shipped."""
    book = ShopBook(rows=rows, shipped=(QOBUZ, BLEEP), retired=retired)
    store, opener = Store(book, refuse), Opener(takes)
    return ShopEditing(store, opener), store, opener


def test_the_list_drawn_is_the_stores() -> None:
    use, store, _opener = editing(QOBUZ)
    assert use.book() is store.held


def test_an_added_shop_goes_last() -> None:
    """FR-S19."""
    use, store, _opener = editing(QOBUZ)
    assert use.add(JUNO).rows == (QOBUZ, JUNO)
    assert store.held.rows == (QOBUZ, JUNO)


def test_an_edited_shop_keeps_its_place() -> None:
    """FR-S19."""
    use, store, _opener = editing(QOBUZ, BLEEP, JUNO)
    edited = Shop("Bleep", BLEEP.template, "Warp.")
    use.edit(1, edited)
    assert store.held.rows == (QOBUZ, edited, JUNO)


def test_deleting_a_shipped_shop_records_it() -> None:
    """FR-S25."""
    use, store, _opener = editing(QOBUZ, BLEEP)
    use.delete(1)
    assert store.held.rows == (QOBUZ,)
    assert store.held.deleted == ("Bleep",)


def test_renaming_a_shipped_shop_records_the_old_name() -> None:
    """FR-S26."""
    use, store, _opener = editing(QOBUZ)
    use.edit(0, Shop("Qobuz UK", QOBUZ.template))
    assert store.held.deleted == ("Qobuz",)


def test_a_move_is_kept() -> None:
    """FR-S28."""
    use, store, _opener = editing(QOBUZ, BLEEP)
    use.move(1, -1)
    assert store.held.rows == (BLEEP, QOBUZ)


def test_a_move_that_changes_nothing_writes_nothing() -> None:
    """A move past the top is no move, so no write nobody asked for."""
    use, store, _opener = editing(QOBUZ, BLEEP)
    use.move(0, -1)
    use.move_to(1, 1)
    assert store.saved == []


def test_a_drag_is_kept() -> None:
    """FR-S27."""
    use, store, _opener = editing(QOBUZ, BLEEP, JUNO)
    use.move_to(2, 0)
    assert store.held.rows == (JUNO, QOBUZ, BLEEP)


def test_putting_back_is_kept() -> None:
    """FR-S37."""
    use, store, _opener = editing(JUNO)
    use.put_back()
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)


def test_a_change_that_cannot_be_kept_raises_and_is_not_held() -> None:
    """FR-S29: the dialog must go on showing what the file holds."""
    use, store, _opener = editing(QOBUZ, refuse=True)
    with pytest.raises(ShopListUnwritable):
        use.delete(0)
    assert store.held.rows == (QOBUZ,)


def test_the_form_does_not_count_the_row_being_edited_as_taken() -> None:
    """FR-S21, where the edit keeps its own name."""
    use, _store, _opener = editing(QOBUZ, BLEEP)
    assert use.problems("Qobuz", "https://q/{artist}", 0) == ()
    assert use.problems("Qobuz", "https://q/{artist}", 1) == (ShopProblem.NAME_TAKEN,)


def test_try_opens_the_album_it_is_given_and_keeps_nothing() -> None:
    """FR-S22: a try is a look, not a save."""
    use, store, opener = editing(QOBUZ)
    assert use.try_shop(Shop("X", "https://x/?q={artist}"), HOUNDS)
    assert opener.opened == ["https://x/?q=Kate%20Bush"]
    assert store.saved == []


def test_a_try_that_will_not_open_says_so() -> None:
    """FR-S23."""
    use, _store, _opener = editing(QOBUZ, takes=False)
    assert not use.try_shop(QOBUZ, HOUNDS)


def test_retired_shops_are_announced_once() -> None:
    """FR-S35."""
    use, store, _opener = editing(QOBUZ, retired=("Bleep",))
    assert use.announce() == ("Bleep",)
    assert use.announce() == ()
    assert store.held.retired == ()


def test_nothing_retired_writes_nothing() -> None:
    use, store, _opener = editing(QOBUZ)
    assert use.announce() == ()
    assert store.saved == []


def test_an_announcement_that_cannot_be_kept_is_still_made() -> None:
    """Told now and again next time beats not told at all."""
    use, store, _opener = editing(QOBUZ, retired=("Bleep",), refuse=True)
    assert use.announce() == ("Bleep",)
    assert store.held.retired == ("Bleep",)


def test_shopping_carries_no_editor_unless_given_one() -> None:
    """The dialogs built before the editor still build."""
    use, store, opener = editing(QOBUZ)
    assert Shopping(store, opener, None).editing is None
    assert Shopping(store, opener, None, use).editing is use
