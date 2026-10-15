"""The Cover letter agents and their guidelines name only files that exist. Reads the real repo; never writes to it."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUIDELINES = REPO / "ai/skills/ieakaso/general-knowledge-base/cover-letter-guidelines.md"
FILES = [REPO / "ai/agents/applicant.md", REPO / "ai/agents/recruiter.md", GUIDELINES]
# User data: the candidate's own data, absent from a fresh clone.
USER_DATA = ("input/", "output/", "db/", "config.yml")


def named_paths(path: Path) -> set[str]:
    """Backticked tokens that look like file paths: no spaces or placeholders, and a folder or an extension."""
    tokens = re.findall(r"`([^`\s<>]+)`", path.read_text())
    return {token for token in tokens if "/" in token or re.search(r"\.\w+$", token)}


def exists(name: str, named_in: Path) -> bool:
    """A path is relative to the repository root, or a bare file name next to the file that names it."""
    return (REPO / name).exists() or (named_in.parent / name).exists()


def test_the_agents_read_the_cover_letter_guidelines():
    for path in FILES[:2]:
        assert str(GUIDELINES.relative_to(REPO)) in path.read_text(), path


def test_every_named_tracked_file_exists():
    missing = [
        f"{path.relative_to(REPO)}: {name}"
        for path in FILES
        for name in named_paths(path)
        if not name.startswith(USER_DATA) and not exists(name, path)
    ]
    assert not missing
