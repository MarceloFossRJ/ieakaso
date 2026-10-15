# The LinkedIn profile and reference letters are parsed like the CV

ADR 0001 made the Parsed CV deterministic code output. The LinkedIn profile and the reference letters now join the Personal knowledge base, so the agents take claims about the candidate from them too. They follow the same rule: the CV parser writes a Parsed document for each (`input/linkedin.md`, `input/reference-letters/<source file name>.md`), with the same words in the same order, and the agents read only those. The reason is ADR 0001's: an agent reading a PDF can silently reword, drop or add content, and a claim's source must be a file anyone can check.

## Considered Options

- **The agents read the PDFs directly.** Rejected for ADR 0001's reasons: not repeatable, not testable, and not every coding assistant reads PDFs.
- **A separate command and setup step for the other documents.** Rejected: it is the same parser and the same fingerprinting, so the CV parser's command, mode and setup step do both. The exit code still reflects the CV alone; a document that fails to parse is a warning, never a stop, because the CV is the only mandatory document.
- **Also Xing, Wellfound and Peerlist profiles.** Left out: they mostly repeat the CV and the LinkedIn profile, and init does not know them.

## Consequences

- A Parsed document whose Source document is gone is deleted at the next parse, so the Personal knowledge base never keeps facts the candidate removed.
- A Source document the parser can't read is recorded in `db/system_status.json` and reported once, until it changes; Ieakaso carries on without it.
- The LinkedIn PDF export has a sidebar (contact, skills, languages): the parser keeps the stored block order, so the sidebar comes out as whole blocks before the main column.
