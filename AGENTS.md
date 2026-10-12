# AGENTS.md

This file provides guidance to AI coding agents in this repository.

## Project state

Ieakaso is mostly at the design stage: the product runs through the `/ieakaso` skill (see Commands). The Python package in `src/ieakaso/` holds the CV parser, the usage display and the development tools.

- **Toolchain:** Python 3.14 managed by `uv`. Dependencies live in `pyproject.toml`; add them with `uv add` (or `uv add --dev` for development-only ones).
- **Tests:** `uv run pytest` (pytest, in `tests/`). Tests run on temporary fake repos; never let a test write to the real `input/`, `output/`, `config.yml`, or `db/`.
- **CV parser:** `src/ieakaso/cv_parser/` turns the Source CV into the Parsed CV `input/cv.md` (terms in `CONTEXT.md`, decisions in `docs/adr/0001-deterministic-cv-parser.md`). It is deterministic code, never the agent. Its expected outputs in `tests/fixtures/expected/` are the spec: when output changes, regenerate them with `uv run python tests/fixtures/update_expected.py --all`, review the diff, and raise `PARSER_VERSION` in the same commit. Fixtures are synthetic or anonymized CVs only; the repo is public.
- **Development tools** live in `src/ieakaso/devtools/` and are never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.
  - Cleaner: `uv run python -m ieakaso.devtools.cleaner clean | restore [name] | list` returns the repo to a fresh state (see `CONTEXT.md`) so init can be tested from scratch. The command always backs up to `~/.ieakaso-backups/` first, and `restore` brings the newest backup back, or the named one. Options: `--dry-run` (`clean` and `restore`: show what would happen, change nothing), `--root` (default: found from the current folder), `--backup-dir`. Called from Python, `clean()` only backs up when given a `backup_dir`. If you add user data anywhere, add it to the cleaner and `.gitignore` together; `tests/test_cleaner_drift.py` fails when they disagree.
- **Usage display:** `src/ieakaso/usage/` derives each Run's Token usage, models and Context fill from the Claude Code transcript (nothing is saved). `uv run python -m ieakaso.usage start <mode> | summary | statusline`: the router runs `start` as the Run marker and `summary` when a mode ends; the status line is `statusLine` in the tracked `.claude/settings.json`. Tests use fake transcripts only (`tests/usage_fakes.py`), never `~/.claude`. Context window sizes live in `CONTEXT_WINDOWS` in `report.py`. Background Agent runs often leave a message without its final line, so its output count is a mid-stream snapshot; such output is estimated from the visible characters, calibrated on the Session's final messages, and shown as `~X (low–high)` (`_estimate_outputs` in `transcript.py`).
- `README.md` describes the product as designed in the [diagram](`docs/flows.excalidraw`); its Roadmap section lists features beyond the diagram that are not designed yet.
- License: AGPL-3.0.

## Requirements (source: `docs/flows.excalidraw`)

- **Runtime:** runs locally, driven from a coding-assistant CLI (Claude Code, OpenCode) rather than its own UI.
- **Storage:** file-based, using Markdown files in a structured folder tree. Application status is the folder an application sits in: `Applied` → `Interviewing` → `Not selected` / `Offer`.
- **Memory:** on first run, the user provides their CV, a professional "about me", key projects, biggest achievements, and a personal SWOT. The agent should compound learnings from each application process back into memory.
- **Two agents:** an *Applicant Agent* that writes the drafts and a *Seasoned Recruiter* that reviews them. A third role, the *Job Application Assistant*, is the main conversation: it starts the two agents and passes work between them (`docs/adr/0002-job-application-assistant-in-main-conversation.md`). Role files are in `ai/agents/`; the Applicant and the Recruiter have pointers in `.claude/agents/` and `.opencode/agents/` (the same agents and targets in both, checked by `tests/test_agent_pointers_drift.py`), the Assistant never does.
- **Application flow:**
  1. The user pastes a job ad URL.
  2. The `job-analyzer` mode reads the ad and highlights the Job ad's strong and weak points.
  3. The same mode decides whether the user is a top applicant (the Verdict).
  4. Read the application form.
  5. Prepare an application report.
  6. If the form asks for a cover letter, the Job Application Assistant runs the `cover-letter` mode: the Applicant Agent drafts it and the Seasoned Recruiter gives it a Review score from 0 to 100. Below 90, the Recruiter lists what to remove, rewrite and improve and the Applicant rewrites. Each draft plus its Review is a Round. This repeats until the score is at least 90, the Recruiter declares a Plateau, or 5 Rounds have run; the best-scoring draft is kept.
  7. Suggest next steps.
- **Interview prep flow:** a second flow, not yet detailed.

## Commands

All commands go through one skill, `ai/skills/ieakaso/` (loaded through the pointer `.claude/skills/ieakaso/SKILL.md`): `/ieakaso <mode> [args]`. Each mode is a file in `ai/skills/ieakaso/modes/`. The skill description lives only in the pointer; update it there when modes change.

- **Mode entries** (see `CONTEXT.md`): each mode also has a pointer that routes through the skill as that mode: `/ieakaso:<mode>` in Claude Code and `/ieakaso-<mode>` in OpenCode. A new mode touches five places: its mode file, the mode table in `ai/skills/ieakaso/SKILL.md`, the skill description in the pointer, `.claude/skills/ieakaso/skills/<mode>/SKILL.md` (with `disable-model-invocation: true`, so Claude itself only routes through `/ieakaso`), and `.opencode/commands/ieakaso-<mode>.md`. Each mode entry's description is `Ieakaso <mode>: ` plus the table's "Does" text, and the Claude one's `argument-hint` is the table's "Arguments" (OpenCode commands have no argument hint field). `tests/test_mode_entries_drift.py` fails when they disagree.
- **Claude Code plugin:** `.claude/skills/ieakaso/.claude-plugin/plugin.json` makes that folder a project-local plugin, which is what gives the `ieakaso:` prefix. It loads only in a trusted folder and only when Claude Code starts at the repo root; `claude plugin validate .claude/skills/ieakaso` checks it.
- **OpenCode:** reads the pointer `.claude/skills/ieakaso/SKILL.md` as a skill; its `metadata: opencode/slash: "true"` is what makes `/ieakaso` a slash command there. Keep it.
- **First run:** every mode except `init` checks `db/system_status.json` first and runs `/ieakaso init` if setup is missing or incomplete. `init` is idempotent.
- **User data:** `config.yml` (candidate data, format in `config_example.yml`), `db/system_status.json` (setup state, starting point in `db/system_status_example.json`), `db/ieakaso_db.json`, and the contents of `input/` and `output/` are gitignored and stay on the user's machine. The only mandatory document is the CV in `input/documents/cv/`.

## Product guardrails

The tool drafts and the user acts. It never submits applications or sends emails, and it never fabricates CV content; it only reformulates it. Reviews only suggest changes backed by the candidate's files; anything else becomes a question for the candidate. It advises against applying when the score is below 4.0/5, but the user can override that.

## Agent Skills Settings

- When the human invokes `/grill-me` or `/grill-with-docs`, use the Claude Opus model. This phase requires deep reasoning to map out the complete design tree, capture hidden requirements, and write the specification.
- When the human invokes `/implement`, use the Claude Sonnet model. This phase relies strictly on the pre-generated static markdown context (`docs/agents/`) to build code following test-driven development (TDD), optimizing for fast context-window compliance.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `MarceloFossRJ/ieakaso`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
