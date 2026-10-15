"""Fakes for the tracker's and the viewer's tests: a Job analysis payload and a full record, on fake repos only."""

import copy
import json
from datetime import date
from pathlib import Path

from ieakaso.tracker.schema import SCHEMA_VERSION

TODAY = date(2026, 10, 15)
ID = "acme_senior-backend-engineer_2026-10-10"
FOLDER = f"output/applications/{ID}"


def payload(**overrides) -> dict:
    """What job-analyzer hands the tracker after a Job analysis."""
    data = {
        "id": ID,
        "company": "Acme",
        "position": "Senior Backend Engineer",
        "analysis": {"on": "2026-10-10", "doc": f"{FOLDER}/{ID}_job-analysis.md", "score": 84, "verdict": "Apply"},
        "home_office": "twice a week",
        "location": {"city": "Berlin", "country": "DE"},
        "source": {
            "board": "LinkedIn",
            "board_url": "https://www.linkedin.com/jobs/view/123",
            "job_ad": f"{FOLDER}/{ID}_job-ad.md",
        },
        "contacts": [],
    }
    data.update(overrides)
    return data


def record(**overrides) -> dict:
    """A complete, valid record: the example from docs/database.md."""
    data = {
        "id": ID,
        "company": "Acme",
        "position": "Senior Backend Engineer",
        "status": "applied",
        "status_history": [{"status": "lead", "on": "2026-10-10"}, {"status": "applied", "on": "2026-10-12"}],
        "stage": 1,
        "stages": [
            {"name": "recruiter screening", "description": "30 min call"},
            {"name": "technical interview", "description": ""},
        ],
        "created_at": "2026-10-10",
        "analysis": {"on": "2026-10-10", "doc": f"{FOLDER}/{ID}_job-analysis.md", "score": 84, "verdict": "Apply"},
        "applied_on": "2026-10-12",
        "home_office": "twice a week in the office",
        "location": {"city": "Berlin", "country": "DE"},
        "salary_expectation": {"period": "yearly", "min": 95000, "max": 105000, "currency": "EUR"},
        "cover_letter": f"{FOLDER}/{ID}_cover-letter.md",
        "company_research": f"{FOLDER}/{ID}_company-research.md",
        "source": {
            "board": "LinkedIn",
            "board_url": "https://www.linkedin.com/jobs/view/123",
            "form_url": "https://jobs.acme.example/apply/123",
            "job_ad": f"{FOLDER}/{ID}_job-ad.md",
        },
        "contacts": [
            {
                "contact_type": "recruiter",
                "name": "Jane Doe",
                "linkedin_url": "https://www.linkedin.com/in/janedoe",
                "email": None,
            }
        ],
        "notes": "",
    }
    data.update(overrides)
    return copy.deepcopy(data)


def lead(**overrides) -> dict:
    """A record as job-analyzer leaves it: lead, nothing the candidate adds yet."""
    base = record(
        status="lead",
        status_history=[{"status": "lead", "on": "2026-10-10"}],
        stage=0,
        stages=[],
        applied_on=None,
        salary_expectation=None,
        cover_letter=None,
        company_research=None,
        contacts=[],
        home_office=None,
    )
    base["source"]["form_url"] = None
    base.update(overrides)
    return base


def write_db(path: Path, *records: dict, version: int = SCHEMA_VERSION) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": {"schema_version": version}, "records": list(records)}, indent=2) + "\n")
    return path
