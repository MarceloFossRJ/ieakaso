class TrackerError(Exception):
    """The tracker can't do what was asked. The message is written for the candidate; exit_code is the command's."""

    exit_code = 1


class InvalidRecordError(TrackerError):
    """A record, a Job analysis payload or an edit breaks the schema in docs/database.md."""

    exit_code = 1


class InvalidDbError(TrackerError):
    """db/ieakaso_db.json is not valid JSON or not a tracker file. The tracker never overwrites it."""

    exit_code = 2


class ConflictError(TrackerError):
    """The file changed on disk after it was read, so saving would overwrite someone else's change."""

    exit_code = 3


class RecordNotFoundError(TrackerError):
    """No record has that Application ID."""

    exit_code = 4
