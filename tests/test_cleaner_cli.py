from pathlib import Path

import pytest
from conftest import TRACKED, USER_DATA, snapshot, write_files

from ieakaso.devtools.cleaner import find_root, main


def run(repo: Path, backups: Path, *args: str) -> int:
    return main([*args, "--root", str(repo), "--backup-dir", str(backups)])


def test_find_root_walks_up_from_a_subfolder(repo: Path):
    assert find_root(repo / "input/documents/cv") == repo


def test_find_root_returns_none_outside_the_repo(tmp_path: Path):
    assert find_root(tmp_path) is None


def test_cli_refuses_a_root_that_is_not_ieakaso(tmp_path: Path, backups: Path):
    other = tmp_path / "other"
    write_files(other, {"config.yml": "x", "input/cv.pdf": "x", "pyproject.toml": '[project]\nname = "other"\n'})
    before = snapshot(other)

    assert run(other, backups, "clean") != 0
    assert snapshot(other) == before


def test_cli_clean_always_backs_up(repo: Path, backups: Path):
    assert run(repo, backups, "clean") == 0

    assert snapshot(repo) == {k: v.encode() for k, v in TRACKED.items()}
    assert len(list(backups.iterdir())) == 1


def test_cli_dry_run_changes_nothing(repo: Path, backups: Path, capsys):
    before = snapshot(repo)

    assert run(repo, backups, "clean", "--dry-run") == 0
    assert snapshot(repo) == before
    assert "config.yml" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["restore"], ["list"], ["clean", "20261010-143005"]])
def test_cli_rejects_unknown_commands_and_a_backup_name(repo: Path, backups: Path, args: list[str]):
    before = snapshot(repo)

    with pytest.raises(SystemExit) as exit:
        run(repo, backups, *args)

    assert exit.value.code == 2
    assert snapshot(repo) == before


def test_cli_clean_applications_keeps_the_setup_and_backs_up(repo: Path, backups: Path, capsys):
    assert run(repo, backups, "clean", "--applications") == 0

    assert (repo / "config.yml").read_text() == USER_DATA["config.yml"]
    assert not (repo / "db/ieakaso_db.json").exists()
    out = capsys.readouterr().out
    assert "deleted db/ieakaso_db.json" in out
    assert "backup: " in out
    assert len(list(backups.iterdir())) == 1
