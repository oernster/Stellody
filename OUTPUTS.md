# Choosing the output device

Specification for letting a listener choose which sound device Stellody plays
through, in the house form: EARS requirements, each with its failure case
beside it, each naming the test that proves it. Every requirement states the
rule as it stands today.

## 1. Introduction

### 1.1 Purpose

By default Stellody plays to whatever the operating system calls its default
output and follows it when the system moves it
(`infrastructure/output_devices.py`). A listener who wants the music on the
Focusrite while everything else stays on the speakers chooses it here, rather
than moving the whole system's default and every other application with it.

The choice is Stellody's alone. The list holds only the devices the system can
play to and is kept current while the application runs.

### 1.2 Intended audience

Whoever maintains or reviews it and Oliver, who owns every decision recorded
here.

### 1.3 What the design rests on

- **The player takes a device.** `WasapiPlayback` in `infrastructure/audio.py`
  hands its device to every stream it opens; `WasapiPlayback.use_device` sets
  it for the streams opened after.
- **A reopen in place exists.** `Transport._reopen_in_place` in
  `application/transport.py` opens the track in hand again at the same
  position, a paused track staying paused. The exclusive switch uses it too.
- **PortAudio lists every output up to four times** on Windows: once each
  through MME, DirectSound, WASAPI and WDM-KS. MME cuts names short; WDM-KS
  names driver endpoints. The WASAPI outputs are the list a listener knows,
  under the names Windows' own Sound settings use.
- **Qt lists outputs only.** No input device appears in
  `QMediaDevices.audioOutputs()`. PortAudio reports input and output channel
  counts for every device, so its list can be narrowed the same way.
- **Two outputs can share one name.** On the reference machine
  `U13ZA (NVIDIA High Definition Audio)` appears twice, told apart by Windows
  only through the endpoint identity.
- **The bundled PortAudio cannot state that identity.** It does not export
  `PaWasapi_GetDeviceId`, so a device can be matched to a PortAudio device only
  by name and position (NFR-O-PORT-001).
- **Qt notices changes; PortAudio does not.** `audioOutputsChanged` fires for a
  move of the default and for a change to the list. PortAudio lists devices
  once and keeps that list until it is taken again, which closes every stream
  it has open.

### 1.4 Scope

In:

- A button on the bottom strip opening a vertical list of the output devices.
- The same list in the Sound menu.
- A "System default" entry following the system's default.
- The list kept current while Stellody runs, with no relaunch.
- The choice remembered between launches.
- What happens when the chosen device is missing, disappears or returns.

Out, so that none of it is argued twice:

- **Input devices of any kind.** Microphones, line inputs and loopback
  captures are never listed.
- **Changing the system's default output.** Stellody chooses where its own
  music goes and nothing else; every other application stays where it was.
- **More than one device at once.** One stream, one device.
- **A device per track, album or genre.** One choice, for everything.
- **Setting a device's own format, volume or enhancements.** Those belong to
  the operating system's sound settings.
- **ASIO or any other driver model beyond the ones already used.**
- **Renaming a device.** Names are the system's.

### 1.5 Definitions

| Term | Meaning |
|---|---|
| Output device | A device the operating system lists as able to play sound: on Windows as its own endpoint enumeration (`IMMDeviceEnumerator::EnumAudioEndpoints`, render, active) reports it, elsewhere as `QMediaDevices.audioOutputs()` does. |
| System default | The output device the operating system currently names as its default. It can move while Stellody runs. |
| The choice | What the listener last picked: either System default or one named output device. |
| The device in use | The output device the open stream plays to. It differs from the choice only while the chosen device is missing or has refused to open. |
| The output list | The vertical list the button and the Sound menu both show. |
| Endpoint identity | The identity the operating system gives an output device: on Windows the endpoint identity its enumeration states, elsewhere `QAudioDevice.id()`. It survives a rename and tells apart two devices of the same name. |

### 1.6 References

- `ARCHITECTURE.md`: invariant 12, the section "Reaching the sound device"
  (which covers exclusive output) and the section "Choosing the output device".
- `infrastructure/output_devices.py`, `infrastructure/endpoints.py` and
  `infrastructure/pulsesink.py`, whose docstrings hold the measurements.
- `FORMATS.md`, for the house form this follows.

## 2. Overall description

### 2.1 Product perspective

An addition to playback. It changes where a stream opens, never what is in it:
the samples a device receives are those it received before, so bit perfect
exclusive output is untouched by it.

### 2.2 The one user class

A listener at the machine, who knows their devices by the names the system's
sound settings give them.

### 2.3 Operating environment

Three machines, one of each kind: a Windows 11 AMD desktop; a Framework 13 (AMD)
running Linux, measured inside the installed Flatpak; a MacBook Air on M4
silicon. "The reference machine" elsewhere in this document means the Windows
desktop.

### 2.4 Constraints

- **Taking PortAudio's list again closes every stream it has open.** Nothing
  that keeps the output list current may do it while music plays; it is done
  on the way into opening a stream, exactly as a move of the default is.
- **Identity by endpoint, display by name.** The choice is stored by endpoint
  identity because names repeat; the name is what the listener reads.
- **Nothing here reaches the network.** Invariant 12 stands unchanged.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-O01 | Qt's output list is the list the system's own sound settings show. Confirmed by Oliver choosing each listed device on all three machines of section 2.3 and hearing it play. | Oliver | Confirmed |
| A-O02 | `audioOutputsChanged` fires when a Bluetooth output connects or disconnects. Observed live: the list followed a pair of Bluetooth headphones on and off. The timed probe of OQ-O4 was not run. | Claude, with Oliver's Bathys | OQ-O4 |

## 3. Requirements

Every requirement below is a Must unless it carries a Priority line;
section 4 lists them.

### 3.1 Functional

**FR-O01 The button sits after the sound group's rule**
- Requirement: The bottom strip shall place the choose-device button, drawn from
  `assets/choose-audio-device.png`, immediately after the rule in the sound group
  and immediately before the exclusive switch.
- Rationale: Oliver's ruling. The device is a question about the stream, like
  exclusive output and the equalizer beside it, so it joins them after the rule
  rather than volume and mute before it.
- Acceptance: Given the window open, when the sound group is read left to right,
  then it holds volume, mute, the rule, choose device, exclusive, equalizer.
- Verified by: `tests/ui/test_output_button.py::test_the_button_sits_after_the_rule_before_exclusive`

**FR-O02 A press opens the output list**
- Requirement: When the choose-device button is pressed, the bottom strip shall
  open the output list as a vertical list anchored to the button.
- Rationale: The volume button opens its slider this way, so the strip keeps one
  way of opening something from a button.
- Acceptance: Given the window open, when the button is pressed, then a vertical
  list appears against it naming System default and every output device.
- Verified by: `tests/ui/test_output_button.py::test_a_press_opens_the_list`

**FR-O03 System default is listed first**
- Requirement: The output list shall name System default as its first entry,
  above every output device.
- Rationale: Oliver's ruling. It is the behaviour without a choice, so a listener
  who never opens the list loses nothing.
- Acceptance: Given any set of output devices, when the list is shown, then its
  first entry is System default.
- Verified by: `tests/domain/test_output_choice.py::test_system_default_leads_the_list`

**FR-O04 Only outputs are listed**
- Requirement: The output list shall name only devices the operating system
  reports as able to play sound.
- Rationale: Oliver's ruling. A microphone in a list of places to send music is a
  choice that cannot work.
- Acceptance: Given the reference machine with the Focusrite inputs, the OBSBOT
  microphone and Stereo Mix present, when the list is shown, then none of them
  appears in it.
- Verified by: `tests/infrastructure/test_output_list.py::TestTheRealList::test_the_list_is_read_from_the_outputs_alone`, plus a demonstration on the reference machine.

**FR-O05 Names are the system's, told apart where they repeat**
- Requirement: The output list shall show each output device under the name the
  operating system gives it; where two or more share a name, it shall add
  ` (2)`, ` (3)` and so on to the second and later, in the order the system
  lists them (on Windows, its endpoint enumeration order).
- Rationale: Oliver's ruling. Two identical lines are two choices a listener
  cannot tell apart.
- Acceptance: Given two devices named `U13ZA (NVIDIA High Definition Audio)`,
  when the list is shown, then they read `U13ZA (NVIDIA High Definition Audio)`
  and `U13ZA (NVIDIA High Definition Audio) (2)`.
- Verified by: `tests/domain/test_output_choice.py::test_a_repeated_name_is_numbered_in_listed_order`

**FR-O06 The device in use is marked**
- Requirement: The output list shall mark the entry the music is going to: the
  chosen device while it is present and opened, else System default.
- Rationale: A list of places with nothing saying which is in force answers the
  wrong half of the question. A tick on a device that is not playing answers it
  wrongly (Oliver's ruling).
- Acceptance: Given the Focusrite chosen, when the list is shown, then the
  Focusrite entry alone is marked. Given the Focusrite chosen and refusing, when
  the list is shown, then System default alone is marked.
- Verified by: `tests/ui/test_output_button.py::test_the_choice_is_marked`, `tests/domain/test_output_choice.py::test_a_refused_choice_leaves_the_tick_on_the_system_default`, `tests/application/test_choosing_an_output.py::TestARefusal::test_the_tick_is_on_the_default_it_plays_on`

**FR-O07 Choosing moves the music at once**
- Requirement: When an entry is chosen from the output list, the transport shall
  open the track in hand again on that device from the position it had reached,
  leaving a paused track paused. With nothing loaded, nothing is opened; the
  next stream opens on the new device.
- Rationale: Oliver's ruling, on the same reasoning as the exclusive switch: a
  choice whose effect cannot be heard until later reads as a choice that did
  nothing. It is a gap rather than a restart.
- Acceptance: Given a track playing at 1:30 on the speakers, when the Focusrite
  is chosen, then the track goes on from 1:30 on the Focusrite; given a track
  paused at 1:30, then it is still paused at 1:30, now on the Focusrite.
- Verified by: `tests/application/test_choosing_an_output.py::TestChoosing::test_choosing_reopens_in_place`, `tests/application/test_choosing_an_output.py::TestChoosing::test_a_paused_track_stays_paused`

**FR-O08 A device that will not open is said, not left silent**
- Requirement: If the chosen device refuses the stream, then the transport shall
  open the track on the system default instead; the window shall say on the
  status line which device refused and its reason. The choice stays as it was;
  the refused device is not asked again until the listener chooses it again or
  it leaves the list and returns. Where the refusal comes at a track boundary,
  the next track opens on the system default paused and the status line says
  so (`REFUSED_HELD_MESSAGE`), since music never goes to the speakers without a
  press (OQ-O5).
- Rationale: The unwanted sibling of FR-O07. Another application holding the
  device exclusively is the ordinary way it happens. Silence would read as a
  press that missed; retrying on every track would open each into the same
  refusal with the same message.
- Acceptance: Given the Focusrite held exclusively by another application, when
  it is chosen, then the music plays on the system default and the status line
  names the Focusrite with the reason the device gave.
- Verified by: `tests/application/test_choosing_an_output.py::TestARefusal::test_a_refusal_falls_back_to_the_default`, `tests/ui/test_output_messages.py::test_a_refusal_is_said`, `tests/application/test_a_lost_device_between_tracks.py::test_a_stale_device_failing_at_a_seam_holds_the_music`, `tests/ui/test_output_messages.py::test_a_refusal_at_the_next_track_is_said_by_the_poll`

**FR-O09 The choice is remembered**
- Requirement: The window shall store the choice by endpoint identity when it is
  made; at launch, the window shall restore it.
- Rationale: Oliver's ruling. Every other setting on the strip outlasts a
  session. Stored by identity because names repeat (FR-O05).
- Acceptance: Given the Focusrite chosen, when Stellody is closed and started
  again, then the Focusrite is the choice and the first track plays on it.
- Verified by: `tests/ui/test_output_settings.py::test_the_choice_outlasts_a_launch`

**FR-O10 A remembered device missing at launch**
- Requirement: If the remembered device is not listed at launch, then the
  transport shall play on the system default; the window shall keep the choice
  and say once on the status line that the device is missing.
- Rationale: Oliver's ruling. Headphones switched off overnight are not a reason
  to forget that the listener wants them.
- Acceptance: Given the Bathys remembered and switched off, when Stellody starts
  and a track plays, then it plays on the system default, the status line says
  the Bathys is not connected and the list still names the Bathys, with System
  default ticked (FR-O14).
- Verified by: `tests/application/test_choosing_an_output.py::TestAMissingChoice::test_a_missing_choice_plays_on_the_default`, `tests/ui/test_output_messages.py::test_a_missing_device_is_said_once`

**FR-O11 The chosen device disappearing while playing**
- Requirement: If the device in use disappears from the output list while a
  track is loaded, then the transport shall pause the track where it was; when
  play is next pressed, the transport shall open it on the system default from
  that place. The window shall say on the status line that the device
  disconnected.
- Rationale: Oliver's ruling (OQ-O5): music never goes to the speakers without a
  press. It is the same pause a move of the system output makes. A Bluetooth pair
  walking out of range is the ordinary case.
- Acceptance: Given a track playing at 2:00 on the Bathys, when the Bathys
  disconnects, then the track pauses at about 2:00 and the status line says the
  Bathys disconnected; when play is pressed, then it goes on from there on the
  system default.
- Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`, `tests/ui/test_output_messages.py::test_a_disconnect_while_playing_is_said`, `tests/ui/test_output_messages.py::test_a_disconnect_with_nothing_playing_is_said`

**FR-O12 The chosen device returning**
- Requirement: While the chosen device is missing, when it appears in the output
  list, the transport shall open the track in hand again on it from the position
  it had reached, leaving a paused track paused.
- Rationale: The other half of FR-O10 and FR-O11. The choice was kept precisely
  so it could come back; a listener who puts their headphones back on expects
  the music in them. A track paused by the loss stays paused, so nothing starts
  without a press. Only the listener's own choice is ever returned to
  automatically.
- Acceptance: Given the Bathys chosen but disconnected while a track plays on the
  speakers, when the Bathys connects, then the track moves to the Bathys from
  where it had reached and plays on; given a track paused when the Bathys
  disconnected, when the Bathys connects, then the track is on the Bathys and
  still paused.
- Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`

**FR-O13 The list is kept current**
- Requirement: When the operating system reports a change to its output
  devices, the window shall take the output list again, including while the list
  is open.
- Rationale: Oliver's ruling: a device connected while Stellody runs is offered
  with no relaunch. Event driven, since Qt already reports the change (section
  1.3); a poll would be a second mechanism for something one already answers.
  A-O02 is the measurement that decides whether Bluetooth is among what it
  reports.
- Acceptance: Given Stellody running with the list open, when the Bathys
  connects, then the Bathys appears in the list; when it disconnects, then it
  leaves the list unless it is the choice (FR-O14).
- Verified by: `tests/ui/test_output_list_follows.py::test_a_new_device_appears`, `tests/ui/test_output_list_follows.py::test_a_removed_device_leaves`, plus the live observation of A-O02.

**FR-O14 A missing choice stays in the list**
- Requirement: While the chosen device is missing, the output list shall still
  name it, marked as not connected and not ticked; System default carries the
  tick (FR-O06).
- Rationale: Without it, the choice the window kept (FR-O10) would be invisible;
  a listener could not see what will happen when the device returns.
- Acceptance: Given the Bathys chosen and disconnected, when the list is shown,
  then it names the Bathys as not connected, with System default ticked; when
  the Bathys returns, the tick goes back to it.
- Verified by: `tests/domain/test_output_choice.py::test_a_missing_choice_is_still_listed`, `tests/domain/test_output_choice.py::test_a_missing_choice_leaves_the_tick_on_the_system_default`, `tests/ui/test_output_list_follows.py::test_the_tick_moves_to_where_the_music_goes`, `tests/ui/test_output_list_follows.py::test_the_tick_goes_back_with_the_device`

**FR-O15 System default keeps following the system**
- Requirement: While System default is the choice, when the operating system
  moves its default output, the transport shall send the next stream it opens to
  the new default. Where the previous default is still listed (read from Qt's
  list at the moment the default moves), the transport shall also move the track
  in hand to the new default where it was, a playing track playing on and a
  paused one staying paused; where the previous default is gone, the track in
  hand is paused (FR-O11). While music plays on a device the listener named, a
  move of the default does nothing to it; music on the default only because the
  chosen device is missing or refused is paused rather than carried.
- Rationale: Headphones switched on are a request to hear the music there
  (Oliver's ruling), as is a default changed by hand with both devices still
  present. A device leaving still pauses, since music never goes to the speakers
  without a press.
- Acceptance: Given System default chosen, when Windows moves its default to the
  Focusrite, then the next track plays on the Focusrite. Given a track playing
  on the speakers, when the Px7 connects and becomes the default, then the track
  plays on through the Px7 from where it was, with no press.
- Verified by: `tests/infrastructure/test_output_devices.py`, `tests/application/test_choosing_an_output.py::TestTheSystemMovingItsDefault::test_the_default_is_followed`, `tests/application/test_a_device_arriving.py`, `tests/ui/test_output_composition.py::test_whether_the_default_left_reaches_the_transport`

**FR-O16 Exclusive output answers for the device in use**
- Requirement: The window shall judge whether exclusive output is offered
  against the device in use.
- Rationale: The rates a device takes exclusively differ by device. An offer
  judged against the system default while the music goes elsewhere would be a
  promise about the wrong device.
- Acceptance: Given the Focusrite chosen, when the window asks which rates are
  taken exclusively, then the question is put to the Focusrite.
- Verified by: `tests/ui/test_exclusive_follows_the_device.py`

**FR-O17 The Sound menu holds the same list**
- Requirement: The Sound menu shall hold an Output device submenu, beside
  Exclusive output, naming the same entries in the same order with the same
  mark.
- Rationale: Oliver's ruling. Every control on the strip is mirrored in the
  menus, which is also how a keyboard reaches it without the ring.
- Acceptance: Given the Focusrite chosen, when the Sound menu is opened, then
  its Output device submenu names System default and every output device, the
  Focusrite marked.
- Verified by: `tests/ui/test_output_menu.py::test_the_menu_mirrors_the_list`

**FR-O18 The keyboard reaches it**
- Requirement: The focus ring shall stop on the choose-device button in its drawn
  place; while the output list is open, the arrow keys shall move along it, Enter
  shall choose and Escape shall close it with the choice unchanged.
- Rationale: The house keyboard model, applied to one more control. A list only
  a mouse can use is not reachable.
- Acceptance: Given focus on mute, when Tab is pressed, then focus is on
  the choose-device button; given the list open, when Down is pressed twice
  (past System default) then Enter, then the first output device is chosen;
  given the list open, when
  Escape is pressed, then nothing changes.
- Verified by: `tests/ui/test_output_button.py::test_the_ring_stops_on_it_straight_after_mute`, `tests/ui/test_output_button.py::test_the_list_is_keyboard_driven`, `tests/ui/test_output_button.py::test_escape_leaves_the_choice_alone`

**FR-O19 The tooltip names the press**
- Requirement: The choose-device button shall carry the tooltip "Choose the
  output device".
- Rationale: The strip's rule: a tooltip names what a press would do.
- Acceptance: Given the window open, when the button is hovered, then its
  tooltip reads "Choose the output device".
- Verified by: `tests/ui/test_output_button.py::test_the_tooltip_names_the_press`

**FR-O20 A second press closes the output list**
- Requirement: While the output list is open, when the choose-device button is
  pressed, the bottom strip shall leave the list closed rather than opening it
  again.
- Rationale: The volume slider closes on a second press of its own button, so
  the strip keeps one way of closing something a button opened. Qt takes the
  list down on the press itself, then Windows replays that press onto the
  button, whose click would otherwise open a fresh list; the button therefore
  has to tell a replayed click from a first one.
- Acceptance: Given the output list open, when the button is pressed, then no
  list is on the screen afterwards; when it is pressed again, then the list
  opens.
- Verified by: `tests/ui/test_output_button.py::test_a_second_press_closes_it`,
  `tests/ui/test_output_button.py::test_a_press_anywhere_else_closes_it_without_swallowing_the_next`,
  `tests/ui/test_output_button.py::test_choosing_a_line_leaves_the_list_able_to_open_again`

### 3.2 Non-functional

**NFR-O-PERF-001 A device change reaches the list in time.** When an output
device connects or disconnects, the output list shall reflect it within 2
seconds of the operating system's own Sound settings showing the change,
measured on the reference machine by connecting and disconnecting the Bathys
five times with the list open. Not yet measured: that is the timed probe of
OQ-O4, which is still open. Priority: Must.

**NFR-O-PERF-002 Keeping the list current never interrupts the music.** While
a track plays, a change to the device list shall not take PortAudio's list
again, unless the change is one FR-O11 or FR-O12 acts on. Verified by
`tests/infrastructure/test_output_list.py::test_a_list_change_leaves_the_stream_alone`,
which counts calls to the rescan. Priority: Must.

**NFR-O-PRIV-001 Nothing leaves the machine.** Device names and identities
are held in Stellody's own settings alone. No code of Stellody's writes them to
either of its logs. Qt's own warnings are copied into the diary word for word
(`infrastructure/qt_messages.py`), so a Qt warning that named a device would
carry that name there; no test checks for one. That nothing leaves the machine
is held by the existing invariant 12 test, which this change must leave green.
Priority: Must.

**NFR-O-MAINT-001 The house limits hold.** Domain and application keep 100%
branch coverage; every module stays at or below the 400 line cap and out of
the danger band. The button lives inside `SoundControls`
(`ui/sound_controls.py`) rather than in `ui/bottom_tray.py`. Verified by the
existing structural suite. Priority: Must.

**NFR-O-PORT-001 Platforms.** The button and the list shall be present on
Windows, macOS and Linux alike (Oliver's ruling: a feature that is not there
cannot be proved to work or to fail). Each is verified on a real machine of
that kind by choosing every listed device and hearing it play there. A chosen
device is reached as follows:

- **Windows.** The list is read from Windows' own endpoint enumeration, which
  gives the identity and the order together; Qt's order (default first) is
  never used to match. PortAudio's WASAPI outputs arrive in that enumeration
  order, so the n-th device of a name is the n-th PortAudio WASAPI output of
  that name (`domain/outputs.py`, `opener_position`). That correspondence was
  measured on one machine, so it is relied on only while the two lists agree
  name for name; otherwise a device whose name repeats is not guessed at. A
  device whose name is unique is matched by name whatever the order.
- **macOS.** Qt's names match PortAudio's CoreAudio names, so a device is
  matched by name.
- **Linux and any other platform.** Qt lists the sound server's devices while
  PortAudio is built against ALSA, so no name appears on both sides. Qt's id
  for a device is the sink's own name, so the stream is opened on PortAudio's
  `pulse` device with `PULSE_SINK` naming the sink
  (`infrastructure/pulsesink.py`); the by-name match stays the route where
  there is no sound server. The variable is held for the open alone, since a
  sink is chosen when the stream connects. A sink name no sink carries opens on
  the system default, as FR-O10 asks.

A device that cannot be matched or addressed is a refusal, so FR-O08 applies:
the music falls back to the system default and the status line names the
device. Priority: Must.

### 3.3 Data

Two settings beside the others in `ui/settings_keys.py`:

| Setting | Holds | Empty means |
|---|---|---|
| `output_device` | The endpoint identity of the chosen device | System default |
| `output_device_name` | The name the device had when it was chosen | Nothing; used only to name a missing device in FR-O10 |

The name is stored as well as the identity because a missing device cannot be
asked its name; without it FR-O10 could only say "a device is missing".

## 4. Prioritisation

Every functional requirement is a Must: the feature is small; each one is a
case the feature would be incomplete without. Won't this time is the out-of-scope list
in section 1.4.

## 5. Open questions

| # | Question | Owner | Probe | Status |
|---|---|---|---|---|
| OQ-O1 | Which PortAudio device is which of two outputs sharing a name? | Claude | | Answered: by Windows' enumeration order (NFR-O-PORT-001) |
| OQ-O2 | Can Qt's and PortAudio's lists be matched on Linux inside the Flatpak? | Claude | | Answered: not by name; the device is addressed by sink (NFR-O-PORT-001) |
| OQ-O3 | On macOS, do Qt's names match PortAudio's CoreAudio names? | Oliver | | Answered: they match; every listed device plays when chosen |
| OQ-O4 | Does Qt report a Bluetooth output connecting and disconnecting on Windows? (A-O02) | Claude, with Oliver's Bathys | Log every `audioOutputsChanged` with a timestamp while the Bathys connects and disconnects five times. If it misses any, a poll of `QMediaDevices.audioOutputs()` once a second replaces the signal; the poll never touches PortAudio. | Observed working live; the timed probe is still open |
| OQ-O5 | Which rule governs the chosen device leaving and returning? | Oliver | | Answered: music never goes to the speakers without a press (FR-O11, FR-O12) |

## 6. How the layers divide the work

1. **Domain**: the output list as a value (System default first, numbered
   repeats, a missing choice kept and marked), plus the rule choosing the
   device in use from the choice and the devices present. Pure, with no Qt.
2. **Application**: the transport taking a choice, reopening in place on a
   change, falling back on a refusal or a disappearance, moving back on a
   return. Driven by fakes; FR-O07 to FR-O12 all run with no device.
3. **Infrastructure**: reading the output list; matching an entry to a
   PortAudio device or addressing its sink (NFR-O-PORT-001); the engine opening
   each stream on the device it is handed.
4. **UI**: the button, the list, the menu mirror, the messages, the settings.

Choosing a device, losing it and getting it back are each driven from tests
against fakes (`tests/application/test_choosing_an_output.py`).
