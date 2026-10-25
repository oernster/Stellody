# Formats proved by a fixture rather than by a file somebody owns

Specification for the formats Stellody decodes on the strength of a generated
fixture. EARS requirements in the house form, each naming the test that proves
it.

## 1. Introduction

### 1.1 Purpose

`.wma`, `.wv` and `.aac` need no new decoder: the FFmpeg inside PyAV decodes
them, mutagen reads the WMA and WavPack tags (a raw AAC stream carries none,
FR-F04) and the packet reader addresses them by frame.
Each is claimed on the standard of section 1.3.

### 1.2 Intended audience

Implementers, reviewers and Oliver, who owns every decision here.

### 1.3 The evidence standard

A format may be claimed where a test proves the whole path: a fixture encoded
at test time, walked, probed, assembled and decoded back (Oliver's ruling).

This proves the pipeline handles what FFmpeg writes, not what other encoders or
rippers write; tags are where those differ. "Supported" here means decoded with
whatever tags the file carries read, proved by test; not verified against files
in the wild (NFR-F-HONEST-001).

### 1.4 Scope

**In scope:** the three suffixes; their tag reading; the bit-depth honesty rule
extended to them; fixtures generated in the suite.

**Out of scope:**

- **Monkey's Audio, Musepack, DSD and TAK.** The bundled FFmpeg decodes them
  and mutagen reads their tags but FFmpeg encodes none, so no fixture can meet
  the standard. They are reported (FR-F08). Each reopens once a fixture can be
  made or a real file is measured.
- **CAF.** libsndfile decodes it; mutagen reads nothing from it, so it would
  scan as an album with no title.
- **`.m4b`** (Oliver's ruling). It would work like `.m4a` but an audiobook is
  not music; a chaptered one would arrive as one enormous track.
- **`.tta`.** It decodes but mutagen states no channel count, so the probe
  would have to invent one; also rare.
- **Writing any of these formats.** Stellody never writes music files
  (invariants 1 and 2); only the suite writes fixtures, to a temporary
  directory.
- **Any new dependency.**

### 1.5 Definitions

| Term | Meaning here |
|---|---|
| Fixture | An audio file the suite encodes at test time; never committed. |
| Stated depth | The bits per sample a file declares; nought if none. |
| Taken suffix | An extension the walk accepts as a track. |
| Reported suffix | An extension the walk names as present and unplayable. |

### 1.6 References

`ARCHITECTURE.md`: its invariants and "Formats and probing", which states the
five tag shapes the probe reads.

## 2. Overall description

### 2.1 Product perspective

Held by the walk, the probe and the decoder chooser. Nothing here reaches the
network (invariant 12 holds) or adds a dependency.

### 2.2 The one user class

A listener with a mixed library on their own machine.

### 2.3 Operating environment

Windows, macOS and Linux. The FFmpeg inside PyAV supplies every decoder named.

### 2.4 Constraints

- **C-F01** No new dependency; no growth in the packaged build.
- **C-F02** No music file is written, except fixtures the suite writes to its
  own temporary directory.
- **C-F03** A format is claimed only where a test proves the whole path.
- **C-F04** The layering, line cap and coverage gate hold (NFR-F-MAINT-001).

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-F01 | Measured: the bundled FFmpeg decodes wmav1, wmav2, wmapro, wmalossless, wavpack and aac; it encodes all but wmapro and wmalossless. | | Answered |
| A-F02 | Measured: mutagen reads ASF and WavPack tags; it opens raw AAC but reads no tags from it. It states no depth for WMA or raw AAC; a WavPack fixture written as `s16p` reports 16. | | Answered |
| A-F03 | A listener with WMA files wants them in the library rather than reported (Oliver's ruling, made without a WMA library to check against). If wrong, albums appear where a report was wanted, which is visible rather than silent. | | Answered |

## 3. Requirements

Every requirement is a Must unless it carries a Priority line (section 4).

### 3.1 Functional

**FR-F01 The three suffixes are taken**
- Requirement: The walker shall take `.wma`, `.wv` and `.aac` as audio and
  shall not report them as unplayable.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_widened_suffixes_are_taken`

**FR-F02 Each is decoded through the reader that already addresses packets**
- Requirement: When a source with one of the three suffixes is opened, the
  decoder chooser shall return the packet reader, which counts packet
  timestamps back into frame positions.
- Rationale: As for M4A, none is frame addressable like a WAV; cue slices, the
  equalizer, the visualiser and gapless depend on that counting.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_each_widened_format_decodes_through_the_packet_reader`

**FR-F03 A file that will not decode is reported, never left as silence**
- Requirement: If a file with one of the three suffixes cannot be decoded, then
  the transport shall raise the domain's playback error, which the window
  catches in one place to say so and release the device.
- Rationale: Files in the wild will differ from the fixture, so this is the
  ordinary case here.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_widened_suffix_that_will_not_decode_says_so`, `tests/ui/test_saying_a_track_will_not_open.py`

**FR-F04 Tags are read for each family**
- Requirement: When a file with one of the three suffixes is probed, the probe
  shall read its album artist, title, date, genre, disc number and track number
  where stated, translated into the names the resolution rules read. ASF (WMA)
  is the fourth tag shape; APEv2 (WavPack), iterated as keys rather than pairs,
  is the fifth. A raw AAC stream has no tag block, so states no tags.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_asf_tags_arrive_under_the_domain_names`

**FR-F05 A file whose tags cannot be read still scans**
- Requirement: If a file with one of the three suffixes states no readable
  tags, then the probe shall report the values as absent without raising, so
  the folder assembles into an album as usual.
- Rationale: One file must never put rows in the store that break every later
  start.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_an_untagged_widened_file_still_assembles`

**FR-F06 A lossy source states no depth and is never bit perfect**
- Requirement: The probe shall report a stated depth of nought for WMA and AAC,
  so `is_bit_perfect` is false for either in every output mode.
  `stellody/domain/formats.py` names both in `LOSSY_FAMILIES` by codec, so a
  tag library reporting a header depth changes nothing.
- Rationale: The requirement this specification turns on: a container's stated
  depth would otherwise badge a lossy track as delivered untouched.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_a_lossy_widened_format_states_no_depth`, `tests/domain/test_output_request.py::test_a_widened_lossy_source_is_never_bit_perfect`, `tests/infrastructure/test_exclusive_refusal.py::test_a_lossy_source_is_refused_exclusive_for_the_file`

**FR-F07 A lossless source keeps the depth it states**
- Requirement: The probe shall report the bits per sample a WavPack file
  states rather than nought.
- Rationale: The half a guard written only against lossy formats would break.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_wavpack_keeps_the_depth_it_states`

**FR-F08 What remains unplayable is still named**
- Requirement: The walker shall name `.ape`, `.mpc`, `.dsf`, `.dff`, `.tta`,
  `.tak`, `.m4b` and `.caf` as unplayable, so a folder holding only those
  raises one finding naming how many files and which formats.
- Rationale: An album a listener owns must never be silently absent.
- Verified by: `tests/infrastructure/test_scanning_formats.py::test_the_formats_left_out_are_still_reported`

### 3.2 Non-functional

**NFR-F-TEST-001 Every fixture is generated, never committed**
- Requirement: The suite shall encode each fixture into a temporary directory
  at test time; the repository holds no `.wma`, `.wv` or `.aac` file.
- Rationale: The basis of the evidence standard; it also avoids licence
  questions and repository growth.
- Verification: `tests/structural/test_no_committed_audio.py::test_no_fixture_audio_is_committed`
  (invariant 21), which scans the working tree for any `.wma`, `.wv` or `.aac`
  file (so it also catches a fixture nobody has staged), plus every fixture
  being built by `tests/infrastructure/widened_support.py` into the temporary
  directory pytest hands the test.

**NFR-F-TEST-002 A fixture states its sample format**
- Requirement: Every fixture shall state its sample format rather than letting
  the encoder choose.
- Rationale: The WavPack encoder defaults to `u8p`, so an unstated fixture
  reports depth 8 and the test passes while proving the wrong thing.
- Verification: the WavPack cases of FR-F07, which assert 16 and 32 against
  fixtures stating `s16p` and `s32p`.

**NFR-F-HONEST-001 The README says what supported means here**
- Requirement: The README shall state that these three formats are proved by
  generated fixtures rather than files in the wild, naming the formats that
  remain reported rather than played (Oliver's ruling).
- Verification: inspection. No test reads the README's wording.

**NFR-F-MAINT-001 The layering and the gate hold**
- Requirement: Every module holding these rules shall stay at or below the
  line cap; where it enters the danger band it shall land at or below the
  comfortable target (both in `tests/structural/test_loc.py`, which counts a
  file at the cap as inside the band); domain and application hold 100% branch
  coverage.
- Verification: `.\gate.ps1`, read by exit code.

### 3.3 Data

No file or store of its own. In `infrastructure/walker.py`, `AUDIO_SUFFIXES`
includes the suffixes of FR-F01; `UNPLAYABLE_SUFFIXES` is the list of FR-F08.
In `infrastructure/decode.py`, `PACKET_SUFFIXES` holds the three beside `.m4a`
and the picture suffixes, which is how the chooser of FR-F02 sends them to the
packet reader.

## 4. Prioritisation

Must: FR-F01 to FR-F08 and every NFR. Should and Could: nothing.

Won't: Monkey's Audio, Musepack, DSD, TAK, CAF, `.m4b` and `.tta` (section
1.4).

## 5. Open questions

None.
