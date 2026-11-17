class EvidenceBankError(Exception):
    """A failure the command reports on stderr, with the exit code it ends with."""

    exit_code = 2


class NoBankError(EvidenceBankError):
    """The Application has no Evidence bank file, or the file has no Sources section to check."""


class ApplicationError(EvidenceBankError):
    """The Application's folder is missing."""

    exit_code = 3
