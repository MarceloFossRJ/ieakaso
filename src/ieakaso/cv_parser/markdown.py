"""Markdown the format readers share, so tables and footnotes look the same from every format."""


def table_cell(text: str) -> str:
    """One line of cell text, with pipes escaped so they don't split the cell."""
    return " ".join(text.split()).replace("|", "\\|")


def table(rows: list[list[str]]) -> str:
    """A Markdown table with the first row as header; short rows are padded with empty cells."""
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return "\n".join(_row(r) for r in [rows[0], ["---"] * width, *rows[1:]])


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


class Footnotes:
    """Footnotes numbered by first reference, and how many have had their text written.

    A reader calls `reference` where a footnote is referenced, and `take` after the block
    that references it; the text then follows that block.
    """

    def __init__(self):
        self._texts: list[str | None] = []  # [^n] is the n-th; None when the note's text is missing
        self._written = 0

    def __len__(self) -> int:
        return len(self._texts)

    def reference(self, text: str | None) -> str:
        """Record a footnote and return its marker."""
        self._texts.append(text)
        return f"[^{len(self._texts)}]"

    def take(self, up_to: int | None = None) -> str:
        """Definitions for the footnotes not written yet, up to number up_to (default: all)."""
        up_to = len(self._texts) if up_to is None else up_to
        lines = [
            f"[^{number}]: {text}"
            for number, text in enumerate(self._texts[self._written:up_to], start=self._written + 1)
            if text is not None
        ]
        self._written = max(self._written, up_to)
        return "\n".join(lines)
