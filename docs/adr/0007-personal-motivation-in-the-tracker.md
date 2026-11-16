# The Personal motivation is kept in the tracker

A Personal motivation is the candidate's own reason for wanting one Application's Job ad. The candidate gives it to the cover-letter mode, as `--motivation "<text>"` or when the mode asks, and Ieakaso keeps it as the record's `personal_motivation` in `db/ieakaso_db.json`, through the tracker. It is part of the Personal knowledge base, which so far was only `config.yml` and `input/`. An Application holds at most one; when a new one arrives, the candidate chooses to replace, keep or remove the stored one.

## Considered Options

- **A file per Application in `input/candidate/personal-motivations/<application-id>.md`.** It would keep the Personal knowledge base inside `input/` and follow ADR 0006 (the candidate writes `input/candidate/`). Rejected: the motivation belongs to one Application, like its status and Salary expectation, and the candidate gives it while asking for a letter, not by editing a file. A file would also need Ieakaso to write into `input/candidate/` for the chat answer, an exception to ADR 0006, and the cleaner to delete it with the Applications.
- **A file in the Application's folder in `output/`.** Rejected: `output/` holds what Ieakaso delivers, not what the candidate states.

## Consequences

- The tracker's schema goes to version 4; the upgrade from version 3 sets every record's `personal_motivation` to `null`. A later Job analysis never touches it.
- The agents never read the db: the Job Application Assistant reads the motivation with the tracker and passes its text, as given, to the Applicant Agent and the Seasoned Recruiter.
- `clean --applications` removes Personal motivations with the records, with nothing else to clean.
- The viewer shows it read-only; only the cover-letter mode sets it.
