"""The install actions, including the fence around archive extraction."""

from __future__ import annotations

import pathlib
import zipfile

import pytest

from installer import actions, registry


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
    assert registry.installed_size_kib(tmp_path) == 4


def test_the_uninstall_registry_key_names_the_application() -> None:
    assert registry.registry_key().endswith(registry.APP_NAME)


def test_shortcut_paths_cover_desktop_and_start_menu() -> None:
    paths = actions.shortcut_paths()
    assert len(paths) == 2
    assert all(path.name == f"{registry.APP_NAME}.lnk" for path in paths)


def test_a_version_becomes_comparable_numbers() -> None:
    assert actions.version_key("1.2.3") == (1, 2, 3)
    assert actions.version_key("0.1.0") < actions.version_key("0.2.0")


def test_a_version_suffix_is_ignored_rather_than_refused() -> None:
    assert actions.version_key("0.0.0-dev") == (0, 0, 0)
    assert actions.version_key("1.2.3rc1") == (1, 2, 3)


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
    command = registry.sign_in_command(pathlib.Path("C:/Program Files/S.exe"))
    assert command.startswith('"')
    assert "Program Files" in command


def test_a_sign_in_start_is_always_a_quiet_one() -> None:
    """The other half of that choice is an app opening over your desktop."""
    command = registry.sign_in_command(pathlib.Path("C:/S.exe"))
    assert command.endswith(registry.HIDDEN_FLAG)


def test_the_tray_flag_is_the_one_the_application_reads() -> None:
    """Both sides of the sign-in handover must spell the flag the same way."""
    from stellody.shared import startup

    assert registry.HIDDEN_FLAG == startup.HIDDEN_FLAG
    command = registry.sign_in_command(pathlib.Path("C:/S.exe"))
    assert startup.starts_hidden(command.split())


def test_powershell_is_given_no_console_window_of_its_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A console child of a windowless build gets a black box, unless told not to."""
    captured: dict[str, object] = {}

    class Result:
        returncode = 0

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return Result()

    monkeypatch.setattr(actions.subprocess, "run", fake_run)
    assert actions._run_powershell("$x = 1") is True
    assert actions.NO_WINDOW != 0, "the flag must be real on Windows"
    assert captured["creationflags"] == actions.NO_WINDOW


def test_the_progress_ladder_is_weighted_by_where_the_time_goes(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each shortcut is half the install's running time, so it owns the bar."""
    archive = _archive(tmp_path / "payload.zip", {"Stellody.exe": "binary"})
    reported: list[tuple[int, str]] = []
    monkeypatch.setattr(actions, "setup_executable", lambda: archive)
    monkeypatch.setattr(actions, "create_shortcut", lambda *args: True)
    monkeypatch.setattr(actions, "register", lambda *args: None)
    monkeypatch.setattr(actions, "set_sign_in_entry", lambda *args: None)
    monkeypatch.setattr(actions, "desktop_dir", lambda: tmp_path / "desktop")
    monkeypatch.setattr(actions, "start_menu_dir", lambda: tmp_path / "menu")
    plan = actions.InstallPlan(target=tmp_path / "app", version="0.1.0")

    actions.install(plan, archive, lambda pct, msg: reported.append((pct, msg)))

    percentages = [percent for percent, _ in reported]
    assert percentages == sorted(percentages), "the bar must never travel backwards"
    assert percentages[-1] == actions.PCT_DONE
    # Everything before the first shortcut is a twentieth of the running time,
    # so it must not consume more than a small share of the bar.
    assert actions.PCT_REGISTRY <= 10
    shortcut_share = actions.PCT_START_MENU - actions.PCT_REGISTRY
    assert (
        shortcut_share >= 50
    ), "the shortcuts own most of the time, so most of the bar"
