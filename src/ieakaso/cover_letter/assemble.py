"""Builds `<id>_cover-letter.md` and `<id>_cover-letter-review.md` from `rounds/round-<n>_draft.md` and `_review.md`.

The review log's format is the one `ai/skills/ieakaso/modes/cover-letter.md` defines. Nothing is written unless every
Round file is there and readable.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ieakaso.cover_letter.errors import ApplicationError, ArgumentError, RoundFileError
from ieakaso.layout import APPLICATIONS

NOTES = "## Notes for the Assistant"
SCORE = re.compile(r"^[ \t]*(?:#+[ \t]*)?\**Review score:\**[ \t]*(\d+)/100\**[ \t]*$", re.MULTILINE)
EXITS = (
    "Review score 90 or above",
    "Plateau",
    "5 Rounds",
    "change requested by the candidate",
    "Round after the candidate's answers",
)


@dataclass(frozen=True)
class Outcome:
    """How the Run ended: what the command's arguments say."""

    rounds: int
    final: int
    requested: tuple[int, ...]
    exit_name: str
    reason: str
    motivated: bool = False  # whether the Run passed a Personal motivation to the agents

    def validate(self) -> None:
        if self.exit_name not in EXITS:
            raise ArgumentError(f"--exit must be one of: {'; '.join(EXITS)}")
        if not 1 <= self.final <= self.rounds:
            raise ArgumentError(f"--final {self.final} is not one of the {self.rounds} Round(s)")
        if outside := [n for n in self.requested if not 1 <= n <= self.rounds]:
            raise ArgumentError(f"--requested {outside} is not one of the {self.rounds} Round(s)")


@dataclass(frozen=True)
class Round:
    number: int
    draft: str
    review: str
    score: int
    refused: str
    language: str | None  # read from the notes; only the final Round's is needed
    path: Path


def _read(path: Path, error: type[Exception], what: str) -> str:
    try:
        return path.read_text()
    except OSError:
        raise error(f"{what} missing or unreadable: {path}") from None


def _field(notes: str, label: str) -> str | None:
    """The value of a `- **<label>:**` bullet of the Applicant's notes, with its continuation lines."""
    match = re.search(rf"^- \*\*{re.escape(label)}:\*\*(.*?)(?=^- \*\*|\Z)", notes, re.MULTILINE | re.DOTALL)
    if not match or not match.group(1).strip():
        return None
    return "\n".join(line.strip() if i == 0 else line for i, line in enumerate(match.group(1).strip().splitlines()))


def read_round(rounds: Path, number: int) -> Round:
    draft_path, review_path = rounds / f"round-{number}_draft.md", rounds / f"round-{number}_review.md"
    text, review = _read(draft_path, RoundFileError, "Round file"), _read(review_path, RoundFileError, "Round file")
    head, found, notes = text.partition(NOTES)
    if not found or not head.startswith("## Draft"):
        raise RoundFileError(f"{draft_path}: not a draft ('## Draft' then '{NOTES}')")
    score = SCORE.search(review)
    if not score:
        raise RoundFileError(f"{review_path}: no '## Review score: <n>/100' line")
    refused = _field(notes, "Refused suggestions")
    if refused is None:
        raise RoundFileError(f"{draft_path}: no 'Refused suggestions' in the notes for the Assistant")
    return Round(
        number=number,
        draft=head.removeprefix("## Draft").strip("\n"),
        review=review.strip("\n"),
        score=int(score.group(1)),
        refused=refused,
        language=_field(notes, "Language"),
        path=draft_path,
    )


def _job_ad(folder: Path, application_id: str) -> tuple[str, str]:
    """The `[Position] @ [Company]` title and the `**Job ad:**` value of the Application's Job ad file."""
    path = folder / f"{application_id}_job-ad.md"
    text = _read(path, ApplicationError, "Job ad file")
    title = re.search(r"^# Job ad: (.+)$", text, re.MULTILINE)
    url = re.search(r"\*\*Job ad:\*\* (.+?)\s*(?:\||$)", text, re.MULTILINE)
    if not title or not url:
        raise ApplicationError(f"{path}: no '# Job ad: ...' title or '**Job ad:**' header")
    return title.group(1).strip(), url.group(1).strip()


def _research_date(folder: Path, application_id: str) -> str:
    path = folder / f"{application_id}_company-research.md"
    if not path.is_file():
        return "none"
    text = _read(path, ApplicationError, "Company research file")
    found = re.search(r"\*\*Date researched:\*\* (\d{4}-\d{2}-\d{2})", text)
    return found.group(1) if found else "none"


def review_log(
    title: str, url: str, research_date: str, today: date, outcome: Outcome, played: list[Round]
) -> str:
    """The review log, in the format `ai/skills/ieakaso/modes/cover-letter.md` defines. `played` is Rounds 1 to n."""
    best = played[outcome.final - 1]
    lines = [
        f"# Cover letter review log: {title}",
        "",
        (
            f"> **Date:** {today.isoformat()} | **Job ad:** {url} | **Company research:** {research_date}"
            f" | **Personal motivation:** {'used' if outcome.motivated else 'none'}"
            f" | **Final Review score:** {best.score}/100 | **Rounds:** {outcome.rounds} | **Exit:** {outcome.exit_name}"
        ),
        "",
        "After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.",
        "",
        f"**Final letter:** Round {outcome.final}'s draft."
        + (" It scored highest; later drafts scored lower." if outcome.final != outcome.rounds else ""),
        "",
        f"**Language:** {best.language}",
        "",
    ]
    for item in played:
        mark = " (requested by the candidate)" if item.number in outcome.requested else ""
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
    lines += ["## Exit reason", "", outcome.reason, ""]
    return "\n".join(lines)


def assemble(root: Path, application_id: str, outcome: Outcome, today: date) -> str:
    """Write both files into the Application's folder and return the final letter."""
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"No such Application folder: {folder}")
    outcome.validate()
    title, url = _job_ad(folder, application_id)
    played = [read_round(folder / "rounds", n) for n in range(1, outcome.rounds + 1)]
    best = played[outcome.final - 1]
    if best.language is None:
        raise RoundFileError(f"{best.path}: no 'Language' in the notes for the Assistant")

    log = review_log(title, url, _research_date(folder, application_id), today, outcome, played)
    letter = best.draft + "\n"
    (folder / f"{application_id}_cover-letter.md").write_text(letter)
    (folder / f"{application_id}_cover-letter-review.md").write_text(log)
    return letter
