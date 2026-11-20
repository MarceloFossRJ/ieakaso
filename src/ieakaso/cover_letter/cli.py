"""`uv run python -m ieakaso.cover_letter assemble <id> --rounds <n> --final <n> --exit <name> --reason <text>
[--requested <n> ...] --motivation used|none`: builds the Application's Cover letter and its review log from the Round files.

Reads `output/applications/<id>/rounds/plan.md` (the Letter plan), `round-<n>_draft.md` and `_review.md` for Rounds 1
to --rounds, the header data from `<id>_job-ad.md` and `<id>_company-research.md`, and today's date. Writes `<id>_cover-letter.md` (the Draft
section of Round --final, unchanged) and `<id>_cover-letter-review.md`, and prints the final letter to stdout.
--motivation (used or none, required) is the header's Personal motivation: whether the mode passed one to the agents.
--requested names the Rounds the candidate requested. --exit is the header's Exit, --reason the Exit reason section.

Exit codes: 0 both files written, 1 the Letter plan is missing or empty, a Round file is missing or unusable, --exit is not one of the fixed values, or --final
or --requested names a Round that isn't there (nothing is written), 3 the Application's folder or Job ad file is missing, or its Company research file is unreadable. The message for exits 1
and 3 goes to stderr. The command never sends data anywhere.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from ieakaso.cover_letter.assemble import Outcome, assemble
from ieakaso.cover_letter.errors import CoverLetterError
from ieakaso.repo import find_root


def main(
    argv: list[str] | None = None,
    today: date | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.cover_letter",
        description="Build the Cover letter and its review log from the Round files.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("assemble", help="write the letter and the review log, print the letter")
    build.add_argument("id", help="the Application ID")
    build.add_argument("--rounds", type=int, required=True, help="how many Rounds have run (Round files 1 to n)")
    build.add_argument("--final", type=int, required=True, help="the Round whose draft is the final letter")
    build.add_argument("--requested", type=int, nargs="*", default=[], help="Rounds the candidate requested")
    build.add_argument("--exit", required=True, dest="exit_name", help="the header's Exit")
    build.add_argument("--reason", required=True, help="the Exit reason section, one line")
    build.add_argument(
        "--motivation", required=True, choices=("used", "none"), help="whether a Personal motivation was passed to the agents"
    )
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    try:
        outcome = Outcome(args.rounds, args.final, tuple(args.requested), args.exit_name, args.reason, args.motivation == "used")
        letter = assemble(root, args.id, outcome, today)
    except CoverLetterError as error:
        print(error, file=err)
        return error.exit_code
    print(letter, end="", file=out)
    return 0
