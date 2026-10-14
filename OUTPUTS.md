# Choosing the output device

Requirements for choosing which sound device Stellody plays through. EARS
form; each requirement names its test.

## 1. Introduction

### 1.1 Purpose

By default Stellody follows the system's default output
(`infrastructure/output_devices.py`). This lets the listener send the music
elsewhere without moving the system default. The list holds only playable
devices and stays current.

### 1.2 Intended audience

Maintainers, reviewers and Oliver, who owns every decision here.

### 1.3 What the design rests on

- `WasapiPlayback` (`infrastructure/audio.py`) opens every stream on its
  device; `use_device` sets it for later streams.
- `Transport._reopen_in_place` (`application/transport.py`) reopens the track
  in hand at its position, paused if it was.
- On Windows PortAudio lists each output once per host API; the WASAPI ones
  carry Windows' own names.
- Qt lists outputs only; PortAudio's channel counts narrow its list likewise.
- Two outputs can share a name; only the endpoint identity separates them.
- The bundled PortAudio lacks `PaWasapi_GetDeviceId`, so matching is by name
  and position (NFR-O-PORT-001).
- Qt's `audioOutputsChanged` reports default moves and list changes.
  PortAudio's list is fixed until retaken, which closes every open stream.

### 1.4 Scope

In: a bottom-strip button opening a vertical device list; the same list in the
Sound menu; a "System default" entry; live updates; the choice remembered;
handling a chosen device missing, leaving or returning.

Out: input devices; changing the system default; several devices at once; a
device per track, album or genre; device format, volume or enhancements; ASIO
or other driver models; renaming devices.

### 1.5 Definitions

| Term | Meaning |
|---|---|
| Output device | One the system lists as able to play: on Windows its active render endpoints (`IMMDeviceEnumerator::EnumAudioEndpoints`), elsewhere `QMediaDevices.audioOutputs()`. |
| System default | The system's current default output; it can move. |
| The choice | The listener's last pick: System default or one device. |
| The device in use | Where the open stream plays; differs from the choice only while the chosen device is missing or refused. |
| The output list | The list the button and the Sound menu show. |
| Endpoint identity | The system's id for a device (Windows enumeration, elsewhere `QAudioDevice.id()`); survives renames and separates same-named devices. |

### 1.6 References

`ARCHITECTURE.md` (invariant 12, "Reaching the sound device", "Choosing the
output device"); the docstrings of `infrastructure/output_devices.py`,
`endpoints.py` and `pulsesink.py`; `FORMATS.md`.

## 2. Overall description

### 2.1 Product perspective

It changes where a stream opens, never its samples; bit perfect output is
untouched.

### 2.2 The one user class

A listener who knows devices by the system's names.

### 2.3 Operating environment

The reference machine is a Windows 11 AMD desktop; also a Framework 13 (AMD)
running the Linux Flatpak and an M4 MacBook Air.

### 2.4 Constraints

- PortAudio's list is retaken only on the way into opening a stream, never
  while music plays.
- Stored by endpoint identity, shown by name.
- Nothing reaches the network (invariant 12).

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-O01 | Qt's list matches the system's sound settings; every device was heard on all three machines. | Oliver | Confirmed |
| A-O02 | `audioOutputsChanged` fires on Bluetooth connect and disconnect; seen live, not yet timed. | Claude, with Oliver's Bathys | OQ-O4 |

## 3. Requirements

All Must (section 4).

### 3.1 Functional

**FR-O01 The button sits after the sound group's rule**
- Requirement: The bottom strip shall place the choose-device button
  (`assets/choose-audio-device.png`) immediately after the sound group's rule
  and before the exclusive switch (Oliver's ruling).
- Verified by: `tests/ui/test_output_button.py::test_the_button_sits_after_the_rule_before_exclusive`

**FR-O02 A press opens the output list**
- Requirement: When the button is pressed, the bottom strip shall open the
  output list as a vertical list anchored to it.
- Verified by: `tests/ui/test_output_button.py::test_a_press_opens_the_list`

**FR-O03 System default is listed first**
- Requirement: The output list shall name System default first (Oliver's
  ruling).
- Verified by: `tests/domain/test_output_choice.py::test_system_default_leads_the_list`

**FR-O04 Only outputs are listed**
- Requirement: The output list shall name only devices the system reports as
  able to play (Oliver's ruling).
- Verified by: `tests/infrastructure/test_output_list.py::TestTheRealList::test_the_list_is_read_from_the_outputs_alone`, plus a demonstration on the reference machine.

**FR-O05 Names are the system's, told apart where they repeat**
- Requirement: The output list shall use the system's names, adding ` (2)`, `
  (3)` and so on to repeats in the system's listing order (Oliver's ruling).
- Verified by: `tests/domain/test_output_choice.py::test_a_repeated_name_is_numbered_in_listed_order`

**FR-O06 The device in use is marked**
- Requirement: The output list shall tick the chosen device while it is present
  and opened, else System default (Oliver's ruling).
- Verified by: `tests/ui/test_output_button.py::test_the_choice_is_marked`, `tests/domain/test_output_choice.py::test_a_refused_choice_leaves_the_tick_on_the_system_default`, `tests/application/test_choosing_an_output.py::TestARefusal::test_the_tick_is_on_the_default_it_plays_on`

**FR-O07 Choosing moves the music at once**
- Requirement: When an entry is chosen, the transport shall reopen the track in
  hand there at its position, paused if it was; with nothing loaded, the next
  stream opens there (Oliver's ruling).
- Verified by: `tests/application/test_choosing_an_output.py::TestChoosing::test_choosing_reopens_in_place`, `tests/application/test_choosing_an_output.py::TestChoosing::test_a_paused_track_stays_paused`

**FR-O08 A device that will not open is said, not left silent**
- Requirement: If the chosen device refuses the stream, then the transport shall
  play on the system default; the status line shall name the device and reason.
  The choice stays; the device is not retried until chosen again or until it
  leaves the list and returns. At a track boundary the next track opens on the
  default paused, said on the status line (`REFUSED_HELD_MESSAGE`; OQ-O5).
- Verified by: `tests/application/test_choosing_an_output.py::TestARefusal::test_a_refusal_falls_back_to_the_default`, `tests/ui/test_output_messages.py::test_a_refusal_is_said`, `tests/application/test_a_lost_device_between_tracks.py::test_a_stale_device_failing_at_a_seam_holds_the_music`, `tests/ui/test_output_messages.py::test_a_refusal_at_the_next_track_is_said_by_the_poll`

**FR-O09 The choice is remembered**
- Requirement: The window shall store the choice by endpoint identity and
  restore it at launch (Oliver's ruling).
- Verified by: `tests/ui/test_output_settings.py::test_the_choice_outlasts_a_launch`

**FR-O10 A remembered device missing at launch**
- Requirement: If the remembered device is absent at launch, then the transport
  shall play on the system default; the window shall keep the choice and say
  once that the device is missing (Oliver's ruling).
- Verified by: `tests/application/test_choosing_an_output.py::TestAMissingChoice::test_a_missing_choice_plays_on_the_default`, `tests/ui/test_output_messages.py::test_a_missing_device_is_said_once`

**FR-O11 The chosen device disappearing while playing**
- Requirement: If the device in use leaves the list while a track is loaded,
  then the transport shall pause it; the next play opens it on the system
  default from there. The status line shall say the device disconnected. Music
  never goes to the speakers without a press (Oliver's ruling, OQ-O5).
- Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`, `tests/ui/test_output_messages.py::test_a_disconnect_while_playing_is_said`, `tests/ui/test_output_messages.py::test_a_disconnect_with_nothing_playing_is_said`

**FR-O12 The chosen device returning**
- Requirement: While the chosen device is missing, when it reappears, the
  transport shall reopen the track in hand on it at its position, paused if it
  was.
- Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`

**FR-O13 The list is kept current**
- Requirement: When the system reports an output change, the window shall retake
  the output list, even while it is open (Oliver's ruling).
- Verified by: `tests/ui/test_output_list_follows.py::test_a_new_device_appears`, `tests/ui/test_output_list_follows.py::test_a_removed_device_leaves`, plus the live observation of A-O02.

**FR-O14 A missing choice stays in the list**
- Requirement: While the chosen device is missing, the list shall still name it,
  marked not connected; System default carries the tick.
- Verified by: `tests/domain/test_output_choice.py::test_a_missing_choice_is_still_listed`, `tests/domain/test_output_choice.py::test_a_missing_choice_leaves_the_tick_on_the_system_default`, `tests/ui/test_output_list_follows.py::test_the_tick_moves_to_where_the_music_goes`, `tests/ui/test_output_list_follows.py::test_the_tick_goes_back_with_the_device`

**FR-O15 System default keeps following the system**
- Requirement: While System default is the choice, when the system default
  moves, the next stream shall open on the new default. If the old default is
  still in Qt's list at that moment, the track in hand moves to the new one as
  it was, playing or paused; if gone, it pauses (FR-O11). A default move leaves
  music on a named device alone; music on the default only because the choice is
  missing or refused is paused (Oliver's ruling).
- Verified by: `tests/infrastructure/test_output_devices.py`, `tests/application/test_choosing_an_output.py::TestTheSystemMovingItsDefault::test_the_default_is_followed`, `tests/application/test_a_device_arriving.py`, `tests/ui/test_output_composition.py::test_whether_the_default_left_reaches_the_transport`

**FR-O16 Exclusive output answers for the device in use**
- Requirement: The window shall judge whether exclusive output is offered
  against the device in use.
- Verified by: `tests/ui/test_exclusive_follows_the_device.py`

**FR-O17 The Sound menu holds the same list**
- Requirement: The Sound menu shall hold an Output device submenu beside
  Exclusive output with the same entries, order and tick (Oliver's ruling).
- Verified by: `tests/ui/test_output_menu.py::test_the_menu_mirrors_the_list`

**FR-O18 The keyboard reaches it**
- Requirement: The focus ring shall stop on the button in its drawn place; in
  the open list, arrows shall move, Enter shall choose; Escape shall close it
  unchanged.
- Verified by: `tests/ui/test_output_button.py::test_the_ring_stops_on_it_straight_after_mute`, `tests/ui/test_output_button.py::test_the_list_is_keyboard_driven`, `tests/ui/test_output_button.py::test_escape_leaves_the_choice_alone`

**FR-O19 The tooltip names the press**
- Requirement: The button shall carry the tooltip "Choose the output device".
- Verified by: `tests/ui/test_output_button.py::test_the_tooltip_names_the_press`

**FR-O20 A second press closes the output list**
- Requirement: While the list is open, when the button is pressed, the list
  shall end closed; the button tells Windows' replay of the closing press from a
  first click.
- Verified by: `tests/ui/test_output_button.py::test_a_second_press_closes_it`,
  `tests/ui/test_output_button.py::test_a_press_anywhere_else_closes_it_without_swallowing_the_next`,
  `tests/ui/test_output_button.py::test_choosing_a_line_leaves_the_list_able_to_open_again`

### 3.2 Non-functional

**NFR-O-PERF-001 A device change reaches the list in time.** Not yet measured
(OQ-O4). A connect or disconnect shall show in the list within 2 seconds of
the system's Sound settings, over five cycles on the reference machine.

**NFR-O-PERF-002 Keeping the list current never interrupts the music.** While
a track plays, a list change shall not retake PortAudio's list unless FR-O11
or FR-O12 acts on it. Verified by
`tests/infrastructure/test_output_list.py::test_a_list_change_leaves_the_stream_alone`.

**NFR-O-PRIV-001 Nothing leaves the machine.** Device names and identities
live only in settings; no Stellody code logs them. Qt warnings are copied into
the diary verbatim (`infrastructure/qt_messages.py`), so one naming a device
would carry it; untested. The invariant 12 test holds the rest.

**NFR-O-MAINT-001 The house limits hold.** Full branch coverage of domain and
application; every module within `LINE_CAP` and out of the danger band
(`tests/structural/test_loc.py`). The button lives in `SoundControls`
(`ui/sound_controls.py`). Verified by the structural suite.

**NFR-O-PORT-001 Platforms.** The button and list shall exist on Windows,
macOS and Linux (Oliver's ruling), each verified by hearing every listed device
on a real machine. Reaching a device:

- **Windows.** The list comes from the endpoint enumeration, giving identity
  and order; PortAudio's WASAPI outputs share that order, so the n-th device of
  a name is the n-th WASAPI output of that name (`domain/outputs.py`,
  `opener_position`), trusted only while both lists agree name for name. A
  unique name matches by name.
- **macOS.** Qt's names match CoreAudio's; matched by name.
- **Linux and elsewhere.** No names match across Qt and ALSA, so the stream
  opens on PortAudio's `pulse` device with `PULSE_SINK` set to Qt's id for
  the open alone (`infrastructure/pulsesink.py`); without a sound server, name
  matching. An unknown sink opens on the system default (FR-O10).

An unmatched device is a refusal (FR-O08).

### 3.3 Data

In `ui/settings_keys.py`:

| Setting | Holds | Empty means |
|---|---|---|
| `output_device` | The chosen device's endpoint identity | System default |
| `output_device_name` | Its name when chosen, so FR-O10 can name it while missing | Nothing |

## 4. Prioritisation

Every requirement is a Must. Won't this time is the out list in 1.4.

## 5. Open questions

| # | Question | Owner | Status |
|---|---|---|---|
| OQ-O1 | Which PortAudio device is which of two same-named outputs? | Claude | Answered: enumeration order (NFR-O-PORT-001) |
| OQ-O2 | Can Qt's and PortAudio's lists match on Linux in the Flatpak? | Claude | Answered: by sink, not name (NFR-O-PORT-001) |
| OQ-O3 | On macOS, do Qt's names match CoreAudio's? | Oliver | Answered: yes |
| OQ-O4 | Does Qt report Bluetooth connects and disconnects on Windows? (A-O02) | Claude, with Oliver's Bathys | Seen live. Probe: timestamp every `audioOutputsChanged` over five cycles; a miss means a once-a-second poll of `QMediaDevices.audioOutputs()`, never touching PortAudio, replaces the signal. |
| OQ-O5 | Which rule governs the chosen device leaving and returning? | Oliver | Answered: no music to the speakers without a press (FR-O11, FR-O12) |

## 6. How the layers divide the work

1. **Domain**: the list as a value (System default first, numbered repeats,
   missing choice kept) and the rule picking the device in use. No Qt.
2. **Application**: the transport choosing, reopening, falling back and
   returning; FR-O07 to FR-O12 run on fakes
   (`tests/application/test_choosing_an_output.py`).
3. **Infrastructure**: reading the list; matching or addressing a device;
   opening streams on it.
4. **UI**: button, list, menu, messages, settings.
