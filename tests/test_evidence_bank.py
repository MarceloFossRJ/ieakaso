"""The evidence_bank command: stamp and check the Sources section of an Evidence bank. Fake repo only."""

import hashlib
import io
from pathlib import Path

import pytest

from ieakaso.evidence_bank import cli
from ieakaso.evidence_bank.sources import source_files

ID = "acme_senior-backend-engineer_2026-10-10"
BODY = "# Evidence bank: Senior Backend Engineer @ Acme\n\n## Requirement evidence\n\n- Go: 6 years (cv.md)\n"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for path, text in {
        "config.yml": "name: Jane\n",
        "input/parsed-documents/cv.md": "# CV\n",
        "input/parsed-documents/linkedin.md": "# LinkedIn\n",
        "input/candidate/presentation.md": "Hi\n",
        "input/candidate/writing-style.md": "Plain\n",
    }.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    (root / "output" / "applications" / ID).mkdir(parents=True)
    return root


def bank(root: Path) -> Path:
    return root / "output" / "applications" / ID / f"{ID}_evidence-bank.md"


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), *argv], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_the_sources_are_the_existing_files_of_the_personal_knowledge_base_the_bank_is_built_from(root: Path):
    assert [str(p) for p in source_files(root)] == [
        "config.yml",
        "input/parsed-documents/cv.md",
        "input/parsed-documents/linkedin.md",
        "input/candidate/presentation.md",
    ]  # writing-style.md is the voice, read by the Applicant itself; missing optional files are left out


def test_stamp_appends_the_sources_section_with_each_file_hash(root: Path):
    bank(root).write_text(BODY)

    code, out, err = run(root, "stamp", ID)

    assert (code, err) == (0, "")
    assert out == f"evidence bank stamped for {ID}: 4 source files\n"
    text = bank(root).read_text()
    assert text.startswith(BODY.rstrip("\n") + "\n\n## Sources\n")
    assert f"| `config.yml` | `{sha('name: Jane\n')}` |" in text
    assert f"| `input/parsed-documents/cv.md` | `{sha('# CV\n')}` |" in text


def test_stamp_replaces_an_old_sources_section(root: Path):
    bank(root).write_text(BODY)
    run(root, "stamp", ID)
    (root / "input/parsed-documents/cv.md").write_text("# CV v2\n")

    run(root, "stamp", ID)

    text = bank(root).read_text()
    assert text.count("## Sources") == 1
    assert sha("# CV v2\n") in text and sha("# CV\n") not in text


def test_check_says_current_for_a_freshly_stamped_bank(root: Path):
    bank(root).write_text(BODY)
    run(root, "stamp", ID)

    assert run(root, "check", ID) == (0, f"evidence bank is current for {ID}\n", "")


def test_check_exits_1_and_names_changed_added_and_removed_files(root: Path):
    bank(root).write_text(BODY)
    run(root, "stamp", ID)
    (root / "input/parsed-documents/cv.md").write_text("# CV v2\n")
    (root / "input/candidate/professional-self-reflection.md").write_text("I want\n")
    (root / "input/parsed-documents/linkedin.md").unlink()

    code, out, _ = run(root, "check", ID)

    assert code == 1
    assert out.splitlines() == [
        "Changed: input/parsed-documents/cv.md",
        "Added: input/candidate/professional-self-reflection.md",
        "Removed: input/parsed-documents/linkedin.md",
    ]


def test_check_exits_2_when_there_is_no_bank_or_it_has_no_sources_section(root: Path):
    code, _, err = run(root, "check", ID)
    assert code == 2 and "no Evidence bank" in err

    bank(root).write_text(BODY)
    code, _, err = run(root, "check", ID)
    assert code == 2 and "no Sources section" in err


def test_stamp_exits_2_without_a_bank_file(root: Path):
    code, _, err = run(root, "stamp", ID)

    assert code == 2 and "no Evidence bank" in err


def test_exit_3_when_the_application_folder_is_missing(root: Path):
    assert run(root, "check", "nope")[0] == 3
    assert run(root, "stamp", "nope")[0] == 3
