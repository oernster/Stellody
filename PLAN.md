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

## 1. One loudness across albums

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
of 42 minutes took 3.0 seconds, about 841 times real time. At that rate the
reference library, 671 hours of music, is roughly 48 minutes of one core,
against the 3.75 seconds the ordinary scan takes reading tags alone. So it cannot ride along quietly with a
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

## 2. Make the sites findable

Nothing has been submitted to a search engine, no structured data has been
validated against a real checker and neither host has been observed in an
index. What is left happens in a browser rather than in this repository:

- **Register both hosts.** Google Search Console plus Bing Webmaster Tools for
  `stellody.co.uk`, then submit `sitemap.xml`. Register `stellody.com` as well,
  where the point is the opposite one: confirm the cross-domain canonical is
  read, so the mirror is treated as the copy rather than as a rival.
- **Validate the structured data** in the Rich Results Test rather than by
  reading it, on each of the four pages.

Done when: both hosts are verified in Search Console with the sitemap submitted
and no coverage errors, the structured data passes the Rich Results Test and a
search for the application by name returns the site.

## 3. macOS and Flatpak

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

## 4. Discover music the library does not hold

Everything else here is about music already owned. This is the opposite: which
artists and albums are worth reaching for next, given what the library already
says about somebody's taste.

**It is the last milestone because it is the largest thing on this list by a
wide margin.** Three stages, in the order they were settled, each one usable on
its own so the third is never a condition of the first two.

**Stage one: suggest by genre, from what is already owned.** The stated genres
give a picture of what somebody listens to, so the first suggestions come from
that picture rather than from anything outside. It needs the tag editor's genre
stage, which is built; it needs nothing else.

**Stage two: artists, keyed by the artists already held.** For each artist
looked up, offer ten artists not already in the library, growing towards twenty
where the source supports it. Ten is the number to start at. Nothing already
owned is ever offered back.

The shape settled for this is a JSON file whose KEYS are the artists in the
library and whose values are the artists to look up from them. That makes the
mapping a piece of data rather than a rule buried in code, so it can be read,
corrected and grown without a release. Open: where its values come from in the
first place; whether it ships with the application or is built on the machine.

**Stage three: reach the places that sell it. This needs real discussion and is
not designed.** Once the gaps are known, this would look them
up for sale in a browser. There are three kinds of gap:

- an artist not in the library at all;
- an album by an artist who IS in the library, where that album is not;
- an album by an artist not held at all.

The listener says which format matters, FLAC or MP3 or another; the search
carries that filter. Named as candidate sources: 7digital, Boomkat and Qobuz;
there are many more and the list is not settled.

**This is consistent with the network stance rather than an exception to it.**
The rule in "Not planned" forbids anything outward that carries the library or
names the listener. It already records that handing an address to a browser is
not such a call: the address goes out and the browser does the asking. Buying
music is that same move. What would breach it is sending the library to a
recommender; the same goes for anything else identifying the listener.

Open questions, none answered yet:

- Where do the suggestions themselves come from? Every outward call in this
  application today is one a listener asks for, sends nothing about the machine
  and names nobody. That must hold here too, which constrains what a source can
  be.
- What does a suggestion look like on screen; where does it live?
- Is anything written down between runs; if so, where?

Done when: cannot be stated yet as one thing. Each stage gets its own, settled
when that stage is designed.

## Not planned, so that this is not revisited

- **The formats no decoder here carries.** WMA, Monkey's Audio, WavPack,
  Musepack and DSD stay named in `UNPLAYABLE_SUFFIXES` and reported rather than
  played. Measured over the reference library: of the 126 folders that then held
  nothing Stellody could decode, every one was M4A and not one file of those
  five existed anywhere, so writing more decoders is a decision about other
  people's libraries rather than about this one. It reopens when somebody has a
  library that needs it.
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
- **Repairing the files themselves.** Accepting a correction records it in
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
