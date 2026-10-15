"""The tracker command: upsert, set-cover-letter and set-company-research, exit codes 0-4. Fake repo, injected today."""

import io
import json
from pathlib import Path

import pytest
from tracker_fakes import FOLDER, ID, TODAY, lead, payload, write_db

from ieakaso.tracker import cli


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def db_file(root: Path) -> Path:
    return root / "db" / "ieakaso_db.json"


def run(root: Path, *argv: str, stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), *argv], today=TODAY, stdin=io.StringIO(stdin), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_upsert_from_the_json_argument_creates_the_db_and_the_record(root: Path):
    code, out, err = run(root, "upsert", "--json", json.dumps(payload()))

    assert (code, err) == (0, "")
    assert out == f"created {ID}\n"
    data = json.loads(db_file(root).read_text())
    assert data["meta"] == {"schema_version": 2}
    assert data["records"][0]["status"] == "lead"


def test_upsert_reads_stdin_without_the_json_argument(root: Path):
    code, out, _ = run(root, "upsert", stdin=json.dumps(payload()))

    assert code == 0 and out == f"created {ID}\n"


def test_upsert_again_says_updated(root: Path):
    run(root, "upsert", "--json", json.dumps(payload()))

    code, out, _ = run(root, "upsert", "--json", json.dumps(payload()))

    assert code == 0 and out == f"updated {ID}\n"
    assert len(json.loads(db_file(root).read_text())["records"]) == 1


def test_exit_1_when_the_payload_is_not_valid(root: Path):
    code, out, err = run(root, "upsert", "--json", json.dumps(payload(company="")))

    assert (code, out) == (1, "")
    assert "company" in err
    assert not db_file(root).exists()


def test_exit_1_when_the_payload_is_not_json(root: Path):
    code, _, err = run(root, "upsert", "--json", "{nope")

    assert code == 1 and "JSON" in err


def test_exit_2_when_the_db_is_not_valid_json_and_it_is_left_alone(root: Path):
    db_file(root).parent.mkdir(parents=True)
    db_file(root).write_text("{ broken")

    code, out, err = run(root, "upsert", "--json", json.dumps(payload()))

    assert (code, out) == (2, "")
    assert "ieakaso_db.json" in err
    assert db_file(root).read_text() == "{ broken"


def test_set_cover_letter(root: Path):
    write_db(db_file(root), lead())
    path = f"{FOLDER}/{ID}_cover-letter.md"

    code, out, _ = run(root, "set-cover-letter", ID, path)

    assert (code, out) == (0, f"cover letter set for {ID}\n")
    assert json.loads(db_file(root).read_text())["records"][0]["cover_letter"] == path


def test_exit_4_when_the_application_is_not_tracked(root: Path):
    write_db(db_file(root), lead())

    code, _, err = run(root, "set-cover-letter", "nope", "a.md")

    assert code == 4 and "nope" in err


def test_exit_1_for_a_bad_cover_letter_path(root: Path):
    write_db(db_file(root), lead())

    code, _, _ = run(root, "set-cover-letter", ID, "/abs.md")

    assert code == 1


def test_exit_3_when_the_file_changes_while_the_command_runs(root: Path, monkeypatch: pytest.MonkeyPatch):
    write_db(db_file(root), lead())
    real_save = cli.save

    def racing_save(db):
        write_db(db_file(root))  # another process wrote in between
        return real_save(db)

    monkeypatch.setattr(cli, "save", racing_save)

    code, _, err = run(root, "set-cover-letter", ID, "a.md")

    assert code == 3 and "changed" in err


def test_set_company_research(root: Path):
    write_db(db_file(root), lead())
    path = f"{FOLDER}/{ID}_company-research.md"

    code, out, _ = run(root, "set-company-research", ID, path)

    assert (code, out) == (0, f"company research set for {ID}\n")
    assert json.loads(db_file(root).read_text())["records"][0]["company_research"] == path


def test_set_company_research_exits_4_for_an_unknown_id_and_1_for_a_bad_path(root: Path):
    write_db(db_file(root), lead())

    assert run(root, "set-company-research", "nope", "a.md")[0] == 4
    assert run(root, "set-company-research", ID, "/abs.md")[0] == 1


def test_a_version_1_db_is_backfilled_from_the_repo_and_saved_as_version_2(root: Path):
    rec = lead(company_research=f"{FOLDER}/{ID}_company-research.md")
    write_db(db_file(root), {k: v for k, v in rec.items() if k != "company_research"}, version=1)
    (root / rec["company_research"]).parent.mkdir(parents=True, exist_ok=True)
    (root / rec["company_research"]).write_text("x")

    code, _, _ = run(root, "set-cover-letter", ID, f"{FOLDER}/{ID}_cover-letter.md")

    data = json.loads(db_file(root).read_text())
    assert code == 0 and data["meta"] == {"schema_version": 2}
    assert data["records"][0]["company_research"] == rec["company_research"]
