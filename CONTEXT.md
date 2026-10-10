# Ieakaso

A local job-search assistant that drafts applications for a candidate; the candidate acts on them.

## Language

**User data**:
The candidate's own files, which are gitignored and never leave their machine: `config.yml`, `db/system_status.json`, `db/ieakaso_db.json`, and everything in `input/` and `output/` except the tracked placeholders (`.gitkeep` files and `input/documents/README.md`).
_Avoid_: personal data, private files

**Fresh state**:
The repo with no user data, exactly as after a clone and before the first `/ieakaso init`. The development cleaner (`ieakaso.devtools.cleaner`) returns a repo to it.
_Avoid_: clean install, reset state, empty repo

**Mode**:
One candidate-facing action of the `/ieakaso` skill, such as init, cv-parser or job-analyzer. Development tools are never modes.
_Avoid_: command, subcommand, sub-skill

**Mode entry**:
A Mode's own item in the coding assistant's `/` menu, so the candidate can pick the mode instead of typing it. It always runs the mode through `/ieakaso`, so it behaves exactly like `/ieakaso <mode>`.
_Avoid_: menu entry, thin entry, shortcut

**Source CV**:
The candidate's main CV file in `input/documents/cv/`, as chosen during init. It is the only source of truth for CV content.
_Avoid_: original CV, uploaded CV, main document

**Parsed CV**:
`input/cv.md`, generated from the Source CV by the CV parser with the same words in the same order (footnote text moves to just after the passage that references it). It is never edited by hand; to change it, change the Source CV and parse again. Other modes read the Parsed CV, never the Source CV.
_Avoid_: CV markdown, transcribed CV, living CV

**Job ad**:
The ad for one position, as the candidate supplies it: a URL Ieakaso can read, or the ad's text pasted in.
_Avoid_: job description, JD, posting

**Job analysis**:
The report the job-analyzer mode writes on how well the Parsed CV fits one Job ad, ending in a Verdict.
_Avoid_: CV score, fit report

**Verdict**:
The job analysis's advice on whether to apply: Top applicant, Apply, Stretch or Don't apply. Stretch and Don't apply advise against applying; the candidate can override either.
_Avoid_: suggestion, recommendation
