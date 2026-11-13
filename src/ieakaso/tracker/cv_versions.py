"""CV versions in the tracker (docs/database.md, docs/adr/0005-cv-versions.md): adding one, its label, which one a record
holds. Like the other operations, each validates first and changes nothing when it refuses."""

import copy
from datetime import date

from ieakaso.tracker.errors import InvalidRecordError, RecordNotFoundError
from ieakaso.tracker.ops import get_record, is_empty, replace_record
from ieakaso.tracker.schema import cv_version_problems, fits_application
from ieakaso.tracker.store import Db


def _version(db: Db, version_id: str) -> dict:
    version = db.find_cv_version(version_id)
    if version is None:
        raise RecordNotFoundError(f"no CV version has the ID {version_id!r}")
    return version


def next_cv_version_id(db: Db, today: date) -> str:
    """`cv_<yyyy-mm-dd>` for the first version captured on `today`, then `_2`, `_3` for the others."""
    base = f"cv_{today.isoformat()}"
    taken = {v["id"] for v in db.cv_versions}
    candidate, n = base, 1
    while candidate in taken:
        n += 1
        candidate = f"{base}_{n}"
    return candidate


def add_cv_version(
    db: Db, version_id: str, label: str, path: str, today: date, tailored_for: str | None = None
) -> dict:
    """Record a captured CV version; `path` is its Source CV, relative to the repo root.

    A Tailored CV (`tailored_for` an Application ID) also becomes that Application's `cv_version`.
    """
    version = {
        "id": version_id,
        "label": label,
        "path": path,
        "captured_at": today.isoformat(),
        "tailored_for": tailored_for,
    }
    found = cv_version_problems(version)
    if found:
        raise InvalidRecordError("; ".join(found))
    if db.find_cv_version(version_id):
        raise InvalidRecordError(f"a CV version with the ID {version_id!r} already exists")
    record = get_record(db, tailored_for) if tailored_for else None
    db.cv_versions.append(version)
    if record is not None:
        record["cv_version"] = version_id
    return version


def set_cv_version_label(db: Db, version_id: str, label: str) -> dict:
    version = _version(db, version_id)
    new = {**version, "label": label.strip()}
    found = cv_version_problems(new)
    if found:
        raise InvalidRecordError("; ".join(found))
    version["label"] = new["label"]
    return version


def set_record_cv_version(db: Db, record_id: str, version_id: str | None) -> dict:
    """Set the CV version an Application was sent with (`None` clears it). A Tailored CV fits its own Application only."""
    record = get_record(db, record_id)
    if version_id is not None:
        version = _version(db, version_id)
        if not fits_application(version, record_id):
            raise InvalidRecordError(
                f"CV version {version_id!r} is a Tailored CV for another Application, so it can't be set on {record_id!r}"
            )
    new = copy.deepcopy(record)
    new["cv_version"] = version_id
    return replace_record(record, new)


def link_applied_records(db: Db, version_id: str) -> list[str]:
    """Give every record past Lead (`applied_on` set) that holds no CV version this one. Returns their IDs."""
    _version(db, version_id)
    linked = []
    for record in db.records:
        if not is_empty(record["applied_on"]) and is_empty(record["cv_version"]):
            record["cv_version"] = version_id
            linked.append(record["id"])
    return linked
