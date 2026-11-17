"""The Cover letter agents read the Personal knowledge base only through the Evidence bank (ADR 0008): their INPUTS name
no other file of it. Reads the real repo; never writes to it."""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
# The Personal knowledge base files each agent may still read itself.
ALLOWED = {
    "ai/agents/applicant.md": {"config.yml", "input/candidate/writing-style.md"},
    "ai/agents/recruiter.md": {"config.yml", "input/parsed-documents/cv.md"},
}


def inputs_section(path: Path) -> str:
    return path.read_text().split("\n## INPUTS\n", 1)[1].split("\n## ", 1)[0]


def knowledge_base_files(text: str) -> set[str]:
    """Backticked paths into the Personal knowledge base: `config.yml` and anything in `input/`."""
    return {token for token in re.findall(r"`([^`\s]+)`", text) if token == "config.yml" or token.startswith("input/")}


@pytest.mark.parametrize("agent", sorted(ALLOWED))
def test_an_agent_reads_no_personal_knowledge_base_file_beyond_its_allowed_ones(agent: str):
    named = knowledge_base_files(inputs_section(REPO / agent))

    assert named <= ALLOWED[agent], f"{agent} reads {sorted(named - ALLOWED[agent])}; pass it through the Evidence bank"


@pytest.mark.parametrize("agent", sorted(ALLOWED))
def test_an_agent_reads_the_evidence_bank(agent: str):
    assert "Evidence bank" in inputs_section(REPO / agent)
