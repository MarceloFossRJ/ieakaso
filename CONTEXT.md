# Ieakaso

A local job-search assistant that drafts applications for a candidate; the candidate acts on them.

## Language

**User data**:
The candidate's own files, which are gitignored and never leave their machine: `config.yml`, `db/system_status.json`, `db/ieakaso_db.json`, and everything in `input/` and `output/` except the tracked placeholders (`.gitkeep` files and `input/documents/README.md`).
_Avoid_: personal data, private files

**Fresh state**:
The repo with no user data, exactly as after a clone and before the first `/ieakaso init`. The development cleaner (`ieakaso.devtools.cleaner`) returns a repo to it.
_Avoid_: clean install, reset state, empty repo

**Source CV**:
The candidate's main CV file in `input/documents/cv/`, as chosen during init. It is the only source of truth for CV content.
_Avoid_: original CV, uploaded CV, main document

**Parsed CV**:
`input/cv.md`, generated from the Source CV by the CV parser with the same words in the same order. It is never edited by hand; to change it, change the Source CV and parse again. Other modes read the Parsed CV, never the Source CV.
_Avoid_: CV markdown, transcribed CV, living CV
