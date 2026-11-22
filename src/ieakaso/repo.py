"""Finding the Ieakaso repository root, and remembering it for `ieakaso-view` (ADR 0013).

`uv run python -m ieakaso.repo remember [--replace]` writes the repo it is run from to `repo.toml` in the
config folder (`$XDG_CONFIG_HOME/ieakaso`, or `~/.config/ieakaso`) and prints `remembered <root> in <file>`.
Exit codes: 0 written or already the same (a remembered repo that is gone is overwritten), 1 the file can't be
written, 2 not run inside an Ieakaso repo, 4 a different repo that still exists is remembered (left alone;
`--replace` overwrites). The message for exits 1, 2 and 4 goes to stderr.
"""

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

REPO_FILE = "repo.toml"


class RepoNotFound(Exception):
    """No Ieakaso repo to open; the message says why and what to do."""


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
    """The nearest Ieakaso repo at or above start."""
    for path in [start, *start.parents]:
        if is_ieakaso_repo(path):
            return path
    return None


def remembered_root(config_dir: Path) -> Path | None:
    """The repo in config_dir's repo.toml, resolved, or None when there is no usable file."""
    try:
        root = tomllib.loads((config_dir / REPO_FILE).read_text())["root"]
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return None
    return Path(root).resolve() if isinstance(root, str) else None


def remember_root(config_dir: Path, root: Path) -> Path:
    """Write root to config_dir's repo.toml and return the file. Raises OSError when it can't."""
    file = config_dir / REPO_FILE
    config_dir.mkdir(parents=True, exist_ok=True)
    file.write_text(f"root = {json.dumps(str(root))}\n")
    return file


def locate(root: Path | None, cwd: Path, config_dir: Path) -> Path:
    """The repo ieakaso-view opens: root if given, else the repo at or above cwd, else the remembered one."""
    if root is not None:
        root = cwd / root  # a relative --root is read from cwd
        if not is_ieakaso_repo(root):
            raise RepoNotFound(f"{root} is not an Ieakaso repo")
        return root.resolve()
    found = find_root(cwd)
    if found is not None:
        return found.resolve()
    remembered = remembered_root(config_dir)
    if remembered is None:
        raise RepoNotFound("Can't find the Ieakaso repo: run it from the repo or pass --root")
    if not is_ieakaso_repo(remembered):
        raise RepoNotFound(
            f"The remembered repo {remembered} is gone: run /ieakaso init from the repo, or pass --root"
        )
    return remembered


def main(argv: list[str] | None = None, *, cwd: Path | None = None, config_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ieakaso.repo")
    commands = parser.add_subparsers(dest="command", required=True)
    remember = commands.add_parser("remember", help="remember this repo for ieakaso-view")
    remember.add_argument("--replace", action="store_true", help="replace a different remembered repo")
    args = parser.parse_args(argv)
    cwd = cwd or Path.cwd()
    config_dir = config_dir or default_config_dir()

    found = find_root(cwd)
    if found is None:
        print(f"{cwd} is not inside an Ieakaso repo; nothing written", file=sys.stderr)
        return 2
    root = found.resolve()
    file = config_dir / REPO_FILE
    current = remembered_root(config_dir)
    if current == root:
        print(f"remembered {root} in {file}")
        return 0
    if current is not None and is_ieakaso_repo(current) and not args.replace:
        print(f"ieakaso-view opens {current}; pass --replace to switch it to {root}", file=sys.stderr)
        return 4
    try:
        remember_root(config_dir, root)
    except OSError as error:
        print(f"Can't write {file}: {error.strerror}", file=sys.stderr)
        return 1
    print(f"remembered {root} in {file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
