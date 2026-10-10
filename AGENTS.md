# AGENTS.md

This file provides guidance to AI coding agents in this repository.

## Project state

Ieakaso is mostly at the design stage: the product runs through the `/ieakaso` skill (see Commands), and the Python package in `src/ieakaso/` so far holds only development tools.

- **Toolchain:** Python 3.14 managed by `uv`. Dependencies live in `pyproject.toml`; add them with `uv add` (or `uv add --dev` for development-only ones).
- **Tests:** `uv run pytest` (pytest, in `tests/`). Tests run on temporary fake repos; never let a test write to the real `input/`, `output/`, `config.yml`, or `db/`.
- **Development tools** live in `src/ieakaso/devtools/` and are never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.
  - Cleaner: `uv run python -m ieakaso.devtools.cleaner clean | restore [name] | list` returns the repo to a fresh state (see `CONTEXT.md`) so init can be tested from scratch. The command always backs up to `~/.ieakaso-backups/` first, and `restore` brings the newest backup back, or the named one. Options: `--dry-run` (`clean` and `restore`: show what would happen, change nothing), `--root` (default: found from the current folder), `--backup-dir`. Called from Python, `clean()` only backs up when given a `backup_dir`. If you add user data anywhere, add it to the cleaner and `.gitignore` together; `tests/test_cleaner_drift.py` fails when they disagree.
- `README.md` describes the product as designed in the [diagram](`docs/flows.excalidraw`); its Roadmap section lists features beyond the diagram that are not designed yet.
- License: AGPL-3.0.

## Requirements (source: `docs/flows.excalidraw`)

- **Runtime:** runs locally, driven from a coding-assistant CLI (Claude Code, OpenCode) rather than its own UI.
- **Storage:** file-based, using Markdown files in a structured folder tree. Application status is the folder an application sits in: `Applied` → `Interviewing` → `Not selected` / `Offer`.
- **Memory:** on first run, the user provides their CV, a professional "about me", key projects, biggest achievements, and a personal SWOT. The agent should compound learnings from each application process back into memory.
- **Two agents:** an *Applicant Agent* that writes the drafts and a *Seasoned Recruiter* that reviews them.
- **Application flow:**
  1. The user pastes a job ad URL.
  2. Read the ad and highlight the posting's strong and weak points.
  3. Decide whether the user is a top applicant.
  4. Read the application form.
  5. Prepare an application report.
  6. If the form asks for a cover letter, the Applicant drafts it and the Recruiter grades it from 1 to 10. Below 9, the Recruiter suggests changes and the Applicant rewrites, and this repeats until the grade is at least 9.
  7. Suggest next steps.
- **Interview prep flow:** a second flow, not yet detailed.

## Commands

All commands go through one skill, `ai/skills/ieakaso/` (loaded through the pointer `.claude/skills/ieakaso/SKILL.md`): `/ieakaso <mode> [args]`. Each mode is a file in `ai/skills/ieakaso/modes/`; add new modes there and to the table in `ai/skills/ieakaso/SKILL.md`. The skill description lives only in the pointer; update it there when modes change.

- **First run:** every mode except `init` checks `db/system_status.json` first and runs `/ieakaso init` if setup is missing or incomplete. `init` is idempotent.
- **User data:** `config.yml` (candidate data, format in `config_example.yml`), `db/system_status.json` (setup state, starting point in `db/system_status_example.json`), `db/ieakaso_db.json`, and the contents of `input/` and `output/` are gitignored and stay on the user's machine. The only mandatory document is the CV in `input/documents/cv/`.

## Product guardrails

The tool drafts and the user acts. It never submits applications or sends emails, and it never fabricates CV content; it only reformulates it. It advises against applying when the score is below 4.0/5, but the user can override that.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `MarceloFossRJ/ieakaso`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
