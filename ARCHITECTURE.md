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
| 12 | Exactly two modules may open a connection, each named with what it is for; only the composition root may name them. Nothing on the scanning, drawing or playback path can reach the network at all. | `tests/structural/test_offline.py` |

Invariants 1 and 2 are the reason this project exists. The library that
Stellody was built for was damaged by a player that wrote tags back into the
files, duplicating and overwriting metadata across 33 albums. Stellody
describes a damaged tag; it never repairs one.

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
| `infrastructure` | SQLite, mutagen, soundfile, sounddevice, Qt's image codecs, the filesystem. | `domain` and `application`. |
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
own choosing. That view is read-only today. Two repair controls are drawn and
both are disabled: one on the bottom strip beside the rescan whose findings
it would answer, one pinned at the top of the health dialog. Their tooltip is
stated once in `stellody/ui/bottom_tray.py` and read from there by the dialog, so
the two cannot come to say different things about the same unbuilt feature.
They are disabled because the corrections are computed on every load while
there is nowhere yet to keep one that has been accepted. `PLAN.md` milestone 6
is that work.

`stellody/domain/ordering.py` holds the track rules, `stellody/domain/grouping.py`
the album rules and `stellody/domain/health.py` the reporting vocabulary.

## Scanning

The walker lists folders, the probe reads tags out of one file and the store
caches a whole folder's result. A rescan compares each file's size and
modification time against the store; a folder whose files are all unchanged is
reused without opening a single file. On the reference library a cold scan of
510 folders and 4,870 files takes about two and a half seconds and a rescan
a little over four tenths of a second, grouping into 482 albums of 6,877
tracks.

**The store holds raw tag values, not resolved ones.** Resolution happens on
load, so improving any rule above takes effect on the next start without
rescanning a library.

**What the walker skips is named, never guessed.** An earlier version treated a
leading dot as "hidden" and silently swallowed two real albums, `...And Justice
for All` and `...Nothing Like The Sun`. It now skips a fixed list of system
directories plus macOS AppleDouble stubs; nothing else.

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
| Missing files are flagged, never deleted | An unplugged drive, a failed restore or an interrupted scan must not destroy library metadata. |
| The claim to being the running copy is separate from the channel that reaches it | Asking a listener whether it is there answers "is one running" only once that listener is accepting, which is a race at the exact moment it matters. Ownership is a shared memory claim taken under a semaphore; the channel only carries activation. |
| The ask carries a word rather than being the connection itself | Any process on the machine may open a named pipe, so a connection alone is not evidence that a Stellody wants showing. The word is read before the window moves. |
| Ending the application is said out loud, never left to Qt | Quitting when the last window closes is off, which is what lets the cross leave Stellody in the notification area. Nothing then ends the event loop by itself, so every path that means to leave says so. |
| A file's shape is measured once and shared by its tracks | A cue-sheet album is one file holding many tracks, so measuring per track would decode the same file once for every track cut from it. `stellody/application/shapes.py` slices one measurement; the record is keyed by a digest of the file's path rather than by the path itself, since a music folder's names are arbitrary where a filesystem's are not. |
| Peaks are rounded where they are measured, not on the way to the record | A measurement differing from its own record by a rounding would redraw slightly differently after a restart, for no reason anybody could see. Four places also holds a record to roughly a third of the size, measured at 13.6 against 34.1 kilobytes. |
| A cover is read by one module and kept by another | The module that can open music files should not also be the one encoding and writing them. `infrastructure/covers.py` opens audio and reads a picture out of it, nothing more; `infrastructure/artwork.py` decodes, scales and writes without importing a tag library at all. That is what lets the second be granted permission to write without granting it to anything holding a tag library, which invariant 1 then enforces rather than merely describes. |
| A cover is kept against the album's identity, not a path | A rescan after a folder rename reuses the picture instead of reading it again. What it was read from is recorded beside it and checked against that file's size and modification time, so a cover replaced on disk is still read afresh. |
| One kept size serves every place a cover is drawn | Measured on the reference library, a kept cover is about 30 kilobytes at 512 pixels, against sources whose median is 94 kilobytes and whose largest is 1.3 megabytes. One pixmap then serves both views: it is held at the size the grid draws it and Qt scales it down for a row, so switching view costs no second reading. Changing the grid size does read every sleeve again, out of Stellody's own store rather than out of the music, which is what holds memory to the size chosen instead of to the largest on offer. |
| A row states its own decoration size | A `QPixmap` in `DecorationRole` sizes the row itself and a view's icon size is never consulted for it. Measured here: a 40 pixel icon size on the tree still gave a 166 pixel album row. `RowCover` states `option.decorationSize` in the delegate instead, which takes it to 46. Only a row carrying a picture is touched, so a track stays the height of the line of text it is. |
| A shape is drawn as it is read, not when the reading finishes | Reading a file through is the only way to know its loudest sample in each bucket, so the wait cannot be avoided; it can be watched instead. The reader offers the shape so far every five seconds of the music, the bar draws it and the picture builds from the left. Measured cold: an ordinary 28 megabyte track put its first picture up at 0.02 seconds and finished at 0.49; a 272 megabyte album FLAC put one up at 0.01 and finished at 8.17. Only the finished measurement is kept, since a part written down would be wrong on every redraw afterwards without ever looking wrong enough to notice. A part and a finish are separate signals: a runner that could not tell them apart let go of its thread on the first part while the reading carried on behind it. |
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
| Every switch says what a press would do, on both strips | One convention for the whole application, arrived at in two steps. The tray always worked this way: the appearance toggle shows the appearance it would move to, the view toggle names the view it would move to and the mute switch is struck through while the sound is on, because that press is the one that silences it. The bottom strip reported its own state instead, on the reasoning that a strip of settings is not a strip of actions. That failed in use: a crossed wheel on a switch doing nothing reads as a refusal rather than as an offer; two strips inches apart also disagreed about what a picture meant. The strip now follows the tray, which is what its own tooltips had always said in words. |
| The album pane's play button doubles the tray's, so it toggles with it | Two play buttons on one screen that disagree about what a press does are worse than one. It offered to start the open album whatever was already playing; it wears the pause face while something plays now and pauses on a press, which is the rule the tray's button has always followed. It is told what is playing from the one place that already tells the tray, so the two faces cannot drift apart. |
| The About button became a Help button with a menu under it | A picture button is named by its tooltip alone, so a button that opens several things cannot be named after one of them. Its tooltip is Help and the menu says what each entry does. The two entries are also on the menu bar's Help menu, since a menu bar is where somebody looks for About before they look at a strip of pictures. |
| A prompt waved away decides nothing | The close prompt set its answer to the offered default the moment it was built, so being dismissed reported exactly what choosing Minimise to tray reported and the caller could not tell them apart: the cross on it minimised the window, while with the remember box ticked it wrote that non-answer down as the standing behaviour. The answer now starts at ASK, which is the word the settings already use for nobody has said; only a button moves it off that. A non-answer takes the whole press back: the window neither leaves nor hides, nothing is written. |
| A three-state switch is told apart by its artwork, never by a fill | A fill behind one unchanging picture says exactly two things, so it could never carry repeat's three. Each state has its own picture instead, made from two files plus a cross composed over one of them at run time rather than a third drawing. The fill was then removed altogether rather than left repeating what the picture already said, in a wash that fought the artwork above it; shuffle lost it at the same time, so one rule reads the whole strip. |
| Holding one track is decided where an ending is noticed, not in `next` | An ending is the question repeat answers; pressing Next is a listener overruling it. Deciding both in one place would make Next dead under repeat-one, leaving no way off the track but the switch. So `advance_if_finished` replays the track while `next` advances under every mode. |
| The colours are kept apart from the stylesheet that applies them | What a colour IS and where it is APPLIED are two questions that change for different reasons. `stellody/ui/palette.py` holds every colour value and nothing else; `stellody/ui/theme.py` builds the stylesheet and re-exports both names, so no caller had to learn about the split. The file holding both had reached the line cap, which is what said so out loud. |
| Where a queue move lands is decided apart from the device | `domain/moving.py` holds what Next, Back and an ending mean under repeat and shuffle, as pure functions of a queue and the two switches. The transport applies the answers rather than working them out, which is what lets the same rule decide both a button press and a seam the engine will cross unattended. Randomness enters as an argument, exactly as time does. |
| The equalizer switch is kept apart from its sliders | Somebody comparing on against off is asking one question; losing the curve they set up to compare with would answer a different one. The two are stored as two settings for the same reason. |
| A boost is clipped at the format's ceiling | A lift can ask for more than a sample holds. The filtering is gathered in floating point and only then put back into the block's own format, because writing an out of range value into an integer array overflows rather than clips, which turns a loud passage into noise instead of a loud passage. |
| What the library is shown as sits beside the search that also changes it | The view toggle, the sleeve size and the equalizer moved up out of the settings strip to join the search box. All four change what is on show rather than what is playing, where the strip below holds what outlasts a track. The three are one child group rather than three loose buttons, so their order is stated once and the tray delegates to it. |
| The top tray decides how narrow the window may be | Every control in it is a fixed size, so the tray's own minimum is the window's: 1274 pixels as measured. The default width is chosen for the library rather than for the strips, so the minimum is a floor the default is checked against rather than a value it tracks. `tests/ui/test_window_size.py` holds that floor, since nothing else keeps the two in step. |
| Rescan and repair sit on the bottom strip, not in the tray above | The two strips are split by one question: what is playing against what the library holds. A rescan is asked for when something has been added to the music folder, so it is an errand rather than a control a listener reaches for while listening; repair follows it because it is the answer to what a rescan finds. Repair had been moved up beside rescan on the reasoning that it should follow the control it answers, which was right about the pairing and wrong about the strip; the pair moved down together. A hairline keeps the donate button ruled off from them, so the one control that leaves the application is still not reached by accident. |
| A cancelled search is silenced rather than stopped | A request already inside `urlopen` cannot be interrupted, so cancelling promises the narrower thing: the answer is not announced. The worker reads its flag after each slow call and before the emit that follows; letting go of it disconnects it as well. Asking who sent an answer does not work here: measured, a queued cross thread signal arrives with no sender, so an identity check against a runner that has just dropped its worker passes exactly when it should fail. `tests/ui/test_cover_worker.py` holds a search open, lets go of it, releases it and watches nothing arrive. |

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
