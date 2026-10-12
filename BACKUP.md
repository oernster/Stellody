# Backing up the library and restoring it

Specification for keeping a copy of everything Stellody has learned about a
library somewhere the listener chooses, then putting that copy back. It is in
the house form: EARS requirements, each with the failure case beside it, each
naming the test that proves it. Every requirement states the rule as it stands
today. No version number of its own: a document version beside a product
version is two numbers a reader has to tell apart, only one of them the
product's.

It is built. Every requirement below names what verifies it. FR-B13 and FR-B23
are also checked by hand in a packaged build; NFR-B01 is checked only by a
timed run on the reference machine.

## 1. Introduction

### 1.1 Purpose

The library database holds a good deal that cannot be had back by
scanning again: tag and album edits, overrides, ratings, listening history,
settings and taste profiles. Beside it sit the discovery answer, the catalogue
memory, the genre cache and the shop list, each of which cost network time or
editing time to build. A lost or damaged data folder loses all of it. This
gives the listener a backup they can keep wherever they like, plus a restore
that puts one back without hand-copying files into Stellody's own directory.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 Scope

**In scope:** a File menu command that writes one dated zip to a folder the
listener chooses; a File menu command that restores from such a zip; a
manifest in every zip stating its format and the schema of each file it holds;
a schema number for the database and for each JSON file a backup carries; a
safety backup taken before every restore; Stellody restarting itself to take up
a restored library; saying so when a restored library names a music folder that
is not there.

**Out of scope, so that it is not re-proposed:**

- Scheduled or automatic backups. A backup happens when the listener asks for
  one; the safety backup before a restore is the one exception (FR-B20).
- Pruning old backups. What is kept in the chosen folder is the listener's.
- Backing up the music. Stellody never writes to the music folder; the music
  is the listener's to copy.
- The artwork and waveform caches (`artwork`, `shapes`). Both are rebuilt by
  measuring again, so carrying them makes every backup larger for nothing that
  is lost without them.
- The two logs (`stellody-diary.log`, `stellody-startup.log`). They describe a
  session on one machine, not the library.
- Restoring part of a backup: one file, one table or one setting. A restore
  puts back the whole set (FR-B25).
- Merging a backup with the current library. Restore replaces.
- Encryption or a password on the zip. A backup holds what the data folder
  already holds unencrypted; see 2.4.
- Cloud storage, upload or sync of any kind. The chosen folder may be one a
  sync client watches; that is the listener's arrangement, not Stellody's.
- Rewriting the music folder named inside a restored library. FR-B32 says it is
  missing; choosing another stays with File > Choose music folder.
- Restoring a backup made by a Stellody whose schemas are newer than this one
  knows (FR-B29).

### 1.4 Definitions

| Term | Meaning here |
|---|---|
| Data folder | Stellody's own per-user directory (`paths.data_location()`). |
| Backup | One zip written by FR-B03, holding the backed-up set plus a manifest. |
| Backed-up set | The database plus the JSON files and journals listed in DATA-B01. Nothing else. |
| Manifest | `manifest.json` inside a backup: the backup format number, the Stellody version that wrote it, the moment it was written, plus a schema number and a checksum for every file in the set. |
| Backup format | The layout of the zip and its manifest, numbered. Distinct from any file's schema. |
| Schema number | A whole number naming the shape of one stored file. Each file has exactly one owner, whose upgrade steps fix the newest number it writes and the oldest it can still read. |
| Owner | The infrastructure module that reads and writes a file: `store.py` for the database, `catalogue_memory.py`, `discovery_file.py` and `shop_file.py` for the JSON files. |
| Safety backup | The backup FR-B20 writes automatically before a restore replaces anything. |
| Remembered folder | The folder the last backup was written to, kept in the settings table. |
| Staged restore | A verified backup unpacked inside the data folder, waiting to replace the live set at the next start (FR-B24). |

### 1.5 References

- `ARCHITECTURE.md`, for the layering and for the modules permitted to write
  to disk.
- `DISCOVERY.md` and `SHOPS.md`, which specify the JSON files a backup carries.
- `infrastructure/switch_reset.py`, the existing pattern of a note left in the
  data folder that the next start acts on.

## 2. Overall description

### 2.1 Product perspective

Two File menu commands over one application service (`Backups`, in
`application/backing_up.py`); one infrastructure module that writes and reads
backups (`backup_file.py`) plus one that completes a staged restore at the next
start (`staged_restore.py`); a schema number on every file in the set. The
database carries its number in `PRAGMA user_version`, its steps listed in
`database_schema.py`; each JSON owner lists its upgrade steps, from which its
range is derived (FR-B17). No outward connection.

### 2.2 User classes

One: the listener, who owns the library and the machine. There is no second
role.

### 2.3 Operating environment

Windows, macOS and Linux, the three Stellody already ships to. The listener's
Downloads folder is the one the operating system names (Qt's
`QStandardPaths.DownloadLocation`).

### 2.4 Constraints

- The database runs in WAL mode (`store.py`, `JOURNAL_MODE`). A file copy
  taken while Stellody runs can miss what the WAL holds, so the database is
  copied through SQLite's online backup, never as a file.
- The catalogue memory is written whole only when Stellody quits
  (`catalogue_memory.py` docstring); the genre cache is written whole when a
  discovery run finishes asking about candidates
  (`application/candidate_genres.py`).
  Between those writes their answers live in the `.record` journals beside
  them. A backup without the journals silently loses those answers.
- Windows will not replace a file another handle holds open. A restore cannot
  swap the live database underneath the running store.
- A backup holds personal data unencrypted, exactly as the data folder does.
  Where it is kept decides who can read it; Stellody says nothing more about
  that than it already says about the data folder.
- The house rules hold: clean-architecture layering, modules within
  `LINE_CAP` (`tests/structural/test_loc.py`), 100 percent branch coverage over domain and application, no magic values, no Qt
  below the infrastructure layer, confirmation before anything destructive.

### 2.5 Assumptions and dependencies

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | A journal copied while a discovery run appends to it can end in a torn last line, which the journal reader skips: held by `tests/infrastructure/test_journal.py::test_a_half_written_last_line_costs_only_that_line`. | Claude | Answered |
| A-02 | Stellody can relaunch itself as a packaged build: seen by Oliver, a restore relaunched the built copy. | Oliver | Answered |
| A-03 | A backup is a matter of seconds. Measured on a copy of Oliver's real library: a 26,128,646 byte set (database 7,405,568) backed up and zipped in 0.30 s over three runs, giving a 3,579,524 byte zip. | Oliver | Answered |

## 3. Requirements

Every requirement below is a Must unless it carries a Priority line;
Appendix B lists them.

### 3.1 Functional: backing up

**FR-B01 Back up is on the File menu**
- Requirement: The File menu shall carry "Back up library..." directly below
  Rescan.
- Rationale: Oliver's ruling. The File menu already holds the commands that
  act on the library as a whole.
- Acceptance: Given the main window, when the File menu is read, then the item
  after Rescan is "Back up library...".
- Verified by: `tests/ui/test_backup_menu.py::test_back_up_sits_below_rescan`

**FR-B02 The folder is chosen first**
- Requirement: When "Back up library..." is chosen, Stellody shall ask for a
  folder before writing anything.
- Acceptance: Given the menu item is chosen, when the folder dialog is
  cancelled, then no file is written anywhere.
- Verified by: `tests/ui/test_backup_menu.py::test_cancelling_the_folder_writes_nothing`

**FR-B03 One dated zip is written**
- Requirement: When a folder is chosen, the backup service shall write one zip
  named `stellody-backup-YYYY-MM-DD-HHMM.zip` into it, holding the backed-up
  set plus a manifest.
- Rationale: Oliver's ruling: one file to move or keep. The minute in the name
  stops two backups on one day colliding.
- Acceptance: Given the clock reads 2026-10-12 14:05, when a backup is written
  to a folder, then that folder gains `stellody-backup-2026-10-12-1405.zip`.
- Verified by: `tests/domain/test_backups.py::TestNaming::test_the_zip_is_named_by_the_minute`,
  `tests/application/test_restoring.py::test_a_backup_is_written_under_a_dated_name`

**FR-B04 A name already taken is not overwritten**
- Requirement: If the chosen folder already holds a file of the name FR-B03
  gives, then the backup service shall add a counter to the new name rather
  than replace the existing file.
- Rationale: The unwanted sibling of FR-B03. Two backups inside one minute are
  possible; losing the first to the second is not acceptable.
- Acceptance: Given the folder holds `stellody-backup-2026-10-12-1405.zip`,
  when a second backup is written in the same minute, then the folder holds
  that file unchanged plus `stellody-backup-2026-10-12-1405-2.zip`.
- Verified by: `tests/domain/test_backups.py::TestNaming::test_a_taken_name_gains_a_counter`

**FR-B05 The picker opens on Downloads the first time**
- Requirement: While no folder is remembered, the folder dialog shall open on
  the listener's Downloads folder.
- Rationale: Oliver's ruling.
- Acceptance: Given a library with no remembered folder, when Back up is
  chosen, then the dialog opens on the Downloads folder.
- Verified by: `tests/ui/test_backup_menu.py::test_the_first_backup_opens_on_downloads`

**FR-B06 The last folder is remembered**
- Requirement: When a backup is written, Stellody shall remember its folder;
  the next folder dialog for a backup or a restore shall open there.
- Rationale: Oliver's ruling.
- Acceptance: Given a backup was written to `D:\Backups`, when Back up is
  chosen again, then the dialog opens on `D:\Backups`.
- Verified by: `tests/ui/test_backup_menu.py::test_the_next_backup_opens_where_the_last_went`

**FR-B07 A remembered folder that has gone falls back**
- Requirement: If the remembered folder no longer exists, then the folder
  dialog shall open on Downloads.
- Rationale: The unwanted sibling of FR-B06: a removed drive or folder must not
  leave a dialog opening on nothing.
- Acceptance: Given the remembered folder has been deleted, when Back up is
  chosen, then the dialog opens on Downloads.
- Verified by: `tests/ui/test_backup_menu.py::test_a_vanished_folder_falls_back_to_downloads`

**FR-B08 The database is copied through SQLite's own backup**
- Requirement: The backup service shall copy the database with SQLite's online
  backup, never as a file.
- Rationale: 2.4: the WAL.
- Acceptance: Given a write committed to the library but not yet checkpointed
  out of the WAL, when a backup is written, then the database inside the zip
  holds that write.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_write_still_in_the_wal_is_carried`

**FR-B09 Every file in the set is carried when it exists**
- Requirement: The backup service shall carry every file of DATA-B01 that
  exists in the data folder; one that does not exist is left out and the
  manifest shall not list it.
- Rationale: Absence is an answer: a listener who never ran discovery has no
  `discovered.json`, which is a fact a restore must reproduce (FR-B25).
- Acceptance: Given a data folder without `shops.json`, when a backup is
  written, then the zip holds no `shops.json` and the manifest names none.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_missing_file_is_left_out`

**FR-B10 Nothing outside the set is carried**
- Requirement: The backup service shall carry nothing from the data folder
  that DATA-B01 does not name.
- Rationale: The caches and logs are out of scope (1.3).
- Acceptance: Given a data folder holding `artwork`, `shapes` and both logs,
  when a backup is written, then the zip holds none of them.
- Verified by: `tests/infrastructure/test_backup_file.py::test_caches_and_logs_stay_behind`

**FR-B11 A finished backup says where it went**
- Requirement: When a backup has been written, Stellody shall say so, naming
  the file's full path.
- Acceptance: Given a backup written to `D:\Backups`, when it completes, then
  a message names `D:\Backups\stellody-backup-2026-10-12-1405.zip`.
- Verified by: `tests/ui/test_backup_menu.py::test_a_finished_backup_names_its_file`

**FR-B12 A backup that fails leaves no partial zip**
- Requirement: If writing a backup fails, then the backup service shall remove
  any partly written zip; Stellody shall say what failed and where, naming the
  folder.
- Rationale: The unwanted sibling of FR-B03. A half zip under a backup's name
  is worse than none: it is trusted later. A full disk and a folder that cannot
  be written are the ordinary causes.
- Acceptance: Given a folder that refuses writes, when a backup is attempted,
  then no zip exists there and the message names the folder plus the reason.
- Verified by: `tests/infrastructure/test_backup_file.py::test_a_failed_write_leaves_nothing`,
  `tests/ui/test_backup_menu.py::test_a_failed_backup_says_why`

**FR-B13 Playback carries on while a backup is written**
- Requirement: While a backup is being written, Stellody shall keep playing
  without an audible gap and the window shall keep answering input.
- Rationale: A dropout is a defect, not a matter of taste. The writing happens
  off the window's thread.
- Acceptance: Given a track playing, when a backup is written, then no dropout
  is heard and the window answers a click within the same frame budget as
  without one.
- Verified by: by hand in a real build, plus
  `tests/ui/test_backup_menu.py::test_the_backup_runs_off_the_window_thread`

**FR-B35 Work in progress is shown**
- Requirement: While a backup is being written, a chosen backup is being
  verified or the current library is being saved before a restore, Stellody
  shall show that it is working, naming which of the three.
- Rationale: Oliver's ruling: a spinning disk can make either take
  far longer than the reference machine does, so the listener must never be
  left wondering whether anything is happening.
- Acceptance: Given a backup service held part way by a test double, when the
  window is read, then it says a backup is being written.
- Verified by: `tests/ui/test_backup_menu.py::test_a_running_backup_is_shown`

**FR-B36 One at a time**
- Requirement: While any errand of FR-B35 runs, Stellody shall disable "Back
  up library..." and "Restore from backup...".
- Rationale: The unwanted sibling of FR-B35. A second press on a slow machine
  would start a second backup under the same minute's name; it could also start
  a restore over a backup still being written.
- Acceptance: Given a backup held part way, when the File menu is read, then
  both items are disabled; when it completes, both are enabled.
- Verified by: `tests/ui/test_backup_menu.py::test_both_commands_wait_for_the_running_one`

### 3.2 Functional: the manifest and schemas

**FR-B14 Every backup carries a manifest**
- Requirement: The backup service shall write `manifest.json` into every zip,
  naming the backup format number, the Stellody version that wrote it, the
  moment it was written, plus each carried file's name, schema number and
  SHA-256 checksum.
- Rationale: Oliver's ruling: the backup's data is versioned by schema.
- Acceptance: Given a library at database schema 1, when a backup is written,
  then the manifest lists `library.sqlite3` at schema 1 with the checksum of
  the copy in the zip.
- Verified by: `tests/infrastructure/test_backup_file.py::test_the_manifest_names_every_file`

**FR-B15 The database knows its schema**
- Requirement: The store shall keep the database's schema number in
  `PRAGMA user_version`.
- Rationale: A database that records no shape cannot be compared with another
  copy of itself.
- Acceptance: Given a database just opened by the store, when `user_version` is
  read, then it equals the store's current schema number.
- Verified by: `tests/infrastructure/test_schema_numbers.py::test_the_database_carries_its_number`

**FR-B16 An unnumbered database is brought up to the current schema**
- Requirement: When the store opens a database whose `user_version` is 0, it
  shall apply every numbered step up to the current schema, then record the
  number.
- Rationale: The unwanted sibling of FR-B15: a library written before
  numbering reads 0. The `folders.derivation` column (`folder_derivation.py`)
  is step 1 (`database_schema.py`, `STEPS`). Every step runs on every open, so
  a file whose number and shape disagree is repaired rather than refused.
- Acceptance: Given an unnumbered database holding no `derivation` column,
  when the store opens it, then the column exists and `user_version` reads the
  current schema.
- Verified by: `tests/infrastructure/test_schema_numbers.py::test_an_unnumbered_library_is_brought_up`

**FR-B17 Each JSON owner declares its schema**
- Requirement: Each owner of a JSON file in DATA-B01 shall declare every
  upgrade step it has added to that file; the file's schema range shall be
  derived from those steps, starting at the first schema.
- Rationale: A range worked out from the steps cannot claim a shape no step
  reaches, nor fall out of step with a journal beside its file.
- Acceptance: Given an owner's list of steps, when its file's range is read,
  then it runs from the first schema to one past it per step; given the set,
  then every file of DATA-B01 has a range.
- Verified by: `tests/domain/test_backups.py::TestUpgrading::test_a_range_starts_at_the_first_schema_whatever_was_added`,
  `tests/domain/test_backups.py::TestUpgrading::test_an_owner_with_no_steps_reads_only_its_first_schema`,
  `tests/infrastructure/test_schema_numbers.py::test_every_owner_declares_its_range`

**FR-B18 A database shape change cannot ship without a schema bump**
- Requirement: The structural suite shall fail when the database's creating
  statements change while its schema number does not.
- Rationale: A schema number is honest only while it is bumped. The database's
  shape is text, so it can be fingerprinted; a JSON file's shape is built in
  code and written down nowhere as one text, so the same guard over the JSON
  owners is Won't this time (Appendix B). Proved by planting a
  column: exit 1 with it, exit 0 once removed.
- Acceptance: Given a column added to the database schema, when the structural
  suite runs without the number changing, then it fails naming
  `database_schema.py`.
- Verified by: `tests/structural/test_schema_bumps.py::test_a_changed_shape_needs_a_new_number`

### 3.3 Functional: restoring

**FR-B19 Restore is on the File menu**
- Requirement: The File menu shall carry "Restore from backup..." directly
  below "Back up library...".
- Acceptance: Given the main window, when the File menu is read, then the item
  after "Back up library..." is "Restore from backup...".
- Verified by: `tests/ui/test_backup_menu.py::test_restore_sits_below_back_up`

**FR-B20 A safety backup is written before anything is replaced**
- Requirement: When a restore is confirmed, the restore service shall first
  write a backup of the current set named
  `stellody-before-restore-YYYY-MM-DD-HHMM.zip` into the remembered folder
  (Downloads where none is remembered).
- Rationale: Oliver's ruling. A wrong choice of file is then always undoable.
- Acceptance: Given a confirmed restore at 2026-10-12 14:05, when it begins,
  then `stellody-before-restore-2026-10-12-1405.zip` exists before any live
  file changes.
- Verified by: `tests/application/test_restoring.py::test_the_safety_backup_comes_first`

**FR-B21 No safety backup, no restore**
- Requirement: If the safety backup cannot be written, then the restore
  service shall change nothing and Stellody shall say why, naming the folder.
- Rationale: The unwanted sibling of FR-B20.
- Acceptance: Given a remembered folder that refuses writes, when a restore is
  confirmed, then every live file is unchanged and the message names the
  folder.
- Verified by: `tests/application/test_restoring.py::test_a_failed_safety_backup_stops_the_restore`

**FR-B22 Restore asks first**
- Requirement: When a backup has been chosen and verified, Stellody shall ask
  for confirmation in a modal dialog naming the backup's file name, the date it
  was written and that the current library will be replaced.
- Rationale: The house rule: nothing destructive without a confirmation naming
  its target.
- Acceptance: Given a verified backup, when the dialog is cancelled, then no
  file is written or changed.
- Verified by: `tests/ui/test_backup_menu.py::test_cancelling_the_restore_changes_nothing`

**FR-B23 Stellody restarts itself to take it up**
- Requirement: When the safety backup is written, Stellody shall stage the
  restore, then quit and start again.
- Rationale: Oliver's ruling. Nothing held in memory can then disagree with the
  restored files; 2.4 rules out swapping files under the open store.
- Acceptance: Given a confirmed restore, when the safety backup completes, then
  a staged restore exists and a new Stellody process starts.
- Verified by: `tests/ui/test_backup_menu.py::test_a_confirmed_restore_stages_then_starts_again`,
  `tests/infrastructure/test_detached.py::test_starting_again_names_the_program_and_its_folder`,
  plus by hand in a packaged build (A-02)

**FR-B24 A staged restore completes at the next start**
- Requirement: When Stellody starts and finds a staged restore, it shall put
  the staged set in place before the library is opened, then remove the
  staging.
- Rationale: The restart can fail; the listener can quit before it happens;
  the restore must not depend on that one relaunch.
- Acceptance: Given a staged restore left by a process that never relaunched,
  when Stellody is next started by hand, then the restored set is live and no
  staging remains.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_the_next_start_completes_it`

**FR-B25 The restored set is exactly the backup's set**
- Requirement: When a staged restore is put in place, every file of DATA-B01
  that the backup does not hold shall be removed from the data folder.
- Rationale: A restore replaces; it does not merge (1.3). A `shops.json` left
  over beside a backup that had none would be a set nobody ever had.
- Acceptance: Given a live `shops.json` and a backup without one, when the
  restore completes, then the data folder holds no `shops.json`.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_a_file_the_backup_lacks_is_removed`

**FR-B26 No stale WAL survives a restore**
- Requirement: When a staged restore puts the database in place, the
  database's `-wal` and `-shm` companions from before shall be removed first.
- Rationale: A leftover WAL replays the old library's pages onto the restored
  one.
- Acceptance: Given a live database with a non-empty WAL, when the restore
  completes, then the restored rows read back unchanged.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_an_old_wal_is_not_replayed`

### 3.4 Functional: deciding whether a backup can be restored

**FR-B27 A backup is verified before anything else happens**
- Requirement: When a backup is chosen for restore, the restore service shall
  check its manifest, checksums and schemas before the confirmation of FR-B22
  is shown.
- Acceptance: Given a backup that fails any check, when it is chosen, then no
  confirmation appears and no safety backup is written.
- Verified by: `tests/application/test_restoring.py::test_verification_comes_before_confirmation`

**FR-B28 A damaged backup is refused**
- Requirement: If a chosen file is not a zip, holds no readable manifest,
  lacks a file its manifest lists or holds one whose checksum differs, then the
  restore service shall refuse it, naming the file and what is wrong.
- Rationale: The unwanted sibling of FR-B27.
- Acceptance: Given a backup whose `library.sqlite3` has one byte changed, when
  it is chosen, then the refusal names `library.sqlite3` and a checksum
  mismatch.
- Verified by: `tests/infrastructure/test_backup_file.py::TestReading::test_a_changed_byte_is_refused`

**FR-B29 A newer schema is refused whole**
- Requirement: If any file in a backup carries a schema number above the
  newest its owner writes (or the backup format is newer than this Stellody
  knows), then the restore service shall refuse the whole backup, naming the
  file, its schema and the newest this Stellody understands.
- Rationale: Oliver's ruling: decided by schema, never by app version. An
  owner cannot know what a newer shape means.
- Acceptance: Given a backup listing `library.sqlite3` at schema 3 restored by
  a Stellody whose store writes schema 2, when it is chosen, then the refusal
  names `library.sqlite3`, schema 3 and schema 2.
- Verified by: `tests/application/test_restoring.py::test_a_newer_schema_is_refused`

**FR-B30 An older schema is brought up to date**
- Requirement: When a backup's file carries a schema at or above its owner's
  oldest readable number but below its newest, the restore service shall
  accept it; a JSON file shall be taken through every upgrade step since as it
  is staged, while the database is brought up by the store as it opens.
- Rationale: Old backups stay restorable (Oliver's ruling).
- Acceptance: Given a backup holding a database at schema 0, when it is
  restored, then the library opens at the current schema with its rows intact.
  Given a shop file at schema 1 and an owner that has added one step since,
  when it is staged, then the staged file is the step's output.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_an_older_database_is_brought_up`,
  `tests/infrastructure/test_old_backups.py::test_a_file_from_before_a_change_is_brought_up_as_it_is_staged`,
  `tests/domain/test_backups.py::TestUpgrading`

**FR-B31 A schema too old to read is refused**
- Requirement: If a backup's file carries a schema below its owner's oldest
  readable number, then the restore service shall refuse the whole backup,
  naming the file, its schema and the oldest this Stellody reads.
- Rationale: The unwanted sibling of FR-B30. Under FR-B37 no owner ever stops
  reading a shape it wrote, so only a manifest no Stellody wrote can reach
  this; a zip is foreign input and says whatever it says.
- Acceptance: Given an owner whose oldest readable schema is 2 and a backup
  holding that file at 1, when it is chosen, then the refusal names the file,
  schema 1 and schema 2.
- Verified by: `tests/domain/test_backups.py::TestJudging::test_a_schema_too_old_is_refused`

**FR-B37 No owner stops reading a shape it once wrote**
- Requirement: The suite shall fail when any file of DATA-B01 can no longer be
  read at the schema it was first numbered at: zero for the database, the
  first schema for each JSON file.
- Rationale: A backup made by an older version must restore (Oliver's ruling).
  A change of shape adds a step; it never removes one. Proved by raising the database's oldest readable schema to 1:
  exit 1 with it, exit 0 once removed.
- Acceptance: Given the database's oldest readable schema raised from 0 to 1,
  when the suite runs, then it fails naming the database.
- Verified by: `tests/infrastructure/test_old_backups.py::test_no_owner_stops_reading_a_shape_it_once_wrote`

**FR-B38 Every backup format stays readable**
- Requirement: The archive shall read a backup written in any format from the
  first to the newest.
- Rationale: The unwanted sibling of a format change. A later format adds a
  reader for itself rather than changing what an earlier one is read as.
- Acceptance: Given a format 1 backup whose manifest is typed out as literal
  text, holding a schema 0 database, when it is restored, then the library
  opens at the current schema with its rows intact.
- Verified by: `tests/infrastructure/test_old_backups.py::test_a_format_one_backup_of_an_unnumbered_library_restores`

### 3.5 Functional: after a restore

**FR-B32 A missing music folder is said after the restart**
- Requirement: When Stellody starts after a restore and the restored library's
  music folder does not exist, Stellody shall name the folder as missing and
  offer File > Choose music folder.
- Rationale: Oliver's ruling. A backup restored on another machine names that
  machine's folder.
- Acceptance: Given a restored library naming `E:\Music`, which does not
  exist, when Stellody starts, then a message names `E:\Music` and offers to
  choose a folder.
- Verified by: `tests/ui/test_after_restore.py::test_a_missing_folder_is_named`

**FR-B33 A completed restore says so**
- Requirement: When Stellody starts after a restore, it shall say the restore
  is complete, naming the backup restored and the safety backup written.
- Acceptance: Given a completed restore, when the window opens, then a message
  names both zips.
- Verified by: `tests/ui/test_after_restore.py::test_the_restore_is_reported`

**FR-B34 A restore that fails at start is said and undone**
- Requirement: If putting a staged restore in place fails part way, then
  Stellody shall put the set it moved aside back in place, then say what failed,
  naming the safety backup.
- Rationale: The unwanted sibling of FR-B24. A half-restored folder is a set
  nobody ever had. The live set is moved aside by renames inside the data
  folder rather than deleted, so putting it back is the same renames reversed;
  the safety backup stays as the copy of last resort.
- Acceptance: Given a staged restore whose second file cannot be moved in,
  when Stellody starts, then the live set is the one from before and the
  message names the safety backup.
- Verified by: `tests/infrastructure/test_staged_restore.py::test_a_failure_part_way_is_undone`,
  `tests/ui/test_after_restore.py::test_a_failure_part_way_is_said`

### 3.6 Non-functional

**NFR-B01 A backup does not get slower unnoticed**
- Requirement: When a backup is written on the reference machine of a set
  totalling no more than 260 MB, the backup service shall finish within
  5 seconds.
- Rationale: A regression guard, not a promise to every listener. The
  reference machine is Oliver's, with a solid-state disk; a spinning disk or
  an older processor will take longer by an amount nobody has measured, which
  is why FR-B13, FR-B35 and FR-B36 hold whatever the duration. 260 MB is ten
  times the measured set (A-03); linear scaling gives about 3 seconds there.
  Zipping took 0.26 of the measured 0.30 s, so the bound mostly guards
  processor work.
- Verified by: a timed run on the reference machine over a copy of Oliver's
  real library, padded to the bound.

**NFR-B02 Coverage**
- Requirement: The backup and restore service (`application/backing_up.py`)
  and the backup rules (`domain/backups.py`: naming, schema ranges, judging
  and upgrading) shall be held at 100 percent branch coverage by the gated
  suite. The infrastructure modules (`backup_file.py`, `staged_restore.py`,
  `database_schema.py`) lie outside the layers the gate measures; their
  behaviour is held by the tests each requirement names.
- Verified by: the coverage gate (`pyproject.toml`, `--cov-fail-under=100`
  over `stellody.domain` and `stellody.application`).

### 3.7 Data

**DATA-B01 The backed-up set**

| File | Owner | Why it is carried |
|---|---|---|
| `library.sqlite3` | `store.py` | The library, edits, overrides, listening, settings, taste profiles |
| `catalogue-memory.json` | `catalogue_memory.py` | What the catalogues already said |
| `catalogue-memory.record` | `catalogue_memory.py` | Answers since the file was last written (2.4) |
| `discovered.json` | `discovery_file.py` | The last discovery answer |
| `candidate-genres-2.json` | `discovery_file.py` | What was learned about candidates |
| `candidate-genres-2.record` | `discovery_file.py` | Answers since the cache was last written (2.4) |
| `shops.json` | `shop_file.py` | The shop list as edited |

A journal carries a schema number of its own, derived from its own list of
upgrade steps (`JOURNAL_UPGRADES`, `CACHE_JOURNAL_UPGRADES`) rather than from
its file's. A cache whose name carries a rule's number, such as
`candidate-genres-2.json`, takes a new file name when that rule changes: an older backup
holding the old name carries a file this Stellody does not list, which a
restore leaves out rather than refusing.

## Appendix A: Open questions register

There are no open questions.

## Appendix B: Priorities

- **Must:** FR-B01 to FR-B38, NFR-B01, NFR-B02.
- **Won't this time:** everything in the out-of-scope list in 1.3, plus a
  schema-bump guard over the JSON owners (FR-B18 says why).
