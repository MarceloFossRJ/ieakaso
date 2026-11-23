"""Possible Echoes: the sentences of a Round's draft that share most of their content words with one Job ad sentence.

A smell, not a verdict: the Applicant Agent and the Seasoned Recruiter judge each hit (`CONTEXT.md`, Echo). Words are
compared lowercased, without stopwords, after stripping a few English suffixes, so "growing" meets "grow".
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ieakaso.cover_letter.assemble import NOTES
from ieakaso.cover_letter.errors import ApplicationError, RoundFileError
from ieakaso.layout import APPLICATIONS

# A draft sentence is a possible Echo when one ad sentence covers this share of its content words…
THRESHOLD = 0.5
# …and at least this many of them, so a sentence that only reuses the ad's terms ("the Customer Experience domain")
# is not flagged.
MIN_SHARED = 4

STOPWORDS = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "also",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "more",
        "most",
        "my",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "us",
        "let",
        "lets",
    ]
)
SUFFIXES = ("ing", "ed", "es", "ly", "s")
SENTENCE = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"”’)])\s+|\n+")
# An ad's lists are often one line joined with semicolons; each item is a sentence of its own.
AD_SENTENCE = re.compile(SENTENCE.pattern + r"|;\s+")
# A letter sentence ends like one: its header lines (the subject line, the company's address) are not checked.
ENDS = re.compile(r"[.!?][\"”’)]?$")
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class Echo:
    letter: str
    ad: str
    score: float


def _stem(word: str) -> str:
    word = word.removesuffix("'s")
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def content_words(sentence: str) -> set[str]:
    return {_stem(word) for word in WORD.findall(sentence.lower()) if word not in STOPWORDS}


def sentences(text: str, pattern: re.Pattern[str] = SENTENCE) -> list[str]:
    found = []
    for line in pattern.split(text):
        line = line.strip().lstrip("#>-*• ").rstrip("*").strip()
        if line:
            found.append(line)
    return found


def _read(path: Path, error: type[Exception], what: str) -> str:
    try:
        return path.read_text()
    except OSError:
        raise error(f"{what} missing or unreadable: {path}") from None


def _ad_text(folder: Path, application_id: str) -> str:
    """The Job ad file without its `# Job ad:` title and its `>` header line."""
    text = _read(folder / f"{application_id}_job-ad.md", ApplicationError, "Job ad file")
    return "\n".join(line for line in text.splitlines() if not line.startswith(("# Job ad:", ">")))


def _draft_text(folder: Path, round_number: int) -> str:
    """The Draft section of the Round's draft file: the letter alone, without the notes for the Assistant."""
    path = folder / "rounds" / f"round-{round_number}_draft.md"
    head, found, _ = _read(path, RoundFileError, "Round file").partition(NOTES)
    if not found or not head.startswith("## Draft"):
        raise RoundFileError(f"{path}: not a draft ('## Draft' then '{NOTES}')")
    return head.removeprefix("## Draft")


def find_echoes(root: Path, application_id: str, round_number: int) -> list[Echo]:
    """The draft's possible Echoes, each with its closest ad sentence, in the draft's order."""
    folder = root / APPLICATIONS / application_id
    if not folder.is_dir():
        raise ApplicationError(f"no Application folder: {folder}")
    ad = [(sentence, content_words(sentence)) for sentence in sentences(_ad_text(folder, application_id), AD_SENTENCE)]
    echoes = []
    for sentence in sentences(_draft_text(folder, round_number)):
        words = content_words(sentence)
        if not ad or not ENDS.search(sentence) or len(words) < MIN_SHARED:
            continue
        best, shared = max(((ad_sentence, len(words & ad_words)) for ad_sentence, ad_words in ad), key=lambda p: p[1])
        score = shared / len(words)
        if shared >= MIN_SHARED and score >= THRESHOLD:
            echoes.append(Echo(sentence, best, round(score, 2)))
    return echoes
