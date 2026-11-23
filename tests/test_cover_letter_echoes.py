"""The cover_letter echoes command: the draft sentences most like a Job ad sentence, as smells for the agents. Fake repo
only; the examples are the ones in issue #96."""

import io
from pathlib import Path

import pytest

from ieakaso.cover_letter import cli

ID = "acme_engineering-manager_2026-11-23"

AD = """# Job ad: Engineering Manager @ Acme

> **Job ad:** https://jobs.acme.example/1 | **Date read:** 2026-11-23 | **Read by:** WebFetch

## About the role
You will lead the Customer Experience domain, with several subteams.
The team is growing, and you will shape both what it builds and how it works.
You stay close to the technology, because in a field that changes this quickly, good leadership decisions depend on understanding the technical details.
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    folder = tmp_path / "repo" / "output" / "applications" / ID
    (folder / "rounds").mkdir(parents=True)
    (folder / f"{ID}_job-ad.md").write_text(AD)
    return tmp_path / "repo"


def write_draft(root: Path, body: str, n: int = 1):
    path = root / "output" / "applications" / ID / "rounds" / f"round-{n}_draft.md"
    path.write_text(
        f"## Draft\n\nDear Hiring Team,\n\n{body}\n\nKind regards,\n\n## Notes for the Assistant\n- **Word count:** 50\n"
    )


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), "echoes", *argv], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_flags_an_ad_sentence_handed_back_with_the_pronouns_swapped(root: Path):
    write_draft(root, "Your team is growing, and its lead will shape both what it builds and how it works.")

    code, out, _ = run(root, ID, "1")

    assert code == 0
    assert "letter: Your team is growing, and its lead will shape both what it builds and how it works." in out
    assert "ad: The team is growing, and you will shape both what it builds and how it works." in out


def test_flags_an_ad_sentence_restated_as_the_candidates_own_thought(root: Path):
    write_draft(
        root,
        "The role also keeps me close to the technology; in a field that changes this quickly, good leadership "
        "decisions depend on the technical details.",
    )

    _, out, _ = run(root, ID, "1")

    assert "possible Echoes in round 1: 1" in out
    assert "ad: You stay close to the technology, because in a field that changes this quickly" in out


def test_a_sentence_that_only_reuses_the_ads_terms_is_not_an_echo(root: Path):
    write_draft(root, "I led the Customer Experience domain's mobile work.")

    code, out, _ = run(root, ID, "1")

    assert code == 0
    assert out == "no possible Echoes in round 1\n"


def test_a_missing_draft_exits_1(root: Path):
    code, out, err = run(root, ID, "2")

    assert (code, out) == (1, "")
    assert "round-2_draft.md" in err


def test_a_file_that_is_not_a_draft_exits_1(root: Path):
    (root / "output" / "applications" / ID / "rounds" / "round-1_draft.md").write_text("Just a letter.\n")

    code, _, err = run(root, ID, "1")

    assert code == 1
    assert "not a draft" in err


def test_a_missing_job_ad_file_exits_3(root: Path):
    write_draft(root, "Body.")
    (root / "output" / "applications" / ID / f"{ID}_job-ad.md").unlink()

    code, _, err = run(root, ID, "1")

    assert code == 3
    assert "Job ad file" in err


def test_a_missing_application_folder_exits_3(root: Path):
    code, _, err = run(root, "nobody_nothing_2026-01-01", "1")

    assert code == 3
    assert "no Application folder" in err


def test_the_letters_header_lines_are_not_echoes(root: Path):
    ad = root / "output" / "applications" / ID / f"{ID}_job-ad.md"
    ad.write_text(AD + "Job title:** Engineering Manager – Customer Experience (m/f/d)\n")
    write_draft(root, "**Application: Engineering Manager – Customer Experience (m/f/d)**\n\nI build teams.")

    _, out, _ = run(root, ID, "1")

    assert out == "no possible Echoes in round 1\n"


def test_an_ad_sentence_ending_in_a_quote_is_its_own_sentence(root: Path):
    ad = root / "output" / "applications" / ID / f"{ID}_job-ad.md"
    ad.write_text(
        AD + '"Lead the team that decides how customers meet the product." The domain owns the app and the assistant.\n'
    )
    write_draft(root, "I want to lead the team that decides how customers meet the product.")

    _, out, _ = run(root, ID, "1")

    assert 'ad: "Lead the team that decides how customers meet the product."\n' in out
