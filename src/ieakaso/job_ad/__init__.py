"""The Job ad fetcher: reads one Job ad from a URL with one plain GET and writes it as Markdown.

Deterministic like the CV parser (docs/adr/0001-deterministic-cv-parser.md): same page in, same text out.
"""

from ieakaso.job_ad.errors import FetchError, JobAdError, NoAdError, UnreadableError
from ieakaso.job_ad.extract import extract
from ieakaso.job_ad.fetch import Page, fetch_page

__all__ = ["FetchError", "JobAdError", "NoAdError", "Page", "UnreadableError", "extract", "fetch_page"]
