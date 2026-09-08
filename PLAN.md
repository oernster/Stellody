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

Version 1.0 was that readiness call and the owner has made it. What it commits
to is stated in `README.md` and in `ARCHITECTURE.md` rather than here: the
invariants are the promise. The two that matter most to somebody's collection,
that a music file is only ever read and that nothing reaches the network unasked
beyond the update check, are held by tests rather than by intention. Nothing
below is sized against the number.

## 1. Make the sites findable

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

## 2. Discover music the library does not hold

Everything else here is about music already owned. This is the opposite: which
artists and albums are worth reaching for next, given what the library already
says about somebody's taste.

**Both stages are BUILT and neither is finished.** The code is written, the
gate is green over it and both specifications are amended to match. What is
open is the half no test can supply: neither stage has been run against the
real services and had its answer checked by a person, which is what each of the
two milestones below states as done.

Stage one is specified in `DISCOVERY.md` and stage two in `SHOPS.md`. Nothing
from either is repeated here, so the three cannot come to disagree; the
structure they landed in is described in `ARCHITECTURE.md` under "Discovering
what the library does not hold".

**Stage one, still open: a real run, checked by hand.** A run against the live
catalogues over one of the small genres, with the gaps it reports read through
by somebody who knows the library. Everything about the matching rule was
settled against titles as the LIBRARY spells them; it has never been tested
against titles as MusicBrainz spells them, which is exactly what a live run
answers and nothing else can. Folk or Reggae is the obvious first run, being
small enough to read the whole of.

Done when: a run over one of the small genres completes against the real
sources and writes a file whose gaps are checked by hand and are real.

**Stage two, still open: the shipped shop templates, on the day they ship.**
A-03 in `SHOPS.md` puts that on every release, for the reason the shop list is
data at all: three of the eight checked on 2026-09-07 had closed, walled or
moved their search that same afternoon. OQ-S01 sits under it, HDtracks needing
a human to confirm its search before it can join the defaults.

Done when: a gap ticked in the results dialog opens that shop's own search for
it in a browser, having sent nothing about the listener.

## 3. A music video for a track. Not designed.

Idea recorded 2026-09-06 for later scoping. It is written down so it is not
lost, not because it is understood: what it costs, whether it can be done at
all within this project's stance and whether it should be are all open.

The thought: for a track with no video beside it on disk, find and play a music
video for it from an outside service, else fetch one to keep.

Playing a video with the sound is already built, so this is about where a video
comes from rather than about showing one. `infrastructure/video.py` reads the
picture out of a container with the sound as the clock.

Three things to settle before anything else, none of them small:

- **The network stance.** Naming every track to a video service is a much larger
  outward reach than the discovery run, which names artists inside genres the
  listener ticked. What the equivalent scoping is here has to be found before
  the rest is worth discussing.
- **Fetching a copy is a separate question from playing one; it is the harder
  one.** The terms of the obvious services forbid it; this project ships publicly
  under a licence that would carry that decision to everyone who forks it.
  Playing an address in a browser and keeping a file are not one feature.
- **What "the video for this track" even means.** A title and an artist do not
  identify a video; the first result for a track is frequently not the record.

Done when: cannot be stated. It is an idea rather than a milestone; it becomes
one only after the discussion above.

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
  scrobbling, no telemetry, no account, no identifier. Three modules reach
  outward, each named in invariant 12. The cover chooser reaches only when a
  listener opens it; the update check asks GitHub about Stellody, sending
  nothing whatever about the machine asking; a discovery run names the artists
  inside the genres somebody ticked, which is a subset they chose rather than
  an inventory of what they own. Handing an address to a browser is not a
  fourth, whether it goes to the donation page or to a shop: the address goes
  outward and the browser does the asking.
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
- **Levelling the loudness across albums.** Albums are mastered at whatever
  level their era chose, so moving between them means reaching for the volume.
  That is real; it is not worth what it costs here. The decode is not the
  expensive part, which is the thing most likely to be re-argued:
  `infrastructure/waveform.py` already reads every file through to measure its
  shape and already accumulates the sums of squares a loudness figure is built
  from, so the measurement would ride on a pass that happens anyway. What rules
  it out is the output. Measured in `infrastructure/audio.py`, a block reaches
  the device untouched only where the volume is exactly unity; any other figure
  multiplies the block and casts it back to the file's own integer type. A
  levelling gain is nearly always a reduction, so every album that had been
  measured would be scaled and requantised on the way out. This application
  exists because another player altered somebody's files; handing the device
  exactly what the file holds is that same promise, so spending it to save
  reaching for the volume once a record is a poor trade. It reopens for somebody
  who listens by shuffling across the library rather than by playing records
  through, since that is the pattern it would actually pay off for; it would
  default to off even then.
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
