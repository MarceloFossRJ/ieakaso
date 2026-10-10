from pathlib import Path

from conftest import TRACKED, USER_DATA, snapshot, write_files

from ieakaso.devtools.cleaner import find_root, list_backups, main


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
    assert len(list_backups(backups)) == 1


def test_cli_dry_run_changes_nothing(repo: Path, backups: Path, capsys):
    before = snapshot(repo)

    assert run(repo, backups, "clean", "--dry-run") == 0
    assert snapshot(repo) == before
    assert "config.yml" in capsys.readouterr().out


def test_cli_restore_uses_the_newest_backup_by_default(repo: Path, backups: Path):
    run(repo, backups, "clean")

    assert run(repo, backups, "restore") == 0
    assert (repo / "config.yml").read_text() == USER_DATA["config.yml"]


def test_cli_restore_a_named_backup(repo: Path, backups: Path):
    run(repo, backups, "clean")
    name = list_backups(backups)[0].name

    assert run(repo, backups, "restore", name) == 0
    assert (repo / "input/cv.md").read_text() == USER_DATA["input/cv.md"]


def test_cli_restore_without_backups_fails_and_changes_nothing(repo: Path, backups: Path):
    before = snapshot(repo)

    assert run(repo, backups, "restore") != 0
    assert snapshot(repo) == before


def test_cli_list_shows_backups(repo: Path, backups: Path, capsys):
    run(repo, backups, "clean")
    capsys.readouterr()

    assert run(repo, backups, "list") == 0
    assert list_backups(backups)[0].name in capsys.readouterr().out


def test_cli_restore_dry_run_changes_nothing(repo: Path, backups: Path, capsys):
    run(repo, backups, "clean")
    (repo / "config.yml").write_text("from a test init\n")
    before = snapshot(repo)
    count = len(list_backups(backups))
    capsys.readouterr()

    assert run(repo, backups, "restore", "--dry-run") == 0
    assert snapshot(repo) == before
    assert len(list_backups(backups)) == count
    out = capsys.readouterr().out
    assert "would delete config.yml" in out
    assert f"would restore {list_backups(backups)[-1].name}" in out
