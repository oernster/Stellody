# Formats proved by a fixture rather than by a file somebody owns

Specification for the formats Stellody decodes on the strength of a generated
fixture, in the house form: EARS
requirements, each with its failure case beside it, each naming the test that
proves it. Every requirement states the rule as it stands today.

## 1. Introduction

### 1.1 Purpose

Three audio suffixes, `.wma`, `.wv` and `.aac`, need no new decoder: the FFmpeg
build shipped inside PyAV decodes them, mutagen reads what each carries and the
existing packet reader addresses them by frame. Each is claimed on the
evidence standard of section 1.3.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 The evidence standard

A format may be claimed where a test PROVES the whole path: a fixture encoded at
test time, walked, probed, assembled, then decoded back (Oliver's ruling).

**What this standard is weaker at.** A generated fixture proves the pipeline
handles what FFmpeg writes. It does not prove the pipeline handles what Windows
Media Player, dBpoweramp or a hardware ripper writes; tags are exactly where
those differ. So "supported" here means the format decodes and its tags are
read, proved by test. It does not mean verified against files in the wild.
NFR-F-HONEST-001 requires the README to say so.

### 1.4 Scope

**In scope:** three suffixes, `.wma`, `.wv` and `.aac`; their tag reading; the
bit-depth honesty rule extended to cover them; fixtures generated in the suite.

**Out of scope, so that it is not re-proposed:**

- **Monkey's Audio, Musepack, DSD and TAK.** The bundled FFmpeg decodes all
  four and mutagen reads their tags; it can encode none of them, so no fixture
  can be generated and the standard cannot be met. They are reported rather
  than silently absent (FR-F08). Each reopens the day a fixture can be made for
  it or a real file is measured.
- **CAF.** libsndfile decodes it while mutagen reads nothing out of it, so it
  would scan into an album with no title.
- **`.m4b`, the MPEG-4 audiobook** (Oliver's ruling). It would work, being the
  same container, codec and tag table as `.m4a`; it is ruled out on kind. An
  audiobook is not music; a chaptered one arrives as a single enormous track
  and would read as an album nobody made.
- **`.tta`, TrueAudio.** It decodes; mutagen states no channel count for it, so
  the probe would have to invent one. Cut for that plus rarity.
- **Writing any of these formats.** Stellody reads music files and never writes
  them, which invariants 1 and 2 enforce. The fixtures are written into a
  temporary directory by the SUITE, never by the application.
- **Any new dependency.** Everything here is already installed and shipped.

### 1.5 Definitions

| Term | Meaning here |
|---|---|
| Fixture | An audio file the suite encodes for itself at test time, never committed. |
| Stated depth | The bits per sample a file declares. Nought means it declares none. |
| Taken suffix | A file extension the walk accepts as a track. |
| Reported suffix | A file extension the walk names as present and unplayable. |

### 1.6 References

- `ARCHITECTURE.md`, whose invariants govern every requirement here and whose
  "Formats and probing" section states the five tag shapes the probe reads.
- `DISCOVERY.md` and `SHOPS.md`, the two specifications this follows in form.

## 2. Overall description

### 2.1 Product perspective

Held by the walk, the probe and the decoder chooser. No module here reaches the
network, so invariant 12's list of four holds. No dependency is added, so the
packaged build does not grow.

### 2.2 The one user class

A listener with a mixed library, running Stellody on their own machine.

### 2.3 Operating environment

Windows, macOS and Linux, as the application already ships. The FFmpeg build
inside PyAV supplies every decoder named here.

### 2.4 Constraints

- **C-F01** No new dependency and no growth in the packaged build.
- **C-F02** No music file is ever written, fixtures excepted, which the suite
  writes to a temporary directory of its own.
- **C-F03** A format is claimed only where a test proves the whole path.
- **C-F04** Domain and application hold 100% branch coverage; modules stay
  within the line cap and out of the danger band named in
  `tests/structural/test_loc.py`.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-F01 | MEASURED. The bundled FFmpeg decodes wmav1, wmav2, wmapro, wmalossless, wavpack and aac; of those it encodes wmav1, wmav2, wavpack and aac, not wmapro or wmalossless. | | Answered |
| A-F02 | MEASURED. mutagen reads ASF and WavPack tags. It opens a raw AAC stream but reads no tags from it, since its AAC class does not support tagging. It states no bits per sample for WMA or raw AAC; a WavPack fixture written as `s16p` reports 16. | | Answered |
| A-F03 | A listener with WMA files wants them in the library rather than reported (Oliver's ruling, made without certainty; section 5). | | Answered |

## 3. Requirements

Every requirement below is a Must unless it carries a Priority line;
section 4 lists them.

### 3.1 Functional

**FR-F01 The three suffixes are taken**
- Requirement: The walker shall take `.wma`, `.wv` and `.aac` as audio rather
  than naming them among the suffixes it reports as unplayable.
- Rationale: They are decodable, taggable and provable. A suffix in both tables
  would be a file that is scanned and reported as missing at once.
- Acceptance: Given a folder holding one file of each of the three, when the
  walk lists it, then all three are taken as tracks and none appears in the
  unplayable report.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_widened_suffixes_are_taken`

**FR-F02 Each is decoded through the reader that already addresses packets**
- Requirement: When a source with one of the three suffixes is opened, the
  decoder chooser shall return the packet reader, which counts packet timestamps
  back into frame positions.
- Rationale: The same answer M4A gets, for the same reason: none of the three is
  addressable by frame the way libsndfile addresses a WAV, so a cue slice, the
  equalizer, the visualiser and gapless all depend on that counting.
- Acceptance: Given a fixture of each of the three, when a source is opened for
  it, then a packet reader is returned and reading it back yields the frames
  that were encoded.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_each_widened_format_decodes_through_the_packet_reader`

**FR-F03 A file that will not decode is reported, never left as silence**
- Requirement: If a file carrying one of the three suffixes cannot be decoded,
  then the transport shall raise the domain's playback error, which the window
  catches in one place to say what happened and give the device back.
- Rationale: The unwanted sibling of FR-F02. A listener cannot tell a silent
  failure from a press that missed. A suffix taken on the strength of a fixture
  will meet files in the wild the fixture did not represent, so this is the
  ordinary case here rather than the edge one.
- Acceptance: Given a file named `.wma` whose content is not WMA at all, when it
  is played, then a playback error is raised naming the file and the window
  reports it.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_widened_suffix_that_will_not_decode_says_so`, `tests/ui/test_saying_a_track_will_not_open.py`

**FR-F04 Tags are read for each family**
- Requirement: When a file with one of the three suffixes is probed, the probe
  shall read its album artist, title, date, genre, disc number and track number
  where the file states them, translating each family's own vocabulary into the
  one the resolution rules read. ASF (WMA) is the fourth tag shape the probe
  reads; APEv2 (WavPack), which iterates as keys rather than pairs, is the fifth.
  A raw AAC is an ADTS stream with no tag block, so it states no tags whatever
  wrote it.
- Rationale: A format that decodes but whose tags are not translated scans into
  an album with no title, which is the reason CAF is excluded rather than
  supported.
- Acceptance: Given a WMA fixture whose ASF tags state an album, an artist and a
  track number, when it is probed, then those three arrive under the domain's own
  names.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_asf_tags_arrive_under_the_domain_names`

**FR-F05 A file whose tags cannot be read still scans**
- Requirement: If a file carrying one of the three suffixes states no readable
  tags, then the probe shall report the values as absent rather than raising,
  leaving the folder to assemble into an album as it otherwise would.
- Rationale: The unwanted sibling of FR-F04. A file from a real ripper may state
  no tags; one file must never put rows in the store that the loader then chokes
  on, which would fail every later start too.
- Acceptance: Given a WavPack fixture carrying no tags at all, when the folder is
  scanned, then no file is reported unreadable, the folder assembles into an album
  of one track and that track still carries a title.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_an_untagged_widened_file_still_assembles`

**FR-F06 A lossy source states no depth and is never bit perfect**
- Requirement: The probe shall report a stated depth of nought for WMA and for
  AAC, which is what makes `is_bit_perfect` false for a source of either format
  in every output mode. `stellody/domain/formats.py` names both among
  `LOSSY_FAMILIES` on what the codec does, so a tag library that starts
  reporting a header depth for either changes nothing.
- Rationale: **The requirement this whole change turns on.** A lossy MP4 states
  sixteen bits per sample because its container carries that number whatever the
  codec does; passing it through would badge an AAC track as delivered untouched.
  The promise the README leads with is held by reporting rather than by hoping, so
  a new lossy format is exactly where that promise is at risk.
- Acceptance: Given a WMA fixture and an AAC fixture, when each is probed, then
  the stated depth is nought; when an output request is built for either in
  exclusive mode, then it is refused with the reason naming the file rather than
  the device, with `is_bit_perfect` false.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_lossy_widened_format_states_no_depth`, `tests/domain/test_output_request.py::test_a_widened_lossy_source_is_never_bit_perfect`, `tests/infrastructure/test_exclusive_refusal.py::test_a_lossy_source_is_refused_exclusive_for_the_file`

**FR-F07 A lossless source keeps the depth it states**
- Requirement: The probe shall report the bits per sample a WavPack file states
  rather than reducing it to nought.
- Rationale: The other half of FR-F06; it is the half a guard written only
  against lossy formats would break. WavPack is lossless and states a real depth,
  so suppressing it would deny a bit-perfect stream to a file that has earned
  one.
- Acceptance: Given a WavPack fixture encoded at sixteen bits, when it is probed,
  then the stated depth is sixteen; given one encoded at thirty two, then it is
  thirty two.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_wavpack_keeps_the_depth_it_states`

**FR-F08 What remains unplayable is still named**
- Requirement: The walker shall name `.ape`, `.mpc`, `.dsf`, `.dff`, `.tta`,
  `.tak`, `.m4b` and `.caf` as unplayable, so a folder holding only those raises
  one finding naming how many files and which formats. An AAC inside an MP4 is an
  `.m4a` and plays, so no such case is named.
- Rationale: Somebody went looking for an album they owned and found nothing at
  all. Widening the taken set must not narrow the reported one.
- Acceptance: Given a folder holding one Monkey's Audio file, when it is scanned,
  then one finding names it and no album is silently absent.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_formats_left_out_are_still_reported`

### 3.2 Non-functional

**NFR-F-TEST-001 Every fixture is generated, never committed**
- Requirement: The suite shall encode each fixture into a temporary directory at
  test time, so the repository holds no audio file of any of the three formats.
- Rationale: The whole basis of the evidence standard. A committed binary is also
  a licence question and a repository that grows with every format.
- Verification: `tests/structural/test_no_committed_audio.py`, which scans the
  working tree for any `.wma`, `.wv` or `.aac` file (so it also catches a fixture
  nobody has staged), plus the fixtures being built by a helper the tests call.

**NFR-F-TEST-002 A fixture states its sample format**
- Requirement: Every fixture shall state the sample format it is encoded at
  rather than letting the encoder choose.
- Rationale: The WavPack encoder accepts `u8p`, `s16p`, `s32p` and `fltp`,
  defaulting to the FIRST of them, so a fixture written without stating one is
  eight bit, reports a stated depth of 8 and the test proves the wrong thing
  while passing. A fixture that lies is worse than no fixture.
- Verification: the WavPack cases of FR-F07, which assert 16 and 32 against
  fixtures stating `s16p` and `s32p`.

**NFR-F-HONEST-001 The README says what supported means here**
- Requirement: The README shall state that these three formats are proved by
  generated fixtures rather than verified against files in the wild, naming also
  the formats that remain reported rather than played.
- Rationale: The README honesty rule, applied to the weaker evidence standard of
  section 1.3. A reader assuming "supported" means "tested against my files"
  would be assuming something nobody has checked.
- Verification: inspection, plus `tests/structural/test_no_dashes.py`, which
  holds every Markdown file to the rule on dashes. No test checks the README for
  version data or for the other prose rules.

**NFR-F-MAINT-001 The layering and the gate hold**
- Requirement: Every module holding these rules shall stay at or below the line
  cap, shall land at the comfortable target or below where it enters the danger
  band (both named in `tests/structural/test_loc.py`, which counts a file at the
  cap as inside the band), with the domain and application layers holding 100%
  branch coverage.
- Verification: `.\gate.ps1`, read by exit code.

### 3.3 Data

No new file and no new store. Two frozen sets in `walker.py` hold the rule:
`AUDIO_SUFFIXES` gains the three suffixes of FR-F01 and `UNPLAYABLE_SUFFIXES`
is the list of FR-F08.

## 4. Prioritisation

Must: FR-F01 to FR-F08 and every NFR.
Should: nothing.
Could: nothing.

Won't, recorded so it is not re-proposed: Monkey's Audio, Musepack,
DSD, TAK, CAF, `.m4b` and `.tta`, each for the reason given in section 1.4.

## 5. Open questions

None. OQ-F01: WMA files belong in the library rather than reported (Oliver's
ruling). It was made without certainty, since nobody here holds a WMA library;
somebody who does saying how theirs reads would settle it. Being wrong costs a
listener who wanted those files reported seeing albums appear instead, which is
visible rather than silent.

## 6. The standing check

A fixture of each format is walked, probed, assembled into an album and decoded
back from a test. That diagnostic says the foundation is sound; nothing here has
an interface of its own.
