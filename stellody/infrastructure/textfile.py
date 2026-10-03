"""Reading a small sidecar text file, such as a cue sheet.

Cue sheets are frequently not UTF-8, so several encodings are tried before
giving up. The file is only ever opened for reading.

A UTF-16 sheet is recognised by its byte order mark, either way round, before
any of those is tried. Left to them it never failed: the last accepts every
byte there is, so the sheet came back with a nul between every letter, matched
no command and its album played as one long track. Nothing is guessed beyond
that mark; a sheet in an encoding that carries none is read as before.
"""

from __future__ import annotations

import codecs

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

# Python's own UTF-16 codec reads the mark, takes the byte order from it and
# drops it from the text, so one name covers both orders.
UTF16_MARKS = (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
UTF16 = ("utf-16",)
MARK_LENGTH = max(len(mark) for mark in UTF16_MARKS)


class SidecarTextReader:
    """Reads a sidecar text file, tolerating the encodings rippers produce."""

    def read(self, path: str) -> str | None:
        """The file's text; None when it cannot be read at all."""
        try:
            with open(path, "rb") as handle:
                opening = handle.read(MARK_LENGTH)
        except OSError:
            return None
        encodings = UTF16 if opening.startswith(UTF16_MARKS) else ENCODINGS
        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read()
            except UnicodeDecodeError:
                continue
            except OSError:
                return None
        return None
