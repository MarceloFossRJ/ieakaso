class CoverLetterError(Exception):
    """A failure the command reports on stderr, with the exit code it ends with."""

    exit_code = 1


class RoundFileError(CoverLetterError):
    """A Round file is missing or not in the format its agent returns, or the arguments name a Round that isn't there."""

    exit_code = 1


class ApplicationError(CoverLetterError):
    """The Application's folder or its Job ad file is missing."""

    exit_code = 3
