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

## 1. Concerts near you by artists you hold. Not designed.

Idea recorded 2026-09-09 for later scoping, at Oliver's request and in his
words: the ability to explore, over say the next month, the concerts within a
reasonable range that are on for artists you have albums for. It is written
down so it is not lost, not because it is understood.

It shares its shape with a discovery run, which is why it is worth recording
rather than starting: it names artists the library holds to an outside service
and shows what comes back. What it adds is two things a run has never had.

Three things to settle before anything else, none of them small:

- **It names a PLACE as well as artists.** Everything Stellody reaches out
  with today says what a listener ticked and nothing about who or where they
  are. A radius around somewhere is a location; a location beside a taste
  in music is a different kind of disclosure than either alone. Where that
  place comes from, whether it is typed in rather than detected and what is
  sent to get an answer are the first questions, ahead of which service is
  asked.
- **The answer goes stale in a way a discovery answer does not.** A record
  that exists still exists next month; a concert next month does not. The
  memory that makes a run affordable stands for thirty days on the ground that
  catalogues barely change over that period, which is precisely untrue here, so
  what may be remembered and for how long has to be worked out again rather
  than inherited.
- **Which service, on what terms.** It decides whether this is a list on a
  screen or an address handed to a browser; the answer to that shapes
  everything above it. It is also what ruled the video idea out below, so the
  answer is worth having before anything is built rather than after.

Done when: cannot be stated. It is an idea rather than a milestone; it becomes
one only after the discussion above.

## Not planned, so that this is not revisited

- **Making the sites findable.** Ruled out by the owner on 2026-09-08, having
  been raised more than once. Registering the hosts with Search Console and
  Bing, submitting the sitemap and validating the structured data in the Rich
  Results Test are all work in a browser rather than in this repository; none
  of it is wanted. The markup the pages already carry stays as it is; it
  is simply not chased. This is a decision about reach rather than about the
  site, so nothing here reopens it.
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
