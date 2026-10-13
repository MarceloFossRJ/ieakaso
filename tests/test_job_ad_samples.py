"""The Job ad fetcher on Sample pages: real Job ad pages, anonymized, each with a hand-written expected ad.

The expected outputs hold what the agents need from the ad, so every expected line must appear in the fetcher's
output, in the same order; other page text around it is allowed. Markdown syntax and entities don't count.
A Sample the fetcher can't match yet is a strict xfail: when one starts passing, remove its mark.
"""

import html
import re

import pytest
from job_ad_fakes import SAMPLES, URL, sample, sample_expected

from ieakaso.job_ad import extract

PENDING: dict[str, str] = {}  # Samples the fetcher can't match yet, and why

LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BLOCK_PREFIX = re.compile(r"^\s*(#+\s+|[-*+]\s+|\d+\.\s+)", re.MULTILINE)
EMPHASIS = re.compile(r"\*\*|__|(?<!\w)[_*]|[_*](?!\w)")  # bold, and italics at a word's edge


def words(markdown: str) -> list[str]:
    """The text's words in order, without Markdown syntax or HTML entities."""
    text = BLOCK_PREFIX.sub("", LINK.sub(r"\1", markdown))
    return html.unescape(EMPHASIS.sub("", text)).split()


def missing_lines(expected: str, output: str) -> list[str]:
    """The expected lines not found in the output in the expected order, as normalized words."""
    text = f" {' '.join(words(output))} "
    missing, position = [], 0
    for line in expected.splitlines():
        wanted = " ".join(words(line))
        if not wanted:
            continue
        found = text.find(f" {wanted} ", position)
        if found < 0:
            missing.append(wanted)
        else:
            position = found + len(wanted) + 1
    return missing


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
    missing = missing_lines(sample_expected(name), ad)
    assert not missing, f"{name}: expected lines not found in order:\n" + "\n".join(line[:200] for line in missing)


def test_words_ignore_markdown_syntax_and_entities():
    assert words("## Role\n\n - __Lead__ the [team](https://x.example/) &amp; _ship_ fast\n1. Hire") == words(
        "Role\n- Lead the team & ship fast\n\nHire"
    )


def test_words_keep_underscores_inside_a_word():
    assert words("snake_case and 2*3") == ["snake_case", "and", "2*3"]


def test_expected_lines_may_have_other_text_around_them():
    assert (
        missing_lines("# Role\n\nLead the team", "Skip to content\n\n## Role\n\nApply now\n\nLead the team\n\nFooter")
        == []
    )


def test_an_expected_line_out_of_order_is_missing():
    assert missing_lines("First\nSecond", "Second\n\nFirst") == ["Second"]


def test_an_expected_line_matches_whole_words_only():
    assert missing_lines("Hybrid", "Hybrids only") == ["Hybrid"]
