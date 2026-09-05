"""The window's half of stating a selection's tags, without touching a file.

Holds the service, opens the panel over whatever was right clicked and reloads
afterwards so the library says what is now true. A window built without the
service offers no entry at all, which is the shape every optional service here
already has and is what lets a test raise the menu without a store behind it.

Over a TRACK the panel states things about that track. Over an ALBUM it states
them about every track the album holds, which is what somebody right clicking a
sleeve and choosing Edit tags means; the title is not offered there, since a
title names one track.
"""

from __future__ import annotations

from stellody.application.editing import TagEditing
from stellody.domain.album import Album
from stellody.domain.track import Track
from stellody.ui.tag_editor import TagEditor


class EditingTags:
    """The window's half of stating tags as Stellody's own state."""

    def start_editing_tags(self, editing: TagEditing | None) -> None:
        """Hold the service, when there is one to hold."""
        self._tag_editing = editing

    @property
    def can_edit_tags(self) -> bool:
        """Whether this window was built with somewhere to record an edit."""
        return self._tag_editing is not None

    def edit_track_tags(self, album: Album, track: Track) -> None:
        """State values about one track, plus the album around it."""
        self._edit(album, (track,))

    def edit_album_tags(self, album: Album) -> None:
        """State values about every track of one album, plus the album itself."""
        self._edit(album, album.ordered_tracks())

    def _edit(self, album: Album, tracks: tuple[Track, ...]) -> None:
        """Open the panel, then reload where anything was actually stated.

        Reloaded rather than redrawn, because an edit changes what the library
        resolves to and every view is built from that. Nothing is reloaded
        where nothing was stated, so a panel opened and closed again costs
        what looking at something costs.
        """
        if self._tag_editing is None or not tracks:
            return
        dialog = TagEditor(
            self._tag_editing, album.identity.handle, tracks, self, holding=album
        )
        dialog.exec()
        if dialog.written:
            self.load_remembered()
