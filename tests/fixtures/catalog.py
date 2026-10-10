"""Where the fixtures and their expected outputs live; shared by the tests and update_expected.py."""

import hashlib
from pathlib import Path

from ieakaso.cv_parser import ACCEPTED

FIXTURES = Path(__file__).parent
EXPECTED = FIXTURES / "expected"
MANIFEST = EXPECTED / "manifest.json"
# Generated fixtures that must fail to parse, with a phrase the candidate's message must contain.
FAILING = {
    "scanned.pdf": "text-based",
    "corrupt.pdf": "could not be read",
    "corrupt.docx": "could not be read",
    "unknown-command.tex": r"\cventry",
    "latin1.txt": "UTF-8",
    "empty.txt": "empty",
    "cv.rtf": ".pdf, .docx, .tex, .txt",
}


def sources() -> list[Path]:
    """Every fixture that parses, so has an expected output."""
    return sorted(
        p
        for folder in ("pdf", "synthetic-resumes", "generated")
        for p in (FIXTURES / folder).iterdir()
        if p.suffix in ACCEPTED and p.name not in FAILING
    )


def expected_path(source: Path) -> Path:
    rel = source.relative_to(FIXTURES)
    return EXPECTED / rel.parent / f"{rel.name}.md"


def expected_outputs() -> dict[str, str]:
    """Every expected output, by path relative to EXPECTED, with its sha256."""
    return {
        p.relative_to(EXPECTED).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(EXPECTED.rglob("*.md"))
    }
