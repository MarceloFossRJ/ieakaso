"""The record schema of docs/database.md: allowed values and validation. Nothing here touches the disk."""

import re
from datetime import date
from typing import Any

from ieakaso.tracker.errors import InvalidRecordError

SCHEMA_VERSION = 1
STATUSES = ("lead", "desisted", "applied", "no_answer", "interviewing", "offer", "not_selected")
CLOSED_STATUSES = ("desisted", "not_selected")
VERDICTS = ("Top applicant", "Apply", "Stretch", "Don't apply")
CONTACT_TYPES = ("recruiter", "hiring_manager", "referral", "other")
PERIODS = ("yearly", "monthly", "daily", "hourly")

RECORD_KEYS = (
    "id",
    "company",
    "position",
    "status",
    "status_history",
    "stage",
    "stages",
    "created_at",
    "analysis",
    "applied_on",
    "home_office",
    "location",
    "salary_expectation",
    "cover_letter",
    "source",
    "contacts",
    "notes",
)
ANALYSIS_KEYS = ("on", "doc", "score", "verdict")
SOURCE_KEYS = ("board", "board_url", "form_url", "job_ad")
LOCATION_KEYS = ("city", "country")
SALARY_KEYS = ("period", "min", "max", "currency")
CONTACT_KEYS = ("contact_type", "name", "linkedin_url", "email")

_SNAKE = re.compile(r"[a-z][a-z0-9_]*")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")


def is_date(value: Any) -> bool:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_path(value: Any) -> bool:
    """A repo-relative path with forward slashes."""
    if not _is_text(value) or "\\" in value or value.startswith("/") or re.match(r"[A-Za-z]:", value):
        return False
    return ".." not in value.split("/")


def _keys(where: str, value: dict, expected: tuple[str, ...], out: list[str]) -> None:
    for key in value:
        if not isinstance(key, str) or not _SNAKE.fullmatch(key):
            out.append(f"{where}: key {key!r} is not snake_case")
        elif key not in expected:
            out.append(f"{where}: unknown key {key!r}")
    for key in expected:
        if key not in value:
            out.append(f"{where}: missing key {key!r}")


def _optional_text(where: str, value: Any, out: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        out.append(f"{where} must be text or null")


def problems(record: Any) -> list[str]:
    """Everything wrong with a record, one message each; empty when it is valid."""
    if not isinstance(record, dict):
        return ["a record must be an object"]
    out: list[str] = []
    _keys("record", record, RECORD_KEYS, out)
    get = record.get

    if "id" in record and not (isinstance(get("id"), str) and _ID.fullmatch(get("id"))):
        out.append("id must be lowercase text: <company>_<position>_<yyyy-mm-dd>, each part in kebab-case")
    for key in ("company", "position"):
        if key in record and not _is_text(get(key)):
            out.append(f"{key} must be non-empty text")
    if "status" in record and get("status") not in STATUSES:
        out.append(f"status must be one of {', '.join(STATUSES)}")
    if "status_history" in record:
        history = get("status_history")
        if not isinstance(history, list) or not history:
            out.append("status_history must be a non-empty list")
        else:
            for entry in history:
                if not (isinstance(entry, dict) and set(entry) == {"status", "on"}):
                    out.append("status_history entries must be {status, on}")
                elif entry["status"] not in STATUSES or not is_date(entry["on"]):
                    out.append(f"status_history entry {entry} needs a valid status and a yyyy-mm-dd date")
    stages = get("stages")
    if "stages" in record:
        if not isinstance(stages, list):
            out.append("stages must be a list")
        else:
            for stage in stages:
                if not (isinstance(stage, dict) and set(stage) == {"name", "description"}):
                    out.append("stages entries must be {name, description}")
                elif not _is_text(stage["name"]) or not isinstance(stage["description"], str):
                    out.append(f"stage {stage} needs a name and a text description")
    if "stage" in record:
        stage = get("stage")
        count = len(stages) if isinstance(stages, list) else 0
        if not _is_int(stage) or not 0 <= stage <= count:
            out.append(f"stage must be a whole number from 0 to the number of stages ({count})")
    for key in ("created_at", "applied_on"):
        if key in record and not (is_date(get(key)) or (key == "applied_on" and get(key) is None)):
            out.append(f"{key} must be a yyyy-mm-dd date" + (" or null" if key == "applied_on" else ""))
    if "home_office" in record:
        _optional_text("home_office", get("home_office"), out)
    if "notes" in record and not isinstance(get("notes"), str):
        out.append("notes must be text")
    if "cover_letter" in record and get("cover_letter") is not None and not _is_path(get("cover_letter")):
        out.append("cover_letter must be a repo-relative path or null")

    _analysis(get("analysis"), "analysis" in record, out)
    _location(get("location"), "location" in record, out)
    _salary(get("salary_expectation"), "salary_expectation" in record, out)
    _source(get("source"), "source" in record, out)
    _contacts(get("contacts"), "contacts" in record, out)
    return out


def _analysis(value: Any, present: bool, out: list[str]) -> None:
    if not present:
        return
    if not isinstance(value, dict):
        out.append("analysis must be an object")
        return
    _keys("analysis", value, ANALYSIS_KEYS, out)
    if "on" in value and not is_date(value["on"]):
        out.append("analysis.on must be a yyyy-mm-dd date")
    if "doc" in value and not _is_path(value["doc"]):
        out.append("analysis.doc must be a repo-relative path")
    if "score" in value and not (_is_int(value["score"]) and 0 <= value["score"] <= 100):
        out.append("analysis.score must be a whole number from 0 to 100")
    if "verdict" in value and value["verdict"] not in VERDICTS:
        out.append(f"analysis.verdict must be one of {', '.join(VERDICTS)}")


def _location(value: Any, present: bool, out: list[str]) -> None:
    if not present:
        return
    if not isinstance(value, dict):
        out.append("location must be an object")
        return
    _keys("location", value, LOCATION_KEYS, out)
    _optional_text("location.city", value.get("city"), out)
    country = value.get("country")
    if country is not None and not (isinstance(country, str) and re.fullmatch(r"[A-Z]{2}", country)):
        out.append("location.country must be an ISO 3166-1 alpha-2 code (DE) or null")


def _salary(value: Any, present: bool, out: list[str]) -> None:
    if not present or value is None:
        return
    if not isinstance(value, dict):
        out.append("salary_expectation must be an object or null")
        return
    _keys("salary_expectation", value, SALARY_KEYS, out)
    if "period" in value and value["period"] not in PERIODS:
        out.append(f"salary_expectation.period must be one of {', '.join(PERIODS)}")
    low, high = value.get("min"), value.get("max")
    if not (_is_number(low) and _is_number(high)) or low < 0 or low > high:
        out.append("salary_expectation.min and max must be numbers with min not above max")
    currency = value.get("currency")
    if not (isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency)):
        out.append("salary_expectation.currency must be an ISO 4217 code (EUR)")


def _source(value: Any, present: bool, out: list[str]) -> None:
    if not present:
        return
    if not isinstance(value, dict):
        out.append("source must be an object")
        return
    _keys("source", value, SOURCE_KEYS, out)
    for key in ("board", "board_url", "form_url"):
        _optional_text(f"source.{key}", value.get(key), out)
    if "job_ad" in value and not _is_path(value["job_ad"]):
        out.append("source.job_ad must be a repo-relative path")


def _contacts(value: Any, present: bool, out: list[str]) -> None:
    if not present:
        return
    if not isinstance(value, list):
        out.append("contacts must be a list")
        return
    for contact in value:
        if not isinstance(contact, dict):
            out.append("contacts entries must be objects")
            continue
        _keys("contact", contact, CONTACT_KEYS, out)
        if contact.get("contact_type") not in CONTACT_TYPES:
            out.append(f"contact_type must be one of {', '.join(CONTACT_TYPES)}")
        if not _is_text(contact.get("name")):
            out.append("a contact needs a name")
        for key in ("linkedin_url", "email"):
            _optional_text(f"contact.{key}", contact.get(key), out)


def validate(record: Any) -> None:
    """Raise InvalidRecordError naming what is wrong, if anything."""
    found = problems(record)
    if found:
        who = record.get("id") if isinstance(record, dict) else None
        raise InvalidRecordError(("record " + repr(who) + ": " if who else "") + "; ".join(found))
