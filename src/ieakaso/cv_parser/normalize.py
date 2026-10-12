"""The character-level cleanups every format gets (except Markdown, copied as is)."""

import re
import unicodedata

# Typographic ligatures: one glyph drawn for several letters, not content of its own.
LIGATURES = str.maketrans({
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",
    "ﬆ": "st",
})


def normalize(text: str) -> str:
    """LF line endings, ligatures expanded, NFC, no trailing spaces, at most one blank
    line in a row, no leading blank lines, exactly one final newline."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text.translate(LIGATURES))
    lines = [line.rstrip() for line in text.split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip("\n") + "\n"
