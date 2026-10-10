"""parse() turns a Source CV into the Parsed CV text. Expected outputs live in tests/fixtures/expected/."""

import json
import re
from collections import Counter
from pathlib import Path

import docx
import pymupdf
import pytest
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from fixtures.catalog import FAILING, FIXTURES, MANIFEST, expected_outputs, expected_path, sources
from fixtures.generate import TEX_VISIBLE
from lxml import etree

from ieakaso.cv_parser import PARSER_VERSION, CvParseError, parse

DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}

def words(text: str) -> Counter:
    return Counter(text.split())


def strip_markup(md: str) -> str:
    """The Parsed CV's text without the markdown the parser adds."""
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)  # links
    md = re.sub(r"\[\^\d+\]:?", " ", md)  # footnote markers
    md = re.sub(r"(?m)^\| *(?:--- *\| *)+$", "", md)  # table separator rows
    md = re.sub(r"(?m)^(?:#{1,6} |- |\d+\. )", "", md)  # headings, list items
    md = re.sub(r"(?m)^\|.*\|$", lambda row: re.sub(r"(?<!\\)\|", " ", row.group()), md)  # table borders
    return md.replace("\\|", "|")


def letters(text: str) -> str:
    """The text without any whitespace: compares content and order, not layout."""
    return "".join(text.split())


def visible_docx_text(element) -> str:
    # Text boxes are stored twice (modern and fallback); count only the modern copy.
    # Text a tracked move took away (w:moveFrom) is no longer in the document.
    for gone in element.xpath(".//mc:Fallback | .//w:moveFrom", namespaces=DOCX_NS):
        gone.getparent().remove(gone)
    text = []
    for node in element.xpath(".//w:t | .//w:sym", namespaces=DOCX_NS):
        sym = node.get(f"{{{DOCX_NS['w']}}}char")
        text.append(chr(int(sym, 16)) if sym else node.text)
    return "".join(text)


# --- expected outputs -------------------------------------------------------


def test_every_fixture_has_an_expected_output():
    assert [s.relative_to(FIXTURES) for s in sources() if not expected_path(s).is_file()] == []


def test_expected_outputs_belong_to_the_current_parser_version():
    # update_expected.py refuses to change an output without a PARSER_VERSION raise.
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["parser_version"] == PARSER_VERSION
    assert manifest["outputs"] == expected_outputs()


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


@pytest.mark.parametrize("source", [s for s in sources() if s.suffix == ".docx"], ids=lambda p: p.name)
def test_docx_output_has_exactly_the_visible_docx_characters_in_order(source: Path):
    document = docx.Document(source).part
    by_type = {}
    for rel in document.rels.values():
        if not rel.is_external:
            by_type.setdefault(rel.reltype, []).append(rel.target_part)
    # Reading order: page headers, body, page footers. Footnote text follows the block that
    # references it, numbered by first reference, so it is checked note by note.
    parts = [*by_type.get(RT.HEADER, []), document, *by_type.get(RT.FOOTER, [])]
    notes = {
        note.get(f"{{{DOCX_NS['w']}}}id"): letters(visible_docx_text(note))
        for part in by_type.get(RT.FOOTNOTES, [])
        for note in etree.fromstring(part.blob).xpath("w:footnote[not(@w:type)]", namespaces=DOCX_NS)
    }
    body_xml = etree.fromstring(document.blob)
    for gone in body_xml.xpath(".//mc:Fallback | .//w:moveFrom", namespaces=DOCX_NS):
        gone.getparent().remove(gone)
    referenced = body_xml.xpath(".//w:footnoteReference/@w:id", namespaces=DOCX_NS)
    in_reference_order = [notes[i] for i in dict.fromkeys(referenced)]

    output = parse(source)
    definitions = re.findall(r"(?m)^\[\^\d+\]: (.*)$", output)
    body = re.sub(r"(?m)^\[\^\d+\]: .*$", "", output)
    assert letters(strip_markup(body)) == letters("".join(visible_docx_text(etree.fromstring(p.blob)) for p in parts))
    assert [letters(d) for d in definitions] == in_reference_order


def test_tex_output_has_exactly_the_visible_tex_characters_in_order():
    assert letters(strip_markup(parse(FIXTURES / "generated/cv.tex"))) == letters(TEX_VISIBLE)


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


@pytest.mark.parametrize("raw, message", [(b"", "empty"), ("# Jordan Exámple\n".encode("latin-1"), "UTF-8")])
def test_markdown_source_must_be_utf8_and_not_empty(tmp_path, raw: bytes, message: str):
    path = tmp_path / "cv.md"
    path.write_bytes(raw)
    with pytest.raises(CvParseError, match=message):
        parse(path)


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


def test_tex_footnote_follows_its_own_paragraph(tmp_path):
    path = tmp_path / "cv.tex"
    path.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "First.\\footnote{Note one.}\n\nSecond.\n\\end{document}\n"
    )
    assert parse(path) == "First.[^1]\n\n[^1]: Note one.\n\nSecond.\n"


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
