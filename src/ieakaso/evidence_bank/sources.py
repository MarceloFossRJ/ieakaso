"""Stamping and checking the Sources section of `output/applications/<id>/<id>_evidence-bank.md`."""

import hashlib
import re
from pathlib import Path, PurePosixPath

from ieakaso.evidence_bank.errors import ApplicationError, NoBankError
from ieakaso.layout import APPLICATIONS, CANDIDATE, LETTERS_OUTPUT, LINKEDIN_OUTPUT, PARSED_CV

HEADING = "## Sources"
NOTE = (
    "The Personal knowledge base files this bank was built from. Written by `ieakaso.evidence_bank stamp`; do not edit."
)
_ROW = re.compile(r"\| `([^`]+)` \| `([0-9a-f]{64})` \|")

# The Personal knowledge base files the bank is built from, in this order. `writing-style.md` is not one: the
# Applicant reads the candidate's voice itself. The Personal motivation lives in the tracker and is passed as is.
_FIXED = (
    PurePosixPath("config.yml"),
    PARSED_CV,
    LINKEDIN_OUTPUT,
)
_CANDIDATE = (
    "presentation.md",
    "professional-experience-extended.md",
    "professional-self-reflection.md",
    "deliberate-differences.md",
)


def source_files(root: Path) -> list[PurePosixPath]:
    """The source files that exist in `root`; missing optional files are left out."""
    letters = sorted(LETTERS_OUTPUT / p.name for p in (root / LETTERS_OUTPUT).glob("*.md"))
    paths = [*_FIXED, *letters, *(CANDIDATE / name for name in _CANDIDATE)]
    return [p for p in paths if (root / p).is_file()]


def _hashes(root: Path) -> dict[str, str]:
    return {str(p): hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_files(root)}


def bank_path(root: Path, application_id: str) -> Path:
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"no Application {application_id}: {folder.relative_to(root)} is missing")
    path = folder / f"{application_id}_evidence-bank.md"
    if not path.is_file():
        raise NoBankError(f"no Evidence bank for {application_id}: {path.relative_to(root)} is missing")
    return path


def stamp(root: Path, application_id: str) -> int:
    """Write the Sources section at the end of the bank, replacing an old one. Returns the number of files."""
    path = bank_path(root, application_id)
    body = path.read_text().split(f"\n{HEADING}\n", 1)[0].rstrip("\n")
    hashes = _hashes(root)
    rows = "".join(f"| `{name}` | `{digest}` |\n" for name, digest in hashes.items())
    path.write_text(f"{body}\n\n{HEADING}\n\n{NOTE}\n\n| File | SHA-256 |\n|---|---|\n{rows}")
    return len(hashes)


def check(root: Path, application_id: str) -> list[str]:
    """What changed since the bank was stamped, as `Changed:`, `Added:` and `Removed:` lines; empty when current."""
    text = bank_path(root, application_id).read_text()
    if f"\n{HEADING}\n" not in text:
        raise NoBankError(f"the Evidence bank of {application_id} has no Sources section; write it again")
    stamped = dict(_ROW.findall(text.split(f"\n{HEADING}\n", 1)[1]))
    current = _hashes(root)
    return [
        *(f"Changed: {name}" for name in current if name in stamped and stamped[name] != current[name]),
        *(f"Added: {name}" for name in current if name not in stamped),
        *(f"Removed: {name}" for name in stamped if name not in current),
    ]
