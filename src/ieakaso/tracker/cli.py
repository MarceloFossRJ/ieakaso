"""`uv run python -m ieakaso.tracker upsert [--json <payload>] | set-cover-letter <id> <path>
| set-company-research <id> <path> | cv-versions | applications | set-cv-version <id> <version id|none>
| set-cv-label <version id> <label>`.

upsert: create or update the record of a Job analysis; the JSON payload comes from --json or stdin. Writes
`created <id>` or `updated <id>` to stdout.
set-cover-letter: set a record's Cover letter path.
set-company-research: set a record's Company research path.
cv-versions: list the CV versions, one per line, tab-separated: ID, label, captured date, the Application ID of a
Tailored CV or `-`, and `current` for the current version or `-`.
applications: list the records, one per line, tab-separated: ID, status, company, position and CV version ID or `-`.
set-cv-version: set the CV version an Application was sent with (`none` clears it).
set-cv-label: set a CV version's label.
Capturing a CV version is the CV parser's job (it imports `add_cv_version`); there is no command for it.

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
from ieakaso.tracker.cv_versions import set_cv_version_label, set_record_cv_version
from ieakaso.tracker.errors import InvalidDbError, InvalidRecordError, TrackerError
from ieakaso.tracker.ops import set_company_research, set_cover_letter, upsert_from_analysis
from ieakaso.tracker.store import DB_PATH, Db, current_cv_version, load, save

READ_ONLY = ("cv-versions", "applications")


def _read(root: Path) -> Db:
    db = load(root / DB_PATH, root=root)
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
    research = commands.add_parser("set-company-research", help="set the Company research path of a record")
    research.add_argument("id", help="the Application ID")
    research.add_argument("path", help="the report, relative to the repo root")
    commands.add_parser("cv-versions", help="list the CV versions")
    commands.add_parser("applications", help="list the Applications")
    version = commands.add_parser("set-cv-version", help="set the CV version an Application was sent with")
    version.add_argument("id", help="the Application ID")
    version.add_argument("version", help="a CV version ID, or none")
    label = commands.add_parser("set-cv-label", help="set the label of a CV version")
    label.add_argument("version", help="the CV version ID")
    label.add_argument("label", help="the new label")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    try:
        db = _read(root)
        if args.command == "upsert":
            try:
                payload = json.loads(args.json if args.json is not None else stdin.read())
            except ValueError as error:
                raise InvalidRecordError(f"the payload is not valid JSON: {error}") from error
            record, created = upsert_from_analysis(db, payload, today)
            message = f"{'created' if created else 'updated'} {record['id']}"
        elif args.command == "cv-versions":
            current = current_cv_version(db)
            for v in db.cv_versions:
                is_current = "current" if v is current else "-"
                print(v["id"], v["label"], v["captured_at"], v["tailored_for"] or "-", is_current, sep="\t", file=out)
        elif args.command == "applications":
            for r in db.records:
                print(r["id"], r["status"], r["company"], r["position"], r["cv_version"] or "-", sep="\t", file=out)
        elif args.command == "set-cv-version":
            set_record_cv_version(db, args.id, None if args.version == "none" else args.version)
            message = f"cv version {args.version} set for {args.id}"
        elif args.command == "set-cv-label":
            set_cv_version_label(db, args.version, args.label)
            message = f"cv version {args.version} labelled {args.label.strip()!r}"
        elif args.command == "set-cover-letter":
            set_cover_letter(db, args.id, args.path)
            message = f"cover letter set for {args.id}"
        else:
            set_company_research(db, args.id, args.path)
            message = f"company research set for {args.id}"
        if args.command in READ_ONLY:
            return 0
        save(db)
    except TrackerError as error:
        print(error, file=err)
        return error.exit_code
    print(message, file=out)
    return 0
