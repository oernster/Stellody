"""Whether the numbers a format states describe what it actually stores.

A container states a bit depth because its header has a field for one, not
because the codec inside it kept that many bits. The two are different claims
and only one of them is worth reporting: `is_bit_perfect` tests a stated depth,
so a lossy file whose container states sixteen would be badged as delivered
untouched.

The rule is stated here, in the domain, rather than beside the tag library that
reads the number. Two reasons. It is a fact about formats rather than about
mutagen, so it holds whatever reads the file; and it is one place to name a
family, so widening the formats a library takes cannot quietly widen what is
claimed for them.

**A stated depth is believed unless the family is named below.** That direction
is deliberate. Naming the families whose depth may be trusted would mean a
lossless format nobody thought of losing a bit-perfect stream it had earned,
in silence, which is the harder failure to notice of the two.
"""

from __future__ import annotations

# What the probe calls each family whose stated depth is not a stored one.
# A family belongs here on what its codec does rather than on what a tag
# library currently reports: measured on 2026-09-09, mutagen states sixteen
# bits per sample for a lossy MP4 while stating none at all for WMA or for
# AAC. All three are approximations of the signal that went in, so none has a
# stored depth to report; the two that state nothing today are named anyway,
# so a tag library that starts reporting their header field changes nothing.
FAMILY_MP4_LOSSY = "mp4-lossy"
FAMILY_WMA = "wma"
FAMILY_AAC = "aac"

LOSSY_FAMILIES = frozenset({FAMILY_MP4_LOSSY, FAMILY_WMA, FAMILY_AAC})

# What everything else is called, including every lossless family. It carries
# no rule of its own; it is the name for "nothing here refuses this depth".
FAMILY_OTHER = "other"


def stores_its_samples(family: str) -> bool:
    """Whether a file of `family` keeps the samples it was given."""
    return family not in LOSSY_FAMILIES


def stored_depth(family: str, stated: int) -> int:
    """The depth a file of `family` genuinely stores, having stated `stated`.

    Nought for a lossy family whatever it stated, since there is no stored
    depth to report; nought too for a negative figure, which no format states
    and which would otherwise travel downstream as a depth.
    """
    if not stores_its_samples(family):
        return 0
    return max(0, stated)
