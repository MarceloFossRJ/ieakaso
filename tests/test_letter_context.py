"""The letter_context command: the parts of the Job analysis and the Company research the Cover letter agents read.
Fake repo only."""

import io
from datetime import date
from pathlib import Path

import pytest

from ieakaso.letter_context import cli

ID = "acme_senior-backend-engineer_2026-10-10"
TODAY = date(2026, 11, 17)

ANALYSIS = """# Job analysis: Senior Backend Engineer @ Acme

> **Score:** 82/100 | **Verdict:** Apply

## Strengths

- Six years of Go (`input/parsed-documents/cv.md`)

## Weaknesses

- No Kafka in the CV

## The job ad

- Backend role

## Scorecard

| Dimension | Score |
|---|---|
| Must-haves | 80 |

## Requirement match

| Requirement | Evidence |
|---|---|
| Go | 6 years |

## Screener risks

- Two short stints

## CV under-sells

- The payments migration (`input/candidate/professional-experience-extended.md`)

## Conflicts with the CV

- None

## Gaps to close

- Kafka: say what comes closest

## Letter coaching

- **Strengths to amplify:** six years of Go (`input/parsed-documents/cv.md`)
- **Weaknesses, framed positively:** Kafka: the RabbitMQ work as event-driven delivery; don't mention
- **Tone:** confident and specific

## Confidence

High

## Next steps

1. Write the letter
"""

RESEARCH = """# Company research: Acme (for Senior Backend Engineer)

> **Date researched:** 2026-11-10 | **Company:** Acme, acme.com | **Job ad:** https://acme.com/jobs/1

**Notes:**
- The headcount differs by source.

## Summary

- Acme sells widgets.

## At a glance

- What it does: sells widgets online. ([Acme about](https://acme.com/about), 2026-11-01)
- Founded: 2012, per directories (from search snippet). ([Dealroom](https://dealroom.co/acme), undated)
- Ownership: Not found.
- **Year founded:** Not found (no source)
- Size: about 300 people.

## Domain and product

Company-wide products:
- Widget Cloud, a hosted widget store. ([Acme product](https://acme.com/cloud), 2026-09-01)

## Latest releases

Newest first.

- 2026-10-20: Widget Cloud launched in France. ([Acme press](https://acme.com/press/fr), 2026-10-20)
- 2026-03-04: Widget Cloud launched in Italy. ([Acme press](https://acme.com/press/it), 2026-03-04)
- 2026-04: Widget Cloud pricing changed. ([Acme blog](https://acme.com/blog), 2026-04)

## Financial moment

- Funding: EUR 20M Series B. ([TechCrunch](https://techcrunch.com/acme), 2024-02-01)
- Layoffs and restructuring: Not found.

## Culture

- Remote and office policy:
  - Hybrid, two office days. ([Acme careers](https://acme.com/careers), 2026-11-10)
  - A search summary said four office days (From search snippet; [Glassdoor](https://glassdoor.com/acme), undated)
  - Office snacks: Not found.

## Employee reviews

- Glassdoor 3.1 (from search snippet). ([Glassdoor](https://glassdoor.com/acme), undated)

## Role impact

High: the team owns the checkout.

## Red flags

- A lawsuit over widget patents. ([Reuters](https://reuters.com/acme), 2026-08-01)

## Sources

- [Acme about](https://acme.com/about), 2026-11-01
"""

OLD = "(older than 6 months: never call it recent, new or latest)"
UNDATED = "(undated: never call it recent)"

EXPECTED = f"""# Letter context: Senior Backend Engineer @ Acme

Built by `ieakaso.letter_context build` from the Job analysis and the Company research of {ID}; do not edit. The company facts are the usable ones only: fetched, never from a search snippet, red flags or employee reviews.

## From the Job analysis

### Strengths

- Six years of Go (`input/parsed-documents/cv.md`)

### Letter coaching

- **Strengths to amplify:** six years of Go (`input/parsed-documents/cv.md`)
- **Weaknesses, framed positively:** Kafka: the RabbitMQ work as event-driven delivery; don't mention
- **Tone:** confident and specific

### CV under-sells

- The payments migration (`input/candidate/professional-experience-extended.md`)

## Company facts

> **Date researched:** 2026-11-10

### At a glance

- What it does: sells widgets online. ([Acme about](https://acme.com/about), 2026-11-01)
- Size: about 300 people. {UNDATED}

### Domain and product

Company-wide products:
- Widget Cloud, a hosted widget store. ([Acme product](https://acme.com/cloud), 2026-09-01)

### Latest releases

Newest first.

- 2026-10-20: Widget Cloud launched in France. ([Acme press](https://acme.com/press/fr), 2026-10-20)
- 2026-03-04: Widget Cloud launched in Italy. ([Acme press](https://acme.com/press/it), 2026-03-04) {OLD}
- 2026-04: Widget Cloud pricing changed. ([Acme blog](https://acme.com/blog), 2026-04) {OLD}

### Financial moment

- Funding: EUR 20M Series B. ([TechCrunch](https://techcrunch.com/acme), 2024-02-01) {OLD}

### Culture

- Remote and office policy:
  - Hybrid, two office days. ([Acme careers](https://acme.com/careers), 2026-11-10)
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    folder(root).mkdir(parents=True)
    write(root, "job-analysis", ANALYSIS)
    write(root, "company-research", RESEARCH)
    return root


def folder(root: Path) -> Path:
    return root / "output" / "applications" / ID


def write(root: Path, kind: str, text: str) -> None:
    (folder(root) / f"{ID}_{kind}.md").write_text(text)


def context(root: Path) -> str:
    return (folder(root) / f"{ID}_letter-context.md").read_text()


def run(root: Path, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), *argv], today=TODAY, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_build_writes_the_letter_context_from_both_files(root: Path):
    code, out, err = run(root, "build", ID)

    assert (code, err) == (0, "")
    assert out == f"letter context written for {ID}: output/applications/{ID}/{ID}_letter-context.md\n"
    assert context(root) == EXPECTED


def test_never_red_flags_employee_reviews_role_impact_notes_or_snippets(root: Path):
    run(root, "build", ID)

    text = context(root).lower()
    for left_out in ("lawsuit", "glassdoor", "owns the checkout", "headcount differs", "snippet)", "not found"):
        assert left_out not in text


def test_the_date_tag_counts_six_calendar_months_back_from_today(root: Path):
    write(root, "company-research", RESEARCH.replace("2026-03-04", "2026-05-17").replace("2026-04)", "2026-05)"))

    run(root, "build", ID)

    text = context(root)
    assert "([Acme press](https://acme.com/press/it), 2026-05-17)\n" in text  # exactly six months: still recent
    assert f"([Acme blog](https://acme.com/blog), 2026-05) {OLD}\n" in text  # a month counts from its first day


def test_a_bullet_takes_its_newest_date(root: Path):
    research = RESEARCH.replace(
        "- Funding: EUR 20M Series B. ([TechCrunch](https://techcrunch.com/acme), 2024-02-01)",
        "- Expansion: Italy on 2026-10-01, Finland on 2025-03-14. ([Acme press](https://acme.com/press), 2026-10-01)",
    )
    write(root, "company-research", research)

    run(root, "build", ID)

    assert "Finland on 2025-03-14. ([Acme press](https://acme.com/press), 2026-10-01)\n" in context(root)


def test_without_a_company_research_it_writes_the_job_analysis_part_and_exits_1(root: Path):
    (folder(root) / f"{ID}_company-research.md").unlink()

    code, out, err = run(root, "build", ID)

    assert code == 1
    assert err == f"no company facts for {ID}: it has no Company research\n"
    assert out.startswith("letter context written")
    assert context(root).endswith(
        "## Company facts\n\nNone: it has no Company research. Write about the company from the Job ad only.\n"
    )


def test_a_research_without_the_usable_sections_is_no_company_facts(root: Path):
    write(root, "company-research", "# Company research: Acme\n\nSomething else entirely.\n")

    code, _, err = run(root, "build", ID)

    assert code == 1
    assert err == f"no company facts for {ID}: its Company research has none of the usable sections\n"


def test_a_research_with_only_snippets_and_not_found_is_no_company_facts(root: Path):
    write(
        root,
        "company-research",
        "# Company research: Acme\n\n> **Date researched:** 2026-11-10\n\n## At a glance\n\n"
        "- Founded: 2012 (from search snippet).\n- Ownership: Not found.\n\n## Red flags\n\n- A lawsuit.\n",
    )

    code, _, err = run(root, "build", ID)

    assert code == 1
    assert err.endswith(f"no company facts for {ID}: its Company research has no usable fact\n")


def test_never_the_job_analysiss_candid_sections(root: Path):
    run(root, "build", ID)

    text = context(root)
    for left_out in ("### Weaknesses", "### Screener risks", "### Gaps to close", "No Kafka", "short stints"):
        assert left_out not in text


def test_a_missing_section_is_a_warning_and_never_fails(root: Path):
    write(root, "job-analysis", ANALYSIS.replace("## Letter coaching\n\n", "## Coaching\n\n"))
    write(root, "company-research", RESEARCH.replace("## Culture\n", "## Culture and values\n"))

    code, _, err = run(root, "build", ID)

    assert code == 0
    assert err == (
        "Warning: the Job analysis has no Letter coaching section\n"
        "Warning: the Company research has no Culture section\n"
    )
    assert "### Letter coaching" not in context(root)
    assert "### Culture" not in context(root)


def test_a_rebuild_overwrites_the_old_file(root: Path):
    (folder(root) / f"{ID}_letter-context.md").write_text("stale\n")

    run(root, "build", ID)

    assert context(root) == EXPECTED


def test_no_job_analysis_exits_3_and_writes_nothing(root: Path):
    (folder(root) / f"{ID}_job-analysis.md").unlink()

    code, out, err = run(root, "build", ID)

    assert (code, out) == (3, "")
    assert err == f"no Job analysis for {ID}: output/applications/{ID}/{ID}_job-analysis.md is missing\n"
    assert not (folder(root) / f"{ID}_letter-context.md").exists()


def test_no_application_folder_exits_3(root: Path):
    code, _, err = run(root, "build", "nobody_nothing_2026-01-01")

    assert code == 3
    assert err == "no Application nobody_nothing_2026-01-01: output/applications/nobody_nothing_2026-01-01 is missing\n"
