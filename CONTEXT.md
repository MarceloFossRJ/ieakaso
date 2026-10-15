# Ieakaso

A local job-search assistant that drafts applications for a candidate; the candidate acts on them.

## Language

**User data**:
The candidate's own files, which are gitignored and never leave their machine: `config.yml`, `db/system_status.json`, `db/ieakaso_db.json`, temporary files left in `db/` by an interrupted write, and everything in `input/` and `output/` except the tracked placeholders (`.gitkeep` files and `input/documents/README.md`).
_Avoid_: personal data, private files

**Fresh state**:
The repo with no user data, exactly as after a clone and before the first `/ieakaso init`. The development cleaner (`ieakaso.devtools.cleaner`) returns a repo to it.
_Avoid_: clean install, reset state, empty repo

**Set-up state**:
The repo with the candidate's setup (`config.yml`, `db/system_status.json`, everything in `input/`) and no Applications: exactly as after a complete `/ieakaso init` and before the first Job analysis. The development cleaner returns a repo to it with `clean --applications`.
_Avoid_: post-init state, half-clean, soft reset

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
The ad for one Position, as the candidate supplies it: a URL Ieakaso can read, or the ad's text pasted in. When the requirements or responsibilities at the same URL change, the candidate decides whether it is still the same Job ad; the same job posted on another site is a different Job ad unless the candidate says otherwise.
_Avoid_: job description, JD, posting

**Position**:
The job a Job ad offers, as named in the ad (e.g. Senior Backend Engineer).
_Avoid_: role, job title

**Application**:
Everything Ieakaso holds for the candidate's pursuit of one Job ad, from its first Job analysis on, whether or not the candidate ever applies. A later Job analysis of the same Job ad belongs to the same Application. The candidate applies at most once per Application, wherever the ad was found and wherever the application form is.
_Avoid_: job ad folder, candidature, application folder

**Application ID**:
The name of an Application: its company, its Position and the date of its first Job analysis (e.g. `acme_senior-backend-engineer_2026-10-10`). It never changes once given, whatever day later work on the Application happens. When two Job ads would get the same Application ID, the candidate adds a word to tell them apart (e.g. `acme_senior-backend-engineer_2026-10-10_berlin`).
_Avoid_: job ad ID, index, slug

**Application status**:
Where an Application stands, set by the candidate: Lead, Desisted, Applied, No answer, Interviewing, Offer or Not selected. A new Application starts as Lead. Any status can be changed to any other, so mistakes can be corrected.
_Avoid_: state, phase, folder

**Lead**:
An Application whose Job ad the candidate found promising enough to have analysed, and has not applied to yet.
_Avoid_: prospect, candidate job, opportunity

**Applied**:
The Application's status once the candidate has actually sent the application.
_Avoid_: submitted, sent

**Interviewing**:
The company has contacted the candidate to start or continue its interview process.
_Avoid_: in process, screening

**Offer**:
The company has made the candidate an offer.
_Avoid_: accepted, hired

**Not selected**:
The company decided not to go on with the candidate's application.
_Avoid_: rejected, declined

**Desisted**:
The candidate stopped pursuing the Application, at any point: before applying, after applying, or during interviews, including when an attempt to apply failed.
_Avoid_: withdrawn, cancelled, abandoned

**No answer**:
The company has given no feedback 30 days after the candidate applied. Ieakaso suggests it; only the candidate sets it.
_Avoid_: ghosted, no response, stale

**Interview stage**:
One named step of a company's interview process for an Application (e.g. recruiter screening), as the company describes it. An Application's current stage is its position in that list, 0 before the process starts.
_Avoid_: round, step, phase

**Salary expectation**:
The pay the candidate stated in an application form's expected-salary question, as an amount or a range for a period. It is never the salary the Job ad offers.
_Avoid_: compensation, salary, pay

**Job ad fetcher**:
The code that reads a Job ad from a URL when WebFetch can't, and writes it as text. The candidate chooses it over pasting the ad.
_Avoid_: scraper, crawler, downloader

**Job analysis**:
The report the job-analyzer mode writes on how well the Parsed CV fits one Job ad, ending in a Verdict.
_Avoid_: CV score, fit report

**Company research**:
The report on the company behind an Application's Job ad: what it does, its product, its latest releases, its financial moment, its culture, what employees say about it, the Role impact and red flags, each fact with a dated source. The job-analyzer mode makes it after the Job analysis; the candidate never asks for it on its own. It never changes the Job analysis's score or Verdict.
_Avoid_: company report, company profile, due diligence

**Role impact**:
The part of the Company research that judges how much the Position can move the company's product or business, from the Job ad and the research alone, never from the candidate's files.
_Avoid_: fit, role fit, relation to the role

**Verdict**:
The job analysis's advice on whether to apply: Top applicant, Apply, Stretch or Don't apply. Stretch and Don't apply advise against applying; the candidate can override either.
_Avoid_: suggestion, recommendation

**Run**:
One `/ieakaso <mode>` call, including the setup check and any init, cv-parser or job-analyzer it triggers. It lasts until the next Run or the end of the Session, so follow-up questions about its result belong to it. Its Token usage includes that of its Agent runs.
_Avoid_: execution, invocation, job

**Agent run**:
One call to an Ieakaso agent (the Applicant Agent, the Seasoned Recruiter or the Company Researcher) inside a Run.
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

**Company Researcher**:
The agent that researches one topic of a Company research on the web and reports dated, sourced findings; several run in parallel, one per topic, and the job-analyzer mode assembles them. It never reads the candidate's files.
_Avoid_: researcher, scout, company agent

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
