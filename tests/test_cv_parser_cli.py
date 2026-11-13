"""The cv_parser command: captures CV versions from the inbox input/documents/cv/, writes input/cv.md from the
current version, and records both (docs/adr/0005-cv-versions.md)."""

import hashlib
import json
from pathlib import Path

import pytest
from conftest import TRACKED, snapshot, write_files
from tracker_fakes import ID, TODAY, lead, record, write_db

from ieakaso.cv_parser import PARSER_VERSION, cli
from ieakaso.tracker import DB_PATH, current_cv_version, load

INBOX = "input/documents/cv"
CV_PATH = f"{INBOX}/cv.txt"
VERSION = "cv_2026-10-15"
CAPTURED = f"{INBOX}/{VERSION}/cv.txt"
FROZEN = f"{INBOX}/{VERSION}/parsed-cv.md"
CV_TEXT = "Jordan Example\r\nEngineer\r\n"
CV_PARSED = "Jordan Example\nEngineer\n"


def status(cv_path: str | None = None, parsed: dict | None = None) -> str:
    cv = {"status": "found" if cv_path else "missing", "path": cv_path}
    if parsed is not None:
        cv["parsed"] = parsed
    return json.dumps({"init": {"status": "completed"}, "documents": {"cv": cv, "linkedin": {"status": "skipped"}}})


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write_files(root, TRACKED)
    write_files(root, {"db/system_status.json": status(), CV_PATH: CV_TEXT})
    return root


def run(repo: Path, *args: str) -> int:
    return cli.main([*args, "--root", str(repo)], today=TODAY)


def read_status(repo: Path) -> dict:
    return json.loads((repo / "db/system_status.json").read_text())


def versions(repo: Path) -> list[dict]:
    return load(repo / DB_PATH).cv_versions


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_first_run_writes_the_parsed_cv(repo: Path):
    assert run(repo) == 0
    assert (repo / "input/cv.md").read_bytes() == CV_PARSED.encode()


def test_first_run_records_the_parse_in_the_status_file(repo: Path):
    run(repo)

    cv = read_status(repo)["documents"]["cv"]
    parsed = cv["parsed"]
    assert cv["path"] == CAPTURED and cv["status"] == "found"
    assert parsed["source_path"] == CAPTURED
    assert parsed["source_sha256"] == sha((repo / CAPTURED).read_bytes())
    assert parsed["output_sha256"] == sha((repo / "input/cv.md").read_bytes())
    assert parsed["parser_version"] == PARSER_VERSION
    assert parsed["parsed_at"]


def test_the_rest_of_the_status_file_is_kept(repo: Path):
    run(repo)

    data = read_status(repo)
    assert data["init"] == {"status": "completed"}
    assert data["documents"]["linkedin"] == {"status": "skipped"}


def test_an_up_to_date_parsed_cv_is_left_alone(repo: Path, capsys):
    run(repo)
    before = snapshot(repo)

    assert run(repo) == 0
    assert snapshot(repo) == before
    assert "up to date" in capsys.readouterr().out


def test_a_new_parser_version_parses_again(repo: Path, monkeypatch):
    run(repo)
    monkeypatch.setattr(cli, "PARSER_VERSION", PARSER_VERSION + 1)

    assert run(repo) == 0
    assert read_status(repo)["documents"]["cv"]["parsed"]["parser_version"] == PARSER_VERSION + 1


def test_a_missing_parsed_cv_is_written_again(repo: Path):
    run(repo)
    (repo / "input/cv.md").unlink()

    assert run(repo) == 0
    assert (repo / "input/cv.md").read_text() == CV_PARSED


# --- capturing a CV version ------------------------------------------------------


def test_the_first_cv_in_the_inbox_becomes_the_first_version(repo: Path, capsys):
    assert run(repo) == 0

    [version] = versions(repo)
    assert version == {
        "id": VERSION,
        "label": "cv",
        "path": CAPTURED,
        "captured_at": "2026-10-15",
        "tailored_for": None,
    }
    assert f"Captured {VERSION}" in capsys.readouterr().out


def test_the_file_is_moved_not_copied_and_its_bytes_are_kept(repo: Path):
    run(repo)

    assert not (repo / CV_PATH).exists()
    assert (repo / CAPTURED).read_bytes() == CV_TEXT.encode()


def test_a_frozen_parsed_cv_is_written_next_to_the_source(repo: Path):
    run(repo)

    assert (repo / FROZEN).read_text() == CV_PARSED


def test_the_label_is_the_file_name_without_its_extension(repo: Path):
    (repo / CV_PATH).rename(repo / f"{INBOX}/cv_en_333.txt")

    run(repo)

    assert versions(repo)[0]["label"] == "cv_en_333"


def test_the_version_is_identified_by_content_not_by_name(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/renamed.txt": CV_TEXT})

    assert run(repo) == 0
    assert len(versions(repo)) == 1
    assert (repo / f"{INBOX}/renamed.txt").exists()
    out = capsys.readouterr().out
    assert f"Duplicate: {INBOX}/renamed.txt" in out and VERSION in out


def test_a_file_with_the_name_of_a_version_but_new_content_is_new(repo: Path, capsys):
    run(repo)
    write_files(repo, {CV_PATH: "Jordan Example\nStaff Engineer\n"})

    assert run(repo) == 4
    assert f"New CV file: {CV_PATH}" in capsys.readouterr().out


def test_a_new_file_next_to_a_version_waits_for_the_candidate_s_choice(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/other.txt": "Other CV\n"})
    before = snapshot(repo)

    assert run(repo) == 4
    assert snapshot(repo) == before
    assert f"New CV file: {INBOX}/other.txt" in capsys.readouterr().out


def test_main_makes_a_new_file_the_new_main_cv_and_regenerates_the_parsed_cv(repo: Path):
    run(repo)
    write_files(repo, {f"{INBOX}/other.txt": "Other CV\n"})

    assert run(repo, "--main", "other.txt") == 0

    assert (repo / "input/cv.md").read_text() == "Other CV\n"
    assert [v["id"] for v in versions(repo)] == [VERSION, f"{VERSION}_2"]
    assert current_cv_version(load(repo / DB_PATH))["id"] == f"{VERSION}_2"
    assert (repo / f"{INBOX}/{VERSION}_2/parsed-cv.md").read_text() == "Other CV\n"
    assert not (repo / f"{INBOX}/other.txt").exists()
    assert read_status(repo)["documents"]["cv"]["path"] == f"{INBOX}/{VERSION}_2/other.txt"


def test_main_takes_a_repo_relative_path_too(repo: Path):
    run(repo)
    write_files(repo, {f"{INBOX}/other.txt": "Other CV\n"})

    assert run(repo, "--main", f"{INBOX}/other.txt") == 0


def test_with_several_new_files_only_the_chosen_one_is_captured(repo: Path, capsys):
    write_files(repo, {f"{INBOX}/b.txt": "B CV\n"})
    assert run(repo) == 4
    assert not (repo / "input/cv.md").exists()
    captured = capsys.readouterr()
    assert f"New CV file: {CV_PATH}" in captured.out and f"New CV file: {INBOX}/b.txt" in captured.out
    assert captured.err == ""

    assert run(repo, "--main", "b.txt") == 4  # cv.txt is still waiting for its answer

    assert [v["label"] for v in versions(repo)] == ["b"]
    assert (repo / CV_PATH).read_bytes() == CV_TEXT.encode()
    assert (repo / "input/cv.md").read_text() == "B CV\n"


def test_a_tailored_cv_belongs_to_its_application_and_never_becomes_current(repo: Path):
    run(repo)
    write_db(repo / DB_PATH, lead(), cv_versions=versions(repo))
    write_files(repo, {f"{INBOX}/for_acme.txt": "Tailored for Acme\n"})

    assert run(repo, "--tailored", "for_acme.txt", "--for", ID) == 0

    tailored = versions(repo)[1]
    assert tailored["tailored_for"] == ID and tailored["label"] == "for_acme"
    db = load(repo / DB_PATH)
    assert db.find(ID)["cv_version"] == tailored["id"]
    assert current_cv_version(db)["id"] == VERSION
    assert (repo / "input/cv.md").read_text() == CV_PARSED
    assert (repo / INBOX / tailored["id"] / "parsed-cv.md").read_text() == "Tailored for Acme\n"


def test_a_tailored_cv_for_an_unknown_application_changes_nothing(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/for_acme.txt": "Tailored for Acme\n"})
    before = snapshot(repo)

    assert run(repo, "--tailored", "for_acme.txt", "--for", "nope") == 6
    assert snapshot(repo) == before
    assert "nope" in capsys.readouterr().err


def test_tailored_needs_an_application(repo: Path):
    run(repo)
    write_files(repo, {f"{INBOX}/for_acme.txt": "Tailored for Acme\n"})
    before = snapshot(repo)

    assert run(repo, "--tailored", "for_acme.txt") == 6
    assert snapshot(repo) == before


def test_a_file_that_is_not_waiting_in_the_inbox_is_refused(repo: Path, capsys):
    run(repo)
    before = snapshot(repo)

    assert run(repo, "--main", "ghost.txt") == 6
    assert snapshot(repo) == before
    assert "ghost.txt" in capsys.readouterr().err


def test_a_duplicate_named_by_main_is_reported_and_left_alone(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/copy.txt": CV_TEXT})
    before = snapshot(repo)

    assert run(repo, "--main", "copy.txt") == 0
    assert snapshot(repo) == before
    assert "Duplicate" in capsys.readouterr().out


def test_two_identical_new_files_become_one_version_and_one_duplicate(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/a.txt": "Same\n", f"{INBOX}/b.txt": "Same\n"})

    assert run(repo, "--main", "a.txt") == 0

    assert len(versions(repo)) == 2
    assert f"Duplicate: {INBOX}/b.txt" in capsys.readouterr().out


def test_a_second_version_on_the_same_day_gets_a_suffix(repo: Path):
    run(repo)
    write_files(repo, {f"{INBOX}/b.txt": "B\n"})
    run(repo, "--main", "b.txt")
    write_files(repo, {f"{INBOX}/c.txt": "C\n"})

    run(repo, "--main", "c.txt")

    assert [v["id"] for v in versions(repo)] == [VERSION, f"{VERSION}_2", f"{VERSION}_3"]


def test_a_file_that_is_not_a_cv_stays_and_is_reported_again_on_later_runs(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/invoice.txt": "Invoice 42\n"})

    for _ in range(2):
        assert run(repo) == 4
        assert f"New CV file: {INBOX}/invoice.txt" in capsys.readouterr().out

    assert (repo / f"{INBOX}/invoice.txt").read_text() == "Invoice 42\n"
    assert len(versions(repo)) == 1
    assert (repo / "input/cv.md").read_text() == CV_PARSED  # the current CV is still written


def test_files_that_are_not_cv_formats_and_placeholders_are_ignored(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/notes.xlsx": "x", f"{INBOX}/.hidden.txt": "x"})

    assert run(repo) == 0
    assert "New CV file" not in capsys.readouterr().out


def test_a_new_file_that_cannot_be_parsed_is_not_captured(repo: Path, capsys):
    (repo / CV_PATH).write_bytes("Jordan Exámple\n".encode("latin-1"))
    before = snapshot(repo)

    assert run(repo) == 1
    assert snapshot(repo) == before
    err = capsys.readouterr().err
    assert "UTF-8" in err
    assert "input/documents/cv/" in err


def test_a_folder_the_parser_did_not_create_gets_one_warning_and_nothing_else(repo: Path, capsys):
    run(repo)
    write_files(repo, {f"{INBOX}/my_old_cvs/old.pdf": "%PDF", f"{INBOX}/my_old_cvs/old2.txt": "Old CV\n"})
    capsys.readouterr()
    before = snapshot(repo)

    assert run(repo) == 0
    assert snapshot(repo) == before
    out = capsys.readouterr().out
    assert out.count("my_old_cvs") == 1 and "Warning" in out
    assert "New CV file" not in out


def test_a_version_folder_gets_no_warning(repo: Path, capsys):
    run(repo)
    capsys.readouterr()

    run(repo)

    assert "Warning" not in capsys.readouterr().out


def test_raising_the_parser_version_is_not_a_new_version_and_leaves_the_frozen_copy(repo: Path, monkeypatch):
    run(repo)
    (repo / FROZEN).write_text("frozen as the agents read it then\n")
    monkeypatch.setattr(cli, "PARSER_VERSION", PARSER_VERSION + 1)

    assert run(repo) == 0
    assert len(versions(repo)) == 1
    assert (repo / FROZEN).read_text() == "frozen as the agents read it then\n"
    assert (repo / "input/cv.md").read_text() == CV_PARSED


def test_an_unusable_tracker_db_stops_before_anything_is_moved(repo: Path, capsys):
    write_files(repo, {"db/ieakaso_db.json": "{ broken"})
    before = snapshot(repo)

    assert run(repo) == 5
    assert snapshot(repo) == before
    assert "ieakaso_db.json" in capsys.readouterr().err


def test_a_db_that_changes_while_capturing_leaves_the_file_in_the_inbox(repo: Path, monkeypatch, capsys):
    from ieakaso.cv_parser import versions as versions_module

    real_save = versions_module.save

    def racing_save(db):
        write_db(repo / DB_PATH, lead())  # another process wrote in between
        return real_save(db)

    write_db(repo / DB_PATH)
    monkeypatch.setattr(versions_module, "save", racing_save)

    assert run(repo) == 5
    assert (repo / CV_PATH).read_bytes() == CV_TEXT.encode()
    assert not (repo / INBOX / VERSION).exists()
    assert "changed" in capsys.readouterr().err


# --- migration: a Source CV lying directly in the inbox before CV versions ------------


OLD_PARSED = {
    "source_path": CV_PATH,
    "source_sha256": "x",
    "parser_version": PARSER_VERSION,
    "output_sha256": "y",
    "parsed_at": "2026-09-20T08:30:00+00:00",
}


def old_repo(repo: Path, *records: dict) -> None:
    """The repo as it was before CV versions: the Source CV in the inbox, recorded and parsed, a schema 2 db."""
    write_files(repo, {"db/system_status.json": status(CV_PATH, OLD_PARSED), "input/cv.md": CV_PARSED})
    write_db(repo / DB_PATH, *[{k: v for k, v in r.items() if k != "cv_version"} for r in records], version=2)


def test_the_source_cv_in_the_inbox_becomes_the_first_version_dated_by_its_parse(repo: Path, capsys):
    old_repo(repo)

    assert run(repo) == 0

    [version] = versions(repo)
    assert version["id"] == "cv_2026-09-20" and version["captured_at"] == "2026-09-20"
    assert (repo / f"{INBOX}/cv_2026-09-20/cv.txt").read_bytes() == CV_TEXT.encode()
    assert not (repo / CV_PATH).exists()
    assert read_status(repo)["documents"]["cv"]["path"] == f"{INBOX}/cv_2026-09-20/cv.txt"
    assert "New CV file" not in capsys.readouterr().out


def test_the_migration_links_every_record_past_lead_and_no_lead(repo: Path):
    old_repo(
        repo,
        record(id="applied", applied_on="2026-09-25"),
        record(id="desisted-later", status="desisted", applied_on="2026-09-26"),
        lead(id="lead"),
    )

    run(repo)

    db = load(repo / DB_PATH)
    assert db.error is None
    assert {r["id"]: r["cv_version"] for r in db.records} == {
        "applied": "cv_2026-09-20",
        "desisted-later": "cv_2026-09-20",
        "lead": None,
    }


def test_the_migration_keeps_the_parsed_cv_as_the_agents_read_it(repo: Path):
    old_repo(repo)
    write_files(repo, {"input/cv.md": CV_PARSED})
    parsed = dict(OLD_PARSED, source_sha256=sha(CV_TEXT.encode()), output_sha256=sha(CV_PARSED.encode()))
    write_files(repo, {"db/system_status.json": status(CV_PATH, parsed)})

    assert run(repo) == 0
    assert (repo / "input/cv.md").read_text() == CV_PARSED


def test_another_file_in_the_inbox_during_the_migration_waits_for_a_choice(repo: Path, capsys):
    old_repo(repo)
    write_files(repo, {f"{INBOX}/cv_de.txt": "Deutscher Lebenslauf\n"})

    assert run(repo) == 4

    assert [v["id"] for v in versions(repo)] == ["cv_2026-09-20"]
    assert f"New CV file: {INBOX}/cv_de.txt" in capsys.readouterr().out


def test_a_repo_that_was_never_parsed_does_not_migrate_but_captures_today(repo: Path):
    write_files(repo, {"db/system_status.json": status(CV_PATH)})

    run(repo)

    assert versions(repo)[0]["id"] == VERSION


# --- hand edits ------------------------------------------------------------------


def test_a_hand_edited_parsed_cv_is_not_overwritten(repo: Path, capsys):
    run(repo)
    (repo / "input/cv.md").write_text("Jordan Example\nEngineer\nMy own note\n")
    write_files(repo, {f"{INBOX}/new.txt": "Jordan Example\nStaff Engineer\n"})
    capsys.readouterr()
    assert run(repo, "--main", "new.txt") == 3

    assert (repo / "input/cv.md").read_text() == "Jordan Example\nEngineer\nMy own note\n"
    out = capsys.readouterr().out
    assert "-My own note" in out
    assert "+Staff Engineer" in out
    assert "--force" in out
    assert len(versions(repo)) == 2  # the new version is captured already; only input/cv.md waits for the answer


def test_force_overwrites_a_hand_edited_parsed_cv(repo: Path):
    run(repo)
    (repo / "input/cv.md").write_text("edited\n")

    assert run(repo, "--force") == 0
    assert (repo / "input/cv.md").read_text() == CV_PARSED


def test_an_existing_parsed_cv_without_a_record_counts_as_hand_edited(repo: Path):
    write_files(repo, {"input/cv.md": "# My CV, typed by hand\n"})

    assert run(repo) == 3
    assert (repo / "input/cv.md").read_text() == "# My CV, typed by hand\n"


def test_an_existing_parsed_cv_that_already_matches_is_just_recorded(repo: Path):
    write_files(repo, {"input/cv.md": CV_PARSED})

    assert run(repo) == 0
    assert "parsed" in read_status(repo)["documents"]["cv"]


# --- failures ------------------------------------------------------------------


@pytest.mark.parametrize("data", [None, "not json"])
def test_without_a_status_file_it_asks_for_init(repo: Path, capsys, data):
    if data is None:
        (repo / "db/system_status.json").unlink()
    else:
        (repo / "db/system_status.json").write_text(data)
    before = snapshot(repo)

    assert run(repo) == 2
    assert snapshot(repo) == before
    assert "/ieakaso init" in capsys.readouterr().err


def test_without_any_cv_it_asks_for_one(repo: Path, capsys):
    (repo / CV_PATH).unlink()

    assert run(repo) == 2
    assert "/ieakaso init" in capsys.readouterr().err


def test_a_current_version_whose_file_is_gone_asks_for_init(repo: Path, capsys):
    run(repo)
    (repo / CAPTURED).unlink()

    assert run(repo) == 2
    assert "/ieakaso init" in capsys.readouterr().err


def test_it_refuses_a_root_that_is_not_ieakaso(tmp_path: Path):
    assert run(tmp_path) == 2
