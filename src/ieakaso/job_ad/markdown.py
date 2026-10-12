"""HTML to Markdown for Job ads: headings, paragraphs and lists, keeping the words and their order."""

import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP = {
    "script", "style", "head", "title", "noscript", "template", "svg", "iframe", "button", "select",
    "nav", "header", "footer", "aside", "form",
}  # fmt: skip
BLOCK = {
    "p", "div", "section", "article", "main", "blockquote", "pre", "table", "tr", "dl", "dt", "dd", "figure",
    "figcaption", "hr", "address",
}  # fmt: skip
BANNER = re.compile(r"cookie|consent", re.IGNORECASE)
BREAK = "\x00"


class MarkdownConverter(HTMLParser):
    """Turns HTML into Markdown blocks. Blocks are kept per region so the caller can pick <main>, <article> or <body>.

    Headings are at least `min_level` deep (a structured description sits under the ad's own title).
    """

    def __init__(self, min_level: int = 1):
        super().__init__(convert_charrefs=True)
        self.min_level = min_level
        self.body: list[str] = []
        self.main: list[str] = []
        self.article: list[str] = []
        self.has_password = False
        self._stack: list[str] = []
        self._skip_from: int | None = None
        self._inline: list[str] = []
        self._heading: int | None = None
        self._lists: list[list] = []  # [kind, counter]
        self._list_lines: list[str] = []
        self._marker: str | None = None

    # Parser events

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and (attributes.get("type") or "").lower() == "password":
            self.has_password = True
        if tag not in VOID:
            self._stack.append(tag)
            if self._skip_from is None and (tag in SKIP or BANNER.search(_ident(attributes))):
                self._flush()
                self._skip_from = len(self._stack) - 1
        if self._skip_from is not None:
            return
        if tag == "br":
            self._inline.append(BREAK)
        elif tag in ("td", "th"):
            self._inline.append(" ")
        elif tag in ("ul", "ol"):
            self._flush()
            self._lists.append([tag, 0])
        elif tag == "li":
            self._flush()
            if self._lists:
                self._lists[-1][1] += 1
                kind, count = self._lists[-1]
                self._marker = "  " * (len(self._lists) - 1) + ("- " if kind == "ul" else f"{count}. ")
        elif len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self._flush()
            self._heading = max(int(tag[1]), self.min_level)
        elif tag in BLOCK:
            self._flush()

    def handle_startendtag(self, tag, attrs):
        if tag in VOID:
            self.handle_starttag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag not in self._stack:
            return
        if self._skip_from is None:
            self._close(tag)
        while self._stack:
            if self._stack.pop() == tag:
                break
        if self._skip_from is not None and len(self._stack) <= self._skip_from:
            self._skip_from = None

    def handle_data(self, data):
        if self._skip_from is None:
            self._inline.append(data)

    # Output

    def finish(self) -> None:
        self.close()
        self._flush()
        self._end_lists()

    def _close(self, tag: str) -> None:
        if len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self._flush()
            self._heading = None
        elif tag in ("ul", "ol"):
            self._flush()
            if self._lists:
                self._lists.pop()
            if not self._lists:
                self._end_lists()
        elif tag == "li" or tag in BLOCK:
            self._flush()

    def _flush(self) -> None:
        raw = "".join(self._inline)
        self._inline = []
        lines = [" ".join(part.split()) for part in raw.split(BREAK)]
        lines = [line for line in lines if line]
        if not lines:
            return
        if self._heading:
            self._emit("#" * self._heading + " " + " ".join(lines))
        elif self._lists:
            indent = "  " * len(self._lists)
            first = self._marker if self._marker is not None else indent
            self._marker = None
            self._list_lines.append(first + lines[0])
            self._list_lines.extend(indent + line for line in lines[1:])
        else:
            self._emit("\n".join(lines))

    def _end_lists(self) -> None:
        if self._list_lines:
            self._emit("\n".join(self._list_lines))
            self._list_lines = []

    def _emit(self, block: str) -> None:
        self.body.append(block)
        if "main" in self._stack:
            self.main.append(block)
        if "article" in self._stack:
            self.article.append(block)


def to_markdown(html: str, min_level: int = 1) -> str:
    """The Markdown of an HTML fragment, blocks separated by a blank line."""
    converter = MarkdownConverter(min_level)
    converter.feed(html)
    converter.finish()
    return "\n\n".join(converter.body)


def _ident(attributes: dict) -> str:
    return f"{attributes.get('id') or ''} {attributes.get('class') or ''}"
