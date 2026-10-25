# Reaching the shops that sell what the library is missing

Specification for the second stage of discovery: from an album the library
lacks to a shop that sells it. EARS requirements in the house form, each naming
the test that proves it. It is built.

## 1. Introduction

### 1.1 Purpose

From a ticked album in the discovery results, one press reaches a shop's own
search results for it. The shop list is edited from inside Stellody.

### 1.2 Intended audience

Implementers, reviewers and Oliver, who owns every decision here.

### 1.3 Scope

**In scope:** ticking albums in the results dialog; a shops dialog; opening a
shop's search for the ticked albums in the listener's browser; copying the
ticked albums as text; a shop list held as data; adding, editing, deleting,
moving and putting back shops from the shops dialog.

**Out of scope:**

- Payments, baskets, accounts, sign-in, prices, stock or availability.
- Shop APIs, credentials or scraping; affiliate links.
- Physical media (Oliver's ruling); streaming services.
- Remembering what was bought or marking a gap as dealt with.
- Reaching a shop for an album already held (Oliver's ruling, OQ-S03).
- Editing shops anywhere but the shops dialog; importing, exporting or sharing
  a shop list; a picture per shop.
- Checking automatically that a shop's search finds anything.
- Hand-editing `shops.json` stays possible but is not the intended route
  (FR-S42).

### 1.4 Definitions

| Term | Meaning here |
|---|---|
| Gap | An album the library lacks, as a discovery run reported it. |
| Shop | A digital music retailer: one row in the shop list. |
| Template | A shop's search address holding `{artist}`, `{album}` or both. |
| Ticked | An album whose tick box in the results dialog is checked. |
| Artist | What a ticked album carries to a shop and to Copy: the artist of its heading; an entry under a series heading (FR-D74) carries "Various Artists". Held by `tests/ui/test_results_series.py::test_a_series_entry_goes_to_the_shops_under_various_artists`. |
| Title | An album's bare title. The row reads "Title (year)" (FR-D68) but shops and Copy read the row's data, never its text. Held by `tests/ui/test_discovery_years.py::TestAnAlbumRowSaysItsYear::test_a_shop_is_asked_for_the_title_alone`. |
| Opening | Handing an address to the operating system's default browser. |
| Shipped shop | A shop named in the list this Stellody ships; names compare ignoring case and surrounding space. |
| Own shop | A shop the listener added whose name no shipped list carries. |
| Edited | A shipped shop whose name, address or note differs from its recorded shipped copy. Moving is not editing. |
| Deleted record | Names of shipped shops the listener deleted, kept in the shop file. |
| Retired record | Names of shops removed because a release stopped shipping them, kept until the dialog has said so. |
| Shop form | The dialog Add and Edit open: Name, Search address, Note; Cancel, Try and Save. |

Nothing here is ever a track.

### 1.5 References

- `DISCOVERY.md`, the stage this continues.
- `PLAN.md`, which records the network stance.
- `ARCHITECTURE.md` invariant 12, naming every module allowed a connection.

## 2. Overall description

### 2.1 Product perspective

An addition to the results dialog of FR-D28 to FR-D34, a small application
service and `shops.json` in Stellody's own directory. Opening a browser is not
a connection this application makes, so invariant 12's four modules stay four.

### 2.2 User classes

One: the listener, who owns the library and the machine.

### 2.3 Operating environment

Windows, macOS and Linux. A default browser is assumed; failing to open one is
specified (FR-S13).

### 2.4 Constraints

- Nothing identifying the listener or the library leaves the machine; an
  address carrying an artist and an album, sent through the browser, is all
  that goes out.
- The shop list is data, so a shop that closes or moves its search is an edit
  rather than a release.
- House rules: clean-architecture layering, modules within `LINE_CAP`
  (`tests/structural/test_loc.py`), 100 percent branch coverage over domain and
  application, no magic values, no Qt below infrastructure.

### 2.5 Assumptions and dependencies

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | 7digital's search takes `q`; the shipped row carries the UK host and `fallback=true`. Whether artist plus album answers is left to the page (A-03). | Oliver | Answered |
| A-02 | `assets/copy.png` is supplied, matching `shop.png`. | Oliver | Answered |
| A-03 | Shipped shops are not re-checked each release (Oliver's ruling); FR-S09 makes a rotten shop an edit. | Oliver | Answered |
| A-04 | `assets/drag-up-down.png` is supplied for the handle. | Oliver | Answered |
| A-05 | Dragging a row in the shops dialog is feasible in PySide6, held by `tests/ui/test_shop_dragging.py`. | Oliver | Answered |

## 3. Requirements

Every requirement is a Must unless it carries a Priority line (Appendix B).

### 3.1 Functional

**FR-S01 An album can be ticked**
- Requirement: The results dialog shall show a tick box, initially unticked,
  against every album row (Oliver's ruling).
- Verified by: `tests/ui/test_shop_choosing.py::test_every_album_row_can_be_ticked`

**FR-S02 Only albums can be ticked**
- Requirement: The results dialog shall show no tick box against an artist row
  of either kind.
- Verified by: `tests/ui/test_shop_choosing.py::test_an_artist_row_carries_no_tick_box`

**FR-S03 Fetching a candidate's albums gives them tick boxes**
- Requirement: When a candidate artist's albums arrive, the results dialog
  shall draw each with an unticked tick box.
- Verified by: `tests/ui/test_shop_choosing.py::test_fetched_albums_can_be_ticked_too`,
  `tests/ui/test_shop_choosing.py::test_every_fetched_album_arrives_unticked`

**FR-S04 Nothing ticked offers no lookup**
- Requirement: While no album is ticked, the results dialog shall disable the
  shops control and the copy control.
- Verified by: `tests/ui/test_shop_choosing.py::test_the_shops_control_waits_for_a_tick`

**FR-S05 The shops are offered in a dialog**
- Requirement: When the shops control is pressed, the results dialog shall show
  its one shops dialog (FR-S44), listing every configured shop and the number
  of ticked albums (Oliver's ruling).
- Verified by: `tests/ui/test_shop_dialog.py::test_it_lists_the_shops_and_counts_the_albums`

**FR-S06 Choosing a shop opens its search for every ticked album**
- Requirement: When a shop is chosen, the shops dialog shall open that shop's
  search address once per ticked album in the default browser, then say how
  many searches it opened at that shop.
- Verified by: `tests/ui/test_shop_dialog.py::test_choosing_a_shop_opens_one_search_an_album`,
  `tests/ui/test_shop_dialog.py::test_it_says_what_it_just_opened`

**FR-S07 The shops dialog stays open**
- Requirement: Choosing a shop shall leave the shops dialog open until the
  listener closes it, so prices can be compared (Oliver's ruling).
- Verified by: `tests/ui/test_shop_dialog.py::test_it_stays_open_so_prices_can_be_compared`

**FR-S08 Many albums are confirmed first**
- Requirement: If more than `MOST_WITHOUT_ASKING` (`application/shopping.py`;
  Oliver's ruling) albums are ticked when a shop is chosen, then the shops
  dialog shall ask for confirmation naming the number of tabs about to open,
  opening none unless confirmed.
- Verified by: `tests/ui/test_shop_dialog.py::test_a_large_number_of_tabs_is_asked_about_first`, `tests/ui/test_shop_dialog.py::test_a_refused_confirmation_opens_nothing`, `tests/ui/test_shop_dialog.py::test_a_handful_is_not_asked_about`

**FR-S09 The shop list is read from a file**
- Requirement: The shop service shall read the shop list from a file in
  Stellody's own directory, writing the shipped defaults there where none
  exists.
- Verified by: `tests/infrastructure/test_shop_file.py::TestTheFirstTime::test_a_missing_file_is_written_with_the_defaults`

**FR-S10 A template names the artist and the album separately**
- Requirement: The shop service shall build an address by replacing `{artist}`
  and `{album}` in a template with the album's artist and title, each percent
  encoded with a space as `%20`.
- Rationale: Some shops search badly on two terms; some show `+` literally.
- Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_both_placeholders_are_filled_and_encoded`

**FR-S11 A template that names neither is refused**
- Requirement: If a template holds neither `{artist}` nor `{album}`, then the
  shop service shall exclude that row from the searchable shops and keep it in
  the list with its reason (FR-S42).
- Verified by: `tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_template_with_no_placeholder_is_refused`

**FR-S12 A shop file that cannot be read falls back**
- Requirement: If the shop file cannot be parsed, its top level is not a JSON
  object or its `shops` is not a list, then the shop service shall offer the
  shipped defaults and write the file as a first run does (FR-S09; Oliver's
  ruling). Broken rows do not make a file unusable (each is kept and named,
  FR-S42); nor does an empty list.
- Verified by: `tests/infrastructure/test_shop_file.py::TestWhatCannotBeRead::test_it_falls_back_to_the_installed_list`, `tests/infrastructure/test_shop_file.py::TestWhatCannotBeRead::test_a_directory_that_cannot_be_written_still_offers_the_shops`

**FR-S13 A browser that will not open says so**
- Requirement: If the operating system cannot open an address, then the shops
  dialog shall say so naming the shop; the dialog stays open.
- Verified by: `tests/ui/test_shop_dialog.py::test_a_browser_that_will_not_open_says_so`,
  `tests/ui/test_shop_dialog.py::test_a_refusal_leaves_the_dialog_standing`

**FR-S14 The ticked albums can be copied as text**
- Requirement: When the copy control is pressed, the results dialog shall put
  one line per ticked album, holding its artist and title, on the clipboard
  (Oliver's ruling).
- Verified by: `tests/ui/test_shop_choosing.py::test_copy_puts_the_ticked_albums_on_the_clipboard`

**FR-S15 Both controls are reachable from the keyboard**
- Requirement: The results dialog shall open focused on its first list with
  its first row current. The keyboard ring shall take each list then the
  controls in drawn order: Close on the left; the pager's two directions in the
  middle; Filter, Copy and Find in shops on the right. In a list, Up and Down
  walk the rows; Right opens an artist and Left shuts it; Enter and Space tick
  or untick an album and open or shut an artist. The current row wears the ring
  while its list has focus. A list reached by Tab or Shift+Tab with no current
  row makes its first row current; a list reached by a click keeps its current
  row and scroll position. (The house keyboard model; Oliver's ruling.)
- Verified by: `tests/ui/test_shop_choosing.py::test_the_ticks_and_the_controls_are_stops_on_the_ring`,
  `tests/ui/test_shop_choosing.py::test_a_tick_box_is_reached_and_ticked_from_the_keyboard`,
  `tests/ui/test_space_chooses.py::TestADialogOverTheWindow::test_space_still_ticks_an_album_in_the_results`,
  `tests/ui/test_results_keyboard.py`,
  `tests/ui/test_ticking_a_scrolled_row.py`

**FR-S16 A release meets the list shop by shop**
- Requirement: The shop service shall settle each row of the shop file against
  the current shipped list on its own (FR-S30 to FR-S36), never replacing a
  whole file judged unedited.
- Verified by: the tests of FR-S30 to FR-S36.

**FR-S17 A shop can be added**
- Requirement: When the add control is pressed, the shops dialog shall open the
  shop form with every field empty.
- Verified by: `tests/ui/test_shop_editing.py::test_add_opens_an_empty_form`

**FR-S18 A shop can be edited**
- Requirement: When a shop's edit control is pressed, the shops dialog shall
  open the shop form holding that shop's name, address and note.
- Verified by: `tests/ui/test_shop_editing.py::test_edit_opens_the_form_holding_the_shop`

**FR-S19 Saving puts the shop in the list**
- Requirement: When Save is pressed on a form passing FR-S20 and FR-S21, the
  shop service shall write the list with an added shop last or an edited shop
  in its place; the shops dialog shall then show the list as written.
- Verified by: `tests/application/test_editing_the_shop_list.py::test_an_added_shop_goes_last`,
  `tests/application/test_editing_the_shop_list.py::test_an_edited_shop_keeps_its_place`,
  `tests/ui/test_shop_editing.py::test_a_saved_form_puts_the_shop_last`

**FR-S20 A broken shop cannot be saved**
- Requirement: If the name is empty, the address is empty, the address does not
  begin with `https://` or it names neither `{artist}` nor `{album}`, then the
  shop form shall refuse to save and say which beside the field concerned.
- Verified by: `tests/ui/test_shop_editing.py::test_a_shop_that_cannot_search_is_not_saved`

**FR-S21 Two shops cannot share a name**
- Requirement: If the name matches another shop's, ignoring case and
  surrounding space, then the shop form shall refuse to save and say the name
  is taken.
- Verified by: `tests/domain/test_shop_list.py::TestTheForm::test_a_name_already_used_is_refused`,
  `tests/ui/test_shop_editing.py::test_a_shop_that_cannot_search_is_not_saved`

**FR-S22 A shop can be tried before it is saved**
- Requirement: When Try is pressed, the shop form shall open its current
  address for the first ticked album in drawn order, in the default browser,
  saving nothing; the name may be empty (Oliver's ruling). If the address
  breaks an address rule of FR-S20, then the form shall open nothing and say
  which beside the address. A form opened while nothing is ticked (possible
  under FR-S44) shall disable Try.
- Verified by: `tests/ui/test_shop_editing.py::test_try_opens_the_first_ticked_album`,
  `tests/ui/test_shop_editing.py::test_a_try_with_a_broken_address_opens_nothing`

**FR-S23 A try that will not open says so**
- Requirement: If the operating system cannot open the address Try built, then
  the shop form shall say so and stay open.
- Verified by: `tests/ui/test_shop_editing.py::test_a_try_that_will_not_open_says_so`

**FR-S24 Deleting asks first**
- Requirement: When a shop's delete control is pressed, the shops dialog shall
  ask for confirmation naming the shop, deleting it only on yes (Oliver's
  ruling).
- Verified by: `tests/ui/test_shop_editing.py::test_delete_asks_naming_the_shop`,
  `tests/ui/test_shop_editing.py::test_a_refused_delete_keeps_the_shop`

**FR-S25 A deleted shipped shop is remembered**
- Requirement: When a shipped shop is deleted, the shop service shall add its
  name to the deleted record, so no update brings it back (Oliver's ruling).
- Verified by: `tests/application/test_editing_the_shop_list.py::test_deleting_a_shipped_shop_records_it`

**FR-S26 Renaming a shipped shop is a delete plus an add**
- Requirement: When a shipped shop is saved under a different name, the shop
  service shall add its original name to the deleted record.
- Rationale: Otherwise the next release adds the original back.
- Verified by: `tests/application/test_editing_the_shop_list.py::test_renaming_a_shipped_shop_records_the_old_name`

**FR-S27 A shop is moved by dragging its handle**
- Requirement: While a shop's handle is held, the shops dialog shall carry the
  row with the pointer and glide every other row to where it would sit were the
  row let go there, judged from where the rows started (Oliver's ruling). On
  release the shop service shall write the new order, then the row glides into
  place; if the write fails, the row glides back. Release where the row was
  taken writes nothing. While a row is held or landing, Ctrl+Up and Ctrl+Down
  move nothing.
- Verified by: `tests/ui/test_shop_dragging.py::test_the_held_row_follows_the_pointer`,
  `tests/ui/test_shop_dragging.py::test_the_other_rows_make_room_before_it_is_let_go`,
  `tests/ui/test_shop_dragging.py::test_dragging_the_handle_moves_the_shop`,
  `tests/ui/test_shop_dragging.py::test_a_move_the_file_refuses_glides_back`,
  `tests/ui/test_shop_dragging.py::test_letting_go_where_it_was_taken_writes_nothing`,
  `tests/ui/test_shop_dragging.py::test_every_shop_can_be_dragged_to_the_bottom`,
  `tests/ui/test_shop_dragging.py::test_the_keyboard_waits_while_a_row_is_held`

**FR-S28 A shop is moved from the keyboard**
- Requirement: While one of a shop's controls has focus, when Ctrl+Up or
  Ctrl+Down is pressed, the shop service shall move that shop one place and
  write the list, focus staying on that control. A move past either end does
  nothing.
- Verified by: `tests/ui/test_shop_editing.py::test_ctrl_arrows_move_the_focused_shop`

**FR-S29 A change that cannot be written is not shown as made**
- Requirement: If an add, edit, delete or move cannot be written, then the
  screen it was made on shall say so (the shop form for add or edit, the shops
  dialog for delete or move) while the shops dialog keeps showing the list as
  it was.
- Verified by: `tests/ui/test_shop_editing.py::test_a_change_that_cannot_be_saved_is_not_shown`,
  `tests/ui/test_shop_editing.py::test_a_form_that_cannot_be_kept_says_so`

**FR-S30 A new shipped shop is added**
- Requirement: When the shipped list holds a shop whose name is neither in use
  nor in the deleted record, the shop service shall add it last, leaving the
  listener's order alone (Oliver's ruling).
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_new_shipped_shop_is_added_last`

**FR-S31 A shop somebody deleted stays deleted**
- Requirement: If a shipped shop's name is in the deleted record, then the shop
  service shall leave it out of the list in use.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_deleted_shop_never_returns`

**FR-S32 An untouched shipped shop follows the release**
- Requirement: When a release changes the address or note of an unedited
  shipped shop, the shop service shall take the new values, keeping its place.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_untouched_shop_takes_the_new_address`

**FR-S33 An edited shipped shop keeps the edit**
- Requirement: If a shipped shop is edited, then the shop service shall keep the
  listener's name, address and note whatever a release changes. A release never
  touches own shops.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_edited_shop_keeps_the_edit`

**FR-S34 A shop a release drops is removed where untouched**
- Requirement: When a release no longer ships a shop the recorded shipped list
  held, the shop service shall remove it from the list in use if unedited and
  name it in the retired record; an edited one stays.
- Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_untouched_shop_is_removed`,
  `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_edited_shop_stays`

**FR-S35 A removed shop is announced once**
- Requirement: When the shops dialog opens while the retired record names
  shops, it shall say which were removed because Stellody no longer ships them;
  the shop service shall then empty the retired record.
- Verified by: `tests/ui/test_shop_editing.py::test_a_removed_shop_is_announced_once`

**FR-S36 A file with no deleted record gains nothing by surprise**
- Requirement: If the shop file has no deleted record, then the shop service
  shall write an empty one without adding any shipped shop the list lacks.
- Rationale: Such a file predates the editor, so a missing shipped shop may
  have been removed by hand on purpose.
- Verified by: `tests/infrastructure/test_shop_file.py::TestMeetingARelease::test_an_older_file_is_not_added_to`

**FR-S37 The original shops can be put back**
- Requirement: When put back is pressed and confirmed, the shop service shall
  write the shipped shops in shipped order with shipped values, then the own
  shops in their current order, emptying the deleted record in the same write.
- Verified by: `tests/domain/test_shop_list.py::TestTheWayBack::test_putting_back_keeps_own_shops`

**FR-S38 Putting back asks first**
- Requirement: When put back is pressed, the shops dialog shall ask for
  confirmation, changing nothing unless the answer is yes.
- Verified by: `tests/ui/test_shop_editing.py::test_putting_back_asks_first`

**FR-S39 An empty list still offers Add**
- Requirement: While the list is empty, the shops dialog shall show the add
  control and a line saying there are no shops yet. A list emptied from the
  dialog stays empty, since every shipped name is then in the deleted record.
- Verified by: `tests/ui/test_shop_editing.py::test_an_empty_list_offers_add`

**FR-S40 Every new control is on the keyboard ring**
- Requirement: The shops dialog shall put each shop's button, edit and delete
  controls, Close, add and put back on the keyboard ring in reading order; its
  foot reads Close on the left, then add and put back on the right (Oliver's
  ruling, as FR-D97). The shop form's foot reads Cancel on the left, then Try
  and Save on the right, tabbed in that order. The handle is not a stop; FR-S28
  is its keyboard equivalent.
- Verified by: `tests/ui/test_shop_editing.py::test_the_ring_walks_the_rows_in_reading_order`, `tests/ui/test_shop_editing.py::test_the_forms_cancel_stands_left_of_try_and_save`

**FR-S41 The row controls wear artwork the guide explains**
- Requirement: The add, edit and delete controls shall wear `add.png`,
  `edit.png` and `delete.png`; the handle shall wear `drag-up-down.png`. The
  guide shall show all four beside what each does.
- Rationale: Delete avoids `negative.png`, which is kept for striking through
  other artwork (`struck_through`).
- Verified by: `tests/ui/test_guide.py::TestWhatItNames::test_every_picture_the_dialogs_name_is_explained_too`

**FR-S42 A hand-broken row can be mended from the dialog**
- Requirement: If a row in the shop file cannot be read as a shop, then the
  shops dialog shall list it greyed out with its reason, offering edit and
  delete and no search (Oliver's ruling, OQ-S04). Edit opens the form holding
  whatever the row carried, so FR-S20 decides whether it saves.
- Verified by: `tests/ui/test_shop_editing.py::test_a_broken_row_is_listed_greyed_with_its_reason`,
  `tests/ui/test_shop_editing.py::test_a_broken_row_is_deleted_after_asking`,
  `tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_broken_row_is_read_with_its_reason`

**FR-S43 Try, Save and put back wear artwork**
- Requirement: The shop form shall show `try.png` on Try and `save.png` on
  Save; the shops dialog shall show `revert-shops.png` on put back. The guide
  shall show all three beside what each does.
- Verified by: `tests/ui/test_shop_editing.py::test_try_save_and_put_back_wear_their_artwork`,
  `tests/ui/test_guide.py::TestWhatItNames::test_every_picture_the_dialogs_name_is_explained_too`

**FR-S44 The shops dialog follows the ticks behind it**
- Requirement: While open, the shops dialog shall take the albums ticked in the
  results at that moment, stating their number, excluding any tick a filter is
  withholding (FR-D56). The shops control shall bring back the one shops dialog
  rather than open another. While nothing is ticked, no shop is choosable.
- Verified by: `tests/ui/test_shop_following.py`

**FR-S45 Closing the shops dialog clears every tick**
- Requirement: When the shops dialog is closed (Close, Escape or the window's
  close), every album in the results shall be unticked: on screen, under a
  rolled up artist and held back by a filter. This narrows FR-D56: a tick
  outlives a filter, not the close of the shops dialog.
- Verified by: `tests/ui/test_shop_closing.py`

### 3.2 Non-functional

**NFR-S-PRIV-001 Nothing but the artist and the album leaves the machine**
- Requirement: Every shop search address Stellody opens shall contain only the
  template's own text, the artist name and the album title: no identifier of
  the listener, the machine or the library, nor any other album.
- Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_an_address_carries_nothing_but_the_album`

**NFR-S-USE-001 The shops dialog can be read**
- Requirement: As NFR-USE-002, every text colour the shops dialog and the shop
  form use shall meet `READABLE` (`tests/ui/contrast_support.py`, a WCAG
  contrast ratio) against the surface behind it, in both appearances.
- Verified by: `tests/ui/test_shop_contrast.py`, which measures every colour
  `shops_dialog.py` names. The shop form names only `warning`, one of those
  colours, though no test reads its source.

**NFR-S-MAIN-001 The layering and the gate hold**
- Requirement: The domain and application modules of this specification shall
  hold 100 percent branch coverage, import nothing from infrastructure or UI
  and stay within `LINE_CAP`. The merge rules FR-S30 to FR-S34 and FR-S36 are
  one pure domain function, `merged`; putting back (FR-S37) is a pure method,
  `ShopBook.put_back`.
- Verified by: the existing `tests/structural` suite plus the coverage gate.

### 3.3 External interfaces

**The browser.** One call per address to the operating system's default
handler, through a port the application layer declares and infrastructure
implements. The form saves only `https` addresses (FR-S20); a hand-edited row's
address is handed over as it stands. Nothing waits for the page; the call
answers only whether the machine took the address (FR-S13).

**The clipboard.** Plain text, through the same arrangement.

### 3.4 Data requirements

`shops.json` lives beside the discovery file in Stellody's own directory:

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

- `shops` is the list in use, in dialog order; `shipped` is the release list
  last settled against, which tells edited from untouched (FR-S32, FR-S33). A
  missing or non-list `shipped` is read as settled against this release.
- `deleted` is the deleted record (FR-S25, FR-S26, FR-S36); `retired` the
  retired record (FR-S34, FR-S35).
- `name` and `template` are required; a row missing either is kept in place
  with its reason (FR-S42), as is an entry that is not an object. `note` is
  optional and shown beside the shop.
- Unknown keys are ignored on read and dropped on write.

**The shipped defaults** are `DEFAULT_SHOPS` in `infrastructure/shop_file.py`,
in this order: 7digital (first by Oliver's ruling), Qobuz, Bandcamp, Boomkat,
Bleep, Presto Music, ProStudioMasters, Beatport. A note says what a shop
stocks, never a caveat about its address (Oliver's ruling). 7digital uses the
UK storefront with `fallback=true` (A-01); Bandcamp asks for albums alone with `item_type=a`; Boomkat searches the artist
alone under its Download filter (FR-S10).

Not shipped, all addable as rows: Juno Download, Traxsource, eClassical and
Volumo; HDtracks too (Oliver's ruling, OQ-S01).

## 4. Other requirements

**Legal.** Each shop's terms govern its own site. Opening a public search
address is the same act as clicking a link; Stellody holds no account,
credential or relationship with any shop.

**Risk.** Disproportionate for a utility that opens a web search; no FMEA.

## 5. Appendices

### A. Open questions

None open; nothing open may be built from.

| # | Question | Owner |
|---|---|---|
| OQ-S01 | HDtracks is not shipped (Oliver's ruling); it stays addable. | Answered |
| OQ-S02 | The list is edited on the shops dialog (FR-S17 to FR-S43). | Answered |
| OQ-S03 | No shop is reached for an album already held (Oliver's ruling). | Answered |
| OQ-S04 | A hand-broken row is listed greyed with its reason, plus edit and delete (FR-S42). | Answered |

### B. Prioritisation

Must: FR-S01 to FR-S45 and every NFR. Should and Could: nothing.
Won't: everything listed out of scope in section 1.3.

### C. The build order this implies

Inside out:

1. **Domain**: the shop value, placeholder substitution and encoding; the list
   rules (name matching, the edited test, the merge, putting back, moving).
2. **Application**: turning ticked albums plus a shop into addresses over three
   ports (shop list source, opener, clipboard); then `ShopEditing` (add, edit,
   delete, move, put back, try) over a store port and the opener.
3. **Infrastructure**: the shop file reader and writer; the opener.
4. **UI** last: tick boxes, the two controls, the shops dialog, the shop form,
   the guide entries.

Every address for a set of ticked albums at a shop must be buildable from a
test with no screen and no browser; so must every change to the list.
