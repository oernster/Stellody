# Plan

What Stellody has not built yet; also what it has decided not to build, so the
same ground is not argued twice. Where this file and the code disagree, the
code wins.

- Only open work is listed; a shipped milestone is deleted.
- Each milestone states what done means, as something observable.
- The invariants in `ARCHITECTURE.md` constrain every milestone and are not
  repeated here.

## Open work

None. A milestone arrives here when one is decided on.

## Not planned

- **Making the site findable** (Oliver's ruling). Search Console, Bing,
  sitemap submission and Rich Results validation are browser work outside this
  repository; the existing markup stays but reach is not chased.
- **Monkey's Audio, Musepack, DSD, TAK, CAF, `.m4b` and `.tta`.** Reported via
  `UNPLAYABLE_SUFFIXES` rather than played; `FORMATS.md` section 1.4 gives each
  reason and what would reopen it.
- **Streaming, ripping, device syncing and tag writing.** Non-goals; tag
  writing is excluded by invariant 1.
- **Fetching a music video for a track from an outside service** (Oliver's
  ruling). C-07 in `DISCOVERY.md` forbids a compiled-in credential; the obvious
  service's terms forbid re-presenting its streams; sources that permit
  downloads hold almost no commercial videos. Videos already on disk still play.
- **Concerts near you by artists you hold** (Oliver's ruling). Every listing
  service needs an API key, which C-07 rules out; it would also send a location.
- **Anything over the network that carries your library or names you.** No
  scrobbling, telemetry, account or identifier. Invariant 12 names the four
  modules allowed to connect; what each sends is under Your privacy in
  `README.md`.
- **Encryption at rest.** The store holds library metadata, not secrets.
- **Repairing the files themselves.** A correction lives in Stellody's own
  store and is never written back.
- **The album pane inserted inline after the sleeve that opened it.** A list
  view cannot insert a row between two model rows; a hand-written view would
  lose the keyboard reach an item view gives for nothing. The pane sits below.
- **Levelling loudness across albums.** Any gain short of unity in
  `infrastructure/audio.py` breaks the untouched-samples promise exclusive
  output exists for. It reopens only for listeners who shuffle across the
  library, off by default even then.
- **A second library root.** One folder, chosen once.
- **Writing anything at all into the music folder**, cache included.
