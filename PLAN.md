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
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
