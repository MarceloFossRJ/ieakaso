# documents/ — your source documents

Put your documents here, then run `/ieakaso init`. It checks what is here, asks you to confirm the details it reads from them, and saves them in `config.yml`. Run it again whenever you add or change a document.

| Folder | What goes here | |
|---|---|---|
| `cv/` | Your CV (`.pdf`, `.docx`, `.md`, `.txt`, or `.tex`). Save a new CV here whenever you have one; Ieakaso moves it into its own `cv_<date>/` folder and keeps every version. | **Required** |
| `linkedin/` | Your LinkedIn profile as PDF: profile → **Resources** → **Save to PDF** | Strongly recommended |
| `reference_letters/` | Reference letters from former employers or colleagues | Suggested |

Init creates these folders if they are missing.

**Only facts.** Everything in `input/` and `config.yml` is your Personal knowledge base: Ieakaso uses all of it as fact about you when it writes for you, and never checks it. Put in only what is true. Reference letters are background: Ieakaso may use their facts as your own, but never quotes or attributes them.

Ieakaso turns your CV, LinkedIn PDF and reference letters into Parsed documents (Markdown) in `input/parsed-documents/` (`cv.md`, `linkedin.md`, `reference-letters/`, and a frozen copy per CV version in `cv-versions/`), word for word. To change one, change the document and run `/ieakaso cv-parser`; never edit them. Other folders here are not read.

Everything in `input/` is gitignored and stays on your machine, except this README. Ieakaso reads your documents; it never changes or deletes them. The one thing it moves is a CV you save in `cv/`: into its own `cv_<date>/` folder there, so every CV version stays findable; its Parsed CV goes to `input/parsed-documents/cv-versions/`.
