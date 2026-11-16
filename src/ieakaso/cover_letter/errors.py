class CoverLetterError(Exception):
    """A failure the command reports on stderr, with the exit code it ends with."""

    exit_code = 1


class ArgumentError(CoverLetterError):
    """An argument names something that isn't there: an Exit outside the fixed set, or a Round out of range."""


class RoundFileError(CoverLetterError):
    """A Round file is missing or not in the format its agent returns."""


class ApplicationError(CoverLetterError):
    """The Application's folder or its Job ad file is missing, or its Company research file is unreadable."""

    exit_code = 3
