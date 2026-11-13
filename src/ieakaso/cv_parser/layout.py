"""Where things live in input/ (docs/adr/0006-input-split-by-who-writes.md).

The candidate writes `input/candidate/`; Ieakaso writes `input/parsed-documents/`.
"""

from pathlib import PurePosixPath

CANDIDATE = PurePosixPath("input/candidate")
DOCUMENTS = CANDIDATE / "documents"  # the Source documents
INBOX = DOCUMENTS / "cv"  # the CV inbox; each CV version gets a folder in it

PARSED = PurePosixPath("input/parsed-documents")
PARSED_CV = PARSED / "cv.md"
LINKEDIN_OUTPUT = PARSED / "linkedin.md"
LETTERS_OUTPUT = PARSED / "reference-letters"
FROZEN = PARSED / "cv-versions"  # <version id>.md: a CV version's Parsed CV as it was captured
