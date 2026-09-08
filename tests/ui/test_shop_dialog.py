"""The dialog that takes the ticked albums to a shop.

It stays open on purpose, it asks before a great many tabs and it says when a
machine would not open one. Those three are the whole of it; each was a
ruling rather than a preference.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QMessageBox

from stellody.application.shopping import MOST_WITHOUT_ASKING, Shopping
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.ui.palette import Mode
from stellody.ui.shops_dialog import NO_SHOPS, ShopsDialog

QOBUZ = Shop(
    name="Qobuz",
    template="https://q/?q={artist}%20{album}",
    note="Lossless only.",
)
BLEEP = Shop(name="Bleep", template="https://b/?q={artist}%20{album}")
HOUNDS = WantedAlbum(artist="Kate Bush", title="Hounds of Love")
AERIAL = WantedAlbum(artist="Kate Bush", title="Aerial")


class Shops:
    """A shop list holding whatever the test handed it."""

    def __init__(self, *shops: Shop) -> None:
        self._shops = shops

    def shops(self) -> tuple[Shop, ...]:
        """What this fake was told."""
        return self._shops


class Opener:
    """An opener that records; it refuses when told to."""

    def __init__(self, refuse: bool = False) -> None:
        self.opened: list[str] = []
        self._refuse = refuse

    def open(self, address: str) -> bool:
        """Take the address unless this one was told to refuse."""
        self.opened.append(address)
        return not self._refuse


class Clipboard:
    """A clipboard nothing in this file uses, since none of it copies."""

    def put(self, text: str) -> None:
        """Take it and forget it."""


def made(
    *shops: Shop,
    wanted: tuple[WantedAlbum, ...] = (HOUNDS,),
    refuse: bool = False,
):
    """The dialog over stand-ins, with the opener answered back."""
    opener = Opener(refuse)
    shopping = Shopping(Shops(*shops), opener, Clipboard())
    dialog = ShopsDialog(shopping, wanted, Mode.DARK)
    # Shown, because the thing being asserted below is that it is STILL shown
    # after a shop has been chosen.
    dialog.show()
    return dialog, opener


def answering(monkeypatch: pytest.MonkeyPatch, button, asked: list[str]) -> None:
    """Stand in front of the question with this answer, keeping what it said."""

    def question(_parent, _title, text, *_arguments, **_named):
        """Qt's own signature, since it is Qt's own method being replaced."""
        asked.append(text)
        return button

    monkeypatch.setattr(QMessageBox, "question", question)


def many(count: int) -> tuple[WantedAlbum, ...]:
    """That many ticked albums."""
    return tuple(
        WantedAlbum(artist="Kate Bush", title=f"Album {n}") for n in range(count)
    )


def test_it_lists_the_shops_and_counts_the_albums(application) -> None:
    """FR-S05: the choice is worth a screen; so is the count."""
    dialog, _opener = made(QOBUZ, BLEEP, wanted=(HOUNDS, AERIAL))
    assert set(dialog.shop_buttons) == {"Qobuz", "Bleep"}
    assert "2 albums" in dialog.counted.text()


def test_one_album_reads_as_one_album(application) -> None:
    """One of something reads as one of it."""
    dialog, _opener = made(QOBUZ)
    assert "1 album ticked" in dialog.counted.text()


def test_a_shop_says_what_it_stocks_where_it_says_anything(application) -> None:
    """What a shop carries is as much of the choice as its name."""
    dialog, _opener = made(QOBUZ, BLEEP)
    assert "Lossless only." in dialog.shop_buttons["Qobuz"].text()
    assert dialog.shop_buttons["Bleep"].text() == "Bleep"


def test_choosing_a_shop_opens_one_search_an_album(application) -> None:
    """FR-S06: no shop searches for two albums at once."""
    dialog, opener = made(QOBUZ, wanted=(HOUNDS, AERIAL))
    dialog.chose(QOBUZ)
    assert opener.opened == [QOBUZ.address_for(HOUNDS), QOBUZ.address_for(AERIAL)]


def test_it_stays_open_so_prices_can_be_compared(application) -> None:
    """FR-S07, ruled by Oliver: the second shop is the point of the first."""
    dialog, opener = made(QOBUZ, BLEEP)
    dialog.chose(QOBUZ)
    assert dialog.isVisible(), "still there for the next shop"
    dialog.chose(BLEEP)
    assert dialog.isVisible()
    assert opener.opened == [QOBUZ.address_for(HOUNDS), BLEEP.address_for(HOUNDS)]


def test_it_says_what_it_just_opened(application) -> None:
    """A press that quietly worked is a press somebody can see worked."""
    dialog, _opener = made(QOBUZ, wanted=(HOUNDS, AERIAL))
    dialog.chose(QOBUZ)
    assert "2 searches at Qobuz" in dialog.said.text()


def test_a_large_number_of_tabs_is_asked_about_first(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-S08: thirty tabs arriving at once is nobody's deliberate choice."""
    asked: list[str] = []
    answering(monkeypatch, QMessageBox.StandardButton.Yes, asked)
    wanted = many(MOST_WITHOUT_ASKING + 1)
    dialog, opener = made(QOBUZ, wanted=wanted)
    dialog.chose(QOBUZ)
    assert asked and f"{len(wanted)} browser tabs" in asked[0]
    assert len(opener.opened) == len(wanted)


def test_a_refused_confirmation_opens_nothing(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unwanted sibling: no is no, rather than fewer tabs."""
    answering(monkeypatch, QMessageBox.StandardButton.No, [])
    dialog, opener = made(QOBUZ, wanted=many(MOST_WITHOUT_ASKING + 1))
    dialog.chose(QOBUZ)
    assert opener.opened == []


def test_a_handful_is_not_asked_about(
    application, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other side of the same line, so the bar itself is pinned."""
    asked: list[str] = []
    answering(monkeypatch, QMessageBox.StandardButton.No, asked)
    dialog, opener = made(QOBUZ, wanted=many(MOST_WITHOUT_ASKING))
    dialog.chose(QOBUZ)
    assert asked == []
    assert len(opener.opened) == MOST_WITHOUT_ASKING


def test_a_browser_that_will_not_open_says_so(application) -> None:
    """FR-S13: nothing happening is the one outcome nobody can read."""
    dialog, _opener = made(QOBUZ, refuse=True)
    dialog.chose(QOBUZ)
    assert "could not be opened" in dialog.said.text()


def test_a_refusal_leaves_the_dialog_standing(application) -> None:
    """A shop that failed is not a reason to lose the other shops."""
    dialog, opener = made(QOBUZ, BLEEP, refuse=True)
    dialog.chose(QOBUZ)
    dialog.chose(BLEEP)
    assert len(opener.opened) == 2
    assert dialog.shop_buttons["Bleep"].isEnabled()


def test_an_empty_shop_list_says_where_to_put_one(application) -> None:
    """Takes a deliberately emptied file; the reader falls back otherwise."""
    dialog, _opener = made()
    assert dialog.shop_buttons == {}
    lines = [
        child.text()
        for child in dialog.findChildren(type(dialog.counted))
        if child.text()
    ]
    assert any(NO_SHOPS in line for line in lines)


def test_pressing_a_shop_button_is_the_same_as_choosing_it(application) -> None:
    """The wiring between the button and the work, which nothing else tests."""
    dialog, opener = made(QOBUZ)
    dialog.shop_buttons["Qobuz"].click()
    assert opener.opened == [QOBUZ.address_for(HOUNDS)]
