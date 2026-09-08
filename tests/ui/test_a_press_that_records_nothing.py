"""A press that records nothing says so rather than redrawing in silence.

Reported as "Accept everything doesn't do anything". It was writing no pins at
all; a press that writes none reloads nothing and redraws identically, which is
indistinguishable from a dead control.

Its own file rather than another class in the screen's suite, which had reached
the length a module here is allowed.
"""

from __future__ import annotations

import pytest
from repair_support import (  # noqa: F401  the fixtures register by import
    MemoryStore,
    never_really_report,
    opened,
)

from stellody.application.repairs import Repairs


@pytest.fixture
def repairs() -> Repairs:
    """A service over a store nobody has accepted anything in yet."""
    return Repairs(MemoryStore())


class TestAPressThatRecordsNothing:
    """A control that achieves nothing says so rather than redrawing in silence.

    Reported as "Accept everything doesn't do anything". It was writing no pins
    at all; a press that writes none reloads nothing and redraws
    identically, which is indistinguishable from a dead button.
    """

    def test_it_says_so_rather_than_looking_dead(
        self, application, repairs, never_really_report  # noqa: F811
    ) -> None:
        dialog = opened(repairs, None)
        dialog._after(0)
        assert never_really_report, "a press that recorded nothing said nothing"
        dialog.deleteLater()

    def test_a_press_that_records_something_says_nothing_extra(
        self, application, repairs, never_really_report  # noqa: F811
    ) -> None:
        """The report belongs to the failure, so success stays quiet."""
        dialog = opened(repairs, None)
        dialog._after(1)
        assert never_really_report == []
        dialog.deleteLater()
