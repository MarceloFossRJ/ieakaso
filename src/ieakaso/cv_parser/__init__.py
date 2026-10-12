"""Turns the Source CV into the Parsed CV (`input/cv.md`), deterministically.

Same words in the same order; only structure the file declares (headings, lists, links,
tables, footnotes) is added. The one exception to the order: footnote text follows the
paragraph or table that references it, or the whole list. See docs/adr/0001-deterministic-cv-parser.md.
"""

from pathlib import Path

from ieakaso.cv_parser.docx import read_docx
from ieakaso.cv_parser.errors import CvParseError
from ieakaso.cv_parser.normalize import normalize
from ieakaso.cv_parser.pdf import read_pdf
from ieakaso.cv_parser.tex import read_tex

# Raise whenever the output for the same Source CV changes; the setup check then parses again.
PARSER_VERSION = 4


def _read_utf8(source: Path) -> str:
    raw = source.read_bytes()
    if not raw.strip():
        raise _empty(source)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise CvParseError(
            f"{source.name} is not saved as UTF-8 text. Save it again with UTF-8 encoding "
            "(most editors offer it under \"Save as\" or \"Encoding\")."
        ) from None


def _read_txt(source: Path) -> str:
    return _read_utf8(source).removeprefix("\ufeff")


READERS = {".pdf": read_pdf, ".docx": read_docx, ".tex": read_tex, ".txt": _read_txt, ".md": _read_utf8}
ACCEPTED = tuple(READERS)
COPIED_AS_IS = ".md"  # already Markdown: no cleanups, byte for byte

__all__ = ["ACCEPTED", "PARSER_VERSION", "CvParseError", "parse"]


def parse(source: Path) -> str:
    """The Parsed CV text for source. Raises CvParseError with a message for the candidate."""
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix not in READERS:
        raise CvParseError(
            f"{source.name} is not a format Ieakaso can read. "
            f"Save your CV as one of {', '.join(ACCEPTED)}."
        )
    text = READERS[suffix](source)
    if suffix == COPIED_AS_IS:
        return text
    text = normalize(text)
    if not text.strip():
        raise _empty(source)
    return text


def _empty(source: Path) -> CvParseError:
    return CvParseError(f"{source.name} is empty. Add your CV's text to it, or use another file.")
