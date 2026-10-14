# Backing up the library and restoring it

Requirements for copying what Stellody knows about a library to a folder the
listener chooses, then restoring it. EARS form; each names its test. FR-B13
and FR-B23 are also checked by hand in a packaged build; NFR-B01 only by a
timed run.

## 1. Introduction

### 1.1 Purpose

The database holds what a rescan cannot recover (edits, overrides, ratings,
listening, settings, taste profiles); beside it sit costly JSON files. A
backup keeps them wherever the listener likes; a restore puts them back.

### 1.2 Scope

**In:** File menu backup to one dated zip and restore from one; a manifest of
format and per-file schema; schema numbers on every carried file; a safety
backup before every restore; a restart to take the restore up; reporting a
missing music folder afterwards.

**Out:** scheduled backups; pruning old ones; the music; the `artwork` and
`shapes` caches (rebuilt by measuring); the logs; partial restore or merging
(FR-B25); encryption; cloud sync; rewriting the restored music folder
(FR-B32); backups with newer schemas (FR-B29).

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Data folder | `paths.data_location()`. |
| Backed-up set | The files of DATA-B01; nothing else. |
| Manifest | `manifest.json` in a backup (FR-B14). |
| Backup format | The numbered layout of zip and manifest; distinct from file schemas. |
| Schema number | A whole number naming a file's shape; the file's owner fixes the newest it writes and the oldest it reads. |
| Owner | The module reading and writing a file (DATA-B01). |
| Safety backup | The backup FR-B20 writes before a restore. |
| Remembered folder | The last backup's folder, kept in settings. |
| Staged restore | A verified backup unpacked in the data folder, awaiting the next start (FR-B24). |

### 1.4 References

`ARCHITECTURE.md`; `DISCOVERY.md` and `SHOPS.md` (the JSON files);
`infrastructure/switch_reset.py` (the next-start note pattern).

## 2. Overall description

Two File menu commands over `Backups` (`application/backing_up.py`);
`backup_file.py` writes and reads backups; `staged_restore.py` completes a
restore at the next start. No outward connection. One user: the listener, on
Windows, macOS or Linux; Downloads is `QStandardPaths.DownloadLocation`.

Constraints:

- The database runs in WAL mode (`store.py`, `JOURNAL_MODE`); a file copy can
  miss the WAL.
- The catalogue memory is written whole only at quit, the genre cache only
  after a discovery run (`application/candidate_genres.py`); answers between
  live in their `.record` journals.
- Windows will not replace a file held open, so the live database cannot be
  swapped under the running store.
- A backup is as unencrypted as the data folder.
- House rules: layering; `LINE_CAP` (`tests/structural/test_loc.py`); full
  branch coverage of domain and application; no magic values; no Qt below
  infrastructure; confirmation before anything destructive.

| # | Assumption | Owner | Status |
|---|---|---|---|
| A-01 | A journal copied mid-append may end in a torn line, which the reader skips (`tests/infrastructure/test_journal.py::test_a_half_written_last_line_costs_only_that_line`). | Claude | Answered |
| A-02 | A packaged build can relaunch itself; seen by Oliver. | Oliver | Answered |
| A-03 | A real library backs up in well under a second on the reference machine, mostly zipping. | Oliver | Answered |

## 3. Requirements

All Must (Appendix B).

### 3.1 Functional: backing up

**FR-B01 Back up is on the File menu**
- Requirement: The File menu shall carry "Back up library..." directly below
  Rescan (Oliver's ruling).
- Verified by: `tests/ui/test_backup_menu.py::test_back_up_sits_below_rescan`

**FR-B02 The folder is chosen first**
- Requirement: When "Back up library..." is chosen, Stellody shall ask for a
  folder before writing anything.
- Verified by: `tests/ui/test_backup_menu.py::test_cancelling_the_folder_writes_nothing`

**FR-B03 One dated zip is written**
- Requirement: When a folder is chosen, the backup service shall write into it
  one zip, `stellody-backup-YYYY-MM-DD-HHMM.zip`, holding the set plus a
  manifest (Oliver's ruling).
- Verified by: `tests/domain/test_backups.py::TestNaming::test_the_zip_is_named_by_the_minute`,
  `tests/application/test_restoring.py::test_a_backup_is_written_under_a_dated_name`

**FR-B04 A name already taken is not overwritten**
- Requirement: If that name is taken, then the backup service shall add a
  counter to the new name.
- Verified by: `tests/domain/test_backups.py::TestNaming::test_a_taken_name_gains_a_counter`

**FR-B05 The picker opens on Downloads the first time**
- Requirement: While no folder is remembered, the folder dialog shall open on
  Downloads (Oliver's ruling).
- Verified by: `tests/ui/test_backup_menu.py::test_the_first_backup_opens_on_downloads`

**FR-B06 The last folder is remembered**
- Requirement: When a backup is written, Stellody shall remember its folder and
  open the next backup or restore dialog there (Oliver's ruling).
- Verified by: `tests/ui/test_backup_menu.py::test_the_next_backup_opens_where_the_last_went`

**FR-B07 A remembered folder that has gone falls back**
- Requirement: If the remembered folder no longer exists, then the dialog shall
  open on Downloads.
- Verified by: `tests/ui/test_backup_menu.py::test_a_vanished_folder_falls_back_to_downloads`

**FR-B08 The database is copied through SQLite's own backup**
- Requirement: The backup service shall copy the database with SQLite's online
  backup, never as a file.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_write_still_in_the_wal_is_carried`

**FR-B09 Every file in the set is carried when it exists**
- Requirement: The backup service shall carry every DATA-B01 file present; an
  absent one is left out of zip and manifest, so a restore reproduces its
  absence.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_missing_file_is_left_out`

**FR-B10 Nothing outside the set is carried**
- Requirement: The backup service shall carry nothing DATA-B01 does not name.
- Verified by: `tests/infrastructure/test_backup_file.py::test_caches_and_logs_stay_behind`

**FR-B11 A finished backup says where it went**
- Requirement: When a backup is written, Stellody shall say so, naming its full
  path.
- Verified by: `tests/ui/test_backup_menu.py::test_a_finished_backup_names_its_file`

**FR-B12 A backup that fails leaves no partial zip**
- Requirement: If writing a backup fails, then the backup service shall remove
  any partial zip; Stellody shall say what failed, naming the folder.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_failed_write_leaves_nothing`,
  `tests/ui/test_backup_menu.py::test_a_failed_backup_says_why`

**FR-B13 Playback carries on while a backup is written**
- Requirement: While a backup is written (off the window's thread), playback
  shall have no audible gap and the window shall keep answering input.
- Verified by: by hand in a real build, plus
  `tests/ui/test_backup_menu.py::test_the_backup_runs_off_the_window_thread`

**FR-B35 Work in progress is shown**
- Requirement: While a backup is written, a chosen backup is verified or the
  library is saved before a restore, Stellody shall show it is working, naming
  which (Oliver's ruling).
- Verified by: `tests/ui/test_backup_menu.py::test_a_running_backup_is_shown`

**FR-B36 One at a time**
- Requirement: While any FR-B35 errand runs, Stellody shall disable "Back up
  library..." and "Restore from backup...".
- Verified by: `tests/ui/test_backup_menu.py::test_both_commands_wait_for_the_running_one`

### 3.2 Functional: the manifest and schemas

**FR-B14 Every backup carries a manifest**
- Requirement: Every zip shall hold `manifest.json` naming the backup format,
  the writing Stellody's version, the time written, plus each file's name,
  schema number and SHA-256 checksum (Oliver's ruling).
- Verified by: `tests/infrastructure/test_backup_file.py::test_the_manifest_names_every_file`

**FR-B15 The database knows its schema**
- Requirement: The store shall keep the database's schema number in `PRAGMA
  user_version`.
- Verified by: `tests/infrastructure/test_schema_numbers.py::test_the_database_carries_its_number`

**FR-B16 An unnumbered database is brought up to the current schema**
- Requirement: When the store opens a database at `user_version` 0, it shall
  apply every step of `database_schema.py` (`STEPS`), then record the number.
  Every step runs on every open, so a mismatched number and shape are repaired.
- Verified by: `tests/infrastructure/test_schema_numbers.py::test_an_unnumbered_library_is_brought_up`

**FR-B17 Each JSON owner declares its schema**
- Requirement: Each owner of a DATA-B01 JSON file shall declare every upgrade
  step it has added; the file's schema range shall be derived from them,
  starting at the first schema.
- Verified by: `tests/domain/test_backups.py::TestUpgrading::test_a_range_starts_at_the_first_schema_whatever_was_added`,
  `tests/domain/test_backups.py::TestUpgrading::test_an_owner_with_no_steps_reads_only_its_first_schema`,
  `tests/infrastructure/test_schema_numbers.py::test_every_owner_declares_its_range`

**FR-B18 A database shape change cannot ship without a schema bump**
- Requirement: The structural suite shall fail when the database's creating
  statements change while its schema number does not. The JSON equivalent is
  Won't this time: their shapes are code, not one text.
- Verified by: `tests/structural/test_schema_bumps.py::test_a_changed_shape_needs_a_new_number`

### 3.3 Functional: restoring

**FR-B19 Restore is on the File menu**
- Requirement: The File menu shall carry "Restore from backup..." directly below
  "Back up library...".
- Verified by: `tests/ui/test_backup_menu.py::test_restore_sits_below_back_up`

**FR-B20 A safety backup is written before anything is replaced**
- Requirement: When a restore is confirmed, the restore service shall first
  write `stellody-before-restore-YYYY-MM-DD-HHMM.zip` of the current set into
  the remembered folder, else Downloads (Oliver's ruling).
- Verified by: `tests/application/test_restoring.py::test_the_safety_backup_comes_first`

**FR-B21 No safety backup, no restore**
- Requirement: If the safety backup fails, then the restore service shall change
  nothing; Stellody shall say why, naming the folder.
- Verified by: `tests/application/test_restoring.py::test_a_failed_safety_backup_stops_the_restore`

**FR-B22 Restore asks first**
- Requirement: When a backup is chosen and verified, Stellody shall ask for
  confirmation in a modal dialog naming its file name and date and that the
  current library will be replaced.
- Verified by: `tests/ui/test_backup_menu.py::test_cancelling_the_restore_changes_nothing`

**FR-B23 Stellody restarts itself to take it up**
- Requirement: When the safety backup is written, Stellody shall stage the
  restore, then quit and start again (Oliver's ruling).
- Verified by: `tests/ui/test_backup_menu.py::test_a_confirmed_restore_stages_then_starts_again`,
  `tests/infrastructure/test_detached.py::test_starting_again_names_the_program_and_its_folder`,
  plus by hand in a packaged build (A-02)

**FR-B24 A staged restore completes at the next start**
- Requirement: When Stellody starts with a staged restore, it shall put the
  staged set in place before opening the library, then remove the staging; so
  the restore does not depend on the relaunch.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_the_next_start_completes_it`

**FR-B25 The restored set is exactly the backup's set**
- Requirement: When a staged restore is put in place, every DATA-B01 file the
  backup lacks shall be removed.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_a_file_the_backup_lacks_is_removed`

**FR-B26 No stale WAL survives a restore**
- Requirement: Before a staged restore puts the database in place, the old
  `-wal` and `-shm` files shall be removed.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_an_old_wal_is_not_replayed`

### 3.4 Functional: deciding whether a backup can be restored

**FR-B27 A backup is verified before anything else happens**
- Requirement: When a backup is chosen, the restore service shall check its
  manifest, checksums and schemas before FR-B22 asks.
- Verified by: `tests/application/test_restoring.py::test_verification_comes_before_confirmation`

**FR-B28 A damaged backup is refused**
- Requirement: If a chosen file is not a zip, has no readable manifest, lacks a
  listed file or has a checksum mismatch, then the restore service shall refuse
  it, naming the file and fault.
- Verified by: `tests/infrastructure/test_backup_file.py::TestReading::test_a_changed_byte_is_refused`

**FR-B29 A newer schema is refused whole**
- Requirement: If any file's schema is above the newest its owner writes (or the
  format is newer than known), then the restore service shall refuse the whole
  backup, naming the file, its schema and the newest understood. Decided by
  schema, never app version (Oliver's ruling).
- Verified by: `tests/application/test_restoring.py::test_a_newer_schema_is_refused`

**FR-B30 An older schema is brought up to date**
- Requirement: When a file's schema is readable but below the newest, the
  restore service shall accept it: a JSON file is upgraded as it is staged; the
  database by the store as it opens (Oliver's ruling).
- Verified by: `tests/infrastructure/test_staged_restore.py::test_an_older_database_is_brought_up`,
  `tests/infrastructure/test_old_backups.py::test_a_file_from_before_a_change_is_brought_up_as_it_is_staged`,
  `tests/domain/test_backups.py::TestUpgrading`

**FR-B31 A schema too old to read is refused**
- Requirement: If a file's schema is below its owner's oldest readable, then the
  restore service shall refuse the whole backup, naming the file, its schema and
  the oldest read.
- Verified by: `tests/domain/test_backups.py::TestJudging::test_a_schema_too_old_is_refused`

**FR-B37 No owner stops reading a shape it once wrote**
- Requirement: The suite shall fail when any DATA-B01 file cannot be read at its
  first numbered schema: zero for the database, the first schema for JSON
  (Oliver's ruling).
- Verified by: `tests/infrastructure/test_old_backups.py::test_no_owner_stops_reading_a_shape_it_once_wrote`

**FR-B38 Every backup format stays readable**
- Requirement: The archive shall read backups of every format from the first to
  the newest.
- Verified by: `tests/infrastructure/test_old_backups.py::test_a_format_one_backup_of_an_unnumbered_library_restores`

### 3.5 Functional: after a restore

**FR-B32 A missing music folder is said after the restart**
- Requirement: When Stellody starts after a restore whose music folder does not
  exist, it shall name the folder as missing and offer File > Choose music
  folder (Oliver's ruling).
- Verified by: `tests/ui/test_after_restore.py::test_a_missing_folder_is_named`

**FR-B33 A completed restore says so**
- Requirement: When Stellody starts after a restore, it shall report it
  complete, naming the backup restored and the safety backup.
- Verified by: `tests/ui/test_after_restore.py::test_the_restore_is_reported`

**FR-B34 A restore that fails at start is said and undone**
- Requirement: If a staged restore fails part way, then Stellody shall put back
  the set it moved aside, then say what failed, naming the safety backup.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_a_failure_part_way_is_undone`,
  `tests/ui/test_after_restore.py::test_a_failure_part_way_is_said`

### 3.6 Non-functional

**NFR-B01 A backup does not get slower unnoticed**
- Requirement: When the reference machine backs up a set of at most 260 MB, the
  backup service shall finish within 5 seconds.
- Rationale: A regression guard, not a promise; FR-B13, FR-B35 and FR-B36 cover
  slower machines.
- Verified by: a timed run on the reference machine over a copy of Oliver's
  real library, padded to the bound.

**NFR-B02 Coverage**
- Requirement: `application/backing_up.py` and `domain/backups.py` shall have
  100 percent branch coverage in the gated suite; the infrastructure modules are
  held by each requirement's tests.
- Verified by: the coverage gate (`pyproject.toml`, `--cov-fail-under=100`
  over `stellody.domain` and `stellody.application`).

### 3.7 Data

**DATA-B01 The backed-up set**

| File | Owner | Holds |
|---|---|---|
| `library.sqlite3` | `store.py` | The library and all its edits, listening and settings |
| `catalogue-memory.json` | `catalogue_memory.py` | Catalogue answers |
| `catalogue-memory.record` | `catalogue_memory.py` | Answers since the last write |
| `discovered.json` | `discovery_file.py` | The last discovery answer |
| `candidate-genres-2.json` | `discovery_file.py` | Candidate genres |
| `candidate-genres-2.record` | `discovery_file.py` | Answers since the last write |
| `shops.json` | `shop_file.py` | The shop list |

A journal's schema derives from its own steps (`JOURNAL_UPGRADES`,
`CACHE_JOURNAL_UPGRADES`). A cache named by a rule's number is renamed when the
rule changes; a restore skips an old name it does not list.

## Appendix A: Open questions

None.

## Appendix B: Priorities

- **Must:** FR-B01 to FR-B38, NFR-B01, NFR-B02.
- **Won't this time:** everything out of scope in 1.2; a schema-bump guard over
  the JSON owners (FR-B18).
