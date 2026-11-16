"""Builds `<id>_cover-letter.md` and `<id>_cover-letter-review.md` from `rounds/round-<n>_draft.md` and `_review.md`.

The review log's format is the one `ai/skills/ieakaso/modes/cover-letter.md` defines. Nothing is written unless every
Round file is there and readable.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ieakaso.cover_letter.errors import ApplicationError, RoundFileError

APPLICATIONS = Path("output/applications")
NOTES = "## Notes for the Assistant"
SCORE = re.compile(r"^## Review score: (\d+)/100\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Round:
    number: int
    draft: str
    review: str
    score: int
    refused: str
    language: str


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        raise RoundFileError(f"Round file missing or unreadable: {path}") from None


def _field(notes: str, label: str, path: Path) -> str:
    """The value of a `- **<label>:**` bullet of the Applicant's notes, with its continuation lines."""
    match = re.search(rf"^- \*\*{label}:\*\*(.*?)(?=^- \*\*|\Z)", notes, re.MULTILINE | re.DOTALL)
    if not match or not match.group(1).strip():
        raise RoundFileError(f"{path}: no '{label}' in the notes for the Assistant")
    return "\n".join(line.strip() if i == 0 else line for i, line in enumerate(match.group(1).strip().splitlines()))


def read_round(rounds: Path, number: int) -> Round:
    draft_path, review_path = rounds / f"round-{number}_draft.md", rounds / f"round-{number}_review.md"
    text, review = _read(draft_path), _read(review_path)
    head, found, notes = text.partition(NOTES)
    if not found or not head.startswith("## Draft"):
        raise RoundFileError(f"{draft_path}: not a draft ('## Draft' then '{NOTES}')")
    score = SCORE.search(review)
    if not score:
        raise RoundFileError(f"{review_path}: no '## Review score: <n>/100' line")
    return Round(
        number=number,
        draft=head.removeprefix("## Draft").strip("\n"),
        review=review.strip("\n"),
        score=int(score.group(1)),
        refused=_field(notes, "Refused suggestions", draft_path),
        language=_field(notes, "Language", draft_path),
    )


def _job_ad(folder: Path, application_id: str) -> tuple[str, str]:
    """The `[Position] @ [Company]` title and the `**Job ad:**` value of the Application's Job ad file."""
    path = folder / f"{application_id}_job-ad.md"
    try:
        text = path.read_text()
    except OSError:
        raise ApplicationError(f"No Job ad file for {application_id}: {path}") from None
    title = re.search(r"^# Job ad: (.+)$", text, re.MULTILINE)
    url = re.search(r"\*\*Job ad:\*\* (.+?)\s*(?:\||$)", text, re.MULTILINE)
    if not title or not url:
        raise ApplicationError(f"{path}: no '# Job ad: ...' title or '**Job ad:**' header")
    return title.group(1).strip(), url.group(1).strip()


def _research_date(folder: Path, application_id: str) -> str:
    try:
        text = (folder / f"{application_id}_company-research.md").read_text()
    except OSError:
        return "none"
    found = re.search(r"\*\*Date researched:\*\* (\d{4}-\d{2}-\d{2})", text)
    return found.group(1) if found else "none"


def assemble(
    root: Path,
    application_id: str,
    rounds: int,
    final: int,
    exit_name: str,
    reason: str,
    requested: tuple[int, ...],
    today: date,
) -> str:
    """Write both files into the Application's folder and return the final letter."""
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"No such Application folder: {folder}")
    if not 1 <= final <= rounds:
        raise RoundFileError(f"--final {final} is not one of the {rounds} Round(s)")
    if outside := [n for n in requested if not 1 <= n <= rounds]:
        raise RoundFileError(f"--requested {outside} is not one of the {rounds} Round(s)")
    title, url = _job_ad(folder, application_id)
    played = [read_round(folder / "rounds", n) for n in range(1, rounds + 1)]
    best = played[final - 1]

    lines = [
        f"# Cover letter review log: {title}",
        "",
        f"> **Date:** {today.isoformat()} | **Job ad:** {url} | **Company research:** {_research_date(folder, application_id)}"
        f" | **Final Review score:** {best.score}/100 | **Rounds:** {rounds} | **Exit:** {exit_name}",
        "",
        "After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.",
        "",
        f"**Final letter:** Round {final}'s draft." + (" It scored highest; later drafts scored lower." if final != rounds else ""),
        "",
        f"**Language:** {best.language}",
        "",
    ]
    for item in played:
        mark = " (requested by the candidate)" if item.number in requested else ""
        lines += [
            f"## Round {item.number}{mark}",
            "",
            f"**Review score:** {item.score}/100",
            "",
            "### Draft",
            "",
            item.draft,
            "",
            "### Review",
            "",
            item.review,
            "",
            "### Refused suggestions",
            "",
            item.refused,
            "",
        ]
    lines += ["## Exit reason", "", reason, ""]

    letter = best.draft.strip("\n") + "\n"
    (folder / f"{application_id}_cover-letter.md").write_text(letter)
    (folder / f"{application_id}_cover-letter-review.md").write_text("\n".join(lines))
    return letter
