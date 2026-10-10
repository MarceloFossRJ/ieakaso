"""TeX: reads only the document body, and only the commands listed here. Any other
command or environment is a hard error naming its line, never a guess.

pylatexenc is used for parsing only; the mapping to Markdown is ours.
"""

import re
import unicodedata
from pathlib import Path

from pylatexenc import latexwalker as lw
from pylatexenc.macrospec import EnvironmentSpec, MacroSpec

from ieakaso.cv_parser.errors import CvParseError
from ieakaso.cv_parser.markdown import Footnotes, table, table_cell

HEADINGS = {"part": 1, "chapter": 1, "section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4, "subparagraph": 5}

# Commands that show their last argument as it is (styling dropped).
SHOW_CONTENT = {
    "textbf": "{", "textit": "{", "emph": "{", "underline": "{", "textsc": "{", "texttt": "{",
    "textrm": "{", "textsf": "{", "textmd": "{", "textup": "{", "textsl": "{", "textnormal": "{",
    "mbox": "{", "text": "{", "textcolor": "[{{", "colorbox": "[{{", "makebox": "[[{", "fbox": "{",
    "caption": "[{",
}

# Commands that show nothing: layout, spacing, sizes, fonts, and their arguments.
IGNORE = {
    "vspace": "*{", "hspace": "*{", "vfill": "", "medskip": "", "smallskip": "", "bigskip": "",
    "noindent": "", "indent": "", "centering": "", "raggedright": "", "raggedleft": "",
    "clearpage": "", "newpage": "", "pagebreak": "[", "nopagebreak": "[", "nolinebreak": "[",
    "label": "{", "pagestyle": "{", "thispagestyle": "{", "setlength": "{{", "addtolength": "{{",
    "color": "[{", "tiny": "", "scriptsize": "", "footnotesize": "", "small": "", "normalsize": "",
    "large": "", "Large": "", "LARGE": "", "huge": "", "Huge": "", "bfseries": "", "itshape": "",
    "mdseries": "", "scshape": "", "upshape": "", "slshape": "", "normalfont": "", "rmfamily": "",
    "sffamily": "", "ttfamily": "", "sloppy": "", "includegraphics": "[{", "hline": "",
    "cline": "{", "toprule": "[", "midrule": "[", "bottomrule": "[", "cmidrule": "[{",
    "maketitle": "", "tableofcontents": "", "null": "", "strut": "", "@": "", "/": "",
    "protect": "", "relax": "",
}

SPACES = {"hfill": " ", "quad": " ", "qquad": " ", " ": " ", ",": " ", ";": " ", ":": " ", "enspace": " ", "thinspace": " "}

SYMBOLS = {
    "&": "&", "%": "%", "$": "$", "#": "#", "_": "_", "{": "{", "}": "}",
    "textbar": "|", "textbackslash": "\\", "textasciitilde": "~", "textasciicircum": "^",
    "ldots": "…", "dots": "…", "textellipsis": "…", "textendash": "–", "textemdash": "—",
    "textbullet": "•", "textperiodcentered": "·", "textquoteleft": "‘", "textquoteright": "’",
    "textquotedblleft": "“", "textquotedblright": "”", "copyright": "©", "textcopyright": "©",
    "textregistered": "®", "texttrademark": "™", "euro": "€", "texteuro": "€", "pounds": "£",
    "textdegree": "°", "S": "§", "P": "¶", "ss": "ß", "ae": "æ", "AE": "Æ", "oe": "œ", "OE": "Œ",
    "o": "ø", "O": "Ø", "aa": "å", "AA": "Å", "l": "ł", "L": "Ł", "i": "ı", "j": "ȷ",
    "LaTeX": "LaTeX", "TeX": "TeX",
}

ACCENTS = {
    "'": "́", "`": "̀", "^": "̂", '"': "̈", "~": "̃", "=": "̄",
    ".": "̇", "u": "̆", "v": "̌", "H": "̋", "c": "̧", "d": "̣",
    "b": "̱", "k": "̨", "r": "̊",
}

SPECIALS = {"--": "–", "---": "—", "``": "“", "''": "”", "~": " ", "!`": "¡", "?`": "¿"}

MATH = {"sim": "~", "times": "×", "cdot": "·", "pm": "±", "approx": "≈", "leq": "≤", "geq": "≥",
        "rightarrow": "→", "to": "→", "%": "%", "#": "#", "&": "&", "_": "_", "$": "$", "bullet": "•",
        "circ": "°", "degree": "°", "ast": "*", "star": "*", "mid": "|", "vert": "|", "infty": "∞",
        "mu": "µ", "alpha": "α", "beta": "β", "gamma": "γ", "lambda": "λ", "pi": "π", "sigma": "σ"}

TRANSPARENT_ENVS = {
    "document": "", "center": "", "flushleft": "", "flushright": "", "minipage": "[[[{",
    "multicols": "{[", "quote": "", "quotation": "", "verse": "", "table": "[", "table*": "[",
    "figure": "[", "figure*": "[", "small": "", "footnotesize": "", "abstract": "",
}
LIST_ENVS = {"itemize": "-", "enumerate": "1.", "description": "-"}
TABLE_ENVS = {"tabular": "[{", "tabular*": "{[{", "tabularx": "{[{", "tabulary": "{[{", "longtable": "[{"}
# A forced line break (\\); the source newline that usually follows it must not split the paragraph.
LINE_BREAK = "\x01"
PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n\s*")
INCLUDES = {"input", "include", "import", "subfile", "subimport", "includeonly"}


def _context():
    db = lw.get_default_latex_context_db()
    macros = [MacroSpec(name, spec) for name, spec in {**SHOW_CONTENT, **IGNORE}.items()]
    macros += [MacroSpec(name, "") for name in (*SPACES, *SYMBOLS)]
    macros += [MacroSpec(name, "{") for name in ACCENTS]
    macros += [MacroSpec(name, "*[{") for name in HEADINGS]
    macros += [
        MacroSpec("href", "[{{"), MacroSpec("url", "{"), MacroSpec("footnote", "[{"),
        MacroSpec("item", "["), MacroSpec("\\", "*["), MacroSpec("newline", ""), MacroSpec("par", ""),
        MacroSpec("multicolumn", "{{{"), MacroSpec("linebreak", "["),
    ]
    macros += [MacroSpec(name, "{") for name in INCLUDES]
    envs = [EnvironmentSpec(n, s) for n, s in {**TRANSPARENT_ENVS, **TABLE_ENVS}.items()]
    envs += [EnvironmentSpec(n, "[") for n in LIST_ENVS]
    db.add_context_category("ieakaso", macros=macros, environments=envs, prepend=True)
    return db


CONTEXT = _context()


def read_tex(source: Path) -> str:
    try:
        text = source.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CvParseError(
            f"{source.name} is not saved as UTF-8 text. Save it again with UTF-8 encoding."
        ) from None
    return _Renderer(source.name, text).render()


class _Unsupported(Exception):
    def __init__(self, what: str, pos: int):
        self.what, self.pos = what, pos


class _Renderer:
    def __init__(self, name: str, text: str):
        self.name, self.text = name, text
        self.footnotes = Footnotes()
        self.depth = 0  # nesting of blocks(); only the document body (depth 1) writes footnote text

    def render(self) -> str:
        walker = lw.LatexWalker(self.text, latex_context=CONTEXT, tolerant_parsing=False)
        try:
            nodes, _, _ = walker.get_latex_nodes()
        except lw.LatexWalkerError as error:
            line = getattr(error, "lineno", None)
            where = f" near line {line}" if line else ""
            raise CvParseError(
                f"{self.name} could not be read as TeX{where}: {error.msg}. "
                "Check that it compiles, or export your CV as PDF or DOCX instead."
            ) from None
        body = _find_document(nodes)
        if body is None:
            raise CvParseError(
                f"{self.name} has no \\begin{{document}} … \\end{{document}} body. "
                "Use the full TeX file that produces your CV, or export it as PDF or DOCX instead."
            )
        try:
            md = self.blocks(body.nodelist)
        except _Unsupported as error:
            line = self.text.count("\n", 0, error.pos) + 1
            if error.what.lstrip("\\") in INCLUDES:
                hint = "Put the included file's content into the main file, or export your CV as PDF or DOCX instead."
            else:
                hint = "Ieakaso reads only common TeX commands. Export your CV as PDF or DOCX instead."
            raise CvParseError(f"{self.name} uses {error.what} on line {line}, which Ieakaso can't read. {hint}") from None
        return md

    # --- blocks: paragraphs split on blank lines; headings, lists and tables stand alone ---

    def blocks(self, nodes) -> str:
        """Footnote text follows the paragraph, list or table that references it. Blocks nested in
        an environment, list item or table cell leave it to the enclosing top-level block."""
        self.depth += 1
        try:
            return self._blocks(nodes)
        finally:
            self.depth -= 1

    def _blocks(self, nodes) -> str:
        out, paragraph = [], []

        def flush():
            text = _tidy_paragraph("".join(paragraph))
            if text:
                out.append(text)
                self.add_notes(out)
            paragraph.clear()

        for node in nodes:
            block = self.block(node)
            if block is not None:
                flush()
                if block:
                    out.append(block)
                    self.add_notes(out)
            elif isinstance(node, lw.LatexCharsNode):
                # A blank line ends the paragraph here, so its footnotes follow it.
                first, *rest = PARAGRAPH_BREAK.split(node.chars)
                paragraph.append(first)
                for piece in rest:
                    flush()
                    paragraph.append(piece)
            else:
                paragraph.append(self.inline([node], keep_newlines=True))
        flush()
        return "\n\n".join(out)

    def add_notes(self, out: list[str]) -> None:
        """Append the text of footnotes not yet written; only the document body writes it."""
        notes = self.footnotes.take() if self.depth == 1 else ""
        if notes:
            out.append(notes)

    def block(self, node):
        """Markdown for a block-level node, '' for a block that shows nothing, None for inline."""
        if isinstance(node, lw.LatexMacroNode):
            name = node.macroname
            if name in HEADINGS:
                return f"{'#' * HEADINGS[name]} {self.inline_arg(node, -1)}"
            if name == "par":
                return ""
        if isinstance(node, lw.LatexEnvironmentNode):
            name = node.environmentname
            if name in TRANSPARENT_ENVS:
                return self.blocks(node.nodelist)
            if name in LIST_ENVS:
                return self.list(node, LIST_ENVS[name])
            if name in TABLE_ENVS:
                return self.table(node)
            raise _Unsupported(f"the {name} environment", node.pos)
        return None

    def list(self, env, marker: str) -> str:
        items, current = [], None
        for node in env.nodelist:
            if isinstance(node, lw.LatexMacroNode) and node.macroname == "item":
                current = []
                items.append(current)
                label = node.nodeargd.argnlist[0] if node.nodeargd else None
                if label is not None:
                    current.append(self.inline(label.nodelist) + " ")
                continue
            if current is None:
                if self.inline([node]).strip():
                    raise _Unsupported("text before the first \\item", node.pos)
                continue
            block = self.block(node)
            current.append(self.inline([node]) if block is None else "\n" + _indent(block) + "\n")
        lines = []
        for item in items:
            text = "".join(item)
            first, _, rest = text.strip().partition("\n")
            # Lines after the first continue the item: nested blocks keep their indent, text gets it.
            rest = [r if r.startswith("  ") or not r.strip() else "  " + r.strip() for r in rest.rstrip().split("\n")]
            lines.append("\n".join([f"{marker} {_squash(first)}", *rest]).rstrip())
        return "\n".join(lines)

    def table(self, env) -> str:
        rows, row, cell = [], [], []
        pad = 0  # empty cells a \multicolumn adds after its own

        def end_cell():
            nonlocal pad
            row.append(table_cell("".join(cell).replace(LINE_BREAK, " ")))
            row.extend([""] * pad)
            cell.clear()
            pad = 0

        for node in env.nodelist:
            if isinstance(node, lw.LatexSpecialsNode) and node.specials_chars == "&":
                end_cell()
            elif isinstance(node, lw.LatexMacroNode) and node.macroname in ("\\", "tabularnewline"):
                end_cell()
                rows.append(row)
                row = []
            elif isinstance(node, lw.LatexMacroNode) and node.macroname == "multicolumn":
                pad = int(_squash(self.inline_arg(node, 0)) or 1) - 1
                cell.append(self.inline_arg(node, 2))
            else:
                cell.append(self.inline([node]))
        if "".join(cell).strip() or row:
            end_cell()
            rows.append(row)
        return table([r for r in rows if any(r)])

    # --- inline ------------------------------------------------------------

    def inline_arg(self, node, index: int) -> str:
        args = [a for a in node.nodeargd.argnlist if a is not None]
        return _squash(self.inline(args[index].nodelist if hasattr(args[index], "nodelist") else [args[index]]))

    def inline(self, nodes, keep_newlines: bool = False) -> str:
        out = []
        for node in nodes:
            if node is None or isinstance(node, lw.LatexCommentNode):
                continue
            if isinstance(node, lw.LatexCharsNode):
                out.append(node.chars)
            elif isinstance(node, lw.LatexGroupNode):
                out.append(self.inline(node.nodelist, keep_newlines))
            elif isinstance(node, lw.LatexSpecialsNode):
                if node.specials_chars not in SPECIALS:
                    raise _Unsupported(f"“{node.specials_chars}” outside a table", node.pos)
                out.append(SPECIALS[node.specials_chars])
            elif isinstance(node, lw.LatexMathNode):
                out.append(self.math(node))
            elif isinstance(node, lw.LatexMacroNode):
                out.append(self.macro(node))
            elif isinstance(node, lw.LatexEnvironmentNode):
                block = self.block(node)
                out.append("\n\n" + block + "\n\n")
            else:
                raise _Unsupported(type(node).__name__, node.pos)
        return "".join(out)

    def macro(self, node) -> str:
        name = node.macroname
        if name in IGNORE:
            return ""
        if name in SPACES:
            return " "
        if name in SYMBOLS:
            return SYMBOLS[name]
        if name in SHOW_CONTENT:
            return self.inline_arg(node, -1)
        if name in ACCENTS:
            base = self.inline_arg(node, -1)
            return unicodedata.normalize("NFC", base[:1] + ACCENTS[name] + base[1:]) if base else ""
        if name in ("\\", "newline", "linebreak"):
            return LINE_BREAK
        if name == "href":
            url = _squash(self.text_arg(node, -2))
            return f"[{self.inline_arg(node, -1)}]({url})"
        if name == "url":
            url = _squash(self.text_arg(node, -1))
            return f"[{url}]({url})"
        if name == "footnote":
            return self.footnotes.reference(self.inline_arg(node, -1))
        raise _Unsupported(f"\\{name}", node.pos)

    def text_arg(self, node, index: int) -> str:
        """An argument taken literally (URLs), keeping characters like % and ~."""
        args = [a for a in node.nodeargd.argnlist if a is not None]
        arg = args[index]
        verbatim = arg.latex_verbatim()
        return verbatim[1:-1] if verbatim.startswith("{") else verbatim

    def math(self, node) -> str:
        out = []
        for child in node.nodelist:
            if isinstance(child, lw.LatexCharsNode):
                out.append(child.chars)
            elif isinstance(child, lw.LatexMacroNode) and child.macroname in MATH:
                out.append(MATH[child.macroname])
            elif isinstance(child, lw.LatexGroupNode):
                out.append(self.math(child))
            else:
                raise _Unsupported("this math", node.pos)
        return "".join(out)


def _find_document(nodes):
    for node in nodes:
        if isinstance(node, lw.LatexEnvironmentNode) and node.environmentname == "document":
            return node
    return None


def _squash(text: str) -> str:
    return " ".join(text.replace(LINE_BREAK, " ").split())


def _tidy_paragraph(text: str) -> str:
    """Source line breaks inside a paragraph stay; runs of spaces become one; blank lines split."""
    parts = PARAGRAPH_BREAK.split(text)
    tidy = []
    for part in parts:
        part = re.sub(LINE_BREAK + r"[ \t]*\n?", "\n", part)
        lines = [" ".join(line.split()) for line in part.split("\n")]
        joined = "\n".join(line for line in lines if line)
        if joined:
            tidy.append(joined)
    return "\n\n".join(tidy)


def _indent(block: str) -> str:
    return "\n".join(("  " + line) if line else line for line in block.split("\n"))
