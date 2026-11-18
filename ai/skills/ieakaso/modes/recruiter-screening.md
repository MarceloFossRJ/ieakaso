# Recruiter Screening

`/ieakaso recruiter-screening <Application ID> "<Interviewer name>" [<Interviewer LinkedIn URL>]`: writes the Screening prep for one Application's recruiter screening, then offers a mock screening (terms in `CONTEXT.md`).

A recruiter screening is not an interview. **The Interviewer does not decide: they decide what to write down and pass on.** Everything in the Screening prep serves one goal: make the candidate easy to represent. Short, repeatable, low-risk. Two consequences shape the whole document:

- **Three retellable lines beat twenty minutes of nuance.** The prep opens with the three sentences the Interviewer must be able to repeat afterwards.
- **An agency Interviewer is paid on placement, so their interest is aligned with the candidate's.** They are not an adversary, but they are burned by surprises at offer stage, so logistics volunteered early (location, notice, right to work, languages) make the candidate look low-risk.

You write the Screening prep yourself, in this conversation, in one pass: no Applicant Agent, no Seasoned Recruiter, no Review loop. The only Agent runs are the Company Researchers.

---

## INPUTS

**Application:** the first argument, an Application ID. See Step 1.

**Interviewer:** the second argument, their name (required), and the third, their LinkedIn URL (optional).

**Facts about the candidate** come only from:
- the Application's **Evidence bank**, checked and written again when needed in Step 2;
- `config.yml`: `candidate.location`, `candidate.languages`, `search_location` (cities, timezone, `visa_status`);
- the candidate's answers in Step 5, once they are in a file (see there).

Read `writing-style.md` through the writing-style skill for every line the candidate will say. Never read any other file of the Personal knowledge base, except to write the Evidence bank in Step 2.

**Facts about the company** come only from the Job ad file, the Company research (Step 3) and the Interviewer and Compensation research (Step 4).

**From the Job analysis** (`<id>_job-analysis.md`): Strengths, Weaknesses, Screener risks, CV under-sells and Gaps to close. They say what to stress and where the gap is; they are not facts about the candidate.

---

## STEPS

### Step 1: Find the Application and the Interviewer

1. Run `uv run python -m ieakaso.tracker applications` (tab-separated: ID, status, company, Position, CV version).
2. **The first argument is one of those IDs:** use it. **It is missing or not one of them:** ask with a choice question (if your tool has one) listing the Applications, `interviewing` first, then `applied`, then the rest, shown as company and Position. **Never pick one silently.**
3. **A Job ad URL or ad text instead of an ID:** say that a recruiter screening needs an Application with a Job analysis, tell the candidate to run `/ieakaso job-analyzer <job ad>` first, and stop. Never run job-analyzer from this mode.
4. Run `uv run python -m ieakaso.tracker show <id>` and keep the record (JSON). If `analysis.doc` does not exist on disk, say the Application has no Job analysis, tell the candidate to run job-analyzer on its Job ad, and stop.
5. **The Interviewer's name is missing:** ask for it in chat. The LinkedIn URL is never asked for.

### Step 2: Check the Evidence bank

Exactly as cover-letter Step 2d (`ai/skills/ieakaso/modes/cover-letter.md`): `uv run python -m ieakaso.evidence_bank check <id>`, and on exit 1 or 2 write it with job-analyzer's EVIDENCE BANK Steps B1 and B2, inside this Run. Exit 3: stop. If the bank can't be written, stop and tell the candidate. Writing the bank is the one place this mode reads the Personal knowledge base.

### Step 3: Get the Company research

1. **The Application's folder has `<id>_company-research.md` with a Date researched less than 30 days before today:** use it.
2. **It is older, or there is none:** run job-analyzer's COMPANY RESEARCH Steps R1 to R5 (`ai/skills/ieakaso/modes/job-analyzer.md`) now, inside this Run, without its Verdict question in R1 (the candidate is already being screened). Its Agent runs belong to this Run. If it ends without a report, write the prep without one and say so.
3. **An agency ad that does not name its client** (R1 skips the research): name the **probable client** from the ad's fingerprints (headquarters town, product category, stack, department names, benefits), marked "probable, unconfirmed", or "unknown". Never research the guessed client and never change the record's `company`; the call plan tells the candidate to confirm it early, and they can correct `company` in the viewer and run this mode again.

### Step 4: Research the Interviewer and the pay

Start **two Agent runs of the Company Researcher in parallel**, in one message, with the `company-researcher` agent of your tool, as `ai/agents/company-researcher.md` numbers them:

5. **Interviewer:** give it the Interviewer's name, their LinkedIn URL if given, the company (and the end client of an agency ad), the path of the Job ad file and today's date.
6. **Compensation:** give it the Position, the company, the location from the record (`location`, `home_office`) and the Job ad file, and today's date.

Give them nothing from the Personal knowledge base, and never the candidate's Salary expectation. If one returns nothing usable, start it once more; if it fails again, write its part of the prep from the Job ad alone and say so. Their findings go only into the Screening prep, never into the Company research file.

### Step 5: Ask the candidate

Ask before writing, with choice questions where your tool has them, in one go where you can:

1. **Call length** (30, 45 or 60 minutes, or another), so the minute plan fits. Not saved.
2. **What worries them most** about this call. Not saved; it decides what the prep drills hardest.
3. **Salary.** If the record's `salary_expectation` is set, show it and say the prep anchors on it, since the Interviewer has probably seen it; ask only whether to keep that anchor. If it is `null`, ask what they will ask for. Never invent a figure and never save the answer: what they say on the call is not their Salary expectation, which they edit in the viewer if they want to.
4. **Notice period**, unless the Evidence bank holds it.
5. **Missing facts**: anything the prep needs about the candidate that the bank and `config.yml` don't hold, most often a fact the primary gap (section 5) turns on, or why they are leaving their current role. At most 3, never about health, family or protected characteristics.

**Facts about the candidate** (4 and 5) count only once they are in a file, as cover-letter Step 2e says: show the exact text and the memory file (`professional-experience-extended.md` for logistics such as the notice period), and ask **"Add it"** or **"I'll add it myself"**; on "Add it", `uv run python -m ieakaso.candidate_answer append <file name> <id>` with their words on stdin; on the other, wait until they say it is done. Ask for every answer; one yes never covers the next. Use the text as it went into the file; you need not write the bank again for it. A fact the candidate leaves out is written in the prep as a question to settle before the call, never as an assumption. 1 to 3 are the candidate's plans for this call, not facts about them: use them as given.

### Step 6: Write the Screening prep

Write `output/applications/<id>/<id>_screening-prep.md`, in English, in Markdown only. A new Run of this mode overwrites the file without asking; say in chat that it did. Keep it short enough to read twice in one sitting.

**Drafted wording, not advice.** Every line the candidate will say is a blockquote they can say out loud, in their voice (`writing-style.md`): measured, direct, no hype, never "I am excited about". "Consider mentioning X" is not a deliverable. Refer to the candidate by name or as "you", never with a gendered pronoun.

```markdown
# Screening prep: [Position] @ [Company]

> **Date:** [yyyy-mm-dd] | **Interviewer:** [name], [title], [in-house / agency: firm / unknown] | **Call:** [N] min | **Job ad:** [URL, or "pasted text"] | **Company research:** [its Date researched, or "none"]

## 1. The three things they must be able to repeat

[Three sentences, third person, as the Interviewer would write them in their notes. Scope and numbers first.]

## 2. Who you are actually talking to

[The Interviewer and their firm, in-house or agency, and what that implies for how they listen. Be easy to represent; never go deeper technically than they can follow. "Not found" research said plainly.]

## 3. The call, minute by minute

| Minutes | What happens | Your job |
|---|---|---|

[Sized to the call length. One **structural move** early, typically asking who the client is (agency) or what triggered the opening (in-house): it gets the answer, shows preparation and opens the company material.]

## 4. The opening pitch

> [A 90-second answer to "tell me about yourself". Two roles at most: the earliest that establishes scope, the current one that establishes relevance. It closes on why this Position.]

**Delivery notes:** [the two numbers to slow down on, and where to stop talking.]

## 5. The primary gap

[The one thing most likely to end the process, from the Job analysis's Screener risks and Gaps to close.]

- **What is true and can't be claimed:** [...]
- **What is also true:** [the adjacent, real experience from the bank that answers the concern underneath]

> [A script that volunteers the gap rather than defending it, ending in a line that names what the candidate is not.]

[Any fact this needs that the bank does not hold: a question to settle before the call.]

## 6. Secondary probes

[One or two things the ad signals hard (AI use, domain, scale, remote maturity). One calm drafted paragraph each. A growth area the bank holds is framed as a considered position, not hidden.]

## 7. Logistics: volunteer these

[Location and willingness to travel with a concrete rhythm, right to work (`visa_status`), notice period (an exact figure), languages with levels (`candidate.languages`), and a short forward-facing answer to "why are you leaving". Each a stated fact, not a hedge; a missing one is flagged to settle before the call.]

## 8. Salary

[The benchmarks with their sources; the country reading of the advertised figure; a drafted ask; a drafted fallback if the band is lower; how to handle "what do you earn now"; whether to name a figure above the published band, and why.]

## 9. Questions to ask

[Five; pick three. Always "Is this a new team or a replacement, and what happened?", and one that shows the company's real situation rather than its marketing.]

## 10. Company cheat sheet

[The research compressed to what can be read in a second window during the call, ending with **the unstated challenge**: the organisational problem nobody advertises, from the Company research and the research of Step 4, followed by a drafted blockquote naming it, for when the call turns substantive.]

## 11. Things to listen for

[Red flags and what they mean: churn in the role, turnaround language, whether remote is really optional, whether the Interviewer can answer product questions at all.]

## 12. How to close

> [A drafted closing line.]

[A short same-day thank-you referencing one specific thing from the call.]

## Quick reference

**Say these:** [...]

**Avoid these:** [...]
```

### Step 7: Check it before saving

Re-read every claim about the candidate against the Evidence bank, `config.yml` and the answers added in Step 5. Remove any figure, employer, date or achievement they don't hold, and any drafted line that implies experience they don't show. Re-read every claim about the company against the Job ad and the research, each with its source. Honesty about the gap beats polish: naming a real limit plainly is what makes the rest believable.

### Step 8: Record it in the tracker

```
uv run python -m ieakaso.tracker set-screening-prep <id> output/applications/<id>/<id>_screening-prep.md
uv run python -m ieakaso.tracker add-contact <id> --type recruiter --name "<Interviewer name>" [--linkedin <url>]
```

`add-contact` prints `added contact to <id>`, or `contact already on <id>` when a contact with the same name or LinkedIn URL is there. Then, if the record's `status` is not `interviewing`, ask with a choice question (if your tool has one): **"Set it to Interviewing"** or **"Leave it"**, and on yes run `uv run python -m ieakaso.tracker set-status <id> interviewing`. Never change `stage` or `stages`. Exit codes are the tracker's: on any exit but 0, show the message from stderr and go on; the file is already written.

### Step 9: Report in chat

Show the candidate:
- the file path, and that it was overwritten, if so
- the three lines of section 1 and the primary gap, in a line each
- what the research could not find (the Interviewer, the client of an agency ad, pay data)
- any fact left to settle before the call
- the offer of a mock screening (Step 10)

Then the Run summary (see the router), as the last thing you print. Follow-ups stay in the same Run: after each one, show the Run summary again.

### Step 10: Follow-ups, in the same Run

**The mock screening.** On yes, play the Interviewer, in character, from the first line: a realistic greeting, then one question at a time, waiting for each answer. Do not narrate. Follow up on vague answers the way a real Interviewer would. Push hardest on the primary gap (section 5), the salary question and "why are you leaving". After 6 to 8 exchanges, or when the candidate calls time, break character and give a short debrief: what landed, what was too long, what the Interviewer would have written down, and one specific rewrite. Keep it honest: flattery here costs the candidate the real call. Nothing from the mock is saved, except a fact the candidate chooses to "Add it" as in Step 5.

**Changes the candidate asks for** (from the mock's debrief or otherwise): edit the Screening prep in place, keeping its sections, under the same rules (Steps 6 and 7). A new fact goes into a file first, as in Step 5. Say what changed.

---

## RULES

1. **Evidence or nothing.** Every claim about the candidate traces to the Evidence bank, `config.yml` or an answer added to a file in this Run; every claim about the company to the Job ad or the research, with its source. Never invent a metric, employer, date, outcome or salary figure.
2. **The Interviewer is a private person.** Only public, professional facts about them, through the Company Researcher's topic 5; their LinkedIn page is never fetched.
3. **Draft only.** Never contact the Interviewer or anyone else, never send the thank-you; the candidate acts.
4. **Never weigh protected characteristics**, and never ask about health, family or anything that touches them.
5. **No Run start and no Run summary** for the job-analyzer steps or the Agent runs this mode runs inside its Run.
