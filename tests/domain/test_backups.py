"""What a backup is and whether it may be restored. BACKUP.md."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from stellody.domain.backups import (
    BACKUP_FORMAT,
    FIRST_SCHEMA,
    Carried,
    Manifest,
    Refusal,
    RefusalKind,
    SchemaRange,
    backup_name,
    judged,
    restorable,
)

MOMENT = datetime(2026, 10, 12, 14, 5, tzinfo=UTC)
PREFIX = "app-backup"
KNOWN = {
    "library.sqlite3": SchemaRange(0, 2),
    "shops.json": SchemaRange(FIRST_SCHEMA, FIRST_SCHEMA),
}


def _manifest(*carried: Carried, format: int = BACKUP_FORMAT) -> Manifest:
    return Manifest(format=format, written_by="1.0.0", written=MOMENT, carried=carried)


def _file(name: str, schema: int) -> Carried:
    return Carried(name=name, schema=schema, checksum="0" * 64)


class TestARangeIsChecked:
    def test_a_range_may_be_a_single_schema(self) -> None:
        assert SchemaRange(1, 1).newest == 1

    def test_oldest_above_newest_is_refused(self) -> None:
        with pytest.raises(ValueError):
            SchemaRange(2, 1)

    def test_a_negative_schema_is_refused(self) -> None:
        with pytest.raises(ValueError):
            SchemaRange(-1, 1)


class TestNaming:
    def test_the_zip_is_named_by_the_minute(self) -> None:
        """FR-B03."""
        assert backup_name(PREFIX, MOMENT, frozenset()) == (
            "app-backup-2026-10-12-1405.zip"
        )

    def test_a_taken_name_gains_a_counter(self) -> None:
        """FR-B04."""
        taken = frozenset({"app-backup-2026-10-12-1405.zip"})
        assert backup_name(PREFIX, MOMENT, taken) == "app-backup-2026-10-12-1405-2.zip"

    def test_the_counter_climbs_past_every_taken_name(self) -> None:
        taken = frozenset(
            {"app-backup-2026-10-12-1405.zip", "app-backup-2026-10-12-1405-2.zip"}
        )
        assert backup_name(PREFIX, MOMENT, taken) == "app-backup-2026-10-12-1405-3.zip"


class TestJudging:
    def test_a_backup_within_every_range_is_accepted(self) -> None:
        manifest = _manifest(_file("library.sqlite3", 2), _file("shops.json", 1))
        assert judged(manifest, KNOWN, BACKUP_FORMAT) is None

    def test_a_newer_format_is_refused(self) -> None:
        """FR-B29."""
        refusal = judged(_manifest(format=BACKUP_FORMAT + 1), KNOWN, BACKUP_FORMAT)
        assert refusal is not None
        assert refusal.kind is RefusalKind.NEWER_FORMAT
        assert (refusal.found, refusal.limit) == (BACKUP_FORMAT + 1, BACKUP_FORMAT)

    def test_a_newer_schema_is_refused(self) -> None:
        """FR-B29: names the file, its schema and the newest understood."""
        refusal = judged(_manifest(_file("library.sqlite3", 3)), KNOWN, BACKUP_FORMAT)
        assert refusal == Refusal(RefusalKind.NEWER_SCHEMA, "library.sqlite3", 3, 2)

    def test_a_schema_too_old_is_refused(self) -> None:
        """FR-B31."""
        refusal = judged(_manifest(_file("shops.json", 0)), KNOWN, BACKUP_FORMAT)
        assert refusal == Refusal(RefusalKind.OLDER_SCHEMA, "shops.json", 0, 1)

    def test_an_older_schema_still_read_is_accepted(self) -> None:
        """FR-B30."""
        manifest = _manifest(_file("library.sqlite3", 0))
        assert judged(manifest, KNOWN, BACKUP_FORMAT) is None

    def test_a_file_nobody_here_knows_is_no_reason_to_refuse(self) -> None:
        manifest = _manifest(_file("candidate-genres.json", 99))
        assert judged(manifest, KNOWN, BACKUP_FORMAT) is None

    def test_only_known_files_are_restorable(self) -> None:
        kept = _file("shops.json", 1)
        manifest = _manifest(kept, _file("candidate-genres.json", 1))
        assert restorable(manifest, KNOWN) == (kept,)


class TestWhatIsSaid:
    def test_damage_names_the_file_and_the_fault(self) -> None:
        said = Refusal(RefusalKind.DAMAGED, "x.zip", detail="it is not a zip").sentence
        assert said == "x.zip cannot be restored: it is not a zip."

    def test_a_newer_format_names_both_formats(self) -> None:
        said = Refusal(RefusalKind.NEWER_FORMAT, "This backup", 2, 1).sentence
        assert "format 2" in said and "format 1 at most" in said

    def test_a_newer_schema_names_the_file_and_both_numbers(self) -> None:
        said = Refusal(RefusalKind.NEWER_SCHEMA, "library.sqlite3", 3, 2).sentence
        assert "library.sqlite3 at schema 3" in said and "schema 2 at most" in said

    def test_an_older_schema_names_the_oldest_read(self) -> None:
        said = Refusal(RefusalKind.OLDER_SCHEMA, "shops.json", 0, 1).sentence
        assert "shops.json at schema 0" in said and "schema 1 at the oldest" in said
