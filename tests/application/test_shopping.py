"""Taking ticked albums to a shop, over hand-written stand-ins.

No browser is opened here and no file is read: the point of the use case having
three ports is that every one of its decisions can be driven without either.
"""

from __future__ import annotations

from stellody.application.shopping import MOST_WITHOUT_ASKING, Shopping
from stellody.domain.shopping import Shop, WantedAlbum

QOBUZ = Shop(name="Qobuz", template="https://q/?a={artist}&b={album}")
BLEEP = Shop(name="Bleep", template="https://b/?q={artist}%20{album}")
HOUNDS = WantedAlbum(artist="Kate Bush", title="Hounds of Love")
AMBER = WantedAlbum(artist="Autechre", title="Amber")


class Shops:
    """A shop list answering with whatever the test handed it."""

    def __init__(self, *shops: Shop) -> None:
        self._shops = shops
        self.asked = 0

    def shops(self) -> tuple[Shop, ...]:
        """What this fake was told, counting how often it was asked."""
        self.asked += 1
        return self._shops


class Opener:
    """An opener that records; it refuses whatever it was told to."""

    def __init__(self, refuse: tuple[str, ...] = ()) -> None:
        self.opened: list[str] = []
        self._refuse = refuse

    def open(self, address: str) -> bool:
        """Take the address unless this one was set up to be refused."""
        self.opened.append(address)
        return not any(word in address for word in self._refuse)


class Clipboard:
    """A clipboard that only remembers what it was given."""

    def __init__(self) -> None:
        self.holds: list[str] = []

    def put(self, text: str) -> None:
        """Keep it, the way a real clipboard replaces what was there."""
        self.holds.append(text)


def make(*shops: Shop, refuse: tuple[str, ...] = ()):
    """The use case over three stand-ins, with all three answered back."""
    listing, opener, clipboard = Shops(*shops), Opener(refuse), Clipboard()
    return Shopping(listing, opener, clipboard), listing, opener, clipboard


def test_the_shops_offered_are_the_ones_the_list_holds() -> None:
    """The dialog draws what the file said, in the file's own order."""
    shopping, listing, _opener, _clipboard = make(QOBUZ, BLEEP)
    assert shopping.offered() == (QOBUZ, BLEEP)
    assert listing.asked == 1


def test_choosing_a_shop_opens_one_address_an_album() -> None:
    """FR-S06: no shop searches for two albums at once."""
    shopping, _listing, opener, _clipboard = make(QOBUZ)
    assert shopping.look_up(QOBUZ, (HOUNDS, AMBER)) == ()
    assert opener.opened == [QOBUZ.address_for(HOUNDS), QOBUZ.address_for(AMBER)]


def test_an_address_the_machine_refuses_is_reported() -> None:
    """FR-S13: nothing happening at all is the one unreadable outcome."""
    shopping, _listing, _opener, _clipboard = make(QOBUZ, refuse=("Hounds",))
    assert shopping.look_up(QOBUZ, (HOUNDS,)) == (QOBUZ.address_for(HOUNDS),)


def test_one_refusal_does_not_lose_the_rest_of_the_list() -> None:
    """A machine that refused one address may well take the next."""
    shopping, _listing, opener, _clipboard = make(QOBUZ, refuse=("Hounds",))
    refused = shopping.look_up(QOBUZ, (HOUNDS, AMBER))
    assert refused == (QOBUZ.address_for(HOUNDS),)
    assert QOBUZ.address_for(AMBER) in opener.opened


def test_a_handful_of_albums_is_not_worth_asking_about() -> None:
    """FR-S08: the bar is where the tabs stop being what anybody expects."""
    shopping, _listing, _opener, _clipboard = make(QOBUZ)
    wanted = tuple(
        WantedAlbum(artist="A", title=f"Album {n}") for n in range(MOST_WITHOUT_ASKING)
    )
    assert not shopping.needs_asking(wanted)


def test_one_more_than_the_bar_is_asked_about() -> None:
    """The other side of the same line, so the bar itself is pinned."""
    shopping, _listing, _opener, _clipboard = make(QOBUZ)
    wanted = tuple(
        WantedAlbum(artist="A", title=f"Album {n}")
        for n in range(MOST_WITHOUT_ASKING + 1)
    )
    assert shopping.needs_asking(wanted)


def test_copying_puts_a_line_an_album_on_the_clipboard() -> None:
    """FR-S14: the fallback for every shop nobody has configured."""
    shopping, _listing, _opener, clipboard = make(QOBUZ)
    text = shopping.copy((HOUNDS, AMBER))
    assert text == "Kate Bush - Hounds of Love\nAutechre - Amber"
    assert clipboard.holds == [text]


def test_nothing_ticked_opens_nothing_and_copies_nothing() -> None:
    """The empty case, which the dialog prevents and this still answers."""
    shopping, _listing, opener, clipboard = make(QOBUZ)
    assert shopping.look_up(QOBUZ, ()) == ()
    assert shopping.copy(()) == ""
    assert opener.opened == []
    assert clipboard.holds == [""]
