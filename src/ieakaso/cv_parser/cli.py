"""`uv run python -m ieakaso.cv_parser [--main FILE | --tailored FILE --for ID] [--force]`: captures the CV versions
waiting in the inbox `input/documents/cv/` (versions.py), writes the Parsed CV `input/cv.md` from the current
version, and writes the Parsed documents of the LinkedIn profile and reference letters (documents.py).

A new file is captured at once only when it is the first CV there is. Otherwise the mode asks the candidate and runs
the command again with `--main FILE` (the new main CV) or `--tailored FILE --for <Application ID>` (a Tailored CV).
FILE is a file name in the inbox, or its path from the repo root. A file the candidate says is not a CV stays where
it is and is reported on every run.

Exit codes: 0 written or already up to date, 1 the Source CV can't be parsed, 2 no CV or setup is missing (run
/ieakaso init), 3 input/cv.md was edited by hand (diff printed; --force overwrites), 4 new CV files wait for the
candidate's choice (stdout: one `New CV file: <path>` line each; the Parsed CV was still written from the current
version), 5 the tracker db can't be used or changed while capturing (nothing was moved), 6 a flag names a file
that is not waiting in the inbox, or an unknown Application. The first of 1, 2, 3 that applies wins over 4.
Other stdout lines: `Captured <id> ...`, `Duplicate: <path> ...` (same content as a version; left where it is) and
`Warning: <folder>/ ...` (a folder the parser didn't create; ignored).
The exit code reflects the CV alone: the other documents only print warnings.
"""

import argparse
import difflib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from ieakaso.cv_parser import PARSER_VERSION, CvParseError, documents, parse, versions
from ieakaso.cv_parser.files import sha as _sha
from ieakaso.cv_parser.files import write_atomic as _write_atomic
from ieakaso.repo import find_root, is_ieakaso_repo
from ieakaso.tracker import DB_PATH, Db, RecordNotFoundError, current_cv_version, load

STATUS = Path("db/system_status.json")
OUTPUT = Path("input/cv.md")
NO_CV = (
    "No CV found. Save your CV in input/documents/cv/ and run /ieakaso cv-parser again, "
    "or run /ieakaso init if the setup is missing."
)
CORRECT_FILE = "Put the corrected file in input/documents/cv/ and run /ieakaso cv-parser again."


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.cv_parser",
        description="Capture the CV versions waiting in input/documents/cv/ and write the Parsed CV (input/cv.md).",
    )
    parser.add_argument("--main", metavar="FILE", help="capture this new file as the new main CV")
    parser.add_argument("--tailored", metavar="FILE", help="capture this new file as a Tailored CV (needs --for)")
    parser.add_argument("--for", dest="tailored_for", metavar="ID", help="the Application ID of the Tailored CV")
    parser.add_argument("--force", action="store_true", help="overwrite input/cv.md even if it was edited by hand")
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    if not is_ieakaso_repo(root):
        print(f"error: {root} is not the ieakaso repo; nothing changed", file=sys.stderr)
        return 2

    status = _read_status(root)
    if not status:
        print(NO_CV, file=sys.stderr)
        return 2
    db = load(root / DB_PATH, root=root)
    if db.error:
        print(f"{db.error}\nNothing was changed.", file=sys.stderr)
        return 5

    today = today or date.today()  # noqa: DTZ011 - the candidate's local day
    now = datetime.now(UTC).isoformat(timespec="seconds")
    if not isinstance(status.get("documents"), dict):
        status["documents"] = {}
    if not isinstance(status["documents"].get("cv"), dict):
        status["documents"]["cv"] = {}
    cv = status["documents"]["cv"]
    before = json.dumps(cv, sort_keys=True)
    code, cv_changed, pending = 0, False, []
    try:
        pending = _capture(root, db, cv, today, args)
    except versions.VersionError as error:
        print(error, file=sys.stderr)
        return error.exit_code
    except CvParseError as error:
        print(f"{error}\n{CORRECT_FILE} {OUTPUT} was not changed.", file=sys.stderr)
        code = 1

    current = current_cv_version(db)
    if current:
        cv["status"], cv["path"] = "found", current["path"]
    if code:
        pass  # the new file can't be parsed; the other documents carry on
    elif current:
        code, cv_changed = _parse_cv(root, status, args.force, now)
    elif not pending:
        print(NO_CV, file=sys.stderr)
        code = 2
    documents_changed = documents.sync(root, status, args.force, now)
    if cv_changed or documents_changed or json.dumps(cv, sort_keys=True) != before:
        _write_atomic(root / STATUS, (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return code or (4 if pending else 0)


def _capture(root: Path, db: Db, cv: dict, today: date, args: argparse.Namespace) -> list[str]:
    """Capture what the flags and the rules say, report the inbox, and return the files still waiting for a choice."""
    if args.tailored and not args.tailored_for:
        raise versions.VersionError("--tailored needs --for <Application ID>.", 6)
    if args.tailored_for and not args.tailored:
        raise versions.VersionError("--for goes with --tailored <file>.", 6)
    if args.tailored_for and not db.find(args.tailored_for):
        raise versions.VersionError(str(RecordNotFoundError(f"no tracked Application has the ID {args.tailored_for!r}")), 6)

    migration = versions.migration_source(root, db, cv)
    if migration:
        source_rel, parsed_on = migration
        version, linked = versions.capture(root, db, source_rel, parsed_on, link_applied=True)
        print(
            f"Captured {version['id']} ({version['label']}) as the first CV version, from {source_rel}; "
            f"{len(linked)} Application(s) past Lead now hold it."
        )

    inbox = versions.scan(root, db)
    main = versions.resolve(inbox, args.main) if args.main else None
    tailored = versions.resolve(inbox, args.tailored) if args.tailored else None
    if not db.cv_versions and not main and not tailored and len(inbox.new) == 1:
        main = inbox.new[0]  # the first CV there is: nothing to choose
    for rel, tailored_for in ((main, None), (tailored, args.tailored_for)):
        if rel and rel in inbox.new:
            version, _ = versions.capture(root, db, rel, today, tailored_for=tailored_for)
            kind = f"the Tailored CV for {tailored_for}" if tailored_for else "the new main CV"
            print(f"Captured {version['id']} ({version['label']}) as {kind}, from {rel}.")
            inbox = versions.scan(root, db)

    for rel in inbox.foreign_folders:
        print(f"Warning: {rel}/ was not created by Ieakaso, so its contents are ignored.")
    for rel, version in inbox.duplicates:
        print(f"Duplicate: {rel} has the same content as CV version {version['id']} ({version['label']}); left where it is.")
    for rel in inbox.new:
        print(f"New CV file: {rel}")
    return inbox.new


def _parse_cv(root: Path, status: dict, force: bool, now: str) -> tuple[int, bool]:
    """The exit code for the Parsed CV, and whether its record in status changed."""
    cv = _cv_record(status)
    source_rel = cv.get("path")
    if not source_rel or not (root / source_rel).is_file():
        print(NO_CV, file=sys.stderr)
        return 2, False

    source_bytes = (root / source_rel).read_bytes()
    output = root / OUTPUT
    current = output.read_bytes() if output.is_file() else None
    recorded = cv.get("parsed") or {}
    if current is not None and _matches(recorded, _fingerprint(source_rel, source_bytes, current)):
        print(f"{OUTPUT} is up to date with {source_rel}.")
        return 0, False

    try:
        new = parse(root / source_rel).encode("utf-8")
    except CvParseError as error:
        print(f"{error}\n{CORRECT_FILE} {OUTPUT} was not changed.", file=sys.stderr)
        return 1, False

    edited_by_hand = current is not None and current != new and recorded.get("output_sha256") != _sha(current)
    if edited_by_hand and not force:
        _print_overwrite_diff(current, new, source_rel)
        return 3, False

    if current != new:
        _write_atomic(output, new)
    cv["parsed"] = {**_fingerprint(source_rel, source_bytes, new), "parsed_at": now}
    print(f"Wrote {OUTPUT} from {source_rel}.")
    return 0, True


def _read_status(root: Path) -> dict:
    """db/system_status.json, or {} when it is missing or not a JSON object."""
    try:
        status = json.loads((root / STATUS).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return status if isinstance(status, dict) else {}


def _cv_record(status: dict) -> dict:
    """status["documents"]["cv"], the dict itself so changes to it are saved; {} when absent."""
    documents = status.get("documents")
    cv = documents.get("cv") if isinstance(documents, dict) else None
    return cv if isinstance(cv, dict) else {}


def _fingerprint(source_rel: str, source: bytes, output: bytes) -> dict:
    """What a parse depends on and produced; the Parsed CV is up to date while all of it matches."""
    return {
        "source_path": source_rel,
        "source_sha256": _sha(source),
        "parser_version": PARSER_VERSION,
        "output_sha256": _sha(output),
    }


def _matches(recorded: dict, fingerprint: dict) -> bool:
    return all(recorded.get(key) == value for key, value in fingerprint.items())


def _print_overwrite_diff(current: bytes, new: bytes, source_rel: str) -> None:
    diff = difflib.unified_diff(
        current.decode("utf-8", "replace").splitlines(keepends=True),
        new.decode("utf-8").splitlines(keepends=True),
        fromfile=f"{OUTPUT} (now)",
        tofile=f"{OUTPUT} (parsed from {source_rel})",
    )
    print("".join(diff), end="")
    print(
        f"\n{OUTPUT} was changed by hand since it was last parsed. Parsing again replaces it with the "
        "version above and discards those changes. To keep them, put them in your CV instead. "
        "Run again with --force to replace it."
    )
