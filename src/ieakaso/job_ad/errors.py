class JobAdError(Exception):
    """The Job ad can't be read. The message is written for the candidate; exit_code is the command's."""

    exit_code = 1


class FetchError(JobAdError):
    """Network error, timeout or HTTP status >= 400."""

    exit_code = 1


class UnreadableError(JobAdError):
    """Not readable without the candidate: a login wall, or the ad is closed or expired."""

    exit_code = 2


class NoAdError(JobAdError):
    """The page was fetched, but holds no ad content."""

    exit_code = 3
