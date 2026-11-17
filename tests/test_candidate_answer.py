"""The candidate_answer command: append the candidate's own answer, word for word, to one of their memory files. Fake
repo only."""

import io
from datetime import date
from pathlib import Path

import pytest

from ieakaso.candidate_answer import cli

ID = "acme_senior-backend-engineer_2026-10-10"
TODAY = date(2026, 11, 17)
HEADING = f"## Added 2026-11-17 ({ID})"


class Stdin(io.StringIO):
    def __init__(self, text: str, tty: bool = False):
        super().__init__(text)
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "output" / "applications" / ID).mkdir(parents=True)
    (root / "input" / "candidate").mkdir(parents=True)
    (root / "input" / "candidate" / "professional-experience-extended.md").write_text("# Experience\n\nBabbel.\n")
    return root


def memory(root: Path, name: str = "professional-experience-extended.md") -> Path:
    return root / "input" / "candidate" / name


def run(root: Path, *argv: str, stdin: str = "", tty: bool = False) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), *argv], today=TODAY, stdin=Stdin(stdin, tty), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_append_adds_the_answer_word_for_word_under_a_dated_heading(root: Path):
    answer = 'We cut "AI tooling" spend by 30%,\nfrom EUR 10k to EUR 7k a month.\n'

    code, out, err = run(root, "append", "professional-experience-extended.md", ID, stdin=answer)

    assert (code, err) == (0, "")
    assert out == f"answer added to input/candidate/professional-experience-extended.md for {ID}\n"
    assert memory(root).read_text() == f"# Experience\n\nBabbel.\n\n{HEADING}\n\n{answer}"


def test_a_file_without_a_final_newline_still_gets_a_blank_line_before_the_heading(root: Path):
    memory(root).write_text("# Experience")

    run(root, "append", "professional-experience-extended.md", ID, stdin="Thirty percent.")

    assert memory(root).read_text() == f"# Experience\n\n{HEADING}\n\nThirty percent.\n"


def test_a_missing_memory_file_is_created(root: Path):
    code, _, _ = run(root, "append", "presentation.md", ID, stdin="I lead platform teams.\n")

    assert code == 0
    assert memory(root, "presentation.md").read_text() == f"{HEADING}\n\nI lead platform teams.\n"


@pytest.mark.parametrize(
    "name",
    ["writing-style.md", "deliberate-differences.md", "../config.yml", "documents/cv/cv.pdf", "notes.md"],
)
def test_only_the_three_memory_files_take_an_answer(root: Path, name: str):
    code, out, err = run(root, "append", name, ID, stdin="Thirty percent.\n")

    assert (code, out) == (2, "")
    assert err == (
        f"{name} can't take an answer: only professional-experience-extended.md, presentation.md "
        "and professional-self-reflection.md\n"
    )


@pytest.mark.parametrize(("text", "tty"), [("", False), ("  \n\n", False), ("", True)])
def test_no_text_on_stdin_changes_nothing(root: Path, text: str, tty: bool):
    code, out, err = run(root, "append", "professional-experience-extended.md", ID, stdin=text, tty=tty)

    assert (code, out) == (1, "")
    assert err == "no answer: give the candidate's text on standard input\n"
    assert memory(root).read_text() == "# Experience\n\nBabbel.\n"


def test_an_unknown_application_changes_nothing(root: Path):
    code, _, err = run(root, "append", "presentation.md", "nobody_nothing_2026-01-01", stdin="Hi.\n")

    assert code == 3
    assert err == "no Application nobody_nothing_2026-01-01: output/applications/nobody_nothing_2026-01-01 is missing\n"
    assert not memory(root, "presentation.md").exists()
