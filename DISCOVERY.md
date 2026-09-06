# Discovering music the library does not hold

The specification for the first stage of PLAN.md milestone 2. It is written
before any code, because the milestone was explicitly undesigned and a feature
generated from a loose description is a feature debugged rather than built.

Nothing here is implemented yet. Where this document and the code disagree once
work starts, this document is amended rather than quietly diverged from.

## 1. Introduction

### 1.1 Purpose

Stellody knows what somebody owns. It knows nothing about what they might want
next. This adds one thing and no more: a run that reads the library, asks two
public catalogues what is missing around it and writes the answer down as data.

### 1.2 Scope

In scope: a toolbar button, a dialog carrying the genre catalogue, a run that
looks up the artists inside the ticked genres and a JSON file holding what it
found.

Out of scope, stated first so it is a past decision rather than a future
argument:

- **Buying anything.** Reaching a shop is stage three of the milestone and is
  not designed.
- **Showing the results on screen.** The output of this stage is a file. A
  results view is a later stage and would be built from that file.
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

- `PLAN.md` milestone 2, which this stage is the first third of.
- `ARCHITECTURE.md`, whose layering and purity invariants govern every
  requirement here.
- MusicBrainz API and its rate limiting document.
- ListenBrainz API, including the labs similar-artists endpoint.

## 2. Overall description

### 2.1 Product perspective

An addition to an existing application, taking the fourth outward-reaching
module after the cover chooser and the update check. It is a client of the
application layer exactly as every other dialog is.

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
| A-01 | MusicBrainz and ListenBrainz remain reachable without a key. | Oliver | before release |
| A-02 | The ListenBrainz similar-artists endpoint, which sits under `labs`, is stable enough to depend on. | Oliver | before release |
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

Requirement: The main window shall place a discovery button in the toolbar after
the separator and to the left of the theme button.

Rationale: Discovery is a library action rather than a sound control; the separator is already the line between those two ideas.

Acceptance: Given the main window is open, when the toolbar is read left to
right, then the buttons after the separator are discovery, theme, help in that
order.

Verified by: `tests/ui/test_toolbar.py::test_discovery_sits_before_the_theme_button`

---

**FR-D02 The ring follows the button**

Priority: Must

Requirement: The main window shall include the discovery button in the keyboard
ring in its visual position.

Rationale: A control that cannot be reached by keyboard is a control half the
application's users do not have.

Acceptance: Given focus is on the button left of discovery, when Tab is pressed,
then focus is on the discovery button.

Verified by: `tests/ui/test_ring_order.py::test_discovery_is_reachable`

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

Requirement: While a run is under way, the discovery dialog shall show the name
of the artist currently being looked up, the number of artists completed and the
number to be done.

Rationale: A run over the whole library takes about eleven minutes at the rate
the sources permit. A spinner over eleven minutes is indistinguishable from a
hang.

Acceptance: Given a run over three source artists, when the second is reached,
then the dialog shows that artist's name and a count of one completed of three.

Verified by: `tests/ui/test_discovery_dialog.py::test_progress_names_the_artist`

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

Acceptance: Given a run in progress over an existing discovery file, when cancel
is pressed, then no further request is issued, nothing of that run is retained
and the existing file is byte for byte what it was.

Verified by: `tests/application/test_discovery.py::test_cancel_stops_before_the_next_request`

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

Verified by: `tests/infrastructure/test_discovery_file.py::test_shape_of_the_written_file`

---

**FR-D19 The file cannot be written**

Priority: Must

Requirement: If the discovery file cannot be written, then the discovery dialog
shall report the failure with the path it tried while leaving any previous file untouched.

Acceptance: Given a destination that refuses writes, when a run completes, then
the failure is reported naming the path and the previous file is unchanged.

Verified by: `tests/infrastructure/test_discovery_file.py::test_failed_write_keeps_the_old_file`

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

**FR-D23 One run at a time**

Priority: Must

Requirement: While a run is under way, the discovery dialog shall keep its action
button disabled.

Rationale: Two runs racing would double the request rate, breaching NFR-PERF-001
against both hosts, then race each other to replace the same file. Found by the
silence check rather than by anybody asking for it.

Acceptance: Given a run in progress, when the action button is examined, then it
is disabled; when the run ends, then it is enabled again.

Verified by: `tests/ui/test_discovery_dialog.py::test_a_second_run_cannot_start`

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

Verified by: `tests/application/test_discovery.py::test_closing_stops_the_run`

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

Verification: measured once against the real sources before release, recorded
here with the date.

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
the three things the file carries beside the results: the artists that could not
be resolved (FR-D08), the ambiguous ones (FR-D09) and the failures (FR-D22).

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
  tribute, score, soundtrack.

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

Must: FR-D01 to FR-D14, FR-D16 to FR-D24 and every NFR except NFR-PERF-002.
Should: FR-D15, NFR-PERF-002.
Could: nothing this stage.

Won't, this time, recorded so it is not re-proposed: an on-screen results view;
any purchase path; ranking candidates by anything beyond what a source states;
remembering across runs what was offered and rejected.

## 5. Open questions

Nothing marked open may be built from. Each is Oliver's unless stated.

| # | Question | Owner |
|---|---|---|
| OQ-04 | What does deduplication actually reduce the 3,270 candidate genre lookups to? Measurable only by a real run. | measurement, after first build |
| OQ-07 | Is the ListenBrainz labs endpoint stable enough to depend on; does the similarity half need a fallback? | Oliver |

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
