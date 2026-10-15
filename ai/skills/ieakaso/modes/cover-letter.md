# Cover Letter

`/ieakaso cover-letter [<job-url or job-ad text>]`: writes a Cover letter for one Job ad. The Applicant Agent drafts it and the Seasoned Recruiter reviews it, in Rounds, until the Review score is at least 90 (terms in `CONTEXT.md`).

Act as the Job Application Assistant: read `ai/agents/job-application-assistant.md` and follow it for the whole mode. You are the one who runs the steps and starts the Agent runs; the Applicant Agent (`ai/agents/applicant.md`) and the Seasoned Recruiter (`ai/agents/recruiter.md`) never run you or each other. Do not do their work in this conversation.

---

## INPUTS

**Job ad:** the argument, either a URL or the ad's text pasted in. See Step 1 if there is none.

**Job analysis:** found or made in Step 2.

**Company research:** found or made in Step 2b, when there is one.

Each agent's file lists the candidate's files it reads (`ai/agents/applicant.md`, `ai/agents/recruiter.md`); this mode does not repeat them.

---

## STEPS

### Step 1: Find the Job ad

1. If the argument is given, use it.
2. Otherwise use the most recent Job ad from an earlier Run in this Session (a job-analyzer or cover-letter Run). Say which one you are using.
3. Otherwise ask the candidate with a choice question (if your tool has one): the Applications in `output/applications/` (most recently modified folder first, shown as company and Position), or "paste a URL or text". **Never pick an Application silently.** If the candidate picks one, that Application's Job analysis counts as done for Step 2, even if it was made from pasted text, and its ad text comes from its `<id>_job-ad.md`.

If the argument (or the Session's Job ad) is a URL, first look for an Application whose `output/applications/*/*_job-ad.md` has it as its `**Job ad:**` or an `**Also at:**` URL. If several match, ask which one (most recently modified folder first). If one matches, use that Application: its ad text comes from the stored `<id>_job-ad.md`. Do not read the live ad; to check whether a stored ad has changed, the candidate re-runs job-analyzer with the Application's `**Job ad:**` URL. If none matches, get the ad as follows, and Step 2.3 runs job-analyzer.

Get the ad as job-analyzer does (Step 1 of `ai/skills/ieakaso/modes/job-analyzer.md`): WebFetch first, then, if that fails and the candidate agrees, the Ieakaso Job ad fetcher, otherwise the candidate pastes the ad text. Never fetch with `curl` or `wget`. Never write a letter from a URL or a Position alone. Keep the ad's text; the Applicant and the Recruiter receive it.

### Step 2: Get the Job analysis

1. **Reuse** the Application Step 1 found (no second lookup or fetch). Its `<id>_job-analysis.md` is the Job analysis, and the ad text comes from its `<id>_job-ad.md`.
2. Pasted ad text counts as analysed only if it was analysed earlier in this Session, or the candidate picked its Application in Step 1. Otherwise there is no matching analysis.
3. If there is none, **run job-analyzer** (`ai/skills/ieakaso/modes/job-analyzer.md`) now, **inside this Run**: no separate Run start and no Run summary, like the setup check's init and cv-parser. Its report is the Job analysis. Do not stop after it, even though job-analyzer normally ends with its own chat summary of the analysis (verdict, score, strengths and weaknesses): show that chat summary, not the Run summary, and continue. If the candidate picks "stop" in job-analyzer, the cover-letter Run stops there; the Run summary still follows. Pass job-analyzer the ad text you got in Step 1, with its URL and how it was read, so it uses them instead of getting the ad again.
4. Read the Job analysis's **Verdict**. If it is **Stretch** or **Don't apply**, warn the candidate that the analysis advises against applying, name the deciding gap, and ask whether to continue (a choice question if your tool has one). If they decline, stop. The Run summary still follows (see the end).

### Step 2b: Get the Company research

The Applicant Agent and the Seasoned Recruiter use the Application's Company research for facts about the company (terms in `CONTEXT.md`; the rules are in their agent files). Find it as follows:

1. **job-analyzer ran in Step 2.3.** Its Company research step already ran inside this Run: use the report it wrote or reused, or go without one if it skipped the research or every topic failed. Do not ask again.
2. **The Application's folder has `<id>_company-research.md`.** Use it. If its **Date researched** is more than 30 days before today, use it anyway and tell the candidate its age.
3. **There is none.** Ask with a choice question (if your tool has one): **"Research the company first"** or **"Write without it"**. To research, run job-analyzer's COMPANY RESEARCH Steps R1 to R5 (`ai/skills/ieakaso/modes/job-analyzer.md`) now, inside this Run, without its Verdict question in R1 (the candidate just chose). Its Agent runs belong to this Run. If it ends without a report (unknown company, every topic failed), say so and write without it.

Pass the report's path and its Date researched to every Agent run, as their INPUTS list it. Without a report, pass nothing and say in chat that the letter's company specifics come from the Job ad only.

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

Both files go into the Application's folder `output/applications/<application-id>/` and start with its Application ID (e.g. `acme_senior-backend-engineer_2026-10-10`). Use the Application's ID as it is, not today's date. If the Job analysis was just made in Step 2, its Application is the one it joined or made.

If the files already exist, overwrite them as the Job Application Assistant's rules say.

**1. The letter:** `<id>_cover-letter.md`. The final letter only, as the Applicant returned it, ready to copy: contact block, date, recipient, subject line, body, sign-off. No headings, notes or scores in it.

**2. The review log:** `<id>_cover-letter-review.md`:

```markdown
# Cover letter review log: [Position] @ [Company]

> **Date:** [yyyy-mm-dd] | **Job ad:** [URL, or "pasted text"] | **Company research:** [its Date researched, or "none"] | **Final Review score:** [X]/100 | **Rounds:** [N] | **Exit:** [Review score 90 or above / Plateau / 5 Rounds / change requested by the candidate / Round after the candidate's answers]

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

**3. The tracker record.** Once the letter file is written, set the Application's `cover_letter` path with the tracker, which is the only writer of `db/ieakaso_db.json`:

```
uv run python -m ieakaso.tracker set-cover-letter <id> output/applications/<id>/<id>_cover-letter.md
```

Do it after every write of the letter, including a follow-up (Step 7), since the path may have been overwritten. Exit 0 means it is set. Exit 4 means the Application has no record (it was analysed before the tracker existed): tell the candidate, and offer to run job-analyzer on its Job ad to create one. For any other exit, show the message from stderr (2: `db/ieakaso_db.json` is not valid JSON and was left alone; 3: the file changed while the command ran, run it again). A failure here does not stop the mode: the letter and the review log are already written.

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
