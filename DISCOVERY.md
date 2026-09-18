# Discovering music the library does not hold

The specification for the first stage of discovering music the library does
not hold. It was written before any code, because the milestone was explicitly
undesigned and a feature
generated from a loose description is a feature debugged rather than built.

It is built. One diagnostic in section 6 is not yet met; that section says so.
Where this document and the code disagree, this
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
  genre cache NFR-PERF-003 requires and the catalogue memory FR-D46 keeps.

### 1.3 Definitions

One meaning per term, for the life of the document.

| Term | Meaning |
|---|---|
| **Catalogue genre** | A name in `stellody.domain.genres.GENRES`, main or style. |
| **Resolved genre** | An album's genre as the library shows it: the probed tag with any album edit laid over it. Never the raw `sources.genre` column. |
| **Ticked genres** | The catalogue genres selected in the discovery dialog. |
| **Source artist** | An artist a run looks up. For a held album whose resolved genre names at least one ticked genre: its album artist; for a compilation, only while compilations are included, each track credit on it instead. Never "Various Artists" itself. |
| **Compilation** | A held album whose album artist names various artists rather than a person, as `AlbumIdentity.is_compilation` decides. |
| **Track credit** | One of a track's artists, split exactly as the library splits them for playback. |
| **Candidate album** | An album a source gives for a source artist that the library does not hold. |
| **Candidate artist** | An artist a source gives as similar to a source artist, whom the library does not hold. |
| **Release key** | The value two albums are judged the same album on, defined in section 3.5. The title alone, normalised, with edition qualifiers removed and the year deliberately absent. |
| **Discovery run** | One press of the action button, from first request to whichever of its four endings it reaches: completed, nothing to ask, stopped or unavailable. |
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

Two services are reached through ONE permitted module: neither catalogue client
holds a socket, both handing their questions to `infrastructure/fetching.py`.
Invariant 12 names four permitted modules rather than three, the fourth being
the local channel a second launch speaks to the running copy over, which was
found by this work rather than added by it.

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
- **C-05** Modules stay at or below 400 lines; a file in the 381 to 400 band
  is reduced to 350 or below. Amended 2026-09-12: this said 399 while
  `tests/structural/test_loc.py` counts a file at the cap as inside the band.
- **C-06** Domain and application hold 100% branch coverage.
- **C-07** No credential of any kind is compiled into the application, so no
  source requiring an API key may be used. This is what rules out Discogs and
  Last.fm; see the source comparison in section 3.3.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | RESOLVED 2026-09-08. A run over Blues and Folk against the live services returned artists, albums and similar artists, with no credential anywhere in the application. | Oliver | Answered |
| A-02 | RESOLVED 2026-09-08, as far as one run can. The labs similar-artists endpoint answered for every source artist in that run. It is still a labs endpoint; OQ-07 settled that it gets no fallback anyway. | Oliver | Answered |
| A-03 | A listener accepts that a run names their source artists to two public catalogues. | Oliver | ruled 2026-09-06, accepted with genre scoping |

## 3. Requirements

Measured facts this rests on, taken from the library on 2026-09-06: 659 album
folders, 327 album artists, of which 326 are reachable by at least one catalogue
genre. Three folders carry no catalogue genre. The smallest genres hold one
artist; the largest, Rock, holds 107.

**An album naming no catalogue genre is not source material, whatever is
ticked.** Ruled by Oliver on 2026-09-09, so it is a past decision rather than a
future argument. Raised by a run over five albums that answered about three of
them: the two it passed over were single-file rips whose FLAC carried no GENRE
field and whose cue sheet carried no `REM GENRE`, so there was nothing to read
rather than something read wrongly. Ticking every genre still does not reach
them, since an album that names none is named by no tick. The answer is to
state a genre against the album, which the tag editor already does without
touching the file; the run then treats it exactly as a tagged one. Neither a
"not tagged" tick nor an untagged sweep under select-all is wanted.

### 3.1 Functional requirements

---

**FR-D01 Reaching the feature**

Priority: Must

Requirement: The main window shall place a discovery button in the toolbar to
the left of the appearance toggle, with the separator that divides the library
controls from the application controls to its right.

Rationale: Discovery is a library action rather than a control acting on the
application, so it belongs on the library side of that line. Amended on
2026-09-07, when both trays were ruled into groups by what each control acts on:
as first written this asked for a position to the left of the theme button,
which put it among the sound controls it is not one of. The separator is the
line between the two ideas; which side of it this sits on is the requirement.
The theme button was only ever a landmark for saying so. Amended again on
2026-09-16, when the volume and mute moved to the bottom strip: the line now
divides discovery from the appearance toggle and Help, which act on the
application.

**The File menu carries the same press.** Added on 2026-09-16, when every
picture button gained a menu entry: `Discover new music...` calls what the
button calls, so while a run is under way it stops that run as FR-D23 says of
the button. It is offered exactly where the button is enabled, read off the
button each time the menu opens.

Acceptance: Given the main window is open, when the toolbar is read left to
right, then the discovery button appears before the separator and before the
appearance toggle.

Verified by: `tests/ui/test_discovery_button.py::test_discovery_sits_left_of_the_appearance_toggle`, `tests/ui/test_menu_mirrors.py::test_an_entry_is_offered_exactly_where_its_button_is`

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

**The picture says what the words say.** It wears `select-all.png` at the size
every dialog control wears its artwork; clearing wears that same picture with
the shared negative mark laid over it at run time, never a second drawing. That
is the rule the discovery button and every switch at the foot of the window
already follow, so a change to the mark reaches all of them at once.

**It names its next press**, which is the convention both trays already follow
and the reason one control carries both meanings rather than two sitting side
by side. It is read off the boxes so that ticking the last genre by hand moves
it too, which a control remembering its own last press would get wrong.

It does not close, exactly as Clear in the filter dialog does not: sweeping and
then asking is two presses, while somebody who swept by accident has lost
nothing.

Acceptance: Given a dialog with nothing ticked, when the control is read, then
it offers to select all; when it is pressed, then every genre in the catalogue
is ticked, the dialog is still open and no run has started; when it is pressed
again, then nothing is ticked. Given every genre ticked by hand, then the
control offers to clear; given one then unticked by hand, then it offers to
select all again.

Verified by: `tests/ui/test_discovery_dialog.py::test_the_sweep_ticks_every_genre_in_one_press`, `tests/ui/test_discovery_dialog.py::test_a_second_press_clears_them_again`, `tests/ui/test_discovery_dialog.py::test_the_sweep_says_what_a_press_would_do`, `tests/ui/test_discovery_dialog.py::test_ticking_the_last_box_by_hand_moves_the_sweep_too`, `tests/ui/test_discovery_dialog.py::test_the_sweep_is_a_button_rather_than_a_tick_box`, `tests/ui/test_discovery_dialog.py::test_sweeping_leaves_the_dialog_open`, `tests/ui/test_discovery_dialog.py::test_the_sweep_wears_its_own_artwork_at_the_shared_size`, `tests/ui/test_discovery_dialog.py::test_clearing_wears_the_same_picture_struck_through`, `tests/ui/test_discovery_dialog.py::test_the_picture_goes_back_when_there_is_something_to_tick_again`

---

**FR-D05 Who a run asks about**

Priority: Must

Requirement: When a run starts, the discovery service shall take as its source
artists the album artists of every held album that is not a compilation and
whose resolved genre names at least one ticked genre. Where compilations are
included (FR-D51), it shall also take every track credit of each compilation
whose resolved genre names at least one ticked genre. It shall never take
"Various Artists" as a source artist.

Rationale: The resolved genre is what the listener sees and what they spent
their time stating. Reading the probed tag instead reports the library as it was
before any of that work, which was demonstrated on 2026-09-06 by a measurement
that did exactly this and reported 179 albums as untagged when the true figure
was three.

Amended on 2026-09-13, reported by Oliver: adding Global Underground: Adapt #6
changed nothing a run did, which he refused to believe and was right to.
Measured the same day: the rule read only the album artist, so the album
contributed "Various Artists" in place of the 24 credits on its tracks. That
name was already answered from memory, so four runs over four days each finished
in a quarter of a second with the same report. A name meaning nobody in
particular is never worth a request, so it is dropped whether or not
compilations are included.

Acceptance: Given an album whose probed tag names nothing and whose album edit
states Reggae, when Reggae alone is ticked, then that album's artist is a source
artist. Given a compilation in Reggae whose tracks credit Dilby and Tinlicker,
when Reggae is ticked with compilations included, then Dilby and Tinlicker are
source artists while Various Artists is not; with compilations left out, none of
the three is.

Verified by: `tests/application/test_discovery.py::test_sources_read_the_resolved_genre`, `tests/domain/test_stating_an_album.py::TestWhoADiscoveryAsksAbout::test_a_genre_stated_over_an_untagged_album_decides`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_is_asked_about_by_its_track_credits`, `tests/domain/test_discovery_gaps.py::test_a_compilation_left_out_asks_about_nobody`, `tests/domain/test_discovery_gaps.py::test_various_artists_is_never_a_source_artist`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_outside_the_ticks_is_not_asked_about`

---

**FR-D51 Compilations are included only when asked for**

Priority: Must

Requirement: The discovery dialog shall carry a tick box reading "Include
compilations (Various Artists)" between the genres and its buttons. It shall be
unticked the first time the dialog opens. After that it shall open as it was
last left; its state shall be handed to the run with the ticked genres.

Rationale: Ruled by Oliver on 2026-09-13. Measured from the tags of his library
that day: 21 compilations carry 348 distinct track credits, 314 of them never
looked up. Asking about them is a choice about how long somebody is prepared to
wait rather than a default, so it is offered and remembered rather than imposed.
It is still scoped by the ticked genres, also his ruling, since the ticks are
what keep a run naming a subset somebody chose.

Acceptance: Given the dialog opened for the first time, then the box is
unticked. Given it ticked, when Find is pressed, then the run is handed the
ticked genres with compilations included. Given the dialog left with the box
ticked, when it is opened again, then the box is ticked.

Verified by: `tests/ui/test_discovery_compilations.py::test_compilations_start_left_out`, `tests/ui/test_discovery_compilations.py::test_the_run_is_told_whether_compilations_are_included`, `tests/ui/test_discovery_compilations.py::test_the_choice_is_remembered_between_openings`, `tests/ui/test_discovery_compilations.py::test_the_box_is_a_stop_between_the_genres_and_the_buttons`

---

**FR-D52 The cost of including compilations is stated before a run**

Priority: Must

Requirement: Beneath the tick box of FR-D51, the discovery dialog shall state
how many track credits on compilations inside the ticked genres a run would
newly look up, with the minutes that adds at the request pace NFR-PERF-001
permits. It shall restate both whenever a genre is ticked or unticked. A credit
counts as newly looked up unless a run leaving compilations out would already
ask about it or the catalogue memory holds a standing answer for it.

Rationale: Ruled by Oliver on 2026-09-13: a tick box whose consequence is not
stated invites a run of unknown length. The minutes are arithmetic rather than a
prediction, which is what NFR-PERF-002 leaves standing: two paced requests to
identify an artist then read its releases, at 1.1 seconds each. A busy
catalogue, the candidates a run then narrows and the artists FR-D53 adds all
make a real run longer; the words name a busy catalogue and call the figure a
pace rather than a forecast.

Acceptance: Given compilations in a ticked genre crediting three artists nobody
has looked up, when the dialog shows, then it states three artists with the
minutes asking about them adds; given all three already looked up, then it
states that nothing new would be asked.

Verified by: `tests/application/test_compilation_cost.py::test_only_names_not_yet_looked_up_are_counted`, `tests/application/test_compilation_cost.py::test_an_answer_past_its_life_is_counted_again`, `tests/application/test_compilation_cost.py::test_a_credit_a_run_would_ask_about_anyway_costs_nothing`, `tests/application/test_compilation_cost.py::test_the_time_is_priced_at_the_permitted_pace`, `tests/ui/test_discovery_compilations.py::test_the_cost_follows_the_ticks`, `tests/ui/test_discovery_compilations.py::test_nothing_new_to_ask_says_so`

---

**FR-D53 A credit nobody is found under is asked about by its parts**

Priority: Must

Requirement: Where a track credit taken from a compilation reaches nobody in the
catalogue and names several artists joined by an ampersand or a comma, the
discovery service shall take each of those artists as a source artist in the
same run. That credit shall not then be reported as unrecognised; a part that
reaches nobody shall be. A part that is already a source artist shall not be
asked about twice.

Rationale: Ruled by Oliver on 2026-09-13. The whole credit is asked first
because an ampersand does not always join two people: Eli & Fur is one duo,
which split would be two names meaning nobody. It falls back to the parts
because a credit such as ODESZA & Bettye LaVette may reach nobody whole while
naming two artists a catalogue can each be asked about. An album artist is left
whole, since the name somebody filed an album under is theirs to decide.

Acceptance: Given a compilation credit "ODESZA & Bettye LaVette" the catalogue
does not know while it knows both artists, when the run asks, then ODESZA and
Bettye LaVette are each asked about and the credit is not reported as
unrecognised. Given "Eli & Fur" known whole, then no part of it is asked about.

Verified by: `tests/domain/test_text.py::test_a_credit_naming_several_artists_comes_apart`, `tests/domain/test_text.py::test_a_credit_naming_one_artist_has_no_parts`, `tests/application/test_discovering_compilations.py::test_an_unrecognised_credit_is_asked_about_by_its_parts`, `tests/application/test_discovering_compilations.py::test_a_recognised_credit_is_not_split`, `tests/application/test_discovering_compilations.py::test_a_part_nobody_knows_is_reported_unrecognised`, `tests/application/test_discovering_compilations.py::test_a_part_already_asked_about_is_not_asked_again`, `tests/application/test_discovering_compilations.py::test_an_album_artist_nobody_knows_is_not_split`

---

**FR-D06 No source artists**

Priority: Must

Requirement: If the ticked genres yield no source artists, then the window
shall say so in its status bar, make no request and write no file.

Rationale: Ticking a genre nothing in the library carries is an ordinary thing
to do; the library holds a worked example: one artist, Smetana, is reachable by
no genre at all.

Acceptance: Given a genre no held album names, when the action button is
pressed, then the status bar reports that nothing in the library matches, no
request is made and no file is written.

Verified by: `tests/application/test_discovery.py::test_no_sources_makes_no_request`, `tests/ui/test_discovery_wiring.py::test_nothing_to_ask_says_so`

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

Acceptance: Given an identity lookup returning two artists whose names both
match the source artist's name exactly on its normalised comparison key, when
the run completes, then that artist is reported ambiguous with both identifiers
named and no album request was made for them.

Verified by: `tests/application/test_discovery.py::test_ambiguous_name_is_reported`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_two_exact_matches_are_both_returned`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_ranked_near_miss_is_not_the_artist`

---

**FR-D10 Albums by an artist already held**

Priority: Must

Requirement: When a source artist has been identified, the discovery service
shall request the albums that artist made, including each album's stated genres.
The service puts at most 100 on a page (`GROUP_LIMIT` in
`infrastructure/catalogue.py`), so the next page is asked for only after a full
one: an artist who fits costs one request as always, while a larger
discography is read to its end, up to `MOST_PAGES` pages.

Acceptance: Given an identified source artist, when the run reaches their
albums, then one request is made carrying that artist's identifier and asking
for genres.

Verified by: `tests/application/test_discovery.py::test_albums_are_requested_with_genres`

---

**FR-D11 Never offering back what is owned**

Priority: Must

Requirement: When albums are received for a source artist, the discovery service
shall discard every album whose release key and secondary types match those of
an album the library already holds by that artist, as section 3.5 defines them.

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

Rationale: Ten was confirmed on 2026-09-06 as the shipped figure. It is a named
constant (`SIMILAR_WANTED` in `application/discovering.py`) rather than a
literal, since it is a decision about how much to offer rather than a fact about
anything.

The endpoint takes no count, so the ten are taken at the client: the request
carries the identifier and the algorithm, the answer arrives already ranked and
`ListenBrainz.similar_to` in `infrastructure/similarity.py` keeps the first ten
it can name.

Acceptance: Given an identified source artist, when the run reaches similarity,
then one call is made to the similarity source carrying that artist's
identifier and a count of ten, which the client applies to the ranked answer.

Verified by: `tests/application/test_discovery.py::test_similar_artists_are_requested`

---

**FR-D13 Never offering back an artist held**

Priority: Must

Requirement: When similar artists are received, the discovery service shall
discard every artist whose normalised name matches the album artist of an album
in the library. An artist credited only on tracks does not count as held.

Acceptance: Given a similar-artists response naming two artists in the library
and eight not, when the run completes, then that source artist carries eight
candidate artists.

Verified by: `tests/domain/test_discovery_gaps.py::test_held_artists_are_dropped`

---

**FR-D14 The ticked genres filter what is collected**

Priority: Must

Requirement: When a candidate album states a genre that Stellody's genre
catalogue recognises, the discovery service shall discard it where none of the
genres it recognises is a ticked genre.

Rationale: Ticking Folk and receiving that artist's spoken-word record is the
filter failing at the only end that matters to the listener.

Acceptance: Given Folk is ticked and a candidate album states only Comedy, when
the run completes, then that album does not appear.

Verified by: `tests/domain/test_discovery_gaps.py::test_candidate_albums_respect_the_ticks`

---

**FR-D15 A candidate whose genre is unknown**

Priority: Should

Requirement: Where a candidate states no genre that Stellody's genre catalogue
recognises, whether it states none at all or only names that catalogue does not
know, the discovery service shall keep it; `ReleaseGroup.states_no_genre` then
reads true for it.

Rationale: Dropping what a source failed to describe would silently narrow the
result to the well-catalogued, which is the opposite of finding what is missing.
Marking it lets a later stage decide.

Acceptance: Given a candidate album carrying no genres, when the run completes,
then it appears and reads as stating no genre.

Verified by: `tests/domain/test_discovery_gaps.py::test_unstated_genre_is_kept_and_marked`

---

**FR-D16 Saying what is happening**

Priority: Must

Requirement: The toolbar shall carry one progress bar per stage of a run,
stacked in the order the stages happen and each labelled with the name of its
stage. While a run is under way each bar shall show how far through its own
stage the run is as a percentage; a stage that has finished shall be left full
and a stage that has not begun shall show no percentage at all. On hover the
pair shall name the stage and the artist currently being asked about, with that
artist's place in the stage (one more than the number completed) and the
stage's total.

Rationale: A run over the whole library has taken 54 minutes at the rate the
sources permit. A spinner over that long is indistinguishable from a hang.
Amended on 2026-09-07 after a measured failure: the dialog reported the first
half of a run only, so a run over Blues sat at 75% and silent for the whole of
the second half, which is the longer one. Both halves now report; they report to
the toolbar rather than to a dialog, since the dialog closes when the run
starts. The stage rather than the artist is drawn, because a strip of a toolbar
does not hold "Jools Holland & His Rhythm & Blues Orchestra".

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
before issuing its next request, discard the gaps that run had gathered and
leave any existing discovery file untouched. What the catalogues answered along
the way is kept rather than discarded, as FR-D48 requires.

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
twenty second timeout and may be attempted twice, so a run consulted once an
artist could go on for minutes after being told to stop. The waits between
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
is pressed, then no further request is issued, none of that run's gaps is
retained, every answer it had already been given is kept and the existing file
cannot be replaced by that run's report; given the run is waiting out
a refusal when cancel is pressed, then it stops within one slice of that wait
rather than at the end of it; given a cancel arrives between two of the three
requests made about one artist, then the remaining two are never issued; given
a run is wedged inside a request that will not answer at all, then the stop
still returns at once, the window is free to start another and that request is
dropped rather than left to reach its timeout.

Verified by: `tests/application/test_stopping_a_run.py::test_cancel_stops_before_the_next_request`, `tests/application/test_stopping_a_run.py::test_a_stop_is_felt_part_way_through_a_wait`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_request_nobody_wants_any_more_is_dropped_at_once`, `tests/infrastructure/test_discovery_sources.py::TestHandingTheQuestionDown::test_every_question_carries_whether_it_is_still_wanted`, `tests/application/test_stopping_a_run.py::test_a_stop_lands_between_requests_rather_than_between_artists`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_what_was_learned_is_kept_however_the_run_ended`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

---

**FR-D18 The output**

Priority: Must

Requirement: When a run completes, the discovery service shall replace the
single discovery file, whose `gaps` object is keyed by source artist with each
value holding that artist's candidate albums and candidate artists. Beside
`gaps` the file carries the artists left unresolved, ambiguous or failed and the
genres the run was scoped to.

Rationale: A file rather than a screen, because this stage exists to produce the
resource the later stages consume. One file replaced rather than a directory of
dated ones, ruled on 2026-09-06: a run states what is missing now, while a merge
would have to decide what becomes of a candidate offered last month that is
owned today.

Acceptance: Given a completed run over one source artist with two candidate
albums and three candidate artists, when the file is read, then its `gaps`
object holds one key naming that artist, with two albums and three artists
beneath it.

Verified by: `tests/infrastructure/test_discovery_file.py::test_the_file_is_keyed_by_the_artist_it_was_found_for`

---

**FR-D19 The file cannot be written**

Priority: Must

Requirement: If the discovery file cannot be written, then the window shall
report the failure in its status bar with the reason, while leaving any previous
file untouched.

Acceptance: Given a destination that refuses writes, when a run completes, then
the failure is reported with the reason and the previous file is unchanged.

Verified by: `tests/ui/test_discovery_wiring.py::test_a_file_that_will_not_write_is_reported`, `tests/infrastructure/test_discovery_file.py::test_nothing_is_left_half_written`, `tests/infrastructure/test_discovery_file.py::test_a_write_that_fails_leaves_the_last_answer_as_it_was`

---

**FR-D20 The network is not there**

Priority: Must

Requirement: Where a request is answered with nothing at all, the discovery
service shall put that artist back for a later pass exactly as a refusal does;
it shall report an artist nothing ever answered about in words distinct from a
refused one. Only where five requests in a row are answered with nothing at
all, with nothing whatsoever answering in between, shall it stop the run,
report that the network is unavailable and write no file.

Rationale: Continuing through 327 artists that will each fail is 327 ways of
saying the same thing slowly, so a connection that has gone still ends a run.
What changed on 2026-09-09 is what counts as proof that it has: reported by
Oliver after leaving a run going overnight, a run of fifty minutes ended on
its first such answer, which was one ListenBrainz request closed after 64
milliseconds. Measured from that night's diary, it was the only one in 7252
lines. One dropped socket is not a dead connection; five questions in a row
met with nothing, while nothing else answers, is. Being sure is cheap: the run
paces itself at about a second a question, so being wrong five times over
costs seconds.

One cause of such an answer was the run's own doing and was removed on
2026-09-09 rather than counted more carefully. Connections are pooled between
requests; the pause between passes is longer than the host keeps one, so the
first ask of every pass went down a socket the host had already closed. That
is the same artist every pass, so a run could go round twelve times and lose
them each go. A connection idle longer than half the host's measured idle
timeout is now thrown away rather than asked down.

The count is kept for the whole run rather than for either half of it, since
the connection is one thing. In the second half, a candidate the catalogue gave
no answer about is left unknown rather than written down as playing nothing,
whether nothing answered, a refusal outlasted the asks, the service answered
with an error or a stop abandoned the request: a question that was never
answered is not an answer; recording one would drop that candidate from every
later run without anybody having decided anything. An empty list of genres the
catalogue did give is an answer and is kept.

Acceptance: Given one request answered with nothing, when the run is observed,
then that artist is asked about again on a later pass and the run finishes;
given an artist nothing ever answered about, then it is reported in its own
words rather than as refused; given five such answers in a row, then the run
stops there, reports unavailability and writes no file; given an answer
between two of them, then the count starts again.

Verified by: `tests/application/test_a_dropped_connection.py::test_one_dropped_connection_does_not_end_a_run`, `tests/application/test_a_dropped_connection.py::test_a_connection_that_has_gone_still_ends_the_run`, `tests/application/test_a_dropped_connection.py::test_an_answer_between_two_silences_starts_the_count_over`, `tests/application/test_a_dropped_connection.py::test_an_artist_nothing_ever_answered_about_says_that`, `tests/application/test_discovery_narrowing.py::test_a_candidate_nothing_answered_about_is_left_unknown`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_did_not_answer_is_not_remembered`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_answered_with_no_genres_is_remembered`, `tests/application/test_discovery_narrowing.py::test_a_connection_lost_in_the_second_half_ends_the_run`, `tests/infrastructure/test_a_closed_connection.py`

---

**FR-D21 The source refuses**

Priority: Must

Requirement: If a source refuses a request, then the discovery service shall
ask again once on the spot; failing that, it shall put that artist back for a
later pass rather than discarding them. It shall make further passes over the
artists still owed an answer until either none is owed, two passes running
achieve nothing or twelve passes have been made. An artist still owed an answer
then shall be reported as a failure in the words of what happened to it on its
last pass: refused where the source refused it, otherwise as FR-D20 and FR-D50
word it.

Rationale: A refusal is the source asking for patience, not reporting that the
data is absent.

The patience is spent on a pass rather than on an artist. Measured on
2026-09-08 over Oliver's whole library: MusicBrainz refused 45 of 82 asks,
saying in its own words that its web server was busy. A run that waited each
refusal out where it stood spent nine seconds a request against a pace of
1.1 seconds. That run reported three hours remaining. Waiting where you stand
costs a minute an artist; waiting during the next artist's turn costs nothing,
while each pass is smaller than the one before it.

Two passes running that achieve nothing is where it stops, because a service
that is busy for a spell is worth another pass while one that is down stays
down. Twelve is a safety net rather than a plan, since passes that are getting
anywhere shrink geometrically and finish long before it.

Acceptance: Given a source refusing once then answering, when the run
completes, then that artist's results are present; given a source refusing an
artist throughout one pass and answering on the next, then that artist's
results are present; given a source refusing everybody on two passes running,
then the run stops asking and reports those artists as refused.

Verified by: `tests/application/test_discovery.py::test_rate_refusal_is_retried`, `tests/application/test_discovery.py::test_an_artist_refused_on_one_pass_is_asked_about_on_the_next`, `tests/application/test_discovery.py::test_a_refusal_that_never_relents_becomes_a_failure`, `tests/application/test_passing.py`

---

**FR-D50 The source is still thinking when the wait runs out**

Priority: Must

Requirement: Where a request has not been answered by the time the wait runs
out, the discovery service shall put that artist back for a later pass exactly
as a refusal does; it shall not count the wait running out towards the run of
silences FR-D20 ends a run on. It shall report an artist too slow to answer on
every pass in words distinct from a refused one and from one nothing answered
about. In the second half, a candidate whose genres were not answered for in
time shall be left unknown rather than written down as playing nothing.

Rationale: Reported by Oliver on 2026-09-09: a run over an installed copy
produced no data at all. Measured against MusicBrainz the same day, ten
identical searches paced at the rate its own terms ask for, the time to the
first byte was 0.15 seconds seven times, then 3.6, 12.7 and 26.3 seconds. So
the twenty second wait is exceeded by the service ANSWERING, one ask in ten
in that sample; the second ask about the same artist came back in a tenth of a
second. That was recorded against the artist as a failure of its own, which
ends that artist for the whole run. On a library holding three source artists
it was the difference between an answer and an empty screen.

A slow service is a loaded service, which is what a refusal says in words, so
it is answered the same way and for the same reason: the waiting is spent on a
pass rather than on an artist. It is not counted as silence
either. The fetcher gives up on any request still unanswered when the wait runs
out, whether or not the host ever accepted the connection, so a host that never
took the connection is counted as slow too. Counting a wait running out as
silence would let five slow answers in a row claim the network had gone.

Acceptance: Given a request that runs out of time once then answers, when the
run completes, then that artist's results are present and no failure is
reported; given five such answers in a row, then the run still completes;
given an artist too slow on every pass, then it is reported in its own words;
given a candidate whose genres ran out of time, then nothing is written down
about them.

Verified by: `tests/application/test_a_slow_answer.py`

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
where it found nothing. An artist whose earlier answer the discovery file
carries over (FR-D46) has a usable answer and is not counted.

Rationale: FR-D22 records the failures, `Gathering` in
`application/gathering.py` records the other two and the file has carried all
three since; nothing read them back, so a run that could not answer for a third
of a library said exactly what a clean one said. That is
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
holding a failure, then it says only that it was stopped; given a completed run
whose only failure is an artist the file already held an answer for, then the
message names no shortfall and no button is offered.

Verified by: `tests/ui/test_shortfall.py::TestTheSentence`, `tests/ui/test_discovery_wiring.py::test_a_run_names_all_three_kinds_of_silence`, `tests/ui/test_discovery_wiring.py::test_only_the_groups_that_happened_are_named`, `tests/ui/test_discovery_wiring.py::test_finding_nothing_still_says_what_went_unanswered`, `tests/ui/test_discovery_wiring.py::test_a_stopped_run_counts_nothing`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

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
several hundred names would be unreadable at the length that matters; the names
are also the half somebody can act on: a misspelt tag is only fixable once it
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

Verified by: `tests/ui/test_shortfall.py::TestTheButtonLabel`, `tests/ui/test_shortfall.py::TestTheList`, `tests/ui/test_shortfall.py::TestTheDialog`, `tests/ui/test_discovery_wiring.py::test_the_button_appears_carrying_its_own_count`, `tests/ui/test_discovery_wiring.py::test_one_unanswered_artist_reads_as_one`, `tests/ui/test_discovery_wiring.py::test_a_clean_run_offers_no_button`, `tests/ui/test_discovery_wiring.py::test_a_new_run_takes_the_last_one_s_button_away`, `tests/ui/test_discovery_wiring.py::test_pressing_it_opens_the_names`, `tests/ui/test_dialog_first_stop.py`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

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

Requirement: If the application is asked to quit while a run is under way, then
the window shall tell the run to stop before its next request, then wait for it
and for every run abandoned earlier to end, allowing each at most thirty
seconds, before the application ends; the stopped run shall leave any existing
discovery file untouched.

Rationale: The same ruling as a cancel, since a close is a cancel the listener
expressed differently. Found by the silence check.

Acceptance: Given a run in progress, when the application is quit, then the run
has been told to stop by the time the application's departure is called; given a
stopped run's report, then the discovery file refuses to be replaced by it.

Verified by: `tests/ui/test_quitting.py::test_quitting_mid_run_stops_the_discovery_run`, `tests/application/test_stopping_a_run.py::test_closing_stops_the_run`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

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
found to play and shall not ask about a candidate it already holds an answer
for.

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
"Discover music the library does not hold" again. Given a run that has just
been stopped, when a new run is asked for, then it starts at once; the stopped
run winds down on its own thread and reports to nobody.

The bar is let go of on the press rather than on the ending, because a run is
abandoned rather than waited for: a bar held until the run noticed would go on
reporting a run somebody had finished with. Reports arriving afterwards are
dropped for the same reason. They are not hypothetical: the run reports right
up to the moment it notices.

Verified by: `tests/ui/test_discovery_stopping.py::test_a_press_stops_at_once_without_asking_anything`, `tests/ui/test_discovery_stopping.py::test_the_button_wears_the_cross_while_a_run_is_under_way`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_is_stopped`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_finishes_on_its_own`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_fails`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/ui/test_discovery_stopping.py::test_progress_reported_after_a_stop_does_not_revive_the_bar`

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

Verified by: `tests/ui/test_opening_a_candidate.py::test_a_candidate_artist_starts_collapsed`

---

**FR-D31 A candidate artist's albums are fetched on demand**

Priority: Must

Requirement: When a candidate artist is expanded in the results dialog, the
results dialog shall show the releases that artist made which pass the offering
rule section 3.5 states, fetched at the moment of expanding rather than during
the run. Read a page at a time exactly as in FR-D10.

Rationale: Measured on 2026-09-07: one catalogue request costs at least the 1.1
second gap NFR-PERF-001 requires. Asking during the run would add a request for
every candidate surviving the genre filter, roughly doubling a second stage that
is already the longer half. Ruled by Oliver the same day: pay it only for the
ones somebody actually opens.

Acceptance: Given a collapsed candidate artist, when it is expanded, then that
artist's offered releases appear beneath it; given the run that produced the
file, then it issued no request about that artist's releases.

Verified by: `tests/ui/test_opening_a_candidate.py::test_expanding_a_candidate_asks_for_their_albums`, `tests/application/test_expanding.py::test_everything_that_artist_made_is_offered`, `tests/application/test_expanding.py::test_a_hits_package_is_still_noise`, `tests/application/test_discovery_narrowing.py::test_a_run_never_asks_what_a_candidate_released`

---

**FR-D32 The lookup for an expanded artist cannot be made**

Priority: Must

Requirement: The lookup for an expanded candidate artist shall be attempted
five times, the wait between attempts doubling each time, before it is reported
as having failed. If it cannot be fetched, then
the results dialog shall show what went wrong against that artist, shall say
that closing and opening the row tries again; it shall leave every other entry
as it was.

Rationale: The unwanted sibling of FR-D31. One artist nobody could look up is
not a reason to lose the rest of a run that took minutes to make.

Five attempts rather than the two a run gives an artist, reported by Oliver on
2026-09-08 when The Rolling Stones came back refused while every other artist on
the same screen answered. Measured the same day, that artist carries 1474
release groups at MusicBrainz and the request takes 15.6 seconds cold against
0.2 warm, so it is among the first things a busy service sheds. The two callers
can afford different amounts of waiting because of who is doing it: the thirty
seconds those five attempts span, measured on 2026-09-09 as two, four, eight
then sixteen, is a wait somebody who opened one row will sit through, where a
run of 327 artists cannot spend it on each of them.

The message says how to try again because trying again already worked and
nothing said so. A row that failed is asked about afresh the next time it is
opened, which is the behaviour FR-D31 gives it; somebody looking at the failure
had no way to know that.

Acceptance: Given a candidate artist whose lookup fails, when it is expanded,
then that artist shows what went wrong and says the row can be closed and
opened to try again; when another is expanded, then it still lists its releases;
given a service refusing three times running and answering on the fourth, then
the releases are shown rather than a failure.

Verified by: `tests/ui/test_opening_a_candidate.py::test_a_failed_expansion_says_so_and_spares_the_rest`, `tests/ui/test_opening_a_candidate.py::test_an_artist_that_failed_is_asked_again_the_next_time_it_is_opened`, `tests/application/test_expanding.py::test_three_refusals_running_do_not_lose_the_artist`, `tests/application/test_expanding.py::test_a_source_refusing_every_time_is_that_artist_failing`, `tests/application/test_expanding.py::test_the_wait_between_asks_doubles`

---

**FR-D33 Every completed run opens its answer**

Priority: Must

Requirement: If a discovery run completes, then the window shall write its
answer and open the results screen on what was written, whether or not the run
found any candidate album or candidate artist.

Rationale: This said the opposite until 2026-09-09, on the reasoning that an
empty dialog says less than the sentence shown in its place. Ruled the other
way by Oliver that morning, after two whole-library runs ended in one night
with nothing in front of him. A run of an hour reporting into the status bar
reports into a strip nobody is watching; a screen that opens says what the
run looked in and how many artists it could not answer about, which the
sentence alone does not carry. An empty screen is a poor screen; an hour of
work with nothing to show for it is worse.

Nothing missing IS an answer about the library rather than the absence of one,
so it replaces the file exactly as any other completed run does. What the
status bar says is unchanged, so this adds no requirement about it; FR-D16
already governs that.

Acceptance: Given a run that found nothing, when it completes, then its answer
is written and the results screen opens naming the genres it looked in.

Verified by: `tests/ui/test_results_dialog.py::test_a_run_that_found_nothing_still_shows_its_screen`, `tests/ui/test_discovery_wiring.py::test_a_run_that_found_nothing_still_writes_and_opens`

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
give the number of albums beneath it, with the number of similar artists where
there are any. A
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
source artist row with similar artists beneath it is read, then it gives both
counts; when a candidate row is
read, then it names itself a similar artist.

Verified by: `tests/ui/test_results_reading.py::test_the_key_names_all_three_kinds_in_their_own_colours`, `tests/ui/test_results_reading.py::test_a_source_row_says_how_many_of_each_sit_under_it`, `tests/ui/test_results_reading.py::test_a_candidate_row_says_that_it_is_an_artist`

---

**FR-D40 The results say when the catalogue is being asked**

Priority: Must

Requirement: While one or more candidate artist lookups are in flight, the
results dialog shall show a busy indicator naming the artist being asked about;
where there is more than one, it shall name the number of artists instead. The
indicator shall occupy its place whether or not anything is in flight, carrying
instead what to do to fetch an artist's albums.

Rationale: Reported by Oliver on 2026-09-07: opening an amber name left the
dialog doing nothing visible for several seconds, which reads as stuck. It is
not stuck. One lookup costs at least the gap NFR-PERF-001 requires and may wait
out four refusals before answering, so several seconds of quiet is the ordinary
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

**FR-D46 The same library answers the same way twice**

Priority: Must

Requirement: The discovery service shall keep what each catalogue answered,
against the question that was asked; it shall ask a catalogue for an artist's
identity, releases or similar artists only where that answer is not kept or was
kept more than thirty days ago; what a candidate plays is kept without a limit.
A run shall write down what it learned however that run ended. Where a run
cannot reach a source about an artist an earlier run answered for, the discovery
file shall keep the earlier answer and shall record no failure for that artist;
the run's closing message and its count of unanswered artists shall be read from
the answer as the file will hold it, so neither names that artist. Where a run
reaches its end still owing an answer about an artist nothing was ever known
about, the discovery file shall be written with that artist named as unanswered
rather than withheld. The gaps written shall be ordered by artist. Where two
holders of the memory save over one another, the file shall keep every answer
either of them learned, taking the later answer to any question both hold.

Rationale: Reported by Oliver on 2026-09-08, repeatedly and in the strongest
terms: two runs over the same library gave different answers, sometimes
holding an artist and sometimes not, sometimes able to look an artist up and
sometimes not.

A run remembered nothing, so it asked MusicBrainz about every artist afresh
every time and the answer was a property of how that service felt rather than
of the library. Measured that day from one run: 27 requests in 65 seconds, 21
of them refused, which turned seven source artists into one. More patience
helps and cannot fix it; it only changes how often the answer differs.

Thirty days is Oliver's own statement of what is wanted, on the same day: the
same run over the same library should differ over days or weeks, because the
catalogues themselves change; it should not differ over five minutes, because
they do not. A month is long enough that a run over a library asks nothing at
all most of the time, short enough that a record released this year is found
this year. A refresh that is refused costs nothing, since that artist is then
carried over from the file exactly as any other failure is.

A hole is written down rather than refused. Until 2026-09-09 an answer with
any hole in it was not written at all, on the ground that a file holding
whichever artists a service felt like answering about is a different file
every time. That reasoning was aimed at a file that stays SILENT about its
holes; the cost of taking it literally was measured that morning: over two
whole-library runs Oliver was shown nothing at all, the second time after 54
minutes, 843 requests and 327 artists, because ONE artist was refused twice
and then timed out. The answer now carries what could not be answered for
beside what was, the screen says how many artists are missing and names them;
the next run fills those in without asking about anybody else.

The order is by artist rather than by how the answer was arrived at, since an
artist carried over would otherwise sit where the carrying put it while the
same artist answered for directly sits in library order. The same content in
two orders is two different screens.

Carrying an earlier answer over is the second half, for the artist nothing has
ever been learned about, whose first answer arrives on the day a service
happens to be willing. A run may add to what is known and may correct it; it
may not take it away because a service said no. Only an artist this run failed
on is carried over, so an artist no longer in the library still falls away.

Saving lays a copy over what is known rather than writing it whole. A run, the
price of a run and the expansion behind an opened candidate each hold a copy of
the memory; two of them can be alive at once, as when a new run starts while a
stopped one winds down (FR-D27) or a candidate is opened while a run goes on.
Measured on 2026-09-18 against the real file: whichever copy saved last put the
memory back as it stood when that copy was taken, then cleared the running
record that held the rest. Each question now keeps whichever answer came later.
All three share one memory, so one lock covers both a save and any note that
would otherwise land between the save reading the file and clearing the record.

Acceptance: Given a library run over twice with the same genres, when the second
run finishes, then it asked the catalogues nothing and answered exactly as the
first did; given an artist an earlier run answered for and this one could not
reach, then the file still holds that artist and records no failure for it,
while the run's message counts nobody unanswered and no shortfall button is
shown; given an artist nothing has ever been learned about that this run could
not reach either, then the file is still written, holding what did answer with
that artist named among the failures, while the run says which artists it could
not answer about; given an answer kept more than thirty days ago, then it is
asked about again; given two holders of the memory that each learned something
the other did not, when both have saved, then the file holds both answers.

Verified by: `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_the_second_run_asks_the_catalogues_nothing`, `tests/application/test_remembering.py::TestAskingOnlyWhatIsUnknown`, `tests/application/test_remembering.py::TestHowLongAnAnswerStands`, `tests/application/test_remembering.py::TestCarryingAnAnswerOver`, `tests/infrastructure/test_discovery_file.py::test_an_answer_with_a_hole_in_it_is_written_with_the_hole_named`, `tests/infrastructure/test_discovery_file.py::test_an_artist_already_answered_for_is_not_a_hole`, `tests/infrastructure/test_discovery_file.py::test_the_artists_are_written_in_one_order_however_they_arrived`, `tests/ui/test_discovery_wiring.py::test_a_run_with_a_hole_in_it_still_opens_its_answer`, `tests/infrastructure/test_catalogue_memory.py::test_what_is_kept_comes_back_exactly`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`, `tests/application/test_merging_recollections.py`, `tests/infrastructure/test_overlapping_memory.py`, `tests/ui/test_discovery_composition.py::test_everything_keeping_catalogue_answers_shares_one_memory`

---

**FR-D48 An answer is written down the moment it arrives**

Priority: Must

Requirement: Each answer a run's catalogues give and each answer about what a
candidate plays shall be written to a running record as it arrives and forced to
the disk. An answer fetched when a candidate is opened on the results screen is
written straight into the memory file once that lookup ends. Both memories shall
be read as their file plus that record; each record shall be dropped only once
its own file has been written with what it held.

Rationale: Reported by Oliver on 2026-09-09, having left a run going overnight.
Both memories were read once when a run started and written once when it
ended, so everything a run had paid for lived in memory until the last
instant: a run of fifty minutes held 581 answers that a crash, a power cut or
a closed window would have taken in full. That is a run's whole cost held on a
single line of code being reached.

The record is appended rather than rewritten, because an append cannot damage
what is already in the file, so the worst a death mid-write can cost is the
line it was writing. It is forced to the disk rather than merely written,
since a buffered write is a record only the living process can see, which is
the one case this exists for. The whole file is still written at the end,
which is what keeps the record short; reading the two together is what makes
the file's lateness cost nothing.

The record is dropped only after its file has been written. Clearing it beside
a write that failed would throw away the very answers it exists to protect.

Acceptance: Given answers noted by a run that never finished, when a later run
starts, then it knows every one of them and asks about none of them; given a
record whose last line is half written, then every line before it is still
known; given a memory whose file cannot be written, then its record survives;
given a memory whose file is written, then its record is gone.

Verified by: `tests/infrastructure/test_a_dead_run_keeps_what_it_learned.py`, `tests/infrastructure/test_journal.py`, `tests/application/test_remembering.py::TestAnAnswerIsKeptTheMomentItArrives`, `tests/application/test_discovery_narrowing.py::test_each_candidate_is_written_down_as_it_is_answered`

---

**FR-D47 A failure is said in words somebody can act on**

Priority: Must

Requirement: Where a lookup fails, the results dialog shall say what happened
in plain words naming no address, no exception class and no status code; the
technical account shall be written to the diary instead.

Rationale: Reported by Oliver on 2026-09-08, shown a row reading "Could not be
looked up: given up on part way through" followed by a MusicBrainz address.
That line is unreadable to anybody who did not write the program; it is also
the only thing worth having to whoever has to fix it. Both are kept, apart:
the row says which of a busy service, a slow one, one that could not be
reached or something else it was; the diary keeps the class, the message and
the catalogue identifier of the artist it happened to.

The words are read off the KIND of failure rather than off its message, since a
message is written for whoever is fixing the program. That is why a service
that refused every ask and a service that ran out of time are now distinct
kinds: Qt reports an abandoned reply the same way whether the wait ran out or
somebody stopped wanting it; those are different things to say.

Acceptance: Given a lookup that fails for any reason, when the row is drawn,
then it names no address and no exception class; given a service that refused
every attempt, then the row says the catalogue is busy; given a wait that ran
out, then it says the catalogue did not answer in time; given anything else,
then it points at the log; and in every case the diary carries the class, the
message and the artist's catalogue identifier.

Verified by: `tests/ui/test_results_reading.py::TestSayingWhyInWords`, `tests/ui/test_expansion_worker.py::test_the_row_gets_words_and_the_log_gets_the_machine`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_service_that_never_answers_is_given_up_on_anyway`

---

**FR-D49 The answer is turned a page at a time**

Priority: Must

Requirement: The results dialog shall deal its source artists into pages, each
page filling EVERY one of its columns save the last page, which takes what is
left, where how deep a column is filled follows from the height of the dialog.
An artist taller than that depth shall fill its column and be scrolled rather
than dropped or divided; it shares its page wherever the page has more than one
column. It shall show one page at a
time with two controls beneath the answer, one for each direction, each
wearing its own artwork struck through where that direction leads nowhere;
between them shall stand words saying which page of how many is in front.
Those three shall stand on the SAME row as the controls that act on the ticks
and the one that closes the screen, immediately beneath the answer, rather
than on a row of their own above them. Every page shall be built when the
dialog opens and kept, so that an album ticked on one page is still ticked
after another has been looked at.

Rationale: Dealing the answer into columns fixed a run over two genres. A run
over a whole library answers with hundreds of source artists, so three columns
of it are three lists nobody reaches the end of: a scrollbar says how much is
left without saying where in the answer somebody is.

How deep a column is filled follows the height exactly as the columns follow
the width, so a laptop panel gets a shorter page rather than the same page
with more in it. The figure for what one row costs is stated rather than
measured; it cannot be measured here, since the offscreen platform reports no
font families at all, so every label draws at one fallback height. Being wrong
costs a page with room to spare at the foot or a column that scrolls a little;
it is never an error, so a figure checked on a real screen is how to correct
it.

Filling every column is Oliver's ruling of 2026-09-09, made against the first
paged run over his whole library: some pages drew three columns and others
drew one. The rule it replaced ended a page as soon as the next artist would
not fit in the shortest column, which sounds like it prevents scrolling and in
a real library prevents filling. Measured from that run's own answer: 215
artists whose heights run from 1 row to 109, with a median of 23 against a
column of 30. An artist taller than a column is the ordinary case, so the page
ended almost as soon as it began. Filling every column instead lets a column
holding a tall artist scroll, which is one artist's worth of scrolling rather
than the library's; it took that answer from 99 pages to 42 with every one
of them but the last carrying three columns.

Every page is built at once rather than on the way to it, because a tick is held
by the row it is on: a page rebuilt on return would quietly drop whatever was
ticked on it, where what is ticked is exactly what the shop controls beneath are
for. Nothing is fetched either way, since a page holds what the run has already
answered.

One row rather than two is Oliver's ruling of 2026-09-09, made against the
shipped screen: the pager stood above the row holding Copy, Find in shops and
Close, so the foot of the dialog read as two feet. The pager carries a stretch
on each side of itself, so standing it between the controls that act on the
ticks and the one that leaves is what centres it; no stretch is added beside
it, since a second would push it off centre. `ui/results_foot.py` builds that
row, extracted when the dialog reached the danger band.

The unusable direction is struck through rather than merely greyed, which is
the rule the sweep in the discovery dialog and every switch along the foot of
the window follow: a spent control says a press does nothing, while the cross
says which way is left to go. Both directions are struck through where there
is one page, so the pager holds its place rather than arriving with a long
answer and moving everything else on screen.

Acceptance: Given more source artists than a page holds, when the dialog
opens, then the first page is in front and the way back is struck through;
given the last page, then the way on is struck through; given an album ticked
on one page, when another page has been looked at, then it is still ticked and
still goes to a shop; given artists of any heights whatever, then every page
but the last carries every column; given an artist taller than a column, then
it fills one and shares its page; given a run that found nobody, then there is
still one page.

Verified by: `tests/ui/test_results_pages.py`, `tests/ui/test_shop_choosing.py::test_a_tick_holds_across_pages_and_still_reaches_a_shop`

---

**FR-D54 The answer can be narrowed to some of the genres the run looked in**

Priority: Must

Requirement: The results dialog shall carry a Filter control wearing the
library's filter artwork, offering only the genres the run looked in. While any
is picked, it shall show a source artist's albums only where the library holds
an album in a picked genre filed under that artist or crediting them on a
compilation. It shall show a candidate artist only where the candidate genre
cache records a genre for them naming a picked genre. A source artist with
nothing left to show shall not be shown. The control shall stay pressed in while
a filter is on; the pages shall be dealt again from what is shown. The filter
shall not be remembered between openings.

Rationale: Ruled by Oliver on 2026-09-13, after a whole-library answer ran to
5279 albums over hundreds of pages. His choice between two readings: a source
artist is judged by the genres he stated on his own albums, since FR-D05 means
every source artist holds one, so nobody he holds is ever withheld for want of a
genre. Judging each missing album by the catalogue's genre instead would have
withheld 2128 of those 5279, measured from his answer that day. A candidate is
not in the library, so the candidate genre cache (`artist-genres.json`) is all
there is to judge them by.

Acceptance: Given an answer holding a House source artist and a Rock one, when
House alone is picked, then only the House artist is shown and the pages are
dealt from them; when the filter is cleared, both are shown again.

Verified by: `tests/domain/test_discovery_filter.py::test_nothing_picked_shows_everything`, `tests/domain/test_discovery_filter.py::test_a_source_artist_shows_by_the_genres_held`, `tests/domain/test_discovery_filter.py::test_a_candidate_shows_by_its_remembered_genres`, `tests/domain/test_discovery_filter.py::test_an_artist_with_nothing_left_is_not_shown`, `tests/ui/test_results_filter.py::test_only_the_genres_looked_in_are_offered`, `tests/ui/test_results_filter.py::test_the_filter_stays_pressed_in_while_on`, `tests/ui/test_results_filter.py::test_the_pages_are_dealt_from_what_is_shown`

---

**FR-D55 What a filter withholds is said**

Priority: Must

Requirement: While a filter is on, the results dialog shall state how many
candidate artists are withheld because the candidate genre cache records no
genre for them that Stellody's genre catalogue recognises.

Rationale: Measured on 2026-09-13: 260 of 1112 candidates in Oliver's answer
have no remembered genre. A filter cannot judge them; rows that vanish without a
word read as rows that were never found.

Acceptance: Given two candidates with no remembered genre, when any genre is
picked, then the dialog says two are withheld; when the filter is cleared, then
it says nothing about withholding.

Verified by: `tests/domain/test_discovery_filter.py::test_candidates_with_no_genre_are_counted_as_withheld`, `tests/ui/test_results_filter.py::test_the_withheld_count_is_said_while_filtering`

---

**FR-D56 A filter never takes a tick away**

Priority: Must

Requirement: Changing the filter shall keep every tick, including a tick on a
row the filter withholds. Copy and Find in shops shall act only on ticked albums
currently shown.

Rationale: Ruled by Oliver on 2026-09-13. A tick is somebody's decision; a
filter is only where they are looking. Acting on rows out of sight would send
albums to a shop without anybody seeing they were going.

Acceptance: Given an album ticked, when a filter withholds it, then Copy leaves
it out; when the filter is cleared, then it is still ticked.

Verified by: `tests/ui/test_results_filter.py::test_a_withheld_tick_is_left_out_of_copy`, `tests/ui/test_results_filter.py::test_a_tick_survives_the_filter_being_cleared`

---

**FR-D57 The chooser's Filter waits for a tick**

Priority: Must

Requirement: While no genre is ticked in the chooser FR-D54 opens, its Filter
control shall be disabled, unless the chooser opened with a filter on.

Rationale: Reported by Oliver on 2026-09-13: the chooser offered Filter with
nothing ticked, as though there were something to filter by. With nothing
ticked the press can only take a filter off, which is a change where one was on
and nothing where none was. The exception keeps the only way a filter is taken
off, since Cancel keeps it.

Acceptance: Given the chooser opened on no filter, when nothing is ticked, then
Filter is disabled; when a genre is ticked, then it is enabled; when Clear is
pressed, then it is disabled again. Given the chooser opened on a filter, when
Clear is pressed, then Filter is still enabled.

Verified by: `tests/ui/test_filter_controls.py::test_filtering_waits_for_a_tick`, `tests/ui/test_filter_controls.py::test_clearing_every_tick_takes_filtering_away_again`, `tests/ui/test_filter_controls.py::test_a_filter_already_on_can_still_be_taken_off`

---

**FR-D45 The answer is dealt across the width of the screen**

Priority: Must

Requirement: The results dialog shall open at nine tenths of the screen it opens
on, never below 700 by 560 and never above 1920 by 1080. It shall deal the
source artists across as many columns as that width affords, never more than
three, a column being a third of the width it opens at on a real 13 inch
display, each a list read top to bottom. Artists shall be dealt to the shortest
column at the time, counting an artist's height as its own row plus one for each
album and each candidate under it. A column shall be built only where an artist
landed in it; a run that found nobody shall still show one. One selection shall
stand across the columns.

Rationale: Reported by Oliver on 2026-09-08 against a run over two genres,
which already ran off the foot of the screen with the room to show it sitting
empty either side. A run over a whole library answers with hundreds of source
artists carrying albums and candidates under each, so a single list is a shape
nobody reaches the end of whatever height it is given.

The ceiling is his ruling of the same day: no bigger than a 13 inch display can
show, taken then as 1920 by 1080 and kept at that. Nine tenths of a 3440 monitor
is 3096 pixels of dialog, which is a window nobody reads across in one go; it is
also a shape that cannot be checked on the machines this has to run on, so a
defect at that width would only ever be found by the one person with that
screen.

The share is of the screen the dialog opens on only because its native window
exists before it is sized. Measured on 2026-09-16 on a 3440 wide primary beside
13 inch panels at 250% and 300%: a dialog sized before its window existed
opened at its width times the panel's scale wherever that product passed the
primary's width, so the results screen opened across every display. Every
dialog now makes its window first, in `FirstStopDialog` (`ui/dialogs.py`),
except on Wayland, where doing so corrupts the window behind it.

Dealt by height rather than in equal counts because one artist can carry fifteen
albums while the next carries one, so a count-by-count fill leaves one column
twice the length of another. It is the rule the genre grid already deals its
groups by, which is why that helper reads as it does.

The column width is not a number of its own: it is the width the dialog opens at
on a real 13 inch display divided by the three columns that display is meant to
show, so there is one decision to argue with rather than two that can disagree.
Three is Oliver's ruling of 2026-09-08 on seeing the first two-column screen.
Amended on 2026-09-17: the width was the 1920 pixel ceiling divided by three,
640 pixels, which a 13 inch 4K panel at 300% cannot fit three of, so Oliver saw
one column at the far left. Qt reports that panel as 1422 by 836 with the
interface drawn at nine tenths, so the dialog opens 1279 wide there and a column
is 426 pixels; measured on that panel, three columns of 411 pixels drew with no
sideways scrolling. The price, accepted by Oliver the same day, is the longest
rows: at 5.5 to 6.0 pixels a character, measured on 2026-09-08, the longest row
this library produces is about 450 pixels, so it is cut short with an ellipsis
rather than drawn whole. A wide monitor would now have room for a fourth column,
so three is also the most any screen shows. None of this could be measured in
the suite, where the offscreen platform reports no font families at all and
every size draws the same width. One selection across the columns for the reason
the album pane shares one across its tracks: a highlight per column says a
reader is in two places at once. What a press acts on is the ticks, which is
unchanged.

Acceptance: Given a screen wide enough that nine tenths of it holds two column
widths, when the dialog opens, then the source artists are drawn over two or
more lists side by side and each artist appears exactly once; given a screen at
the floor, then one list is drawn as before; given a 3440 monitor, then the
dialog opens no wider than 1920 pixels and shows three columns; given a 13 inch
display at 300% reported as 1422 by 836, then three columns are drawn; given
fewer artists than the width affords columns, then no empty column is built;
given a row chosen in one column, then any selection in the others is cleared.

Verified by: `tests/ui/test_results_columns.py::TestHowMuchRoomItTakes::test_a_wide_monitor_gets_no_more_than_a_13_inch_display`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_three_is_the_ruling_rather_than_whatever_the_constant_says`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_the_13_inch_ceiling_affords_the_three_that_were_asked_for`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_real_13_inch_display_shows_three`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_wide_monitor_shows_three_and_no_more`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_every_artist_lands_in_exactly_one_column`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_it_deals_by_height_rather_than_by_count`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_it_builds_what_the_width_affords`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_fewer_artists_than_columns_builds_no_empty_column`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_a_run_that_found_nobody_still_gets_a_screen`, `tests/ui/test_results_columns.py::TestOneSelectionAcrossThem::test_choosing_in_one_column_clears_the_others`, `tests/ui/test_results_columns.py::TestWhatIsTickedAcrossThem::test_the_ticks_are_read_from_every_column`, `tests/ui/test_results_size.py`, `tests/ui/test_dialog_first_stop.py::test_every_dialog_has_its_window_before_it_is_shown`

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
with nothing on screen saying whether that was normal. The pacing arithmetic
puts a whole library at about twelve minutes for the first stage alone. Somebody
who cannot tell a long run from a hang closes the window, which throws the run
away.

The second place was added the same day, on his report that the estimate could
not be found. It was in the status bar as this required, which is the foot of a
window whose discovery bar is at the top: somebody watching a percentage climb
never meets a sentence at the other end of the window. The bar is a strip 170
pixels wide, so what it carries is "4m" rather than the sentence; the room for
it is taken out of the bar before the stage name is centred in what is left. One
reading of the pace answers both, else the two could be taken a moment apart and
disagree across a rounding.

Acceptance: Given a run under way with an estimate available, when the status
bar is read, then it names a whole number of minutes or says less than a
minute; when the discovery bar is read, then its right hand end carries the
same estimate abbreviated, drawn clear of the stage name.

Verified by: `tests/ui/test_run_estimate.py::TestNamingTheTimeLeft::test_the_status_bar_names_the_time_left`, `tests/ui/test_discovery_bar.py::test_it_writes_how_long_is_left_at_the_right_hand_end_of_the_moving_bar`, `tests/ui/test_discovery_bar.py::test_the_time_and_the_stage_are_never_drawn_over_each_other`, `tests/ui/test_discovery_bar.py::test_the_time_is_actually_drawn_on_the_bar`

---

**FR-D36 The estimate is taken from the run itself**

Priority: Must

Requirement: The window shall derive the estimate from the time the run has
actually taken for each unit of work finished, rather than from the request gap
NFR-PERF-001 states.

Rationale: A run meets refusals; each costs a second ask on the spot as FR-D21
requires, then a place in a later pass, so what a refusal costs is not the gap.
An estimate built on the configured gap would read as confident while being
wrong by minutes on exactly the runs where somebody most needs it.

Acceptance: Given a run whose finished units took twice the gap apiece, when the
estimate is computed, then it follows the observed pace rather than the
configured one.

Verified by: `tests/domain/test_estimating.py::TestThePace::test_the_pace_comes_from_what_happened`

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

Acceptance: Given a run that has finished two of ten source artists and turned
up twelve distinct candidates, when the estimate is computed, then it covers a
projected sixty candidates alongside the eight source artists left.

Verified by: `tests/domain/test_estimating.py::TestProjectingTheSecondStage::test_the_second_stage_is_projected_from_the_first`

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

Verified by: `tests/domain/test_estimating.py::TestThePace::test_one_sample_is_not_enough_to_estimate`, `tests/ui/test_run_estimate.py::TestWhenItWillNotSay::test_one_sample_is_not_enough_to_estimate`

---

### 3.2 Non-functional requirements

---

**NFR-PRIV-001 What leaves the machine**

Priority: Must

Requirement: A discovery run shall send nothing but three kinds of value,
together with the application's own User-Agent: the names of artists drawn from
the ticked genres; the catalogue identifiers the sources answered with, for
those artists or for the candidates the similarity source suggested; fixed
values each client states for itself, being the response format, a result
limit, where a following page starts, the release types, the genres inclusion
and the similarity algorithm.
The headers carry only where the request goes, the User-Agent, the transport's
own terms and a language fixed at any (`ACCEPT_LANGUAGE` in
`infrastructure/fetching.py`).

Rationale: The stance in PLAN.md forbids anything outward that carries the
library or names the listener. Genre scoping is what makes this satisfiable: a
run names the subset the listener chose rather than an inventory of everything
they own. The language is fixed because Qt otherwise adds one by itself from
the system locale: measured on 2026-09-18, every request said `en-GB` about
the machine it came from.

Verification:
`tests/infrastructure/test_what_leaves_the_machine.py::test_a_field_holds_the_name_the_identifier_or_a_constant`
puts every question both catalogue clients can ask through a recording fetcher
and asserts each field holds the artist name, the identifier or a constant the
client states for itself. Proved to bite on 2026-09-13 by planting an extra
field in `infrastructure/catalogue.py`. The headers are read where they arrive,
on a loopback service:
`tests/infrastructure/test_fetching.py::TestAskingAService::test_no_header_says_anything_about_the_listener`
failed on `en-GB,*` before the language was fixed.

---

**NFR-PRIV-002 No identifier of the listener or the machine**

Priority: Must

Requirement: A discovery run shall send no account, no installation identifier,
no machine name, no file path and no library statistic.

Rationale: The application has no account and no telemetry; this must not be
the feature that introduces one by accident.

Verification:
`tests/infrastructure/test_what_leaves_the_machine.py::test_every_field_sent_is_one_its_address_is_allowed`
with `::test_every_address_asked_is_one_the_allowed_set_names` hold every
request against a fixed allowed set of addresses and fields, so a field added
later fails rather than passing unnoticed.
`::test_nothing_sent_names_the_listener_or_the_machine` reads each request
against this machine's name, the user name and the home directory.

---

**NFR-PRIV-003 The User-Agent names the application, never the person**

Priority: Must

Requirement: The catalogue source shall send a User-Agent naming Stellody, its
version and a project contact address, as MusicBrainz requires, with nothing
about the listener.

Verification: `tests/structural/test_user_agent.py` asserts from the source
that `USER_AGENT` in `infrastructure/courtesy.py` is built from `APP_NAME` and
`__version__` out of the version module plus a literal `CONTACT`, with no call
and no other name in it. It also asserts the fetcher's one User-Agent header is
that constant. Proved to bite on 2026-09-13 by planting the user name into the
agent.

---

**NFR-PERF-001 Request pacing**

Priority: Must

Requirement: The discovery service shall issue at most one request per second
per source host, measured over any ten second window.

Rationale: MusicBrainz declines above one per second per IP; ListenBrainz states
the same limit. Pacing to the published figure is the difference between a run
that finishes and an address that gets refused.

Verification:
`tests/infrastructure/test_fetching.py::TestAskingAService::test_it_waits_its_turn_and_names_the_application`
asserts that every request passes through the pacing gate, whose gap is
`REQUEST_GAP_S`, 1.1 seconds, in `infrastructure/courtesy.py`. Amended
2026-09-12: this named a test driving a fake clock over a run of twenty artists,
which does not exist. What is proved is that no request skips the gate; the
spacing itself rests on that one constant. A second client asking the same host
through a gate of its own would undo that spacing, so every client asking
MusicBrainz is given the one gate: the run, an expansion and the cover search.
Held by
`tests/ui/test_discovery_composition.py::test_everything_asking_musicbrainz_waits_at_one_gate`.

---

**NFR-PERF-002 Run duration**

Priority: Won't, ruled 2026-09-09

Withdrawn as a requirement. It asked that a run over the full library of 327
source artists complete within twenty minutes, the two catalogue requests per
artist paced at one per second with the similarity request overlapping them. At
the 1.1 second gap NFR-PERF-001 sets, that arithmetic gives about twelve
minutes; it is what FR-D35 cites and it stands as arithmetic rather than a claim
about any run.

**Ruled by Oliver on 2026-09-09: the duration is not to be measured.** It was
carried as the one requirement no evidence stood behind, on the expectation
that a timed whole-library run would settle it. There is to be no such run, so
the honest thing is to stop asking. A requirement nobody will ever verify is
worse than no requirement, since it reads as held.

Nothing in the suite could have supplied it either: the figure is a property of
two public services on the day they are asked. The pacing that governs how long
a run takes is NFR-PERF-001, which IS measured; how long is left is answered
from the run's own observed pace under FR-D36 rather than from any figure here.

---

**NFR-PERF-003 The candidate genre budget**

Priority: Must

Requirement: The discovery service shall look up a candidate artist's genre at
most once per run, however many source artists name that candidate, then retain
what it learned for reuse by later runs.

Rationale: The similarity source returns identifiers with no genre, so filtering
candidates by genre costs one lookup each. Ten candidates for each of 327
artists is 3,270 requests, which is about another hour at the permitted
rate. Deduplication is what makes the result-side filter affordable. Measured
on 2026-09-13 over a whole-library run, it took 555 source artists' 5,550
possible lookups down to 1,350; OQ-04 records how.

Verification:
`tests/application/test_discovery.py::test_a_candidate_artist_is_asked_about_once`
gives two source artists one shared candidate and asserts one genre lookup
rather than two.

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
below 400 lines and land at 350 or below where it enters the 381 to 400 band.

Verification: `.\gate.ps1`, read by exit code.

---

**NFR-MAINT-002 The suite never reaches the network**

Priority: Must

Requirement: No test shall make a request that leaves the machine. The
application layer reaches every source through an interface it declares, which
its tests fill with a hand-written fake. The clients behind those interfaces
are tested over hand-written fetchers; the fetcher itself is tested against an
HTTP server on the loopback address.

Rationale: The house rule against mock libraries; also the practical one that a
suite depending on a third party fails on their bad day rather than on yours.

**Reworded on 2026-09-13, ruled by Oliver.** It read "no test shall make a
network request", which the suite never met: the fetcher's own tests run a real
HTTP server on the loopback address, in
`tests/infrastructure/fetching_support.py`, because what Qt makes of a status
and a silence is what they exist to test. A fake reply would only test the fake.
None of those requests leaves the machine, which is the property the rationale
is about. Six test modules are permitted the machinery, each with its reason, in
`TESTS_PERMITTED`.

Verification:
`tests/structural/test_offline.py::test_no_test_holds_the_machinery_to_reach_the_network`
scans the whole test tree with the reader the package scan uses.
`::test_every_permitted_test_module_exists_and_still_needs_it` keeps the
permitted set from outliving its reasons. Both proved to bite on 2026-09-13.

---

**NFR-REL-001 Nothing is written into the music folder**

Priority: Must

Requirement: The discovery file, the candidate genre cache, the catalogue
memory and the running record each of those memories keeps shall be written
inside Stellody's own data directory and nowhere else.

Verification: `tests/structural/test_discovery_paths.py` asserts from the source
that every place `infrastructure/discovery_file.py` and
`infrastructure/catalogue_memory.py` name is `paths.data_dir()` with a named
file under it, that neither names a directory of its own and that every call to
the running record (`journal`) or the atomic writer (`_written`) is handed one
of those places. A read made straight off a path is not inspected. Proved to
bite on 2026-09-13 by planting a path under the home directory, then a writer
handed a place of its own.

---

### 3.3 External interfaces

**The catalogue source** answers three questions: the identifier for an artist
name; the albums an artist made with their stated genres; the genres an artist
is said to play. **The similarity source** answers one: the artists similar to
an identifier.

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
C-07: both need a credential; a credential compiled into a GPL application is a
published credential. Last.fm is excluded twice over, since its non-commercial
condition would be imposed on everyone who forks the project. MusicBrainz costs
a User-Agent naming the application, which NFR-PRIV-003 covers.

### 3.4 Data

The discovery file is one JSON object. Its `gaps` member maps each source artist
to what that artist is missing: candidate albums and candidate artists. The
other members, `unresolved`, `ambiguous`, `failed` and `ticked`, carry the four
things named below.

Settled 2026-09-06: **one file, beside the database in Stellody's own data
directory, replaced by every completed run.** Not a directory of dated files,
which becomes a thing to tidy up; not a merge, which would have to rule on a
candidate offered once and owned since. A run therefore states what is missing
at the moment it finished, which is the only claim it can honestly make.

Its JSON shape, written by `infrastructure/discovery_file.py`, is constrained by
FR-D18 and by the four things the file carries beside the results: the artists
that could not be resolved (FR-D08), the ambiguous ones (FR-D09), the failures
(FR-D22) and the genres the run was scoped to (FR-D41).

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
   edition words and connectives with a four-digit year from 1800 to 2099
   permitted.

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
name and is never suppressed by it. Offered: primary type Album and EP, plus the
secondary types Live, Remix and Demo, which are genuinely different records.
Excluded: every other secondary type, Compilation and DJ-mix among them, since a
hits package of an artist already held is noise rather than a discovery.

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
untested against titles as MusicBrainz spells them. The one live run, over
Blues and Folk on 2026-09-08, was read by a person rather than held by a test;
that is one more reason the smallest genres are run first.

## 4. Prioritisation

Must: FR-D01 to FR-D14, FR-D16 to FR-D57 and every NFR except NFR-PERF-002.
Should: FR-D15.
Could: nothing this stage.

Won't, this time, recorded so it is not re-proposed: NFR-PERF-002, withdrawn on
2026-09-09 because the run it would have been measured against is not one
anybody is going to time; any purchase path; ranking candidates by anything
beyond what a source states; remembering across runs what was offered and
rejected; reopening a past run's results from the menu, which FR-D28 makes cheap
to add later and which nobody has asked for yet.

## 5. Open questions

Nothing marked open may be built from. Each is Oliver's unless stated.

| # | Question | Owner |
|---|---|---|
| OQ-04 | RESOLVED 2026-09-13, measured from the files a whole-library run wrote: 34 genres with compilations included, asking the catalogues from 12:04 to 13:01. 555 source artists at ten similar artists each could have cost 5,550 genre lookups. The similarity source returned 4,515 names, since 86 artists came back with none; those name 1,678 distinct artists, because 611 are suggested by more than one source (Coldplay by 81). Taking out the ones the library already holds leaves 1,350 lookups, a quarter of the naive figure: about 25 minutes at the permitted pace rather than 102. Every one of the 1,350 has an answer in the candidate genre cache, which is what a later run reads instead of asking. | Answered |
| OQ-07 | RESOLVED 2026-09-08. Oliver ruled that no fallback is needed; the similarity half depends on the labs endpoint as it stands. Read in `application/discovering.py` on the same day: a refusal raises `SourceFailed`, which is caught for the one artist it happened to, recorded against that artist and written into the discovery file, so the rest of the run carries on regardless. Superseded in part by FR-D21: a refusal now raises `SourceRefused` once its asks run out, which puts that artist back for a later pass rather than recording it as failed. | Answered |

## 6. The build order this implies

Inside out; no user-visible action waits on a screen to be exercisable.

1. **Domain**: the gap rules. What counts as held, what a candidate is, how the
   ticked genres filter both ends. Pure, unit tested against fabricated
   libraries with no source and no library present.
2. **Application**: the discovery service and the two source interfaces, driven
   in tests by hand-written fakes with error injection for every `If` sibling
   above.
3. **Infrastructure**: the two catalogue clients over the one fetching module
   that holds the sockets, the pacing, the JSON writer and the candidate genre
   cache. The retry belongs to the application layer (`application/asking.py`),
   where a run and the expanding of a candidate share it.
4. **UI**: the toolbar button, the dialog and the progress reporting, last.

**Not currently met:** no test drives a whole run into the discovery file. The
application tests assert the run's report;
`tests/infrastructure/test_discovery_file.py` writes reports built by hand; the
window's wiring tests use a fake service, with either a fake writer or the real
writer handed a report built by hand. Meeting this needs one test that runs the
discovery service over a fabricated library and fake sources, writes through the
real writer and asserts the file.

The diagnostic that says the foundation is sound: a whole run must be executable
from a test with a fabricated library and fake sources, producing an asserted
file, before the dialog exists at all. If it cannot be driven that way, the
dialog is not the missing piece.
