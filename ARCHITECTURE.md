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
| 10 | A ring belongs to a control; to every control. No container is named as a ring target, no item view wears one in any state, no pane reaches the window's focus chain; every control that Tab can land on shows a ring, either named in the stylesheet or painted by itself, walked off the real widgets rather than off a list. A checkbox is always the ringed subclass, never Qt's own. | `tests/ui/test_focus_rings.py`, `tests/structural/test_rings.py` |
| 11 | A read-only page is never focused by a click; it is a stop only while it overflows. | `tests/ui/test_reading_panes.py` |
| 12 | Exactly two modules may open a connection, each named with what it is for; only the composition root may name them. Nothing on the scanning, drawing or playback path can reach the network at all. | `tests/structural/test_offline.py` |
| 13 | No control tells a listener that what it does has not been built. Swept off the real widgets of the window and of the dialogs, rather than checked where one was reported. | `tests/ui/test_unbuilt_words.py` |

Invariants 1 and 2 are the reason this project exists. The library that
Stellody was built for was damaged by a player that wrote tags back into the
files, duplicating and overwriting metadata across 33 albums. Stellody
describes a damaged tag; it never repairs one.

Invariant 13 was written after it had already been broken. The repair control
shipped enabled while its tooltip still said "not built yet": enabling a feature
and rewording the thing attached to it are two edits and only one was made. It
is swept rather than checked in the one place it was noticed, for the reason the
menu bar is swept; it is held by a planted claim plus the original wording put
back and watched to fail.

Invariant 12 is the second of that kind. A local-first player that quietly
talks to the internet is not local-first whatever its README says, so the
guarantee is held by a test rather than by a promise. It permits two modules
and no others. `stellody/infrastructure/cover_search.py` is reached when
somebody asks for a cover; `stellody/infrastructure/update_source.py` asks
GitHub whether a newer Stellody has been published. The composition root is the
only thing that may name either, so the reach outward stays two named things
rather than a capability spread through the application.

The count in that test is the point of it. Going from one permitted module to
two was an edit somebody had to make and defend; a guard written as "the
network is used sparingly" would have allowed the same change silently. The
update check is also the only one of the two that speaks without being asked,
which is why what it sends is worth stating exactly: nothing. Not the library,
not an identifier, not the running version. It reads a public document about
Stellody and compares it locally.

## Layers

```
UI  ->  Application  ->  Domain  <-  Infrastructure
```

| Layer | Contains | May import |
|---|---|---|
| `domain` | Values and rules. Frozen dataclasses, pure functions. | The standard library, minus anything with a side effect. |
| `application` | Ports as Protocols, plus use cases. | `domain` and the standard library. |
| `infrastructure` | SQLite, mutagen, soundfile, PyAV, sounddevice, Qt's image codecs, the filesystem. | `domain` and `application`. |
| `ui` | PySide6 widgets, models, dialogs, the colour tokens in `palette.py` and the stylesheet built from them in `theme.py`. | `domain` and `application`. |
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

163 of the 482 albums in the reference library are built from a cue sheet
rather than one file per track, 157 of them a single FLAC holding the whole
album, so this is a main path rather than an edge case. Because the
distinction is captured in one value object, the queue, the transport and
shuffle are written once and work for both shapes without knowing which they
hold. The amplitude monitor inherits the same property: a shape is measured
for the file, then each track takes its own share of it. The grid of sleeves
and the album pane under it inherit it too: both are views over the same
albums, so neither knows which shape a track holds.

**Two readers satisfy it; nothing above them can tell which it holds.**
`AudioSource` in `stellody/infrastructure/decode.py` is the shape both answer
to; `open_source` chooses by suffix and is the only place that knows there are
two. `SourceReader` covers everything libsndfile can address by frame.
`PacketReader`, in `packet_decode.py`, covers M4A, which arrives as packets
carrying timestamps rather than as addressable PCM; it counts those back
into frame positions so that a cue slice, the equalizer, the visualiser and
gapless all keep working without a line changed.

Three things there were measured rather than assumed; each is a comment in
the file next to the code it explains. The timestamps do not start at nought:
an iTunes AAC file begins at 2112, the encoder priming, so a reader ignoring it
starts every track 48 milliseconds in. A seek needs pre-roll: landing on the
packet holding the wanted frame and decoding from there differs from the same
frame played forward by half of full scale, because the codec is being asked to
start cold. And the container is genuinely reopened on every seek rather than
merely seeked, because a decoder that has already decoded does not come back
clean and an explicit flush of its buffers does not clear it; at the start of a
track there is no pre-roll to hide that, so it would have reached the speakers.
Reopening costs under a millisecond against a read block worth ninety.

**PyAV is imported inside `open_source`, not at module scope.** Importing it
loads a shared FFmpeg build of some sixty megabytes. A library holding no M4A
never pays for it and one holding a few pays only when a track from them is
opened. That is the single reason for a function-level import in this codebase.

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
own choosing. That view reports; a second screen accepts. Two repair controls
open it: one on the bottom strip beside the rescan whose findings it answers,
one pinned at the top of the health dialog. Their tooltip is stated once in
`stellody/ui/bottom_tray.py` and read from there by the dialog, so the two
cannot come to say different things about one feature; whether either can act
is answered once as well, in `can_repair`, so they cannot disagree about that
either. Both are disabled where there is nothing outstanding to accept and
nothing already accepted to take back, since the screen would open saying
nothing. See "Accepting a correction" below.

`stellody/domain/ordering.py` holds the track rules, `stellody/domain/grouping.py`
the album rules and `stellody/domain/health.py` the reporting vocabulary.

## Accepting a correction

**Resolution has three layers: the raw tags, the automatic rules, then whatever
has been accepted on top.** The store holds raw tags and resolves on load, so
the library already showed corrected values; what was missing was anywhere to
record that a correction had been ACCEPTED, which is why the same findings were
recomputed and re-read at every start. `stellody/domain/overrides.py` is that
record and `assemble_albums` applies it, so a load and a scan get it from one
place rather than two that could disagree.

**What is pinned is the value the rule proposed.** Accepting is a listener
saying "yes, keep that" about a correction Stellody already made, so the library
does not move when a report is accepted; what changes is that the finding stops
being reported and the value stops depending on the rule that suggested it. The
domain will apply a DIFFERENT value and is tested for it, so preferring one of
your own is a decision rather than a rewrite; nothing in the interface sets one.

**An override is keyed by the album's identity handle, with the path alongside.**
The handle survives a folder rename and a re-rip, which is why artwork and
ratings already use it; it is stated once as `AlbumIdentity.handle` rather than
digested again per user, since three spellings of one value is three chances for
two of them to drift. The path is the tiebreak, so two identical albums in one
library are still told apart; it also names the file a track-level pin is about.

**Two albums that resolve alike are told apart; only those two.** Tags alone
cannot separate two recordings of one work: a symphony under two conductors
carries one composer, one title and often one year, so both answered to one
handle. They then shared a cached cover, an album rating and every track rating
under it; a correction accepted on one was looked up against the other,
matched no file and recorded nothing, so it was reported again at every start
however many times somebody accepted it. That was found in a real library, not
reasoned about.

Assembly now compares the identities it has built and gives each of any that
collide the place it was found, which is the one thing that differs. The
separation is appended to what the handle is digested from rather than joined in
as an empty part, so an album nothing collides with digests exactly the run of
text it always did: its cover and its ratings are found again rather than
orphaned by the rule arriving. A test pins that digest to its literal value,
because a refactor that quietly moved it would empty every library's ratings
with every gate still green. The two are told apart in the records alone; both
still read the same on screen.

**A lossy copy of an album already held lossless is not a second recording.**
That distinction was not needed while M4A could not be decoded; the moment it
could, the rule above did real damage. A lossy rip collided with the lossless
one already in the library, both were told apart, so the album that had been
there for the library's whole life had its handle moved: its cover, its album
rating and every track rating under it orphaned by the arrival of a worse copy.
Three albums in the reference library went that way; the first anyone knew
of it was a report saying they were no longer found.

`stellody/domain/duplicates.py` answers it in two places; the exception is
narrow on purpose. Inside one folder a lossy file is dropped only where a
lossless file claims the same disc and track number AND runs the same length:
The Dance held 17 FLAC and 17 M4A of one performance and listed all 34.

The length is not belt and braces; it is the evidence. The first version of
this rule paired on the number alone, which cannot tell a copy from a variant:
an album may hold a studio take and a live one at one number, while the lossy
rip here titled every track "(Live)" where the lossless one did not, which is
exactly the shape that should stop anybody. Measured, all seventeen pairs
agreed to within 0.7 seconds and most to within 0.1, which is a lossy encoder's
padding rather than a different performance. A pair whose lengths disagree is
two recordings and both are kept, because dropping a file is the one
irreversible thing the rule does. Across folders the lossless copy
keeps the plain handle and only the copies are told apart, ONLY where
exactly one of the colliding albums is lossless. None lossless or several
leaves every one of them told apart exactly as before, which is what keeps the
four genuine collisions already in the reference library, all classical, all
lossless on both sides, behaving as they always have. Widening it would have
orphaned those four to fix three.

**A stated bit depth is what separates the two kinds, not a list of suffixes.**
The probe reports no depth for a format that states none, so the distinction is
one the library already draws and already tests. The pairing reads a missing
disc number as the first disc, which is not a nicety: measured on the reference
library, the FLAC rip of The Dance states no disc at all while the M4A beside it
states disc 1, so compared as written every one of the seventeen pairs missed.

**A finding is silenced only where the whole of it is pinned.** Half an accepted
finding is still a finding: reporting it would be wrong about what is
outstanding while dropping it would hide the part nobody answered. A kind that
proposes no value can never be silenced, because it is absent from
`FIELD_FOR_KIND`; that absence IS the rule, rather than a second list to
disagree with the first.

**A finding names FILE NAMES while a pin names a full path.** They have to be
introduced; one name can stand for two tracks, since a multi-disc album
merged from CD1 and CD2 may hold `01 Intro.flac` in both. Every track wearing
the name is pinned rather than a guess being made about which was meant; pinning
a value a track already holds costs nothing. The matching needs a basename, so
it lives in `stellody/application/repairs.py` rather than in the domain, which
may not import `os` at all.

**The findings and the accepted set are two lists, not one.** This is forced
rather than chosen: a finding that has been accepted leaves the report, so it
cannot also be the thing pointed at to take it back. What the screen offers
instead is the accepted set grouped by album and field, which is the same unit
read from the other side. Reset takes a group, an album or the lot; the lot asks
first and names the count, being the one gesture that undoes an unbounded amount
of work in a single press.

**A store that cannot be read must not cost the library its assembly.** A row
naming a field this version does not know is skipped; a pinned number that is
not one or that no track could hold is ignored rather than raised over. The
asymmetry is the reason: one correction nobody sees applied against a library
that fails to assemble at every start with no way back in.

**None of it reaches a music file.** An override is Stellody's own state, kept
in Stellody's own database beside the ratings and the settings. Resetting drops
a row and lets the automatic rule show through again; there is nothing to
corrupt, because the raw tags were never altered, which invariants 1 and 2
enforce rather than describe.

## Scanning

The walker lists folders, the probe reads tags out of one file and the store
caches a whole folder's result. A rescan compares each file's size and
modification time against the store; a folder whose files are all unchanged is
reused without opening a single file. On the reference library a cold scan of
510 folders and 4,870 files takes about two and a half seconds and a rescan
a little over four tenths of a second.

**The counts and the timings here were read at different widths of the walk, so
they are stated apart rather than blended.** The widened walk reports 530
folders holding 5,101 music files, grouping into 502 albums of 7,108 tracks;
that is the library as it now stands. The timings above and every other library
figure in this document were measured while the walk took FLAC alone, which is
what those 510 folders are: the 487 that are FLAC throughout plus the 23 holding
FLAC beside something else. So the timings are due a re-measure against a cold
scan of the widened library and are left as measured rather than scaled up to
fit the newer counts, since a figure nobody took is worth less than a figure
with a reading behind it.

**The store holds raw tag values, not resolved ones.** Resolution happens on
load, so improving any rule above takes effect on the next start without
rescanning a library.

**What the walker skips is named, never guessed.** An earlier version treated a
leading dot as "hidden" and silently swallowed two real albums, `...And Justice
for All` and `...Nothing Like The Sun`. It now skips a fixed list of system
directories plus macOS AppleDouble stubs; nothing else.

## Formats and probing

**Three tag shapes cover every format, measured rather than assumed.** FLAC and
the Ogg family hand back `(name, value)` pairs already spelled the way the
resolution rules read them, so those pass through whole and nothing a ripper
wrote is discarded. MP3, WAV and AIFF hand back ID3 frames keyed by a four
letter code; iterating one of those yields the codes rather than pairs, so
`ID3_NAMES` in `stellody/infrastructure/probe.py` translates the frames the
domain vocabulary actually reads. A frame nobody reads is left alone rather
than guessed at.

MP4 is the third and it is the one that forced the count up, because the pair
path does not mislabel its atoms, it raises on them. `MP4_NAMES` renames the
atoms and `MP4_PAIR_NAMES` handles the two that arrive as a parsed pair of
integers rather than as the "3/12" text every other format writes; putting them
back into that form is what keeps one set of resolution rules for every format.
Its cover lives in an atom carrying no picture type, so `covers.py` presents
each as a front cover and the existing ordering reduces to size alone.

**A lossy MP4 states a bit depth it does not have; that one had teeth.**
Measured on a real AAC file: mutagen reports sixteen bits per sample, because
the MP4 sample entry carries that number whatever the codec does with it. A
stated depth is exactly what `is_bit_perfect` tests, so passing it through would
have badged an AAC track as delivered untouched. `_bit_depth` therefore honours
the number only for a codec that genuinely stores its samples, which in MP4
means ALAC. The trap itself is pinned by a test, so the suppression cannot be
deleted as unnecessary without someone noticing that mutagen still sets it.

**A date tag is read for its year, never sliced.** What a ripper writes there
has no one shape: a FLAC commonly carries `2003-05-12` while an iTunes rip
carries a whole instant, `2003-08-05T12:00:00Z`, which read straight out put the
timestamp on the row beside the genre. Taking the first four characters happens
to work on both and is not the general answer, since a date is not always
written year first. `year_of` in `stellody/domain/text.py` is the one place that
decides; both the album pane and the row text read it from there. The tag
itself is kept exactly as the file wrote it, which invariant 1 requires anyway.

**What a format does not state is reported as absent, never invented.** Measured
per format: FLAC states both a bit depth and a total sample count; WAV and AIFF
state a depth but no count; MP3, Ogg Vorbis and Opus state neither. A file that
states no depth reports nought rather than a plausible sixteen; a frame count
absent from the file is derived from its length against its own sample rate.
Opus is the one constant here: it always decodes at 48 kHz whatever it was
encoded from and mutagen states no rate for it, so `OPUS_SAMPLE_RATE` records a
property of the format rather than a number chosen here.

**Nought means unstated, which is what keeps bit perfect honest.** `OutputRequest`
refuses only a negative depth; `states_depth` distinguishes nought from a real
value, `depth_is_native` requires it and `is_bit_perfect` is therefore False for
any lossy source in any mode. `open_output` refuses exclusive mode up front with
`NO_STATED_DEPTH` rather than letting the format search fail, so the reason names
the file instead of blaming the device. All three rules were proved by planting
violations: claiming bit perfect for a lossy source, giving a lossy file an
invented depth of sixteen, leaving ID3 frames untranslated.

**`Track` draws the same distinction and must.** It carries its own
`states_depth`, refuses only a negative depth and answers `is_high_resolution`
False wherever no depth is stated, whatever the rate. Opus forces that last
rule: it always decodes at 48 kHz whatever it was encoded from, so a rate test
alone would badge every Opus file as better than CD on the strength of a
property of the codec rather than of the recording.

**The two halves of that rule disagreeing is what
`tests/infrastructure/test_scanning_formats.py` exists to prevent.**
`OutputRequest` was taught that nought means unstated while `Track` still
refused it, yet every gate stayed green: the probe tests read a probe, the
domain tests built a `Track` from real depths, then the branch refusing nought
was fully covered as intended behaviour. Nothing scanned a lossy file the whole
way through, so nothing noticed that the library could not be assembled at all.
The failure was worse than a refused scan, because folder records are written
inside the walk and the library is assembled after it: one MP3 put rows in the
store that `LoadLibrary` then choked on, so every later start failed too. That
test therefore uses the real walker, the real probe and the real store on real
files of every format, asserting through to albums and back out of a reopened
store. It was proved by planting the old rule and watching all six of its cases
fail.

**The suffix table is decided by what can be read, not by what can be decoded.**
`AUDIO_SUFFIXES` in the walker holds `.flac .mp3 .ogg .oga .opus .wav .aiff
.aif .m4a`. CAF is excluded despite libsndfile decoding it, because mutagen
returns None for a CAF entirely, so such a file would scan into an album with
no title. WMA, Musepack, Monkey's Audio, WavPack and DSD need a decoder nothing
here carries.

M4A is the one entry libsndfile cannot open; it is there because a second
decoder was added for it rather than because the rule bent. What the rule asks
of it is unchanged: mutagen has to be able to read its tags. It can, as a
third tag shape the probe was taught. The scope was set by measurement, not by
appetite: of the 126 folders in the reference library holding nothing this
build could decode, all 126 were M4A, 1375 files of it; no WMA, APE, WV,
MPC or DSD file existed anywhere in it to justify writing more.

**There is a second table; nothing is silently absent.** `UNPLAYABLE_SUFFIXES`
names the audio this build knows by sight and cannot decode. A folder holding
only those used to yield no listing at all, so its album was not skipped,
reported or counted: it simply was not there, so a listener looking for one
they own had no way to tell that from a library that had failed to scan. That
was found by somebody going to look for an album they owned.

The walk now yields such a folder and a scan raises ONE finding for it, naming
how many files and which formats. One a folder rather than one a file, because a
library can hold a thousand such tracks and a thousand entries is not a report
anybody reads; what a listener needs is which albums are missing and why.
Nothing is opened to say it, the suffix being the whole of what is known. The
list is NAMED rather than inferred from "not in `AUDIO_SUFFIXES`", since a stray
text file is not a missing album. The finding proposes no value, so it can never
be accepted, which the absence of a field for it in `FIELD_FOR_KIND` already
decides. The unplayable files are left out of a folder's signatures, so a folder
holding nothing else has none and is reused rather than re-listed at every
scan.

## What a scan reports

**A scan answers the question it was pressed to answer.** The status bar already
carried a one-line total and keeps it, which is the right weight for something
nobody asked for; it is the wrong weight for an answer somebody waited on, since
it leaves the screen a few seconds later and cannot say WHICH albums turned up.
So a finished scan also opens a report naming what arrived.

**What changed is a comparison, so it is a domain rule.**
`stellody/domain/changes.py` compares two readings of a library and says what is
different; `stellody/ui/scan_summary.py` turns that into a page and shows it.
The comparison is pure, so what counts as a new album can be tested with nothing
installed.

**An album is new when its identity was not there before; gone albums are
reported too.** The identity is built from tags, so retagging one album can read
as an album leaving and another arriving. Reporting only arrivals would describe
a rename as a discovery, so both halves are shown, with the departures explained
rather than left to alarm: an unplugged drive reads exactly the same way and
nothing has been deleted.

**A track is counted by its source, not by its title or its number.** A source
survives a retag while both of the others can be rewritten by one; the slice
is part of the key rather than the path alone, so a cue-sheet album counts its
tracks apart instead of collapsing to the one file they share.

**Every count is named for what it actually counts.** Reported from a real run:
the report said "Folders read 0" beside "Files read 5101" after a rescan that
changed nothing. Both were true to the field names and false to the reader. The
walk had visited 530 folders and compared every file's size and modification
time; nought was the number it had to open again, so the scan read as having
done nothing rather than as having found nothing to do. The file count was
worse: `files_probed` summed the stats of every record including the reused
ones, so it was the whole library's file count wearing the label of work just
done, naming five thousand files that were never opened. It is now
`files_in_library` and sits under the library's own heading, with
`folders_checked` beside the folders re-read under a separate heading for what
the scan did. A name that says the opposite of what a field holds is the same
defect as the depth rule enforced in one place and not the other; this one
reached a listener rather than a test.

**The window compares what it was showing, rather than asking the store again.**
It holds the previous reading already, so the comparison costs nothing and means
what the reader means by new: new since what was on screen. The runner tears its
thread down before it emits its report, so a modal dialog opened from that
handler has nothing waiting behind it.

**The report is measured rather than given a size.** A scan that changed nothing
says so in six lines while a scan that found twenty albums needs twenty more, so
any fixed height is either a cramped page or a great deal of empty dialog under a
short report, which is what it was. Both dimensions are now taken from the
content: the page is laid out at the widest it may be, asked what width it
actually used, then laid out again at that width to be asked its height. The
tables are sized to their content for the same reason, since at full width every
number was thrown against the right edge, an inch and a half from the label
naming it.

**The measurement is taken on a detached `QTextDocument`; it must be.**
Setting a text width on the view's own document does not hold: the widget puts
its viewport width back. A widget that has not been shown yet is a few dozen
pixels wide, so it reported a page 1853 pixels tall against the 278 it really
is, which clamped every report to the ceiling while looking entirely deliberate.
Two follow-on traps were found the same way and are recorded here so neither is
re-attempted. `idealWidth()` returns the text width back once one has been set,
so a second narrowing pass is a full layout that can never narrow anything.
Releasing the height clamp after measuring lets the page grow back to fill the
dialog on show, which is the empty space the measuring exists to remove, so the
clamp stays.

**The view is made wider than the text by its own frame.** What wraps the text is
the VIEWPORT rather than the widget, so giving the widget the measured width left
the viewport narrower than the width the height was measured at, 618 against 620
as measured, which lets a line wrap that had not wrapped in the measurement and
puts the report past the height it was given. The frame is asked for rather than
assumed, since the style decides it. That exactness is what lets the padding
under the last line be 8 pixels of deliberate breathing room rather than the 26
pixel allowance that was really covering the mismatch.

**Qt rich text is not a browser and the report is written for what it has.** It
supports no `opacity`, so a colour is stated outright rather than faded; an
entity dash renders as a real dash while being invisible to a text sweep for
one, so neither may appear. Both are held by
`tests/ui/test_scan_summary.py::test_the_report_carries_no_dash_and_no_styling_qt_would_drop`,
proved by planting each in turn.

**A modal report hangs a test suite that completes a scan.** `tests/ui/test_launch.py`
patches `ScanSummaryDialog.exec` for exactly that reason, so any later test that
runs a scan to its end has to do the same.

## Searching

**No index, measured rather than assumed.** A full-text table was the first
plan and the measurement refused it. A pass over the whole library, 482 albums
of 6,877 tracks, costs under half a millisecond once the text is normalised,
against the hundred and twenty milliseconds a typed character allows. An index
would also hold the WRONG text, since the store keeps raw tags while the
library shows resolved ones, so a title the resolver corrected would be
unfindable. It would be empty besides: rows are written only where a folder is
probed and a rescan reuses every folder that has not changed, so an existing
library would search nothing until it was scanned cold. SQLite's FTS5 is
available here and is deliberately unused.

Normalising is the part that costs. `comparison_key` over 6,877 titles takes
9.2 milliseconds against 0.24 for a plain fold; the answer cannot change
between keystrokes, so it is done once as the library is assembled.
`stellody/domain/searching.py` is the filter and is pure;
`stellody/ui/searching.py` holds what a load or a scan produced and puts the
answer in front of somebody.

**An album is kept whole.** A phrase that hits one track leaves every track in
place, so the album reads as it always does. The hit is selected as though it
were about to play and its row is then flashed, which gives somewhere to look
rather than a shorter album. Pressing Return asks the same phrase again, since
somebody who has moved off what it found has nothing they could type to get
back.

**A keystroke replaces every row**, which is a model reset. So do inverting
the album order and rescanning. Three consequences, each measured here rather
than reasoned about:

- The pane under the sleeves is left rooted at an index that no longer means
  that album. Untouched it re-roots on the invisible root and lists the whole
  library down both columns, so what was open is put back by opening it again
  rather than by leaving it alone.
- A selected row ignores `BackgroundRole` while honouring `ForegroundRole`, so
  the flash on a row the search has just selected is painted by the delegate
  rather than returned by the model. The writing is never repainted, which is
  why each appearance carries its own colour: banana yellow at 13.33 to 1 in
  the light one, a deep amber at 5.10 to 1 in the dark one.
- `scrollTo` is what opens every level above a row, which a multi-disc album
  needs since its tracks sit under a disc. Expanding the parent alone leaves
  the album shut.

## Ratings and play counts

**Neither is attached to an object or to a path.** A scan rebuilds every album
and every track afresh, so an object cannot be the thing a rating belongs to;
a path is the one thing about a track that a folder rename destroys. The
handle is the album's identity with the disc and track number under it,
digested to sixteen characters, which is what artwork already does and for the
same reason. `stellody/domain/listening.py` holds both the record and the
handle.

**An album is rated apart from its tracks.** The two are different answers, so
neither is derived from the other: a record with one poor track on it is not a
poor record. The album's handle is the same digest over its key alone, which
no track can collide with because no track is numbered nothing. It is set from
the album pane's own header, where a caption says which rating it is: the two
controls look alike and sit inches apart, so leaving that to be inferred would
be leaving it to be got wrong.

**Reaching the end is what counts as a play.** Only the transport can tell an
ending from a track somebody skipped, so it is the transport that says one
happened; it hands over the album with the track, since a record is kept
against an album and since a rescan may already have replaced the track that
just finished. Nothing goes looking for it afterwards.

**The whole log is held in memory and written through.** It holds only the
tracks somebody has actually rated or played, so a library nobody has touched
costs one empty query; a row that had to ask the disk for its rating would ask
once per drawn row. Every change is written as it is made, so there is no save
step to forget.

**The count is read down the rows, never beside the stars.** A figure beside
the stars is about one track and is gone the moment that track ends, which is
the moment a play count becomes worth reading. It sits instead in the detail
cell of each track row, so a record can be read down for what somebody keeps
returning to. The model is handed the log rather than each row asking for it,
so a drawn row costs no query; when a count changes the model redraws that one
row, found by walking the tracks rather than by asking where the track is,
since that search is retried when it misses and spending it here would take
the attempt the highlight needs. The cell text itself lives in
`stellody/ui/row_text.py`, split out of the model when the model reached the
four hundred line cap.

**The stars ride on the position row**, which is the only row that is about
one track rather than about the library. They do not share its rule, though:
the shape belongs to what is audible, so playback owns it, while the stars are
a control somebody acts on, so they belong to whatever is being pointed at.
Otherwise a track picked out while something else played could not be rated at
all, which is the whole of what a rating is for: nothing has to be heard to be
judged. The two agree throughout ordinary listening anyway, since the
highlight follows playback from track to track.

## Gapless transitions

**The seam is crossed inside the engine, by the feeder thread.** At the
moment one track ends, the only thing awake is that thread, halfway through
a run of blocking writes. Nothing can be asked there and nothing can be
loaded there. So the following source is opened while the current track is
still playing and the feeder reads straight on into it. The stream is never
stopped, so the device is handed one unbroken run of blocks.

**The transport finds out afterwards, from a count.** A crossing is counted
rather than signalled, so a poll that was not looking at the moment it
happened still learns about it; the count belongs to the loaded session, so
it starts again from nothing at every load and a stopped device cannot read
as having moved. `stellody/application/following.py` holds both facts.

**What was lined up is kept, not worked out again.** The switches may move
between lining a track up and the device reaching it, so the queue lands
where the music actually went rather than where the rules would send it now.

**A follower is lined up only where it cannot change.** A scattered album
beginning again picks its order at the moment it begins, so there is nothing
to name in advance and that one seam is deliberately left gapped. Lining up
the wrong track would be worse than the gap it saved.

**A follower the open stream cannot carry is refused.** The stream was opened
for one sample rate and one channel count. A source that does not fit needs a
new device, which is a gap however it is arranged, so it is refused rather
than written into a stream that would play it at the wrong speed.

## The equalizer

**Designing the filter and applying it are different jobs.** What a band does
is arithmetic over a frequency and a sample rate, so `domain/equalising.py`
works out the coefficients and can be tested without an audio device;
`infrastructure/filtering.py` multiplies samples and knows nothing about
frequencies. The split is forced as well as wanted: numpy is a framework, so
it cannot appear below infrastructure at all.

**Hand rolled rather than scipy.** A dozen lines of the Audio EQ Cookbook,
against tens of megabytes added to the packaged build for one function.

**A band at nought is dropped, not applied.** A peaking filter at nought
decibels is exactly the identity, so skipping it is the same answer for none
of the cost. That is what lets a flat equalizer cost nothing whatever rather
than little; it also keeps an exclusive stream bit perfect while it is off:
the block is handed back untouched rather than copied. A band at or above
half the sample rate is dropped for the same kind of reason, having nothing
up there to act on.

**One pass over the samples, not one per band.** Measured on a block of 4096
frames, which is 92.9 milliseconds of audio: ten bands cost 25.4 milliseconds
walking the array once per section and 6.9 walking it once with every section
applied to each sample in turn. The cost is the indexing rather than the
arithmetic, which is also why the samples are taken out to a Python list
first. A flat equalizer costs nothing measurable at all.

**The curve is kept where the volume is kept.** Coefficients depend on the
sample rate, so they cannot be worked out until a stream is open; the curve
is held by the engine so one chosen before anything is loaded still applies
to whatever is loaded next; it is redesigned at every load.

## The visualiser

**It shows what the equalizer shapes.** Twenty bars over the ten ISO octave
centres `equalising.py` already defines, so the bars that move are the band the
slider lifts. Somebody with the equalizer open while a record plays can then
see which control owns the sound in front of them. A second set of band edges
would have been a second vocabulary for one idea.

**Two bars to each filter, split at the filter's own centre.** Ten bars across
a few centimetres read as a level meter with gaps rather than as a spectrum. The
pair covers exactly the octave its filter acts on, the split point is the
frequency the slider is named for, no edge exists that the equalizer does not
already have, so the relationship survives the doubling instead of being
traded for it. Dividing again would need only a different count in one place.

**Measuring is split from meaning, as designing is split from applying.** What
a band's edges are and what a magnitude means once measured is arithmetic over
frequencies, so `domain/spectrum.py` holds it and can be checked with nothing
installed. The transform reads the arrays the device is being handed, so
`infrastructure/analysing.py` holds that and calls inward for the meaning.

**It runs AFTER the write, not before it.** The surest way not to delay a
device is to be reached only once the block has gone. A measurement arriving
late is a frame nobody misses; a block arriving late is a gap everybody hears.
That ordering is also what makes it structurally impossible for the display to
alter a sample. `tests/infrastructure/test_watching_the_output.py` compares
every frame written with the display on against every frame written with it
off; moving the measurement ahead of the write and touching the block makes it
fail, which is how that was checked rather than argued.

**What is measured is after the equalizer and before the volume.** The bands
are named for the equalizer, so they should show what it did. Volume scales
every band by the same amount and so says nothing about the music: a display
that shrank as the volume came down would be reporting the knob.

**A short block is refused rather than read as silence.** Every track ends on
one, since the last read is whatever was left over. Reporting silence for it
blanked the display at the end of every piece, which is what the end to end
test found; padding it instead would report a band quieter than the music held,
which is a measurement that is wrong rather than absent. Refusing leaves the
last real reading standing to fall away on its own.

**The measurement is handed sideways, not pushed.** The feeder leaves its
answer where the interface thread can come and take it, as one whole tuple
swapped in; a reader sees the last measurement or this one, never half of each.
A lock there would be the feeder waiting on a painter, which is the one thing
it must never do. A strip that cannot keep up misses measurements rather than
delaying the sound.

**Two clocks, because the rates differ.** A block carries about 93 milliseconds
of audio, so measurements land some eleven times a second, which is slow enough
to read as steps. The strip repaints thirty times a second and lets the domain
decide where a bar has fallen to in between, so the motion is continuous while
every peak in it was really measured. Bars rise instantly and fall at a fixed
rate: the transient is the thing worth seeing; a bar that eased up to it
would arrive after it had gone.

**It has no switch; it is a few centimetres wide.** It was given a band of
the window and an entry in the Sound menu at first. Both were wrong the same
way: the band was room taken from the library for something that is a small
moving thing rather than a feature anybody looks AT, while the entry asked a
listener to decide about it. It now sits in the middle of the bottom strip,
centred by a stretch either side as the transport above it is. It is simply on.
Its width is stated in centimetres and worked out against the screen it opens
on, so the same request means the same size on any display.

**Nothing runs while nothing plays.** The one question left with an answer worth
having is whether there is anything to draw. The timer runs while the music
does and stops when it stops, taking the measurement upstream with it, so an
idle window does no arithmetic for a display of nothing. No analyser exists
while nothing is being measured; that absence IS the switch, so there is no
flag to disagree with it.

**It shows that it is there before it has anything to show.** It had no ground
of its own at first, which measured as one flat colour, the window's: turned on
with nothing playing it was indistinguishable from empty space. It wears the
surface both trays wear and each bar keeps a low mark on the floor, so silence
reads as twenty empty bars rather than as an absence.

## The update check

**Three answers, kept apart.** There is a newer version, this is the newest
one, nobody could be reached. The third is not a failure to report on its own:
a check the clock started says nothing at all unless there is something to
offer, while a check somebody asked for is owed every one of the three, because
they are waiting for an answer.

**The endpoint is the guard.** `releases/latest` answers only with a published
release, never a draft and never a prerelease, so a tag pushed mid-development
is invisible by that contract rather than by this code remembering to filter
it. Nothing re-checks those flags afterwards; a check written twice is a check
that can disagree with itself.

**A version that cannot be read is not newer.** Comparison is between dotted
runs of digits and anything else loses rather than raises. The asymmetry is the
reason: missing an update costs somebody a day, while inventing one tells
somebody their working copy is stale when it is not.

**The question is asked off the interface thread; the answer arrives on it.**
A plain thread asks, then hands the result back through a signal. Measured on
this PySide6, a functor connection takes the SENDER as its context and the
sender is the controller, which lives on the interface thread, so delivery
queues there either way. What the guard actually catches is a worker that shows
the answer itself instead of handing it back, which was verified by planting
exactly that.

**Skip silences a prompt, not the question.** The tag is written into
Stellody's own settings and that release never prompts again, while the next
one prompts normally. A check somebody asks for ignores the skip entirely and
reports the newest version anyway.

The pieces sit where every other feature's do:
`stellody/application/updates.py` holds the comparison, the platform choice and
the service; the `ReleaseSource` port sits in `stellody/application/ports.py`
with its siblings; `stellody/infrastructure/update_source.py` is the adapter,
on stdlib `urllib` rather than a new dependency; `stellody/ui/update_check.py`
is the controller and the dialogs. Invariant 12 is what keeps the adapter the
only new way out.

## Design decisions

| Decision | Reason |
|---|---|
| PySide6 rather than Rust or Go | The requirement is a player that is not buggy. That comes from working where the coverage gate, the structural guards and the delivery lineage already exist. |
| `soundfile` and `sounddevice` rather than `QMediaPlayer` | `QMediaPlayer` cannot present a cue-sheet slice as a track, which is a main path here; it also has no equalizer for the one planned below. |
| PyAV rather than Qt Multimedia, for the formats libsndfile cannot open | The same question the video milestone asks, so it is answered once for both. PyAV reaches the decoder directly, which is what lets a cue-sheet slice stay a slice: `PacketReader` counts packet timestamps back into frame positions and answers the same `AudioSource` as the existing reader, so the equalizer, the visualiser and gapless were not touched. Qt Multimedia would have brought a second idea of what a track is, which is how a player ends up with two decoders disagreeing. |
| The bundled FFmpeg is LGPL, verified rather than assumed | The libraries report "LGPL version 3 or later" from the licence string the build itself computes, read out of the shipped binary. The same build links libx264 and libx265, which are GPL-2.0-or-later and which `avcodec` imports outright, so they cannot be dropped from a package. The decoder lives in `infrastructure`, which is the GPL-3.0 half, so the combination is compatible and the packaged application is distributed as a GPL-3.0 work. Nothing here encodes video; those two arrive as dependencies of a shared build. |
| A lossy duplicate never displaces what is already there | An album's handle is what its cover and every rating are looked up by, so a handle that moves is data lost. Telling both copies apart moved the incumbent's, which is how making M4A visible reported three long-standing albums as no longer found. The lossless copy is the one a listener means, so it keeps the handle; only the copies are told apart. This applies only where exactly one copy is lossless, leaving the genuine two-recording collisions untouched. |
| A track that will not open is reported, never left as silence | Found on a real machine: a checkout whose requirements were not installed had no decoder for M4A, the exception left the transport entirely and the window did nothing at all. A listener cannot tell that from a press that missed. `PlaybackError` is named in the domain so the application can catch a failure without importing the layer that raised it; `DecodeError` and `OutputUnavailableError` are both that error. It is raised rather than reported: the transport lets it out and the window catches it in one place, which is the only place that can give the device back, put the buttons right and say what happened. Reporting it through a callback was tried and was worse, because the press then read as a success: the window said the track was playing over the top of the message saying it would not, with the device still held open behind a track that never started. An unplugged drive and a device another program holds arrive the same way. |
| A pause is not an ending; it is caught in both layers | Reported against a real library: pausing a track then pressing play started it from its beginning. `pause` clears the resume and then stops the stream, so a feeder already past its wait writes into a stream that has just been stopped and PortAudio refuses that write. The failure landed in the branch that means "the track ran out", so a pause set `finished`. Everything downstream then followed correctly from a false premise: `play` declines to start a finished session, so the press did nothing; the poll a quarter of a second later took the ending as real; on the last track of a queue it gave the device back, which is what left the press after it reloading the track from nothing. The write is fixed where it goes wrong: a failure while the resume is already clear is a pause landing on the feeder, so the block in hand is dropped and the loop goes back to waiting. The transport carries the second half, because a device cannot tell a hold from an ending under any circumstances: `_held` is set when a listener pauses, cleared when they resume and taken from `playing` at every load, since a track opened without playing is one somebody is sitting on; `advance_if_finished` does nothing while it is set. Both halves were proved by planting their removal, each against a stream that refuses the write its stop landed in the middle of. |
| Skipping while paused stays paused | Pressing Next while paused started playing, which nobody had asked for. The awkward part is that a track ending arrives through the same method, where playing on is right, while a device that has run out reports itself PAUSED exactly as a paused one does. Whether the move plays is therefore handed in by the caller rather than read off the device: a listener keeps the state they were in, while an ending carries on. Arriving by skipping is also not counted as waiting at a beginning, which is what pressing Back means, so Back after a skip still returns to the start of the track in hand. |
| The runtime is pinned while the development tools keep their floors | A build of one commit has to be the same build whenever it is made, which a floor cannot promise. It matters more here than in most repositories: the packaged application carries a Nuitka flag written for the way one version of PyAV reaches one submodule, so a PyAV or PySide6 release arriving by itself would change the thing that flag is about, with the suite green throughout because the suite runs against whatever the environment holds. `requirements.txt` therefore pins with `==` and `requirements-dev.txt` reads it before adding the tools, so nothing is pinned in one place and floating in another. The tools stay on floors, since a formatter or a linter moving forward is a change to the checks rather than to what is shipped. A pin nothing checks is a comment, so `tests/structural/test_environment.py` asserts every pin is the version actually installed, proved by planting a pin one patch release out and reading the failure name the offender. |
| The checks run in the project's own environment | PyAV was installed into the system Python while the application ran from the venv, so the whole gate reported green, 1544 tests at 100% coverage, while M4A could not be played at all. The suite could not have caught it: it was not running on the machine that was broken. A structural test now refuses to pass anywhere but the venv, a second says everything requirements.txt declares is installed there, then `gate.ps1` names the interpreter so the two cannot drift again. |
| Missing files are flagged, never deleted | An unplugged drive, a failed restore or an interrupted scan must not destroy library metadata. |
| The claim to being the running copy is separate from the channel that reaches it | Asking a listener whether it is there answers "is one running" only once that listener is accepting, which is a race at the exact moment it matters. Ownership is a shared memory claim taken under a semaphore; the channel only carries activation. |
| The ask carries a word rather than being the connection itself | Any process on the machine may open a named pipe, so a connection alone is not evidence that a Stellody wants showing. The word is read before the window moves. |
| Ending the application is said out loud, never left to Qt | Quitting when the last window closes is off, which is what lets the cross leave Stellody in the notification area. Nothing then ends the event loop by itself, so every path that means to leave says so. |
| A file's shape is measured once and shared by its tracks | A cue-sheet album is one file holding many tracks, so measuring per track would decode the same file once for every track cut from it. `stellody/application/shapes.py` slices one measurement; the record is keyed by a digest of the file's path rather than by the path itself, since a music folder's names are arbitrary where a filesystem's are not. |
| A bucket holds how loud it is, not its loudest sample | Reported against a real library: the shape showed maximum height for whole stretches of music. It was measuring the loudest single sample in each bucket; a bucket was then a file divided by two thousand, some 120 milliseconds for an ordinary track. The loudest sample in any 120 milliseconds carrying a drum or a sustained note sits within a few percent of the whole track's peak, so drawn against its own loudest point almost everything reached the top. Measured over three unlike records, AC/DC remastered, Adele and Air's Moon Safari: the median bucket was 0.92 of the track's loudest, between 35 and 46 percent of buckets drew at 99 percent of full height and over half at 90. Air is a gentle 1998 record, which is what rules out mastering as the explanation; it was the statistic. The same three measure as loudness to a median of 0.47 to 0.68 with a tenth of one percent at the top, which is a shape rather than a smear. A transient still survives the drawing, since a column covering several buckets takes the loudest of them. The guard is a file carrying one full scale sample in every otherwise quiet bucket: the old statistic answers 1.0000 for every bucket of it and the new one 0.1037. Kept records are invalidated by a format version, since a peak envelope drawn as loudness would be the old shape wearing the new name. |
| The resolution belongs to the music, not to the file | Reported against a real library once the statistic above was fixed: the shape drew as wide blocks at close to constant height. The count was fixed at two thousand buckets a file, which is about a tenth of a second for an ordinary track while a cue-sheet album of 55.7 minutes holding nine tracks got 1671 milliseconds; its 3:20 opening track took 120 buckets and drew across some 1990 pixels as blocks 16.6 pixels wide. A bucket is therefore stated in time as 100 milliseconds; the count follows from how much music there is, floored at two thousand so a short file is still measured finely and capped at sixty thousand so one long recording cannot run away with the cache. Measured after: that opening track gets exactly 2000 buckets at 0.99 pixels each, a median drawn height of 0.60 with 1.7 percent of it at 90 percent or more; the album's whole record is 224 kilobytes and takes 4.5 seconds to measure. Kept records are invalidated by the format version moving to 3, since a record measured at the old resolution would redraw at the wrong width. The guard is `buckets_for` under four cases, proved by planting a fixed count back into it and reading two of them fail. |
| Levels are rounded where they are measured, not on the way to the record | A measurement differing from its own record by a rounding would redraw slightly differently after a restart, for no reason anybody could see. Four places also holds a record to roughly a third of the size, measured at 13.6 against 34.1 kilobytes on a track at the two thousand buckets a file carried then. |
| A cover is read by one module and kept by another | The module that can open music files should not also be the one encoding and writing them. `infrastructure/covers.py` opens audio and reads a picture out of it, nothing more; `infrastructure/artwork.py` decodes, scales and writes without importing a tag library at all. That is what lets the second be granted permission to write without granting it to anything holding a tag library, which invariant 1 then enforces rather than merely describes. |
| A cover is kept against the album's identity, not a path | A rescan after a folder rename reuses the picture instead of reading it again. What it was read from is recorded beside it and checked against that file's size and modification time, so a cover replaced on disk is still read afresh. |
| One kept size serves every place a cover is drawn | Measured on the reference library, a kept cover is about 30 kilobytes at 512 pixels, against sources whose median is 94 kilobytes and whose largest is 1.3 megabytes. One pixmap then serves both views: it is held at the size the grid draws it and Qt scales it down for a row, so switching view costs no second reading. Changing the grid size does read every sleeve again, out of Stellody's own store rather than out of the music, which is what holds memory to the size chosen instead of to the largest on offer. |
| A row states its own decoration size | A `QPixmap` in `DecorationRole` sizes the row itself and a view's icon size is never consulted for it. Measured here: a 40 pixel icon size on the tree still gave a 166 pixel album row. `RowCover` states `option.decorationSize` in the delegate instead, which takes it to 46. Only a row carrying a picture is touched, so a track stays the height of the line of text it is. |
| A shape is drawn as it is read, not when the reading finishes | Reading a file through is the only way to know how loud each bucket of it is, so the wait cannot be avoided; it can be watched instead. The reader offers the shape so far every five seconds of the music, the bar draws it and the picture builds from the left. Measured cold: an ordinary 28 megabyte track put its first picture up at 0.02 seconds and finished at 0.49; a 272 megabyte album FLAC put one up at 0.01 and finished at 8.17. Only the finished measurement is kept, since a part written down would be wrong on every redraw afterwards without ever looking wrong enough to notice. A part and a finish are separate signals: a runner that could not tell them apart let go of its thread on the first part while the reading carried on behind it. |
| Folding is done by numpy over blocks, not by walking frames | The fold used to step through every frame in Python to find which bucket it belonged to. Measured, that was most of the time: a 60 megabyte track folded in 3.2 seconds a frame at a time and 0.84 vectorised, while a 390 megabyte album FLAC went from 21.8 seconds to 5.3, bit for bit the same answer. |
| A measurement is given up on, never waited out | Reading a file through takes 0.49 seconds for an ordinary track and 8.17 for a whole album FLAC, measured cold; a measurement already kept comes back in 0.6 milliseconds. The bar follows the highlight, so a step through the library replaces a measurement that is very likely still decoding. Asking its thread to quit does not touch a decode, so letting one go used to block the interface thread for the full two second wait: measured at 2.00 seconds a step. The check is therefore handed down to the reader, which gives up at the next block it reads and keeps nothing; letting go never waits. Measured after: 0.2 milliseconds a step, with a shutdown mid-decode in 0.01 seconds. |
| The application keeps an account of its own appearances | A window arriving unbidden cannot be traced after the fact: whatever caused it has finished. `stellody/infrastructure/diary.py` records every show with the frames that led to it, every restore with the door that opened, then each step of a shutdown. It found two faults that reading the source had not. |
| Artwork is local first, with a remote chooser somebody opens | Exactly one album in the reference library lacks local art, so an automatic lookup would buy one cover at the price of the local-first guarantee. A chooser keeps that guarantee for anyone who never opens it. It has to be a chooser rather than a fetch because no file in the library carries a MusicBrainz identifier, so a search has nothing exact to match on and could attach the wrong cover without knowing it had. |
| A chosen cover is kept apart from a read one | A picture somebody chose has no file beside the music to be checked against, so its record carries a chosen marker instead of a size and a modification time. It is therefore never invalidated by a rescan and is preferred to whatever the folder holds, which is the whole point of having gone looking. |
| The store is asked for a cover whatever an album's own files offer | An album with nowhere local to look is the only kind the chooser is ever offered for; a chosen picture has no file beside the music to be found by. A saving that answered such an album without asking the store therefore cost every chosen picture its next restart: it sat in the cache the whole time while nothing asked for it. `AlbumArt.reading` asks the store regardless of what the candidates say. The property that saving read was deleted with it, so it cannot come back by accident. |
| The chooser is injected, so a window without it offers nothing | The lookup reaches outward, so it arrives as an adapter behind a port like every other. A window assembled without one has no entry on its menu at all, which is what lets the whole test suite raise that menu with no network in the room. |
| A refused ask is asked again; a refusal is never reported as an absence | Measured 2026-08-31, MusicBrainz refused 6 of 10 asks for one release at the one a second its own terms request; two asks five seconds apart were refused while a third was answered under three different user agents; the Cover Art Archive answered 4 of 4 in the same minute. So a refusal is neither a rate anybody exceeded nor rare; one ask is not a search: the release search is asked up to five times with a growing pause. What survives all five is carried as a refusal rather than as an empty result, because a service that would not answer has made no claim about the album; "nothing came back for this album" is a claim it never made. Only the search retries; a listing that will not come is one release of several, so the next one is the thing to try. |
| The rating is one control rather than five buttons | Five buttons would each be a stop in the keyboard ring, so reaching past the rating would take five presses; each would carry a focus ring, which would say there are five controls here rather than one. It is one control holding one value, so it is one stop painting one ring. The stars are drawn rather than assembled. |
| Pressing the star a track already sits on takes the rating back | Nought is not a sixth rating; it is the absence of one. The gesture that undoes a thing should be the gesture that did it, rather than a separate clear nobody would find. Stepping down with the arrow keys reaches nought directly instead, since a step that jumped back to where it started would be a trap. |
| The transport is told who to report a play to, rather than being given it | The only place in this application that sets a collaborator rather than injecting one. Whoever is told has to turn a track into the album it belongs to; the only thing that can is the window, which does not exist when the transport is built. The alternative was a transport that knew about the library it plays out of. |
| A narrowing keeps every cover already read | Replacing the rows used to drop the whole cover cache, so each keystroke sent every visible sleeve back to the disk. The pane a search opens is filled in that same call, before any read can answer, so it took the placeholder; the placeholder is painted in the pane's own colour, so the album read as having no sleeve at all. A cover belongs to an album rather than to a run of rows, so the cache is now dropped where the SOURCES are replaced, which only a load or a scan does. The pane also takes a sleeve that arrives after it opened, since reading happens on a thread of its own. |
| A tooltip appears almost at once | Qt holds one back for 700 milliseconds, measured. On a strip of picture buttons the picture is the only name a button has, so that wait means guessing at what each one does. The delay is a style hint rather than a setting, so `stellody/ui/tips.py` is a proxy style answering that one question with 100 milliseconds and every other exactly as the style underneath does. It is built from that style's NAME rather than handed the object, since the application destroys the style it replaces and the proxy would be left holding something already deleted. |
| Every switch says what a press would do, on both strips | One convention for the whole application, arrived at in two steps. The tray always worked this way: the appearance toggle shows the appearance it would move to, the view toggle names the view it would move to and the mute switch is struck through while the sound is on, because that press is the one that silences it. The bottom strip reported its own state instead, on the reasoning that a strip of settings is not a strip of actions. That failed in use: a crossed wheel on a switch doing nothing reads as a refusal rather than as an offer; two strips inches apart also disagreed about what a picture meant. The strip now follows the tray, which is what its own tooltips had always said in words. Repeat's tooltip is the one exception and names the control instead: a two-state switch is fully described by its next press, while three states named one at a time read as a switch stuck the wrong way round. Its picture still names the press, which is the half of the rule that is read at a glance rather than on a hover. |
| The album pane's play button doubles the tray's, so it toggles with it | Two play buttons on one screen that disagree about what a press does are worse than one. It offered to start the open album whatever was already playing; it wears the pause face while something plays now and pauses on a press, which is the rule the tray's button has always followed. It is told what is playing from the one place that already tells the tray, so the two faces cannot drift apart. The faces agreeing was not enough: the presses still disagreed, which is how a paused track appeared to start again. Pausing was handled here while everything else fell through to starting the open album from its first track, so pressing play on a paused track reloaded rather than resumed; on the first track of an album that is indistinguishable from the track beginning again, which is what was reported. Anything with a track loaded is handed to `toggle_playback` now, the one method that decides what a play press means. Starting the open album is what is left, which is the only thing this button can mean with nothing loaded and the one place it may still differ, the tray having no album to be attached to. `tests/ui/test_both_play_buttons_agree.py` asserts the two answer a press identically, proved by planting the old branch. |
| The About button became a Help button with a menu under it | A picture button is named by its tooltip alone, so a button that opens several things cannot be named after one of them. Its tooltip is Help and the menu says what each entry does. The two entries are also on the menu bar's Help menu, since a menu bar is where somebody looks for About before they look at a strip of pictures. |
| A prompt waved away decides nothing | The close prompt set its answer to the offered default the moment it was built, so being dismissed reported exactly what choosing Minimise to tray reported and the caller could not tell them apart: the cross on it minimised the window, while with the remember box ticked it wrote that non-answer down as the standing behaviour. The answer now starts at ASK, which is the word the settings already use for nobody has said; only a button moves it off that. A non-answer takes the whole press back: the window neither leaves nor hides, nothing is written. |
| A three-state switch is told apart by its artwork, never by a fill | A fill behind one unchanging picture says exactly two things, so it could never carry repeat's three. Each state has its own picture instead, made from two files plus a cross composed over one of them at run time rather than a third drawing. The fill was then removed altogether rather than left repeating what the picture already said, in a wash that fought the artwork above it; shuffle lost it at the same time, so one rule reads the whole strip. |
| Holding one track is decided where an ending is noticed, not in `next` | An ending is the question repeat answers; pressing Next is a listener overruling it. Deciding both in one place would make Next dead under repeat-one, leaving no way off the track but the switch. So `advance_if_finished` replays the track while `next` advances under every mode. |
| The colours are kept apart from the stylesheet that applies them | What a colour IS and where it is APPLIED are two questions that change for different reasons. `stellody/ui/palette.py` holds every colour value and nothing else; `stellody/ui/theme.py` builds the stylesheet and re-exports both names, so no caller had to learn about the split. The file holding both had reached the line cap, which is what said so out loud. |
| Where a queue move lands is decided apart from the device | `domain/moving.py` holds what Next, Back and an ending mean under repeat and shuffle, as pure functions of a queue and the two switches. The transport applies the answers rather than working them out, which is what lets the same rule decide both a button press and a seam the engine will cross unattended. Randomness enters as an argument, exactly as time does. |
| The equalizer switch is kept apart from its sliders | Somebody comparing on against off is asking one question; losing the curve they set up to compare with would answer a different one. The two are stored as two settings for the same reason. |
| A boost is clipped at the format's ceiling | A lift can ask for more than a sample holds. The filtering is gathered in floating point and only then put back into the block's own format, because writing an out of range value into an integer array overflows rather than clips, which turns a loud passage into noise instead of a loud passage. |
| What the library is shown as sits beside the search that also changes it | The view toggle, the sleeve size and the equalizer moved up out of the settings strip to join the search box. All four change what is on show rather than what is playing, where the strip below holds what outlasts a track. The three are one child group rather than three loose buttons, so their order is stated once and the tray delegates to it. |
| Opening the whole library is a toggle on its heading | Expand all and Collapse all were on the View menu alone, so this is reach rather than capability: the gesture belongs beside the column of albums it acts on. It is one chevron at the left of the Title heading, this application's own artwork so that the toggle is drawn in the same hand as every other control here. A typed triangle was never on offer, since the font a heading lands in is not decided here while a glyph it lacks shows as a box; measured offscreen, the fallback font carries none of the four triangles. Where the artwork cannot be found the style's own arrow is drawn instead, so a checkout missing its assets shows a toggle rather than a gap. Room for it is kept by `QHeaderView::section:first` in the stylesheet, padded by a width DERIVED in `expanding.py` from the picture plus the space either side of it: written as one number it reserved exactly the picture, which left the chevron touching the word beside it. The picture is fitted once per size rather than per paint, the source being over a thousand pixels square against a heading that repaints on every hover. What a press would do is read off the rows rather than remembered, since a listener opening albums by hand moves the tree without touching this; partly open counts as shut, so one press always finishes the job it looks like it would. The View menu goes through the same object now, because `expandAll` emits no `expanded` for what it opened: the menu was leaving the arrow still offering to do what it had just done. Replacing a tree's heading also throws away what the tree configured on the one it built, measured as three differences: headings centred rather than left, sections that cannot be dragged and a last section that stretches, so all three are taken from the heading being replaced. The heading is not a keyboard stop and does not become one, the menu being the keyboard route. Proved by planting the press away and by freezing the arrow, each failing its own case. |
| A switch of view arrives where the other one was | Only the view on show follows the transport, because the highlight it moves belongs to that view: the tree keeps a current row while the grid keeps one inside the album opened beneath it. The view nobody was looking at therefore knew nothing about what was playing; switching to it arrived at a grid with no album open under it at all. A switch now carries the track the view being left was pointing at, falling back to whatever is playing where it pointed at nothing, so a listener who has browsed away is not dragged back to the music by the act of changing view while one who has touched neither view still lands on it. The arrival takes the same route a press would: the sleeve is PICKED rather than the album opened outright, so the grid travels to it and `_on_album_picked` opens the album underneath, which is what stops an album standing open beneath sleeves that are not it. Proved by planting the carry back out and watching three of its four cases fail. |
| A window that will not fit the screen is maximised, never nudged | Reported as a focus ring missing its right edge on the Help button, which is the right-most control. Measured on the machine it was reported from: the window was not maximised at all, its content was 3440 wide on a 3440 wide screen and Windows had placed it with that content starting 8 pixels in, so its last 8 columns were off the monitor. The ring sits 6 pixels inside that edge, so it was the first thing lost while the icon beside it survived whole, which is why it read as a painting fault. The cause is a units mismatch: `resize` sets the CONTENT size while `availableGeometry` measures room for a whole window; Windows then charges 8 pixels a side for a resize border it never draws. That cannot be corrected by arithmetic, since Qt does not report it: `frameMargins` answers l0 t31 r0 b0 for the very window Windows gives a rectangle 16 pixels wider. What Qt does report correctly is where the content landed, so `fit_on_screen` compares that against the screen at first show and maximises whatever does not fit; moving it instead would need the same frame width that cannot be read. Proved on the real platform rather than offscreen, which draws no frame and cannot see this defect at all: with the guard planted out the content spans 8 to 3447 and sits outside the screen, with it restored 0 to 3439 and inside. |
| The top tray decides how narrow the window may be | Every control in it is a fixed size, so the tray's own minimum is the window's: 1274 pixels as measured. The default width is chosen for the library rather than for the strips, so the minimum is a floor the default is checked against rather than a value it tracks. `tests/ui/test_window_size.py` holds that floor, since nothing else keeps the two in step. |
| Rescan and repair sit on the bottom strip, not in the tray above | The two strips are split by one question: what is playing against what the library holds. A rescan is asked for when something has been added to the music folder, so it is an errand rather than a control a listener reaches for while listening; repair follows it because it is the answer to what a rescan finds. Repair had been moved up beside rescan on the reasoning that it should follow the control it answers, which was right about the pairing and wrong about the strip; the pair moved down together. A hairline keeps the donate button ruled off from them, so the one control that leaves the application is still not reached by accident. |
| A menu entry that cannot act is disabled, as a button that cannot act is | Expand all and Collapse all belong to the list, which is the nested view; the sleeves are a flat grid of albums with nothing inside them to open. Both entries stayed live there and did nothing when pressed. Every button in the application already answers this rule, wearing a ring that says it cannot be pressed; a menu entry was quietly exempt from it only because it is not a button. `viewing.show_covers` is the one place the view changes, so it is the one place that says what the change means for anything else. |
| The whole menu bar is swept, rather than the entry that was reported | Two entries breached the rule above and they were found one at a time: Expand all in the sleeves, then Rescan before a music folder had been chosen, which looked ready and answered "Choose a music folder to begin" once pressed. Fixing the reported one leaves the rest unexamined, so `tests/ui/test_menu_sweep.py` states every entry in the bar against the three situations the enabling turns on and asserts that the table IS the bar. An entry added later with nobody having decided where it can act fails there, which is the half that matters: both defects were entries nobody had thought about away from the view they were written in. Rescan is answered where its state is set rather than inside the errand, so the menu entry and the button on the strip cannot disagree. |
| A stylesheet border needs `WA_StyledBackground` on a plain widget | Both trays were written to be ruled off from the library between them, both said so in `theme.py` and neither drew a line; the top one had gone its whole life that way. Qt fills a plain `QWidget` subclass's background from the sheet while dropping its border unless that attribute is set, with no warning anywhere. Measured on both trays: unset, every edge pixel comes back the surface colour; set, the first and last rows come back the border colour. The attribute is therefore load-bearing rather than decoration, which is why it is stated on each tray with the measurement beside it. `tests/ui/test_tray_rules.py` reads the PAINT rather than the sheet, because asserting the rule is in the sheet is exactly what let this stand: the sheet said the line was there the entire time it was not. |
| Every stop that can be landed on shows a ring, the same one everywhere | The ring rules had been stated one way only: which things must NOT ring. A control with no rule at all passed both checks, so a checkbox shipped as a stop that Tab landed on while nothing on screen reported it, which is worse than not being a stop since the reader is simply lost. The converse is now asserted by walking the real widgets of the window and of the dialogs, rather than against a list, because whoever forgets a rule forgets the list entry with it. Two exceptions are named and reasoned: a zero-size holder has nothing to paint on; the stars paint their own, since five glyphs standing for one value must ring once rather than five times. The stars were also ringing in a colour of their own, a second token nothing else used, so they read blue while the application read green; one name now serves both. |
| A checkbox's ring is painted on its square, not stated in the stylesheet | The ring belongs on the box rather than round the words, because the box is what a checkbox is read as. The sheet cannot draw it there: naming `::indicator` hands Qt the whole subcontrol and the tick goes with it, measured as a square that could not be told ticked from unticked, while a rule scoped to `:focus` alone changes nothing at all. Owning the square in the sheet would mean inventing a checked picture and an unchecked one, which is a redrawn checkbox rather than a ring on Qt's. So `ringed_check.py` paints over the rectangle Qt reports for the square, in the room the sheet's own padding already leaves, taking its two colours from the sheet as properties so the palette stays the single home. The class is then the rule: a structural test forbids a plain `QCheckBox` anywhere but the module that subclasses it, since that is the one way an unringed stop could come back. |
| The sleeve grid travels to a selection rather than snapping to it | A list view counts its scrollbar in items unless told otherwise, so the smallest move it could make was one whole row of sleeves: picking a cover two rows down jumped the grid a row at a time, which is what got reported. Counting in pixels makes the move continuous and a short run over it makes it readable, since artwork that arrives instantly somewhere else has to be found again by eye, which is the thing scrolling to it was meant to save. Where to scroll to stays Qt's answer: the jump it would have made is taken, put back and then travelled, so no second copy of the rules about revealing an item has to be kept in step with its own. Nothing travels while the grid is off screen; otherwise it would still be moving at the moment it is shown. `stellody/ui/gliding.py`, held by `tests/ui/test_gliding_grid.py`, which drives the run by setting its time rather than by sleeping. |
| A cancelled search is silenced rather than stopped | A request already inside `urlopen` cannot be interrupted, so cancelling promises the narrower thing: the answer is not announced. The worker reads its flag after each slow call and before the emit that follows; letting go of it disconnects it as well. Asking who sent an answer does not work here: measured, a queued cross thread signal arrives with no sender, so an identity check against a runner that has just dropped its worker passes exactly when it should fail. `tests/ui/test_cover_worker.py` holds a search open, lets go of it, releases it and watches nothing arrive. |
| A depth of nought means the file stated none; both enforcers say so | A lossy file carries no bit depth to report; a probe answering sixteen would be indistinguishable downstream from a file that really held sixteen, so nought is the absence of a reading rather than a reading of nought. A negative depth is still refused, being a value no file could state. The distinction is drawn in BOTH domain types that enforce it: `OutputRequest.states_depth` decides whether a stream may be opened exclusively, which is what makes `is_bit_perfect` False for every lossy source without the playback rules knowing which formats are lossy. `Track.states_depth` decides whether a track may exist at all and whether it may be called high resolution. Teaching one and not the other produced a library that probed every file correctly then could not be assembled from them, with every gate green, because a test of the probe and a test of the domain each pass while agreeing about nothing. The end to end scan is the only shape of test that catches it, so there is one, on real files of every format. |

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
