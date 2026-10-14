# Testing

How to run Stellody's checks and read what they say. What the tests assert
lives beside the rules they hold: `ARCHITECTURE.md` links each invariant to its
test; `DISCOVERY.md`, `SHOPS.md`, `FORMATS.md`, `OUTPUTS.md` and `BACKUP.md`
name the test behind each requirement.

## The gate

```powershell
.\gate.ps1
```

In order: `black --check .`, `flake8`, `ruff check .`, then `pytest tests`.
Every step runs with `venv\Scripts\python.exe` under
`QT_QPA_PLATFORM=offscreen`, so no window appears; the first failure stops the
run.

A full run takes about ten minutes. A run quiet for several minutes is not
stuck; add `-v` to a pytest run by hand to watch it move.

## Reading a result

**Read the exit code, never the last line.** The coverage gate fails the run
on its own while the summary line says nothing about it. `gate.ps1` checks
`$LASTEXITCODE` after every step and throws on anything but zero; by hand, do
the same.

## Coverage

100% branch coverage over `stellody.domain` and `stellody.application`, set in
`pyproject.toml` (`--cov-fail-under=100`). Those are the layers reachable with
no filesystem, no clock and no audio device, so every branch can be held
cheaply. Infrastructure and the interface are tested against real files, a real
loopback server and a real `QApplication` but are not gated: a floor over code
needing a real device would be a number nobody can hold or a suite of mocks.

## What each suite proves

| Directory | Proves | Against |
|---|---|---|
| `domain/` | the rules, pure | values built in the test |
| `application/` | the use cases | hand-written fakes of every port |
| `infrastructure/` | files, audio, the network client, the store | real files in a temporary folder, a real loopback server |
| `ui/` | the windows, dialogs and trays | a real `QApplication` on the offscreen platform |
| `installer/` | the setup program | a real `QApplication`, with the registry, filesystem and processes stood in for |
| `structural/` | rules no single test can see, each listed with its invariant in `ARCHITECTURE.md` | the source tree itself |

## Running part

```powershell
venv\Scripts\python.exe -m pytest tests\domain --no-cov
venv\Scripts\python.exe -m pytest tests\ui\test_reading_panes.py -v --no-cov
venv\Scripts\python.exe -m pytest --co -q --no-cov
```

`--no-cov` is needed for a partial run, which cannot reach the coverage floor;
the last line counts the tests without running them.

- **Use the project's Python.** `tests/structural/test_environment.py` fails
  the run under any other interpreter.
- **One run at a time.** `tests/infrastructure/test_instance.py` takes a
  machine-wide claim, so a second concurrent run fails falsely.
- `tests/conftest.py` sets the offscreen platform, refuses any test that tries
  to start `stellody.exe` and sends the diary to the test's own temporary
  folder.

## Writing a test

- **No mocking library; Qt is never mocked.** A port is stood in for by a
  hand-written fake: `tests/application/fakes.py` holds the shared ones and
  `tests/recording_player.py` records what playback was asked to do.
- **The window.** `tests/ui/tray_support.py` builds the real main window with
  `build(store, player)`. Start from the nearest `*_support.py` rather than
  writing another.
- **One `QApplication`.** `tests/conftest.py` provides the session's
  `application` fixture; `tests/ui/conftest.py` destroys every top level widget
  between interface tests, since a window left to the garbage collector crashes
  a later test.
- **The network.** `tests/infrastructure/fetching_support.py` runs a real HTTP
  service on the loopback address and records every request and header.
- **Audio.** No audio file of a widened format is committed;
  `m4a_support.py`, `video_support.py` and `widened_support.py` in
  `tests/infrastructure/` encode real files into the test's temporary folder.
- **The interface scale.** The suite runs at scale one; a defect that shows
  only at `INTERFACE_SCALE` needs a process started at it, as
  `tests/ui/test_every_rule_is_drawn.py` does with `tests/ui/rule_sweep.py`.
- **A guard is not trusted until seen to fail.** Plant the violation, read the
  failure, then restore the tree in a `finally` block. Where the plant needs no
  change to the tree, keep it as a test beside the guard, as
  `test_the_guard_bites` in `test_no_dashes.py` does. A test for a defect is
  run before the fix and must fail for the reason named.
