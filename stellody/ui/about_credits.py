"""What this application is built out of, what it asks and what it is not.

Split out of `dialogs.py` when that file reached the 381 to 399 danger band on
gaining the shop statement. It is a cohesive concern rather than an arbitrary
slice: everything here is a CLAIM the About screen makes about the application's
obligations, as opposed to the dialog machinery that draws it.

Three kinds of claim, kept apart because the obligations differ. A library is
something this is built out of and wants its licence honoured. A service is
something this ASKS, run by other people at their own cost; it wants its name
said and its rate respected. A shop is neither: nothing is asked of one and
nothing is owed by one, which is exactly why that has to be said out loud.
"""

from __future__ import annotations

from stellody.shared.version import APP_NAME

CREDITS = (
    ("PySide6 (Qt for Python)", "LGPL-3.0", "the user interface"),
    ("Python", "PSF", "the language and standard library"),
    ("mutagen", "GPL-2.0-or-later", "reading tags"),
    ("soundfile and libsndfile", "BSD-3-Clause and LGPL-2.1", "decoding audio"),
    ("sounddevice and PortAudio", "MIT", "audio output"),
    ("NumPy", "BSD-3-Clause", "sample buffers"),
    ("PyAV", "BSD-3-Clause", "decoding M4A and the video that comes with an album"),
    (
        "FFmpeg, bundled through PyAV",
        "LGPL-3.0-or-later, with libx264 and libx265 under GPL-2.0-or-later",
        "the codecs PyAV reaches",
    ),
    ("pytest, pytest-cov and pytest-qt", "MIT", "the test suite"),
    ("black, flake8 and ruff", "MIT", "formatting and linting"),
    ("Pillow", "HPND", "building the icon set"),
    ("Nuitka", "AGPL-3.0, with its runtime library exception", "compiling a build"),
    ("zstandard and ordered-set", "BSD-3-Clause and MIT", "which that build uses"),
)

# A different kind of debt from the list above. Those are libraries this
# application is built out of; these are public services it ASKS things of,
# run by other people at their own cost, under terms of their own. They are
# credited separately because the obligation is a different one: a library
# wants its licence honoured, a service wants its name said and its rate
# respected.
#
# The MusicBrainz terms are quoted from its own data licence page, read on
# 2026-09-07: core data is CC0, while supplementary data, which is what the
# genres asked for here are, is CC BY-NC-SA 3.0 and asks for credit by name.
# That is the whole reason this section exists rather than a line in the list
# above. No licence is stated for the other two: their pages do not give one
# plainly, so nothing is claimed. A licence invented for a credits box is
# worse than no licence at all.
SOURCES = (
    (
        "MusicBrainz",
        "core data CC0, genres CC BY-NC-SA 3.0",
        "which artist a name means, what they released and what they play",
    ),
    (
        "ListenBrainz",
        "a MetaBrainz project",
        "which artists resemble the ones you already hold",
    ),
    (
        "Cover Art Archive",
        "a MusicBrainz and Internet Archive project",
        "album artwork, where you ask for it",
    ),
)

# Said once and read by both screens somebody could look for it on, since a
# statement about money written twice is two statements the day one is edited.
# The About screen is where a claim about what this application IS belongs; the
# guide reads it from here as well, so somebody meeting the shops for the first
# time has it in front of them rather than having to go looking.
NO_SHOP_AFFILIATION = (
    f"{APP_NAME} has no affiliation with any shop it links to, no arrangement "
    "with one and no interest in whether you buy anything. Choosing a shop "
    "hands your browser that shop's own public search address and nothing "
    "else: no account, no referral, no affiliate tag and nothing whatever "
    "about you. What happens after that is between you and the shop, under "
    "their terms rather than these. The shop list is an ordinary file you can "
    "edit, so the shops offered are the ones you keep in it."
)


def credits_html() -> str:
    """The open source credits as list items."""
    return "".join(
        f"<li><b>{name}</b> - {licence} ({purpose}).</li>"
        for name, licence, purpose in CREDITS
    )


def sources_html() -> str:
    """The services asked about things, as list items."""
    return "".join(
        f"<li><b>{name}</b> - {terms} ({purpose}).</li>"
        for name, terms, purpose in SOURCES
    )
