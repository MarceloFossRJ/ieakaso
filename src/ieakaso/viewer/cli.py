"""`ieakaso-view` (or `python -m ieakaso.viewer`): opens the applications viewer in this terminal, from any folder.

It opens `--root`, else the repo at or above the current folder, else the repo remembered in `repo.toml`
(`ieakaso.repo.locate`, ADR 0013). Exit codes: 0 the viewer ran, 2 no Ieakaso repo to open (`--root` isn't
one, none found, or the remembered one is gone; `repo.toml` is never changed). The message for exit 2 goes
to stderr.
"""

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from ieakaso.repo import RepoNotFound, default_config_dir, locate
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
    parser.add_argument(
        "--root",
        type=Path,
        help="repo root (default: the repo at or above the current folder, else the one /ieakaso init remembered)",
    )
    args = parser.parse_args(argv)
    try:
        root = locate(args.root, cwd or Path.cwd(), config_dir or default_config_dir())
    except RepoNotFound as error:
        print(error, file=sys.stderr)
        return 2
    launch(root)
    return 0
