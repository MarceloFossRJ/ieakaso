"""Reading an Application's files for the cover_letter commands, with the error each failure ends with."""

from pathlib import Path

from ieakaso.cover_letter.errors import ApplicationError, RoundFileError
from ieakaso.layout import APPLICATIONS

NOTES = "## Notes for the Assistant"


def read(path: Path, error: type[Exception], what: str) -> str:
    try:
        return path.read_text()
    except OSError:
        raise error(f"{what} missing or unreadable: {path}") from None


def application_folder(root: Path, application_id: str) -> Path:
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"no Application folder: {folder}")
    return folder


def job_ad_path(folder: Path, application_id: str) -> Path:
    return folder / f"{application_id}_job-ad.md"


def draft_path(folder: Path, round_number: int) -> Path:
    return folder / "rounds" / f"round-{round_number}_draft.md"


def split_draft(path: Path) -> tuple[str, str]:
    """A Round's draft file as its Draft section (the letter, without the heading) and its notes for the Assistant."""
    head, found, notes = read(path, RoundFileError, "Round file").partition(NOTES)
    if not found or not head.startswith("## Draft"):
        raise RoundFileError(f"{path}: not a draft ('## Draft' then '{NOTES}')")
    return head.removeprefix("## Draft"), notes
