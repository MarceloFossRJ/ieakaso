"""A fetched page to the Job ad as Markdown: structured data first, the page's readable text second."""

import re
from urllib.parse import urlparse

from ieakaso.job_ad.errors import NoAdError, UnreadableError
from ieakaso.job_ad.markdown import MarkdownConverter
from ieakaso.job_ad.structured import job_posting, posting_markdown

MIN_TEXT = 150  # readable characters below which a page holds no ad
LOGIN_TEXT_MAX = 1000  # a page with a login form or address and more text than this is still read
LOGIN_PATH = re.compile(r"/(login|log-in|signin|sign-in|authwall|uas/login|checkpoint)(/|$)", re.IGNORECASE)
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
    """The Job ad as Markdown, first line `Source: structured data` or `Source: page text`.

    Raises UnreadableError (login wall, closed ad) or NoAdError (no ad content found).
    """
    posting = job_posting(page_html)
    markdown = posting_markdown(posting) if posting else None
    if markdown:
        return f"Source: structured data\n\n{markdown}\n"

    converter = MarkdownConverter()
    converter.feed(page_html)
    converter.finish()
    blocks = converter.main or converter.article or converter.body
    text = "\n\n".join(blocks)

    login_address = bool(LOGIN_PATH.search(urlparse(url).path))
    if (converter.has_password or login_address) and len(text) < LOGIN_TEXT_MAX:
        raise UnreadableError(
            "The page is a login wall: the ad can't be read without signing in. Please paste the ad text instead."
        )
    if CLOSED.search(text):
        raise UnreadableError(
            "The page says the ad is closed or expired, so it can't be read. "
            "If it is still open, please paste the ad text instead."
        )
    if len(text) < MIN_TEXT:
        raise NoAdError(
            "The page was fetched, but no job ad was found: no schema.org JobPosting and too little readable text "
            "(the page may need JavaScript). Please paste the ad text instead."
        )
    return f"Source: page text\n\n{text}\n"
