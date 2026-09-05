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

There is no open technical debt.

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
and not gated, currently 94% over everything. That is a decision recorded in
`ARCHITECTURE.md`, not an omission: a gate over code needing a real device, a
real library and the Windows shell would either be a number nobody can hold or a
suite full of mocks standing in for the very things worth testing.

**The build and packaging scripts are long and are exempt from the line cap.**
`buildexe.py`, `buildinstaller.py`, `stamp_version.py`, `stamp_sitemap.py` and
`sync_site.py` are linear recipes read top to bottom. Splitting a sequence of
flags across modules costs more than it buys, so the structural line-cap test
does not scope them.

**Quitting during a cover lookup leaves the process without unwinding.** A
search inside a network read is given up within a slice of a second now, so
`leave_at_once` in `composition.py` should never be reached. It stays because
what no amount of asking covers is a socket that never comes back. Qt ends the
process over a thread destroyed while running: an abort with a crash report
rather than the exit code the quit meant. Everything durable is already put away
by the time it is reached, the store closed and the claim released.

**`installer/` reads `stellody.shared` and `stellody.ui`.** That is the setup
program being a client of the application rather than a layer of it; nothing
under `stellody/` imports back, which the layering test enforces. One identity,
one theme and one licence viewer is the point of it.
