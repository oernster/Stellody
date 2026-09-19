"""Which output device the music goes to, stated without reference to any.

`OUTPUTS.md` is the specification. Three rules live here because none of them
needs a device to be true: the list a listener reads (the system default first,
repeated names told apart, a missing choice kept in sight); which device a
choice sends the music to; which entry in an opener's own list a device is.

Identity and name are held apart throughout. Windows gives two monitors on the
reference machine one name, so a choice is kept by identity; the name is what
a listener reads and what an opener that knows no identities is matched by.
"""

from __future__ import annotations

from dataclasses import dataclass

# Added to the second and later devices sharing one name, counting from two:
# the first keeps the system's name untouched. FR-O05.
NAMESAKE_LABEL = "{name} ({ordinal})"
FIRST_NAMESAKE_ORDINAL = 1


@dataclass(frozen=True, slots=True)
class OutputDevice:
    """A device the system lists as able to play sound."""

    identity: str
    name: str


@dataclass(frozen=True, slots=True)
class OutputChoice:
    """What a listener last chose: one device, else the system default.

    The name is the system's own at the moment of choosing, kept so a device
    that has gone missing can still be named (FR-O10). An empty identity is
    the system default.
    """

    identity: str = ""
    name: str = ""

    @property
    def follows_default(self) -> bool:
        """True while the music goes wherever the system's default goes."""
        return not self.identity


SYSTEM_DEFAULT = OutputChoice()


@dataclass(frozen=True, slots=True)
class OutputEntry:
    """One line of the output list.

    `label` is empty on the system default's line, whose words belong to the
    window; every other line reads the system's name, numbered where repeated.
    `chosen` marks the line the music is going to, which is not the choice
    while the chosen device is missing or refused (Amendment 5).
    """

    choice: OutputChoice
    label: str
    chosen: bool
    connected: bool


def output_list(
    devices: tuple[OutputDevice, ...],
    choice: OutputChoice,
    in_use: OutputDevice | None,
) -> tuple[OutputEntry, ...]:
    """The list as a listener reads it: FR-O03, FR-O05, FR-O06 and FR-O14.

    The tick follows `in_use`, the device the music is going to; None is the
    system default. A chosen device that is missing stays listed, unticked,
    as the one the music goes back to (Amendment 5, FR-O12).
    """
    entries = [
        OutputEntry(
            choice=SYSTEM_DEFAULT,
            label="",
            chosen=in_use is None,
            connected=True,
        )
    ]
    seen: dict[str, int] = {}
    for device in devices:
        ordinal = seen.get(device.name, 0) + 1
        seen[device.name] = ordinal
        picked = OutputChoice(identity=device.identity, name=device.name)
        entries.append(
            OutputEntry(
                choice=picked,
                label=_labelled(device.name, ordinal),
                chosen=device == in_use,
                connected=True,
            )
        )
    if not choice.follows_default and device_in_use(devices, choice) is None:
        entries.append(
            OutputEntry(choice=choice, label=choice.name, chosen=False, connected=False)
        )
    return tuple(entries)


def device_in_use(
    devices: tuple[OutputDevice, ...], choice: OutputChoice
) -> OutputDevice | None:
    """The device a choice sends the music to; None means the system default.

    A chosen device that is not listed plays on the default while the choice
    itself is kept, so the same choice finds the device again once it is back
    (FR-O10, FR-O11, FR-O12).
    """
    return next(
        (device for device in devices if device.identity == choice.identity), None
    )


def opener_position(
    devices: tuple[OutputDevice, ...],
    device: OutputDevice,
    opener_names: tuple[str, ...],
) -> int | None:
    """Where `device` sits in an opener's own list of names; None if unsure.

    For an opener that knows names alone, as PortAudio does here (OUTPUTS.md
    section 1.3). Measured on 2026-09-18, its WASAPI outputs arrive in the
    system's own order (Amendment 2), so the n-th device of a name is its
    n-th entry of that name. That was measured on one machine, so it is relied
    on only while the two lists agree name for name; otherwise a name more than
    one device carries is not guessed at. A name only one carries on each side
    needs no order at all.
    """
    candidates = [
        position for position, name in enumerate(opener_names) if name == device.name
    ]
    namesakes = [listed for listed in devices if listed.name == device.name]
    if len(candidates) == 1 and namesakes == [device]:
        return candidates[0]
    if device not in namesakes:
        return None
    if tuple(listed.name for listed in devices) != opener_names:
        return None
    return candidates[namesakes.index(device)]


def _labelled(name: str, ordinal: int) -> str:
    """The system's name, numbered from the second device that carries it."""
    if ordinal == FIRST_NAMESAKE_ORDINAL:
        return name
    return NAMESAKE_LABEL.format(name=name, ordinal=ordinal)
