# AGENTS.md

This file provides guidance to AI coding agents in this repository.

## Project state

Ieakaso is at the design stage: there is no source code, `pyproject.toml`, or test suite yet. 
There are no build, lint, or test commands to run. 
When the first code lands, replace this section with the real commands.

- The intended toolchain is Python 3.14 managed by `uv` (an untracked `.venv` exists, created by uv). Its installed packages are not declared anywhere, so treat them as leftovers, not as dependencies the project has chosen.
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

## Product guardrails

The tool drafts and the user acts. It never submits applications or sends emails, and it never fabricates CV content; it only reformulates it. It advises against applying when the score is below 4.0/5, but the user can override that.
