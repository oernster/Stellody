# Discovering music the library does not hold

The specification for the first stage of discovery. It is built; one diagnostic
in section 6 is not yet met. Where this document and the code disagree, the
document is amended; every requirement names the test that holds it.

## 1. Introduction

### 1.1 Purpose

A run reads the library, asks two public catalogues what is missing around it
and writes the answer down as data.

### 1.2 Scope

In scope: a toolbar button; a dialog carrying the genre catalogue; a run over
the artists in the ticked genres (plus, as the Include boxes ask, the artists on
those genres' compilations and other volumes of their series); a JSON file of
what it found; a results dialog on that file, filtered by genre, kind and year;
taste profiles shared by the three genre dialogs; years in both genre choosers.

Out of scope: buying anything (stage two, `SHOPS.md`; this stage never fetches,
prices or buys a record); recommending by anything but what is held; writing to
a music file; sending anything that identifies the listener or the machine
(NFR-PRIV-001, NFR-PRIV-002); any results cache beyond the candidate genre cache
(NFR-PERF-003) and the catalogue memory (FR-D46).

### 1.3 Definitions

| Term | Meaning |
|---|---|
| **Catalogue genre** | A name in `stellody.domain.genres.GENRES`, main or style. |
| **Resolved genre** | An album's genre as the library shows it: the probed tag with any album edit over it; never the raw `sources.genre` column. |
| **Ticked genres** | The catalogue genres ticked in the discovery dialog. |
| **Source artist** | An artist a run looks up: the album artist of a held album whose resolved genre names a ticked genre; for a compilation, only while FR-D51 includes them, each track credit instead; each artist a name joins once the whole name finds nobody (FR-D53). Never a compilation marker ("Various Artists", "Various", "VA" or "Verschiedene"). |
| **Compilation** | A held album whose album artist names various artists, as `AlbumIdentity.is_compilation` decides. |
| **Track credit** | One of a track's artists, split as the library splits them for playback. |
| **Placeholder artist** | An album artist the catalogue identifies as exactly one artist with no album and no EP, such as "Global Underground". |
| **Series album** | While series are included (FR-D85): a held album in the ticked genres that is a compilation or is filed under a placeholder artist; also one filed under an artist whose discography types it Compilation or DJ-mix (FR-D82), asked about by the catalogue's title for it. |
| **Series stem** | A title cut at its first bracket, first " / " and first " - "; then, where FR-D81 reads a number before a colon as the volume, cut before that number, else with a trailing number marker removed ("#7", "No. 7", "Vol. 7", "Volume 7", "Part 7", "Pt. 7", a bare "7" or a number word from "One" to "Twenty"). Compared on `comparison_key`. "Global Underground: Afterhours 4 - Ibiza / Unmixed" has the stem "Global Underground: Afterhours" and the number 4. |
| **Series** | A named run of release groups: the catalogue series topped up with every release group sharing the series album's stem; where the album is in no catalogue series, those release groups alone, named by the stem. |
| **Candidate album** | An album a source gives for a source artist that the library does not hold. |
| **Candidate artist** | An artist a source gives as similar to a source artist, not held. |
| **Release key** | What two albums are judged the same on (section 3.5): the normalised title without edition qualifiers; never the year. |
| **Discovery run** | One press of the action button through to one of four endings: completed, nothing to ask, stopped or unavailable. |
| **Discovery file** | The JSON a run writes. |

### 1.4 References

`SHOPS.md` (stage two); `ARCHITECTURE.md` (layering and purity invariants); the
MusicBrainz API and its rate limiting document; the ListenBrainz API, including
the labs similar-artists endpoint.

## 2. Overall description

**Perspective.** A client of the application layer like every other dialog.
Neither catalogue client holds a socket: both ask through
`infrastructure/fetching.py`, one of the four modules Invariant 12 of
`ARCHITECTURE.md` permits.

**User.** One class: a listener with a tagged library on their own machine.

**Environment.** Windows, macOS and Linux; outbound HTTPS during a run.

**Constraints.**

- **C-01** The library folder is never written to, cache included.
- **C-02** No music file is ever modified.
- **C-03** Nothing leaves the machine that names the listener or the machine.
- **C-04** The domain layer stays pure: no I/O, no framework, no clock.
- **C-05** Modules stay at or below `LINE_CAP` lines; one in the danger band is
  reduced to `COMFORTABLE_TARGET` (`tests/structural/test_loc.py`).
- **C-06** Domain and application hold 100% branch coverage.
- **C-07** No credential is compiled in, so no source needing an API key is
  used (section 3.3).

**Assumptions.**

| # | Assumption | Owner | Status |
|---|---|---|---|
| A-01 | Both catalogues answer artists, albums and similar artists with no credential. | Oliver | Confirmed by a live run |
| A-02 | The labs similar-artists endpoint answers; it gets no fallback (OQ-07). | Oliver | Confirmed by a live run |
| A-03 | A listener accepts that a run names their source artists to two public catalogues, scoped by the ticked genres. This covers names only, not the held titles NFR-PRIV-001 also lets a run send (FR-D09, FR-D69, FR-D70, FR-D82). | Oliver | Accepted with genre scoping |

## 3. Requirements

Every requirement is a Must unless it carries a Priority line (section 4). An
album naming no catalogue genre is never source material, whatever is ticked;
the listener states a genre for it in the tag editor. Neither a "not tagged"
tick nor an untagged sweep under select-all is wanted (Oliver's ruling).

### 3.1 Functional requirements

**FR-D01 Reaching the feature**
- Requirement: The toolbar shall carry a discovery button left of the appearance
  toggle, with the separator between library and application controls to its
  right and the FR-D43 button between the two. The File menu carries
  `Discover new music...`, calling what the button calls (stopping a run during
  one, FR-D23), enabled exactly when the button is, read each time it opens.
- Verified by: `tests/ui/test_discovery_button.py::test_discovery_sits_left_of_the_appearance_toggle`, `tests/ui/test_menu_mirrors.py::test_an_entry_is_offered_exactly_where_its_button_is`

**FR-D02 The ring follows the button**
- Requirement: The discovery button shall sit in the keyboard ring at its visual
  position.
- Verified by: `tests/ui/test_discovery_button.py::test_discovery_is_reachable`

**FR-D03 Choosing what to look for**
- Requirement: The discovery button shall open the discovery dialog showing the
  filter dialog's genre catalogue. As the application opens, the window builds
  that dialog once, unseen, then discards it.
- Rationale: The first build is slow enough to starve the sound device.
- Verified by: `tests/ui/test_discovery_dialog.py::test_grid_matches_the_catalogue`, `tests/ui/test_discovery_warm.py::test_building_ahead_shows_nothing_and_leaves_nothing`

**FR-D04 Nothing ticked, nothing to do**
- Requirement: While no genre is ticked, the dialog's action button shall be
  disabled.
- Verified by: `tests/ui/test_discovery_dialog.py::test_action_needs_a_genre`

**FR-D44 Every genre can be ticked in one press**
- Requirement: A push button where the filter dialog's Clear sits shall tick
  every genre; where all are already ticked it clears them all. It names what a
  press would do, read from the boxes. It wears `select-all.png` at the shared
  dialog control size; clearing adds the shared negative mark at run time. A
  press neither closes the dialog nor starts a run.
- Verified by: `tests/ui/test_discovery_dialog.py::test_the_sweep_ticks_every_genre_in_one_press`, `tests/ui/test_discovery_dialog.py::test_a_second_press_clears_them_again`, `tests/ui/test_discovery_dialog.py::test_the_sweep_says_what_a_press_would_do`, `tests/ui/test_discovery_dialog.py::test_ticking_the_last_box_by_hand_moves_the_sweep_too`, `tests/ui/test_discovery_dialog.py::test_the_sweep_is_a_button_rather_than_a_tick_box`, `tests/ui/test_discovery_dialog.py::test_sweeping_leaves_the_dialog_open`, `tests/ui/test_discovery_dialog.py::test_the_sweep_wears_its_own_artwork_at_the_shared_size`, `tests/ui/test_discovery_dialog.py::test_clearing_wears_the_same_picture_struck_through`, `tests/ui/test_discovery_dialog.py::test_the_picture_goes_back_when_there_is_something_to_tick_again`

**FR-D05 Who a run asks about**
- Requirement: A run's source artists shall be the album artists of held
  non-compilation albums whose resolved genre names a ticked genre; with FR-D51
  ticked, also the track credits of such compilations. A compilation marker is
  never one. Names differing only in case or spacing are one source artist,
  asked about once under the first spelling met, their holdings compared as one
  on `comparison_key`.
- Verified by: `tests/application/test_discovery.py::test_one_artist_spelled_two_ways_is_asked_about_once`, `tests/domain/test_one_artist_two_spellings.py`, `tests/application/test_discovery.py::test_sources_read_the_resolved_genre`, `tests/domain/test_stating_an_album.py::TestWhoADiscoveryAsksAbout::test_a_genre_stated_over_an_untagged_album_decides`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_is_asked_about_by_its_track_credits`, `tests/domain/test_discovery_gaps.py::test_a_compilation_left_out_asks_about_nobody`, `tests/domain/test_discovery_gaps.py::test_various_artists_is_never_a_source_artist`, `tests/domain/test_discovery_gaps.py::test_an_included_compilation_outside_the_ticks_is_not_asked_about`

**FR-D51 Compilations are included only when asked for**
- Requirement: The dialog shall carry the box "Artists on compilations (Various
  Artists)", first of the Include boxes (FR-D85), between the genres and the
  buttons: unticked on first opening, then as last left, its state handed to the
  run.
- Rationale: Compilation credits can add hundreds of names (Oliver's ruling).
- Verified by: `tests/ui/test_discovery_compilations.py::test_three_boxes_start_as_a_run_that_widens_to_nothing`, `tests/ui/test_discovery_compilations.py::test_the_run_is_told_what_else_to_take_in`, `tests/ui/test_discovery_compilations.py::test_the_choices_are_remembered_between_openings`, `tests/ui/test_discovery_compilations.py::test_the_boxes_sit_between_the_genres_and_the_buttons`

**FR-D52 The cost of including compilations is stated before a run**
- Requirement: Beneath the Include boxes the dialog shall state what a run would
  newly look up and the minutes that adds at NFR-PERF-001's pace
  (`REQUESTS_PER_SOURCE_ARTIST` an artist, `REQUESTS_PER_SERIES` a series). The
  artists box counts track credits on compilations in the ticked genres that a
  run without compilations would not ask about and the catalogue memory holds no
  standing answer for. The series box also counts FR-D84's series, each once,
  where a held album of it in the ticked genres has no standing series answer.
  Placeholders are recognised from the memory alone. With neither ticked nothing
  is said. It is restated on every tick change, once for a FR-D44 press. It
  reads, for example, "3 artists and 2 series on compilations in these genres
  have not been looked up yet: under a minute more at the pace MusicBrainz
  allows, longer when it is busy."
- Rationale: The minutes are arithmetic, not a forecast (Oliver's ruling).
- Verified by: `tests/application/test_compilation_cost.py::test_only_names_not_yet_looked_up_are_counted`, `tests/application/test_compilation_cost.py::test_an_answer_past_its_life_is_counted_again`, `tests/application/test_compilation_cost.py::test_a_credit_a_run_would_ask_about_anyway_costs_nothing`, `tests/application/test_compilation_cost.py::test_the_time_is_priced_at_the_permitted_pace`, `tests/ui/test_discovery_compilations.py::test_the_cost_follows_the_ticks`, `tests/ui/test_discovery_compilations.py::test_nothing_new_to_ask_says_so`, `tests/application/test_compilation_cost.py::test_a_series_is_priced_once_however_many_volumes_are_held`, `tests/application/test_compilation_cost.py::test_a_placeholder_the_memory_knows_brings_its_series`, `tests/ui/test_discovery_compilations.py::test_the_sentence_names_the_series_too`, `tests/ui/test_discovery_compilations.py::test_the_price_is_asked_for_the_boxes_ticked`, `tests/ui/test_discovery_compilations.py::test_nothing_costly_ticked_says_nothing`, `tests/ui/test_discovery_compilations.py::test_select_all_prices_once_rather_than_once_a_box`

**FR-D53 A name nobody is found under is asked about by its parts**
- Requirement: Where a source artist's name reaches nobody and joins artists
  with an ampersand, a comma, a solidus spaced on both sides or "Featuring"
  ("feat.", "ft."), each joined artist shall become a source artist in the same
  run. The whole name is then not reported unrecognised; a part reaching nobody
  is. A part already a source artist is not asked about twice.
- Rationale: Eli & Fur is one duo and a bare solidus belongs to AC/DC (Oliver's
  ruling).
- Verified by: `tests/domain/test_text.py::test_a_credit_naming_several_artists_comes_apart`, `tests/domain/test_text.py::test_a_credit_naming_one_artist_has_no_parts`, `tests/application/test_discovering_compilations.py::test_an_unrecognised_credit_is_asked_about_by_its_parts`, `tests/application/test_discovering_compilations.py::test_a_recognised_credit_is_not_split`, `tests/application/test_discovering_compilations.py::test_a_part_nobody_knows_is_reported_unrecognised`, `tests/application/test_discovering_compilations.py::test_a_part_already_asked_about_is_not_asked_again`, `tests/application/test_discovering_compilations.py::test_an_album_artist_nobody_knows_is_asked_about_by_its_parts`, `tests/application/test_discovering_compilations.py::test_an_album_artist_known_whole_is_not_split`, `tests/domain/test_catalogue_names.py::test_a_spaced_solidus_is_a_join`, `tests/domain/test_catalogue_names.py::test_a_bare_solidus_belongs_to_the_name`, `tests/domain/test_catalogue_names.py::test_a_featured_guest_comes_apart`, `tests/domain/test_catalogue_names.py::test_featuring_inside_a_word_is_not_a_join`

**FR-D06 No source artists**
- Requirement: If the ticked genres yield no source artist (nor series album
  while series are included), the status bar shall say so; nothing is requested
  or written.
- Verified by: `tests/application/test_discovery.py::test_no_sources_makes_no_request`, `tests/ui/test_discovery_wiring.py::test_nothing_to_ask_says_so`; the series album exception by `tests/application/test_discovering_series.py::test_a_compilation_brings_its_series`, whose compilations credit only Various Artists and whose run still completes

**FR-D07 Finding the artist**
- Requirement: Each source artist's identifier shall be requested by name.
- Verified by: `tests/application/test_discovery.py::test_identity_is_requested_once`

**FR-D08 An artist the source does not know**
- Requirement: If the catalogue returns no identifier, the artist shall be
  recorded unresolved and the run moves on. Names match once case, accents and
  typographic dashes are set aside (`catalogue_key`); a trailing Discogs number
  such as "(10)" is left out of the query. Identity answers are kept under
  `IDENTIFIERS` (`application/remembering.py`); the older case-only section is
  never read.
- Rationale: Tags are typed by hand; the library's own key stays strict.
- Verified by: `tests/application/test_discovery.py::test_unknown_artist_is_recorded`, `tests/domain/test_catalogue_names.py::test_a_typed_name_matches_what_the_catalogue_writes`, `tests/domain/test_catalogue_names.py::test_the_library_key_stays_strict`, `tests/domain/test_catalogue_names.py::test_a_discogs_number_is_not_asked_for`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_name_typed_without_its_accents_is_the_artist`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_discogs_number_is_left_out_of_the_search`, `tests/infrastructure/test_remembered_credits.py::test_the_retired_section_is_not_read`

**FR-D09 An ambiguous name**
- Requirement: If several identifiers come back, the service shall ask who is
  credited on up to `MOST_EVIDENCE` titles held under the name, albums first.
  Where the first title crediting any of them credits exactly one, that is the
  source artist; otherwise the name is recorded ambiguous with every candidate
  identifier and nothing more is asked. The rule is in `application/settling.py`;
  the catalogue memory keeps its answers.
- Verified by: `tests/application/test_discovery.py::test_ambiguous_name_is_reported`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_two_exact_matches_are_both_returned`, `tests/infrastructure/test_discovery_sources.py::TestIdentifyingAnArtist::test_a_ranked_near_miss_is_not_the_artist`, `tests/application/test_settling_ambiguity.py`, `tests/domain/test_credit_evidence.py`, `tests/infrastructure/test_discovery_sources.py::TestWhoIsCreditedOnATitle`, `tests/application/test_remembering.py::TestAskingOnlyWhatIsUnknown::test_a_credit_is_asked_for_once_then_remembered`

**FR-D10 Albums by an artist already held**
- Requirement: For an identified source artist the service shall request their
  albums with stated genres, `GROUP_LIMIT` a page (`infrastructure/catalogue.py`),
  the next page only after a full one, up to `MOST_PAGES`.
- Verified by: `tests/application/test_discovery.py::test_albums_are_requested_with_genres`

**FR-D11 Never offering back what is owned**
- Requirement: The service shall discard every album whose release key and
  secondary types match an album held by that artist (section 3.5).
- Verified by: `tests/domain/test_discovery_gaps.py::test_held_albums_are_dropped`

**FR-D12 Artists like the ones held**
- Requirement: For an identified source artist the service shall request the
  `SIMILAR_WANTED` (`application/artist_stage.py`) most similar artists;
  `ListenBrainz.similar_to` (`infrastructure/similarity.py`) keeps the first that
  many it can name, since the endpoint takes no count.
- Verified by: `tests/application/test_discovery.py::test_similar_artists_are_requested`

**FR-D13 Never offering back an artist held**
- Requirement: The service shall discard every similar artist whose normalised
  name matches a held album's album artist; a track credit is not held.
- Verified by: `tests/domain/test_discovery_gaps.py::test_held_artists_are_dropped`

**FR-D14 The ticked genres filter what is collected**
- Requirement: A candidate album stating a recognised genre shall be discarded
  where none of its recognised genres is ticked.
- Verified by: `tests/domain/test_discovery_gaps.py::test_candidate_albums_respect_the_ticks`

**FR-D15 A candidate whose genre is unknown**
- Priority: Should
- Requirement: A candidate stating no recognised genre shall be kept, with
  `ReleaseGroup.states_no_genre` true.
- Verified by: `tests/domain/test_discovery_gaps.py::test_unstated_genre_is_kept_and_marked`

**FR-D16 Saying what is happening**
- Requirement: The toolbar shall carry three progress bars, for looking up
  artists, checking series (FR-D69, FR-D83) and checking styles, stacked in stage
  order and labelled by stage; checking years (FR-D63) is drawn on the styles bar
  under its own name. Each shows its own stage's percentage; a finished stage
  stays full and one not begun shows none (FR-D83). Hovering names the stage,
  the artist being asked about, that artist's place (completed plus one) and the
  stage's total.
- Rationale: A toolbar strip cannot hold a long artist name (Oliver's ruling).
- Verified by: `tests/ui/test_discovery_bar.py::test_there_is_a_bar_for_each_stage_of_a_run`, `tests/ui/test_discovery_bar.py::test_reaching_the_second_half_leaves_the_first_bar_full`, `tests/ui/test_discovery_bar.py::test_it_names_the_stage_rather_than_the_artist`, `tests/application/test_discovery_narrowing.py::test_the_second_half_of_a_run_reports_as_it_goes`, `tests/ui/test_results_series.py::test_the_series_stage_has_a_bar_of_its_own`, `tests/application/test_discovering_series.py::test_the_stage_says_how_far_it_has_got`

**FR-D17 Stopping**
- Requirement: On cancel the service shall stop before its next request, discard
  the run's gaps and leave any discovery file untouched, keeping catalogue
  answers received (FR-D48). The run is asked whether it is still wanted before
  every request, waits sliced so a stop lands inside one; the fetcher drops a
  request in flight, asking every `SLEEP_SLICE_S`. The run is abandoned, not
  waited for (FR-D27).
- Verified by: `tests/application/test_stopping_a_run.py::test_cancel_stops_before_the_next_request`, `tests/application/test_stopping_a_run.py::test_a_stop_is_felt_part_way_through_a_wait`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_request_nobody_wants_any_more_is_dropped_at_once`, `tests/infrastructure/test_discovery_sources.py::TestHandingTheQuestionDown::test_every_question_carries_whether_it_is_still_wanted`, `tests/application/test_stopping_a_run.py::test_a_stop_lands_between_requests_rather_than_between_artists`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_what_was_learned_is_kept_however_the_run_ended`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

**FR-D18 The output**
- Requirement: On completion the service shall replace the single discovery file
  (section 3.4): `gaps` keyed by source artist, each holding candidate albums and
  candidate artists, an offered series keyed by its name and marked a series
  (FR-D74); beside it the unresolved, ambiguous and failed artists, the ticked
  genres, the years (FR-D64; both bounds empty where unset) and the Include
  choices (FR-D85).
- Verified by: `tests/infrastructure/test_discovery_file.py::test_the_file_is_keyed_by_the_artist_it_was_found_for`

**FR-D19 The file cannot be written**
- Requirement: If the file cannot be written, the status bar shall give the
  reason; any previous file stays untouched.
- Verified by: `tests/ui/test_discovery_wiring.py::test_a_file_that_will_not_write_is_reported`, `tests/infrastructure/test_discovery_file.py::test_nothing_is_left_half_written`, `tests/infrastructure/test_discovery_file.py::test_a_write_that_fails_leaves_the_last_answer_as_it_was`

**FR-D20 The network is not there**
- Requirement: A request answered with nothing shall put the artist back for a
  later pass as a refusal does; an artist never answered is reported in words
  distinct from a refused one. Only `SILENCE_MEANS_GONE` silences in a row, with
  nothing answering between and counted across the run, stop the run, report the
  network unavailable and write no file. In the second half a candidate with no
  genre answer (silence, refusals outlasting the asks, an error or a stop) is left
  unknown, not recorded as playing nothing; an empty genre list is an answer and
  kept. A pooled connection idle beyond `IDLE_LIMIT_S` is thrown away rather than
  asked down; a run's pause lets it go once past that limit
  (`infrastructure/resting.py`).
- Rationale: Recording a question never answered would drop that candidate from
  every later run.
- Verified by: `tests/application/test_a_dropped_connection.py::test_one_dropped_connection_does_not_end_a_run`, `tests/application/test_a_dropped_connection.py::test_a_connection_that_has_gone_still_ends_the_run`, `tests/application/test_a_dropped_connection.py::test_an_answer_between_two_silences_starts_the_count_over`, `tests/application/test_a_dropped_connection.py::test_an_artist_nothing_ever_answered_about_says_that`, `tests/application/test_discovery_narrowing.py::test_a_candidate_nothing_answered_about_is_left_unknown`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_did_not_answer_is_not_remembered`, `tests/application/test_discovery_narrowing.py::test_a_candidate_that_answered_with_no_genres_is_remembered`, `tests/application/test_discovery_narrowing.py::test_a_connection_lost_in_the_second_half_ends_the_run`, `tests/infrastructure/test_a_closed_connection.py`

**FR-D21 The source refuses**
- Requirement: On a refusal the service shall ask again at once (`RETRY_ATTEMPTS`
  asks in all), then put the artist back for a later pass. Passes continue until
  none is owed, `QUIET_PASSES` passes running achieve nothing or `MOST_PASSES`
  are made (`application/passing.py`). An artist still owed is reported a failure
  in the words of its last pass: refused, else as FR-D20 or FR-D50 word it.
- Rationale: Waiting during other artists' turns costs nothing.
- Verified by: `tests/application/test_discovery.py::test_rate_refusal_is_retried`, `tests/application/test_discovery.py::test_an_artist_refused_on_one_pass_is_asked_about_on_the_next`, `tests/application/test_discovery.py::test_a_refusal_that_never_relents_becomes_a_failure`, `tests/application/test_passing.py`

**FR-D50 The source is still thinking when the wait runs out**
- Requirement: A request unanswered within `TIMEOUT_S`, connected or not, shall
  put the artist back for a later pass as a refusal does without counting towards
  FR-D20's silences. An artist too slow on every pass is reported in words
  distinct from refused and from never answered. In the second half a candidate
  whose genres came too late is left unknown.
- Verified by: `tests/application/test_a_slow_answer.py`

**FR-D22 The source fails for another reason**
- Requirement: On any other error the artist shall be recorded failed with the
  reason; the run continues and reports the failures.
- Verified by: `tests/application/test_discovery.py::test_other_errors_do_not_stop_the_run`

**FR-D42 An answer says who it could not answer for**
- Requirement: When a completed run lacks a usable answer for some artists,
  whether or not it found anything, its closing message shall count apart those
  that could not be asked about, names not recognised and names matching several
  artists, naming only kinds that happened. An artist carried over (FR-D46) has a
  usable answer. A stopped run, an unreachable one and an unwritten answer count
  nothing.
- Verified by: `tests/ui/test_shortfall.py::TestTheSentence`, `tests/ui/test_discovery_wiring.py::test_a_run_names_all_three_kinds_of_silence`, `tests/ui/test_discovery_wiring.py::test_only_the_groups_that_happened_are_named`, `tests/ui/test_discovery_wiring.py::test_finding_nothing_still_says_what_went_unanswered`, `tests/ui/test_discovery_wiring.py::test_a_stopped_run_counts_nothing`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

**FR-D43 The names themselves are one press away**
- Requirement: A picture button shall always sit immediately right of the
  discovery button, inside the rule before the appearance toggle. While nothing
  is owed it is disabled (with the disabled red ring), skipped by the keyboard
  ring, its tooltip `NOTHING_UNANSWERED_TIP`. When a run ends owing FR-D42's
  message it is enabled, the keyboard reaching it straight after the discovery
  button, wearing a red badge with a white figure top right counting the
  unanswered artists (capped at `BADGE_MOST` with `+`), repainted when the
  appearance changes; its tooltip states the count and what a press does. The
  File menu carries `Show unanswered artists...` after `Discover new music...`,
  calling what the button calls, enabled exactly when it is. A press opens a
  modal dialog listing the artists under a heading per kind, each with a plain
  sentence saying what it means, never the sources' reasons. The next run
  disables it. Enabling it moves no tray control.
- Rationale: Status bar text is soon replaced and does not read as a button
  (Oliver's ruling).
- Verified by: `tests/ui/test_unanswered_button.py`, `tests/ui/test_menu_mirrors.py::test_an_entry_is_offered_exactly_where_its_button_is`, `tests/ui/test_menu_sweep.py`, `tests/ui/test_badge.py`, `tests/ui/test_shortfall.py::TestTheButtonLabel`, `tests/ui/test_shortfall.py::TestTheList`, `tests/ui/test_shortfall.py::TestTheDialog`, `tests/ui/test_discovery_wiring.py::test_the_button_appears_carrying_its_own_count`, `tests/ui/test_discovery_wiring.py::test_one_unanswered_artist_reads_as_one`, `tests/ui/test_discovery_wiring.py::test_a_clean_run_offers_no_button`, `tests/ui/test_discovery_wiring.py::test_a_new_run_takes_the_last_one_s_button_away`, `tests/ui/test_discovery_wiring.py::test_pressing_it_opens_the_names`, `tests/ui/test_dialog_first_stop.py`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`

**FR-D23 One run at a time**
- Requirement: During a run the discovery button shall stop it rather than
  start a second; the runner refuses a second run itself.
- Rationale: Two runs would breach NFR-PERF-001 and race to replace one file.
- Verified by: `tests/ui/test_discovery_stopping.py::test_pressing_it_during_a_run_stops_the_run`, `tests/ui/test_discovery_wiring.py::test_the_runner_refuses_a_second_run`

**FR-D24 The application closes mid-run**
- Requirement: On quit during a run the window shall tell it to stop before its
  next request, then wait for it and every earlier abandoned run, at most
  `WAIT_MS` each (`ui/discovery_worker.py`); the stopped run leaves any discovery
  file untouched.
- Verified by: `tests/ui/test_quitting.py::test_quitting_mid_run_stops_the_discovery_run`, `tests/application/test_stopping_a_run.py::test_closing_stops_the_run`, `tests/infrastructure/test_discovery_file.py::test_a_run_with_nothing_to_say_cannot_replace_one_that_had`

**FR-D25 The dialog asks, then leaves**
- Requirement: Starting a run shall close the discovery dialog, which cannot
  report on, stop or detect a run.
- Verified by: `tests/ui/test_discovery_dialog.py::test_finding_closes_the_dialog`

**FR-D26 What a candidate plays is remembered**
- Requirement: The service shall keep what each candidate artist plays and not
  ask again where it holds an answer, still judging that answer against the
  run's own ticks.
- Verified by: `tests/application/test_discovery_narrowing.py::test_what_was_remembered_is_not_asked_about_again`, `tests/ui/test_discovery_composition.py::test_a_run_is_given_somewhere_to_remember_what_it_learns`

**FR-D27 Stopping is immediate**
- Requirement: The discovery button during a run shall stop it at once without
  asking, let go of the bar at once and ignore later reports; the run winds down
  on its own thread. During a run the button wears the shared negative mark with
  the tooltip "Stop discovery"; the mark comes off on every ending. Picture and
  words are set together in one place; the strings live in
  `stellody/ui/tray_metrics.py`, which the guide reads.
- Rationale: A button that plainly says stop needs no confirmation (Oliver's
  ruling).
- Verified by: `tests/ui/test_discovery_stopping.py::test_a_press_stops_at_once_without_asking_anything`, `tests/ui/test_discovery_stopping.py::test_the_button_wears_the_cross_while_a_run_is_under_way`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_is_stopped`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_finishes_on_its_own`, `tests/ui/test_discovery_stopping.py::test_the_cross_comes_off_when_a_run_fails`, `tests/ui/test_discovery_stopping.py::test_a_stop_lets_go_of_the_run_at_once`, `tests/ui/test_discovery_stopping.py::test_a_stop_is_instant_even_while_a_request_is_wedged`, `tests/ui/test_discovery_stopping.py::test_progress_reported_after_a_stop_does_not_revive_the_bar`

**FR-D28 The results are shown when a run completes**
- Requirement: On completion the window shall write the discovery file, say the
  run's message, then open the modal results dialog on what the file holds
  (FR-D33).
- Rationale: A screen left standing could show an answer a later run replaced
  (Oliver's ruling).
- Verified by: `tests/ui/test_results_dialog.py`, `tests/ui/test_discovery_wiring.py`

**FR-D29 What a source artist shows**
- Requirement: Each source artist the run found something for shall show once,
  with its candidate albums beneath.
- Verified by: `tests/ui/test_results_dialog.py::test_a_source_artist_carries_its_albums`

**FR-D30 What a candidate artist shows**
- Requirement: Each candidate artist shall show collapsed, no album beneath until
  expanded.
- Verified by: `tests/ui/test_opening_a_candidate.py::test_a_candidate_artist_starts_collapsed`

**FR-D31 A candidate artist's albums are fetched on demand**
- Requirement: Expanding a candidate shall show their releases passing section
  3.5's offering rule, fetched then (paged as FR-D10) through the catalogue
  memory. A run asks nothing about a candidate's releases unless years are set,
  when FR-D63 asks during the run and expanding reads that. A
  candidate with no identifier is asked about by nobody and says "The catalogue
  did not say which artist this is"; one with nothing to offer says "No albums
  worth offering".
- Rationale: Each request costs NFR-PERF-001's gap (Oliver's ruling).
- Verified by: `tests/ui/test_opening_a_candidate.py::test_expanding_a_candidate_asks_for_their_albums`, `tests/ui/test_opening_a_candidate.py::test_a_candidate_the_catalogue_could_not_name_says_so`, `tests/ui/test_opening_a_candidate.py::test_a_candidate_with_nothing_to_offer_says_that_rather_than_nothing`, `tests/application/test_expanding.py::test_everything_that_artist_made_is_offered`, `tests/application/test_expanding.py::test_a_hits_package_is_still_noise`, `tests/application/test_discovery_narrowing.py::test_a_run_never_asks_what_a_candidate_released`

**FR-D32 The lookup for an expanded artist cannot be made**
- Requirement: An expanded candidate's lookup shall be tried `OPENED_ATTEMPTS`
  times (`application/asking.py`), the wait doubling each time. On failure the
  row says what went wrong and that reopening it tries again; other entries are
  untouched.
- Verified by: `tests/ui/test_opening_a_candidate.py::test_a_failed_expansion_says_so_and_spares_the_rest`, `tests/ui/test_opening_a_candidate.py::test_an_artist_that_failed_is_asked_again_the_next_time_it_is_opened`, `tests/application/test_expanding.py::test_three_refusals_running_do_not_lose_the_artist`, `tests/application/test_expanding.py::test_a_source_refusing_every_time_is_that_artist_failing`, `tests/application/test_expanding.py::test_the_wait_between_asks_doubles`

**FR-D33 Every completed run opens its answer**
- Requirement: Every completed run shall write its answer and open the results
  screen on it, even with nothing found.
- Rationale: Nothing missing is an answer too (Oliver's ruling).
- Verified by: `tests/ui/test_results_dialog.py::test_a_run_that_found_nothing_still_shows_its_screen`, `tests/ui/test_discovery_wiring.py::test_a_run_that_found_nothing_still_writes_and_opens`

**FR-D34 A source artist and a candidate artist are told apart by colour**
- Requirement: Source and candidate artist names shall differ in colour, both
  from the theme's semantic tokens.
- Verified by: `tests/ui/test_results_dialog.py::test_the_two_kinds_of_artist_are_coloured_apart`

**FR-D39 The results say what they are showing**
- Requirement: A key shall name each kind of row beside a filled circle in its
  colour. A source row gives its number of albums, plus similar artists where
  any; a candidate row calls itself a similar artist, adding its number of albums
  once fetched.
- Verified by: `tests/ui/test_results_reading.py::test_the_key_names_all_three_kinds_in_their_own_colours`, `tests/ui/test_results_reading.py::test_a_source_row_says_how_many_of_each_sit_under_it`, `tests/ui/test_results_reading.py::test_a_candidate_row_says_that_it_is_an_artist`

**FR-D40 The results say when the catalogue is being asked**
- Requirement: While lookups are in flight a busy line shall name the artist
  asked about (their number where several); idle, its reserved place says how to
  fetch an artist's albums.
- Verified by: `tests/ui/test_results_reading.py::test_the_strip_names_who_is_being_asked_about`, `tests/ui/test_results_reading.py::test_the_strip_counts_them_when_several_are_in_flight`, `tests/ui/test_results_reading.py::test_the_strip_goes_quiet_when_the_last_answer_lands`

**FR-D41 The results say what the run looked in**
- Requirement: Above the key the dialog shall give the number and names of the
  run's genres, read from the file shown; a file naming none shows no line.
- Verified by: `tests/ui/test_results_reading.py::test_it_says_which_genres_the_run_looked_in`, `tests/ui/test_results_reading.py::test_one_genre_is_not_called_genres`, `tests/ui/test_results_reading.py::test_a_run_that_names_no_genres_shows_no_line_at_all`, `tests/ui/test_results_reading.py::test_the_genres_sit_above_the_key`, `tests/ui/test_results_dialog.py::test_the_genres_shown_come_from_the_file_it_is_showing`, `tests/application/test_discovery.py::test_a_completed_run_carries_what_it_was_asked_to_look_in`, `tests/infrastructure/test_discovery_results.py::TestWhatTheRunWasAskedFor`

**FR-D46 The same library answers the same way twice**
- Requirement: The service shall keep each catalogue answer against its question
  (identity, releases, similar artists, FR-D09's credits, FR-D69 and FR-D70's
  series) and ask again only where none is kept or it is older than
  `MEMORY_LIFE_DAYS` days; what a candidate plays is kept without limit. A run
  keeps what it learned however it ends. Where a run cannot reach a source about
  an artist an earlier run answered, the file keeps that answer and no failure;
  the closing message and unanswered count read the file's answer, so neither
  names the artist. An artist owed at the end with nothing ever known is written
  as unanswered. Gaps are written in order of the artist's name as written. When
  two holders save the memory over one another (a stopped run beside a new one;
  a run beside an opened candidate), every answer either learned is kept, the
  later winning a shared question; one lock covers every note, save and file
  write.
- Rationale: A run may add and correct, never remove because a service said no
  (Oliver's ruling).
- Verified by: `tests/application/test_remembering.py::TestTwoRunsOverOneLibrary::test_the_second_run_asks_the_catalogues_nothing`, `tests/application/test_remembering.py::TestAskingOnlyWhatIsUnknown`, `tests/application/test_remembering.py::TestHowLongAnAnswerStands`, `tests/application/test_remembering.py::TestCarryingAnAnswerOver`, `tests/infrastructure/test_discovery_file.py::test_an_answer_with_a_hole_in_it_is_written_with_the_hole_named`, `tests/infrastructure/test_discovery_file.py::test_an_artist_already_answered_for_is_not_a_hole`, `tests/infrastructure/test_discovery_file.py::test_the_artists_are_written_in_one_order_however_they_arrived`, `tests/ui/test_discovery_wiring.py::test_a_run_with_a_hole_in_it_still_opens_its_answer`, `tests/infrastructure/test_catalogue_memory.py::test_what_is_kept_comes_back_exactly`, `tests/ui/test_a_carried_answer_is_not_a_shortfall.py::test_an_artist_carried_over_is_not_called_unanswered`, `tests/application/test_merging_recollections.py`, `tests/infrastructure/test_overlapping_memory.py`, `tests/ui/test_discovery_composition.py::test_everything_keeping_catalogue_answers_shares_one_memory`

**FR-D48 An answer is written down the moment it arrives**
- Requirement: Each catalogue answer and each candidate genre answer shall be
  appended to a running record as it arrives and forced to disk. Both memories
  read as their file plus that record; a record is dropped only once its file
  holds what it held. The candidate genre cache is written once the second half
  has asked about every candidate. The catalogue memory is read once a session,
  on its own thread as the application opens, then held: saves and expansions
  update what is held, writing nothing; the file is written whole once, at
  quit, if anything new was learned. Each caller gets a copy.
- Rationale: Whole-file reads and writes stall the interpreter enough to starve
  the sound device.
- Verified by: `tests/infrastructure/test_a_dead_run_keeps_what_it_learned.py`, `tests/infrastructure/test_journal.py`, `tests/infrastructure/test_held_memory.py`, `tests/application/test_remembering.py::TestAnAnswerIsKeptTheMomentItArrives`, `tests/application/test_discovery_narrowing.py::test_each_candidate_is_written_down_as_it_is_answered`

**FR-D47 A failure is said in words somebody can act on**
- Requirement: A failed lookup shall be described in plain words chosen by the
  kind of failure, naming no address, exception class or status code; the diary
  gets the class, the message and the artist's catalogue identifier.
- Verified by: `tests/ui/test_results_reading.py::TestSayingWhyInWords`, `tests/ui/test_expansion_worker.py::test_the_row_gets_words_and_the_log_gets_the_machine`, `tests/infrastructure/test_fetching.py::TestGivingUpOnARequest::test_a_service_that_never_answers_is_given_up_on_anyway`

**FR-D49 The answer is turned a page at a time**
- Requirement: The results dialog shall deal source artists into pages, every
  column of a page filled except on the last page; column depth follows the
  dialog's height. An artist taller than that fills its column and scrolls,
  never dropped or divided, sharing its page where there are more columns. Two
  pager controls each wear their own artwork, struck through where that way leads
  nowhere, with words between saying which page of how many. One foot row
  beneath the answer reads Close on the left, the pager, then Filter (FR-D54),
  Copy and Find in shops on the right (Oliver's ruling); Tab walks it in that
  order. The pager is centred, Close and the right controls each in a side
  sharing the rest equally; where the right side needs more than half it keeps
  its width and the pager stands as near the middle as it can
  (`ui/results_foot.py`). All pages are built on opening and kept, so ticks hold
  across pages.
- Rationale: The rows a column holds at the ceiling are a stated figure
  (`ROWS_AT_THE_CEILING`, `ui/results_room.py`), the row height following from
  it, because the offscreen platform cannot measure fonts; correct it from a
  real screen.
- Verified by: `tests/ui/test_results_pages.py`, `tests/ui/test_results_foot.py`, `tests/ui/test_results_keyboard.py::TestTheRing`, `tests/ui/test_shop_choosing.py::test_a_tick_holds_across_pages_and_still_reaches_a_shop`

**FR-D54 The answer can be narrowed to some of the genres the run looked in**
- Requirement: A Filter control wearing the library's filter artwork shall offer
  the run's genres only. While any is picked it shows a source artist's albums
  only where an album in a picked genre is held under that artist or credits
  them on a compilation; a candidate only where the candidate genre cache
  records a picked genre (else FR-D78); an offered series only where a held album
  in a picked genre has its name as stem. A source artist left empty is hidden.
  The control stays pressed in while filtering; pages are dealt again from what
  is shown. The filter is not remembered between openings.
- Rationale: Nobody held is withheld for want of a genre (Oliver's ruling).
- Verified by: `tests/domain/test_discovery_filter.py::test_nothing_picked_shows_everything`, `tests/domain/test_discovery_filter.py::test_a_source_artist_shows_by_the_genres_held`, `tests/domain/test_discovery_filter.py::test_a_candidate_shows_by_its_remembered_genres`, `tests/domain/test_discovery_filter.py::test_an_artist_with_nothing_left_is_not_shown`, `tests/ui/test_results_filter.py::test_only_the_genres_looked_in_are_offered`, `tests/ui/test_results_filter.py::test_the_filter_stays_pressed_in_while_on`, `tests/ui/test_results_filter.py::test_the_pages_are_dealt_from_what_is_shown`, `tests/domain/test_series.py::TestOnScreen::test_a_filter_keeps_a_series_held_in_the_picked_genres`, `tests/domain/test_series.py::TestOnScreen::test_a_filter_withholds_a_series_held_elsewhere`

**FR-D55 What a filter withholds is said**
- Requirement: While a genre or year filter is on, a line shall name the genres,
  then the years (FR-D99), then how many candidates are withheld because neither
  the candidate genre cache nor their heading's held albums (FR-D78) record a
  recognised genre.
- Verified by: `tests/domain/test_discovery_filter.py::test_candidates_with_no_genre_are_counted_as_withheld`, `tests/ui/test_results_filter.py::test_the_withheld_count_is_said_while_filtering`, `tests/ui/test_results_filter.py::test_the_line_names_the_genres_before_what_it_held_back`, `tests/ui/test_results_filter.py::test_the_line_says_the_source_gave_nothing_either`, `tests/domain/test_genre_rulings.py`

**FR-D56 A filter never takes a tick away**
- Requirement: Changing the filter shall keep every tick, hidden rows included.
  Copy and Find in shops act only on ticked albums shown. Closing the shops
  dialog clears every tick, hidden ones too (FR-S45 in `SHOPS.md`).
- Rationale: No album goes to a shop unseen (Oliver's ruling).
- Verified by: `tests/ui/test_results_filter.py::test_a_withheld_tick_is_left_out_of_copy`, `tests/ui/test_results_filter.py::test_a_tick_survives_the_filter_being_cleared`

**FR-D57 The chooser's Filter waits for a tick**
- Requirement: While FR-D54's chooser has no genre ticked, every FR-D86 kind
  ticked and no year set, its Filter control shall be disabled unless it opened
  with a filter on; while the typed years are unusable it is disabled regardless
  (FR-D99).
- Verified by: `tests/ui/test_filter_controls.py::test_filtering_waits_for_a_tick`, `tests/ui/test_filter_controls.py::test_clearing_every_tick_takes_filtering_away_again`, `tests/ui/test_filter_controls.py::test_a_filter_already_on_can_still_be_taken_off`, `tests/ui/test_results_showing.py::test_a_kind_left_out_is_enough_to_filter_by`, `tests/ui/test_filter_years.py::TestTheFields::test_years_alone_are_enough_to_filter_by`, `tests/ui/test_filter_years.py::TestRefusing`

**FR-D45 The answer is dealt across the width of the screen**
- Requirement: The results dialog shall open at `SCREEN_SHARE` of its screen,
  between `DIALOG_WIDTH_PX` by `DIALOG_HEIGHT_PX` and `CEILING_WIDTH_PX` by
  `CEILING_HEIGHT_PX` (`ui/results_room.py`). Source artists are dealt across as
  many columns as the width affords, at most `COLUMNS_AT_THE_CEILING`, a column
  being a third of the opening width on a real 13 inch display; each column reads
  top to bottom, an over-long row cut with an ellipsis. Each artist goes to the
  shortest column, counting one row for it and one per album and candidate under
  it. Columns are built only where an artist landed, one even when nobody did.
  One selection spans the columns. Every dialog makes its native window before
  sizing, in `FirstStopDialog` (`ui/dialogs.py`), except on Wayland.
- Rationale: Three columns suit a real 13 inch display (Oliver's ruling).
- Verified by: `tests/ui/test_results_columns.py::TestHowMuchRoomItTakes::test_a_wide_monitor_gets_no_more_than_a_13_inch_display`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_three_is_the_ruling_rather_than_whatever_the_constant_says`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_the_13_inch_ceiling_affords_the_three_that_were_asked_for`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_real_13_inch_display_shows_three`, `tests/ui/test_results_columns.py::TestHowManyColumns::test_a_wide_monitor_shows_three_and_no_more`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_every_artist_lands_in_exactly_one_column`, `tests/ui/test_results_columns.py::TestWhichArtistLandsWhere::test_it_deals_by_height_rather_than_by_count`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_it_builds_what_the_width_affords`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_fewer_artists_than_columns_builds_no_empty_column`, `tests/ui/test_results_columns.py::TestTheColumnsOnScreen::test_a_run_that_found_nobody_still_gets_a_screen`, `tests/ui/test_results_columns.py::TestOneSelectionAcrossThem::test_choosing_in_one_column_clears_the_others`, `tests/ui/test_results_columns.py::TestWhatIsTickedAcrossThem::test_the_ticks_are_read_from_every_column`, `tests/ui/test_results_size.py`, `tests/ui/test_dialog_first_stop.py::test_every_dialog_has_its_window_before_it_is_shown`

**FR-D35 How long the run has left**
- Requirement: During a run the window shall show the whole run's estimated time
  left, from one reading of the pace, in the status bar (rounded to the minute;
  "less than a minute" under sixty seconds) and abbreviated at the right hand end
  of the current stage's bar, clear of its name.
- Verified by: `tests/ui/test_run_estimate.py::TestNamingTheTimeLeft::test_the_status_bar_names_the_time_left`, `tests/ui/test_discovery_bar.py::test_it_writes_how_long_is_left_at_the_right_hand_end_of_the_moving_bar`, `tests/ui/test_discovery_bar.py::test_the_time_and_the_stage_are_never_drawn_over_each_other`, `tests/ui/test_discovery_bar.py::test_the_time_is_actually_drawn_on_the_bar`

**FR-D36 The estimate is taken from the run itself**
- Requirement: The estimate shall come from the time finished units actually
  took, not NFR-PERF-001's gap. While artists are looked up, a unit (finished or
  to come) is only a source artist the catalogue memory cannot fully answer, read
  off the memory before each artist (`application/foreseeing.py`); a name the
  memory knows reaches several artists counts as asked.
- Verified by: `tests/domain/test_estimating.py::TestThePace::test_the_pace_comes_from_what_happened`, `tests/domain/test_estimating.py::TestOnlyAskedArtistsAreTimed`, `tests/application/test_foreseeing.py`

**FR-D37 The second stage is estimated before it begins**
- Requirement: During the first stage the estimate shall include the second,
  projected from candidates seen against source artists finished, remembered or
  asked.
- Verified by: `tests/domain/test_estimating.py::TestProjectingTheSecondStage::test_the_second_stage_is_projected_from_the_first`, `tests/domain/test_estimating.py::TestOnlyAskedArtistsAreTimed::test_the_candidates_are_still_projected_from_every_artist`

**FR-D38 Too little has happened to estimate**
- Requirement: Below `MINIMUM_SAMPLES` finished units of the current stage
  (counting only asked artists, FR-D36), the window shall say the run is under
  way without a time.
- Verified by: `tests/domain/test_estimating.py::TestThePace::test_one_sample_is_not_enough_to_estimate`, `tests/ui/test_run_estimate.py::TestWhenItWillNotSay::test_one_sample_is_not_enough_to_estimate`, `tests/domain/test_estimating.py::TestOnlyAskedArtistsAreTimed::test_too_few_asked_to_say_is_silence_however_many_finished`

#### Release years

The years scope what a run offers, never what it learns from. Discover's years
are not remembered between openings; a plausible year runs from `FIRST_YEAR` to
`YEARS_AHEAD` past the current one (Oliver's ruling).

**FR-D58 Choosing the years to look in**
- Requirement: The discovery dialog shall offer optional from and to year
  fields, empty on opening and saying any year while empty.
- Verified by: `tests/ui/test_discovery_years.py::TestTheFields`, `tests/ui/test_discovery_years.py::test_the_runner_hands_the_years_to_the_run`

**FR-D59 Years that cannot be used are refused, not corrected**
- Requirement: If a field holds anything but a four digit plausible year (or
  from is later than to), the dialog shall say which field is wrong and why, with
  Find disabled.
- Verified by: `tests/domain/test_release_years.py::TestReadingTypedYears`, `tests/ui/test_discovery_years.py::TestRefusing`

**FR-D60 The years scope what is offered, never who is asked**
- Requirement: With years set, source artists shall be chosen exactly as without.
- Verified by: `tests/application/test_discovering_by_year.py::TestTheLibraryStillTeaches::test_an_old_album_leads_to_a_new_one`, proved to fail with the library filtered by the years

**FR-D61 A candidate album's year is its first release**
- Requirement: With years set, a candidate album shall be offered only where its
  release group's first release year (`year_of`) lies inside them, bounds
  included.
- Verified by: `tests/domain/test_release_years.py::TestOfferingByYear`, `tests/application/test_discovering_by_year.py::TestAlbumsByYear`

**FR-D62 A candidate album with no stated year is not offered while years are set**
- Requirement: With years set, a candidate album stating no first release year
  shall not be offered.
- Verified by: `tests/domain/test_release_years.py::TestAdmitting::test_no_year_does_not_fit_a_bounded_range`, `tests/application/test_discovering_by_year.py::TestAlbumsByYear::test_no_years_offers_what_it_always_did`

**FR-D63 A candidate artist is offered only with an album inside the years**
- Requirement: With years set, after genre narrowing the service shall ask
  (through the catalogue memory) what each remaining candidate released, keeping
  only those with an offered album inside the years; one that could not be asked
  about or has no identifier is dropped. Progress shows on the styles bar as
  "Checking years".
- Rationale: Known limit: FR-D37's projection leaves this stage out.
- Verified by: `tests/application/test_discovering_by_year.py::TestCandidatesByYear`, `tests/application/test_discovering_by_year.py::TestWhenACandidateCannotBeDated`, `tests/ui/test_discovery_years.py::TestTheBars`

**FR-D64 The answer says which years it was asked for**
- Requirement: A completed run with years set shall record them in the file;
  the results screen names them on the line naming the genres.
- Verified by: `tests/infrastructure/test_release_dates_kept.py::TestTheDiscoveryFile`, `tests/ui/test_discovery_years.py::TestTheResultsSayTheYears`

**FR-D65 An expanded candidate shows only albums inside the years**
- Requirement: Expanding a candidate from a run with years set shall show only
  offered albums inside them.
- Verified by: `tests/application/test_discovering_by_year.py::TestExpandingByYear`

**FR-D66 What is carried over keeps to the years**
- Requirement: An answer carried over (FR-D46) shall carry only albums inside
  this run's years; its candidate artists only where the earlier run had the
  same years.
- Verified by: `tests/application/test_discovering_by_year.py::TestCarryingOverByYear`

**FR-D67 A remembered answer with no dates in it is asked again**
- Requirement: Albums remembered from before release dates were kept shall be
  asked for again.
- Verified by: `tests/infrastructure/test_release_dates_kept.py::TestTheCatalogueMemory`

**FR-D68 An offered album says the year it first came out**
- Requirement: An offered album's stated first release year shall show after
  its title; shop searches and Copy use the bare title, carried on the row.
- Verified by: `tests/ui/test_discovery_years.py::TestAnAlbumRowSaysItsYear`

#### Series

**FR-D69 A series album is asked about by the series it belongs to**
- Requirement: While series are included (FR-D85), for each series album the
  service shall offer every unheld entry of its catalogue series.
- Verified by: `tests/application/test_discovering_series.py::test_a_compilation_brings_its_series`, `tests/application/test_discovering_series.py::test_one_series_is_asked_about_once`, `tests/application/test_discovering_series.py::test_leaving_compilations_out_asks_about_no_series`, `tests/application/test_discovering_series.py::test_a_person_with_albums_is_no_placeholder`, `tests/application/test_discovering_series.py::test_a_name_reaching_several_artists_is_no_placeholder`

**FR-D70 A series album is also matched by its stem**
- Requirement: The service shall also search each series album's stem, offering
  every unheld release group with that stem under the catalogue series' name
  (the stem where there is none). A volume both answers name is offered once
  (FR-D71).
- Rationale: Some series sit in no catalogue series; others lag the catalogue's
  titles (Oliver's ruling).
- Verified by: `tests/application/test_discovering_series.py::test_no_series_falls_back_to_the_stem`, `tests/application/test_discovering_series.py::test_a_volume_found_twice_is_offered_once`, `tests/domain/test_series.py::TestOneVolumeOnce`, `tests/domain/test_series.py`

**FR-D71 A series entry is judged held on its stem and number**
- Requirement: A series entry shall be held where any held album, under any
  artist, shares its stem and number or its release key.
- Verified by: `tests/domain/test_series.py::TestHeld`

**FR-D72 A series offers every kind of record in it**
- Requirement: A series entry shall be offered whatever kinds it states, inside
  the ticked genres and the run's years.
- Verified by: `tests/domain/test_series.py::TestMissing`

**FR-D73 A series question that fails is said, not hidden**
- Requirement: A series question refused through every ask, timed out or failed
  shall record the album's title as a run failure, not put back; the run moves
  on. A silence counts towards FR-D20's run of silences.
- Verified by: `tests/application/test_discovering_series.py::test_a_refused_series_is_a_failure`, `tests/application/test_discovering_series.py::test_a_failed_series_question_is_a_failure_too`, `tests/application/test_discovering_series.py::test_one_silence_is_a_failure_rather_than_an_ending`, `tests/application/test_discovering_series.py::test_a_run_of_silences_ends_the_run`

**FR-D74 A series is shown as a series**
- Requirement: Each offered series shall show as a heading giving its name, the
  word "series" and its number of albums, missing entries beneath; name, flag and
  entries are written to the file. An entry's shop artist is "Various Artists".
- Rationale: The shop artist is Claude's choice, standing until Oliver rules.
- Verified by: `tests/ui/test_results_series.py::test_a_series_heading_says_it_is_one`, `tests/ui/test_results_series.py::test_a_series_entry_goes_to_the_shops_under_various_artists`, `tests/infrastructure/test_series_kept.py::test_a_series_survives_the_file`

**FR-D75 A heading with nothing under it is not shown**
- Requirement: A heading with no album and no similar artist shall be left off
  screen, still recorded in the file (Oliver's ruling).
- Verified by: `tests/ui/test_results_series.py::test_an_empty_heading_is_left_out`, `tests/domain/test_series.py::TestOnScreen::test_an_empty_heading_is_not_worth_showing`

**FR-D76 A thinly voted genre is not believed**
- Requirement: A genre with fewer than `FEWEST_VOTES` votes beside one with at
  least that many shall not count; where none reaches it, all count. Nor does
  one with under 1/`LEADING_SHARE` of the leader's votes; the leader always
  counts. The rule is `believed` (`domain/genre_votes.py`), applied to every
  genre list the catalogue client reads. The candidate genre cache is named by `CACHE_NAME`;
  caches from earlier rules are not read.
- Rationale: Stray tags let anybody through a filter (Oliver's ruling).
- Verified by: `tests/domain/test_genre_votes.py`, `tests/infrastructure/test_discovery_sources.py::TestWhatAnArtistPlays::test_a_genre_voted_for_once_beside_real_ones_is_dropped`, `tests/infrastructure/test_discovery_sources.py::TestWhatAnArtistPlays::test_an_album_s_genres_are_held_to_the_same_rule`

**FR-D77 The catalogue holds the genres similar artists are stated with**
- Requirement: The catalogue shall carry these mains and styles: Dance
  (Breakbeat, Dance-Pop, Disco, Downtempo, EDM, Electronica, Eurodance, Hi-NRG,
  Italo Dance); Electronic (Ambient, Big Beat, Drum n Bass, Dubstep, Jungle, UK
  Garage); House (Acid House, Deep House, Progressive House, Tech House); Techno &
  Electro (EBM, Electro, Minimal Techno, Techno, Trance); Pop carries Britpop,
  Dream Pop, Electropop, Indie Pop, K-Pop, New Wave, Pop Rock and Synth-pop. A
  MusicBrainz genre matching, in any case, a name ruled in
  `domain/genre_rulings.py` (answered for by `genres.ALIASES`) reads as its ruled
  catalogue genre; no ruling is keyed on a catalogue name. The bare tag `dance`
  is the Dance main. A value stored before this catalogue reads as written plus
  the style's new main. Every dialog offering the catalogue offers every genre.
- Rationale: The divisions and the names left unrecognised are Oliver's ruling.
- Verified by: `tests/domain/test_genre_rulings.py::TestTheNamesSimilarArtistsStated`, `tests/domain/test_genre_rulings.py::TestTheNamesSimilarArtistsStated::test_a_value_stored_before_the_split_reads_as_written`, `tests/domain/test_genre_rulings.py::TestTheNamesSimilarArtistsStated::test_the_bare_dance_tag_is_the_dance_main`, `tests/domain/test_genre_rulings.py::TestTheDanceSubTaxonomy`, `tests/domain/test_genre_rulings.py::TestTheRulingsOnTheRest::test_the_names_a_filter_once_withheld`, `tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_every_catalogue_name_in_its_own_spelling_reads_back_as_itself`, `tests/domain/test_genre_rulings.py::TestTagsRuledToMeanAGenre::test_no_alias_is_keyed_on_a_catalogue_name`, `tests/domain/test_genres.py::TestTheCatalogue::test_it_holds_the_mains_that_were_settled`, `tests/ui/test_genre_grid.py::test_every_dialog_holding_the_grid_offers_every_genre`

**FR-D78 An untagged candidate is judged by who it was suggested for**
- Requirement: While a genre filter is on, a candidate with no recognised genre
  in the cache shall be judged by the catalogue genres of its heading's held
  albums: those whose album artist or any track artist equals the heading's
  artist (each artist of a joint credit split by FR-D53 counting); for a series
  heading, those whose stem equals its name. It shows where those meet the
  picked genres, else is filtered out; only where they name no catalogue genre is
  it withheld and counted (FR-D55). Each heading judges it on its own. The rule
  is `filtered_answer` (`domain/discovery_filter.py`).
- Rationale: The artist it resembles is the best evidence (Oliver's ruling).
- Verified by: `tests/domain/test_judged_by_their_source.py::test_an_untagged_candidate_shows_under_a_house_source`, `tests/domain/test_judged_by_their_source.py::test_an_untagged_candidate_under_a_rock_source_is_filtered_out`, `tests/domain/test_judged_by_their_source.py::test_judged_per_heading_where_one_candidate_sits_under_two`, `tests/domain/test_judged_by_their_source.py::test_counted_unjudged_where_the_source_names_no_genre_either`, `tests/domain/test_judged_by_their_source.py::test_a_series_heading_is_judged_by_the_volumes_held`, `tests/domain/test_judged_by_their_source.py::test_a_track_credit_on_a_compilation_judges_too`, `tests/domain/test_judged_by_their_source.py::test_a_recognised_genre_of_its_own_still_judges_first`, `tests/domain/test_judged_by_their_source.py::test_a_heading_split_from_a_joint_credit_judges_by_that_credit`, `tests/domain/test_judged_by_their_source.py::test_a_heading_split_from_a_joint_credit_keeps_its_albums`

**FR-D79 The genre grid's categories fold**
- Requirement: The genre grid shall lay its mains in three columns, catalogue
  order down each. A main with styles has an arrow before its box, on the
  keyboard ring, whose press (click, Enter or Space) shows or hides its styles.
  All start folded on first opening; each of the four grid dialogs remembers its
  own open ones. A folded main shows its ticked style count; folding gives the
  room back (Oliver's ruling).
- Verified by: `tests/ui/test_genre_folding.py`, `tests/ui/test_genre_grid.py::TestWhatItOffers::test_three_columns_is_the_ruling`, `tests/ui/test_genre_grid.py::TestWhatItOffers::test_the_groups_read_down_then_across_in_catalogue_order`

**FR-D80 A DJ mix is offered**
- Requirement: While DJ mixes are included (FR-D85, `ReleaseGroup.offered_with`),
  a release group typed DJ-mix shall be offered despite a Compilation type beside
  it, where its other types are all offered (Live, Remix, Demo). Compilation
  without DJ-mix stays excluded. The rule is `ReleaseGroup.is_offered`
  (`domain/discovery.py`).
- Rationale: A DJ's mix is worth offering where a hits package is not (Oliver's
  ruling).
- Verified by: `tests/domain/test_discovery_gaps.py::test_a_dj_mix_is_a_discovery`, `tests/domain/test_discovery_gaps.py::test_a_dj_mix_of_an_unknown_kind_is_still_left_alone`, `tests/domain/test_discovery_gaps.py::test_a_candidates_dj_mix_is_offered_on_expanding`, `tests/domain/test_discovery_gaps.py::test_a_hits_package_is_not_a_discovery`

**FR-D81 A number before a colon is a volume**
- Requirement: A digit number in a volume title, not reading as a year, with a
  letter before it and a colon and words after it, shall be the volume, the words
  before it the stem; otherwise a number ending the volume title is the volume.
- Rationale: "Fabric 99: Sasha" is a volume; "Sónar 2011: ..." is not.
- Verified by: `tests/domain/test_series.py::TestTheStem::test_a_number_before_a_colon_is_the_volume`, `tests/domain/test_series.py::TestTheStem::test_a_year_before_a_colon_is_not_a_volume`, `tests/domain/test_series.py::TestTheStem::test_a_number_with_no_name_before_it_is_not_a_volume`

**FR-D82 A compilation filed under an artist brings its series**
- Requirement: While series are included, for each held album in the ticked
  genres filed under neither Various Artists nor a placeholder, the service shall
  settle the artist as FR-D09 does. Given one identity it finds the album in
  that discography by release key (kinds aside), else by numbered place in a
  series. Where that release group is typed Compilation or DJ-mix and no release
  group of the artist without either shares the album's release key, its title
  is asked about by series as FR-D70 does. A stem search for an unnumbered title
  keeps only release groups stating a volume.
- Rationale: Most mixes are filed under the DJ (Oliver's ruling).
- Verified by: `tests/application/test_discovering_filed_compilations.py`, `tests/domain/test_series.py::TestFiledUnderAnArtist`, `tests/domain/test_series.py::TestSharingAStem::test_beside_an_unnumbered_title_only_volumes_are_kept`

**FR-D83 Checking series has a bar of its own**
- Requirement: The series stage shall report on its own bar, between the artists
  and styles bars. When a later stage reports, each earlier bar that reported is
  left full; one that never reported stays at rest, named without a percentage.
  Each bar is taller than its writing (Oliver's ruling).
- Verified by: `tests/ui/test_results_series.py::test_the_series_stage_has_a_bar_of_its_own`, `tests/ui/test_results_series.py::test_a_run_checking_no_series_leaves_its_bar_at_rest`, `tests/ui/test_discovery_bar.py::test_there_is_a_bar_for_each_stage_of_a_run`, `tests/ui/test_discovery_bar.py::test_each_bar_is_taller_than_its_writing`

**FR-D84 The time said covers the series stage**
- Requirement: While series are included, the service shall count at the start,
  from the catalogue memory alone, the series the series stage will look up
  (FR-D52's count plus FR-D82's compilations) and carry it on every report while
  artists are looked up; the time said adds them at the first stage's pace scaled
  by `REQUESTS_PER_SERIES` over `REQUESTS_PER_SOURCE_ARTIST`. While series are
  checked, each report carries the candidates the styles stage will ask about,
  added at the series stage's pace scaled by `REQUESTS_PER_CANDIDATE` over
  `REQUESTS_PER_SERIES`. The Include price counts the same series.
- Rationale: Known undercounts: a name only held titles could settle; a first run
  before the memory holds a discography.
- Verified by: `tests/domain/test_estimating.py::TestTheSeriesAhead`, `tests/application/test_discovering_filed_compilations.py::test_the_reports_carry_what_lies_ahead`, `tests/application/test_compilation_cost.py::test_a_compilation_filed_under_its_dj_is_a_series_to_price`

**FR-D85 Three boxes say what else a run takes in**
- Requirement: Under "Include:" the Discover dialog shall carry "Artists on
  compilations (Various Artists)" (FR-D51), "Other volumes of series" (FR-D69,
  FR-D82) and "DJ mixes" (FR-D80). Each acts alone: the first asks about
  compilation credits; the second runs the series stage; the third offers DJ
  mixes in an artist's list, on expanding and in carried answers (FR-D66). Series
  entries ignore the third. Each opens as last left; where the first two were
  never saved, the earlier single compilations setting answers for both. The
  price prices only the first two that are ticked. The choices are written to the
  file and read back for expanding; a file without them reads as the first two
  clear and mixes offered (Oliver's ruling).
- Verified by: `tests/ui/test_discovery_compilations.py`, `tests/application/test_discovering_filed_compilations.py::test_series_need_no_credits`, `tests/application/test_discovering_filed_compilations.py::test_mixes_left_out_are_not_offered_under_their_dj`, `tests/application/test_expanding.py::test_a_run_that_left_mixes_out_leaves_them_out_on_expanding`, `tests/infrastructure/test_discovery_results.py::TestWhatTheRunTookIn`, `tests/domain/test_discovery_gaps.py::test_dj_mixes_left_out_are_not_offered`

**FR-D86 The results filter shows by kind as well as by genre**
- Requirement: Above the genres the results filter shall carry a "Show:" row,
  all ticked on first opening: Albums, DJ mixes, Series and Similar artists. Each
  kind shows only while its box is ticked (a DJ mix by DJ mixes, other albums by
  Albums); an emptied heading is hidden (FR-D75). Kinds apply after the genres
  and with none ticked. Filter is offered once genres or kinds would hide
  anything; Clear unticks every genre and ticks every kind; the button beneath
  the answer stays pressed in while genres, kinds or years (FR-D99) hide
  anything (Oliver's ruling).
- Verified by: `tests/domain/test_showing.py`, `tests/ui/test_results_showing.py`

#### Taste profiles

A taste profile is a named, saved selection of everything the Discover dialog
asks: genres, Include boxes and years (Oliver's ruling).

**FR-D87 A taste profiles button beside Select all**
- Requirement: The Discover dialog shall carry a "Taste profiles" button wearing
  `taste-profiles.png` immediately right of Select all, disabled (red ring)
  while none is saved (Oliver's ruling).
- Verified by: `tests/ui/test_taste_profiles.py`

**FR-D88 The button lifts the saved profiles, by name**
- Requirement: A press shall lift a list above the button (below where there is
  no room), one row per profile in case-blind alphabetical order: delete on the
  left, then the name. The list keeps its own width, its right edge on the
  dialog's, held on screen. A second press puts it down.
- Rationale: A menu row holding two buttons was measured to let neither take the
  keyboard (`ui/taste_list.py`).
- Verified by: `tests/domain/test_taste.py`, `tests/ui/test_taste_profiles.py`,
  `tests/ui/test_taste_list_lifted.py`,
  `tests/ui/test_taste_list_scrolling.py::TestTheBar::test_a_list_too_long_for_the_room_scrolls_and_stays_on_screen`

**FR-D89 Choosing a profile puts its whole selection back**
- Requirement: Choosing a profile shall tick exactly its genres the grid still
  offers and set the Include boxes and year fields to its own, empty where it has
  no bound. A profile older than Include boxes and years reads with their
  defaults (FR-D85, every year).
- Verified by: `tests/ui/test_taste_profiles.py`

**FR-D90 A new selection is offered for saving on Find**
- Requirement: When Find is pressed with a selection (genres in any order,
  Include boxes, years) no saved profile matches exactly, the dialog shall offer
  to save it with a name field, Save and Not now; the run starts after either;
  Escape answers Not now (Oliver's ruling).
- Verified by: `tests/domain/test_taste.py`, `tests/ui/test_taste_profiles.py`

**FR-D91 A profile is saved under a name nobody else holds**
- Requirement: Save shall be disabled while the trimmed name is blank. A name
  matching a profile's ignoring case asks whether to replace it, naming it; No
  returns to the name field, nothing saved.
- Verified by: `tests/domain/test_taste.py`, `tests/ui/test_taste_profiles.py`

**FR-D92 A profile can be deleted, with confirmation**
- Requirement: Each delete button shall wear `delete.png`, as the shops dialog's
  rows do, with the tooltip "Delete the taste profile" and the quoted name. A
  press asks for confirmation naming the profile; only Yes removes it. Removing
  the last disables the button (FR-D87).
- Rationale: `negative.png` is kept for striking through other artwork, as
  SHOPS.md FR-S41 says (Oliver's ruling).
- Verified by: `tests/ui/test_taste_profiles.py`

**FR-D93 Profiles outlast the session**
- Requirement: Profiles shall be kept under one setting, read on every opening;
  an unreadable setting offers none rather than raising.
- Verified by: `tests/ui/test_taste_profiles.py`, `tests/domain/test_taste.py`

**FR-D94 Every button in the list is reached from the keyboard**
- Requirement: The list shall open with focus on the first name; Up and Down
  keep the column, Left and Right cross between delete and name, Tab walks every
  button in reading order, all wrapping. Escape, choosing a name or a delete
  puts the list down.
- Verified by: `tests/ui/test_taste_list_lifted.py::TestTheKeyboard`

**FR-D95 A long list scrolls rather than leaving the screen**
- Requirement: The list shall be no taller than the larger space above or below
  the button on its screen, scrolling vertically only while its rows do not fit
  and bringing a focused button into view. The scroll area never takes focus.
- Verified by: `tests/ui/test_taste_list_scrolling.py`

**FR-D96 Both genre choosers offer the same taste profiles**
- Requirement: The library's Filter by genre dialog and FR-D54's chooser shall
  each carry a Taste profiles button between Clear and the filtering press,
  lifting the same list from the same setting, so saving or deleting anywhere
  applies everywhere. Choosing a profile ticks exactly its genres still offered
  (by the library's catalogue or among the run's genres) and fills the year fields
  (FR-D99), leaving the library's no-genre box or FR-D86's kinds as they were.
  Each chooser offers to save as FR-D98 states (Oliver's ruling).
- Verified by: `tests/ui/test_filter_taste.py`, `tests/ui/test_filter_years.py::TestTasteProfiles`

**FR-D97 The way out stands alone on the left**
- Requirement: Discover's foot row shall read Close, a gap, then Select all,
  Taste profiles and Find; both genre choosers' read Cancel, a gap, then Clear,
  Taste profiles and the filtering press. Tab follows the reading order
  (Oliver's ruling, as for FR-D49 and FR-S40 in `SHOPS.md`).
- Verified by: `tests/ui/test_discovery_dialog.py::test_close_stands_left_with_the_sweeps_beside_find`, `tests/ui/test_filter_controls.py::test_cancel_stands_left_and_clear_beside_the_filter`

**FR-D98 Both genre choosers offer to save their genres and years**
- Requirement: The filtering press in either chooser, with a genre ticked and no
  profile holding exactly those genres and years (whatever its Include boxes),
  shall make FR-D90 and FR-D91's offer before closing. The saved profile holds the
  ticked genres, the FR-D99 years and the Include boxes as Discover first opens
  them. Cancel offers nothing (Oliver's ruling).
- Verified by: `tests/ui/test_filter_taste.py`, `tests/ui/test_filter_years.py::TestTasteProfiles`, `tests/domain/test_taste.py::TestWhatAGenreFilterCountsAsHeld`

**FR-D99 Both genre choosers narrow by year as well**
- Requirement: Both choosers shall offer FR-D58's year fields below the genres,
  opening on the years in use. With years set the library shows only albums whose
  date tag year is inside them; the answer only albums the catalogue dates inside
  them, similar artists untouched; an album with no year is hidden, as is an
  emptied heading (FR-D75). Years alone suffice (FR-D57). Unusable years are
  refused as FR-D59, beneath the fields, the filtering press disabled. Clear
  empties them. The library's Filter button and FR-D55's line name the years
  after the genres.
- Rationale: Profiles hold years (Oliver's ruling).
- Verified by: `tests/domain/test_filtering_by_year.py`, `tests/ui/test_filter_years.py`

### 3.2 Non-functional requirements

**NFR-PRIV-001 What leaves the machine**
- Requirement: A run shall send only these, with the application's User-Agent:
  artist names from the ticked genres (or the artists a name joins, FR-D53), less
  any trailing Discogs number; identifiers the sources answered with; up to
  `MOST_EVIDENCE` held titles under an ambiguous name, cut at the first bracket,
  sent to MusicBrainz alone beside it (FR-D09); while series are included, series
  album titles in the ticked genres (the catalogue's title where filed under an
  artist, FR-D82), cut at the first bracket, spaced solidus or spaced dash, with
  their stems, sent to MusicBrainz alone (FR-D69, FR-D70); fixed values each
  client states (response format, result limit, page start, release types,
  genres inclusion, relations and similarity algorithm). Headers carry only the
  destination, the User-Agent, the transport's terms and a language fixed at any
  (`ACCEPT_LANGUAGE`, `infrastructure/fetching.py`).
- Rationale: Qt otherwise sends the system locale.
- Verification:
  `tests/infrastructure/test_what_leaves_the_machine.py::test_a_field_holds_the_name_the_identifier_or_a_constant`
  puts every question through a recording fetcher and asserts each field holds
  the name (alone or beside a held title), the identifier or a constant; the
  series questions (`infrastructure/catalogue_series.py`) allow only a held
  title's volume title and stem. Both were proved to bite. Headers are read on a
  loopback service by
  `tests/infrastructure/test_fetching.py::TestAskingAService::test_no_header_says_anything_about_the_listener`.

**NFR-PRIV-002 No identifier of the listener or the machine**
- Requirement: A run shall send no account, installation identifier, machine
  name, file path or library statistic.
- Verification:
  `tests/infrastructure/test_what_leaves_the_machine.py::test_every_field_sent_is_one_its_address_is_allowed`
  with `::test_every_address_asked_is_one_the_allowed_set_names` hold every
  request the test asks against a fixed allowed set of addresses and fields; a
  new question is caught only once the test asks it.
  `::test_nothing_sent_names_the_listener_or_the_machine` checks each request
  against the machine name, user name and home directory.

**NFR-PRIV-003 The User-Agent names the application, never the person**
- Requirement: The User-Agent shall name Stellody, its version and a project
  contact address (as MusicBrainz requires) with nothing about the listener.
- Verification: `tests/structural/test_user_agent.py` asserts `USER_AGENT`
  (`infrastructure/courtesy.py`) is built only from `APP_NAME`, `__version__`
  and a literal `CONTACT`; it also asserts the fetcher's one User-Agent header
  is that constant.

**NFR-PERF-001 Request pacing**
- Requirement: At least `REQUEST_GAP_S` shall separate any two requests to one
  host, each host having its own gate.
- Rationale: Both services allow one request a second per IP.
- Verification:
  `tests/infrastructure/test_fetching.py::TestAskingAService::test_it_waits_its_turn_and_names_the_application`
  asserts every request passes the gate;
  `tests/ui/test_discovery_composition.py::test_everything_asking_musicbrainz_waits_at_one_gate`
  holds the run, expansion and cover search to one MusicBrainz gate.

**NFR-PERF-002 Run duration**
- Priority: Won't
- Withdrawn: a whole-library duration depends on two public services on the
  day and nobody would time it (Oliver's ruling).

**NFR-PERF-003 The candidate genre budget**
- Requirement: A candidate's genre shall be looked up at most once a run,
  however many source artists name it; the answer is kept for later runs.
- Verification:
  `tests/application/test_discovery.py::test_a_candidate_artist_is_asked_about_once`
  asserts one lookup for a candidate shared by two source artists.

**NFR-USE-001 The toolbar bar can be read**
- Requirement: Bar text shall reach 4.5 to 1 contrast against both filled and
  unfilled parts in both appearances; the fill shall stand off the groove by 3 to
  1, itself or by an edge reaching that against both.
- Verified by: `tests/ui/test_progress_contrast.py`

**NFR-USE-002 The results dialog can be read**
- Requirement: Every text colour in the results dialog, FR-D34's included, shall
  reach 4.5 to 1 against its surface in both appearances.
- Verified by: `tests/ui/test_results_contrast.py`

**NFR-MAINT-001 The gate**
- Requirement: Every module this work adds shall sit inside the coverage gate
  (100% branch for domain and application) and C-05's line cap.
- Verification: `.\gate.ps1`, read by exit code.

**NFR-MAINT-002 The suite never reaches the network**
- Requirement: No test shall leave the machine. The application reaches sources
  through interfaces its tests fill with hand-written fakes; the clients are
  tested over hand-written fetchers; the fetcher is tested against a loopback
  HTTP server (`tests/infrastructure/fetching_support.py`).
- Rationale: The house rule forbids mock libraries (Oliver's ruling).
- Verification:
  `tests/structural/test_offline.py::test_no_test_holds_the_machinery_to_reach_the_network`
  scans the test tree; permitted modules are named with reasons in
  `TESTS_PERMITTED`, kept honest by
  `::test_every_permitted_test_module_exists_and_still_needs_it`.

**NFR-REL-001 Nothing is written into the music folder**
- Requirement: The discovery file, the candidate genre cache, the catalogue
  memory and their running records shall be written only inside Stellody's data
  directory.
- Verification: `tests/structural/test_discovery_paths.py` asserts every place
  `infrastructure/discovery_file.py` and `infrastructure/catalogue_memory.py`
  name is a named file under `paths.data_dir()` and that every `journal` or
  `_written` call is handed one of them. Direct reads are not inspected.

### 3.3 External interfaces

**The catalogue source** answers: an artist name's identifier; who is credited
on a held title (FR-D09); an artist's albums with stated genres; the genres an
artist plays. While series are included its client in
`infrastructure/catalogue_series.py` also answers which series a release group
is in, what a series holds in order and which release groups a stem search
finds. **The similarity source** answers the artists similar to an identifier.
Both sit behind application-layer interfaces, so the choice is reversible.

**Decision: MusicBrainz for the catalogue, ListenBrainz for similarity.**

| | MusicBrainz | ListenBrainz | Discogs | Last.fm |
|---|---|---|---|---|
| Albums by an artist | yes | no | yes | weaker |
| Similar artists | no such endpoint | yes | no such endpoint | yes |
| Genre on results | yes | no | per release lookup | tags |
| Credential | none | none | token | key |
| Rate | 1 per second | 1 per second | 60 per minute | 5 per second |
| Terms | core data CC0 | MetaBrainz | token | non-commercial only |

Discogs and Last.fm are excluded by C-07: a credential compiled into a GPL
application is a published one.

### 3.4 Data

The discovery file is one JSON object in Stellody's data directory, replaced by
every completed run (`infrastructure/discovery_file.py`). `gaps` maps each
source artist to its candidate albums and candidate artists; each album carries
its first release date under `released`, empty where none was stated; a series
entry carries `series` true. Beside it: `unresolved`, `ambiguous`, `failed`,
`ticked`, `years` and `including` (`credits`, `series` and `mixes`, each true or
false). A file without `ticked` reads as an empty list; one without `including`
reads as the first two false and `mixes` true.

### 3.5 What makes two albums the same album

An edition qualifier describes the pressing; a performance qualifier the
recording. A remaster is the same album; a live version is not. A MusicBrainz
release group already holds its editions as releases, so edition noise exists
only in library tags. `AlbumIdentity` is untouched (its handle keys artwork,
ratings and corrections); matching has its own pure module on the same
`comparison_key`. The year is left out, since a remaster's tag carries the
remaster's year. One source artist's releases are matched against that artist's
held albums only.

**The rule.** The release key is `comparison_key(title)` with trailing
qualifiers (a parenthesised group, a bracketed group or a trailing `" - X"`)
removed when:

1. it is a lone type marker, `EP` or `Single`; or
2. it holds no distinguishing word and either ends in a terminal word or is
   built wholly of edition words and connectives, a four-digit year matching
   `YEAR_LIKE` permitted.

- **Edition words**: remaster, remastered, remasters, deluxe, expanded, edition,
  editions, version, anniversary, special, bonus, track, tracks, reissue,
  digital, super, explicit, clean.
- **Terminal words**: edition, version, remaster, remastered, reissue.
- **Distinguishing words**: live, remix, remixes, remixed, instrumental,
  instrumentals, karaoke, acoustic, demo, demos, mix, mixes, unmixed, dj,
  session, sessions, mono, radio, edit, single, cover, tribute, score,
  soundtrack, compilation.

It is an allowlist so that titles such as `L.I.F.E. (Love Is for Ever)` survive.

A title word merely restating a stated kind is dropped on both sides, so
`Secret World (Live)` meets `Secret World Live` typed Live; a record titled just
`Live` keeps its title. A release group matches on its release key with its
secondary types, so a live album and the studio album never suppress each
other. Offered: primary types Album and EP; secondary types Live, Remix and
Demo; a DJ-mix with or without Compilation, while mixes are included (FR-D80).
Every other secondary type, Compilation without DJ-mix among them, is excluded.

Not done: `&` is not folded to `and` and title diacritics are not stripped
(`normalise` keeps both); artist names are matched on `catalogue_key`, which
sets accents aside (FR-D08). The rule is untested against MusicBrainz's own
spellings.

## 4. Prioritisation

Must: FR-D01 to FR-D14, FR-D16 to FR-D99 and every NFR except NFR-PERF-002.
Should: FR-D15. Could: none.

Won't, recorded so it is not re-proposed: NFR-PERF-002; any purchase path;
ranking beyond what a source states; remembering what was offered and rejected;
reopening a past run's results from the menu; year presets, decade buttons or a
slider; renaming a taste profile.

## 5. Open questions

Nothing marked open may be built from.

| # | Question | Owner |
|---|---|---|
| OQ-07 | Answered: similarity depends on the labs endpoint with no fallback (Oliver's ruling). `SourceRefused` puts the artist back (FR-D21); `SourceFailed` records it (FR-D22); both are caught in `application/artist_stage.py`. | Answered |

## 6. The build order this implies

Inside out: domain gap rules tested against fabricated libraries; the
application service and source interfaces tested with hand-written fakes
injecting every error; infrastructure clients over the one fetching module, the
JSON writer and the candidate genre cache (the retry is in
`application/asking.py`); the UI last.

**Not currently met:** no test drives a whole run into the discovery file. The
application tests assert the report; `tests/infrastructure/test_discovery_file.py`
writes hand-built reports; the wiring tests use a fake service. One test must
run the service over a fabricated library and fake sources, write through the
real writer and assert the file.
