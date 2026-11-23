"""The cover_letter echoes command: the draft sentences most like a Job ad sentence, as smells for the agents. Fake repo
only; the ad and the letters are synthetic, shaped like the Echoes issue #96 describes."""

import io
from pathlib import Path

import pytest

from ieakaso.cover_letter import cli

ID = "acme_engineering-manager_2026-11-23"

AD = """# Job ad: Engineering Manager @ Acme

> **Job ad:** https://jobs.acme.example/1 | **Date read:** 2026-11-23 | **Read by:** WebFetch

## About the role
You will lead the Checkout domain, with several subteams.
The platform is expanding, and you will decide both what it ships and how it runs.
You stay near the code, because in a market that moves this fast, sound product calls rest on knowing the engineering trade-offs.
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    folder = tmp_path / "repo" / "output" / "applications" / ID
    (folder / "rounds").mkdir(parents=True)
    (folder / f"{ID}_job-ad.md").write_text(AD)
    return tmp_path / "repo"


def write_ad(root: Path, text: str):
    (root / "output" / "applications" / ID / f"{ID}_job-ad.md").write_text(text)


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
    write_draft(root, "Your platform is expanding, and its lead will decide both what it ships and how it runs.")

    code, out, _ = run(root, ID, "1")

    assert code == 0
    assert "letter: Your platform is expanding, and its lead will decide both what it ships and how it runs." in out
    assert "ad: The platform is expanding, and you will decide both what it ships and how it runs." in out


def test_flags_an_ad_sentence_restated_as_the_candidates_own_thought(root: Path):
    write_draft(
        root,
        "The role also keeps me near the code; in a market that moves this fast, sound product calls rest on the "
        "engineering trade-offs.",
    )

    _, out, _ = run(root, ID, "1")

    assert "possible Echoes in round 1: 1" in out
    assert "ad: You stay near the code, because in a market that moves this fast" in out


def test_a_hard_wrapped_ad_sentence_is_read_whole(root: Path):
    write_ad(
        root, AD + "Our merchants want payouts\nthe same day, so you will own\nthe settlement pipeline end to end.\n"
    )
    write_draft(root, "Your merchants want same-day payouts, and owning the settlement pipeline end to end is the job.")

    _, out, _ = run(root, ID, "1")

    assert "ad: Our merchants want payouts the same day, so you will own the settlement pipeline end to end.\n" in out


def test_a_draft_without_echoes_prints_none(root: Path):
    write_draft(root, "At my last company I grew a team from 4 to 11 engineers and cut release time from 18 days to 6.")

    code, out, err = run(root, ID, "1")

    assert (code, out, err) == (0, "no possible Echoes in round 1\n", "")


def test_a_sentence_that_only_reuses_the_ads_terms_is_not_an_echo(root: Path):
    write_draft(root, "I led the Checkout domain's mobile work.")

    code, out, _ = run(root, ID, "1")

    assert code == 0
    assert out == "no possible Echoes in round 1\n"


def test_the_letters_header_lines_are_not_echoes(root: Path):
    write_ad(root, AD + "Job title:** Engineering Manager – Checkout Platform (m/f/d)\n")
    write_draft(root, "**Application: Engineering Manager – Checkout Platform (m/f/d)**\n\nI build teams.")

    _, out, _ = run(root, ID, "1")

    assert out == "no possible Echoes in round 1\n"


def test_an_ad_sentence_ending_in_a_quote_is_its_own_sentence(root: Path):
    write_ad(root, AD + '"Build the checkout customers trust with their money." The domain owns the app and the API.\n')
    write_draft(root, "I want to build the checkout customers trust with their money.")

    _, out, _ = run(root, ID, "1")

    assert 'ad: "Build the checkout customers trust with their money."\n' in out


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


def test_a_relative_root_resolves_against_the_current_folder(root: Path):
    write_draft(root, "I build teams.")
    out, err = io.StringIO(), io.StringIO()

    code = cli.main(["--root", "repo", "echoes", ID, "1"], cwd=root.parent, out=out, err=err)

    assert (code, out.getvalue()) == (0, "no possible Echoes in round 1\n")


def test_without_a_root_it_finds_the_repo_from_the_current_folder(root: Path):
    (root / "ai" / "skills" / "ieakaso").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname = "ieakaso"\n')
    write_draft(root, "I build teams.")
    out, err = io.StringIO(), io.StringIO()

    code = cli.main(["echoes", ID, "1"], cwd=root / "output", out=out, err=err)

    assert (code, out.getvalue(), err.getvalue()) == (0, "no possible Echoes in round 1\n", "")


def test_inflected_forms_of_the_ads_words_still_match(root: Path):
    write_ad(root, AD + "You will shape strategy, decide priorities, manage stakeholders and drive delivery.\n")
    write_draft(root, "Shaping strategy, deciding priorities, managing stakeholders and driving delivery is my job.")

    _, out, _ = run(root, ID, "1")

    assert "ad: You will shape strategy, decide priorities, manage stakeholders and drive delivery.\n" in out
