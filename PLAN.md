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

The readiness call has been made and the owner made it; the number itself lives
in `VERSION` rather than in any document here, this file included. What it
commits to is stated in `README.md` and in `ARCHITECTURE.md` rather than here: the
invariants are the promise. The two that matter most to somebody's collection,
that a music file is only ever read and that nothing reaches the network unasked
beyond the update check, are held by tests rather than by intention. Nothing
below is sized against the number.

## There is no open planned work.

Every milestone this file carried has either shipped or been ruled out, so
there is nothing here waiting to be built. That is a statement about the plan
rather than about the product: the section below records what was decided
against and why, which is the half of a plan that stops the same ground being
argued twice. A new milestone arrives here when somebody decides on one.

One question is open rather than one milestone: OQ-F01 in `FORMATS.md` is the
owner's to answer. Does somebody holding WMA files want them in the library
rather than reported? They are in it now, which changes what such a library
looks like without that person having been asked.

## Not planned, so that this is not revisited

- **Making the sites findable.** Ruled out by the owner on 2026-09-08, having
  been raised more than once. Registering the hosts with Search Console and
  Bing, submitting the sitemap and validating the structured data in the Rich
  Results Test are all work in a browser rather than in this repository; none
  of it is wanted. The markup the pages already carry stays as it is; it
  is simply not chased. This is a decision about reach rather than about the
  site, so nothing here reopens it.
- **The formats no fixture can prove.** Monkey's Audio, Musepack, DSD and TAK
  stay named in `UNPLAYABLE_SUFFIXES` and reported rather than played, along
  with CAF, `.m4b` and `.tta`. This entry once covered WMA and WavPack too, on
  the ground that not one file of any of them existed in the reference library,
  so writing decoders was a decision about other people's libraries. Measured
  on 2026-09-09, that ground was wrong about the cost rather than about the
  libraries: the FFmpeg already inside PyAV decodes every one of them and
  mutagen already reads their tags, so no decoder was ever going to be written.
  What separates them now is whether a fixture can be generated to prove the
  path, since FFmpeg can encode only some of what it can decode. The three
  that can be proved are taken. Each of the rest reopens the day a
  fixture can be made for it or a real file is measured; `FORMATS.md` section
  1.4 holds the reason for each.
- **Streaming, ripping, device syncing and tag writing.** Named in the README as
  deliberate non-goals. The last of them is enforced by a structural test rather
  than by intention.
- **Fetching a music video for a track from an outside service.** Ruled out by
  the owner on 2026-09-09 after being scoped rather than on a first reading, so
  the reasoning is recorded here to save scoping it twice. Three findings
  settled it. C-07 forbids compiling in a credential of any kind, which closes
  asking a video service which video belongs to a track before its terms are
  even reached: it is the constraint that already excluded Discogs and Last.fm.
  The terms of the obvious service permit playback through its own player with
  its branding intact, so extracting a stream, hiding the player or presenting
  the content inside this application is a licence liability carried to
  everyone who forks it. Downloading is forbidden there separately, while the
  sources that do permit it hold almost no commercial music videos, so that
  route works and finds nothing. What remains permitted is handing a search
  address to the browser exactly as a shop link already is, which is a link
  rather than a feature and does not earn a milestone. Playing a video that is
  already beside the music on disk is unaffected: that is built and stays.
- **Concerts near you by artists you hold.** Ruled out by the owner on
  2026-09-09, the same day it was scoped and for a related reason: it was
  judged to cause more problems than it solves. What the scoping found is kept
  here so the judgement is not made twice from scratch. Every concert listing
  service is keyed, which meets C-07's second clause rather than its first: the
  objection is not that a key would be published, since a key the listener
  pastes into a file of their own is no more compiled in than a shop row is.
  It is that everybody wanting the feature would have to go and get one. A
  listing screen therefore serves whoever has done that and nobody else. The
  remaining shape that needs no key is handing a gig site's search address to
  the browser, which is the shops mechanism pointed at other sites and is a
  link rather than a feature. Two further costs were open when it was dropped:
  it would send a place as well as artist names, narrowed to a postcode
  district somebody typed rather than one detected; its answers also go stale
  in a way a catalogue's do not, so nothing about the thirty day memory could
  be inherited. It reopens only as a decision about all four together.
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
