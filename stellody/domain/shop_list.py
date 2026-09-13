"""The shop list as something somebody edits; how a release's shops meet it.

SHOPS.md Amendment 1. Before it the list could only be changed by hand in
`shops.json`, where a mistyped row vanished without a word. Now it is changed
from the shops dialog, so the rules for every change live here, pure, where the
coverage gate holds them.

**A shop is recognised by its name.** A release carries no identifier for a
shop, only what the file carries: a name, an address and a note. So the name,
compared ignoring case, is what says two rows are the same shop across releases.
That is why two shops may not share one (FR-S21) and why renaming a shipped shop
records the old name as deleted (FR-S26): otherwise the next release would find
the old name missing and put the shop back beside its renamed self.

**A release meets the list shop by shop, not file by file.** FR-S16 used to ask
whether the whole file had been edited, replacing it where not. With an editor
nearly every file is edited somewhere, which would have frozen every one of them
against every correction. So each row is settled on its own (FR-S30 to FR-S34):
an untouched shipped shop follows the release, an edited one keeps the edit, a
deleted one stays deleted, a new one is added at the bottom, a dropped untouched
one is removed and named so the dialog can say so once.

**A row that is not a shop is kept rather than dropped.** A hand-edited row
that cannot be searched is carried as a `BrokenRow` with its reason, in its own
place, so the dialog can list it greyed out and somebody can mend or delete it
(FR-S42). A release never merges into one; it is nobody's but the listener's.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from stellody.domain.shopping import ALBUM_PLACEHOLDER, ARTIST_PLACEHOLDER, Shop

# The only scheme a shop form will save. A search is a page somebody reads and
# may buy from; an unencrypted one is not worth offering. Hand-edited rows are
# not held to it, so an older file keeps working. FR-S20.
SECURE_SCHEME = "https://"


class ShopProblem(Enum):
    """Why a row cannot be searched; also why a form will not save."""

    NO_NAME = "no_name"
    NO_ADDRESS = "no_address"
    NOT_SECURE = "not_secure"
    NO_PLACEHOLDER = "no_placeholder"
    NAME_TAKEN = "name_taken"
    NOT_A_ROW = "not_a_row"


class NameTakenError(ValueError):
    """A shop was offered under a name another shop in the list already has."""


@dataclass(frozen=True, slots=True)
class BrokenRow:
    """A row of the file that cannot be read as a shop, with what is wrong."""

    name: str
    template: str
    note: str
    problem: ShopProblem


Row = Shop | BrokenRow


def key_of(name: str) -> str:
    """What a name is compared by: its letters, ignoring case and edges."""
    return name.strip().casefold()


def _names_a_placeholder(template: str) -> bool:
    """Whether a template puts anything of the album into the address."""
    return ARTIST_PLACEHOLDER in template or ALBUM_PLACEHOLDER in template


def row_problem(name: str, template: str) -> ShopProblem | None:
    """Why a hand-written row cannot be a shop; None where it can.

    The same three rules `Shop` refuses on, stated as a reason rather than an
    exception so the dialog can say which one a row broke. FR-S42.
    """
    if not name.strip():
        return ShopProblem.NO_NAME
    if not template.strip():
        return ShopProblem.NO_ADDRESS
    if not _names_a_placeholder(template):
        return ShopProblem.NO_PLACEHOLDER
    return None


def form_problems(
    name: str, template: str, taken: tuple[str, ...]
) -> tuple[ShopProblem, ...]:
    """Everything that stops a shop form saving, one reason per field at most.

    `taken` is every other name in the list. The name and the address are
    judged apart, so a form wrong in both says so for both at once. FR-S20 and
    FR-S21.
    """
    problems: list[ShopProblem] = []
    if not name.strip():
        problems.append(ShopProblem.NO_NAME)
    elif key_of(name) in {key_of(other) for other in taken}:
        problems.append(ShopProblem.NAME_TAKEN)
    address = template.strip()
    if not address:
        problems.append(ShopProblem.NO_ADDRESS)
    elif not address.casefold().startswith(SECURE_SCHEME):
        problems.append(ShopProblem.NOT_SECURE)
    elif not _names_a_placeholder(address):
        problems.append(ShopProblem.NO_PLACEHOLDER)
    return tuple(problems)


def _with_name(names: tuple[str, ...], name: str) -> tuple[str, ...]:
    """These names plus one more, where it is not already among them."""
    if key_of(name) in {key_of(held) for held in names}:
        return names
    return (*names, name)


@dataclass(frozen=True, slots=True)
class ShopBook:
    """Everything the shop file says: the rows, the release record and the notes.

    `shipped` is the release list the rows were last settled against; `deleted`
    names shipped shops somebody removed; `retired` names shops a release
    dropped that the dialog has not yet announced.
    """

    rows: tuple[Row, ...]
    shipped: tuple[Shop, ...]
    deleted: tuple[str, ...] = ()
    retired: tuple[str, ...] = ()

    @property
    def shops(self) -> tuple[Shop, ...]:
        """The rows that can be searched, in their order."""
        return tuple(row for row in self.rows if isinstance(row, Shop))

    def names_other_than(self, index: int | None) -> tuple[str, ...]:
        """Every row's name except the one at `index`; all of them for None."""
        return tuple(row.name for at, row in enumerate(self.rows) if at != index)

    def _is_shipped(self, name: str) -> bool:
        """Whether a release this list was settled against carries that name."""
        return key_of(name) in {key_of(shop.name) for shop in self.shipped}

    def _refuse_taken(self, shop: Shop, index: int | None) -> None:
        """Raise where another row already carries this shop's name. FR-S21."""
        if key_of(shop.name) in {key_of(n) for n in self.names_other_than(index)}:
            raise NameTakenError(f"a shop named {shop.name} is already listed")

    def added(self, shop: Shop) -> ShopBook:
        """This list with a new shop at the bottom. FR-S19."""
        self._refuse_taken(shop, None)
        return replace(self, rows=(*self.rows, shop))

    def replaced(self, index: int, shop: Shop) -> ShopBook:
        """This list with the row at `index` edited in its own place.

        A shipped shop saved under another name is a delete of the old name
        plus an add, so the old name is recorded as deleted. FR-S19, FR-S26.
        """
        self._refuse_taken(shop, index)
        old = self.rows[index]
        deleted = self.deleted
        if key_of(old.name) != key_of(shop.name) and self._is_shipped(old.name):
            deleted = _with_name(deleted, old.name)
        rows = (*self.rows[:index], shop, *self.rows[index + 1 :])
        return replace(self, rows=rows, deleted=deleted)

    def removed(self, index: int) -> ShopBook:
        """This list without the row at `index`, remembered if shipped. FR-S25."""
        old = self.rows[index]
        deleted = self.deleted
        if self._is_shipped(old.name):
            deleted = _with_name(deleted, old.name)
        rows = (*self.rows[:index], *self.rows[index + 1 :])
        return replace(self, rows=rows, deleted=deleted)

    def moved_to(self, index: int, target: int) -> ShopBook:
        """This list with the row at `index` placed at `target`. FR-S27.

        A target outside the list changes nothing rather than raising, as does
        the place it already holds: a drop past either end is a drop at it.
        """
        if not 0 <= target < len(self.rows) or target == index:
            return self
        rows = list(self.rows)
        rows.insert(target, rows.pop(index))
        return replace(self, rows=tuple(rows))

    def moved(self, index: int, offset: int) -> ShopBook:
        """This list with the row at `index` moved by `offset` places. FR-S28."""
        return self.moved_to(index, index + offset)

    def announced(self) -> ShopBook:
        """This list with nothing left to announce. FR-S35."""
        return replace(self, retired=())

    def put_back(self) -> ShopBook:
        """The shipped shops as shipped, then the listener's own. FR-S37.

        A row whose name no release carries is the listener's own and keeps its
        place among the others; every shipped name is replaced by the shipped
        shop, which also undoes an edit and a delete alike.
        """
        own = tuple(row for row in self.rows if not self._is_shipped(row.name))
        return replace(self, rows=(*self.shipped, *own), deleted=())


def merged(
    rows: tuple[Row, ...],
    recorded: tuple[Shop, ...] | None,
    deleted: tuple[str, ...] | None,
    retired: tuple[str, ...],
    current: tuple[Shop, ...],
) -> ShopBook:
    """The list a file holds, settled against the shops this release ships.

    `recorded` is the release list the file was last settled against; None for
    a file too old to carry one, which is read as settled against this release,
    so nothing in it is treated as out of date. `deleted` is None for a file
    from before deleting was recorded: such a file is given an empty record and
    no shipped shop it lacks is added, since it may have been removed by hand
    with nothing written down. FR-S30 to FR-S36.
    """
    was = {key_of(shop.name): shop for shop in (recorded or current)}
    now = {key_of(shop.name): shop for shop in current}
    settled: list[Row] = []
    retiring = list(retired)
    for row in rows:
        key = key_of(row.name)
        if isinstance(row, BrokenRow) or key not in was or row != was[key]:
            settled.append(row)
            continue
        if key in now:
            settled.append(now[key])
        else:
            retiring.append(row.name)
    if deleted is not None:
        gone = {key_of(name) for name in deleted}
        present = {key_of(row.name) for row in settled}
        settled.extend(
            shop
            for shop in current
            if key_of(shop.name) not in present and key_of(shop.name) not in gone
        )
    return ShopBook(
        rows=tuple(settled),
        shipped=current,
        deleted=deleted or (),
        retired=tuple(retiring),
    )
