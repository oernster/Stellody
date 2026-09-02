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

## Cutting a release

Releases are being cut as work lands. `VERSION` holds the number for the release
being cut; a bump is owed against the newest TAG rather than against the last
thing written, so a VERSION already ahead of the tag has had its bump.

Cutting one means: the gate is green, the release notes are written in
`NOTES.md` (which is never staged), then the tag and the release are the
owner's to make. A tagged version's notes leave `NOTES.md` on the next pass,
since the file carries the pending release alone.

Version 1.0 is a separate readiness call for the owner to make; nothing below is
sized against it.

## 1. macOS and Flatpak

Windows first, which is where it stands. macOS and Linux come later, built to
the house pattern rather than invented here: `build_flatpak.sh` with
`clean_flatpak.sh` for Linux and `builddmg.py` for macOS, taking ClearBudget as
the worked guide and stripping every inherited specific.

The audio layer is the part that does not travel. `WasapiPlayback` is named for
a Windows interface and speaks to one; the playback port it sits behind is
already the seam a second output goes in at. So this milestone is two pieces:
the packaging, plus an output that works where WASAPI is not.

The Flatpak needs `--share=network` in its finish-args, named in a comment as
being for the update check. The house recipe grants no network by default,
which is right for an application with no outbound call and would leave every
update check here reporting that GitHub could not be reached. It fails quietly,
so it would be found by a listener rather than by a build.

Done when: a Flatpak and a DMG are built by their own scripts, each plays
audio; the update check reaches GitHub from inside the sandbox; the Windows
build is untouched by either.

## 2. Play the formats that need a decoder Stellody does not carry

The formats libsndfile can decode are done and watched: the walk takes `.flac
.mp3 .ogg .oga .opus .wav .aiff .aif`, a general probe reads what each format
actually states, the existing decode path serves the lot and real albums in each
of MP3, Ogg and WAV have been played through in the built application. What
remains is everything libsndfile cannot decode.

**What that costs, measured over the reference library on 2026-08-30.** Of 656
folders holding audio, 146 held no FLAC at all and were invisible. Extending the
walk brought back 19 of them. The other 127 are M4A and wait on a decoder: 1,356
tracks, more than a fifth of the library still unreachable. An album asked after
by name, BT's Emotional Technology, is one of the 127.

**What is left needs a decoder rather than a suffix.** M4A with AAC or ALAC,
WMA, Musepack, Monkey's Audio, WavPack, DSD. Each means either FFmpeg through a
binding or Qt Multimedia, so each carries a new dependency and a licence
question the first half did not.

That asks the same question milestone 3 asks, so answer it once: **one media
backend, chosen for both**. Deciding it separately is how a player ends up with
two decoders that disagree about what a track is.

Honesty applies as usual; the rule the first half established carries forward.
A lossy format cannot be bit perfect however the device is opened, so
whatever the new backend decodes has to state what it states and no more.

Done when: an M4A album scans, groups and plays in the built application; a
format Stellody cannot decode is reported as unreadable rather than silently
skipped.

## 3. Play video files

Wanted, though after the first release. A local library holds more than audio:
a concert film sitting beside the albums it came from is part of the same
collection.

This is the one milestone that changes what Stellody IS, so it changes several
things that currently assume audio: the walk takes audio suffixes only, a track
is a slice of an audio file, the output port speaks to a sound device. A video
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

Depends on the transport the position display already built. Shares its
backend decision with milestone 2.

## 4. Accept the repairs the health report describes

The report says what Stellody worked around. It cannot yet be told "yes, keep
that", so the same 142 findings are recomputed and re-read on every start.

**Most of this already exists.** The store keeps RAW tag values, not resolved
ones; resolution happens on load, which is what lets a rule be improved
without rescanning. So Stellody already reads damaged tags, works out what they
should be and shows the corrected library while the files stay untouched. What
is missing is not the correction. It is anywhere to record that a correction
was accepted, plus any way to prefer yours over the rule's.

**Measured on the reference library**, so the size of this is known rather than
guessed, though measured while the walk still took FLAC alone: 142 issues across
36 of the 482 albums. 132 are two files claiming one
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
plus the two repair buttons enabled: the one on the bottom strip beside the
rescan whose findings it answers and the one pinned at the top of the health
dialog,
both of which are already drawn and already wired to a seam that does nothing.

Done when: accepting everything the report lists empties it in one gesture, the
library shows the corrected values, both survive a restart and a rescan, then
resetting brings the original findings back; no music file has changed, which
the read-only structural tests already prove.

## 5. One loudness across albums

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

## 6. Make the sites findable

The markup is already there: a title and a description on every page, a
canonical, the full Open Graph and Twitter set, `SoftwareApplication`
structured data on the front page, a sitemap and a robots file. None of that is
discovery. Nothing has been submitted to a search engine, no structured data
has been validated against a real checker and neither host has been observed in
an index.

What is left is the part that moves it:

- **Register both hosts.** Google Search Console plus Bing Webmaster Tools for
  `stellody.co.uk`, then submit `sitemap.xml`. Register `stellody.com` as well,
  where the point is the opposite one: confirm the cross-domain canonical is
  read, so the mirror is treated as the copy rather than as a rival.
- **Validate the structured data** in the Rich Results Test rather than by
  reading it, then extend it past the front page. The other three pages carry
  no JSON-LD at all.
- **Give the link previews their pictures.** The cards ask for `summary` with
  the 512px icon; the site holds two screenshots that would carry a
  `summary_large_image` card instead.
- **Put `lastmod` in the sitemap.** Visible dates are forbidden on these sites;
  machine metadata is exempt, so this is the only signal a sitemap carries
  beyond the list of URLs.
- **Link to it from the hub.** `ernster.dev` has never listed Stellody, so the
  site has no inbound link from the one place certain to give it one.

Every page change lands in `docs/` and reaches `stellody.com` on its own
through the mirror workflow, so this is one repository's work.

Done when: both hosts are verified in Search Console with the sitemap submitted
and no coverage errors, the structured data passes the Rich Results Test and a
search for the application by name returns the site.

## Not planned, so that this is not revisited

- **Streaming, ripping, device syncing and tag writing.** Named in the README as
  deliberate non-goals. The last of them is enforced by a structural test rather
  than by intention.
- **Anything over the network that carries your library or names you.** No
  scrobbling, no telemetry, no account, no identifier. Two modules reach
  outward. The cover chooser reaches only when a listener opens it; the update
  check asks GitHub about Stellody, sending nothing whatever about the machine
  asking. Handing the donation link to a browser is not a third: the
  address goes outward and the browser does the asking.
- **Encryption at rest.** The store holds library metadata, not secrets; the
  README says so plainly.
- **Repairing the files themselves.** Milestone 4 records a correction in
  Stellody's own store and shows it on load. It never writes one back; no
  amount of accepting changes that.
- **The album pane inserted inline after the sleeve that opened it.** That is
  what MediaMonkey does and it reads well; a list view cannot insert a row of
  its own between two rows of the model. It would mean a view written from
  scratch, losing with it the keyboard reach an item view carries for nothing.
  The pane sits below the grid instead, which is the same information a row
  lower down.
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
