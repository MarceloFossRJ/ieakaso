# AGENTS.md

This file provides guidance to AI coding agents in this repository.

## Project state

Ieakaso is mostly at the design stage: the product runs through the `/ieakaso` skill (see Commands). The Python package in `src/ieakaso/` holds the CV parser, the Job ad fetcher, the tracker, the viewer, the usage display and the development tools.

- **Toolchain:** Python 3.14 managed by `uv`. Dependencies live in `pyproject.toml`; add them with `uv add` (or `uv add --dev` for development-only ones).
- **Tests:** `uv run pytest` (pytest, in `tests/`). Tests run on temporary fake repos; never let a test write to the real `input/`, `output/`, `config.yml`, or `db/`.
- **CV parser:** `src/ieakaso/cv_parser/` turns the Source CV into the Parsed CV `input/cv.md` (terms in `CONTEXT.md`, decisions in `docs/adr/0001-deterministic-cv-parser.md`). It is deterministic code, never the agent. Its expected outputs in `tests/fixtures/expected/` are the spec: when output changes, regenerate them with `uv run python tests/fixtures/update_expected.py --all`, review the diff, and raise `PARSER_VERSION` in the same commit. Fixtures are synthetic or anonymized CVs only; the repo is public.
- **Job ad fetcher:** `src/ieakaso/job_ad/` reads a Job ad from a URL when WebFetch can't: `uv run python -m ieakaso.job_ad fetch <url>` writes the ad as Markdown to stdout, first line `Source: structured data` (a schema.org `JobPosting` in ld+json), `Source: structured data + page text` (the same plus a `## More from the page` section with the page's other readable text) or `Source: page text`, then `Page title: <title>` when the page has one. Exit codes: 0 ad written, 1 fetch failed, 2 login wall or closed ad, 3 no ad content; the job-analyzer mode acts on them, and asks the candidate before using it. It is deterministic code like the CV parser: one GET, no JavaScript, no login, no cookies, one retry, never candidate data. Its expected outputs in `tests/fixtures/job_ads/expected/` are the spec: when output changes, regenerate them with `uv run python tests/fixtures/job_ads/update_expected.py --all` (no network; without `--all` it writes only missing ones), and review the diff. Fixtures are synthetic pages, or Sample pages in `tests/fixtures/job_ads/samples/`: real Job ad pages saved from the web and anonymized (public repo), whose expected outputs in `samples/expected/` are written by hand, hold what the agents need from the ad, and are never regenerated; `tests/test_job_ad_samples.py` checks that every expected line appears in the fetcher's output in order (other page text around it is fine), ignoring Markdown syntax, and a Sample the fetcher can't match yet is a strict xfail. Tests inject the HTTP call, never touching the network. Agents never fetch Job ads with `curl` or `wget`.
- **Tracker:** `src/ieakaso/tracker/` is the only reader and writer of `db/ieakaso_db.json` (model in `docs/database.md`, which is kept in sync with its schema). Deterministic code like the CV parser; agents never edit the JSON. It validates records, writes atomically (temp file + rename), creates the file on its first write, refuses to save over a file it couldn't read as valid JSON, and raises `ConflictError` when the file changed on disk since it was read. `uv run python -m ieakaso.tracker upsert [--json <payload>]` (payload on stdin otherwise) creates or updates the record of a Job analysis, following the re-run rule in `docs/database.md`, and prints `created <id>` or `updated <id>`; `set-cover-letter <id> <path>` sets the Cover letter path. Exit codes: 0 done, 1 invalid payload or path, 2 the db is not valid JSON (left alone), 3 the file changed while the command ran, 4 no such Application. The job-analyzer and cover-letter modes call it; `db/ieakaso_db_example.json` is a valid example, checked by the tests. Tests inject the repo root and `today`, and use temp dbs, never the real `db/`.
- **Viewer:** `src/ieakaso/viewer/` is a Textual app (`uv run ieakaso-viewer`, opened by the `viewer` mode in a new terminal window) over the tracker: table, detail screen with immediate saves, the No answer suggestions, opening the Job ad, Job analysis and Cover letter. It edits records and never creates or deletes them, and every write goes through the tracker module. Tests drive it with Textual's pilot (`pytest-asyncio`, auto mode) on temp dbs, with the document opener injected.
- **Development tools** live in `src/ieakaso/devtools/` and are never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.
  - Cleaner: `uv run python -m ieakaso.devtools.cleaner clean [--applications]` returns the repo to a fresh state, or with `--applications` to the Set-up state (terms in `CONTEXT.md`; `--applications` deletes only the tracker db, its temp files and `output/applications/`), so init, or a mode, can be tested from scratch. It always backs up what it deletes to `~/.ieakaso-backups/` first, in a timestamped folder; there is no restore, copy files back by hand. Options: `--dry-run` (show what would happen, change nothing), `--root` (default: found from the current folder), `--backup-dir`. Called from Python, `clean()` only backs up when given a `backup_dir`. If you add user data anywhere, add it to the cleaner and `.gitignore` together; `tests/test_cleaner_drift.py` fails when they disagree.
  - Estimate backtest: `uv run python -m ieakaso.devtools.estimate_backtest [session-id | transcript.jsonl ...] [--all]` checks the usage display's output estimate on messages whose output count is known: each final message is left out, estimated from the Session's others, and compared. About 80% in range and a small median error mean the estimate is sound; if not, remove the estimate rather than tune it to one Session.
- **Usage display:** `src/ieakaso/usage/` derives each Run's Token usage, models and Context fill from the Claude Code transcript (nothing is saved). `uv run python -m ieakaso.usage start <mode> | summary | statusline`: the router runs `start` as the Run marker and `summary` when a mode ends; the status line is `statusLine` in the tracked `.claude/settings.json`. Tests use fake transcripts only (`tests/usage_fakes.py`), never `~/.claude`. Context window sizes live in `CONTEXT_WINDOWS` in `report.py`. Background Agent runs often leave a message without its final line, so its output count is a mid-stream snapshot; such output is estimated from the visible characters, calibrated on the Session's final messages, and shown as `~X (low–high)` (`_estimate_outputs` in `transcript.py`).
- `README.md` describes the product as designed in the [diagram](`docs/flows.excalidraw`); its Roadmap section lists features beyond the diagram that are not designed yet.
- License: AGPL-3.0.

## Requirements (source: `docs/flows.excalidraw`)

- **Runtime:** runs locally, driven from a coding-assistant CLI (Claude Code, OpenCode) rather than its own UI.
- **Storage:** file-based: Markdown files in a structured folder tree, and the applications tracker `db/ieakaso_db.json`. Each Application's files live in `output/applications/<application-id>/`, a folder that never moves; its status is a field of its record in the tracker (`docs/adr/0003-application-status-in-the-db.md`).
- **Memory:** on first run, the user provides their CV, a professional "about me", key projects, biggest achievements, and a personal SWOT. The agent should compound learnings from each application process back into memory.
- **Agents:** an *Applicant Agent* that writes the drafts and a *Seasoned Recruiter* that reviews them. A third role, the *Job Application Assistant*, is the main conversation: it starts the two agents and passes work between them (`docs/adr/0002-job-application-assistant-in-main-conversation.md`). A *Company Researcher* (Sonnet, web tools only) researches one topic of a Company research; the job-analyzer mode starts four in parallel and assembles them. Role files are in `ai/agents/`; the Applicant, the Recruiter and the Company Researcher have pointers in `.claude/agents/` and `.opencode/agents/` (the same agents and targets in both, checked by `tests/test_agent_pointers_drift.py`, which also checks that the usage display counts exactly those agents, `IEAKASO_AGENTS`), the Assistant never does.
- **Application flow:**
  1. The user pastes a job ad URL.
  2. The `job-analyzer` mode reads the ad and highlights the Job ad's strong and weak points.
  3. The same mode decides whether the user is a top applicant (the Verdict), then writes a Company research on the company behind the ad (automatic for Top applicant and Apply, offered for Stretch and Don't apply; reused when less than 30 days old). It never changes the Verdict.
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
- **User data:** `config.yml` (candidate data, format in `config_example.yml`), `db/system_status.json` (setup state, starting point in `db/system_status_example.json`), `db/ieakaso_db.json` (the applications tracker; model in `docs/database.md`), and the contents of `input/` and `output/` are gitignored and stay on the user's machine. The only mandatory document is the CV in `input/documents/cv/`.

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
