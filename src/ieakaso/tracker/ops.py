"""What the tracker does to a loaded db. Each operation validates first and changes nothing when it refuses."""

import copy
from datetime import date

from ieakaso.tracker.errors import InvalidRecordError, RecordNotFoundError
from ieakaso.tracker.schema import STATUSES, is_date, validate
from ieakaso.tracker.store import Db

EDIT_KEYS = (
    "company",
    "position",
    "status",
    "stage",
    "stages",
    "applied_on",
    "home_office",
    "location",
    "salary_expectation",
    "source",
    "contacts",
    "notes",
)
EDIT_SOURCE_KEYS = ("board", "board_url", "form_url")
PAYLOAD_KEYS = ("id", "company", "position", "analysis", "home_office", "location", "source", "contacts")
NO_ANSWER_AFTER_DAYS = 30


def _get(db: Db, record_id: str) -> dict:
    record = db.find(record_id)
    if record is None:
        raise RecordNotFoundError(f"no tracked Application has the ID {record_id!r}")
    return record


def _replace(db: Db, record: dict, new: dict) -> dict:
    validate(new)
    record.clear()
    record.update(new)
    return record


def _empty(value) -> bool:
    return value is None or value == ""


def upsert_from_analysis(db: Db, payload: dict, today: date) -> tuple[dict, bool]:
    """Create the record of a Job analysis, or update an existing one. Returns the record and whether it is new.

    The re-run rule (docs/database.md): an existing record gets the new `analysis` and its still-empty fields filled;
    nothing already there is overwritten, and status, stage, stages, contacts, notes and salary_expectation stay.
    """
    if not isinstance(payload, dict):
        raise InvalidRecordError("the Job analysis payload must be a JSON object")
    unknown = sorted(set(payload) - set(PAYLOAD_KEYS))
    if unknown:
        raise InvalidRecordError(f"the Job analysis payload can't set {', '.join(unknown)}")
    missing = [key for key in ("id", "company", "position", "analysis", "source") if key not in payload]
    if missing:
        raise InvalidRecordError(f"the Job analysis payload needs {', '.join(missing)}")
    analysis = {"on": today.isoformat(), **payload["analysis"]} if isinstance(payload["analysis"], dict) else {}
    source = payload["source"] if isinstance(payload["source"], dict) else {}
    incoming = {
        "company": payload["company"],
        "position": payload["position"],
        "analysis": analysis,
        "home_office": payload.get("home_office"),
        "location": {"city": None, "country": None, **(payload.get("location") or {})},
        "source": {"board": None, "board_url": None, "form_url": None, **source},
    }
    existing = db.find(payload["id"]) if isinstance(payload["id"], str) else None
    if existing is None:
        record = {
            "id": payload["id"],
            "company": incoming["company"],
            "position": incoming["position"],
            "status": "lead",
            "status_history": [{"status": "lead", "on": analysis.get("on")}],
            "stage": 0,
            "stages": [],
            "created_at": analysis.get("on"),
            "analysis": analysis,
            "applied_on": None,
            "home_office": incoming["home_office"],
            "location": incoming["location"],
            "salary_expectation": None,
            "cover_letter": None,
            "source": {**incoming["source"], "form_url": None},
            "contacts": copy.deepcopy(payload.get("contacts") or []),
            "notes": "",
        }
        validate(record)
        db.records.append(record)
        return record, True

    new = copy.deepcopy(existing)
    new["analysis"] = analysis
    for key in ("company", "position", "home_office"):
        if _empty(new[key]):
            new[key] = incoming[key]
    for key in ("city", "country"):
        if _empty(new["location"].get(key)):
            new["location"][key] = incoming["location"][key]
    for key in ("board", "board_url", "job_description"):
        if _empty(new["source"].get(key)) and key in incoming["source"]:
            new["source"][key] = incoming["source"][key]
    return _replace(db, existing, new), False


def _change_status(record: dict, status: str, today: date) -> None:
    if status == record["status"]:
        return
    record["status"] = status
    record["status_history"].append({"status": status, "on": today.isoformat()})
    if status == "applied" and _empty(record["applied_on"]):
        record["applied_on"] = today.isoformat()


def set_status(db: Db, record_id: str, status: str, today: date) -> dict:
    """Set the Application status (any to any), appending to `status_history`; `applied` fills an empty `applied_on`."""
    record = _get(db, record_id)
    if status not in STATUSES:
        raise InvalidRecordError(f"status must be one of {', '.join(STATUSES)}")
    new = copy.deepcopy(record)
    _change_status(new, status, today)
    return _replace(db, record, new)


def set_cover_letter(db: Db, record_id: str, path: str) -> dict:
    record = _get(db, record_id)
    new = copy.deepcopy(record)
    new["cover_letter"] = path
    return _replace(db, record, new)


def update_record(db: Db, record_id: str, changes: dict, today: date) -> dict:
    """Apply the candidate's edits to the editable fields (docs/database.md). Refuses anything else."""
    record = _get(db, record_id)
    unknown = sorted(set(changes) - set(EDIT_KEYS))
    if unknown:
        raise InvalidRecordError(f"can't edit {', '.join(unknown)}")
    new = copy.deepcopy(record)
    for key, value in changes.items():
        if key == "status":
            continue
        if key == "source":
            if not isinstance(value, dict) or set(value) - set(EDIT_SOURCE_KEYS):
                raise InvalidRecordError(f"can't edit source fields other than {', '.join(EDIT_SOURCE_KEYS)}")
            new["source"].update(value)
        else:
            new[key] = copy.deepcopy(value)
    if "status" in changes:
        if changes["status"] not in STATUSES:
            raise InvalidRecordError(f"status must be one of {', '.join(STATUSES)}")
        _change_status(new, changes["status"], today)
    return _replace(db, record, new)


def no_answer_candidates(db: Db, today: date) -> list[dict]:
    """Applied records whose application is more than 30 days old: the viewer suggests No answer for them."""
    found = []
    for record in db.records:
        applied_on = record.get("applied_on")
        if record["status"] != "applied" or not is_date(applied_on):
            continue
        if (today - date.fromisoformat(applied_on)).days > NO_ANSWER_AFTER_DAYS:
            found.append(record)
    return found
