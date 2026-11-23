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

`uv run python -m ieakaso.cover_letter echoes <id> <round>`: lists the possible Echoes (`CONTEXT.md`) in Round <round>'s
draft, for the Applicant Agent and the Seasoned Recruiter to judge. Reads the Draft section of
`output/applications/<id>/rounds/round-<round>_draft.md` and `<id>_job-ad.md`, and writes nothing. Both are split into
sentences, with hard-wrapped lines joined; a draft line that doesn't end like a sentence (the contact block, the subject
line) is never checked. Words are compared without stopwords, as light English stems ("shaping" meets "shape"). A
draft sentence is a possible Echo when one ad sentence shares at least half of its content words, and at least 4 of
them. Prints
`possible Echoes in round <round>: <n>`, then for each one its score and two lines, `letter: <sentence>` and
`ad: <sentence>`; or `no possible Echoes in round <round>`.

Exit codes: 0 the list (or none) printed, 1 the Round's draft file is missing, unreadable or not a draft, 3 the
Application's folder is missing, or its Job ad file is missing, unreadable or has no text to compare. The message for
exits 1 and 3 goes to stderr.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from ieakaso.cover_letter.assemble import Outcome, assemble
from ieakaso.cover_letter.echoes import find_echoes
from ieakaso.cover_letter.errors import CoverLetterError
from ieakaso.repo import find_root


def main(
    argv: list[str] | None = None,
    today: date | None = None,
    cwd: Path | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.cover_letter",
        description="Build the Cover letter and its review log from the Round files, or list a draft's possible Echoes.",
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
        "--motivation",
        required=True,
        choices=("used", "none"),
        help="whether a Personal motivation was passed to the agents",
    )
    echoes = commands.add_parser("echoes", help="list the draft sentences that may echo a Job ad sentence")
    echoes.add_argument("id", help="the Application ID")
    echoes.add_argument("round", type=int, help="the Round whose draft to check")
    args = parser.parse_args(argv)

    cwd = cwd or Path.cwd()
    root = (cwd / args.root if args.root else find_root(cwd) or cwd).resolve()
    if args.command == "echoes":
        return _echoes(root, args.id, args.round, out, err)
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    try:
        outcome = Outcome(
            args.rounds, args.final, tuple(args.requested), args.exit_name, args.reason, args.motivation == "used"
        )
        letter = assemble(root, args.id, outcome, today)
    except CoverLetterError as error:
        print(error, file=err)
        return error.exit_code
    print(letter, end="", file=out)
    return 0


def _echoes(root: Path, application_id: str, round_number: int, out: TextIO, err: TextIO) -> int:
    try:
        found = find_echoes(root, application_id, round_number)
    except CoverLetterError as error:
        print(error, file=err)
        return error.exit_code
    if not found:
        print(f"no possible Echoes in round {round_number}", file=out)
        return 0
    print(f"possible Echoes in round {round_number}: {len(found)}", file=out)
    for echo in found:
        print(f"\n{echo.score:.2f}\nletter: {echo.letter}\nad: {echo.ad}", file=out)
    return 0
