"""HTML to Markdown for Job ads: headings, paragraphs and lists, keeping the words and their order."""

import re
from dataclasses import dataclass
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
PAGE_ROOTS = {"html", "body", "main", "article"}  # the page itself: never a banner or a notice, whatever its class
BANNER = re.compile(r"cookie|consent", re.IGNORECASE)
NOTICE = re.compile(r"notice|alert|expired|closed", re.IGNORECASE)
NOTICE_ROLES = {"alert", "status"}
BREAK = "\x00"


@dataclass
class _List:
    kind: str  # "ul" or "ol"
    count: int = 0  # items so far, for the numbers of an "ol"


class MarkdownConverter(HTMLParser):
    """Turns HTML into Markdown blocks. Blocks are kept per region so the caller can pick <main>, <article> or <body>.

    Headings are at least `min_level` deep (a structured description sits under the ad's own title).
    `notices` holds the text of elements that look like a notice (role alert or status, or a name saying so).
    """

    def __init__(self, min_level: int = 1):
        super().__init__(convert_charrefs=True)
        self.min_level = min_level
        self.body: list[str] = []
        self.main: list[str] = []
        self.article: list[str] = []
        self.notices: list[str] = []
        self.has_password = False
        self._stack: list[str] = []
        self._skip_from: int | None = None
        self._notice_from: int | None = None
        self._notice_text: list[str] = []
        self._inline: list[str] = []
        self._heading: int | None = None
        self._lists: list[_List] = []
        self._list_lines: list[str] = []
        self._marker: str | None = None

    @property
    def readable_blocks(self) -> list[str]:
        """The page's readable blocks: <main> if it has any, else <article>, else the whole <body>."""
        return self.main or self.article or self.body

    # Parser events

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and (attributes.get("type") or "").lower() == "password":
            self.has_password = True
        if tag not in VOID:
            self._stack.append(tag)
            if tag not in PAGE_ROOTS:
                self._open_special(tag, attributes)
        if self._skip_from is not None:
            return
        level = _heading_level(tag)
        if tag == "br":
            self._inline.append(BREAK)
        elif tag in ("td", "th"):
            self._inline.append(" ")
        elif tag in ("ul", "ol"):
            self._flush()
            self._lists.append(_List(tag))
        elif tag == "li":
            self._flush()
            if self._lists:
                current = self._lists[-1]
                current.count += 1
                bullet = "- " if current.kind == "ul" else f"{current.count}. "
                self._marker = "  " * (len(self._lists) - 1) + bullet
        elif level:
            self._flush()
            self._heading = max(level, self.min_level)
        elif tag in BLOCK:
            self._flush()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
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
        if self._notice_from is not None and len(self._stack) <= self._notice_from:
            self.notices.append(" ".join("".join(self._notice_text).split()))
            self._notice_from = None

    def handle_data(self, data):
        if self._notice_from is not None:
            self._notice_text.append(data)
        if self._skip_from is None:
            self._inline.append(data)

    # Output

    def finish(self) -> None:
        """Call after feed(): flushes what is still pending."""
        self.close()
        self._flush()
        self._end_lists()

    def _open_special(self, tag: str, attributes: dict) -> None:
        """Start skipping a script, a banner and the like; start collecting the text of a notice."""
        name = f"{attributes.get('id') or ''} {attributes.get('class') or ''}"
        if self._skip_from is None and (tag in SKIP or BANNER.search(name)):
            self._flush()
            self._skip_from = len(self._stack) - 1
        is_notice = (attributes.get("role") or "").lower() in NOTICE_ROLES or NOTICE.search(name)
        if self._notice_from is None and is_notice:
            self._notice_from = len(self._stack) - 1
            self._notice_text = []

    def _close(self, tag: str) -> None:
        if _heading_level(tag):
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
        """Turn the pending inline text into a block (or a list line)."""
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


def convert(html: str, min_level: int = 1) -> MarkdownConverter:
    """Parse an HTML page or fragment; the result holds its Markdown blocks."""
    converter = MarkdownConverter(min_level)
    converter.feed(html)
    converter.finish()
    return converter


def to_markdown(html: str, min_level: int = 1) -> str:
    """The Markdown of an HTML fragment, blocks separated by a blank line."""
    return "\n\n".join(convert(html, min_level).body)


def _heading_level(tag: str) -> int | None:
    """1-6 for h1-h6, else None."""
    return int(tag[1]) if len(tag) == 2 and tag[0] == "h" and tag[1] in "123456" else None
