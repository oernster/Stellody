# Reaching the shops that sell what the library is missing

Specification for the second stage of PLAN.md milestone 2. The first stage says
what the library is missing; this says how somebody gets from one of those gaps
to a place that sells it. It is written before the code, in the house form:
EARS requirements, each with the failure case beside it, each naming the test
that will prove it.

Baseline: 1.0, 2026-09-08. Changes after this arrive as numbered amendments
with a reason rather than as silent edits.

## 1. Introduction

### 1.1 Purpose

A discovery run ends with a list of albums the library does not hold. Today
that list is somewhere to look at rather than somewhere to act, so buying one of
them means retyping an artist and a title into a shop by hand. This closes that
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
- An editor screen for the shop list. The file is edited in a text editor for
  now; see OQ-S02.

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
- `PLAN.md` milestone 2, stage two, which recorded the intent and the network
  stance.
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
| A-03 | Every shipped template still works on the day it ships. Measured 2026-09-07; they rot without notice, which is what FR-S09 exists for. | Oliver | Each release |

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

Verified by: `tests/infrastructure/test_shop_file.py::test_a_missing_file_is_written_with_the_defaults`

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

Verified by: `tests/domain/test_shop_address.py::test_both_placeholders_are_filled_and_encoded`

---

**FR-S11 A template that names neither is refused**

Priority: Must

Requirement: If a shop's template holds neither `{artist}` nor `{album}`, then
the shop service shall leave that shop out of the list and shall say which row
was refused.

Rationale: The unwanted sibling of FR-S10. A template with no placeholder opens
the same page whatever is ticked, which looks like a broken search rather than
a mistyped row.

Acceptance: Given a shop file holding a row whose template has no placeholder,
when the list is read, then that shop is absent and the reason names it.

Verified by: `tests/infrastructure/test_shop_file.py::test_a_template_with_no_placeholder_is_refused`

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

Verified by: `tests/infrastructure/test_shop_file.py::test_an_unreadable_file_falls_back_and_is_left_alone`

---

**FR-S13 A browser that will not open says so**

Priority: Must

Requirement: If the operating system cannot open an address, then the shops
dialog shall say so against that shop and shall leave the dialog open.

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

Requirement: The shop file shall record the shipped list it was written from
alongside the list in use. Where the two are identical and the shipped list has
since changed, the shop service shall replace both with the current shipped
list. Where the file records no shipped list and its list is identical to the
current shipped list, the shop service shall write the record, leaving the list
itself unchanged. In every other case the file shall be left exactly as it is.

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

Verified by: `tests/infrastructure/test_shop_file.py::TestRefreshingAnUntouchedFile`

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

Verified by: `tests/domain/test_shop_address.py::test_an_address_carries_nothing_but_the_album`

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
      "note": "Lossless downloads only, so no format filter is needed."
    }
  ]
}
```

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
not be read past their bot and consent walls; Volumo's search path answered 404;
HDtracks reached a search page whose results could not be confirmed. Any of them
can be added as a row.

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
| OQ-S01 | Does HDtracks return usable results for an artist and an album, so it can join the defaults? Its hash route needs a human to confirm. | Oliver |
| OQ-S02 | Is a screen for editing the shop list wanted? Is the file enough? | Oliver |
| OQ-S03 | Should an album already held be reachable at a shop too, for a better copy? Out of scope this time. | Oliver |

### B. Prioritisation

Must: FR-S01 to FR-S16 and every NFR.
Should: nothing this stage.
Could: OQ-S02's editor screen.
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
