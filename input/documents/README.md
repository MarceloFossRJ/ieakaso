# documents/ — your source documents

Put your documents here, then run `/ieakaso init`. It checks what is here, asks you to confirm the details it reads from them, and saves them in `config.yml`. Run it again whenever you add or change a document.

| Folder | What goes here | |
|---|---|---|
| `cv/` | Your CV (`.pdf`, `.docx`, `.md`, `.txt`, or `.tex`). With several (e.g. one per language), init asks which is the main one. | **Required** |
| `linkedin/` | Your LinkedIn profile as PDF: profile → **Resources** → **Save to PDF** | Strongly recommended |
| `reference_letters/` | Reference letters from former employers or colleagues | Suggested |

Init creates these folders if they are missing.

Everything in `input/` is gitignored and stays on your machine, except this README. Ieakaso reads your documents; it never changes, moves, or deletes them.
