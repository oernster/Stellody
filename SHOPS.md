# Reaching the shops that sell what the library is missing

Specification for the second stage of discovering music the library does not
hold. The first stage says what the library is missing; this says how somebody
gets from one of those gaps to a place that sells it. It is in the house form:
EARS requirements, each with the failure case beside it, each naming the test
that proves it. Every requirement states the rule as it stands today. No
version number of its own: a document version beside a product version is two
numbers a reader has to tell apart, only one of them the product's.

It is built. Every requirement below names the test that holds it.

## 1. Introduction

### 1.1 Purpose

A discovery run ends with a list of albums the library does not hold. Without
this stage that list is somewhere to look at rather than somewhere to act, so
buying one of them means retyping an artist and a title into a shop by hand.
This closes that gap: from a ticked album, one press reaches a shop's own search
results for it. The shop list itself is edited from inside Stellody.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 Scope

**In scope:** ticking albums in the results dialog; a dialog that lists the
shops; opening a shop's search for the ticked albums in the listener's own
browser; copying the ticked albums as text; a shop list that is data rather
than code; adding, editing, deleting, moving and putting back shops from the
shops dialog.

**Out of scope, so that it is not re-proposed:**

- Any payment, basket, account, sign-in or price display. Stellody opens a
  search and stops there. What happens next is between the listener and the
  shop.
- Any shop API, any credential and any scraping of a shop's pages. The browser
  does the asking; Stellody only ever hands over an address.
- Prices, stock and availability shown inside Stellody. Those need what the
  bullet above rules out.
- Affiliate links or any revenue arrangement.
- Physical media. Digital only (Oliver's ruling).
- Streaming services. This is about owning a copy.
- Remembering what was bought; marking a gap as dealt with.
- Reaching a shop for an album already held, from the main library window or
  anywhere else (Oliver's ruling, OQ-S03): an album the library holds is not
  considered again.
- Editing shops anywhere but the shops dialog: no menu entry, no Preferences
  page.
- Importing, exporting or sharing a shop list.
- A picture per shop.
- Checking automatically that a shop's search finds anything. Try opens the
  page; judging it is the listener's.
- Hand-editing `shops.json` stays possible; it is not the way the list is meant
  to change. What a hand-broken row does is FR-S42.

### 1.4 Definitions

| Term | Meaning here |
|---|---|
| Gap | An album the library does not hold, as a discovery run reported it. |
| Shop | A digital music retailer, named by a row in the shop list. |
| Template | A shop's search address holding an `{artist}` placeholder, an `{album}` placeholder or both. |
| Ticked | An album whose tick box in the results dialog is checked. |
| Artist | The artist a ticked album carries to a shop and to Copy: the artist of the heading it sits under. An entry under a series heading (FR-D74) carries "Various Artists" instead, since a series names nobody and that is how the catalogue credits its entries. Held by `tests/ui/test_results_series.py::test_a_series_entry_goes_to_the_shops_under_various_artists`. |
| Title | An album's bare title. The results row reads "Title (year)" (FR-D68); a shop is still searched for the bare title and Copy puts the bare title on the clipboard: both read the artist and the title the row carries as data, never the row's text. Held by `tests/ui/test_discovery_years.py::TestAnAlbumRowSaysItsYear::test_a_shop_is_asked_for_the_title_alone`. |
| Opening | Handing an address to the operating system's default browser. |
| Shipped shop | A shop whose name appears in the list this Stellody ships. Names are compared ignoring case and surrounding space. |
| Own shop | A shop the listener added, whose name no shipped list carries. |
| Edited | A shipped shop whose name, address or note differs from the recorded shipped copy of it. Moving a shop does not edit it. |
| Deleted record | The names of shipped shops the listener deleted, kept in the shop file. |
| Retired record | The names of shops removed because a release stopped shipping them, kept until the dialog has said so. |
| Shop form | The small dialog Add and Edit open: Name, Search address, Note, Try, Save, Cancel. |

Nothing here is ever a track. A run deals in artists and albums; so does this.

### 1.5 References

- `DISCOVERY.md`, the stage-one specification, which this continues.
- `PLAN.md`, which recorded the intent and the network stance.
- `ARCHITECTURE.md` invariant 12, which names every module allowed to open a
  connection.

## 2. Overall description

### 2.1 Product perspective

An addition to the results dialog built for FR-D28 to FR-D34, plus a small
application service and one new file in Stellody's own directory. No new
outward connection: opening a browser is not a call this application makes.
The four modules named in invariant 12 stay four.

### 2.2 User classes

One: the listener, who owns the library and the machine. There is no second
role, no administrator and no shared state.

### 2.3 Operating environment

Windows, macOS and Linux, the three Stellody already ships to. A default
browser is assumed present; the case where the operating system cannot open one
is specified rather than assumed away.

### 2.4 Constraints

- Nothing identifying the listener or the library may leave the machine. An
  address carrying an artist and an album is the whole of what goes out. It
  travels through the browser rather than from Stellody.
- The shop list is data. Shops close, wall their search and move it without
  notice; a list compiled into the application would need a release every time
  that happens.
- The house rules hold: clean-architecture layering, 400-line modules, 100
  percent branch coverage over domain and application, no magic values, no Qt
  below the infrastructure layer.

### 2.5 Assumptions and dependencies

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | 7digital's search takes `q`, confirmed by Oliver in a browser past the wall that refuses automated visitors; the shipped row carries the UK host and `fallback=true` it was seen with. Whether an artist and an album together answer there is left to the page (A-03). | Oliver | Answered |
| A-02 | `assets/copy.png` is supplied, matching `shop.png`. | Oliver | Answered |
| A-03 | The shipped shops are not re-checked at each release (Oliver's ruling): FR-S09 makes a shop that rots an edit rather than a release. | Oliver | Answered |
| A-04 | `assets/drag-up-down.png` is supplied for the handle, so it is artwork rather than drawn in code. | Oliver | Answered |
| A-05 | Dragging a row within the shops dialog is feasible in PySide6, held by `tests/ui/test_shop_dragging.py` and tested by hand by Oliver. | Oliver | Answered |

## 3. Requirements

Every requirement below is a Must unless it carries a Priority line;
section 4 lists them.

### 3.1 Functional

**FR-S01 An album can be ticked**
- Requirement: The results dialog shall show a tick box against every album row,
  unticked when the row is first drawn.
- Rationale: Oliver's ruling. Selection in a tree is invisible once focus moves
  and cannot survive a row being rebuilt; a tick box is a state the reader can see
  and the dialog can read back.
- Acceptance: Given a run holding two albums under one artist, when the dialog
  opens, then each album row carries an unticked box and no artist row carries
  one.
- Verified by: `tests/ui/test_shop_choosing.py::test_every_album_row_can_be_ticked`

**FR-S02 Only albums can be ticked**
- Requirement: The results dialog shall not show a tick box against an artist row
  of either kind.
- Rationale: The unwanted sibling of FR-S01. An artist is not something a shop
  sells; a candidate artist row with no albums fetched has nothing to look up.
- Acceptance: Given a dialog holding a source artist and a candidate artist, when
  the rows are read, then neither carries a tick box.
- Verified by: `tests/ui/test_shop_choosing.py::test_an_artist_row_carries_no_tick_box`

**FR-S03 Fetching a candidate's albums gives them tick boxes**
- Requirement: When the albums of a candidate artist arrive, the results dialog
  shall draw each with a tick box, unticked.
- Rationale: Those albums are the ones least likely to be held, so they are the
  ones most likely to be wanted. They arrive after the dialog is built, which is
  the case a tick box added only at build time would miss.
- Acceptance: Given a candidate artist expanded and answered with three albums,
  when its rows are read, then each carries an unticked box.
- Verified by: `tests/ui/test_shop_choosing.py::test_fetched_albums_can_be_ticked_too`,
  `tests/ui/test_shop_choosing.py::test_every_fetched_album_arrives_unticked`

**FR-S04 Nothing ticked offers no lookup**
- Requirement: While no album is ticked, the results dialog shall disable the
  control that opens the shops and the copy control.
- Rationale: A press that can only report emptiness is a press worth preventing.
  The same rule the discovery dialog applies to its own Find button.
- Acceptance: Given a dialog with nothing ticked, when the controls are read, then
  both are disabled; when one album is ticked, then both are enabled.
- Verified by: `tests/ui/test_shop_choosing.py::test_the_shops_control_waits_for_a_tick`

**FR-S05 The shops are offered in a dialog**
- Requirement: When the shops control is pressed, the results dialog shall show
  its one shops dialog (FR-S44), listing every configured shop and stating how
  many albums are ticked.
- Rationale: Oliver's ruling. A press has to choose between shops; the choice is
  worth a screen, since it is also where the count is confirmed before anything
  opens.
- Acceptance: Given three albums ticked and four shops configured, when the
  control is pressed, then a dialog lists the four shops and says three albums.
- Verified by: `tests/ui/test_shop_dialog.py::test_it_lists_the_shops_and_counts_the_albums`

**FR-S06 Choosing a shop opens its search for every ticked album**
- Requirement: When a shop is chosen in the shops dialog, the shops dialog shall
  open that shop's search address for each ticked album in the listener's default
  browser, then say in the dialog how many searches it opened at that shop.
- Rationale: The whole point. One address per album rather than one address for
  all of them, since no shop searches for several albums at once.
- Acceptance: Given two albums ticked and Qobuz chosen, when the shop is chosen,
  then two addresses are opened, each being Qobuz's search for one of those
  albums; the dialog then says it opened 2 searches at Qobuz.
- Verified by: `tests/ui/test_shop_dialog.py::test_choosing_a_shop_opens_one_search_an_album`,
  `tests/ui/test_shop_dialog.py::test_it_says_what_it_just_opened`

**FR-S07 The shops dialog stays open**
- Requirement: While the shops dialog is open, choosing a shop shall leave it
  open, until the listener closes it.
- Rationale: Oliver's ruling: prices are compared across shops, so a dialog that
  closed on the first choice would have to be reopened for every shop after it.
- Acceptance: Given a shop chosen, when the dialog is read, then it is still
  open and a second shop can be chosen from it.
- Verified by: `tests/ui/test_shop_dialog.py::test_it_stays_open_so_prices_can_be_compared`

**FR-S08 More than five albums is confirmed first**
- Requirement: If more than five albums are ticked when a shop is chosen, then
  the shops dialog shall ask for confirmation naming the number of browser tabs
  about to open, opening none of them unless it is given.
- Rationale: One album is one browser tab. Thirty ticked albums is thirty tabs
  arriving at once over whatever the listener was doing, which is not a state
  anybody chooses deliberately. Five is the bar (Oliver's ruling).
- Acceptance: Given six albums ticked, when a shop is chosen and the question is
  answered no, then nothing is opened; when it is answered yes, then six
  addresses are opened.
- Verified by: `tests/ui/test_shop_dialog.py::test_a_large_number_of_tabs_is_asked_about_first`, `tests/ui/test_shop_dialog.py::test_a_refused_confirmation_opens_nothing`, `tests/ui/test_shop_dialog.py::test_a_handful_is_not_asked_about`

**FR-S09 The shop list is read from a file**
- Requirement: The shop service shall read the shop list from a file in
  Stellody's own directory, writing the shipped defaults there where no file
  exists.
- Rationale: A shop list inside the application is a release every time a shop
  closes or moves its search; a file is an edit (section 2.4).
- Acceptance: Given no shop file, when the shops dialog is first opened, then the
  file is written holding the shipped defaults and those shops are listed.
- Verified by: `tests/infrastructure/test_shop_file.py::TestTheFirstTime::test_a_missing_file_is_written_with_the_defaults`

**FR-S10 A template names the artist and the album separately**
- Requirement: The shop service shall build an address by replacing `{artist}`
  and `{album}` in a shop's template with the album's artist and title, each
  percent encoded, with a space encoded as `%20`.
- Rationale: Some shops search badly on two terms (Boomkat finds nothing for an
  artist plus an album yet finds the album under the artist alone), so two
  placeholders let each row say what that shop can take. `%20` rather than `+`
  because some shops show a literal plus sign, while the shops checked all took
  `%20`.
- Acceptance: Given the template
  `https://www.qobuz.com/gb-en/search?q={artist}%20{album}` and the album
  "Hounds of Love" by "Kate Bush", when the address is built, then it is
  `https://www.qobuz.com/gb-en/search?q=Kate%20Bush%20Hounds%20of%20Love`.
- Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_both_placeholders_are_filled_and_encoded`

**FR-S11 A template that names neither is refused**
- Requirement: If a shop's template holds neither `{artist}` nor `{album}`, then
  the shop service shall leave that row out of the shops that can be searched and
  shall keep it in the list with its reason (FR-S42).
- Rationale: The unwanted sibling of FR-S10. A template with no placeholder opens
  the same page whatever is ticked, which looks like a broken search rather than
  a mistyped row.
- Acceptance: Given a shop file holding a row whose template has no placeholder,
  when the list is read, then that row is not among the shops that can be
  searched and is read back as a broken row naming its reason.
- Verified by: `tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_template_with_no_placeholder_is_refused`

**FR-S12 A shop file that cannot be read falls back**
- Requirement: If the shop file cannot be parsed, its top level is not a JSON
  object or its `shops` is not a list, then the shop service shall offer the
  shipped defaults and shall write the file as a first run installs it (FR-S09).
  A list whose rows are broken is not unusable: each row is kept and named
  (FR-S42). An empty list is a list, not an unusable file.
- Rationale: The unwanted sibling of FR-S09: a list nobody can read is a
  disappointment, while an exception in the middle of a results dialog is worse.
  The unusable file goes straight back to the installed state, which is what the
  dialog shows (Oliver's ruling); leaving it on disk only postponed that, since
  the first change made in the dialog would save over it.
- Acceptance: Given a shop file holding malformed JSON, a top level that is not an
  object or a `shops` that is not a list, when the list is read, then the shipped
  defaults are offered and the file on disk is exactly what a first run writes.
  Given a directory that refuses the write, the shipped defaults are still
  offered.
- Verified by: `tests/infrastructure/test_shop_file.py::TestWhatCannotBeRead::test_it_falls_back_to_the_installed_list`, `tests/infrastructure/test_shop_file.py::TestWhatCannotBeRead::test_a_directory_that_cannot_be_written_still_offers_the_shops`

**FR-S13 A browser that will not open says so**
- Requirement: If the operating system cannot open an address, then the shops
  dialog shall say so in the dialog, naming that shop, while leaving the dialog
  open.
- Rationale: The unwanted sibling of FR-S06. Nothing happening at all is the one
  outcome indistinguishable from the application being broken.
- Acceptance: Given an opener that refuses, when a shop is chosen, then the dialog
  says that shop could not be opened and remains open.
- Verified by: `tests/ui/test_shop_dialog.py::test_a_browser_that_will_not_open_says_so`,
  `tests/ui/test_shop_dialog.py::test_a_refusal_leaves_the_dialog_standing`

**FR-S14 The ticked albums can be copied as text**
- Requirement: When the copy control is pressed, the results dialog shall put one
  line per ticked album on the clipboard, each holding the artist and the album
  title.
- Rationale: Oliver's ruling. It covers every shop nobody has configured, every
  shop that has just changed its search path and anywhere else somebody wants to
  paste a list.
- Acceptance: Given two albums ticked, when copy is pressed, then the clipboard
  holds two lines, each naming an artist and an album.
- Verified by: `tests/ui/test_shop_choosing.py::test_copy_puts_the_ticked_albums_on_the_clipboard`

**FR-S15 Both controls are reachable from the keyboard**
- Requirement: The results dialog shall open focused on its first list with that
  list's first row current. It shall place each list then each control beneath
  them in the keyboard ring, in the order they are drawn. Within a list, Up and
  Down shall walk the rows; Right shall open an artist and Left shall shut it;
  Enter and Space shall tick or untick an album and open or shut an artist. The
  current row shall wear the ring while its list has the focus. A list given the
  focus by Tab or Shift+Tab with no row current shall make its first row current;
  a list given the focus by a click shall leave its current row and its scroll
  position alone, so the click lands on the box it was aimed at.
- Rationale: The house keyboard model (Oliver's ruling). A control reachable only
  with a mouse is half a control. A tick box is a row of its list rather than a
  widget of its own, so the ring stops on the list and the arrow keys move within
  it. The arrangement follows the library list, where Left and Right shut and
  open an album.
- Acceptance: Given the dialog open, then the first list has the focus and its
  first row is current; when Tab is pressed repeatedly, then each list and each
  enabled control are reached in the order they are drawn; within a list, Right
  opens an artist and Left shuts it without leaving the list; Enter and Space
  tick and untick an album without closing the dialog and open and shut an
  artist; the current row is ringed while its list has the focus and not after.
- Verified by: `tests/ui/test_shop_choosing.py::test_the_ticks_and_the_controls_are_stops_on_the_ring`,
  `tests/ui/test_shop_choosing.py::test_a_tick_box_is_reached_and_ticked_from_the_keyboard`,
  `tests/ui/test_space_chooses.py::TestADialogOverTheWindow::test_space_still_ticks_an_album_in_the_results`,
  `tests/ui/test_results_keyboard.py`,
  `tests/ui/test_ticking_a_scrolled_row.py`

**FR-S16 A release meets the list shop by shop**
- Requirement: The shop service shall settle each row of the shop file against
  the current shipped list on its own, as FR-S30 to FR-S36 state, rather than
  replacing a whole file judged unedited.
- Rationale: With an editor nearly every file is edited somewhere, so a
  whole-file rule would freeze every file against every correction.
- Verified by: the tests of FR-S30 to FR-S36.

**FR-S17 A shop can be added**
- Requirement: When the add control is pressed, the shops dialog shall open the
  shop form with every field empty.
- Acceptance: Given the shops dialog, when add is pressed, then the shop form
  opens with an empty name, address and note.
- Verified by: `tests/ui/test_shop_editing.py::test_add_opens_an_empty_form`

**FR-S18 A shop can be edited**
- Requirement: When a shop's edit control is pressed, the shops dialog shall open
  the shop form holding that shop's name, address and note.
- Acceptance: Given Qobuz listed, when its edit control is pressed, then the form
  holds Qobuz's name, address and note.
- Verified by: `tests/ui/test_shop_editing.py::test_edit_opens_the_form_holding_the_shop`

**FR-S19 Saving puts the shop in the list**
- Requirement: When Save is pressed on a shop form that passes FR-S20 and FR-S21,
  the shop service shall write the list to the shop file with an added shop at the
  bottom or an edited shop in its own place, then the shops dialog shall show the
  list as written.
- Acceptance: Given Qobuz listed and a form holding "Juno" with a valid address,
  when Save is pressed, then the list holds Qobuz then Juno and the form closes.
- Verified by: `tests/application/test_editing_the_shop_list.py::test_an_added_shop_goes_last`,
  `tests/application/test_editing_the_shop_list.py::test_an_edited_shop_keeps_its_place`,
  `tests/ui/test_shop_editing.py::test_a_saved_form_puts_the_shop_last`

**FR-S20 A broken shop cannot be saved**
- Requirement: If the name is empty, the address is empty, the address does not
  begin with `https://` or the address names neither `{artist}` nor `{album}`,
  then the shop form shall refuse to save and shall say which of those is wrong
  beside the field it concerns.
- Rationale: A shop that cannot search is stopped at the one moment somebody is
  looking at it, rather than vanishing from the list later.
- Acceptance: Given a form whose address is `https://example.com/search`, when
  Save is pressed, then nothing is written and the address field says it names
  neither placeholder.
- Verified by: `tests/ui/test_shop_editing.py::test_a_shop_that_cannot_search_is_not_saved`

**FR-S21 Two shops cannot share a name**
- Requirement: If the name matches, ignoring case, the name of another shop in
  the list, then the shop form shall refuse to save and shall say the name is
  taken.
- Rationale: A name is how a shipped shop is recognised across releases (section
  1.4), so two of one name would make FR-S30 to FR-S33 guess.
- Acceptance: Given Qobuz listed, when a new shop named "qobuz" is saved, then
  nothing is written and the name field says it is taken.
- Verified by: `tests/domain/test_shop_list.py::TestTheForm::test_a_name_already_used_is_refused`,
  `tests/ui/test_shop_editing.py::test_a_shop_that_cannot_search_is_not_saved`

**FR-S22 A shop can be tried before it is saved**
- Requirement: When Try is pressed, the shop form shall open the address it
  currently holds, for the first ticked album in the order the results draw them,
  in the default browser, without saving anything. If the address breaks one of
  FR-S20's address rules, then the form shall open nothing and shall say which
  beside the address field; the name need not be filled in to try a shop.
- Rationale: Whether a shop works is judged by looking at its page (Oliver's
  ruling). The shops dialog opens only with at least one album ticked (FR-S04).
  It can stay open while every tick is cleared (FR-S44); a form opened then has
  no album to try, so Try is disabled until one is ticked and the form is opened
  again.
- Acceptance: Given "Kate Bush, Hounds of Love" ticked first and a form holding
  `https://example.com/s?q={artist}`, when Try is pressed, then
  `https://example.com/s?q=Kate%20Bush` is opened and the file is unchanged.
- Verified by: `tests/ui/test_shop_editing.py::test_try_opens_the_first_ticked_album`,
  `tests/ui/test_shop_editing.py::test_a_try_with_a_broken_address_opens_nothing`

**FR-S23 A try that will not open says so**
- Requirement: If the operating system cannot open the address Try built, then
  the shop form shall say so and shall stay open.
- Acceptance: Given an opener that refuses, when Try is pressed, then the form
  says the address could not be opened and remains open.
- Verified by: `tests/ui/test_shop_editing.py::test_a_try_that_will_not_open_says_so`

**FR-S24 Deleting asks first**
- Requirement: When a shop's delete control is pressed, the shops dialog shall
  ask for confirmation naming that shop, deleting it only when the answer is yes
  (Oliver's ruling).
- Acceptance: Given Beatport listed, when its delete control is pressed and the
  answer is no, then Beatport is still listed; when the answer is yes, then it is
  gone from the dialog and from the file.
- Verified by: `tests/ui/test_shop_editing.py::test_delete_asks_naming_the_shop`,
  `tests/ui/test_shop_editing.py::test_a_refused_delete_keeps_the_shop`

**FR-S25 A deleted shipped shop is remembered**
- Requirement: When a shipped shop is deleted, the shop service shall add its name
  to the deleted record.
- Rationale: An update must never bring back a shop somebody removed (Oliver's
  ruling).
- Acceptance: Given Beatport deleted, when the file is read, then its deleted
  record names Beatport.
- Verified by: `tests/application/test_editing_the_shop_list.py::test_deleting_a_shipped_shop_records_it`

**FR-S26 Renaming a shipped shop is a delete plus an add**
- Requirement: When a shipped shop is saved under a different name, the shop
  service shall add its original name to the deleted record.
- Rationale: Without it the next release would find the original name missing and
  add the shop back beside the renamed one.
- Acceptance: Given Qobuz saved as "Qobuz UK", when the file is read, then the
  list holds "Qobuz UK", no "Qobuz" and the deleted record names Qobuz.
- Verified by: `tests/application/test_editing_the_shop_list.py::test_renaming_a_shipped_shop_records_the_old_name`

**FR-S27 A shop is moved by dragging its handle**
- Requirement: While a shop's handle is held, the shops dialog shall carry that
  row with the pointer and glide every other row to the place it would take were
  the held row let go there. When the handle is let go, the shop service shall
  write the list in the new order, then the row shall glide into its place. If the
  list cannot be written, then the row shall glide back to where it started.
  Letting go where the row was taken shall write nothing. While a row is held or
  still landing, Ctrl+Up and Ctrl+Down shall move nothing.
- Rationale: A row that stays put while the pointer moves gives no sign of where
  it will go; one that jumps on release has to be found again by eye (Oliver's
  ruling). Where the row would land is read off where the rows started, so the
  answer does not move while the others glide. The write comes before the glide
  home, which keeps FR-S29's rule that what is shown is what the file holds.
- Acceptance: Given Juno third, when its handle is carried level with the first
  row, then Juno's row has moved with the pointer, Qobuz and Bleep have each moved
  down one place and nothing is written; when it is let go, then the file holds
  Juno first and the rows stand where the three rows started. Given a file that
  refuses writes, then nothing is written and the rows stand in their old order.
  Given any shop of eight carried below the last row, then it lands last.
- Verified by: `tests/ui/test_shop_dragging.py::test_the_held_row_follows_the_pointer`,
  `tests/ui/test_shop_dragging.py::test_the_other_rows_make_room_before_it_is_let_go`,
  `tests/ui/test_shop_dragging.py::test_dragging_the_handle_moves_the_shop`,
  `tests/ui/test_shop_dragging.py::test_a_move_the_file_refuses_glides_back`,
  `tests/ui/test_shop_dragging.py::test_letting_go_where_it_was_taken_writes_nothing`,
  `tests/ui/test_shop_dragging.py::test_every_shop_can_be_dragged_to_the_bottom`,
  `tests/ui/test_shop_dragging.py::test_the_keyboard_waits_while_a_row_is_held`

**FR-S28 A shop is moved from the keyboard**
- Requirement: While one of a shop's controls holds focus, when Ctrl+Up or
  Ctrl+Down is pressed, the shop service shall move that shop one place up or down
  and write the list, focus staying on the control that held it.
- Rationale: The house keyboard model: a control reachable only with a mouse is
  half a control. A move past either end does nothing.
- Acceptance: Given focus on Qobuz's button with Qobuz second, when Ctrl+Up is
  pressed, then Qobuz is first and still holds focus; when Ctrl+Up is pressed
  again, then nothing changes.
- Verified by: `tests/ui/test_shop_editing.py::test_ctrl_arrows_move_the_focused_shop`

**FR-S29 A change that cannot be written is not shown as made**
- Requirement: If an add, edit, delete or move cannot be written to the shop file,
  then the screen the change was made on shall say so (the shop form for an add or
  an edit, the shops dialog for a delete or a move) while the shops dialog goes on
  showing the list as it was.
- Acceptance: Given a shop file that refuses writes, when a shop is deleted, then
  the dialog says the change could not be saved and still lists that shop.
- Verified by: `tests/ui/test_shop_editing.py::test_a_change_that_cannot_be_saved_is_not_shown`,
  `tests/ui/test_shop_editing.py::test_a_form_that_cannot_be_kept_says_so`

**FR-S30 A new shipped shop is added**
- Requirement: When the shipped list holds a shop whose name is neither in the
  list in use nor in the deleted record, the shop service shall add that shop at
  the bottom of the list in use.
- Rationale: New shops arrive while the listener's own order stays theirs
  (Oliver's ruling).
- Acceptance: Given a file holding the eight shops and a release shipping a ninth,
  "Juno", when the shops are read, then Juno is ninth.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_new_shipped_shop_is_added_last`

**FR-S31 A shop somebody deleted stays deleted**
- Requirement: If a shipped shop's name is in the deleted record, then the shop
  service shall leave it out of the list in use whatever the shipped list says.
- Acceptance: Given Beatport in the deleted record and a release still shipping
  Beatport, when the shops are read, then Beatport is not listed.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_deleted_shop_never_returns`

**FR-S32 An untouched shipped shop follows the release**
- Requirement: When a release changes the address or the note of a shipped shop
  that is not edited, the shop service shall take the new address and note,
  keeping the shop in its place.
- Acceptance: Given Qobuz untouched in second place and a release changing Qobuz's
  address, when the shops are read, then Qobuz is second with the new address.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_untouched_shop_takes_the_new_address`

**FR-S33 An edited shipped shop keeps the edit**
- Requirement: If a shipped shop is edited, then the shop service shall keep the
  listener's name, address and note whatever a release changes about that shop.
  Shops the listener added are never touched by a release.
- Acceptance: Given Qobuz with an edited note and a release changing Qobuz's
  address, when the shops are read, then Qobuz keeps the listener's address and
  note.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_edited_shop_keeps_the_edit`

**FR-S34 A shop a release drops is removed where untouched**
- Requirement: When a release no longer ships a shop the recorded shipped list
  held, the shop service shall remove that shop from the list in use where it is
  not edited and shall name it in the retired record; an edited one stays.
- Rationale: The usual reason a shop leaves the shipped list is that it closed.
- Acceptance: Given Bleep untouched and a release that no longer ships Bleep, when
  the shops are read, then Bleep is not listed and the retired record names it.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_untouched_shop_is_removed`,
  `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_edited_shop_stays`

**FR-S35 A removed shop is announced once**
- Requirement: When the shops dialog opens while the retired record names shops,
  the shops dialog shall say which shops were removed because Stellody no longer
  ships them, then the shop service shall empty the retired record.
- Acceptance: Given the retired record naming Bleep, when the shops dialog opens,
  then it says Bleep was removed; when it is closed and opened again, then it says
  nothing about Bleep.
- Verified by: `tests/ui/test_shop_editing.py::test_a_removed_shop_is_announced_once`

**FR-S36 A file with no deleted record gains nothing by surprise**
- Requirement: If the shop file records no deleted record, then the shop service
  shall write an empty one without adding any shipped shop the list lacks.
- Rationale: A file with no deleted record was last written when a shop could be
  removed only by hand-editing, which left no record. A shipped shop missing from
  such a file may have been removed on purpose, so it is not put back.
- Acceptance: Given a file without a deleted record whose list lacks Beatport,
  when the shops are read, then Beatport is still absent and the file holds an
  empty deleted record.
- Verified by: `tests/infrastructure/test_shop_file.py::TestMeetingARelease::test_an_older_file_is_not_added_to`

**FR-S37 The original shops can be put back**
- Requirement: When the put-back control is pressed and confirmed, the shop
  service shall write the shipped shops in shipped order with their shipped
  values, followed by the listener's own shops in their current order; the same
  write empties the deleted record.
- Rationale: The way back from any amount of editing, which keeps what the
  listener added rather than taking that too.
- Acceptance: Given Beatport deleted, Qobuz edited and an own shop "Juno" added,
  when put back is confirmed, then the eight shipped shops are listed as shipped
  with Juno ninth and the deleted record is empty.
- Verified by: `tests/domain/test_shop_list.py::TestTheWayBack::test_putting_back_keeps_own_shops`

**FR-S38 Putting back asks first**
- Requirement: When the put-back control is pressed, the shops dialog shall ask
  for confirmation, changing nothing unless the answer is yes.
- Acceptance: Given an edited list, when put back is pressed and the answer is no,
  then the list and the file are unchanged.
- Verified by: `tests/ui/test_shop_editing.py::test_putting_back_asks_first`

**FR-S39 An empty list still offers Add**
- Requirement: While the list holds no shops, the shops dialog shall show the add
  control and a line saying there are no shops yet. A list emptied from the
  dialog stays empty, since every shipped name is then in the deleted record.
- Rationale: The dialog is the way the list changes, so the empty state points at
  Add rather than at hand-editing `shops.json`.
- Acceptance: Given every shop deleted, when the dialog is read, then it shows the
  add control and does not mention `shops.json`.
- Verified by: `tests/ui/test_shop_editing.py::test_an_empty_list_offers_add`

**FR-S40 Every new control is on the keyboard ring**
- Requirement: The shops dialog shall place each shop's button, edit control and
  delete control, the add control and the put-back control in the keyboard ring in
  reading order. The handle shall not be a stop.
- Rationale: The handle is a mouse affordance whose keyboard equivalent is
  FR-S28, so a stop on it would be a press that does nothing.
- Acceptance: Given two shops listed, when Tab is pressed repeatedly, then focus
  reaches the first shop's button, edit and delete, then the second's, then add,
  then put back, then Close.
- Verified by: `tests/ui/test_shop_editing.py::test_the_ring_walks_the_rows_in_reading_order`

**FR-S41 The row controls wear artwork the guide explains**
- Requirement: The add, edit and delete controls shall wear `add.png`, `edit.png`
  and `delete.png`; the handle shall wear `drag-up-down.png`, a ribbed grip with
  an arrow above and below. The guide shall show all four beside what each does.
- Rationale: The artwork is Oliver's. Delete does not wear `negative.png`, which
  `ARCHITECTURE.md` keeps for composing over another picture.
  `tests/ui/test_guide.py` fails on a picture the interface names that the guide
  does not draw.
- Verified by: `tests/ui/test_guide.py::TestWhatItNames` (existing)

**FR-S42 A hand-broken row can be mended from the dialog**
- Requirement: If a row in the shop file cannot be read as a shop, then the shops
  dialog shall list it greyed out with the reason it cannot be used, offering its
  edit and delete controls and no way to search it.
- Rationale: Oliver's ruling (OQ-S04). The row is still never searched (FR-S11),
  while it is no longer skipped without a word. Edit opens the shop form holding
  whatever the row carried, so FR-S20 decides whether the mended row saves.
- Acceptance: Given a file holding a row named "Juno" whose address names no
  placeholder, when the dialog opens, then Juno is listed greyed out saying its
  address names neither placeholder; its edit control opens the form holding that
  address; its delete control removes the row after asking.
- Verified by: `tests/ui/test_shop_editing.py::test_a_broken_row_is_listed_greyed_with_its_reason`,
  `tests/ui/test_shop_editing.py::test_a_broken_row_is_deleted_after_asking`,
  `tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_broken_row_is_read_with_its_reason`

**FR-S43 Try, Save and put back wear artwork**
- Requirement: The shop form shall show `try.png` on Try and `save.png` on Save;
  the shops dialog shall show `revert-shops.png` on its put-back control. The
  guide shall show all three beside what each does.
- Rationale: Apart from the buttons carrying a shop's own name, the other controls
  on both screens wear Oliver's artwork, so three bare words beside them read as
  unfinished.
- Verified by: `tests/ui/test_shop_editing.py::test_try_save_and_put_back_wear_their_artwork`,
  `tests/ui/test_guide.py`

**FR-S44 The shops dialog follows the ticks behind it**
- Requirement: While the shops dialog is open, it shall take the albums ticked
  in the results at that moment, stating their number. The shops control shall
  bring back the one shops dialog rather than open another. While nothing
  is ticked, no shop shall be choosable.
- Rationale: The dialog stays open (FR-S07) while the ticks behind it change, so
  an album unticked since it opened must not go on opening. One dialog rather
  than one per press stops dialogs piling up, each with its own old list.
- Acceptance: Given one album ticked, the shops dialog opened, that album
  unticked and another ticked, when a shop is chosen, then only the second album
  is opened; given the dialog closed, an album ticked afresh (closing cleared the
  ticks, FR-S45) and the control pressed again, then the same dialog comes back.
- Verified by: `tests/ui/test_shop_following.py`

**FR-S45 Closing the shops dialog clears every tick**
- Requirement: When the shops dialog is closed (by its Close control, by Escape
  or by the window's own close), every album in the results shall be unticked:
  those on screen, those under an artist rolled up and those a filter is holding
  back.
- Rationale: A round of shopping is finished when its dialog closes; ticks that
  outlive it are work to undo by hand before the next. A tick nobody can see is
  worse, since it would be sent with the next round unnoticed. This narrows
  FR-D56: a tick still outlives a filter; it no longer outlives the close of the
  shops dialog.
- Acceptance: Given two albums ticked (one under an artist then rolled up) with
  the shops dialog opened, when it is closed, then nothing is ticked and neither
  Copy nor Find in shops is enabled. Given an album ticked and then withheld by a
  filter, when the shops dialog is closed and the filter cleared, then nothing is
  ticked.
- Verified by: `tests/ui/test_shop_closing.py`

### 3.2 Non-functional

**NFR-S-PRIV-001 Nothing but the artist and the album leaves the machine**
- Requirement: Every shop search address Stellody opens shall contain only the
  shop's own template text, the artist name and the album title. It shall contain
  no identifier for the listener, the machine or the library, nor any other
  album.
- Rationale: The stance PLAN.md records, stated as something testable rather than
  as an intention. Handing an address to a browser is not an outward call that
  carries the library; that stays true only while the address carries nothing
  else.
- Acceptance: Given a shop template and an album, when the address is built, then
  it equals that template with the encoded artist and the encoded title put in
  place of the two placeholders.
- Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_an_address_carries_nothing_but_the_album`

**NFR-S-USE-001 The shops dialog can be read**
- Requirement: Every colour the shops dialog and the shop form use for text shall
  hold a contrast ratio of at least 4.5 to 1 against the surface behind it, in
  both appearances, measured by the WCAG relative luminance formula.
- Rationale: The same requirement as NFR-USE-002, applied to the new screens so
  neither can be the one that quietly falls short.
- Acceptance: Given either appearance, when each text colour is measured against
  its surface, then every ratio reaches 4.5.
- Verified by: `tests/ui/test_shop_contrast.py`, which measures every colour
  `shops_dialog.py` names. The shop form names only `warning`, one of those
  colours, though no test reads its source.

**NFR-S-MAIN-001 The layering and the gate hold**
- Requirement: The domain and application modules added by this specification
  shall hold 100 percent branch coverage, shall import nothing from
  infrastructure or UI and shall each stay within the 400-line module cap. The
  merge rules FR-S30 to FR-S34 and FR-S36 sit in the domain as one pure function,
  `merged`; putting back (FR-S37) is a pure method, `ShopBook.put_back`.
- Rationale: The house invariants, restated here because a new area is where they
  get forgotten first.
- Acceptance: Given the suite, when it runs, then the coverage gate passes and the
  structural tests pass unchanged.
- Verified by: the existing `tests/structural` suite plus the coverage gate.

### 3.3 External interfaces

**The browser.** One call per address to the operating system's default
handler, through a port the application layer declares and the infrastructure
layer implements. The shop form saves only an `https` address (FR-S20); a
hand-edited row is not held to that, so its address is handed over as it
stands. Nothing waits for the page to load. The call answers only whether the
machine took the address, which the application layer reads to report an
address that would not open (FR-S13).

**The clipboard.** Plain text only, through the same arrangement.

### 3.4 Data requirements

The shop file lives beside the discovery file in Stellody's own directory and
is named `shops.json`. Its shape:

```json
{
  "shops": [
    {
      "name": "Qobuz",
      "template": "https://www.qobuz.com/gb-en/search?q={artist}%20{album}",
      "note": "Lossless and hi-res downloads only."
    }
  ],
  "shipped": [
    {
      "name": "Qobuz",
      "template": "https://www.qobuz.com/gb-en/search?q={artist}%20{album}",
      "note": "Lossless and hi-res downloads only."
    }
  ],
  "deleted": ["Beatport"],
  "retired": ["Bleep"]
}
```

- `shops` is the list in use; `shipped` records the release list the rows were
  last settled against, which is how FR-S32 and FR-S33 tell an untouched
  shipped shop from an edited one. A file whose `shipped` is missing or is not a
  list is read as settled against this release, so none of its rows is taken
  for out of date.
- `deleted` is the deleted record (FR-S25, FR-S26, FR-S36); `retired` is the
  retired record (FR-S34, FR-S35).
- `name` and `template` are required. A row missing either is kept in its
  place with its reason (FR-S42), as is an entry that is not an object.
- `note` is optional and is shown beside the shop.
- Order in the file is the order in the dialog.
- Unknown keys are ignored, so a file written by a later Stellody is read by an
  earlier one. They are not kept: every write holds only the keys named here.

**The shipped defaults** are `DEFAULT_SHOPS` in `infrastructure/shop_file.py`,
in this order: 7digital (first by Oliver's ruling), Qobuz, Bandcamp, Boomkat,
Bleep, Presto Music, ProStudioMasters, Beatport. Each template was loaded and
answered before it shipped. A note says what a shop stocks, never a caveat about
its address (Oliver's ruling). Two templates carry a deliberate shape: 7digital
uses the UK storefront with `fallback=true` (A-01); Boomkat searches the artist
alone under its Download filter (FR-S10).

Not shipped: Juno Download (closed); Traxsource and eClassical (their bot and
consent walls could not be read past); Volumo (its search path answered 404);
HDtracks (Oliver's ruling, OQ-S01). Any of them can be added as a row.

## 4. Other requirements

**Legal.** Each shop's terms govern what happens on its own site. Stellody
opens a public search address in the listener's browser, which is the same act
as clicking a link. It holds no account, no credential and no relationship with
any shop. Adding a shop that forbids being linked to is the listener's decision
and their file.

**Risk.** Judged disproportionate to a personal utility that opens a web search.
No FMEA.

## 5. Appendices

### A. Open questions

Nothing marked open may be built from. None is open.

| # | Question | Owner |
|---|---|---|
| OQ-S01 | HDtracks does not join the shipped defaults (Oliver's ruling); it stays addable as a row. | Answered |
| OQ-S02 | An editor screen is wanted: the list is edited on the shops dialog (FR-S17 to FR-S43). | Answered |
| OQ-S03 | No shop is reached for an album already held, for a better copy or otherwise (Oliver's ruling). | Answered |
| OQ-S04 | A row broken by hand-editing is listed greyed out with its reason, plus edit and delete (FR-S42). | Answered |

### B. Prioritisation

Must: FR-S01 to FR-S45 and every NFR.
Should: nothing this stage.
Could: nothing this stage.
Won't, this time: payments, prices, stock, shop APIs, affiliate links, physical
media, streaming, remembering what was bought, reaching a shop for an album
already held, editing shops outside the shops dialog, importing or exporting a
shop list.

### C. The build order this implies

Inside out. No user-visible action waits on a screen to be exercisable.

1. **Domain**: the address rule (a shop as a value object, the placeholder
   substitution and the encoding), then the shop list rules (name matching, the
   edited test, the merge of FR-S30 to FR-S34, putting back, moving); pure and
   unit tested.
2. **Application**: the use case that turns ticked albums plus a chosen shop
   into addresses, over three declared ports: where the shop list comes from,
   how an address is opened and where copied text is put. Then add, edit,
   delete, move, put back and try, as methods of one use case, `ShopEditing`,
   over a store port that reads and writes the list plus the opener port.
3. **Infrastructure**: the shop file reader and writer, including `deleted` and
   `retired`, plus the opener that hands an address to the operating system.
4. **UI**: the tick boxes, the two controls, the shops dialog with its row
   controls and handle, the shop form, the guide entries, last.

The diagnostic that says the foundation is sound: building every address for a
set of ticked albums at a chosen shop must be executable from a test with no
screen and no browser, before the dialog exists; so must every change to the
list.
