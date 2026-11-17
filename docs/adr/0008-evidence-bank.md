# The agents read an Evidence bank, not the Personal knowledge base

The job-analyzer mode, which already reads the whole Personal knowledge base for the Job analysis, also writes an Evidence bank for the Application, `<id>_evidence-bank.md`, for every Verdict. The Applicant Agent writes from the bank, `config.yml`, `writing-style.md` and the Personal motivation; the Seasoned Recruiter reviews with the Parsed CV and checks every claim about the candidate against the bank, the Parsed CV, `config.yml` and the Personal motivation. Neither agent reads the other files of the Personal knowledge base. Every item in the bank names its source file, so the Personal knowledge base stays the only source of facts about the candidate; the bank only carries them.

Before, both agents read the whole Personal knowledge base in every Round: up to eleven reads of the same files per Application (the Job analysis, then two per Round over five Rounds).

## Considered Options

- **A Career Coach agent** that reads the Personal knowledge base once and instructs the Applicant, with the Recruiter seeing only the CV and the Job ad (the first sketch in `docs/flows.excalidraw`). Rejected: most of its work (strengths, weaknesses, gaps, the Verdict) is the Job analysis's already, so it would add an Agent run and a second read of the files. A Recruiter that sees only the CV also can't check claims taken from the other files, so the claim check would go.
- **A brief of chosen points instead of a bank.** Rejected: a Review that asks for a different story needs other stories to choose from, and the claim check needs every usable fact, not a selection. What to stress stays in the Job analysis.
- **A section of the Job analysis instead of its own file.** Rejected: the Job analysis is written for the candidate, the agents would read all of it to get the bank, and the bank must be rewritten without touching the Job analysis's score or Verdict.
- **Keep the status quo.** Rejected for its Token usage: the Personal knowledge base is a large share of every Agent run's input.

## Consequences

- The bank ends with a Sources section listing its source files with their SHA-256, written by code (`ieakaso.evidence_bank stamp`), never by the agent. The cover-letter mode compares them (`check`) at its start and before a Round after the candidate's answers; when one changed, or the Application has no bank (analysed before this decision), it writes the bank again, and only the bank: the Job analysis, its score and its Verdict stay. This is how the candidate's answers to the Recruiter's questions reach the letter.
- A fact in the Personal knowledge base that the bank left out can't be used until the bank is written again; the Recruiter asks for it as a question, as for any missing fact.
- The tracker record gets a top-level `evidence_bank` path, set with `set-evidence-bank <id> <path>`; the schema version goes up and the upgrade sets it to `null`.
- The product guardrail now reads: Reviews only suggest changes backed by the Evidence bank, which quotes the Personal knowledge base.
