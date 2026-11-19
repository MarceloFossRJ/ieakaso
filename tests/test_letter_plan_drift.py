"""The Cover letter agents draft from and review against the Letter plan and the Final check (ADR 0012), and the
Applicant writes every notes field the assembler reads. Reads the real repo; never writes to it."""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUIDELINES = REPO / "ai/skills/ieakaso/general-knowledge-base/cover-letter-guidelines.md"
APPLICANT = REPO / "ai/agents/applicant.md"
RECRUITER = REPO / "ai/agents/recruiter.md"
# The notes fields `src/ieakaso/cover_letter/assemble.py` reads from a draft.
ASSEMBLED_NOTES = ("Language", "Refused suggestions", "Adapted for voice", "Plan departures")


def section(path: Path, heading: str) -> str:
    return path.read_text().split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def inputs_rows(path: Path) -> set[str]:
    return {line.split("|")[1].strip() for line in section(path, "INPUTS").splitlines() if line.startswith("| ")}


def test_the_guidelines_hold_the_final_check_with_seven_checks():
    assert len(re.findall(r"^\d+\. ", section(GUIDELINES, "Final check"), re.MULTILINE)) == 7


@pytest.mark.parametrize("label", ASSEMBLED_NOTES)
def test_the_applicant_writes_every_notes_field_the_assembler_reads(label: str):
    assert f"**{label}:**" in section(APPLICANT, "YOUR REPLY")


@pytest.mark.parametrize(
    "agent",
    [
        pytest.param(APPLICANT, id="applicant"),
        pytest.param(RECRUITER, id="recruiter", marks=pytest.mark.xfail(strict=True, reason="Task 3")),
    ],
)
def test_an_agent_reads_the_letter_plan_and_uses_the_final_check(agent: Path):
    assert "The Letter plan" in inputs_rows(agent)
    assert "Final check" in agent.read_text()
