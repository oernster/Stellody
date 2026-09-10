# Formats proved by a fixture rather than by a file somebody owns

Specification for widening what Stellody decodes, written before the code in
the house form: EARS requirements, each with its failure case beside it, each
naming the test that will prove it.

Baseline: this specification as first written, 2026-09-09. Changes after that
arrive as numbered amendments with a reason rather than as silent edits.

## 1. Introduction

### 1.1 Purpose

Stellody decodes nine suffixes and names nine more it can see but not play.
Three of those nine turn out to need no new decoder at all: the FFmpeg build
already shipped inside PyAV decodes them, mutagen already reads their tags and
the existing packet reader already addresses them by frame. What kept them out
was a rule about evidence rather than a gap in capability.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 The rule this amends, stated first

`walker.py` gives the reason `.m4b` sits among the unplayable suffixes:

> M4B is an audiobook in the same container M4A uses. It is left here rather
> than moved across with M4A because no file of that kind was measured; a
> format is claimed to work only where it has been seen to.

**That standard is amended by this document, on Oliver's ruling of
2026-09-09.** A format may now be claimed where a test PROVES the whole path:
a fixture encoded at test time, walked, probed, assembled, then decoded back.
The old standard required a real file somebody owned, which is why five
formats sat unplayable in a library holding none of them.

**What the new standard is weaker at, said plainly rather than discovered
later.** A generated fixture proves the pipeline handles what FFmpeg writes.
It does not prove the pipeline handles what Windows Media Player, dBpoweramp
or a hardware ripper writes; tags are exactly where those differ. So
"supported" here means the format decodes and its tags are read, proved by
test. It does not mean verified against files in the wild. NFR-F-HONEST-001
requires the README to say so.

### 1.4 Scope

**In scope:** three suffixes, `.wma`, `.wv` and `.aac`; their tag reading; the
bit-depth honesty rule extended to cover them; fixtures generated in the suite.

**Out of scope, so that it is not re-proposed:**

- **Monkey's Audio, Musepack, DSD and TAK.** Measured 2026-09-09: the bundled
  FFmpeg decodes all four and mutagen reads tags for all four; it can encode
  none of them, so no fixture can be generated and the new standard cannot be
  met. They stay named among the unplayable suffixes, where they are reported
  rather than silently absent. Each reopens the day a fixture can be made for
  it or a real file is measured.
- **CAF.** Excluded for a different reason that still holds: libsndfile decodes
  it while mutagen reads nothing out of it, so it would scan into an album with
  no title.
- **`.m4b`, the MPEG-4 audiobook.** Ruled out by Oliver on 2026-09-09 on kind
  rather than on capability: it is the cheapest of all the candidates, being
  the same container, codec and tag table as `.m4a`; it was measured
  working. An audiobook is not music; a chaptered one arrives as a single
  enormous track and would read as an album nobody made. It stays reported.
- **`.tta`, TrueAudio.** Measured working; mutagen states no channel count
  for it at all, so the probe would have to invent one. Cut on 2026-09-09 for
  that plus rarity.
- **Writing any of these formats.** Stellody reads music files and never writes
  them, which invariants 1 and 2 enforce. The fixtures are written into a
  temporary directory by the SUITE, never by the application.
- **Any new dependency.** Everything here is already installed and already
  shipped.

### 1.5 Definitions

| Term | Meaning here |
|---|---|
| Fixture | An audio file the suite encodes for itself at test time, never committed. |
| Stated depth | The bits per sample a file declares. Nought means it declares none. |
| Taken suffix | A file extension the walk accepts as a track. |
| Reported suffix | A file extension the walk names as present and unplayable. |

### 1.6 References

- `ARCHITECTURE.md`, whose invariants govern every requirement here and whose
  "Formats and probing" section states the three tag shapes this adds to.
- `DISCOVERY.md` and `SHOPS.md`, the two specifications this follows in form.

## 2. Overall description

### 2.1 Product perspective

An addition to the walk, the probe and the decoder chooser. No new module
reaches the network, so invariant 12's list of four is untouched. No new
dependency, so the packaged build does not grow.

### 2.2 The one user class

A listener with a mixed library, running Stellody on their own machine.

### 2.3 Operating environment

Windows, Linux and macOS, as the application already ships. The FFmpeg build
inside PyAV supplies every decoder named here.

### 2.4 Constraints

- **C-F01** No new dependency and no growth in the packaged build.
- **C-F02** No music file is ever written, fixtures excepted, which the suite
  writes to a temporary directory of its own.
- **C-F03** A format is claimed only where a test proves the whole path.
- **C-F04** Domain and application hold 100% branch coverage; modules stay at
  or below 400 lines.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-F01 | MEASURED 2026-09-09. The bundled FFmpeg decodes wmav1, wmav2, wmapro, wmalossless, wavpack and aac; it encodes wmav2, wavpack and aac. | Answered |
| A-F02 | MEASURED 2026-09-09. mutagen reads ASF, WavPack and AAC tags; a WMA fixture reports no stated depth, a WavPack fixture written as `s16p` reports 16. | Answered |
| A-F03 | A listener with WMA files wants them in the library rather than reported. Nobody has been asked; the alternative is the current behaviour, which is to report them. | Oliver | before release |

## 3. Requirements

### 3.1 Functional

---

**FR-F01 The three suffixes are taken**

Priority: Must

Requirement: The walker shall take `.wma`, `.wv` and `.aac` as audio rather
than naming them among the suffixes it reports as unplayable.

Rationale: They are decodable, taggable and now provable. A suffix in both
tables would be a file that is scanned and reported as missing at once.

Acceptance: Given a folder holding one file of each of the three, when the
walk lists it, then all three are taken as tracks and none appears in the
unplayable report.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_widened_suffixes_are_taken`

---

**FR-F02 Each is decoded through the reader that already addresses packets**

Priority: Must

Requirement: When a source with one of the three suffixes is opened, the
decoder chooser shall return the packet reader, which counts packet timestamps
back into frame positions.

Rationale: The same answer M4A already gets, for the same reason: none of the
three is addressable by frame the way libsndfile addresses a WAV, so a cue
slice, the equalizer, the visualiser and gapless all depend on that counting.

Acceptance: Given a fixture of each of the three, when a source is opened for
it, then a packet reader is returned and reading it back yields the frames
that were encoded.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_each_widened_format_decodes_through_the_packet_reader`

---

**FR-F03 A file that will not decode is reported, never left as silence**

Priority: Must

Requirement: If a file carrying one of the three suffixes cannot be decoded,
then the transport shall raise the domain's playback error, which the window
already catches in one place to say what happened and give the device back.

Rationale: The unwanted sibling of FR-F02; also the rule the application
already holds: a listener cannot tell a silent failure from a press that
missed. A suffix taken on the strength of a fixture will meet files in the
wild that the fixture did not represent, so this is the ordinary case here
rather than the edge one.

Acceptance: Given a file named `.wma` whose content is not WMA at all, when it
is played, then a playback error is raised naming the file and the window
reports it.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_widened_suffix_that_will_not_decode_says_so`

---

**FR-F04 Tags are read for each family**

Priority: Must

Requirement: When a file with one of the three suffixes is probed, the probe
shall read its album artist, title, date, genre, disc number and track number
where the file states them, translating each family's own vocabulary into the
one the resolution rules read.

Rationale: The third tag shape cost this project a scan that could not
assemble; ASF is a fourth. A format that decodes but whose tags are not
translated scans into an album with no title, which is the reason CAF is
excluded rather than supported.

Acceptance: Given a WMA fixture whose ASF tags state an album, an artist and a
track number, when it is probed, then those three arrive under the domain's own
names.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_asf_tags_arrive_under_the_domain_names`

---

**FR-F05 A file whose tags cannot be read still scans**

Priority: Must

Requirement: If a file carrying one of the three suffixes states no readable
tags, then the probe shall report the values as absent rather than raising,
leaving the folder to assemble into an album as it otherwise would.

Rationale: The unwanted sibling of FR-F04. A fixture states clean tags; a file
from a real ripper may state none; the failure mode to avoid is the one
already on record, where one file put rows in the store that the loader then
choked on, so every later start failed too.

Acceptance: Given a WavPack fixture carrying no tags at all, when the folder is
scanned, then it assembles and the missing values read as absent.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_an_untagged_widened_file_still_assembles`

---

**FR-F06 A lossy source states no depth and is never bit perfect**

Priority: Must

Requirement: The probe shall report a stated depth of nought for WMA and for
AAC, which is what makes `is_bit_perfect` false for a source of either format
in every output mode.

Rationale: **The requirement this whole change turns on.** A lossy MP4 already
states sixteen bits per sample because its container carries that number
whatever the codec does; passing it through would have badged an AAC track
as delivered untouched. WMA is the same shape. The promise the README leads
with is held by reporting rather than by hoping, so a new lossy format is
exactly where that promise is at risk.

Acceptance: Given a WMA fixture and an AAC fixture, when each is probed, then
the stated depth is nought; when an output request is built for either in
exclusive mode, then it is refused with the reason naming the file rather than
the device, with `is_bit_perfect` false.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_lossy_widened_format_states_no_depth`, `tests/domain/test_output_request.py::test_a_widened_lossy_source_is_never_bit_perfect`

---

**FR-F07 A lossless source keeps the depth it states**

Priority: Must

Requirement: The probe shall report the bits per sample a WavPack file states
rather than reducing it to nought.

Rationale: The other half of FR-F06; it is the half a guard written only
against lossy formats would break. WavPack is lossless and states a real depth, so
suppressing it would deny a bit-perfect stream to a file that has earned one.

Acceptance: Given a WavPack fixture encoded at sixteen bits, when it is probed,
then the stated depth is sixteen; given one encoded at thirty two, then it is
thirty two.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_wavpack_keeps_the_depth_it_states`

---

**FR-F08 What remains unplayable is still named**

Priority: Must

Requirement: The walker shall continue to name `.ape`, `.mpc`, `.dsf`, `.dff`,
`.tta`, `.m4b`, `.caf` and the AAC-in-MP4 cases it already names, so a folder
holding only those raises one finding naming how many files and which formats.

Rationale: The behaviour that exists because somebody went looking for an album
they owned and found nothing at all. Widening the taken set must not narrow the
reported one.

Acceptance: Given a folder holding one Monkey's Audio file, when it is scanned,
then one finding names it and no album is silently absent.

Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_formats_left_out_are_still_reported`

---

### 3.2 Non-functional

---

**NFR-F-TEST-001 Every fixture is generated, never committed**

Priority: Must

Requirement: The suite shall encode each fixture into a temporary directory at
test time, so the repository holds no audio file of any of the three formats.

Rationale: The whole basis of the amended rule. A committed binary is also a
licence question and a repository that grows with every format.

Verification: a structural test asserting no `.wma`, `.wv` or `.aac` file is
tracked, plus the fixtures being built by a helper the tests call.

---

**NFR-F-TEST-002 A fixture states its sample format**

Priority: Must

Requirement: Every fixture shall state the sample format it is encoded at
rather than letting the encoder choose.

Rationale: Measured 2026-09-09, which is why it is a requirement rather than
a note. The WavPack encoder accepts `u8p`, `s16p`, `s32p` and `fltp`,
defaulting to the FIRST of them, so a fixture written without stating one is
eight bit. It then reports a stated depth of 8 and the test proves the wrong
thing while passing. A fixture that lies is worse than no fixture.

Verification: the WavPack cases of FR-F07, which assert 16 and 32 against
fixtures stating `s16p` and `s32p`.

---

**NFR-F-HONEST-001 The README says what supported means here**

Priority: Must

Requirement: The README shall state that these three formats are proved by
generated fixtures rather than verified against files in the wild, naming also
the formats that remain reported rather than played.

Rationale: The README honesty rule, applied to the weaker evidence standard
this document adopts. A reader assuming "supported" means "tested against my
files" would be assuming something nobody has checked.

Verification: inspection, plus the existing structural sweep for version data
and prose rules.

---

**NFR-F-MAINT-001 The layering and the gate hold**

Priority: Must

Requirement: Every module this change touches shall stay at or below 400 lines,
shall land at 350 or below where it enters the 381 to 399 band, with the domain
and application layers holding 100% branch coverage.

Verification: `.\gate.ps1`, read by exit code.

---

### 3.3 Data

No new file and no new store. Two frozen sets in `walker.py` change membership;
one names three more suffixes and the other names three fewer.

## 4. Prioritisation

Must: FR-F01 to FR-F08 and every NFR.
Should: nothing this stage.
Could: nothing this stage.

Won't, this time, recorded so it is not re-proposed: Monkey's Audio, Musepack,
DSD, TAK, CAF, `.m4b` and `.tta`, each for the reason given in section 1.4.

## 5. Open questions

None. OQ-F01 asked whether a listener holding WMA files wants them in the
library rather than reported, since taking them changes what such a library
looks like without that person being asked. Ruled by Oliver on 2026-09-10:
they belong in the library, which is the behaviour that shipped.

The ruling was made without certainty and is recorded that way, because a
decision stated more confidently than it was made is the kind that gets
quietly reversed later by whoever reads it. Nobody here holds a WMA library,
so nobody here can settle it; what would settle it is somebody who does saying
how theirs reads. Until then the answer stands and the cost of being wrong is
known: a listener who wanted those files reported instead sees albums appear
that used to be named in the health report, which is visible rather than
silent and is the milder of the two directions to be wrong in.

## 6. The build order this implies

Inside out, as every feature here is built.

1. **Domain**: the depth rules, FR-F06 and FR-F07, as pure functions over a
   stated depth. Testable with no file present.
2. **Infrastructure, probe**: the ASF names table and whatever WavPack and AAC
   need, proved against generated fixtures.
3. **Infrastructure, walker and decoder chooser**: the two suffix sets and the
   routing, which is the smallest part.
4. **Documents**: the README non-claim, then `ARCHITECTURE.md`'s formats
   section gaining the fourth tag shape.

The diagnostic that says the foundation is sound: a fixture of each format must
be walked, probed, assembled into an album and decoded back from a test, before
anything about the interface is touched. Nothing here has an interface of its
own.
