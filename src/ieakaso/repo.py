"""Finding the ieakaso repository root."""

import tomllib
from pathlib import Path


def is_ieakaso_repo(path: Path) -> bool:
    try:
        project = tomllib.loads((path / "pyproject.toml").read_text())["project"]
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return False
    return project.get("name") == "ieakaso" and (path / "ai/skills/ieakaso").is_dir()


def find_root(start: Path) -> Path | None:
    """The nearest ieakaso repo at or above start."""
    for path in [start, *start.parents]:
        if is_ieakaso_repo(path):
            return path
    return None
