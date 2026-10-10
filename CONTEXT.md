# Ieakaso

A local job-search assistant that drafts applications for a candidate; the candidate acts on them.

## Language

**User data**:
The candidate's own files, which are gitignored and never leave their machine: `config.yml`, `db/system_status.json`, `db/ieakaso_db.json`, and everything in `input/` and `output/` except the tracked placeholders (`.gitkeep` files and `input/documents/README.md`).
_Avoid_: personal data, private files

**Fresh state**:
The repo with no user data, exactly as after a clone and before the first `/ieakaso init`. The development cleaner (`ieakaso.devtools.cleaner`) returns a repo to it.
_Avoid_: clean install, reset state, empty repo
