# Cover Letter

`/ieakaso cover-letter [<job-url or job-ad text>]`: writes a Cover letter for one Job ad. The Applicant Agent drafts it and the Seasoned Recruiter reviews it, in Rounds, until the Review score is at least 90 (terms in `CONTEXT.md`).

Act as the Job Application Assistant: read `ai/agents/job-application-assistant.md` and follow it for the whole mode. You are the one who runs the steps and starts the Agent runs; the Applicant Agent (`ai/agents/applicant.md`) and the Seasoned Recruiter (`ai/agents/recruiter.md`) never run you or each other. Do not do their work in this conversation.

---

## INPUTS

**Job ad:** the argument, either a URL or the ad's text pasted in. See Step 1 if there is none.

**Job analysis:** found or made in Step 2.

Each agent's file lists the candidate's files it reads (`ai/agents/applicant.md`, `ai/agents/recruiter.md`); this mode does not repeat them.

---

## STEPS

### Step 1: Find the Job ad

1. If the argument is given, use it.
2. Otherwise use the most recent Job ad from an earlier Run in this Session (a job-analyzer or cover-letter Run). Say which one you are using.
3. Otherwise ask the candidate with a choice question (if your tool has one): the most recent files in `output/job-analysis/` (newest first, shown as company and position), or "paste a URL or text". **Never pick a file from disk silently.** If the candidate picks a file, its `**Job ad:**` header gives the URL, and the ad's text is in the report's "Job ad (as analysed)" section. That analysis counts as done for Step 2, even if it was made from pasted text.

If the argument is a URL, get the ad as job-analyzer does (Step 1 of `ai/skills/ieakaso/modes/job-analyzer.md`): WebFetch first, then, if that fails and the candidate agrees, the Ieakaso job ad fetcher, otherwise the candidate pastes the ad text. Never fetch with `curl` or `wget`. Never write a letter from a URL or a job title alone. Keep the ad's text; the Applicant and the Recruiter receive it.

### Step 2: Get the Job analysis

1. **Reuse** the newest `output/job-analysis/*.md` whose `**Job ad:**` header URL matches the Job ad's URL.
2. Pasted ad text counts as analysed only if it was analysed earlier in this Session, or the candidate picked its analysis from disk in Step 1. Otherwise there is no matching analysis.
3. If there is none, **run job-analyzer** (`ai/skills/ieakaso/modes/job-analyzer.md`) now, **inside this Run**: no separate Run start and no Run summary, like the setup check's init and cv-parser. Its report is the Job analysis. Do not stop after it, even though job-analyzer normally ends with its own chat summary of the analysis (verdict, score, strengths and weaknesses): show that chat summary, not the Run summary, and continue.
4. Read the Job analysis's **Verdict**. If it is **Stretch** or **Don't apply**, warn the candidate that the analysis advises against applying, name the deciding gap, and ask whether to continue (a choice question if your tool has one). If they decline, stop. The Run summary still follows (see the end).

### Step 3: Run the Rounds

One **Round** is a fresh Applicant Agent run (the draft) followed by a fresh Seasoned Recruiter run (the Review). Start and feed every Agent run as `ai/agents/job-application-assistant.md` says: pass each agent everything its INPUTS lists (`ai/agents/applicant.md`, `ai/agents/recruiter.md`).

After each Round, note the draft, the Review score and the Recruiter's handover decision. Keep every one.

### Step 4: Exit

Stop at the **first** of these:

1. The Review score is **90 or above**.
2. The Seasoned Recruiter declares a **Plateau** (its handover decision).
3. **5 Rounds** have run.

Otherwise the Recruiter hands back to the Applicant and the next Round runs.

The result is the best draft, per the Job Application Assistant's rules. Its Review is the final Review.

### Step 5: Write the files

Names follow job-analyzer: `<company>_<position>_<yyyymmdd>`, with `<company>` and `<position>` in lowercase kebab-case and today's date (e.g. `output/cover-letter/acme_senior-backend-engineer_20261010`). Use the company and position of the Job analysis.

If the files already exist, overwrite them as the Job Application Assistant's rules say.

**1. The letter:** `output/cover-letter/<company>_<position>_<yyyymmdd>.md`. The final letter only, as the Applicant returned it, ready to copy: contact block, date, recipient, subject line, body, sign-off. No headings, notes or scores in it.

**2. The review log:** `output/cover-letter/<company>_<position>_<yyyymmdd>_review.md`:

```markdown
# Cover letter review log: [Position] @ [Company]

> **Date:** [yyyy-mm-dd] | **Job ad:** [URL, or "pasted text"] | **Final Review score:** [X]/100 | **Rounds:** [N] | **Exit:** [Review score 90 or above / Plateau / 5 Rounds / change requested by the candidate / Round after the candidate's answers]

After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.

**Final letter:** Round [N]'s draft. [If it is not the last Round: "It scored highest; later drafts scored lower."]

**Language:** [the letter's language, and the reason if it is not the ad's]

## Round [N]

[Repeat for each Round, in order. Add "(requested by the candidate)" to the heading of a Round that came from a change the candidate asked for.]

**Review score:** [X]/100

### Draft

[The Applicant's whole draft for this Round]

### Review

[The Seasoned Recruiter's Review for this Round, as returned: domain, scorecard, the Remove / Rewrite / Improve items, Questions for the candidate, handover decision]

### Refused suggestions

[From the Applicant's notes, or "None"]

## Exit reason

[Which exit condition ended the process, and in one line why. Name the best-scoring Round if it is not the last.]
```

### Step 6: Report in chat

Show the candidate:
- the **final letter** (the whole text)
- its **Review score** and the **exit reason**
- a short **summary of each Round**: the score and the main change
- the open **Questions for the candidate** from the final Review (not those the candidate has answered), or "none"
- the **file paths** of both files, and that they were overwritten, if so
- the language, if it is not the ad's language
- any refused suggestion that matters

Then the Run summary (see the router), as the last thing you print. Follow-ups (Step 7) stay in the same Run: after each one, report again and show the Run summary again, so it includes the follow-up's Agent runs.

### Step 7: Follow-ups, in the same Run

**Answers to Questions for the candidate.** A fact given only in chat is not used (the Job Application Assistant's rules). Ask the candidate to add it to the right file first: the Source CV or the memory file the Recruiter named. When they say it is done:

1. If they added it to the Source CV, run the cv-parser mode (`ai/skills/ieakaso/modes/cv-parser.md`) now, inside this Run, so `input/cv.md` is current. If it does not end with exit 0, stop and tell the candidate.
2. Run **one more Round** (Step 3), starting from the current result (the draft shown as the final letter, not the last draft written), update both files, and report again. A Round after the 5 Rounds is allowed here; it is the candidate's request. In the review log, set the exit to "Round after the candidate's answers".

**Changes the candidate requests** (a different tone, a shorter body, a different emphasis). Start a fresh Applicant Agent run with everything in its INPUTS, plus the change request and the current result as its draft, then **one** Seasoned Recruiter Review of the result, to which you also pass the change request. No automatic loop afterwards. **The candidate's request wins even if the score drops**, and the Job Application Assistant's best-draft reset applies. Update both files, add a Round marked "requested by the candidate" to the review log, and set the Exit to "change requested by the candidate" and the exit reason to say so. Report the new Review score and any drop.

---

## RULES

1. **Act as the Job Application Assistant** and follow its rules for Agent runs, the best draft, overwriting and facts. You manage; the agents write and review.
2. **No Run start and no Run summary for the job-analyzer run in Step 2**, and none for the Agent runs.
