"""The applications tracker: the only reader and writer of db/ieakaso_db.json (model in docs/database.md).

Deterministic code like the CV parser. Modes call its command line; the viewer imports it.
"""

from ieakaso.tracker.errors import (
    ConflictError,
    InvalidDbError,
    InvalidRecordError,
    RecordNotFoundError,
    TrackerError,
)
from ieakaso.tracker.ops import (
    EDIT_KEYS,
    no_answer_candidates,
    set_cover_letter,
    set_status,
    update_record,
    upsert_from_analysis,
)
from ieakaso.tracker.schema import (
    CLOSED_STATUSES,
    CONTACT_TYPES,
    PERIODS,
    STATUSES,
    VERDICTS,
    problems,
    validate,
)
from ieakaso.tracker.store import DB_PATH, Db, load, save

__all__ = [
    "CLOSED_STATUSES",
    "CONTACT_TYPES",
    "DB_PATH",
    "EDIT_KEYS",
    "PERIODS",
    "STATUSES",
    "VERDICTS",
    "ConflictError",
    "Db",
    "InvalidDbError",
    "InvalidRecordError",
    "RecordNotFoundError",
    "TrackerError",
    "load",
    "no_answer_candidates",
    "problems",
    "save",
    "set_cover_letter",
    "set_status",
    "update_record",
    "upsert_from_analysis",
    "validate",
]
