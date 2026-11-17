# The agents read a Letter context, not the Job analysis and the Company research

> Amends ADR 0008: what to stress still comes from the Job analysis, but the agents read only its strategy sections, through the Letter context.

At the start of every cover-letter Run, code (`uv run python -m ieakaso.letter_context build <id>`) writes the Application's Letter context, `<id>_letter-context.md`: the Job analysis's Strengths, Weaknesses, Screener risks, CV under-sells and Gaps to close, and the Company research's usable company facts. Those are the facts in At a glance, Domain and product, Latest releases, Financial moment and Culture, without those known only from a search snippet and without the "Not found" items. Each fact whose newest date is more than 6 months before today is tagged "older than 6 months", and each with no date "undated". The Applicant Agent and the Seasoned Recruiter read the Letter context, never the Job analysis or the Company research.

Before, both agents read both files in full in every Agent run: on a five-Round letter, ten reads of about 38 KB, most of which a letter must not use (Red flags, Employee reviews, Role impact, Notes, snippet-only facts) or need not (the Scorecard, the Requirement match the Evidence bank already covers, the Dimension detail). The rule on what was usable, and the date arithmetic for "recent", were judged by both agents in every Round. On the Applications at hand the Letter context is 37–64% smaller than the two files.

## Considered Options

- **An LLM-written file per Application, made by job-analyzer.** Rejected: it costs tokens to write, it can drift from its sources, and it can't be tested like code.
- **Telling the agents which sections to read, with no new file.** Rejected: a Read tool reads the whole file, so it saves nothing, and the red flags would still be in the agents' context.
- **Falling back to the full Company research when it can't be parsed.** Rejected: it would let red flags and employee reviews back in. Without usable facts the Letter context says "None" and the letter writes about the company from the Job ad only, as it does without a Company research.
- **Recording the Letter context in the tracker.** Rejected: it is rebuilt in every Run and is for the agents, not the candidate, so it needs no path in the record and no place in the viewer.

## Consequences

- The usable-facts rule and the 6-month rule live in code (`src/ieakaso/letter_context/`), tested on synthetic reports. The agents obey the Letter context's tags, and a company claim is supported only when the Job ad or a company fact in the Letter context states it.
- The parsing follows the Company research and Job analysis templates in `ai/skills/ieakaso/modes/job-analyzer.md`. When a section heading changes there, the command warns that the section is missing; change both together.
- `tests/test_evidence_bank_drift.py` fails when either agent's INPUTS lists the Job analysis or the Company research, or no Letter context.
- The Job analysis and the Company research stay what the candidate reads; nothing about them changes.
