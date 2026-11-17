# Reference letters are no longer part of the Personal knowledge base

ADR 0004 added reference letters to the Personal knowledge base as trusted background. They are now removed from the product: init no longer suggests them, the CV parser no longer parses them, and neither the Conflict report nor the Evidence bank uses them. The main reason is that the facts in a reference letter are the candidate's to state: the Personal knowledge base holds only facts the candidate vouches for, so a fact the CV leaves out (a team size, a project's result) belongs in `input/candidate/professional-experience-extended.md`, in the candidate's own words, not in someone else's letter that Ieakaso has to filter for opinions. It also makes init simpler: one fewer document to ask about, and one fewer source for the Conflict report. This supersedes the reference-letter half of ADR 0004; the LinkedIn profile is still parsed as that ADR says.

## Considered Options

- **Keep the feature and let the candidate skip it.** Init already allowed that. Rejected: the rules that kept a letter's opinions out of the drafts (background only, never quoted or attributed) cost guidelines, agent rules and Review checks for a source the candidate can replace with their own words.
- **A general rule against quoting what others said about the candidate.** Left out: it would be a new feature, not part of removing letters.

## Consequences

- No clone held reference letters when this was decided, so there is no clean-up step: the `reference_letters/` folder, its setup-state key and its parser code are simply removed. An old `documents.reference_letters` key in `db/system_status.json` is dropped by init and never makes setup incomplete.
- The Conflict report compares the Parsed CV with the LinkedIn profile and `config.yml` only.
