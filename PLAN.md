# Plan

What Stellody has not built yet, in the order it is worth building.

This file exists because the plan lived in a conversation and the conversation
ended. It was rebuilt on 2026-08-29 from two sources: the tree as it actually
stands, read module by module, plus the surviving milestone shorthand from the
last session. Where the two disagreed the code won. The four questions it could
not settle were put to the owner on 2026-08-29; their answers are folded into
the milestones below rather than kept as a list of loose ends.

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

## The next release: 0.1.0

Version 1.0 is a readiness call for the owner to make, so nothing below is
sized against it. The near target is a 0.1.0 release. `VERSION` already
reads 0.1.0 with no tag cut, so no bump is owed: the work is what goes in it.

**Proposed scope, for the owner to confirm: milestones 1, 2, 3 and 14.** A music
player that cannot play is not a release whatever else it does; a release whose
README promises an equalizer it does not have is not an honest one. The amplitude monitor
joins that scope because it is how this player shows position at all. Cover art,
search, ratings and the rest are 0.2.0 and later, the wider formats and video
among them.

Cutting it means: the milestones in scope are done, the gate is green, the
README describes only what the binary does, the release notes are written in
`NOTES.md` (which is never staged), then the tag and the release are the
owner's to make.

## 1. Play something

The audio engine was written, tested and then left unreferenced by anything, so
the application could not play a note. The queue, the transport and the buttons
that drive them are now built; what remains is the proving.

Needed: a playback port bound in the composition root, the transport centred in
the tray (previous, play toggling to pause, stop, next), activation from the
tree by double click and by Return, plus an engine closed on quit the way the
store already is.

Volume and seeking are not in this milestone. Where playback has reached is
shown by milestone 3 rather than by a plain bar, so this one ships with the
transport and no position display at all.

Still to do: sound confirmed coming out of a real device, since a test harness
cannot hear one, then the queue behaviour confirmed in the built application
rather than only in the tests.

Done when: a track chosen in the built application plays, pauses, resumes and
stops, the queue moves on by itself at the end of a track; quitting mid-track
leaves no process behind.

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

The grid view the README promises is wanted, so it is milestone 4 rather than
an open question. This milestone is the artwork itself, which that view needs.

Done when: an album with embedded or sidecar art shows it, an album without one
shows a placeholder rather than a gap; a rescan does not rebuild a cache
entry that is still current.

## 5. A grid of covers, toggled with the text view

Confirmed as wanted: both views, with a toggle between them rather than one
replacing the other. The text view in use today stays exactly as it is.

Needed: a second view over the same model, a toggle in the View menu and on the
tray, plus the choice remembered like the theme and the sort order already are.

Done when: the toggle switches between the two views, each keeps the sort order
the other was using; the choice survives a restart.

Depends on: milestone 4, which is what a grid of covers has to draw.

## 6. Search the library

The stack table in the README names SQLite with FTS5. The schema has five plain
tables and no search of any kind.

Needed: an FTS table fed as sources are saved, a search box, plus a filtered view
that leaves the sort order alone.

Filtering by rating and by play count is wanted too. Those columns arrive with
milestone 7, so the filter is built to take a condition rather than a phrase
alone; it gains the second kind when there is something to read.

Done when: typing part of an album, artist or track title narrows the library as
you type; clearing the box restores it.

## 7. Ratings and play counts

The README's opening paragraph promises both, as the reason Stellody keeps its
own store. Neither exists: no schema, no column, no code.

They are worth naming together because they share a decision: a play count means
nothing until playback exists and something decides what counts as a play.

Both are wanted, as is filtering by them later, so each is stored as a first
class column rather than derived: milestone 6 filters on what
this one records.

Done when: a rating can be set and survives a restart, a completed play
increments a count; neither ever reaches the music files.

Depends on: milestone 1, for the play count half.

## 8. Shuffle and repeat

Neither appears anywhere in the source. Both are transport concerns: an order to
take the queue in, plus what to do when it runs out.

Done when: shuffle reorders without repeating a track before the queue is
exhausted, repeat covers both the queue and the single track; both survive a
restart.

Depends on: milestone 1.

## 9. Gapless transitions

Promised in the README and not present. This is the hardest item here: it wants
the next track decoding before the current one ends, plus a device that is
not stopped and restarted between them.

Worth doing properly or not at all, since a nearly gapless player is more
irritating than an honestly gapped one.

Done when: two tracks that run together on the disc run together through
Stellody; a test measures the seam rather than a listener judging it.

Depends on: milestone 1.

## 10. The equalizer

Promised in the README, entirely absent. Needs a decision before any code:
either a fixed set of bands applied to the decoded buffer or nothing at all.

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

Wanted for 0.2.0. A local library holds more than audio: a concert film sitting
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

## 14. Make the README true

Today it describes a finished product. Measured against the tree, five claims
are not built: the equalizer, shuffle, repeat, gapless transitions, the cover
grid, plus ratings and play counts in the opening paragraph and FTS5 in the
stack table.

Every other README in the account states what its product does NOT do. This one
currently promises what its binary cannot.

Two honest ways out; this file assumes the first. Each milestone above trims
its own claim as it lands, then anything abandoned is deleted from the README
the day it is abandoned. The alternative is to trim every unbuilt claim
now and add each back as it ships.

Done when: no sentence in the README describes something the binary will not do.

## Not planned, so that this is not revisited

- **Streaming, ripping, device syncing and tag writing.** Named in the README as
  deliberate non-goals. The last of them is enforced by a structural test rather
  than by intention.
- **Anything over the network.** No cover lookup, no scrobbling, no telemetry,
  no update check. The absence is the feature.
- **Encryption at rest.** The store holds library metadata, not secrets; the
  README says so plainly.
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
