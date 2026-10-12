"""Claude Code and OpenCode point at the same agent files. Reads the real repo; never writes to it."""

import re
from pathlib import Path

import yaml

from ieakaso.usage.transcript import IEAKASO_AGENTS

REPO = Path(__file__).resolve().parents[1]
CLAUDE_AGENTS = REPO / ".claude/agents"
OPENCODE_AGENTS = REPO / ".opencode/agents"
ROLE_FILES = REPO / "ai/agents"
# Runs in the main conversation (docs/adr/0002): a pointer would make it a subagent.
ASSISTANT = "job-application-assistant"


def pointers(folder: Path) -> dict[str, Path]:
    """Agent name → the file its pointer tells the agent to read."""
    found = {}
    for path in folder.glob("*.md"):
        target = re.search(r"Read `([^`]+)` \(relative to the repository root\)", path.read_text())
        assert target, f"{path} has no 'Read `<file>` (relative to the repository root)' line"
        found[path.stem] = REPO / target.group(1)
    return found


def frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---")[1])


def test_both_tools_point_at_the_same_agents_and_files():
    assert pointers(CLAUDE_AGENTS)
    assert pointers(CLAUDE_AGENTS) == pointers(OPENCODE_AGENTS)


def test_every_agent_points_at_its_own_role_file():
    for name, target in pointers(CLAUDE_AGENTS).items():
        assert target == ROLE_FILES / f"{name}.md"


def test_every_target_exists_and_is_not_empty():
    for target in pointers(CLAUDE_AGENTS).values():
        assert target.is_file(), target
        assert target.read_text().strip(), target


def test_the_job_application_assistant_has_no_pointer():
    assert ASSISTANT not in pointers(CLAUDE_AGENTS)
    assert ASSISTANT not in pointers(OPENCODE_AGENTS)
    assert (ROLE_FILES / f"{ASSISTANT}.md").read_text().strip()


def test_every_role_file_is_a_pointer_target_or_the_assistant():
    files = {path.stem for path in ROLE_FILES.glob("*.md")}
    assert files == set(pointers(CLAUDE_AGENTS)) | {ASSISTANT}


def test_descriptions_match():
    for name in pointers(CLAUDE_AGENTS):
        claude = frontmatter(CLAUDE_AGENTS / f"{name}.md")
        opencode = frontmatter(OPENCODE_AGENTS / f"{name}.md")
        assert claude["description"] == opencode["description"], name


def test_usage_counts_exactly_the_agents_that_have_pointers():
    assert IEAKASO_AGENTS == set(pointers(CLAUDE_AGENTS))


def test_opencode_agents_are_subagents():
    for name in pointers(OPENCODE_AGENTS):
        assert frontmatter(OPENCODE_AGENTS / f"{name}.md")["mode"] == "subagent", name
