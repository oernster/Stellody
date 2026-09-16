"""No audio file of a widened format sits in the tree.

NFR-F-TEST-001. The three formats `FORMATS.md` adds are proved by fixtures the
suite encodes into a temporary directory at test time; that is the whole basis
on which they were added: a committed binary would be a licence question
and a repository that grows by a file for every format anybody wants next.

The check is a scan of the working tree rather than a question put to git,
which is stricter in the one direction that matters here. A fixture written
into the repository by mistake is caught whether or not anybody staged it;
no fixture is ever written into the repository on purpose, since every one
goes to the temporary folder pytest hands the test.
"""

from __future__ import annotations

import pathlib

from conftest import REPO_ROOT, relative, repository_files

# The formats proved by a fixture, so the formats no file of may be committed.
FIXTURE_SUFFIXES = (".wma", ".wv", ".aac")


def _tracked_paths() -> list[pathlib.Path]:
    """Every file in the working tree that is the repository's own.

    The virtual environment holds other people's packages and the build
    directories hold output, neither of which is anybody's decision to commit
    an audio file; `conftest.NOT_OURS` names them.
    """
    return repository_files(REPO_ROOT, "*")


def test_no_fixture_audio_is_committed() -> None:
    """A fixture belongs to the test that wrote it and to nothing else."""
    found = [
        relative(path)
        for path in _tracked_paths()
        if path.suffix.casefold() in FIXTURE_SUFFIXES
    ]
    assert not found, "Audio fixtures must be generated, never committed: " + "; ".join(
        found
    )
