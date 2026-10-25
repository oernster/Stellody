# Decisions and trade-offs

The deliberate choices Stellody rests on: what was chosen, what was given up
for it and why, as the product makes them today. The detail lives in
[ARCHITECTURE.md](ARCHITECTURE.md) and the specifications
([DISCOVERY.md](DISCOVERY.md), [SHOPS.md](SHOPS.md), [FORMATS.md](FORMATS.md),
[OUTPUTS.md](OUTPUTS.md), [BACKUP.md](BACKUP.md)); [PLAN.md](PLAN.md) holds
what is deliberately not planned.

## The product as a whole

### Local first, one listener, one machine

Everything Stellody knows is kept on the computer it runs on, for one person,
rather than in a server, an account or anything synchronised. There is nothing
to sign in to and it works offline; the library notes reach another machine
only in a backup.

### Python and PySide6

Python on Qt rather than Rust or Go, so the test gate, structural guards and
delivery recipe proved on earlier projects carry over. The cost is a larger
runtime than a native binary and packaging that takes more care.

### Specification before code

Each feature area is written as requirements naming their tests, with a list
of what it will not do. A ruled-out idea stays ruled out and a claim in the
docs is one a test holds; keeping the specifications true is work.

### What Stellody deliberately is not

It plays and organises music the listener already owns; it does not stream,
rip, sync to devices or write tags. The surface stays small enough to hold to
a high bar.

## Privacy and the network

### Only a named few modules may reach the network

Cover search, the update check, the discovery catalogues and the pipe handing
a second launch to the first are the only code able to open a connection; a
structural test holds the list. Shops and donations are handed to the browser.
Every new way out has to be argued for.

### Nothing names the listener; no credential compiled in

No account, telemetry, identifier or scrobbling: a discovery run sends a fixed
set of fields; the update check sends the product name alone. Only sources
needing no key are used, since a key in open source is a published key. There
are no usage figures; discovery is limited to MusicBrainz and ListenBrainz.

### Update checks: daily, quiet unless there is news

A check runs after launch and then daily, silent unless a newer release
exists; one somebody asks for always answers. A version it cannot read is
never newer. The cost is one unprompted request a day.

### No encryption at rest; a plain-text diary

The store and the diary are ordinary files in Stellody's own data directory,
where a sandbox cannot discard them (Oliver's ruling). The diary records starts and
quits, each time the main window appears, every dropout and every address a
discovery run asked; it is never sent. It has found faults reading the source could not; anyone with the
account can read it.

## The library and its files

### The library is read, never written

Music files are opened for reading only and nothing is written inside the one
library root; the Linux build is granted read access only. A wrong tag is
corrected in Stellody's own store. A curated collection cannot be damaged;
music in unrelated places has to be gathered under one root.

### Folders group albums; tags name them

A folder is where an album starts; tags give its title, artist, year and
genre. Tags may join folders but never split one, so albums are what the
person who ripped them meant. Two recordings whose tags resolve alike show as
one.

### Raw tags stored, corrections layered on loading

The store keeps tags as read; each load layers on what the listener stated,
the automatic rules and the accepted corrections, each of which can be reset.
An improved rule reaches the library without a rescan; the working out repeats
at every load.

### A rescan reads only what changed and deletes nothing

A folder unchanged in size and time is reused from the store. A scan that
cannot reach the music folder changes nothing; a folder no longer found has
its files marked absent. A rescan is near instant and unplugging a drive costs
nothing; an edit keeping size and time exactly goes unnoticed.

### A lossy copy beside its lossless original is not a second album

A lossy file sharing disc, track number and about the same length with a
lossless one is set aside. Length tells a copy from a live version; two
different recordings of equal length could in principle be paired.

### A track can be part of a file

A cue sheet over one long file is a first-class album: a track is a slice of a
file. Queueing, shuffle and gapless playback are written once; every decoder
has to start and stop at a frame.

### Unknown stays unknown; supported means proved

A bit depth, date or genre the file does not state is held as unknown, never
given a plausible default. A format plays only when a test file in it can be
generated and played end to end; the rest are reported. Nothing is claimed on
a guess; a few real lossless formats are not played.

### Ratings and plays follow the album

Ratings and play counts are keyed to album identity, so they survive a rename
or rescan; a play counts only when a track reaches its end.

### Search is a plain pass over what is shown

Search runs over the library as shown rather than SQLite's full-text index,
which would hold raw tags while the screen shows corrected ones. It finds
exactly what is on screen; the work grows with the library.

### Compilations are one artist, ordered by title; a settled genre list

Every spelling of a compilation shows as Various Artists, ordered by title
with numbers counted as numbers, so a series reads in order. Genres are a
fixed catalogue matching the catalogues' spelling, with tag strings mapped
onto it, so filters mean the same everywhere. The mapping needs keeping up.

### Cover art from the album's folder; online only when asked

A cover comes from an image beside the music, then from one embedded in the
files, kept small against the album's identity. Searching online is a chooser
the listener opens: no file carries a catalogue identifier, so an automatic
match could attach the wrong cover. Missing art stays missing until the
listener acts.

A lookup the listener asked for is worth an answer. A failure belonging to the
moment (a server error, a refusal or a timeout) is asked again at the cost of
a longer wait; a "not found" is taken as the answer. A search never answered
says so rather than claiming the album has no art. Quitting during a lookup
may wait a few seconds longer, so a slow service has time to reply.

## Backups

### A backup carries the listener's notes, not what can be rebuilt

A backup holds the database, the discovery answer, the catalogue memory, the
genre cache and the shop list; caches and logs stay behind. It is small and
quick; covers and waveforms are rebuilt after a restore.

### Judged by each file's shape; old backups always restore

Each file is listed with its schema number and its owner says whether it can
read it, rather than comparing releases. A change of shape adds an upgrade
step and never removes one, so a backup kept for years restores. The code
reading old shapes only grows.

### A restore completes at the next start

A restore writes a safety backup, stages the chosen one and restarts; the
files are put in place before the library opens, never under a running copy.
A restore failing part way puts the previous files back. The cost is a
restart.

## Playback and sound

### Its own audio pipeline

Stellody decodes and plays audio itself through libsndfile, FFmpeg and
PortAudio rather than Qt's media player, which cannot play part of a file or
equalise. A track that will not open is reported, never left as silence. It
gains cue tracks, an equalizer and in-engine gapless joins; it owns its
threading and the bundled FFmpeg makes the package GPL-3.0.

### Shared by default; bit-perfect only when proved

Music plays through the system mixer unless exclusive output is asked for,
offered only where the device can take the song. The readout says bit perfect
only when exclusive output was granted at the file's format with volume full
and no equalizer curve. No levelling is applied. No claim rests on an
unhonoured request; the default is not bit-perfect.

### The transport works by state, not timing

Back returns to the track's start, then a track back; Next always moves on;
repeat-one answers only an ending. A pause is never read as an ending and
skipping keeps playing or paused as it was. Every press does the same thing
whatever its timing.

### Video tracks follow the sound

A bonus video plays as a track with the sound as the clock, drawn in the
library area. There are no video features beyond playing it.

### A hand-written equalizer and a watching visualiser

The equalizer is written from the standard formulas: a flat curve leaves
samples untouched and headroom is made before any lift. Its switch is apart
from its sliders, so comparing keeps the curve. The visualiser measures what
reached the device and can never alter a sample. The filters are Stellody's
own to maintain.

### Music never moves to the speakers without a press

An output device is remembered by identity. If it disappears while playing
the track pauses; when it returns the music moves back. Nothing plays aloud by
surprise; a press is needed to carry on.

### Windows' own volume is reported, never reset

Windows keeps a volume and a mute for each program on each device, beyond
Stellody's reach; held at nought, the music is silent while the visualiser
still moves. When music starts Stellody reads that setting; if it silences the
music, the status line says so and where to change it. Stellody never resets
it, since that would override a choice the listener or Windows made (Oliver's
ruling). The cost is a trip to the system's settings; off Windows nothing is
asked.

### The waveform shows loudness, drawn as it is read

Loudness rather than peaks, at a resolution stated in time, measured once per
file and given up on when the listener moves away. The faster reduction was
kept only once it matched the slow answer exactly. A whole-album file still
takes seconds.

## Discovery

### Ask what is missing from the listener's own collection

Public catalogues are asked what the listener's artists released that is not
on the shelf and who resembles them, naming only artists in the ticked genres.
No account or inventory is sent and every suggestion traces to an owned album;
it is less personal than a recommender trained on habits.

### Two sources, each for one question, credited as they ask

MusicBrainz answers what an artist released; ListenBrainz answers who sounds
like them; both are credited in their own licence words. Similarity comes
from an experimental endpoint with no fallback.

### Polite, slow and remembered

Requests go through one gate paced below the published limit; a refused artist
is put back for a later pass, never read as an absence. Every answer is
written as it arrives and kept for a period; runs differ over weeks rather
than minutes (Oliver's ruling). A crash loses at most one answer; a large run
takes many minutes.

### Nothing heavy while music plays

The catalogue memory is read once as Stellody opens and written whole only at
quit, with a journal covering a crash; the Discover dialog is built once,
unseen, at launch. Either job done mid-session starved the sound device enough
to be heard. The cost is memory held all session.

### A partial answer is still an answer

A failure is recorded and the run carries on; the answer says how many could
not be asked, were not recognised or shared a name. A run of silences ends as
unavailable, keeping the previous answer.

### Shared names: abstain; never offer back what is owned

An artist is identified by an exact name match, never a ranking; a shared
name is settled by held titles or reported as ambiguous. An album or series
volume already held is never suggested. A few names go unanswered.

### Years narrow what is offered, in every genre chooser

A year range filters offered albums by first release, never which artists
are asked; the library's filter uses each album's date tag and hides an
undated one. A sparsely dated library loses albums from view while years are
set.

### A genre needs real support

A catalogue genre counts only with enough votes beside the artist's leading
one; a similar artist with none is judged by the albums that led to it. A
stray tag cannot misfile a band; some secondary genres are lost.

### What a run takes in is chosen; its time is stated

Compilation artists, series volumes and DJ mixes are separate choices. Before
a run widens the dialog says roughly how long it adds; during a run the time
left is measured from the run's own speed. A long run is chosen knowingly.

### A run works in the background; one answer, kept with its question

Progress shows on the main window while listening carries on; Stop ends the
run at once and discards it. Each run replaces one answer that records what
was asked, so the answer on screen always matches its question.

### A taste profile is the whole selection, in one shared list

A profile holds the genres, the Include choices and the years; one list serves
Discover and both genre choosers. A genre chooser uses only genres and years,
so profiles differing only in what they include look alike there.

### The answer is read a page at a time

Results are dealt into columns a page at a time, capped at what a 13 inch
display shows (Oliver's ruling), with every page built on opening so ticks
survive.

## Shops

### Shops are editable search addresses opened in the browser

A shop is a search address with artist and album filled in, handed to the
browser; the list is the listener's to edit. A broken shop is an edit rather
than a release. A release's list merges with the listener's: edits kept,
deletions remembered, broken rows greyed for mending. Many tabs at once asks
first.

### No commerce in the program

No prices, baskets, accounts, scraping or affiliate links; digital purchases
only. There is no relationship with any shop.

## The interface

### Smaller by default

The interface is drawn below its natural size on every screen, so it fits a
small high-resolution laptop; Qt's scale setting overrides it. Thin rules have
to draw themselves to stay visible.

### One home for every colour; colour never alone

Every colour is defined once in light and dark sets, apart from the stylesheet
applying it. Every coloured distinction is also said in words or artwork and
contrast is checked by test.

### Two views of one library

The cover grid and the list are two views of one model; the open album's
tracks sit below the grid, up to half the page. Switching views keeps the
selection.

### Browsing is never dragged back

The highlight follows playback only when the track changes; the grid glides
to a selection and a reload keeps the listener's place. Browsing and listening
do not fight.

### Closing asks once; one copy runs

The close button asks whether to quit or keep playing from the tray and can
remember the answer; dismissing it decides nothing. A second launch hands over
to the running copy. One more question until remembered.

### Controls say what they do and stay put

Each switch shows the state a press leads to. A control that cannot act is
shown switched off, never removed, with any count as a badge (Oliver's
ruling). No control may say a feature is coming. Nothing moves when a state
changes; a rarely usable control is always on show.

### Everything reachable from the keyboard and the menus

Every button bar the volume and donation is mirrored on the menu bar; every
control is on the keyboard ring with one focus ring, drawn on controls and
never on panes. A row of two buttons is a frame rather than a menu, so both
can be reached. Every new control needs its menu entry and ring place.

### The playing name leads to its album

The playing track's name along the foot opens its album, rather than a new
picture button (Oliver's ruling). An album hidden by a filter stays hidden
and the foot says so. The name shows no sign it can be clicked.

### The way out stands alone on the left

Close or Cancel stands alone at the left of a dialog's button row with the
acting controls on the right; both genre filters share one row (Oliver's
ruling). The way out is in one place everywhere; a pointer travels further.

### Reading dialogs read themselves; the guide uses real controls

Long help and report pages scroll gently until the reader takes over. The
guide is drawn with the controls' own pictures, so it cannot drift; it is
generated rather than freely laid out.

### A window that does not fit is maximised

The window remembers its size; one overhanging the screen is maximised on the
screen its title bar is on rather than nudged. Nothing opens partly off
screen.

## Building and installing

### Nuitka on Windows and macOS, each platform on itself

Windows and macOS are compiled with Nuitka rather than PyInstaller for
smaller packages; the Linux Flatpak runs the source on its runtime's Python.
Each is built on its own platform with macOS signed and notarised. Some
modules must be named explicitly; it needs a machine of each kind and an
Apple account.

### Ship what a screen can show, nothing the program never loads

Pictures ship scaled to the most pixels any screen can draw them rather than
as the full masters. Every package leaves out the other platforms' icons; the
compiled ones also leave out the Qt plugins and libraries Stellody never
loads. The download is less than half the size of shipping everything. The
cost is a build step plus a rule: a new picture format or a larger icon has to
be reflected in the build.

### Installed for one user by a setup program of its own

Windows installs into the user's folders without administrator rights; the
Flatpak may read the home folder but not write it. One bespoke program
installs, updates, repairs and removes, never opening the library database.
It is Stellody's own to maintain.

### Two licences plus a commercial one

The model is GPL-3.0 and the interface LGPL-3.0; the package is GPL-3.0
because of FFmpeg. A commercial licence for Stellody's own code is offered;
there are two licence files to keep straight.

### A website written for the listener

The site explains what Stellody does for somebody who will use it, with no
source links, build steps or dates; developers go to the repository.

### Exact versions for what ships

Shipped libraries are pinned exactly and the suite refuses to run outside the
project's environment; development tools have floors. A build of one commit
is the same whenever made.

## Engineering

### Layers with one place where they meet

Domain, application, infrastructure and interface each depend only inward,
wired in one composition root; structural tests hold the boundaries. The
rules are tested with no disk, network, clock or screen, at the cost of
explicit wiring.

### Complete coverage where it means something

Branch coverage is total over the domain and application layers; the layers
touching devices, disks and the screen are tested but held to no figure,
which only mocks could meet.

### Small modules; every value has one home

Every module has a line ceiling and one nearing it is cut at a real seam. The
name, version, colours and icons each come from one place. Nothing drifts, at
the cost of many small files.

### Threads are owned

Every thread outliving its errand is held until it ends and a cancelled one
stops where it stands; a worker's answer arrives on the interface thread.
Quitting waits for each thread; one stuck in a socket ends with the process
rather than being torn down beneath it.

### Tests with real parts

No mocking library, Qt never mocked; outward adapters are injected so the
suite never reaches the network. Every guard is proved by planting a
violation. Fakes are written by hand; the suite takes minutes.
