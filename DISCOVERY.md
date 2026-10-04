# Discovering music the library does not hold

The specification for the first stage of discovering music the library does
not hold. It is built. One diagnostic in section 6 is not yet met; it says so.
Where this document and the code disagree, this document is amended rather
than quietly diverged from; every requirement names the test that holds it.

## 1. Introduction

### 1.1 Purpose

Stellody knows what somebody owns. It knows nothing about what they might want
next. This adds one thing and no more: a run that reads the library, asks two
public catalogues what is missing around it and writes the answer down as data.

### 1.2 Scope

In scope: a toolbar button, a dialog carrying the genre catalogue, a run that
looks up the artists inside the ticked genres (where the dialog's Include boxes
ask for them, also the artists credited on those genres' compilations and the
other volumes of the series their compilations belong to), a JSON file holding
what it found and a dialog showing what that file holds when a run completes.

Out of scope:

- **Buying anything.** Reaching a shop is stage two, specified in `SHOPS.md`,
  which adds tick boxes to the results dialog and a shops screen behind them.
  This stage names records and never fetches, prices or buys one.
- **Recommending by anything except what is held.** No listening history, no
  taste model, no ranking beyond what a source itself states.
- **Writing to a music file.** The invariant the whole project exists for.
- **Sending anything that identifies the listener or the machine.** See
  NFR-PRIV-001 and NFR-PRIV-002.
- **A results cache that outlives the discovery file**, beyond the candidate
  genre cache NFR-PERF-003 requires and the catalogue memory FR-D46 keeps.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| **Catalogue genre** | A name in `stellody.domain.genres.GENRES`, main or style. |
| **Resolved genre** | An album's genre as the library shows it: the probed tag with any album edit laid over it. Never the raw `sources.genre` column. |
| **Ticked genres** | The catalogue genres selected in the discovery dialog. |
| **Source artist** | An artist a run looks up. For a held album whose resolved genre names at least one ticked genre: its album artist; for a compilation, only while artists on compilations are included (FR-D51), each track credit on it instead. Also each artist a name joins, once the catalogue finds nobody under the whole name (FR-D53). Never "Various Artists" itself. |
| **Compilation** | A held album whose album artist names various artists rather than a person, as `AlbumIdentity.is_compilation` decides. |
| **Track credit** | One of a track's artists, split exactly as the library splits them for playback. |
| **Placeholder artist** | An album artist the catalogue identifies as exactly one artist who has released no album and no EP, such as MusicBrainz's "Global Underground". |
| **Series album** | A held album inside the ticked genres, while other volumes of series are included (FR-D85), that is a compilation or is filed under a placeholder artist; also one filed under an artist whose discography types it as Compilation or DJ-mix (FR-D82), asked about by the catalogue's own title for it. |
| **Series stem** | A title cut at its first bracket, its first " / " and its first " - ", then with whatever follows a number and a colon taken off where FR-D81 reads that number as the volume, else with a trailing number marker taken off: "#7", "No. 7", "Vol. 7", "Volume 7", "Part 7", "Pt. 7", a bare "7" or a number word from "One" to "Twenty" ("Select Ten" is volume 10). Stems are compared on `comparison_key`. "Global Underground: Afterhours 4 - Ibiza / Unmixed" has the stem "Global Underground: Afterhours" and the number 4. |
| **Series** | A named run of release groups the catalogue groups together: a catalogue series (MusicBrainz's own), topped up with every release group whose series stem equals the series album's; where that album belongs to no catalogue series, those release groups alone, named by the stem. |
| **Candidate album** | An album a source gives for a source artist that the library does not hold. |
| **Candidate artist** | An artist a source gives as similar to a source artist, whom the library does not hold. |
| **Release key** | The value two albums are judged the same album on, defined in section 3.5: the title alone, normalised, with edition qualifiers removed and the year deliberately absent. |
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

An addition to an existing application, the third outward-reaching module
after the cover chooser and the update check. It is a client of the
application layer exactly as every other dialog is.

Two services are reached through ONE permitted module: neither catalogue client
holds a socket, both handing their questions to `infrastructure/fetching.py`.
Invariant 12 names four permitted modules, the fourth being the local channel a
second launch speaks to the running copy over.

### 2.2 The one user class

A listener with a tagged library, running Stellody on their own machine. There
is no second class: no administrator, no server, no other person's library.

### 2.3 Operating environment

Windows, macOS and Linux, as the application already ships. A working outbound
HTTPS connection during a run.

### 2.4 Constraints

- **C-01** The library folder is never written to, cache included.
- **C-02** No music file is ever modified.
- **C-03** Nothing leaves the machine that names the listener or the machine.
- **C-04** The domain layer stays pure: no I/O, no framework, no clock.
- **C-05** Modules stay at or below `LINE_CAP` lines; a file in the danger band
  is reduced to `COMFORTABLE_TARGET` or below
  (`tests/structural/test_loc.py`).
- **C-06** Domain and application hold 100% branch coverage.
- **C-07** No credential of any kind is compiled into the application, so no
  source requiring an API key may be used. This rules out Discogs and Last.fm;
  see section 3.3.

### 2.5 Assumptions

| # | Assumption | Owner | Status |
|---|---|---|---|
| A-01 | Both catalogues answer artists, albums and similar artists with no credential. | Oliver | Confirmed by a live run |
| A-02 | The labs similar-artists endpoint answers; it gets no fallback (OQ-07). | Oliver | Confirmed by a live run |
| A-03 | A listener accepts that a run names their source artists to two public catalogues, scoped by the ticked genres. The acceptance was given about names alone; it does not yet cover the held titles NFR-PRIV-001 also lets a run send (FR-D09, FR-D69, FR-D70, FR-D82). | Oliver | Accepted with genre scoping |

## 3. Requirements

Every requirement below is a Must unless it carries a Priority line;
section 4 lists them.

**An album naming no catalogue genre is not source material, whatever is
ticked.** Ticking every genre does not reach it, since no tick names it. The
answer is to state a genre against the album in the tag editor, which touches
no file; the run then treats it exactly as a tagged one. Neither a "not
tagged" tick nor an untagged sweep under select-all is wanted (Oliver's
ruling).

### 3.1 Functional requirements

**FR-D01 Reaching the feature**
- Requirement: The main window shall place a discovery button in the toolbar to
  the left of the appearance toggle, with the separator that divides the library
  controls from the application controls to its right. The File menu shall carry
  `Discover new music...`, which calls what the button calls (so during a run it
  stops that run, FR-D23) and is offered exactly where the button is enabled,
  read off the button each time the menu opens.
- Rationale: Discovery is a library action rather than a control acting on the
  application, so it belongs on the library side of that line.
- Acceptance: Given the main window is open, when the toolbar is read left to
  right, then the discovery button appears before the separator and before the
  appearance toggle.
- Verified by: `tests/ui/test_discovery_button.py::test_discovery_sits_left_of_the_appearance_toggle`, `tests/ui/test_menu_mirrors.py::test_an_entry_is_offered_exactly_where_its_button_is`

**FR-D02 The ring follows the button**
- Requirement: The main window shall include the discovery button in the keyboard
  ring in its visual position.
- Rationale: A control that cannot be reached by keyboard is a control half the
  application's users do not have.
- Acceptance: Given focus is on the button left of discovery, when Tab is pressed,
  then focus is on the discovery button.
- Verified by: `tests/ui/test_discovery_button.py::test_discovery_is_reachable`

**FR-D03 Choosing what to look for**
- Requirement: When the discovery button is pressed, the main window shall open
  the discovery dialog showing the same genre catalogue the filter dialog shows.
- Rationale: Two grids built from one catalogue cannot come to disagree; a second
  vocabulary invented here would.
- Acceptance: Given the catalogue holds a genre, when the discovery dialog opens,
  then that genre appears in its grid with the same main and the same spelling as
  in the filter dialog.
- Verified by: `tests/ui/test_discovery_dialog.py::test_grid_matches_the_catalogue`

**FR-D04 Nothing ticked, nothing to do**
- Requirement: While no genre is ticked, the discovery dialog shall keep its
  action button disabled.
- Rationale: A run over no genres has no source artists, so offering it invites a
  press that can only report emptiness.
- Acceptance: Given the dialog has just opened with nothing ticked, when the
  action button is examined, then it is disabled; when one genre is ticked, then
  it is enabled.
- Verified by: `tests/ui/test_discovery_dialog.py::test_action_needs_a_genre`

**FR-D44 Every genre can be ticked in one press**
- Requirement: The discovery dialog shall carry a push button, distinct from the
  genre tick boxes and placed where the filter dialog's Clear sits, that ticks
  every genre in the catalogue; where every genre is already ticked it shall
  instead clear them all. It shall name whichever of the two a press would do,
  read from the boxes rather than from its last press. It shall wear
  `select-all.png` at the shared dialog control size; clearing shall wear that
  same picture with the shared negative mark laid over it at run time. Pressing
  it shall not close the dialog and shall start no run.
- Rationale: Asking about a whole library should not take a press per genre. A
  tick box would read as one more genre; naming the next press and reusing the
  shared mark follow the convention both trays already keep.
- Acceptance: Given a dialog with nothing ticked, when the control is read, then
  it offers to select all; when it is pressed, then every genre in the catalogue
  is ticked, the dialog is still open and no run has started; when it is pressed
  again, then nothing is ticked. Given every genre ticked by hand, then the
  control offers to clear; given one then unticked by hand, then it offers to
  select all again.
- Verified by: `tests/ui/test_discovery_dialog.py::test_the_sweep_ticks_every_genre_in_one_press`, `tests/ui/test_discovery_dialog.py::test_a_second_press_clears_them_again`, `tests/ui/test_discovery_dialog.py::test_the_sweep_says_what_a_press_would_do`, `tests/ui/test_discovery_dialog.py::test_ticking_the_last_box_by_hand_moves_the_sweep_too`, `tests/ui/test_discovery_dialog.py::test_the_sweep_is_a_button_rather_than_a_tick_box`, `tests/ui/test_discovery_dialog.py::test_sweeping_leaves_the_dialog_open`, `tests/ui/test_discovery_dialog.py::test_the_sweep_wears_its_own_artwork_at_the_shared_size`, `tests/ui/test_discovery_dialog.py::test_clearing_wears_the_same_picture_struck_through`, `tests/ui/test_discovery_dialog.py::test_the_picture_goes_back_when_there_is_something_to_tick_again`

**FR-D05 Who a run asks about**
- Requirement: When a run starts, the discovery service shall take as its source
  artists the album artists of every held album that is not a compilation and
  whose resolved genre names at least one ticked genre. Where artists on
  compilations are included (FR-D51), it shall also take every track credit of
  each compilation whose resolved genre names at least one ticked genre. It shall
  never take "Various Artists" as a source artist. Two names that differ only in
  case or spacing shall be one source artist, asked about once under the spelling
  met first, with what they hold compared as one on `comparison_key`.
- Rationale: The resolved genre is what the listener sees and spent their time
  stating; the probed tag is the library before that work. A name meaning nobody
  in particular is never worth a request, while two spellings of one artist must
  not offer back an album held under the other (FR-D11).
- Acceptance: Given an album whose probed tag names nothing and whose album edit
  states Reggae, when Reggae alone is ticked, then that album's artist is a source
  artist. Given a compilation in Reggae whose tracks credit Dilby and Tinlicker,
  when Reggae is ticked with artists on compilations included, then Dilby and
  Tinlicker are source artists while Various Artists is not; with them left out,
  none of the three is. Given albums "First" by Dennis De Laat and "Second" by
  Dennis de Laat, when the catalogue offers First, Second and Third, then one
  source artist is asked about and only Third is offered.
- Verified by: `tests/application/test_discovery.py::test_one_artist_spelled_two_ways_is_asked_about_once`, `tests/domain/test_one_artist_two_spellings.py`, `tests/application/test_discovery.py::test_sources_read_the_resolved_genre`, `tests/domain/test_stating_an_album.py::TestWhoADiscoveryAsksAbout::test_a_genre_stated_over_an_untagged_album_decides`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_is_asked_about_by_its_track_credits`, `tests/domain/test_discovery_gaps.py::test_a_compilation_left_out_asks_about_nobody`, `tests/domain/test_discovery_gaps.py::test_various_artists_is_never_a_source_artist`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_outside_the_ticks_is_not_asked_about`

**FR-D51 Compilations are included only when asked for**
- Requirement: The discovery dialog shall carry a tick box reading "Artists on
  compilations (Various Artists)", the first of the Include boxes of FR-D85,
  between the genres and its buttons. It shall be unticked the first time the
  dialog opens. After that it shall open as it was last left; its state shall be
  handed to the run with the ticked genres.
- Rationale: Compilation credits can add hundreds of names, so asking about them
  is a choice about how long somebody will wait rather than a default. It is
  still scoped by the ticked genres (Oliver's ruling).
- Acceptance: Given the dialog opened for the first time, then the box is
  unticked. Given it ticked, when Find is pressed, then the run is handed the
  ticked genres with artists on compilations included. Given the dialog left with
  the box ticked, when it is opened again, then the box is ticked.
- Verified by: `tests/ui/test_discovery_compilations.py::test_three_boxes_start_as_a_run_that_widens_to_nothing`, `tests/ui/test_discovery_compilations.py::test_the_run_is_told_what_else_to_take_in`, `tests/ui/test_discovery_compilations.py::test_the_choices_are_remembered_between_openings`, `tests/ui/test_discovery_compilations.py::test_the_boxes_sit_between_the_genres_and_the_buttons`

**FR-D52 The cost of including compilations is stated before a run**
- Requirement: Beneath the Include boxes (FR-D85) the discovery dialog shall
  state what a run would newly look up, with the minutes that adds at the pace
  NFR-PERF-001 permits (`REQUESTS_PER_SOURCE_ARTIST` paced requests an artist,
  `REQUESTS_PER_SERIES` a series). While the artists box is ticked it shall count
  the track credits on compilations inside the ticked genres; a credit counts
  unless a run leaving compilations out would already ask about it or the
  catalogue memory holds a standing answer for it. While the series box is
  ticked it shall count, apart from the artists, the series FR-D84 counts: a
  series once, where any held album of it in the ticked genres has no standing
  answer to which series it is in. A placeholder artist is recognised from the
  catalogue memory alone. With neither box ticked nothing shall be said. The
  statement shall be restated whenever a genre or a box is ticked or unticked; a
  press of the control of FR-D44 shall restate it once, after every genre has
  moved. It reads, for example, "3 artists and 2 series on compilations in these
  genres have not been looked up yet".
- Rationale: A tick box whose consequence is not stated invites a run of unknown
  length. The minutes are arithmetic rather than a forecast, so the words name a
  busy catalogue and call the figure a pace (Oliver's ruling).
- Acceptance: Given compilations in a ticked genre crediting three artists nobody
  has looked up, when the dialog shows, then it states three artists with the
  minutes asking about them adds; given all three already looked up, then it
  states that nothing new would be asked.
- Verified by: `tests/application/test_compilation_cost.py::test_only_names_not_yet_looked_up_are_counted`, `tests/application/test_compilation_cost.py::test_an_answer_past_its_life_is_counted_again`, `tests/application/test_compilation_cost.py::test_a_credit_a_run_would_ask_about_anyway_costs_nothing`, `tests/application/test_compilation_cost.py::test_the_time_is_priced_at_the_permitted_pace`, `tests/ui/test_discovery_compilations.py::test_the_cost_follows_the_ticks`, `tests/ui/test_discovery_compilations.py::test_nothing_new_to_ask_says_so`, `tests/application/test_compilation_cost.py::test_a_series_is_priced_once_however_many_volumes_are_held`, `tests/application/test_compilation_cost.py::test_a_placeholder_the_memory_knows_brings_its_series`, `tests/ui/test_discovery_compilations.py::test_the_sentence_names_the_series_too`, `tests/ui/test_discovery_compilations.py::test_the_price_is_asked_for_the_boxes_ticked`, `tests/ui/test_discovery_compilations.py::test_nothing_costly_ticked_says_nothing`, `tests/ui/test_discovery_compilations.py::test_select_all_prices_once_rather_than_once_a_box`

**FR-D53 A name nobody is found under is asked about by its parts**
- Requirement: Where a source artist's name (an album artist or a track credit
  taken from a compilation) reaches nobody in the catalogue and names several
  artists joined by an ampersand, a comma, a solidus with a space on each side
  or "Featuring" (with its short forms "feat." and "ft."), the discovery service
  shall take each of those artists as a source artist in the same run. That name
  shall not then be reported as unrecognised; a part that reaches nobody shall
  be. A part that is already a source artist shall not be asked about twice.
- Rationale: The whole name is asked first because a join does not always mean
  two people: Eli & Fur is one duo. A bare solidus is not a join, since it
  belongs to names such as AC/DC (Oliver's ruling).
- Acceptance: Given a compilation credit "ODESZA & Bettye LaVette" the catalogue
  does not know while it knows both artists, when the run asks, then ODESZA and
  Bettye LaVette are each asked about and the credit is not reported as
  unrecognised. Given "Eli & Fur" known whole, then no part of it is asked about.
- Verified by: `tests/domain/test_text.py::test_a_credit_naming_several_artists_comes_apart`, `tests/domain/test_text.py::test_a_credit_naming_one_artist_has_no_parts`, `tests/application/test_discovering_compilations.py::test_an_unrecognised_credit_is_asked_about_by_its_parts`, `tests/application/test_discovering_compilations.py::test_a_recognised_credit_is_not_split`, `tests/application/test_discovering_compilations.py::test_a_part_nobody_knows_is_reported_unrecognised`, `tests/application/test_discovering_compilations.py::test_a_part_already_asked_about_is_not_asked_again`, `tests/application/test_discovering_compilations.py::test_an_album_artist_nobody_knows_is_asked_about_by_its_parts`, `tests/application/test_discovering_compilations.py::test_an_album_artist_known_whole_is_not_split`, `tests/domain/test_catalogue_names.py::test_a_spaced_solidus_is_a_join`, `tests/domain/test_catalogue_names.py::test_a_bare_solidus_belongs_to_the_name`, `tests/domain/test_catalogue_names.py::test_a_featured_guest_comes_apart`, `tests/domain/test_catalogue_names.py::test_featuring_inside_a_word_is_not_a_join`

**FR-D06 No source artists**
- Requirement: If the ticked genres yield no source artists, nor any series album
  while other volumes of series are included, then the window shall say so in its
  status bar, make no request and write no file.
- Rationale: Ticking a genre nothing in the library carries is an ordinary thing
  to do.
- Acceptance: Given a genre no held album names, when the action button is
  pressed, then the status bar reports that nothing in the library matches, no
  request is made and no file is written.
- Verified by: `tests/application/test_discovery.py::test_no_sources_makes_no_request`, `tests/ui/test_discovery_wiring.py::test_nothing_to_ask_says_so`; the series album exception by `tests/application/test_discovering_series.py::test_a_compilation_brings_its_series`, whose compilations credit only Various Artists and whose run still completes

**FR-D07 Finding the artist**
- Requirement: When a source artist is reached, the discovery service shall
  request that artist's identifier from the catalogue source by name.
- Acceptance: Given a source artist named in the library, when the run reaches
  them, then exactly one identity request carrying that name is made.
- Verified by: `tests/application/test_discovery.py::test_identity_is_requested_once`

**FR-D08 An artist the source does not know**
- Requirement: If the catalogue source returns no identifier for a source artist,
  then the discovery service shall record that artist as unresolved, continue with
  the next artist and make no further request about them. A catalogue name shall
  count as the source artist's where the two agree once case, accents and
  typographic dashes are set aside (`catalogue_key`); a trailing Discogs number
  such as "(10)" shall be left out of the name asked for. Identity answers are
  kept under the memory section `IDENTIFIERS` (`application/remembering.py`); an
  older section matched on case alone is never read.
- Rationale: A run that stops on the first unknown name never finishes. Matching
  is looser than the library's own key because a tag is typed on a keyboard,
  while the library key stays strict because two spellings on the shelf are the
  listener's filing.
- Acceptance: Given a source whose identity lookup returns nothing, when the run
  completes, then that artist appears in the run's unresolved list and the run's
  exit is normal. Given the tag "Hernan Cattaneo" and a catalogue answering
  "Hernán Cattáneo", then that artist is identified.
- Verified by: `tests/application/test_discovery.py::test_unknown_artist_is_recorded`, `tests/domain/test_catalogue_names.py::test_a_typed_name_matches_what_the_catalogue_writes`, `tests/domain/test_catalogue_names.py::test_the_library_key_stays_strict`, `tests/domain/test_catalogue_names.py::test_a_discogs_number_is_not_asked_for`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_name_typed_without_its_accents_is_the_artist`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_discogs_number_is_left_out_of_the_search`, `tests/infrastructure/test_remembered_credits.py::test_the_retired_section_is_not_read`

**FR-D09 An ambiguous name**
- Requirement: If the catalogue source returns more than one identifier for a
  source artist's name, then the discovery service shall put up to
  `MOST_EVIDENCE` titles the library holds under that name to the catalogue as
  "who is credited on this": held albums first, then held tracks. Where the first
  title crediting any of them credits exactly one, that artist shall be taken as
  the source artist. Otherwise the discovery service shall record that artist as
  ambiguous, name every candidate identifier in the run's report and make no
  further request about them. The rule lives in `application/settling.py`; its
  answers are kept by the catalogue memory, so two runs settle a name the same
  way.
- Rationale: Choosing between namesakes on a listener's behalf would put a whole
  discography under the wrong heading, silently. A title on the listener's own
  shelf is not a guess: only one of the namesakes made it.
- Acceptance: Given an identity lookup returning two artists whose names both
  match the source artist's name on the catalogue key, when the run completes,
  then: where a held title credits one of them, that one is the source artist
  and its albums are asked for; where a held title credits both (or no held title
  credits either), that artist is reported ambiguous with both identifiers named
  and no album request was made for them.
- Verified by: `tests/application/test_discovery.py::test_ambiguous_name_is_reported`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_two_exact_matches_are_both_returned`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_ranked_near_miss_is_not_the_artist`, `tests/application/test_settling_ambiguity.py`, `tests/domain/test_credit_evidence.py`, `tests/infrastructure/test_discovery_sources.py::TestWhoIsCreditedOnATitle`, `tests/application/test_remembering.py::TestAskingOnlyWhatIsUnknown::test_a_credit_is_asked_for_once_then_remembered`

**FR-D10 Albums by an artist already held**
- Requirement: When a source artist has been identified, the discovery service
  shall request the albums that artist made, including each album's stated
  genres. It shall ask `GROUP_LIMIT` to a page (`infrastructure/catalogue.py`)
  and ask for the next page only after a full one, up to `MOST_PAGES` pages.
- Acceptance: Given an identified source artist, when the run reaches their
  albums, then one request is made carrying that artist's identifier and asking
  for genres.
- Verified by: `tests/application/test_discovery.py::test_albums_are_requested_with_genres`

**FR-D11 Never offering back what is owned**
- Requirement: When albums are received for a source artist, the discovery service
  shall discard every album whose release key and secondary types match those of
  an album the library already holds by that artist, as section 3.5 defines them.
- Rationale: The whole value of the feature is the gap. An offer of something on
  the shelf teaches the listener to distrust the rest of the list.
- Acceptance: Given a source artist holding two albums in the library and five at
  the source, when the run completes, then that artist's candidate albums number
  three and neither held title appears.
- Verified by: `tests/domain/test_discovery_gaps.py::test_held_albums_are_dropped`

**FR-D12 Artists like the ones held**
- Requirement: When a source artist has been identified, the discovery service
  shall request the `SIMILAR_WANTED` artists (`application/artist_stage.py`) the
  similarity source considers most similar to them. The endpoint takes no count,
  so `ListenBrainz.similar_to` in `infrastructure/similarity.py` keeps the first
  that many it can name from the ranked answer.
- Rationale: How many to offer is a decision rather than a fact, so it is a named
  constant.
- Acceptance: Given an identified source artist, when the run reaches similarity,
  then one call is made to the similarity source carrying that artist's
  identifier and a count of `SIMILAR_WANTED`, which the client applies to the
  ranked answer.
- Verified by: `tests/application/test_discovery.py::test_similar_artists_are_requested`

**FR-D13 Never offering back an artist held**
- Requirement: When similar artists are received, the discovery service shall
  discard every artist whose normalised name matches the album artist of an album
  in the library. An artist credited only on tracks does not count as held.
- Acceptance: Given a similar-artists response naming two artists in the library
  and eight not, when the run completes, then that source artist carries eight
  candidate artists.
- Verified by: `tests/domain/test_discovery_gaps.py::test_held_artists_are_dropped`

**FR-D14 The ticked genres filter what is collected**
- Requirement: When a candidate album states a genre that Stellody's genre
  catalogue recognises, the discovery service shall discard it where none of the
  genres it recognises is a ticked genre.
- Rationale: Ticking Folk and receiving that artist's spoken-word record is the
  filter failing at the only end that matters to the listener.
- Acceptance: Given Folk is ticked and a candidate album states only Comedy, when
  the run completes, then that album does not appear.
- Verified by: `tests/domain/test_discovery_gaps.py::test_candidate_albums_respect_the_ticks`

**FR-D15 A candidate whose genre is unknown**
- Priority: Should
- Requirement: Where a candidate states no genre that Stellody's genre catalogue
  recognises, whether it states none at all or only names that catalogue does not
  know, the discovery service shall keep it; `ReleaseGroup.states_no_genre` then
  reads true for it.
- Rationale: Dropping what a source failed to describe would narrow the result to
  the well-catalogued, the opposite of finding what is missing.
- Acceptance: Given a candidate album carrying no genres, when the run completes,
  then it appears and reads as stating no genre.
- Verified by: `tests/domain/test_discovery_gaps.py::test_unstated_genre_is_kept_and_marked`

**FR-D16 Saying what is happening**
- Requirement: The toolbar shall carry three progress bars, one each for looking
  up artists, checking series (FR-D69, FR-D83) and checking styles, stacked in
  the order the stages happen and each labelled with the name of its stage;
  checking years, run only while years are set, is drawn on the styles bar under
  its own name (FR-D63). While a run is under way each bar shall show how far
  through its own stage the run is as a percentage; a stage that has finished
  shall be left full and a stage that has not begun shall show no percentage at
  all (FR-D83). On hover the bars shall name the stage and the artist currently
  being asked about, with that artist's place in the stage (one more than the
  number completed) and the stage's total.
- Rationale: A long run with a spinner is indistinguishable from a hang. A bar
  per stage says where the run is at a glance; the stage rather than the artist
  is drawn because a strip of toolbar cannot hold a long name (Oliver's ruling).
- Acceptance: Given a run over three source artists, when the second is reached,
  then the first bar reads one third and the bars name that artist on hover;
  given the run reaches checking styles, then the first bar is left full and the
  styles bar counts against the number of candidates to be asked about.
- Verified by: `tests/ui/test_discovery_bar.py::test_there_is_a_bar_for_each_stage_of_a_run`, `tests/ui/test_discovery_bar.py::test_reaching_the_second_half_leaves_the_first_bar_full`, `tests/ui/test_discovery_bar.py::test_it_names_the_stage_rather_than_the_artist`, `tests/application/test_discovery_narrowing.py::test_the_second_half_of_a_run_reports_as_it_goes`, `tests/ui/test_results_series.py::test_the_series_stage_has_a_bar_of_its_own`, `tests/application/test_discovering_series.py::test_the_stage_says_how_far_it_has_got`

**FR-D17 Stopping**
- Requirement: When the listener cancels a run, the discovery service shall stop
  before issuing its next request, discard the gaps that run had gathered and
  leave any existing discovery file untouched; what the catalogues answered along
  the way is kept, as FR-D48 requires. The run shall be asked whether it is still
  wanted before EVERY request, the waits between attempts being sliced so a stop
  lands inside one. The request in flight shall be dropped rather than waited
  out: the fetcher asks every `SLEEP_SLICE_S` whether anybody still wants it. The
  run itself is abandoned rather than waited for (FR-D27).
- Rationale: Stopping between requests keeps the source's rate accounting honest
  and leaves nothing half-written. A cancel discards rather than parks, since a
  resumable run would have to reconcile partial state against a library that may
  have changed.
- Acceptance: Given a run in progress over an existing discovery file, when cancel
  is pressed, then no further request is issued, none of that run's gaps is
  retained, every answer it had already been given is kept and the existing file
  cannot be replaced by that run's report; given the run is waiting out a refusal
  when cancel is pressed, then it stops within one slice of that wait rather than
  at the end of it; given a cancel arrives between two of the three requests made
  about one artist, then the remaining two are never issued; given a run is
  wedged inside a request that will not answer at all, then the stop still
  returns at once, the window is free to start another and that request is
  dropped rather than left to reach its timeout.
- Verified by: `tests/application/test_stopping_a_run.py::test_cancel_stops_before_the_next_request`, `tests/application/test_stopping_a_run.py::test_a_stop_is_felt_part_way_through_a_wait`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_request_nobody_wants_any_more_is_dropped_at_once`, `tests/infrastructure/test_discovery_sources.py::TestHandingTheQuestionDown::test_every_question_carries_whether_it_is_still_wanted`, `tests/application/test_stopping_a_run.py::test_a_stop_lands_between_requests_rather_than_between_artists`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_what_was_learned_is_kept_however_the_run_ended`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

**FR-D18 The output**
- Requirement: When a run completes, the discovery service shall replace the
  single discovery file, whose `gaps` object is keyed by source artist with each
  value holding that artist's candidate albums and candidate artists; an offered
  series (FR-D69) is keyed by its name and marked as a series (FR-D74). Beside
  `gaps` the file carries the artists left unresolved, ambiguous or failed, the
  genres the run was scoped to, the years it was asked for (FR-D64; both bounds
  empty where none were set) and what the Include boxes took in (FR-D85).
- Rationale: A file rather than a screen, because this stage produces the
  resource the later stages consume. One file replaced rather than merged,
  because a run states what is missing now (section 3.4).
- Acceptance: Given a completed run over one source artist with two candidate
  albums and three candidate artists, when the file is read, then its `gaps`
  object holds one key naming that artist, with two albums and three artists
  beneath it.
- Verified by: `tests/infrastructure/test_discovery_file.py::test_the_file_is_keyed_by_the_artist_it_was_found_for`

**FR-D19 The file cannot be written**
- Requirement: If the discovery file cannot be written, then the window shall
  report the failure in its status bar with the reason, while leaving any previous
  file untouched.
- Acceptance: Given a destination that refuses writes, when a run completes, then
  the failure is reported with the reason and the previous file is unchanged.
- Verified by: `tests/ui/test_discovery_wiring.py::test_a_file_that_will_not_write_is_reported`, `tests/infrastructure/test_discovery_file.py::test_nothing_is_left_half_written`, `tests/infrastructure/test_discovery_file.py::test_a_write_that_fails_leaves_the_last_answer_as_it_was`

**FR-D20 The network is not there**
- Requirement: Where a request is answered with nothing at all, the discovery
  service shall put that artist back for a later pass exactly as a refusal does;
  it shall report an artist nothing ever answered about in words distinct from a
  refused one. Only where `SILENCE_MEANS_GONE` requests in a row are answered
  with nothing at all, with nothing whatsoever answering in between, shall it
  stop the run, report that the network is unavailable and write no file. The
  count is kept for the whole run. In the second half, a candidate the catalogue
  gave no answer about (nothing answered, a refusal outlasted the asks, an error
  or a stop abandoned the request) shall be left unknown rather than written down
  as playing nothing; an empty list of genres the catalogue did give is an answer
  and is kept. A pooled connection idle longer than `IDLE_LIMIT_S` shall be
  thrown away rather than asked down.
- Rationale: One dropped socket is not a dead connection, while several questions
  in a row met with nothing is; the pace makes being sure cheap. A question never
  answered is not an answer, so recording one would drop that candidate from
  every later run.
- Acceptance: Given one request answered with nothing, when the run is observed,
  then that artist is asked about again on a later pass and the run finishes;
  given an artist nothing ever answered about, then it is reported in its own
  words rather than as refused; given `SILENCE_MEANS_GONE` such answers in a row,
  then the run stops there, reports unavailability and writes no file; given an
  answer between two of them, then the count starts again.
- Verified by: `tests/application/test_a_dropped_connection.py::test_one_dropped_connection_does_not_end_a_run`, `tests/application/test_a_dropped_connection.py::test_a_connection_that_has_gone_still_ends_the_run`, `tests/application/test_a_dropped_connection.py::test_an_answer_between_two_silences_starts_the_count_over`, `tests/application/test_a_dropped_connection.py::test_an_artist_nothing_ever_answered_about_says_that`, `tests/application/test_discovery_narrowing.py::test_a_candidate_nothing_answered_about_is_left_unknown`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_did_not_answer_is_not_remembered`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_answered_with_no_genres_is_remembered`, `tests/application/test_discovery_narrowing.py::test_a_connection_lost_in_the_second_half_ends_the_run`, `tests/infrastructure/test_a_closed_connection.py`

**FR-D21 The source refuses**
- Requirement: If a source refuses a request, then the discovery service shall
  ask again on the spot (`RETRY_ATTEMPTS` asks in all); failing that, it shall put
  that artist back for a later pass rather than discarding them. It shall make
  further passes over the artists still owed an answer until either none is owed,
  `QUIET_PASSES` passes running achieve nothing or `MOST_PASSES` passes have been
  made (`application/passing.py`). An artist still owed an answer then shall be
  reported as a failure in the words of what happened to it on its last pass:
  refused where the source refused it, otherwise as FR-D20 and FR-D50 word it.
- Rationale: A refusal is the source asking for patience, not reporting that the
  data is absent. Waiting during the next artist's turn costs nothing, whereas
  waiting where you stand costs a minute an artist.
- Acceptance: Given a source refusing once then answering, when the run
  completes, then that artist's results are present; given a source refusing an
  artist throughout one pass and answering on the next, then that artist's
  results are present; given a source refusing everybody on two passes running,
  then the run stops asking and reports those artists as refused.
- Verified by: `tests/application/test_discovery.py::test_rate_refusal_is_retried`, `tests/application/test_discovery.py::test_an_artist_refused_on_one_pass_is_asked_about_on_the_next`, `tests/application/test_discovery.py::test_a_refusal_that_never_relents_becomes_a_failure`, `tests/application/test_passing.py`

**FR-D50 The source is still thinking when the wait runs out**
- Requirement: Where a request has not been answered by the time the wait runs
  out (`TIMEOUT_S`), whether or not the host accepted the connection, the
  discovery service shall put that artist back for a later pass exactly as a
  refusal does; it shall not count the wait running out towards the run of
  silences FR-D20 ends a run on. It shall report an artist too slow to answer on
  every pass in words distinct from a refused one and from one nothing answered
  about. In the second half, a candidate whose genres were not answered for in
  time shall be left unknown rather than written down as playing nothing.
- Rationale: A slow service is a loaded one, which is what a refusal says in
  words, so it is answered the same way. Counting slowness as silence would let a
  few slow answers claim the network had gone.
- Acceptance: Given a request that runs out of time once then answers, when the
  run completes, then that artist's results are present and no failure is
  reported; given `SILENCE_MEANS_GONE` such answers in a row, then the run still
  completes;
  given an artist too slow on every pass, then it is reported in its own words;
  given a candidate whose genres ran out of time, then nothing is written down
  about them.
- Verified by: `tests/application/test_a_slow_answer.py`

**FR-D22 The source fails for another reason**
- Requirement: If a source returns an error that is not a rate refusal, then the
  discovery service shall record that artist as failed with the reason, continue
  with the next artist and include the failures in the run's report.
- Acceptance: Given a source returning a server error for one artist of three,
  when the run completes, then the other two are present and the failed one is
  named with its reason.
- Verified by: `tests/application/test_discovery.py::test_other_errors_do_not_stop_the_run`

**FR-D42 An answer says who it could not answer for**
- Requirement: When a run completes without a usable answer for one or more
  artists, the message shown at the end of that run shall count each kind
  separately: artists that could not be asked about, names the catalogue did not
  recognise and names that matched more than one artist. Only the kinds that
  happened shall be named. This applies both where the run found something and
  where it found nothing. An artist whose earlier answer the discovery file
  carries over (FR-D46) has a usable answer and is not counted. A stopped run, an
  unreachable one and an answer that could not be written count nothing, since
  each already says it is incomplete.
- Rationale: An artist nobody could look up is one somebody would otherwise
  assume had nothing missing. The kinds are counted apart because each calls for
  something different: run again, fix a spelling or accept that a name cannot be
  settled.
- Acceptance: Given a completed run that found albums, could not ask about four
  artists, did not recognise three names and found two names shared, when it ends,
  then the message names the counts found and says all three of those numbers with
  no comma before the `and`; given a run whose only trouble was three unrecognised
  names, then it says that alone and names neither other kind; given a stopped run
  holding a failure, then it says only that it was stopped; given a completed run
  whose only failure is an artist the file already held an answer for, then the
  message names no shortfall and no button is offered.
- Verified by: `tests/ui/test_shortfall.py::TestTheSentence`, `tests/ui/test_discovery_wiring.py::test_a_run_names_all_three_kinds_of_silence`, `tests/ui/test_discovery_wiring.py::test_only_the_groups_that_happened_are_named`, `tests/ui/test_discovery_wiring.py::test_finding_nothing_still_says_what_went_unanswered`, `tests/ui/test_discovery_wiring.py::test_a_stopped_run_counts_nothing`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

**FR-D43 The names themselves are one press away**
- Requirement: Where a run ends owing the message in FR-D42, a button shall be
  offered beside that message carrying its own count of the artists gone
  unanswered. Pressing it shall open a modal dialog listing those artists, grouped
  under a heading for each of the three kinds with a plain sentence saying what
  that kind means; the sources' own reasons are not shown. The button shall be
  offered only where something is owed and shall be taken away when the next run
  starts.
- Rationale: The names are the half somebody can act on. The button carries its
  own count because the shared status bar soon replaces the sentence beside it.
- Acceptance: Given a run that could not answer for nine artists, when it ends,
  then a button reading `9 artists unanswered` is offered; given one artist, then
  it reads `1 artist unanswered`; given the button pressed, then a modal dialog
  lists every one of those artists under the heading for its kind; given a run
  that answered for everybody, then no button is offered; given a new run started,
  then the button is taken away.
- Verified by: `tests/ui/test_shortfall.py::TestTheButtonLabel`, `tests/ui/test_shortfall.py::TestTheList`, `tests/ui/test_shortfall.py::TestTheDialog`, `tests/ui/test_discovery_wiring.py::test_the_button_appears_carrying_its_own_count`, `tests/ui/test_discovery_wiring.py::test_one_unanswered_artist_reads_as_one`, `tests/ui/test_discovery_wiring.py::test_a_clean_run_offers_no_button`, `tests/ui/test_discovery_wiring.py::test_a_new_run_takes_the_last_one_s_button_away`, `tests/ui/test_discovery_wiring.py::test_pressing_it_opens_the_names`, `tests/ui/test_dialog_first_stop.py`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

**FR-D23 One run at a time**
- Requirement: While a run is under way, pressing the discovery button shall stop
  that run rather than offer a second one; the runner shall refuse a second run
  of its own accord.
- Rationale: Two runs racing would double the request rate, breaching
  NFR-PERF-001, then race each other to replace the same file.
- Acceptance: Given a run in progress, when the discovery button is pressed, then
  that run is asked to stop and no dialog opens; when no run is under way, then
  the same press opens the dialog.
- Verified by: `tests/ui/test_discovery_stopping.py::test_pressing_it_during_a_run_stops_the_run`, `tests/ui/test_discovery_wiring.py::test_the_runner_refuses_a_second_run`

**FR-D24 The application closes mid-run**
- Requirement: If the application is asked to quit while a run is under way, then
  the window shall tell the run to stop before its next request, then wait for it
  and for every run abandoned earlier to end, allowing each at most `WAIT_MS`
  (`ui/discovery_worker.py`), before the application ends; the stopped run shall
  leave any existing discovery file untouched.
- Rationale: A close is a cancel the listener expressed differently.
- Acceptance: Given a run in progress, when the application is quit, then the run
  has been told to stop by the time the application's departure is called; given a
  stopped run's report, then the discovery file refuses to be replaced by it.
- Verified by: `tests/ui/test_quitting.py::test_quitting_mid_run_stops_the_discovery_run`, `tests/application/test_stopping_a_run.py::test_closing_stops_the_run`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

**FR-D25 The dialog asks, then leaves**
- Requirement: When a run is started, the discovery dialog shall close. It knows
  nothing about a run: it cannot report on one, stop one or tell whether one is
  under way.
- Rationale: A run takes minutes; a dialog held open for all of them is one
  somebody has to work around, while the toolbar bars carry the progress.
- Acceptance: Given a genre is ticked, when the action is pressed, then the ticks
  are handed over and the dialog closes; given nothing is ticked, when the action
  is reached from the keyboard and pressed, then nothing is started and the dialog
  stays.
- Verified by: `tests/ui/test_discovery_dialog.py::test_finding_closes_the_dialog`

**FR-D26 What a candidate plays is remembered**
- Requirement: The discovery service shall keep what each candidate artist was
  found to play and shall not ask about a candidate it already holds an answer
  for. An answer already held shall still be judged against the run's own ticks.
- Rationale: What somebody plays does not change between runs, so asking again
  spends minutes on an answer already held; judging it afresh stops memory
  smuggling a candidate past a run's scope.
- Acceptance: Given a run that asked about two candidates, when a second run meets
  the same two, then no request is issued about either and both are judged against
  that run's own ticks.
- Verified by: `tests/application/test_discovery_narrowing.py::test_what_was_remembered_is_not_asked_about_again`, `tests/ui/test_discovery_composition.py::test_a_run_is_given_somewhere_to_remember_what_it_learns`

**FR-D27 Stopping is immediate**
- Requirement: When the discovery button is pressed while a run is under way, the
  window shall stop that run at once, without asking anything, let go of the bar
  at once and ignore any report the run sends afterwards; the run winds down on
  its own thread reporting to nobody. While a run is under way the button shall
  wear the shared negative mark over its picture and shall say "Stop discovery";
  the mark shall come off on EVERY ending, whether the run was stopped,
  completed, found nothing, could not be reached or failed. Picture and words are
  set together in one place; the strings live in `stellody/ui/tray_metrics.py`,
  from which the guide reads them.
- Rationale: A confirmation question was a thing a press had to get past, so the
  control that said stop did not stop; a button that plainly says what it will do
  needs no check. The run is abandoned rather than waited for, so a stop is
  instant (Oliver's ruling).
- Acceptance: Given a run in progress, when the discovery button is pressed, then
  the run is asked to stop with no question raised, the toolbar bar returns to
  rest at once and reports are ignored until the run ends. Given a run in
  progress, then the button carries the negative mark and says "Stop discovery".
  Given a run that is stopped, one that completes, one that fails and one that
  reaches nothing, then in every case the mark comes off and the button says
  "Discover music the library does not hold" again. Given a run that has just
  been stopped, when a new run is asked for, then it starts at once; the stopped
  run winds down on its own thread and reports to nobody.
- Verified by: `tests/ui/test_discovery_stopping.py::test_a_press_stops_at_once_without_asking_anything`, `tests/ui/test_discovery_stopping.py::test_the_button_wears_the_cross_while_a_run_is_under_way`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_is_stopped`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_finishes_on_its_own`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_fails`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/ui/test_discovery_stopping.py::test_progress_reported_after_a_stop_does_not_revive_the_bar`

**FR-D28 The results are shown when a run completes**
- Requirement: When a discovery run completes, the window shall write the
  discovery file and then open the results dialog on what that file holds
  (FR-D33). The results screen shall be MODAL, so only one exists at a time. The
  run's own message shall be said BEFORE the screen opens.
- Rationale: Built from the file so one thing stays authoritative. Modal because
  a completed run replaces the file, so a screen left standing would show an
  answer that no longer exists anywhere; a message set behind a modal screen is
  only seen once it closes (Oliver's ruling).
- Acceptance: Given a run that found two candidate albums, when it completes, then
  the file is written and a dialog opens naming both, modally; given the run's own
  message, then it is said before the screen opens rather than behind it.
- Verified by: `tests/ui/test_results_dialog.py`, `tests/ui/test_discovery_wiring.py`

**FR-D29 What a source artist shows**
- Requirement: For each source artist the run found something for, the results
  dialog shall show that artist once, with the candidate albums beneath them.
- Rationale: The source artist is the reason each album is offered.
- Acceptance: Given a source artist with two candidate albums, when the dialog
  opens, then the artist appears once and both albums appear beneath that name.
- Verified by: `tests/ui/test_results_dialog.py::test_a_source_artist_carries_its_albums`

**FR-D30 What a candidate artist shows**
- Requirement: For each candidate artist, the results dialog shall show that
  artist's name collapsed, with no album beneath it until it is expanded.
- Rationale: Every record a candidate made is unheld, so the list beneath them
  would be their whole discography; most are never opened (FR-D31).
- Acceptance: Given a run that found three candidate artists, when the dialog
  opens, then three names are shown and no album sits under any of them.
- Verified by: `tests/ui/test_opening_a_candidate.py::test_a_candidate_artist_starts_collapsed`

**FR-D31 A candidate artist's albums are fetched on demand**
- Requirement: When a candidate artist is expanded in the results dialog, the
  results dialog shall show the releases that artist made which pass the offering
  rule section 3.5 states, fetched at the moment of expanding (read a page at a
  time as in FR-D10) through the catalogue memory. With no years set, a run asks
  nothing about a candidate's releases; while years are set, FR-D63 asks during
  the run and expanding reads what it was told. A row never opens onto nothing: a
  candidate the similarity source named without an identifier is asked about by
  nobody and says "The catalogue did not say which artist this is"; one the
  catalogue answered with nothing worth offering says "No albums worth offering".
- Rationale: Each catalogue request costs at least the gap NFR-PERF-001 requires,
  so it is paid only for the candidates somebody opens (Oliver's ruling).
- Acceptance: Given a collapsed candidate artist, when it is expanded, then that
  artist's offered releases appear beneath it; given the run that produced the
  file had no years set, then it issued no request about that artist's releases;
  given a candidate with no identifier, when it is expanded, then no request is
  made and the row says the catalogue did not say which artist it is; given an
  answer offering nothing, then the row says so.
- Verified by: `tests/ui/test_opening_a_candidate.py::test_expanding_a_candidate_asks_for_their_albums`, `tests/ui/test_opening_a_candidate.py::test_a_candidate_the_catalogue_could_not_name_says_so`, `tests/ui/test_opening_a_candidate.py::test_a_candidate_with_nothing_to_offer_says_that_rather_than_nothing`, `tests/application/test_expanding.py::test_everything_that_artist_made_is_offered`, `tests/application/test_expanding.py::test_a_hits_package_is_still_noise`, `tests/application/test_discovery_narrowing.py::test_a_run_never_asks_what_a_candidate_released`

**FR-D32 The lookup for an expanded artist cannot be made**
- Requirement: The lookup for an expanded candidate artist shall be attempted
  `OPENED_ATTEMPTS` times (`application/asking.py`), the wait between attempts
  doubling each time, before it is reported as having failed. If it cannot be
  fetched, then the results dialog shall show what went wrong against that
  artist and say that closing and opening the row tries again; it shall leave
  every other entry as it was.
- Rationale: One artist nobody could look up is no reason to lose the rest of a
  run. Somebody who opened one row will sit through a longer wait than a run can
  spend on every artist.
- Acceptance: Given a candidate artist whose lookup fails, when it is expanded,
  then that artist shows what went wrong and says the row can be closed and
  opened to try again; when another is expanded, then it still lists its releases;
  given a service refusing three times running and answering on the fourth, then
  the releases are shown rather than a failure.
- Verified by: `tests/ui/test_opening_a_candidate.py::test_a_failed_expansion_says_so_and_spares_the_rest`, `tests/ui/test_opening_a_candidate.py::test_an_artist_that_failed_is_asked_again_the_next_time_it_is_opened`, `tests/application/test_expanding.py::test_three_refusals_running_do_not_lose_the_artist`, `tests/application/test_expanding.py::test_a_source_refusing_every_time_is_that_artist_failing`, `tests/application/test_expanding.py::test_the_wait_between_asks_doubles`

**FR-D33 Every completed run opens its answer**
- Requirement: If a discovery run completes, then the window shall write its
  answer and open the results screen on what was written, whether or not the run
  found any candidate album or candidate artist.
- Rationale: Nothing missing is an answer about the library; a screen that opens
  says what the run looked in and who it could not answer about, which a status
  bar nobody is watching does not (Oliver's ruling).
- Acceptance: Given a run that found nothing, when it completes, then its answer
  is written and the results screen opens naming the genres it looked in.
- Verified by: `tests/ui/test_results_dialog.py::test_a_run_that_found_nothing_still_shows_its_screen`, `tests/ui/test_discovery_wiring.py::test_a_run_that_found_nothing_still_writes_and_opens`

**FR-D34 A source artist and a candidate artist are told apart by colour**
- Requirement: The results dialog shall draw source artist names in a different
  colour from candidate artist names, both colours taken from the theme's
  semantic tokens.
- Rationale: A source artist is held and missing records; a candidate is not held
  at all.
- Acceptance: Given a dialog holding both kinds, when the two colours are read
  from the theme, then they differ in each appearance.
- Verified by: `tests/ui/test_results_dialog.py::test_the_two_kinds_of_artist_are_coloured_apart`

**FR-D39 The results say what they are showing**
- Requirement: The results dialog shall carry a key naming each kind of row it
  draws, each entry marked with a filled circle in the colour that kind is drawn
  in. Every artist row shall state its kind in words: a source artist row shall
  give the number of albums beneath it, with the number of similar artists where
  there are any. A candidate artist row shall name itself as a similar artist,
  gaining the number of its albums once they have been fetched.
- Rationale: An indented candidate otherwise reads as an album and its albums as
  tracks. Colour alone fails a reader who cannot separate the hues; FR-D34 keeps
  the colours and this says what they mean.
- Acceptance: Given a dialog holding both kinds, when the key is read, then it
  names all three kinds of row with a mark in each kind's own colour; when a
  source artist row with similar artists beneath it is read, then it gives both
  counts; when a candidate row is read, then it names itself a similar artist.
- Verified by: `tests/ui/test_results_reading.py::test_the_key_names_all_three_kinds_in_their_own_colours`, `tests/ui/test_results_reading.py::test_a_source_row_says_how_many_of_each_sit_under_it`, `tests/ui/test_results_reading.py::test_a_candidate_row_says_that_it_is_an_artist`

**FR-D40 The results say when the catalogue is being asked**
- Requirement: While one or more candidate artist lookups are in flight, the
  results dialog shall show a busy indicator naming the artist being asked about;
  where there is more than one, it shall name the number of artists instead. The
  indicator shall occupy its place whether or not anything is in flight, carrying
  instead what to do to fetch an artist's albums.
- Rationale: Several seconds of quiet is the ordinary case and reads as stuck
  unless something says so. The space is reserved so the list does not jump at
  the moment somebody clicks in it.
- Acceptance: Given a candidate artist being expanded, when the dialog is read,
  then the indicator names that artist and is busy rather than counted; given two
  in flight, then it names the number; given the last answer arriving, then it
  returns to carrying the instruction.
- Verified by: `tests/ui/test_results_reading.py::test_the_strip_names_who_is_being_asked_about`, `tests/ui/test_results_reading.py::test_the_strip_counts_them_when_several_are_in_flight`, `tests/ui/test_results_reading.py::test_the_strip_goes_quiet_when_the_last_answer_lands`

**FR-D41 The results say what the run looked in**
- Requirement: The results dialog shall state, above the key, the number of
  genres the run was scoped to and their names. The genres shall be read from the
  discovery file being shown, in the same reading as the gaps, rather than from
  the ticks handed over when the run started. Where the file names no genres the
  dialog shall show no such line at all.
- Rationale: Two runs over unlike genres otherwise yield screens that read
  identically. Reading from the file keeps one source of truth.
- Acceptance: Given a run scoped to two genres, when the dialog opens, then a
  line above the key names both and says there were two; given one genre, then
  the line says one genre rather than genres; given a file naming no genres, then
  no such line is drawn and the gaps are shown as before.
- Verified by: `tests/ui/test_results_reading.py::test_it_says_which_genres_the_run_looked_in`, `tests/ui/test_results_reading.py::test_one_genre_is_not_called_genres`, `tests/ui/test_results_reading.py::test_a_run_that_names_no_genres_shows_no_line_at_all`, `tests/ui/test_results_reading.py::test_the_genres_sit_above_the_key`, `tests/ui/test_results_dialog.py::test_the_genres_shown_come_from_the_file_it_is_showing`, `tests/application/test_discovery.py::test_a_completed_run_carries_what_it_was_asked_to_look_in`, `tests/infrastructure/test_discovery_results.py::TestWhatTheRunWasAskedFor`

**FR-D46 The same library answers the same way twice**
- Requirement: The discovery service shall keep what each catalogue answered,
  against the question that was asked; it shall ask a catalogue for an artist's
  identity, releases or similar artists (also who is credited on a held title as
  FR-D09 asks; also the series questions of FR-D69 and FR-D70) only where that
  answer is not kept or was kept more than thirty days ago (`MEMORY_LIFE_DAYS`);
  what a candidate plays is kept without a limit. A run shall write down what it
  learned however that run ended. Where a run cannot reach a source about an
  artist an earlier run answered for, the discovery file shall keep the earlier
  answer and shall record no failure for that artist; the run's closing message
  and its count of unanswered artists shall be read from the answer as the file
  will hold it, so neither names that artist. Where a run reaches its end still
  owing an answer about an artist nothing was ever known about, the discovery
  file shall be written with that artist named as unanswered rather than
  withheld. The gaps written shall be ordered by artist. Where two holders of the
  memory save over one another, the file shall keep every answer either of them
  learned, taking the later answer to any question both hold; one lock covers a
  save and any note that would land between its read and its clearing of the
  record.
- Rationale: Without memory the answer is a property of how a service feels that
  day rather than of the library. Thirty days is long enough that a run usually
  asks nothing, short enough that this year's record is found this year
  (Oliver's ruling). A run may add to what is known and correct it but may not
  take it away because a service said no.
- Acceptance: Given a library run over twice with the same genres, when the second
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
- Verified by: `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_the_second_run_asks_the_catalogues_nothing`, `tests/application/test_remembering.py::TestAskingOnlyWhatIsUnknown`, `tests/application/test_remembering.py::TestHowLongAnAnswerStands`, `tests/application/test_remembering.py::TestCarryingAnAnswerOver`, `tests/infrastructure/test_discovery_file.py::test_an_answer_with_a_hole_in_it_is_written_with_the_hole_named`, `tests/infrastructure/test_discovery_file.py::test_an_artist_already_answered_for_is_not_a_hole`, `tests/infrastructure/test_discovery_file.py::test_the_artists_are_written_in_one_order_however_they_arrived`, `tests/ui/test_discovery_wiring.py::test_a_run_with_a_hole_in_it_still_opens_its_answer`, `tests/infrastructure/test_catalogue_memory.py::test_what_is_kept_comes_back_exactly`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`, `tests/application/test_merging_recollections.py`, `tests/infrastructure/test_overlapping_memory.py`, `tests/ui/test_discovery_composition.py::test_everything_keeping_catalogue_answers_shares_one_memory`

**FR-D48 An answer is written down the moment it arrives**
- Requirement: Each answer a run's catalogues give and each answer about what a
  candidate plays shall be appended to a running record as it arrives and forced
  to the disk. An answer fetched when a candidate is opened on the results screen
  is written straight into the memory file once that lookup ends. Both memories
  shall be read as their file plus that record; each record shall be dropped only
  once its own file has been written with what it held.
- Rationale: A crash or a closed window must not take a run's whole cost with it.
  An append cannot damage what is already there; clearing the record beside a
  failed write would discard the very answers it protects.
- Acceptance: Given answers noted by a run that never finished, when a later run
  starts, then it knows every one of them and asks about none of them; given a
  record whose last line is half written, then every line before it is still
  known; given a memory whose file cannot be written, then its record survives;
  given a memory whose file is written, then its record is gone.
- Verified by: `tests/infrastructure/test_a_dead_run_keeps_what_it_learned.py`, `tests/infrastructure/test_journal.py`, `tests/application/test_remembering.py::TestAnAnswerIsKeptTheMomentItArrives`, `tests/application/test_discovery_narrowing.py::test_each_candidate_is_written_down_as_it_is_answered`

**FR-D47 A failure is said in words somebody can act on**
- Requirement: Where a lookup fails, the results dialog shall say what happened
  in plain words naming no address, no exception class and no status code, read
  off the KIND of failure rather than its message; the diary shall carry the
  class, the message and the catalogue identifier of the artist instead.
- Rationale: The technical account is unreadable to a listener and the only thing
  worth having to whoever fixes it, so both are kept, apart.
- Acceptance: Given a lookup that fails for any reason, when the row is drawn,
  then it names no address and no exception class; given a service that refused
  every attempt, then the row says the catalogue is busy; given a wait that ran
  out, then it says the catalogue did not answer in time; given anything else,
  then it points at the log; and in every case the diary carries the class, the
  message and the artist's catalogue identifier.
- Verified by: `tests/ui/test_results_reading.py::TestSayingWhyInWords`, `tests/ui/test_expansion_worker.py::test_the_row_gets_words_and_the_log_gets_the_machine`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_service_that_never_answers_is_given_up_on_anyway`

**FR-D49 The answer is turned a page at a time**
- Requirement: The results dialog shall deal its source artists into pages, each
  page filling EVERY one of its columns save the last page, which takes what is
  left, where how deep a column is filled follows from the height of the dialog.
  An artist taller than that depth shall fill its column and be scrolled rather
  than dropped or divided; it shares its page wherever the page has more than one
  column. It shall show one page at a time with two controls beneath the answer,
  one for each direction, each wearing its own artwork struck through where that
  direction leads nowhere (both where there is one page); between them shall
  stand words saying which page of how many is in front. Those three shall stand
  on the SAME row as the Filter control of FR-D54, which leads it, the controls
  that act on the ticks and Close, immediately beneath the answer. The pager
  shall stand on the middle of the dialog, the left controls and Close each in a
  side of their own sharing equally the width it leaves; where the left side
  cannot fit in half, it keeps its width and the pager stands as near the middle
  as that allows (`ui/results_foot.py`). Every page shall be built when the
  dialog opens and kept, so that an album ticked on one page is still ticked
  after another has been looked at.
- Rationale: A whole-library answer in scrolling columns gives no sense of where
  in it somebody is. Filling every column lets one tall artist scroll rather than
  leaving pages half empty; one foot row rather than two is Oliver's ruling.
  The per-row height is a stated figure, since the offscreen platform cannot
  measure fonts; correct it from a real screen.
- Acceptance: Given more source artists than a page holds, when the dialog
  opens, then the first page is in front and the way back is struck through;
  given the last page, then the way on is struck through; given an album ticked
  on one page, when another page has been looked at, then it is still ticked and
  still goes to a shop; given artists of any heights whatever, then every page
  but the last carries every column; given an artist taller than a column, then
  it fills one and shares its page; given a run that found nobody, then there is
  still one page.
- Verified by: `tests/ui/test_results_pages.py`, `tests/ui/test_results_foot.py`, `tests/ui/test_shop_choosing.py::test_a_tick_holds_across_pages_and_still_reaches_a_shop`

**FR-D54 The answer can be narrowed to some of the genres the run looked in**
- Requirement: The results dialog shall carry a Filter control wearing the
  library's filter artwork, offering only the genres the run looked in. While any
  is picked, it shall show a source artist's albums only where the library holds
  an album in a picked genre filed under that artist or crediting them on a
  compilation. It shall show a candidate artist only where the candidate genre
  cache records a genre for them naming a picked genre (else as FR-D78 says). It
  shall show an offered series (FR-D69) only where a held album in a picked genre
  has that series' name as its series stem. A source artist with nothing left to
  show shall not be shown. The control shall stay pressed in while a filter is
  on; the pages shall be dealt again from what is shown. The filter shall not be
  remembered between openings.
- Rationale: A source artist is judged by the genres the listener stated on
  their own albums, so nobody held is withheld for want of a genre. A candidate
  is not in the library, so the candidate genre cache is what judges them; a
  catalogue series whose name matches no held stem is withheld while a filter is
  on (Oliver's ruling).
- Acceptance: Given an answer holding a House source artist and a Rock one, when
  House alone is picked, then only the House artist is shown and the pages are
  dealt from them; when the filter is cleared, both are shown again.
- Verified by: `tests/domain/test_discovery_filter.py::test_nothing_picked_shows_everything`, `tests/domain/test_discovery_filter.py::test_a_source_artist_shows_by_the_genres_held`, `tests/domain/test_discovery_filter.py::test_a_candidate_shows_by_its_remembered_genres`, `tests/domain/test_discovery_filter.py::test_an_artist_with_nothing_left_is_not_shown`, `tests/ui/test_results_filter.py::test_only_the_genres_looked_in_are_offered`, `tests/ui/test_results_filter.py::test_the_filter_stays_pressed_in_while_on`, `tests/ui/test_results_filter.py::test_the_pages_are_dealt_from_what_is_shown`, `tests/domain/test_series.py::TestOnScreen::test_a_filter_keeps_a_series_held_in_the_picked_genres`, `tests/domain/test_series.py::TestOnScreen::test_a_filter_withholds_a_series_held_elsewhere`

**FR-D55 What a filter withholds is said**
- Requirement: While a filter is on, the results dialog shall name the genres it
  is set to, then state how many candidate artists are withheld because neither
  the candidate genre cache nor the library's albums for the heading they sit
  under (FR-D78) record a genre for them that Stellody's genre catalogue
  recognises.
- Rationale: Rows that vanish without a word read as rows never found. Naming the
  filter first stops the line reading as though the picked genres were unknown.
- Acceptance: Given two candidates with no remembered genre under a heading the
  library holds no album for, when House is picked, then the dialog reads
  "Filtered to House: 2 similar artists held back, since neither MusicBrainz nor
  the artist they were suggested for gives a genre Stellody recognises"; when the
  filter is cleared, then it says nothing.
- Verified by: `tests/domain/test_discovery_filter.py::test_candidates_with_no_genre_are_counted_as_withheld`, `tests/ui/test_results_filter.py::test_the_withheld_count_is_said_while_filtering`, `tests/ui/test_results_filter.py::test_the_line_names_the_genres_before_what_it_held_back`, `tests/ui/test_results_filter.py::test_the_line_says_the_source_gave_nothing_either`, `tests/domain/test_genre_rulings.py`

**FR-D56 A filter never takes a tick away**
- Requirement: Changing the filter shall keep every tick, including a tick on a
  row the filter withholds. Copy and Find in shops shall act only on ticked albums
  currently shown. Closing the shops dialog clears every tick, including one a
  filter holds back (FR-S45 in `SHOPS.md`).
- Rationale: A tick is somebody's decision; a filter is only where they are
  looking. Acting on rows out of sight would send albums to a shop unseen
  (Oliver's ruling).
- Acceptance: Given an album ticked, when a filter withholds it, then Copy leaves
  it out; when the filter is cleared, then it is still ticked.
- Verified by: `tests/ui/test_results_filter.py::test_a_withheld_tick_is_left_out_of_copy`, `tests/ui/test_results_filter.py::test_a_tick_survives_the_filter_being_cleared`

**FR-D57 The chooser's Filter waits for a tick**
- Requirement: While no genre is ticked in the chooser FR-D54 opens and every
  kind of FR-D86 is ticked, its Filter control shall be disabled, unless the
  chooser opened with a filter on.
- Rationale: With nothing to filter by, the press can only take a filter off; the
  exception keeps that the one way a filter comes off, since Cancel keeps it.
- Acceptance: Given the chooser opened on no filter, when nothing is ticked, then
  Filter is disabled; when a genre is ticked, then it is enabled; when Clear is
  pressed, then it is disabled again. Given the chooser opened on a filter, when
  Clear is pressed, then Filter is still enabled.
- Verified by: `tests/ui/test_filter_controls.py::test_filtering_waits_for_a_tick`, `tests/ui/test_filter_controls.py::test_clearing_every_tick_takes_filtering_away_again`, `tests/ui/test_filter_controls.py::test_a_filter_already_on_can_still_be_taken_off`, `tests/ui/test_results_showing.py::test_a_kind_left_out_is_enough_to_filter_by`

**FR-D45 The answer is dealt across the width of the screen**
- Requirement: The results dialog shall open at nine tenths of the screen it opens
  on, never below 700 by 560 and never above 1920 by 1080. It shall deal the
  source artists across as many columns as that width affords, never more than
  three, a column being a third of the width it opens at on a real 13 inch
  display, each a list read top to bottom; a row too long for its column is cut
  short with an ellipsis. Artists shall be dealt to the shortest column at the
  time, counting an artist's height as its own row plus one for each album and
  each candidate under it. A column shall be built only where an artist landed in
  it; a run that found nobody shall still show one. One selection shall stand
  across the columns. Every dialog shall make its native window before it is
  sized, in `FirstStopDialog` (`ui/dialogs.py`), except on Wayland, so the share
  is of the screen it opens on.
- Rationale: A single list is a shape nobody reaches the end of. The ceiling is
  what a 13 inch display shows and three columns is what one shows comfortably
  (Oliver's ruling); dealing by height keeps columns even.
- Acceptance: Given a screen wide enough that nine tenths of it holds two column
  widths, when the dialog opens, then the source artists are drawn over two or
  more lists side by side and each artist appears exactly once; given a screen at
  the floor, then one list is drawn as before; given a 3440 monitor, then the
  dialog opens no wider than 1920 pixels and shows three columns; given a 13 inch
  display at 300% reported as 1422 by 836, then three columns are drawn; given
  fewer artists than the width affords columns, then no empty column is built;
  given a row chosen in one column, then any selection in the others is cleared.
- Verified by: `tests/ui/test_results_columns.py::TestHowMuchRoomItTakes::test_a_wide_monitor_gets_no_more_than_a_13_inch_display`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_three_is_the_ruling_rather_than_whatever_the_constant_says`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_the_13_inch_ceiling_affords_the_three_that_were_asked_for`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_real_13_inch_display_shows_three`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_wide_monitor_shows_three_and_no_more`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_every_artist_lands_in_exactly_one_column`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_it_deals_by_height_rather_than_by_count`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_it_builds_what_the_width_affords`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_fewer_artists_than_columns_builds_no_empty_column`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_a_run_that_found_nobody_still_gets_a_screen`, `tests/ui/test_results_columns.py::TestOneSelectionAcrossThem::test_choosing_in_one_column_clears_the_others`, `tests/ui/test_results_columns.py::TestWhatIsTickedAcrossThem::test_the_ticks_are_read_from_every_column`, `tests/ui/test_results_size.py`, `tests/ui/test_dialog_first_stop.py::test_every_dialog_has_its_window_before_it_is_shown`

**FR-D35 How long the run has left**
- Requirement: While a discovery run is under way, the window shall show an
  estimate of the time remaining for the whole run in BOTH of two places. In the
  status bar it shall be a sentence rounded to the nearest minute, saying less
  than a minute where the estimate is under sixty seconds. At the right hand end
  of the bar of the stage under way (FR-D16) it shall be an abbreviated form of
  that same estimate, drawn clear of the stage name. Both shall be answered from
  one reading of the pace.
- Rationale: Somebody who cannot tell a long run from a hang closes the window.
  The bar is where a watcher looks; one reading keeps the two from disagreeing
  across a rounding.
- Acceptance: Given a run under way with an estimate available, when the status
  bar is read, then it names a whole number of minutes or says less than a
  minute; when the moving bar is read, then its right hand end carries the
  same estimate abbreviated, drawn clear of the stage name.
- Verified by: `tests/ui/test_run_estimate.py::TestNamingTheTimeLeft::test_the_status_bar_names_the_time_left`, `tests/ui/test_discovery_bar.py::test_it_writes_how_long_is_left_at_the_right_hand_end_of_the_moving_bar`, `tests/ui/test_discovery_bar.py::test_the_time_and_the_stage_are_never_drawn_over_each_other`, `tests/ui/test_discovery_bar.py::test_the_time_is_actually_drawn_on_the_bar`

**FR-D36 The estimate is taken from the run itself**
- Requirement: The window shall derive the estimate from the time the run has
  actually taken for each unit of work finished, rather than from the request gap
  NFR-PERF-001 states.
- Rationale: Refusals and passes (FR-D21) make the real cost differ from the gap,
  so an estimate built on the gap would be confidently wrong.
- Acceptance: Given a run whose finished units took twice the gap apiece, when the
  estimate is computed, then it follows the observed pace rather than the
  configured one.
- Verified by: `tests/domain/test_estimating.py::TestThePace::test_the_pace_comes_from_what_happened`

**FR-D37 The second stage is estimated before it begins**
- Requirement: While a run is in its first stage, the window shall include in the
  estimate a projection of the second stage, sized from the candidate artists seen
  so far against the source artists finished so far.
- Rationale: The second stage is the larger half; leaving it out would understate
  the wait.
- Acceptance: Given a run that has finished two of ten source artists and turned
  up twelve distinct candidates, when the estimate is computed, then it covers a
  projected sixty candidates alongside the eight source artists left.
- Verified by: `tests/domain/test_estimating.py::TestProjectingTheSecondStage::test_the_second_stage_is_projected_from_the_first`

**FR-D38 Too little has happened to estimate**
- Requirement: If fewer than `MINIMUM_SAMPLES` units of the current stage have
  finished, then the window shall say the run is under way without naming a time.
- Rationale: A pace measured over one sample swings by a factor; an honest silence
  is trusted more.
- Acceptance: Given a run that has finished one source artist, when the status bar
  is read, then it says the run is under way and names no time.
- Verified by: `tests/domain/test_estimating.py::TestThePace::test_one_sample_is_not_enough_to_estimate`, `tests/ui/test_run_estimate.py::TestWhenItWillNotSay::test_one_sample_is_not_enough_to_estimate`

#### Release years

A run may be told which years the music it offers was released in. **The years
scope what a run offers, never what it learns from.** A candidate artist is
checked during the run; the years are not remembered between dialogs; a
plausible year runs from `FIRST_YEAR` to `YEARS_AHEAD` after the current one
(Oliver's ruling). A release group with no stated year is ordinary rather than
rare.

**FR-D58 Choosing the years to look in**
- Requirement: The discovery dialog shall offer two optional year fields, from
  and to, each empty when the dialog opens.
- Rationale: Two optional bounds cover after, before, between and any. Empty on
  opening because what to look for is decided afresh each time, unlike the
  Include boxes (FR-D51, FR-D85).
- Acceptance: Given the dialog opens, then both fields are empty; given 1980 is
  typed in from and 1989 in to, when Find is pressed, then the run is started with
  the years 1980 to 1989 inclusive.
- Verified by: `tests/ui/test_discovery_years.py::TestTheFields`, `tests/ui/test_discovery_years.py::test_the_runner_hands_the_years_to_the_run`

**FR-D59 Years that cannot be used are refused, not corrected**
- Requirement: If a year field holds anything other than a four digit year from
  `FIRST_YEAR` to the year after the current one (or the from year is later than
  the to year), then the discovery dialog shall say which field is wrong and why,
  with Find disabled.
- Rationale: A range quietly clamped answers a question nobody asked. The ceiling
  is read from the clock so it cannot go stale.
- Acceptance: Given 1990 in from and 1980 in to, then the dialog says the from
  year is later than the to year and Find is disabled; given 198 in from, then it
  says that is not a year.
- Verified by: `tests/domain/test_release_years.py::TestReadingTypedYears`, `tests/ui/test_discovery_years.py::TestRefusing`

**FR-D60 The years scope what is offered, never who is asked**
- Requirement: While years are set, the discovery service shall choose its source
  artists exactly as it does with no years set.
- Rationale: The library is what discovery learns from; the years constrain only
  what it may hand back.
- Acceptance: Given a library holding only a 1977 album by a source artist whose
  catalogue offers an unheld album first released in 2021, when a run over the
  years 2020 onwards completes, then that 2021 album is offered.
- Verified by: `tests/application/test_discovering_by_year.py::TestTheLibraryStillTeaches::test_an_old_album_leads_to_a_new_one`, proved to fail with the library filtered by the years

**FR-D61 A candidate album's year is its first release**
- Requirement: While years are set, the discovery service shall offer a candidate
  album only where the year of the release group's first release lies inside them,
  both bounds included. The year is read by `year_of`.
- Rationale: The release group's first release is the original's year, so a
  reissue of a 1977 album is a 1977 album, as section 3.5 already relies on.
- Acceptance: Given years 1980 to 1989, then albums first released in 1980 and in
  1989 are offered while ones first released in 1979 and in 1990 are not.
- Verified by: `tests/domain/test_release_years.py::TestOfferingByYear`, `tests/application/test_discovering_by_year.py::TestAlbumsByYear`

**FR-D62 A candidate album with no stated year is not offered while years are set**
- Requirement: If a candidate album's release group states no first release year,
  then while years are set the discovery service shall not offer it.
- Rationale: No year is invented to make a candidate fit; with no years set the
  album is offered as before.
- Acceptance: Given years 2020 onwards and an album stating no first release date,
  then the album is not offered; given no years, then it is.
- Verified by: `tests/domain/test_release_years.py::TestAdmitting::test_no_year_does_not_fit_a_bounded_range`, `tests/application/test_discovering_by_year.py::TestAlbumsByYear::test_no_years_offers_what_it_always_did`

**FR-D63 A candidate artist is offered only with an album inside the years**
- Requirement: While years are set, after the candidates have been narrowed by
  genre, the discovery service shall ask the catalogue, through the catalogue
  memory, what each remaining candidate artist released and shall keep only
  those with an offered album inside the years. A candidate that could not be
  asked about or carries no identifier is not offered. The progress is reported
  on the styles bar, named "Checking years".
- Rationale: A candidate artist arrives with no dates, so without asking the run
  would offer artists who released nothing in the years. Known limit: the
  first-stage projection (FR-D37) leaves this stage out of the time said.
- Acceptance: Given years 2020 onwards and two candidates, one whose only album
  was first released in 1975 and one with an album first released in 2022, then
  only the second is offered; given no years, then no albums are asked for any
  candidate.
- Verified by: `tests/application/test_discovering_by_year.py::TestCandidatesByYear`, `tests/application/test_discovering_by_year.py::TestWhenACandidateCannotBeDated`, `tests/ui/test_discovery_years.py::TestTheBars`

**FR-D64 The answer says which years it was asked for**
- Requirement: When a run with years set completes, the discovery file shall
  record the years beside the ticked genres and the results screen shall say them
  on the line naming what the run looked in.
- Rationale: FR-D41 for the new question: an answer scoped to one decade that did
  not say so reads as a library missing nothing from any other.
- Acceptance: Given a completed run over Rock for 1980 to 1989, when the results
  open, then the line reads `Looked in 1 genre: Rock; released 1980 to 1989`.
- Verified by: `tests/infrastructure/test_release_dates_kept.py::TestTheDiscoveryFile`, `tests/ui/test_discovery_years.py::TestTheResultsSayTheYears`

**FR-D65 An expanded candidate shows only albums inside the years**
- Requirement: When a candidate artist is expanded in the results of a run that
  had years set, the results screen shall show only that artist's offered albums
  inside those years.
- Rationale: Otherwise expanding would bring back the records the run was asked
  to leave out.
- Acceptance: Given a run for 2020 onwards, when a candidate is expanded whose
  albums were first released in 1975 and in 2022, then only the 2022 album shows.
- Verified by: `tests/application/test_discovering_by_year.py::TestExpandingByYear`

**FR-D66 What is carried over keeps to the years**
- Requirement: When an earlier answer is carried over for an artist this run
  failed on (FR-D46), the discovery service shall carry only the albums inside
  this run's years; it shall carry that artist's candidate artists only where the
  earlier run was asked for the same years.
- Rationale: Carried albums carry their dates, so they can be held to the new
  years; carried candidates were checked against the earlier years only.
- Acceptance: Given an earlier answer with no years holding albums first released
  in 1975 and in 2022 plus one candidate artist, when a run for 2020 onwards fails
  on that artist, then only the 2022 album is carried and no candidate artist is.
- Verified by: `tests/application/test_discovering_by_year.py::TestCarryingOverByYear`

**FR-D67 A remembered answer with no dates in it is asked again**
- Requirement: If the catalogue memory holds an artist's albums written before
  release dates were kept, then the discovery service shall ask the catalogue
  again rather than reuse them.
- Rationale: An album remembered without its date would read as having no year
  and be dropped by any run with years set.
- Acceptance: Given a catalogue memory entry whose albums carry no date field,
  when the memory is read, then that entry is absent while the rest are kept.
- Verified by: `tests/infrastructure/test_release_dates_kept.py::TestTheCatalogueMemory`

**FR-D68 An offered album says the year it first came out**
- Requirement: Where the catalogue states a first release year for an offered
  album, the results dialog shall show that year after the album's title. What a
  shop is searched for and what Copy puts on the clipboard stay the bare title,
  carried on the row as data.
- Rationale: The year shown is the one the range is judged by (FR-D61); nothing
  is added where none is stated, since a guess would say something false.
- Acceptance: Given an offered album "Tripwires" first released in 2019, then
  its row reads "Tripwires (2019)"; when it is ticked, then the album handed to
  the shops is titled "Tripwires".
- Verified by: `tests/ui/test_discovery_years.py::TestAnAlbumRowSaysItsYear`

#### Series

**FR-D69 A series album is asked about by the series it belongs to**
- Requirement: While other volumes of series are included (FR-D85), when a run
  reaches a series album, the discovery service shall offer each entry of that
  album's catalogue series that the library does not hold.
- Rationale: A compilation's natural neighbours are its other volumes, which
  asking about artists can never reach; a placeholder artist has no albums of
  its own.
- Acceptance: Given held albums "Global Underground: Adapt #2" and "Global
  Underground: Adapt #6" credited to Various Artists, with series included,
  when the catalogue places both in the series "Global Underground: Adapt" of six
  entries, then that series is offered with Adapt, Adapt #3, Adapt #4 and Adapt

#5 and nothing else.

Verified by: `tests/application/test_discovering_series.py::test_a_compilation_brings_its_series`, `tests/application/test_discovering_series.py::test_one_series_is_asked_about_once`, `tests/application/test_discovering_series.py::test_leaving_compilations_out_asks_about_no_series`, `tests/application/test_discovering_series.py::test_a_person_with_albums_is_no_placeholder`, `tests/application/test_discovering_series.py::test_a_name_reaching_several_artists_is_no_placeholder`

**FR-D70 A series album is also matched by its stem**
- Requirement: When a run reaches a series album, the discovery service shall
  also search for its series stem, whether or not a catalogue series exists; it
  shall offer each release group whose series stem equals the album's series
  stem and which the library does not hold, under the catalogue series' name
  where there is one and under the stem where there is none. A volume both
  answers name shall be offered once, compared on its stem and number (FR-D71).
- Rationale: Some series sit in no catalogue series and a catalogue series list
  can lag the catalogue's own titles (Oliver's ruling).
- Acceptance: Given held "Global Underground: Unique #2" filed under the
  placeholder artist "Global Underground", with series included and no
  catalogue series for it, when a title search answers Unique, Unique #2, Unique

#3 and "Global Underground: Uniqueness", then Unique and Unique #3 are offered
under "Global Underground: Unique".

Verified by: `tests/application/test_discovering_series.py::test_no_series_falls_back_to_the_stem`, `tests/application/test_discovering_series.py::test_a_volume_found_twice_is_offered_once`, `tests/domain/test_series.py::TestOneVolumeOnce`, `tests/domain/test_series.py`

**FR-D71 A series entry is judged held on its stem and number**
- Requirement: The discovery service shall treat a series entry as held where
  any held album has either the same series stem and number or the same release
  key (section 3.5), whoever that album is filed under.
- Rationale: Library titles such as "Global Underground: Select #7 / Unmixed" do
  not reduce to the catalogue's title by release key; FR-D11 outranks
  completeness. The artist is ignored because one series is filed under several
  names in one library.
- Acceptance: Given held "Global Underground: Select #7 / Unmixed", when the
  series offers "Global Underground: Select #7", then it is not offered.
- Verified by: `tests/domain/test_series.py::TestHeld`

**FR-D72 A series offers every kind of record in it**
- Requirement: The discovery service shall offer a series entry whatever kinds
  the catalogue states for it, inside the ticked genres and the run's years.
- Rationale: Series entries are typed Compilation, DJ-mix or both, so the
  offering rule of section 3.5 would leave every series empty.
- Acceptance: Given a series entry typed Compilation and DJ-mix, first released in
  2018, when the run has no years set, then it is offered.
- Verified by: `tests/domain/test_series.py::TestMissing`

**FR-D73 A series question that fails is said, not hidden**
- Requirement: If a question about a series album is refused through every ask,
  times out or fails, then the discovery service shall record that album's title
  as a failure of the run and carry on with the next series album; it is not put
  back for a later pass. A question answered with nothing counts towards the run
  of silences of FR-D20.
- Rationale: A series nobody could look up is exactly the one somebody would read
  as complete (as FR-D22 judges of artists).
- Acceptance: Given a catalogue that refuses every series question, when a run
  reaches "Global Underground: Adapt #2", then the report names that title among
  its failures and the run completes.
- Verified by: `tests/application/test_discovering_series.py::test_a_refused_series_is_a_failure`, `tests/application/test_discovering_series.py::test_a_failed_series_question_is_a_failure_too`, `tests/application/test_discovering_series.py::test_one_silence_is_a_failure_rather_than_an_ending`, `tests/application/test_discovering_series.py::test_a_run_of_silences_ends_the_run`

**FR-D74 A series is shown as a series**
- Requirement: The results dialog shall show each offered series as a heading
  naming the series, the word "series" and its count of albums, with the missing
  entries beneath it. The name, the flag and the entries are written to the
  discovery file. An entry's shop artist is "Various Artists".
- Rationale: A heading reading like an artist would tell a listener they hold
  somebody they do not. The shop artist follows how the catalogue credits such
  series; it is Claude's choice rather than a ruling and stands until Oliver says
  otherwise.
- Acceptance: Given the Adapt series with four missing entries, when the results
  open, then a heading reads "Global Underground: Adapt (series, 4 albums)".
- Verified by: `tests/ui/test_results_series.py::test_a_series_heading_says_it_is_one`, `tests/ui/test_results_series.py::test_a_series_entry_goes_to_the_shops_under_various_artists`, `tests/infrastructure/test_series_kept.py::test_a_series_survives_the_file`

**FR-D75 A heading with nothing under it is not shown**
- Requirement: The results dialog shall leave out any heading with no album and
  no similar artist beneath it. The discovery file still records it.
- Rationale: A heading with nothing under it says nothing a listener can act on
  (Oliver's ruling).
- Acceptance: Given an answer holding "Global Underground" with nothing found and
  "Giza Djs" with three albums, when the results open, then only "Giza Djs" is
  shown.
- Verified by: `tests/ui/test_results_series.py::test_an_empty_heading_is_left_out`, `tests/domain/test_series.py::TestOnScreen::test_an_empty_heading_is_not_worth_showing`

**FR-D76 A genre with one vote or under half the leading votes is not believed**
- Requirement: Where a catalogue states a genre with fewer than two votes beside
  one with two or more, the discovery service shall not count it among that
  artist's or that album's genres; where every genre has a single vote, all are
  kept. Nor shall it count a genre with fewer than half the votes of the leading
  genre (`LEADING_SHARE`); the leading genre always stays. The rule is `believed`
  in `domain/genre_votes.py`, applied by the catalogue client to every genre list
  it reads. The candidate genre cache is `candidate-genres-2.json`; caches kept
  under earlier rules are not read.
- Rationale: Stray tags let almost anybody through a genre filter; a minor genre
  far behind the leading one is no description of the artist (Oliver's ruling).
- Acceptance: Given MusicBrainz answering Nirvana with grunge 67 and electronic
  1, then Nirvana's genres are grunge alone; given an artist with techno 1 and
  house 1, then both are kept; given Lady Gaga with pop 24, dance-pop 20,
  electropop 17 and electronic 6, then her genres are pop, dance-pop and
  electropop, so an Electronic filter does not show her.
- Verified by: `tests/domain/test_genre_votes.py`, `tests/infrastructure/test_discovery_sources.py::TestWhatAnArtistPlays::test_a_genre_voted_for_once_beside_real_ones_is_dropped`, `tests/infrastructure/test_discovery_sources.py::TestWhatAnArtistPlays::test_an_album_s_genres_are_held_to_the_same_rule`

**FR-D77 The catalogue holds the genres similar artists are stated with**
- Requirement: The genre catalogue shall carry these mains in place of the
  single Electronic, each with these styles: Dance (Breakbeat, Dance-Pop, Disco,
  Downtempo, EDM, Electronica, Eurodance, Hi-NRG, Italo Dance); Electronic
  (Ambient, Big Beat, Drum n Bass, Dubstep, Jungle, UK Garage); House (Acid
  House, Deep House, Progressive House, Tech House); Techno & Electro (EBM,
  Electro, Minimal Techno, Techno, Trance). Pop shall carry Britpop, Dream Pop,
  Electropop, Indie Pop, K-Pop, New Wave, Pop Rock and Synth-pop. When a genre
  name MusicBrainz states matches, in any case, one of the names ruled in
  `domain/genre_rulings.py` (answered for by `genres.ALIASES`), the discovery
  service shall read it as the catalogue genre it was ruled to mean; no ruling is
  keyed on a catalogue name. The bare tag `dance` shall state the Dance main. A
  genre value stored before this catalogue shall be read as written, with the
  style's new main added and nothing rewritten. Every dialog that offers the
  catalogue shall show a tick box for every genre in it.
- Rationale: Many similar artists stated only names the catalogue did not know.
  Where the lines between the four mains fall is Oliver's ruling, not a
  definition: Electronic is ambient, bass and breaks; House and Techno & Electro
  are the club families; Dance is chart and festival dance music. Rock
  subgenres, R&B, soul, folk, country, blues, reggae, production music, new age,
  poetry and spoken word were not ruled and stay unrecognised (Oliver's ruling).
- Acceptance: Given MusicBrainz stating `dubstep`, then the candidate reads as
  Electronic and Dubstep; given `goa trance`, then Techno & Electro and Trance;
  given `microhouse`, then House alone; given `trip hop`, then Dance and
  Downtempo; given `death metal`, then Rock and Heavy Metal; given `acid jazz`,
  then Jazz; given `dance` or `DANCE`, then Dance alone; given a box ticked for
  Dance, then the stored value reads back as Dance; given the stored
  `Electronic; House`, then Electronic and House. Every genre has a box in the
  discovery dialog, the library filter, the answer's filter and the tag editor.
- Verified by: `tests/domain/test_genre_rulings.py::TestTheRulingsOf2026_10_01`, `tests/domain/test_genre_rulings.py::TestTheRulingsOf2026_10_01::test_a_value_stored_before_the_split_reads_as_written`, `tests/domain/test_genre_rulings.py::TestTheRulingsOf2026_10_01::test_the_bare_dance_tag_is_the_dance_main`, `tests/domain/test_genre_rulings.py::TestTheDanceSubTaxonomy`, `tests/domain/test_genre_rulings.py::TestTheRulingsOnTheRest::test_the_names_a_filter_withheld_on_2026_09_30`, `tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_every_catalogue_name_in_its_own_spelling_reads_back_as_itself`, `tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_no_alias_is_keyed_on_a_catalogue_name`, `tests/domain/test_genres.py::TestTheCatalogue::test_it_holds_the_mains_that_were_settled`, `tests/ui/test_genre_grid.py::test_every_dialog_holding_the_grid_offers_every_genre`

**FR-D78 An untagged candidate is judged by who it was suggested for**
- Requirement: While a genre filter is on, where the candidate genre cache
  records no genre the catalogue recognises for a candidate artist, the results
  dialog shall judge that candidate by the catalogue genres of the held albums
  belonging to the heading it sits under: albums whose album artist or any track
  artist compares equal to the heading's artist (a joint credit the run took
  apart counts for each artist it names, FR-D53); for a series heading, albums
  whose series stem compares equal to the heading's name. The candidate shall be
  shown where those genres meet the picked genres and filtered out where they do
  not. Only where those albums name no catalogue genre either shall the candidate
  be withheld and counted under FR-D55. A candidate under several headings shall
  be judged under each on its own. The rule is `filtered_answer` in
  `domain/discovery_filter.py`.
- Rationale: Most such candidates have no genre in the catalogue at all; they
  were suggested because they resemble an artist held, so the genres held for
  that artist are the best evidence there is (Oliver's ruling).
- Acceptance: Given an untagged candidate under a heading whose held album is
  House, when House is picked, then the candidate is shown and nothing is held
  back; under a heading held as Rock, then it is filtered out and not counted;
  under a heading whose albums state only `Skiffle`, then it is counted as held
  back; under the series heading Global Underground with "Global Underground #7
  / Unmixed" held as House, then it is shown; under Lane 8, credited on a
  Various Artists album held as House, then it is shown; under DJ Tennis, held
  only as "Moat, Kyozo, & DJ Tennis" in House, then it is shown and DJ Tennis
  keeps its albums.
- Verified by: `tests/domain/test_judged_by_their_source.py::test_an_untagged_candidate_shows_under_a_house_source`, `tests/domain/test_judged_by_their_source.py::test_an_untagged_candidate_under_a_rock_source_is_filtered_out`, `tests/domain/test_judged_by_their_source.py::test_judged_per_heading_where_one_candidate_sits_under_two`, `tests/domain/test_judged_by_their_source.py::test_counted_unjudged_where_the_source_names_no_genre_either`, `tests/domain/test_judged_by_their_source.py::test_a_series_heading_is_judged_by_the_volumes_held`, `tests/domain/test_judged_by_their_source.py::test_a_track_credit_on_a_compilation_judges_too`, `tests/domain/test_judged_by_their_source.py::test_a_recognised_genre_of_its_own_still_judges_first`, `tests/domain/test_judged_by_their_source.py::test_a_heading_split_from_a_joint_credit_judges_by_that_credit`, `tests/domain/test_judged_by_their_source.py::test_a_heading_split_from_a_joint_credit_keeps_its_albums`

**FR-D79 The genre grid's categories fold**
- Requirement: The genre grid shall lay the catalogue's mains out in three
  columns, in catalogue order down each column. Each main that carries styles
  shall show an arrow before its box, a stop on the keyboard ring; a press of the
  arrow (a click, Enter or Space) shall show or hide that main's styles. Every
  category shall start folded the first time a dialog is opened. Each of the four
  dialogs holding the grid shall remember on its own which categories were left
  open and open them again next time. While a category is folded, a count of its
  ticked styles shall show beside the main's name. A dialog shall give back the
  room a category took once it is folded again.
- Rationale: With every box showing, the grid made its dialogs too wide; the
  count keeps a folded-away tick from being a choice nobody can see (Oliver's
  ruling).
- Acceptance: Given a dialog never opened before, then every category is folded
  and no style shows; when the arrow beside Dance is pressed, then Dance's nine
  styles show under it; given Dubstep ticked with Electronic folded, then
  `(1)` shows beside Electronic; given Dance left open in the library filter,
  when it is opened again, then Dance is open there and nowhere else; in the
  answer's filter, a main with nothing on offer is not shown and a main offered
  without its styles shows no arrow.
- Verified by: `tests/ui/test_genre_folding.py`, `tests/ui/test_genre_grid.py::TestWhatItOffers::test_three_columns_is_the_ruling`, `tests/ui/test_genre_grid.py::TestWhatItOffers::test_the_groups_read_down_then_across_in_catalogue_order`

**FR-D80 A DJ mix is offered**
- Requirement: While DJ mixes are included (FR-D85, `ReleaseGroup.offered_with`),
  where a release group states the DJ-mix secondary type, the discovery service
  shall treat a Compilation type beside it as no bar to offering it; it shall
  offer the release group wherever its remaining types are all offered types
  (Live, Remix, Demo). A release group stating Compilation without DJ-mix shall
  stay excluded. The rule is `ReleaseGroup.is_offered` in `domain/discovery.py`.
- Rationale: MusicBrainz files a mix as Compilation plus DJ-mix, so excluding
  Compilation excluded the mix. A DJ's mix is worth offering; a hits package is
  not (Oliver's ruling).
- Acceptance: Given an artist whose discography holds "Involver" as Compilation
  plus DJ-mix, "Fundacion" as DJ-mix and "Live at Fabric" as DJ-mix plus Live,
  then all three are offered; given "Greatest Hits" as Compilation alone, then
  it is not; given a DJ-mix also stating Soundtrack or an unrecognised type,
  then it is not; expanding a candidate offers its mixes on the same rule.
- Verified by: `tests/domain/test_discovery_gaps.py::test_a_dj_mix_is_a_discovery`, `tests/domain/test_discovery_gaps.py::test_a_dj_mix_of_an_unknown_kind_is_still_left_alone`, `tests/domain/test_discovery_gaps.py::test_a_candidates_dj_mix_is_offered_on_expanding`, `tests/domain/test_discovery_gaps.py::test_a_hits_package_is_not_a_discovery`

**FR-D81 A number before a colon is a volume**
- Requirement: Where a title's volume title holds a number, written in digits
  and not reading as a year, followed by a colon and further words, with a
  letter before the number, the discovery service shall read that number as the
  volume and the words before it as the series stem. Otherwise a number ending
  the volume title shall be the volume.
- Rationale: The library and the catalogue write a numbered mix such as "Global
  Underground #45: ..." or "Fabric 99: Sasha" with the number before a colon, so
  read whole neither named a volume. A year is excluded because "Sónar 2011: ..."
  is one mix of that year. Known misreadings remain ("Mixmag Presents Hot Since
  82" reads as volume 82); each only matters inside a series search.
- Acceptance: Given "Global Underground #45: Danny Tenaglia - Brooklyn" and
  "Global Underground 045: Danny Tenaglia in Brooklyn", then both are volume 45
  of "Global Underground"; given "Fabric 99: Sasha", then volume 99 of
  "Fabric"; given "Sónar 2011: Selected and Mixed by Agoria" or "2001: A Space
  Odyssey", then the whole title is the stem and no volume is read.
- Verified by: `tests/domain/test_series.py::TestTheStem::test_a_number_before_a_colon_is_the_volume`, `tests/domain/test_series.py::TestTheStem::test_a_year_before_a_colon_is_not_a_volume`, `tests/domain/test_series.py::TestTheStem::test_a_number_with_no_name_before_it_is_not_a_volume`

**FR-D82 A compilation filed under an artist brings its series**
- Requirement: While other volumes of series are included (FR-D85), for each held
  album inside the ticked genres filed under an artist who is neither Various
  Artists nor a placeholder, the discovery service shall settle that artist as
  FR-D09 does. Where one identity results, it shall look the album up in that
  artist's discography: by its release key, kinds aside, else by its numbered
  place in a series. Where the release group found states Compilation or DJ-mix
  while no release group of that artist without either kind shares the album's
  release key, the service shall ask about that release group's title by series
  as FR-D70 does. A stem search answered for an unnumbered title shall keep only
  release groups that state a volume number.
- Rationale: Most mixes are filed under the DJ rather than Various Artists; the
  discography is already in the run's memory. A hits package counts, since
  some series are typed Compilation alone; a plain album of the same title wins;
  only volumes are kept beside an unnumbered title, which otherwise matches every
  recording of a work (Oliver's ruling).
- Acceptance: Given "Global Underground #45: Danny Tenaglia - Brooklyn" held
  under Danny Tenaglia, whose discography holds "Global Underground 045: Danny
  Tenaglia in Brooklyn" as Compilation plus DJ-mix, then that title is asked
  which series it belongs to and the series' other volumes are offered; given a
  name with two identities the library cannot settle, then nothing is asked;
  given "Led Zeppelin" held where the artist released an album and a
  compilation of that title, then nothing is asked.
- Verified by: `tests/application/test_discovering_filed_compilations.py`, `tests/domain/test_series.py::TestFiledUnderAnArtist`, `tests/domain/test_series.py::TestSharingAStem::test_beside_an_unnumbered_title_only_volumes_are_kept`

**FR-D83 Checking series has a bar of its own**
- Requirement: The series stage shall report on a bar of its own, stacked between
  the artists bar and the styles bar. When a later stage reports, each earlier
  bar that has reported shall be left full; an earlier bar that never reported
  shall stay at rest, showing its name and no percentage. Each bar shall be
  taller than its writing.
- Rationale: The series stage is a stage of its own size; sharing a bar left
  that bar's percentage meaning two things in turn. A run with series left out
  checks none, which a full bar would misstate (Oliver's ruling).
- Acceptance: Given a run reaching the series stage, then the artists bar reads
  full and the series bar counts the series titles; given a run that goes from
  looking up straight to checking styles, then the series bar still reads
  "Checking series" with no percentage.
- Verified by: `tests/ui/test_results_series.py::test_the_series_stage_has_a_bar_of_its_own`, `tests/ui/test_results_series.py::test_a_run_checking_no_series_leaves_its_bar_at_rest`, `tests/ui/test_discovery_bar.py::test_there_is_a_bar_for_each_stage_of_a_run`, `tests/ui/test_discovery_bar.py::test_each_bar_is_taller_than_its_writing`

**FR-D84 The time said covers the series stage**
- Requirement: While other volumes of series are included (FR-D85), the
  discovery service shall count, as a run starts and from the catalogue memory
  alone, the series the series stage will have to look up (FR-D52's count,
  extended to the compilations of FR-D82); it shall carry that count on every
  report while artists are looked up. The time said then shall add those series
  at the first stage's own pace, scaled by `REQUESTS_PER_SERIES` against
  `REQUESTS_PER_SOURCE_ARTIST`. While series are checked, each report shall carry
  the number of candidates the styles stage will ask about; the time said shall
  add them at the series stage's pace, scaled by `REQUESTS_PER_CANDIDATE` against
  `REQUESTS_PER_SERIES`. The price beneath the Include boxes shall count the same
  series.
- Rationale: Each stage's time should include the stages still ahead once their
  size is known. A name only the library's titles could settle is not counted,
  nor is anything on a first run before the memory holds a discography: known
  undercounts.
- Acceptance: Given two of six artists done in four seconds with three series
  ahead, then the time said is eight seconds for the artists plus twelve for the
  series; given ten of thirty series done in twenty seconds with eight candidates
  ahead, then forty plus four; given a DJ whose remembered discography types a
  held album as a DJ mix, then the price counts one series; none where the
  memory holds two artists of that name.
- Verified by: `tests/domain/test_estimating.py::TestTheSeriesAhead`, `tests/application/test_discovering_filed_compilations.py::test_the_reports_carry_what_lies_ahead`, `tests/application/test_compilation_cost.py::test_a_compilation_filed_under_its_dj_is_a_series_to_price`

**FR-D85 Three boxes say what else a run takes in**
- Requirement: The Discover dialog shall carry, under the heading "Include:",
  three boxes: "Artists on compilations (Various Artists)" (FR-D51), "Other
  volumes of series" (FR-D69, FR-D82) and "DJ mixes" (FR-D80). Each shall act
  alone: the run shall ask about compilation credits only with the first, run the
  series stage only with the second; it shall offer DJ mixes in an artist's own
  list, on expanding a candidate and among answers carried over (FR-D66) only
  with the third. Series entries are offered whatever the third box says, since a
  series of mixes is made of nothing else. Each box shall open as it was last
  left; where the first two were never saved, an earlier single compilations
  setting shall answer for both. The price line shall price only those of the
  first two that are ticked. The run's choices shall be written to the discovery
  file beside its years and read back for expanding; a file without them reads as
  the first two clear and mixes offered.
- Rationale: The three cost different amounts and are wanted for different
  reasons, so each is chosen on its own (Oliver's ruling).
- Acceptance: Given a fresh dialog, then the boxes read clear, clear, ticked;
  given the series box alone ticked, then the series stage runs and no
  compilation credit is asked about; given the mixes box clear, then a DJ's
  unheld mix is not offered and expanding a candidate offers none; given the old
  box saved as ticked and the new ones never saved, then the first two open
  ticked.
- Verified by: `tests/ui/test_discovery_compilations.py`, `tests/application/test_discovering_filed_compilations.py::test_series_need_no_credits`, `tests/application/test_discovering_filed_compilations.py::test_mixes_left_out_are_not_offered_under_their_dj`, `tests/application/test_expanding.py::test_a_run_that_left_mixes_out_leaves_them_out_on_expanding`, `tests/infrastructure/test_discovery_results.py::TestWhatTheRunTookIn`, `tests/domain/test_discovery_gaps.py::test_dj_mixes_left_out_are_not_offered`

**FR-D86 The results filter shows by kind as well as by genre**
- Requirement: Above the genres, the results filter shall carry a "Show:" row of
  four boxes, all ticked when first opened: Albums, DJ mixes, Series and Similar
  artists. A series heading shall be shown only with Series ticked; under an
  artist, a DJ mix only with DJ mixes ticked, any other album only with Albums
  ticked and the similar artists only with Similar artists ticked. A heading left
  with nothing under it shall not be shown (FR-D75). The kinds apply after the
  genres and with no genre ticked. The Filter press shall be offered once either
  the genres or the kinds would hide anything; Clear shall untick every genre and
  tick every kind; the button beneath the answer shall stay pressed in while
  either filter is on.
- Rationale: With series and DJ mixes offered in number, an answer needs
  separating by what each thing is (Oliver's ruling).
- Acceptance: Given an answer with an artist holding a mix, an album and a
  similar artist plus a series heading, when Series is cleared, then only the
  artist's heading shows; when DJ mixes is cleared, then the artist's mix goes
  while the series keeps its mixes; when only Series is ticked, then only the
  series heading shows; given the chooser opened with no genre ticked, when one
  kind is cleared, then Filter can be pressed.
- Verified by: `tests/domain/test_showing.py`, `tests/ui/test_results_showing.py`

### 3.2 Non-functional requirements

**NFR-PRIV-001 What leaves the machine**
- Requirement: A discovery run shall send nothing but five kinds of value,
  together with the application's own User-Agent: the names of artists drawn from
  the ticked genres (or the artists such a name joins, FR-D53), less any trailing
  Discogs number; the catalogue identifiers the sources answered with, whether
  for those artists, for the candidates the similarity source suggested or for
  the release groups and series a series question found; where MusicBrainz knows
  a name under several artists, up to `MOST_EVIDENCE` album or track titles the
  library holds under that name, each cut at its first bracket and sent to
  MusicBrainz alone beside that name (FR-D09); while other volumes of series are
  included, the titles of series albums inside the ticked genres (for an album
  filed under an artist, the catalogue's own title for it, FR-D82), each cut at
  its first bracket, spaced solidus or spaced dash, with the series stem of each
  such title, each sent to MusicBrainz alone (FR-D69, FR-D70); fixed values each
  client states for itself, being the response format, a result limit, where a
  following page starts, the release types, the genres inclusion, the relations
  asked for and the similarity algorithm. The headers carry only where the
  request goes, the User-Agent, the transport's own terms and a language fixed at
  any (`ACCEPT_LANGUAGE` in `infrastructure/fetching.py`).
- Rationale: Nothing outward may carry the library or name the listener; genre
  scoping means a run names a chosen subset rather than an inventory. The
  language is fixed because Qt otherwise adds the system locale.
- Verification:
  `tests/infrastructure/test_what_leaves_the_machine.py::test_a_field_holds_the_name_the_identifier_or_a_constant`
  puts the identity, releases, genres, credit and similarity questions through a
  recording fetcher and asserts each field holds the artist name (alone or beside
  a held title), the identifier or a constant the client states for itself. The
  series questions (`infrastructure/catalogue_series.py`) are held the same way,
  a held title's volume title and its stem being the only values allowed in the
  query. Each was proved to bite by planting an extra field or a title carrying
  more than was held. The headers are read where
  they arrive, on a loopback service:
  `tests/infrastructure/test_fetching.py::TestAskingAService::test_no_header_says_anything_about_the_listener`.

**NFR-PRIV-002 No identifier of the listener or the machine**
- Requirement: A discovery run shall send no account, no installation identifier,
  no machine name, no file path and no library statistic.
- Rationale: The application has no account and no telemetry; this must not be
  the feature that introduces one by accident.
- Verification:
  `tests/infrastructure/test_what_leaves_the_machine.py::test_every_field_sent_is_one_its_address_is_allowed`
  with `::test_every_address_asked_is_one_the_allowed_set_names` hold every
  request the test asks (the FR-D09 credit question and the series questions
  included) against a fixed allowed set of addresses and fields, so an added
  field fails; a new question is caught only once the test asks it.
  `::test_nothing_sent_names_the_listener_or_the_machine` reads each request
  against this machine's name, the user name and the home directory.

**NFR-PRIV-003 The User-Agent names the application, never the person**
- Requirement: The catalogue source shall send a User-Agent naming Stellody, its
  version and a project contact address, as MusicBrainz requires, with nothing
  about the listener.
- Verification: `tests/structural/test_user_agent.py` asserts from the source
  that `USER_AGENT` in `infrastructure/courtesy.py` is built from `APP_NAME` and
  `__version__` out of the version module plus a literal `CONTACT`, with no call
  and no other name in it. It also asserts the fetcher's one User-Agent header
  is that constant.

**NFR-PERF-001 Request pacing**
- Requirement: The discovery service shall issue at most one request per second
  per source host, measured over any ten second window.
- Rationale: MusicBrainz declines above one per second per IP and ListenBrainz
  states the same limit.
- Verification:
  `tests/infrastructure/test_fetching.py::TestAskingAService::test_it_waits_its_turn_and_names_the_application`
  asserts that every request passes through the pacing gate, whose gap is
  `REQUEST_GAP_S` in `infrastructure/courtesy.py`; the spacing itself rests on
  that constant. Every client asking MusicBrainz (the run, an expansion and the
  cover search) is given the one gate, held by
  `tests/ui/test_discovery_composition.py::test_everything_asking_musicbrainz_waits_at_one_gate`.

**NFR-PERF-002 Run duration**
- Priority: Won't
- Withdrawn: no target duration for a whole-library run. The figure is a property
  of two public services on the day they are asked and nobody will time it, so it
  would read as held while unverified; pacing is NFR-PERF-001 and the time left
  comes from the run's own pace (FR-D36) (Oliver's ruling).

**NFR-PERF-003 The candidate genre budget**
- Requirement: The discovery service shall look up a candidate artist's genre at
  most once per run, however many source artists name that candidate, then retain
  what it learned for reuse by later runs.
- Rationale: The similarity source returns identifiers with no genre, so
  filtering candidates costs one lookup each; deduplication is what makes the
  filter affordable (OQ-04).
- Verification:
  `tests/application/test_discovery.py::test_a_candidate_artist_is_asked_about_once`
  gives two source artists one shared candidate and asserts one genre lookup
  rather than two.

**NFR-USE-001 The toolbar bar can be read**
- Requirement: The text on the discovery bar shall hold a contrast ratio of at
  least 4.5 to 1 against both the filled and the unfilled part of that bar, in
  both appearances. The filled part shall be distinguishable from the groove by at
  least 3 to 1, either by the fill itself or by an edge drawn round it reaching
  that against both the fill and the groove.
- Rationale: A bar carries one colour of text across two backgrounds, so both are
  measured. In the dark appearance a fill dark enough for white writing cannot
  also stand off the near-black groove, so the boundary is drawn as an edge.
- Acceptance: Given either appearance, when the colours are measured by the WCAG
  relative luminance formula, then text against fill and text against groove each
  reach 4.5; either fill against groove reaches 3 or the edge reaches 3 against
  both the fill and the groove.
- Verified by: `tests/ui/test_progress_contrast.py`

**NFR-USE-002 The results dialog can be read**
- Requirement: Every colour the results dialog uses for text, the two artist
  colours FR-D34 requires included, shall hold a contrast ratio of at least 4.5 to
  1 against the surface behind it, in both appearances.
- Rationale: Two colours that differ from each other are not thereby two colours
  that can each be read.
- Acceptance: Given either appearance, when each text colour is measured against
  its surface by the WCAG relative luminance formula, then every ratio reaches
  4.5.
- Verified by: `tests/ui/test_results_contrast.py`

**NFR-MAINT-001 The gate**
- Requirement: Every module added by this work shall sit inside the existing
  coverage gate at 100% branch for the domain and application layers and keep to
  the line cap of C-05.
- Verification: `.\gate.ps1`, read by exit code.

**NFR-MAINT-002 The suite never reaches the network**
- Requirement: No test shall make a request that leaves the machine. The
  application layer reaches every source through an interface it declares, which
  its tests fill with a hand-written fake. The clients behind those interfaces
  are tested over hand-written fetchers; the fetcher itself is tested against an
  HTTP server on the loopback address
  (`tests/infrastructure/fetching_support.py`).
- Rationale: The house rule against mock libraries; a suite depending on a third
  party fails on their bad day. What Qt makes of a status and a silence can only
  be tested against a real server, which loopback provides without leaving the
  machine (Oliver's ruling).
- Verification:
  `tests/structural/test_offline.py::test_no_test_holds_the_machinery_to_reach_the_network`
  scans the whole test tree with the reader the package scan uses; the modules
  permitted the machinery are named with their reasons in `TESTS_PERMITTED`.
  `::test_every_permitted_test_module_exists_and_still_needs_it` keeps that set
  from outliving its reasons.

**NFR-REL-001 Nothing is written into the music folder**
- Requirement: The discovery file, the candidate genre cache, the catalogue
  memory and the running record each of those memories keeps shall be written
  inside Stellody's own data directory and nowhere else.
- Verification: `tests/structural/test_discovery_paths.py` asserts from the source
  that every place `infrastructure/discovery_file.py` and
  `infrastructure/catalogue_memory.py` name is `paths.data_dir()` with a named
  file under it, that neither names a directory of its own and that every call to
  the running record (`journal`) or the atomic writer (`_written`) is handed one
  of those places. A read made straight off a path is not inspected.

### 3.3 External interfaces

**The catalogue source** answers four questions: the identifier for an artist
name; the artists credited on a held album or track title under a name (FR-D09);
the albums an artist made with their stated genres; the genres an artist is
said to play. While other volumes of series are included it answers three more
(FR-D69, FR-D70) through its own client in `infrastructure/catalogue_series.py`:
which series a held title's release group belongs to; what one series holds, in
order; which release groups a search for a series stem finds. **The similarity
source** answers one: the artists similar to an identifier.

Both are reached through interfaces declared in the application layer, so the
choice below is reversible without touching a requirement above.

**Decision: MusicBrainz for the catalogue, ListenBrainz for similarity.**

| | MusicBrainz | ListenBrainz | Discogs | Last.fm |
|---|---|---|---|---|
| Albums by an artist | yes | no | yes | weaker |
| Similar artists | no such endpoint | yes | no such endpoint | yes |
| Genre on results | yes | no | per release lookup | tags |
| Credential | none | none | token | key |
| Rate | 1 per second | 1 per second | 60 per minute | 5 per second |
| Terms | core data CC0 | MetaBrainz | token | non-commercial only |

Neither catalogue source has a similarity relation, so two sources are
required. Discogs and Last.fm are excluded by C-07, since a credential compiled
into a GPL application is a published one; Last.fm's non-commercial condition
would also bind everyone who forks the project. MusicBrainz asks only for a
User-Agent naming the application (NFR-PRIV-003).

### 3.4 Data

The discovery file is **one JSON object, beside the database in Stellody's own
data directory, replaced by every completed run**, written by
`infrastructure/discovery_file.py`. Not a directory of dated files, which
becomes a thing to tidy; not a merge, which would have to rule on a candidate
offered once and owned since. A run states what is missing at the moment it
finished.

Its `gaps` member maps each source artist to what that artist is missing:
candidate albums and candidate artists. Each album carries its first release
date under `released`, empty where the catalogue stated none. An entry naming a
series rather than an artist carries `series` set true (FR-D74). Beside `gaps`
it carries six things: `unresolved` (FR-D08), `ambiguous` (FR-D09), `failed`
(FR-D22), `ticked`, the genres the run was scoped to (FR-D41), `years`
(FR-D64) and `including` (FR-D85), which holds `credits`, `series` and `mixes`
as true or false. The reader is forgiving: a file without `ticked` reads as an
empty list; one without `including` reads as the first two false and `mixes`
true.

### 3.5 What makes two albums the same album

This is what FR-D11 means by an album the library already holds.

**The principle.** An EDITION qualifier describes the pressing. A PERFORMANCE
qualifier describes the recording. The same recording in a different pressing
is the same album; a different recording is a different album. A remaster is
therefore the same album; a live version is not.

**The source side arrives clean.** A MusicBrainz release group is the abstract
album, with its remasters, deluxe editions and country pressings held inside it
as releases. The edition noise exists only in the library, because a ripper
wrote it into a tag.

**`AlbumIdentity` is not touched.** Its handle keys the artwork cache, the album
rating, every track rating and every accepted correction. Matching gets its own
pure module built on the same `comparison_key` primitive, so the two cannot
drift on normalisation.

**The year is deliberately absent from the key.** A remastered album's tag
carries the remaster's year while the release group carries the original's.
The artist is fixed for the comparison, since one source artist's releases are
matched against that same artist's held albums.

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

It is an allowlist on purpose: stripping any trailing segment unless it names a
different recording would destroy titles such as `L.I.F.E. (Love Is for Ever)`
and `The Death of Slim Shady (Coup de Grâce)`. The terminal words catch
editions carrying one unlisted word (`Tenth Anniversary Edition`); the type
markers stop `- EP` and `- Single` titles becoming false gaps.

**A title word merely restating a stated type is noise**, on both sides. The
library reads its kinds out of the title and then takes the qualifier off; the
catalogue takes its kinds as data and drops any trailing word that only repeats
one of them. Both sides arrive as a key plus a kind, so `Secret World (Live)`
meets `Secret World Live` typed Live. A record actually titled `Live` keeps its
title rather than reducing to nothing.

**The source's own types do the rest.** A release group's identity for matching
is its release key together with its secondary types, so a live album never
suppresses the studio album of the same name and is never suppressed by it.
Offered: primary type Album and EP, plus the secondary types Live, Remix and
Demo, which are genuinely different records, plus a DJ-mix whether or not it
also states Compilation, while DJ mixes are included (FR-D80, FR-D85).
Excluded: every other secondary type, Compilation without DJ-mix among them,
since a hits package of an artist already held is noise rather than a
discovery.

**What the rule does not do**, so it is not mistaken for covered: it does not
fold `&` to `and` and it does not strip diacritics, because `normalise` keeps
both deliberately and no miss caused by either has been observed. Artist names
are another matter: FR-D08 matches them on `catalogue_key`, which does set
accents aside; album titles are not matched that way. It is also untested
against titles as MusicBrainz spells them, which is one reason the smallest
genres are run first.

## 4. Prioritisation

Must: FR-D01 to FR-D14, FR-D16 to FR-D86 and every NFR except NFR-PERF-002.
Should: FR-D15.
Could: nothing this stage.

Won't, this time, recorded so it is not re-proposed: NFR-PERF-002; any purchase
path; ranking candidates by anything beyond what a source states; remembering
across runs what was offered and rejected; reopening a past run's results from
the menu, which FR-D28 makes cheap to add later; year presets, decade buttons
or a slider beside the two fields of FR-D58; narrowing a finished answer by
year on the results screen, where FR-D54 narrows by genre.

## 5. Open questions

Nothing marked open may be built from. Each is Oliver's unless stated.

| # | Question | Owner |
|---|---|---|
| OQ-04 | Answered: deduplicating shared candidates and dropping held ones brings a whole-library run's genre lookups to about a quarter of one per suggestion; the candidate genre cache then answers later runs instead of asking. | Answered |
| OQ-07 | Answered: the similarity half depends on the labs endpoint with no fallback (Oliver's ruling). A refusal that outlasts its asks raises `SourceRefused` and puts that artist back for a later pass (FR-D21); any other failure raises `SourceFailed` and is recorded against that artist (FR-D22); both are caught in `application/artist_stage.py`. | Answered |

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
