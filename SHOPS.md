# Reaching the shops that sell what the library is missing

Specification for the second stage of discovering music the library does not
hold. The first stage says
what the library is missing; this says how somebody gets from one of those gaps
to a place that sells it. It is written before the code, in the house form:
EARS requirements, each with the failure case beside it, each naming the test
that will prove it.

Baseline: this specification as first written, 2026-09-08. Changes after that
arrive as numbered amendments with a reason rather than as silent edits. No
number of its own: a document version beside a product version is two numbers
a reader has to tell apart, only one of them the product's.

It is built. Every requirement below names the test that holds it; FR-S11 says
plainly where the build stops short of its requirement. Amendment 1, in section
6, is built.

## 1. Introduction

### 1.1 Purpose

A discovery run ends with a list of albums the library does not hold. Before
this stage that list was somewhere to look at rather than somewhere to act, so
buying one of them meant retyping an artist and a title into a shop by hand. This closes that
gap: from a ticked album, one press reaches a shop's own search results for it.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 Scope

**In scope:** ticking albums in the results dialog; a dialog that lists the
shops; opening a shop's search for the ticked albums in the listener's own
browser; copying the ticked albums as text; a shop list that is data rather
than code.

**Out of scope, so that it is not re-proposed:**

- Any payment, basket, account, sign-in or price display. Stellody opens a
  search and stops there. What happens next is between the listener and the
  shop.
- Any shop API, any credential and any scraping of a shop's pages. The browser
  does the asking; Stellody only ever hands over an address.
- Prices, stock and availability shown inside Stellody. Those need what the
  bullet above rules out.
- Affiliate links or any revenue arrangement.
- Physical media. Digital only, ruled by Oliver on 2026-09-07.
- Streaming services. This is about owning a copy.
- Remembering what was bought; marking a gap as dealt with.
- Reaching a shop from the main library window for an album already held.
  Recorded in the open questions rather than built.
- ~~An editor screen for the shop list.~~ Struck by Amendment 1, which puts
  one on the shops dialog.

### 1.4 Definitions

| Term | Meaning here |
|---|---|
| Gap | An album the library does not hold, as a discovery run reported it. |
| Shop | A digital music retailer, named by a row in the shop list. |
| Template | A shop's search address holding `{artist}` and `{album}` placeholders. |
| Ticked | An album whose tick box in the results dialog is checked. |
| Opening | Handing an address to the operating system's default browser. |

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

Windows, Linux and macOS, the three Stellody already ships to. A default
browser is assumed present; the case where the operating system cannot open one
is specified rather than assumed away.

### 2.4 Constraints

- Nothing identifying the listener or the library may leave the machine. An
  address carrying an artist and an album is the whole of what goes out. It
  travels through the browser rather than from Stellody.
- The shop list is data. Measured on 2026-09-07: Juno Download had closed,
  7digital had put a bot wall in front of its search and Volumo's search path
  had become a 404, all within one afternoon of checking eight shops. A list
  compiled into the application is a list that needs a release every time a
  shop moves.
- The house rules hold: clean-architecture layering, 400-line modules, 100
  percent branch coverage over domain and application, no magic values, PySide6
  in the UI layer only.

### 2.5 Assumptions and dependencies

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-01 | RESOLVED 2026-09-08. Oliver reached the search in a browser, past the wall that refuses us, then read back `uk.7digital.com/search?q=fleetwood%20mac&fallback=true`. The `q` parameter is confirmed; the shipped row now carries the regional host and the fallback with it. What one name cannot show is whether an artist and an album together answer, as Boomkat did not. | Oliver | Answered |
| A-02 | RESOLVED 2026-09-08. `assets/copy.png` supplied: 1254 square, transparent, matching `shop.png`. | Oliver | Answered |
| A-03 | RESOLVED 2026-09-08. Measured 2026-09-07, then confirmed by Oliver against the running application, every shipped shop opening. He ruled that it is not to be re-checked at each release: FR-S09 already puts the shop list in a file, so a shop that rots is an edit somebody makes rather than a release somebody waits for. Re-verifying eight addresses before every tag buys nothing the file does not already give. | Oliver | Answered |

## 3. Requirements

### 3.1 Functional

---

**FR-S01 An album can be ticked**

Priority: Must

Requirement: The results dialog shall show a tick box against every album row,
unticked when the row is first drawn.

Rationale: Ruled by Oliver on 2026-09-08. Selection in a tree is invisible once
focus moves and cannot survive a row being rebuilt; a tick box is a state the
reader can see and the dialog can read back.

Acceptance: Given a run holding two albums under one artist, when the dialog
opens, then each album row carries an unticked box and no artist row carries one.

Verified by: `tests/ui/test_shop_choosing.py::test_every_album_row_can_be_ticked`

---

**FR-S02 Only albums can be ticked**

Priority: Must

Requirement: The results dialog shall not show a tick box against an artist row
of either kind.

Rationale: The unwanted sibling of FR-S01. An artist is not something a shop
sells; a candidate artist row with no albums fetched has nothing to look up.

Acceptance: Given a dialog holding a source artist and a candidate artist, when
the rows are read, then neither carries a tick box.

Verified by: `tests/ui/test_shop_choosing.py::test_an_artist_row_carries_no_tick_box`

---

**FR-S03 Fetching a candidate's albums gives them tick boxes**

Priority: Must

Requirement: When the albums of a candidate artist arrive, the results dialog
shall draw each with a tick box, unticked.

Rationale: Those albums are the ones least likely to be held, so they are the
ones most likely to be wanted. They arrive after the dialog is built, which is
the case a tick box added only at build time would miss.

Acceptance: Given a candidate artist expanded and answered with three albums,
when its rows are read, then each carries an unticked box.

Verified by: `tests/ui/test_shop_choosing.py::test_fetched_albums_can_be_ticked_too`

---

**FR-S04 Nothing ticked offers no lookup**

Priority: Must

Requirement: While no album is ticked, the results dialog shall disable the
control that opens the shops.

Rationale: A press that can only report emptiness is a press worth preventing.
The same rule the discovery dialog applies to its own Find button.

Acceptance: Given a dialog with nothing ticked, when the control is read, then
it is disabled; when one album is ticked, then it is enabled.

Verified by: `tests/ui/test_shop_choosing.py::test_the_shops_control_waits_for_a_tick`

---

**FR-S05 The shops are offered in a dialog**

Priority: Must

Requirement: When the shops control is pressed, the results dialog shall open a
shops dialog listing every configured shop and stating how many albums are
ticked.

Rationale: Ruled by Oliver on 2026-09-08. A press has to choose between shops;
the choice is worth a screen, since it is also where the count is confirmed
before anything opens.

Acceptance: Given three albums ticked and four shops configured, when the
control is pressed, then a dialog lists the four shops and says three albums.

Verified by: `tests/ui/test_shop_dialog.py::test_it_lists_the_shops_and_counts_the_albums`

---

**FR-S06 Choosing a shop opens its search for every ticked album**

Priority: Must

Requirement: When a shop is chosen in the shops dialog, the shops dialog shall
open that shop's search address for each ticked album in the listener's default
browser.

Rationale: The whole point. One address per album rather than one address for
all of them, since no shop searches for several albums at once.

Acceptance: Given two albums ticked and Qobuz chosen, when the shop is chosen,
then two addresses are opened, each being Qobuz's search for one of those
albums.

Verified by: `tests/ui/test_shop_dialog.py::test_choosing_a_shop_opens_one_search_an_album`

---

**FR-S07 The shops dialog stays open**

Priority: Must

Requirement: While the shops dialog is open, choosing a shop shall leave it
open, until the listener closes it.

Rationale: Ruled by Oliver on 2026-09-08: prices are compared across shops, so
a dialog that closed on the first choice would have to be reopened for every
shop after it.

Acceptance: Given a shop chosen, when the dialog is read, then it is still
open and a second shop can be chosen from it.

Verified by: `tests/ui/test_shop_dialog.py::test_it_stays_open_so_prices_can_be_compared`

---

**FR-S08 More than five albums is confirmed first**

Priority: Must

Requirement: If more than five albums are ticked when a shop is chosen, then
the shops dialog shall ask for confirmation naming the number of browser tabs
about to open, opening none of them unless it is given.

Rationale: One album is one browser tab. Thirty ticked albums is thirty tabs
arriving at once over whatever the listener was doing, which is not a state
anybody chooses deliberately. Five is the bar Oliver accepted on 2026-09-08.

Acceptance: Given six albums ticked, when a shop is chosen and the question is
answered no, then nothing is opened; when it is answered yes, then six
addresses are opened.

Verified by: `tests/ui/test_shop_dialog.py::test_a_large_number_of_tabs_is_asked_about_first`, `tests/ui/test_shop_dialog.py::test_a_refused_confirmation_opens_nothing`

---

**FR-S09 The shop list is read from a file**

Priority: Must

Requirement: The shop service shall read the shop list from a file in
Stellody's own directory, writing the shipped defaults there where no file
exists.

Rationale: Measured on 2026-09-07 across eight shops: one had closed, one had
walled its search and one had moved it. A shop list inside the application is a
release every time that happens; a file is an edit.

Acceptance: Given no shop file, when the shops dialog is opened, then the file
is written holding the shipped defaults and those shops are listed.

Verified by: `tests/infrastructure/test_shop_file.py::TestTheFirstTime::test_a_missing_file_is_written_with_the_defaults`

---

**FR-S10 A template names the artist and the album separately**

Priority: Must

Requirement: The shop service shall build an address by replacing `{artist}`
and `{album}` in a shop's template with the album's artist and title, each
percent encoded, with a space encoded as `%20`.

Rationale: Measured on 2026-09-07: Boomkat's search returned nothing for
"Autechre Amber" and 85 results including Amber for "Autechre", so a shop that
searches badly on two terms is given one. Two placeholders let each row say
what that shop can actually take. `%20` rather than `+` because HDtracks shows
a literal plus sign, while every other shop measured accepted `%20`.

Acceptance: Given the template `https://example.com/s?q={artist}%20{album}` and
the album "Hounds of Love" by "Kate Bush", when the address is built, then it is
`https://example.com/s?q=Kate%20Bush%20Hounds%20of%20Love`.

Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_both_placeholders_are_filled_and_encoded`

---

**FR-S11 A template that names neither is refused**

Priority: Must

**Completed by FR-S42.** The row is never searched; the shops dialog lists
it greyed out with its reason instead of passing over it in silence.

Requirement: If a shop's template holds neither `{artist}` nor `{album}`, then
the shop service shall leave that shop out of the list and shall say which row
was refused.

Rationale: The unwanted sibling of FR-S10. A template with no placeholder opens
the same page whatever is ticked, which looks like a broken search rather than
a mistyped row.

Acceptance: Given a shop file holding a row whose template has no placeholder,
when the list is read, then that shop is absent and the reason names it.

Verified by: `tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_template_with_no_placeholder_is_refused`

---

**FR-S12 A shop file that cannot be read falls back**

Priority: Must

Requirement: If the shop file cannot be read or does not hold a usable list,
then the shop service shall offer the shipped defaults and shall not overwrite
the file.

Rationale: The unwanted sibling of FR-S09; also the same judgement the
discovery file already makes: a list nobody can read is a disappointment, while an
exception in the middle of a results dialog is worse. The file is left alone
because a half-parsed file somebody is editing must not be replaced under them.

Acceptance: Given a shop file holding malformed JSON, when the list is read,
then the shipped defaults are offered and the file on disk is unchanged.

Verified by: `tests/infrastructure/test_shop_file.py::TestWhatCannotBeRead::test_an_unreadable_file_falls_back_and_is_left_alone`

---

**FR-S13 A browser that will not open says so**

Priority: Must

Requirement: If the operating system cannot open an address, then the shops
dialog shall say so in the dialog, naming that shop, while leaving the dialog
open.

Rationale: The unwanted sibling of FR-S06. Nothing happening at all is the one
outcome indistinguishable from the application being broken, which is the
report that produced FR-D40 a day earlier.

Acceptance: Given an opener that refuses, when a shop is chosen, then the dialog
says the address could not be opened and remains open.

Verified by: `tests/ui/test_shop_dialog.py::test_a_browser_that_will_not_open_says_so`

---

**FR-S14 The ticked albums can be copied as text**

Priority: Must

Requirement: When the copy control is pressed, the results dialog shall put one
line per ticked album on the clipboard, each holding the artist and the album
title.

Rationale: Ruled by Oliver on 2026-09-08. It covers every shop nobody has
configured, every shop that has just changed its search path and anywhere else
somebody wants to paste a list.

Acceptance: Given two albums ticked, when copy is pressed, then the clipboard
holds two lines, each naming an artist and an album.

Verified by: `tests/ui/test_shop_choosing.py::test_copy_puts_the_ticked_albums_on_the_clipboard`

---

**FR-S15 Both controls are reachable from the keyboard**

Priority: Must

Requirement: The results dialog shall place its tick boxes and both controls in
the keyboard ring, in reading order.

Rationale: The house keyboard model. A control reachable only with a mouse is
half a control.

Acceptance: Given the dialog open, when Tab is pressed repeatedly, then every
tick box and both controls are reached in the order they are drawn.

Verified by: `tests/ui/test_shop_choosing.py::test_the_ticks_and_the_controls_are_stops_on_the_ring`

---

**FR-S16 A shop file nobody has edited follows the shipped list**

Priority: Must

**Superseded by Amendment 1** (FR-S30 to FR-S36), which merges a release's
shops shop by shop rather than file by file. Kept for the record.

Requirement: The shop file shall record the shipped list it was written from
alongside the list in use. Where the two are identical and the shipped list has
since changed, the shop service shall replace both with the current shipped
list. Where its list is identical to the current shipped list but the file
records no shipped list or an older one, the shop service shall write the
current record, leaving the list itself unchanged. In every other case the file shall be left exactly as it is.

Rationale: FR-S09 writes the file once and never overwrites it, so a corrected
address can never reach anybody who has already opened the shops. Found on
2026-09-08: 7digital's address was corrected and reordered in the application
while the only file in existence went on offering the old row, which reads as
the change not having been made. The file is written once to protect an EDIT,
so what it must actually detect is whether anybody has edited it, rather than
whether it exists. Recording what was shipped is what makes that answerable
instead of guessed at: an untouched file is one that still says what we put in
it. A file carrying no record is settled the same way where it can be: one
still holding exactly the shipped list is untouched by the only other evidence
available, so it gains the record and becomes refreshable, which is what every
file written before this existed needs. One carrying no record AND a different
list is either an edit or an older list, with nothing on disk to tell them
apart, so it is left alone: the same judgement FR-S12 makes.

Acceptance: Given a shop file whose list is identical to the shipped list it
records, with a shipped list that has since changed, when the shops are read,
then the file holds the current shipped list and those shops are offered. Given
a shop file whose list differs from the shipped list it records, when the shops
are read, then the file is unchanged and its own rows are offered.

Verified by: retired with this requirement; its successors name their own tests.

---

### 3.2 Non-functional

**NFR-S-PRIV-001 Nothing but the artist and the album leaves the machine**

Priority: Must

Requirement: Every address Stellody opens shall contain only the shop's own
template text, the artist name and the album title. It shall contain no
identifier for the listener, the machine or the library, nor any other album.

Rationale: The stance PLAN.md records, stated as something testable rather than
as an intention. Handing an address to a browser is not an outward call that
carries the library; that stays true only while the address carries nothing
else.

Acceptance: Given any shipped shop and any album, when the address is built,
then the only text in it beyond the template is the artist and the title.

Verified by: `tests/domain/test_shop_address.py::TestTheAddress::test_an_address_carries_nothing_but_the_album`

---

**NFR-S-USE-001 The shops dialog can be read**

Priority: Must

Requirement: Every colour the shops dialog uses for text shall hold a contrast
ratio of at least 4.5 to 1 against the surface behind it, in both appearances,
measured by the WCAG relative luminance formula.

Rationale: The same requirement as NFR-USE-002, applied to the new screen so it
cannot be the one that quietly falls short.

Acceptance: Given either appearance, when each text colour is measured against
its surface, then every ratio reaches 4.5.

Verified by: `tests/ui/test_shop_contrast.py`

---

**NFR-S-MAIN-001 The layering and the gate hold**

Priority: Must

Requirement: The domain and application modules added by this specification
shall hold 100 percent branch coverage, shall import nothing from
infrastructure or UI, then shall each stay within the 400-line module cap.

Rationale: The house invariants, restated here because a new area is where they
get forgotten first.

Acceptance: Given the suite, when it runs, then the coverage gate passes and the
structural tests pass unchanged.

Verified by: the existing `tests/structural` suite plus the coverage gate.

---

### 3.3 External interfaces

**The browser.** One outbound call to the operating system's default handler
for an `https` address, through a port the application layer declares and the
infrastructure layer implements. Nothing waits for it and nothing reads
anything back.

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
  ]
}
```

- `shops` is the list in use; `shipped` records the list the file was written
  from, which is how FR-S16 tells a file nobody edited from one somebody did.
- `name` and `template` are required; a row missing either is skipped.
- `note` is optional and is shown beside the shop.
- Order in the file is the order in the dialog.
- Unknown keys are ignored, so a file written by a later Stellody is read by an
  earlier one.

**The shipped defaults**, every template measured on 2026-09-07 by loading it
and reading what came back, except where marked:

| Shop | Template | Measured |
|---|---|---|
| 7digital | `https://uk.7digital.com/search?q={artist}%20{album}&fallback=true` | Read from a browser on 2026-09-08, since the search refuses an automated visitor. The UK storefront, with the fallback it was seen carrying. See A-01. |
| Qobuz | `https://www.qobuz.com/gb-en/search?q={artist}%20{album}` | Exact album first hit. Lossless only. |
| Bandcamp | `https://bandcamp.com/search?q={artist}%20{album}&item_type=a` | Albums only. Independent catalogue, so majors are absent. |
| Boomkat | `https://boomkat.com/products?q[keywords]={artist}&q[format]=Download` | Digital filter verified. Artist alone, since two terms returned nothing. |
| Bleep | `https://bleep.com/search/query?q={artist}%20{album}` | Search reached and answered. |
| Presto Music | `https://www.prestomusic.com/search?search_query={artist}%20{album}` | Answered. Mixes physical, digital, books and sheet music. |
| ProStudioMasters | `https://www.prostudiomasters.com/search?q={artist}%20{album}` | Answered. Hi-res, with FLAC, MQA and DSD tabs on the page. |
| Beatport | `https://www.beatport.com/search?q={artist}%20{album}` | Exact release found. Electronic; rarely FLAC. |

Not shipped, with the reason: Juno Download has closed; Traxsource and eClassical could
not be read past their bot and consent walls; Volumo's search path answered 404.
HDtracks reached a search page whose results could not be confirmed and was then
ruled out by Oliver on 2026-09-08 rather than left pending. Any of them can be
added as a row.

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

Nothing marked open may be built from.

| # | Question | Owner |
|---|---|---|
| OQ-S01 | RESOLVED 2026-09-08. Oliver ruled HDtracks out; it does not join the shipped defaults. It stays addable as a row like any other shop, so the question does not reopen by itself. | Answered |
| OQ-S02 | RESOLVED 2026-09-13. A screen is wanted: Amendment 1 edits the list on the shops dialog. | Answered |
| OQ-S03 | Should an album already held be reachable at a shop too, for a better copy? Out of scope this time. | Oliver |

### B. Prioritisation

Must: FR-S01 to FR-S15, every NFR, then FR-S17 to FR-S42 from Amendment 1.
Should: nothing this stage.
Could: nothing this stage.
Won't, this time: payments, prices, stock, shop APIs, affiliate links, physical
media, streaming, remembering what was bought.

### C. The build order this implies

Inside out. No user-visible action waits on a screen to be exercisable.

1. **Domain**: the address rule. A shop as a value object, the placeholder
   substitution and the encoding, pure and unit tested.
2. **Application**: the use case that turns ticked albums plus a chosen shop
   into addresses, over two declared ports: where the shop list comes from and
   how an address is opened.
3. **Infrastructure**: the shop file reader and writer, plus the opener that
   hands an address to the operating system.
4. **UI**: the tick boxes, the two controls and the shops dialog, last.

The diagnostic that says the foundation is sound: building every address for a
set of ticked albums at a chosen shop must be executable from a test with no
screen and no browser, before the dialog exists.

## 6. Amendments

Numbered, each with its reason, as the baseline asks.

**Amendment 1, 2026-09-13: editing the shop list inside Stellody. Baselined
the same day on Oliver's word.** With it the out-of-scope bullet for an editor
screen is struck, OQ-S02 is resolved, FR-S16 is superseded by FR-S30 to FR-S36
and section 3.4 gains the `deleted` and `retired` keys described in 6.6.

### 6.1 Why

Reported by Oliver on 2026-09-13. A shop row broken by hand-editing
`shops.json` vanished from the list without a word (FR-S11 is built in part).
Two repairs were put to him: a message naming the broken row, which he judged
the wrong fix; leaving the silence, which he judged worse. What he chose is
removing the need to hand-edit at all: the list is changed from inside the
shops dialog, which refuses to save a broken shop in the first place. He wants
to add and remove shops.

**Rulings taken on 2026-09-13**, each his:

- Add, edit, delete and move sit on the shops dialog itself.
- Delete wears `assets/delete.png`, add wears `assets/add.png`, edit wears
  `assets/edit.png`, all three supplied by him. `negative.png` is NOT used: its
  standing rule in ARCHITECTURE.md is that it is only ever composed over another
  picture.
- Moving is a handle beside each shop, shaped like the grip Steam shows: a
  ribbed bar with an arrow above and below. It wears `assets/drag-up-down.png`,
  supplied by him.
- A row broken by hand-editing `shops.json` is shown greyed out with its reason,
  plus edit and delete, so it can be mended from the dialog (OQ-S04).
- Deleting asks first. A form can try a shop in the browser before saving it.
- When a new Stellody ships a changed shop list, new shops are added, shops he
  added are never touched and a shop he deleted never comes back.
- Every other choice below is a recommendation he accepted without seeing it
  written out, so reading this is the check on each.

### 6.2 Out of scope for this amendment

- Editing shops anywhere but the shops dialog: no menu entry, no Preferences
  page.
- Importing, exporting or sharing a shop list.
- A picture per shop.
- Checking automatically that a shop's search finds anything. Try opens the
  page; judging it is the listener's.
- Hand-editing `shops.json` stays possible; it is no longer the way the list is
  meant to change. What a hand-broken row does is OQ-S04.

### 6.3 Definitions added

| Term | Meaning here |
|---|---|
| Shipped shop | A shop whose name appears in the list this Stellody ships. Names are compared ignoring case. |
| Own shop | A shop the listener added, whose name no shipped list carries. |
| Edited | A shipped shop whose name, address or note differs from the recorded shipped copy of it. Moving a shop does not edit it. |
| Deleted record | The names of shipped shops the listener deleted, kept in the shop file. |
| Shop form | The small dialog Add and Edit open: Name, Search address, Note, Try, Save, Cancel. |

### 6.4 Functional requirements

---

**FR-S17 A shop can be added**

Priority: Must

Requirement: When the add control is pressed, the shops dialog shall open the
shop form with every field empty.

Acceptance: Given the shops dialog, when add is pressed, then the shop form
opens with an empty name, address and note.

Verified by: `tests/ui/test_shop_editing.py::test_add_opens_an_empty_form`

---

**FR-S18 A shop can be edited**

Priority: Must

Requirement: When a shop's edit control is pressed, the shops dialog shall open
the shop form holding that shop's name, address and note.

Acceptance: Given Qobuz listed, when its edit control is pressed, then the form
holds Qobuz's name, address and note.

Verified by: `tests/ui/test_shop_editing.py::test_edit_opens_the_form_holding_the_shop`

---

**FR-S19 Saving puts the shop in the list**

Priority: Must

Requirement: When Save is pressed on a shop form that passes FR-S20 and FR-S21,
the shop service shall write the list to the shop file with an added shop at the
bottom or an edited shop in its own place, then the shops dialog shall show the
list as written.

Acceptance: Given eight shops and a form holding "Juno" with a valid address,
when Save is pressed, then the file holds nine shops with Juno last and the
dialog lists nine.

Verified by: `tests/application/test_editing_the_shop_list.py::test_an_added_shop_goes_last`,
`tests/application/test_editing_the_shop_list.py::test_an_edited_shop_keeps_its_place`

---

**FR-S20 A broken shop cannot be saved**

Priority: Must

Requirement: If the name is empty, the address is empty, the address does not
begin with `https://` or the address names neither `{artist}` nor `{album}`,
then the shop form shall refuse to save and shall say which of those is wrong
beside the field it concerns.

Rationale: The fix for the report in 6.1. A shop that cannot search is stopped
at the one moment somebody is looking at it.

Acceptance: Given a form whose address is `https://example.com/search`, when
Save is pressed, then nothing is written and the address field says it names
neither placeholder.

Verified by: `tests/ui/test_shop_editing.py::test_a_shop_that_cannot_search_is_not_saved`

---

**FR-S21 Two shops cannot share a name**

Priority: Must

Requirement: If the name matches, ignoring case, the name of another shop in
the list, then the shop form shall refuse to save and shall say the name is
taken.

Rationale: A name is how a shipped shop is recognised across releases (6.3), so
two of one name would make FR-S30 to FR-S33 guess.

Acceptance: Given Qobuz listed, when a new shop named "qobuz" is saved, then
nothing is written and the name field says it is taken.

Verified by: `tests/domain/test_shop_list.py::TestTheForm::test_a_name_already_used_is_refused`

---

**FR-S22 A shop can be tried before it is saved**

Priority: Must

Requirement: When Try is pressed, the shop form shall open the address it
currently holds, for the first ticked album, in the default browser, without
saving anything.

Rationale: Ruled by Oliver on 2026-09-13: whether a shop works is judged by
looking at its page. The shops dialog is only reachable with at least one album
ticked (FR-S04), so there is always a first album to try.

Acceptance: Given "Kate Bush, Hounds of Love" ticked first and a form holding
`https://example.com/s?q={artist}`, when Try is pressed, then
`https://example.com/s?q=Kate%20Bush` is opened and the file is unchanged.

Verified by: `tests/ui/test_shop_editing.py::test_try_opens_the_first_ticked_album`

---

**FR-S23 A try that will not open says so**

Priority: Must

Requirement: If the operating system cannot open the address Try built, then
the shop form shall say so and shall stay open.

Acceptance: Given an opener that refuses, when Try is pressed, then the form
says the address could not be opened and remains open.

Verified by: `tests/ui/test_shop_editing.py::test_a_try_that_will_not_open_says_so`

---

**FR-S24 Deleting asks first**

Priority: Must

Requirement: When a shop's delete control is pressed, the shops dialog shall
ask for confirmation naming that shop, deleting it only when the answer is yes.

Acceptance: Given Beatport listed, when its delete control is pressed and the
answer is no, then Beatport is still listed; when the answer is yes, then it is
gone from the dialog and from the file.

Verified by: `tests/ui/test_shop_editing.py::test_delete_asks_naming_the_shop`,
`tests/ui/test_shop_editing.py::test_a_refused_delete_keeps_the_shop`

---

**FR-S25 A deleted shipped shop is remembered**

Priority: Must

Requirement: When a shipped shop is deleted, the shop service shall add its name
to the deleted record.

Rationale: Ruled by Oliver on 2026-09-13: an update must never bring back a shop
somebody removed.

Acceptance: Given Beatport deleted, when the file is read, then its deleted
record names Beatport.

Verified by: `tests/application/test_editing_the_shop_list.py::test_deleting_a_shipped_shop_records_it`

---

**FR-S26 Renaming a shipped shop is a delete plus an add**

Priority: Must

Requirement: When a shipped shop is saved under a different name, the shop
service shall add its original name to the deleted record.

Rationale: Without it the next release would find the original name missing and
add the shop back beside the renamed one.

Acceptance: Given Qobuz saved as "Qobuz UK", when the file is read, then the
list holds "Qobuz UK", no "Qobuz" and the deleted record names Qobuz.

Verified by: `tests/application/test_editing_the_shop_list.py::test_renaming_a_shipped_shop_records_the_old_name`

---

**FR-S27 A shop is moved by dragging its handle**

Priority: Must

Requirement: When a shop's handle is dragged to another place in the list, the
shop service shall write the list in the new order.

Acceptance: Given Beatport eighth, when its handle is dropped above 7digital,
then Beatport is first in the dialog and in the file.

Verified by: `tests/ui/test_shop_editing.py::test_dragging_the_handle_moves_the_shop`

---

**FR-S28 A shop is moved from the keyboard**

Priority: Must

Requirement: While one of a shop's controls holds focus, when Ctrl+Up or
Ctrl+Down is pressed, the shop service shall move that shop one place up or down
and write the list, focus staying on the control that held it.

Rationale: The house keyboard model: a control reachable only with a mouse is
half a control. A move past either end does nothing.

Acceptance: Given focus on Qobuz's button with Qobuz second, when Ctrl+Up is
pressed, then Qobuz is first and still holds focus; when Ctrl+Up is pressed
again, then nothing changes.

Verified by: `tests/ui/test_shop_editing.py::test_ctrl_arrows_move_the_focused_shop`

---

**FR-S29 A change that cannot be written is not shown as made**

Priority: Must

Requirement: If an add, edit, delete or move cannot be written to the shop file,
then the shops dialog shall say so and shall go on showing the list as it was.

Acceptance: Given a shop file that refuses writes, when a shop is deleted, then
the dialog says the change could not be saved and still lists that shop.

Verified by: `tests/ui/test_shop_editing.py::test_a_change_that_cannot_be_saved_is_not_shown`

---

**FR-S30 A new shipped shop is added**

Priority: Must

Requirement: When the shipped list holds a shop whose name is neither in the
list in use nor in the deleted record, the shop service shall add that shop at
the bottom of the list in use.

Acceptance: Given a file holding the eight shops and a release shipping a ninth,
"Juno", when the shops are read, then Juno is ninth.

Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_new_shipped_shop_is_added_last`

---

**FR-S31 A shop somebody deleted stays deleted**

Priority: Must

Requirement: If a shipped shop's name is in the deleted record, then the shop
service shall leave it out of the list in use whatever the shipped list says.

Acceptance: Given Beatport in the deleted record and a release still shipping
Beatport, when the shops are read, then Beatport is not listed.

Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_deleted_shop_never_returns`

---

**FR-S32 An untouched shipped shop follows the release**

Priority: Must

Requirement: When a release changes the address or the note of a shipped shop
that is not edited, the shop service shall take the new address and note,
keeping the shop in its place.

Acceptance: Given Qobuz untouched in second place and a release changing Qobuz's
address, when the shops are read, then Qobuz is second with the new address.

Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_untouched_shop_takes_the_new_address`

---

**FR-S33 An edited shipped shop keeps the edit**

Priority: Must

Requirement: If a shipped shop is edited, then the shop service shall keep the
listener's name, address and note whatever a release changes about that shop.

Acceptance: Given Qobuz with an edited note and a release changing Qobuz's
address, when the shops are read, then Qobuz keeps the listener's address and
note.

Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_an_edited_shop_keeps_the_edit`

---

**FR-S34 A shop a release drops is removed where untouched**

Priority: Must

Requirement: When a release no longer ships a shop the recorded shipped list
held, the shop service shall remove that shop from the list in use where it is
not edited and shall name it in the retired record; an edited one stays.

Rationale: The usual reason a shop leaves the shipped list is that it closed,
which is what happened to Juno Download on 2026-09-07.

Acceptance: Given Bleep untouched and a release that no longer ships Bleep, when
the shops are read, then Bleep is not listed and the retired record names it.

Verified by: `tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_untouched_shop_is_removed`,
`tests/domain/test_shop_list.py::TestMeetingARelease::test_a_dropped_edited_shop_stays`

---

**FR-S35 A removed shop is announced once**

Priority: Must

Requirement: When the shops dialog opens while the retired record names shops,
the shops dialog shall say which shops were removed because Stellody no longer
ships them, then the shop service shall empty the retired record.

Acceptance: Given the retired record naming Bleep, when the shops dialog opens,
then it says Bleep was removed; when it is closed and opened again, then it says
nothing about Bleep.

Verified by: `tests/ui/test_shop_editing.py::test_a_removed_shop_is_announced_once`

---

**FR-S36 A file from before this amendment gains nothing by surprise**

Priority: Must

Requirement: If the shop file records no deleted record, then the shop service
shall write an empty one without adding any shipped shop the list lacks.

Rationale: Before this amendment a shop could only be removed by hand-editing
the file, which left no record. A shipped shop missing from such a file may
have been removed on purpose, so it is not put back.

Acceptance: Given a file without a deleted record whose list lacks Beatport,
when the shops are read, then Beatport is still absent and the file holds an
empty deleted record.

Verified by: `tests/infrastructure/test_shop_file.py::TestMeetingARelease::test_an_older_file_is_not_added_to`

---

**FR-S37 The original shops can be put back**

Priority: Must

Requirement: When the put-back control is pressed and confirmed, the shop
service shall write the shipped shops in shipped order with their shipped
values, followed by the listener's own shops in their current order; the same
write empties the deleted record.

Rationale: The way back from any amount of editing, which keeps what the
listener added rather than taking that too.

Acceptance: Given Beatport deleted, Qobuz edited and an own shop "Juno" added,
when put back is confirmed, then the eight shipped shops are listed as shipped
with Juno ninth and the deleted record is empty.

Verified by: `tests/domain/test_shop_list.py::TestTheWayBack::test_putting_back_keeps_own_shops`

---

**FR-S38 Putting back asks first**

Priority: Must

Requirement: When the put-back control is pressed, the shops dialog shall ask
for confirmation, changing nothing unless the answer is yes.

Acceptance: Given an edited list, when put back is pressed and the answer is no,
then the list and the file are unchanged.

Verified by: `tests/ui/test_shop_editing.py::test_putting_back_asks_first`

---

**FR-S39 An empty list still offers Add**

Priority: Must

Requirement: While the list holds no shops, the shops dialog shall show the add
control and a line saying there are no shops yet.

Rationale: Today that line tells somebody to edit `shops.json` by hand, which is
the thing this amendment exists to end.

Acceptance: Given every shop deleted, when the dialog is read, then it shows the
add control and does not mention `shops.json`.

Verified by: `tests/ui/test_shop_editing.py::test_an_empty_list_offers_add`

---

**FR-S40 Every new control is on the keyboard ring**

Priority: Must

Requirement: The shops dialog shall place each shop's button, edit control and
delete control, the add control and the put-back control in the keyboard ring in
reading order. The handle shall not be a stop.

Rationale: The handle is a mouse affordance whose keyboard equivalent is
FR-S28, so a stop on it would be a press that does nothing.

Acceptance: Given two shops listed, when Tab is pressed repeatedly, then focus
reaches the first shop's button, edit and delete, then the second's, then add,
then put back, then Close.

Verified by: `tests/ui/test_shop_editing.py::test_the_ring_walks_the_rows_in_reading_order`

---

**FR-S41 The guide explains the new pictures**

Priority: Must

Requirement: The guide shall show `add.png`, `edit.png`, `delete.png` and
`drag-up-down.png` beside what each does.

Rationale: `tests/ui/test_guide.py` already fails on a picture the interface
names that the guide does not draw, so this is stated rather than discovered.

Verified by: `tests/ui/test_guide.py::TestWhatItNames` (existing)

---

**FR-S42 A hand-broken row can be mended from the dialog**

Priority: Must

Requirement: If a row in the shop file cannot be read as a shop, then the shops
dialog shall list it greyed out with the reason it cannot be used, offering its
edit and delete controls and no way to search it.

Rationale: Ruled by Oliver on 2026-09-13 (OQ-S04). It completes FR-S11: the row
is still never searched, while it is no longer skipped without a word. Edit
opens the shop form holding whatever the row carried, so FR-S20 decides whether
the mended row saves.

Acceptance: Given a file holding a row named "Juno" whose address names no
placeholder, when the dialog opens, then Juno is listed greyed out saying its
address names neither placeholder; its edit control opens the form holding that
address; its delete control removes the row after asking.

Verified by: `tests/ui/test_shop_editing.py::test_a_broken_row_is_listed_greyed_with_its_reason`,
`tests/infrastructure/test_shop_file.py::TestWhatIsRefused::test_a_broken_row_is_read_with_its_reason`

---

### 6.5 Non-functional

NFR-S-USE-001 and NFR-S-MAIN-001 apply to everything added here, unchanged. The
merge rules FR-S30 to FR-S34 and FR-S37 sit in the domain as one pure function
over the list in use, the recorded shipped list, the current shipped list and
the deleted record, so they fall under the 100 percent branch gate.

### 6.6 Data

`shops.json` gains two keys beside `shops` and `shipped`:

```json
{
  "deleted": ["Beatport"],
  "retired": ["Bleep"]
}
```

- `deleted` names shipped shops the listener removed (FR-S25, FR-S26).
- `retired` names shops removed because a release stopped shipping them, until
  the dialog has said so (FR-S34, FR-S35).
- An older Stellody ignores both, since unknown keys are already ignored.
- FR-S12's "does not hold a usable list" now means a file that cannot be parsed
  or whose `shops` is not a list. A list whose rows are broken is read with
  each row kept and named (FR-S42); an empty list stays empty (FR-S39).

### 6.7 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-04 | RESOLVED 2026-09-13. Oliver supplied `assets/drag-up-down.png` for the handle, so it is artwork rather than drawn in code. | Oliver | Answered |
| A-05 | Dragging a row within the shops dialog is feasible in PySide6 at the dialog's current shape. Nothing in Stellody drags today (searched on 2026-09-13), so it is proved by a probe before FR-S27 is built rather than assumed. PARTLY ANSWERED 2026-09-13: the drop is measured offscreen by `tests/ui/test_shop_editing.py::test_dragging_the_handle_moves_the_shop`; how a drag feels with a real mouse is still to be checked by hand. | Oliver | First run of the build |

### 6.8 Open questions

| # | Question | Recommendation | Owner |
|---|---|---|---|
| OQ-S04 | RESOLVED 2026-09-13. A row broken by hand-editing `shops.json` is listed greyed out with its reason, plus edit and delete; now FR-S42. | Yes | Answered |

### 6.9 Build order

1. **Domain**: the shop list rules. Name matching, the edited test, the merge of
   FR-S30 to FR-S34, putting back, moving; pure and unit tested.
2. **Application**: add, edit, delete, move, put back and try, as one use case
   each over the existing ports plus a writing port.
3. **Infrastructure**: the shop file reading and writing `deleted` and
   `retired`, retiring FR-S16's logic.
4. **UI**: the row controls, the handle, the shop form, the put-back control,
   the guide entries, last.

Every action above must be drivable from a test with no screen before the
dialog changes.
