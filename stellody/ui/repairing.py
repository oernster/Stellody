"""Accepting the corrections the health report describes, then taking them back.

**Accept everything is the default path.** It is the first control on the
screen and the one Return presses, rather than a shortcut hidden behind a
per-issue flow. 142 findings is not a workflow and a library twice the size
makes it ten times worse, so the per-album and per-finding buttons exist for the
case where a rule guessed wrong about one album rather than as the way through.

**The findings and what has been accepted are two lists, not one.** A finding
that has been accepted leaves the report, so it cannot also be the thing you
point at to take it back. The second list is the accepted set itself, grouped by
album and field as it was accepted, which is the same unit read from the other
side.

**Nothing here is a stop that says nothing.** The scroll area holds real
controls, so it never takes focus itself and the buttons inside it are the ring
stops, which is the rule every pane in the application already follows.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from stellody.application.repairs import AcceptedGroup, Repairs
from stellody.application.scan import LibraryView
from stellody.domain.health import LibraryIssue, sorted_issues
from stellody.ui.dialogs import FirstStopDialog, close_row

DIALOG_WIDTH_PX = 760
DIALOG_HEIGHT_PX = 620
# The indent a finding sits at under the album it belongs to, so the two read
# as a list within a list rather than as one flat run of rows.
FINDING_INDENT_PX = 24

HEADING = (
    "<h3>Accept these corrections</h3>"
    "<p>Stellody worked each of these out for you and is already showing the "
    "corrected library. Accepting one keeps it, so it stops being worked out "
    "and reported every time you start.</p>"
    "<p><b>Your music files are not touched.</b> An accepted correction lives "
    "in Stellody's own store; resetting takes it straight back out and the "
    "original finding returns.</p>"
)
NOTHING_TO_ACCEPT = (
    "<p><i>Nothing is waiting to be accepted. Anything Stellody cannot propose "
    "a value for, such as missing artwork or a file it could not read, is "
    "reported rather than offered here.</i></p>"
)
NOTHING_ACCEPTED = "<p><i>You have not accepted anything yet.</i></p>"

FIELD_WORDS = {
    "track-number": "track numbers",
    "disc-number": "disc numbers",
    "title": "titles",
    "album-artist": "the album artist",
}


def _caption(text: str, parent: QWidget, indent: int = 0) -> QLabel:
    """One line of explanation beside a control, wrapping rather than clipping."""
    label = QLabel(text, parent)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    if indent:
        label.setContentsMargins(indent, 0, 0, 0)
    return label


def _acting_row(
    parent: QWidget,
    text: str,
    action: str,
    on_click: Callable[[], None],
    indent: int = 0,
) -> QWidget:
    """A line of text with the one button that acts on it, on the right."""
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(_caption(text, row, indent), stretch=1)
    button = QPushButton(action, row)
    button.clicked.connect(on_click)
    layout.addWidget(button)
    return row


def _scrolling_column(parent: QWidget) -> tuple[QScrollArea, QVBoxLayout]:
    """A scrollable column that is never itself a stop on the ring.

    The controls inside it are what a reader tabs to, so the area holding them
    has nothing of its own to offer and takes no focus, which is the rule a
    pane in this application already follows.
    """
    area = QScrollArea(parent)
    area.setWidgetResizable(True)
    area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    area.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
    inner = QWidget(area)
    column = QVBoxLayout(inner)
    column.setContentsMargins(0, 0, 0, 0)
    area.setWidget(inner)
    return area, column


def group_summary(group: AcceptedGroup, label: str) -> str:
    """What one accepted group says about itself, in a reader's words."""
    words = FIELD_WORDS.get(str(group.field), str(group.field))
    if group.count == 1:
        return f"<b>{label}</b><br>{words}"
    return f"<b>{label}</b><br>{words}, {group.count} files"


def by_album(
    issues: Iterable[LibraryIssue],
) -> tuple[tuple[str, str, tuple[LibraryIssue, ...]], ...]:
    """The findings bucketed by the album they belong to, most serious first.

    Keyed by the album's handle rather than by its label, since two albums can
    wear one label; the label is carried alongside for showing.
    """
    order: list[str] = []
    held: dict[str, list[LibraryIssue]] = {}
    labels: dict[str, str] = {}
    for issue in sorted_issues(tuple(issues)):
        if issue.album_key not in held:
            held[issue.album_key] = []
            labels[issue.album_key] = issue.album
            order.append(issue.album_key)
        held[issue.album_key].append(issue)
    return tuple((key, labels[key], tuple(held[key])) for key in order)


class RepairDialog(FirstStopDialog):
    """Offers the report's corrections for accepting; undoes them too."""

    def __init__(
        self,
        repairs: Repairs,
        reload_library: Callable[[], LibraryView],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Accept corrections")
        self.resize(DIALOG_WIDTH_PX, DIALOG_HEIGHT_PX)
        self._repairs = repairs
        self._reload = reload_library
        self._view = reload_library()
        self._outer = QVBoxLayout(self)
        self._outer.addWidget(_caption(HEADING, self))
        self._area, self._column = _scrolling_column(self)
        self._outer.addWidget(self._area, stretch=1)
        self._outer.addLayout(close_row(self))
        self._fill()

    def _clear(self) -> None:
        """Empty the column, so it can be filled from the library as it now is."""
        while self._column.count():
            item = self._column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _after(self, changed: int, to_top: bool = False) -> None:
        """Reload the library and redraw, so the screen says what is now true.

        Where the reader is left is decided here rather than by Qt. Rebuilding
        destroys the button that was just pressed, so focus goes wherever the
        toolkit finds it next and the scroll area travels to meet it, which is
        how pressing the control at the very top left somebody at the bottom of
        a long list. A press that replaces the whole screen returns to the top;
        one that answers a single row keeps the reader where they were reading.
        """
        if changed:
            self._view = self._reload()
        keeping = self._area.verticalScrollBar().value()
        self._clear()
        self._fill()
        # Laid out before the bar is set, since a scrollbar with no range yet
        # clamps whatever it is given back to nought.
        self._area.widget().adjustSize()
        self._settle(0 if to_top else keeping)

    def _settle(self, position: int) -> None:
        """Put the reader back, with focus on a control that will not move it.

        Focus is placed before the bar is set: a control taking focus scrolls
        itself into view, so doing it the other way round would undo this.
        """
        first = self._area.widget().findChild(QPushButton)
        if first is not None:
            first.setFocus(Qt.FocusReason.OtherFocusReason)
        self._area.verticalScrollBar().setValue(position)

    def _fill(self) -> None:
        """Build both lists from the library and the accepted set."""
        self._fill_outstanding()
        self._fill_accepted()
        self._column.addStretch()

    def _fill_outstanding(self) -> None:
        """The findings waiting to be accepted, the whole-report button first."""
        outstanding = self._repairs.acceptable(self._view.issues)
        if not outstanding:
            self._column.addWidget(_caption(NOTHING_TO_ACCEPT, self))
            return
        self.accept_all_button = QPushButton(
            f"Accept everything ({len(outstanding)})", self
        )
        self.accept_all_button.setDefault(True)
        self.accept_all_button.clicked.connect(self._accept_everything)
        self._column.addWidget(self.accept_all_button)
        for key, label, findings in by_album(outstanding):
            self._column.addWidget(
                _acting_row(
                    self,
                    f"<b>{label}</b>",
                    f"Accept album ({len(findings)})",
                    self._accepting(self._repairs.in_album(outstanding, key)),
                )
            )
            for finding in findings:
                self._column.addWidget(
                    _acting_row(
                        self,
                        finding.summary,
                        "Accept",
                        self._accepting((finding,)),
                        indent=FINDING_INDENT_PX,
                    )
                )

    def _fill_accepted(self) -> None:
        """What has been accepted, each group with the button that undoes it."""
        groups = self._repairs.accepted()
        self._column.addWidget(_caption("<h3>Already accepted</h3>", self))
        if not groups:
            self._column.addWidget(_caption(NOTHING_ACCEPTED, self))
            return
        self.reset_all_button = QPushButton(
            f"Reset everything ({sum(group.count for group in groups)})", self
        )
        self.reset_all_button.clicked.connect(self._reset_everything)
        self._column.addWidget(self.reset_all_button)
        labels = {
            album.identity.handle: album.identity.label for album in self._view.albums
        }
        for group in groups:
            self._column.addWidget(
                _acting_row(
                    self,
                    group_summary(group, labels.get(group.album, group.album)),
                    "Reset",
                    self._resetting(group),
                )
            )

    def _accepting(self, findings: tuple[LibraryIssue, ...]) -> Callable[[], None]:
        """The handler that accepts one run of findings."""

        def accept() -> None:
            self._after(self._repairs.accept(self._view, findings))

        return accept

    def _resetting(self, group: AcceptedGroup) -> Callable[[], None]:
        """The handler that takes one accepted group back."""

        def reset() -> None:
            self._after(self._repairs.reset((group,)))

        return reset

    def _accept_everything(self) -> None:
        """Accept every finding the report lists, which is the default path."""
        self._after(
            self._repairs.accept(
                self._view, self._repairs.acceptable(self._view.issues)
            ),
            to_top=True,
        )

    def _reset_everything(self) -> None:
        """Take every accepted correction back, once it has been confirmed.

        Asked about because it is the one gesture here that undoes an unbounded
        amount of somebody's work in a single press, so the count is named
        before it happens rather than reported after it.
        """
        held = sum(group.count for group in self._repairs.accepted())
        confirmed = QMessageBox.question(
            self,
            "Reset every correction",
            f"Take back all {held} accepted corrections? "
            "Every finding they answered will be reported again. "
            "Your music files are not affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed is QMessageBox.StandardButton.Yes:
            self._after(self._repairs.reset_everything(), to_top=True)
