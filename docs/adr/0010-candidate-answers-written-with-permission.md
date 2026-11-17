# Ieakaso may append the candidate's own answers to their memory files, with permission

> Amends ADR 0006: `input/candidate/` is still the candidate's; Ieakaso only types their words into it, when they say so.

When the candidate answers a question about a fact the letter needs (the cover-letter mode's questions before Round 1, or the Seasoned Recruiter's Questions for the candidate), the Job Application Assistant may append the answer to one of the candidate's memory files: `professional-experience-extended.md`, `presentation.md` or `professional-self-reflection.md`. It shows the exact text and the file first and asks "Add it" or "I'll add it myself", for every answer. The text is the candidate's, word for word, under `## Added <yyyy-mm-dd> (<Application ID>)` at the end of the file. A deterministic command writes it (`uv run python -m ieakaso.candidate_answer append <file name> <id>`, text on stdin), never the agent: it refuses any other file and any rewording is impossible, since the text passes through unchanged.

Before, the candidate had to open the file and paste the answer themselves before a Round could use it. The answers are facts the candidate gave, so typing them in for the candidate adds no fact; asking each time keeps the candidate the author of `input/candidate/`.

## Considered Options

- **The candidate always adds the answer themselves** (ADR 0006 as it was). Kept as the other choice of every question: it is the only way for the Source CV, which is a PDF or a Word file.
- **Answers kept per Application in the tracker, like the Personal motivation.** Rejected: an answer about the candidate's experience holds for every Application, so it belongs in the memory files, where the Evidence bank of every later Application finds it.
- **Standing permission for a whole Run.** Rejected: the candidate sees and approves each text before it becomes a fact Ieakaso will use from then on.
- **The Assistant edits the file freehand.** Rejected: nothing would stop a reworded answer or a write to another file.

## Consequences

- The cover-letter mode asks for missing facts before Round 1 (its Step 2e), at most three, and only when a Must or Knockout requirement has no evidence or the Job analysis has Gaps to close. Questions the candidate skipped are not shown again from the final Review.
- `writing-style.md`, `deliberate-differences.md`, `config.yml` and the Source documents are never written by Ieakaso.
- After an answer is added, the Evidence bank check sees the changed file and the bank is written again, as for any change the candidate makes.
- A fact given only in chat is still never used.
