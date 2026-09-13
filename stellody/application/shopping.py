"""Taking ticked albums to a shop; or to the clipboard.

The use case stage two is made of, plus the three things it needs from outside
itself. It holds no address of its own: where the shops come from, how a page
is opened and where text is put are all handed in, so the whole of this can be
driven in a test with no browser, no file and no screen.

**Opening reports rather than assumes.** An address handed to an operating
system that has no browser or that refuses is the one case indistinguishable
from the application being broken. So the port answers whether it worked and
this collects what did not, for somebody to be told about. FR-S13.

**The bar for asking first lives here.** How many browser tabs may open without
a question is a rule about the work rather than about the screen that asks it,
so the number sits beside the use case and the dialog reads it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from stellody.domain.shopping import Shop, WantedAlbum, addresses_at, copied_text

if TYPE_CHECKING:
    from stellody.application.shop_editing import ShopEditing

# How many albums may be looked up before somebody is asked. One album is one
# browser tab: thirty ticked albums is thirty tabs arriving over whatever was
# being done, which nobody chooses deliberately. Ruled by Oliver on 2026-09-08.
MOST_WITHOUT_ASKING = 5


class ShopList(Protocol):
    """Where the shops come from; data rather than code.

    Measured on 2026-09-07: of eight shops checked, one had closed, one had
    walled its search and one had moved it. A list compiled into the
    application needs a release every time that happens, so it is read from
    somewhere a listener can edit.
    """

    def shops(self) -> tuple[Shop, ...]:
        """Every shop worth offering, in the order to offer them."""
        ...


class OpenAddress(Protocol):
    """Hands one address to whatever the machine opens pages with."""

    def open(self, address: str) -> bool:
        """True where it was taken; False where the machine would not."""
        ...


class PutOnClipboard(Protocol):
    """Puts plain text where a paste will find it."""

    def put(self, text: str) -> None:
        """Replace whatever is on the clipboard with this."""
        ...


@dataclass(frozen=True, slots=True)
class Shopping:
    """Everything stage two does, over three things handed in.

    `editing` is the shop list editor of SHOPS.md Amendment 1. It travels with
    this rather than beside it, since everywhere the shops are offered is
    somewhere they can be changed; None leaves the dialog without the editor.
    """

    shops: ShopList
    opener: OpenAddress
    clipboard: PutOnClipboard
    editing: ShopEditing | None = None

    def offered(self) -> tuple[Shop, ...]:
        """The shops to put in front of somebody."""
        return self.shops.shops()

    def needs_asking(self, wanted: tuple[WantedAlbum, ...]) -> bool:
        """Whether this many tabs is more than anybody expects. FR-S08."""
        return len(wanted) > MOST_WITHOUT_ASKING

    def look_up(self, shop: Shop, wanted: tuple[WantedAlbum, ...]) -> tuple[str, ...]:
        """Open this shop's search for each ticked album; what would not open.

        Every album is attempted even after one fails, since a machine that
        refused one address may well take the next and the alternative is
        losing the rest of a list to its first bad entry.
        """
        return tuple(
            address
            for address in addresses_at(shop, wanted)
            if not self.opener.open(address)
        )

    def copy(self, wanted: tuple[WantedAlbum, ...]) -> str:
        """Put the ticked albums on the clipboard; what was put there. FR-S14."""
        text = copied_text(wanted)
        self.clipboard.put(text)
        return text
