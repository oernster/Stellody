"""Repairing, retiming the shortcuts and taking things away again.

The three actions that touch the machine without a full install behind them.
Each is exercised against real files in a temporary directory rather than a
mock, so what is asserted is what the filesystem actually holds afterwards.
"""

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


def test_a_repair_writes_the_files_back(tmp_path: pathlib.Path) -> None:
    archive = _archive(tmp_path / "payload.zip", {"Stellody.exe": "good"})
    target = tmp_path / "install"
    target.mkdir()
    (target / "Stellody.exe").write_text("damaged", encoding="utf-8")
    executable = actions.repair(target, archive)
    assert executable == target / actions.EXE_NAME
    assert (target / "Stellody.exe").read_text(encoding="utf-8") == "good"


def test_a_repair_leaves_everything_beside_the_files_alone(
    tmp_path: pathlib.Path,
) -> None:
    """That is the whole of the difference between a repair and a reinstall."""
    archive = _archive(tmp_path / "payload.zip", {"Stellody.exe": "good"})
    target = tmp_path / "install"
    target.mkdir()
    kept = target / "settings-the-user-put-here.txt"
    kept.write_text("mine", encoding="utf-8")
    actions.repair(target, archive)
    assert kept.read_text(encoding="utf-8") == "mine"


def test_a_repair_reports_its_steps(tmp_path: pathlib.Path) -> None:
    archive = _archive(tmp_path / "payload.zip", {"Stellody.exe": "good"})
    seen: list[int] = []
    actions.repair(tmp_path / "install", archive, lambda pct, msg: seen.append(pct))
    assert seen[0] == actions.PCT_START
    assert seen[-1] == actions.PCT_DONE


def test_ticking_a_shortcut_box_writes_it_and_unticking_removes_it(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a matching version the boxes are the only thing that can act."""
    desktop = tmp_path / "Desktop" / "Stellody.lnk"
    start_menu = tmp_path / "Start" / "Stellody.lnk"
    monkeypatch.setattr(actions, "shortcut_paths", lambda: (desktop, start_menu))
    written: list[pathlib.Path] = []
    monkeypatch.setattr(
        actions,
        "create_shortcut",
        lambda link, executable, icon: written.append(link) or True,
    )
    executable = tmp_path / "Stellody.exe"

    actions.set_shortcuts(executable, desktop=True, start_menu=False)
    assert written == [desktop]

    start_menu.parent.mkdir(parents=True, exist_ok=True)
    start_menu.write_text("link", encoding="utf-8")
    actions.set_shortcuts(executable, desktop=False, start_menu=True)
    assert written == [desktop, start_menu]


def test_removing_an_absent_shortcut_is_not_an_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absent = tmp_path / "gone" / "Stellody.lnk"
    monkeypatch.setattr(actions, "shortcut_paths", lambda: (absent, absent))
    actions.set_shortcuts(tmp_path / "Stellody.exe", desktop=False, start_menu=False)


def _prepared(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """An install and a data directory, with the registry work stubbed out."""
    target = tmp_path / "install"
    target.mkdir()
    (target / "Stellody.exe").write_text("binary", encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    (data / "library.sqlite3").write_text("index", encoding="utf-8")
    monkeypatch.setattr(actions, "shortcut_paths", lambda: ())
    monkeypatch.setattr(actions, "clear_sign_in_entry", lambda: None)
    monkeypatch.setattr(actions, "unregister", lambda: None)
    monkeypatch.setattr(actions, "data_location", lambda: data)
    return target


def test_an_uninstall_keeps_the_library_index_by_default(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """They may well want it back if they reinstall, so keeping it is default."""
    target = _prepared(tmp_path, monkeypatch)
    actions.uninstall(target)
    assert not target.exists()
    assert (tmp_path / "data" / "library.sqlite3").exists()


def test_the_forget_box_takes_the_library_index_with_it(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _prepared(tmp_path, monkeypatch)
    actions.uninstall(target, remove_data=True)
    assert not target.exists()
    assert not (tmp_path / "data").exists()
