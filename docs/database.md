# Database model

`db/ieakaso_db.json` holds one record per Application (terms in `CONTEXT.md`). It is User data: gitignored, never committed. A valid example lives in `db/ieakaso_db_example.json`.

Only the tracker module (`src/ieakaso/tracker/`) reads and writes the file. Modes call its CLI; the viewer imports it. Agents never edit the JSON by hand. The tracker creates the file on its first write.

## Rules

- **One record per Application.** The candidate applies at most once per Application. Two Job ads joined through `**Also at:**` are still one record.
- **Records are created only by modes.** job-analyzer creates a record as `lead`. The viewer edits records; it never creates or deletes them.
- **No text, only paths.** The ad, the Job analysis and the Cover letter stay in `output/applications/<id>/`; the db holds their paths, relative to the repo root.
- **Nothing derived is stored.** Counts by status or stage are computed when needed.
- **Keys are snake_case.** Dates are `yyyy-mm-dd`. A value not known yet is `null`.

## Structure

```jsonc
{
  "meta": { "schema_version": 1 },
  "records": [
    {
      "id": "acme_senior-backend-engineer_2026-10-10",
      "company": "Acme",
      "position": "Senior Backend Engineer",
      "status": "applied",
      "status_history": [
        { "status": "lead", "on": "2026-10-10" },
        { "status": "applied", "on": "2026-10-12" }
      ],
      "stage": 1,
      "stages": [
        { "name": "recruiter screening", "description": "30 min call" },
        { "name": "technical interview", "description": "" }
      ],
      "created_at": "2026-10-10",
      "analysis": {
        "on": "2026-10-10",
        "doc": "output/applications/acme_senior-backend-engineer_2026-10-10/acme_senior-backend-engineer_2026-10-10_job-analysis.md",
        "score": 84,
        "verdict": "Apply"
      },
      "applied_on": "2026-10-12",
      "home_office": "twice a week in the office",
      "location": { "city": "Berlin", "country": "DE" },
      "salary_expectation": { "period": "yearly", "min": 95000, "max": 105000, "currency": "EUR" },
      "cover_letter": "output/applications/acme_senior-backend-engineer_2026-10-10/acme_senior-backend-engineer_2026-10-10_cover-letter.md",
      "source": {
        "board": "LinkedIn",
        "board_url": "https://www.linkedin.com/jobs/view/123",
        "form_url": "https://jobs.acme.example/apply/123",
        "job_description": "output/applications/acme_senior-backend-engineer_2026-10-10/acme_senior-backend-engineer_2026-10-10_job-ad.md"
      },
      "contacts": [
        { "contact_type": "recruiter", "name": "Jane Doe", "linkedin_url": "https://www.linkedin.com/in/janedoe", "email": null }
      ],
      "notes": ""
    }
  ]
}
```

## Fields

"Written by" says who sets the field: **analyzer** (the job-analyzer mode), **cover-letter** (the cover-letter mode), **candidate** (in the viewer) or **tracker** (automatically). Fields marked "no" in the Editable column are shown in the viewer but can't be changed there.

### `meta`

| Field | Type | Written by | Meaning |
|---|---|---|---|
| `schema_version` | integer | tracker | Version of this model. Currently `1`. |

### Record

| Field | Type | Written by | Editable | Meaning |
|---|---|---|---|---|
| `id` | string | analyzer | no | The Application ID, `<company>_<position>_<yyyy-mm-dd>` in lowercase kebab-case, with an optional extra word after a collision. Never changes. |
| `company` | string | analyzer | yes | The company, as named in the Job ad. |
| `position` | string | analyzer | yes | The Position, as named in the Job ad. |
| `status` | enum | analyzer, candidate | yes | The Application status; see [Statuses](#statuses). New records start as `lead`. Any status can be changed to any other. |
| `status_history` | list | tracker | no | Every status the record has had, oldest first: `{status, on}`. A change of `status` appends an entry. |
| `stage` | integer | candidate | yes | The current Interview stage: `0` before the interview process starts, otherwise a 1-based position in `stages`. Never more than the number of `stages`. |
| `stages` | list | candidate | yes | The company's interview process, in order: `{name, description}`. Empty until the candidate learns it. |
| `created_at` | date | analyzer | no | The date of the first Job analysis; the same date as in the `id`. |
| `analysis` | object | analyzer | no | The latest Job analysis; see below. |
| `applied_on` | date or `null` | candidate | yes | When the candidate sent the application. Filled with today when `status` becomes `applied` and it is empty. |
| `home_office` | string or `null` | analyzer, candidate | yes | Free text on how often the Position needs the office (e.g. "twice a week", "fully remote"). |
| `location` | object | analyzer, candidate | yes | `{city, country}`; `country` is an ISO 3166-1 alpha-2 code (`DE`). Either may be `null`. |
| `salary_expectation` | object or `null` | candidate | yes | The Salary expectation the candidate gave in the application form; see below. Never the salary the ad offers (that is in the Job analysis). |
| `cover_letter` | path or `null` | cover-letter | no | The kept Cover letter draft. |
| `source` | object | analyzer, candidate | partly | Where the ad was found and where to apply; see below. |
| `contacts` | list | analyzer, candidate | yes | People at the company or agency; see below. The analyzer adds one only when the ad names a person. |
| `notes` | string | candidate | yes | Free text, e.g. why the candidate desisted. |

### `analysis`

Only job-analyzer writes it, on every run.

| Field | Type | Meaning |
|---|---|---|
| `on` | date | The date of the latest Job analysis. |
| `doc` | path | The Job analysis file, `<id>_job-analysis.md`. |
| `score` | integer | The final score, 0-100. |
| `verdict` | enum | `Top applicant`, `Apply`, `Stretch` or `Don't apply`. |

### `salary_expectation`

| Field | Type | Meaning |
|---|---|---|
| `period` | enum | `yearly`, `monthly`, `daily` or `hourly`. |
| `min` | number | The lower end; equal to `max` when the candidate gave one amount. |
| `max` | number | The upper end. |
| `currency` | string | ISO 4217 code (`EUR`). |

### `source`

| Field | Type | Written by | Editable | Meaning |
|---|---|---|---|---|
| `board` | string or `null` | analyzer, candidate | yes | The site where the candidate found the ad (e.g. LinkedIn, the company site). |
| `board_url` | URL or `null` | analyzer, candidate | yes | The ad's URL on that site; `null` for a pasted ad. Other copies of the same ad stay in the Job ad file's `**Also at:**` field. |
| `form_url` | URL or `null` | candidate | yes | Where the candidate applies. The same as `board_url` when they apply on the board itself. |
| `job_description` | path | analyzer | no | The Job ad file, `<id>_job-ad.md`. |

### `contacts[]`

| Field | Type | Meaning |
|---|---|---|
| `contact_type` | enum | `recruiter`, `hiring_manager`, `referral` or `other`. |
| `name` | string | The person's name. |
| `linkedin_url` | URL or `null` | Their LinkedIn profile. |
| `email` | string or `null` | Their email address. |

## Statuses

| Value | Meaning |
|---|---|
| `lead` | The candidate had the Job ad analysed and has not applied yet. |
| `desisted` | The candidate stopped pursuing the Application, at any point, including a failed attempt to apply. |
| `applied` | The candidate sent the application. |
| `no_answer` | No feedback 30 days after applying. The viewer suggests it on launch; only the candidate sets it. |
| `interviewing` | The company started its interview process with the candidate. |
| `offer` | The company made the candidate an offer. |
| `not_selected` | The company decided not to go on with the application. |

The usual path is `lead` → `applied` or `desisted`, then `applied` → `no_answer`, `interviewing` or `not_selected`, then `interviewing` → `offer`, `not_selected` or `desisted`. These paths are guidance only: the viewer allows any change, so mistakes can be corrected.

## When job-analyzer runs again

A later Job analysis of an existing Application updates `analysis` and fills fields that are still empty. It never overwrites a value that's already there, and never touches `status`, `stage`, `stages`, `contacts`, `notes` or `salary_expectation`.
