"""What ListenBrainz knows: which artists resemble a given one.

The other half of a discovery run, which has to be a second service because
neither catalogue answers both questions. MusicBrainz has no notion of
similarity at all; this one takes MusicBrainz identifiers and answers with
more of them, so the two compose with nothing to translate between.

**The algorithm is named rather than defaulted.** The endpoint offers several,
each a different reading of how far back to look and how much agreement to
require; it answers 400 to a name it does not carry. The one used here was
read off the endpoint itself on 2026-09-06 and confirmed against a real artist:
a long window with a middling threshold, which is the reading that suits a
library rather than a week's listening.

**Answers are already ranked, so the first ten are the ten wanted.** No opinion
of our own is applied to the order; the service knows more about it than this
does.

Nothing here opens a connection; `fetching.py` holds the socket.
"""

from __future__ import annotations

from stellody.domain.discovery import SimilarArtist
from stellody.infrastructure.fetching import Fetcher

SIMILAR_URL = "https://labs.api.listenbrainz.org/similar-artists/json"
# Read verbatim off the endpoint on 2026-09-06 and confirmed with a real
# artist: a wrong value answers 400 rather than falling back to a default, so
# this is not somewhere to be inventive.
ALGORITHM = (
    "session_based_days_7500_session_300_contribution_5"
    "_threshold_10_limit_100_filter_True_skip_30"
)


class ListenBrainz:
    """The similarity catalogue, asked the one question a run has for it."""

    def __init__(self, fetcher: Fetcher | None = None) -> None:
        self._fetch = fetcher if fetcher is not None else Fetcher()

    def similar_to(self, identifier: str, wanted: int) -> tuple[SimilarArtist, ...]:
        """The artists most like this one, at most `wanted` of them.

        An entry with no name is passed over rather than carried: a candidate
        nobody can be told about is not a candidate.
        """
        answer = self._fetch.json(
            SIMILAR_URL, {"artist_mbids": identifier, "algorithm": ALGORITHM}
        )
        if not isinstance(answer, list):
            return ()
        found = []
        for entry in answer:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            found.append(
                SimilarArtist(name=name, identifier=str(entry.get("artist_mbid") or ""))
            )
            if len(found) == wanted:
                break
        return tuple(found)
