# CV Parser

`/ieakaso cv-parser`: writes the Parsed CV (`input/cv.md`) from the Source CV that init recorded in `documents.cv.path`. Also runs at the end of init's document step and from the setup check.

The parsing is done by code, never by you: same Source CV, same bytes out (see `docs/adr/0001-deterministic-cv-parser.md`). Your job is to run the command and relay its result. Leave `input/cv.md` to the command; to change it, the candidate changes the Source CV.

## Step 1: Run the parser

```
uv run python -m ieakaso.cv_parser
```

## Step 2: Act on the exit code

| Exit | Meaning | What you do |
|---|---|---|
| 0 | Written, or already up to date | Relay the one-line result. Done. |
| 1 | The Source CV can't be parsed | Show the candidate the message from stderr as it is: it says what failed and where to put a corrected file. Stop; the mode that called this one does not run. |
| 2 | No main CV recorded, or the file is gone | Run `/ieakaso init`, then this mode again. |
| 3 | `input/cv.md` was edited by hand | Show the candidate the diff from stdout and ask whether to replace the file. On yes, run the command again with `--force`. On no, stop, and tell them to put their changes into the Source CV so the next parse keeps them. |

The step is done when the command has exited 0, or the candidate has the exit 1 message, or the candidate declined the exit 3 overwrite.
