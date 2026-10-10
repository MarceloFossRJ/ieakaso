"""Every mode in the router table has a mode entry in each tool, and every mode entry matches its row. Reads the real repo; never writes to it."""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ROUTER = REPO / "ai/skills/ieakaso/SKILL.md"
CLAUDE_ENTRIES = REPO / ".claude/skills/ieakaso/skills"
OPENCODE_ENTRIES = REPO / ".opencode/commands"
NO_ARGUMENTS = "—"


def router_modes() -> dict[str, tuple[str, str]]:
    """Mode → (Arguments, Does), from the router's mode table."""
    rows = re.findall(
        r"^\| `([a-z0-9-]+)` \| (.*?) \| .*? \| (.*?) \|$",
        ROUTER.read_text(),
        re.MULTILINE,
    )
    return {mode: (arguments.strip("`"), does) for mode, arguments, does in rows}


def claude_entries() -> dict[str, Path]:
    return {path.parent.name: path for path in CLAUDE_ENTRIES.glob("*/SKILL.md")}


def opencode_entries() -> dict[str, Path]:
    return {
        path.stem.removeprefix("ieakaso-"): path
        for path in OPENCODE_ENTRIES.glob("ieakaso-*.md")
    }


def frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---")[1])


def test_the_router_table_lists_modes():
    assert router_modes()


def test_every_mode_has_an_entry_in_each_tool():
    assert claude_entries().keys() == router_modes().keys()
    assert opencode_entries().keys() == router_modes().keys()


def test_every_entry_routes_to_its_own_mode():
    for mode, path in [*claude_entries().items(), *opencode_entries().items()]:
        text = path.read_text()
        assert f"follow it as mode `{mode}`" in text, path
        assert "$ARGUMENTS" in text, path


def test_every_entry_is_described_by_its_row():
    modes = router_modes()
    for mode, path in [*claude_entries().items(), *opencode_entries().items()]:
        assert (
            frontmatter(path)["description"] == f"Ieakaso {mode}: {modes[mode][1]}"
        ), path


def test_claude_entries_match_their_row_and_only_the_user_starts_them():
    modes = router_modes()
    for mode, path in claude_entries().items():
        meta = frontmatter(path)
        arguments = modes[mode][0]
        assert meta["name"] == mode, path
        assert meta.get("argument-hint") == (
            None if arguments == NO_ARGUMENTS else arguments
        ), path
        assert meta["disable-model-invocation"] is True, path
