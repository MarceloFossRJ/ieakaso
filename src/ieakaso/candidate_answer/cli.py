"""`uv run python -m ieakaso.candidate_answer append <file name> <id>`: append the candidate's answer to a memory file.

The answer comes on standard input and is written word for word, trimmed of blank lines around it, at the end of
`input/candidate/<file name>` under `## Added <yyyy-mm-dd> (<id>)`. The file is created when it is missing. Only
`professional-experience-extended.md`, `presentation.md` and `professional-self-reflection.md` take an answer: never the
Source CV, `writing-style.md`, `deliberate-differences.md` or `config.yml`. Prints
`answer added to <path> for <id>`.

Exit codes: 0 appended, 1 no text on stdin (nothing changed), 2 the file can't take an answer, 3 the Application's
folder is missing. The message for exits 1 to 3 goes to stderr. The command never sends data anywhere.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from ieakaso.layout import APPLICATIONS, CANDIDATE
from ieakaso.repo import find_root

MEMORY_FILES = ("professional-experience-extended.md", "presentation.md", "professional-self-reflection.md")


def main(
    argv: list[str] | None = None,
    today: date | None = None,
    stdin: TextIO | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    stdin, out, err = stdin or sys.stdin, out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.candidate_answer",
        description="Append the candidate's answer, word for word, to one of their memory files.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("append", help="append the answer on stdin")
    command.add_argument("file", help=f"the memory file: {', '.join(MEMORY_FILES)}")
    command.add_argument("id", help="the Application ID the answer was given for")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    if args.file not in MEMORY_FILES:
        print(f"{args.file} can't take an answer: only {', '.join(MEMORY_FILES[:-1])} and {MEMORY_FILES[-1]}", file=err)
        return 2
    folder = APPLICATIONS / args.id
    if not (root / folder).is_dir():
        print(f"no Application {args.id}: {folder} is missing", file=err)
        return 3
    answer = "" if stdin.isatty() else stdin.read().strip("\n")
    if not answer.strip():
        print("no answer: give the candidate's text on standard input", file=err)
        return 1

    path = CANDIDATE / args.file
    target = root / path
    old = target.read_text() if target.is_file() else ""
    before = old.rstrip("\n") + "\n\n" if old.strip() else ""  # one blank line between the old text and the answer
    target.write_text(f"{before}## Added {today.isoformat()} ({args.id})\n\n{answer}\n")
    print(f"answer added to {path} for {args.id}", file=out)
    return 0
