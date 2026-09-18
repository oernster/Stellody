# <img width="128" height="128" alt="application-icon" src="https://github.com/user-attachments/assets/856669d1-6207-4f38-8ed6-816c6b05a40f" /> Stellody

**A free music player for the collection already on your computer.**

*Stellar* and *melody*, run together. The icon says the same thing: a note over
a galaxy, wearing a planet's ring.

No account, no subscription, no adverts and nothing about you sent anywhere.
Point it at your music folder and it does the rest.

Above all, it never changes a single one of your files.

[Download](https://stellody.co.uk/download.html) for Windows, macOS or Linux
&middot;
[stellody.co.uk](https://stellody.co.uk/)

> **Commercial licences available.** Stellody is free and open source under
> GPL-3.0, with its interface layer under LGPL-3.0. If those terms do not suit
> what you are building, such as a closed-source product, a commercial licence
> can be bought from me separately. It covers my own code; PySide6 (LGPL-3.0)
> and the bundled FFmpeg build (LGPL-3.0-or-later, linking libx264 and libx265
> under GPL-2.0-or-later) keep their own terms. See
> [commercial licensing](https://ernster.dev/commercial-licensing.html).

## Why it exists

Someone spent years turning a shelf of CDs into files: ripping each one,
checking the track names, fixing the artist on the compilations, finding the
right cover art. Then a well known music player reached into those files and
rewrote the information stored inside them. It damaged 33 albums. The music
still played. Every one of those albums was put right in the end; a music player
should never have touched them.

Stellody is built on one rule that everything else follows from: your files are
opened to be read and never to be changed. Where it finds something muddled in
the way an album is labelled, it tells you plainly then leaves the file exactly
as it found it.

That is not a promise on a page. It is checked by the test suite every time the
checks run; if it ever stopped being true the suite would fail.

## What you get

- **A wall of album covers**, else a plain list, whichever suits you. Click a
  cover and the album opens underneath without losing your place. Switching
  between the two lands where you were, so whatever is playing is picked out
  either way: its row is marked in both views and its name sits along the foot
  of the window. In the list, one press on the arrow at the left of the Title
  heading opens every album at once; another closes them.
- **Search that narrows as you type**, however many thousands of songs you
  have. The album stays whole around whatever you were looking for.
- **Albums that flow.** Records made to run straight through play that way,
  with no silence dropped in where the artist never put one.
- **An equalizer, plus little bars that dance.** Ten sliders from deep bass to
  high treble, with twenty bars along the bottom showing what the music is
  doing. A curve that lifts any part of the sound first lowers the whole record
  by as much as it lifts, so a loud record never clips; music plays quieter
  with such a curve on, while a curve that only cuts keeps its level. Switched
  off it adds nothing of its own, handing each block back untouched; at full
  volume nothing else in Stellody touches the samples either. Volume, mute,
  exclusive output and the equalizer sit together at the right end of the
  bottom strip, ahead of shuffle and repeat.
- **Exclusive output, for the track exactly as the file holds it.** One press
  on the bottom strip asks the sound device for the music with the system
  mixer out of the way, which is the only way it can be bit perfect. Pressing
  it reopens the song in hand where it was; a paused song stays paused. Beside
  the playing time sits what the device actually took: the mode, the rate, the
  depth plus "bit perfect" where that is true. Bit perfect also needs the volume at
  100% and the equalizer off, since either one alters the samples. It is
  offered only for a song the device can take untouched: not for a lossy song
  such as an MP3, which has nothing to deliver untouched, nor at a rate the
  device does not take. A Bluetooth headphone taking 48 kHz alone cannot have a
  44.1 kHz CD rip that way. For such a song the switch is shut off, with the
  reason on it naming the rates the device does take; the choice stands, so
  the next song that can have it gets it without a press. With no song
  selected the device is judged against your library instead: the switch is
  shut off where the device takes none of the rates your lossless songs are
  at. Changing the sound output while Stellody runs asks the new device
  again, so the right device brings the switch back. A device that turns
  down a request it was expected to take, because another application holds
  it say, takes the switch back to shared; the foot of the window says why.
  Stellody remembers the choice between sessions.
  - **Windows** hands the device over outright, so no other application can
    play through it meanwhile.
  - **macOS** runs the device at the song's own rate and refuses to convert,
    so the samples arrive untouched while another application playing at the
    same time is still mixed in.
  - **Linux** does not offer it; the music plays through the system mixer.
- **No crackle when the computer is busy.** The sound device keeps about two
  blocks of music queued rather than the sliver it would choose for itself, so
  a machine working hard at something else does not break the sound up. Any
  dropout that still happens is written in the diary described under Your
  privacy.
- **Headphones in, music paused.** When your computer's sound output changes,
  say because headphones connected, Stellody pauses rather than carrying on
  through the old one. Both play buttons show play and the foot of the window
  says why; press play and it carries on through the new output from where you
  last heard it.
- **The shape of each song** drawn along the bottom, so you can see the quiet
  parts and the loud ones. Click anywhere on it to jump there.
- **Stars and play counts.** Every song shows its rating in a Rating column
  beside Plays, in the list and in the album opened under the covers, so you can
  read down a record to see what you keep coming back to. Click a star to rate;
  clicking the star already held clears it. The number keys 1 to 5 rate the
  highlighted song and 0 clears it. The album keeps a rating of its own, set in
  the header of its pane. The play count of the song in hand also sits beside
  its shape. Only a song that plays on to its end counts; pressing Next before
  then does not.
- **Album art found for you**, from what your files already carry. For an album
  with none, ask Stellody to look then pick from what it finds. It never
  guesses.
- **Your messy collection, sorted out.** An album saved as one long file, a box
  set spread over several folders, a bonus disc with no number in its name: all
  of it comes out as one album where there should be one album.
- **A scan that says what it found.** Add music, press Rescan and you get the
  new albums by name, the new tracks counted and your library's totals, rather
  than a line that disappears while you are looking elsewhere.
- **Say what an album really is.** Where a tag is wrong rather than merely
  muddled, state the artist, the title, the date or the genre yourself and
  Stellody remembers it. A single song takes its own title, artist, disc number
  and track number the same way, even one song of an album saved as one long
  file. Genres come from a settled list of eighteen headings
  with their styles under them, so the same music cannot end up under three
  spellings of one word. Your files are read for this and never written.
- **Show me only the folk.** Narrow the wall of covers to the genres you ask
  for, including the albums that state none at all, then clear it in one press.
  Every tick widens what is shown, so asking for two genres shows both.
- **What your collection is missing.** Discovery sits at the right end of the
  top tray, beside the appearance toggle and Help. Tick the genres worth
  looking in and Stellody asks two public music catalogues what those artists
  made that you do not hold, along with who else sounds like them. Tick the box
  for compilations and it asks about the artists on their tracks too, saying
  first roughly how many minutes that adds. It reports as it goes, says roughly
  how long is left and stops the moment you ask it to or quit Stellody. Where it
  could not get a usable answer about somebody and holds none from an earlier
  run, it says so and counts them, with the names one press away, so an answer
  with gaps in it never reads like a complete one. Every answer is kept the
  moment it arrives, so a run stopped or cut short loses nothing it had already
  paid for and a second attempt asks only for the rest. What it finds opens as
  a list you can read and tick, dealt across the width of the screen and turned
  a page at a time, then narrowed to some of the genres it looked in when the
  answer runs long. From there Find in shops takes the ticked albums to the
  shop you choose, opening that shop's own search for each of them in your
  browser. The shops on offer are yours to add, edit, delete and reorder on the
  screen where you choose one.
  Nothing is bought here and nothing is streamed: Stellody hands over a search
  and stops.
- **The videos that came with the album.** A bonus video sits in the album it
  belongs to, plays from the same press as any song and draws its picture at
  the size it was made; fill the window when you want it larger.
- **Corrections you can keep.** Where an album's labelling is muddled, Stellody
  works out what it should be and shows you the tidy version. Now you can tell
  it to keep that answer, all of it at once or one album at a time, so the same
  list of problems stops greeting you at every start. Changed your mind? One
  press puts it back, for one group of files, one album or the lot. Your files
  are untouched either way.
- **A guide to the window itself.** Help then Guide names every button on both
  trays beside the picture the window actually draws, so nothing has to be
  recognised from a description. Under that sit the four rules no single screen
  can state for itself: your files are only ever read, folders group while tags
  name, a correction differs from a stated tag, ratings follow the album rather
  than the file.
- **How to lay a library out.** Stellody reads a collection the way it finds
  it, so the same guide states the rules it reads by: one album to a folder,
  discs of one release side by side, two folders joining where the artist and
  the title both agree, a cue sheet read only where the folder holds one audio
  file. The short version is put in front of you before you choose a music
  folder for the first time, so you can go and look at what you have rather
  than find out afterwards.
- **Everything reachable from the keyboard.** Every button on both trays bar
  the donation button is on the menu bar too, down to the repeat mode and the
  size of the album art.

The [features page](https://stellody.co.uk/features.html) has the lot.

## Before you download

- **It plays FLAC, MP3, Ogg, Opus, WAV, AIFF, M4A, WMA, WavPack and AAC.** Not
  Monkey's Audio, Musepack, DSD, TAK, TrueAudio, CAF or an M4B audiobook.
  A file in one of those formats is named in the health report rather than
  passed over, as is one whose details cannot be read, so a missing album says
  so instead of simply not appearing. An M4A
  carries either AAC or ALAC and Stellody tells them apart: ALAC states the
  depth it stores, while AAC is lossy and states none. WMA and AAC are lossy on
  the same terms; WavPack is lossless and keeps the depth it states. A bonus
  video that came with an album plays as well, from the same MP4 container
  under a `.m4v` name.
- **The last three of those are proved differently, so here is what that
  means.** Every other format on that list was tested against files somebody
  owns. There were none of WMA, WavPack or AAC to test with, so each is proved
  against a file the test suite encodes for the purpose. That exercises the
  whole path, the walk, the tags, the decode and the honesty rules; it does not
  tell anybody what a Windows Media ripper of 2004 actually wrote. If one of
  yours is read wrongly, that is a defect worth reporting rather than a format
  nobody thought about.
- **Windows, macOS and Linux.** A setup program on Windows, a disk image
  on macOS and a Flatpak on Linux. Out of the box the sound reaches the device
  through the system mixer, which converts on the way, so it is not bit
  perfect. Exclusive output, described above, takes the mixer out of the way
  on Windows and macOS; Linux does not offer it.
- **Sized to fit a laptop screen.** Everything is drawn at nine tenths of the
  size it is built at, so the whole window fits a 13 inch 4K screen at 300%
  scaling. To choose a different size, set the `QT_SCALE_FACTOR` environment
  variable before starting Stellody; it uses yours rather than its own.
- **It is a player, nothing more.** It does not stream, does not copy your CDs,
  does not sync to a phone and will not reorganise your files by rewriting
  them. It will point your browser at a shop selling what you are missing; it
  sells nothing itself, holds no account with any shop and takes nothing from a
  sale.
- **It reads; it never repairs.** It tidies muddled labelling in its own view
  and lets you keep that, though it will never rewrite the files themselves:
  that is the whole point rather than a limitation. A control that cannot do
  anything just now is shown switched off rather than left to disappoint you.

## Your privacy

Stellody does not know who you are. No account, no profile, no newsletter and
no record kept anywhere of what you listen to. Your music plays perfectly well
with the internet switched off.

Five things reach outside your computer at all, so here are all five:

- **Looking for album art**, only ever when you ask, one album at a time.
- **Checking for a new version**, a few seconds after Stellody starts and once
  a day while it runs. It sends nothing about you or
  your music, not even which version you have: the request names the program
  and asks for one public page. Then it stays quiet unless there is something
  new. Where there is, pressing Download hands your browser the file for your
  platform, else the release page when the release carries none, exactly as the
  two entries below hand over an address.
- **Looking for music you do not own**, only ever when you ask. A discovery run
  names the artists inside the genres you ticked to two public music
  catalogues, MusicBrainz and ListenBrainz, then asks what those artists made
  that you do not hold. What goes out is those artist names, the MusicBrainz
  identifiers the catalogues give back for them and for the similar artists
  they find, the fixed settings each request states for itself (the answer's
  format, how many results to return, which release types to list, which
  details to include and which similarity algorithm to use) plus a user agent
  naming Stellody, its version and the project's contact address: not your
  library, not a count of it, not a word about you or your machine. Tick
  nothing and nothing leaves.
- **Reaching a shop**, which hands an address to your web browser. Tick albums
  a run found, choose a shop and Stellody gives the browser one search address
  per album, carrying the artist, the title or both as that shop's address
  asks. Stellody connects to no shop, holds no account with one and takes
  nothing from any sale.
- **The donation button**, which hands an address to your web browser. Stellody
  itself connects to nothing. It is one button on the bottom strip and the only
  place money is mentioned; its tooltip offers to buy the author a drink, which
  is the whole of the asking. Nothing prompts you beyond that button being
  there, nothing reminds you later and nothing about the program changes if you
  never press it.

It does not encrypt anything at rest: the store holds notes about your library,
not secrets. It also keeps a plain-text account of its own comings and goings,
named `stellody-diary.log` and written in Stellody's own data directory beside
the library database: `%LOCALAPPDATA%\Stellody` on Windows,
`~/.local/share/stellody` on Linux and `~/Library/Application Support/Stellody`
on macOS. A Linux flatpak keeps its own copy of that directory under
`~/.var/app/uk.codecrafter.Stellody/data/stellody`. It records no audio and
nothing about you; during a discovery run it notes each address asked, which
carries the artist names sent. A playback dropout is noted there too, with
where in the track it fell. Beside it, `stellody-startup.log` holds the
reason when Stellody could not start. Neither is ever sent anywhere; either can
be deleted whenever you like.

## Installing

**Windows.** Download the setup program and run it. It installs just for you, so
Windows will not ask for an administrator password. Running it again later is
how you update, repair or remove it. After an install, a repair or a reinstall
Stellody opens maximised on the screen the setup program was on.

**macOS.** Download the disk image, open it and drag Stellody to Applications.
It is signed and notarized, so it opens without argument.

**Linux.** Download the Flatpak and install it for yourself:

```
flatpak install --user stellody.flatpak
flatpak run uk.codecrafter.Stellody
```

It can read your home directory and any removable drive but can write to none
of them: Stellody never writes to a music file, so on Linux it is not given the
means to. Beyond that it asks for sound, the screen and the network, the last
for the things listed under Your privacy.

---

# For developers

Everything above is the product. What follows is the code.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for M4A, WMA, WavPack and AAC |
| Output | sounddevice over PortAudio: WASAPI on Windows, CoreAudio on macOS, the system mixer on Linux; Qt Multimedia notices the output device changing |
| Buffers | numpy |
| Store | SQLite |

`ARCHITECTURE.md` states the invariants first, each linked to the test that
enforces it. `PLAN.md` holds the open work plus what is deliberately excluded.
`TECH_DEBT.md` says what is still open internally, what is deliberately left
and what only looks like debt. `DISCOVERY.md` and `SHOPS.md` are the two
specifications discovery was built from; `FORMATS.md` specifies the three
formats proved by a generated fixture. Each requirement names the test that
proves it.

## Running from source

```
python -m pip install -r requirements-dev.txt
python main.py
```

**The runtime is pinned; the tools are not.** `requirements.txt` names exact
versions, because a build of one commit has to be the same build whenever it is
made. `requirements-dev.txt` reads it before adding the tools, black, flake8,
ruff, pytest and Nuitka among them, which keep their floors, since a linter
moving forward changes the checks rather than what is shipped. Upgrading a
pinned package therefore fails the suite until the pin is moved to match, naming
the package and both versions; that is the guard working rather than a fault.

## Tests

```
.\gate.ps1
```

That runs the formatter, both linters and the suite against the project's own
virtual environment, reading each exit code rather than its output. Running
`python -m pytest` directly works too, provided it is the venv's Python;
otherwise a test fails the run, since the checks passing in one environment
while the application runs in another is a fault this project has actually had.

The suite gates at 100% branch coverage over the domain and application
layers; below that the run fails. It also runs black, flake8 and ruff as
assertions, so a formatting or linting regression is a test failure.

## Building

Each platform builds on itself; none of the three cross-compiles.

**Windows:**

```
python buildexe.py
python buildinstaller.py
```

The first compiles the application with Nuitka into a single file, using every
core the machine has. The second zips that file as a payload and compiles the
setup program around it, producing `dist-installer/StellodySetup.exe`.

Everything the setup program writes is per user, so Windows never asks for
administrator rights. Pass `--standalone` to the first script for a directory
bundle instead, which is quicker to inspect when a build misbehaves.

**macOS:**

```
python builddmg.py
```

Compiles with Nuitka as the Windows build does, strips the object files PySide6
ships inside its QML plugins, signs with a Developer ID, then notarizes both
the application and the image before stapling each. Notarization is not
optional: Gatekeeper rejects a signed but unnotarized application, so the
credential comes from a keychain profile stored once with
`xcrun notarytool store-credentials Stellody`. `ALLOW_UNNOTARIZED=1` builds
without it, for local testing only.

**Linux:**

```
./build_flatpak.sh
./clean_flatpak.sh
```

The wheels and the source archives are fetched to the host first, so the build
itself reaches the network for nothing. PortAudio is compiled from source into
the bundle, because the sounddevice wheel carries a library for Windows and
macOS only while the freedesktop runtime ships none. So is the Kerberos client
library, which Qt's network module links while the runtime carries none. The
cleaner uninstalls Stellody then removes what the build wrote and nothing else;
pass `--purge-data` to remove your ratings, play counts, stated tags and
accepted corrections as well.

## The website

`docs/` is the site, served by GitHub Pages at
[stellody.co.uk](https://stellody.co.uk/), which is the canonical host. Version
tokens in it are stamped from `VERSION` by `stamp_version.py`, which the Windows
and macOS build scripts call, so the site is never hand-versioned. The Flatpak
build does not stamp the site; run the script directly after a bump made
without building on either of the other two.

The same pages are also served at `stellody.com`, out of the
[stellody-website](https://github.com/oernster/stellody-website) repository
under `public/`. **That mirror keeps itself up to date and needs nothing from
you.** Pushing a change to `docs/` runs `.github/workflows/mirror-site.yml`,
which carries it across, pushes it then asks Render to deploy it. Commit here
and both hosts follow.

**The deploy is asked for rather than inferred, deliberately.** Render's own
Auto-Deploy is set to On Commit, yet it stopped hearing pushes with nothing
anywhere saying so; deploys went out only when somebody pressed for one. The
workflow already knows a deploy is wanted, so it says so outright, through a
deploy hook held as `RENDER_DEPLOY_HOOK`. Without that secret the mirror still
updates while stellody.com waits; the run then logs a warning saying exactly
that.

One trap is worth knowing before investigating either host. A browser holding
the previous page is indistinguishable from a deploy that never ran, so hard
refresh first.

`sync_site.py` is what the workflow runs. It works locally too:

```
python sync_site.py           # carry docs/ across to ../stellody-website/public
python sync_site.py --check   # report drift, write nothing, exit 1 if any
```

Two files are deliberately NOT mirrored. `docs/CNAME` names the Pages custom
domain and means nothing on Render; `docs/sitemap.xml` stays because this host
owns the sitemap. `robots.txt` differs on the mirror on purpose, so it is
neither copied over nor deleted there. The mirrored pages keep their
`canonical`, `og:url` and `og:image` pointing here, which is what stops the two
hosts competing for the same pages.

The workflow reads two secrets. `MIRROR_TOKEN` is a fine-grained personal access
token scoped to `oernster/stellody-website` alone, with Contents set to read
and write; without it the run stops at once. `RENDER_DEPLOY_HOOK` is the deploy
hook described above.

## Supporting the project

Stellody is free and stays free. There is no paid tier, no licence key and no
feature held back behind a donation. If it has replaced something you were
paying for, a donation supports its maintenance and continued development.

<a href="https://www.paypal.com/ncp/payment/QGC2XK2Z5WNUW"><img src="docs/donate.png" alt="Donate to Stellody" width="120"></a>

## Licence

Dual licensed. The model, meaning the domain, application, infrastructure and
shared layers together with `main.py`, the build scripts and the tests, is
under GPL-3.0. The user interface layer is under LGPL-3.0, to align with Qt.
The Windows setup program under `installer/` is under LGPL-3.0 alone; its
Licence button says so, then says that Stellody itself is dual licensed. See
`LICENSE` for the mapping.

A packaged build bundles FFmpeg through PyAV, to decode M4A, WMA, WavPack and
AAC. The FFmpeg libraries themselves are built LGPL-3.0-or-later, verified from
the licence string the build reports rather than from its documentation. That
build also links libx264 and libx265, which are GPL-2.0-or-later, so the
packaged application as a whole is distributed as a GPL-3.0 work. Nothing here
encodes video; those two arrive as dependencies of the shared FFmpeg build.

A commercial licence for my own code is also available, separately from the
open-source licences: see
[commercial licensing](https://ernster.dev/commercial-licensing.html).
