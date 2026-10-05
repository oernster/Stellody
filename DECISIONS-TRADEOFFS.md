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
a few JSON files, for the one person whose library it is. Chosen over a server
database, an account or anything synchronised. There is nothing to install
beside it or sign in to; it works with the network off. The cost: the library
notes belong to that one machine and follow nobody elsewhere.

### Python and PySide6

The application is written in Python on Qt for Python rather than Rust or Go,
so the test gate, structural guards and delivery recipe already proved on
earlier projects carry over and the effort goes on the player. The cost is a
larger runtime than a native binary and packaging that takes more care.

### Specification before code

Each feature area is written down as requirements before it is built, each
naming the test that proves it, with a list of what it will not do. Chosen over
building first and describing afterwards: a ruled-out idea stays ruled out and
a claim in the docs is one a test holds. Keeping the specifications true is
work of its own.

### What Stellody deliberately is not

It plays and organises music the listener already owns. It does not stream,
rip, sync to devices or write tags. Turning down the all-in-one media suite
keeps the surface small enough to hold to a high bar; those other jobs need
other tools.

## Privacy and the network

### Only a named few modules may reach the network

Fetching cover art, checking for an update, asking the discovery catalogues
and the local pipe that hands a second launch to the first are the only code
able to open a connection; a structural test holds the list. Chosen over a
promise to use the network sparingly, so "local first" is a test result and a
new way out is an edit somebody must defend. Every new outward feature must go
through an existing route or argue for another.

### Nothing names the listener or the machine

No account, telemetry, identifier or scrobbling. A discovery run sends a fixed
set of fields a test checks, with a fixed language rather than the computer's;
the update check sends the product name alone, not even its version. Chosen
over the conveniences other players offer and the defaults networking
libraries send. The cost: no usage figures to steer development; the update
server cannot tell which versions are in use.

### No credential compiled in

Only sources that need no key or token are used, rather than Discogs or
Last.fm: a key built into an open-source application is a published key and
Last.fm's terms would bind every fork. Nothing can leak. The cost: discovery is
limited to MusicBrainz and ListenBrainz; the same rule rules out music videos
and concert listings.

### Update checks: daily, quiet unless there is news

A check runs shortly after launch and then daily, saying nothing unless a newer
release exists; a check somebody asks for always answers. A version it cannot
read is never treated as newer. Chosen over no check or one that reports every
outcome: updates are found without nagging. The cost is one unprompted request
a day.

### Shops and donations go through the browser

Stellody hands an address to the default browser and stops there, rather than
making those requests itself. No connection is added inside the application
and the shop sees the listener's own browser session. Stellody never learns
what happened next.

### No encryption at rest; a plain-text diary

The store and the diary are ordinary files in the application's own data
directory. The diary records comings and goings, dropouts and every address a
discovery run asked; it is never sent anywhere. Chosen over encrypting library
notes or keeping no record: the files are simple to inspect and the diary has
found faults that reading the source could not. Anyone with access to the
account can read the library notes and the artist names a run sent.

## The library and its files

### The library is read, never written

Music files are opened for reading only and nothing Stellody keeps, cache
included, is written inside the one library root; the Linux build is granted
read access only. A wrong tag is corrected in Stellody's own store and
reported. Chosen over repairing tags on disk, sidecar files or several roots:
Stellody cannot damage a curated collection. Corrections live only in
Stellody; music spread across unrelated places has to be gathered under one
root.

### Folders group albums; tags name them

A folder is where an album starts; tags give its title, artist, year and genre.
Tags may join folders into one album (disc folders, folders whose tags agree)
but never split one; where tags contradict something physical, the physical
thing wins. Chosen over grouping by tags alone, which real collections with
inconsistent tags break apart. Albums are what the person who ripped them
meant. The stated price: two recordings whose tags resolve alike show as one.

### Raw tags stored, corrections layered on loading

The store keeps tags as read. Each load applies, in layers, what the listener
stated by hand, the automatic rules and the corrections accepted. Findings in
the health view are accepted all at once, an album at a time or singly; any
accepted correction can be reset for the library, an album or one field.
Chosen over storing the corrected result: an improved rule reaches the whole
library without a rescan; what the file says is never lost; a library's tidying
is one decision that can be taken back. The working out repeats at every load;
a rule that changes what is recorded at scan time still needs a rescan.

### A rescan reads only what changed

A folder whose music files, cue sheets and pictures are unchanged in size and
time is reused from the store. After a scan the listener is told which albums
arrived and which left, judged by album identity. Chosen over reading every
file on every scan or comparing the music files alone. A rescan of hundreds of
folders is near instant. An edit that keeps a file's size and time exactly is
not noticed; a retagged album reads as one leaving and one arriving.

### An unreachable drive is not a deleted library

A scan checks the music folder can be reached and stops without changing
anything when it cannot. A folder the walk is refused keeps its albums; one no
longer found has its files marked absent, never deleted. Chosen over
recording whatever difference the walk sees: unplugging a drive costs nothing.
A root that is genuinely gone is reported rather than cleared automatically.

### A lossy copy beside its lossless original is not a second album

Where a lossless and a lossy file share a disc and track number and run about
the same length, the lossy one is set aside. Chosen over pairing on track
number alone, which cannot tell a copy from a live version. Each recording
shows once; two genuinely different recordings of the same length could be
paired, though none has been seen.

### A track can be part of a file

A cue sheet over one long file is a first-class album: a track is a slice of a
file; a whole file is the slice that covers it all. Chosen over one file per
track, so queueing, shuffle and gapless playback are written once. Every
decoder has to start and stop at a frame rather than at a file's ends.

### Unknown stays unknown where a claim depends on it

A bit depth, date or genre the file does not state is held as unknown rather
than filled with a plausible default; the display uses the folder name or a
placeholder; a missing title, album artist or track number is reported. Chosen
over a tidy interface of invented values, so nothing (bit-perfect output, an
exact date) is claimed on a guess. Some albums show placeholders until
corrected.

### Supported means proved

A format is played only when a test file in it can be generated and played end
to end; the rest are reported in the health view, alongside a few left out on
other grounds (audiobooks; files that state too little). Chosen over playing
whatever the decoder opens: every playable path is tested and no audio files
are committed. Real files in a handful of lossless formats are not played.

### Ratings and plays follow the album, not the file path

Ratings and play counts are keyed to album identity, so they survive a rename
or rescan; a play counts only when a track reaches its end; albums and tracks
are rated separately. The listener's history outlives reorganising folders.
Merging two albums keeps the rating of the one merged into.

### Search is a plain pass over what is shown

Search runs over the library as shown on screen, with text prepared once at
load. Chosen over SQLite's full-text index, which would hold raw tags while the
screen shows corrected ones and would need rebuilding. Search finds exactly
what is on screen and is quick at real library sizes; the work grows with the
library, so a far larger collection would need measuring again.

### A settled genre list

Genres are a fixed catalogue of main genres with styles, spelled to match the
catalogues; a library's own tag strings are mapped onto it. Chosen over
offering whatever strings the tags contain: every dialog shows the same boxes
and filters mean the same thing for everybody. The mapping needs keeping up.

### Cover art from the album's folder; online only when asked

A cover comes from an image beside the music, then from a picture embedded in
the files; parent folders are never searched; covers are cached small in
Stellody's own directory. Searching online is a chooser the listener opens,
never an automatic lookup. An album never wears another's cover. The files
carry no catalogue identifiers, so an automatic match could attach the wrong
one unknowingly; anyone who never opens the chooser sends nothing. Missing art
stays missing until the listener acts.

## Playback and sound

### Its own audio pipeline

Stellody decodes and plays audio itself: libsndfile for the formats it opens,
FFmpeg (bundled through PyAV, loaded only when needed) for the rest and
PortAudio for output, queued a little deeper than the minimum so load does not
cause dropouts. Chosen over system codecs and Qt's media player, which
cannot play part of a file or equalise. It gains cue-sheet tracks, an equalizer
and one decoder behaving alike everywhere. It owns its decoding, output and
threading; the bundled FFmpeg includes GPL components, so the packaged
application is GPL-3.0.

### Shared output by default; exclusive where the platform allows

Music plays through the system mixer unless the listener asks for exclusive
output: on Windows that takes the device; on macOS it asks for the file's own
format while others can still reach the device; Linux uses the mixer only. The
switch is offered only for a song the device can take. Stellody plays alongside
everything else and never offers what it cannot keep. The default is not
bit-perfect; exclusive output on Windows locks other applications out.

### Bit-perfect only when the stream proves it; no levelling

The readout says bit perfect only when exclusive output was granted at the
file's rate and depth with volume full, unmuted and no equalizer curve. What
was asked and what was granted are kept apart; a refusal returns the switch to
shared and says why. Albums play at their mastered level with no
ReplayGain-style levelling. No claim rests on an unhonoured request or an
altered stream. The claim comes and goes as the volume moves; the listener
adjusts volume between records mastered at different levels.

### Gapless inside the engine

The next track is joined inside the playback thread without stopping the
stream, rather than reopening it per track. Two joins stay gapped on purpose:
a change of sample rate; a shuffled album starting again. Albums meant to run
without a break do; a sample-rate change leaves a gap.

### The transport works by state, not timing

Back returns to the track's start and waits; pressed again it goes to the
previous track. Next always moves on, even on repeat. Shuffle begins with the
track in hand and never reopens on the one that just ended; under shuffle Back
never leaves the track in hand. Skipping keeps playing or paused as it was; a
pause is never read as an ending. Volume starts below full. Chosen over
double-press timing windows: every press does the same thing; a first run is
never startling.

### Video tracks follow the sound

A bonus video plays as a track; the sound is the clock and the picture is drawn
at its own size in the library area, filling the window only when asked.
Chosen over a separate window or a stretched picture, so video is part of the
album. There are no video features beyond playing it.

### A hand-written equalizer and a watching visualiser

The equalizer is written from the standard filter formulas: a band at zero
costs nothing, so a flat equalizer leaves samples untouched; headroom is made
before any lift. The always-on spectrum is measured from what was written to
the device in the equalizer's own bands and idles when nothing plays. Chosen
over a large scientific library for one function and over a display in the
audio path: the package stays small and the visualiser can never delay or
alter a sample. The filters are Stellody's own to maintain.

### Music never moves to the speakers without a press

An output device is remembered by identity, not name. If it is missing, music
plays on the system default and says so; if it disappears while playing, the
track pauses; when it returns the music moves back. Chosen over forgetting the
choice or carrying on through whatever is left: nothing plays aloud by
surprise. A press is needed to carry on after a disconnect.

### The waveform: faster only with the same answer

The waveform is reduced over whole blocks of samples (kept only once it gave
bit-for-bit the frame-by-frame result) and drawn as it is read. It shows
loudness rather than peaks, which crowd every moment near the top. A long track
shows its shape almost at once; a whole-album file still takes seconds.

## Discovery

### Ask what is missing from the listener's own collection

Discovery starts from the albums the listener owns and asks public catalogues
what those artists released that is not on the shelf and which artists
resemble them. A run names only artists inside the ticked genres, plus titles
in a few stated cases; tick nothing and nothing leaves. Chosen over a
listening history, a profile or sending the whole library: there is no
account, what is sent is a chosen subset rather than an inventory and every
suggestion traces to an owned album. It is less personal than a recommender
trained on habits; other genres need another run.

### Two sources, each for one question, credited as they ask

MusicBrainz answers what an artist released; ListenBrainz answers who sounds
like them; they are joined through MusicBrainz identifiers. Both are credited
in the application in words from their own licence pages; no licence is
invented for a source that states none. Chosen over one commercial service
needing a key: open data, no key. Similarity comes from an experimental
endpoint with nothing to fall back to.

### Polite, slow and remembered

Requests to MusicBrainz are paced a little below its published limit through
one gate shared by everything that asks it; a refusal gets one quick retry,
then waits for a later pass. Every answer is kept for a month and written to
disk as it arrives. Runs finish instead of being refused; the same library
gives the same answer; later runs ask little; a crash loses at most one answer.
A large run takes many minutes; a new release can take a month to appear.

### A partial answer is still an answer

An artist a busy catalogue refused is retried on a later pass; any other
failure is recorded and the run carries on. The answer says separately how
many could not be asked, were not recognised or shared a name; a run that
found nothing still opens to say why. A run of silences ends it as
unavailable, keeping the previous answer. Chosen over ending on the first
failure or hiding failures in one total. A real outage costs a few questions
before it is recognised.

### Shared names: abstain rather than guess

An artist is identified only by a match on the name itself (case, accents and
dashes set aside), never by a ranking. Where several share the name, a few
titles the listener holds decide; failing that, the name is reported as
ambiguous. A discography is never filed under the wrong artist; a few names go
unanswered and a few titles are sent to tell them apart.

### Years narrow what is offered; pay only for what is opened

A year range filters offered albums by first release, never which of the
listener's artists are asked about. A suggested artist's albums are fetched
when the listener opens them rather than during the run, except with a year
range set: then the run asks each suggested artist, offers none not shown to
have released inside the range and answers opening from memory. An old album
can still lead to a new release and runs are far shorter. Set years cost a
question per suggested artist; opening one not asked about waits on the
catalogue.

### Time is stated from pace, never promised

Before a run widens to compilations or series, the dialog says how many more
artists and series that means and roughly how many minutes at the permitted
pace. During a run the time left is measured from the run's own speed and says
nothing until there is enough to measure. Chosen over unstated consequences or
arithmetic from configured pace: the listener chooses a long run knowingly. A
busy catalogue makes a run longer than quoted; there is no estimate at first.

### A genre needs real support

A genre the catalogue states for an artist counts only with enough votes,
relative to the artist's leading genre; an artist whose genres are all thinly
voted keeps them all. A similar artist with no genre is judged by the genres
of the listener's albums by the artist it was suggested for; failing that the
filter holds it back and says how many it could not judge. A stray tag no
longer puts a rock band under house. Some genuine secondary genres are lost;
an inferred genre can be wrong.

### Three choices for what else a run takes in

Artists credited on compilations, other volumes of series and DJ mixes are
three separate choices; the first two start clear, mixes start offered. Series
volumes come from the catalogue's series list topped up by a search for titles
differing only by volume number. Each cost is chosen on its own and missing
volumes are found where the list is incomplete. More choices to understand;
more requests; held compilation titles are sent, cut short.

### Never offer back what is owned

An album held under an artist is never suggested for that artist, however the
name is spelled; a series volume held anywhere is never suggested. A remaster
is the album it remasters, while a live recording is its own album. Chosen
over completeness at the risk of offering what is on the shelf. An album held
under a different name can still be suggested.

### A run works in the background; stop means stop

The dialog asks its question and leaves; progress shows on the main window
while listening carries on. Stop ends the run at once without asking. One run
at a time; a stopped run is discarded rather than resumed; quitting stops a
run, closing to the tray does not. Chosen over a modal run, a confirmation or
resumable runs. A stray press loses the run, though what it learned is
remembered.

### One answer, kept with its question

Each run replaces a single answer file recording what was asked (genres,
years, choices) as well as what was found. Chosen over dated files needing
tidying: the answer on screen always matches its question and expanding later
obeys the same choices. An earlier answer is replaced once a new run
completes, except for artists that run could not reach.

### The answer is read a page at a time

Results open in a window that holds attention until closed, dealt into columns
a page at a time sized for a small laptop, with every page built on opening so
ticks survive turning pages. Chosen over one long list or a window beside the
main one. A large answer takes a moment to lay out; the longest rows do not
fit a column whole.

## Shops

### Shops are editable search addresses

A shop is a search address with the artist and album filled in; the list
ships with defaults and is the listener's to edit. Chosen over a compiled list
or shop interfaces, since shops change without warning: a broken shop is an
edit, not a release. Search quality is whatever each shop's search gives.

### No commerce in the program

No prices, stock, baskets, accounts, scraping, affiliate links or revenue;
digital purchases only, no streaming. There is no relationship with any shop
and no conflict of interest. Comparing prices is done in the browser.

### Updates respect the listener's edits

A new release's shop list is merged with the listener's: edits are kept,
deletions remembered and a hand-broken entry is shown greyed for mending
rather than dropped. Improvements arrive without undoing anybody's changes;
the merge rules are intricate.

### Ask before opening many tabs

More than a handful of albums at once asks first; copying the list as text is
always available instead. No browser is buried by accident, at the cost of one
more question on a large selection.

## The interface

### Smaller by default

The whole interface is drawn below its natural size; the standard Qt scale
setting overrides it. It fits a small high-resolution laptop screen. At
ordinary resolution a point is drawn smaller than a pixel, so thin rules need
care to stay visible.

### One home for every colour; colour never alone

Every colour is defined once, in light and dark sets, with the accent taken
from the application's artwork. Every coloured distinction is also said in
words; contrast is checked by test wherever colour carries text or meaning.
Chosen over colours written where used or colour as the only signal: the two
appearances stay consistent and unreadable colour fails the suite. A new
colour must earn its place; there are more words on screen.

### Two views of one library

The cover grid and the list are two views over one model; the open album's
tracks sit in a pane below the grid, as tall as needed up to half the page.
Chosen over a pane inline among the covers, which would need a custom view and
lose keyboard reach. Switching views keeps the selection; the tracks sit below
the covers rather than beside the album.

### Browsing is never dragged back

The highlight follows playback only when the playing track changes, so a
listener browsing elsewhere is not pulled back; browsing and listening do not
fight.

### Closing asks once; one copy runs

The close button asks whether to quit or keep playing from the tray; it can
remember the answer and dismissing it decides nothing. A second launch hands
over to the copy already running. Music can carry on with the window away and
there is only ever one player; there is one more question until remembered.

### Nothing promises what is not built

No control may say a feature is coming; a sweep of every control forbids it.
Everything on screen works; planned work is invisible until it ships.

### A switch shows what a press will do

Each switch carries the picture of the state a press leads to rather than the
current state: one convention everywhere, learned once.

### A control that cannot act is shown switched off, never removed

A control with nothing to do just now keeps its place, switched off and ringed
in red, rather than appearing only when it can act; a count it owes rides on it
as a badge (Oliver's ruling). Chosen over controls that come and go: nothing in
a tray moves when a state changes and every control can be found before it is
needed. The cost is a control that is rarely usable always on show.

### Everything reachable from the keyboard and the menus

Every button bar the volume and the donation button is mirrored on the menu
bar; every control is on the keyboard ring; the focus ring is drawn on
controls, never on the panes that hold them. The whole application works
without a mouse; every new control needs its menu entry and its place in the
ring.

### Reading dialogs read themselves; the guide uses real controls

Long help and report pages scroll gently on their own and stop the moment the
reader takes over. The help guide is drawn with the same pictures as the
controls it explains rather than screenshots, so it cannot drift from the
interface; the cost is a guide generated rather than freely laid out.

### A window that does not fit is maximised

The window remembers its size (held to the screen it opens on) and opens
maximised on a first run; one that still overhangs the screen once shown is
maximised rather than nudged aside. Nothing opens partly off the screen.

## Building and installing

### Nuitka

The application is compiled with Nuitka into a single executable on Windows
and a packaged application on macOS, rather than bundled by PyInstaller. One
tool builds both platforms with one set of packaging behaviour and far smaller
packages. It has quirks of its own: some modules must be named explicitly,
which ties the build to particular library versions.

### Installed for one user by a setup program of its own

On Windows the setup program installs into the user's own folders and
registry without administrator rights; on Linux the Flatpak may read the home
folder but not write it, so the read-only promise is enforced by the system as
well. Each account installs separately. Install, update, repair and removal
are one bespoke program wearing the application's look. It reads the
application's shared code but never opens the library database, leaving a
note instead; it checks every payload file lands
inside the install folder before unpacking any; removal keeps the listener's
data unless asked. Chosen over a machine-wide generic installer: no
administrator prompt, one identity throughout and the database untouched at
its least safe moment. It is Stellody's own to maintain.

### Each platform builds on itself

Windows, macOS and Linux packages are each built on their own platform; the
macOS one is signed and notarised. Chosen over cross-compiling or shipping
macOS unsigned. It needs a machine of each kind and an Apple developer account.

### Two licences plus a commercial one

The model is GPL-3.0 and the interface LGPL-3.0; the packaged application is
GPL-3.0 because of the bundled FFmpeg codecs. A commercial licence for
Stellody's own code is offered separately. The interface can be reused under
the lighter terms Qt itself carries; there are two licence files to keep
straight.

### A website written for the listener

The website explains what Stellody does for somebody who will use it: no links
into the source, build instructions, dependency lists or dates. The people
deciding whether to install it find what they need; developers go to the
repository.

### Exact versions for what ships

The libraries the application ships with are pinned exactly and a test checks
the installed ones match; development tools only have floors. A build of one
commit is the same whenever it is made; every upgrade is a deliberate change to
the pins.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface, each
depending only inward, with one composition root wiring them by constructor;
structural tests hold the boundaries. Chosen over convention alone or a
dependency injection framework: the rules about music and discovery are tested
with no disk, network, clock or screen. The cost is more modules and explicit
wiring.

### Complete coverage where it means something

Branch coverage must be total over the domain and application layers; the
layers that talk to devices, disks and the screen are tested but not held to a
figure. One whole-program figure could only be met with mocks standing in for
the things worth testing. Anything short of complete in the pure layers is a
decision nobody made; device, file and screen code relies on targeted tests.

### Small modules

Every module has a line ceiling; one that comes close is cut well below rather
than shaved; build scripts are exempt. Modules split at real seams, at the
cost of many small files.

### Every value has one home

The product name, the version, each colour and the icons each come from one
place; everything else reads or is generated from it. A change is made once
and cannot drift; static files such as the website have to be stamped from the
source.

### Threads are owned

Every thread that outlives its errand is held until it ends; an answer from a
worker thread is received by a method of an object on the interface thread,
never a loose function that would run on the worker's. Quitting never pulls
the ground from under a working thread, at the cost of more ceremony around
background work.

### Tests with real parts

No mocking library; Qt is never mocked; the suite never reaches the network
and never starts the application. Every guard is proved by planting a
violation and watching it fail. A passing test means the real thing works;
fakes are written by hand and the suite takes minutes rather than seconds.
