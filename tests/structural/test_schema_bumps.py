"""A change to the database's shape cannot ship under the same number. FR-B18.

The database's shape is text: the statements that create it. So each schema
number is recorded here beside a fingerprint of that text; a change to the
text without a new number fails. Adding a number means adding a step to
`database_schema.py`, which is the only way NEWEST can move.

What this cannot see is a JSON file's shape, which is built in code rather than
written down anywhere as one text; BACKUP.md records that half as not done.
"""

from __future__ import annotations

import hashlib

from stellody.domain.backups import FIRST_SCHEMA
from stellody.infrastructure import album_edit_rows, database_schema, override_rows
from stellody.infrastructure.store import SCHEMA

# One fingerprint per schema number, never edited once written: a new shape
# gets a new number and a new line.
FINGERPRINTS = {
    1: "bb8969f8f44dfec39a4ab4febef0a399d5666cdaf76ef99885ae57fef9cb6d79",
}


def fingerprint() -> str:
    """The database's creating statements, whitespace aside, hashed."""
    text = SCHEMA + override_rows.SCHEMA + album_edit_rows.SCHEMA
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def test_a_changed_shape_needs_a_new_number() -> None:
    recorded = FINGERPRINTS.get(database_schema.NEWEST)
    assert recorded == fingerprint(), (
        "the database's shape is not the one recorded for schema "
        f"{database_schema.NEWEST}. A change to it needs a step in "
        "stellody/infrastructure/database_schema.py and a new line here "
        f"for the new number: {fingerprint()}"
    )


def test_every_number_up_to_the_newest_is_recorded() -> None:
    assert sorted(FINGERPRINTS) == list(range(FIRST_SCHEMA, database_schema.NEWEST + 1))
