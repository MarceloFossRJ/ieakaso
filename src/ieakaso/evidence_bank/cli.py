"""`uv run python -m ieakaso.evidence_bank stamp <id> | check <id>`: the Sources section of an Evidence bank.

stamp: after the job-analyzer mode writes `output/applications/<id>/<id>_evidence-bank.md`, write its Sources section:
every Personal knowledge base file the bank is built from, with its SHA-256, replacing an old section. Prints
`evidence bank stamped for <id>: <n> source files`.
check: compare the Sources section with the files now. Prints `evidence bank is current for <id>`, or one line per
difference: `Changed: <path>`, `Added: <path>`, `Removed: <path>`.

Exit codes: 0 stamped or current, 1 the bank is stale (check), 2 no Evidence bank file or no Sources section in it,
3 the Application's folder is missing. The message for exits 2 and 3 goes to stderr. The command never sends data
anywhere.
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ieakaso.evidence_bank.errors import EvidenceBankError
from ieakaso.evidence_bank.sources import check, stamp
from ieakaso.repo import find_root


def main(argv: list[str] | None = None, out: TextIO | None = None, err: TextIO | None = None) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.evidence_bank",
        description="Stamp or check the Sources section of an Evidence bank.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("stamp", "write the Sources section"), ("check", "check whether the bank is current")):
        command = commands.add_parser(name, help=text)
        command.add_argument("id", help="the Application ID")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    try:
        if args.command == "stamp":
            count = stamp(root, args.id)
            print(f"evidence bank stamped for {args.id}: {count} source files", file=out)
            return 0
        changes = check(root, args.id)
    except EvidenceBankError as error:
        print(error, file=err)
        return error.exit_code
    if not changes:
        print(f"evidence bank is current for {args.id}", file=out)
        return 0
    for line in changes:
        print(line, file=out)
    return 1
