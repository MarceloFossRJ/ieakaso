"""The Job ad fetcher on Sample pages: real Job ad pages, anonymized, each with a hand-written expected ad.

The expected outputs hold only the ad, so they are the spec for a fetcher that isolates the ad on a page without
structured data. The comparison is on words in order; Markdown syntax and entities don't count.
A Sample the fetcher can't match yet is a strict xfail: when one starts passing, remove its mark.
"""

import difflib
import html
import re

import pytest
from job_ad_fakes import SAMPLES, URL, sample, sample_expected

from ieakaso.job_ad import extract

NO_PAGE_TITLE = "no 'Page title:' line"
OTHER_TEXT = "keeps page text outside the ad"
MISSED_TEXT = "misses part of the ad"
GLUED = "glues the text of separate elements"

PENDING = {  # Samples the fetcher can't match yet, and why
    "director_engineering_frontend": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
    "em_ai_insurance": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
    "em_applied_ai_remote": NO_PAGE_TITLE,
    "em_fintech_trading": f"{NO_PAGE_TITLE}; {OTHER_TEXT}; {MISSED_TEXT}",
    "em_software_ai_job_board": OTHER_TEXT,
    "em_travel_business": f"{NO_PAGE_TITLE}; {GLUED}",
    "head_of_engineering_construction_ai": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
    "head_of_engineering_fintech": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
    "senior_em_accounting": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
    "software_em_media": f"{NO_PAGE_TITLE}; {OTHER_TEXT}",
}

LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BLOCK_PREFIX = re.compile(r"^\s*(#+\s+|[-*+]\s+|\d+\.\s+)", re.MULTILINE)
EMPHASIS = re.compile(r"\*\*|__|(?<!\w)[_*]|[_*](?!\w)")  # bold, and italics at a word's edge


def words(markdown: str) -> list[str]:
    """The text's words in order, without Markdown syntax or HTML entities."""
    text = BLOCK_PREFIX.sub("", LINK.sub(r"\1", markdown))
    return html.unescape(EMPHASIS.sub("", text)).split()


def word_diff(expected: list[str], actual: list[str]) -> str:
    """The words missing from the output and the extra ones, with a little context, for a failure message."""
    lines = []
    for tag, e1, e2, a1, a2 in difflib.SequenceMatcher(None, expected, actual, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            lines.append(f"missing at word {e1}: {' '.join(expected[e1:e2])[:300]}")
        if tag in ("insert", "replace"):
            lines.append(f"extra after word {e1}: {' '.join(actual[a1:a2])[:300]}")
    return "\n".join(lines)


def _cases():
    for path in sorted(SAMPLES.glob("*.html")):
        name = path.stem
        if not (SAMPLES / "expected" / f"{name}.md").exists():
            yield pytest.param(name, marks=pytest.mark.skip(reason="expected output not written yet"))
        elif name in PENDING:
            yield pytest.param(name, marks=pytest.mark.xfail(reason=f"the fetcher: {PENDING[name]}", strict=True))
        else:
            yield name


@pytest.mark.parametrize("name", list(_cases()))
def test_the_fetcher_finds_the_ad_on_a_sample_page(name: str):
    first, _, ad = extract(sample(name), URL).partition("\n")
    assert first == "Source: page text"
    expected, actual = words(sample_expected(name)), words(ad)
    assert actual == expected, f"{name}: the fetched ad differs from the expected one\n{word_diff(expected, actual)}"


def test_words_ignore_markdown_syntax_and_entities():
    assert words("## Role\n\n - __Lead__ the [team](https://x.example/) &amp; _ship_ fast\n1. Hire") == words(
        "Role\n- Lead the team & ship fast\n\nHire"
    )


def test_words_keep_underscores_inside_a_word():
    assert words("snake_case and 2*3") == ["snake_case", "and", "2*3"]
