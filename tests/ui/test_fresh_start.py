"""What a new install or a reinstall forgets; an update forgets nothing.

Oliver ruled on 2026-10-12: an update keeps the visualiser's style while a
fresh install starts on the dot matrix. An update leaves the settings alone
(the setup program leaves no note), so keeping is the window reading what is
stored, held in `test_visualisations.py`; what is held here is the forgetting.
"""

from __future__ import annotations

from recording_player import RecordingPlayer
from tray_support import RememberingStore, build

from stellody.ui.close_prompt import CloseAction
from stellody.ui.fresh_start import forget_for_a_fresh_install
from stellody.ui.settings_keys import (
    FALSE,
    SETTING_CLOSE,
    SETTING_REPEAT,
    SETTING_SHUFFLE,
    SETTING_VISUALISATION,
    TRUE,
)
from stellody.ui.visualisations import Visualisation


def test_a_reinstall_forgets_the_choices_an_old_install_left() -> None:
    store = RememberingStore(
        {
            SETTING_SHUFFLE: TRUE,
            SETTING_REPEAT: "album",
            SETTING_CLOSE: CloseAction.TRAY.value,
            SETTING_VISUALISATION: Visualisation.RAINBOW.value,
        }
    )
    forget_for_a_fresh_install(store)
    assert store.get_setting(SETTING_SHUFFLE) == FALSE
    assert store.get_setting(SETTING_REPEAT) == FALSE
    assert store.get_setting(SETTING_CLOSE) == CloseAction.ASK.value
    assert store.get_setting(SETTING_VISUALISATION) == Visualisation.DOT_MATRIX.value


def test_a_brand_new_install_draws_the_dot_matrix(application) -> None:
    made = build(RememberingStore(), RecordingPlayer())
    assert made._visualiser.style is Visualisation.DOT_MATRIX
    made.close()
