"""parse() turns a Source CV into the Parsed CV text. Expected outputs live in tests/fixtures/expected/."""

import re
from collections import Counter
from pathlib import Path

import docx
import pymupdf
import pytest
from lxml import etree

from ieakaso.cv_parser import CvParseError, parse

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED = FIXTURES / "expected"
SUPPORTED = {".pdf", ".docx", ".tex", ".txt", ".md"}
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
    return sorted(
        p
        for folder in ("pdf", "synthetic-resumes", "generated")
        for p in (FIXTURES / folder).iterdir()
        if p.suffix in SUPPORTED and p.name not in FAILING
    )


def expected_path(source: Path) -> Path:
    rel = source.relative_to(FIXTURES)
    return EXPECTED / rel.parent / f"{rel.name}.md"


def words(text: str) -> Counter:
    return Counter(text.split())


def strip_markup(md: str) -> str:
    """The Parsed CV's text without the markdown the parser adds."""
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)  # links
    md = re.sub(r"\[\^\d+\]:?", " ", md)  # footnote markers
    md = re.sub(r"(?m)^\| *(?:--- *\| *)+$", "", md)  # table separator rows
    md = re.sub(r"(?m)^(?:#{1,6} |- |\d+\. )", "", md)  # headings, list items
    md = re.sub(r"(?<!\\)\|", " ", md)  # table cell borders
    return md.replace("\\|", "|")


# --- expected outputs -------------------------------------------------------


def test_every_fixture_has_an_expected_output():
    assert [s.relative_to(FIXTURES) for s in sources() if not expected_path(s).is_file()] == []


@pytest.mark.parametrize("source", sources(), ids=lambda p: str(p.relative_to(FIXTURES)))
def test_output_matches_the_expected_output(source: Path):
    assert parse(source).encode("utf-8") == expected_path(source).read_bytes()


@pytest.mark.parametrize("source", sources(), ids=lambda p: str(p.relative_to(FIXTURES)))
def test_parsing_twice_gives_the_same_output(source: Path):
    assert parse(source) == parse(source)


# --- same words as the source -----------------------------------------------


def test_pdf_output_has_exactly_the_pdf_words():
    for source in sorted((FIXTURES / "pdf").glob("*.pdf")) + [FIXTURES / "generated/cv.pdf"]:
        flags = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
        with pymupdf.open(source) as doc:
            text = "".join(page.get_text("text", flags=flags) for page in doc)
        assert words(strip_markup(parse(source))) == words(text), source.name


def test_docx_output_has_exactly_the_visible_docx_characters_in_order():
    source = FIXTURES / "generated/cv.docx"
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    }
    parts = {p.partname.split("/")[-1]: p for p in docx.Document(source).part.package.iter_parts()}
    text = []
    for name in ("header1.xml", "document.xml", "footnotes.xml", "footer1.xml"):  # reading order
        element = etree.fromstring(parts[name].blob)
        # Text boxes are stored twice (modern and fallback); count only the modern copy.
        for fallback in element.xpath(".//mc:Fallback", namespaces=ns):
            fallback.getparent().remove(fallback)
        text += [t.text for t in element.xpath(".//w:t", namespaces=ns)]
    assert "".join(strip_markup(parse(source)).split()) == "".join("".join(text).split())


def test_txt_output_has_exactly_the_txt_words():
    for source in sorted((FIXTURES / "synthetic-resumes").glob("*.txt")):
        assert words(parse(source)) == words(source.read_text("utf-8-sig")), source.name


# --- cleanups (TXT shows them without any other markup) ----------------------


def parse_text(tmp_path: Path, raw: bytes) -> str:
    path = tmp_path / "cv.txt"
    path.write_bytes(raw)
    return parse(path)


def test_line_endings_become_lf(tmp_path):
    assert parse_text(tmp_path, b"a\r\nb\rc\n") == "a\nb\nc\n"


def test_ligatures_are_expanded(tmp_path):
    assert parse_text(tmp_path, "ﬁnance ﬂow ﬀ ﬃ ﬄ ﬅ ﬆ\n".encode()) == "finance flow ff ffi ffl st st\n"


def test_text_is_nfc_normalized(tmp_path):
    assert parse_text(tmp_path, "Cafe\u0301\n".encode()) == "Caf\u00e9\n"


def test_trailing_spaces_are_removed_but_leading_ones_kept(tmp_path):
    assert parse_text(tmp_path, b"  indented  \t\nnext \n") == "  indented\nnext\n"


def test_blank_lines_collapse_to_one(tmp_path):
    assert parse_text(tmp_path, b"\n\na\n\n\n\n  \nb\n\n\n") == "a\n\nb\n"


def test_output_ends_with_exactly_one_newline(tmp_path):
    assert parse_text(tmp_path, b"a") == "a\n"


def test_byte_order_mark_is_dropped(tmp_path):
    assert parse_text(tmp_path, b"\xef\xbb\xbfa\n") == "a\n"


def test_hyphenated_line_breaks_are_never_joined(tmp_path):
    assert parse_text(tmp_path, b"manage-\nment self-\nmanaged\n") == "manage-\nment self-\nmanaged\n"


def test_markdown_source_is_copied_byte_for_byte():
    source = FIXTURES / "generated/cv.md"
    assert parse(source).encode("utf-8") == source.read_bytes()


def test_suffix_is_case_insensitive(tmp_path):
    path = tmp_path / "CV.TXT"
    path.write_bytes(b"a\n")
    assert parse(path) == "a\n"


# --- failures ------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(FAILING))
def test_unparseable_source_raises_a_message_for_the_candidate(name: str):
    with pytest.raises(CvParseError) as error:
        parse(FIXTURES / "generated" / name)
    assert FAILING[name] in str(error.value)
    assert name in str(error.value)


def test_unknown_tex_command_names_its_line():
    with pytest.raises(CvParseError, match="line 4"):
        parse(FIXTURES / "generated/unknown-command.tex")


def test_tex_input_is_refused(tmp_path):
    path = tmp_path / "cv.tex"
    path.write_text("\\documentclass{article}\n\\begin{document}\n\\input{experience}\n\\end{document}\n")
    with pytest.raises(CvParseError, match=r"\\input"):
        parse(path)


def test_tex_without_a_document_body_is_refused(tmp_path):
    path = tmp_path / "cv.tex"
    path.write_text("\\documentclass{article}\n")
    with pytest.raises(CvParseError, match="document"):
        parse(path)
