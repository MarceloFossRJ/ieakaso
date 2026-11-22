"""The cover_letter assemble command: the letter and the review log built from the Round files. Fake repo only."""

import io
from datetime import date
from pathlib import Path

import pytest

from ieakaso.cover_letter import cli
from ieakaso.cover_letter.assemble import Outcome, Round, review_log

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


PLAN = "### Needs\n\nPlan text."


def write_plan(root: Path, text: str = PLAN):
    rounds = folder(root) / "rounds"
    rounds.mkdir(exist_ok=True)
    (rounds / "plan.md").write_text(text)


def write_round(
    root: Path,
    n: int,
    score: int,
    refused: str = "None",
    language: str = "English",
    draft: bool = True,
    adapted: str = "None",
    departures: str = "None",
):
    """Writes Round n's files, and the Letter plan when there is none yet."""
    rounds = folder(root) / "rounds"
    rounds.mkdir(exist_ok=True)
    if not (rounds / "plan.md").exists():
        write_plan(root)
    if draft:
        (rounds / f"round-{n}_draft.md").write_text(
            f"## Draft\n\nLetter {n}  \nBody {n}.\n\n## Notes for the Assistant\n"
            f"- **Word count:** 300\n- **Language:** {language}\n- **Refused suggestions:** {refused}\n"
            f"- **Missing inputs:** None\n- **Motivation left out:** None\n"
            f"- **Plan departures:** {departures}\n- **Adapted for voice:** {adapted}\n"
        )
    (rounds / f"round-{n}_review.md").write_text(
        f"**Domain:** fintech\n\n## Review score: {score}/100\n\nReview {n} text.\n\n## Handover decision\n\nBack\n"
    )


def review(n: int) -> str:
    score = {1: 70, 2: 88, 3: 81}[n]
    return f"**Domain:** fintech\n\n## Review score: {score}/100\n\nReview {n} text.\n\n## Handover decision\n\nBack"


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    flag = [] if "--motivation" in argv else ["--motivation", "none"]
    code = cli.main(["--root", str(root), "assemble", ID, *argv, *flag], today=TODAY, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_assembles_the_best_draft_when_it_is_not_the_last(root: Path):
    write_round(root, 1, 70)
    write_round(root, 2, 88, refused='"Add a number": no file has one')
    write_round(root, 3, 81)

    code, out, err = run(
        root, "--rounds", "3", "--final", "2", "--exit", "3 Rounds", "--reason", "Round 2 scored highest."
    )

    notes = "\n\n### Adapted for voice\n\nNone\n\n### Plan departures\n\nNone\n\n"
    assert (code, err) == (0, "")
    assert out == "Letter 2  \nBody 2.\n"
    assert (folder(root) / f"{ID}_cover-letter.md").read_text() == "Letter 2  \nBody 2.\n"
    assert (folder(root) / f"{ID}_cover-letter-review.md").read_text() == (
        "# Cover letter review log: Senior Backend Engineer @ Acme\n\n"
        f"> **Date:** 2026-10-15 | **Job ad:** {URL} | **Company research:** none | **Personal motivation:** none | **Final Review score:** 88/100"
        " | **Rounds:** 3 | **Exit:** 3 Rounds\n\n"
        "After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.\n\n"
        "**Final letter:** Round 2's draft. It scored highest; later drafts scored lower.\n\n"
        "**Language:** English\n\n"
        "## Letter plan\n\n### Needs\n\nPlan text.\n\n"
        "## Round 1\n\n**Review score:** 70/100\n\n### Draft\n\nLetter 1  \nBody 1.\n\n"
        "### Review\n\n"
        + review(1)
        + "\n\n### Refused suggestions\n\nNone"
        + notes
        + "## Round 2\n\n**Review score:** 88/100\n\n### Draft\n\nLetter 2  \nBody 2.\n\n"
        "### Review\n\n"
        + review(2)
        + '\n\n### Refused suggestions\n\n"Add a number": no file has one'
        + notes
        + "## Round 3\n\n**Review score:** 81/100\n\n### Draft\n\nLetter 3  \nBody 3.\n\n"
        "### Review\n\n"
        + review(3)
        + "\n\n### Refused suggestions\n\nNone"
        + notes
        + "## Exit reason\n\nRound 2 scored highest.\n"
    )


def test_an_exit_of_five_rounds_is_now_an_error(root: Path):
    write_round(root, 1, 70)

    code, _, err = run(root, "--rounds", "1", "--final", "1", "--exit", "5 Rounds", "--reason", "y")

    assert code == 1
    assert "--exit" in err
    assert_nothing_written(root)


def test_a_missing_plan_is_an_error_and_writes_nothing(root: Path):
    write_round(root, 1, 70)
    (folder(root) / "rounds" / "plan.md").unlink()

    code, out, err = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert (code, out) == (1, "")
    assert "plan.md" in err
    assert_nothing_written(root)


def test_an_empty_plan_is_an_error(root: Path):
    write_plan(root, "  \n\n")
    write_round(root, 1, 70)

    code, _, err = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 1
    assert "plan.md" in err
    assert_nothing_written(root)


def test_a_multi_line_adaptation_is_kept_whole(root: Path):
    adapted = '"Replace with: I led and grew the team"\n  became "I led the team and grew it"'
    write_round(root, 1, 92, adapted=adapted)

    code, _, _ = run(root, "--rounds", "1", "--final", "1", "--exit", "Review score 90 or above", "--reason", "92.")

    assert code == 0
    assert (
        '### Adapted for voice\n\n"Replace with: I led and grew the team"\n  became "I led the team and grew it"\n\n'
        "### Plan departures\n\nNone\n"
    ) in log_of(root)


def test_a_round_past_the_cap_after_the_candidates_answers_assembles(root: Path):
    for n in range(1, 5):
        write_round(root, n, 80 + n)

    code, _, _ = run(
        root, "--rounds", "4", "--final", "4", "--exit", "Round after the candidate's answers", "--reason", "y"
    )

    assert code == 0
    assert "## Round 4\n" in log_of(root)


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
        root,
        "--rounds",
        "2",
        "--final",
        "2",
        "--requested",
        "2",
        "--exit",
        "change requested by the candidate",
        "--reason",
        "r",
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


def test_an_unreadable_company_research_file_is_an_application_error(root: Path):
    write_round(root, 1, 70)
    research = folder(root) / f"{ID}_company-research.md"
    research.write_text("**Date researched:** 2026-11-01\n")
    research.chmod(0)

    try:
        code, _, err = run(root, "--rounds", "1", "--final", "1", "--exit", "Plateau", "--reason", "y")
    finally:
        research.chmod(0o644)

    assert code == 3
    assert "Company research file" in err
    assert_nothing_written(root)


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


@pytest.mark.parametrize("label", ["Language", "Refused suggestions", "Adapted for voice", "Plan departures"])
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
        root,
        "--rounds",
        "2",
        "--final",
        "2",
        "--requested",
        "2",
        "--exit",
        "change requested by the candidate",
        "--reason",
        "y",
    )

    log = (folder(root) / f"{ID}_cover-letter-review.md").read_text()
    assert code == 0
    assert out == "Letter 2  \nBody 2.\n"
    assert "**Final Review score:** 70/100" in log
    assert "**Final letter:** Round 2's draft.\n" in log


@pytest.mark.parametrize(
    "line", ["Review score: 70/100", "### **Review score:** 70/100", "  ## Review score: 70/100  "]
)
def test_the_review_score_line_is_read_tolerantly(root: Path, line: str):
    write_round(root, 1, 99)
    (folder(root) / "rounds" / "round-1_review.md").write_text(f"**Domain:** x\n\n{line}\n")

    code, _, _ = run(root, "--rounds", "1", "--final", "1", *ARGS)

    assert code == 0
    assert "**Final Review score:** 70/100" in (folder(root) / f"{ID}_cover-letter-review.md").read_text()


def test_an_earlier_round_without_a_language_line_is_fine(root: Path):
    write_round(root, 1, 70)
    path = folder(root) / "rounds" / "round-1_draft.md"
    path.write_text("\n".join(line for line in path.read_text().splitlines() if "**Language:**" not in line) + "\n")
    write_round(root, 2, 80)

    code, _, _ = run(root, "--rounds", "2", "--final", "2", *ARGS)

    assert code == 0


def test_review_log_format_without_the_filesystem():
    played = [
        Round(1, "Letter 1", "## Review score: 80/100", 80, "None", "None", "None", None, Path("r1")),
        Round(2, "Letter 2", "## Review score: 75/100", 75, "None", "None", "None", "German", Path("r2")),
    ]
    outcome = Outcome(2, 2, (2,), "change requested by the candidate", "The candidate asked.", motivated=True)

    log = review_log("Dev @ Acme", "pasted text", "none", TODAY, outcome, "Plan.", played)

    assert "**Language:** German\n\n## Letter plan\n\nPlan.\n\n## Round 1\n" in log
    assert log.startswith("# Cover letter review log: Dev @ Acme\n\n> **Date:** 2026-10-15 | **Job ad:** pasted text")
    assert "**Final Review score:** 75/100 | **Rounds:** 2 | **Exit:** change requested by the candidate" in log
    assert "| **Company research:** none | **Personal motivation:** used |" in log
    assert "**Language:** German\n" in log
    assert "## Round 2 (requested by the candidate)\n" in log
    assert log.endswith("## Exit reason\n\nThe candidate asked.\n")


def log_of(root: Path) -> str:
    return (folder(root) / f"{ID}_cover-letter-review.md").read_text()


def finish(root: Path, *flag: str) -> tuple[int, str, str]:
    write_round(root, 1, 92)
    return run(root, "--rounds", "1", "--final", "1", "--exit", "Review score 90 or above", "--reason", "92.", *flag)


@pytest.mark.parametrize("value", ["used", "none"])
def test_the_header_names_whether_a_personal_motivation_was_used(root: Path, value: str):
    assert finish(root, "--motivation", value)[0] == 0
    assert f"| **Personal motivation:** {value} |" in log_of(root)


def test_the_motivation_flag_is_required_and_takes_used_or_none(root: Path):
    write_round(root, 1, 92)
    base = ("--rounds", "1", "--final", "1", "--exit", "Review score 90 or above", "--reason", "92.")
    out, err = io.StringIO(), io.StringIO()

    with pytest.raises(SystemExit):
        cli.main(["--root", str(root), "assemble", ID, *base], today=TODAY, out=out, err=err)
    with pytest.raises(SystemExit):
        cli.main(["--root", str(root), "assemble", ID, *base, "--motivation", "maybe"], today=TODAY, out=out, err=err)
    assert not (folder(root) / f"{ID}_cover-letter.md").exists()


def test_the_assembler_ignores_the_tracker_db(root: Path):
    (root / "db").mkdir()
    (root / "db" / "ieakaso_db.json").write_text("not json")

    assert finish(root, "--motivation", "used")[0] == 0
    assert "| **Personal motivation:** used |" in log_of(root)
