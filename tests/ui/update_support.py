"""What the update check suites share: the running version and its settings.

Shared by the check's own tests and by the one holding what happens when the
window goes before the answer comes back.
"""

from __future__ import annotations

from stellody.ui.settings_keys import SETTING_SKIPPED_UPDATE

CURRENT = "0.5.0"


class Settings:
    """The two settings calls the controller is given, recorded."""

    def __init__(self, stored: str = "") -> None:
        self.values = {SETTING_SKIPPED_UPDATE: stored} if stored else {}

    def get(self, key: str, default: str = "") -> str:
        """What is stored under a key, else the default."""
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Write a value down, as the real store does."""
        self.values[key] = value
