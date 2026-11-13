# CV Parser

`/ieakaso cv-parser`: captures the CV versions waiting in the inbox `input/documents/cv/`, writes the Parsed CV (`input/cv.md`) from the current CV version, and writes the Parsed documents of the LinkedIn profile (`input/linkedin.md`) and of each reference letter (`input/reference-letters/<file name>.md`) that init recorded (terms in `CONTEXT.md`). Also runs at the end of init's document step and from the setup check.

The candidate supplies a new CV by saving the file in `input/documents/cv/`, in any format the parser reads. The parser moves it (it does not copy it) into its own folder `input/documents/cv/cv_<yyyy-mm-dd>/` next to a frozen copy of its Parsed CV, and records the CV version in the tracker (`docs/adr/0005-cv-versions.md`, `docs/database.md`). A file whose content matches a version is not captured again, whatever its name. `input/cv.md` always holds the current version, the most recently captured one that is not a Tailored CV. Versions are never changed or deleted.

The parsing is done by code, never by you: same Source document, same bytes out (see `docs/adr/0001-deterministic-cv-parser.md` and `docs/adr/0004-parsed-documents.md`). Your job is to run the command, ask the candidate what the code can't decide, and relay the result. Leave the Parsed documents to the command; to change one, the candidate changes its Source document.

## Step 1: Run the parser

```
uv run python -m ieakaso.cv_parser
```

## Step 2: Act on the exit code

| Exit | Meaning | What you do |
|---|---|---|
| 0 | Written, or already up to date | Relay the result in a line or two (a `Captured …` line means a new CV version). Done. |
| 1 | A new CV file can't be parsed, or the current Source CV can't | Show the candidate the message from stderr as it is: it says what failed and where to put a corrected file. Stop; the mode that called this one does not run. |
| 2 | No CV, or setup is missing | Ask the candidate to save their CV in `input/documents/cv/` and run `/ieakaso init`, then this mode again. |
| 3 | `input/cv.md` was edited by hand | Show the candidate the diff from stdout and ask whether to replace the file. On yes, run the command again with `--force`. On no, stop, and tell them to put their changes into the Source CV so the next parse keeps them. |
| 4 | New CV files wait for the candidate's choice | See Step 3. This is not a failure: `input/cv.md` was still written from the current version, so the calling mode carries on once you have asked. |
| 5 | The tracker db can't be used, or changed while capturing | Show the message from stderr. Nothing was moved. Stop; on "changed", run the command again once. |
| 6 | A flag named a file that is not waiting in the inbox, or an unknown Application | Show the message from stderr and ask again, or stop. |

The exit code is about the CV alone. The LinkedIn profile and reference letters never stop the step; whatever the exit code, also act on stdout's lines:

- `Captured …`: relay it. It names the new version's ID and label (the label is the file name without its extension; the candidate can change it in the viewer, key `v`).
- `Duplicate: <path> has the same content as CV version …`: relay it in one line. The file stays where it is; the candidate can delete it.
- `Warning: <folder>/ was not created by Ieakaso …`: relay it in one line. The parser ignores that folder; nothing else is done about it. It warns once per folder (recorded in `documents.cv.ignored_folders`), not on every run.
- `Wrote …` or `Removed …`: relay them in one line.
- `Warning: … can't be read`: show it to the candidate as it is. Ieakaso carries on without that document; it is reported once, until the file changes.
- `Warning: … was changed by hand`: show it and ask whether to replace (or, when its source is gone, delete) the file. On yes, run the command again with `--force`. On no, carry on.

## Step 3: Exit 4, a new CV file

Stdout has one line `New CV file: <path>` per file whose content is no CV version yet. The parser decides nothing about them, not even the very first CV (only the migration below skips the question). Ask in chat, and run the command again with the flags that follow the answer. A file name from the line is enough for FILE.

- **One new file.** Ask whether it is
  1. their **new main CV**: run with `--main <FILE>`;
  2. a **Tailored CV for one Application** (not offered while no CV version exists yet, the first CV is always the main one or not a CV): list the Applications with `uv run python -m ieakaso.tracker applications` (tab-separated: ID, status, company, position, CV version), ask which one, and run with `--tailored <FILE> --for <Application ID>`. A Tailored CV belongs to that Application only and never becomes the current version. With no Applications tracked, say so: there is none to tailor for;
  3. **not a CV, leave it**: run nothing. The file stays in the inbox, nothing is captured, and you remind the candidate in one line that it is still there. The parser reports it on every run, so they will be reminded again; tell them they can move it out of `input/documents/cv/`.
- **Several new files.** Ask which one becomes the new main CV (or none of them), and run with `--main <FILE>`. Do not ask about the others in this run: they stay in the inbox untouched, and each is asked about on a later run, one at a time.

Ask once per file per Run. After your run with the flags the command can exit 4 again for files you did not (or could not) decide: that is expected, tell the candidate those files are still waiting, and carry on. With no CV version yet the question is only "is this your main CV, or not a CV?" (several files: which one is the main CV). If no CV version exists yet and the candidate captures none, stop: the calling mode does not run.

A new main CV replaces the Parsed CV `input/cv.md`: when it was edited by hand the exit is 3 (Step 2) after the version is captured.

Never move, copy, rename or delete a CV file yourself, and never edit `db/ieakaso_db.json`: the parser and the tracker do it.

The step is done when the command has exited 0, or exited 4 and the candidate has been asked, or the candidate has the exit 1 message, or the candidate declined the exit 3 overwrite.

## Migration

The first run after CV versions landed finds the Source CV lying directly in `input/documents/cv/` (recorded in `documents.cv.path` and parsed before). The parser captures it as the first version, `cv_<date of documents.cv.parsed.parsed_at>`, without asking, and gives it to every Application past Lead (`applied_on` set); Leads stay empty. Relay its `Captured …` line. Other files in the inbox are asked about as in Step 3.

## Raising `PARSER_VERSION`

A new parser version is not a new CV version. The command regenerates `input/cv.md` and leaves each version's frozen Parsed CV as it was.
