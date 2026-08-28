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


def test_a_version_becomes_comparable_numbers() -> None:
    assert actions.version_key("1.2.3") == (1, 2, 3)
    assert actions.version_key("0.1.0") < actions.version_key("0.2.0")


def test_a_version_suffix_is_ignored_rather_than_refused() -> None:
    assert actions.version_key("0.0.0-dev") == (0, 0, 0)
    assert actions.version_key("1.2.3rc1") == (1, 2, 3)


def test_a_missing_install_is_summarised_as_such() -> None:
    assert "not currently installed" in actions.upgrade_summary("", "0.2.0")


def test_the_same_version_reads_as_a_reinstall() -> None:
    summary = actions.upgrade_summary("0.2.0", "0.2.0")
    assert "already installed" in summary
    assert "reinstalls" in summary


def test_an_older_install_reads_as_an_update_naming_both_versions() -> None:
    summary = actions.upgrade_summary("0.1.0", "0.2.0")
    assert "0.1.0" in summary
    assert "0.2.0" in summary
    assert "updates" in summary


def test_a_newer_install_is_reported_as_newer_rather_than_hidden() -> None:
    summary = actions.upgrade_summary("0.3.0", "0.2.0")
    assert "newer" in summary
    assert "replaces" in summary


def test_the_payload_is_searched_for_beside_the_unpacked_module() -> None:
    """argv[0] is the original exe under a onefile build, so it cannot lead."""
    roots = actions.payload_roots()
    here = pathlib.Path(actions.__file__).resolve()
    assert here.parent in roots
    assert here.parents[1] in roots


def test_a_staged_payload_is_found_from_a_source_checkout(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged = tmp_path / actions.PAYLOAD_DIR
    staged.mkdir()
    archive = _archive(staged / actions.PAYLOAD_ZIP, {"a.txt": "a"})
    monkeypatch.setattr(actions, "payload_roots", lambda: (tmp_path,))
    assert actions.payload_zip() == archive


def test_no_payload_anywhere_reports_none(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(actions, "payload_roots", lambda: (tmp_path,))
    assert actions.payload_zip() is None


def test_the_sign_in_command_quotes_the_path() -> None:
    command = actions.sign_in_command(pathlib.Path("C:/Program Files/S.exe"), False)
    assert command.startswith('"')
    assert command.endswith('"')


def test_the_sign_in_command_carries_the_tray_flag_when_minimised() -> None:
    command = actions.sign_in_command(pathlib.Path("C:/S.exe"), True)
    assert command.endswith(actions.HIDDEN_FLAG)


def test_the_tray_flag_is_the_one_the_application_reads() -> None:
    """Both sides of the sign-in handover must spell the flag the same way."""
    from stellody.shared import startup

    assert actions.HIDDEN_FLAG == startup.HIDDEN_FLAG
    command = actions.sign_in_command(pathlib.Path("C:/S.exe"), True)
    assert startup.starts_hidden(command.split())


def test_a_plain_sign_in_command_does_not_start_hidden() -> None:
    from stellody.shared import startup

    command = actions.sign_in_command(pathlib.Path("C:/S.exe"), False)
    assert not startup.starts_hidden(command.split())
