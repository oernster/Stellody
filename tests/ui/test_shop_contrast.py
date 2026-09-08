"""Whether every colour the shops dialog writes in can be read.

NFR-S-USE-001, which is NFR-USE-002 applied to the new screen so that it cannot
be the one that quietly falls short. The same instrument as the other two
contrast suites, since one formula written three times is three formulas the
day any of them is touched.
"""

from __future__ import annotations

import inspect
import pathlib
import re

import pytest
from contrast_support import READABLE, contrast

from stellody.ui.palette import Mode, Palette, palette_for
from stellody.ui.shops_dialog import ShopsDialog

# What the dialog writes in: the count and the shop names in the ordinary text
# colour, what it just did in the muted one; what would not open in the
# warning one. Named by attribute so a colour added without being measured is
# a name this list does not carry rather than a ratio nobody took.
WRITING = ("text", "text_muted", "warning")
BEHIND = ("window", "surface")


def _surfaces(colour: Palette) -> tuple[str, ...]:
    """The backgrounds a line of this dialog can land on."""
    return tuple(getattr(colour, name) for name in BEHIND)


@pytest.mark.parametrize("mode", tuple(Mode))
@pytest.mark.parametrize("role", WRITING)
def test_every_colour_the_dialog_writes_in_can_be_read(mode: Mode, role: str) -> None:
    """Every colour, both surfaces, both appearances. NFR-S-USE-001."""
    colour = palette_for(mode)
    for behind in _surfaces(colour):
        assert contrast(getattr(colour, role), behind) >= READABLE


def test_the_dialog_writes_in_nothing_that_was_not_measured() -> None:
    """The guard on the list above, so a fourth colour cannot slip in.

    The module's own text is read rather than its behaviour, because a colour
    is chosen where it is named: a role used by a line nobody wrote a test for
    is still a role the dialog paints with.
    """
    source = pathlib.Path(inspect.getfile(ShopsDialog))
    used = set(re.findall(r"_colour\.([a-z_]+)", source.read_text(encoding="utf-8")))
    assert used <= set(WRITING)
