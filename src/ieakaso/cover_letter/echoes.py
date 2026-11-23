"""Possible Echoes: the sentences of a Round's draft that share most of their content words with one Job ad sentence.

A smell for the agents to judge: the Applicant Agent and the Seasoned Recruiter decide whether each hit is an Echo (`CONTEXT.md`, Echo). Words are
compared lowercased, without stopwords, as light English stems, so "growing" meets "grow" and "shaping" meets "shape".
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ieakaso.cover_letter.errors import ApplicationError
from ieakaso.cover_letter.files import application_folder, draft_path, job_ad_path, read, split_draft

# A draft sentence is a possible Echo when one ad sentence covers this share of its content words…
THRESHOLD = 0.5
# …and at least this many of them, so a sentence that only reuses the ad's terms ("the Customer Experience domain")
# is not flagged.
MIN_SHARED = 4

STOPWORDS = frozenset(
    """a about above after again against all also am an and any are as at be because been before being below between
    both but by can could did do does doing down during each few for from further had has have having he her here hers
    him his how i if in into is it its itself just me more most my no nor not now of off on once only or other our ours
    out over own same she should so some such than that the their theirs them then there these they this those through
    to too under until up very was we were what when where which while who whom why will with would you your yours
    us let lets""".split()  # noqa: SIM905 - a word list reads better as text
)
# Longest first. "-ies" and "-ied" become "-y" (priorities, priority); the rest are cut.
SUFFIXES = ("ingly", "edly", "ings", "ing", "ies", "ied", "es", "ed", "ly", "s")
# A stem shorter than this is left whole: "uses" stays a word, not "us".
MIN_STEM = 3
SENTENCE = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"”’)])\s+|\n+")
# An ad's lists are often one line joined with semicolons; each item is a sentence of its own.
AD_SENTENCE = re.compile(SENTENCE.pattern + r"|;\s+")
# A line that starts a block of its own, never joined to the line before: a heading, a quote, a list item, a table row.
BLOCK_START = re.compile(r"\s*(?:#|>|[-*•+] |\d+[.)] |\|)")
# A letter sentence ends like one: its header lines (the subject line, the company's address) are not checked.
ENDS = re.compile(r"[.!?][\"”’)]?$")
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class Echo:
    letter: str
    ad: str
    score: float  # the share of the letter sentence's content words the ad sentence holds, 0 to 1


@dataclass(frozen=True)
class AdSentence:
    text: str
    words: set[str]


def _stem(word: str) -> str:
    """A light English stem: the suffix cut, then a final silent "e" dropped and a doubled final consonant undoubled,
    so a word's forms meet ("shape", "shaping"; "plan", "planned"; "decide", "deciding")."""
    word = word.removesuffix("'s")
    for suffix in SUFFIXES:
        if suffix == "s" and word.endswith(("ss", "us", "is")):
            continue  # process, status, analysis: no plural to cut
        if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM:
            word = word[: -len(suffix)] + ("y" if suffix in ("ies", "ied") else "")
            break
    if word.endswith("e") and len(word) > MIN_STEM:
        word = word[:-1]
    # "planned" -> "plann" -> "plan"; vowels, "l" and "s" stay doubled, as in "feel", "skill" and "process".
    if len(word) > MIN_STEM and word[-1] == word[-2] and word[-1] not in "aeiouls":
        word = word[:-1]
    return word


def content_words(sentence: str) -> set[str]:
    return {_stem(word) for word in WORD.findall(sentence.lower()) if word not in STOPWORDS}


def _unwrap(text: str) -> str:
    """Join the lines a hard-wrapped sentence was broken into: a line that goes on in lowercase. A blank line, a heading,
    a list item, a table row or a Markdown hard break (two trailing spaces) still ends a line, and so does a line before
    one that starts with a capital, as the items of a list without markers do."""
    lines: list[str] = []
    for line in text.splitlines():
        joins = lines and lines[-1].strip() and not lines[-1].endswith("  ") and line.strip()[:1].islower()
        if joins and not BLOCK_START.match(line) and not BLOCK_START.match(lines[-1]):
            lines[-1] = f"{lines[-1].rstrip()} {line.strip()}"
        else:
            lines.append(line)
    return "\n".join(lines)


def sentences(text: str, pattern: re.Pattern[str] = SENTENCE) -> list[str]:
    found = []
    for line in pattern.split(_unwrap(text)):
        line = line.strip().lstrip("#>-*• ").rstrip("*").strip()
        if line:
            found.append(line)
    return found


def _ad_text(folder: Path, application_id: str) -> str:
    """The Job ad file without its `# Job ad:` title and its `>` header line."""
    text = read(job_ad_path(folder, application_id), ApplicationError, "Job ad file")
    return "\n".join(line for line in text.splitlines() if not line.startswith(("# Job ad:", ">")))


def find_echoes(root: Path, application_id: str, round_number: int) -> list[Echo]:
    """The draft's possible Echoes, each with its closest ad sentence, in the draft's order."""
    folder = application_folder(root, application_id)
    ad = [AdSentence(text, content_words(text)) for text in sentences(_ad_text(folder, application_id), AD_SENTENCE)]
    if not ad:
        raise ApplicationError(f"the Job ad file has no text to compare: {job_ad_path(folder, application_id)}")
    draft, _ = split_draft(draft_path(folder, round_number))
    echoes = []
    for sentence in sentences(draft):
        words = content_words(sentence)
        if not ENDS.search(sentence) or len(words) < MIN_SHARED:
            continue
        closest = max(ad, key=lambda candidate: len(words & candidate.words))
        shared = len(words & closest.words)
        score = shared / len(words)
        if shared >= MIN_SHARED and score >= THRESHOLD:
            echoes.append(Echo(sentence, closest.text, score))
    return echoes
