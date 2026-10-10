"""DOCX: walks the document XML in order. Structure comes only from what the file declares:
heading and list styles, hyperlinks, tables and footnotes. Bold and italic are dropped.

Order: page headers, body, page footers. Text boxes follow the paragraph that holds them;
footnote text follows the paragraph or table that references it, or the whole list.
"""

import re
import zipfile
from pathlib import Path

import docx
from docx.oxml import parse_xml
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.exceptions import PackageNotFoundError

from ieakaso.cv_parser.errors import CvParseError

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
HEADING = re.compile(r"heading (\d)")
FIELD_LINK = re.compile(r'^\s*HYPERLINK\s+"([^"]+)"')


def read_docx(source: Path) -> str:
    try:
        document = docx.Document(source)
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError):
        raise CvParseError(
            f"{source.name} could not be read as a Word document; it may be damaged. "
            "Save it again as .docx and try again."
        ) from None
    return _Reader(document).read()


class _Reader:
    def __init__(self, document):
        self.document = document
        self.part = document.part
        self.styles = {s.style_id: s for s in document.styles}
        self.footnote_ids: list[str] = []  # in order of first reference; [^n] is index + 1
        self.footnote_part = next(
            (rel.target_part for rel in self.part.rels.values() if rel.reltype == RT.FOOTNOTES),
            None,
        )

    def read(self) -> str:
        body = self.part.element.body
        headers, footers = self._page_parts(body)
        sections = [self._blocks(part.element, part) for part in headers]
        sections.append(self._blocks(body, self.part))
        sections += [self._blocks(part.element, part) for part in footers]
        return "\n\n".join(s for s in sections if s)

    # --- parts -----------------------------------------------------------

    def _page_parts(self, body):
        headers, footers, seen = [], [], set()
        for sect in body.iter(f"{W}sectPr"):
            for ref in sect:
                kind = {f"{W}headerReference": headers, f"{W}footerReference": footers}.get(ref.tag)
                if kind is None:
                    continue
                part = self.part.related_parts[ref.get(f"{R}id")]
                if id(part) not in seen:
                    seen.add(id(part))
                    kind.append(part)
        return headers, footers

    def _footnotes(self, start: int) -> str:
        """Definitions for the footnotes referenced since footnote_ids[start]."""
        if start >= len(self.footnote_ids) or self.footnote_part is None:
            return ""
        part = self.footnote_part
        # python-docx has no footnotes part type; it loads footnotes.xml as a plain part.
        element = getattr(part, "element", None)
        if element is None:
            element = parse_xml(part.blob)
        notes = {n.get(f"{W}id"): n for n in element.iter(f"{W}footnote")}
        lines = []
        for number, note_id in enumerate(self.footnote_ids[start:], start=start + 1):
            note = notes.get(note_id)
            if note is not None:
                text = " ".join(self._paragraph_text(p, part) for p in note.iter(f"{W}p"))
                lines.append(f"[^{number}]: {text.strip()}")
        return "\n".join(lines)

    # --- blocks ----------------------------------------------------------

    def _blocks(self, container, part) -> str:
        """Paragraphs and tables, separated by blank lines; items of one list stay together.
        Footnote text follows the paragraph or table that references it, or the whole list."""
        out = []
        last_list = None
        noted = len(self.footnote_ids)

        def add_notes():
            nonlocal noted
            notes = self._footnotes(noted)
            noted = len(self.footnote_ids)
            if notes:
                out.append("\n\n" + notes)

        for kind, text, list_id in self._block_items(container, part):
            if not text.strip():
                continue
            if last_list is not None and list_id != last_list:
                add_notes()
            if out:
                out.append("\n" if list_id is not None and list_id == last_list else "\n\n")
            out.append(text)
            last_list = list_id
            if list_id is None:
                add_notes()
        add_notes()
        return "".join(out).lstrip("\n")

    def _block_items(self, container, part):
        for child in container:
            if child.tag == f"{W}p":
                yield from self._paragraph(child, part)
            elif child.tag == f"{W}tbl":
                yield "table", self._table(child, part), None
            elif child.tag == f"{W}sdt":
                content = child.find(f"{W}sdtContent")
                if content is not None:
                    yield from self._block_items(content, part)

    def _paragraph(self, p, part):
        text = self._paragraph_text(p, part)
        level = self._heading_level(p)
        numbering = self._numbering(p)
        if level:
            yield "heading", f"{'#' * level} {' '.join(text.split())}", None
        elif numbering:
            num_id, ilvl, marker = numbering
            yield "list", f"{'  ' * ilvl}{marker} {text.strip()}", num_id
        else:
            yield "paragraph", text, None
        for box in self._text_boxes(p):
            yield from self._block_items(box, part)

    def _text_boxes(self, p):
        """The paragraph's own text boxes. Boxes nested in them are read with their box."""
        return [box for box in p.iter(f"{W}txbxContent") if _owned_box(box, p)]

    # --- inline ----------------------------------------------------------

    def _paragraph_text(self, p, part) -> str:
        out = []
        field = None  # the open complex field: its instruction and the runs it displays
        for node in self._runs(p, part):
            tag = None if isinstance(node, str) else node.tag
            if tag == f"{W}fldChar":
                kind = node.get(f"{W}fldCharType")
                if kind == "begin":
                    field = {"instr": "", "text": [], "result": False}
                elif kind == "separate" and field is not None:
                    field["result"] = True
                elif kind == "end" and field is not None:
                    out.append(_field_text(field))
                    field = None
                continue
            if tag == f"{W}instrText":
                if field is not None:
                    field["instr"] += node.text or ""
                continue
            text = node if isinstance(node, str) else self._run_child_text(node)
            if field is not None:
                if field["result"]:
                    field["text"].append(text)
            else:
                out.append(text)
        if field is not None:
            out.append(_field_text(field))
        return "".join(out)

    def _runs(self, element, part):
        """Run children in order; hyperlinks are yielded as finished '[text](uri)' strings."""
        for child in element:
            tag = child.tag
            if tag == f"{W}r":
                yield from child
            elif tag == f"{W}hyperlink":
                uri = None
                r_id = child.get(f"{R}id")
                if r_id and r_id in part.rels and part.rels[r_id].is_external:
                    uri = part.rels[r_id].target_ref
                text = "".join(
                    n if isinstance(n, str) else self._run_child_text(n) for n in self._runs(child, part)
                )
                yield f"[{text}]({uri})" if uri and text.strip() else text
            elif tag in (f"{W}ins", f"{W}moveTo", f"{W}smartTag", f"{W}customXml", f"{W}fldSimple", f"{W}dir", f"{W}bdo"):
                yield from self._runs(child, part)
            elif tag == f"{W}sdt":
                content = child.find(f"{W}sdtContent")
                if content is not None:
                    yield from self._runs(content, part)

    def _run_child_text(self, node) -> str:
        tag = node.tag
        if tag == f"{W}t":
            return node.text or ""
        if tag in (f"{W}tab", f"{W}ptab"):
            return "\t"
        if tag in (f"{W}br", f"{W}cr"):
            return "\n"
        if tag == f"{W}noBreakHyphen":
            return "-"
        if tag == f"{W}sym":
            return chr(int(node.get(f"{W}char"), 16))
        if tag == f"{W}footnoteReference":
            self.footnote_ids.append(node.get(f"{W}id"))
            return f"[^{len(self.footnote_ids)}]"
        return ""

    # --- tables ----------------------------------------------------------

    def _table(self, tbl, part) -> str:
        rows = []
        for tr in tbl.iter(f"{W}tr"):
            if _parent_table(tr) is not tbl:
                continue
            cells = []
            for tc in tr.findall(f"{W}tc"):
                text = " ".join(self._cell_text(tc, part).split()).replace("|", "\\|")
                cells.append(text)
                span = tc.find(f"{W}tcPr/{W}gridSpan")
                cells += [""] * (int(span.get(f"{W}val")) - 1 if span is not None else 0)
            rows.append(cells)
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines = [_table_row(rows[0]), _table_row(["---"] * width)]
        lines += [_table_row(r) for r in rows[1:]]
        return "\n".join(lines)

    def _cell_text(self, tc, part) -> str:
        texts = []
        for child in tc:
            if child.tag == f"{W}p":
                texts.append(self._paragraph_text(child, part))
                texts += [self._blocks(box, part) for box in self._text_boxes(child)]
            elif child.tag == f"{W}tbl":
                texts.append(" ".join(self._cell_text(inner, part) for inner in child.iter(f"{W}tc")))
        return " ".join(texts)

    # --- styles ----------------------------------------------------------

    def _style(self, p):
        style_id = p.find(f"{W}pPr/{W}pStyle")
        style_id = style_id.get(f"{W}val") if style_id is not None else None
        return self.styles.get(style_id) if style_id else self.document.styles.default(1)

    def _style_chain(self, p):
        style = self._style(p)
        seen = set()
        while style is not None and style.style_id not in seen:
            seen.add(style.style_id)
            yield style
            style = style.base_style

    def _heading_level(self, p) -> int:
        for style in self._style_chain(p):
            name = (style.name or "").lower()
            if name == "title":
                return 1
            match = HEADING.fullmatch(name)
            if match:
                return min(int(match.group(1)), 6)
        return 0

    def _numbering(self, p):
        num_pr = p.find(f"{W}pPr/{W}numPr")
        if num_pr is None:
            for style in self._style_chain(p):
                num_pr = style.element.find(f"{W}pPr/{W}numPr")
                if num_pr is not None:
                    break
        if num_pr is None:
            return None
        num_id = num_pr.find(f"{W}numId")
        ilvl = num_pr.find(f"{W}ilvl")
        num_id = num_id.get(f"{W}val") if num_id is not None else None
        ilvl = int(ilvl.get(f"{W}val")) if ilvl is not None else 0
        if num_id in (None, "0"):
            return None
        return num_id, ilvl, "-" if self._num_format(num_id, ilvl) == "bullet" else "1."

    def _num_format(self, num_id: str, ilvl: int) -> str | None:
        try:
            numbering = self.part.numbering_part.element
        except (KeyError, NotImplementedError):
            return None
        num = next((n for n in numbering.iter(f"{W}num") if n.get(f"{W}numId") == num_id), None)
        if num is None:
            return None
        override = num.find(f"{W}lvlOverride[@{W}ilvl='{ilvl}']/{W}lvl/{W}numFmt")
        if override is not None:
            return override.get(f"{W}val")
        abstract_id = num.find(f"{W}abstractNumId").get(f"{W}val")
        abstract = next(
            (a for a in numbering.iter(f"{W}abstractNum") if a.get(f"{W}abstractNumId") == abstract_id),
            None,
        )
        if abstract is None:
            return None
        fmt = abstract.find(f"{W}lvl[@{W}ilvl='{ilvl}']/{W}numFmt")
        return fmt.get(f"{W}val") if fmt is not None else None


def _field_text(field: dict) -> str:
    text = "".join(field["text"])
    match = FIELD_LINK.match(field["instr"])
    if match and text.strip():
        return f"[{text}]({match.group(1)})"
    return text


def _owned_box(box, p) -> bool:
    """True when box belongs to p directly: not inside another box, and not the mc:Fallback
    copy (text boxes are stored twice, as mc:Choice and mc:Fallback; only the Choice is read)."""
    parent = box.getparent()
    while parent is not None and parent is not p:
        if parent.tag in (f"{MC}Fallback", f"{W}txbxContent"):
            return False
        parent = parent.getparent()
    return True


def _parent_table(element):
    parent = element.getparent()
    while parent is not None and parent.tag != f"{W}tbl":
        parent = parent.getparent()
    return parent


def _table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"
