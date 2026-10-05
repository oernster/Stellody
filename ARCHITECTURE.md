# Architecture

This file holds the rules the structure keeps and why it is shaped as it is.
Requirements live in their specifications (`DISCOVERY.md`, `SHOPS.md`,
`OUTPUTS.md`, `FORMATS.md`); product trade-offs live in
`DECISIONS-TRADEOFFS.md`; each module's docstring holds its detail. Where a
constant governs behaviour it is named here rather than quoted, so its value
has one home.

## Invariants

Each invariant names the test that enforces it. Every one of these guards has
been verified by planting a violation and reading the exit code; a guard that
has never been seen to fail is not yet a guard. How to run these tests and
write new ones is in [`TESTING.md`](TESTING.md).

| # | Invariant | Enforced by |
|---|---|---|
| 1 | Stellody never writes tags back into a music file. The mutagen write surface is unreachable from any module that can read tags. What the test checks: every module importing a tag library (mutagen, soundfile, taglib or PyAV) is scanned for a call to a method named `save`, `delete`, `add_tags` or `add_picture`. | `tests/structural/test_readonly.py::test_tag_writing_is_unreachable_from_every_tag_reading_module` |
| 2 | Only the modules that own Stellody's own state may write to disk. No module on the scanning or probing path writes; what a scan learns is written through the store that owns that state. What the test checks: outside the permitted modules it refuses a fixed set of write call shapes, namely `open` with a literal write mode, named `os` and `shutil` calls spelled `module.function(...)` plus path methods such as `write_text` and `unlink`; a write spelled another way is not seen. | `tests/structural/test_readonly.py::test_only_state_owning_modules_write_to_disk` |
| 3 | Layers never import upward. UI and Infrastructure both depend inward, never on each other. | `tests/structural/test_layers.py::test_layers_never_import_upward` |
| 4 | No Qt, no tag library and no audio library appears below the infrastructure layer. | `tests/structural/test_layers.py::test_domain_and_application_are_framework_free` |
| 5 | The domain layer touches no filesystem, no network and no scheduler. | `tests/structural/test_layers.py::test_domain_has_no_side_effects` |
| 6 | Time enters the domain as an argument, never by being looked up. | `tests/structural/test_layers.py::test_domain_never_reads_the_clock` |
| 7 | No module exceeds 400 lines: every Python file in the repository from its root, bar the build scripts named in the test and the directories `tests/structural/conftest.py` names as not ours (the virtual environment and build output among them). | `tests/structural/test_loc.py::test_no_module_exceeds_the_line_cap` |
| 8 | No module sits in the 381 to 400 danger band; a file that reaches it is reduced to 350 or below rather than shaved. | `tests/structural/test_loc.py::test_no_module_sits_in_the_danger_band` |
| 9 | Formatting and linting are current, as assertions rather than as a remembered step. | `tests/structural/test_style.py` |
| 10 | A ring belongs to a control; to every control. No container is named as a ring target, no item view wears one round itself in any state (a row may: the results list rings its current row, the cover chooser its picked tile), no text view wears one in any state either, so Tab reaching a licence, About or the guide never outlines the whole page; no pane reaches the window's focus chain; every other control that Tab can land on shows a ring, either named in the stylesheet or painted by itself, walked off the real widgets rather than off a list. A checkbox is always the ringed subclass, never Qt's own. | `tests/ui/test_focus_rings.py`, `tests/ui/test_every_stop_paints_a_ring.py`, `tests/structural/test_rings.py`, `tests/structural/test_focus_ring_selectors.py` |
| 11 | A read-only page is never focused by a click and is never what a dialog opens on; it is a stop only while it overflows. | `tests/ui/test_reading_panes.py`, `tests/ui/test_dialog_first_stop.py` |
| 12 | Exactly four modules may hold the machinery to open a connection, each named with what it is for; the cover search is reached only through its port, which the composition root alone builds. Nothing on the scanning, drawing or playback path can reach the network at all. | `tests/structural/test_offline.py` |
| 13 | No control tells a listener that what it does has not been built. Swept off the real widgets of the window and of the dialogs, rather than checked where one was reported. | `tests/ui/test_unbuilt_words.py` |
| 14 | The setup program is a client of the application, never a layer of it: `installer/` reads what it needs from `stellody`, while nothing under `stellody/` imports `installer`. | `tests/structural/test_layers.py::test_the_application_never_imports_the_setup_program` |
| 15 | The product name is written in one place, for the application and for the setup program alike. No string a reader or the operating system meets spells it out again; every other surface builds it from `APP_NAME`. | `tests/structural/test_one_name.py::test_the_product_name_is_written_in_one_place` |
| 16 | No file the repository ships or writes carries a dash-like character; the hyphen-minus is the one allowed. | `tests/structural/test_no_dashes.py::test_no_file_carries_a_dash_like_character` |
| 17 | The user agent the discovery fetcher sends is built from the product name, the version and one fixed contact address alone; the fetcher sets that one header from that constant. | `tests/structural/test_user_agent.py` |
| 18 | Everything discovery keeps is written under Stellody's own data directory, each place named through `paths.py`. | `tests/structural/test_discovery_paths.py` |
| 19 | No test holds the machinery to reach the network, except the named few that open nothing beyond this machine. | `tests/structural/test_offline.py::test_no_test_holds_the_machinery_to_reach_the_network` |
| 20 | Every runtime pin in `requirements.txt` is the version installed in the environment the suite runs in. | `tests/structural/test_environment.py` |
| 21 | No audio file of a format proved by a generated fixture sits in the tree. | `tests/structural/test_no_committed_audio.py` |
| 22 | Halving is stated once: `HALF` is defined in `stellody/ui/theme.py` and in no other module of the package or of the suite. | `tests/structural/test_half_has_one_home.py::test_half_is_defined_only_in_the_theme` |

**Invariants 1 and 2 are the reason this project exists.** The library
Stellody was built for was damaged by a player that wrote tags back into the
files. Stellody describes a damaged tag; it never repairs one.

**Invariant 12 holds local-first as a test rather than a promise.** The four
permitted modules are `stellody/infrastructure/cover_search.py` (reached when
somebody asks for a cover), `update_source.py` (asks GitHub whether a newer
Stellody is published), `fetching.py` (the one module a discovery run and an
expansion ask both catalogues through) and `instance.py` (the channel a second
launch uses to show the running copy: a named pipe or a local socket file,
never a way off the machine). The composition root builds all four. The
catalogue clients `catalogue.py`, `catalogue_series.py` and `similarity.py`
hold no socket: each is handed the fetcher. The cover search is held to its
port by `test_the_search_is_reached_only_through_its_port`. Dotted imports are
matched in full, since every window imports `PySide6` while only
`PySide6.QtNetwork` reaches out. The count is the point: adding a fifth module
is an edit somebody has to make and defend.

**The update check is the one that speaks unasked, so what it sends is
fixed:** a fixed URL, an Accept header naming GitHub's JSON media type and a
user agent that is the product name alone. The agent is stated because
urllib's default would name the machine's Python. Held by
`tests/infrastructure/test_update_source.py`.

**Invariant 13 is swept rather than spot-checked**, because a feature enabled
without its tooltip being reworded is two edits of which one gets made.
**Invariant 15** exists because copies of the name agree until one is edited;
comments and docstrings are prose about a module, so the guard leaves them
alone. **Invariant 14** gives the setup program's direction a test rather than
a claim.

## Layers

```
UI  ->  Application  ->  Domain  <-  Infrastructure
```

| Layer | Contains | May import |
|---|---|---|
| `domain` | Values and rules. Frozen dataclasses, pure functions. | The standard library, minus anything with a side effect. |
| `application` | Ports as Protocols, plus use cases. | `domain` and the standard library. |
| `infrastructure` | SQLite, mutagen, soundfile, PyAV, sounddevice and the host API chosen from it, Qt Multimedia's list of output devices, Windows' own audio endpoint enumeration over COM, Qt's image codecs, Qt's network stack, the filesystem. | `domain`, `application` and `shared`. |
| `ui` | PySide6 widgets, models, dialogs, the colour tokens in `palette.py` and the stylesheet built from them in `theme.py`. | `domain`, `application` and `shared`. |
| `shared` | Identity: the name, the version read from `VERSION`, the copyright and the donation address, plus asset resolution and the start-hidden flag. | The standard library. |

`stellody/composition.py` is the only composition root; `main.py` is a thin
entry point that only calls into it. Dependencies are supplied by constructor
injection; there is no container and no service locator.

## The setup program

`installer/` is a second PySide6 application in the same repository, compiled
by `buildinstaller.py` around the payload `buildexe.py` produces. It reads the
identity, the theme, the licence viewer and what it needs from
`stellody.infrastructure`; invariant 14 holds that direction and the line cap
applies to it as to the package.

- `installer/route.py` reads the machine once and picks the route: install,
  update, downgrade, manage (repair or reinstall at the same version) or
  uninstall.
- `installer/actions.py` and `installer/registry.py` own everything written,
  all per user (`%LOCALAPPDATA%\Programs`, the uninstall record and sign-in
  entry under `HKCU`), so Windows never asks for administrator rights.
  `installer/steplog.py` owns setup's own log; `installer/performing.py` owns
  the sequence rather than the writing.
- `installer/app.py` assembles the interface from `screens.py`, `shell.py`,
  `footer.py`, `wording.py`, `theme.py` and `appearance.py`, one screen to a
  step. `tests/installer/` covers it.

**Setup never opens the library database.** It runs just after ending the
application by force, the moment that file is least safe to touch, so it
leaves notes for the application to act on instead:
`stellody/infrastructure/switch_reset.py` (clear the switches on a fresh
install) and `stellody/infrastructure/window_reset.py` (open maximised on the
screen setup was on, after an install, repair or reinstall). The composition
root takes the window note, forgets the remembered size through
`forget_window` and lays the window on that screen through `open_on` in
`stellody/ui/geometry.py` before it is shown. An update or downgrade leaves no
note, so the last size comes back.

## The central abstraction

**A track is a slice of a file, not a file.**

```python
TrackSource(path, start_frame, end_frame)
```

A normal track is `TrackSource("07 Venus.flac")`; a cue-sheet track is
`TrackSource("album.flac", 18_432_000, 32_532_000)`. Cue albums are a main path
in the reference library, not an edge case. Because the distinction is one
value object, the queue, the transport, shuffle, the amplitude monitor, the
grid and the album pane are written once and never ask which shape they hold.

**Two readers satisfy it; nothing above them can tell which.** `AudioSource`
in `stellody/infrastructure/decode.py` is the shape both answer to;
`open_source` chooses by suffix and is the only place that knows there are
two. `SourceReader` covers everything libsndfile addresses by frame.
`PacketReader` (`packet_decode.py`) covers `PACKET_SUFFIXES`, which arrive as
timestamped packets; it counts them back into frame positions so cue slices,
the equalizer, the visualiser and gapless need no change. Three traps in it
are commented where they are handled: timestamps do not start at nought
(encoder priming); a seek needs pre-roll; the container is reopened on
every seek because a used decoder does not come back clean.

**The picture is a separate stream that follows the sound.**
`stellody/infrastructure/video.py` keeps no clock: it asks what moment the
transport has reached and hands back the frame due then, so the two streams
cannot drift. It crosses the boundary as `domain/picture.py` (packed RGB, the
one arrangement both sides can state); `application/pictures.py` holds one
open for the track in hand; `ui/picturing.py` shows it in the library's own
area so closing it returns the listener where they were.

**PyAV is imported only once a track needs it**, inside `open_source` and
inside `VideoReader`, since it loads a large shared FFmpeg build. The other
deferred imports are platform choices: `output.py` reaches `wasapi` and
`coreaudio`, `output_list.py` reaches `endpoints`, while
`stellody/__init__.py` defers the composition root into `main`.

## Grouping: folders group, tags name and join

**A folder is where an album starts, not where it ends.** Sibling folders
differing only by a disc marker merge into one multi-disc album. Folders
anywhere whose most common album and album artist tags agree are then folded
into one album by `fold_by_tags` in `stellody/domain/folding.py`, since a
library may keep an album's audio and its bonus videos apart. The date is left
out of that comparison (audio and videos disagree about it); a folder naming
no album or no album artist is never folded. The tags then supply title,
artist, date and genre as the most common value among the tracks.

Grouping by tags alone was tried and fragmented classical rips, which carry
the composer in `ALBUM` and a different `DATE` per track. A folder boundary is
what a ripper actually records, so it is trusted; folding never splits a
folder, it only joins folders that agree.

## Resolving damaged metadata

Tags name things; they do not decide structure. Where they contradict
something physical, the physical thing wins:

| Conflict | Winner | Why |
|---|---|---|
| Two tracks in one album claim the same disc and track number | The leading number in the file name | In observed tag damage the file names stayed correct and distinct |
| A track's `DISCNUMBER` disagrees with a folder named `(Disc 2)` | The folder | The folder name was written by a person, the tag by software |
| A colliding track's title duplicates another's | The file name | A bulk tag overwrite copies the title along with the number |

Every fallback is recorded as a `LibraryIssue` and surfaced in the health view
so the listener can repair it in a tagger of their choosing. That view
reports; a second screen accepts (below). Its two repair controls share one
tooltip (stated in `stellody/ui/bottom_tray.py`) plus one answer to whether they
can act, `can_repair`; both are disabled while there is nothing to accept or
take back.

**A file is reported once for its track number, however many rules touched
it.** `resolve_tracks` reports a missing number only where the tags carried
none; `Repairs.pins_for` keeps one pin per album, file and field, so `accept`
counts files. Held by
`tests/domain/test_health_and_ordering.py::test_a_colliding_file_with_no_ordinal_is_reported_once`
and
`tests/application/test_repairs.py::TestAcceptingAndResetting::test_two_findings_naming_one_file_for_one_field_pin_it_once`.

`stellody/domain/ordering.py` holds the track rules, `grouping.py` the album
rules, `folding.py` the folding rule and `health.py` the reporting vocabulary.

## Accepting a correction

**Resolution has three layers: raw tags, the automatic rules, then what has
been accepted.** The store holds raw tags and resolves on load.
`stellody/domain/overrides.py` records what was accepted and
`assemble_albums` applies it, so a load and a scan get it from one place.

**What is pinned is the value the rule proposed**, so accepting moves nothing
on screen: the finding stops being reported and the value stops depending on
the rule. The domain also applies a different value; the tag editor records
one through the same table.

**An override is keyed by the album's identity handle plus a source
address.** `AlbumIdentity.handle` survives a folder rename or re-rip, which is
why artwork and ratings use it too. The address names the one source a
track-level pin is about, so two files folded into one album are never
confused. A track-level pin reverts to the automatic value when its folder
moves.

**Two albums that resolve alike are one album; that is a stated price.** Tags
cannot separate two recordings of one work; folders naming the same album
and album artist fold together for the reason
[Grouping](#grouping-folders-group-tags-name-and-join) gives. They share a
cover, an album rating and accepted corrections.
`tests/domain/test_identity_collisions.py` holds that cost so whoever reverses
it sees what they buy back. Telling apart by place survives only where albums
collide without folding: `_named_apart` in `stellody/domain/grouping.py`
appends the place to what the handle is digested from, so an album nothing
collides with digests exactly as before. A test pins that digest to its
literal value, since a refactor moving it would silently empty every
library's ratings.

**A lossy copy of an album already held lossless is not a second recording.**
`stellody/domain/duplicates.py` drops a lossy file only where a lossless file
in the same album claims the same disc and track number AND runs the same
length within `SAME_RECORDING_MS`. The length is the evidence: a number alone
cannot tell a copy from a live take at the same number; dropping a file is
the one irreversible thing the rule does. A missing disc number reads as the
first disc, since one rip may state a disc where the other states none. Lossy
and lossless are told apart by a stated bit depth, not a suffix list. The
lossless album keeps its handle; `TestWhatMustNotChange` in
`tests/domain/test_lossy_duplicates.py` holds what must not move.

**A finding is silenced only where the whole of it is pinned.** A kind that
proposes no value is absent from `FIELD_FOR_KIND`; that absence is the
rule.

**A finding names the sources it is about, not the names it shows.**
`LibraryIssue.paths` holds display names; `LibraryIssue.addresses` holds what a
pin is written against. A cue track's display name is invented by the scan and
renumbering can change it, while every track of a cue album shares one path,
so neither a name nor a path can carry a pin. `TrackSource.address` is the bare
path for a whole file and `path#start_frame` for a slice; a whole file
addresses exactly as it always did, so no stored pin changed shape.
`overrides.applied` looks pins up by address; `edits_for` in
`stellody/application/editing.py` writes the tag editor's values against it
(`tests/application/test_editing_a_cue_album.py`).

**The findings and the accepted set are two lists.** An accepted finding
leaves the report, so it cannot be what is pointed at to take it back. The
screen lists the accepted set by album and field; reset takes a group, an
album or the lot; only the lot asks first, being unbounded.

**A store that cannot be read must not cost the library its assembly.** An
unknown field or an impossible pinned number is skipped rather than raised:
one unapplied correction is cheaper than a library that fails at every start.

**None of it reaches a music file.** An override is a row in Stellody's own
database; invariants 1 and 2 enforce that.

## Stating what an album is

**Accepting and stating are different acts, so they are different records.**
`Override` keeps what a rule proposed; `AlbumEdit` in
`stellody/domain/overrides.py` says what the album IS.

**A stated value is keyed by the folder, never the handle.** The handle is a
digest of artist, title and year, so an edit keyed by it would stop matching
the moment it took effect.

**Stated values are laid on before anything is folded.** `stated_over` in
`stellody/domain/entries.py` rewrites the entries, then assembly runs, so a
stated artist or title is what the album is identified and sorted by.
Consequently stating one folder's tags to match another's merges them; the
merged album takes the rating held against the joined handle.

**`AlbumField` names the stateable fields:** album artist, title, date and
genre. A stated genre is what the filter narrows on.

## Scanning

The walker lists folders, the probe reads one file's tags and the store caches
a folder's result. A folder is reused without opening a file only when every
file's size and modification time is unchanged AND its record was written
under the rules now in force: `records.DERIVATION` names those rules and
`_unchanged` requires the record to carry the same value, so a corrected
derivation rule (how a file becomes records, including cue parsing) reaches
the whole library on the next scan.

**The store holds raw tag values.** Resolution happens on load, so a corrected
resolution rule takes effect on the next start without a rescan.

**Missing files are flagged, never deleted.** An unplugged drive or
interrupted scan must not destroy library metadata. A folder whose files are
all flagged is left out until they return; `load_folders` applies the same
rule on load (`tests/infrastructure/test_a_vanished_folder_stays_gone.py`).

**A scan whose music folder is not there is refused before it touches
anything.** A disconnected root walks as no folders with no error, so the
walker answers `reachable` first and `ScanLibrary` raises
`LibraryUnreachableError`; the library on screen stays as it was
(`tests/application/test_an_unplugged_drive.py`).

**A scan and a load must assemble the same library from the same store**,
since the window compares every scan against what `LoadLibrary`
(`application/loading.py`) assembled; any difference reads as albums arriving
and leaving at every rescan. Both lay stated values on first
(`tests/application/test_a_rescan_keeps_stated_albums.py`).

**What the walker skips is named, never guessed:** a fixed list of system
directories plus macOS AppleDouble stubs. A leading dot is not "hidden", since
real album folders begin with one.

## Formats and probing

`FORMATS.md` is the specification for which formats are taken and why; this
section is how the probe is built around them.

**Five tag shapes cover every format.** FLAC and the Ogg family hand back
pairs already spelled as the resolution rules read them. ID3 (MP3, WAV, AIFF)
is translated by `ID3_NAMES`; MP4 by `MP4_NAMES` plus `MP4_PAIR_NAMES` for the
two integer pairs, rewritten as the "3/12" text other formats use; WMA by
`ASF_NAMES`, matched without regard to case and collected once per name;
WavPack's APEv2 needs no table. All in
`stellody/infrastructure/probe.py`; a frame nobody reads is left alone. An MP4
cover carries no picture type, so `covers.py` treats each as a front cover.

**What a format does not state is reported as absent, never invented.** A file
stating no bit depth reports nought; a missing frame count is derived from
length and sample rate. `OPUS_SAMPLE_RATE` records a property of the format,
since mutagen states no rate for Opus.

**Nought means unstated, which keeps bit perfect honest.** `OutputRequest` and
`Track` refuse only a negative depth; `states_depth` separates nought from a
real value. `depth_is_native` requires a stated depth, so `is_bit_perfect` is
False for any lossy source; `Track.is_high_resolution` is False wherever
no depth is stated (otherwise Opus's fixed rate would badge every Opus file).
`open_output` in `wasapi.py` and `coreaudio.py` declines exclusive mode up
front with `NO_STATED_DEPTH`, worded once in `portaudio.py`, so the reason
names the file rather than blaming the device.

**Which families are lossy is the domain's to say**: `LOSSY_FAMILIES` and
`stored_depth` in `stellody/domain/formats.py`. The rule believes a stated
depth unless the family is named, so a lossless format nobody listed never
loses bit perfect in silence. `_bit_depth` in the probe honours an MP4 depth
only for ALAC, because the MP4 sample entry states a depth for AAC too; a test
pins that mutagen still does so.

**A date tag is read for its year, never sliced.** `year_of` in
`stellody/domain/text.py` is the one place that decides; the tag itself is
kept as written.

**`tests/infrastructure/test_scanning_formats.py` scans real files of every
format end to end** through the real walker, probe and store and back out of a
reopened store. Unit tests of the probe and of the domain once passed while
disagreeing about nought, leaving rows a load could not assemble; only an end
to end scan catches that shape.

**What the walk takes is `AUDIO_SUFFIXES` united with `PICTURE_SUFFIXES`**
(`PLAYABLE_SUFFIXES`). Whether a suffix carries a picture is the domain's
(`stellody/domain/track.py`, `TrackSource.carries_picture`), so a bonus video
is walked, probed and assembled as a song is. The formats proved only by a
generated fixture are encoded at test time by
`tests/infrastructure/widened_support.py`; invariant 21 keeps their audio out
of the tree.

**Nothing is silently absent.** `UNPLAYABLE_SUFFIXES` names audio this build
recognises and will not play. A folder holding only those raises ONE finding
naming the count and formats (one per folder, not per file, so the report
stays readable). The list is named rather than inferred, since a stray text
file is not a missing album. The finding proposes no value, so it can never be
accepted; unplayable files are left out of a folder's signatures, so such a
folder is reused rather than re-listed.

## What a scan reports

**A scan answers the question it was pressed to answer.** The status bar keeps
its one-line total; a finished scan also opens a report naming what arrived.

**What changed is a domain rule.** `stellody/domain/changes.py` compares two
readings; `stellody/ui/scan_summary.py` shows the page. Gone albums are
reported beside new ones, since a retag reads as one leaving and another
arriving. A track is counted by its source (slice included), which survives a
retag.

**Every count is named for what it counts:** `files_in_library` sits under
the library's heading; `folders_checked` and the folders re-read sit under
what the scan did.

**The window compares what it was showing** rather than asking the store
again. The runner tears its thread down before emitting, so a modal opened
from the handler has nothing waiting behind it.

**The report is measured rather than given a size**, on a detached
`QTextDocument`, because the view's own document has its width reset by the
widget. Two traps are not to be re-attempted: `idealWidth()` returns the set
width, so a second narrowing pass narrows nothing; releasing the height clamp
after measuring lets the page grow back, so the clamp stays. The view is made
wider than the text by its own frame (asked of the style), since the viewport
is what wraps.

**Qt rich text is not a browser:** no `opacity`; an entity dash renders as
a real dash, so neither appears. Held by
`tests/ui/test_scan_summary.py::test_the_report_carries_no_dash_and_no_styling_qt_would_drop`.

**A modal report hangs a test that completes a scan**, so
`tests/ui/test_launch.py` patches `ScanSummaryDialog.exec`; any later test that
runs a scan to its end must do the same.

## Searching

**No index.** A pass over the whole library costs a fraction of a keystroke
once text is normalised. An index would also hold the wrong text (the store
keeps raw tags while the library shows resolved ones) and would be empty for
any folder a rescan reused. SQLite's FTS5 is deliberately unused.

Normalising is the costly part and cannot change between keystrokes, so
`show_library` in `stellody/ui/searching.py` does it once per load or scan.
`stellody/domain/searching.py` is the pure filter.

**An album is kept whole.** A hit is selected as though about to play and its
row flashed, rather than the album shortened. Return asks the same phrase
again, so somebody who moved off it can get back.

**A keystroke replaces every row (a model reset)**, as do inverting the order
and rescanning. Consequences: the pane under the sleeves must be reopened
rather than left alone, else it re-roots on the invisible root; Qt never asks a
selected row for `BackgroundRole`, so the delegate in `stellody/ui/covering.py`
paints the flash brush itself (each appearance carries its own flash colour,
since the writing is never repainted); `scrollTo` is what opens every level
above a row, which a multi-disc album needs.

## The genre catalogue and the filter

**A settled list, not the library's own strings.** The catalogue in
`stellody/domain/genres.py` is a fixed set of mains, some carrying styles,
alphabetical. Spellings follow Discogs so names are familiar and tags from
other tools can match; the hierarchy is ruled here where Discogs read wrong
against this library. `DISCOVERY.md` holds the requirements behind it. A value
stored before a split of the catalogue still reads as written.

**The grid's categories fold.** `stellody/ui/genre_grid.py` deals mains into
columns; each is a `GenreGroup` (`genre_group.py`) whose arrow is made before
its box, so the focus chain reaches the arrow first and a folded style is off
the ring because it is hidden. A main with no styles keeps the arrow's room so
boxes align. What is open is kept per dialog by `Folds` (`genre_folds.py`)
under the `SETTING_GENRES_OPEN_*` keys in `settings_keys.py`. After a fold
`_keep_folds` invalidates every layout from the group up and then adjusts the
dialog's size; either step alone leaves the open height. Held by
`tests/ui/test_genre_folding.py`.

**The alias table is where rulings live.** `ALIASES` in
`stellody/domain/genre_rulings.py` (re-exported as `genres.ALIASES`) maps
spellings found in tags and in MusicBrainz onto catalogue entries, read by
`MAIN_OF` and `chosen_in`. No key is a catalogue name, so a name always means
itself
(`tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_no_alias_is_keyed_on_a_catalogue_name`).
It grows by somebody making a decision, not by pattern.

**What MusicBrainz states is weighed before it is read.** `believed` in
`stellody/domain/genre_votes.py` drops a genre under `FEWEST_VOTES` unless none
reaches it, then drops one with under half the leading genre's votes
(`LEADING_SHARE`), so stray crowd tags do not file an artist under a genre.
`_genres` in `infrastructure/catalogue.py` applies it to every genre list;
`tests/domain/test_genre_votes.py` holds it. The candidate genre cache file is
renamed whenever the rule changes, so each candidate is asked again.

**The filter is pure and takes a field, not a genre.** `Narrowing` and
`narrowed_to` live in `stellody/domain/narrowing.py`; other fields arrive by
being passed rather than by the module learning about them.

**Any, not all** (Oliver's ruling): an album is kept when it carries any
ticked value, so each tick widens. **A style is not its main in the ask**:
`chosen_in` already reports a style's main, so ticking a style means that
style alone. **"Not stated" is a box** so untagged and unrecognised albums are
reachable. **The filter runs before the phrase**; the two compose because
neither knows about the other.

## Ratings and play counts

**Neither is attached to an object or a path.** A scan rebuilds every object
and a rename destroys a path. A track's handle is the album identity with the
disc and track number under it, digested; `stellody/domain/listening.py` holds
the record and the handle.

**An album is rated apart from its tracks**, since a record with one poor
track is not a poor record. Its handle cannot collide with a track's. It is
set from the album pane's header, captioned so the two rating controls are not
confused.

**Reaching the end is what counts as a play.** Only the transport can tell an
ending from a skip, so it reports the play, handing over the album with the
track because a rescan may already have replaced the track.

**The whole log is held in memory and written through:** a drawn row costs no
query and there is no save step.

**Counts and stars are columns of their own**, `Column.PLAYS` and
`Column.STARS`, in the library list and the open album's track columns alike,
one fact to a cell so they align down a record. Cell text lives in
`stellody/ui/row_text.py`. The model is handed the log; a changed count
redraws the one row found by `find_handle` in `stellody/ui/nodes.py`. Stars are
answered under `STARS_ROLE` and drawn by the one `RowCover` delegate, so no row
carries a widget; `stellody/ui/star_cells.py` holds what a star cell means and
`stellody/ui/stars.py` holds the drawing, press rule and wording shared with
the album's rating widget. A double click on stars is consumed so rating never
starts a track; number keys rate the highlighted track and 0 clears it.
Pressing the star a rating already sits on takes it back, since nought is the
absence of a rating. Held by `tests/ui/test_star_column.py`.

**What is playing is marked in the model and named along the foot.**
`stellody/ui/playing_mark.py` holds the playing track by handle (a row number
breaks on a sort, an object on a reload), so the mark reaches both views
through the one `AlbumTreeModel` and survives a reload
(`tests/ui/test_the_mark_survives_a_reload.py`). A search flash wins while it
pulses; the mark is a pink told from the selection by hue.
`stellody/ui/now_playing.py` writes the permanent label, asked for by
`_show_transport` in `stellody/ui/playing.py`, which every command, failure and
poll passes through. A stop clears both; a pause keeps them.

## Gapless transitions

**The seam is crossed inside the engine, by the feeder thread.** At the moment
a track ends nothing else is awake, so the following source is opened while
the current one plays and the feeder reads straight on; the device gets one
unbroken run of blocks.

**The transport learns afterwards, from a count**, so a poll that missed the
moment still learns of it; the count belongs to the loaded session.
`stellody/application/following.py` holds it. What was lined up is kept, so
the queue lands where the music actually went even if the switches moved.

**A follower is lined up only where it cannot change** (a scattered album
beginning again picks its order then, so that seam stays gapped) **and only
where the open stream can carry it** (same rate and channel count); otherwise
a gap is better than the wrong track or the wrong speed.

## The equalizer

**Designing the filter and applying it are different jobs.**
`domain/equalising.py` works out coefficients and is testable without a
device; `infrastructure/filtering.py` multiplies samples. numpy is a framework,
so it cannot sit below infrastructure anyway. Hand rolled from the Audio EQ
Cookbook rather than adding scipy to the build.

**A band at nought is dropped, not applied**, as is a band at or above half
the sample rate. A flat equalizer therefore costs nothing and hands the block
back untouched, keeping an exclusive stream bit perfect.

**A lift is given room before it is applied.** Volume is applied after the
filter, so it cannot prevent clipping. `cascade` searches the combined
response for its largest lift (neighbouring lifts pile up above any one
slider) and folds that attenuation into the first section; a curve that only
cuts is left as designed. The visualiser measures after the filter, so it
shows the same reduction. Held by `tests/domain/test_equalising.py` and
`tests/infrastructure/test_filtering.py`.

**One pass over the samples, not one per band**, since the cost is indexing
rather than arithmetic.

**The curve is kept where the volume is kept**, by the engine, so a curve
chosen before anything loads still applies. It is redesigned at every load and
whenever it changes while a stream is open.

## The visualiser

**It shows what the equalizer shapes:** two bars to each of the ISO octave
bands `equalising.py` defines, split at the band's centre, so no second set of
band edges exists.

**Measuring is split from meaning.** `domain/spectrum.py` holds band edges and
what a magnitude means; `infrastructure/analysing.py` runs the transform on the
arrays the device is handed.

**It runs after the write, not before**, so it can never delay a block or
alter a sample. `tests/infrastructure/test_watching_the_output.py` compares
every frame written with the display on and off. It measures after the
equalizer and before the volume, so it shows the music rather than the knob.

**A short block is refused rather than read as silence**, leaving the last
reading to fall away. **The measurement is handed sideways:** the feeder swaps
in one whole tuple for the interface thread to take, with no lock, so the
feeder never waits on a painter. **Two clocks:** measurements land per block
while the strip repaints faster and lets the domain decide where a bar has
fallen; bars rise instantly and fall at a fixed rate.

**It has no switch.** It sits at the middle of the bottom strip, held there by
`tray_parts.centred_row`, sized in centimetres against its screen; it draws
twenty empty bars on the tray surface when silent. Its timer runs only while
music does; the feeder measures only what it has written.

## Discovering what the library does not hold

`DISCOVERY.md` and `SHOPS.md` are the specifications, each requirement naming
its test. This section is the structure they landed in; requirement numbers
point there for the detail.

**A run is staged, one bar per stage.** The artist stage asks what each artist
inside the ticked genres released and who resembles them; while series are
included a series stage follows; the styles stage asks what each suggested
artist plays so the ticks apply to them too. `STAGE_ORDER` in
`ui/discovery_progress.py` stacks the bars (FR-D83). With years set, a years
stage (`application/candidate_years.py`) follows the styles and takes over
that bar (`SHARES_BAR`), asking through the same catalogue memory an expansion
uses.

**Years scope what a run offers, never whom it asks about.** `read_years` in
`domain/release_years.py` builds a `ReleaseYears` from the dialog's two fields
(`ui/year_fields.py`), refusing rather than correcting a bad range.
`source_artists` never sees them; `albums_missing` and `everything_offered` in
`domain/discovery.py` both ask `ReleaseYears.admits`, judged on a release
group's first release date.

**Genre is what makes the reach outward acceptable.** A run asks only about
what sits inside the ticked genres, never the whole of what somebody owns;
that is the difference from a recommender, which is why the ticks scope the
ask rather than filter the answer. Exactly what goes out to MusicBrainz and
ListenBrainz is stated in `DISCOVERY.md`.

**Two services, one permitted module.** MusicBrainz has no similarity;
ListenBrainz answers in MusicBrainz identifiers, so they compose with nothing
to translate. Every catalogue client asks through `infrastructure/fetching.py`
(see [Invariants](#invariants)). `infrastructure/courtesy.py` holds the user
agent and pacing for everything reached through `cover_search.py` or
`fetching.py`; the composition root hands the run, its series client, an
expansion and the cover search one MusicBrainz gate
(`tests/ui/test_discovery_composition.py::test_everything_asking_musicbrainz_waits_at_one_gate`).

**A request in flight is killed rather than abandoned; that is why it is on
Qt.** Nothing portable interrupts a thread blocked on a socket; Qt's network
stack is event driven, so a request is asked periodically whether its answer
is still wanted. `Fetcher` keeps one `QNetworkAccessManager` per asking thread
under a lock, because a stopped run is abandoned while the next may already be
asking through the same fetcher; a manager is released when its own thread's
`finished` is heard. Held by
`tests/infrastructure/test_a_fetcher_shared_between_runs.py`.

**A stopped run is abandoned rather than waited for**, so a stop is instant;
late reports are dropped. Quitting is the one place a run is waited for:
`_leave_for_good` in `stellody/ui/leaving.py` calls the runner's `wait`
(FR-D24,
`tests/ui/test_quitting.py::test_quitting_mid_run_stops_the_discovery_run`).
The button changes its words rather than asking for confirmation; the wording
lives in `ui/tray_metrics.py`.

**The estimate is read off the run, not the configured gap**, since refusals
and retries dominate. Every bar's time is the whole run's: `Ahead` in
`application/reporting_ahead.py` stamps what lies ahead onto each report;
`looking_up_seconds_left` and `series_seconds_left` in `domain/estimating.py`
price later stages from the current pace (FR-D84); `ui/run_estimate.py` reads
pace afresh at every change of stage. Too few finished units says nothing
rather than swinging.

**Colour never carries meaning alone:** every row states its kind in words.

**A candidate's albums are fetched when somebody opens them**, not during the
run, which would add a request per surviving candidate.

**A compilation is asked about by its track credits only when ticked**
(`Including.credits`); "Various Artists" itself is never asked about.
`application/compilation_cost.py` prices the credits and series before a run,
from the same memory and pace, so the price is arithmetic. Select all sets
`_sweeping` in `ui/discovery_dialog.py` so the price is worked out once.

**A compilation's neighbours are its other volumes, so a second box asks after
the series** (FR-D69 to FR-D75, FR-D81, FR-D82):

- `domain/series.py` is the pure rule: what a title's series stem and volume
  are, which entries are held and which are missing.
- `application/series_stage.py` holds `SeriesStage`, run after the artist
  stage and before candidates are narrowed, finding placeholders and filed
  compilations from answers already in hand. The run's one `Silence` counts
  across every stage; it reports as `DiscoveryStage.SERIES`.
- `application/discovery_ports.py` holds `SeriesSource` beside
  `CatalogueSource`, with `NoSeries` as the null object;
  `infrastructure/catalogue_series.py` (`MusicBrainzSeries`) is the adapter.
- `domain/including.py` holds `Including` (credits, series, mixes; FR-D85),
  carried from the dialog through the worker to `Discovery.run` and written to
  the discovery file. `ui/discovery_choices.py` keeps the boxes;
  `application/artist_stage.py` is the artist stage;
  `infrastructure/file_shapes.py` is the one home for the files' shapes;
  `application/remembering_series.py` keeps series answers as catalogue
  answers are kept.

A series with gaps becomes a `Gaps` with `series` set, written by
`infrastructure/discovery_file.py`; `worth_showing` in
`domain/discovery_filter.py` keeps empty headings off screen. Held by
`tests/domain/test_series.py`, `tests/application/test_discovering_series.py`,
`tests/application/test_discovering_filed_compilations.py`,
`tests/infrastructure/test_series_kept.py` and
`tests/ui/test_results_series.py`.

**A DJ mix is offered; a hits package is not.** `ReleaseGroup.is_offered`
sets `MIX_KINDS` aside where DJ-mix is stated (FR-D80); `offered_with` applies
the mixes box; `Expansion.releases_of` receives the choice the run was
made with (FR-D85). Held by `tests/domain/test_discovery_gaps.py` and
`tests/application/test_expanding.py`.

**A name nobody is found under is asked about by its parts.** `credit_parts`
in `domain/text.py` splits at the joins FR-D53 lists; the whole name is always
asked first; a bare solidus is not a join. Album artists are split alike
(Oliver's ruling). `Passes.everyone` stops a part being asked twice.

**A catalogue name is matched more loosely than the library's own.**
`catalogue_key` sets aside case, accents and typographic dashes;
`catalogue_name` drops a trailing Discogs number (FR-D08). `comparison_key`
stays strict, since two shelf names being one artist is the listener's
filing. Identities are remembered under the `identities` section.

**A name several artists share is settled by what the library holds.**
`evidence_by_artist` in `domain/credit_evidence.py` indexes held titles per
name; `settled` in `application/settling.py` puts up to `MOST_EVIDENCE` of
them to the catalogue through `credited` on the `CatalogueSource` port
(FR-D09). Answers are remembered under `CREDITED`, keyed by
`Evidence.question`, so two runs settle a name alike.

**Reaching a shop opens no connection.** `infrastructure/browsing.py` hands an
address to the system's browser, so it is not in the offline guard's list. The
address is the shop's template with artist and title filled in
(`tests/domain/test_shop_address.py`).

**The shop list is data because shops move.** `shops.json` records the
shipped list beside the list in use; `stellody/domain/shop_list.py` settles
them shop by shop, recognising a shop by name ignoring case. Untouched shipped
shops follow the release, edits are kept, deletions and renames are recorded
in `deleted` so a release does not restore them, dropped shops are named in
`retired`. An unreadable file is replaced by the shipped defaults (FR-S12,
`tests/infrastructure/test_shop_file.py`). `stellody/application/shop_editing.py`
writes every change before the dialog shows it.

**Two albums match when they are the same recording, not the same pressing.**
`stellody/domain/matching.py` reduces both sides to a key plus a kind,
symmetrically (the library reads kinds from the title; the catalogue states
them), on the same `comparison_key` the search uses. The year is deliberately
absent, since a remaster's tag carries the remaster's year. `AlbumIdentity` is
untouched, its handle keying artwork and ratings.

**What a candidate plays is remembered between runs**, since the similarity
source returns no genre and asking per suggestion would multiply requests. A
remembered answer is still judged against this run's ticks. Only an answer is
remembered: any failed lookup leaves the candidate unknown
(`CandidateGenres.narrowed` in `application/candidate_genres.py`,
`tests/application/test_discovery_narrowing.py`).

**The results can be narrowed by genre, judged differently at each end**
(FR-D54 to FR-D56, FR-D78). A source artist is judged by the genres on the
listener's own albums; a candidate by its remembered genres, else by the
heading it sits under (matched per credit part through `_keys_of`).
`filtered_answer` in `domain/discovery_filter.py` is the rule
(`tests/domain/test_judged_by_their_source.py`). `ui/results_filtering.py`
re-deals the pages rather than hiding rows, holding ticks and fetched albums
across the deal; `ui/results_asking.py` holds the asking half.

**The answer is narrowed by kind as well** (FR-D86): `Showing` and `shown` in
`domain/showing.py` are the pure rule, drawn by `ui/results_filter.py`
(`tests/domain/test_showing.py`, `tests/ui/test_results_showing.py`).

**A row shows the year; a shop is asked for the title alone** (FR-D68).
`album_row` in `ui/results_words.py` writes the year; the bare title rides
under `TITLE_ROLE`, set by `make_tickable` and read by `album_on` in
`ui/results_ticks.py`.

**One shops dialog serves the results screen; closing it ends the round.**
`ui/shops_dialog.py` is reused on a second press and follows tick changes
through `follow` (FR-S44); its `finished` unticks every row (FR-S45,
`tests/ui/test_shop_closing.py`).

**The file records what was asked as well as what was found:** genres and
years beside the answer, read in one reading so one run's question never sits
above another's answer (FR-D64).

**An answer says who it could not be given for.** Refused, unknown and
ambiguous names are counted apart in the run's message, with a badged tray
button beside the discovery button naming them; `stellody/ui/shortfall.py` holds
the words, the report and the mixin owning the button, `icons.badged` draws the
badge and the tray places the button.

**One file, replaced by every completed run; a run may correct what is known
but not take it away.** `carried_over` in `application/carrying_over.py` (pure)
carries an earlier answer only for an artist this run failed to reach, kept to
this run's years through a `LastRun` (FR-D66). `_carried` in
`ui/discovery_endings.py` applies the same rule to the message, so it never
contradicts the results screen. The file is written through
`infrastructure/atomic.py`.

## The update check

**Three answers, kept apart:** newer, newest, unreachable. A scheduled check
speaks only when there is something to offer; a check somebody asked for owes
all three.

**The endpoint is the guard.** `releases/latest` returns only a published
release, never a draft or prerelease, so nothing re-checks those flags.

**A version that cannot be read is not newer**: inventing an update costs
more than missing one.

**Asked off the interface thread; answered on it.** A plain thread asks and
emits a signal. An answer whose controller has gone is dropped where
`shiboken6.isValid` says so in `_run` in `stellody/ui/update_check.py`
(`tests/ui/test_update_check_after_close.py`); asking first would race.

**Skip silences a prompt, not the question:** the skipped tag never prompts
again; an asked-for check ignores the skip.

`stellody/application/updates.py` holds the comparison, platform choice and
service; `ReleaseSource` sits in `stellody/application/ports.py`;
`stellody/infrastructure/update_source.py` is the stdlib `urllib` adapter;
`stellody/ui/update_check.py` is the controller and dialogs.

## The guide

**It is drawn from the same pictures the window is.**
`stellody/ui/guide.py` resolves every icon through `stellody.shared.resources`,
the lookup the trays use; a missing icon yields no picture rather than an
exception. `guide_discovery.py` holds the discovery and shops procedure,
`guide_pictures.py` the drawing helpers (`INLINE_ICON_PX` sizes pictures larger
than body text) and `layout_advice.py` the layout section.

**A control the guide does not explain is a failure, found by sweeping rather
than listing.** `tests/ui/test_guide.py` is parametrised over every resource
getter minus a named, reasoned set of non-controls; `_named_pictures`
parses every module in `stellody/ui` for each `.png` it names, with no
exemptions, since dialogs fetch assets by name through `resources.find_asset`.
A companion case asserts the scan finds something.

**Under the furniture sit the rules no single screen can state**, plus how a
library wants laying out. `stellody/ui/layout_advice.py` states the latter
once; the guide shows it whole and a first-time listener sees a short note
before the folder picker opens. A test asserts the guide carries that module's
words rather than a copy.

## Reaching the sound device

**One class touches a device; PortAudio is what it speaks to.** WASAPI is a
host API within PortAudio, so the split follows that line:
`infrastructure/portaudio.py` is the substrate holding what every platform
shares (including `opened_shared` and `open_shared`);
`infrastructure/wasapi.py` and `infrastructure/coreaudio.py` specialise it.
The direction cannot reverse without a cycle.

**`infrastructure/output.py` is all the application knows about there being
more than one way to open a stream.** It switches on `sys.platform`, because
the interface differs rather than the hardware: Windows takes `wasapi.py`,
macOS `coreaudio.py`, everything else the substrate, which fails safe to the
mixer. Both host modules are imported inside the call. Where the device list
comes from is `infrastructure/output_list.py`; whether a device is addressed
by sink is `routes_by_sink` in `infrastructure/pulsesink.py`.

**The listener chooses the mode; the strip shows what the device answered.**
The bottom strip's switch calls `Transport.set_output_mode`, which reopens the
track in hand where it was, since a mode belongs to a stream. The choice is
stored under `output_mode`. `ui/stream_words.py` shows what was granted, read
off `PlaybackPort.report`, saying bit perfect only where
`SoundSettings.bit_perfect` agrees.

**The switch is offered only for a song the device in use can take**
(Oliver's ruling). `follow_song` in `ui/switches.py` stands the switch down for
a lossy file, a rate the device does not list or a device listing nothing,
with the reason in the tooltip; with no song in hand the device is judged
against `lossless_rates` in `domain/album.py`. The choice itself is left alone,
so the next eligible song gets the mode with no press. Held by
`tests/ui/test_no_exclusive_for_a_lossy_song.py` and
`tests/ui/test_exclusive_follows_the_device.py`.

**Which rates a device takes is asked once per device.** `exclusive_rates` in
`infrastructure/wasapi.py` asks the driver rate by rate without opening a
stream; `OutputDevices.exclusive_rates` in `infrastructure/output_devices.py`
keeps the answer for that device until the output moves or the list changes.
After a move PortAudio still means the old device until its list is taken
again, which closes any open stream, so the list is retaken only while no
stream is open: with none open the new device is asked at once; with one open
the answer is unknown until the next stream opens. Unknown stands nothing
down. A Mac is not asked, since the probing flags may disturb a device others
are using.

**An unforeseen refusal takes the switch back to shared.** The request has
already been answered by the mixer, so `follow_output_refusal` moves the
choice with `Transport.stand_down_to_shared`, leaving the stream alone. It
passes over a song `follow_song` already stood down for. A chosen device that
will not open at all is answered differently; see
[Choosing the output device](#choosing-the-output-device).

**Two things stop an exclusive stream being bit perfect from inside the
application:** volume below unity (`infrastructure/audio.py`) and an
equalizer designing any sections (`infrastructure/filtering.py`).
`OutputReport.is_bit_perfect` answers for the stream as opened;
`bit_perfect_as_played` in `domain/playback.py` adds the level and curve, each
tested by the engine's own condition for leaving a block alone.
`SoundSettings.bit_perfect` combines them and the window redraws the line when
volume, mute or curve moves (`tests/ui/test_bit_perfect_is_earned.py`).

**The route past the mixer differs per platform; on one there is none.**
`offers_exclusive` in `output.py` answers whether the mode is offered.

- **Windows** takes the device through WASAPI exclusive mode, the only route
  that stops other applications reaching it.
- **macOS** has no hog mode reachable through PortAudio (`paMacCorePro` is the
  same flag as `paMacCoreChangeDeviceParameters`). `coreaudio.py` instead runs
  the device at the track's rate and refuses a converting stream, delivering
  the samples untouched while other applications still mix in. It is reported
  as exclusive because that is the mode asked for and granted.
- **Linux is ruled out deliberately** (Oliver's ruling). The Flatpak sandbox
  hands over a sound socket rather than a device; outside it the route
  varies by machine; a mode that works on some machines and silently not on
  others is worse than one disabled with its reason.

**A device arriving carries the music on; a device leaving pauses it**
(`OUTPUTS.md` FR-O15). PortAudio takes its device list once per process while
Qt's `QMediaDevices.audioOutputsChanged` fires on every switch (and on changes
that move nothing), so `infrastructure/output_devices.py` reports a move only
when the default's identity changes and retakes PortAudio's list before the
next stream opens (or when rates are asked with no stream open). The
composition root opens every stream through it. Each move says whether the
default left behind is still listed. What a move does is
`application/output_following.py`'s: with System default chosen and the old
default still listed, a device has arrived and `output_switched` reopens the
track there as it was. Otherwise `output_moved` holds an active track (playing
or paused) and marks the output moved; `Transport.toggle` then reopens the
track from where it was rather than resuming, until the next load clears the
mark. A default changed by hand with both devices present reads as an arrival,
which the ruling accepts.

**A device switched off fails the stream before Qt says so.** The feeder marks
the session interrupted and holds the track rather than reading the failure as
an ending (`infrastructure/audio.py`); `output_moved` counts that as the move
having stopped the music, once; `Transport.toggle` reopens an interrupted
track. Music on a device the listener named ignores moves of the default;
music on the default only because the chosen device is away is never carried
to a device nobody chose. Held by
`tests/application/test_following_the_output.py`,
`tests/application/test_a_device_arriving.py`,
`tests/infrastructure/test_output_devices.py`,
`tests/ui/test_pausing_when_the_output_moves.py` and
`tests/ui/test_output_composition.py`.

`tests/infrastructure/test_portaudio_output.py` asserts that no host API
settings object is passed to the substrate (one belongs to a single host API);
`tests/infrastructure/test_output_switch.py` walks the platform switch under
each stated platform, since only the Windows branch runs on the development
machine.

## Choosing the output device

`OUTPUTS.md` holds the requirements; this is where they landed.

**The choice is kept apart from the device in use.** `OutputChoice` in
`stellody/domain/outputs.py` is an identity plus the name the system gave it;
an empty identity is System default. While the chosen device is missing or has
refused, music plays on the default and the choice waits. The name is kept
because a missing device cannot be asked for one.

**Identity decides; the name is what a listener reads.** Two devices can share
a name, so the choice is stored under `output_device` with
`output_device_name` beside it. `output_list` builds both lists: System
default first, devices in the system's order, repeated names numbered, a
missing choice last as not connected. The tick follows the device in use
(FR-O06).

**Windows' own enumeration is read, because PortAudio names no identity.**
PortAudio's WASAPI outputs come in the order
`IMMDeviceEnumerator::EnumAudioEndpoints` gives, so
`infrastructure/endpoints.py` reads that over COM through ctypes and
`infrastructure/output_list.py` matches by position among namesakes.
`opener_position` relies on that order only while the lists agree name for
name; otherwise a shared name is refused rather than guessed. Elsewhere (or if
COM fails) the list is Qt's.

**On Linux a device is addressed by its sink** (NFR-O-PORT-001). The Flatpak's
PortAudio shares no device names with Qt; Qt's identity there is the
sink's own name. On any platform that is neither Windows nor macOS,
`open_named` in `infrastructure/output_list.py` opens PortAudio's `pulse`
device with `PULSE_SINK` set for that open alone (routing in
`infrastructure/pulsesink.py`, `tests/infrastructure/test_pulsesink.py`). With
no `pulse` device it falls back to matching by name.

**What a choice does is the transport's.** `OutputChoosing` in
`stellody/application/output_choosing.py` is mixed into the transport beside
`OutputFollowing`. Choosing reopens the track in hand where it was; a stopped
queue is not opened just to be moved. A new device list answers with
`OutputChange`: losing the chosen device pauses (play then opens on the
default, FR-O11); its return takes the track back as it was. A device
refusing to open is answered by the default with a `Refusal` kept for the
window once; it is not asked again until chosen again or re-listed.

**The window says what a listener would otherwise guess.**
`stellody/ui/choosing_outputs.py` shows the list, stores the choice and
reports refusal, absence at launch and disconnection.
`stellody/ui/output_menu.py` fills the strip's popup and the Sound menu's
submenu from one function. `OutputDevices` emits `listed` before `changed`, so
the list is current before a move is acted on.

## Shipping to three platforms

**Each platform builds on itself; none cross-compiles.** `buildexe.py` with
`buildinstaller.py` (Windows setup), `builddmg.py` (macOS disk image),
`build_flatpak.sh` (Linux Flatpak), with `clean_flatpak.sh` undoing the last
and touching application data only under `--purge-data`. Output paths are
independent so no cleaner reaches a sibling's output.

**The site's icons and assets follow the application.** `generate_icons.py`
writes the icon set into `assets/` and copies the site's icons into `docs/`
byte for byte. `stamp_version.py` writes the version from `VERSION` into
`docs/` and gives every local stylesheet or script link a `?v=` content hash
(line endings folded), defeating GitHub Pages caching.

**Nuitka compiles on Windows and macOS**, one set of packaging surprises.
PyAV reaches `av.utils` in a way Nuitka does not follow, so both builds name it
explicitly.

**PortAudio is built from source in the Flatpak**, since sounddevice bundles
binaries only for Windows and macOS and the runtime ships none.

**The Flatpak is granted the home directory read only**, putting the sandbox
behind invariants 1 and 2.

**macOS notarization is not optional.** `builddmg.py` notarizes by default and
staples both the application and the image, so a copied-out application
launches offline.

## Reading panes and the keyboard

**A long page reads itself, then yields at once.** `AutoScroller` in
`stellody/ui/auto_scroller.py` works on any surface with a vertical scroll bar
and a viewport, parented to it so both live equally long. The licence viewer
and About (`stellody/ui/dialogs.py`) and the guide build one; the health report
does not. Each also wraps its text in a `ReadingPane` (invariant 11) that wears
no ring (invariant 10).

**The pace belongs to the class, never a dialog.** One timer ticks every
`TICK_MS`: an opening hold (`START_PAUSE_MS`), a slow descent (`DOWN_STEP_PX`
every `DOWN_TICKS_PER_STEP`), a hold at the end (`BOTTOM_PAUSE_MS`), a fast
rewind (`UP_STEP_PX`), a hold at the top (`TOP_PAUSE_MS`), repeat. A page that
fits never moves.

**Reading by hand suspends the cycle.** A wheel, mouse or key on the surface,
its viewport or its scroll bar hands the page over for `RESUME_AFTER_MS`; so
does focus arriving on it or anything inside it (watched at the application,
since a child never reaches the surface's filter); then the descent resumes
where the reader left it. Focus is ignored during the opening hold, so a dialog
focusing its own text does not count as a reader. A surface under a modal other
than its own dialog is `frozen`: time and input change nothing. Held by
`tests/ui/test_auto_scroller.py` (counts derived from the constants),
`tests/ui/test_dialogs.py::test_the_licence_reads_itself` and
`tests/ui/test_guide.py::TestTheDialog::test_it_opens_and_can_be_read`; no test
asserts About has a scroller.

**Space chooses a row, exactly as Enter does**, by being handed on as Enter
rather than given a second path. `SpaceChooses` in `stellody/ui/activating.py`
is an application event filter, built by `wire_the_arrows` in
`stellody/ui/ring_order.py`. On an unmodified Space delivered to a
`QAbstractItemView` of the main window that holds the focus
(`holds_the_focus` in `stellody/ui/ring.py`) and has a current row, it sends
Return and consumes the Space; otherwise Space passes on. It answers only the
main window's own views (the library list, the album grid and the two track
columns), since dialogs' item views answer Space themselves and an Enter would
tick nothing. What Enter does is the window's: `activate` in
`stellody/ui/playing.py` for the list and pane, `open_album_at` for the grid.
Held by `tests/ui/test_space_chooses.py`. Menus answer the other half:
`RingedMenuBar` in `stellody/ui/menu_bar.py` turns Space on a highlighted item
into Return, since Windows styles answer `SH_Menu_SpaceActivatesItem` with 0
(`tests/ui/test_menu_ring.py`).

**The discovery results answer their own keys.** Each list is a `ResultsList`
in `stellody/ui/results_tree.py` setting `keeps_horizontal_keys`, so Left and
Right shut and open an artist. Enter or Space chooses the current row (ticks an
album, opens or shuts an artist) inside the list, since Qt would hand Enter to
the dialog's default control. `focusInEvent` makes the first row current only
when focus arrives by Tab or Backtab (`ASKING_FOR_A_PLACE` from
`stellody/ui/gliding.py`) with nothing current; a click leaves the current row
and scroll alone, because focus arrives before the press is handled and
choosing the first row would scroll the list under the pointer.
`FirstStopDialog` passes over scroll areas, so the results dialog names its
first list as its first stop. Initial focus is handed over as a Tab.
`_state_ring` in `results_dialog.py` states the Tab order. The current row is
ringed through `QTreeWidget#ResultsList::item:focus`, the one rule that rings
a row for focus. Lists are styled before rows go in, so row heights agree.
`BoxedTicks` in `results_ticks.py` has the style draw its own empty box under a
ticked row's tick (the Windows style draws a bare tick; Oliver's ruling).
Held by `tests/ui/test_results_keyboard.py`.

## Design decisions

| Decision | Reason |
|---|---|
| PySide6 rather than Rust or Go | The requirement is a player that is not buggy, which comes from working where the coverage gate, the structural guards and the delivery lineage already exist. |
| `soundfile` and `sounddevice` rather than `QMediaPlayer` | `QMediaPlayer` cannot present a cue-sheet slice as a track and offers no equalizer to build on. |
| PyAV rather than Qt Multimedia, for the formats libsndfile cannot open | PyAV reaches the decoder directly, so a cue slice stays a slice; Qt Multimedia would bring a second idea of what a track is. See [The central abstraction](#the-central-abstraction). |
| The bundled FFmpeg is LGPL, verified rather than assumed | Its own licence string, read from the shipped binary, says LGPL 3 or later. It also links libx264 and libx265 (GPL-2.0-or-later) which `avcodec` imports outright; the decoder lives in the GPL-3.0 application, so the combination is compatible and the package is distributed as a GPL-3.0 work. Nothing here encodes video. |
| A track that will not open is reported, never left as silence | A listener cannot tell silence from a missed press. `PlaybackError` is named in the domain so the application catches it without importing the raising layer; `DecodeError` and `OutputUnavailableError` are both that error. It is raised, not reported through a callback, so the window catches it in the one place that can give the device back, reset the buttons and say what happened. A chosen device that will not open is answered by the default instead (see [Choosing the output device](#choosing-the-output-device)). |
| A pause is not an ending; it is caught in both layers | A device cannot tell a hold from an ending. In the engine, a write failing while the resume is already clear is a pause landing on the feeder, so the block is dropped and the feeder waits again. In the transport, `_held` is set on a pause, cleared on resume and taken from `playing` at every load; `advance_if_finished` does not advance while it is set. A feeder failure is acted on first, held or not, since a failed feeder cannot resume (`application/ending.py`). |
| Skipping while paused stays paused | A track ending and a press of Next arrive through the same method; a run-out device reports PAUSED like a paused one, so whether the move plays is handed in by the caller. Arriving by a skip does not count as waiting at a beginning, so Back still returns to the start of the track in hand. |
| The runtime is pinned while the development tools keep their floors | A build of one commit must be the same build whenever made; the Nuitka flag for PyAV depends on exact versions. `requirements.txt` pins with `==` and `requirements-dev.txt` reads it before adding tools on floors. Invariant 20 holds every pin to what is installed. |
| The checks run in the project's own environment | A suite run in a different interpreter can pass while the application cannot play. Where the project has a venv a structural test refuses to pass elsewhere, a second checks everything `requirements.txt` declares is installed there; `gate.ps1` names the interpreter. |
| The claim to being the running copy is separate from the channel that reaches it | Asking a listener whether it is there races at the moment it matters. Ownership is a shared memory claim under a semaphore; the channel only carries activation. |
| The ask carries a word rather than being the connection itself | Any process may open a named pipe, so the word is read before the window moves. |
| Ending the application is said out loud, never left to Qt | Quit-on-last-window-closed is off so the cross can leave Stellody in the notification area; every path that means to leave says so. |
| A file's shape is measured once and shared by its tracks | A cue album would otherwise be decoded once per track. `stellody/application/shapes.py` slices one measurement, keyed by a digest of the file's path. |
| A bucket holds how loud it is, not its loudest sample | The loudest sample in a short bucket sits near the track's peak, so a peak envelope draws almost everything at full height. Loudness gives a shape; a column covering several buckets still takes their loudest, so transients survive. Kept records are invalidated by the format version. |
| The resolution belongs to the music, not to the file | A fixed bucket count per file made long cue albums draw in wide blocks. A bucket is stated in time, the count following the music between a floor and a cap: `buckets_for` in `stellody/domain/waveform.py` (`BUCKET_MILLISECONDS`, `LEAST_BUCKETS`, `MOST_BUCKETS`), held by `tests/domain/test_envelope.py`. `FORMAT_VERSION` in `stellody/infrastructure/waveform.py` invalidates older records. |
| Levels are rounded where they are measured, not on the way to the record | A measurement differing from its own record by a rounding would redraw differently after a restart; rounding also keeps records small. |
| A cover is read by one module and kept by another | `infrastructure/covers.py` reads a picture out of audio and nothing more; `infrastructure/artwork.py` decodes, scales and writes without importing a tag library, so it can be granted writing without granting it to a tag reader (invariant 1). |
| A cover is kept against the album's identity, not a path | A rename reuses the picture; the source's size and modification time are recorded, so a replaced cover is read afresh. |
| One kept size serves every place a cover is drawn | One pixmap held at the grid's size serves both views, Qt scaling it for a row. Changing grid size re-reads from Stellody's own store, holding memory to the size chosen. |
| A row states its own decoration size | A `QPixmap` in `DecorationRole` sizes the row and the view's icon size is ignored, so `RowCover` states `option.decorationSize`; only rows with a picture are touched. |
| A shape is drawn as it is read, not when the reading finishes | The wait cannot be avoided but can be watched: the reader offers the shape so far periodically and the picture builds from the left. Only the finished measurement is kept. A part and a finish are separate signals, so a runner never lets go of its thread on the first part. |
| Folding is done by numpy over blocks, not by walking frames | Per-frame Python dominated the time; the vectorised fold gives the same answer bit for bit. |
| A measurement is given up on, never waited out | The bar follows the highlight, so a step through the library replaces a measurement likely still decoding. Quitting a thread does not interrupt a decode, so the cancel check is handed down to the reader, which gives up at its next block and keeps nothing; letting go never blocks the interface thread. |
| The application keeps an account of its own appearances | A window arriving unbidden cannot be traced afterwards. `stellody/infrastructure/diary.py` records every show with its frames, every restore and each shutdown step. It and `startup_log.py` live in Stellody's own data directory (Oliver's ruling), since a sandboxed Flatpak discards its temporary directory. Both make the directory when they write and catch `RuntimeError` as well as `OSError`, since locating the data directory can itself fail. |
| Artwork is local first, with a remote chooser somebody opens | An automatic lookup would trade the local-first guarantee for very few covers; no file carries a MusicBrainz identifier, so a fetch could attach the wrong cover unknowingly. |
| A chosen cover is kept apart from a read one | It has no source file to check, so its record carries a chosen marker, is never invalidated by a rescan and is preferred to the folder's. |
| The store is asked for a cover whatever an album's own files offer | A chosen picture has no file beside the music, so `AlbumArt.reading` always asks the store. |
| The chooser is injected, so a window without it offers nothing | The lookup reaches outward, so it arrives as an adapter behind a port; a window built without one has no menu entry, which lets the suite run with no network. |
| A refused ask is asked again; a refusal is never reported as an absence | MusicBrainz refuses often under load. The release search is retried with a growing pause; what survives every retry is carried as a refusal, since a service that would not answer made no claim about the album. Only the search retries. |
| The rating is one control rather than five buttons | One value is one keyboard stop painting one ring; the stars are drawn rather than assembled. |
| The transport is told who to report a play to, rather than being given it | The one place a collaborator is set rather than injected: only the window can turn a track into its album and it does not exist when the transport is built (`Transport.report_plays_to`). |
| A narrowing keeps every cover already read | A cover belongs to an album, not a run of rows, so the cache is dropped only where the sources are replaced (a load or scan). The pane takes a sleeve that arrives after it opened. |
| A tooltip appears almost at once | On picture buttons the tooltip is the only name. `stellody/ui/tips.py` is a proxy style shortening the tooltip delay, built from the replaced style's name since the application destroys that style. Its `polish` marks every window `WA_AlwaysShowToolTips`, so tips show while Stellody is behind another application (`tests/ui/test_tips.py`). |
| A ring a popup leaves behind is redrawn | Qt withholds HoverLeave from a window while another's popup is up, leaving a hover-drawn ring stale. `stellody/ui/hover_paint.py` is an application filter asking for a paint on a Leave under a popup, for every `WA_Hover` widget (`tests/ui/test_leaving_under_a_popup.py`). |
| Every switch says what a press would do, on both strips | One convention for the whole application: a switch shows the state it would move to, as the mute switch is struck through while sound is on. Repeat's tooltip names the control instead, since three states named one at a time read as stuck; its picture still names the press. |
| The album pane's play button doubles the tray's, so it toggles with it | Two play buttons that disagree are worse than one. With a track loaded it hands the press to `toggle_playback`, the one method deciding what play means (`tests/ui/test_both_play_buttons_agree.py`); with nothing loaded it starts the open album. `_point_at_what_is_in_hand` in `stellody/ui/viewing.py` reopens the album holding the track in hand on that track (`tests/ui/test_resuming_after_the_pane_comes_back.py`). |
| The About button became a Help button with a menu under it | A picture button is named by its tooltip, so one opening several things is named Help. Its menu IS the menu bar's Help menu, so the two cannot drift (`tests/ui/test_update_check.py`). |
| A reading dialog never opens on its own page | A ring round a whole page offers nothing to act on. `first_stop` passes over a scrolling region; the pane keeps its stop; a dialog that is only a pane opens on nothing. Held by a sweep over every dialog discovered from source. |
| A dialog's native window exists before anything sizes it | On Windows with mixed scaling a dialog sized before its native window existed opened scaled across several displays. `FirstStopDialog.__init__` calls `self.winId()` first except on Wayland, where it corrupts the window behind (`makes_window_early`). `tests/ui/test_dialog_first_stop.py::test_every_dialog_has_its_window_before_it_is_shown` pins the precondition. |
| A prompt waved away decides nothing | The close prompt's answer starts at ASK and only a button moves it, so dismissing it neither leaves, hides nor writes anything. |
| The waiting after a refusal is spent on a pass, never on one artist | MusicBrainz refusals reflect its load, not our rate. A refused artist is asked once more, then put back for a later pass, so waiting overlaps other artists. `application/passing.py` is the bookkeeping and asks nothing. |
| A run asks a catalogue only what it has never been told | Asking everything every run made answers vary with a service's mood. Answers are kept in `catalogue-memory.json`: `application/remembering.py` holds the rule, `infrastructure/catalogue_memory.py` the file. An answer stands for a period then is asked again (Oliver's ruling: runs should differ over weeks, not minutes). Saving merges with what the file holds (`merged`); one `FileCatalogueMemory` serves the run, its price and expansion. Undated album and series answers are dropped on read (`_dated`, FR-D67). The kinds include identities, `credited`, `series-of`, `series` and `titled`; asking lives once in `recalled` over an `Asking` (`tests/ui/test_discovery_composition.py::test_everything_keeping_catalogue_answers_shares_one_memory`). |
| The answer is turned a page at a time, with every page built up front | A page fills every column, depth following height (Oliver's ruling); a column holding a tall artist scrolls. Every page is built at open because a tick is held by its row. `ui/results_room.py` is the arithmetic, `results_pages.py` the pages, `results_pager.py` the controls, `results_foot.py` the one foot row they share with the shop controls (Oliver's ruling). |
| Every block the device ran dry before it arrived is written to the diary | `stellody/infrastructure/dropouts.py` watches the room in the buffer (PortAudio's underflow flag proved blind on shared WASAPI): a write finding the whole buffer free follows a device that ran dry; a write taking longer than its audio plus what was buffered held a silence of the difference (timed on `perf_counter`). The buffer's size is read once per stream, on its first start, since a queue survives a stop. `stellody/infrastructure/buffering.py` asks every stream for two blocks of queue, which ended the static heard under load; `lead_frames` counts that queue for position and pictures. Held by `tests/infrastructure/test_dropouts.py` and `tests/infrastructure/test_buffering.py`, both on the real device. Metering lives in `stellody/infrastructure/metering.py`. |
| One dropped connection no longer ends a run; a run of them still does | An artist nothing answered about goes round again like a refused one; the run gives up only after a run of consecutive silences, counted once for the whole run by `Silence` in `application/gathering.py`. |
| Every answer is written down as it arrives, not only when a run ends | Each answer is appended to a running record and forced to disk; each memory reads its file plus that record, dropping the record once the file holds it. `infrastructure/journal.py` owns appending, as `atomic.py` owns replacing. |
| An answer with a hole in it is written, with the hole named in it | What could not be answered is written beside what was, shown in the shortfall sentence and filled by the next run; gaps are written in artist order. |
| What a failure says on screen is read off its kind, never off its message | The row gets a sentence; the diary gets class, message and artist. A refusal and a timeout are distinct kinds. |
| The results screen is dealt into columns and stops at a 13 inch display | It takes a share of the screen in up to three columns, capped at what a 13 inch display shows (Oliver's ruling; FR-D45 holds the measurement, `THIRTEEN_INCH_ROOM` the room). `results_room.py` is widget-free arithmetic; `results_columns.py` joins it to widgets. |
| A control that closes something wears the close picture, not the negative mark | `negative.png` is only ever composed over another picture to say off; alone it names no action. |
| Both genre filters share one row of pictured controls | Filter, Cancel and Clear are built once by `stellody/ui/filter_controls.py` (Oliver's ruling, including Clear wearing the close picture without leaving). Filtering is disabled while nothing is ticked, except in a chooser opened on a filter; `offer_apply` reads the boxes at every toggle (`tests/ui/test_filter_controls.py`). |
| A three-state switch is told apart by its artwork, never by a fill | A fill says two things, never three; each state has its own picture, one composed with a cross at run time. |
| Holding one track is decided where an ending is noticed, not in `next` | Repeat-one answers an ending; Next overrules it. So `advance_if_finished` replays while `next` always advances. |
| The colours are kept apart from the stylesheet that applies them | What a colour is and where it applies change for different reasons: `stellody/ui/palette.py` holds values, `stellody/ui/theme.py` builds the sheet and re-exports both. |
| Where a queue move lands is decided apart from the device | `domain/moving.py` holds what Next, Back and an ending mean under repeat and shuffle as pure functions, so one rule serves a press and an unattended seam. Randomness enters as an argument. |
| The equalizer switch is kept apart from its sliders | Comparing on against off must not lose the curve; they are two settings. |
| A boost is clipped at the format's ceiling, as the last resort | The curve already makes room for its lift; what can still reach the ceiling is input already over it plus small overshoots. Filtering is done in floating point, since writing out-of-range values into an integer array overflows rather than clips. |
| What the library is shown as is one group on the bottom strip | The view toggle and sleeve size are one child group in `stellody/ui/showing_controls.py`. |
| How the music sounds is one group on the right of the bottom strip | Volume, mute, output device, exclusive output and equalizer sit in `stellody/ui/sound_controls.py` in an order Oliver ruled: volume beside mute, then a rule, then device before how it is held (`OUTPUTS.md` FR-O01). |
| Opening the whole library is a toggle on its heading | One chevron at the left of the Title heading, the application's own artwork (falling back to the style's arrow), with room derived in `expanding.py`. What a press does is read off the rows; partly open counts as shut. Replacing the header copies the replaced header's alignment, movability and stretch. Not a keyboard stop; the menu is the keyboard route. |
| A change that moves every row is answered once, never per row | `expandAll` reports every row it opens, so the chevron's answer is silenced during such a change and asked once at the end; the View menu goes through the same object. Held by counting questions, not timing. |
| An album's own chevron is the same picture as the heading's | `Chevrons` loads and fits the two pictures once per size; `ExpandingTree.drawBranches` draws them for rows with children only. |
| A switch of view arrives where the other one was | A switch carries the track the left view pointed at, else what is playing; the sleeve is picked rather than opened outright so the grid travels to it and `_on_album_picked` opens the album beneath. |
| A window that will not fit the screen is maximised, never nudged | On Windows `resize` sets content size while the frame Windows adds is not reported by Qt (`frameMargins`), so a full-width window lands partly off screen. `fit_on_screen` compares where the content landed and maximises what does not fit. Offscreen cannot see this. |
| A window is maximised on the screen its title bar is on, never where most of it lies | Windows maximises onto the monitor holding most of a window, which across mixed scaling can be a screen the title bar is not on. `stellody/ui/maximising.py` takes the maximise only where those differ, lays the window on the title bar's screen and maximises there. `stellody/ui/title_bar.py` is the module that asks Windows where the title bar is. `tests/ui/test_maximising.py` holds the decision; the Windows half rests on measurement. |
| The top tray decides how narrow the window may be | Every tray control is fixed size, so the tray's minimum is the window's; `tests/ui/test_window_size.py` checks the default width against it. |
| The whole interface is drawn at nine tenths, on every screen | On a small high-DPI panel the window's minimum exceeded the room. `stellody/ui/interface_scale.py` asks Qt's global scale factor before the application is built (Qt reads it once); a scale set in the environment wins. Held by `tests/ui/test_interface_scale.py` and `tests/ui/test_launch.py`. |
| Rescan and repair sit on the bottom strip, not in the tray above | The strips split by what is playing against what the library holds; rescan is an errand and repair answers it. A hairline rules donate off from them. |
| A rule draws its own line rather than wearing a background | At nine tenths scale a one pixel background can cover no device pixel. `tray_parts.Rule` draws a cosmetic pen, one device pixel at any scale (`tests/ui/test_every_rule_is_drawn.py`). |
| A menu entry that cannot act is disabled, as a button that cannot act is | `viewing.show_covers` is the one place the view changes, so it disables Expand all and Collapse all in the sleeves. |
| The whole menu bar is swept, rather than the entry that was reported | `tests/ui/test_menu_sweep.py` states every entry against the situations enabling turns on and asserts the table IS the bar, so a new entry must be decided. Rescan's state is set where the button's is. |
| Every picture button is on the menu bar too | Placement is Oliver's ruling: File, Edit, View, Sound, Control; the volume slider and donate stay off menus (`open_donation` is wired to the strip alone). Each entry reads its state from what it stands for when the menu opens (`stellody/ui/menu_mirrors.py`); the Output device submenu is refilled by `show_outputs`. `tests/ui/test_menu_mirrors.py` changes state through the window, not the entry. |
| One thing held at the middle of a strip is held by three columns, not two stretches | Two stretches centre only when the end groups match in width. `tray_parts.centred_row` lays three grid columns with equal outer shares (`tests/ui/test_transport_centred.py`). |
| A stylesheet border needs `WA_StyledBackground` on a plain widget | Qt drops a plain `QWidget` subclass's sheet border without it, silently. `tests/ui/test_tray_rules.py` reads the paint, not the sheet. |
| Every stop that can be landed on shows a ring, the same one everywhere | Asserted by walking the real widgets, not a list. Named exceptions paint their own ring (the stars, the ringed checkbox, the sleeve size button, menu titles) or hold nothing to paint; item and text views stand outside the rule (invariant 10). One colour token serves every ring. |
| A checkbox's ring is painted on its square, not stated in the stylesheet | Styling `::indicator` replaces the whole subcontrol and loses the tick. `ringed_check.py` paints over the square Qt reports, taking colours from the sheet as properties; a structural test forbids a plain `QCheckBox` elsewhere. |
| The sleeve grid travels to a selection rather than snapping to it | The grid scrolls per pixel and glides to where Qt would have jumped, so no second copy of Qt's reveal rules exists; nothing glides while off screen. `stellody/ui/gliding.py`, held by `tests/ui/test_gliding_grid.py`. |
| A cancelled lookup is stopped where it stands, not merely silenced | The worker hands the archive a question it asks between paced gaps and inside every read, in `CHUNK_BYTES` pieces and `SLEEP_SLICE_S` slices. A queued cross-thread signal arrives with no sender, so identity is never checked that way (`tests/ui/test_cover_worker.py`). |
| A thread that outlives its dialog is held by the window, with leaving outright as the last resort | `ThreadKeeper`, given by the window, holds worker and thread until each finishes, connecting before reading the finished state. `leave_at_once` in `stellody/composition.py` leaves the process before teardown, since Qt aborts over a thread still running. |
| Where the library was looking survives a reload that changes nothing about where it should be looking | `stellody/ui/placing.py` names the album by identity with a pixel offset and finds its row again after the reload; a vanished album still restores the offset. |
| The focus rule names the arrivals that ARE a choice, rather than the ones that are not | Qt invents a current index on any focus arrival, right for Tab only. `ASKING_FOR_A_PLACE` in `stellody/ui/gliding.py` names Tab and Backtab; every other reason leaves the place alone, the safe direction to fail in. The results lists follow the same rule. |
| One notch of the wheel moves one row | `NOTCH` in `stellody/ui/gliding.py` is Qt's documented detent, written here; part-turns are carried so fractional wheels still move a row per notch. Trackpad pixel deltas are left to Qt's continuous scrolling. |
| A broken shop row is shown for mending, never dropped in silence | The shops dialog refuses a form that would not make a working shop; a hand-broken row is read as a `BrokenRow` with its reason, listed greyed with edit and delete, never merged by a release. `domain/shop_list.py` (`tests/domain/test_shop_list.py`); the dialog is `tests/ui/test_shop_editing.py`. |
| A dragged shop is carried with the pointer, never placed on release | `stellody/ui/shop_dragging.py` switches the layout off while a row is held and glides the others; the landing place is the start position whose top is nearest the held row's top, read from the layout's own tops. The move is written on release; a refused write glides back. Not Qt's drag loop, which carries a picture and cannot be driven offscreen (`tests/ui/test_shop_dragging.py`). |
| The album pane is as tall as its album, up to half the page | Each column in `stellody/ui/track_column.py` asks for its rows' height; `stellody/ui/covers_page.py` caps the pane so the grid keeps half the page (or one whole row of sleeves where larger), recomputed on resize and sleeve size. `GlidingGrid.scroll_settled` forces layout before scrolling. Held by `tests/ui/test_the_pane_fits_its_album.py` and `tests/ui/test_opening_an_album_keeps_its_sleeve_in_view.py`. |

## Coverage

The gate is 100% branch coverage over `stellody.domain` and
`stellody.application`: the layers reachable with no filesystem, no clock and
no audio device, where anything short of complete is a decision nobody made.
Infrastructure and UI sit outside the gate and outside what is measured, since
much of them needs a real device, library or the Windows shell.

**No test may start the application.** `tests/conftest.py` refuses any
`subprocess.Popen` command naming `stellody.exe`, points the diary at a
directory of the test's own and sets `QT_QPA_PLATFORM=offscreen` before any
`QApplication` exists, however the suite was started.
