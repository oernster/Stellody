"""What a new install or a reinstall forgets; an update forgets nothing.

The setup program leaves a note (`switch_reset.py`) after a new install or a
reinstall, never after an update, a downgrade or a repair. Stellody's own
directory outlives an uninstall unless the user asks for it to go, so without
this a reinstall came back wearing choices somebody made months ago.

Forgotten: shuffle and repeat, turned off; the remembered close choice, which
asks again; the visualiser's style, back to the default. Oliver ruled on
2026-10-12 that an update keeps the style while a fresh install starts on the
dot matrix, the default `visualisations.py` names.
"""

from __future__ import annotations

from stellody.application.ports import SettingsStore
from stellody.ui.close_prompt import CloseAction
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_CLOSE,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VISUALISATION,
)
from stellody.ui.visualisations import DEFAULT_VISUALISATION


def forget_for_a_fresh_install(store: SettingsStore) -> None:
    """Put back what a new install starts with, over what an old one left."""
    for key in (SETTING_SHUFFLE, SETTING_REPEAT):
        store.set_setting(key, FALSE)
    # An answer given once that outlives the install it was given to: a
    # reinstall still acting on it would offer no way to notice.
    store.set_setting(SETTING_CLOSE, CloseAction.ASK.value)
    store.set_setting(SETTING_VISUALISATION, DEFAULT_VISUALISATION.value)
