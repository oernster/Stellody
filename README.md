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

Someone spent years turning a shelf of CDs into files. Then a well known music
player reached into those files and rewrote the information stored inside them,
damaging 33 albums. Every one was put right in the end; a music player should
never have touched them.

Stellody is built on one rule: your files are opened to be read and never to be
changed. Where it finds muddled labelling it tells you plainly and leaves the
file exactly as it found it. The test suite checks this on every run; if it ever
stopped being true the suite would fail. [Why it exists](https://stellody.co.uk/why.html)
tells the story in full.

## Who it is for

Somebody with a collection of music files on their own computer, ripped or
bought over the years, who wants it played well and left exactly as it is.

It is not for anybody after a streaming service or a tag editor. It does not
stream, does not copy your CDs, does not sync to a phone and will not
reorganise your files by rewriting them. It will point your browser at a shop
selling what you are missing; it sells nothing itself, holds no account with
any shop and takes nothing from a sale.

## What you get

Each line is a summary; the site has the detail.

**Library** ([library page](https://stellody.co.uk/library.html))

- A wall of album covers or a plain list; the playing track is marked in both
  and named along the foot of the window.
- Search that narrows as you type, keeping each album whole around the match.
- Messy collections sorted out: an album saved as one long file, a box set over
  several folders or an unnumbered bonus disc comes out as one album.
- A genre filter over the covers, including albums that state no genre.
- State what an album or a single song really is (artist, title, date, genre,
  disc and track number); genres come from a settled list of headings with
  their styles under them. Stored by Stellody, never written to the file.
- Corrections you can keep (all at once or one album at a time) then undo later.
- Album art from what your files carry; for an album with none, ask Stellody to
  search and pick from what it finds. It never guesses.
- Stars and play counts per song, plus a rating for the album. Only a song that
  plays to its end counts as played.
- A rescan that names the new albums, counts the new tracks and gives the
  library's totals.
- Bonus videos that came with an album play inside it.

**Playback and sound** ([playback page](https://stellody.co.uk/playback.html))

- Gapless albums: no silence where the artist never put one.
- An equalizer with a spectrum display. A curve that lifts any band is lowered
  by its largest lift to keep a boost from clipping on ordinary material (not a
  guarantee against every waveform); switched off it hands each block back
  untouched.
- Exclusive output for bit perfect playback on Windows and macOS, with the
  rate, depth and mode the device actually took shown beside the playing time.
  Bit perfect also needs full volume, mute off and the equalizer off or flat;
  the claim drops the moment one of those moves. It is offered only where the
  device can take the song untouched, so not for a lossy song or an unsupported
  rate. Windows hands the device over outright; macOS runs it at the song's
  rate while still mixing other applications in; Linux does not offer it.
- Choose the output device; the choice is remembered and the list follows
  devices as they come and go. A device that disconnects pauses the music
  rather than sending it out of the speakers.
- A larger output buffer than the device would choose, so a busy machine does
  not break the sound up; any dropout is noted in the diary (see Your privacy).
- The waveform of each song along the bottom; click to jump there.

**Discovery** ([discovery page](https://stellody.co.uk/discovery.html))

- Tick genres and Stellody asks two public music catalogues what those artists
  made that you do not hold, plus who sounds like them.
- Optional year range, artists on compilations, missing volumes of series you
  collect and DJ mixes.
- Progress bars per stage, an estimate of time left and a stop that takes
  effect at once. Answers are kept as they arrive, so a second run asks only
  for the rest; gaps are counted and named rather than hidden.
- Find in shops opens each ticked album as a search on a shop you choose, in
  your browser. The shop list is yours to edit. Nothing is bought or streamed.

**Everywhere**

- Help then Guide names every button beside the picture the window draws, plus
  the rules Stellody reads a library by.
- Every button on both trays bar the donation button is on the menu bar too.

The [features page](https://stellody.co.uk/features.html) has the overview;
[the technical page](https://stellody.co.uk/technical.html) says how its claims
are kept true.

## Before you download

- **Formats.** FLAC, MP3, Ogg, Opus, WAV, AIFF, M4A (AAC or ALAC, told apart),
  WMA, WavPack and AAC, plus bonus videos under a `.m4v` name. Not Monkey's
  Audio, Musepack, DSD, TAK, TrueAudio, CAF or M4B audiobooks: such a file is
  named in the health report rather than passed over, as is one whose details
  cannot be read.
- **WMA, WavPack and AAC are proved against files the test suite encodes**,
  since no real ones were to hand. That exercises the whole path; it cannot say
  what an old ripper actually wrote. A file of yours read wrongly is a defect
  worth reporting.
- **Windows, macOS and Linux.** A setup program, a disk image and a Flatpak.
  By default the sound goes through the system mixer, which is not bit perfect;
  exclusive output takes it out of the way on Windows and macOS.
- **Sized to fit a laptop screen.** The window is drawn smaller than it is
  built so it fits a 13 inch 4K screen at 300% scaling. Set `QT_SCALE_FACTOR`
  before starting Stellody to choose your own size.
- **It reads; it never repairs.** Tidied labelling lives in its own view; the
  files are never rewritten. A control that cannot act just now is shown
  switched off.

## Your privacy

Stellody does not know who you are. No account, no profile and no record kept
anywhere of what you listen to. Your music plays with the internet switched
off. Five things reach outside your computer; nothing else does.

- **Looking for album art**, only when you ask, one album at a time.
  MusicBrainz is sent that album's artist and title; the Cover Art Archive is
  then asked for pictures by the release identifier MusicBrainz returned.
- **Checking for a new version**, shortly after start and once a day while it
  runs. It sends nothing about you or your music, not even which version you
  have: the request names the program and asks for one public page. Download
  hands your browser the file for your platform, else the release page.
- **Looking for music you do not own**, only when you ask. A discovery run
  sends MusicBrainz the names of the artists inside the genres you ticked, plus
  the identifiers it returned; ListenBrainz is sent artist identifiers alone.
  Requests carry their own fixed settings and a user agent naming Stellody, its
  version and the project's contact address. Titles you hold go out in two
  cases only:
  - up to three of them beside a name MusicBrainz knows as several artists, to
    tell which is meant;
  - with Other volumes of series ticked, the title of each compilation inside
    the ticked genres, of each album filed under a name MusicBrainz knows as
    one artist with no album or EP, plus MusicBrainz's own title for an album
    you hold that it lists as a compilation or a DJ mix. Each is cut at its
    first bracket, spaced slash or spaced dash, then sent again without its
    volume number.

  Not your library as a whole, not a count of it, not your chosen years and
  nothing about you or your machine. Tick nothing and nothing leaves.
- **Reaching a shop** hands your browser one search address per ticked album.
  Stellody connects to no shop, holds no account with one and takes nothing
  from any sale.
- **The donation button** hands your browser an address. It is one button on
  the bottom strip, the only place money is mentioned; nothing prompts or
  reminds you and nothing changes if you never press it.

Nothing is encrypted at rest: the store holds notes about your library, not
secrets. Stellody keeps a plain-text diary, `stellody-diary.log`, beside its
library database in its data directory (`%LOCALAPPDATA%\Stellody` on Windows,
`~/Library/Application Support/Stellody` on macOS, `~/.local/share/stellody` on
Linux or `~/.var/app/uk.codecrafter.Stellody/data/stellody` under Flatpak). It
records no audio and nothing about you; it notes each address a discovery run
asks, which carries the artist names and any titles sent, plus playback
dropouts. `stellody-startup.log` holds the reason when Stellody could not
start. Neither is ever sent anywhere; either can be deleted whenever you like.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for M4A, WMA, WavPack and AAC |
| Output | sounddevice over PortAudio: WASAPI on Windows, CoreAudio on macOS, the system mixer on Linux |
| Store | SQLite |
| Packaging | Nuitka on Windows and macOS, Flatpak on Linux |

## Installing

**Windows.** Download the setup program and run it. It installs just for you,
so no administrator password is needed; running it again updates, repairs or
removes it.

**macOS.** Download the disk image, open it and drag Stellody to Applications.
It is signed and notarized.

**Linux.** Download the Flatpak and install it for yourself:

```
flatpak install --user stellody.flatpak
flatpak run uk.codecrafter.Stellody
```

It can read your home directory and removable drives but write to none of them.
Beyond that it asks for sound, the screen and the network, the last for the
things listed under Your privacy.

## Running from source

Create a virtual environment named `venv` at the repository root and activate
it before installing; that is the interpreter the gate runs with.

```
python -m venv venv
python -m pip install -r requirements-dev.txt
python main.py
```

## Tests

```
.\gate.ps1
```

Runs black, flake8, ruff and the test suite with `venv\Scripts\python.exe`,
stopping at the first that fails. The suite gates at 100% branch coverage over
the domain and application layers.

## Building

Each platform builds on itself: `python buildexe.py` then
`python buildinstaller.py` on Windows, `python builddmg.py` on macOS and
`./build_flatpak.sh` on Linux.

## For developers

- [`DEVELOPMENT.md`](DEVELOPMENT.md): running, testing and building on each
  platform in full; publishing the website.
- [`TESTING.md`](TESTING.md): how the tests are run and written.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): the invariants, each linked to the test
  that enforces it.
- [`PLAN.md`](PLAN.md): open work and what is deliberately excluded.
- [`TECH_DEBT.md`](TECH_DEBT.md): internal debt, open and deliberately left.
- [`DECISIONS-TRADEOFFS.md`](DECISIONS-TRADEOFFS.md): the decisions the product
  rests on, with their gains and costs.
- [`DISCOVERY.md`](DISCOVERY.md), [`SHOPS.md`](SHOPS.md),
  [`FORMATS.md`](FORMATS.md) and [`OUTPUTS.md`](OUTPUTS.md): specifications
  whose requirements each name the test that proves them.

## Supporting Stellody

Stellody is free and stays free. There is no paid tier, no licence key and no
feature held back behind a donation. If it has replaced something you were
paying for, a donation supports its maintenance and continued development.

<a href="https://www.paypal.com/ncp/payment/A7PWRKSKXHBGC"><img src="docs/donate.png" alt="Donate to Stellody" width="120"></a>

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
