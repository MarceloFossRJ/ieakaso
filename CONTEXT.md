# Ieakaso

A local job-search assistant that drafts applications for a candidate; the candidate acts on them.

## Language

**User data**:
The candidate's own files, which are gitignored and never leave their machine: `config.yml`, `db/system_status.json`, `db/ieakaso_db.json`, and everything in `input/` and `output/` except the tracked placeholders (`.gitkeep` files and `input/documents/README.md`).
_Avoid_: personal data, private files

**Fresh state**:
The repo with no user data, exactly as after a clone and before the first `/ieakaso init`. The development cleaner (`ieakaso.devtools.cleaner`) returns a repo to it.
_Avoid_: clean install, reset state, empty repo

**Mode**:
One candidate-facing action of the `/ieakaso` skill, such as init, cv-parser, job-analyzer or cover-letter. Development tools are never modes.
_Avoid_: command, subcommand, sub-skill

**Mode entry**:
A Mode's own item in the coding assistant's `/` menu, so the candidate can pick the mode instead of typing it. It always runs the mode through `/ieakaso`, so it behaves exactly like `/ieakaso <mode>`.
_Avoid_: menu entry, thin entry, shortcut

**Source CV**:
The candidate's main CV file in `input/documents/cv/`, as chosen during init. It is the only source of truth for CV content.
_Avoid_: original CV, uploaded CV, main document

**Parsed CV**:
`input/cv.md`, generated from the Source CV by the CV parser with the same words in the same order (footnote text moves to just after the passage that references it). It is never edited by hand; to change it, change the Source CV and parse again. Other modes read the Parsed CV, never the Source CV.
_Avoid_: CV markdown, transcribed CV, living CV

**Job ad**:
The ad for one position, as the candidate supplies it: a URL Ieakaso can read, or the ad's text pasted in.
_Avoid_: job description, JD, posting

**Job analysis**:
The report the job-analyzer mode writes on how well the Parsed CV fits one Job ad, ending in a Verdict.
_Avoid_: CV score, fit report

**Verdict**:
The job analysis's advice on whether to apply: Top applicant, Apply, Stretch or Don't apply. Stretch and Don't apply advise against applying; the candidate can override either.
_Avoid_: suggestion, recommendation

**Run**:
One `/ieakaso <mode>` call, including the setup check and any init, cv-parser or job-analyzer it triggers. It lasts until the next Run or the end of the Session, so follow-up questions about its result belong to it. Its Token usage includes that of its Agent runs.
_Avoid_: execution, invocation, job

**Agent run**:
One call to an Ieakaso agent (the Applicant Agent or the Seasoned Recruiter) inside a Run.
_Avoid_: subagent execution, agent call

### Agents

**Job Application Assistant**:
The role that manages an application process for the candidate: it runs the steps, starts the Agent runs and passes drafts and reviews between them. It is never an Agent run.
_Avoid_: orchestrator, Cover Letter Manager, application agent

**Applicant Agent**:
The agent that writes the candidate's application drafts, in the candidate's voice and only from the candidate's files.
_Avoid_: AI candidate, candidate assistant, writer

**Seasoned Recruiter**:
The agent that reviews the Applicant Agent's drafts as an experienced recruiter for the Job ad's domain.
_Avoid_: reviewer, grader, recruiter agent

### Cover letters

**Cover letter**:
A letter from the candidate to the employer for one Job ad, drafted by the Applicant Agent and refined through Review rounds.
_Avoid_: motivation letter, application letter

**Review**:
The Seasoned Recruiter's assessment of one Cover letter draft: a Review score, what to remove, rewrite and improve, and questions for the candidate.
_Avoid_: feedback, critique, grading

**Review score**:
The 0-100 score a Review gives a draft.
_Avoid_: rating, grade, Job analysis score

**Round**:
One draft by the Applicant Agent followed by one Review of it.
_Avoid_: iteration, cycle, pass

**Plateau**:
The Seasoned Recruiter's judgment that no change backed by the candidate's files would raise a draft's Review score.
_Avoid_: cannot be improved, max quality, dead end

**Session**:
One coding-assistant session, from its start (or `/clear`) to its end; resuming a session continues it. Ieakaso keeps nothing from a Session once it ends.
_Avoid_: conversation, chat

**Token usage**:
The tokens a Run or Agent run spends, split into input, output and cache read. Ieakaso shows tokens only, never a cost. Session token usage is the sum of its Runs only; other activity in the Session is not counted.
_Avoid_: spend, consumption, credits, cost

**Context fill**:
How full the model's context window is: tokens in the conversation out of the window size.
_Avoid_: context size, context usage
