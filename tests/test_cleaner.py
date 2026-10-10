from datetime import datetime
from pathlib import Path

from conftest import TRACKED, snapshot

from ieakaso.devtools import cleaner
from ieakaso.devtools.cleaner import clean, list_backups, restore


def test_clean_empties_input_but_keeps_placeholders(repo: Path):
    clean(repo)

    remaining = {p for p in snapshot(repo) if p.startswith("input/")}
    assert remaining == {p for p in TRACKED if p.startswith("input/")}


def test_clean_removes_config_and_keeps_example(repo: Path):
    clean(repo)

    assert not (repo / "config.yml").exists()
    assert (repo / "config_example.yml").read_text() == TRACKED["config_example.yml"]


def test_clean_removes_status_and_db_and_keeps_examples(repo: Path):
    clean(repo)

    assert not (repo / "db/system_status.json").exists()
    assert not (repo / "db/ieakaso_db.json").exists()
    assert sorted(p.name for p in (repo / "db").iterdir()) == [
        "ieakaso_db_structure.json",
        "system_status_example.json",
    ]


def test_clean_empties_output_but_keeps_gitkeep(repo: Path):
    clean(repo)

    assert {p for p in snapshot(repo) if p.startswith("output/")} == {"output/.gitkeep"}


def test_clean_removes_leftover_folders_without_gitkeep(repo: Path):
    report = clean(repo)

    assert not (repo / "input/documents/xing").exists()
    assert not (repo / "output/acme").exists()
    assert (repo / "input/documents/cv").is_dir()
    assert Path("input/documents/xing") in report.removed_dirs


def test_clean_leaves_a_fresh_repo_as_a_fresh_clone(repo: Path):
    clean(repo)

    assert snapshot(repo) == {k: v.encode() for k, v in TRACKED.items()}


def test_clean_twice_reports_nothing_the_second_time(repo: Path):
    first = clean(repo)
    second = clean(repo)

    assert Path("config.yml") in first.deleted
    assert second.deleted == []
    assert second.removed_dirs == []


def test_dry_run_reports_what_a_real_run_deletes_and_changes_nothing(repo: Path, tmp_path: Path, backups: Path):
    before = snapshot(repo)
    dry = clean(repo, backup_dir=backups, dry_run=True)

    assert snapshot(repo) == before
    assert not backups.exists()
    real = clean(repo)
    assert (dry.deleted, dry.removed_dirs) == (real.deleted, real.removed_dirs)


def test_clean_backs_up_user_data_before_deleting(repo: Path, backups: Path):
    report = clean(repo, backup_dir=backups)

    assert report.backup is not None and report.backup.parent == backups
    assert (report.backup / "config.yml").read_text() == "candidate:\n  name: Real\n"
    assert (report.backup / "input/documents/xing/nested/profile.pdf").exists()
    assert sorted(p.relative_to(report.backup) for p in report.backup.rglob("*") if p.is_file()) == report.deleted


def test_clean_skips_the_backup_when_there_is_nothing_to_delete(repo: Path, backups: Path):
    clean(repo)

    assert clean(repo, backup_dir=backups).backup is None
    assert list_backups(backups) == []


def test_backup_round_trip_restores_the_repo_byte_for_byte(repo: Path, backups: Path):
    before = snapshot(repo)
    first = clean(repo, backup_dir=backups)
    (repo / "config.yml").write_text("from a test init\n")

    restore(repo, first.backup, backup_dir=backups)

    assert snapshot(repo) == before
    newest = list_backups(backups)[-1]
    assert newest != first.backup
    assert (newest / "config.yml").read_text() == "from a test init\n"


def test_two_backups_in_the_same_second_get_a_suffix(repo: Path, backups: Path, monkeypatch):
    monkeypatch.setattr(cleaner, "_now", lambda: datetime(2026, 10, 10, 14, 30, 5))
    first = clean(repo, backup_dir=backups)
    (repo / "config.yml").write_text("again\n")
    second = clean(repo, backup_dir=backups)

    assert first.backup.name == "20261010-143005"
    assert second.backup.name == "20261010-143005-2"
    assert list_backups(backups) == [first.backup, second.backup]


def test_list_backups_ignores_folders_that_are_not_backups(repo: Path, backups: Path):
    (backups / "old").mkdir(parents=True)
    (backups / "notes.txt").write_text("x")
    report = clean(repo, backup_dir=backups)

    assert list_backups(backups) == [report.backup]
