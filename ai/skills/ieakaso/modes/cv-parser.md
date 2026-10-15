# CV Parser

`/ieakaso cv-parser`: writes the Parsed CV (`input/cv.md`) from the Source CV that init recorded in `documents.cv.path`, and the Parsed documents of the LinkedIn profile (`input/linkedin.md`) and of each reference letter (`input/reference-letters/<file name>.md`) that init recorded (terms in `CONTEXT.md`). Also runs at the end of init's document step and from the setup check.

The parsing is done by code, never by you: same Source document, same bytes out (see `docs/adr/0001-deterministic-cv-parser.md` and `docs/adr/0004-parsed-documents.md`). Your job is to run the command and relay its result. Leave the Parsed documents to the command; to change one, the candidate changes its Source document.

## Step 1: Run the parser

```
uv run python -m ieakaso.cv_parser
```

## Step 2: Act on the exit code

| Exit | Meaning | What you do |
|---|---|---|
| 0 | Written, or already up to date | Relay the one-line result. Done. |
| 1 | The Source CV can't be parsed | Show the candidate the message from stderr as it is: it says what failed and where to put a corrected file. Stop; the mode that called this one does not run. |
| 2 | No Source CV recorded, or the file is gone | Run `/ieakaso init`, then this mode again. |
| 3 | `input/cv.md` was edited by hand | Show the candidate the diff from stdout and ask whether to replace the file. On yes, run the command again with `--force`. On no, stop, and tell them to put their changes into the Source CV so the next parse keeps them. |

The exit code is about the CV alone. The LinkedIn profile and reference letters never stop the step; whatever the exit code, also act on stdout's lines about them:

- `Wrote …` or `Removed …`: relay them in one line.
- `Warning: … can't be read`: show it to the candidate as it is. Ieakaso carries on without that document; it is reported once, until the file changes.
- `Warning: … was changed by hand`: show it and ask whether to replace (or, when its source is gone, delete) the file. On yes, run the command again with `--force`. On no, carry on.

The step is done when the command has exited 0, or the candidate has the exit 1 message, or the candidate declined the exit 3 overwrite.
