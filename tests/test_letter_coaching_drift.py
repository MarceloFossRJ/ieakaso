"""job-analyzer writes Letter coaching for the Cover letter agents, the Letter context carries it, and cover-letter
writes it when an older Job analysis has none (ADR 0014). Reads the real repo; never writes to it."""

import re
from pathlib import Path

from ieakaso.letter_context.build import ANALYSIS_SECTIONS

REPO = Path(__file__).resolve().parents[1]
JOB_ANALYZER = REPO / "ai/skills/ieakaso/modes/job-analyzer.md"
COVER_LETTER = REPO / "ai/skills/ieakaso/modes/cover-letter.md"


def analysis_template() -> str:
    text = JOB_ANALYZER.read_text()
    return text.split("**2. The Job analysis:**", 1)[1].split("**3. The tracker record.**", 1)[0]


def headings(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def test_the_job_analysis_template_has_letter_coaching_between_gaps_to_close_and_confidence():
    found = headings(analysis_template())
    assert found.index("Gaps to close") + 1 == found.index("Letter coaching") == found.index("Confidence") - 1


def test_every_section_the_letter_context_takes_is_in_the_job_analysis_template():
    assert set(ANALYSIS_SECTIONS) <= set(headings(analysis_template()))


def test_letter_coaching_has_its_three_parts():
    coaching = analysis_template().split("## Letter coaching", 1)[1].split("\n## ", 1)[0]
    for part in ("Strengths to amplify", "Weaknesses, framed positively", "Tone"):
        assert f"**{part}:**" in coaching


def test_cover_letter_writes_a_missing_letter_coaching_before_it_builds_the_letter_context():
    step = COVER_LETTER.read_text().split("### Step 2f", 1)[1].split("\n### ", 1)[0]
    before_the_build = step.split("uv run python -m ieakaso.letter_context build", 1)[0]
    assert "has no Letter coaching section" in before_the_build
    assert "Step 8" in before_the_build
