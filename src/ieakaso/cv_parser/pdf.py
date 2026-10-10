"""PDF: text blocks in the order the file stores them, plus link annotations. No layout guessing, no OCR.

Stored order, not top-to-bottom sorting: on two-column CVs sorting interleaves the sidebar into
the main column mid-sentence, while stored order follows how the authoring program wrote the page.
"""

from pathlib import Path

import pymupdf

from ieakaso.cv_parser.errors import CvParseError

# PyMuPDF's defaults, minus keeping ligatures (normalize would expand them anyway).
FLAGS = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_LIGATURES


def read_pdf(source: Path) -> str:
    try:
        doc = pymupdf.open(source, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError):
        raise CvParseError(_unreadable(source)) from None
    with doc:
        if doc.needs_pass:
            raise CvParseError(
                f"{source.name} is password-protected. Save a copy without a password and try again."
            )
        try:
            pages = [_page_text(page) for page in doc]
        except (pymupdf.FileDataError, RuntimeError, ValueError):
            raise CvParseError(_unreadable(source)) from None
    if not any(p.strip() for p in pages):
        raise CvParseError(
            f"{source.name} has no text layer: it looks like a scanned image. "
            "Ieakaso does not read text from images. Export a text-based PDF from the program "
            "you wrote the CV in, or use a DOCX or TXT file instead."
        )
    return "\n\n".join(pages)


def _unreadable(source: Path) -> str:
    return f"{source.name} could not be read as a PDF; it may be damaged. Export it again and try again."


def _page_text(page: pymupdf.Page) -> str:
    links = [(link["from"], link["uri"]) for link in page.get_links() if link.get("uri")]
    blocks = []
    for block in page.get_text("rawdict", flags=FLAGS)["blocks"]:
        if block.get("type") != 0:
            continue
        lines = [_line_text(line, links) for line in block["lines"]]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _line_text(line: dict, links: list) -> str:
    """The line's characters, with runs that fall inside a link rectangle written as [text](uri)."""
    out = []
    current_uri = None
    run = []

    def flush():
        if current_uri is None:
            out.append("".join(run))
        else:
            text = "".join(run)
            stripped = text.strip()
            lead = text[: len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()):]
            out.append(f"{lead}[{stripped}]({current_uri}){trail}" if stripped else text)
        run.clear()

    for span in line["spans"]:
        for char in span["chars"]:
            uri = _uri_at(char["bbox"], links)
            if uri != current_uri:
                flush()
                current_uri = uri
            run.append(char["c"])
    flush()
    return "".join(out)


def _uri_at(bbox, links: list) -> str | None:
    x = (bbox[0] + bbox[2]) / 2
    y = (bbox[1] + bbox[3]) / 2
    for rect, uri in links:
        if rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1:
            return uri
    return None
