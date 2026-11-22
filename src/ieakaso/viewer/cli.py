"""`ieakaso-view` (or `python -m ieakaso.viewer`): opens the applications viewer in this terminal, from any folder."""

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from ieakaso.repo import default_config_dir, find_root, is_ieakaso_repo, remembered_root
from ieakaso.viewer.app import ViewerApp


def open_with_system(path: Path) -> None:
    """Open a file with the system's default application."""
    command = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([command, str(path)], check=False)


def run_viewer(root: Path) -> None:
    ViewerApp(root, opener=open_with_system).run()


def main(
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    config_dir: Path | None = None,
    launch: Callable[[Path], None] = run_viewer,
) -> int:
    parser = argparse.ArgumentParser(
        prog="ieakaso-view",
        description="View and edit the Applications in db/ieakaso_db.json. Needs a real terminal.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    args = parser.parse_args(argv)
    cwd = cwd or Path.cwd()
    config_dir = config_dir or default_config_dir()
    root = args.root or find_root(cwd)
    if root is None:
        remembered = remembered_root(config_dir)
        if remembered is None:
            print("Can't find the Ieakaso repo: run it from the repo or pass --root", file=sys.stderr)
            return 2
        if not is_ieakaso_repo(remembered):
            print(
                f"The remembered repo {remembered} is gone: run /ieakaso init from the repo, or pass --root",
                file=sys.stderr,
            )
            return 2
        root = remembered
    launch(root.resolve())
    return 0
