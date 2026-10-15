"""The tracker's operations on a loaded db: upsert from a Job analysis, status, cover letter, edits, No answer."""

from datetime import date
from pathlib import Path

import pytest
from tracker_fakes import FOLDER, ID, TODAY, lead, payload, record, write_db

from ieakaso.tracker import (
    InvalidRecordError,
    RecordNotFoundError,
    load,
    no_answer_suggestions,
    problems,
    set_cover_letter,
    set_status,
    update_record,
    upsert_from_analysis,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "db" / "ieakaso_db.json"


def test_a_new_application_becomes_a_lead(db_path: Path):
    db = load(db_path)

    rec, created = upsert_from_analysis(db, payload(), TODAY)

    assert created
    assert db.records == [rec]
    assert rec["status"] == "lead"
    assert rec["status_history"] == [{"status": "lead", "on": "2026-10-15"}]
    assert rec["created_at"] == "2026-10-15"
    assert rec["analysis"]["on"] == "2026-10-10"
    assert rec["stage"] == 0 and rec["stages"] == []
    assert rec["applied_on"] is None and rec["salary_expectation"] is None and rec["cover_letter"] is None
    assert rec["source"]["form_url"] is None
    assert rec["notes"] == ""
    assert problems(rec) == []


def test_the_analysis_date_defaults_to_today(db_path: Path):
    data = payload()
    del data["analysis"]["on"]

    rec, _ = upsert_from_analysis(load(db_path), data, TODAY)

    assert rec["analysis"]["on"] == "2026-10-15"


def test_optional_fields_of_the_payload_may_be_left_out(db_path: Path):
    data = payload()
    for key in ("home_office", "location", "contacts"):
        del data[key]
    del data["source"]["board"], data["source"]["board_url"]

    rec, _ = upsert_from_analysis(load(db_path), data, TODAY)

    assert rec["location"] == {"city": None, "country": None}
    assert rec["home_office"] is None and rec["contacts"] == []
    assert rec["source"]["board"] is None and rec["source"]["board_url"] is None


def test_contacts_in_the_payload_are_kept_on_a_new_record(db_path: Path):
    contact = {"contact_type": "recruiter", "name": "Jane Doe", "linkedin_url": None, "email": "j@acme.example"}

    rec, _ = upsert_from_analysis(load(db_path), payload(contacts=[contact]), TODAY)

    assert rec["contacts"] == [contact]


def test_an_invalid_payload_changes_nothing(db_path: Path):
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        upsert_from_analysis(db, payload(analysis={"doc": "x.md", "score": 500, "verdict": "Apply"}), TODAY)
    assert db.records == []


@pytest.mark.parametrize("key", ["status", "stage", "stages", "notes", "salary_expectation", "cover_letter"])
def test_the_payload_cannot_set_what_the_analyzer_does_not_own(db_path: Path, key: str):
    with pytest.raises(InvalidRecordError):
        upsert_from_analysis(load(db_path), payload(**{key: "x"}), TODAY)


def test_a_missing_required_payload_field_is_reported(db_path: Path):
    data = payload()
    del data["company"]

    with pytest.raises(InvalidRecordError, match="company"):
        upsert_from_analysis(load(db_path), data, TODAY)


def test_a_rerun_updates_the_analysis_only(db_path: Path):
    write_db(db_path, record())
    db = load(db_path)
    again = payload(
        analysis={"on": "2026-10-20", "doc": f"{FOLDER}/{ID}_job-analysis.md", "score": 91, "verdict": "Top applicant"}
    )

    rec, created = upsert_from_analysis(db, again, date(2026, 10, 20))

    assert not created
    assert len(db.records) == 1
    assert rec["analysis"]["score"] == 91 and rec["analysis"]["verdict"] == "Top applicant"
    assert rec["analysis"]["on"] == "2026-10-20"
    assert rec["created_at"] == "2026-10-10"
    assert {k: v for k, v in rec.items() if k != "analysis"} == {k: v for k, v in record().items() if k != "analysis"}


def test_a_rerun_never_overwrites_a_value_already_there(db_path: Path):
    write_db(db_path, record())
    db = load(db_path)
    again = payload(
        company="ACME GmbH",
        position="Other",
        home_office="fully remote",
        location={"city": "Munich", "country": "DE"},
        source={"board": "Indeed", "board_url": "https://indeed.example/1", "job_ad": "other/ad.md"},
    )

    rec, _ = upsert_from_analysis(db, again, TODAY)

    assert rec["company"] == "Acme" and rec["position"] == "Senior Backend Engineer"
    assert rec["home_office"] == "twice a week in the office"
    assert rec["location"] == {"city": "Berlin", "country": "DE"}
    assert rec["source"]["board"] == "LinkedIn"
    assert rec["source"]["board_url"] == "https://www.linkedin.com/jobs/view/123"
    assert rec["source"]["job_ad"] == f"{FOLDER}/{ID}_job-ad.md"


def test_a_rerun_fills_fields_still_empty(db_path: Path):
    existing = lead(home_office=None, location={"city": None, "country": "DE"})
    existing["source"].update(board=None, board_url=None)
    write_db(db_path, existing)

    rec, _ = upsert_from_analysis(load(db_path), payload(), TODAY)

    assert rec["home_office"] == "twice a week"
    assert rec["location"] == {"city": "Berlin", "country": "DE"}
    assert rec["source"]["board"] == "LinkedIn"
    assert rec["source"]["board_url"] == "https://www.linkedin.com/jobs/view/123"


def test_a_rerun_never_touches_status_stage_stages_contacts_notes_or_salary(db_path: Path):
    mine = record(notes="called them", status="interviewing")
    write_db(db_path, mine)
    new_contact = {"contact_type": "other", "name": "Bob", "linkedin_url": None, "email": None}

    rec, _ = upsert_from_analysis(load(db_path), payload(contacts=[new_contact]), TODAY)

    for key in ("status", "status_history", "stage", "stages", "contacts", "notes", "salary_expectation"):
        assert rec[key] == mine[key], key


def test_set_status_appends_to_the_history(db_path: Path):
    write_db(db_path, lead())
    db = load(db_path)

    rec = set_status(db, ID, "desisted", date(2026, 10, 16))

    assert rec["status"] == "desisted"
    assert rec["status_history"] == [{"status": "lead", "on": "2026-10-10"}, {"status": "desisted", "on": "2026-10-16"}]
    assert rec["applied_on"] is None


def test_applied_fills_an_empty_applied_on_with_today(db_path: Path):
    write_db(db_path, lead())

    rec = set_status(load(db_path), ID, "applied", TODAY)

    assert rec["applied_on"] == "2026-10-15"


def test_applied_keeps_an_applied_on_already_there(db_path: Path):
    write_db(db_path, lead(applied_on="2026-10-12"))

    rec = set_status(load(db_path), ID, "applied", TODAY)

    assert rec["applied_on"] == "2026-10-12"


def test_any_status_can_be_set_from_any_status(db_path: Path):
    write_db(db_path, record(status="offer"))

    rec = set_status(load(db_path), ID, "lead", TODAY)

    assert rec["status"] == "lead"


def test_setting_the_same_status_changes_nothing(db_path: Path):
    write_db(db_path, record())

    rec = set_status(load(db_path), ID, "applied", TODAY)

    assert rec == record()


def test_an_unknown_status_is_refused(db_path: Path):
    write_db(db_path, lead())
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        set_status(db, ID, "ghosted", TODAY)
    assert db.records == [lead()]


def test_an_unknown_record_is_reported(db_path: Path):
    with pytest.raises(RecordNotFoundError):
        set_status(load(db_path), "nope", "applied", TODAY)
    with pytest.raises(RecordNotFoundError):
        set_cover_letter(load(db_path), "nope", "a.md")


def test_set_cover_letter(db_path: Path):
    write_db(db_path, lead())

    rec = set_cover_letter(load(db_path), ID, f"{FOLDER}/{ID}_cover-letter.md")

    assert rec["cover_letter"] == f"{FOLDER}/{ID}_cover-letter.md"
    assert problems(rec) == []


def test_set_cover_letter_overwrites_the_previous_path(db_path: Path):
    write_db(db_path, record())

    rec = set_cover_letter(load(db_path), ID, "output/other.md")

    assert rec["cover_letter"] == "output/other.md"


def test_set_cover_letter_refuses_a_path_outside_the_repo(db_path: Path):
    write_db(db_path, record())

    with pytest.raises(InvalidRecordError):
        set_cover_letter(load(db_path), ID, "/etc/passwd")


# update_record: the candidate's edits from the viewer


def test_update_record_changes_editable_fields(db_path: Path):
    write_db(db_path, record())

    rec = update_record(
        load(db_path),
        ID,
        {"company": "Acme GmbH", "notes": "n", "stage": 2, "contacts": [], "home_office": None},
        TODAY,
    )

    assert (rec["company"], rec["notes"], rec["stage"], rec["contacts"], rec["home_office"]) == (
        "Acme GmbH",
        "n",
        2,
        [],
        None,
    )


def test_update_record_edits_the_editable_source_fields_only(db_path: Path):
    write_db(db_path, record())

    rec = update_record(load(db_path), ID, {"source": {"form_url": "https://x.example/apply"}}, TODAY)

    assert rec["source"]["form_url"] == "https://x.example/apply"
    assert rec["source"]["board"] == "LinkedIn"
    with pytest.raises(InvalidRecordError):
        update_record(load(db_path), ID, {"source": {"job_ad": "other.md"}}, TODAY)


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "x"},
        {"created_at": "2026-01-01"},
        {"analysis": {"on": "2026-01-01", "doc": "a", "score": 1, "verdict": "Apply"}},
        {"status_history": []},
        {"cover_letter": "x.md"},
        {"surprise": 1},
    ],
)
def test_update_record_refuses_what_is_not_editable(db_path: Path, changes: dict):
    write_db(db_path, record())
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        update_record(db, ID, changes, TODAY)
    assert db.records == [record()]


def test_update_record_refuses_an_invalid_result_and_leaves_the_record(db_path: Path):
    write_db(db_path, record())
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        update_record(db, ID, {"stage": 5}, TODAY)
    with pytest.raises(InvalidRecordError):
        update_record(db, ID, {"stages": []}, TODAY)  # stage 1 would exceed 0 stages
    assert db.records == [record()]


def test_update_record_status_goes_through_set_status(db_path: Path):
    write_db(db_path, lead())

    rec = update_record(load(db_path), ID, {"status": "applied", "notes": "sent"}, TODAY)

    assert rec["status"] == "applied" and rec["applied_on"] == "2026-10-15"
    assert rec["status_history"][-1] == {"status": "applied", "on": "2026-10-15"}
    assert rec["notes"] == "sent"


def test_update_record_applied_on_given_with_applied_wins_over_today(db_path: Path):
    write_db(db_path, lead())

    rec = update_record(load(db_path), ID, {"status": "applied", "applied_on": "2026-10-13"}, TODAY)

    assert rec["applied_on"] == "2026-10-13"


# No answer suggestions


def test_no_answer_suggestions_are_applied_records_more_than_30_days_old(db_path: Path):
    write_db(
        db_path,
        record(id="old", applied_on="2026-09-14"),  # 31 days
        record(id="edge", applied_on="2026-09-15"),  # 30 days: not yet
        record(id="new", applied_on="2026-10-10"),
        record(id="interviewing", status="interviewing", applied_on="2026-08-01"),
        record(id="lead", status="lead", applied_on=None),
        record(id="no-date", applied_on=None),
    )

    found = no_answer_suggestions(load(db_path), TODAY)

    assert [r["id"] for r in found] == ["old"]
