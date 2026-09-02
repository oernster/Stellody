"""Reading a disc marker off an album folder's name.

A folder name is the only place some rips say which disc they are, so this is
where that is read. Kept apart from the grouping itself because it answers a
different question: this one is about text, while grouping is about which
album a file belongs to.
"""

from __future__ import annotations

import re

# "The Book of Souls CD1", "White Album (Disc 2)", "Box Set [Disk 3]".
# The literal CD or Disc word is required, so an album whose title merely ends
# in a number, such as Northern Exposure 2, is never split.
_DISC_SUFFIX = re.compile(
    r"^(?P<base>.*?)[\s._-]*[(\[]?\s*(?:CD|Disc|Disk)\s*[.\-_]?\s*"
    r"(?P<number>\d{1,2})\s*[)\]]?$",
    re.IGNORECASE,
)

# "Ether Song (Bonus Disc)", "Album [Extra CD]", "Album - Bonus Disc 2". The
# number is optional here BECAUSE the bonus word is required: that word is what
# says the folder holds another disc of the album beside it, so nothing is
# inferred from a name merely ending in the word Disc. Tried before the pattern
# above, since a numbered bonus folder matches both and only this one reads it
# without leaving half the bracket in the album name.
_BONUS_SUFFIX = re.compile(
    r"^(?P<base>.*?)[\s._-]*[(\[]?\s*(?:bonus|extra)\s*"
    r"(?:CD|Disc|Disk)\s*[.\-_]?\s*(?P<number>\d{1,2})?\s*[)\]]?$",
    re.IGNORECASE,
)


def folder_base_and_disc(folder_name: str) -> tuple[str, int | None]:
    """Split a trailing disc marker off a folder name.

    Returns the name without the marker and the disc number it carried; the
    name unchanged and None when it carried none. A bonus disc is a marker even
    where it names no number, so it folds into the album beside it and leaves
    which disc it is to be worked out.
    """
    for pattern in (_BONUS_SUFFIX, _DISC_SUFFIX):
        match = pattern.match(folder_name)
        if match is None:
            continue
        base = match.group("base").strip()
        if not base:
            continue
        number = match.group("number")
        return base, int(number) if number else None
    return folder_name, None


def is_unnumbered_bonus(folder_name: str) -> bool:
    """Whether this folder calls itself a bonus disc without saying which."""
    match = _BONUS_SUFFIX.match(folder_name)
    return (
        match is not None
        and bool(match.group("base").strip())
        and match.group("number") is None
    )
