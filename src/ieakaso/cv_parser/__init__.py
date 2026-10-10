"""Turns the Source CV into the Parsed CV (`input/cv.md`), deterministically.

Same words in the same order; only structure the file declares (headings, lists, links,
tables, footnotes) is added. The one exception to the order: footnote text follows the
paragraph or table that references it, or the whole list. See docs/adr/0001-deterministic-cv-parser.md.
"""

from pathlib import Path

from ieakaso.cv_parser.errors import CvParseError
from ieakaso.cv_parser.normalize import normalize

# Raise whenever the output for the same Source CV changes; the setup check then parses again.
PARSER_VERSION = 4

ACCEPTED = (".pdf", ".docx", ".tex", ".txt", ".md")

__all__ = ["ACCEPTED", "PARSER_VERSION", "CvParseError", "parse"]


def parse(source: Path) -> str:
    """The Parsed CV text for source. Raises CvParseError with a message for the candidate."""
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix not in ACCEPTED:
        raise CvParseError(
            f"{source.name} is not a format Ieakaso can read. "
            f"Save your CV as one of {', '.join(ACCEPTED)}."
        )
    if suffix == ".md":
        return _decode(source)
    if suffix == ".txt":
        text = _decode(source)
    elif suffix == ".pdf":
        from ieakaso.cv_parser.pdf import read_pdf

        text = read_pdf(source)
    elif suffix == ".docx":
        from ieakaso.cv_parser.docx import read_docx

        text = read_docx(source)
    else:
        from ieakaso.cv_parser.tex import read_tex

        text = read_tex(source)
    text = normalize(text)
    if not text.strip():
        raise CvParseError(f"{source.name} is empty. Add your CV's text to it, or use another file.")
    return text


def _decode(source: Path) -> str:
    raw = source.read_bytes()
    if not raw.strip():
        raise CvParseError(f"{source.name} is empty. Add your CV's text to it, or use another file.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise CvParseError(
            f"{source.name} is not saved as UTF-8 text. Save it again with UTF-8 encoding "
            "(most editors offer it under \"Save as\" or \"Encoding\")."
        ) from None
    if source.suffix.lower() == ".txt":
        text = text.removeprefix("﻿")
    return text
