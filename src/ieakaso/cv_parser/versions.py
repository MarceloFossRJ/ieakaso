"""CV versions (docs/adr/0005-cv-versions.md): `input/documents/cv/` is an inbox, and each Source CV with new content
is moved into its own folder `input/documents/cv/<version-id>/`, next to a frozen copy of its Parsed CV.

Everything here is deterministic. What the candidate has to decide (which new file is the main CV, which is a
Tailored CV, which is not a CV) is decided by the mode and handed to the command as flags. The tracker is the only
writer of the db: this module imports its operations.
"""

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath

from ieakaso import cv_parser
from ieakaso.cv_parser.files import sha, write_atomic
from ieakaso.tracker import (
    Db,
    TrackerError,
    add_cv_version,
    link_applied_records,
    next_cv_version_id,
    save,
)

INBOX = PurePosixPath("input/documents/cv")
PARSED_NAME = "parsed-cv.md"  # the frozen Parsed CV in a version's folder


class VersionError(Exception):
    """Something the candidate must fix first; exit_code is the command's."""

    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class Inbox:
    """What is lying in the inbox, as repo-relative paths."""

    new: list[str] = field(default_factory=list)  # a CV format whose content is no version yet
    duplicates: list[tuple[str, dict]] = field(default_factory=list)  # the file and the version it matches
    foreign_folders: list[str] = field(default_factory=list)  # folders the parser didn't create


def scan(root: Path, db: Db) -> Inbox:
    by_sha = {}
    for version in db.cv_versions:
        source = root / version["path"]
        if source.is_file():
            by_sha.setdefault(sha(source.read_bytes()), version)
    known = {v["id"] for v in db.cv_versions}
    inbox = Inbox()
    for entry in sorted((root / INBOX).iterdir()) if (root / INBOX).is_dir() else []:
        rel = (INBOX / entry.name).as_posix()
        if entry.is_dir():
            if entry.name not in known:
                inbox.foreign_folders.append(rel)
        elif entry.is_file() and not entry.name.startswith(".") and entry.suffix.lower() in cv_parser.ACCEPTED:
            match = by_sha.get(sha(entry.read_bytes()))
            if match:
                inbox.duplicates.append((rel, match))
            else:
                inbox.new.append(rel)
    return inbox


def resolve(inbox: Inbox, name: str) -> str:
    """The repo-relative path of the new file `name` (a file name, or a path from the repo root) in the inbox."""
    for rel in inbox.new:
        if name in (rel, PurePosixPath(rel).name):
            return rel
    for rel, _ in inbox.duplicates:
        if name in (rel, PurePosixPath(rel).name):
            return rel
    raise VersionError(f"{name} is not a CV file in {INBOX}/ (it must be saved there, not in a folder).", 6)


def capture(
    root: Path,
    db: Db,
    source_rel: str,
    captured_on: date,
    tailored_for: str | None = None,
    link_applied: bool = False,
) -> tuple[dict, list[str]]:
    """Move the Source CV into its version folder with a frozen Parsed CV, record the version, and save the db.

    Returns the version and the IDs of the records linked to it (`link_applied`: those past Lead). Nothing is moved
    when the file can't be parsed (CvParseError) or the db can't be saved; the file then stays in the inbox.
    """
    source = root / source_rel
    parsed = cv_parser.parse(source).encode("utf-8")
    version_id = next_cv_version_id(db, captured_on)
    folder = root / INBOX / version_id
    target_rel = (INBOX / version_id / source.name).as_posix()
    try:
        folder.mkdir(parents=True)
        shutil.copy2(source, root / target_rel)
        write_atomic(folder / (PARSED_NAME if source.name != PARSED_NAME else "parsed-cv.frozen.md"), parsed)
        count = len(db.cv_versions)
        try:
            version = add_cv_version(db, version_id, source.stem, target_rel, captured_on, tailored_for)
            linked = link_applied_records(db, version_id) if link_applied else []
            save(db)
        except TrackerError as error:
            del db.cv_versions[count:]
            raise VersionError(f"{error} Nothing was moved; run the CV parser again.", 5) from error
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    source.unlink()
    return version, linked


def migration_source(root: Path, db: Db, cv: dict) -> tuple[str, date] | None:
    """The Source CV that lies directly in the inbox from before CV versions, and the day it was parsed.

    Only before any version exists, and only when it was parsed once (`documents.cv.parsed.parsed_at`).
    """
    path = cv.get("path")
    parsed = cv.get("parsed")
    parsed_at = parsed.get("parsed_at") if isinstance(parsed, dict) else None
    if db.cv_versions or not isinstance(path, str) or not isinstance(parsed_at, str):
        return None
    if PurePosixPath(path).parent != INBOX or not (root / path).is_file():
        return None
    try:
        return path, date.fromisoformat(parsed_at[:10])
    except ValueError:
        return None
