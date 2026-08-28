"""The install actions, including the fence around archive extraction."""

from __future__ import annotations

import pathlib
import zipfile

import pytest

from installer import actions


def _archive(path: pathlib.Path, entries: dict[str, str]) -> pathlib.Path:
    """Write a zip holding the given entries."""
    with zipfile.ZipFile(path, "w") as bundle:
        for name, content in entries.items():
            bundle.writestr(name, content)
    return path


def test_a_normal_archive_extracts(tmp_path: pathlib.Path) -> None:
    archive = _archive(
        tmp_path / "payload.zip",
        {"Stellody.exe": "binary", "_internal/VERSION": "0.1.0"},
    )
    target = tmp_path / "install"
    written = actions.extract_payload(archive, target)
    assert written == 2
    assert (target / "Stellody.exe").is_file()
    assert (target / "_internal" / "VERSION").read_text(encoding="utf-8") == "0.1.0"


def test_an_entry_climbing_out_of_the_target_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """A crafted archive must not write outside the folder the user chose."""
    archive = _archive(tmp_path / "evil.zip", {"../escaped.txt": "no"})
    target = tmp_path / "install"
    with pytest.raises(ValueError, match="escapes the install folder"):
        actions.extract_payload(archive, target)
    assert not (tmp_path / "escaped.txt").exists()


def test_nothing_is_written_when_any_entry_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The whole archive is checked before a single file is written."""
    archive = _archive(
        tmp_path / "mixed.zip", {"good.txt": "yes", "../escaped.txt": "no"}
    )
    target = tmp_path / "install"
    with pytest.raises(ValueError):
        actions.extract_payload(archive, target)
    assert not (target / "good.txt").exists()


def test_installed_size_is_reported_in_kibibytes(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 4096)
    assert actions.installed_size_kib(tmp_path) == 4


def test_the_uninstall_registry_key_names_the_application() -> None:
    assert actions.registry_key().endswith(actions.APP_NAME)


def test_shortcut_paths_cover_desktop_and_start_menu() -> None:
    paths = actions.shortcut_paths()
    assert len(paths) == 2
    assert all(path.name == f"{actions.APP_NAME}.lnk" for path in paths)
