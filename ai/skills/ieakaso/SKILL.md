# Ieakaso

Route `/ieakaso <mode> [args]` to the matching mode file, after the setup check.

Loaded through the pointer `.claude/skills/ieakaso/SKILL.md`, which holds the skill's name and description. All paths here and in the mode files are relative to the repository root.

## Modes

| Mode | Arguments | File | Does |
|---|---|---|---|
| `init` | — | `ai/skills/ieakaso/modes/init.md` | Checks the candidate's documents and collects `config.yml` |
| `cv-parser` | — | `ai/skills/ieakaso/modes/cv-parser.md` | Writes `input/cv.md` from the candidate's CV, word for word |
| `job-analyzer` | `<job-url>` | `ai/skills/ieakaso/modes/job-analyzer.md` | Scores the CV against one job ad, 0-100 |

If the mode is missing or not in the table, show this table and stop.

If the user asks for something a mode covers without naming it (e.g. pastes a job ad URL), pick that mode and say which one you are running.

## Setup check

Run this before every mode except `init`:

1. Read `db/system_status.json`. If it does not exist or is not valid JSON, copy `db/system_status_example.json` to `db/system_status.json` first.
2. Run `ai/skills/ieakaso/modes/init.md` first if any of these is true:
   - `init.status` is not `"completed"`
   - `config.yml` does not exist, or a mandatory field (listed in `ai/skills/ieakaso/modes/init.md`) is empty
   - the file at `documents.cv.path` no longer exists
3. Unless the mode is `cv-parser` itself, run `ai/skills/ieakaso/modes/cv-parser.md`. It is quick when `input/cv.md` is already up to date. If it ends without exit 0, stop: the mode the user asked for does not run on a missing or out-of-date Parsed CV.
4. When init and the parser finish, continue with the mode the user asked for.

This check never blocks on, or reminds about, the LinkedIn PDF or reference letters. Only `/ieakaso init` does that.

Then read the mode file and follow it.
