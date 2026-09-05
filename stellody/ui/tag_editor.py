"""Stating a selection's tags, without a music file being opened for writing.

The panel a tagger offers, with the one difference that matters: **pressing OK
writes nothing to your music.** Every value stated becomes a row in Stellody's
own store, laid over the raw tags exactly as an accepted correction is, then
taken straight back out by the same Reset. The application cannot write a tag
at all; a structural test fails the build if any module that reads tags so much
as reaches the API that writes them.

**A box left empty is a field left alone.** Across several tracks the panel
starts empty wherever they disagree, so what it shows is what they have in
common; anything typed is a statement about all of them and anything left is
not a statement at all. That is what a tagger's checkboxes are for and it is
the half that makes editing many tracks at once safe rather than destructive.

The title is a track's own name, so it is offered only over ONE track. Over
many it is disabled and says why, rather than being offered and quietly
flattening twelve different names into one.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stellody.application.editing import (
    ALBUM_FIELDS,
    TRACK_FIELDS,
    TagEditing,
    album_shown_for,
    shown_for,
)
from stellody.domain.album import Album
from stellody.domain.overrides import AlbumField, OverrideField
from stellody.domain.track import Track
from stellody.ui.dialogs import NeutralDialog

DIALOG_WIDTH_PX = 520

# What each field is called where somebody reads it, which is not what the
# store calls it. One home for the words, so the panel and anything that
# reports what it did cannot come to disagree.
FIELD_WORDS = {
    OverrideField.TITLE: "Title",
    OverrideField.ARTIST: "Artist(s)",
    OverrideField.DISC_NUMBER: "Disc #",
    OverrideField.TRACK_NUMBER: "Track #",
}

# Offered over one track only. A title names THAT track, so stating one about
# a dozen is never what somebody meant.
SINGLE_TRACK_ONLY = frozenset({OverrideField.TITLE})

# What an album is called, by the album rather than by its tracks. These
# are the fields an album is IDENTIFIED by, so stating one changes which
# album this is; the panel says so where somebody is about to do it.
ALBUM_WORDS = {
    AlbumField.ALBUM_ARTIST: "Album artist(s)",
    AlbumField.TITLE: "Album",
    AlbumField.DATE: "Date",
    AlbumField.GENRE: "Genre(s)",
}

FOLDING_NOTE = (
    "<p>Giving this album the artist and title another already carries joins "
    "the two into one, sharing its artwork and its rating. That is how a "
    "release split across two folders becomes one album.</p>"
)

PROMISE = (
    "<p><b>Your music files are not touched.</b> What you state here is kept "
    "in Stellody's own store and laid over the tags it reads. Resetting takes "
    "it straight back out.</p>"
    "<p>A box left empty is a field left alone. Where the tracks you have "
    "chosen disagree, the box starts empty.</p>"
)

MANY_TRACKS_NOTE = "one track at a time"
REFUSED_NOTE = "A disc or track number has to be a counting number."


class TagEditor(NeutralDialog):
    """States values about a selection of tracks. Writes no music file."""

    def __init__(
        self,
        editing: TagEditing,
        album: str,
        tracks: tuple[Track, ...],
        parent: QWidget | None = None,
        holding: Album | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit tags")
        self.setMinimumWidth(DIALOG_WIDTH_PX)
        self._editing = editing
        self._album = album
        self._tracks = tracks
        self._holding = holding
        self._boxes: dict[OverrideField, QLineEdit] = {}
        self._album_boxes: dict[AlbumField, QLineEdit] = {}
        self.written = 0

        outer = QVBoxLayout(self)
        heading = QLabel(PROMISE, self)
        heading.setWordWrap(True)
        heading.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(heading)
        outer.addLayout(self._form())
        if self._holding is not None:
            outer.addWidget(self._album_heading())
            outer.addLayout(self._album_form())
        self._trouble = QLabel("", self)
        self._trouble.setWordWrap(True)
        self._trouble.setVisible(False)
        outer.addWidget(self._trouble)
        outer.addLayout(self._buttons())

    def _form(self) -> QFormLayout:
        """One box a field, holding what the selection has in common."""
        form = QFormLayout()
        alone = len(self._tracks) == 1
        for field in TRACK_FIELDS:
            box = QLineEdit(shown_for(self._tracks, field), self)
            if field in SINGLE_TRACK_ONLY and not alone:
                box.setEnabled(False)
                box.setPlaceholderText(MANY_TRACKS_NOTE)
            self._boxes[field] = box
            form.addRow(f"{FIELD_WORDS[field]}:", box)
        return form

    def _album_heading(self) -> QLabel:
        """Say what stating an album value does before somebody does it."""
        label = QLabel(FOLDING_NOTE, self)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        return label

    def _album_form(self) -> QFormLayout:
        """One box a field, holding what the album currently says."""
        form = QFormLayout()
        for field in ALBUM_FIELDS:
            box = QLineEdit(album_shown_for(self._holding, field), self)
            self._album_boxes[field] = box
            form.addRow(f"{ALBUM_WORDS[field]}:", box)
        return form

    def stated_album(self) -> dict[AlbumField, str]:
        """What has been typed about the album itself, by field."""
        return {field: box.text() for field, box in self._album_boxes.items()}

    def _buttons(self) -> QHBoxLayout:
        """Keep, then a way out that states nothing."""
        row = QHBoxLayout()
        row.addStretch()
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        self.keep_button = QPushButton("Keep", self)
        self.keep_button.setDefault(True)
        self.keep_button.clicked.connect(self.keep)
        row.addWidget(self.keep_button)
        return row

    def stated(self) -> dict[OverrideField, str]:
        """What has been typed, by field, with the disabled boxes left out."""
        return {
            field: box.text() for field, box in self._boxes.items() if box.isEnabled()
        }

    def keep(self) -> None:
        """Record what was stated, unless something stated cannot be held.

        A refusal keeps the panel open with the words still in it. Closing on
        one would throw away everything else somebody had typed to punish a
        single box; they would then have to work out for themselves which.
        """
        stated = self.stated()
        refused = self._editing.refused(stated)
        if refused:
            names = ", ".join(FIELD_WORDS[field] for field in refused)
            self._trouble.setText(f"{names}: {REFUSED_NOTE}")
            self._trouble.setVisible(True)
            return
        self.written = self._editing.state(self._album, self._tracks, stated)
        if self._holding is not None:
            self.written += self._editing.state_album(
                self._holding, self.stated_album()
            )
        self.accept()
