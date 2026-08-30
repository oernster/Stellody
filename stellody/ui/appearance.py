"""Which of the two appearances the window is wearing, then remembering it.

Kept apart from the window itself because it is one concern with one home:
every surface that paints differently in light and dark is told from here, in
one place, so a new surface that forgets to follow is a visible omission
rather than a line lost among everything else a window does.
"""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from stellody.ui.settings_keys import SETTING_THEME
from stellody.ui.theme import Mode, stylesheet


class Appearance:
    """The window's half of wearing an appearance."""

    @property
    def theme_mode(self) -> Mode:
        """The appearance currently stored."""
        stored = self._settings.get_setting(SETTING_THEME, Mode.DARK.value)
        return Mode(stored) if stored in tuple(Mode) else Mode.DARK

    @Slot()
    def toggle_theme(self) -> None:
        """Swap between the two appearances, from the tray."""
        self._apply_theme(Mode.LIGHT if self.theme_mode is Mode.DARK else Mode.DARK)

    @Slot()
    def use_light(self) -> None:
        """Switch to the light appearance."""
        self._apply_theme(Mode.LIGHT)

    @Slot()
    def use_dark(self) -> None:
        """Switch to the dark appearance."""
        self._apply_theme(Mode.DARK)

    def _apply_theme(self, mode: Mode) -> None:
        """Paint the application in one appearance and remember the choice."""
        self._settings.set_setting(SETTING_THEME, mode.value)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(mode))
        self._light_action.setChecked(mode is Mode.LIGHT)
        self._dark_action.setChecked(mode is Mode.DARK)
        self._tray.set_mode(mode)
        self._position_bar.show_appearance(mode)
        self.show_cover_appearance(mode)
