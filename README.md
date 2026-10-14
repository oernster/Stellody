# <img width="128" height="128" alt="application-icon" src="https://github.com/user-attachments/assets/856669d1-6207-4f38-8ed6-816c6b05a40f" /> Stellody

**A free music player for the collection already on your computer.**

No account, no subscription, no adverts and nothing about you sent anywhere.
Point it at your music folder and it does the rest. It never changes a single
one of your files.

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

A well known music player once rewrote the information stored inside a
collection's files and damaged 33 albums. Stellody is built on one rule: your
files are opened to be read and never to be changed. Muddled labelling is
reported plainly and the file left as it was; the test suite fails if that ever
stops being true. [Why it exists](https://stellody.co.uk/why.html) tells the
story.

## Who it is for

Somebody with music files on their own computer, ripped or bought over the
years, who wants them played well and left exactly as they are.

Not for anybody after a streaming service or a tag editor: it does not stream,
copy CDs, sync to a phone or rewrite your files. It can point your browser at a
shop selling what you are missing; it sells nothing itself.

## What you get

- **Library** ([page](https://stellody.co.uk/library.html)): a wall of covers
  or a plain list; search as you type; albums split across files, folders or
  bonus discs gathered into one; a genre and year filter; your own statement of
  what an album or song is, kept by Stellody and never written to the file;
  corrections you can keep then undo; album art from your files or a search
  you choose from; stars, play counts and album ratings; bonus videos played
  inside their album.
- **Backup** ([BACKUP.md](BACKUP.md)): everything Stellody knows about your
  library in one zip, restorable here or on another computer.
- **Playback** ([page](https://stellody.co.uk/playback.html)): gapless albums;
  an equalizer that lowers a lifted curve to avoid clipping; bit perfect
  exclusive output on Windows and macOS; a chosen output device that is
  remembered ([OUTPUTS.md](OUTPUTS.md)); a visualiser in ten styles; the
  waveform of each song to click along.
- **Discovery** ([page](https://stellody.co.uk/discovery.html),
  [DISCOVERY.md](DISCOVERY.md)): tick genres and Stellody asks two public music
  catalogues what those artists made that you do not hold, plus who sounds like
  them; saved taste profiles; answers kept so a second run asks only for the
  rest.
- **Shops** ([SHOPS.md](SHOPS.md)): each ticked album opened as a search on a
  shop you choose, in your browser, from a list you can edit.
- **Formats** ([FORMATS.md](FORMATS.md)): FLAC, MP3, Ogg, Opus, WAV, AIFF, M4A
  (AAC or ALAC), WMA, WavPack and AAC, plus bonus videos as `.m4v`. Monkey's
  Audio, Musepack, DSD, TAK, TrueAudio, CAF and M4B audiobooks are named in the
  health report rather than played.
- **Help**: a guide naming every button beside the picture the window draws.

The window is drawn at nine tenths of its built size so it fits a 13 inch 4K
screen at 300% scaling; set `QT_SCALE_FACTOR` before starting to choose your
own size.

## Your privacy

Your music plays with the internet switched off. Five things reach outside your
computer, each only as described:

- **Album art**, when you ask: MusicBrainz is sent that album's artist and
  title; the Cover Art Archive is sent the release identifier it returned.
- **The update check**, shortly after start then daily: a fixed request naming
  the program alone.
- **Discovery**, when you ask: artist names from the ticked genres, plus a few
  titles in the cases [DISCOVERY.md](DISCOVERY.md) sets out. Never your library
  as a whole.
- **Shops** and **the donation button** hand your browser an address; Stellody
  itself connects to neither.

Stellody keeps `stellody-diary.log` (discovery requests and playback dropouts)
and `stellody-startup.log` (why it could not start) beside its database in its
data directory: `%LOCALAPPDATA%\Stellody` on Windows,
`~/Library/Application Support/Stellody` on macOS, `~/.local/share/stellody` on
Linux or `~/.var/app/uk.codecrafter.Stellody/data/stellody` under Flatpak.
Neither is ever sent anywhere. Nothing is encrypted at rest: the store holds
notes about your library, not secrets.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.13 |
| Interface | PySide6 |
| Tags | mutagen |
| Decode | soundfile, plus PyAV for M4A, WMA, WavPack, AAC and bonus videos |
| Output | sounddevice over PortAudio |
| Store | SQLite |
| Packaging | Nuitka on Windows and macOS, Flatpak on Linux |

## Installing

**Windows.** Run the setup program. It installs for you alone, so no
administrator password is needed; running it again updates, repairs or
removes it.

**macOS.** Open the disk image and drag Stellody to Applications. It is signed
and notarized.

**Linux.**

```
flatpak install --user stellody.flatpak
flatpak run uk.codecrafter.Stellody
```

It can read your home directory and removable drives but write to none of them.

## Running from source

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python main.py
```

## Tests

```powershell
.\gate.ps1
```

Runs black, flake8, ruff then the suite with `venv\Scripts\python.exe`,
stopping at the first failure. The suite gates at 100% branch coverage over the
domain and application layers. See [TESTING.md](TESTING.md).

## Building

Each platform builds on itself: `python buildexe.py` then
`python buildinstaller.py` on Windows, `python builddmg.py` on macOS and
`./build_flatpak.sh` on Linux. See [DEVELOPMENT.md](DEVELOPMENT.md).

## For developers

- [ARCHITECTURE.md](ARCHITECTURE.md): the invariants, each linked to the test
  that enforces it.
- [TESTING.md](TESTING.md) and [DEVELOPMENT.md](DEVELOPMENT.md): testing,
  building and releasing.
- [DECISIONS-TRADEOFFS.md](DECISIONS-TRADEOFFS.md): the decisions the product
  rests on.
- [PLAN.md](PLAN.md) and [TECH_DEBT.md](TECH_DEBT.md): open work and internal
  debt.

## Supporting the project

Stellody is free and stays free. There is no paid tier, no licence key and no
feature held back behind a donation. If it has replaced something you were
paying for, a donation supports its maintenance and continued development.

<a href="https://www.paypal.com/ncp/payment/A7PWRKSKXHBGC"><img src="docs/donate.png" alt="Donate to Stellody" width="120"></a>

## Licence

Dual licensed; see `LICENSE` for the mapping. The model (the domain,
application, infrastructure and shared layers with `main.py`, the build scripts
and the tests) is under GPL-3.0. The interface layer is under LGPL-3.0, to
align with Qt. The Windows setup program under `installer/` is under LGPL-3.0
alone.

A packaged build bundles FFmpeg through PyAV. The FFmpeg libraries report
their licence as LGPL-3.0-or-later; that build also links libx264 and libx265
(GPL-2.0-or-later), so the packaged application as a whole is distributed as a
GPL-3.0 work. Nothing here encodes video.

A commercial licence for my own code is also available, separately from the
open-source licences: see
[commercial licensing](https://ernster.dev/commercial-licensing.html).
