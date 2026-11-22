"""AGENTS.md stays within its word budget (issue #94). Reads the real repo; never writes to it.

AGENTS.md is loaded into every agent's context on every turn, so it holds only what the code can't tell; its
Project state section says where each contract lives instead.
"""

from pathlib import Path

AGENTS_MD = Path(__file__).resolve().parents[1] / "AGENTS.md"
WORD_BUDGET = 1800


def over_budget(path: Path, budget: int = WORD_BUDGET) -> str | None:
    """Why the file is over budget, or None when it fits."""
    words = len(path.read_text().split())
    if words <= budget:
        return None
    return (
        f"{path.name} has {words} words, over its budget of {budget}. Move detail into the module's docstring, "
        "or another doc a pointer reaches, instead of raising the budget."
    )


def test_a_file_over_budget_is_reported(tmp_path: Path):
    path = tmp_path / "AGENTS.md"
    path.write_text("word " * 11)

    assert over_budget(path, budget=10) == (
        "AGENTS.md has 11 words, over its budget of 10. Move detail into the module's docstring, "
        "or another doc a pointer reaches, instead of raising the budget."
    )


def test_a_file_within_budget_passes(tmp_path: Path):
    path = tmp_path / "AGENTS.md"
    path.write_text("word " * 10)

    assert over_budget(path, budget=10) is None


def test_agents_md_is_within_its_word_budget():
    assert over_budget(AGENTS_MD) is None
