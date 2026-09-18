"""The output list and the choice behind it, as `OUTPUTS.md` states them.

Nothing here asks a device anything. The list a listener reads, which device
the music goes to and which entry in an opener's own list is meant are all
rules over names and identities, so they are proved on plain values.
"""

from __future__ import annotations

from stellody.domain.outputs import (
    SYSTEM_DEFAULT,
    OutputChoice,
    OutputDevice,
    device_in_use,
    opener_position,
    output_list,
)

# The reference machine's seven outputs, in Windows' own enumeration order,
# measured on 2026-09-18 (OUTPUTS.md Amendment 2). Identities are shortened.
MONITOR = "U13ZA (NVIDIA High Definition Audio)"
FIRST_MONITOR = OutputDevice(identity="{099b6e7b}", name=MONITOR)
SMALL_MONITOR = OutputDevice(identity="{3a634f65}", name="U13NA (NVIDIA)")
DIGITAL = OutputDevice(identity="{43c814e1}", name="Realtek Digital Output")
FOCUSRITE = OutputDevice(identity="{625c7c32}", name="Speakers (Focusrite)")
SPEAKERS = OutputDevice(identity="{632d18d4}", name="Speakers (Realtek)")
SECOND_MONITOR = OutputDevice(identity="{aa712c5b}", name=MONITOR)
ULTRAGEAR = OutputDevice(identity="{fdff97af}", name="LG ULTRAGEAR")
REFERENCE = (
    FIRST_MONITOR,
    SMALL_MONITOR,
    DIGITAL,
    FOCUSRITE,
    SPEAKERS,
    SECOND_MONITOR,
    ULTRAGEAR,
)
BATHYS = OutputDevice(identity="{bathys}", name="Headphones (Focal Bathys)")


def chose(device: OutputDevice) -> OutputChoice:
    """The choice a listener makes by picking this device."""
    return OutputChoice(identity=device.identity, name=device.name)


def test_system_default_leads_the_list() -> None:
    """FR-O03."""
    entries = output_list(REFERENCE, chose(FOCUSRITE))

    assert entries[0].choice == SYSTEM_DEFAULT
    assert entries[0].choice.follows_default


def test_system_default_is_listed_with_no_devices_at_all() -> None:
    """FR-O03, at the empty end: the list is never empty."""
    entries = output_list((), SYSTEM_DEFAULT)

    assert tuple(entry.choice for entry in entries) == (SYSTEM_DEFAULT,)


def test_every_device_follows_in_listed_order() -> None:
    """FR-O05: the system's names, in the system's order, after the default."""
    entries = output_list(REFERENCE, SYSTEM_DEFAULT)

    assert tuple(entry.choice.identity for entry in entries[1:]) == tuple(
        device.identity for device in REFERENCE
    )


def test_a_repeated_name_is_numbered_in_listed_order() -> None:
    """FR-O05, measured: two monitors here share one name."""
    labels = {
        entry.choice.identity: entry.label
        for entry in output_list(REFERENCE, SYSTEM_DEFAULT)[1:]
    }

    assert labels[FIRST_MONITOR.identity] == MONITOR
    assert labels[SECOND_MONITOR.identity] == f"{MONITOR} (2)"
    assert labels[FOCUSRITE.identity] == FOCUSRITE.name


def test_a_third_namesake_is_numbered_three() -> None:
    """FR-O05: the count runs on, whatever lies between the namesakes."""
    third = OutputDevice(identity="{third}", name=MONITOR)
    entries = output_list((*REFERENCE, third), SYSTEM_DEFAULT)

    assert entries[-1].label == f"{MONITOR} (3)"


def test_choosing_an_entry_keeps_the_systems_own_name() -> None:
    """FR-O09: the name stored is the system's, never the numbered label."""
    second = output_list(REFERENCE, SYSTEM_DEFAULT)[6]

    assert second.choice == chose(SECOND_MONITOR)


def test_the_choice_alone_is_marked() -> None:
    """FR-O06."""
    entries = output_list(REFERENCE, chose(FOCUSRITE))

    assert tuple(entry.choice for entry in entries if entry.chosen) == (
        chose(FOCUSRITE),
    )


def test_system_default_is_marked_while_it_is_the_choice() -> None:
    """FR-O06, for the entry every listener starts on."""
    entries = output_list(REFERENCE, SYSTEM_DEFAULT)

    assert tuple(entry.chosen for entry in entries) == (True,) + (False,) * len(
        REFERENCE
    )


def test_every_present_device_is_connected() -> None:
    """FR-O14's other side: only a missing choice is marked absent."""
    entries = output_list(REFERENCE, chose(FOCUSRITE))

    assert all(entry.connected for entry in entries)


def test_a_missing_choice_is_still_listed() -> None:
    """FR-O14: last, marked as the choice and as not connected."""
    entries = output_list(REFERENCE, chose(BATHYS))

    assert entries[-1].choice == chose(BATHYS)
    assert entries[-1].label == BATHYS.name
    assert entries[-1].chosen
    assert not entries[-1].connected
    assert len(entries) == len(REFERENCE) + 2


def test_the_default_goes_to_the_system_default() -> None:
    """FR-O15: no device named means the opener's own default."""
    assert device_in_use(REFERENCE, SYSTEM_DEFAULT) is None


def test_a_present_choice_is_the_device_in_use() -> None:
    """FR-O07."""
    assert device_in_use(REFERENCE, chose(SECOND_MONITOR)) == SECOND_MONITOR


def test_a_missing_choice_plays_on_the_system_default() -> None:
    """FR-O10 and FR-O11: absent means the default, with the choice kept."""
    assert device_in_use(REFERENCE, chose(BATHYS)) is None


def test_a_returning_choice_is_in_use_again() -> None:
    """FR-O12: the same choice finds the device once it is listed again."""
    assert device_in_use((*REFERENCE, BATHYS), chose(BATHYS)) == BATHYS


NAMES = tuple(device.name for device in REFERENCE)


def test_a_repeated_name_is_found_by_position_when_the_orders_agree() -> None:
    """Amendment 2: the n-th of a name is the opener's n-th of that name."""
    assert opener_position(REFERENCE, FIRST_MONITOR, NAMES) == 0
    assert opener_position(REFERENCE, SECOND_MONITOR, NAMES) == len(NAMES) - 2


def test_a_repeated_name_is_refused_when_the_orders_disagree() -> None:
    """Amendment 2: a guess between namesakes is never made."""
    shuffled = NAMES[1:] + NAMES[:1]

    assert opener_position(REFERENCE, SECOND_MONITOR, shuffled) is None


def test_a_unique_name_is_found_whatever_the_order() -> None:
    """Amendment 2: a name nobody shares needs no order to be matched."""
    shuffled = tuple(reversed(NAMES))

    assert opener_position(REFERENCE, FOCUSRITE, shuffled) == shuffled.index(
        FOCUSRITE.name
    )


def test_a_name_the_opener_lacks_is_not_found() -> None:
    """FR-O08 starts here: a device the opener cannot see is a refusal."""
    assert opener_position((*REFERENCE, BATHYS), BATHYS, NAMES) is None


def test_a_device_the_list_no_longer_holds_is_not_found() -> None:
    """The list may be read again between choosing and opening."""
    assert opener_position(REFERENCE[:-2], SECOND_MONITOR, NAMES) is None


def test_a_unique_name_the_opener_repeats_needs_the_orders_to_agree() -> None:
    """One listed device and two opener entries is still a choice to guess."""
    doubled = (*NAMES, FOCUSRITE.name)

    assert opener_position(REFERENCE, FOCUSRITE, doubled) is None
