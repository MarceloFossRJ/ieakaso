# `input/` is split by who writes each file

`input/` holds everything the agents read about the candidate, and `output/` everything Ieakaso delivers. Inside `input/`, the folder says who writes each file. The candidate writes `input/candidate/`: the Source documents in `input/candidate/documents/` (including the CV inbox and the CV version folders) and the memory files. Ieakaso writes `input/parsed-documents/`: `cv.md`, `linkedin.md`, `reference-letters/<name>.md` and the frozen copies `cv-versions/<id>.md`, which the candidate must never edit. Before this, generated and hand-written files sat side by side in `input/`, so a candidate couldn't tell which ones were theirs to change.

## Considered Options

- **Generated files as named exceptions in `input/`.** Rejected: every new generated file adds an exception to remember.
- **Parsed documents in `output/parsed-documents/`.** Rejected: the agents read them as inputs, so a future reader would wonder why they sit with the deliverables, and the Personal knowledge base would span both folders.

## Consequences

- This amends ADR 0004 (the Parsed documents' paths) and ADR 0005: a CV version folder now holds only the candidate's file, and its frozen Parsed CV lives in `input/parsed-documents/cv-versions/`.
- On its first run, the CV parser moves every file from its old place to its new one before any check. It rewrites the paths in `db/system_status.json` and in `cv_versions`, and it never overwrites a file already at the new place. Moving rather than regenerating keeps a hand-edited Parsed document detectable.
