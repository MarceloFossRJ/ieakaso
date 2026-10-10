"""Builds the synthetic Source CVs in tests/fixtures/generated/.

The generated files are committed, so tests never depend on running this. Run it again
only to change a fixture, then review the expected outputs in tests/fixtures/expected/:
    uv run python tests/fixtures/generate.py
Every person, address and company here is made up.
"""

from pathlib import Path

import docx
import pymupdf
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart
from docx.oxml import parse_xml

OUT = Path(__file__).parent / "generated"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = (
    f'xmlns:w="{W}" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:v="urn:schemas-microsoft-com:vml"'
)


def build_docx(path: Path) -> None:
    doc = docx.Document()
    section = doc.sections[0]
    section.header.paragraphs[0].text = "Jordan Example – CV"
    section.footer.paragraphs[0].text = "jordan@example.com"

    doc.add_paragraph("Jordan Example", style="Title")
    intro = doc.add_paragraph("Senior engineer. Portfolio at ")
    _add_hyperlink(intro, "https://jordan.example.dev", "jordan.example.dev")
    intro.add_run(" and code on ")
    _add_hyperlink(intro, "https://github.com/jordan-example", "GitHub")
    intro.add_run(".")

    blog = doc.add_paragraph("See ")
    blog._p.append(parse_xml(
        f'<w:r {NS}><w:fldChar w:fldCharType="begin"/></w:r>'
    ))
    blog._p.append(parse_xml(
        f'<w:r {NS}><w:instrText xml:space="preserve"> HYPERLINK "https://blog.example.dev" </w:instrText></w:r>'
    ))
    blog._p.append(parse_xml(f'<w:r {NS}><w:fldChar w:fldCharType="separate"/></w:r>'))
    blog._p.append(parse_xml(f'<w:r {NS}><w:t>my blog</w:t></w:r>'))
    blog._p.append(parse_xml(f'<w:r {NS}><w:fldChar w:fldCharType="end"/></w:r>'))
    blog.add_run(".")

    doc.add_paragraph("Experience", style="Heading 1")
    doc.add_paragraph("Senior Engineer, Acme Corp", style="Heading 2")
    dates = doc.add_paragraph()
    run = dates.add_run("Acme Corp")
    run.bold = True
    dates.add_run("\t2019–2023")
    doc.add_paragraph("Led a team of five engineers.", style="List Bullet")
    impact = doc.add_paragraph("Cut deployment time by 40%.", style="List Bullet")
    impact._p.append(parse_xml(_footnote_run(1)))
    doc.add_paragraph("First numbered point.", style="List Number")
    doc.add_paragraph("Second numbered point.", style="List Number")

    edited = doc.add_paragraph("Worked with ")
    edited._p.append(parse_xml(
        f'<w:del {NS} w:id="90" w:author="x" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:delText>removed words </w:delText></w:r></w:del>'
    ))
    edited._p.append(parse_xml(
        f'<w:ins {NS} w:id="91" w:author="x" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t>inserted words</w:t></w:r></w:ins>'
    ))
    edited.add_run(" daily.")

    table = doc.add_table(rows=3, cols=3)
    for cell, text in zip(table.rows[0].cells, ["Skill", "Level", "Years"]):
        cell.text = text
    for cell, text in zip(table.rows[1].cells, ["Python", "Expert | daily", "8"]):
        cell.text = text
    merged = table.cell(2, 0).merge(table.cell(2, 1))
    merged.text = "Spanning cell"
    table.cell(2, 2).text = "3"
    table.cell(1, 2).paragraphs[0]._p.append(parse_xml(_footnote_run(3)))

    box = doc.add_paragraph("Address block")
    box._p.append(parse_xml(_textbox_run("<w:p><w:r><w:t>Contact: jordan@example.com</w:t></w:r></w:p>")))

    moved = doc.add_paragraph("Moved: ")
    moved._p.append(parse_xml(
        f'<w:moveFrom {NS} w:id="92" w:author="x" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t xml:space="preserve">OldPlace </w:t></w:r></w:moveFrom>'
    ))
    moved._p.append(parse_xml(
        f'<w:moveTo {NS} w:id="93" w:author="x" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t>MovedWord</w:t></w:r></w:moveTo>'
    ))
    moved.add_run(" end.")

    rating = doc.add_paragraph("Rating: ")
    rating._p.append(parse_xml(f'<w:r {NS}><w:sym w:font="Wingdings" w:char="F0B7"/></w:r>'))
    rating.add_run(" 5")

    nested = doc.add_paragraph("Nested boxes")
    inner = _textbox_run("<w:p><w:r><w:t>Inner box</w:t></w:r></w:p>").replace(f" {NS}", "", 1)
    nested._p.append(parse_xml(_textbox_run(f"<w:p><w:r><w:t>Outer box</w:t></w:r>{inner}</w:p>")))

    doc.add_paragraph("Languages", style="Heading 1")
    languages = doc.add_paragraph("English (native), German (C1)")
    languages._p.append(parse_xml(_footnote_run(2)))

    _add_footnotes(doc, {1: "Measured over 2023.", 2: "Certified in 2024.", 3: "Since 2016."})
    doc.core_properties.author = "Jordan Example"
    doc.save(path)


def _add_hyperlink(paragraph, url: str, text: str) -> None:
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    paragraph._p.append(parse_xml(
        f'<w:hyperlink {NS} r:id="{r_id}"><w:r><w:t>{text}</w:t></w:r></w:hyperlink>'
    ))


def _textbox_run(paragraphs: str) -> str:
    content = f"<w:txbxContent>{paragraphs}</w:txbxContent>"
    return (
        f"<w:r {NS}><mc:AlternateContent>"
        "<mc:Choice Requires=\"wps\"><w:drawing><wp:anchor><a:graphic><a:graphicData>"
        f"<wps:wsp><wps:txbx>{content}</wps:txbx></wps:wsp>"
        "</a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice>"
        f"<mc:Fallback><w:pict><v:shape><v:textbox>{content}</v:textbox></v:shape></w:pict></mc:Fallback>"
        "</mc:AlternateContent></w:r>"
    )


def _footnote_run(note_id: int) -> str:
    return (
        f'<w:r {NS}><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
        f'<w:footnoteReference w:id="{note_id}"/></w:r>'
    )


def _add_footnotes(doc, notes: dict[int, str]) -> None:
    body = "".join(
        f'<w:footnote w:id="{i}"><w:p><w:r><w:footnoteRef/></w:r>'
        f'<w:r><w:t xml:space="preserve"> {text}</w:t></w:r></w:p></w:footnote>'
        for i, text in notes.items()
    )
    xml = (
        f'<w:footnotes {NS}>'
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
        f"{body}</w:footnotes>"
    )
    part = XmlPart(PackURI("/word/footnotes.xml"), CT.WML_FOOTNOTES, parse_xml(xml), doc.part.package)
    doc.part.relate_to(part, RT.FOOTNOTES)


def build_pdf(path: Path) -> None:
    doc = pymupdf.open()
    for number in (1, 2):
        page = doc.new_page()
        page.insert_text((72, 40), f"Jordan Example - Page {number} of 2", fontsize=8)
        if number == 1:
            page.insert_text((72, 90), "Jordan Example", fontsize=20)
            page.insert_text((72, 120), "Portfolio: jordan.example.dev", fontsize=11)
            rect = page.search_for("jordan.example.dev")[0]
            page.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": "https://jordan.example.dev"})
            page.insert_text((72, 140), "Mail: jordan@example.com", fontsize=11)
            rect = page.search_for("jordan@example.com")[0]
            page.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": "mailto:jordan@example.com"})
            page.insert_text((72, 180), "Experience", fontsize=14)
            page.insert_text((72, 200), "Senior Engineer, Acme Corp, 2019-2023", fontsize=11)
        else:
            page.insert_text((72, 90), "Education", fontsize=14)
            page.insert_text((72, 110), "BSc Computer Science, Example University", fontsize=11)
    doc.set_metadata({"producer": "ieakaso fixtures", "creationDate": "", "modDate": ""})
    doc.save(path, garbage=4, deflate=True, no_new_id=True)


def build_two_column_pdf(path: Path) -> None:
    """A sidebar line sits between two main-column lines: stored order keeps the columns apart."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Main column first line", fontsize=11)
    page.insert_text((72, 140), "Main column second line", fontsize=11)
    page.insert_text((380, 120), "Sidebar line", fontsize=11)
    doc.set_metadata({"producer": "ieakaso fixtures", "creationDate": "", "modDate": ""})
    doc.save(path, garbage=4, deflate=True, no_new_id=True)


def build_scanned_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(200)
    page.insert_image(pymupdf.Rect(72, 72, 272, 272), pixmap=pix)
    doc.set_metadata({"producer": "ieakaso fixtures", "creationDate": "", "modDate": ""})
    doc.save(path, garbage=4, deflate=True, no_new_id=True)


TEX = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{hyperref}
\newcommand{\unused}{never shown}

\begin{document}

\begin{center}
{\LARGE \textbf{Jordan Example}}\\
Berlin, Germany \textbar{} \href{mailto:jordan@example.com}{jordan@example.com} \textbar{} \url{https://jordan.example.dev}
\end{center}

% A comment the reader never sees.
\section*{Summary}
Senior engineer with ten years of experience in R\&D teams, cutting costs by 30\%.
Caf\'e owner on weekends -- and na\"ive about nothing.

\section{Experience}
\subsection{Senior Engineer, Acme Corp \hfill 2019--2023}
\begin{itemize}
  \item Led a team of \emph{five} engineers.\footnote{Across two countries.}
  \item Cut deployment time by 40\%~in two quarters.
\end{itemize}

\subsection*{Engineer, Example GmbH}
\begin{enumerate}
  \item First numbered point.
  \item[--] Labelled point.
\end{enumerate}

\section{Skills}
\begin{tabular}{l|l}
\hline
Skill & Level \\
\hline
Python & Expert\footnote{Daily use since 2016.} \\
Go & Intermediate \\
\hline
\end{tabular}

\vspace{1em}
\noindent Languages: English, German.\footnote{Both used at work.}
\end{document}
"""

# The text a reader sees in the compiled cv.tex, in order, typed by hand. Numbers and bullets
# TeX generates (section numbers, list bullets) are not in the source, so they are not here.
# Footnote text sits after the paragraph, list or table that references it, as in the Parsed CV.
TEX_VISIBLE = """
Jordan Example
Berlin, Germany | jordan@example.com | https://jordan.example.dev
Summary
Senior engineer with ten years of experience in R&D teams, cutting costs by 30%.
Café owner on weekends – and naïve about nothing.
Experience
Senior Engineer, Acme Corp 2019–2023
Led a team of five engineers.
Cut deployment time by 40% in two quarters.
Across two countries.
Engineer, Example GmbH
First numbered point.
– Labelled point.
Skills
Skill Level
Python Expert
Go Intermediate
Daily use since 2016.
Languages: English, German.
Both used at work.
"""

TEX_UNKNOWN = r"""\documentclass{article}
\begin{document}
\section{Experience}
\cventry{2019}{Engineer}{Acme}{}{}{}
\end{document}
"""

MD = "# Jordan Example\r\n\r\nAlready **markdown**, copied as it is.  \r\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    build_docx(OUT / "cv.docx")
    build_pdf(OUT / "cv.pdf")
    build_two_column_pdf(OUT / "two-column.pdf")
    build_scanned_pdf(OUT / "scanned.pdf")
    (OUT / "cv.tex").write_text(TEX, encoding="utf-8")
    (OUT / "unknown-command.tex").write_text(TEX_UNKNOWN, encoding="utf-8")
    (OUT / "cv.md").write_bytes(MD.encode("utf-8"))
    (OUT / "latin1.txt").write_bytes("Jordan Exámple\n".encode("latin-1"))
    (OUT / "empty.txt").write_bytes(b"")
    (OUT / "corrupt.pdf").write_bytes(b"%PDF-1.7\nthis is not a pdf\n")
    (OUT / "corrupt.docx").write_bytes(b"not a zip file")
    (OUT / "cv.rtf").write_bytes(b"{\\rtf1 Jordan}")


if __name__ == "__main__":
    main()
