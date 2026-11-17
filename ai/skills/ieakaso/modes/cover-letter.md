# Cover Letter

`/ieakaso cover-letter [<job-url or job-ad text>] [--motivation "<text>"]`: writes a Cover letter for one Job ad. The Applicant Agent drafts it and the Seasoned Recruiter reviews it, in Rounds, until the Review score is at least 90 (terms in `CONTEXT.md`).

Act as the Job Application Assistant: read `ai/agents/job-application-assistant.md` and follow it for the whole mode. You are the one who runs the steps and starts the Agent runs; the Applicant Agent (`ai/agents/applicant.md`) and the Seasoned Recruiter (`ai/agents/recruiter.md`) never run you or each other. Do not do their work in this conversation.

---

## INPUTS

**Job ad:** the argument, either a URL or the ad's text pasted in. See Step 1 if there is none. `--motivation "<text>"` is not part of the Job ad: take it out of the argument first.

**Job analysis:** found or made in Step 2.

**Company research:** found or made in Step 2b, when there is one.

**Evidence bank:** the facts from the Personal knowledge base the agents write and review from, checked, and written when needed, in Step 2d.

**Letter context:** the parts of the Job analysis and the Company research the agents read, built in Step 2f. The agents never read the Job analysis or the Company research themselves.

**Personal motivation:** the candidate's own reason for wanting this Application's job, optional (terms in `CONTEXT.md`). It comes from `--motivation` or from the candidate's answer in Step 2c, and is kept in the Application's tracker record; Step 2c saves it, and reads it when there is no new one.

Each agent's file lists what it reads (`ai/agents/applicant.md`, `ai/agents/recruiter.md`); this mode does not repeat them. Neither reads the Personal knowledge base beyond the Evidence bank, the Parsed CV (the Recruiter) and `config.yml`.

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

The Applicant Agent and the Seasoned Recruiter take their facts about the company from the Application's Company research, through the Letter context (Step 2f; terms in `CONTEXT.md`, rules in their agent files). Find it as follows:

1. **job-analyzer ran in Step 2.3.** Its Company research step already ran inside this Run: use the report it wrote or reused, or go without one if it skipped the research or every topic failed. Do not ask again.
2. **The Application's folder has `<id>_company-research.md`.** Use it. If its **Date researched** is more than 30 days before today, use it anyway and tell the candidate its age.
3. **There is none.** Ask with a choice question (if your tool has one): **"Research the company first"** or **"Write without it"**. To research, run job-analyzer's COMPANY RESEARCH Steps R1 to R5 (`ai/skills/ieakaso/modes/job-analyzer.md`) now, inside this Run, without its Verdict question in R1 (the candidate just chose). Its Agent runs belong to this Run. If it ends without a report (unknown company, every topic failed), say so and write without it.

Never pass the report to an Agent run: Step 2f builds the Letter context from it.

### Step 2c: Get the Personal motivation

The Personal motivation is optional and never blocks a letter. It belongs to this Application only; reasons that hold for any job belong in `input/candidate/professional-self-reflection.md`. This step runs after Step 2 and before Round 1, so a candidate who stops at the Verdict warning in Step 2.4 saves nothing. job-analyzer never asks for a motivation.

1. **Read the stored one:** `uv run python -m ieakaso.tracker personal-motivation <id>` prints the text, or nothing when there is none. Exit 4 means the Application has no record (it was analysed before the tracker existed): tell the candidate, offer to run job-analyzer on its Job ad to create one (inside this Run, as in Step 2.3), and otherwise write the letter without a motivation, skipping the rest of this step. For any other exit, show the message from stderr and write without a motivation.
2. **A new one is given** by `--motivation`, or by the candidate's answer in item 4:
   - With **no stored one**, save it.
   - With a **stored one**, show the stored text and ask with a choice question (if your tool has one): **"Replace"** (save the new one), **"Keep"** (use the stored one, drop the new one) or **"Remove"** (delete the stored one and write without a motivation). Never merge the two texts.
3. **No new one is given, and one is stored:** use the stored one without asking.
4. **No new one is given, and none is stored:** ask with a choice question (if your tool has one): **"Add a personal motivation"** or **"Write without one"**. If they add one, ask for it in chat and save it.

**Saving** keeps the candidate's words as given, with no rewording, summary or correction. Pass the text on standard input, so quotes and line breaks arrive unchanged:

```
uv run python -m ieakaso.tracker set-personal-motivation <id> <<'EOF'
<the text>
EOF
```

Exit 0 prints `personal motivation set for <id>:` and then the trimmed text as stored. Remove runs `uv run python -m ieakaso.tracker set-personal-motivation <id> --clear </dev/null` (it refuses text on stdin). Exit 1 means the text was empty, there was no text on stdin, or `--clear` was given text: nothing was changed, so write without the new text. Exit 4 is handled as in item 1. For exit 2 or 3, show the message from stderr (2: `db/ieakaso_db.json` is not valid JSON and was left alone; 3: the file changed while the command ran, run it again). A save that fails does not stop the mode: write the letter without the new text, and tell the candidate.

The motivation the letter uses is the one the tracker holds after this step: the text you read in item 1 (kept), or the text the save command printed (replaced or added). Pass it verbatim to both agents (Step 3), and remember whether there is one: Step 5 needs it. With none (skipped, removed, a failed save, no record), pass nothing. Nothing ever writes "none" to the tracker: skipping leaves the field as it was.

A new `--motivation` on an Application that already has a letter is a fresh Run: Step 3 deletes the Round files, and Step 5 overwrites the letter and the review log. Step 7 is unchanged: a fact given only in chat is still never used.

### Step 2d: Check the Evidence bank

The Applicant Agent and the Seasoned Recruiter take their facts about the candidate from the Application's Evidence bank, never from the Personal knowledge base itself (terms in `CONTEXT.md`). Check that it exists and matches the candidate's files:

```
uv run python -m ieakaso.evidence_bank check <id>
```

| Exit | Meaning | What you do |
|---|---|---|
| 0 | The bank is current | Use it. |
| 1 | A source file changed, was added or was removed since the bank was written (one `Changed:`, `Added:` or `Removed:` line each) | Write it again (below), and say in chat which files changed. |
| 2 | No bank (the Application was analysed before Evidence banks existed), or a bank with no Sources section | Write it (below), and say so in chat. |
| 3 | The Application's folder is missing | Stop and tell the candidate. |

**Writing the bank:** run job-analyzer's EVIDENCE BANK Steps B1 and B2 (`ai/skills/ieakaso/modes/job-analyzer.md`) now, inside this Run. Only the bank is written: the Job analysis, its score and its Verdict stay. This is the one place in this mode where you read the Personal knowledge base, and only to write the bank: you still never draft or review. If the bank can't be written, stop and tell the candidate; never let the agents read the Personal knowledge base instead.

When job-analyzer ran in Step 2.3, it wrote the bank in this Run: the check passes, and you go on.

Pass the bank's path, `output/applications/<id>/<id>_evidence-bank.md`, to every Agent run, as their INPUTS list it.

### Step 2f: Build the Letter context

The agents read the parts of the Job analysis and the Company research they need from the Letter context, never those files themselves (terms in `CONTEXT.md`; decision in `docs/adr/0011-letter-context.md`). Build it, in every Run, so it is never out of date:

```
uv run python -m ieakaso.letter_context build <id>
```

| Exit | Meaning | What you do |
|---|---|---|
| 0 | Written | Use it. Any `Warning:` line on stderr names a section that is missing: go on. |
| 1 | Written without company facts: no Company research, it can't be read, or it has no usable fact (the reason is on stderr) | Use it, and say in chat that the letter's company specifics come from the Job ad only. |
| 3 | The Application's folder or its Job analysis is missing | Stop and tell the candidate. |

Pass its path, `output/applications/<id>/<id>_letter-context.md`, to every Agent run, as their INPUTS list it. Never pass them the Job analysis or the Company research.

### Step 3: Run the Rounds

One **Round** is a fresh Applicant Agent run (the draft) followed by a fresh Seasoned Recruiter run (the Review). Start and feed every Agent run as `ai/agents/job-application-assistant.md` says: pass each agent everything its INPUTS lists (`ai/agents/applicant.md`, `ai/agents/recruiter.md`). The Personal motivation (Step 2c) lives in the tracker, which agents never read: pass its text in the prompt, word for word and marked as "the Application's Personal motivation", to the Applicant and to the Recruiter, in every Round and every follow-up.

**Round files.** Each Agent run writes its full output to a file in the Application's folder and replies with a short summary (the agent files say what it holds). You pass paths, never text, and you never read these files:

- `output/applications/<id>/rounds/round-<n>_draft.md`: the Applicant's draft and notes.
- `output/applications/<id>/rounds/round-<n>_review.md`: the Seasoned Recruiter's Review.

A Round the candidate requested gets the same files, and its number continues the sequence. A new cover-letter Run for an Application starts by deleting its `rounds/` folder, and you say so in chat if it held files.

Give the Applicant the path of the draft file to write, and, from the second Round on, the path of the current draft and of the latest Review. Give the Recruiter the path of the draft to review, the paths of all earlier Reviews and the path of the Review file to write.

After each Round, note the paths, the Review score and the Recruiter's handover decision (with its Plateau flag), all from the agents' replies. Keep every one. Ask the candidate the Recruiter's Questions for the candidate from its reply.

### Step 4: Exit

Stop at the **first** of these:

1. The Review score is **90 or above**.
2. The Seasoned Recruiter declares a **Plateau** (its handover decision).
3. **5 Rounds** have run.

Otherwise the Recruiter hands back to the Applicant and the next Round runs.

The result is the best draft, per the Job Application Assistant's rules, chosen from the Review scores in the replies. Its Review is the final Review.

### Step 5: Write the files

Both files go into the Application's folder `output/applications/<application-id>/` and start with its Application ID (e.g. `acme_senior-backend-engineer_2026-10-10`). Use the Application's ID as it is, not today's date. If the Job analysis was just made in Step 2, its Application is the one it joined or made.

If the files already exist, overwrite them as the Job Application Assistant's rules say.

**Run the command** (the text of the Round files never enters the conversation):

```
uv run python -m ieakaso.cover_letter assemble <id> --rounds <n> --final <n> --exit "<Exit>" --reason "<Exit reason>" --motivation used|none [--requested <n> ...]
```

`--rounds` is how many Rounds have run, `--final` the Round whose draft is the final letter (the best draft), `--requested` the Rounds the candidate requested, `--motivation` `used` when you passed a Personal motivation to the agents in this Run (given, stored or just saved) and `none` otherwise (required; the command never reads the tracker), `--exit` the header's Exit (exactly one of the values in the template below; any other value is exit 1) and `--reason` the Exit reason: which exit condition ended the process, and in one line why, naming the best-scoring Round if it is not the last. The command reads the Round files, the Job ad file (title and URL), the Company research (its Date researched), uses today's date, writes both files and prints the final letter. Exit 0 means both files are written. Exit 1 means a Round file is missing or unusable, `--exit` is not one of the values, or `--final` or `--requested` names a Round that isn't there; exit 3 means the Application's folder or Job ad file is missing, or its Company research file is unreadable. For either, nothing was written: show the message from stderr, start the Agent run again if a Round file is missing or unusable, and stop if it fails again.

What it writes:

**1. The letter:** `<id>_cover-letter.md`. The Draft section of the final Round's file, unchanged: the final letter only, ready to copy: contact block, date, recipient, subject line, body, sign-off. No headings, notes or scores in it.

**2. The review log:** `<id>_cover-letter-review.md`:

```markdown
# Cover letter review log: [Position] @ [Company]

> **Date:** [yyyy-mm-dd] | **Job ad:** [URL, or "pasted text"] | **Company research:** [its Date researched, or "none"] | **Personal motivation:** [used if you passed one to the agents, else none] | **Final Review score:** [X]/100 | **Rounds:** [N] | **Exit:** [Review score 90 or above / Plateau / 5 Rounds / change requested by the candidate / Round after the candidate's answers]

After a follow-up (Step 7), the header's Final Review score, Rounds and Exit describe the current result.

**Final letter:** Round [N]'s draft. [If it is not the last Round: "It scored highest; later drafts scored lower."]

**Language:** [the letter's language, and the reason if it is not the ad's]

## Round [N]

[Repeat for each Round, in order. Add "(requested by the candidate)" to the heading of a Round that came from a change the candidate asked for.]

**Review score:** [X]/100

### Draft

[The Applicant's whole draft for this Round, from its Round file]

### Review

[The Seasoned Recruiter's Review for this Round, from its Round file: domain, scorecard, the Remove / Rewrite / Improve items, Questions for the candidate, handover decision]

### Refused suggestions

[From the Applicant's notes in its Round file, or "None"]

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
- the **final letter** (the whole text: the command prints it, and this is the only full text you show)
- its **Review score** and the **exit reason**
- a short **summary of each Round**: the score and the main change
- the open **Questions for the candidate** from the final Review (not those the candidate has answered), or "none"
- the **file paths** of both files, and that they were overwritten, if so
- the language, if it is not the ad's language
- what the Applicant left out of the Personal motivation (its **Motivation left out** note), if anything
- when the Recruiter asked for a Personal motivation among its Questions for the candidate: that the candidate can re-run `/ieakaso cover-letter --motivation "<text>"` to give one, and say that a re-run is a fresh Run: it replaces the Round files, the letter and the review log, so they should copy the current letter first if they want to keep it
- any refused suggestion that matters

Then the Run summary (see the router), as the last thing you print. Follow-ups (Step 7) stay in the same Run: after each one, report again and show the Run summary again, so it includes the follow-up's Agent runs.

### Step 7: Follow-ups, in the same Run

**Answers to Questions for the candidate.** A fact given only in chat is not used (the Job Application Assistant's rules). Ask the candidate to add it to the right file first: the Source CV or the memory file the Recruiter named. When they say it is done:

1. If they added it to the Source CV, run the cv-parser mode (`ai/skills/ieakaso/modes/cv-parser.md`) now, inside this Run, so `input/parsed-documents/cv.md` is current. If it ends with neither exit 0 nor exit 4 (new CV files asked about), stop and tell the candidate.
2. Run Step 2d again, so the Evidence bank holds the new fact. If the check says the bank is current, the candidate has not changed a source file yet: say so and wait.
3. Run Step 2f again, then **one more Round** (Step 3), starting from the path of the current result's draft (the draft shown as the final letter, not the last draft written), run the assemble command again with the new Round count, update both files, and report again. A Round after the 5 Rounds is allowed here; it is the candidate's request. In the review log, set the exit to "Round after the candidate's answers".

**Changes the candidate requests** (a different tone, a shorter body, a different emphasis). Run Step 2f again, then start a fresh Applicant Agent run with everything in its INPUTS, plus the change request and the path of the current result's draft, then **one** Seasoned Recruiter Review of the result, to which you also pass the change request. No automatic loop afterwards. **The candidate's request wins even if the score drops**, and the Job Application Assistant's best-draft reset applies. Run the assemble command again, with the Round in `--requested`, to update both files and mark the Round "requested by the candidate" in the review log, and set the Exit to "change requested by the candidate" and the exit reason to say so. Report the new Review score and any drop.

---

## RULES

1. **Act as the Job Application Assistant** and follow its rules for Agent runs, the best draft, overwriting and facts. You manage; the agents write and review.
2. **No Run start and no Run summary for the job-analyzer run in Step 2**, and none for the Agent runs.
