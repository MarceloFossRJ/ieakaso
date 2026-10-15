"""`uv run python -m ieakaso.tracker upsert [--json <payload>] | set-cover-letter <id> <path>`.

upsert: create or update the record of a Job analysis; the JSON payload comes from --json or stdin. Writes
`created <id>` or `updated <id>` to stdout.
set-cover-letter: set a record's Cover letter path.

Exit codes: 0 done, 1 invalid payload or path, 2 db/ieakaso_db.json is not valid JSON (it is left alone),
3 the file changed while the command ran (run it again), 4 no tracked Application has that ID.
The message for exits 1-4 goes to stderr. The tracker never sends data anywhere.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from ieakaso.repo import find_root
from ieakaso.tracker.errors import InvalidDbError, InvalidRecordError, TrackerError
from ieakaso.tracker.ops import set_cover_letter, upsert_from_analysis
from ieakaso.tracker.store import DB_PATH, Db, load, save


def _read(db_path: Path) -> Db:
    db = load(db_path)
    if db.error:
        raise InvalidDbError(db.error)
    return db


def main(
    argv: list[str] | None = None,
    today: date | None = None,
    stdin: TextIO | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    stdin, out, err = stdin or sys.stdin, out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.tracker",
        description="Create or update records in db/ieakaso_db.json.",
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    commands = parser.add_subparsers(dest="command", required=True)
    upsert = commands.add_parser("upsert", help="create or update the record of a Job analysis")
    upsert.add_argument("--json", help="the payload as JSON (default: read from stdin)")
    cover = commands.add_parser("set-cover-letter", help="set the Cover letter path of a record")
    cover.add_argument("id", help="the Application ID")
    cover.add_argument("path", help="the kept draft, relative to the repo root")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    try:
        db = _read(root / DB_PATH)
        if args.command == "upsert":
            try:
                payload = json.loads(args.json if args.json is not None else stdin.read())
            except ValueError as error:
                raise InvalidRecordError(f"the payload is not valid JSON: {error}") from error
            record, created = upsert_from_analysis(db, payload, today)
            message = f"{'created' if created else 'updated'} {record['id']}"
        else:
            set_cover_letter(db, args.id, args.path)
            message = f"cover letter set for {args.id}"
        save(db)
    except TrackerError as error:
        print(error, file=err)
        return error.exit_code
    print(message, file=out)
    return 0
