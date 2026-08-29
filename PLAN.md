# Plan

What Stellody has not built yet, in the order it is worth building.

This file exists because the plan lived in a conversation and the conversation
ended. It is rebuilt from the tree as it actually stands, read module by
module. Where the code and the shorthand disagree, the code wins.

## How this file works

- **Only open work is listed.** A milestone that ships is deleted outright,
  never rewritten as done and never archived. What was built is recorded in the
  release notes and in the history; a plan that carries its own past stops being
  a plan and becomes a diary.
- **Each milestone states what done means**, in terms of something observable,
  so finishing it is a measurement rather than an opinion.
- **The invariants are not repeated here.** They live in `ARCHITECTURE.md` and
  in the structural tests; they constrain every milestone below: the library
  is never written to, nothing reaches the network, the domain stays pure,
  modules stay under the cap, domain and application hold 100% branch coverage.
- **The order is a recommendation, not a contract.** The dependencies named in
  each milestone are real; everything else can be taken in any order.

## The first release

Version 1.0 is a readiness call for the owner to make, so nothing below is
sized against it. `VERSION` holds the number for the release being cut and no
tag has been cut yet, so nothing is owed there either: the work is what goes
into it.

The README now describes only what the binary does, so the honesty half of the
first release is met. What remains inside its scope is the position display:
milestones 1 and 2, then the amplitude monitor that shows position at all.
Cover art, search, ratings and the rest come later, the wider formats and
video among them.

Cutting it means: the milestones in scope are done, the gate is green, the
release notes are written in `NOTES.md` (which is never staged), then the tag
and the release are the owner's to make.

## 1. Play something

Everything this milestone asked for is written: the playback port is bound in
the composition root, the transport sits centred in the tray, a track is
activated from the tree by double click, by Return or from the right click
menu; the library highlight follows whatever is playing. Volume and mute
arrived alongside, ahead of the plan.

Playing, pausing and resuming have been exercised in the built application by
the owner, so those are confirmed. Two parts of the closing condition have
not been watched in the built application: the queue moving on by itself at
the end of a track, then quitting mid-track leaving no process behind. Both
hold in the tests; neither has been seen in the binary.

Seeking is still absent, deliberately. Where playback has reached is shown by
milestone 3 rather than by a plain bar, so this milestone carries no position
display at all.

Done when: the two unwatched parts above are seen in the built application.
That is the owner's observation to make, not a test's.

Blocks: every milestone below except 6.

## 2. Report the position that is audible

Measured last session: `position()` reports DECODED frames, which run about one
buffer ahead of what is coming out of the speakers. A progress display fed from
it drifts ahead of the music by that much.

The correction belongs with the transport rather than in the engine, because the
size of the lead is a property of the buffer the transport chose.

Done when: the reported position matches what is audible to within a buffer;
a test pins the correction against a known buffer size.

Depends on: milestone 1.

## 3. The amplitude monitor

Where a track has reached is shown as a line crossing the track's own waveform,
rather than as a bar filling up. The amplitude is the point: it says what is
coming as well as how far in the track is.

The shape has to be computed rather than watched, since it covers the whole
track including the part not yet played. That is a decode of the file ahead of
playback, so it is done off the interface thread and cached beside the artwork,
keyed on the source rather than on the track: a cue sheet album is one file
holding many tracks, so one shape serves all of them.

Needed: an envelope of peaks per bucket, a cache that survives a restart, a
widget drawing it in the palette's own colours, plus a playhead driven by the
position that milestone 2 makes honest.

Done when: playing a track draws its shape immediately from the cache or
within a second or two of starting without it, the line crosses the shape in
time with the music; a track played twice does not decode twice.

Depends on: milestones 1 and 2.

## 4. Show the cover art

The scan already records one image path per source, chosen by the ripper-name
ranking in the walker, so the data is in the store. Nothing loads it.

Needed: a cache under the data directory keyed by the album identity handle that
`stellody/domain/identity.py` already provides, a decode step off the interface
thread, plus a delegate that draws it in the library.

The grid view is wanted, confirmed rather than assumed, so it is milestone 4
rather than an open question. This milestone is the artwork itself, which that
view needs.

Done when: an album with embedded or sidecar art shows it, an album without one
shows a placeholder rather than a gap; a rescan does not rebuild a cache
entry that is still current.

## 5. A grid of covers, toggled with the text view

Confirmed as wanted: both views, with a toggle between them rather than one
replacing the other. The text view in use today stays exactly as it is.

The toggle itself is already drawn, at the left of the bottom strip, disabled
and saying so in its tooltip. It is named in the focus ring; the tray takes
a handler for it with a no-op default, so this milestone enables it rather than
placing it.

Needed: a second view over the same model, that toggle enabled and wired, plus
the choice remembered like the theme and the sort order already are.

Done when: the toggle switches between the two views, each keeps the sort order
the other was using; the choice survives a restart.

Depends on: milestone 4, which is what a grid of covers has to draw.

## 6. Search the library

The schema has five plain tables and no search of any kind. The README's
stack table used to name FTS5; it no longer does, so this is a gap rather than
a broken promise.

Needed: an FTS table fed as sources are saved, a search box, plus a filtered view
that leaves the sort order alone.

Filtering by rating and by play count is wanted too. Those columns arrive with
milestone 7, so the filter is built to take a condition rather than a phrase
alone; it gains the second kind when there is something to read.

Done when: typing part of an album, artist or track title narrows the library as
you type; clearing the box restores it.

## 7. Ratings and play counts

Neither exists: no schema, no column, no code. The README's opening paragraph
used to promise both as the reason Stellody keeps its own store; it now says
only what the store actually holds.

They are worth naming together because they share a decision: a play count means
nothing until playback exists and something decides what counts as a play.

Both are wanted, as is filtering by them later, so each is stored as a first
class column rather than derived: milestone 6 filters on what
this one records.

Done when: a rating can be set and survives a restart, a completed play
increments a count; neither ever reaches the music files.

Depends on: milestone 1, for the play count half.

## 8. Repeat one track

Shuffle and repeat both shipped: shuffle takes a permutation of the album and
keeps playing whatever is playing, repeat carries the end of the queue round to
its start; each is remembered between sessions. A queue holding one track
already repeats that track, because wrapping lands back on it.

What is missing is repeat-one as a MODE, so a single track can be held on
repeat inside a queue of many. That is a third state on a switch drawn with one
piece of artwork, so it needs a second image before it needs any code.

Done when: a track can be set to repeat on its own within a full queue, the
switch shows which of the three states it is in; the choice survives a restart.

Depends on: milestone 1.

## 9. Gapless transitions

Not present. This is the hardest item here: it wants the next track decoding
before the current one ends, plus a device that is not stopped and restarted
between them.

Worth doing properly or not at all, since a nearly gapless player is more
irritating than an honestly gapped one.

Done when: two tracks that run together on the disc run together through
Stellody; a test measures the seam rather than a listener judging it.

Depends on: milestone 1.

## 10. The equalizer

Entirely absent. Needs a decision before any code: either a fixed set of
bands applied to the decoded buffer or nothing at all.

Done when: the bands change what is heard, the setting survives a restart;
switching it off costs nothing in the signal path.

Depends on: milestone 1.

## 11. macOS and Flatpak

Windows first, which is where it stands. macOS and Linux come later, built to
the house pattern rather than invented here: `build_flatpak.sh` with
`clean_flatpak.sh` for Linux and `builddmg.py` for macOS, taking ClearBudget as
the worked guide and stripping every inherited specific.

The audio layer is the part that does not travel. `WasapiPlayback` is named for
a Windows interface and speaks to one; the playback port it sits behind is
already the seam a second output goes in at. So this milestone is two pieces:
the packaging, plus an output that works where WASAPI is not.

Done when: a Flatpak and a DMG are built by their own scripts, each plays
audio; the Windows build is untouched by either.

Depends on: milestone 1, since there is no point porting an engine nothing
uses.

## 12. Play every audio format, not only FLAC

Stellody takes `.flac` and nothing else: one suffix in the walk, a probe that
reads FLAC stream info, a README calling it a FLAC player. A local library of
any age holds more than that.

**Measured, so the size of this is known rather than guessed.** The decoder
already behind the application is libsndfile 1.2.2, which reads FLAC, MP3, WAV,
AIFF, OGG, W64, CAF, AU and a long tail of older formats. So the work divides
in two; the first half is far cheaper than it looks:

- **What libsndfile already decodes.** Extend the walk beyond one suffix,
  replace the FLAC-only probe with a general one (mutagen reads tags for
  everything in this list), then let the existing decode path serve it. No new
  dependency, no new licence, no change to the audio path.
- **What it does not.** M4A with AAC or ALAC, WMA, Musepack, Monkey's Audio,
  WavPack, DSD. Each needs a decoder Stellody does not carry, which means
  either FFmpeg through a binding or Qt Multimedia.

That second half asks the same question milestone 13 asks, so answer it once:
**one media backend, chosen for both**. Deciding it separately is how a player
ends up with two decoders that disagree about what a track is.

Honesty applies as usual. A lossy format cannot be bit perfect however the
device is opened, so anything the interface says about exclusive output has to
say that too.

Needed: suffixes from one table rather than a literal, a probe that reports what
each format actually states (a missing bit depth is honest for a lossy file,
not an error), the decode extended, plus the README's opening line rewritten:
this stops being a FLAC player the day the first half ships.

Done when: an album in each of the formats in the first half scans, groups and
plays; a format Stellody cannot decode is reported as unreadable rather than
silently skipped.

## 13. Play video files

Wanted, though after the first release. A local library holds more than audio: a concert film sitting
beside the albums it came from is part of the same collection.

This is the one milestone that changes what Stellody IS, so it changes several
things that currently assume audio: the walk takes only FLAC today, a track is
a slice of an audio file, the output port speaks to a sound device. A video
needs a surface to draw on, a second stream kept in step with the sound, plus a
window that can give it room without the library view losing its place.

Decide before any code: either Qt Multimedia, which brings a player and a
surface for nothing while deciding the decode for us; else the existing decode
beside a video decoder, which keeps the audio path bit perfect at considerably
more cost. The first is the honest default; the second is the one to
argue for, not to assume.

Needed: the walk extended to video containers, a track that knows it carries
picture, a video surface in the window, plus the transport driving both streams
from one clock.

Done when: a video file in the library plays with its sound in step, the
transport controls it exactly as it controls a track; closing it returns to the
library where it was left.

Depends on: milestones 1 and 2, since it is the same transport. Shares its
backend decision with milestone 12.

## 14. Accept the repairs the health report describes

The report says what Stellody worked around. It cannot yet be told "yes, keep
that", so the same 142 findings are recomputed and re-read on every start.

**Most of this already exists.** The store keeps RAW tag values, not resolved
ones; resolution happens on load, which is what lets a rule be improved
without rescanning. So Stellody already reads damaged tags, works out what they
should be and shows the corrected library while the files stay untouched. What
is missing is not the correction. It is anywhere to record that a correction
was accepted, plus any way to prefer yours over the rule's.

**Measured on the reference library**, so the size of this is known rather than
guessed: 142 issues across 36 of the 485 albums. 132 are two files claiming one
track number, 6 are a disc number disagreeing with its folder, 4 are a missing
album artist. Every one of those three kinds already has a resolution rule, so
every one of the 142 has a value waiting to be accepted. The two kinds with
nothing to propose, missing artwork and an unreadable file, did not occur.

### An overrides table, not a file

One row per accepted correction in Stellody's own store: what it applies to,
which field, then the value. Resolution gains a third layer, applied in this
order: raw tags, then the automatic rules, then the accepted overrides on top.

This keeps the invariant that the project exists for. An override is Stellody's
own state, written where Stellody's own state lives, so nothing is written to
the music folder, sidecar or otherwise. Exporting corrections for another
player to read is a different feature and is not this one.

### Keyed by album identity, with the path as a tiebreak

A file path is precise until the album is re-ripped or the folder renamed, at
which point every correction is silently lost. The album identity handle in
`stellody/domain/identity.py` survives both, which is why the artwork cache is
already keyed by it. Store the path alongside, so two identical albums in one
library can still be told apart.

### Accept all, else the feature is worse than not having it

142 prompts is not a workflow; a library twice the size makes it ten times
worse. Three granularities, all of them one gesture:

- accept everything the report lists,
- accept everything in one album, which matters because the findings cluster
  into 36 albums rather than spreading evenly,
- accept one finding.

Accept-all is the DEFAULT path through this screen, not a power-user shortcut
hidden behind the per-issue flow. The per-issue accept exists for the case
where the rule guessed wrong about one track.

### Nothing accepted is permanent

Accepting in bulk is only safe if it is reversible, so the same three
granularities undo: reset everything, reset an album, reset one finding. A
reset drops the override row and the automatic rule shows through again. There
is nothing to corrupt, because the raw tags were never altered.

### What it must not do

An override never reaches a music file. A rescan never discards one: a
correction outliving the scan that prompted it is the whole point. An issue
whose kind proposes no value, missing artwork or an unreadable file, is
reported and cannot be accepted, since there is nothing to accept.

Needed: an overrides table keyed by album identity, that third layer in the
load-time resolution, an accept and a reset at each of the three granularities,
plus the two repair buttons enabled: the one on the bottom strip and the one
pinned at the top of the health dialog, both of which are already drawn and
already wired to a seam that does nothing.

Done when: accepting everything the report lists empties it in one gesture, the
library shows the corrected values, both survive a restart and a rescan, then
resetting brings the original findings back; no music file has changed, which
the read-only structural tests already prove.

## 15. One loudness across albums

Albums are mastered at whatever level their era and label chose, so moving from
one to the next means reaching for the volume. Stellody should play them at a
comparable loudness, on by default, remembered between runs.

**Album gain, not track gain.** The point is that albums sit level with each
other, so the whole album moves by one figure and the quiet track stays quiet
against the loud one beside it. Track gain would flatten exactly the dynamics
the album was mastered with.

**The tags are not there.** Measured over 60 albums sampled at random from the
library, three files each: not one carried a ReplayGain or R128 tag of any
kind. So reading what the files already say, which would have been nearly free
since the probe collects every tag as it walks, does nothing at all here. The
loudness has to be measured.

**Measuring it is affordable but not free.** Decoding and measuring one album
of 42 minutes took 3.0 seconds, about 841 times real time. At that rate a
6,877 track library is roughly 33 minutes of one core, against 2.5 seconds for
the ordinary scan that reads tags alone. So it cannot ride along quietly with a
scan. It is either a pass the user starts and watches or work spread behind
playback; that decision is the one this milestone opens with. Whichever is
chosen, an album that has not been measured plays at unity rather than waiting.

**Where it is applied.** The engine already multiplies each decoded block by
the volume, so the album's gain multiplies into the same figure: no second
signal path and nothing to switch on and off in the hot loop. The measured peak
is stored beside the gain; the applied gain is held below the point where that
peak would clip, an album asking for more is left at the loudest that
does not.

**Where it is kept.** In Stellody's own store, keyed by album identity, never
written back into the files: writing tags is a non-goal enforced by a
structural test, which this does not change.

**Its state.** One setting, on unless the user turned it off. An absent setting
reads as on, so a fresh install has it on without the setup program being
involved at all, unlike shuffle and repeat, which default off and therefore
need clearing when a reinstall inherits the directory.

Done when: two albums that differ by a known amount in measured loudness play
within one decibel of each other with it on, differing by the original amount
with it off; the setting survives a restart; an album with no measurement plays
at exactly unity, with the same samples the file holds.

Depends on: milestone 1.

## Not planned, so that this is not revisited

- **Streaming, ripping, device syncing and tag writing.** Named in the README as
  deliberate non-goals. The last of them is enforced by a structural test rather
  than by intention.
- **Anything over the network.** No cover lookup, no scrobbling, no telemetry,
  no update check. The absence is the feature. Handing the donation link to a
  browser is not an exception to this: the address goes outward and the
  browser does the asking, so Stellody still opens no connection of its own.
- **Encryption at rest.** The store holds library metadata, not secrets; the
  README says so plainly.
- **Repairing the files themselves.** Milestone 14 records a correction in
  Stellody's own store and shows it on load. It never writes one back; no
  amount of accepting changes that.
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
