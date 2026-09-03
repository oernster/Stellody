# Technical debt

What is still open, what is deliberately left and what only looks like debt.

Every item here is a behaviour-preserving internal concern: nothing in this file
reverts a feature or changes what a listener sees. Anything that would is a plan
item rather than a debt item, so it lives in `PLAN.md`. Read alongside
`ARCHITECTURE.md`, which states the invariants; also the structural tests, which
enforce them.

Open items are numbered. A numbered heading IS the definition of an open item,
which is why the two sections at the foot carry no numbers. A resolved item is
deleted outright rather than marked done: technical-debt history is not
technical debt. What a resolution was worth is recorded in the release notes.

## 1. The dependency floors do not pin a packaged build

`requirements.txt` names floors throughout: `PySide6>=6.7`, `av>=15.0`,
`numpy>=1.26` and so on. Two people building the installer a month apart can
therefore ship different binaries from the same commit; a release cannot be
rebuilt as it was.

The cost is not hypothetical here. The application is compiled by Nuitka with
`--include-module=av.utils`, a flag that exists because of how one version of
PyAV reaches one submodule; a PySide6 or PyAV release that changes its import
shape would be picked up silently by the next build rather than by a change
anybody made. The gate would stay green throughout, since the suite runs against
whatever the venv happens to hold.

What it is blocked on is an owner decision rather than effort, because the two
answers are both defensible and they are not the same answer:

- **Pin the runtime and keep the floors for development.** A second file, else
  `==` in `requirements.txt` with `requirements-dev.txt` left loose, so a build
  is reproducible while a working copy still picks up fixes.
- **Leave it.** Floors are what the rest of the portfolio uses; a desktop
  application with no server to match is the case where drift costs least.

A structural test already refuses to run anywhere but the project's own venv,
so whichever is chosen, the environment cannot quietly become someone else's.

## Looks like debt, not worth touching

**`_drive` catches `OSError`, `RuntimeError` and `ValueError` rather than
`PlaybackError` alone.** Now that the domain names a playback error and the
transport raises it, narrowing the catch looks like the tidy move. It is the
wrong one: the catch exists because an exception raised inside a Qt slot ends
the slot in silence, leaving the buttons wearing faces that are no longer true
and nothing said to anybody. A narrow catch would let exactly the failures
nobody predicted through that hole, which is the failure mode the catch was
written for. The breadth is the point.

**The suffix tables are two lists that could be one.** `AUDIO_SUFFIXES` and
`UNPLAYABLE_SUFFIXES` in the walker could be a single mapping. They are
deliberately apart: what can be decoded and what is known-but-unplayable are
different facts; inferring the second from "not in the first" is exactly what
made a stray text file read as a missing album once already.

## Not debt (do not "fix" these)

**Infrastructure and the interface sit outside the coverage gate.** The gate is
100% branch over `stellody.domain` and `stellody.application`, the layers
reachable with no filesystem, no clock and no audio device. The rest is measured
and not gated, currently 92% over everything. That is a decision recorded in
`ARCHITECTURE.md`, not an omission: a gate over code needing a real device, a
real library and the Windows shell would either be a number nobody can hold or a
suite full of mocks standing in for the very things worth testing.

**The build and packaging scripts are long and are exempt from the line cap.**
`buildexe.py`, `buildinstaller.py`, `stamp_version.py` and `sync_site.py` are
linear recipes read top to bottom. Splitting a sequence of flags across modules
costs more than it buys, so the structural line-cap test does not scope them.

**`installer/` reads `stellody.shared` and `stellody.ui`.** That is the setup
program being a client of the application rather than a layer of it; nothing
under `stellody/` imports back, which the layering test enforces. One identity,
one theme and one licence viewer is the point of it.
