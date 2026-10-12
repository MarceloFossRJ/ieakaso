"""A fetched page to the Job ad as Markdown: structured data first, the page's readable text with it or instead."""

import re
from urllib.parse import urlparse

from ieakaso.job_ad.errors import NoAdError, UnreadableError
from ieakaso.job_ad.markdown import convert
from ieakaso.job_ad.structured import ad_data, job_posting

MIN_TEXT = 150  # readable characters below which a page holds no ad
LOGIN_TEXT_MAX = 1000  # a page with a login form or address and more text than this is still read
CLOSED_TOP = 600  # a closed notice outside a notice element counts only in this many leading characters
LOGIN_PATH = re.compile(r"/(login|log-in|signin|sign-in|authwall|uas/login|checkpoint)(/|$)", re.IGNORECASE)
LIST_OR_HEADING_PREFIX = re.compile(r"^\s*(#+\s+|[-*]\s+|\d+\.\s+)")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
CLOSED = re.compile(
    r"no longer (available|accepting|open)"
    r"|(position|job|vacancy|role|posting|ad|listing)\b.{0,40}\b(has been filled|is filled|expired|(is|has|was) closed)"
    r"|applications?\s+(are\s+|is\s+)?(now\s+)?closed"
    r"|nicht mehr (verfügbar|aktuell|online|ausgeschrieben)"
    r"|(bereits|schon) besetzt"
    r"|stellenanzeige ist abgelaufen",
    re.IGNORECASE,
)


def extract(page_html: str, url: str = "") -> str:
    """The Job ad as Markdown. The first line is `Source: structured data`, `Source: page text` or
    `Source: structured data + page text` (the JobPosting plus a "More from the page" section).

    Raises UnreadableError (login wall, closed ad) or NoAdError (no ad content found).
    """
    job = job_posting(page_html)
    data = ad_data(job) if job else None
    page = convert(page_html, min_level=3 if data else 1)
    blocks = page.readable_blocks
    text = "\n\n".join(blocks)

    login_address = bool(LOGIN_PATH.search(urlparse(url).path))
    if not data and (page.has_password or login_address) and len(text) < LOGIN_TEXT_MAX:
        raise UnreadableError(
            "The page is a login wall: the ad can't be read without signing in. Please paste the ad text instead."
        )
    if CLOSED.search(" ".join([*page.notices, text[:CLOSED_TOP].replace("\n", " ")])):
        raise UnreadableError(
            "The page says the ad is closed or expired, so it can't be read. "
            "If it is still open, please paste the ad text instead."
        )

    if data:
        # The structured data can be thin (a benefits list, the contact person live only in the page).
        extra = _without_known_text(blocks, data.markdown)
        if not data.has_description and len(extra) < MIN_TEXT:
            raise NoAdError(_NO_AD)
        if extra:
            return f"Source: structured data + page text\n\n{data.markdown}\n\n## More from the page\n\n{extra}\n"
        return f"Source: structured data\n\n{data.markdown}\n"

    if len(text) < MIN_TEXT:
        raise NoAdError(_NO_AD)
    return f"Source: page text\n\n{text}\n"


_NO_AD = (
    "The page was fetched, but no Job ad was found: no schema.org JobPosting with a description and too little "
    "readable text (the page may need JavaScript). Please paste the ad text instead."
)


def _comparable(text: str) -> str:
    """Text without its Markdown prefix, whitespace-normalised and lowercase, for comparing."""
    return " ".join(LIST_OR_HEADING_PREFIX.sub("", text).split()).lower()


def _is_paragraph(block: str) -> bool:
    return not LIST_OR_HEADING_PREFIX.match(block)


def _sentences(paragraph: str) -> list[str]:
    """A paragraph's sentences, however its lines were broken."""
    return SENTENCE_END.split(" ".join(paragraph.split()))


def _heading_depth(block: str) -> int:
    """How many # a heading block starts with; 0 for any other block."""
    return len(block) - len(block.lstrip("#")) if block.startswith("#") else 0


def _without_known_text(blocks: list[str], known: str) -> str:
    """The blocks minus the sentences and list lines already in `known`; a heading with nothing under it goes too."""
    seen = set()
    for block in known.split("\n\n"):
        if _is_paragraph(block):
            seen.update(_comparable(sentence) for sentence in _sentences(block))
        else:
            seen.update(_comparable(line) for line in block.splitlines())

    kept = []
    for block in blocks:
        if _is_paragraph(block):
            new = [sentence for sentence in _sentences(block) if _comparable(sentence) not in seen]
            if new:
                kept.append(" ".join(new))
        else:
            lines = [line for line in block.splitlines() if _comparable(line) not in seen]
            if lines:
                kept.append("\n".join(lines))

    def empty_heading(index: int) -> bool:
        depth = _heading_depth(kept[index])
        if not depth:
            return False
        following = _heading_depth(kept[index + 1]) if index + 1 < len(kept) else 0
        return index + 1 == len(kept) or 0 < following <= depth

    return "\n\n".join(block for index, block in enumerate(kept) if not empty_heading(index))
