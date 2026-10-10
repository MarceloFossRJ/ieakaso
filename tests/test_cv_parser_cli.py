"""The cv_parser command: writes input/cv.md from documents.cv.path and records it in db/system_status.json."""

import hashlib
import json
from pathlib import Path

import pytest
from conftest import TRACKED, snapshot, write_files

from ieakaso.cv_parser import PARSER_VERSION, cli

CV_PATH = "input/documents/cv/cv.txt"


def status(cv_path: str | None = CV_PATH, parsed: dict | None = None) -> str:
    cv = {"status": "found" if cv_path else "missing", "path": cv_path}
    if parsed is not None:
        cv["parsed"] = parsed
    return json.dumps({"init": {"status": "completed"}, "documents": {"cv": cv, "linkedin": {"status": "skipped"}}})


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write_files(root, TRACKED)
    write_files(root, {"db/system_status.json": status(), CV_PATH: "Jordan Example\r\nEngineer\r\n"})
    return root


def run(repo: Path, *args: str) -> int:
    return cli.main([*args, "--root", str(repo)])


def read_status(repo: Path) -> dict:
    return json.loads((repo / "db/system_status.json").read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_first_run_writes_the_parsed_cv(repo: Path):
    assert run(repo) == 0
    assert (repo / "input/cv.md").read_bytes() == b"Jordan Example\nEngineer\n"


def test_first_run_records_the_parse_in_the_status_file(repo: Path):
    run(repo)

    parsed = read_status(repo)["documents"]["cv"]["parsed"]
    assert parsed["source_path"] == CV_PATH
    assert parsed["source_sha256"] == sha((repo / CV_PATH).read_bytes())
    assert parsed["output_sha256"] == sha((repo / "input/cv.md").read_bytes())
    assert parsed["parser_version"] == PARSER_VERSION
    assert parsed["parsed_at"]


def test_the_rest_of_the_status_file_is_kept(repo: Path):
    run(repo)

    data = read_status(repo)
    assert data["init"] == {"status": "completed"}
    assert data["documents"]["linkedin"] == {"status": "skipped"}
    assert data["documents"]["cv"]["path"] == CV_PATH


def test_an_up_to_date_parsed_cv_is_left_alone(repo: Path, capsys):
    run(repo)
    before = snapshot(repo)

    assert run(repo) == 0
    assert snapshot(repo) == before
    assert "up to date" in capsys.readouterr().out


def test_a_changed_source_cv_is_parsed_again(repo: Path):
    run(repo)
    (repo / CV_PATH).write_text("Jordan Example\nStaff Engineer\n")

    assert run(repo) == 0
    assert (repo / "input/cv.md").read_text() == "Jordan Example\nStaff Engineer\n"
    assert read_status(repo)["documents"]["cv"]["parsed"]["source_sha256"] == sha((repo / CV_PATH).read_bytes())


def test_a_different_source_cv_is_parsed_again(repo: Path):
    run(repo)
    write_files(repo, {"input/documents/cv/other.txt": "Other CV\n"})
    data = read_status(repo)
    data["documents"]["cv"]["path"] = "input/documents/cv/other.txt"
    (repo / "db/system_status.json").write_text(json.dumps(data))

    assert run(repo) == 0
    assert (repo / "input/cv.md").read_text() == "Other CV\n"


def test_a_new_parser_version_parses_again(repo: Path, monkeypatch):
    run(repo)
    monkeypatch.setattr(cli, "PARSER_VERSION", PARSER_VERSION + 1)

    assert run(repo) == 0
    assert read_status(repo)["documents"]["cv"]["parsed"]["parser_version"] == PARSER_VERSION + 1


def test_a_missing_parsed_cv_is_written_again(repo: Path):
    run(repo)
    (repo / "input/cv.md").unlink()

    assert run(repo) == 0
    assert (repo / "input/cv.md").read_text() == "Jordan Example\nEngineer\n"


# --- hand edits ------------------------------------------------------------------


def test_a_hand_edited_parsed_cv_is_not_overwritten(repo: Path, capsys):
    run(repo)
    (repo / "input/cv.md").write_text("Jordan Example\nEngineer\nMy own note\n")
    (repo / CV_PATH).write_text("Jordan Example\nStaff Engineer\n")
    before = snapshot(repo)

    assert run(repo) == 3
    assert snapshot(repo) == before
    out = capsys.readouterr().out
    assert "-My own note" in out
    assert "+Staff Engineer" in out
    assert "--force" in out


def test_force_overwrites_a_hand_edited_parsed_cv(repo: Path):
    run(repo)
    (repo / "input/cv.md").write_text("edited\n")

    assert run(repo, "--force") == 0
    assert (repo / "input/cv.md").read_text() == "Jordan Example\nEngineer\n"


def test_an_existing_parsed_cv_without_a_record_counts_as_hand_edited(repo: Path):
    write_files(repo, {"input/cv.md": "# My CV, typed by hand\n"})

    assert run(repo) == 3
    assert (repo / "input/cv.md").read_text() == "# My CV, typed by hand\n"


def test_an_existing_parsed_cv_that_already_matches_is_just_recorded(repo: Path):
    write_files(repo, {"input/cv.md": "Jordan Example\nEngineer\n"})

    assert run(repo) == 0
    assert "parsed" in read_status(repo)["documents"]["cv"]


# --- failures ------------------------------------------------------------------


def test_a_source_that_fails_to_parse_changes_nothing(repo: Path, capsys):
    run(repo)
    (repo / CV_PATH).write_bytes("Jordan Exámple\n".encode("latin-1"))
    before = snapshot(repo)

    assert run(repo) == 1
    assert snapshot(repo) == before
    err = capsys.readouterr().err
    assert "UTF-8" in err
    assert "input/documents/cv/" in err


@pytest.mark.parametrize("data", [None, "not json", status(cv_path=None)])
def test_without_a_recorded_source_cv_it_asks_for_init(repo: Path, capsys, data):
    if data is None:
        (repo / "db/system_status.json").unlink()
    else:
        (repo / "db/system_status.json").write_text(data)
    before = snapshot(repo)

    assert run(repo) == 2
    assert snapshot(repo) == before
    assert "/ieakaso init" in capsys.readouterr().err


def test_a_recorded_source_cv_that_no_longer_exists_asks_for_init(repo: Path, capsys):
    (repo / CV_PATH).unlink()

    assert run(repo) == 2
    assert "/ieakaso init" in capsys.readouterr().err


def test_it_refuses_a_root_that_is_not_ieakaso(tmp_path: Path):
    assert run(tmp_path) == 2
