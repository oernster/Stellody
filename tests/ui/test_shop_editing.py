"""Changing the shops from the shops dialog. SHOPS.md Amendment 1."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from stellody.application.shop_editing import ShopEditing, ShopListUnwritable
from stellody.application.shopping import Shopping
from stellody.domain.shop_list import BrokenRow, ShopBook, ShopProblem
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.ui.palette import Mode
from stellody.ui.shop_form import ShopForm
from stellody.ui.shops_dialog import NO_SHOPS_YET, ShopsDialog

QOBUZ = Shop("Qobuz", "https://q/?q={artist}", "Lossless.")
BLEEP = Shop("Bleep", "https://b/?q={album}")
JUNO = Shop("Juno", "https://j/?q={artist}")
BROKEN = BrokenRow("Odd", "https://odd/", "", ShopProblem.NO_PLACEHOLDER)
HOUNDS = WantedAlbum(artist="Kate Bush", title="Hounds of Love")


class Store:
    """A list in memory; refuses writes where told."""

    def __init__(self, book: ShopBook, refuse: bool = False) -> None:
        self.held = book
        self.refuse = refuse

    def book(self) -> ShopBook:
        return self.held

    def save(self, book: ShopBook) -> None:
        if self.refuse:
            raise ShopListUnwritable("read only")
        self.held = book


class Opener:
    """Records what it was asked to open."""

    def __init__(self, takes: bool = True) -> None:
        self.opened: list[str] = []
        self.takes = takes

    def open(self, address: str) -> bool:
        self.opened.append(address)
        return self.takes


class Nowhere:
    def shops(self) -> tuple[Shop, ...]:
        return ()

    def put(self, text: str) -> None:
        """Take it and forget it."""


def dialog_over(*rows, retired=(), refuse=False, takes=True):
    """A shown shops dialog with an editor over these rows."""
    store = Store(ShopBook(rows=rows, shipped=(QOBUZ, BLEEP), retired=retired), refuse)
    opener = Opener(takes)
    editing = ShopEditing(store, opener)
    shopping = Shopping(Nowhere(), opener, Nowhere(), editing)
    dialog = ShopsDialog(shopping, (HOUNDS,), Mode.DARK)
    dialog.show()
    return dialog, store, opener, editing


def answering(monkeypatch: pytest.MonkeyPatch, yes: bool, asked: list[str]) -> None:
    """Stand in front of every question with one answer."""
    answer = QMessageBox.StandardButton.Yes if yes else QMessageBox.StandardButton.No

    def question(_parent, _title, text, *_arguments, **_named):
        asked.append(text)
        return answer

    monkeypatch.setattr(QMessageBox, "question", question)


@pytest.fixture
def forms(monkeypatch: pytest.MonkeyPatch) -> list[ShopForm]:
    """Every form the dialog opens, kept instead of being run."""
    opened: list[ShopForm] = []

    def exec_(form) -> int:
        opened.append(form)
        return 0

    monkeypatch.setattr(ShopForm, "exec", exec_)
    return opened


def test_add_opens_an_empty_form(application, forms) -> None:
    """FR-S17."""
    dialog, *_rest = dialog_over(QOBUZ)
    dialog.add_button.click()
    assert [forms[0].name.text(), forms[0].address.text()] == ["", ""]


def test_edit_opens_the_form_holding_the_shop(application, forms) -> None:
    """FR-S18."""
    dialog, *_rest = dialog_over(QOBUZ, BLEEP)
    dialog.controls[0].edit.click()
    assert forms[0].name.text() == "Qobuz"
    assert forms[0].address.text() == QOBUZ.template
    assert forms[0].note.text() == "Lossless."


def test_a_saved_form_puts_the_shop_last(application) -> None:
    """FR-S19."""
    _dialog, store, _opener, editing = dialog_over(QOBUZ)
    form = ShopForm(editing, HOUNDS)
    form.name.setText("Juno")
    form.address.setText(JUNO.template)
    form.save()
    assert store.held.rows == (QOBUZ, JUNO)
    assert form.result() == ShopForm.DialogCode.Accepted


def test_a_shop_that_cannot_search_is_not_saved(application) -> None:
    """FR-S20 and FR-S21, both said at once beside their fields."""
    _dialog, store, _opener, editing = dialog_over(QOBUZ)
    form = ShopForm(editing, HOUNDS)
    form.name.setText("qobuz")
    form.address.setText("https://example.com/search")
    form.save()
    assert store.held.rows == (QOBUZ,)
    assert "already has that name" in form.name_problem.text()
    assert "neither" in form.address_problem.text()


def test_a_form_that_cannot_be_kept_says_so(application) -> None:
    """FR-S29 from inside the form."""
    _dialog, _store, _opener, editing = dialog_over(QOBUZ, refuse=True)
    form = ShopForm(editing, HOUNDS, 0, QOBUZ)
    form.note.setText("Changed.")
    form.save()
    assert "could not be saved" in form.said.text()


def test_try_opens_the_first_ticked_album(application) -> None:
    """FR-S22: a look, not a save."""
    _dialog, store, opener, editing = dialog_over(QOBUZ)
    form = ShopForm(editing, HOUNDS)
    form.address.setText("https://x/?q={artist}")
    form.try_it()
    assert opener.opened == ["https://x/?q=Kate%20Bush"]
    assert store.held.rows == (QOBUZ,)
    assert "Kate Bush" in form.said.text()


def test_a_try_with_a_broken_address_opens_nothing(application) -> None:
    _dialog, _store, opener, editing = dialog_over(QOBUZ)
    form = ShopForm(editing, HOUNDS)
    form.address.setText("http://x/?q={artist}")
    form.try_it()
    assert opener.opened == []
    assert "https://" in form.address_problem.text()


def test_a_try_that_will_not_open_says_so(application) -> None:
    """FR-S23."""
    _dialog, _store, _opener, editing = dialog_over(QOBUZ, takes=False)
    form = ShopForm(editing, HOUNDS)
    form.address.setText(QOBUZ.template)
    form.try_it()
    assert "could not be opened" in form.said.text()


def test_delete_asks_naming_the_shop(application, monkeypatch) -> None:
    """FR-S24."""
    asked: list[str] = []
    answering(monkeypatch, True, asked)
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP)
    dialog.controls[1].delete.click()
    assert "Bleep" in asked[0]
    assert store.held.rows == (QOBUZ,)
    assert set(dialog.shop_buttons) == {"Qobuz"}


def test_a_refused_delete_keeps_the_shop(application, monkeypatch) -> None:
    answering(monkeypatch, False, [])
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP)
    dialog.controls[1].delete.click()
    assert store.held.rows == (QOBUZ, BLEEP)


def test_dragging_the_handle_moves_the_shop(application) -> None:
    """FR-S27: dropped above the first row, the third becomes first."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP, JUNO)
    application.processEvents()
    top = dialog.controls[0].holder
    above_it = top.mapToGlobal(top.rect().topLeft())
    dialog.drop(2, above_it)
    assert store.held.rows == (JUNO, QOBUZ, BLEEP)


def test_ctrl_arrows_move_the_focused_shop(application) -> None:
    """FR-S28: focus follows the shop; a move past the top does nothing."""
    dialog, store, *_rest = dialog_over(QOBUZ, BLEEP)
    dialog.controls[1].button.setFocus()
    dialog.move_focused(-1)
    assert store.held.rows == (BLEEP, QOBUZ)
    assert dialog.focusWidget() is dialog.controls[0].button
    dialog.move_focused(-1)
    assert store.held.rows == (BLEEP, QOBUZ)


def test_the_arrows_are_bound_to_ctrl(application) -> None:
    dialog, *_rest = dialog_over(QOBUZ)
    keys = {shortcut.key().toString() for shortcut in dialog._shortcuts}
    assert keys == {"Ctrl+Up", "Ctrl+Down"}


def test_a_change_that_cannot_be_saved_is_not_shown(application, monkeypatch) -> None:
    """FR-S29."""
    answering(monkeypatch, True, [])
    dialog, _store, *_rest = dialog_over(QOBUZ, refuse=True)
    dialog.controls[0].delete.click()
    assert "could not be saved" in dialog.said.text()
    assert set(dialog.shop_buttons) == {"Qobuz"}


def test_a_removed_shop_is_announced_once(application) -> None:
    """FR-S35."""
    dialog, _store, _opener, editing = dialog_over(QOBUZ, retired=("Bleep",))
    assert "Bleep" in dialog.announced.text()
    again = ShopsDialog(Shopping(Nowhere(), Opener(), Nowhere(), editing), (HOUNDS,))
    assert again.announced.text() == ""


def test_putting_back_asks_first(application, monkeypatch) -> None:
    """FR-S37 and FR-S38."""
    answering(monkeypatch, False, [])
    dialog, store, *_rest = dialog_over(JUNO)
    dialog.put_back_button.click()
    assert store.held.rows == (JUNO,)
    answering(monkeypatch, True, [])
    dialog.put_back_button.click()
    assert store.held.rows == (QOBUZ, BLEEP, JUNO)


def test_an_empty_list_offers_add(application) -> None:
    """FR-S39."""
    dialog, *_rest = dialog_over()
    lines = [label.text() for label in dialog.findChildren(type(dialog.counted))]
    assert NO_SHOPS_YET in lines
    assert not any("shops.json" in line for line in lines)
    assert dialog.add_button.isVisible()


def test_the_ring_walks_the_rows_in_reading_order(application) -> None:
    """FR-S40: each row's button, edit and delete, then add, put back, Close."""
    dialog, *_rest = dialog_over(QOBUZ, BLEEP)
    first, second = dialog.controls
    expected = [
        first.button,
        first.edit,
        first.delete,
        second.button,
        second.edit,
        second.delete,
        dialog.add_button,
        dialog.put_back_button,
        dialog.close_button,
    ]
    walked, widget = [], first.button
    for _ in expected:
        walked.append(widget)
        widget = widget.nextInFocusChain()
        while not widget.focusPolicy() & Qt.FocusPolicy.TabFocus:
            widget = widget.nextInFocusChain()
    assert walked == expected


def test_a_broken_row_is_listed_greyed_with_its_reason(application, forms) -> None:
    """FR-S42: never searched, still mended or removed from here."""
    dialog, *_rest = dialog_over(BROKEN, QOBUZ)
    broken = dialog.controls[0]
    assert not broken.button.isEnabled()
    assert "neither" in broken.button.text()
    assert "Odd" not in dialog.shop_buttons
    broken.edit.click()
    assert forms[0].address.text() == "https://odd/"
