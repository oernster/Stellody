"""Reading a small sidecar text file, such as a cue sheet.

Cue sheets are frequently not UTF-8, so several encodings are tried before
giving up. The file is only ever opened for reading.
"""

from __future__ import annotations

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class SidecarTextReader:
    """Reads a sidecar text file, tolerating the encodings rippers produce."""

    def read(self, path: str) -> str | None:
        """The file's text; None when it cannot be read at all."""
        for encoding in ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read()
            except UnicodeDecodeError:
                continue
            except OSError:
                return None
        return None
