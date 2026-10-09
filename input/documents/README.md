# documents/ — profile intake sources

Incöude here documents you have, then ask your agent to run the
`intake` mode (see `modes/intake.md`). It extracts text locally, proposes
source-annotated additions to `config/profile.yml` / `../cv.md` /
`modes/_profile.md`, and writes nothing without your explicit confirmation.

| Folder | What goes here |
|---|---|
| `cv/` | Master CV (PDF, `.md`, `.tex`, or `.txt`) |
| `linkedin/` | LinkedIn "Save to PDF" export |
| `peerlist/` | Peerlist "Save to PDF" export |
| `wellfound/` | Wellfound "Save to PDF" export |
| `xing/` | Xing "Save to PDF" export |
| `diplomas/` | Transcripts, degree certificates |
| `reference_letters/` | Reference letters |

Your source documents here are **user layer**: gitignored, never touched by
the updater, never leaving your machine. `../../README.md` and `.gitkeep` are the
system-owned scaffold for the folder — they are tracked, and the updater does
maintain them.
Extraction is fully local.
Re-runs are idempotent.