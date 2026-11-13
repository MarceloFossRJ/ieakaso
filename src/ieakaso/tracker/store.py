"""Load and save db/ieakaso_db.json: atomic writes, a change check, and no overwriting of a file it couldn't read."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ieakaso.tracker.errors import ConflictError, InvalidDbError, InvalidRecordError
from ieakaso.tracker.schema import SCHEMA_VERSION, cv_version_problems, links_problem, problems, validate

DB_PATH = Path("db/ieakaso_db.json")
COMPANY_RESEARCH_PATH = "output/applications/{id}/{id}_company-research.md"


@dataclass
class Db:
    """The tracker file as read. `signature` is what the file held then; `error` is set when it couldn't be used."""

    path: Path
    records: list[dict] = field(default_factory=list)
    cv_versions: list[dict] = field(default_factory=list)
    signature: str | None = None
    error: str | None = None

    def changed_on_disk(self) -> bool:
        return _signature(self.path) != self.signature

    def find(self, record_id: str) -> dict | None:
        return next((r for r in self.records if r.get("id") == record_id), None)

    def find_cv_version(self, version_id: str) -> dict | None:
        return next((v for v in self.cv_versions if v.get("id") == version_id), None)


def current_cv_version(db: Db) -> dict | None:
    """The most recently captured CV version that is not a Tailored CV. Derived on every call, never stored."""
    return next((v for v in reversed(db.cv_versions) if v["tailored_for"] is None), None)


def _signature(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def load(path: Path, root: Path | None = None) -> Db:
    """Read the file. A missing file is an empty db; an unusable one comes back with `error` set and no records.

    `root` is the repo root the records' paths are relative to. An older file is upgraded on load (`_migrate`), and
    the upgrade looks there for files to fill in; without a root it fills in nothing.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return Db(path)
    except OSError as error:
        return Db(path, error=f"{path.name} can't be read: {error}")
    signature = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw)
    except ValueError as error:
        return Db(path, signature=signature, error=f"{path.name} is not valid JSON: {error}")
    _migrate(data, root)
    reason = _structure_problem(data)
    if reason:
        return Db(path, signature=signature, error=f"{path.name} {reason}")
    return Db(path, records=data["records"], cv_versions=data["cv_versions"], signature=signature)


def _is_tracker_file(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("meta"), dict) and isinstance(data.get("records"), list)


def _migrate(data: Any, root: Path | None) -> None:
    """Upgrade an older file in memory to SCHEMA_VERSION; the next save writes it. Anything else is left as it is.

    Version 1 had no `company_research`: it is the report's path when the report is in `root`, otherwise null.
    Version 2 had no CV versions: the file gets an empty list and every record a null `cv_version`; the CV parser
    then captures the Source CV and links the Applications past Lead to it.
    """
    if not _is_tracker_file(data):
        return
    if data["meta"].get("schema_version") == 1:
        for record in data["records"]:
            if isinstance(record, dict) and "company_research" not in record:
                report = COMPANY_RESEARCH_PATH.format(id=record.get("id"))
                record["company_research"] = report if root and (root / report).is_file() else None
        data["meta"]["schema_version"] = 2
    if data["meta"].get("schema_version") == 2:
        data["cv_versions"] = []
        for record in data["records"]:
            if isinstance(record, dict):
                record.setdefault("cv_version", None)
        data["meta"]["schema_version"] = SCHEMA_VERSION


def _structure_problem(data: Any) -> str | None:
    if not _is_tracker_file(data):
        return 'is not a tracker file: it needs "meta" and a list of "records"'
    if data["meta"].get("schema_version") != SCHEMA_VERSION:
        return f"has schema_version {data['meta'].get('schema_version')!r}, this tracker reads {SCHEMA_VERSION}"
    if not isinstance(data.get("cv_versions"), list):
        return 'is not a tracker file: it needs a list of "cv_versions"'
    for version in data["cv_versions"]:
        found = cv_version_problems(version)
        if found:
            return f"has an invalid CV version: {'; '.join(found)}"
    for record in data["records"]:
        found = problems(record)
        if found:
            who = record.get("id") if isinstance(record, dict) else record
            return f"has an invalid record {who!r}: {'; '.join(found)}"
    return links_problem(data["records"], data["cv_versions"])


def save(db: Db) -> None:
    """Write the records atomically. Refuses a db that couldn't be read, an invalid record, or a file that changed."""
    if db.error:
        raise InvalidDbError(f"not saving: {db.error}")
    for version in db.cv_versions:
        found = cv_version_problems(version)
        if found:
            raise InvalidRecordError("; ".join(found))
    for record in db.records:
        validate(record)
    linked = links_problem(db.records, db.cv_versions)
    if linked:
        raise InvalidRecordError(f"{db.path.name} {linked}")
    if db.changed_on_disk():
        raise ConflictError(f"{db.path.name} changed on disk since it was read; nothing was saved")
    data = {"meta": {"schema_version": SCHEMA_VERSION}, "cv_versions": db.cv_versions, "records": db.records}
    text = json.dumps(data, indent=2, ensure_ascii=False)
    db.path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=db.path.parent, prefix=f".{db.path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text + "\n")
        os.replace(temp, db.path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
    db.signature = _signature(db.path)
