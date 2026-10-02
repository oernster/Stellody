# Decisions and trade-offs

The deliberate choices Stellody rests on: what was chosen, what was given up
for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md) and the specifications
([DISCOVERY.md](DISCOVERY.md), [SHOPS.md](SHOPS.md), [FORMATS.md](FORMATS.md),
[OUTPUTS.md](OUTPUTS.md)); [PLAN.md](PLAN.md) holds what is deliberately not
planned.

## The product as a whole

### Local first, one listener, one machine

Everything Stellody knows is kept on the computer it runs on, in SQLite plus
a few JSON files, for the one person whose library it is.

- **Rather than:** a server database, an account or anything synchronised.
- **Gains:** no server to install or run; nothing to sign in to; it works with
  the network switched off.
- **Costs:** the library notes belong to that one machine. Nothing follows the
  listener to another computer.

### Python and PySide6

The application is written in Python on Qt for Python.

- **Rather than:** Rust or Go.
- **Gains:** the test gate, the structural guards and the delivery recipe
  already proved on earlier projects, so the effort goes on the player.
- **Costs:** a larger runtime than a native binary would need; packaging takes
  more care.

### Specification before code

Each feature area is written down as requirements before it is built, each
requirement naming the test that proves it, with a list of what it will not
do.

- **Rather than:** building first and describing afterwards.
- **Gains:** a ruled-out idea stays ruled out instead of being argued again;
  a claim in the docs is one a test holds.
- **Costs:** writing and keeping the specifications true is work of its own.

### What Stellody deliberately is not

It plays and organises music the listener already owns. It does not stream,
rip, sync to devices or write tags.

- **Rather than:** an all-in-one media suite.
- **Gains:** a small surface that can be held to a high bar.
- **Costs:** those jobs need other tools.

## Privacy and the network

### Only four modules may reach the network

Fetching cover art, checking for an update, asking the discovery catalogues
and the local pipe that hands a second launch to the first are the only code
able to open a connection. A structural test counts them.

- **Rather than:** a promise that the network is used sparingly.
- **Gains:** "local first" is a test result rather than a sentence. A new way
  out is an edit somebody has to make and defend.
- **Costs:** every new outward feature must go through an existing route or
  argue for a fifth.

### Nothing names the listener or the machine

No account, no telemetry, no identifier, no scrobbling. What a discovery run
sends is a fixed set of fields that a test checks; the language asked for is
fixed rather than taken from the computer. The update check sends the product
name alone, not even its version.

- **Rather than:** the conveniences other players offer; the defaults the
  networking libraries would send.
- **Gains:** nothing about the listener, the machine or the library as a whole
  leaves the computer.
- **Costs:** no usage figures to steer development; the update server cannot
  tell which versions are in use.

### No credential compiled in

Only sources that need no key or token are used.

- **Rather than:** Discogs or Last.fm, which need one. A key built into an
  open-source application is a published key; Last.fm's terms would also bind
  every fork.
- **Gains:** nothing to leak; no licence terms passed on to anyone building
  from the source.
- **Costs:** discovery is limited to MusicBrainz and ListenBrainz. The same
  rule rules out music videos and concert listings.

### Update checks: daily, quiet unless there is news

A check runs shortly after launch and then once a day; it says nothing unless
there is a newer release. A check somebody asks for always answers. A version
it cannot read is never treated as newer.

- **Rather than:** no check at all; one that reports every outcome.
- **Gains:** updates are found without nagging; a malformed release never
  tells somebody their copy is stale.
- **Costs:** one unprompted request a day.

### Cover art from the internet only when asked

Covers come from the music folder. Searching online for one is a chooser the
listener opens, never an automatic lookup.

- **Rather than:** fetching missing art automatically.
- **Gains:** the files carry no catalogue identifiers, so an automatic match
  could attach the wrong cover without knowing; anyone who never opens the
  chooser sends nothing.
- **Costs:** missing art stays missing until the listener acts.

### Shops and donations go through the browser

Stellody hands an address to the default browser and stops there.

- **Rather than:** making those requests itself.
- **Gains:** no new connection inside the application; the shop sees the
  listener's own browser session.
- **Costs:** Stellody never learns what happened next.

### No encryption at rest; a plain-text diary

The store and the diary are ordinary files in the application's own data
directory. The diary records its own comings and goings, dropouts and every
address a discovery run asked; it is never sent anywhere.

- **Rather than:** encrypting library notes; keeping no record.
- **Gains:** simple, inspectable files; faults that reading the source could
  not find have been found by reading the diary.
- **Costs:** anyone with access to the account can read the library notes and
  the artist names a run sent.

## The library and its files

### The library is read, never written

Music files are opened for reading only. A wrong tag is corrected inside
Stellody's own store and reported; the file is left exactly as it was. Two
structural tests hold this; the Linux build is only granted read access
to the home folder.

- **Rather than:** repairing tags on disk.
- **Gains:** Stellody cannot damage a collection somebody spent years curating.
- **Costs:** corrections live only in Stellody; other players never see them.

### One library folder, nothing written into it

The library is one root folder. Nothing Stellody keeps, cache included, is
written inside it.

- **Rather than:** several roots; sidecar files beside the music.
- **Gains:** the music folder stays the listener's alone.
- **Costs:** music spread across unrelated places has to be gathered under one
  root.

### Folders group albums; tags name them

A folder is where an album starts. Tags give it its title, artist, year and
genre. Tags may join folders into one album (disc folders or folders whose
tags agree) but never split one. Where tags contradict something physical, the
physical thing wins.

- **Rather than:** grouping by tags alone. Real collections carry inconsistent
  tags: grouping one classical folder by its tags split it into five albums,
  two of them a single track.
- **Gains:** albums are what the person who ripped them meant.
- **Costs:** two different recordings whose tags resolve alike are shown as
  one album; that price is stated rather than hidden.

### Raw tags stored, the album worked out on loading

The store keeps the tags as read. Rules and accepted corrections are applied
each time the library loads, in layers: raw tags, automatic rules, then
corrections the listener accepted.

- **Rather than:** storing the corrected result.
- **Gains:** an improved rule reaches the whole library without a rescan;
  what the file itself says is never lost under a correction.
- **Costs:** the working out is repeated at every load. A rule that changes
  what is written down at scan time still needs the folders read again.

### Corrections accepted in bulk, undone in bulk

The health view's findings can be accepted all at once, an album at a time or
one at a time; anything accepted can be reset at the same three sizes.

- **Rather than:** one finding at a time, which is not a workflow over a
  hundred or more findings.
- **Gains:** a whole library's tidying is one decision that can be taken back.
- **Costs:** none recorded.

### A rescan reads only what changed

A folder whose files are unchanged is reused from the store rather than read
again.

- **Rather than:** reading every file on every scan.
- **Gains:** a rescan of hundreds of folders takes well under a second.
- **Costs:** the store must know when a folder's record is out of date.

### A lossy copy beside its lossless original is not a second album

Where a lossless file and a lossy one share a disc, a track number and a
length, the lossy one is set aside.

- **Rather than:** pairing on the track number alone, which cannot tell a copy
  from a live version.
- **Gains:** a collection holding both shows each recording once.
- **Costs:** two genuinely different recordings of the same length could be
  paired; none has been seen.

### A track can be part of a file

A cue sheet over one long file is a first-class album: a track is a slice of a
file; a whole file is simply the slice that covers it all.

- **Rather than:** assuming one file per track.
- **Gains:** queueing, shuffle and gapless playback are written once for both
  shapes of album.
- **Costs:** every decoder has to start and stop at a frame rather than at the
  ends of a file.

### Unknown stays unknown where a claim depends on it

A bit depth, a date or a genre the file does not state is held as unknown
rather than filled with a plausible default. Where the display needs a name,
the folder name or a placeholder stands in and the gap is reported as an
issue.

- **Rather than:** a tidy interface full of invented values.
- **Gains:** nothing is claimed (bit-perfect output, an exact date) on the
  strength of a guess.
- **Costs:** some albums show placeholders until the listener corrects them.

### An unreachable drive is not a deleted library

A scan checks that the music folder can be reached before it starts and stops
without changing anything when it cannot. Within a reachable folder, a file no
longer found is marked absent, never deleted.

- **Rather than:** walking whatever is there and recording the difference.
- **Gains:** unplugging a drive costs nothing; plugging it back restores the
  library as it was.
- **Costs:** a library root that is genuinely gone is not cleared away
  automatically; the scan reports it instead.

### A scan says what arrived and what left

After a scan the listener is told which albums are new and which have gone,
judged by album identity. A retagged album reads as one leaving and one
arriving rather than as a discovery.

- **Rather than:** a count of files; nothing at all.
- **Gains:** the listener sees what the scan actually changed.
- **Costs:** none recorded.

### Cover art from the album's own folder

A cover comes from an image file beside the music first, then from a picture
embedded in the files. Parent folders are never searched. Covers are cached
small, in Stellody's own directory.

- **Rather than:** borrowing an image from a parent folder.
- **Gains:** an album never wears another album's cover; the grid stays quick.
- **Costs:** an album whose art sits only in a parent folder shows none.

### Supported means proved

A format is played only when a test file in it can be generated and played end
to end. Formats that cannot be proved that way are reported in the library's
health view rather than played, alongside a few left out on other grounds (no
tags, audiobooks).

- **Rather than:** playing everything the decoder happens to open.
- **Gains:** every playable path is tested; no audio files are committed to
  the repository.
- **Costs:** real files in a handful of lossless formats are not played.

### Ratings and plays follow the album, not the file path

Ratings and play counts are keyed to an album's identity, so they survive a
rename or a rescan. A play counts only when a track reaches its end. Albums
and tracks are rated separately.

- **Rather than:** keying by file path.
- **Gains:** the listener's history outlives reorganising the folders.
- **Costs:** merging two albums keeps the rating of the one merged into.

### Search reads the whole library on every keystroke

Search is a plain pass over the library as shown on screen, with the text
prepared once when the library loads.

- **Rather than:** a full-text index, which SQLite offers and Stellody leaves
  unused. An index would hold raw tags while the screen shows corrected ones.
  It would also need rebuilding.
- **Gains:** search finds exactly what is on screen; there is no index to keep
  in step. Measured on a library of about six hundred albums, a pass takes a
  small fraction of the time between keystrokes.
- **Costs:** the work grows with the library; a far larger collection would
  need measuring again.

### A settled genre list

Genres are a fixed catalogue of main genres with styles under them, with
spellings that match the catalogues. A library's own tag strings are mapped
onto it.

- **Rather than:** offering whatever strings the library's tags contain.
- **Gains:** the same boxes in every dialog; filters that mean the same thing
  for everybody.
- **Costs:** the mapping from other spellings needs keeping up.

## Playback and sound

### Its own audio pipeline

Stellody decodes and plays audio itself: libsndfile for the formats it
opens, FFmpeg (bundled through PyAV and loaded only when needed) for the rest
and PortAudio for output.

- **Rather than:** Qt's media player, which cannot play part of a file as a
  track and has no equalizer; the system's own codecs.
- **Gains:** cue-sheet tracks, an equalizer and one decoder that behaves the
  same on every platform.
- **Costs:** Stellody owns its own decoding, output and threading. The bundled
  FFmpeg build includes GPL components, so the packaged application is
  distributed under GPL-3.0.

### Shared output by default; exclusive where the platform allows

Music plays through the system mixer unless the listener asks for exclusive
output. On Windows that takes the device itself. On macOS it asks the device
for the file's own format, though other applications can still reach it.
Linux plays through the mixer only. The exclusive switch is offered only for a
song the device can actually take.

- **Rather than:** exclusive by default; a hi-fi switch offered where it
  cannot be honoured.
- **Gains:** Stellody plays alongside everything else by default; an offer of
  exclusive output is one the device can keep.
- **Costs:** the default is not bit-perfect; exclusive output locks other
  applications out of the device on Windows.

### Bit-perfect only when the stream proves it

The readout says bit perfect only when exclusive output was granted at the
file's own rate and depth with the volume at full, unmuted and with no
equalizer curve shaping the sound. What was asked for and what was granted are
kept apart; a refusal moves the switch back to shared and says why.

- **Rather than:** treating "exclusive selected" as success.
- **Gains:** no claim rests on a request the device did not honour, nor on a
  stream the volume or the equalizer has since altered.
- **Costs:** the line changes as the volume moves, so a listener nudging the
  slider sees the claim come and go.

### No loudness levelling

Albums play at the level they were mastered. At full volume the samples reach
the device untouched.

- **Rather than:** ReplayGain-style levelling across albums.
- **Gains:** the promise that the device receives exactly what the file holds
  stays true; exclusive output keeps its point.
- **Costs:** the listener reaches for the volume between records mastered at
  different levels.

### Gapless inside the engine

The next track is joined to the current one inside the playback thread
without stopping the stream. Two joins stay gapped on purpose: a next track at
another sample rate; a shuffled album starting again.

- **Rather than:** reopening the stream for every track, which cut the sound
  at every join.
- **Gains:** albums meant to run without a break do.
- **Costs:** a change of sample rate between tracks leaves a gap.

### The transport works by state, not timing

Back returns to the start of the track and waits; pressed again from there it
goes to the previous track. Next always moves on, even when one track is set
to repeat. Shuffle begins with the track in hand and never reopens on the track
that just ended. Skipping keeps playing or paused as it was; a pause is never
read as an ending. Volume starts at three quarters.

- **Rather than:** double-press timing windows, which proved the wrong model;
  full volume on a first run.
- **Gains:** every press does the same thing whatever the timing; a first run
  is never startling and leaves room to go up.
- **Costs:** none recorded.

### Video tracks follow the sound

A bonus video plays as a track. The sound is the clock; the picture is drawn
at its own size in the library area and fills the window only when asked.

- **Rather than:** a separate video window; stretching the picture.
- **Gains:** video is part of the album rather than a second program.
- **Costs:** no video features beyond playing it.

### A deeper output queue

Output is queued two blocks deep.

- **Rather than:** the shortest possible queue.
- **Gains:** dropouts under load stopped (measured, from dozens in a few
  seconds to none).
- **Costs:** a little more delay between a press and the sound changing.

### A hand-written equalizer

The equalizer is written from the standard filter formulas. A band at zero
costs nothing, so a flat equalizer leaves the samples untouched; headroom is
made before any lift.

- **Rather than:** a scientific library tens of megabytes in size for one
  function.
- **Gains:** a small package; a flat equalizer is truly off.
- **Costs:** the filters are Stellody's own to maintain.

### The visualiser watches, never touches

The spectrum is measured from what was written to the device, in the
equalizer's own bands; it goes idle when nothing plays. It is always on, with
no setting.

- **Rather than:** a display with bands of its own; one in the audio path.
- **Gains:** it can never delay or alter a sample.
- **Costs:** none recorded.

### Music never moves to the speakers without a press

An output device is remembered by its identity rather than its name. If the
chosen device is missing, music plays on the system default and says so. If
it disappears while playing, the track pauses where it was. When it returns
the music moves back to it.

- **Rather than:** forgetting the choice; carrying on through whatever
  device is left.
- **Gains:** nothing plays out loud by surprise; the listener's choice
  survives a device being unplugged.
- **Costs:** a press is needed to carry on after a disconnect.

### Faster only with the same answer

The waveform is reduced over whole blocks of samples at once rather than a
frame at a time; it was kept only once it gave bit-for-bit the same result. It
is drawn as it is read rather than after. It shows loudness rather than peaks:
drawn from peaks, nearly every moment of a track sat close to its loudest.

- **Rather than:** the simpler frame-by-frame loop.
- **Gains:** roughly four times faster; a long track shows its shape almost
  at once.
- **Costs:** a whole-album file still takes several seconds to complete.

## Discovery

### Ask what is missing from the listener's own collection

Discovery starts from the albums the listener owns, inside the genres they
tick. It asks public catalogues what those artists and their neighbours have
released that is not on the shelf.

- **Rather than:** a listening history or a behavioural profile.
- **Gains:** no account and no profile; every suggestion can be traced to an
  album the listener owns.
- **Costs:** less personal than a recommender trained on habits.

### Two sources, each for one question

MusicBrainz answers what an artist released; ListenBrainz answers who sounds
like them. Neither answers both, so they are joined through MusicBrainz's
identifiers.

- **Rather than:** one commercial service that needs a key.
- **Gains:** open data; no key.
- **Costs:** similarity comes from an experimental endpoint with nothing to
  fall back to.

### The genres ticked decide who is asked about

A run names only artists inside the ticked genres, plus titles in a few stated
cases. Tick nothing and nothing leaves.

- **Rather than:** sending the whole library and filtering the answers.
- **Gains:** what is sent is a subset the listener chose, not an inventory.
- **Costs:** discovery outside those genres needs another run.

### Polite and slow by design

Requests to MusicBrainz are paced a little below its published limit, through
one gate shared by everything that asks it. A refusal is retried on a later
pass rather than waited out on the spot.

- **Rather than:** asking faster; giving each part of the program its own
  pace.
- **Gains:** runs finish instead of having the address refused.
- **Costs:** a large run takes many minutes.

### Answers remembered for a month

Every catalogue answer is kept for thirty days and written to disk as it
arrives.

- **Rather than:** always asking afresh; saving only at the end.
- **Gains:** the same library gives the same answer whatever the service felt
  like that minute; most later runs ask little; a crash loses at most one
  answer.
- **Costs:** a new release can take up to a month to appear.

### A partial answer is still an answer

An artist that could not be asked about is retried on a later pass. Others are
recorded and the run carries on. The answer says separately how many could
not be asked, were not recognised or shared a name. Five questions in a row
met with silence end the run as unavailable; the previous answer is kept.

The answer file names its gaps rather than leaving them out. A run that
found nothing still opens its results to say why.

- **Rather than:** ending a run on its first failure; hiding failures in one
  total.
- **Gains:** a busy catalogue or a dropped connection costs a few artists
  rather than the whole run.
- **Costs:** a real outage costs a few questions before it is recognised.

### Shared names: abstain rather than guess

An artist is identified only by an exact name match. Where several artists
share the name, up to three titles the listener holds decide which is meant.
If that does not settle it, the name is reported as ambiguous.

- **Rather than:** taking the top-ranked match.
- **Gains:** a discography is never filed under the wrong artist.
- **Costs:** a few names go unanswered; a few titles are sent to tell them
  apart.

### Years narrow what is offered, never who is asked

A year range filters the albums offered by their first release. It never
filters which of the listener's own artists are asked about.

- **Rather than:** filtering the library by the same years.
- **Gains:** an old album on the shelf can still lead to a new release.
- **Costs:** none recorded.

### A run is priced before it starts

Before a run widens to compilations or series, the dialog says how many more
artists and series that means and roughly how many minutes, at the pace the
catalogue permits. No duration is promised.

- **Rather than:** a box with an unstated consequence; a time target nobody
  could verify.
- **Gains:** the listener chooses a long run knowingly.
- **Costs:** the figure is a pace rather than a forecast; a busy catalogue
  makes the real run longer.

### Time left comes from the run's own pace

The time remaining is measured from how fast the run is actually going. It
says nothing until there is enough to measure.

- **Rather than:** arithmetic from the configured pace.
- **Gains:** honest on the slow runs that need it most.
- **Costs:** no estimate in the first moments.

### A genre needs real support

A genre the catalogue states for an artist counts only with at least two votes
and at least half the votes of the artist's leading genre.

- **Rather than:** every stated genre counting equally.
- **Gains:** a genre filter means what it says; a single stray tag no longer
  puts a rock band under house.
- **Costs:** some genuine secondary genres are lost too.

### An artist with no genre is judged by who it resembles

A similar artist the catalogue gives no genre is judged by the genres of the
listener's albums by the artist it was suggested for. Where that gives nothing
either, it is marked unknown rather than dropped.

- **Rather than:** dropping every artist the catalogue has not tagged.
- **Gains:** most such artists become reachable through the filters.
- **Costs:** an inferred genre can be wrong.

### Three choices for what else a run takes in

Artists credited on compilations, the other volumes of series and DJ mixes
are three separate choices. The first two start clear; mixes start offered.

- **Rather than:** one box meaning several things at different costs.
- **Gains:** each cost is chosen on its own.
- **Costs:** more choices to understand; more to store with each answer.

### Series found two ways

The other volumes of a compilation series come from the catalogue's own series
list, topped up by a search for titles that differ only by volume number.

- **Rather than:** trusting the catalogue's series list alone, which stops
  short of the newer volumes.
- **Gains:** missing volumes are found even where the series list is
  incomplete.
- **Costs:** more requests; held compilation titles are sent, cut short.

### Never offer back what is owned

An album the listener holds is never suggested, whoever it is filed under. An
album is the same album whatever the year of the pressing: a remaster is the
album it remasters, while a live recording is an album of its own.

- **Rather than:** completeness at the risk of suggesting what is already on
  the shelf.
- **Gains:** every suggestion is something new.
- **Costs:** none recorded.

### Pay only for what is opened

A suggested artist's albums are fetched when the listener opens them, not
during the run.

- **Rather than:** fetching every candidate's albums up front.
- **Gains:** runs are far shorter.
- **Costs:** opening an artist takes a few seconds.

### A run works in the background; stop means stop

The dialog asks its question and leaves; progress shows on the main window
while listening carries on. Stop ends the run at once without asking;
whatever was in flight is abandoned. One run at a time; a stopped run is
discarded rather than resumed. Quitting Stellody stops a run; closing it to
the tray does not.

- **Rather than:** a modal run, a confirmation on stop or resumable runs.
- **Gains:** listening is never blocked; stop is instant; no reconciling a
  half run against a library that has changed since.
- **Costs:** a stray press loses the run; stopping costs the time spent.

### One answer, kept with its question

Each run replaces a single answer file, which records what was asked (genres,
years, choices) as well as what was found.

- **Rather than:** dated files that need tidying; merging answers.
- **Gains:** the answer on screen always matches the question that produced
  it; expanding later obeys the same choices.
- **Costs:** an earlier answer is gone once a new run completes.

### The answer is read a page at a time

The results open in a window of their own that holds the listener's attention
until closed. They are dealt into columns a page at a time, sized for a small
laptop screen, with every page built when the window opens so ticks survive
turning pages.

- **Rather than:** one long scrolling list; a window left open beside the
  main one.
- **Gains:** a long answer reads like a book; nothing ticked is lost.
- **Costs:** a large answer takes a moment to lay out; the longest names are
  shortened to fit.

### The catalogues are credited as they ask

The sources discovery uses are credited in the application, worded from their
own licence pages; no licence is invented for a source that states none.

- **Rather than:** a generic acknowledgement.
- **Gains:** the credit is what each source actually asks for.
- **Costs:** none recorded.

### Colour never carries meaning alone

Every coloured distinction is also said in words, at a contrast that can be
read.

- **Rather than:** colour as the only signal.
- **Gains:** readable for everybody.
- **Costs:** more words on screen.

## Shops

### Shops are editable search addresses

A shop is a search address with the artist and album filled in. The list
ships with defaults and is the listener's to edit.

- **Rather than:** a list compiled into the program; shop interfaces. Shops
  change without warning: one afternoon's check found one closed, one walled
  and one broken.
- **Gains:** a broken shop is an edit, not a release.
- **Costs:** search quality is whatever each shop's search gives.

### No commerce in the program

No prices, stock, baskets, accounts, scraping, affiliate links or revenue.
Digital purchases only; no streaming.

- **Rather than:** price comparison or earning from sales.
- **Gains:** no relationship with any shop; no conflict of interest.
- **Costs:** comparing prices is done in the browser.

### Updates respect the listener's edits

A new release's shop list is merged with the listener's: edits are kept,
deletions are remembered and a hand-broken entry is shown greyed for mending
rather than dropped.

- **Rather than:** overwriting the list; silently discarding what does not
  parse.
- **Gains:** improvements arrive without undoing anybody's changes.
- **Costs:** the merge rules are intricate.

### Ask before opening many tabs

More than a handful of albums at once asks first. Copying the list as text is
always available instead.

- **Rather than:** opening any number of tabs on one press.
- **Gains:** no browser buried by accident.
- **Costs:** one more question on a large selection.

## The interface

### Smaller by default

The whole interface is drawn at nine tenths of its natural size; the
standard Qt scale setting overrides it.

- **Rather than:** shrinking parts of it.
- **Gains:** fits a small high-resolution laptop screen.
- **Costs:** at ordinary resolution a point is drawn smaller than a pixel, so
  thin rules need drawing with care to stay visible.

### One home for every colour

Every colour is defined once, in light and dark sets, with the accent taken
from the application's own artwork; contrast is checked by test.

- **Rather than:** colours written where they are used.
- **Gains:** the two appearances stay consistent; a colour that cannot be read
  fails the suite rather than shipping.
- **Costs:** a new colour has to earn its place in the palette.

### Two views of one library

The cover grid and the list are two views over one model. The open album's
tracks sit in a pane below the grid, as tall as the album needs up to half the
page.

- **Rather than:** a pane inserted inline among the covers, which would need a
  view of Stellody's own and lose keyboard reach.
- **Gains:** switching views keeps the selection; the keyboard reaches
  everything.
- **Costs:** the tracks sit below the covers rather than beside the album.

### Browsing is never dragged back

The highlight follows playback only when the playing track changes, so a
listener browsing elsewhere is not pulled back to it.

- **Rather than:** a highlight pinned to whatever is playing.
- **Gains:** browsing and listening do not fight.
- **Costs:** none recorded.

### Closing asks once; one copy runs

The close button asks whether to quit or keep playing from the tray. It can
remember the answer; dismissing the question decides nothing. A second launch
hands over to the copy already running.

- **Rather than:** closing always quitting; several copies playing at once.
- **Gains:** music can carry on with the window out of the way; there is only
  ever one player.
- **Costs:** one more question until it is remembered.

### Nothing promises what is not built

No control may say a feature is coming. A structural sweep forbids it.

- **Rather than:** disabled buttons for planned features.
- **Gains:** everything on screen works.
- **Costs:** planned work is invisible until it ships.

### A switch shows what a press will do

Each switch carries the picture of the state a press leads to.

- **Rather than:** showing the current state.
- **Gains:** one convention everywhere.
- **Costs:** learned once.

### Everything reachable from the keyboard and the menus

Every button bar the volume and the donation button is mirrored on the menu
bar, every control is on the keyboard ring and the focus ring is drawn on
controls, never on the panes that hold them.

- **Rather than:** mouse-first controls.
- **Gains:** the whole application works without a mouse.
- **Costs:** every new control needs its menu entry and its place in the ring.

### Reading dialogs read themselves

Long help and report pages scroll gently on their own and stop the moment the
reader takes over.

- **Rather than:** static pages.
- **Gains:** long text can be read hands free.
- **Costs:** none recorded.

### The guide is drawn from the real controls

The help guide uses the same pictures as the controls it explains.

- **Rather than:** screenshots or hand-drawn pictures.
- **Gains:** the guide cannot drift from the interface.
- **Costs:** the guide is generated, not freely laid out.

### A window that does not fit is maximised

The window remembers its size and opens maximised on a first run. A window too
large for the screen opens maximised rather than being shrunk or moved.

- **Rather than:** nudging or resizing it.
- **Gains:** nothing opens partly off the screen.
- **Costs:** none recorded.

## Building and installing

### Nuitka

The application is compiled with Nuitka into a single executable on Windows
and a packaged application on macOS. It was chosen over PyInstaller when
selling Stellody was under consideration, because compiling ships no readable
source. The source is now public under the GPL, so that reason has lapsed; one
tool building both platforms is the reason it stays.

- **Rather than:** PyInstaller, which bundles the source as it is.
- **Gains:** one set of packaging behaviour across Windows and macOS; far
  smaller packages (measured when it replaced PyInstaller, the application
  fell from 123 MiB to 27 and the setup program from 105 MiB to 49).
- **Costs:** quirks of its own; some modules must be named explicitly, which
  ties the build to particular library versions.

### Installed for one user, without administrator rights

On Windows the setup program installs into the user's own folders and
registry. On Linux the Flatpak may read the home folder but not write it.

- **Rather than:** a machine-wide install.
- **Gains:** no administrator prompt; on Linux the read-only promise is
  enforced by the system as well as by the code.
- **Costs:** each account on a machine installs separately.

### A setup program of its own

Install, update, repair and removal are one bespoke program wearing the
application's own look. It reads the application's shared code but never opens
the library database; it leaves a note for the application instead. It checks
the whole payload before writing anything; removing Stellody keeps the
listener's data unless asked otherwise.

- **Rather than:** a generic installer.
- **Gains:** one identity throughout; the database is never touched at its
  least safe moment.
- **Costs:** the setup program is Stellody's own to maintain.

### Each platform builds on itself

Windows, macOS and Linux packages are each built on their own platform; the
macOS one is signed and notarised.

- **Rather than:** cross-compiling; shipping macOS unsigned.
- **Gains:** each package is built by the tools that know that platform.
- **Costs:** a machine of each kind to build on; an Apple developer account
  for the signing.

### Two licences plus a commercial one

The model is GPL-3.0 and the interface LGPL-3.0. The packaged application is
distributed under GPL-3.0 because of the codecs in the bundled FFmpeg. A
commercial licence for Stellody's own code is offered separately.

- **Rather than:** one licence for everything.
- **Gains:** the interface can be reused under the lighter terms Qt itself
  carries.
- **Costs:** two licence files to keep straight.

### A website written for the listener

The website explains what Stellody does for somebody who will use it: no
repository links, build instructions or dependency lists. It carries no dates.

- **Rather than:** a developer's project page.
- **Gains:** the people deciding whether to install it find what they need.
- **Costs:** developers go to the repository instead.

### Exact versions for what ships

The libraries the application ships with are pinned to exact versions and a
test checks the installed ones match. Development tools only have floors.

- **Rather than:** minimum versions throughout.
- **Gains:** a build of one commit is the same build whenever it is made.
- **Costs:** every upgrade is a deliberate change to the pins.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface,
each allowed to depend only inward, with one composition root wiring them
together by constructor. Structural tests hold the boundaries.

- **Rather than:** convention alone; a dependency injection framework.
- **Gains:** the rules about music and discovery can be tested with no disk,
  network, clock or screen.
- **Costs:** more modules and more explicit wiring.

### Complete coverage where it means something

Branch coverage must be total over the domain and application layers. The
layers that talk to devices, disks and the screen are tested but not held to
a figure.

- **Rather than:** one figure over the whole program, which could only be met
  with mocks standing in for the very things worth testing.
- **Gains:** anything short of complete in the pure layers is a decision
  nobody made.
- **Costs:** device, file and screen code relies on targeted tests.

### Small modules

No module may exceed four hundred lines; one that comes close is cut well
below rather than shaved. Build scripts are exempt.

- **Rather than:** letting files grow.
- **Gains:** modules split at real seams.
- **Costs:** many small files.

### Every value has one home

The product name, the version, each colour and the icons each come from one
place; everything else reads or is generated from it.

- **Rather than:** copies written where they are needed.
- **Gains:** a change is made once and cannot drift.
- **Costs:** static files such as the website have to be stamped from the
  source.

### Threads are owned

Every thread that outlives its errand is held until it ends; every signal is
received by a slot of an interface object, never a loose function.

- **Rather than:** fire-and-forget threads.
- **Gains:** quitting never pulls the ground from under a thread still
  working.
- **Costs:** more ceremony around background work.

### Tests with real parts

No mocking library; Qt is never mocked; the suite never reaches the network
and never starts the application. Every guard is proved by planting a
violation and watching it fail.

- **Rather than:** mocks and assumed guards.
- **Gains:** a passing test means the real thing works; a guard is known to
  bite.
- **Costs:** fakes are written by hand; the suite takes minutes rather than
  seconds.
