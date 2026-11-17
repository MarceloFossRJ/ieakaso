"""Building `output/applications/<id>/<id>_letter-context.md` from the Application's Job analysis and Company research."""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ieakaso.layout import APPLICATIONS
from ieakaso.letter_context.errors import ApplicationError

# The Job analysis sections the agents need: what to stress and what to address. The Requirement match is left out,
# since the Evidence bank holds the evidence per requirement.
ANALYSIS_SECTIONS = ("Strengths", "Weaknesses", "Screener risks", "CV under-sells", "Gaps to close")
# The Company research sections that hold usable company facts. Never Summary, Employee reviews, Role impact, Red flags,
# Sources or the Notes.
COMPANY_SECTIONS = ("At a glance", "Domain and product", "Latest releases", "Financial moment", "Culture")

OLD = "(older than 6 months: never call it recent, new or latest)"
UNDATED = "(undated: never call it recent)"
NOTE = (
    "Built by `ieakaso.letter_context build` from the Job analysis and the Company research of {id}; do not edit. "
    "The company facts are the usable ones only: fetched, never from a search snippet, red flags or employee reviews."
)

_DATE = re.compile(r"(?<![\d-])(\d{4})-(\d{2})(?:-(\d{2}))?(?!\d)")
_NOT_FOUND = re.compile(r"^-\s+(?:[^:]*:\s*)?Not found\b")
_RESEARCHED = re.compile(r"\*\*Date researched:\*\* (\d{4}-\d{2}-\d{2})")


@dataclass
class Built:
    text: str
    warnings: list[str] = field(default_factory=list)
    no_company_facts: str | None = None  # why there are none, or None when there are


def context_path(application_id: str) -> Path:
    return Path(APPLICATIONS) / application_id / f"{application_id}_letter-context.md"


def _sections(text: str) -> dict[str, str]:
    """Each `## ` section's body, by heading."""
    found: dict[str, str] = {}
    for chunk in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        heading, _, body = chunk.partition("\n")
        found[heading.strip()] = body.strip("\n")
    return found


def _six_months_before(today: date) -> date:
    year, month = (today.year, today.month - 6) if today.month > 6 else (today.year - 1, today.month + 6)
    for day in range(today.day, 0, -1):  # clamp the 31st to the month's last day
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise AssertionError("unreachable")


def _newest_date(lines: list[str]) -> date | None:
    """The newest date the lines name; a month alone counts from its first day."""
    dates = []
    for year, month, day in _DATE.findall("\n".join(lines)):
        try:
            dates.append(date(int(year), int(month), int(day or 1)))
        except ValueError:
            continue
    return max(dates, default=None)


def _blocks(body: str) -> list[list[str]]:
    """Top-level lines with their indented continuation lines; a blank line is a block of its own."""
    blocks: list[list[str]] = []
    for line in body.splitlines():
        if line.strip() and line[0].isspace() and blocks and blocks[-1] != [""]:
            blocks[-1].append(line)
        else:
            blocks.append([line] if line.strip() else [""])
    return blocks


def _unusable(line: str) -> bool:
    return "search snippet" in line.lower() or bool(_NOT_FOUND.match(line.strip().replace("**", "")))


def _usable(body: str, cutoff: date) -> tuple[str, int]:
    """The section without snippet-only and Not found items, each fact tagged when it is old or undated. Returns the
    text and how many facts are left."""
    kept: list[str] = []
    facts = 0
    for block in _blocks(body):
        first = block[0]
        if _unusable(first):
            continue
        children = [line for line in block[1:] if not (line.lstrip().startswith("- ") and _unusable(line))]
        if len(block) > 1 and first.rstrip().endswith(":") and not any(c.lstrip().startswith("- ") for c in children):
            continue  # a heading bullet whose items were all dropped
        if first.startswith("- "):
            facts += 1
            newest = _newest_date([first, *children])
            if newest is None:
                first = f"{first} {UNDATED}"
            elif newest < cutoff:
                first = f"{first} {OLD}"
        kept.append("\n".join([first, *children]))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip("\n")
    return text, facts


def _company_part(research: Path, today: date, built: Built) -> str:
    if not research.is_file():
        built.no_company_facts = "it has no Company research"
    else:
        try:
            text = research.read_text()
        except OSError, UnicodeDecodeError:
            text = None
            built.no_company_facts = "its Company research can't be read"
        sections = _sections(text) if text is not None else {}
        if text is not None and not any(name in sections for name in COMPANY_SECTIONS):
            built.no_company_facts = "its Company research has none of the usable sections"
        elif text is not None:
            cutoff = _six_months_before(today)
            parts, facts = [], 0
            for name in COMPANY_SECTIONS:
                if name not in sections:
                    built.warnings.append(f"Warning: the Company research has no {name} section")
                    continue
                usable, count = _usable(sections[name], cutoff)
                facts += count
                if usable:
                    parts.append(f"### {name}\n\n{usable}")
            if facts:
                found = _RESEARCHED.search(text)
                header = f"> **Date researched:** {found[1]}\n\n" if found else ""
                return "## Company facts\n\n" + header + "\n\n".join(parts) + "\n"
            built.no_company_facts = "its Company research has no usable fact"
    return f"## Company facts\n\nNone: {built.no_company_facts}. Write about the company from the Job ad only.\n"


def build(root: Path, application_id: str, today: date) -> Built:
    """Write the Letter context, overwriting an old one."""
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"no Application {application_id}: {folder.relative_to(root)} is missing")
    analysis_path = folder / f"{application_id}_job-analysis.md"
    if not analysis_path.is_file():
        raise ApplicationError(f"no Job analysis for {application_id}: {analysis_path.relative_to(root)} is missing")
    analysis = analysis_path.read_text()

    built = Built("")
    title = re.search(r"^# Job analysis: (.+)$", analysis, flags=re.MULTILINE)
    sections = _sections(analysis)
    parts = [f"# Letter context: {title[1] if title else application_id}", NOTE.format(id=application_id)]
    analysis_parts = []
    for name in ANALYSIS_SECTIONS:
        if name in sections:
            analysis_parts.append(f"### {name}\n\n{sections[name]}")
        else:
            built.warnings.append(f"Warning: the Job analysis has no {name} section")
    parts.append("## From the Job analysis\n\n" + "\n\n".join(analysis_parts))
    parts.append(_company_part(folder / f"{application_id}_company-research.md", today, built))

    built.text = "\n\n".join(parts)
    (root / context_path(application_id)).write_text(built.text)
    return built
