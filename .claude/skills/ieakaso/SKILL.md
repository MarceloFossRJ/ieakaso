---
name: ieakaso
description: Ieakaso job-search assistant. Routes `/ieakaso <mode> [args]` to a mode. Use for any Ieakaso command — setting up the candidate profile and checking its documents against the CV (`init`), turning the CV, the LinkedIn profile and reference letters into Markdown in `input/` (`cv-parser`), scoring the CV against a job ad and giving a verdict (`job-analyzer`), drafting and reviewing a cover letter for a job ad (`cover-letter`), opening the applications tracker to view and edit the candidate's applications (`viewer`) — or when the user pastes a job ad URL or job ad text or asks to start a job search.
argument-hint: <mode> [args]
metadata:
  opencode/slash: "true"
---

Read `ai/skills/ieakaso/SKILL.md` (relative to the repository root) and follow it, passing on the arguments: $ARGUMENTS
