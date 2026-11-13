# CV versions: `input/documents/cv/` is an inbox, and versions are frozen folders

The candidate's CV changes during a job search, and they need to know which CV each Application was sent with. A CV version is identified by its Source CV file's fingerprint, not by its name: Ieakaso never reads meaning into a file name (a candidate's semver in it is just the version's default label). The candidate supplies a new version by saving the file in `input/documents/cv/`, which is an inbox: the CV parser **moves** each new file into its own folder `input/documents/cv/<version-id>/` (`cv_<yyyy-mm-dd>`, `_2`, `_3` on the same day), next to a frozen copy of its Parsed CV, and the version's metadata goes to `cv_versions` in the tracker db. `input/cv.md` is always the current version's Parsed CV, the only one agents read. Folders are never changed or deleted, so the file an employer received and the Parsed CV the agents read for it can always be found again.

## Considered Options

- **Copy instead of move, the Source CV stays in `input/documents/cv/`.** Rejected: the next CV saved there would sit next to the old one, and init would ask on every run which of the files is the main CV.
- **Folders the candidate creates.** Rejected: a second way in, with its own edge cases (two files in a folder, a name that isn't an ID, an old file). Saving one file is the only thing to learn; the parser warns once about folders it didn't create.
- **Every version's content in `input/cv.md`.** Rejected: agents would mix old and new claims, and the Parsed CV would stop being the reference other documents are checked against.
- **Version data read from the folders.** Rejected in favour of the tracker db, which stays the only reader and writer of what the viewer edits (a version's label).

## Consequences

- A re-parse after a `PARSER_VERSION` bump is not a new version: it rewrites `input/cv.md` and leaves the frozen copy as the agents read it then.
- A file whose content matches an existing version is not captured; a file the candidate says is not a CV stays in the inbox. Nothing is ever deleted, so a version captured by mistake stays.
- `clean --applications` keeps `cv_versions`: CV versions are setup, not Applications.
- A Tailored CV is a version linked to one Application; it never becomes current, and the agents still read `input/cv.md` for that Application.
