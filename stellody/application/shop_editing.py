"""Changing the shop list from the shops dialog. SHOPS.md Amendment 1.

Every change is read from the store, applied by the domain, then written back
before anybody is shown it. A change the file will not take raises, so the
dialog goes on showing the list the file actually holds rather than one it
merely wished it held. FR-S29.

The rules themselves are not here. What an edit, a delete or a move MEANS lives
in `domain/shop_list.py`, where it is pure; this is the sequence around it, so
every action the dialog offers can be driven with no screen and no file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stellody.application.shopping import OpenAddress
from stellody.domain.shop_list import ShopBook, ShopProblem, form_problems
from stellody.domain.shopping import Shop, WantedAlbum


class ShopListUnwritable(Exception):
    """The shop file would not take a change."""


class ShopBookStore(Protocol):
    """Where the shop list is kept, settled against this release when read."""

    def book(self) -> ShopBook:
        """The list as it stands."""
        ...

    def save(self, book: ShopBook) -> None:
        """Keep this list; raise `ShopListUnwritable` where it cannot be kept."""
        ...


@dataclass(frozen=True, slots=True)
class ShopEditing:
    """Every change the shops dialog can make, over a store and an opener."""

    store: ShopBookStore
    opener: OpenAddress

    def book(self) -> ShopBook:
        """The list to draw."""
        return self.store.book()

    def problems(
        self, name: str, template: str, index: int | None
    ) -> tuple[ShopProblem, ...]:
        """What stops a form saving; `index` is the row being edited, if any."""
        taken = self.store.book().names_other_than(index)
        return form_problems(name, template, taken)

    def add(self, shop: Shop) -> ShopBook:
        """Put a new shop at the bottom and keep it. FR-S19."""
        return self._kept(self.store.book().added(shop))

    def edit(self, index: int, shop: Shop) -> ShopBook:
        """Replace the row at `index` in its place and keep it. FR-S19."""
        return self._kept(self.store.book().replaced(index, shop))

    def delete(self, index: int) -> ShopBook:
        """Remove the row at `index` and keep that. FR-S24, FR-S25."""
        return self._kept(self.store.book().removed(index))

    def move(self, index: int, offset: int) -> ShopBook:
        """Move a row by `offset` places, writing only a real change. FR-S28."""
        before = self.store.book()
        return self._changed(before, before.moved(index, offset))

    def move_to(self, index: int, target: int) -> ShopBook:
        """Move a row to `target`, writing only a real change. FR-S27."""
        before = self.store.book()
        return self._changed(before, before.moved_to(index, target))

    def put_back(self) -> ShopBook:
        """The shipped shops as shipped, then the listener's own. FR-S37."""
        return self._kept(self.store.book().put_back())

    def announce(self) -> tuple[str, ...]:
        """The shops a release removed, forgotten once said. FR-S35.

        Said even where forgetting cannot be written: the listener is told
        now and told again next time, which beats not being told at all.
        """
        book = self.store.book()
        if not book.retired:
            return ()
        try:
            self.store.save(book.announced())
        except ShopListUnwritable:
            pass
        return book.retired

    def try_shop(self, shop: Shop, album: WantedAlbum) -> bool:
        """Open this shop's search for one album without keeping it. FR-S22."""
        return self.opener.open(shop.address_for(album))

    def _changed(self, before: ShopBook, after: ShopBook) -> ShopBook:
        """Keep `after` only where it differs from `before`."""
        if after is before:
            return before
        return self._kept(after)

    def _kept(self, book: ShopBook) -> ShopBook:
        """Write this list, then answer with it."""
        self.store.save(book)
        return book
