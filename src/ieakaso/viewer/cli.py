"""`uv run ieakaso-viewer` (or `python -m ieakaso.viewer`): opens the applications viewer in this terminal."""

import argparse
import subprocess
import sys
from pathlib import Path

from ieakaso.repo import find_root
from ieakaso.viewer.app import ViewerApp


def open_with_system(path: Path) -> None:
    """Open a file with the system's default application."""
    command = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([command, str(path)], check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ieakaso-viewer",
        description="View and edit the Applications in db/ieakaso_db.json. Needs a real terminal.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    args = parser.parse_args(argv)
    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    ViewerApp(root, opener=open_with_system).run()
    return 0
