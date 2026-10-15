"""The cv_parser command also writes the Parsed documents of the LinkedIn profile and the reference letters.

The exit code reflects the CV alone; problems with the other documents are warnings (docs/adr/0004-parsed-documents.md).
"""

import json
from pathlib import Path

import pytest
from conftest import TRACKED, snapshot, write_files

from ieakaso.cv_parser import PARSER_VERSION, cli

CV_PATH = "input/documents/cv/cv.txt"
LINKEDIN_PATH = "input/documents/linkedin/Profile.md"
LETTER_PATH = "input/documents/reference_letters/acme.txt"
LINKEDIN_OUT = "input/linkedin.md"
LETTER_OUT = "input/reference-letters/acme.txt.md"


def status(linkedin: str | None = LINKEDIN_PATH, letters: list[str] | None = None) -> str:
    letters = [LETTER_PATH] if letters is None else letters
    return json.dumps({
        "init": {"status": "completed"},
        "documents": {
            "cv": {"status": "found", "path": CV_PATH},
            "linkedin": {"status": "found" if linkedin else "skipped", "path": linkedin},
            "reference_letters": {"status": "found" if letters else "skipped", "paths": letters},
        },
    })


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write_files(root, TRACKED)
    write_files(root, {
        "db/system_status.json": status(),
        CV_PATH: "Jordan Example\nEngineer\n",
        LINKEDIN_PATH: "# Jordan Example\n\nEngineering Manager\n",
        LETTER_PATH: "Jordan led the platform team.\r\n",
    })
    return root


def run(repo: Path, *args: str) -> int:
    return cli.main([*args, "--root", str(repo)])


def documents(repo: Path) -> dict:
    return json.loads((repo / "db/system_status.json").read_text())["documents"]


def set_documents(repo: Path, **changes) -> None:
    data = json.loads((repo / "db/system_status.json").read_text())
    for key, value in changes.items():
        data["documents"][key].update(value)
    (repo / "db/system_status.json").write_text(json.dumps(data))


def test_it_writes_a_parsed_document_for_the_linkedin_profile_and_each_reference_letter(repo: Path):
    assert run(repo) == 0
    assert (repo / LINKEDIN_OUT).read_text() == "# Jordan Example\n\nEngineering Manager\n"
    assert (repo / LETTER_OUT).read_text() == "Jordan led the platform team.\n"


def test_it_records_each_parse_in_the_status_file(repo: Path):
    run(repo)

    linkedin = documents(repo)["linkedin"]["parsed"]
    assert linkedin["source_path"] == LINKEDIN_PATH
    assert linkedin["output_path"] == LINKEDIN_OUT
    assert linkedin["parser_version"] == PARSER_VERSION
    [letter] = documents(repo)["reference_letters"]["parsed"]
    assert letter["source_path"] == LETTER_PATH
    assert letter["output_path"] == LETTER_OUT


def test_up_to_date_parsed_documents_are_left_alone(repo: Path, capsys):
    run(repo)
    before = snapshot(repo)
    capsys.readouterr()

    assert run(repo) == 0
    assert snapshot(repo) == before
    assert "Wrote" not in capsys.readouterr().out


def test_a_changed_source_document_is_parsed_again(repo: Path):
    run(repo)
    (repo / LETTER_PATH).write_text("Jordan led the payments team.\n")

    assert run(repo) == 0
    assert (repo / LETTER_OUT).read_text() == "Jordan led the payments team.\n"


def test_documents_are_parsed_even_when_the_parsed_cv_is_up_to_date(repo: Path):
    run(repo)
    (repo / LINKEDIN_OUT).unlink()

    assert run(repo) == 0
    assert (repo / LINKEDIN_OUT).is_file()


def test_documents_not_recorded_by_init_are_not_parsed(repo: Path):
    write_files(repo, {"input/documents/xing/profile.txt": "Xing profile\n"})
    set_documents(repo, linkedin={"status": "skipped", "path": None}, reference_letters={"paths": []})

    assert run(repo) == 0
    assert not (repo / LINKEDIN_OUT).exists()
    assert not (repo / "input/reference-letters").exists()
    assert sorted(p.name for p in (repo / "input").glob("*.md")) == ["cv.md"]


# --- a document whose source is gone ---------------------------------------------


def test_a_parsed_document_whose_source_is_deleted_is_removed(repo: Path, capsys):
    run(repo)
    (repo / LETTER_PATH).unlink()

    assert run(repo) == 0
    assert not (repo / LETTER_OUT).exists()
    assert "parsed" not in documents(repo)["reference_letters"]
    assert "Removed" in capsys.readouterr().out


def test_a_parsed_document_dropped_by_init_is_removed(repo: Path):
    run(repo)
    set_documents(repo, linkedin={"status": "skipped", "path": None})

    assert run(repo) == 0
    assert not (repo / LINKEDIN_OUT).exists()
    assert "parsed" not in documents(repo)["linkedin"]


def test_a_hand_edited_parsed_document_whose_source_is_gone_is_kept_unless_forced(repo: Path, capsys):
    run(repo)
    (repo / LETTER_OUT).write_text("edited\n")
    (repo / LETTER_PATH).unlink()

    assert run(repo) == 0
    assert (repo / LETTER_OUT).read_text() == "edited\n"
    assert "--force" in capsys.readouterr().out

    assert run(repo, "--force") == 0
    assert not (repo / LETTER_OUT).exists()


# --- hand edits -------------------------------------------------------------------


def test_a_hand_edited_parsed_document_is_not_overwritten(repo: Path, capsys):
    run(repo)
    (repo / LINKEDIN_OUT).write_text("my own version\n")
    (repo / LINKEDIN_PATH).write_text("# Jordan Example\n\nDirector\n")
    capsys.readouterr()

    assert run(repo) == 0
    assert (repo / LINKEDIN_OUT).read_text() == "my own version\n"
    out = capsys.readouterr().out
    assert "Warning:" in out
    assert "--force" in out


def test_force_overwrites_a_hand_edited_parsed_document(repo: Path):
    run(repo)
    (repo / LINKEDIN_OUT).write_text("my own version\n")

    assert run(repo, "--force") == 0
    assert (repo / LINKEDIN_OUT).read_text() == "# Jordan Example\n\nEngineering Manager\n"


# --- unreadable documents ------------------------------------------------------------


def test_an_unreadable_document_is_a_warning_and_never_blocks_the_cv(repo: Path, capsys):
    (repo / LETTER_PATH).write_bytes(b"")

    assert run(repo) == 0
    assert (repo / "input/cv.md").is_file()
    assert not (repo / LETTER_OUT).exists()
    out = capsys.readouterr().out
    assert "Warning:" in out and LETTER_PATH in out
    [letter] = documents(repo)["reference_letters"]["parsed"]
    assert "empty" in letter["unreadable"]


def test_an_unreadable_document_is_reported_once_until_it_changes(repo: Path, capsys):
    (repo / LETTER_PATH).write_bytes(b"")
    run(repo)
    capsys.readouterr()

    run(repo)
    assert "Warning:" not in capsys.readouterr().out

    (repo / LETTER_PATH).write_bytes(b"   \n")
    run(repo)
    assert "Warning:" in capsys.readouterr().out


def test_a_document_that_becomes_unreadable_loses_its_parsed_document(repo: Path):
    run(repo)
    (repo / LETTER_PATH).write_bytes(b"")

    assert run(repo) == 0
    assert not (repo / LETTER_OUT).exists()


def test_documents_are_parsed_even_when_the_cv_fails(repo: Path):
    (repo / CV_PATH).write_bytes(b"")

    assert run(repo) == 1
    assert (repo / LINKEDIN_OUT).is_file()
    assert documents(repo)["linkedin"]["parsed"]["output_path"] == LINKEDIN_OUT
