# Ieakaso

Route `/ieakaso <mode> [args]` to the matching mode file, after the setup check.

Loaded through the pointer `.claude/skills/ieakaso/SKILL.md`, which holds the skill's name and description. All paths here and in the mode files are relative to the repository root.

Each mode also has a mode entry, so the candidate can pick it from the `/` menu instead of typing it: `/ieakaso:<mode>` in Claude Code (`.claude/skills/ieakaso/skills/<mode>/SKILL.md`) and `/ieakaso-<mode>` in OpenCode (`.opencode/commands/ieakaso-<mode>.md`). A mode entry names the mode for you; all the arguments it passes on belong to that mode.

## Modes

| Mode | Arguments | File | Does |
|---|---|---|---|
| `init` | — | `ai/skills/ieakaso/modes/init.md` | Checks the candidate's documents and collects `config.yml` |
| `cv-parser` | — | `ai/skills/ieakaso/modes/cv-parser.md` | Writes `input/cv.md` from the candidate's CV, word for word |
| `job-analyzer` | `<job-url or job-ad text>` | `ai/skills/ieakaso/modes/job-analyzer.md` | Scores the CV against one job ad and gives a verdict |

If the mode is missing, ask the user which mode to run, with a choice question listing the modes in the table if your tool has one; otherwise show this table and stop. If the mode is not in the table, show this table and stop.

If the user asks for something a mode covers without naming it (e.g. pastes a job ad URL), pick that mode and say which one you are running.

## Run start

The very first step of every Run, before the setup check, however the mode was chosen (`/ieakaso <mode>`, a mode entry, or you picking it for pasted text), is to run:

```
uv run python -m ieakaso.usage start <mode>
```

That command is how the Run is counted: it only prints a line, so just continue. Do it once per Run. The setup check's init and cv-parser runs are part of the Run that triggered them and do not start another one.

## Run summary

When the mode's work ends, including when it stops early (setup incomplete, cv-parser failure, no job ad text), run `uv run python -m ieakaso.usage summary` and show its output verbatim to the candidate, as the last thing you print. If it prints a notice instead, show the notice. Do this once per mode, not for the init or cv-parser the setup check ran.

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
