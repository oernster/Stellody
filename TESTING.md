# Testing

How Stellody is tested: running the checks, reading what they say, the rules a
run by hand has to follow and how a new test or guard is written. The rules
themselves are in `ARCHITECTURE.md`, each invariant linked to the test that
enforces it; `DISCOVERY.md`, `SHOPS.md`, `FORMATS.md` and `OUTPUTS.md` name the
test behind every requirement. This file is how to work with those tests, not a second copy
of what they assert.

## Running the checks

```
.\gate.ps1
```

`gate.ps1` is the whole gate, in order: `black --check`, `flake8`,
`ruff check`, then `pytest tests`. It runs every step with the project's own
interpreter (`venv\Scripts\python.exe`) and stops at the first that fails. It
sets `QT_QPA_PLATFORM=offscreen` for the run, so no window appears.

**A full run takes about ten minutes.** Timed on 2026-09-24 and counted again
on 2026-09-25: the 2,114 tests outside `tests/ui` take about 80 seconds; the
1,477 interface tests take the rest, many of them spending most of a second building their window. A run
that is quiet for several minutes is not stuck. To see it moving, add `-v` to
a pytest run by hand, which names each test as it starts.

**Read the exit code, never the last line.** The suite is coverage gated, so it
prints the coverage table last and no summary line of passed and failed; a
coverage row named after a module such as `errors.py` also reads like a result
to anybody searching the text. `gate.ps1` reads `$LASTEXITCODE` after every
step and throws on anything but nought. Running a step by hand, do the same.
For a count of tests, `python -m pytest --no-cov -q` ends with one.

## What the gate holds

- **Coverage.** 100% branch coverage over `stellody.domain` and
  `stellody.application`, set in `pyproject.toml`; below that the run fails.
  Those are the layers that reach no disk, no network and no device, so
  anything short there is a decision nobody made. Infrastructure and the
  interface are tested too, against real files, a real loopback server and a
  real `QApplication`; they sit outside the floor rather than dragging it down
  to a number that means nothing.
- **Style.** `tests/structural/test_style.py` runs black, flake8 and ruff as
  assertions, so a formatting or linting regression fails the suite even
  without the gate around it.
- **Structure.** The structural suite below.

## Running it by hand

- **Use the project's Python.** `python -m pytest` works provided it is
  `venv\Scripts\python.exe`. `tests/structural/test_environment.py` fails the
  run anywhere else, since checks passing in one environment while the
  application runs in another is a fault this project has actually had.
- **The offscreen platform is set for you.** `tests/conftest.py` sets
  `QT_QPA_PLATFORM=offscreen` before any `QApplication` exists, however the
  suite was started. The interface tests build real windows; before this was
  in the conftest, a bare `pytest` put each of them on the desktop in turn,
  every one answering a close with its own quit prompt.
- **One run at a time.** Two runs of the suite at once fail falsely: at least
  `tests/infrastructure/test_instance.py` and `tests/ui/test_arrow_ring.py`
  collide. A failure met while another run was going is not evidence of
  anything; run it again alone.
- **The application is never started.** `tests/conftest.py` refuses any test
  that tries to start `stellody.exe`, whatever it believes it patched, since a
  stand-in that stopped matching once started the installed copy on every run.
  It also sends the diary to the test's own temporary folder, so a run never
  writes into the account of real runs.

## Where the tests live

`tests/` mirrors the package, one directory a layer:

| Directory | What it tests | Against |
|---|---|---|
| `domain/` | the rules, pure | values built in the test |
| `application/` | the use cases | hand-written fakes of every port |
| `infrastructure/` | files, audio, the network client, the store | real files in a temporary folder, a real loopback server |
| `ui/` | the windows, dialogs and trays | a real `QApplication` on the offscreen platform |
| `installer/` | the setup program | a real `QApplication`, with the registry, the filesystem and the processes stood in for |
| `structural/` | the rules no single test can see | the source tree itself |

## Writing a test

- **No mocking library; Qt is never mocked.** A port is stood in for by a
  hand-written fake: `tests/application/fakes.py` holds the shared ones and
  `tests/recording_player.py` is the playback port every suite drives, one
  that records what it was asked rather than playing it. A fake is a small
  class you can read; a mock is a script of expectations nobody reads twice.
- **The window.** `tests/ui/tray_support.py` builds the real main window over a
  `RememberingStore` and a `RecordingPlayer` with `build(store, player)`.
  Many interface suites have a `*_support.py` beside them building the window,
  album or dialog they are driven against; start from the nearest one rather
  than writing another.
- **One `QApplication`, no window outliving its test.** `tests/conftest.py`
  provides the session's `application` fixture to every suite, so no suite
  builds its own; `tests/ui/conftest.py` destroys every top level widget
  between the interface tests. A window left to the garbage collector was destroyed
  inside the next test, measured as an access violation five runs in six.
- **The network.** `tests/infrastructure/fetching_support.py` runs a real HTTP
  service on the loopback address and records every ask and every header, so a
  test reads what actually arrived rather than what the code meant to send.
- **Audio.** No audio file of a widened format is committed
  (`tests/structural/test_no_committed_audio.py`). `m4a_support.py`,
  `video_support.py` and `widened_support.py` in `tests/infrastructure/` encode
  real files for the test and throw them away with its temporary folder.
- **Anything the scale changes.** Qt reads its scale once, as the application
  is built, while the suite runs at one. A defect that shows only at the nine
  tenths every window is drawn at needs a process started at that scale:
  `tests/ui/test_every_rule_is_drawn.py` runs `tests/ui/rule_sweep.py` that
  way and reads what it prints.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds
for code nobody has written yet. The suite in `tests/structural/`:

| Guard | Holds |
|---|---|
| `test_readonly.py` | Stellody never writes to a music library |
| `test_offline.py` | only the permitted modules can open a connection |
| `test_layers.py` | layer boundaries and domain purity |
| `test_loc.py` | the 400 line limit and the danger band below it |
| `test_environment.py` | the suite runs where the application runs |
| `test_style.py` | black, flake8 and ruff, as assertions |
| `test_no_dashes.py` | no dash-like character in a screen, document or comment |
| `test_one_name.py` | the product name has one home |
| `test_half_has_one_home.py` | halving has one home |
| `test_user_agent.py` | the agent names Stellody, its version and a contact |
| `test_discovery_paths.py` | discovery keeps what it keeps in Stellody's own data directory |
| `test_focus_ring_selectors.py` | no stylesheet rings a pane or a region |
| `test_rings.py` | no checkbox ships without a ring |
| `test_no_committed_audio.py` | no audio file of a widened format in the tree |

**A guard is not trusted until it has been seen to fail.** Every new guard is proved by planting the violation it
exists to catch and reading the failure, then restoring the tree in a
`finally` block so an interrupted proof cannot leave the plant behind. A test
written for a defect is run before the fix, where it has to fail for the
reason named, not merely fail. The proof is recorded where the rule is
described, usually as "proved by planting" in `ARCHITECTURE.md`.
