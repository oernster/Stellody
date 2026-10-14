# Architecture

The rules the structure keeps and why it is shaped as it is. Requirements live
in their specifications (`DISCOVERY.md`, `SHOPS.md`, `OUTPUTS.md`,
`FORMATS.md`, `BACKUP.md`); product trade-offs live in
[`DECISIONS-TRADEOFFS.md`](DECISIONS-TRADEOFFS.md); each module's docstring
holds its detail. A constant that governs behaviour is named here rather than
quoted, so its value has one home.

## Invariants

Each invariant names the test that enforces it. A new guard is proved by
planting a violation and reading the exit code. Running and writing tests is in
[`TESTING.md`](TESTING.md).

| # | Invariant | Enforced by |
|---|---|---|
| 1 | Stellody never writes tags back into a music file. Every module importing a tag library (mutagen, soundfile, taglib or PyAV) is scanned for a call to `save`, `delete`, `add_tags` or `add_picture`. | `tests/structural/test_readonly.py::test_tag_writing_is_unreachable_from_every_tag_reading_module` |
| 2 | Only the modules that own Stellody's own state may write to disk; nothing on the scanning or probing path writes. Outside the permitted modules the test refuses `open` with a literal write mode, named `os` and `shutil` calls spelled `module.function(...)` plus path methods such as `write_text` and `unlink`; a write spelled another way is not seen. | `tests/structural/test_readonly.py::test_only_state_owning_modules_write_to_disk` |
| 3 | Layers never import upward. UI and Infrastructure both depend inward, never on each other. | `tests/structural/test_layers.py::test_layers_never_import_upward` |
| 4 | No Qt, no tag library and no audio library appears below the infrastructure layer. | `tests/structural/test_layers.py::test_domain_and_application_are_framework_free` |
| 5 | The domain layer touches no filesystem, no network and no scheduler. | `tests/structural/test_layers.py::test_domain_has_no_side_effects` |
| 6 | Time enters the domain as an argument, never by being looked up. | `tests/structural/test_layers.py::test_domain_never_reads_the_clock` |
| 7 | No module exceeds `LINE_CAP` lines: every Python file in the repository bar the build scripts named in the test and the directories `tests/structural/conftest.py` names as not ours. | `tests/structural/test_loc.py::test_no_module_exceeds_the_line_cap` |
| 8 | No module sits in the danger band above `DANGER_BAND_FLOOR`; a file that reaches it is reduced to `COMFORTABLE_TARGET` or below rather than shaved. | `tests/structural/test_loc.py::test_no_module_sits_in_the_danger_band` |
| 9 | Formatting and linting are current, as assertions. | `tests/structural/test_style.py` |
| 10 | A ring belongs to a control; to every control. No container is a ring target; no item view or text view wears one round itself (a row may: the results list rings its current row, the cover chooser its picked tile); no pane reaches the window's focus chain; every other control Tab can land on shows a ring, walked off the real widgets. A checkbox is always the ringed subclass. | `tests/ui/test_focus_rings.py`, `tests/ui/test_every_stop_paints_a_ring.py`, `tests/structural/test_rings.py`, `tests/structural/test_focus_ring_selectors.py` |
| 11 | A read-only page is never focused by a click and is never what a dialog opens on; it is a stop only while it overflows. | `tests/ui/test_reading_panes.py`, `tests/ui/test_dialog_first_stop.py` |
| 12 | Exactly four modules may hold the machinery to open a connection; the cover search is reached only through its port, which the composition root alone builds. Nothing on the scanning, drawing or playback path can reach the network. | `tests/structural/test_offline.py::test_only_the_permitted_modules_can_reach_the_network`, `tests/structural/test_offline.py::test_the_search_is_reached_only_through_its_port` |
| 13 | No control tells a listener that what it does has not been built; swept off the real widgets of the window and dialogs. | `tests/ui/test_unbuilt_words.py` |
| 14 | `installer/` reads from `stellody`; nothing under `stellody/` imports `installer`. | `tests/structural/test_layers.py::test_the_application_never_imports_the_setup_program` |
| 15 | The product name is written once, as `APP_NAME`; every other surface builds it from that. Comments and docstrings are left alone. | `tests/structural/test_one_name.py::test_the_product_name_is_written_in_one_place` |
| 16 | No file the repository ships or writes carries a dash-like character other than the hyphen-minus. | `tests/structural/test_no_dashes.py::test_no_file_carries_a_dash_like_character` |
| 17 | The discovery fetcher's user agent is built from the product name, the version and one fixed contact address alone. | `tests/structural/test_user_agent.py` |
| 18 | Everything discovery keeps is written under Stellody's own data directory, each place named through `paths.py`. | `tests/structural/test_discovery_paths.py` |
| 19 | No test holds the machinery to reach the network, except the named few that open nothing beyond this machine. | `tests/structural/test_offline.py::test_no_test_holds_the_machinery_to_reach_the_network` |
| 20 | Every runtime pin in `requirements.txt` is the version installed in the environment the suite runs in. | `tests/structural/test_environment.py::test_every_pin_is_the_version_installed` |
| 21 | No audio file of a format proved by a generated fixture sits in the tree. | `tests/structural/test_no_committed_audio.py::test_no_fixture_audio_is_committed` |
| 22 | `HALF` is defined in `stellody/ui/theme.py` and in no other module of the package or suite. | `tests/structural/test_half_has_one_home.py::test_half_is_defined_only_in_the_theme` |

**Invariants 1 and 2 are why the project exists.** Stellody describes a
damaged tag; it never repairs one.

**Invariant 12's four modules:** `stellody/infrastructure/cover_search.py`
(a cover somebody asked for), `update_source.py` (the update check),
`fetching.py` (every catalogue request of a discovery run or an expansion) and
`instance.py` (the second-launch channel: a named pipe or local socket file).
The composition root builds all four. The catalogue clients `catalogue.py`,
`catalogue_series.py` and `similarity.py` hold no socket; each is handed the
fetcher. Dotted imports are matched in full, since every window
imports `PySide6` while only `PySide6.QtNetwork` reaches out.

**Every client that leaves the machine is held to named hosts.**
`stellody/infrastructure/reach.py` holds them; a redirect elsewhere is refused
(`PinnedRedirects` in `update_source.py`, borrowed by the cover search;
`Fetcher` in `fetching.py`). Held by `tests/infrastructure/test_redirects.py`.

**The update check sends a fixed request:** a fixed URL, an Accept header
naming GitHub's JSON media type and a user agent that is the product name
alone, so urllib's default does not name the machine's Python. Held by
`tests/infrastructure/test_update_source.py`.

**A library database that will not open is set aside, never refused.**
`stellody/infrastructure/opening.py` moves it aside whole with its write ahead
log and shared memory file, opens a fresh one and the window says where the old
file went. Held by `tests/infrastructure/test_opening.py`.

## Layers

```
UI  ->  Application  ->  Domain  <-  Infrastructure
```

| Layer | Contains | May import |
|---|---|---|
| `domain` | Values and rules. Frozen dataclasses, pure functions. | The standard library, minus anything with a side effect. |
| `application` | Ports as Protocols, plus use cases. | `domain` and the standard library. |
| `infrastructure` | SQLite, mutagen, soundfile, PyAV, sounddevice and its host APIs, Qt Multimedia's device list, Windows' audio endpoint enumeration over COM, Qt's image codecs and network stack, the filesystem. | `domain`, `application` and `shared`. |
| `ui` | PySide6 widgets, models, dialogs, the colour tokens in `palette.py` and the stylesheet built from them in `theme.py`. | `domain`, `application` and `shared`. |
| `shared` | Identity (name, version read from `VERSION`, copyright, donation address), asset resolution and the start-hidden flag. | The standard library. |

`stellody/composition.py` is the only composition root; `main.py` only calls
into it. Dependencies are supplied by constructor injection; there is no
container and no service locator. Two collaborators are set rather than
injected because the window does not exist when they are built:
`Transport.report_plays_to` and the device lister handed over through
`start_choosing_outputs`.

## The setup program

`installer/` is a second PySide6 application, compiled by `buildinstaller.py`
around the payload `buildexe.py` produces. It reads identity, theme, the
licence viewer and parts of `stellody.infrastructure`; invariant 14 holds the
direction and the line cap applies to it.

- `installer/route.py` reads the machine once and picks the route: install,
  update, downgrade, manage (repair or reinstall) or uninstall.
- `installer/actions.py` and `installer/registry.py` own everything written,
  all per user (`%LOCALAPPDATA%\Programs`, the uninstall record and sign-in
  entry under `HKCU`), so no administrator rights are asked for.
  `installer/steplog.py` owns setup's log; `installer/performing.py` owns the
  sequence.
- `installer/app.py` assembles the interface from `screens.py`, `shell.py`,
  `footer.py`, `wording.py`, `theme.py` and `appearance.py`, one screen to a
  step. `tests/installer/` covers it.

**Setup never opens the library database**, since it runs just after ending
the application by force. It leaves notes instead:
`stellody/infrastructure/switch_reset.py` (after an install or reinstall,
acted on by `stellody/ui/fresh_start.py`) and
`stellody/infrastructure/window_reset.py` (open maximised on setup's screen
after an install, repair or reinstall; the composition root forgets the
remembered size through `forget_window` and places the window through
`open_on` in `stellody/ui/geometry.py`). An update or downgrade leaves no note.

## The central abstraction

**A track is a slice of a file, not a file.**

```python
TrackSource(path, start_frame, end_frame)
```

A cue-sheet track and a whole file are one value object, so the queue, the
transport, shuffle, the amplitude monitor, the grid and the album pane never
ask which shape they hold. `TrackSource.address` is the bare path for a whole
file and `path#start_frame` for a slice.

**Two readers satisfy it.** `AudioSource` in
`stellody/infrastructure/decode.py` is the shape; `open_source` chooses by
suffix and is the only place that knows there are two. `SourceReader` covers
what libsndfile addresses by frame; `PacketReader` (`packet_decode.py`) covers
`PACKET_SUFFIXES`, counting timestamped packets back into frame positions.
Its traps (timestamps not starting at nought, seek pre-roll, reopening the
container on every seek) are commented where handled.

**The picture follows the sound.** `stellody/infrastructure/video.py` keeps
no clock: it asks the transport's position and hands back the frame due, so
the streams cannot drift. It crosses the boundary as `domain/picture.py`
(packed RGB); `application/pictures.py` holds one open for the track in hand;
`ui/picturing.py` shows it in the library's own area.

**Deferred imports:** PyAV only inside `open_source` and `VideoReader` (it
loads a large FFmpeg build); `output.py` reaches `wasapi` and `coreaudio`,
`output_list.py` reaches `endpoints`; `stellody/__init__.py` defers the
composition root into `main`.

## Grouping: folders group, tags name and join

**A folder is where an album starts, not where it ends.** Sibling folders
differing only by a disc marker merge into one multi-disc album. Folders whose
most common album and album artist tags agree are then folded by `fold_by_tags`
in `stellody/domain/folding.py` (the date is left out; a folder naming no album
or album artist is never folded). Folding never splits a folder. Title, artist,
date and genre are the most common value among the tracks.

## Resolving damaged metadata

Tags name things; they do not decide structure. Where they contradict
something physical, the physical thing wins:

| Conflict | Winner |
|---|---|
| Two tracks in one album claim the same disc and track number | The leading number in the file name |
| A track's `DISCNUMBER` disagrees with a folder named `(Disc 2)` | The folder |
| A colliding track's title duplicates another's | The file name |

Every fallback is a `LibraryIssue`, shown in the health view so the listener
can repair it in a tagger. Its two repair controls share one tooltip (in
`stellody/ui/bottom_tray.py`) and one `can_repair`.

`stellody/domain/ordering.py` holds the track rules, `grouping.py` the album
rules, `folding.py` the folding rule and `health.py` the reporting vocabulary.

**A file is reported once for its track number.** `resolve_tracks` reports a
missing number only where the tags carried none; `Repairs.pins_for` keeps one
pin per album, file and field. Held by
`tests/domain/test_health_and_ordering.py::test_a_colliding_file_with_no_ordinal_is_reported_once`
and
`tests/application/test_repairs.py::TestAcceptingAndResetting::test_two_findings_naming_one_file_for_one_field_pin_it_once`.

**Album order:** artist, year, title; a compilation by title, then year.
`AlbumIdentity.sort_key` in `stellody/domain/identity.py` is the one ordering.
A leading article is set aside, every compilation spelling
(`is_various_artists`) files as Various Artists and digit runs compare by
value. Held by
`tests/domain/test_identity_and_album.py::test_sort_key_keeps_a_compilation_series_together_across_spellings`.

## Accepting a correction

**Three layers: raw tags, the automatic rules, then what has been accepted.**
The store holds raw tags and resolves on load. `stellody/domain/overrides.py`
records what was accepted; `assemble_albums` applies it, so a load and a scan
get it from one place. What is pinned is the value the rule proposed, so
accepting moves nothing on screen; the tag editor records a different value
through the same table.

**An override is keyed by the album's identity handle plus a source
address.** `AlbumIdentity.handle` survives a folder rename or re-rip (artwork
and ratings use it too). A track-level pin reverts when its folder moves.
`LibraryIssue.paths` holds display names; `LibraryIssue.addresses` holds what a
pin is written against, since a cue track's display name can change and every
track of a cue album shares one path. `overrides.applied` looks pins up by
address; `edits_for` in `stellody/application/editing.py` writes the tag
editor's values against it
(`tests/application/test_editing_a_cue_album.py`).

**Two albums that resolve alike are one album; a stated price.** They share a
cover, an album rating and corrections
(`tests/domain/test_identity_collisions.py`). Where albums collide without
folding, `_named_apart` in `stellody/domain/grouping.py` appends the place to
what the handle is digested from; an album nothing collides with digests from
artist, title and year alone. A test pins that digest to its literal value,
since moving it would empty every library's ratings.

**A lossy copy of an album held lossless is dropped** by
`stellody/domain/duplicates.py` only where a lossless file in the same album
claims the same disc and track number and runs the same length within
`SAME_RECORDING_MS`. A missing disc number reads as the first disc; lossy and
lossless are told apart by a stated bit depth. `TestWhatMustNotChange` in
`tests/domain/test_lossy_duplicates.py` holds what must not move.

**A finding is silenced only where the whole of it is pinned.** A kind that
proposes no value is absent from `FIELD_FOR_KIND`.

**The findings and the accepted set are two lists**, since an accepted finding
leaves the report. Reset takes a group, an album or the lot; only the lot asks
first.

**An unreadable override is skipped rather than raised**, so one unapplied
correction never stops assembly.

## Stating what an album is

`Override` keeps what a rule proposed; `AlbumEdit` in
`stellody/domain/overrides.py` says what the album is. **A stated value is
keyed by the folder, never the handle**, since the handle digests the very
fields being stated. **Stated values are laid on before folding:**
`stated_over` in `stellody/domain/entries.py` rewrites the entries, then
assembly runs, so stating one folder's tags to match another's merges them.
`AlbumField` names the stateable fields: album artist, title, date and genre.

## Scanning

The walker lists folders, the probe reads one file's tags and the store caches
a folder's result. A folder is reused unopened only when every file's size and
modification time is unchanged and its record carries the current
`records.DERIVATION` (checked by `_unchanged`), so a corrected derivation rule
reaches the whole library on the next scan. The store holds raw tag values, so
a corrected resolution rule takes effect on the next start.

**Missing files are flagged, never deleted.** A folder whose files are all
flagged is left out until they return; `load_folders` applies the same rule
(`tests/infrastructure/test_a_vanished_folder_stays_gone.py`).

**A scan whose music folder is not there is refused.** The walker answers
`reachable` first and `ScanLibrary` raises `LibraryUnreachableError`
(`tests/application/test_an_unplugged_drive.py`).

**A scan and a load assemble the same library from the same store**, since
the window compares every scan against what `LoadLibrary`
(`application/loading.py`) assembled. Both lay stated values on first
(`tests/application/test_a_rescan_keeps_stated_albums.py`).

**What the walker skips is named:** a fixed list of system directories plus
macOS AppleDouble stubs. A leading dot is not hidden.

## Formats and probing

[`FORMATS.md`](FORMATS.md) specifies which formats are taken. All tag reading
is in `stellody/infrastructure/probe.py`, over five tag shapes: FLAC and Ogg
pairs as read; ID3 through `ID3_NAMES`; MP4 through `MP4_NAMES` plus
`MP4_PAIR_NAMES`; WMA through `ASF_NAMES` (case blind); WavPack's APEv2 with no
table. `covers.py` treats each MP4 cover as a front cover.

**What a format does not state is reported as absent.** No stated bit depth
reads as nought; `OPUS_SAMPLE_RATE` supplies the rate mutagen omits.
`OutputRequest` and `Track` refuse only a negative depth; `states_depth`
separates nought from a value; `depth_is_native` requires a stated depth, so
`is_bit_perfect` is False for any lossy source, as is
`Track.is_high_resolution`. `open_output` in `wasapi.py` and `coreaudio.py`
declines exclusive mode up front with `NO_STATED_DEPTH` (worded in
`portaudio.py`).

**Lossy families are the domain's:** `LOSSY_FAMILIES` and `stored_depth` in
`stellody/domain/formats.py` believe a stated depth unless the family is
named. `_bit_depth` in the probe honours an MP4 depth only for ALAC.

**A date tag is read for its year** by `year_of` in `stellody/domain/text.py`;
the tag is kept as written.

**`tests/infrastructure/test_scanning_formats.py` scans real files of every
format end to end**, through the real walker, probe and store, because unit
tests on each side can pass while disagreeing.

**The walk takes `PLAYABLE_SUFFIXES`** (`AUDIO_SUFFIXES` united with
`PICTURE_SUFFIXES`); `TrackSource.carries_picture` in
`stellody/domain/track.py` decides whether a suffix carries a picture.
Formats proved only by a generated fixture are encoded at test time by
`tests/infrastructure/widened_support.py` (invariant 21).

**Nothing is silently absent.** `UNPLAYABLE_SUFFIXES` names audio this build
recognises and will not play; a folder holding only those raises one finding
per folder. It proposes no value, so it cannot be accepted; unplayable files
are left out of a folder's signatures, so the folder is reused.

## What a scan reports

A finished scan opens a report naming what arrived and what left.
`stellody/domain/changes.py` compares two readings, counting a track by its
source; `stellody/ui/scan_summary.py` shows the page. The window compares what
it was showing rather than asking the store again. The runner tears its thread
down before emitting, so a modal opened from the handler has nothing waiting
behind it.

**The report is measured on a detached `QTextDocument`**, since the view's own
document has its width reset. `idealWidth()` returns the set width and
releasing the height clamp lets the page grow back, so neither is
re-attempted; the view is widened by `frameWidth`. Qt rich text has no
`opacity` and renders an entity dash as a real dash
(`tests/ui/test_scan_summary.py::test_the_report_carries_no_dash_and_no_styling_qt_would_drop`).

**A modal report hangs a test that completes a scan**, so
`tests/ui/test_launch.py` patches `ScanSummaryDialog.exec`; any later such
test must do the same.

## Searching

**No index; FTS5 is deliberately unused.** A pass over the normalised
library is cheap, while an index would hold raw rather than resolved text and
be empty for reused folders. `show_library` in `stellody/ui/searching.py`
normalises once per load or scan; `stellody/domain/searching.py` is the pure
filter.

**An album is kept whole.** A hit is selected and its row flashed; Return asks
the same phrase again.

**A keystroke resets the model**, as do inverting the order and rescanning. So
the pane under the sleeves is reopened; the delegate in
`stellody/ui/covering.py` paints the flash itself (Qt never asks a selected row
for `BackgroundRole`); `scrollTo` opens every level above a row.

## The genre catalogue and the filter

**A settled list, not the library's own strings.** The catalogue in
`stellody/domain/genres.py` is a fixed alphabetical set of mains, some
carrying styles, spelled as Discogs spells them. A value stored before a split
still reads as written.

**The grid's categories fold.** `stellody/ui/genre_grid.py` deals mains into
columns of `GenreGroup` (`genre_group.py`), whose arrow is made before its box
so focus reaches it first. `Folds` (`genre_folds.py`) keeps what is open per
dialog under the `SETTING_GENRES_OPEN_*` keys in `settings_keys.py`. After a
fold `_keep_folds` invalidates every layout from the group up, then adjusts the
dialog's size. Held by `tests/ui/test_genre_folding.py`.

**Rulings live in the alias table.** `ALIASES` in
`stellody/domain/genre_rulings.py` (re-exported as `genres.ALIASES`) maps tag
and MusicBrainz spellings onto catalogue entries, read by `MAIN_OF` and
`chosen_in`. No key is a catalogue name
(`tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_no_alias_is_keyed_on_a_catalogue_name`).

**MusicBrainz genres are weighed before reading.** `believed` in
`stellody/domain/genre_votes.py` drops a genre under `FEWEST_VOTES` unless none
reaches it, then any under `LEADING_SHARE` of the leader; `_genres` in
`infrastructure/catalogue.py` applies it (`tests/domain/test_genre_votes.py`).
The candidate genre cache file is renamed whenever the rule changes.

**The filter is pure and takes a field.** `Narrowing` and `narrowed_to` live in
`stellody/domain/narrowing.py`; `Narrowing.years` carries the years (FR-D99).
Any, not all (Oliver's ruling): each tick widens. A ticked style means that
style alone. "Not stated" is a box. The filter runs before the phrase; neither
knows about the other.

## Ratings and play counts

**Neither is attached to an object or a path.** A track's handle is the album
identity with disc and track number, digested; `stellody/domain/listening.py`
holds the record and the handle. An album is rated apart from its tracks
under a handle that cannot collide with a track's.

**Reaching the end is a play.** Only the transport can tell an ending from a
skip, so it reports the play with the album, since a rescan may already have
replaced the track. The whole log is held in memory and written through.

**Counts and stars are columns** (`Column.PLAYS`, `Column.STARS`) in the
library list and the album's track columns. Cell text is in
`stellody/ui/row_text.py`; a changed count redraws the row found by
`find_handle` in `stellody/ui/nodes.py`. Stars are answered under `STARS_ROLE`
and drawn by the one `RowCover` delegate, so no row carries a widget;
`stellody/ui/star_cells.py` holds what a star cell means and
`stellody/ui/stars.py` the drawing, press rule and wording shared with the
album's rating widget. A double click on stars never starts a track; number
keys rate and 0 clears; pressing the current star takes the rating back.
Held by `tests/ui/test_star_column.py`.

**What is playing is marked in the model and named along the foot.**
`stellody/ui/playing_mark.py` holds the playing track by handle, so the mark
reaches both views through `AlbumTreeModel` and survives a reload
(`tests/ui/test_the_mark_survives_a_reload.py`). `stellody/ui/now_playing.py`
writes the label, asked for by `_show_transport` in `stellody/ui/playing.py`,
which every command, failure and poll passes through. A stop clears both; a
pause keeps them.

**Going to the playing album.** Clicking the `PlayingLine` or the View menu's
Go to playing album (Ctrl+J) runs `show_playing_album`: it finds the track by
handle and carries the view there through `_carry_to_view` in
`stellody/ui/viewing.py`. In the sleeves that picks the album's sleeve, calls
`open_album_at` and then always scrolls the grid to the sleeve
(`self._grid.scroll_settled(sleeve)`), so the sleeve is reached even when a
cover size change moved it while the pane was open. Where the search or filter
hides the album it says so rather than clearing them
(`tests/ui/test_going_to_what_is_playing.py`). The action is enabled from
`show_now_playing`, since a disabled action refuses its shortcut too. A switch
of view takes the same route, carrying the track the left view pointed at,
else what is playing.

## Playback and the queue

**The seam is crossed inside the engine, by the feeder thread.** The following
source is opened while the current one plays and the feeder reads straight on.
The transport learns afterwards from a count belonging to the loaded session
(`stellody/application/following.py`). A follower is lined up only where it
cannot change (a scattered album beginning again keeps that seam gapped) and
where the open stream can carry it (same rate and channel count).

**Where a queue move lands is pure.** `domain/moving.py` holds what Next, Back
and an ending mean under repeat and shuffle; randomness enters as an argument.
Repeat-one is decided in `advance_if_finished`; `next` always advances.

**A pause is not an ending.** In the engine, a write failing while the resume
is already clear drops the block and waits again. In the transport `_held` is
set on a pause and `advance_if_finished` does not advance while it is set; a
feeder failure is acted on first (`application/ending.py`).

**A track that will not open is raised, never left as silence.**
`PlaybackError` is named in the domain; `DecodeError` and
`OutputUnavailableError` are both that error, caught by the window in the one
place that can give the device back.

## The equalizer

`domain/equalising.py` designs coefficients (testable without a device, hand
rolled from the Audio EQ Cookbook); `infrastructure/filtering.py` multiplies
samples in one pass over all bands, in floating point. A band at nought or at
or above half the sample rate is dropped, so a flat curve hands the block back
untouched and keeps an exclusive stream bit perfect.

**A lift is given room before it is applied.** `cascade` finds the combined
response's largest lift and folds that attenuation into the first section; a
curve that only cuts is left as designed. Held by
`tests/domain/test_equalising.py` and `tests/infrastructure/test_filtering.py`.

**The curve is kept by the engine**, with the volume, so a curve chosen before
anything loads still applies; it is redesigned at every load and every change
while a stream is open. The switch and the sliders are two settings.

## The visualiser

**It shows what the equalizer shapes:** two bars to each ISO octave band
`equalising.py` defines. `domain/spectrum.py` holds band edges and meaning;
`infrastructure/analysing.py` runs the transform.

**It runs after the write**, so it can never delay a block or alter a sample
(`tests/infrastructure/test_watching_the_output.py`); it measures after the
equalizer and before the volume. A short block is refused rather than read as
silence. The feeder swaps in one whole tuple for the interface thread to take,
with no lock. Measurements land per block; the strip repaints faster, bars
rising instantly and falling at a fixed rate. Its timer runs only while music
does.

**It sits mid-strip with no on or off switch**, held by
`tray_parts.centred_row`.

**Ten named styles draw the same measurement.** `Visualisation` in
`stellody/ui/visualisations.py` names them, with `DEFAULT_VISUALISATION` (the
dot matrix, Oliver's ruling); `PAINTERS` in `stellody/ui/spectrum_styles.py`
maps each to a painter in `spectrum_painting.py` or `spectrum_figures.py`. The
widget keeps clock, heights and peaks whatever the style and clips each painter
to its room. The choice is stored by name under `SETTING_VISUALISATION`; an
unknown name reads as the default. The list is lifted by `LiftMenu` in
`stellody/ui/lift_menu.py`, shared with the output devices. Held by
`tests/ui/test_visualisations.py`.

## Discovering what the library does not hold

[`DISCOVERY.md`](DISCOVERY.md) and [`SHOPS.md`](SHOPS.md) specify the
behaviour, each requirement naming its test. The structure:

- **Domain (pure rules).** `discovery.py` (`albums_missing`,
  `everything_offered`), `release_years.py` (`ReleaseYears`), `series.py`,
  `including.py` (`Including`), `matching.py`, `credit_evidence.py`,
  `estimating.py`, `taste.py`, `showing.py`, `discovery_filter.py` and
  `shop_list.py`.
- **Application (stages and bookkeeping).** `Discovery.run` in
  `discovering.py` drives the staged run: `artist_stage.py`, `series_stage.py` (`SeriesStage`),
  `candidate_genres.py`, `candidate_years.py`; `passing.py` and `gathering.py`
  (`Silence`) handle refusals and dropped connections; `remembering.py` and
  `remembering_series.py` keep answers; `settling.py`, `foreseeing.py`,
  `reporting_ahead.py`, `compilation_cost.py`, `carrying_over.py` and
  `shop_editing.py`. Ports are in `discovery_ports.py` (`CatalogueSource`,
  `SeriesSource`, `NoSeries`).
- **Infrastructure (the only way out).** Every catalogue client
  (`catalogue.py`, `catalogue_series.py`, `similarity.py`) asks through
  `fetching.py` (`Fetcher`, one `QNetworkAccessManager` per asking thread so a
  request in flight can be killed); `courtesy.py` holds pacing and the user
  agent behind one MusicBrainz gate
  (`tests/ui/test_discovery_composition.py::test_everything_asking_musicbrainz_waits_at_one_gate`);
  `resting.py` lets idle connections go while a run rests. One
  `FileCatalogueMemory` (`held_memory.py`, over `catalogue_memory.py` and
  `journal.py`) serves the run, its price and expansion, read once a session
  and written whole at quit. `browsing.py` hands a shop address to the
  system's browser and opens no connection.
- **UI.** `discovery_dialog.py` (built unseen at launch by `warm_discovery` in
  `discovering.py`), `discovery_progress.py` (`STAGE_ORDER`),
  `discovery_choices.py`, `year_fields.py`, the taste profile modules
  (`taste_store.py`, `taste_controls.py`, `taste_list.py`), the results
  screen (`results_dialog.py`, `results_room.py`, `results_pages.py`,
  `results_pager.py`, `results_foot.py`, `results_filtering.py`,
  `results_ticks.py`), `shops_dialog.py` and `shortfall.py`.

**Data flow.** The dialog's genres, years and `Including` go to a worker
running `Discovery.run`, which asks only about artists inside the ticked
genres; answers come back through the fetcher and the catalogue memory; the
completed run is written to one discovery file by
`infrastructure/discovery_file.py` through `infrastructure/atomic.py` (shapes
in `infrastructure/file_shapes.py`), recording what was asked beside what was
found; `carried_over` keeps an earlier answer only for an artist this run
failed to reach. The results screen reads that file. A stopped run is
abandoned rather than waited for, except at quit (`_leave_for_good` in
`stellody/ui/leaving.py`). Shops live in `shops.json`, settled shop by shop
against the shipped list.

## The update check

`stellody/application/updates.py` holds the comparison, platform choice and
service; `ReleaseSource` sits in `stellody/application/ports.py`;
`stellody/infrastructure/update_source.py` is the `urllib` adapter;
`stellody/ui/update_check.py` is the controller and dialogs.

**Three answers: newer, newest, unreachable.** A scheduled check speaks only
when there is something to offer; an asked-for check owes all three and
ignores a skipped tag. `releases/latest` never returns a draft or prerelease.
A version that cannot be read is not newer.

**Asked off the interface thread; answered on it.** An answer whose controller
has gone is dropped where `shiboken6.isValid` says so in `_run`
(`tests/ui/test_update_check_after_close.py`).

## Cover art from the archive

`ArchiveCovers` in `stellody/infrastructure/cover_search.py` asks MusicBrainz
for an album's releases and the Cover Art Archive for each release's pictures;
`stellody/application/choosing_covers.py` is the use case,
`stellody/domain/cover_choice.py` the offer, `stellody/ui/cover_worker.py` the
thread and `stellody/ui/cover_chooser.py` the dialog.

**Nothing found, refused and unreached are three answers.** `CoverOffer.unreached`
marks a search never answered (timed out, cut off, garbled or raised) or one
whose every listing was lost to a passing failure; the chooser then says the
search could not be made, never that nothing came back. A 404 listing is an
answer: that release has no art. Held by
`tests/infrastructure/test_cover_reaching.py::TestASearchThatWasNeverAnswered`
and
`tests/ui/test_cover_chooser.py::TestWhatTheChooserShows::test_a_search_never_answered_is_never_reported_as_nothing_found`.

**A passing failure is asked again.** A status at or above
`SERVER_ERROR_FLOOR`, one of `REFUSAL_CODES`, a timeout or another `OSError`
is retried up to `SEARCH_ATTEMPTS`, `LISTING_ATTEMPTS` or `FETCH_ATTEMPTS`
(`tests/infrastructure/test_cover_reaching.py::TestAPassingFailureIsAskedAgain`).

**The listing names its pictures over http.** Such an address is raised to
https as the listing is read (`PLAIN_SCHEME` in `reach.py`); any other scheme
is left as written, so `COVER_REACH` refuses it
(`tests/infrastructure/test_cover_reaching.py::TestTheSchemeTheListingNames`).

**A read is taken in slices of `SLICE_S`**, so a cancel is noticed within one;
the thread's quit wait, `WAIT_MS` in `cover_worker.py`, stays above it
(`tests/infrastructure/test_cover_reaching.py::TestHowLongAReadMayTake`).

## The guide

`stellody/ui/guide.py` resolves every icon through `stellody.shared.resources`,
as the trays do. `guide_discovery.py` holds discovery and shops,
`guide_backups.py` backups (using the File menu's labels from
`backup_words.py`), `guide_pictures.py` the drawing helpers
(`INLINE_ICON_PX`) and `layout_advice.py` the layout section, whose words a
first-time listener also sees before the folder picker.

**An unexplained control is found by sweeping.** `tests/ui/test_guide.py` is
parametrised over every resource getter minus a named set of non-controls;
`_named_pictures` parses every module in `stellody/ui` for each `.png` it
names. Certain passages are pinned word for word
(`tests/ui/test_guide.py::TestWhatItNames::test_it_describes_the_rows_and_profiles_as_they_now_stand`).

## Reaching the sound device

[`OUTPUTS.md`](OUTPUTS.md) specifies the behaviour.

**One class touches a device; PortAudio is what it speaks to.**
`infrastructure/portaudio.py` is the substrate (including `opened_shared` and
`open_shared`); `infrastructure/wasapi.py` and `infrastructure/coreaudio.py`
specialise it. `infrastructure/output.py` switches on `sys.platform` and is all
the application knows about there being more than one way to open a stream;
anything other than Windows or macOS takes the substrate. The device list
comes from `infrastructure/output_list.py`; whether a device is addressed by
sink is `routes_by_sink` in `infrastructure/pulsesink.py`.
`tests/infrastructure/test_portaudio_output.py` asserts no host API settings
object reaches the substrate; `tests/infrastructure/test_output_switch.py`
walks the switch under each platform.

**The listener chooses the mode; the strip shows what the device answered.**
The switch calls `Transport.set_output_mode`, which reopens the track in hand
where it was; the choice is stored under `output_mode`.
`ui/stream_words.py` shows what was granted, read off `PlaybackPort.report`.

**The switch is offered only for a song the device can take** (Oliver's
ruling). `follow_song` in `ui/switches.py` stands it down for a lossy file, an
unlisted rate or a device listing nothing; with no song in hand the device is
judged against `lossless_rates` in `domain/album.py`. The choice is kept for
the next eligible song (`tests/ui/test_no_exclusive_for_a_lossy_song.py`,
`tests/ui/test_exclusive_follows_the_device.py`).

**Rates are asked once per device.** `exclusive_rates` in
`infrastructure/wasapi.py` asks the driver without opening a stream;
`OutputDevices.exclusive_rates` in `infrastructure/output_devices.py` keeps the
answer until the output moves or the list changes. PortAudio's list is retaken
only while no stream is open, since retaking closes it; until then the answer
is unknown, which stands nothing down. A Mac is not asked.

**An unforeseen refusal takes the switch back to shared**:
`follow_output_refusal` calls `Transport.stand_down_to_shared`, leaving the
stream alone.

**Bit perfect is earned.** `OutputReport.is_bit_perfect` answers for the
stream as opened; `bit_perfect_as_played` in `domain/playback.py` adds volume
below unity (`infrastructure/audio.py`) and an equalizer with sections
(`infrastructure/filtering.py`); `SoundSettings.bit_perfect` combines them
(`tests/ui/test_bit_perfect_is_earned.py`).

**The route past the mixer differs per platform.** `offers_exclusive` in
`output.py` answers whether it is offered. Windows uses WASAPI exclusive mode.
macOS has no hog mode reachable through PortAudio, so `coreaudio.py` runs the
device at the track's rate and refuses a converting stream. Linux is ruled out
(Oliver's ruling).

**Following the default device.** `infrastructure/output_devices.py` reports a
move only when the default's identity changes, retaking PortAudio's list before
the next stream opens; the composition root opens every stream through it.
`application/output_following.py` decides: with System default chosen and the
old default still listed, `output_switched` reopens the track on the arrival;
otherwise `output_moved` holds the track and marks the output moved, so
`Transport.toggle` reopens rather than resumes. A device switched off fails
the stream first; the feeder marks the session interrupted rather than ended
(`infrastructure/audio.py`). Held by
`tests/application/test_following_the_output.py`,
`tests/application/test_a_device_arriving.py`,
`tests/infrastructure/test_output_devices.py`,
`tests/ui/test_pausing_when_the_output_moves.py` and
`tests/ui/test_output_composition.py`.

**Underruns and buffering.** `stellody/infrastructure/dropouts.py` watches the
room in the buffer (PortAudio's underflow flag is blind on shared WASAPI) and
writes each dry spell to the diary; `stellody/infrastructure/buffering.py`
asks every stream for `BUFFER_BLOCKS` blocks of queue and `lead_frames` counts
it for position and pictures; metering is in
`stellody/infrastructure/metering.py`. Held by
`tests/infrastructure/test_dropouts.py` and
`tests/infrastructure/test_buffering.py`.

## Choosing the output device

**The choice is kept apart from the device in use.** `OutputChoice` in
`stellody/domain/outputs.py` is an identity plus the system's name for it; an
empty identity is System default. It is stored under `output_device` with
`output_device_name` beside it. `output_list` in the same module builds the
lists: System default first, devices in the system's order, repeated names
numbered, a missing choice last.

**Identity on Windows comes from Windows.** `infrastructure/endpoints.py` reads
`IMMDeviceEnumerator::EnumAudioEndpoints` over COM through ctypes and
`infrastructure/output_list.py` matches by position among namesakes;
`opener_position` refuses a shared name when the lists disagree. Elsewhere the
list is Qt's. On Linux `open_named` opens PortAudio's `pulse` device with
`PULSE_SINK` set for that open (`infrastructure/pulsesink.py`,
`tests/infrastructure/test_pulsesink.py`), falling back to names.

**What a choice does is the transport's.** `OutputChoosing` in
`stellody/application/output_choosing.py` is mixed into the transport beside
`OutputFollowing`. A new device list answers with `OutputChange`; a device
refusing to open is answered by the default with a `Refusal` kept for the
window once.

**The window.** `stellody/ui/choosing_outputs.py` shows the list, stores the
choice and reports refusal, absence and disconnection;
`stellody/ui/output_menu.py` fills the strip's popup and the Sound menu from
one function. `OutputDevices` emits `listed` before `changed`.

## Backing up and restoring

[`BACKUP.md`](BACKUP.md) specifies the behaviour.
`stellody/application/backing_up.py` holds `Backups` (back up, verify,
restore) and the `BackupArchive` port; `stellody/domain/backups.py` holds the
manifest, the name and whether a backup may be put back, judged by each file's
schema. `stellody/ui/keeping_backups.py` is the window's half; each errand runs
through `stellody/ui/errand_worker.py`.

**Every file carries a numbered shape.** The database records its own in
`PRAGMA user_version`; `stellody/infrastructure/database_schema.py` holds the
upgrade steps, so the newest number is their count. Each JSON owner declares
its steps; `backup_file.py` derives each file's range from them.
`tests/structural/test_schema_bumps.py` fingerprints the creating statements
per number. An old backup always restores (Oliver's ruling;
`tests/infrastructure/test_old_backups.py`, whose format 1 backup is literal
text).

**A backup is the one file Stellody writes outside its own directory.**
`stellody/infrastructure/backup_file.py` writes the zip under a temporary name
moved into place, copying the database through SQLite's own backup; its entry
in invariant 2's permitted list says so.

**A restore completes at the next start.** A confirmed restore is unpacked
into a staging folder whose note is written last; the window quits and
`stellody/composition.py` relaunches through
`stellody/infrastructure/detached.py` once the single-instance claim is
released. The next start runs `stellody/infrastructure/staged_restore.py`
before the store opens, swapping by renames and moving the old set back on
failure.

## Shipping to three platforms

**Each platform builds on itself.** `buildexe.py` with `buildinstaller.py`
(Windows), `builddmg.py` (macOS, notarized and stapled by default),
`build_flatpak.sh` (Linux), with `clean_flatpak.sh` touching application data
only under `--purge-data`. Output paths are independent.

`generate_icons.py` writes the icon set into `assets/` and copies the site's
icons into `docs/`. `stamp_version.py` writes the version from `VERSION` into
`docs/` and gives each local stylesheet or script link a `?v=` content hash.

Nuitka compiles on Windows and macOS, both naming `av.utils` explicitly.
PortAudio is built from source in the Flatpak. The Flatpak is granted the home
directory read only, putting the sandbox behind invariants 1 and 2.

## The window

**Trays.** The top tray's fixed-size controls set the window's minimum width
(`tests/ui/test_window_size.py`). The bottom strip groups the view controls in
`stellody/ui/showing_controls.py` and the sound controls in
`stellody/ui/sound_controls.py` (order: Oliver's ruling); one thing centred on
a strip uses `tray_parts.centred_row` (`tests/ui/test_transport_centred.py`);
`tray_parts.Rule` draws its own one device pixel line
(`tests/ui/test_every_rule_is_drawn.py`). A plain widget's stylesheet border
needs `WA_StyledBackground` (`tests/ui/test_tray_rules.py`). Colours live in
`stellody/ui/palette.py`; `stellody/ui/theme.py` builds the sheet.

**Scale and placement.** `stellody/ui/interface_scale.py` sets
`INTERFACE_SCALE` before the application is built
(`tests/ui/test_interface_scale.py`). `fit_on_screen` maximises a window that
does not fit; `stellody/ui/maximising.py` maximises on the title bar's screen,
asked through `stellody/ui/title_bar.py` (`tests/ui/test_maximising.py`).
`FirstStopDialog.__init__` calls `self.winId()` before sizing except on Wayland
(`makes_window_early`;
`tests/ui/test_dialog_first_stop.py::test_every_dialog_has_its_window_before_it_is_shown`);
`keep_siblings_plain` in `stellody/ui/native_windows.py` sets
`AA_DontCreateNativeWidgetSiblings` (`tests/ui/test_neutral_start.py`).
`lifted_top` in `stellody/ui/lifting.py` places a lifted popup above or below
its button on the button's own screen.

**Menus.** Every picture button bar the volume slider and donate is mirrored
on the menu bar (placement: Oliver's ruling); `stellody/ui/menu_mirrors.py`
reads each entry's state when the menu opens
(`tests/ui/test_menu_mirrors.py`); `tests/ui/test_menu_sweep.py` asserts its
table is the bar. `viewing.show_covers` is the one place the view changes.

**The sleeve grid.** `stellody/ui/gliding.py` glides to where Qt would have
jumped (`tests/ui/test_gliding_grid.py`); `NOTCH` moves one row per wheel
detent; `ASKING_FOR_A_PLACE` names the focus reasons (Tab, Backtab) that pick a
current row. `GlidingGrid.scroll_settled` forces layout before scrolling, so
the destination is measured against the room left once the album pane has
taken its own. `stellody/ui/covers_page.py` caps the pane so the grid keeps
half the page (`tests/ui/test_the_pane_fits_its_album.py`,
`tests/ui/test_opening_an_album_keeps_its_sleeve_in_view.py`).
`stellody/ui/placing.py` restores the place after a reload. The pane's play
button hands a loaded track to `toggle_playback`
(`tests/ui/test_both_play_buttons_agree.py`); `_point_at_what_is_in_hand`
reopens on the track in hand
(`tests/ui/test_resuming_after_the_pane_comes_back.py`).

## Reading panes and the keyboard

**A long page reads itself, then yields at once.** `AutoScroller` in
`stellody/ui/auto_scroller.py` works on any surface with a vertical scroll bar
and a viewport. The licence viewer, About (`stellody/ui/dialogs.py`) and the
guide build one; each wraps its text in a `ReadingPane` (invariant 11). The
pace is named in the module: `TICK_MS`, `START_PAUSE_MS`, `DOWN_STEP_PX`,
`DOWN_TICKS_PER_STEP`, `BOTTOM_PAUSE_MS`, `UP_STEP_PX`, `TOP_PAUSE_MS`. Input on
the surface (or focus arriving inside it after the opening hold) suspends the
cycle for `RESUME_AFTER_MS`; a surface under another modal is `frozen`. Held by
`tests/ui/test_auto_scroller.py`,
`tests/ui/test_dialogs.py::test_the_licence_reads_itself` and
`tests/ui/test_guide.py::TestTheDialog::test_it_opens_and_can_be_read`.

**Space chooses a row, exactly as Enter does.** `SpaceChooses` in
`stellody/ui/activating.py` is an application event filter built by
`wire_the_arrows` in `stellody/ui/ring_order.py`. On an unmodified Space to one
of the main window's item views that holds the focus (`holds_the_focus` in
`stellody/ui/ring.py`) with a current row, it sends Return. Enter is `activate`
in `stellody/ui/playing.py` for the list and pane; `open_album_at` in
`stellody/ui/viewing.py` for the grid (`tests/ui/test_space_chooses.py`).
`RingedMenuBar` in `stellody/ui/menu_bar.py` turns Space on a menu item into
Return (`tests/ui/test_menu_ring.py`).

**The discovery results answer their own keys.** Each list is a `ResultsList`
in `stellody/ui/results_tree.py` setting `keeps_horizontal_keys`; Enter or
Space chooses inside the list. `focusInEvent` makes the first row current only
on `ASKING_FOR_A_PLACE` with nothing current. `_state_ring` in
`results_dialog.py` states the Tab order; `QTreeWidget#ResultsList::item:focus`
is the one rule that rings a row. `BoxedTicks` in `results_ticks.py` draws an
empty box under a tick (Oliver's ruling). Held by
`tests/ui/test_results_keyboard.py`.

**Tooltips.** `stellody/ui/tips.py` shortens the delay and marks every window
`WA_AlwaysShowToolTips` (`tests/ui/test_tips.py`); `AlbumTile.helpEvent` in
`stellody/ui/tiles.py` shows a cut name whole (`tests/ui/test_tile_names.py`);
`stellody/ui/hover_paint.py` repaints a ring a popup left stale
(`tests/ui/test_leaving_under_a_popup.py`).

## Coverage

The gate is 100% branch coverage over `stellody.domain` and
`stellody.application`: the layers reachable with no filesystem, no clock and
no audio device. Infrastructure and UI sit outside the gate, since much of
them needs a real device, library or the Windows shell. What the suite's
harness guarantees is in [`TESTING.md`](TESTING.md).
