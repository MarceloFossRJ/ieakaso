"""`uv run python -m ieakaso.repo remember [--replace]`: remembers the repo it is run from for `ieakaso-view`.

Writes `repo.toml` in the config folder (ADR 0013) and prints `remembered <root> in <file>`. Exit codes: 0 written or
already the same (a remembered repo that is gone is overwritten), 1 the file can't be written, 2 not run inside an
Ieakaso repo, 4 a different repo that still exists is remembered (left alone; `--replace` overwrites). The message
for exits 1, 2 and 4 goes to stderr.
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ieakaso.repo import REPO_FILE, default_config_dir, find_root, is_ieakaso_repo, remember_root, remembered_root


def main(
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    config_dir: Path | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m ieakaso.repo")
    commands = parser.add_subparsers(dest="command", required=True)
    remember = commands.add_parser("remember", help="remember this repo for ieakaso-view")
    remember.add_argument("--replace", action="store_true", help="replace a different remembered repo")
    args = parser.parse_args(argv)
    cwd = cwd or Path.cwd()
    config_dir = config_dir or default_config_dir()
    out = out or sys.stdout
    err = err or sys.stderr

    found = find_root(cwd)
    if found is None:
        print(f"{cwd} is not inside an Ieakaso repo; nothing written", file=err)
        return 2
    root = found.resolve()
    file = config_dir / REPO_FILE
    current = remembered_root(config_dir)
    if current == root:
        print(f"remembered {root} in {file}", file=out)
        return 0
    if current is not None and is_ieakaso_repo(current) and not args.replace:
        print(f"ieakaso-view opens {current}; pass --replace to switch it to {root}", file=err)
        return 4
    try:
        remember_root(config_dir, root)
    except OSError as error:
        print(f"can't write {file}: {error.strerror}", file=err)
        return 1
    print(f"remembered {root} in {file}", file=out)
    return 0
