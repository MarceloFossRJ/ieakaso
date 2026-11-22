# AGENTS.md

This file provides guidance to AI coding agents in this repository.

## Project state

Ieakaso is mostly at the design stage: the product runs through the `/ieakaso` skill (see Commands). `src/ieakaso/` holds the deterministic code the modes call; agents never do its work by hand. Each CLI's contract (flags, output lines, exit codes) is its `<package>/cli.py` docstring (a dev tool's: its module docstring) and `--help`; the coding standards are in `CODING_STANDARDS.md`.

- **Toolchain:** Python 3.14 managed by `uv`. Dependencies live in `pyproject.toml`; add them with `uv add` (or `uv add --dev` for development-only ones).
- **Tests:** `uv run pytest` (pytest, in `tests/`). CI (`.github/workflows/ci.yml`) runs `ruff format --check`, `ruff check` and pytest on every push and PR to `main`. Tests run on temporary fake repos; never let a test write to the real `input/`, `output/`, `config.yml`, `db/`, or `~/.config/ieakaso/`.
- **CV parser** (`cv_parser/`): the Source CV to the Parsed CV `input/parsed-documents/cv.md`, the LinkedIn profile's Parsed document, and CV versions (`versions.py`; ADRs 0001, 0004, 0005, 0006). The candidate writes `input/candidate/`, Ieakaso writes `input/parsed-documents/`; `layout.py` holds the paths. Its expected outputs in `tests/fixtures/expected/` are the spec: when output changes, run `uv run python tests/fixtures/update_expected.py --all`, review the diff, and raise `PARSER_VERSION` in the same commit. Fixtures are synthetic or anonymized CVs only: the repo is public.
- **Job ad fetcher** (`job_ad/`): reads a Job ad from a URL when WebFetch can't, with one plain GET; job-analyzer asks the candidate before using it. Regenerate its expected outputs with `uv run python tests/fixtures/job_ads/update_expected.py --all` and review the diff; Sample pages (`tests/fixtures/job_ads/samples/`, real pages, anonymized) have hand-written expected outputs that are never regenerated. Agents never fetch Job ads with `curl` or `wget`.
- **Tracker** (`tracker/`): the only reader and writer of `db/ieakaso_db.json` (model in `docs/database.md`, kept in sync with its schema); agents never edit the JSON. A change to the record's keys raises `SCHEMA_VERSION` (`schema.py`), adds an upgrade to `_migrate` in `store.py`, and is listed under Schema versions in `docs/database.md`. `db/ieakaso_db_example.json` is a valid example, checked by the tests.
- **Cover letter assembler** (`cover_letter/`): builds the Cover letter and its review log from the Round files, so no draft or Review text enters the main conversation.
- **Evidence bank stamp** (`evidence_bank/`): writes and checks the Evidence bank's Sources section, so the agents work from the bank, not the Personal knowledge base (ADR 0008).
- **Letter context** (`letter_context/`): the parts of the Job analysis and the Company research the letter agents read (ADR 0011). Its parsing follows the templates in `ai/skills/ieakaso/modes/job-analyzer.md`: change both together.
- **Candidate answer** (`candidate_answer/`): appends the candidate's own answer to one of their memory files, word for word, with their permission (ADR 0010).
- **Viewer** (`viewer/`): the Textual app over the tracker, `ieakaso-view` from any terminal (ADR 0013). It edits records, never creates or deletes them, and writes only through the tracker. Tests drive it with Textual's pilot on temp dbs.
- **Remembered repo** (`repo/`): finds the repo (`find_root`, `locate`) and remembers it for `ieakaso-view` in `~/.config/ieakaso/repo.toml`; init runs `remember` on every run.
- **Development tools** (`devtools/`), never exposed to the candidate: the cleaner returns the repo to a fresh state or the Set-up state, backing up first; the estimate backtest checks the usage display's output estimate. If you add user data anywhere, add it to the cleaner and `.gitignore` together; `tests/test_cleaner_drift.py` fails when they disagree.
- **Usage display** (`usage/`): each Run's Token usage, models and Context fill, from the Claude Code transcript; the router runs `start` and `summary`, and the status line is `statusLine` in `.claude/settings.json`. Tests use fake transcripts (`tests/usage_fakes.py`), never `~/.claude`.
- `README.md` describes the product as designed in the [diagram](`docs/flows.excalidraw`); its Roadmap section lists features beyond the diagram that are not designed yet.
- License: AGPL-3.0.

## Requirements (source: `docs/flows.excalidraw`)

- **Runtime:** runs locally, driven from a coding-assistant CLI (Claude Code, OpenCode) rather than its own UI.
- **Storage:** file-based: Markdown files in a structured folder tree, and the applications tracker `db/ieakaso_db.json`. Each Application's files live in `output/applications/<application-id>/`, a folder that never moves; its status is a field of its record in the tracker (`docs/adr/0003-application-status-in-the-db.md`).
- **Memory:** on first run, the user provides their CV, a professional "about me", key projects, and biggest achievements. The agent should compound learnings from each application process back into memory.
- **Agents:** an *Applicant Agent* that writes the drafts and a *Seasoned Recruiter* that reviews them. A third role, the *Job Application Assistant*, is the main conversation: it starts the two agents and passes work between them (`docs/adr/0002-job-application-assistant-in-main-conversation.md`). A *Company Researcher* (Sonnet, web tools only) researches one topic of a Company research; the job-analyzer mode starts four in parallel and assembles them, and the recruiter-screening mode starts two more topics (Interviewer, Compensation) for the Screening prep. Role files are in `ai/agents/`; the Applicant, the Recruiter and the Company Researcher have pointers in `.claude/agents/` and `.opencode/agents/` (the same agents and targets in both, checked by `tests/test_agent_pointers_drift.py`, which also checks that the usage display counts exactly those agents, `IEAKASO_AGENTS`), the Assistant never does. The Applicant drafts by, and the Recruiter reviews against, the Cover letter guidelines in `ai/skills/ieakaso/general-knowledge-base/` (the General knowledge base; the tech guide next to them is for maintainers, not agents). `tests/test_cover_letter_paths_drift.py` fails when those three files name a tracked file that doesn't exist.
- **Application flow:**
  1. The user pastes a job ad URL.
  2. The `job-analyzer` mode reads the ad and highlights the Job ad's strong and weak points. It is the only reader of the whole Personal knowledge base: after the Job analysis it writes the Application's Evidence bank, the facts the agents write and review from (`docs/adr/0008-evidence-bank.md`).
  3. The same mode decides whether the user is a top applicant (the Verdict), then writes a Company research on the company behind the ad (automatic for Top applicant and Apply, offered for Stretch and Don't apply; reused when less than 30 days old). It never changes the Verdict.
  4. Read the application form.
  5. Prepare an application report.
  6. If the form asks for a cover letter, the `cover-letter` mode writes it: the Seasoned Recruiter plans the letter, the Applicant Agent drafts it from the Evidence bank and the Letter context, and the Recruiter scores each draft, for up to 3 Rounds or until 90/100 (`ai/skills/ieakaso/modes/cover-letter.md`, ADR 0012).
  7. Suggest next steps.
- **Interview prep flow:** the `recruiter-screening` mode writes the Screening prep for a recruiter screening itself, in one pass with no Review loop, from the Evidence bank, the Job analysis and the Company research (`ai/skills/ieakaso/modes/recruiter-screening.md`). Later stages are not designed yet.

## Commands

All commands go through one skill, `ai/skills/ieakaso/` (loaded through the pointer `.claude/skills/ieakaso/SKILL.md`): `/ieakaso <mode> [args]`. Each mode is a file in `ai/skills/ieakaso/modes/`. The skill description lives only in the pointer; update it there when modes change.

- **Mode entries** (see `CONTEXT.md`): each mode also has a pointer that routes through the skill as that mode: `/ieakaso:<mode>` in Claude Code and `/ieakaso-<mode>` in OpenCode. A new mode touches five places: its mode file, the mode table in `ai/skills/ieakaso/SKILL.md`, the skill description in the pointer, `.claude/skills/ieakaso/skills/<mode>/SKILL.md` (with `disable-model-invocation: true`, so Claude itself only routes through `/ieakaso`), and `.opencode/commands/ieakaso-<mode>.md`. Each mode entry's description is `Ieakaso <mode>: ` plus the table's "Does" text, and the Claude one's `argument-hint` is the table's "Arguments" (OpenCode commands have no argument hint field). `tests/test_mode_entries_drift.py` fails when they disagree.
- **Commands in the docs:** `tests/test_doc_commands_drift.py` fails when a doc (README, AGENTS, CONTEXT, `docs/`, `ai/`, `.claude/`, `.opencode/`) names a `uv run <name>` that isn't a script or dependency in `pyproject.toml`, or a `python -m ieakaso.<module>` that can't run. Rename a command and its docs together.
- **CLI exit codes:** `tests/test_cli_docstrings_drift.py` fails when a module under `src/ieakaso/` with a top-level `main` has no `Exit codes` sentence in its docstring, or doesn't name there a code `main` returns.
- **Claude Code plugin:** `.claude/skills/ieakaso/.claude-plugin/plugin.json` makes that folder a project-local plugin, which is what gives the `ieakaso:` prefix. It loads only in a trusted folder and only when Claude Code starts at the repo root; `claude plugin validate .claude/skills/ieakaso` checks it.
- **OpenCode:** reads the pointer `.claude/skills/ieakaso/SKILL.md` as a skill; its `metadata: opencode/slash: "true"` is what makes `/ieakaso` a slash command there. Keep it.
- **First run:** every mode except `init` checks `db/system_status.json` first and runs `/ieakaso init` if setup is missing or incomplete. `init` is idempotent.
- **User data:** `config.yml` (candidate data, format in `config_example.yml`), `db/system_status.json` (setup state, starting point in `db/system_status_example.json`), `db/ieakaso_db.json` (the applications tracker; model in `docs/database.md`), and the contents of `input/` and `output/` are gitignored and stay on the user's machine. Outside the repo, `~/.config/ieakaso/repo.toml` holds only the repo's path for `ieakaso-view` (ADR 0013); it is not candidate data, and the cleaner leaves it alone. Inside `input/`, the candidate writes `input/candidate/` (Ieakaso only appends their own answers to the memory files, with permission each time: ADR 0010) (the Source documents in `documents/`, and `presentation.md`, `professional-experience-extended.md`, `professional-self-reflection.md`, `writing-style.md` and the optional `deliberate-differences.md`, see Deliberate difference in `CONTEXT.md`) and Ieakaso writes `input/parsed-documents/`, which the candidate never edits. The only mandatory document is the CV: saved in the inbox `input/candidate/documents/cv/`, it becomes a CV version in its own folder there.

## Product guardrails

The tool drafts and the user acts. It never submits applications or sends emails, and it never adds facts about the candidate that the Personal knowledge base doesn't hold; it only reformulates them. Reviews only suggest changes backed by the Evidence bank, which quotes the Personal knowledge base; anything else becomes a question for the candidate. The Applicant Agent and the Seasoned Recruiter never read the Personal knowledge base beyond the Evidence bank, the Parsed CV (the Recruiter), `config.yml` and `writing-style.md` (both: the Recruiter writes replacement text in the candidate's voice, and takes no facts from it); `tests/test_evidence_bank_drift.py` checks their INPUTS. A letter's claims about the company come only from the Job ad and the Company research's public, fetched facts, which reach the agents through the Letter context (never its red flags or employee reviews), and the Review checks them like claims about the candidate. It advises against applying when the score is below 4.0/5, but the user can override that. Research on an Interviewer covers only their public, professional facts; their LinkedIn page is never fetched.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `MarceloFossRJ/ieakaso`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
