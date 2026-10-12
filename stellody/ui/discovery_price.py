"""What ticking the Include boxes would cost, in the words beneath them. FR-D52.

Split from `discovery_dialog.py` once that file reached the line cap's danger
band: the sentence and its counting are a concern of their own, while the
dialog only says where the sentence goes.
"""

from __future__ import annotations

from stellody.application.compilation_cost import Cost
from stellody.domain.estimating import SECONDS_PER_MINUTE, rounded_minutes

# What ticking the boxes would cost, said beneath them. FR-D52. The minutes are
# arithmetic at the pace the catalogue permits, so the sentence names what makes
# a real run longer rather than passing a floor off as a forecast.
NOTHING_NEW = (
    "Every artist and series on compilations in these genres has been looked up "
    "already, so including them asks nothing new."
)
# The artists and the series still to look up, named apart since a series is
# not an artist. FR-D52, FR-D69.
ONE_ARTIST = "one artist"
SOME_ARTISTS = "{count} artists"
ONE_SERIES = "one series"
SOME_SERIES = "{count} series"
BOTH = "{artists} and {series}"
NOT_LOOKED_UP = "{what} on compilations in these genres {verb} not been looked up yet"
HAS = "has"
HAVE = "have"
UNDER_A_MINUTE = "under a minute more"
ABOUT_A_MINUTE = "about a minute more"
ABOUT_MINUTES = "about {minutes} minutes more"
COST = "{names}: {time} at the pace MusicBrainz allows, longer when it is busy."
# A single name or a single minute reads as "one" rather than "1 artists".
ONE = 1


def _counted(count: int, one: str, some: str) -> str:
    """A count in words: "one" for a single one rather than "1"."""
    return one if count == ONE else some.format(count=count)


def _still_to_look_up(cost: Cost) -> str:
    """Who and what is still to be looked up, as the start of a sentence."""
    artists = _counted(cost.names, ONE_ARTIST, SOME_ARTISTS)
    series = _counted(cost.series, ONE_SERIES, SOME_SERIES)
    if cost.names and cost.series:
        what = BOTH.format(artists=artists, series=series)
    else:
        what = artists if cost.names else series
    single = cost.names + cost.series == ONE
    said = NOT_LOOKED_UP.format(what=what, verb=HAS if single else HAVE)
    return said[0].upper() + said[1:]


def cost_sentence(cost: Cost) -> str:
    """What including compilations would add, in the words beneath the box."""
    if not cost.names and not cost.series:
        return NOTHING_NEW
    names = _still_to_look_up(cost)
    minutes = rounded_minutes(cost.seconds)
    if cost.seconds < SECONDS_PER_MINUTE:
        said = UNDER_A_MINUTE
    elif minutes == ONE:
        said = ABOUT_A_MINUTE
    else:
        said = ABOUT_MINUTES.format(minutes=minutes)
    return COST.format(names=names, time=said)
