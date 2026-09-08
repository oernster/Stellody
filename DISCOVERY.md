# Discovering music the library does not hold

The specification for the first stage of discovering music the library does
not hold. It is written
before any code, because the milestone was explicitly undesigned and a feature
generated from a loose description is a feature debugged rather than built.

It is built and it is finished. Where this document and the code disagree, this
document is amended rather than quietly diverged from; every requirement below
names the test that holds it, so a claim here is checkable against the suite.

The half no test could supply was a run against the live services with its
answer read by a person. Oliver ran one over Blues and Folk on 2026-09-08 and
read the gaps: both catalogues answered without a key, the similarity endpoint
returned artists and the gaps were real records rather than albums already
held.

## 1. Introduction

### 1.1 Purpose

Stellody knows what somebody owns. It knows nothing about what they might want
next. This adds one thing and no more: a run that reads the library, asks two
public catalogues what is missing around it and writes the answer down as data.

### 1.2 Scope

In scope: a toolbar button, a dialog carrying the genre catalogue, a run that
looks up the artists inside the ticked genres, a JSON file holding what it found
and a dialog showing what that file holds when a run completes.

Out of scope, stated first so it is a past decision rather than a future
argument:

- **Buying anything.** Reaching a shop is stage two of the milestone, specified
  separately in `SHOPS.md` and built on top of what this stage produces.
  Nothing here buys, prices or holds an account.
- **Reaching a shop from these results.** Written as out of scope while this
  stage stood alone; `SHOPS.md` is what reversed it, adding tick boxes to the
  results dialog and a shops screen behind them. This stage still names records
  and never fetches one.
- **Recommending by anything except what is held.** No listening history, no
  taste model, no ranking beyond what a source itself states.
- **Writing to a music file.** The invariant the whole project exists for.
- **Sending anything that identifies the listener or the machine.** See
  NFR-PRIV-001 and NFR-PRIV-002.
- **A results cache that outlives the discovery file**, beyond the candidate
  genre cache NFR-PERF-003 requires.

### 1.3 Definitions

One meaning per term, for the life of the document.

| Term | Meaning |
|---|---|
| **Catalogue genre** | A name in `stellody.domain.genres.GENRES`, main or style. |
| **Resolved genre** | An album's genre as the library shows it: the probed tag with any album edit laid over it. Never the raw `sources.genre` column. |
| **Ticked genres** | The catalogue genres selected in the discovery dialog. |
| **Source artist** | An album artist of at least one held album whose resolved genre names at least one ticked genre. |
| **Candidate album** | An album a source gives for a source artist that the library does not hold. |
| **Candidate artist** | An artist a source gives as similar to a source artist, whom the library does not hold. |
| **Release key** | The value two albums are judged the same album on, defined in section 3.5. The title alone, normalised, with edition qualifiers removed and the year deliberately absent. |
| **Discovery run** | One press of the action button, from first request to file written or cancellation. |
| **Discovery file** | The JSON written by a run. |

### 1.4 References

- `SHOPS.md`, the second half, which builds on the results this stage produces.
- `ARCHITECTURE.md`, whose layering and purity invariants govern every
  requirement here.
- MusicBrainz API and its rate limiting document.
- ListenBrainz API, including the labs similar-artists endpoint.

## 2. Overall description

### 2.1 Product perspective

An addition to an existing application, taking the third outward-reaching
module after the cover chooser and the update check. It is a client of the
application layer exactly as every other dialog is.

Two services are reached through ONE of them: neither catalogue client holds a
socket, both handing their questions to `infrastructure/fetching.py`. Invariant
12 names four permitted modules rather than three, the fourth being the local
channel a second launch speaks to the running copy over, which was found by
this work rather than added by it.

### 2.2 The one user class

A listener with a tagged library, running Stellody on their own machine. There
is no second class: no administrator, no server, no other person's library.

### 2.3 Operating environment

Windows, Linux and macOS, as the application already ships. A working outbound
HTTPS connection during a run. Everything else the application already assumes.

### 2.4 Constraints

- **C-01** The library folder is never written to, cache included.
- **C-02** No music file is ever modified.
- **C-03** Nothing leaves the machine that names the listener or the machine.
- **C-04** The domain layer stays pure: no I/O, no framework, no clock.
- **C-05** Modules stay at or below 400 lines; a file in the 381 to 399 band
  is reduced to 350 or below.
- **C-06** Domain and application hold 100% branch coverage.
- **C-07** No credential of any kind is compiled into the application, so no
  source requiring an API key may be used. This is what rules out Discogs and
  Last.fm; see the source comparison in section 3.3.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | RESOLVED 2026-09-08. A run over Blues and Folk against the live services returned artists, albums and similar artists, with no credential anywhere in the application. | Answered |
| A-02 | RESOLVED 2026-09-08, as far as one run can. The labs similar-artists endpoint answered for every source artist in that run. It is still a labs endpoint; OQ-07 settled that it gets no fallback anyway. | Answered |
| A-03 | A listener accepts that a run names their source artists to two public catalogues. | Oliver | ruled 2026-09-06, accepted with genre scoping |

## 3. Requirements

Measured facts this rests on, taken from the library on 2026-09-06: 659 album
folders, 327 album artists, of which 326 are reachable by at least one catalogue
genre. Three folders carry no catalogue genre. The smallest genres hold one
artist; the largest, Rock, holds 107.

### 3.1 Functional requirements

---

**FR-D01 Reaching the feature**

Priority: Must

Requirement: The main window shall place a discovery button in the toolbar to
the left of the volume control, with the separator that divides the library
controls from the sound controls to its right.

Rationale: Discovery is a library action rather than a sound control, so it
belongs on the library side of that line. Amended on 2026-09-07, when both
trays were ruled into groups by what each control acts on: as first written
this asked for a position to the left of the theme button, which put it among
the sound controls it is not one of. The separator is the line between the two
ideas; which side of it this sits on is the requirement. The theme button was
only ever a landmark for saying so.

Acceptance: Given the main window is open, when the toolbar is read left to
right, then the discovery button appears before the separator and before the
volume control.

Verified by: `tests/ui/test_discovery_button.py::test_discovery_sits_left_of_the_volume_button`

---

**FR-D02 The ring follows the button**

Priority: Must

Requirement: The main window shall include the discovery button in the keyboard
ring in its visual position.

Rationale: A control that cannot be reached by keyboard is a control half the
application's users do not have.

Acceptance: Given focus is on the button left of discovery, when Tab is pressed,
then focus is on the discovery button.

Verified by: `tests/ui/test_discovery_button.py::test_discovery_is_reachable`

---

**FR-D03 Choosing what to look for**

Priority: Must

Requirement: When the discovery button is pressed, the main window shall open
the discovery dialog showing the same genre catalogue the filter dialog shows.

Rationale: Two grids built from one catalogue cannot come to disagree; a second
vocabulary invented here would.

Acceptance: Given the catalogue holds a genre, when the discovery dialog opens,
then that genre appears in its grid with the same main and the same spelling as
in the filter dialog.

Verified by: `tests/ui/test_discovery_dialog.py::test_grid_matches_the_catalogue`

---

**FR-D04 Nothing ticked, nothing to do**

Priority: Must

Requirement: While no genre is ticked, the discovery dialog shall keep its
action button disabled.

Rationale: A run over no genres has no source artists, so offering it invites a
press that can only report emptiness.

Acceptance: Given the dialog has just opened with nothing ticked, when the
action button is examined, then it is disabled; when one genre is ticked, then
it is enabled.

Verified by: `tests/ui/test_discovery_dialog.py::test_action_needs_a_genre`

---

**FR-D44 Every genre can be ticked in one press**

Priority: Must

Requirement: The discovery dialog shall carry a control, distinct from the
genre tick boxes, that ticks every genre in the catalogue. Where every genre is
already ticked that control shall instead clear them all. It shall name
whichever of the two a press would do, read from the boxes rather than from the
last press it received. Pressing it shall not close the dialog and shall start
no run.

Rationale: Asked for by Oliver on 2026-09-08. The catalogue holds 34 boxes, so
asking about a whole library meant 34 presses; that is the kind of tidying a
dialog should do for somebody. A push button rather than a 35th tick box,
placed where the filter dialog's Clear already sits, because a tick box here
would read as one more genre and would be swept by its own sweep.

**It names its next press**, which is the convention both trays already follow
and the reason one control carries both meanings rather than two sitting side
by side. It is read off the boxes so that ticking the last genre by hand moves
it too, which a control remembering its own last press would get wrong.

It does not close, for the reason FR-D25 gives for Clear in the filter dialog:
sweeping and then asking is two presses, while somebody who swept by accident
has lost nothing.

Acceptance: Given a dialog with nothing ticked, when the control is read, then
it offers to select all; when it is pressed, then every genre in the catalogue
is ticked, the dialog is still open and no run has started; when it is pressed
again, then nothing is ticked. Given every genre ticked by hand, then the
control offers to clear; given one then unticked by hand, then it offers to
select all again.

Verified by: `tests/ui/test_discovery_dialog.py::test_the_sweep_ticks_every_genre_in_one_press`, `tests/ui/test_discovery_dialog.py::test_a_second_press_clears_them_again`, `tests/ui/test_discovery_dialog.py::test_the_sweep_says_what_a_press_would_do`, `tests/ui/test_discovery_dialog.py::test_ticking_the_last_box_by_hand_moves_the_sweep_too`, `tests/ui/test_discovery_dialog.py::test_the_sweep_is_a_button_rather_than_a_tick_box`, `tests/ui/test_discovery_dialog.py::test_sweeping_leaves_the_dialog_open`

---

**FR-D05 Who a run asks about**

Priority: Must

Requirement: When a run starts, the discovery service shall take as its source
artists the album artists of every held album whose resolved genre names at
least one ticked genre.

Rationale: The resolved genre is what the listener sees and what they spent
their time stating. Reading the probed tag instead reports the library as it was
before any of that work, which was demonstrated on 2026-09-06 by a measurement
that did exactly this and reported 179 albums as untagged when the true figure
was three.

Acceptance: Given an album whose probed tag names nothing and whose album edit
states Reggae, when Reggae alone is ticked, then that album's artist is a source
artist.

Verified by: `tests/application/test_discovery.py::test_sources_read_the_resolved_genre`

---

**FR-D06 No source artists**

Priority: Must

Requirement: If the ticked genres yield no source artists, then the discovery
dialog shall say so, make no request and write no file.

Rationale: Ticking a genre nothing in the library carries is an ordinary thing to do; the library holds a worked example: one artist, Smetana, is reachable
by no genre at all.

Acceptance: Given a genre no held album names, when the action button is
pressed, then the dialog reports that nothing in the library matches, no request
is made and no file is written.

Verified by: `tests/application/test_discovery.py::test_no_sources_makes_no_request`

---

**FR-D07 Finding the artist**

Priority: Must

Requirement: When a source artist is reached, the discovery service shall
request that artist's identifier from the catalogue source by name.

Acceptance: Given a source artist named in the library, when the run reaches
them, then exactly one identity request carrying that name is made.

Verified by: `tests/application/test_discovery.py::test_identity_is_requested_once`

---

**FR-D08 An artist the source does not know**

Priority: Must

Requirement: If the catalogue source returns no identifier for a source artist,
then the discovery service shall record that artist as unresolved, continue with
the next artist and make no further request about them.

Rationale: A library holds names a catalogue does not; a run that stops on
the first of them is a run that never finishes.

Acceptance: Given a source whose identity lookup returns nothing, when the run
completes, then that artist appears in the run's unresolved list and the run's
exit is normal.

Verified by: `tests/application/test_discovery.py::test_unknown_artist_is_recorded`

---

**FR-D09 An ambiguous name**

Priority: Must

Requirement: If the catalogue source returns more than one identifier for a
source artist's name, then the discovery service shall record that artist as
ambiguous, name every candidate identifier in the run's report and make no
further request about them.

Rationale: Choosing between two bands of the same name on a listener's behalf
would put an entire discography under the wrong heading, silently. Reporting the
ambiguity is honest; guessing at it is not.

Acceptance: Given an identity lookup returning two artists of equal score, when
the run completes, then that artist is reported ambiguous with both identifiers
named and no album request was made for them.

Verified by: `tests/application/test_discovery.py::test_ambiguous_name_is_reported`

---

**FR-D10 Albums by an artist already held**

Priority: Must

Requirement: When a source artist has been identified, the discovery service
shall request the albums that artist made, including each album's stated genres.

Acceptance: Given an identified source artist, when the run reaches their
albums, then one request is made carrying that artist's identifier and asking
for genres.

Verified by: `tests/application/test_discovery.py::test_albums_are_requested_with_genres`

---

**FR-D11 Never offering back what is owned**

Priority: Must

Requirement: When albums are received for a source artist, the discovery service
shall discard every album whose release key and secondary types match those of an
album the library already holds by that artist, as section 3.5 defines them.

Rationale: The whole value of the feature is the gap. An offer of something on
the shelf spends the listener's attention and teaches them to distrust the rest
of the list.

Acceptance: Given a source artist holding two albums in the library and five at
the source, when the run completes, then that artist's candidate albums number
three and neither held title appears.

Verified by: `tests/domain/test_discovery_gaps.py::test_held_albums_are_dropped`

---

**FR-D12 Artists like the ones held**

Priority: Must

Requirement: When a source artist has been identified, the discovery service
shall request the ten artists the similarity source considers most similar to
them.

Rationale: Ten was settled in PLAN.md and confirmed on 2026-09-06 as the shipped
figure. It is a named constant rather than a literal, since it is a decision
about how much to offer rather than a fact about anything.

Acceptance: Given an identified source artist, when the run reaches similarity,
then one request is made carrying that artist's identifier and asking for ten.

Verified by: `tests/application/test_discovery.py::test_similar_artists_are_requested`

---

**FR-D13 Never offering back an artist held**

Priority: Must

Requirement: When similar artists are received, the discovery service shall
discard every artist the library already holds.

Acceptance: Given a similar-artists response naming two artists in the library
and eight not, when the run completes, then that source artist carries eight
candidate artists.

Verified by: `tests/domain/test_discovery_gaps.py::test_held_artists_are_dropped`

---

**FR-D14 The ticked genres filter what is collected**

Priority: Must

Requirement: When a candidate album states genres, the discovery service shall
discard it where none of its stated genres names a ticked genre.

Rationale: Ticking Folk and receiving that artist's spoken-word record is the
filter failing at the only end that matters to the listener.

Acceptance: Given Folk is ticked and a candidate album states only Comedy, when
the run completes, then that album does not appear.

Verified by: `tests/domain/test_discovery_gaps.py::test_candidate_albums_respect_the_ticks`

---

**FR-D15 A candidate whose genre is unknown**

Priority: Should

Requirement: Where a candidate states no genre at all, the discovery service
shall keep it and mark it as of unstated genre.

Rationale: Dropping what a source failed to describe would silently narrow the
result to the well-catalogued, which is the opposite of finding what is missing.
Marking it lets a later stage decide.

Acceptance: Given a candidate album carrying no genres, when the run completes,
then it appears with its genre recorded as unstated.

Verified by: `tests/domain/test_discovery_gaps.py::test_unstated_genre_is_kept_and_marked`

---

**FR-D16 Saying what is happening**

Priority: Must

Requirement: The toolbar shall carry one progress bar per stage of a run,
stacked in the order the stages happen and each labelled with the name of its
stage. While a run is under way each bar shall show how far through its own
stage the run is as a percentage; a stage that has finished shall be left full
and a stage that has not begun shall show no percentage at all. On hover the
pair shall name the artist currently being asked about, with the number
completed and the number to be done.

Rationale: A run over the whole library takes about eleven minutes at the rate
the sources permit. A spinner over eleven minutes is indistinguishable from a
hang. Amended on 2026-09-07 after a measured failure: the dialog reported the
first half of a run only, so a run over Blues sat at 75% and silent for the
whole of the second half, which is the longer one. Both halves now report; they
report to the toolbar rather than to a dialog, since the dialog closes when the
run starts. The stage rather than the artist is drawn, because a strip of a
toolbar does not hold "Jools Holland & His Rhythm & Blues Orchestra".

Amended again the same day, on Oliver's ruling. One bar carrying both halves in
turn says how far through the current half a run is and nothing whatever about
the other, so a bar back at a tenth is either bad news or ordinary progress with
no way to tell which. Two bars say where the run is at a glance: the first full
with the second climbing is plainly further on than the first climbing with the
second empty. They occupy the height the single bar had, so the tray does not
grow and the centred transport does not move.

Acceptance: Given a run over three source artists, when the second is reached,
then the first bar reads one third and the pair names that artist on hover;
given the run reaches its second stage, then the first bar is left full and the
second counts against the number of candidates to be asked about.

Verified by: `tests/ui/test_discovery_bar.py::test_there_is_a_bar_for_each_half_of_a_run`, `tests/ui/test_discovery_bar.py::test_reaching_the_second_half_leaves_the_first_bar_full`, `tests/ui/test_discovery_bar.py::test_it_names_the_stage_rather_than_the_artist`, `tests/application/test_discovery_narrowing.py::test_the_second_half_of_a_run_reports_as_it_goes`

---

**FR-D17 Stopping**

Priority: Must

Requirement: When the listener cancels a run, the discovery service shall stop
before issuing its next request, discard everything that run had gathered and
leave any existing discovery file untouched.

Rationale: Stopping between requests rather than mid-flight keeps the source's
rate accounting honest and leaves nothing half-written. A cancel discards rather
than parks, ruled on 2026-09-06: a resumable run means keeping partial state
that has to be reconciled against a library that may have changed; the
smallest genres cost seconds to run again.

A stop is also felt rather than merely obeyed. Amended three times on
2026-09-07, after the button was reported as not working, then reported again
once the first amendment turned out to have fixed only how it looked, then
amended once more when the request in flight stopped being a floor.

The run is asked whether it is still wanted before EVERY request rather than
once an artist. One artist costs three requests, each of which may take the full
twenty second timeout and may be attempted three times, so a run consulted once
an artist could go on for minutes after being told to stop. The waits between
attempts are sliced as well, so a stop lands inside one rather than at the end
of it.

The request already in flight is killed rather than merely abandoned. It used
to be the floor on how quickly a stop could be felt: nothing portable
interrupts a thread waiting on a socket, while the wait for a response happens
inside the call that opens it, before there is any object to close. So the
fetcher no longer waits on one. Qt's network stack is event driven and a reply
in flight can be dropped outright; the request is asked whether anybody still
wants it every quarter second and ends the moment the answer is no. Measured on
2026-09-07 against a service that accepts a connection then says nothing: the
reply ends in under a millisecond, where the blocking client sat there until
its twenty second timeout.

The run itself is still not hurried. It is ABANDONED: cut loose from the
window, reporting to nobody, ending in its own time. That is what makes a stop
instant rather than eventual, which is the ruling in FR-D27. What the abandoned
run costs is its share of the request pacing: a new run started immediately is
queued behind whatever the old one has left, since both go through the same
gate and that gate exists to keep a promise to the services rather than to
either run. That cost is now bounded by the gap the terms ask for rather than
by a request that will not answer, because the last request of an abandoned run
dies with it instead of outliving it.

Acceptance: Given a run in progress over an existing discovery file, when cancel
is pressed, then no further request is issued, nothing of that run is retained
and the existing file is byte for byte what it was; given the run is waiting out
a refusal when cancel is pressed, then it stops within one slice of that wait
rather than at the end of it; given a cancel arrives between two of the three
requests made about one artist, then the remaining two are never issued; given
a run is wedged inside a request that will not answer at all, then the stop
still returns at once, the window is free to start another and that request is
dropped rather than left to reach its timeout.

Verified by: `tests/application/test_stopping_a_run.py::test_cancel_stops_before_the_next_request`, `tests/application/test_stopping_a_run.py::test_a_stop_is_felt_part_way_through_a_wait`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_request_nobody_wants_any_more_is_dropped_at_once`, `tests/infrastructure/test_discovery_sources.py::TestHandingTheQuestionDown::test_every_question_carries_whether_it_is_still_wanted`

---

**FR-D18 The output**

Priority: Must

Requirement: When a run completes, the discovery service shall replace the single
discovery file, whose keys are the source artists and whose value for each is
that artist's candidate albums and candidate artists.

Rationale: A file rather than a screen, because this stage exists to produce the
resource the later stages consume. One file replaced rather than a directory of
dated ones, ruled on 2026-09-06: a run states what is missing now, while a merge
would have to decide what becomes of a candidate offered last month that is
owned today.

Acceptance: Given a completed run over one source artist with two candidate
albums and three candidate artists, when the file is read, then it holds one key
naming that artist, with two albums and three artists beneath it.

Verified by: `tests/infrastructure/test_discovery_file.py::test_the_file_is_keyed_by_the_artist_it_was_found_for`

---

**FR-D19 The file cannot be written**

Priority: Must

Requirement: If the discovery file cannot be written, then the window shall
report the failure in its status bar with the reason, while leaving any previous
file untouched.

Acceptance: Given a destination that refuses writes, when a run completes, then
the failure is reported naming the path and the previous file is unchanged.

Verified by: `tests/ui/test_discovery_wiring.py::test_a_file_that_will_not_write_is_reported`, `tests/infrastructure/test_discovery_file.py::test_nothing_is_left_half_written`

---

**FR-D20 The network is not there**

Priority: Must

Requirement: If a request fails because no connection is available, then the
discovery service shall stop the run, report that the network is unavailable and
write no file.

Rationale: Continuing through 327 artists that will each fail is 327 ways of
saying the same thing slowly.

Acceptance: Given the first request raises a connection failure, when the run is
observed, then it stops at that point, reports unavailability and writes no
file.

Verified by: `tests/application/test_discovery.py::test_no_network_stops_the_run`

---

**FR-D21 The source refuses**

Priority: Must

Requirement: If a source answers that the request rate has been exceeded, then
the discovery service shall wait and retry that request rather than discarding
the artist, up to a stated number of attempts.

Rationale: A rate refusal is the source asking for patience, not reporting that
the data is absent.

Acceptance: Given a source refusing once then answering, when the run completes,
then that artist's results are present and exactly one retry was made.

Verified by: `tests/application/test_discovery.py::test_rate_refusal_is_retried`

---

**FR-D22 The source fails for another reason**

Priority: Must

Requirement: If a source returns an error that is not a rate refusal, then the
discovery service shall record that artist as failed with the reason, continue
with the next artist and include the failures in the run's report.

Acceptance: Given a source returning a server error for one artist of three,
when the run completes, then the other two are present and the failed one is
named with its reason.

Verified by: `tests/application/test_discovery.py::test_other_errors_do_not_stop_the_run`

---

**FR-D42 An answer says who it could not answer for**

Priority: Must

Requirement: When a run completes without a usable answer for one or more
artists, the message shown at the end of that run shall count each kind
separately: artists that could not be asked about, names the catalogue did not
recognise and names that matched more than one artist. Only the kinds that
happened shall be named. This applies both where the run found something and
where it found nothing.

Rationale: FR-D22 records the failures, `_about` records the other two and the
file has carried all three since; nothing read them back, so a run that could
not answer for a third of a library said exactly what a clean one said. That is
the misreading `RunReport` was written to prevent, in its own words: an artist
nobody could look up is the artist somebody would otherwise assume had nothing
missing. Found 2026-09-08 by reading the path rather than by anybody meeting it.

**Counted apart because they are not the same news.** A source error is worth
running again later; a name the catalogue does not hold is a spelling to look
at; a name several artists share cannot be settled from a name at all. One
total would hide which of the three somebody is looking at.

A stopped run and an unreachable one are deliberately left out. Each already
says its answer is incomplete, so a count there states the same thing twice; the
endings that mislead are the two that read as finished. An answer that could not
be written is left out for the same reason.

Acceptance: Given a completed run that found albums, could not ask about four
artists, did not recognise three names and found two names shared, when it ends,
then the message names the counts found and says all three of those numbers with
no comma before the `and`; given a run whose only trouble was three unrecognised
names, then it says that alone and names neither other kind; given a stopped run
holding a failure, then it says only that it was stopped.

Verified by: `tests/ui/test_shortfall.py::TestTheSentence`, `tests/ui/test_discovery_wiring.py::test_a_run_names_all_three_kinds_of_silence`, `tests/ui/test_discovery_wiring.py::test_only_the_groups_that_happened_are_named`, `tests/ui/test_discovery_wiring.py::test_finding_nothing_still_says_what_went_unanswered`, `tests/ui/test_discovery_wiring.py::test_a_stopped_run_counts_nothing`

---

**FR-D43 The names themselves are one press away**

Priority: Must

Requirement: Where a run ends owing the message in FR-D42, a button shall be
offered beside that message carrying its own count of the artists gone
unanswered. Pressing it shall open a modal dialog listing those artists, grouped
under a heading for each of the three kinds with a plain sentence saying what
that kind means. The button shall be offered only where something is owed and
shall be taken away when the next run starts.

Rationale: The same split `scan_summary` already makes. A count is the right
weight for something nobody asked for; the names are the right weight for an
answer somebody pressed a button to get. A status line that tried to carry
several hundred names would be unreadable at the length that matters; the
names are also the half somebody can act on: a misspelt tag is only fixable once it
has been seen.

**The button carries its own count rather than leaning on the sentence.** The
status bar is shared: playing a track replaces the text within seconds, which
would leave a button reading `Show them` beside a sentence about something else.
`9 artists unanswered` still says what it is once its sentence has gone. That is
also why it survives the results screen, which is modal and opens over the
message the moment a run ends.

**It is taken away when the next run begins**, not when the next message is
said. A shortfall belongs to the run that had it; a run under way has not
produced one yet.

The reasons the sources gave are not shown. They are wording written for a
program, the discovery file already holds every one of them and a column of them
beside the names would bury the names.

Acceptance: Given a run that could not answer for nine artists, when it ends,
then a button reading `9 artists unanswered` is offered; given one artist, then
it reads `1 artist unanswered`; given the button pressed, then a modal dialog
lists every one of those artists under the heading for its kind; given a run
that answered for everybody, then no button is offered; given a new run started,
then the button is taken away.

Verified by: `tests/ui/test_shortfall.py::TestTheButtonLabel`, `tests/ui/test_shortfall.py::TestTheList`, `tests/ui/test_shortfall.py::TestTheDialog`, `tests/ui/test_discovery_wiring.py::test_the_button_appears_carrying_its_own_count`, `tests/ui/test_discovery_wiring.py::test_one_unanswered_artist_reads_as_one`, `tests/ui/test_discovery_wiring.py::test_a_clean_run_offers_no_button`, `tests/ui/test_discovery_wiring.py::test_a_new_run_takes_the_last_one_s_button_away`, `tests/ui/test_discovery_wiring.py::test_pressing_it_opens_the_names`, `tests/ui/test_dialog_first_stop.py`

---

**FR-D23 One run at a time**

Priority: Must

Requirement: While a run is under way, pressing the discovery button shall stop
that run rather than offer a second one.

Rationale: Two runs racing would double the request rate, breaching NFR-PERF-001
against both hosts, then race each other to replace the same file. Found by the
silence check rather than by anybody asking for it. Amended on 2026-09-07: the
dialog closes when a run starts, so there is no action button left to disable
and the thing wanted of a run in progress is to stop it. The runner refuses a
second run of its own accord, which is where the guard belongs.

Acceptance: Given a run in progress, when the discovery button is pressed, then
that run is asked to stop and no dialog opens; when no run is under way, then
the same press opens the dialog.

Verified by: `tests/ui/test_discovery_stopping.py::test_pressing_it_during_a_run_stops_the_run`, `tests/ui/test_discovery_wiring.py::test_the_runner_refuses_a_second_run`

---

**FR-D24 The application closes mid-run**

Priority: Must

Requirement: If the application is asked to close while a run is under way, then
the discovery service shall stop before its next request and leave any existing
discovery file untouched.

Rationale: The same ruling as a cancel, since a close is a cancel the listener
expressed differently. Found by the silence check.

Acceptance: Given a run in progress over an existing discovery file, when the
window is closed, then no further request is issued and the existing file is
byte for byte what it was.

Verified by: `tests/application/test_stopping_a_run.py::test_closing_stops_the_run`

---

**FR-D25 The dialog asks, then leaves**

Priority: Must

Requirement: When a run is started, the discovery dialog shall close.

Rationale: Ruled on 2026-09-07 after a run was watched. A run takes minutes at
the rate the sources permit; a dialog held open for all of them is one
somebody has to work around to carry on listening; a listener who wants to
watch a bar can watch the one in the toolbar. The dialog therefore knows nothing
about a run: it cannot report on one, cannot stop one and does not know whether
one is under way.

Acceptance: Given a genre is ticked, when the action is pressed, then the ticks
are handed over and the dialog closes; given nothing is ticked, when the action
is reached from the keyboard and pressed, then nothing is started and the dialog
stays.

Verified by: `tests/ui/test_discovery_dialog.py::test_finding_closes_the_dialog`

---

**FR-D26 What a candidate plays is remembered**

Priority: Must

Requirement: The discovery service shall keep what each candidate artist was
found to play and shall not ask about a candidate it already holds an answer for.

Rationale: The second stage of a run asks the catalogue what every suggested
artist plays, at one request a second. What somebody plays does not change
between one run and the next, so asking again spends a listener's minutes on an
answer already held. Ruled on 2026-09-07, when the cache was found to exist,
to be tested and to be wired to nothing: every run had been asking from scratch.
An answer already held is still judged against the genres ticked, so remembering
cannot smuggle a candidate past the scope of a run.

Acceptance: Given a run that asked about two candidates, when a second run meets
the same two, then no request is issued about either and both are judged against
that run's own ticks.

Verified by: `tests/application/test_discovery_narrowing.py::test_what_was_remembered_is_not_asked_about_again`, `tests/ui/test_discovery_composition.py::test_a_run_is_given_somewhere_to_remember_what_it_learns`

---

**FR-D27 Stopping is immediate**

Priority: Must

Requirement: When the discovery button is pressed while a run is under way, the
window shall stop that run at once, without asking anything. While a run is
under way the button shall wear the negative mark over its picture and shall
say "Stop discovery"; the mark shall come off on EVERY ending, whether the run
was stopped, completed, found nothing, could not be reached or failed.

Rationale: Ruled on 2026-09-07, REVERSING the confirmation this requirement
asked for earlier the same day. The question was added so that eleven minutes
of waiting could not be discarded by a stray press. It was measured doing the
opposite: a trace of the running application caught the question answering No
while the run carried on, which is the whole of a defect reported three times
as the stop never stopping. A question defaulting to leaving the run alone is a
thing a press has to get past, so the control that says stop did not stop.

What the question was protecting against is now answered by the button saying
what it is. One control carries both meanings, so it shows which one it is
carrying: crossed out and reading "Stop discovery" while a run is going, plain
and offering to discover while none is. A press on a control that plainly says
stop is not a press that needs checking; the accident the question guarded
against was a button that gave no sign of having changed meaning.

The mark is the same artwork the switches at the foot of the window wear rather
than a second discovery picture, so a change to it reaches every use. Picture
and words are set together in one place, because a button crossed out while
offering to start a run is worse than either alone.

Amended on 2026-09-08. The wording was "Stop looking" when written and became
"Stop discovery" in the shipped button without this being amended with it, so
the guide was then written from here and told a reader the wrong thing. The
strings live in `stellody/ui/tray_metrics.py`; the guide reads them from there
now rather than quoting them, which is what stops this document being able to
mislead a screen again.

Acceptance: Given a run in progress, when the discovery button is pressed, then
the run is asked to stop with no question raised, the toolbar bar returns to
rest at once and reports are ignored until the run ends. Given a run in
progress, then the button carries the negative mark and says "Stop discovery".
Given a run that is stopped, one that completes, one that fails and one that
reaches nothing, then in every case the mark comes off and the button says
"Discover music the library does not hold" again. Given a new run is asked for
before the last one has finished winding down, then the window says so rather
than appearing to do nothing.

The bar is let go of on the press rather than on the ending, because a run is
abandoned rather than waited for: a bar held until the run noticed would go on
reporting a run somebody had finished with. Reports arriving afterwards are
dropped for the same reason. They are not hypothetical: the run reports right
up to the moment it notices.

Verified by: `tests/ui/test_discovery_stopping.py::test_a_press_stops_at_once_without_asking_anything`, `tests/ui/test_discovery_stopping.py::test_the_button_wears_the_cross_while_a_run_is_under_way`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_is_stopped`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_finishes_on_its_own`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_fails`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/ui/test_discovery_stopping.py::test_a_new_run_asked_for_too_soon_says_so`

---

**FR-D28 The results are shown when a run completes**

Priority: Must

Requirement: When a discovery run completes having found at least one candidate,
the window shall write the discovery file and then open the results dialog on
what that file holds.

Rationale: Reverses the stage-one exclusion, which ruled a results view out and
said it would be built from the file. It is built from the file: one thing stays
authoritative, so showing a past run's answer again later then costs nothing
extra on the day that is wanted.

**Only one results screen exists at a time; it is MODAL.** Amended twice on
2026-09-08. Two screens were first seen stacked over each other, which was
answered by closing the standing one as a new one opened. That treated the
symptom: it did not hold in the running application, so Oliver ruled the screen
modal instead and the closing was deleted with the defect it was patching.

A completed run REPLACES the discovery file, so a screen left standing from an
earlier run shows an answer that no longer exists anywhere. Being modal removes
the state rather than tidying it: one run's answer is read and dismissed before
another can be started, so there is never a second screen to reconcile.

**Modeless was the earlier decision and is recorded as reversed rather than
deleted**, so it is not re-proposed on the reasoning that first produced it. The
answer arrives minutes after the question, so a modal screen does seize the
application at a moment nobody chose; the screen is also worked over minutes,
candidates being expanded a few seconds apiece. What outweighed that is what
runs stacking without limit actually cost: an answer on screen that no longer
existed anywhere, which is worse than being interrupted.

**A message set behind a modal screen is only seen once that screen closes**, so
the run's own message is said BEFORE the screen opens rather than after it. The
settled path returns its message and opens nothing; completion says it, then
opens.

Acceptance: Given a run that found two candidate albums, when it completes, then
the file is written and a dialog opens naming both, modally; given the run's own
message, then it is said before the screen opens rather than behind it.

Verified by: `tests/ui/test_results_dialog.py`, `tests/ui/test_discovery_wiring.py`

---

**FR-D29 What a source artist shows**

Priority: Must

Requirement: For each source artist the run found something for, the results
dialog shall show that artist once, with the candidate albums beneath them.

Rationale: The source artist is the reason each album is being offered, so an
album shown without the name it hangs under says nothing about why it is there.

Acceptance: Given a source artist with two candidate albums, when the dialog
opens, then the artist appears once and both albums appear beneath that name.

Verified by: `tests/ui/test_results_dialog.py::test_a_source_artist_carries_its_albums`

---

**FR-D30 What a candidate artist shows**

Priority: Must

Requirement: For each candidate artist, the results dialog shall show that
artist's name collapsed, with no album beneath it until it is expanded.

Rationale: A candidate artist is one the library holds nothing by, so every
record they made is unheld and the list beneath them would be their whole
discography. Most are never opened; FR-D31 states what asking for all of them
would cost.

Acceptance: Given a run that found three candidate artists, when the dialog
opens, then three names are shown and no album sits under any of them.

Verified by: `tests/ui/test_results_dialog.py::test_a_candidate_artist_starts_collapsed`

---

**FR-D31 A candidate artist's albums are fetched on demand**

Priority: Must

Requirement: When a candidate artist is expanded in the results dialog, the
results dialog shall show the releases that artist made which pass the offering
rule FR-D08 states, fetched at the moment of expanding rather than during the
run.

Rationale: Measured on 2026-09-07: one catalogue request costs at least the 1.1
second gap NFR-PERF-001 requires. Asking during the run would add a request for
every candidate surviving the genre filter, roughly doubling a second stage that
is already the longer half. Ruled by Oliver the same day: pay it only for the
ones somebody actually opens.

Acceptance: Given a collapsed candidate artist, when it is expanded, then that
artist's offered releases appear beneath it; given the run that produced the
file, then it issued no request about that artist's releases.

Verified by: `tests/ui/test_results_dialog.py::test_expanding_a_candidate_asks_for_their_albums`

---

**FR-D32 The lookup for an expanded artist cannot be made**

Priority: Must

Requirement: If the releases of an expanded candidate artist cannot be fetched,
then the results dialog shall show what went wrong against that artist, leaving
every other entry as it was.

Rationale: The unwanted sibling of FR-D31. One artist nobody could look up is
not a reason to lose the rest of a run that took minutes to make.

Acceptance: Given a candidate artist whose lookup fails, when it is expanded,
then that artist shows what went wrong; when another is expanded, then it still
lists its releases.

Verified by: `tests/ui/test_results_dialog.py::test_a_failed_expansion_says_so_and_spares_the_rest`

---

**FR-D33 A run that found nothing opens no dialog**

Priority: Must

Requirement: If a discovery run completes having found no candidate album and no
candidate artist, then the window shall not open the results dialog.

Rationale: The unwanted sibling of FR-D28. An empty dialog says less than the
sentence shown in its place, while still landing in front of whatever somebody
had moved on to doing. What the status bar says in that case is unchanged, so
this adds no requirement about it; FR-D16 already governs that.

Acceptance: Given a run that found nothing, when it completes, then no dialog
opens and the status bar carries the message it carries today.

Verified by: `tests/ui/test_results_dialog.py::test_a_run_that_found_nothing_shows_no_dialog`

---

**FR-D34 A source artist and a candidate artist are told apart by colour**

Priority: Must

Requirement: The results dialog shall draw source artist names in a different
colour from candidate artist names, both colours taken from the theme's
semantic tokens.

Rationale: The two mean different things. A source artist is somebody already
held who is missing records; a candidate artist is somebody not held at all. A
list reading the same for both leaves the reader working out which is which from
context that is not on the screen.

Acceptance: Given a dialog holding both kinds, when the two colours are read
from the theme, then they differ in each appearance.

Verified by: `tests/ui/test_results_dialog.py::test_the_two_kinds_of_artist_are_coloured_apart`

---

**FR-D39 The results say what they are showing**

Priority: Must

Requirement: The results dialog shall carry a key naming each kind of row it
draws, each entry marked with a filled circle in the colour that kind is drawn
in. Every artist row shall state its kind in words: a source artist row shall
give the number of albums and the number of similar artists beneath it. A
candidate artist row shall name itself as a similar artist, gaining the number
of its albums once they have been fetched.

Rationale: Reported by Oliver on 2026-09-07, looking at a real run: shown blue
names, amber names and plain names, he asked which lines were albums and which
were tracks, then whether two of the amber names were artists at all. They were.
A candidate artist is drawn indented under the source artist that led to it, so
it reads as an album under an artist; its own albums then read as tracks under
that. Nothing in the run is ever a track, which the key can say outright.

Colour is not left to carry the meaning by itself. It fails a reader who cannot
separate the two hues, it fails a screenshot pasted into a message and it failed
the person who commissioned it. FR-D34 keeps the colours; this states what they
mean in words beside them.

Acceptance: Given a dialog holding both kinds, when the key is read, then it
names all three kinds of row with a mark in each kind's own colour; when a
source artist row is read, then it gives both counts; when a candidate row is
read, then it names itself a similar artist.

Verified by: `tests/ui/test_results_reading.py::test_the_key_names_all_three_kinds_in_their_own_colours`, `tests/ui/test_results_reading.py::test_a_source_row_says_how_many_of_each_sit_under_it`, `tests/ui/test_results_reading.py::test_a_candidate_row_says_that_it_is_an_artist`

---

**FR-D40 The results say when the catalogue is being asked**

Priority: Must

Requirement: While one or more candidate artist lookups are in flight, the
results dialog shall show a busy indicator naming the artist being asked about;
where there is more than one, it shall name the number of artists instead. The indicator shall
occupy its place whether or not anything is in flight, carrying instead what to
do to fetch an artist's albums.

Rationale: Reported by Oliver on 2026-09-07: opening an amber name left the
dialog doing nothing visible for several seconds, which reads as stuck. It is
not stuck. One lookup costs at least the gap NFR-PERF-001 requires and may wait
out two refusals before answering, so several seconds of quiet is the ordinary
case rather than a fault; what was missing was anything on screen saying so.

Busy rather than counted, since one request has no measurable progress: it
either comes back or is waited out. The space is reserved rather than shown only
while something is in flight, because a strip that appeared would push the whole
list down at the moment somebody clicked an arrow in it.

Acceptance: Given a candidate artist being expanded, when the dialog is read,
then the indicator names that artist and is busy rather than counted; given two
in flight, then it names the number; given the last answer arriving, then it
returns to carrying the instruction.

Verified by: `tests/ui/test_results_reading.py::test_the_strip_names_who_is_being_asked_about`, `tests/ui/test_results_reading.py::test_the_strip_counts_them_when_several_are_in_flight`, `tests/ui/test_results_reading.py::test_the_strip_goes_quiet_when_the_last_answer_lands`

---

**FR-D41 The results say what the run looked in**

Priority: Must

Requirement: The results dialog shall state, above the key, the number of
genres the run was scoped to and their names. The genres shall be read from the
discovery file being shown rather than from the ticks handed over when the run
started. Where the file names no genres the dialog shall show no such line at
all.

Rationale: Asked for by Oliver on 2026-09-08. A run's answer says nothing about
the question that produced it: the same library asked about Folk and asked
about Rock yields two unlike screens that read identically, so a listener
returning to one has no way to tell which run they are looking at, nor why an
artist they expected is absent.

From the file rather than from the ticks, for the reason FR-D28 shows the gaps
from the file: two sources are two things to disagree. Held in one reading with
the gaps for the reason FR-D35 takes one reading of the pace, since a file
replaced between two reads would put one run's question above another run's
answer.

The count is given as well as the names because a run over eleven genres is a
different thing from a run over one; the number says which before the list is
read. The line is absent rather than empty where the file names none, which
only a file written before this existed can be: "looked in nothing" would be
worse than the absence, while nothing about the gaps changes either way.

Acceptance: Given a run scoped to two genres, when the dialog opens, then a
line above the key names both and says there were two; given one genre, then
the line says one genre rather than genres; given a file naming no genres, then
no such line is drawn and the gaps are shown as before.

Verified by: `tests/ui/test_results_reading.py::test_it_says_which_genres_the_run_looked_in`, `tests/ui/test_results_reading.py::test_one_genre_is_not_called_genres`, `tests/ui/test_results_reading.py::test_a_run_that_names_no_genres_shows_no_line_at_all`, `tests/ui/test_results_reading.py::test_the_genres_sit_above_the_key`, `tests/ui/test_results_dialog.py::test_the_genres_shown_come_from_the_file_it_is_showing`, `tests/application/test_discovery.py::test_a_completed_run_carries_what_it_was_asked_to_look_in`, `tests/infrastructure/test_discovery_results.py::TestWhatTheRunWasAskedFor`

---

**FR-D35 How long the run has left**

Priority: Must

Requirement: While a discovery run is under way, the window shall show an
estimate of the time remaining for the whole run in BOTH of two places. In the
status bar it shall be a sentence rounded to the nearest minute, saying less
than a minute where the estimate is under sixty seconds. At the right hand end
of the discovery bar it shall be an abbreviated form of that same estimate.
Both shall be answered from one reading of the pace.

Rationale: Reported by Oliver on 2026-09-07: a small run took a minute or two
with nothing on screen saying whether that was normal. NFR-PERF-002 puts a whole
library at about eleven minutes for the first stage alone. Somebody who cannot
tell a long run from a hang closes the window, which throws the run away.

The second place was added the same day, on his report that the estimate could
not be found. It was in the status bar as this required, which is the foot of a
window whose discovery bar is at the top: somebody watching a percentage climb
never meets a sentence 800 pixels below it. The bar is a strip 170 pixels wide,
so what it carries is "4m" rather than the sentence; the room for it is taken
out of the bar before the stage name is centred in what is left. One
reading of the pace answers both, else the two could be taken a moment apart
and disagree across a rounding.

Acceptance: Given a run under way with an estimate available, when the status
bar is read, then it names a whole number of minutes or says less than a
minute; when the discovery bar is read, then its right hand end carries the
same estimate abbreviated, drawn clear of the stage name.

Verified by: `tests/ui/test_run_estimate.py::test_the_status_bar_names_the_time_left`, `tests/ui/test_discovery_bar.py::test_it_writes_how_long_is_left_at_the_right_hand_end_of_the_moving_bar`, `tests/ui/test_discovery_bar.py::test_the_time_and_the_stage_are_never_drawn_over_each_other`, `tests/ui/test_discovery_bar.py::test_the_time_is_actually_drawn_on_the_bar`

---

**FR-D36 The estimate is taken from the run itself**

Priority: Must

Requirement: The window shall derive the estimate from the time the run has
actually taken for each unit of work finished, rather than from the request gap
NFR-PERF-001 states.

Rationale: A run meets refusals; each costs up to three attempts with a
lengthening wait between them, as FR-D21 requires. An estimate built on the
configured gap would read as confident while being wrong by minutes on exactly
the runs where somebody most needs it.

Acceptance: Given a run whose finished units took twice the gap apiece, when the
estimate is computed, then it follows the observed pace rather than the
configured one.

Verified by: `tests/domain/test_estimating.py::test_the_pace_comes_from_what_happened`

---

**FR-D37 The second stage is estimated before it begins**

Priority: Must

Requirement: While a run is in its first stage, the window shall include in the
estimate a projection of the second stage, sized from the candidate artists seen
so far against the source artists finished so far.

Rationale: The second stage asks about every candidate the first stage turns up,
so its size is unknown until the first stage ends. An estimate covering only the
first stage would understate the wait by the larger half of it, which is worse
than saying nothing at all.

Acceptance: Given a run that has finished two of ten source artists and turned up
twelve distinct candidates, when the estimate is computed, then it covers a
projected sixty candidates alongside the eight source artists left.

Verified by: `tests/domain/test_estimating.py::test_the_second_stage_is_projected_from_the_first`

---

**FR-D38 Too little has happened to estimate**

Priority: Must

Requirement: If fewer than two units of the current stage have finished, then
the window shall say the run is under way without naming a time.

Rationale: The unwanted sibling of FR-D35. A pace measured over one sample is
wrong by a factor on any run whose first request met a refusal. A number that
swings is trusted less than an honest silence.

Acceptance: Given a run that has finished one source artist, when the status bar
is read, then it says the run is under way and names no time.

Verified by: `tests/domain/test_estimating.py::test_one_sample_is_not_enough_to_estimate`

---

### 3.2 Non-functional requirements

---

**NFR-PRIV-001 What leaves the machine**

Priority: Must

Requirement: A discovery run shall send nothing but artist names and artist
identifiers drawn from the ticked genres, together with the application's own
User-Agent.

Rationale: The stance in PLAN.md forbids anything outward that carries the
library or names the listener. Genre scoping is what makes this satisfiable: a
run names the subset the listener chose rather than an inventory of everything
they own.

Verification: inspection of every request the fake source records in
`tests/application/test_discovery.py`, asserting the request bodies and query
strings hold nothing beyond names and identifiers.

---

**NFR-PRIV-002 No identifier of the listener or the machine**

Priority: Must

Requirement: A discovery run shall send no account, no installation identifier,
no machine name, no file path and no library statistic.

Rationale: The application has no account and no telemetry; this must not be
the feature that introduces one by accident.

Verification: as NFR-PRIV-001, asserted against a fixed allowed set of request
fields, so a field added later fails the test rather than passing unnoticed.

---

**NFR-PRIV-003 The User-Agent names the application, never the person**

Priority: Must

Requirement: The catalogue source shall send a User-Agent naming Stellody, its
version and a project contact address, as MusicBrainz requires, with nothing about the listener.

Verification: a structural test asserting the User-Agent is built from the
version module and a fixed contact string, with no other interpolation.

---

**NFR-PERF-001 Request pacing**

Priority: Must

Requirement: The discovery service shall issue at most one request per second
per source host, measured over any ten second window.

Rationale: MusicBrainz declines above one per second per IP; ListenBrainz states
the same limit. Pacing to the published figure is the difference between a run
that finishes and an address that gets refused.

Verification: a test driving a fake clock over a fabricated run of twenty
artists, asserting no two requests to one host fall inside one second.

---

**NFR-PERF-002 Run duration**

Priority: Should

Requirement: A run over the full library of 327 source artists shall complete
within twenty minutes on the reference machine, with the two catalogue requests
per artist paced at one per second and the similarity request overlapping them.

Rationale: The arithmetic gives about eleven minutes; twenty is the figure that
may be asserted without the test becoming a weather report.

**NOT MEASURED. This is the one requirement here that no evidence stands
behind.** The live run of 2026-09-08 covered Blues and Folk rather than the
whole library, so it says nothing about a run over all 327 source artists.
Nothing in the suite can supply it either, since the figure is a property of
two public services on the day they are asked.

Verification: a run over every genre against the real sources, timed end to
end, recorded here with the date it was taken. Until that happens the twenty
minutes is arithmetic rather than a measurement, which is why this is a Should
rather than a Must.

---

**NFR-PERF-003 The candidate genre budget**

Priority: Must

Requirement: The discovery service shall look up a candidate artist's genre at
most once per run, however many source artists name that candidate, then retain what it learned for reuse by later runs.

Rationale: The similarity source returns identifiers with no genre, so filtering
candidates by genre costs one lookup each. Ten candidates for each of 327
artists is 3,270 requests, which is another fifty-four minutes at the permitted
rate. Deduplication is what makes the result-side filter affordable; the true
saving cannot be stated before a real run and is recorded in OQ-04.

Verification: a test with two source artists sharing a candidate, asserting one
genre lookup rather than two.

---

**NFR-USE-001 The toolbar bar can be read**

Priority: Must

Requirement: The text on the discovery bar shall hold a contrast ratio of at
least 4.5 to 1 against both the filled and the unfilled part of that bar, in
both appearances. The filled part shall be distinguishable from the groove by at
least 3 to 1, either by the fill itself or by an edge drawn round it reaching
that against both the fill and the groove.

Rationale: The bar drew its text in the muted colour over the accent as a fill,
which measured 1.29 to 1 in the light appearance and 1.32 to 1 in the dark one.
Reported on 2026-09-07 as difficult to read, which was an understatement. A bar
is the one surface here carrying one colour of text across two backgrounds, so
both are measured; nothing caught it because nothing measured it.

The first repair cleared 4.5 and was still reported as hard to read: 4.82 to 1
of white on blue is a pass and a smudge at the same time. Taking the dark fill
down to #24478f and the writing up to plain white lifts it to 8.85, measured
after the near-white it carried was reported as still not bright enough. What
that costs is the other half, since the
groove in the dark appearance is nearly black: a fill dark enough for white
writing sits at 2.11 against it. The two constraints have no solution together,
so the boundary is DRAWN instead of inferred, which is what the second clause
allows. The requirement is that the filled part can be told from the groove;
lightness was only ever one way of meeting it.

Acceptance: Given either appearance, when the colours are measured by the WCAG
relative luminance formula, then text against fill and text against groove each
reach 4.5; either fill against groove reaches 3 or the edge reaches 3 against
both the fill and the groove.

Verified by: `tests/ui/test_progress_contrast.py`

---

**NFR-USE-002 The results dialog can be read**

Priority: Must

Requirement: Every colour the results dialog uses for text, the two artist
colours FR-D34 requires included, shall hold a contrast ratio of at least 4.5 to
1 against the surface behind it, in both appearances.

Rationale: FR-D34 asks for two colours that differ from each other, which is not
the same as two colours that can each be read. The discovery bar was shipped at
1.29 to 1 by satisfying one of those and not the other, reported on 2026-09-07
as difficult to read. Two colours chosen to be distinguishable are exactly where
that happens again.

Acceptance: Given either appearance, when each text colour is measured against
its surface by the WCAG relative luminance formula, then every ratio reaches
4.5.

Verified by: `tests/ui/test_results_contrast.py`

---

**NFR-MAINT-001 The gate**

Priority: Must

Requirement: Every module added by this work shall sit inside the existing
coverage gate at 100% branch for the domain and application layers, stay at or
below 400 lines and land at 350 or below where it enters the 381 to 399 band.

Verification: `.\gate.ps1`, read by exit code.

---

**NFR-MAINT-002 The suite never reaches the network**

Priority: Must

Requirement: No test shall make a network request. Every source is reached
through an application-layer interface with a hand-written fake behind it.

Rationale: The house rule against mock libraries; also the practical one that a
suite depending on a third party fails on their bad day rather than on yours.

Verification: a structural test scanning the test tree for imports of any HTTP
client.

---

**NFR-REL-001 Nothing is written into the music folder**

Priority: Must

Requirement: The discovery file and the candidate genre cache shall be written
inside Stellody's own data directory and nowhere else.

Verification: a structural test asserting the discovery modules resolve their
paths through `infrastructure/paths.py` alone.

---

### 3.3 External interfaces

**The catalogue source** answers two questions: the identifier for an artist name; the albums an artist made with their stated genres. **The similarity
source** answers one: the artists similar to an identifier.

Both are reached through interfaces declared in the application layer, so the
choice below is an infrastructure decision and is reversible without touching a
requirement above.

**Decision, 2026-09-06: MusicBrainz for the catalogue, ListenBrainz for
similarity.** Recorded with its reasoning so it is not re-argued.

| | MusicBrainz | ListenBrainz | Discogs | Last.fm |
|---|---|---|---|---|
| Albums by an artist | yes | no | yes | weaker |
| Similar artists | no such endpoint | yes | no such endpoint | yes |
| Genre on results | yes | no | per release lookup | tags |
| Credential | none | none | token | key |
| Rate | 1 per second | 1 per second | 60 per minute | 5 per second |
| Terms | core data CC0 | MetaBrainz | token | non-commercial only |

Neither catalogue source has a similarity relation, so two sources are required
by the sources rather than by preference. Discogs and Last.fm are excluded by
C-07: both need a credential; a credential compiled into a GPL application
is a published credential. Last.fm is excluded twice over, since its
non-commercial condition would be imposed on everyone who forks the project.
MusicBrainz costs a User-Agent naming the application, which NFR-PRIV-003 covers.

### 3.4 Data

The discovery file is JSON, keyed by source artist, with each value holding that
artist's candidate albums and candidate artists.

Settled 2026-09-06: **one file, beside the database in Stellody's own data
directory, replaced by every completed run.** Not a directory of dated files,
which becomes a thing to tidy up; not a merge, which would have to rule on a
candidate offered once and owned since. A run therefore states what is missing
at the moment it finished, which is the only claim it can honestly make.

Its exact JSON shape is settled at implementation, constrained by FR-D18 and by
the four things the file carries beside the results: the artists that could not
be resolved (FR-D08), the ambiguous ones (FR-D09), the failures (FR-D22) and
the genres the run was scoped to (FR-D41).

The genres were added on 2026-09-08. Until then the file was an answer to a
question nobody had written down, so a run over Folk and a run over Rock
produced files that could not be told apart. A file written before that carries
none, which reads as an empty list rather than as a fault: the reader is
forgiving here exactly as it is about every other part of the file.

### 3.5 What makes two albums the same album

Settled 2026-09-06, against the 619 album titles actually held. This is what
FR-D11 means by an album the library already holds.

**The principle the tables follow from.** An EDITION qualifier describes the
pressing. A PERFORMANCE qualifier describes the recording. The same recording in
a different pressing is the same album; a different recording is a different
album. A remaster is therefore the same album; a live version is not.

**The source side arrives clean, so the two sides are treated differently.** A
MusicBrainz release group is the abstract album, with its remasters, deluxe
editions and country pressings held inside it as releases. The edition noise
exists only in the library, because a ripper wrote it into a tag.

**`AlbumIdentity` is not touched.** Its handle keys the artwork cache, the album
rating, every track rating and every accepted correction, so changing it would
orphan all of them. Matching gets its own pure module built on the same
`comparison_key` primitive, so the two cannot drift on normalisation.

**The year is deliberately absent from the key.** A remastered album's tag
carries the remaster's year while the release group carries the original's, so a
key holding the year makes every remastered album a false gap. The artist is
fixed for the comparison anyway, since one source artist's releases are matched
against that same artist's held albums.

**The rule.** The release key is `comparison_key(title)` with trailing
qualifiers removed, a qualifier being a parenthesised group, a bracketed group
or a trailing `" - X"` segment. A segment is removed when:

1. it is a lone type marker, `EP` or `Single`, which iTunes writes into a title
   and the source states as a primary type instead; or
2. it holds no word naming a different recording; it either ends in `edition`,
   `version`, `remaster`, `remastered` or `reissue`, else is built wholly of
   edition words and connectives with a four-digit year permitted.

The three tables are data rather than rules buried in code:

- **Edition words**: remaster, remastered, remasters, deluxe, expanded, edition,
  editions, version, anniversary, special, bonus, track, tracks, reissue,
  digital, super, explicit, clean.
- **Terminal words**, which carry a segment whatever else it holds: edition,
  version, remaster, remastered, reissue.
- **Distinguishing words**, one of which anywhere stops a strip: live, remix,
  remixes, remixed, instrumental, instrumentals, karaoke, acoustic, demo, demos,
  mix, mixes, unmixed, dj, session, sessions, mono, radio, edit, single, cover,
  tribute, score, soundtrack, compilation.

**Amended 2026-09-06, while the domain was being built.** As first written, this
section compared a release key plus the secondary types and said no more, which
would have made every live and remix album a false gap: the library holds
`Secret World (Live)`, keying to `secret world (live)`, while the catalogue has
that record as `Secret World Live` with the type stated separately. The two
never meet. The rule is therefore symmetric; the principle behind it is that
**a title word merely restating a stated type is noise**. The library reads its
kinds out of the title and then takes the qualifier off; the catalogue takes its
kinds as data and drops any trailing word that only repeats one of them. Both
sides arrive as a key plus a kind. A record actually titled `Live` keeps its
title rather than reducing to nothing.

**The source's own types do the rest.** A release group states a primary type
and secondary types, which are stated data rather than a string parsed by us. A
release group's identity for matching is its release key together with its
secondary types, so a live album never suppresses the studio album of the same
name and is never suppressed by it. Offered: primary type Album and EP, plus the secondary types Live, Remix and Demo, which are genuinely different records.
Excluded: Compilation and DJ-mix, since a hits package of an artist already held
is noise rather than a discovery.

**What the library measured, which is why each table looks as it does.**

- 30 titles are stripped, every one a pressing.
- 27 trailing qualifiers are kept, every one a different recording or part of a
  title: the four Global Underground city names, `L.I.F.E. (Love Is for Ever)`,
  `The Death of Slim Shady (Coup de Grâce)`, two `(Live)` records, two
  `(DJ Mix)` records and the Django Reinhardt date range.
- 4 pairs collapse into one key; none is a rule failure: two differ only in
  capitalisation, which `comparison_key` already folds; two are a standard
  edition beside a deluxe or remastered one, which is the intended behaviour.
- The terminal-word rule earns its place: without it, `Tenth Anniversary
  Edition`, `Special Collector's Edition`, `Deluxe Experience Edition` and
  `International Version` were all kept, each for one unlisted word.
- The type-marker rule earns its place: four held titles carry `- EP` or
  `- Single`, each of which would have been a false gap.
- **The inverse design was tested and rejected on this evidence.** Stripping any
  trailing segment unless it names a different recording would have destroyed
  `Love Is for Ever`, `Coup de Grâce`, the four city names and the date range.
  An allowlist it stays.

**What the rule does not do**, so it is not mistaken for covered: it does not
fold `&` to `and` and it does not strip diacritics, because `normalise` keeps
both deliberately and no miss caused by either has been observed. It is also
untested against titles as MusicBrainz spells them, which needs a live run; that
is one more reason the smallest genres are run first.

## 4. Prioritisation

Must: FR-D01 to FR-D14, FR-D16 to FR-D24, FR-D27 to FR-D44 and every NFR except
NFR-PERF-002.
Should: FR-D15, NFR-PERF-002.
Could: nothing this stage.

Won't, this time, recorded so it is not re-proposed: any purchase path; ranking
candidates by anything beyond what a source states; remembering across runs what
was offered and rejected; reopening a past run's results from the menu, which
FR-D28 makes cheap to add later and which nobody has asked for yet.

## 5. Open questions

Nothing marked open may be built from. Each is Oliver's unless stated.

| # | Question | Owner |
|---|---|---|
| OQ-04 | What does deduplication actually reduce the 3,270 candidate genre lookups to? Measurable only by a real run. | measurement, after first build |
| OQ-07 | RESOLVED 2026-09-08. Oliver ruled that no fallback is needed; the similarity half depends on the labs endpoint as it stands. Read in `application/discovering.py` on the same day: a refusal raises `SourceFailed`, which is caught for the one artist it happened to, recorded against that artist and written into the discovery file, so the rest of the run carries on regardless. | Answered |

## 6. The build order this implies

Inside out; no user-visible action waits on a screen to be exercisable.

1. **Domain**: the gap rules. What counts as held, what a candidate is, how the
   ticked genres filter both ends. Pure, unit tested against fabricated
   libraries with no source and no library present.
2. **Application**: the discovery service and the two source interfaces, driven
   in tests by hand-written fakes with error injection for every `If` sibling
   above.
3. **Infrastructure**: the two HTTP clients, the pacing, the retry, the JSON
   writer and the candidate genre cache.
4. **UI**: the toolbar button, the dialog and the progress reporting, last.

The diagnostic that says the foundation is sound: a whole run must be executable
from a test with a fabricated library and fake sources, producing an asserted
file, before the dialog exists at all. If it cannot be driven that way, the
dialog is not the missing piece.
