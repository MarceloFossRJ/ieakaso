"""The cover_letter assemble command: the letter and the review log built from the Round files. Fake repo only."""

import io
from datetime import date
from pathlib import Path

import pytest

from ieakaso.cover_letter import cli

TODAY = date(2026, 10, 15)
ID = "acme_senior-backend-engineer_2026-10-10"
URL = "https://jobs.acme.example/123"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    folder = tmp_path / "repo" / "output" / "applications" / ID
    folder.mkdir(parents=True)
    (folder / f"{ID}_job-ad.md").write_text(
        f"# Job ad: Senior Backend Engineer @ Acme\n\n> **Job ad:** {URL} | **Date read:** 2026-10-10 | **Read by:** WebFetch\n\nText\n"
    )
    return tmp_path / "repo"


def folder(root: Path) -> Path:
    return root / "output" / "applications" / ID


def write_round(root: Path, n: int, score: int, refused: str = "None", language: str = "English", draft: bool = True):
    rounds = folder(root) / "rounds"
    rounds.mkdir(exist_ok=True)
    if draft:
        (rounds / f"round-{n}_draft.md").write_text(
            f"## Draft\n\nLetter {n}  \nBody {n}.\n\n## Notes for the Assistant\n"
            f"- **Word count:** 300\n- **Language:** {language}\n- **Refused suggestions:** {refused}\n"
            f"- **Missing inputs:** None\n- **Conflicts:** None\n"
        )
    (rounds / f"round-{n}_review.md").write_text(
        f"**Domain:** fintech\n\n## Review score: {score}/100\n\nReview {n} text.\n\n## Handover decision\n\nBack\n"
    )


def review(n: int) -> str:
    score = {1: 70, 2: 88, 3: 81}[n]
    return f"**Domain:** fintech\n\n## Review score: {score}/100\n\nReview {n} text.\n\n## Handover decision\n\nBack"


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), "assemble", ID, *argv], today=TODAY, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_assembles_the_best_draft_when_it_is_not_the_last(root: Path):
    write_round(root, 1, 70)
    write_round(root, 2, 88, refused='"Add a number": no file has one')
    write_round(root, 3, 81)

    code, out, err = run(root, "--rounds", "3", "--final", "2", "--exit", "5 Rounds", "--reason", "Round 2 scored highest.")

    assert (code, err) == (0, "")
    assert out == "Letter 2  \nBody 2.\n"
    assert (folder(root) / f"{ID}_cover-letter.md").read_text() == "Letter 2  \nBody 2.\n"
    assert (folder(root) / f"{ID}_cover-letter-review.md").read_text() == (
        "# Cover letter review log: Senior Backend Engineer @ Acme\n\n"
        f"> **Date:** 2026-10-15 | **Job ad:** {URL} | **Company research:** none | **Final Review score:** 88/100"
        " | **Rounds:** 3 | **Exit:** 5 Rounds\n\n"
        "After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.\n\n"
        "**Final letter:** Round 2's draft. It scored highest; later drafts scored lower.\n\n"
        "**Language:** English\n\n"
        "## Round 1\n\n**Review score:** 70/100\n\n### Draft\n\nLetter 1  \nBody 1.\n\n"
        "### Review\n\n" + review(1) + "\n\n### Refused suggestions\n\nNone\n\n"
        "## Round 2\n\n**Review score:** 88/100\n\n### Draft\n\nLetter 2  \nBody 2.\n\n"
        "### Review\n\n" + review(2) + '\n\n### Refused suggestions\n\n"Add a number": no file has one\n\n'
        "## Round 3\n\n**Review score:** 81/100\n\n### Draft\n\nLetter 3  \nBody 3.\n\n"
        "### Review\n\n" + review(3) + "\n\n### Refused suggestions\n\nNone\n\n"
        "## Exit reason\n\nRound 2 scored highest.\n"
    )


def test_the_last_draft_as_final_has_no_scored_highest_line_and_the_research_date_is_named(root: Path):
    write_round(root, 1, 92)
    (folder(root) / f"{ID}_company-research.md").write_text(
        "# Company research: Acme (for X)\n\n> **Date researched:** 2026-10-01 | **Company:** Acme\n"
    )

    code, _, _ = run(root, "--rounds", "1", "--final", "1", "--exit", "Review score 90 or above", "--reason", "92.")

    log = (folder(root) / f"{ID}_cover-letter-review.md").read_text()
    assert code == 0
    assert "**Company research:** 2026-10-01 |" in log
    assert "**Final letter:** Round 1's draft.\n\n" in log


def test_a_round_requested_by_the_candidate_is_marked_in_its_heading(root: Path):
    write_round(root, 1, 85)
    write_round(root, 2, 80)

    code, _, _ = run(
        root, "--rounds", "2", "--final", "2", "--requested", "2", "--exit", "change requested by the candidate", "--reason", "r"
    )

    log = (folder(root) / f"{ID}_cover-letter-review.md").read_text()
    assert code == 0
    assert "## Round 1\n" in log
    assert "## Round 2 (requested by the candidate)\n" in log


def test_a_missing_round_file_is_an_error_and_writes_nothing(root: Path):
    write_round(root, 1, 70)
    write_round(root, 2, 80, draft=False)

    code, out, err = run(root, "--rounds", "2", "--final", "1", "--exit", "Plateau", "--reason", "y")

    assert code == 1
    assert out == ""
    assert "round-2_draft.md" in err
    assert not (folder(root) / f"{ID}_cover-letter.md").exists()
    assert not (folder(root) / f"{ID}_cover-letter-review.md").exists()


def test_an_unknown_application_is_an_error(root: Path):
    (folder(root) / f"{ID}_job-ad.md").unlink()

    code, _, err = run(root, "--rounds", "1", "--final", "1", "--exit", "Plateau", "--reason", "y")

    assert code == 3
    assert "job-ad" in err


def test_a_final_round_outside_the_rounds_is_an_error(root: Path):
    write_round(root, 1, 70)

    code, _, err = run(root, "--rounds", "1", "--final", "2", "--exit", "Plateau", "--reason", "y")

    assert code == 1
    assert "--final" in err


ARGS = ("--exit", "Plateau", "--reason", "y")


def assert_nothing_written(root: Path):
    assert not (folder(root) / f"{ID}_cover-letter.md").exists()
    assert not (folder(root) / f"{ID}_cover-letter-review.md").exists()


def test_a_requested_round_out_of_range_is_an_error(root: Path):
    write_round(root, 1, 70)

    code, _, err = run(root, "--rounds", "1", "--final", "1", "--requested", "2", *ARGS)

    assert code == 1
    assert "--requested" in err
    assert_nothing_written(root)


def test_a_draft_without_a_draft_heading_is_an_error(root: Path):
    write_round(root, 1, 70)
    (folder(root) / "rounds" / "round-1_draft.md").write_text("Just a letter\n")

    code, _, err = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 1
    assert "not a draft" in err
    assert_nothing_written(root)


def test_a_review_without_a_score_line_is_an_error(root: Path):
    write_round(root, 1, 70)
    (folder(root) / "rounds" / "round-1_review.md").write_text("**Domain:** x\n")

    code, _, err = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 1
    assert "Review score" in err
    assert_nothing_written(root)


@pytest.mark.parametrize("label", ["Language", "Refused suggestions"])
def test_notes_missing_a_field_are_an_error(root: Path, label: str):
    write_round(root, 1, 70)
    path = folder(root) / "rounds" / "round-1_draft.md"
    path.write_text("\n".join(line for line in path.read_text().splitlines() if f"**{label}:**" not in line) + "\n")

    code, _, err = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 1
    assert label in err
    assert_nothing_written(root)


def test_an_exit_outside_the_fixed_set_is_an_error(root: Path):
    write_round(root, 1, 70)

    code, _, err = run(root, "--rounds", "1", "--final", "1", "--exit", "tired", "--reason", "y")

    assert code == 1
    assert "--exit" in err
    assert_nothing_written(root)


def test_a_requested_round_that_scores_lower_can_be_final(root: Path):
    write_round(root, 1, 85)
    write_round(root, 2, 70)

    code, out, _ = run(
        root, "--rounds", "2", "--final", "2", "--requested", "2", "--exit", "change requested by the candidate", "--reason", "y"
    )

    log = (folder(root) / f"{ID}_cover-letter-review.md").read_text()
    assert code == 0
    assert out == "Letter 2  \nBody 2.\n"
    assert "**Final Review score:** 70/100" in log
    assert "**Final letter:** Round 2's draft.\n" in log


@pytest.mark.parametrize("line", ["Review score: 70/100", "### **Review score:** 70/100", "  ## Review score: 70/100  "])
def test_the_review_score_line_is_read_tolerantly(root: Path, line: str):
    write_round(root, 1, 99)
    (folder(root) / "rounds" / "round-1_review.md").write_text(f"**Domain:** x\n\n{line}\n")

    code, _, _ = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 0
    assert "**Final Review score:** 70/100" in (folder(root) / f"{ID}_cover-letter-review.md").read_text()
