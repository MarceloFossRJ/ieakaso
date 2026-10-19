# Init

Sets the candidate up for a job search: checks their documents, collects `config.yml`, records the result in `db/system_status.json`, and writes a Conflict report of where the other documents disagree with the CV.

Runs when the user calls `/ieakaso init`, and from the setup check in `ai/skills/ieakaso/SKILL.md` when setup is missing or incomplete.

Init is idempotent. Running it again re-checks everything, keeps what is already confirmed, and only asks about what is missing or what the user wants to change. Never overwrite a value in `config.yml` without the user's confirmation, and never delete or move the user's files.

---

## Step 1: Read the current state

- `db/system_status.json` (format in "Status file" below). If it does not exist or is not valid JSON, copy `db/system_status_example.json` to `db/system_status.json` first.
- `config.yml`, if it exists
- `config_example.yml`, for the key layout

If this is a re-run (`init.status` is `"completed"`), tell the user init already ran on `init.completed_at` and that you will re-check documents and show the current config.

## Step 2: Documents

Create any of these folders that are missing: `input/documents/cv/`, `input/documents/linkedin/`, `input/documents/reference_letters/`. Leave every other folder under `input/documents/` as it is.

### CV — mandatory

Accepted files: `.pdf`, `.docx`, `.md`, `.txt`, `.tex`, not empty.

- **None found:** tell the user the CV is required and ask for it. If they give a file path, copy it into `input/documents/cv/` (copy, never move). Without a CV, stop here: save the status file with `init.status: "in_progress"` and tell the user to run `/ieakaso init` again once the CV is in place.
- **One found:** use it.
- **Several found** (e.g. one per language): if `documents.cv.path` in the status file still points to one of them, keep it; otherwise ask which one is the main CV.

### LinkedIn PDF — strongly recommended

Any `.pdf` in `input/documents/linkedin/`.

If none is found, recommend it strongly: recruiters compare it with the CV, and it often holds detail the CV leaves out. Give the export steps:

1. Open your LinkedIn profile.
2. Click **Resources** (or **More**) under your name.
3. Click **Save to PDF**.
4. Put the file in `input/documents/linkedin/`.

The user can add it now (then re-check) or answer "skip".

### Reference letters — suggested

Any accepted file in `input/documents/reference_letters/`.

If none is found, suggest adding them: they back up achievements with a third party's words. The user can add them now or answer "skip".

"Skip" is recorded as `"skipped"` and stays until the next `/ieakaso init`, which asks again.

### Parsed CV

Once the main CV is chosen (it becomes the Source CV) and the LinkedIn PDF and reference letters are recorded, run `ai/skills/ieakaso/modes/cv-parser.md`; it also writes their Parsed documents. If it ends without exit 0 (the CV can't be parsed, or the candidate keeps a hand-edited `input/cv.md`), record the CV as `found` and carry on with init; the setup check runs the parser again before the next mode.

Settle the LinkedIn PDF and reference letters (found or skipped) before starting Step 3, so the user never has two open questions at once and a bare "skip" or "ok" is never ambiguous.

## Step 3: Config

### Pre-fill

Read the main CV and the LinkedIn PDF (if present) and pre-fill what they state: name, last name, email, phone, location, LinkedIn, portfolio, GitHub, languages and proficiency. Keep values already in `config.yml` over pre-filled ones. Never guess a value the documents do not state; leave it empty.

Target positions and search location are always asked, never pre-filled.

### Confirm, one section at a time

Go through four sections in this order, one message each:

1. Personal details (`candidate.*` except languages)
2. Languages (`candidate.languages`)
3. Target positions (`target_positions.main`, `target_positions.siblings`)
4. Search location (`search_location`)

Show every item numbered with its current value and its source (`from CV`, `from LinkedIn`, `in config.yml`, or `empty`). Ask the user to reply `ok` to confirm all, or `<n>: <new value>` to change one, or `<n>: skip` for an optional field. Repeat the section until every item is confirmed or skipped. A bare `ok` on a section with an empty optional field records that field as `skipped`; it cannot confirm an empty mandatory field.

```
Personal details
 1. name: John (from CV)
 2. last_name: Doe (from CV)
 3. email: john.doe@provider.com (from CV)
 4. phone: (empty)
 ...
Reply "ok", or "<n>: <new value>", or "<n>: skip".
```

On a re-run, show the current values the same way; `ok` keeps them.

### Fields and allowed values

The fields init tracks are the keys of `config.fields` in `db/system_status_example.json`. When adding or removing a field, update that file, this section, and `config_example.yml` together.

**Mandatory** (cannot be skipped):
- `candidate.name`, `candidate.last_name`, `candidate.email`, `candidate.location`
- at least one entry in `candidate.languages`
- at least one entry in `target_positions.main`
- `search_location.country`

**Optional:** `candidate.phone`, `candidate.linkedin`, `candidate.portfolio_url`, `candidate.github`, `target_positions.siblings`, `search_location.cities`, `search_location.timezone`, `search_location.visa_status`, and `seniority` on any position.

**Allowed values:**
- `languages[].name`: ISO language code (`en`, `de`, `pt-br`)
- `languages[].proficiency`: `A1`, `A2`, `B1`, `B2`, `C1`, `C2`, `native`
- `target_positions.siblings[].priority`: `main` (same weight as the main target), `secondary` (good fit), `stretch`
- `search_location.cities[].priority`: `main`, `secondary`; a city `name` of `Any` means the whole country

Reject other values and ask again.

### Write `config.yml`

Write the confirmed values to `config.yml` at the repository root, with the same keys and order as `config_example.yml`. Omit skipped optional fields.

## Step 4: Status file and summary

Write `db/system_status.json` (create `db/` if missing), then show a short summary:

- CV, LinkedIn PDF, reference letters: found / skipped / missing
- Config: confirmed, with any skipped optional fields
- Only facts: everything in `input/` and `config.yml` is the candidate's Personal knowledge base (terms in `CONTEXT.md`). Ieakaso uses all of it as fact and never checks it, so it must hold only what is true.
- What's next: `/ieakaso job-analyzer <job-url or job-ad text>` to score the CV against a job ad and get a verdict

Then run Step 5. Its chat part comes after this summary, as the last thing init shows.

## Step 5: Conflict report

Compare the candidate's documents with the Parsed CV and write a Conflict report (terms in `CONTEXT.md`). Do this yourself; it takes judgement (the same job under two titles, a date written two ways), so it is not part of the CV parser. Run it on every init, including a re-run where no document changed. It never blocks init, never changes `init.status`, and never edits a document or `config.yml`.

### What to compare

The Parsed CV `input/cv.md` is the reference. Compare it with:

1. **The LinkedIn profile's Parsed document** `input/linkedin.md`: employers, titles, dates, locations, team sizes, budgets and other numbers, achievements, education, certifications, languages, the headline and summary.
2. **Each Reference letter's Parsed document** `input/reference-letters/*.md`: titles, dates, team sizes and claimed results.
3. **`config.yml`**: name, last name, email, phone, location, LinkedIn, GitHub, portfolio and languages (`candidate.*`), where the CV states them.

Compare only the Parsed documents that exist: one the parser could not write (a warning in Step 2) is left out, and the report's header says so. Never read the Source documents, and leave the memory files out (`professional-self-reflection.md` and the others): job-analyzer checks those against the CV on every run.

**No Parsed CV:** when `input/cv.md` does not exist (the parser could not write it in Step 2), write no report, and say in chat that the check runs once the CV is parsed.

**Nothing to compare:** when there is no `input/linkedin.md` and no file in `input/reference-letters/`, write no report, and say in chat that there was nothing to compare the CV with yet, and that adding the LinkedIn PDF or reference letters and running `/ieakaso init` again will check them.

### What counts

- **A conflict:** the same fact, stated differently. The same job with a different title, employer or dates; a different number for the same thing; a different language level. Treat the CV as right and the other document as the one to fix.
- **Only on one side:** a fact one document holds and the other does not (a degree, a job, a certification, an achievement). A gap, not a conflict.
- **Different positioning:** the LinkedIn headline or summary presents the candidate differently from the CV's summary (e.g. one leads with AI/ML, the other does not).

Report only what the documents say: quote or closely paraphrase each side, and never guess which side is true or why they differ.

Rate each conflict:

| Relevance | When | Examples |
|---|---|---|
| High | A recruiter or a background check would catch it | Different job titles or employers; dates more than a month apart; numbers that don't match (a 1M€ budget against a 9-figure one) |
| Medium | The same fact, with a different scope or level | Team size; countries; a language level |
| Low | Cosmetic | A one-month date shift; a typo; the same title worded differently |

### Write the report

Write a new file `output/conflict-reports/<yyyy-mm-dd>T<hh-mm>_conflicts.md`, with the local date and time of this run (create the folder if missing). Never overwrite a report: if that name exists (two runs in the same minute), add `-2`, `-3` and so on before `_conflicts`. Older reports stay as they are, as the history of past checks.

```markdown
# Conflict report

> **Checked:** [yyyy-mm-dd hh:mm] | **CV:** `input/cv.md` (from [Source CV path]) | **Compared with:** `input/linkedin.md` (from [LinkedIn PDF path]), `input/reference-letters/[name].md` (from [letter path]), `config.yml`

[Documents left out, if any: which, and why]

The CV is the reference: fix the other document to match it, or the Source CV if the CV is wrong.

## Conflicts

| # | Relevance | Topic | CV says | Other document says | Why it matters |
|---|---|---|---|---|---|
| 1 | High / Medium / Low | [...] | [...] | [document]: [...] | [one line] |

## Only on one side

| Only in [document] | Only in the CV |
|---|---|
| [...] | [...] |

## Different positioning

- **CV:** [...]
- **[document]:** [...]
```

Order the conflicts High first, then Medium, then Low, and number them in that order. A section with nothing in it reads "None found". When there are no conflicts, gaps or positioning differences at all, still write the file, with "No conflicts found." under the header, so the candidate can see the check ran.

### Show it in chat

After the Step 4 summary:

- The High and Medium conflicts, one line each (relevance, topic, the two versions), and how many Low ones there are; or "No conflicts found."
- The report's path
- The next step, when there is a conflict: fix the document that disagrees with the CV (or the Source CV, if the CV is wrong), put the new file in its folder under `input/documents/`, and run `/ieakaso init` again, which writes a new report

---

## Status file

`db/system_status.json` records setup state only. It never holds a copy of the config values. It is gitignored; its committed starting point, with every value missing, is `db/system_status_example.json`, which also shows the format.

- `init.status`: `not_started` (fresh copy of the example), `in_progress` (stopped before the end, e.g. no CV), or `completed`
- `init.completed_at`, `config.validated_at`: ISO 8601 timestamps, `null` until set
- `init.version`: the version of this status format; currently `1`
- `config.fields`: one entry per tracked field (lists count as one field), each:
  - `confirmed`: has a value the user approved
  - `skipped`: optional, and the user chose not to provide it; omitted from `config.yml`. Mandatory fields can never be `skipped`.
  - `missing`: not answered yet
- `documents.cv` and `documents.linkedin`: `status` and `path` (`null` when not found)
- `documents.cv.parsed`: written only by the CV parser (`ai/skills/ieakaso/modes/cv-parser.md`), never by hand: the source path and fingerprints, `parser_version` and `parsed_at` of the last parse. Missing means `input/cv.md` has not been parsed yet. Keep it when you rewrite the status file.
- `documents.reference_letters`: `status` and `paths` (a list, empty when not found)
- `documents.*.status`: `found`, `skipped` (LinkedIn PDF and reference letters only), or `missing`

**Completion rule:** set `init.status` to `"completed"` only when every config field is `confirmed` or `skipped`, the CV is `found`, and the LinkedIn PDF and reference letters are `found` or `skipped`. `missing` appears only while `init.status` is `"not_started"` or `"in_progress"`.
