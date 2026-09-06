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
