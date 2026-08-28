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
| `shared` | Version, paths and resource resolution. | The standard library. |

`main.py` is the only composition root. Dependencies are supplied by
constructor injection; there is no container and no service locator.

## The central abstraction

**A track is a slice of a file, not a file.**

```python
TrackSource(path, start_frame, end_frame)
```

A normal track is `TrackSource("07 Venus.flac")`. A cue-sheet track is
`TrackSource("album.flac", 18_432_000, 32_532_000)`.

171 of the 510 albums in the reference library are a single FLAC with a sidecar
cue sheet, so this is a main path rather than an edge case. Because the
distinction is captured in one value object, the queue, the progress bar, the
album grid, shuffle and gapless playback are all written once and work for both
shapes without knowing which they hold.

## Resolving damaged metadata

Tags are primary. Folder layout is a fallback hint, not a source of truth.

Where two tracks in one album claim the same disc and track number, the leading
number in the file name is the tiebreaker, because in every observed case of tag
damage the file names remained correct and distinct. Where the colliding tracks
also share a title, the title comes from the file name too.

Every such fallback is recorded as a `LibraryIssue` and surfaced in a read-only
health view, so the user gets a precise list of what to repair in a tagger of
their own choosing. `stellody/domain/ordering.py` holds the rule and
`stellody/domain/health.py` holds the reporting vocabulary.

## Design decisions

| Decision | Reason |
|---|---|
| PySide6 rather than Rust or Go | The requirement is a player that is not buggy. That comes from working where the coverage gate, the structural guards and the delivery lineage already exist. |
| `soundfile` and `sounddevice` rather than `QMediaPlayer` | `QMediaPlayer` has no equalizer and cannot present a cue-sheet slice as a track. Both are v1 requirements. |
| A hand-rolled biquad cascade rather than scipy | The equalizer is pure arithmetic, so it belongs in the domain and tests without an audio device. scipy would add tens of megabytes to the packaged build for one function. |
| Artwork keyed by album identity, not by path | A rescan after a folder rename reuses the cached image instead of refetching it. |
| Missing files are flagged, never deleted | An unplugged drive, a failed restore or an interrupted scan must not destroy library metadata. |
| Artwork is read locally only | Exactly one album in the reference library lacks local art, so the network buys nothing and costs the local-first guarantee. |

## Coverage

The gate is 100% branch coverage over `stellody.domain` and
`stellody.application`: the layers reachable with no filesystem, no clock and no
audio device, where anything short of complete is a decision nobody made.

Infrastructure and UI are measured but sit outside the gate rather than dragging
it down to a number that means nothing. Infrastructure needs a real audio
device, a real library and the Windows shell.
