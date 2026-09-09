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

## 1. A music video for a track. Not designed.

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

Two ideas recorded by the owner on 2026-09-09, for that discussion rather than
as decisions:

- **Addresses rather than files.** A YouTube address per track, handed outward
  the way a shop address already is. That keeps the second question above on
  the near side of it: an address given to a browser is not a copy kept; it is
  also the reach this project already makes for shops and for the donation
  page. What it does not settle is the first question, since asking which
  video belongs to a track still names that track to a service.
- **Proving a result is a video at all.** Much of what a service returns for a
  track is the record with a still picture over it, which is a worse answer
  than none: somebody asking for the video gets the sound they already have.
  The test he proposes is to sample several positions, five say, then compare
  the frames: a still is identical at every position while a video is not. It
  is a cheap discriminator that needs no understanding of what is in frame.
  What it would have to be checked against first is the false pass, since a
  still picture under a moving level meter or a slow pan over one photograph
  also differs frame to frame; whether those are common enough to matter is a
  measurement nobody has taken. Sampling frames also means fetching them,
  which lands back on the network stance above rather than beside it.

Done when: cannot be stated. It is an idea rather than a milestone; it becomes
one only after the discussion above.

## 2. Concerts near you by artists you hold. Not designed.

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
- **Which service, on what terms.** The same question the video idea raises.
  It decides whether this is a list on a screen or an address handed to a
  browser; the answer to that shapes everything above it.

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
