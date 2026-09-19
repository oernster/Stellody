# Choosing the output device

Specification for letting a listener choose which sound device Stellody plays
through, written before the code in the house form: EARS requirements, each
with its failure case beside it, each naming the test that will prove it.

Baseline: this specification as first written, 2026-09-18. Changes after that
arrive as numbered amendments with a reason rather than as silent edits.

## 1. Introduction

### 1.1 Purpose

Stellody plays to whatever the operating system calls its default output and
follows it when the system moves it (`infrastructure/output_devices.py`). A
listener who wants the music on the Focusrite while everything else on the
machine stays on the speakers has no way to say so; they have to move the
whole system's default, which moves every other application with it.

This adds a choice of output device to Stellody alone, listing only the
devices the system can play to, kept current while the application runs.

### 1.2 Intended audience

Whoever implements it, whoever reviews it and Oliver, who owns every decision
recorded here.

### 1.3 What already exists, measured

Measured on the reference machine on 2026-09-18 unless marked otherwise.

- **The player already takes a device.** `AudioEngine` in
  `infrastructure/audio.py` accepts a device number and hands it to every
  stream it opens; the composition root passes none, so today every stream
  opens on the default. The number is fixed when the engine is built.
- **A reopen in place already exists.** `Transport._reopen_in_place` in
  `application/transport.py` opens the track in hand again at the same
  position, a paused track staying paused. The exclusive switch uses it.
- **PortAudio lists every output up to four times.** Once each through MME,
  DirectSound, WASAPI and WDM-KS. MME cuts names to 31 characters; WDM-KS names
  driver endpoints, among them
  `Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0 ...)`.
- **The WASAPI outputs are the list a listener knows.** Seven of them, with the
  names Windows' own Sound settings use. Qt's `QMediaDevices.audioOutputs()`
  reports the same seven names, each with the endpoint identity Windows gives
  it.
- **Qt lists outputs only.** No input device appears in
  `QMediaDevices.audioOutputs()`. PortAudio reports input and output channel
  counts for every device, so its list can be narrowed the same way.
- **Two outputs share one name.** `U13ZA (NVIDIA High Definition Audio)`
  appears twice, told apart by Windows only through the endpoint identity.
- **PortAudio cannot state that identity here.** The bundled library is
  `PortAudio V19.7.0-devel`; it does not export `PaWasapi_GetDeviceId`, so a
  device Qt names can be matched to a PortAudio device by name alone. OQ-O1.
- **Qt notices changes; PortAudio does not.** Measured on 2026-09-14 and
  recorded in `output_devices.py`: `audioOutputsChanged` fired within a second
  of every default switch and fires for a change to the list too. PortAudio
  lists devices once and keeps that list until it is taken again, which closes
  every stream it has open.

### 1.4 Scope

In:

- A button on the bottom strip opening a vertical list of the output devices.
- The same list in the Sound menu.
- A "System default" entry keeping today's behaviour.
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
| Output device | A device the operating system lists as able to play sound: on Windows as its own endpoint enumeration reports it (Amendment 2), elsewhere as `QMediaDevices.audioOutputs()` does. |
| System default | The output device the operating system currently names as its default. It can move while Stellody runs. |
| The choice | What the listener last picked: either System default or one named output device. |
| The device in use | The output device the open stream plays to. It differs from the choice only while the chosen device is missing or has refused to open (Amendment 3). |
| The output list | The vertical list the button and the Sound menu both show. |
| Endpoint identity | The identity the operating system gives an output device: on Windows the endpoint identity its enumeration states, elsewhere `QAudioDevice.id()`. It survives a rename and tells apart two devices of the same name. |

### 1.6 References

- `ARCHITECTURE.md`, the exclusive output section and invariant 12.
- `infrastructure/output_devices.py`, the measurements of 2026-09-14.
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

Windows 11 on the reference machine, measured. macOS and Linux (the Flatpak)
are targets whose device lists have not been measured; OQ-O2 and OQ-O3.

### 2.4 Constraints

- **Taking PortAudio's list again closes every stream it has open.** Nothing
  that keeps the output list current may do it while music plays; it is done
  on the way into opening a stream, exactly as a move of the default already
  is.
- **Identity by endpoint, display by name.** The choice is stored by endpoint
  identity because names repeat; the name is what the listener reads.
- **Nothing here reaches the network.** Invariant 12 stands unchanged.

### 2.5 Assumptions

| # | Assumption | Owner | Confirm by |
|---|---|---|---|
| A-O01 | Qt's output list on Windows is the list Windows' Sound settings show. Measured on one machine only. | Claude | Build, on the reference machine |
| A-O02 | `audioOutputsChanged` fires when a Bluetooth output connects or disconnects. Observed on 2026-09-19 in the live test with the Px7 S3: the list followed the headphones on and off. The timed five-cycle probe of OQ-O4 was not run. | Claude, with Oliver's Bathys | OQ-O4 |

## 3. Requirements

### 3.1 Functional

---

**FR-O01 The button sits after the sound group's rule**

Priority: Must

Requirement: The bottom strip shall place the choose-device button, drawn from
`assets/choose-audio-device.png`, immediately after the rule in the sound group
and immediately before the exclusive switch.

Rationale: Asked for by Oliver on 2026-09-18. The device is a question about
the stream, like exclusive output and the equalizer beside it, so it joins
them after the rule rather than volume and mute before it.

Acceptance: Given the window open, when the sound group is read left to right,
then it holds volume, mute, the rule, choose device, exclusive, equalizer.

Verified by: `tests/ui/test_output_button.py::test_the_button_sits_after_the_rule_before_exclusive`

---

**FR-O02 A press opens the output list**

Priority: Must

Requirement: When the choose-device button is pressed, the bottom strip shall
open the output list as a vertical list anchored to the button.

Rationale: The volume button already opens its slider this way, so the strip
keeps one way of opening something from a button.

Acceptance: Given the window open, when the button is pressed, then a vertical
list appears against it naming System default and every output device.

Verified by: `tests/ui/test_output_button.py::test_a_press_opens_the_list`

---

**FR-O03 System default is listed first**

Priority: Must

Requirement: The output list shall name System default as its first entry,
above every output device.

Rationale: Decision 1 of 2026-09-18. It is today's behaviour, so a listener
who never opens the list loses nothing.

Acceptance: Given any set of output devices, when the list is shown, then its
first entry is System default.

Verified by: `tests/domain/test_output_choice.py::test_system_default_leads_the_list`

---

**FR-O04 Only outputs are listed**

Priority: Must

Requirement: The output list shall name only devices the operating system
reports as able to play sound.

Rationale: Asked for by Oliver on 2026-09-18: outputs only, not inputs. A
microphone in a list of places to send music is a choice that cannot work.

Acceptance: Given the reference machine with the Focusrite inputs, the OBSBOT
microphone and Stereo Mix present, when the list is shown, then none of them
appears in it.

Verified by: `tests/infrastructure/test_output_list.py::test_the_list_is_read_from_the_outputs_alone`, plus a demonstration on the reference machine.

---

**FR-O05 Names are the system's, told apart where they repeat**

Priority: Must

Requirement: The output list shall show each output device under the name the
operating system gives it; where two or more share a name, it shall add
` (2)`, ` (3)` and so on to the second and later, in the order the system
lists them.

Rationale: Decision 5 of 2026-09-18. Measured: two outputs here are both
`U13ZA (NVIDIA High Definition Audio)`. Two identical lines are two choices a
listener cannot tell apart.

Acceptance: Given two devices named `U13ZA (NVIDIA High Definition Audio)`,
when the list is shown, then they read `U13ZA (NVIDIA High Definition Audio)`
and `U13ZA (NVIDIA High Definition Audio) (2)`.

Verified by: `tests/domain/test_output_choice.py::test_a_repeated_name_is_numbered_in_listed_order`

---

**FR-O06 The device in use is marked**

Priority: Must

Requirement: The output list shall mark the entry the music is going to: the
chosen device while it is present and opened, else System default (rewritten
by Amendment 5).

Rationale: A list of places with nothing saying which is in force answers the
wrong half of the question. A tick on a device that is not playing answers it
wrongly.

Acceptance: Given the Focusrite chosen, when the list is shown, then the
Focusrite entry alone is marked. Given the Focusrite chosen and refusing, when
the list is shown, then System default alone is marked.

Verified by: `tests/ui/test_output_button.py::test_the_choice_is_marked`, `tests/domain/test_output_choice.py::test_a_refused_choice_leaves_the_tick_on_the_system_default`, `tests/application/test_choosing_an_output.py::TestARefusal::test_the_tick_is_on_the_default_it_plays_on`

---

**FR-O07 Choosing moves the music at once**

Priority: Must

Requirement: When an entry is chosen from the output list, the transport shall
open the track in hand again on that device from the position it had reached,
leaving a paused track paused.

Rationale: Decision 3 of 2026-09-18. The same reasoning as the exclusive
switch: a choice whose effect cannot be heard until later reads as a choice
that did nothing. It is a gap rather than a restart.

Acceptance: Given a track playing at 1:30 on the speakers, when the Focusrite
is chosen, then the track goes on from 1:30 on the Focusrite; given a track
paused at 1:30, then it is still paused at 1:30, now on the Focusrite.

Verified by: `tests/application/test_choosing_an_output.py::test_choosing_reopens_in_place`, `tests/application/test_choosing_an_output.py::test_a_paused_track_stays_paused`

---

**FR-O08 A device that will not open is said, not left silent**

Priority: Must

Requirement: If the chosen device refuses the stream, then the transport shall
open the track on the system default instead; the window shall say on the
status line which device refused and its reason.

Rationale: The unwanted sibling of FR-O07. Another application holding the
device exclusively is the ordinary way it happens. Silence would read as a
press that missed.

Acceptance: Given the Focusrite held exclusively by another application, when
it is chosen, then the music plays on the system default and the status line
names the Focusrite with the reason the device gave.

Verified by: `tests/application/test_choosing_an_output.py::test_a_refusal_falls_back_to_the_default`, `tests/ui/test_output_messages.py::test_a_refusal_is_said`

---

**FR-O09 The choice is remembered**

Priority: Must

Requirement: The window shall store the choice by endpoint identity when it is
made; at launch, the window shall restore it.

Rationale: Decision 2 of 2026-09-18. Every other setting on the strip outlasts
a session. Stored by identity because names repeat (FR-O05).

Acceptance: Given the Focusrite chosen, when Stellody is closed and started
again, then the Focusrite is the choice and the first track plays on it.

Verified by: `tests/ui/test_output_settings.py::test_the_choice_outlasts_a_launch`

---

**FR-O10 A remembered device missing at launch**

Priority: Must

Requirement: If the remembered device is not listed at launch, then the
transport shall play on the system default; the window shall keep the choice
and say once on the status line that the device is missing.

Rationale: Decision 2 of 2026-09-18. Headphones switched off overnight are not
a reason to forget that the listener wants them.

Acceptance: Given the Bathys remembered and switched off, when Stellody starts
and a track plays, then it plays on the system default, the status line says
the Bathys is not connected and the list still names the Bathys, with System
default ticked (Amendment 5).

Verified by: `tests/application/test_choosing_an_output.py::test_a_missing_choice_plays_on_the_default`, `tests/ui/test_output_messages.py::test_a_missing_device_is_said_once`

---

**FR-O11 The chosen device disappearing while playing**

Priority: Must

Requirement: If the device in use disappears from the output list while a
track is loaded, then the transport shall pause the track where it was; when
play is next pressed, the transport shall open it on the system default from
that place. The window shall say on the status line that the device
disconnected.

Rationale: Decision 4 of 2026-09-18, brought under Oliver's rule of
2026-09-14 by his ruling on OQ-O5 (Amendment 4): music never goes to the
speakers without a press. A Bluetooth pair walking out of range is the
ordinary case.

Acceptance: Given a track playing at 2:00 on the Bathys, when the Bathys
disconnects, then the track pauses at about 2:00 and the status line says the
Bathys disconnected; when play is pressed, then it goes on from there on the
system default.

Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`, `tests/ui/test_output_messages.py::test_a_disconnect_while_playing_is_said`, `tests/ui/test_output_messages.py::test_a_disconnect_with_nothing_playing_is_said`

---

**FR-O12 The chosen device returning**

Priority: Must

Requirement: While the chosen device is missing, when it appears in the output
list, the transport shall open the track in hand again on it from the position
it had reached, leaving a paused track paused.

Rationale: The other half of FR-O10 and FR-O11. The choice was kept precisely
so it could come back; a listener who puts their headphones back on expects
the music in them. A track paused by the loss stays paused (Amendment 4), so
nothing starts without a press.

Acceptance: Given the Bathys chosen but disconnected while a track plays on the
speakers, when the Bathys connects, then the track moves to the Bathys from
where it had reached and plays on; given a track paused when the Bathys
disconnected, when the Bathys connects, then the track is on the Bathys and
still paused.

Verified by: `tests/application/test_choosing_an_output.py::TestWhatALossDoesToTheTrackInHand`

---

**FR-O13 The list is kept current**

Priority: Must

Requirement: When the operating system reports a change to its output
devices, the window shall take the output list again, including while the list
is open.

Rationale: Asked for by Oliver on 2026-09-18: connecting the Bathys while
Stellody runs should offer it with no relaunch. Event driven, since Qt already
reports the change (section 1.3); a poll would be a second mechanism for
something one already answers. A-O02 is the measurement that decides whether
Bluetooth is among what it reports.

Acceptance: Given Stellody running with the list open, when the Bathys
connects, then the Bathys appears in the list; when it disconnects, then it
leaves the list unless it is the choice (FR-O14).

Verified by: `tests/ui/test_output_list_follows.py::test_a_new_device_appears`, `tests/ui/test_output_list_follows.py::test_a_removed_device_leaves`, plus a demonstration with the Bathys on the reference machine.

---

**FR-O14 A missing choice stays in the list**

Priority: Must

Requirement: While the chosen device is missing, the output list shall still
name it, marked as not connected and not ticked; System default carries the
tick (rewritten by Amendment 5).

Rationale: Without it, the choice the window kept (FR-O10) would be invisible;
a listener could not see what will happen when the device returns.

Acceptance: Given the Bathys chosen and disconnected, when the list is shown,
then it names the Bathys as not connected, with System default ticked; when
the Bathys returns, the tick goes back to it.

Verified by: `tests/domain/test_output_choice.py::test_a_missing_choice_is_still_listed`, `tests/domain/test_output_choice.py::test_a_missing_choice_leaves_the_tick_on_the_system_default`, `tests/ui/test_output_list_follows.py::test_the_tick_moves_to_where_the_music_goes`, `tests/ui/test_output_list_follows.py::test_the_tick_goes_back_with_the_device`

---

**FR-O15 System default keeps following the system**

Priority: Must

Requirement: While System default is the choice, when the operating system
moves its default output, the transport shall send the next stream it opens to
the new default. Where the previous default is still listed, the transport
shall also move the track in hand to the new default where it was, a playing
track playing on and a paused one staying paused; where the previous default
is gone, the track in hand is paused (FR-O11). Rewritten by Amendment 5.

Rationale: Today's behaviour, held rather than rebuilt, so the new choice
cannot quietly break it. Headphones switched on are a request to hear the
music there; the rule of 2026-09-14 paused it instead, which the live test of
2026-09-19 showed to be the wrong answer for an arrival.

Acceptance: Given System default chosen, when Windows moves its default to the
Focusrite, then the next track plays on the Focusrite. Given a track playing
on the speakers, when the Px7 connects and becomes the default, then the track
plays on through the Px7 from where it was, with no press.

Verified by: `tests/infrastructure/test_output_devices.py`, `tests/application/test_choosing_an_output.py::test_the_default_is_followed`, `tests/application/test_a_device_arriving.py`, `tests/ui/test_output_composition.py::test_whether_the_default_left_reaches_the_transport`

---

**FR-O16 Exclusive output answers for the device in use**

Priority: Must

Requirement: The window shall judge whether exclusive output is offered
against the device in use.

Rationale: The rates a device takes exclusively differ by device. An offer
judged against the system default while the music goes elsewhere would be a
promise about the wrong device.

Acceptance: Given the Focusrite chosen, when the window asks which rates are
taken exclusively, then the question is put to the Focusrite.

Verified by: `tests/ui/test_exclusive_follows_the_device.py` (extended)

---

**FR-O17 The Sound menu holds the same list**

Priority: Must

Requirement: The Sound menu shall hold an Output device submenu, beside
Exclusive output, naming the same entries in the same order with the same
mark.

Rationale: Decision 6 of 2026-09-18. Every control on the strip is mirrored in
the menus, which is also how a keyboard reaches it without the ring.

Acceptance: Given the Focusrite chosen, when the Sound menu is opened, then
its Output device submenu names System default and every output device, the
Focusrite marked.

Verified by: `tests/ui/test_output_menu.py::test_the_menu_mirrors_the_list`

---

**FR-O18 The keyboard reaches it**

Priority: Must

Requirement: The focus ring shall stop on the choose-device button in its drawn
place; while the output list is open, the arrow keys shall move along it, Enter
shall choose and Escape shall close it with the choice unchanged.

Rationale: The house keyboard model, applied to one more control. A list only
a mouse can use is not reachable.

Acceptance: Given focus on mute, when Tab is pressed, then focus is on
the choose-device button; given the list open, when Down then Enter are
pressed, then the first output device is chosen; given the list open, when
Escape is pressed, then nothing changes.

Verified by: `tests/ui/test_output_button.py::test_the_ring_stops_on_it_straight_after_mute`, `tests/ui/test_output_button.py::test_the_list_is_keyboard_driven`, `tests/ui/test_output_button.py::test_escape_leaves_the_choice_alone`

---

**FR-O19 The tooltip names the press**

Priority: Must

Requirement: The choose-device button shall carry the tooltip "Choose the
output device".

Rationale: The strip's rule: a tooltip names what a press would do.

Acceptance: Given the window open, when the button is hovered, then its
tooltip reads "Choose the output device".

Verified by: `tests/ui/test_output_button.py::test_the_tooltip_names_the_press`

### 3.2 Non-functional

**NFR-O-PERF-001 A device change reaches the list in time.** When an output
device connects or disconnects, the output list shall reflect it within 2
seconds of the operating system's own Sound settings showing the change,
measured on the reference machine by connecting and disconnecting the Bathys
five times with the list open. Priority: Must.

**NFR-O-PERF-002 Keeping the list current never interrupts the music.** While
a track plays, a change to the device list shall not take PortAudio's list
again, unless the change is one FR-O11 or FR-O12 acts on. Verified by
`tests/infrastructure/test_output_list.py::test_a_list_change_leaves_the_stream_alone`,
which counts calls to the rescan. Priority: Must.

**NFR-O-PRIV-001 Nothing leaves the machine.** Device names and identities
are held in Stellody's own settings and log alone. Held by the existing
invariant 12 test, which this change must leave green. Priority: Must.

**NFR-O-MAINT-001 The house limits hold.** Domain and application keep 100%
branch coverage; every module stays at or below the 400 line cap and out of
the danger band. `ui/bottom_tray.py` is 359 lines at baseline, so the button
belongs inside `SoundControls` rather than beside it. Verified by the existing
structural suite. Priority: Must.

**NFR-O-PORT-001 Platforms.** The button and the list shall be present on
Windows, macOS and Linux alike. Windows is verified on the reference machine;
macOS and Linux are verified by Oliver choosing each listed device on a real
machine of that kind and hearing it play there (OQ-O2, OQ-O3). A listed
device that cannot be matched to one PortAudio can open is a refusal, so
FR-O08 applies: the music falls back to the system default and the status line
names the device. Priority: Must.

### 3.3 Data

One new setting beside the others in `ui/settings_keys.py`:

| Setting | Holds | Empty means |
|---|---|---|
| `output_device` | The endpoint identity of the chosen device | System default |
| `output_device_name` | The name the device had when it was chosen | Nothing; used only to name a missing device in FR-O10 |

The name is stored as well as the identity because a missing device cannot be
asked its name; without it FR-O10 could only say "a device is missing".

## 4. Prioritisation

Every functional requirement is a Must: the feature is small; each one is a
case the feature cannot ship without. Won't this time is the out-of-scope list in section 1.4.

## 5. Open questions

| # | Question | Owner | Probe | Status |
|---|---|---|---|---|
| OQ-O1 | Two outputs share the name `U13ZA (NVIDIA High Definition Audio)` and PortAudio cannot state endpoint identity. Which PortAudio device is which? | Claude | Played a tone through each PortAudio WASAPI output while reading every endpoint's own peak meter. | Answered 2026-09-18; Amendment 2 |
| OQ-O2 | On Linux, Qt lists PulseAudio or PipeWire outputs while PortAudio may see ALSA devices under other names. Can the two be matched, inside the Flatpak? | Oliver, on the Linux machine | Run the device probe from this session inside the Flatpak build; compare the two lists. | Open |
| OQ-O3 | On macOS, do Qt's names match PortAudio's CoreAudio names? | Oliver, on the Mac | The same probe on the Mac. | Open |
| OQ-O5 | FR-O11 keeps the music playing on the system default when the chosen device disappears; FR-O12 moves it back when the device returns. Oliver ruled on 2026-09-14 (`application/output_following.py`) that a move of the system output PAUSES the music rather than carrying it somewhere without warning, after a track went on through the speakers once headphones connected. Which rule governs the chosen device leaving and returning? | Oliver | A ruling | Answered 2026-09-18; Amendment 4 |
| OQ-O4 | Does Qt report a Bluetooth output connecting and disconnecting on Windows? (A-O02) | Claude, with Oliver's Bathys | Log every `audioOutputsChanged` with a timestamp while the Bathys connects and disconnects five times. If it misses any, a poll of `QMediaDevices.audioOutputs()` once a second replaces the signal; the poll never touches PortAudio. | Observed working with the Px7 S3 on 2026-09-19; the timed probe is still open |

## 6. The build order this implies

Inside out, as every feature here is built.

1. **Domain**: the output list as a value (System default first, numbered
   repeats, a missing choice kept and marked), plus the rule choosing the
   device in use from the choice and the devices present. Pure, with no Qt.
2. **Application**: the transport taking a choice, reopening in place on a
   change, falling back on a refusal or a disappearance, moving back on a
   return. Driven by fakes; FR-O07 to FR-O12 all run with no device.
3. **Infrastructure**: reading Qt's output list; matching an entry to a
   PortAudio device (OQ-O1 first); the engine opening each stream on the
   device it is handed rather than on one fixed at construction.
4. **UI**: the button, the list, the menu mirror, the messages, the settings.

The diagnostic that says the foundation is sound: choosing a device,
losing it and getting it back must each be driven from a test against fakes
before the button exists.

Then the documents: `ARCHITECTURE.md` gains the choice beside exclusive
output; the README's feature list and the site gain one line each.

## 7. Amendments

Numbered, each with its reason, as the baseline asks.

**Amendment 1, 2026-09-18: the feature is present on every platform.**
NFR-O-PORT-001 first hid the button on macOS and Linux until their lists were
proved. Oliver ruled it out the same day: a feature that is not there cannot
be proved to work or to fail. It ships everywhere; a device that cannot be
opened falls to FR-O08, which already says so rather than going silent.

**Amendment 2, 2026-09-18: OQ-O1 answered by measurement.** A probe listed
Windows' render endpoints through `IMMDeviceEnumerator::EnumAudioEndpoints`
(render, active) with their identities, then played a quiet tone through each
PortAudio WASAPI output in turn while reading every endpoint's
`IAudioMeterInformation` peak. Each tone moved exactly one endpoint's meter at
the tone's level, beside the default speakers, which were already carrying
other sound throughout:

| PortAudio | Endpoint moved | Identity |
|---|---|---|
| 22 `U13ZA` | Windows 0 | `{099b6e7b-...}` |
| 23 `U13NA` | Windows 1 | `{3a634f65-...}` |
| 24 Realtek Digital Output | Windows 2 | `{43c814e1-...}` |
| 25 Focusrite | Windows 3 | `{625c7c32-...}` |
| 26 Realtek Speakers | Windows 4 | `{632d18d4-...}` |
| 27 `U13ZA` | Windows 5 | `{aa712c5b-...}` |
| 28 LG ULTRAGEAR | Windows 6 | `{fdff97af-...}` |

PortAudio's WASAPI outputs come in Windows' enumeration order, one for one,
so the two `U13ZA` monitors are told apart by position. Qt lists the same
seven in a different order (the default first), so Qt's order must never be
used to match. What follows for the build:

- On Windows, the list is read from Windows' own enumeration, which gives the
  identity and the order together. The n-th output of a name there is the n-th
  PortAudio WASAPI output of that name.
- FR-O05's "the order the system lists them" means that enumeration order.
- The one-for-one correspondence is measured on one machine rather than read
  from PortAudio's source. So the match is checked each time a stream opens:
  if PortAudio's WASAPI output names, in order, differ from Windows'
  enumeration, then a device whose name repeats is not guessed at; it is a
  refusal under FR-O08. A device whose name is unique is matched by name
  whatever the order.

**Amendment 3, 2026-09-18: three rules the application layer had to settle.**
None changes a requirement's intent; each states a case the text left open.

- **A named device ignores the default moving.** FR-O15 says what the default
  moving does while it is the choice. While music plays on a device the
  listener named, the default moving is nothing to it, so the pause
  `application/output_following.py` makes for a move is not made. Music on the
  default because the chosen device is missing does follow it.
- **A refusal keeps the choice and is not retried on every track.** FR-O08
  falls back to the default. The choice stays as it was, marked in the list;
  the refused device is not asked again until the listener chooses it again,
  else it leaves the list and returns. Otherwise every later track would open
  into the same refusal with the same message.
- **A choice made with nothing loaded opens nothing.** FR-O07 moves the track
  in hand; a queue left stopped is not a track in hand, so it is not opened
  just to be moved.

**Amendment 4, 2026-09-18: OQ-O5 answered.** Oliver ruled that his rule of
2026-09-14 governs the chosen device leaving and returning: music never goes
to the speakers without a press. FR-O11 was rewritten in place: a loss pauses
the track where it was, the same pause a move of the system output makes;
play then opens it on the default. FR-O12 gained that a paused track stays
paused when the device returns; a playing one moves back and plays on.

**Amendment 5, 2026-09-19: three rulings from the live test.** Oliver tested
the installed build with his Px7 S3 headphones. FR-O06, FR-O14 and FR-O15 were
rewritten in place. Whether the previous default is still listed is read from
Qt's own list at the moment the default moves
(`infrastructure/output_devices.py`), so a default changed by hand in Windows,
both devices still present, carries the music on as an arrival does.

- **The tick follows the device in use.** FR-O06 and FR-O14 change: while the
  chosen device is missing or refused, System default carries the tick; the
  chosen device stays listed as not connected, unticked, still the one the
  music goes back to (FR-O12 unchanged).
- **A device arriving carries the music on.** FR-O15 changes: while System
  default is the choice, when the system's default moves because a device
  arrived (the previous default still listed), the transport shall move the
  track in hand to it where it was and keep it playing; a paused track stays
  paused. This replaces the rule of 2026-09-14 for that case alone.
- **A device leaving still pauses.** Where the previous default is gone, as
  where the stream was interrupted, the pause stands: music never goes to the speakers
  without a press (FR-O11, Amendment 4).
- **Nothing switches to a device never chosen.** Only the listener's own choice
  is ever returned to automatically.
