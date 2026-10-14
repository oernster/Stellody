# Technical debt

Internal concerns only: nothing here changes what a listener sees; anything
that would belongs in `PLAN.md`. A numbered heading is an open item; a resolved
item is deleted. The invariants are in `ARCHITECTURE.md`.

## 1. The listener's own data shares a file with the scan cache

Ratings and play counts (the `listening` table in `infrastructure/store.py`),
accepted corrections (`infrastructure/override_rows.py`) and album edits
(`infrastructure/album_edit_rows.py`) live in `library.sqlite3` beside the scan
index a rescan rebuilds. A file too damaged to open is set aside whole by
`infrastructure/opening.py`, so nothing is lost; the application then starts
without that data until a backup is restored.

The fix is a file of its own for that data. That is a migration of user data
whose format and location are a decision rather than a refactor: blocked on
Oliver deciding both.

## Looks like debt, not worth touching

**`_drive` in `ui/playing.py` catches `OSError`, `RuntimeError` and
`ValueError` rather than `PlaybackError` alone.** An exception raised inside a
Qt slot ends the slot in silence, leaving the buttons showing a state that is
no longer true. The breadth catches the failures nobody predicted, which is
what it exists for.

**`AUDIO_SUFFIXES` and `UNPLAYABLE_SUFFIXES` in the walker are two sets.**
What can be decoded and what is known but unplayable are different facts;
inferring the second from absence in the first would make a stray text file
read as a missing album.

## Not debt (do not "fix" these)

**Infrastructure and the interface sit outside the coverage gate.** The reason
is under Coverage in `TESTING.md`.

**The build scripts are exempt from the line cap.** `BUILD_SCRIPTS` in
`tests/structural/test_loc.py` names them: linear recipes where splitting a
sequence of flags across modules costs more than it buys. A name on that list
the walk no longer finds fails the suite.

**Quitting during a cover lookup can leave without unwinding.** A search inside
a network read gives up within one read slice (`SLICE_S` in
`infrastructure/cover_search.py`), which the quit wait (`WAIT_MS` in
`ui/cover_worker.py`) outlasts, so `leave_at_once` in `composition.py` should
never be reached. It stays for a socket that never comes back, where Qt
would otherwise abort over a running thread. The store is closed and the claim
released before it is reached.

**`installer/` imports `stellody.shared`, `stellody.ui` and
`stellody.infrastructure`.** The setup program is a client of the application;
nothing under `stellody/` imports back (invariant 14).
