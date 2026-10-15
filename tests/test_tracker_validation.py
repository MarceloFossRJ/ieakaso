"""Record validation: enums, dates, snake_case keys, stage, paths. The example in db/ must validate."""

import json
from pathlib import Path

import pytest
from tracker_fakes import lead, record

from ieakaso.tracker import STATUSES, InvalidRecordError, load, problems, validate

REPO = Path(__file__).resolve().parents[1]


def test_the_example_record_and_the_lead_record_are_valid():
    assert problems(record()) == []
    assert problems(lead()) == []


def test_the_example_in_db_validates():
    db = load(REPO / "db" / "ieakaso_db_example.json")

    assert db.error is None
    assert len(db.records) == 1
    assert db.records[0] == record()


def test_the_example_is_the_one_in_the_database_doc():
    doc = (REPO / "docs" / "database.md").read_text()
    block = doc.split("```jsonc\n", 1)[1].split("```", 1)[0]

    assert json.loads(block) == json.loads((REPO / "db" / "ieakaso_db_example.json").read_text())


def broken(**overrides) -> dict:
    return record(**overrides)


@pytest.mark.parametrize(
    "bad",
    [
        broken(status="ghosted"),
        broken(created_at="2026-13-01"),
        broken(created_at="10/10/2026"),
        broken(applied_on="2026-1-2"),
        broken(stage=3),  # only 2 stages
        broken(stage=-1),
        broken(stage=True),
        broken(stage="1"),
        broken(company=""),
        broken(company=5),
        broken(analysis={"on": "2026-10-10", "doc": "a.md", "score": 101, "verdict": "Apply"}),
        broken(analysis={"on": "2026-10-10", "doc": "a.md", "score": 80, "verdict": "Maybe"}),
        broken(analysis={"on": "2026-10-10", "doc": "a.md", "score": 80}),
        broken(cover_letter="/abs/path.md"),
        broken(cover_letter="../outside.md"),
        broken(cover_letter="a\\b.md"),
        broken(salary_expectation={"period": "weekly", "min": 1, "max": 2, "currency": "EUR"}),
        broken(salary_expectation={"period": "yearly", "min": 3, "max": 2, "currency": "EUR"}),
        broken(salary_expectation={"period": "yearly", "min": 1, "max": 2, "currency": "euro"}),
        broken(location={"city": "Berlin", "country": "Germany"}),
        broken(location={"city": "Berlin"}),
        broken(contacts=[{"contact_type": "boss", "name": "J", "linkedin_url": None, "email": None}]),
        broken(contacts=[{"contact_type": "recruiter", "name": "", "linkedin_url": None, "email": None}]),
        broken(stages=[{"name": "", "description": ""}]),
        broken(status_history=[{"status": "lead", "on": "yesterday"}]),
        broken(status_history=[]),
        broken(notes=None),
        broken(surprise="x"),
        broken(source={"board": None, "board_url": None, "form_url": None}),
    ],
)
def test_invalid_records_are_reported(bad: dict):
    assert problems(bad)
    with pytest.raises(InvalidRecordError):
        validate(bad)


def test_keys_must_be_snake_case():
    bad = record()
    bad["source"]["formUrl"] = "x"

    assert any("formUrl" in p for p in problems(bad))


def test_a_missing_key_is_reported():
    bad = record()
    del bad["notes"]

    assert any("notes" in p for p in problems(bad))


def test_every_status_is_accepted():
    for status in STATUSES:
        assert problems(record(status=status)) == []


def test_not_a_record_at_all():
    assert problems("nope")
