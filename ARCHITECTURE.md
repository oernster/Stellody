# Architecture

## Invariants

Each invariant names the test that enforces it. Every one of these guards has
been verified by planting a violation and reading the exit code; a guard that
has never been seen to fail is not yet a guard.

| # | Invariant | Enforced by |
|---|---|---|
| 1 | Stellody never writes tags back into a music file. The mutagen write surface is unreachable from any module that can read tags. | `tests/structural/test_readonly.py::test_tag_writing_is_unreachable_from_every_tag_reading_module` |
| 2 | Only the modules that own Stellody's own state may write to disk. Nothing in the scanning or probing path writes at all. | `tests/structural/test_readonly.py::test_only_state_owning_modules_write_to_disk` |
| 3 | Layers never import upward. UI and Infrastructure both depend inward, never on each other. | `tests/structural/test_layers.py::test_layers_never_import_upward` |
| 4 | No Qt, no tag library and no audio library appears below the infrastructure layer. | `tests/structural/test_layers.py::test_domain_and_application_are_framework_free` |
| 5 | The domain layer touches no filesystem, no network and no scheduler. | `tests/structural/test_layers.py::test_domain_has_no_side_effects` |
| 6 | Time enters the domain as an argument, never by being looked up. | `tests/structural/test_layers.py::test_domain_never_reads_the_clock` |
| 7 | No module exceeds 400 lines. | `tests/structural/test_loc.py::test_no_module_exceeds_the_line_cap` |
| 8 | No module sits in the 381 to 400 danger band; a file that reaches it is reduced to 350 or below rather than shaved. | `tests/structural/test_loc.py::test_no_module_sits_in_the_danger_band` |
| 9 | Formatting and linting are current, as assertions rather than as a remembered step. | `tests/structural/test_style.py` |
| 10 | A ring belongs to a control. No container is named as a ring target, no item view wears one in any state, no pane reaches the window's focus chain. | `tests/ui/test_focus_rings.py` |
| 11 | A read-only page is never focused by a click; it is a stop only while it overflows. | `tests/ui/test_reading_panes.py` |

Invariants 1 and 2 are the reason this project exists. The library that
Stellody was built for was damaged by a player that wrote tags back into the
files, duplicating and overwriting metadata across 21 albums. Stellody
describes a damaged tag; it never repairs one.

## Layers

```
UI  ->  Application  ->  Domain  <-  Infrastructure
```

| Layer | Contains | May import |
|---|---|---|
| `domain` | Values and rules. Frozen dataclasses, pure functions. | The standard library, minus anything with a side effect. |
| `application` | Ports as Protocols, plus use cases. | `domain` and the standard library. |
| `infrastructure` | SQLite, mutagen, soundfile, sounddevice, the filesystem. | `domain` and `application`. |
| `ui` | PySide6 widgets, models, dialogs and theme tokens. | `domain` and `application`. |
| `shared` | Identity: the name, the version read from `VERSION`, the copyright and the donation address, plus asset resolution and the start-hidden flag. | The standard library. |

`stellody/composition.py` is the only composition root; `main.py` is a
thin entry point that only calls into it. Dependencies are supplied by
constructor injection; there is no container and no service locator.

## The setup program

`installer/` is a second PySide6 application in the same repository, compiled
by `buildinstaller.py` around the payload `buildexe.py` produces. It is a
client of Stellody rather than a layer of it: it reads the identity, the theme
and the licence viewer out of `stellody.shared` and `stellody.ui`, while
nothing under `stellody/` imports it back. The line cap applies to it exactly
as to the package.

One reading of the machine picks the route. `installer/route.py` compares the
version the Apps list records against the one being installed and returns
install, update, downgrade, manage or uninstall; manage is where an install
already at this version is offered repair or reinstall. `installer/actions.py`
and `installer/registry.py` own everything written, which is per user
throughout: the files under `%LOCALAPPDATA%\Programs`, the uninstall record and
the sign-in entry under `HKCU`, so Windows never asks for administrator rights.
`installer/performing.py` drives them a step at a time and reports how it went,
owning the sequence rather than the writing. `installer/screens.py`,
`installer/shell.py`,
`installer/wording.py` and `installer/theme.py` hold the interface, one screen
to a step. `tests/installer/` covers it.

**Setup never opens the library database.** It runs at the one moment that file
is least safe to touch, having just ended the application by force, so where a
fresh install has to clear the switches it leaves a marker file for the
application to act on instead. `stellody/infrastructure/switch_reset.py` is
both halves of that handover.

## The central abstraction

**A track is a slice of a file, not a file.**

```python
TrackSource(path, start_frame, end_frame)
```

A normal track is `TrackSource("07 Venus.flac")`. A cue-sheet track is
`TrackSource("album.flac", 18_432_000, 32_532_000)`.

163 of the 485 albums in the reference library are built from a cue sheet
rather than one file per track, 157 of them a single FLAC holding the whole
album, so this is a main path rather than an edge case. Because the
distinction is captured in one value object, the queue, the transport and
shuffle are written once and work for both shapes without knowing which they
hold. The amplitude monitor inherits the same property: a shape is measured
for the file, then each track takes its own share of it. The displays still to
be built, the cover grid among them, inherit it too.

## Grouping: folders group, tags name

**A folder is one album.** Sibling folders whose names differ only by a disc
marker, `CD1` and `CD2` or `(Disc 1)` and `(Disc 2)`, merge into one multi-disc
album. The tags then supply that album's title, artist, date and genre, each
taken as the most common value its tracks carry.

Grouping by tags was tried first and measured against the reference library. It
failed: classical rips frequently carry the composer in the `ALBUM` tag and a
different `DATE` on every track, which fragmented one Mozart folder into five
albums, two of them holding a single track. A folder boundary is what a ripper
actually records, so that is what is trusted.

## Resolving damaged metadata

Tags name things. They do not decide structure; where they contradict
something physical the physical thing wins. Three rules, each measured against
real damage in the reference library:

| Conflict | Winner | Why |
|---|---|---|
| Two tracks in one album claim the same disc and track number | The leading number in the file name | In every observed case of tag damage the file names stayed correct and distinct |
| A track's `DISCNUMBER` disagrees with a folder named `(Disc 2)` | The folder | One such folder holds tags claiming discs 1, 2 and 3; the folder name was written by a person, the tag by software |
| A colliding track's title duplicates another's | The file name | A bulk tag overwrite copies the title along with the number |

Every fallback is recorded as a `LibraryIssue` and surfaced in a health
view, so the user gets a precise list of what to repair in a tagger of their
own choosing. That view is read-only today: it carries a repair control, drawn
and disabled, because the corrections are computed on every load but there is
nowhere yet to keep one that has been accepted. `PLAN.md` milestone 13 is that
work. `stellody/domain/ordering.py` holds the track rules,
`stellody/domain/grouping.py` the album rules and `stellody/domain/health.py`
the reporting vocabulary.

## Scanning

The walker lists folders, the probe reads tags out of one file and the store
caches a whole folder's result. A rescan compares each file's size and
modification time against the store; a folder whose files are all unchanged is
reused without opening a single file. On the reference library a cold scan of
510 folders and 4,870 files takes about two and a half seconds and a rescan
about a third of a second, grouping into 485 albums of 6,877 tracks.

**The store holds raw tag values, not resolved ones.** Resolution happens on
load, so improving any rule above takes effect on the next start without
rescanning a library.

**What the walker skips is named, never guessed.** An earlier version treated a
leading dot as "hidden" and silently swallowed two real albums, `...And Justice
for All` and `...Nothing Like The Sun`. It now skips a fixed list of system
directories plus macOS AppleDouble stubs; nothing else.

## Design decisions

| Decision | Reason |
|---|---|
| PySide6 rather than Rust or Go | The requirement is a player that is not buggy. That comes from working where the coverage gate, the structural guards and the delivery lineage already exist. |
| `soundfile` and `sounddevice` rather than `QMediaPlayer` | `QMediaPlayer` cannot present a cue-sheet slice as a track, which is a main path here; it also has no equalizer for the one planned below. |
| Missing files are flagged, never deleted | An unplugged drive, a failed restore or an interrupted scan must not destroy library metadata. |
| The claim to being the running copy is separate from the channel that reaches it | Asking a listener whether it is there answers "is one running" only once that listener is accepting, which is a race at the exact moment it matters. Ownership is a shared memory claim taken under a semaphore; the channel only carries activation. |
| The ask carries a word rather than being the connection itself | Any process on the machine may open a named pipe, so a connection alone is not evidence that a Stellody wants showing. The word is read before the window moves. |
| Ending the application is said out loud, never left to Qt | Quitting when the last window closes is off, which is what lets the cross leave Stellody in the notification area. Nothing then ends the event loop by itself, so every path that means to leave says so. |
| A file's shape is measured once and shared by its tracks | A cue-sheet album is one file holding many tracks, so measuring per track would decode the same file once for every track cut from it. `stellody/application/shapes.py` slices one measurement; the record is keyed by a digest of the file's path rather than by the path itself, since a music folder's names are arbitrary where a filesystem's are not. |
| Peaks are rounded where they are measured, not on the way to the record | A measurement differing from its own record by a rounding would redraw slightly differently after a restart, for no reason anybody could see. Four places also holds a record to roughly a third of the size, measured at 13.6 against 34.1 kilobytes. |
| The application keeps an account of its own appearances | A window arriving unbidden cannot be traced after the fact: whatever caused it has finished. `stellody/infrastructure/diary.py` records every show with the frames that led to it, every restore with the door that opened, then each step of a shutdown. It found two faults that reading the source had not. |

### Decided but not built

**None of the following runs today.** They are recorded so the decision is not
taken twice; `PLAN.md` holds the work itself.

| Decision | Reason |
|---|---|
| A hand-rolled biquad cascade rather than scipy | The equalizer will be pure arithmetic, so it belongs in the domain and tests without an audio device. scipy would add tens of megabytes to the packaged build for one function. |
| Artwork keyed by album identity, not by path | A rescan after a folder rename will reuse the cached image instead of reading it again. The scan already records where each folder's art sits; nothing loads it yet. |
| Artwork is read locally only | Exactly one album in the reference library lacks local art, so the network buys nothing and costs the local-first guarantee. |

## Coverage

The gate is 100% branch coverage over `stellody.domain` and
`stellody.application`: the layers reachable with no filesystem, no clock and no
audio device, where anything short of complete is a decision nobody made.

Infrastructure and UI are measured but sit outside the gate rather than dragging
it down to a number that means nothing. Infrastructure needs a real audio
device, a real library and the Windows shell.

**No test may start the application.** Four tests once stood in for the install
but not for the launch that follows it, so every run of the suite started the
copy of Stellody installed on the machine, on the owner's own desktop, while a
window arriving unbidden was being hunted. `tests/conftest.py` refuses to start
anything named like the application, whatever a test believes it has stood in
for. It also points the diary at a temporary directory, so a run cannot write
into the account of real ones.
