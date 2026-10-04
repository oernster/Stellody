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
  is never written to, nothing reaches the network outside the four modules
  invariant 12 names, the domain stays pure, modules stay under the cap,
  domain and application hold 100% branch coverage.
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
commits to is stated in `README.md` and in `ARCHITECTURE.md` rather than here:
the invariants are the promise. The two that matter most to somebody's
collection, that a music file is only ever read and that nothing reaches the
network unasked beyond the update check, are held by tests rather than by
intention. Nothing below is sized against the number.

## Open work

There is no open planned work. Every milestone this file carried has either
shipped or been ruled out. The section below records what was decided against
and why, so the same ground is not argued twice. A new milestone arrives here
when somebody decides on one.

## Not planned, so that this is not revisited

- **Making the sites findable** (Oliver's ruling). Search Console, Bing,
  sitemap submission and Rich Results validation are browser work outside this
  repository; the existing markup stays but reach is not chased.
- **Monkey's Audio, Musepack, DSD and TAK.** Reported rather than played via
  `UNPLAYABLE_SUFFIXES`, since FFmpeg cannot encode a fixture to prove them;
  each reopens when a fixture can be made or a real file is measured.
- **CAF, `.m4b` and `.tta`.** Reported rather than played for reasons a fixture
  does not answer: CAF yields no tags, an audiobook is not music and TrueAudio
  states no channel count. `FORMATS.md` section 1.4 holds each reason.
- **Streaming, ripping, device syncing and tag writing.** Deliberate non-goals
  named in the README; tag writing is excluded by a structural test.
- **Fetching a music video for a track from an outside service** (Oliver's
  ruling). C-07 forbids a compiled-in credential; the obvious service's terms
  forbid extracting or re-presenting its streams; sources that permit downloads
  hold almost no commercial videos. A search link would be a link, not a
  feature. Videos already on disk beside the music still play.
- **Concerts near you by artists you hold** (Oliver's ruling). Every listing
  service needs an API key, which C-07 in `DISCOVERY.md` rules out; it would
  also send a location and its answers go stale. A gig search link would be a
  link, not a feature.
- **Anything over the network that carries your library or names you.** No
  scrobbling, telemetry, account or identifier. Invariant 12 names the four
  modules allowed to connect; only three leave the machine, since the instance
  channel is local. What each sends is set out under Your privacy in
  `README.md`. Handing an address to the browser (a shop or the donation page)
  is not a connection Stellody makes.
- **Encryption at rest.** The store holds library metadata, not secrets.
- **Repairing the files themselves.** An accepted correction lives in
  Stellody's own store and is never written back.
- **The album pane inserted inline after the sleeve that opened it.** A list
  view cannot insert a row between two model rows; a hand-written view would
  lose the keyboard reach an item view gives for nothing. The pane sits below.
- **Levelling the loudness across albums.** The measurement would ride on the
  waveform pass in `infrastructure/waveform.py`; any gain short of unity
  scales every block on the way out in `infrastructure/audio.py`, breaking the
  untouched-samples promise that exclusive output exists for. It reopens only
  for listeners who shuffle across the library, defaulting to off even then.
- **A second library root.** One folder, chosen once, rescanned incrementally.
- **Writing anything at all into the music folder**, cache included.
