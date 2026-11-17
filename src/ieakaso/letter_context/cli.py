"""`uv run python -m ieakaso.letter_context build <id>`: the Letter context of an Application.

Reads `output/applications/<id>/<id>_job-analysis.md` and `<id>_company-research.md` and writes
`<id>_letter-context.md`, overwriting an old one: the Job analysis's Strengths, Weaknesses, Screener risks, CV
under-sells and Gaps to close, and the Company research's usable company facts (At a glance, Domain and product, Latest
releases, Financial moment and Culture, without items from a search snippet or Not found), each fact tagged when its
newest date is more than 6 months before today, or when it has none. Prints
`letter context written for <id>: <path>`; a missing section prints a `Warning:` line to stderr and never fails.

Exit codes: 0 written, 1 written without company facts (no Company research, it can't be read, or it has no usable
fact; the reason goes to stderr), 3 the Application's folder or its Job analysis is missing (nothing written, the
message goes to stderr). The command never sends data anywhere.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from ieakaso.letter_context.build import build, context_path
from ieakaso.letter_context.errors import LetterContextError
from ieakaso.repo import find_root


def main(
    argv: list[str] | None = None,
    today: date | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.letter_context",
        description="Build the Letter context the Cover letter agents read.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("build", help="write the Letter context")
    command.add_argument("id", help="the Application ID")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    try:
        built = build(root, args.id, today)
    except LetterContextError as error:
        print(error, file=err)
        return error.exit_code
    for warning in built.warnings:
        print(warning, file=err)
    print(f"letter context written for {args.id}: {context_path(args.id)}", file=out)
    if built.no_company_facts:
        print(f"no company facts for {args.id}: {built.no_company_facts}", file=err)
        return 1
    return 0
