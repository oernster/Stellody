"""Every dialog the application can open, built for a sweep over the lot.

A sweep is only worth the name if the thing it walks is the whole set. The
first-stop rules were held against a list somebody maintained by hand, which
is the shape of guard that passes on the day it matters: a new dialog is
outside the rule until somebody remembers to add it; whoever forgot the rule
forgets the list entry with it. That is exactly how the guide arrived
opening with its whole page ringed while the suite stayed green.

So the set is DISCOVERED rather than declared. `dialog_classes` reads the
package's own source and answers every concrete subclass of FirstStopDialog;
`BUILDERS` says how to construct each one. A dialog added without a builder
fails the coverage assertion in `test_dialog_first_stop.py`, so the list cannot
quietly fall behind the package.

The fakes are the ones the individual dialog suites already use, imported
rather than written again, so a change to what a service looks like reaches
here too instead of leaving a second copy behind to rot.
"""

from __future__ import annotations

import ast
import pathlib

from cover_support import FakeArtwork, FakeSearch
from repair_support import MemoryStore, load
from tray_support import album

from stellody.application.choosing_covers import ChooseCover
from stellody.application.editing import TagEditing
from stellody.application.repairs import Repairs
from stellody.application.scan import ScanReport
from stellody.application.shop_editing import ShopEditing
from stellody.application.shopping import Shopping
from stellody.application.values import (
    Ambiguity,
    RunOutcome,
    RunReport,
    SourceFailure,
)
from stellody.domain.changes import LibraryChange
from stellody.domain.discovery import Gaps, ReleaseGroup, SimilarArtist
from stellody.domain.equalising import Equalisation
from stellody.domain.health import IssueKind, LibraryIssue
from stellody.domain.identity import AlbumIdentity
from stellody.domain.narrowing import Narrowing
from stellody.domain.shop_list import ShopBook
from stellody.domain.shopping import Shop, WantedAlbum
from stellody.infrastructure.shop_file import DEFAULT_SHOPS
from stellody.shared import resources
from stellody.ui.close_prompt import ClosePrompt
from stellody.ui.cover_chooser import CoverChooser
from stellody.ui.dialogs import AboutDialog, LicenceDialog
from stellody.ui.discovery_dialog import DiscoveryDialog
from stellody.ui.equaliser import EqualiserDialog
from stellody.ui.filter_dialog import FilterDialog
from stellody.ui.guide import GuideDialog
from stellody.ui.health import HealthDialog
from stellody.ui.layout_advice import LayoutAdviceDialog
from stellody.ui.repairing import RepairDialog
from stellody.ui.results_dialog import ResultsDialog
from stellody.ui.scan_summary import ScanSummaryDialog
from stellody.ui.shop_form import ShopForm
from stellody.ui.shops_dialog import ShopsDialog
from stellody.ui.shortfall import ShortfallDialog
from stellody.ui.tag_editor import TagEditor
from stellody.ui.theme import Mode

BASE = "FirstStopDialog"
UI_PACKAGE = pathlib.Path(__file__).resolve().parents[2] / "stellody" / "ui"
ISSUE_COUNT = 3
ALBUM_KEY = "a1b2c3"


def dialog_classes() -> frozenset[str]:
    """Every concrete FirstStopDialog subclass the package defines.

    Read out of the source rather than by importing and walking subclasses,
    because a subclass only exists once its module has been imported and the
    thing being guarded against is precisely a module nobody thought to name.
    The base itself is not a dialog somebody opens, so it is left out.
    """
    found: set[str] = set()
    for path in sorted(UI_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            names = {base.id for base in node.bases if isinstance(base, ast.Name)}
            if BASE in names and node.name != BASE:
                found.add(node.name)
    return frozenset(found)


def _issues() -> tuple[LibraryIssue, ...]:
    """A little reported damage, which is all a health page needs to exist."""
    return tuple(
        LibraryIssue(
            kind=IssueKind.DUPLICATE_TRACK_NUMBER,
            album=f"Album {number}",
            detail="two tracks claim track 3",
            paths=(f"H:/music/{number}.flac",),
        )
        for number in range(ISSUE_COUNT)
    )


def _a_scan() -> tuple[LibraryChange, ScanReport]:
    """A finished scan with something in it to report."""
    change = LibraryChange(
        new_albums=(AlbumIdentity(album_artist="Sasha", title="Involver"),),
        new_tracks=1,
        gone_tracks=0,
        total_albums=1,
        total_tracks=1,
        previous_albums=0,
    )
    return change, ScanReport(issues=_issues())


def _found() -> tuple[Gaps, ...]:
    """A run's answer with both kinds of artist in it, which is the full shape."""
    return (
        Gaps(
            artist="Kate Bush",
            albums=(ReleaseGroup(title="Aerial"),),
            artists=(SimilarArtist(name="Peter Gabriel", identifier="id-pg"),),
        ),
    )


def _shopping() -> Shopping:
    """The use case over stand-ins, since no browser opens during a sweep.

    With the editor, so the sweep reaches every control the shops dialog can
    show rather than the smaller dialog it draws without one.
    """
    return Shopping(
        shops=_ShopList(), opener=_Nowhere(), clipboard=_Nowhere(), editing=_editing()
    )


class _MemoryBook:
    """A shop list held in memory, so a sweep writes no file."""

    def __init__(self) -> None:
        self._book = ShopBook(rows=DEFAULT_SHOPS[:2], shipped=DEFAULT_SHOPS[:2])

    def book(self) -> ShopBook:
        """What it holds."""
        return self._book

    def save(self, book: ShopBook) -> None:
        """Hold this instead."""
        self._book = book


def _editing() -> ShopEditing:
    """The editor over a list in memory."""
    return ShopEditing(store=_MemoryBook(), opener=_Nowhere())


def _ticked() -> tuple[WantedAlbum, ...]:
    """One ticked album, which is all the dialog needs to have something to do."""
    return (WantedAlbum(artist="Kate Bush", title="Aerial"),)


class _ShopList:
    """The shipped shops, without touching the file they normally come from."""

    def shops(self) -> tuple[Shop, ...]:
        """Two of them, which is enough for a dialog to have buttons."""
        return DEFAULT_SHOPS[:2]


class _Nowhere:
    """An opener and a clipboard that do nothing at all."""

    def open(self, address: str) -> bool:
        """Say it worked without doing anything."""
        return True

    def put(self, text: str) -> None:
        """Take it and forget it."""


def _repairs() -> Repairs:
    """The real service over a store nobody has accepted anything in yet."""
    return Repairs(MemoryStore())


# How to build each dialog, keyed by the class name so the coverage assertion
# can compare against what the package actually defines. Every builder takes
# the parent and nothing else, so the sweep does not have to know them apart.
def _a_shortfall() -> RunReport:
    """A run that could not answer for somebody, of each kind there is."""
    return RunReport(
        outcome=RunOutcome.COMPLETED,
        failed=(SourceFailure(artist="Nobody", reason="a server error"),),
        unresolved=("Unknown",),
        ambiguous=(Ambiguity(artist="Several", identifiers=("a", "b")),),
    )


BUILDERS = {
    "AboutDialog": lambda parent: AboutDialog(parent),
    "ClosePrompt": lambda parent: ClosePrompt(parent),
    "CoverChooser": lambda parent: CoverChooser(
        ChooseCover(FakeSearch(), FakeArtwork()), album(), Mode.DARK, parent
    ),
    "EqualiserDialog": lambda parent: EqualiserDialog(
        parent, Equalisation(), lambda _curve: None
    ),
    "DiscoveryDialog": lambda parent: DiscoveryDialog(parent=parent),
    "FilterDialog": lambda parent: FilterDialog(Narrowing(), parent),
    "GuideDialog": lambda parent: GuideDialog(parent),
    "HealthDialog": lambda parent: HealthDialog(_issues(), parent),
    "LayoutAdviceDialog": lambda parent: LayoutAdviceDialog(parent),
    "LicenceDialog": lambda parent: LicenceDialog(
        "Model", resources.model_licence_path(), parent
    ),
    "RepairDialog": lambda parent: _repair_dialog(parent),
    "ResultsDialog": lambda parent: ResultsDialog(_found(), parent=parent),
    "ShopsDialog": lambda parent: ShopsDialog(_shopping(), _ticked(), parent=parent),
    "ShopForm": lambda parent: ShopForm(_editing(), _ticked()[0], parent=parent),
    "ScanSummaryDialog": lambda parent: ScanSummaryDialog(*_a_scan(), parent),
    "ShortfallDialog": lambda parent: ShortfallDialog(_a_shortfall(), parent),
    "TagEditor": lambda parent: TagEditor(
        TagEditing(MemoryStore()), ALBUM_KEY, album().ordered_tracks(), parent
    ),
}


def _repair_dialog(parent) -> RepairDialog:
    """The repair dialog over a library with one damaged album."""
    service = _repairs()
    return RepairDialog(service, load(service), parent)


def settled(dialog, application) -> None:
    """Let a dialog that started work of its own finish it.

    Only the cover chooser does; it searches an archive on a thread of its
    own. Walking off while that runs destroys a running thread, which is the
    abort the dialog's own suite exists to prevent, arriving from a test
    rather than from the application.
    """
    if not isinstance(dialog, CoverChooser):
        return
    for _attempt in range(SETTLE_ATTEMPTS):
        application.processEvents()
        if not dialog.searching:
            application.processEvents()
            return


SETTLE_ATTEMPTS = 2000
