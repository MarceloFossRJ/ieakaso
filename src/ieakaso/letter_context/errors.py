class LetterContextError(Exception):
    """A failure the command reports on stderr, with the exit code it ends with; nothing is written."""

    exit_code = 3


class ApplicationError(LetterContextError):
    """The Application's folder or its Job analysis is missing."""
