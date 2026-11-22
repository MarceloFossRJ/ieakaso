"""Finding the ieakaso repository root, and remembering it for `ieakaso-view` (ADR 0013).

`uv run python -m ieakaso.repo remember [--replace]` writes the repo it is run from to `repo.toml`
in the config folder. Exit codes: 0 written or already the same, 1 the file can't be written,
2 not run inside an ieakaso repo, 4 a different repo that still exists is remembered (left alone).
"""

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

REPO_FILE = "repo.toml"


def default_config_dir() -> Path:
    """Where repo.toml lives: $XDG_CONFIG_HOME/ieakaso, or ~/.config/ieakaso (macOS included)."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ieakaso"


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


def remembered_root(config_dir: Path) -> Path | None:
    """The repo in config_dir's repo.toml, or None when there is no usable file."""
    try:
        root = tomllib.loads((config_dir / REPO_FILE).read_text())["root"]
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return None
    return Path(root) if isinstance(root, str) else None


def main(argv: list[str] | None = None, *, cwd: Path, config_dir: Path) -> int:
    parser = argparse.ArgumentParser(prog="python -m ieakaso.repo")
    commands = parser.add_subparsers(dest="command", required=True)
    remember = commands.add_parser("remember", help="remember this repo for ieakaso-view")
    remember.add_argument("--replace", action="store_true", help="replace a different remembered repo")
    args = parser.parse_args(argv)

    found = find_root(cwd)
    if found is None:
        print(f"error: {cwd} is not inside the ieakaso repo; nothing written", file=sys.stderr)
        return 2
    root = found.resolve()
    file = config_dir / REPO_FILE
    current = remembered_root(config_dir)
    if current is not None and current != root and is_ieakaso_repo(current) and not args.replace:
        print(f"ieakaso-view opens {current}; pass --replace to switch it to {root}", file=sys.stderr)
        return 4
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        file.write_text(f"root = {json.dumps(str(root))}\n")
    except OSError as error:
        print(f"error: can't write {file}: {error.strerror}", file=sys.stderr)
        return 1
    print(f"remembered {root} in {file}")
    return 0


if __name__ == "__main__":
    sys.exit(main(cwd=Path.cwd(), config_dir=default_config_dir()))
