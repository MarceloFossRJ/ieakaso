"""CV versions in the tracker: adding, the current one, labels, linking records, and the auto-fill on Applied."""

from pathlib import Path

import pytest
from tracker_fakes import ID, TODAY, cv_version, lead, record, write_db

from ieakaso.tracker import (
    InvalidRecordError,
    RecordNotFoundError,
    add_cv_version,
    current_cv_version,
    link_applied_records,
    load,
    next_cv_version_id,
    save,
    set_cv_version_label,
    set_cv_version_path,
    set_record_cv_version,
    set_status,
    update_record,
)

MAIN = "cv_2026-10-01"
NEWER = "cv_2026-10-08"
TAILORED = "cv_2026-10-09"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "db" / "ieakaso_db.json"


def versions() -> list[dict]:
    """Two main versions, then a Tailored CV for ID, which is the latest captured."""
    return [
        cv_version(),
        cv_version(id=NEWER, label="cv_en_334", captured_at="2026-10-08"),
        cv_version(id=TAILORED, label="cv_for_acme", captured_at="2026-10-09", tailored_for=ID),
    ]


# the current version


def test_the_current_version_is_the_latest_captured_one_that_is_not_tailored(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())

    assert current_cv_version(load(db_path))["id"] == NEWER


def test_there_is_no_current_version_without_versions(db_path: Path):
    write_db(db_path, lead())

    assert current_cv_version(load(db_path)) is None


def test_a_tailored_cv_alone_is_never_current(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version(tailored_for=ID)])

    assert current_cv_version(load(db_path)) is None


# IDs


def test_the_first_id_of_a_day_is_cv_and_the_date(db_path: Path):
    assert next_cv_version_id(load(db_path), TODAY) == "cv_2026-10-15"


def test_further_ids_of_the_same_day_count_up_from_2(db_path: Path):
    db = load(db_path)
    assert next_cv_version_id(db, TODAY) == "cv_2026-10-15"
    add_cv_version(db, "cv_2026-10-15", "a", "input/candidate/documents/cv/cv_2026-10-15/a.pdf", TODAY)
    assert next_cv_version_id(db, TODAY) == "cv_2026-10-15_2"
    add_cv_version(db, "cv_2026-10-15_2", "b", "input/candidate/documents/cv/cv_2026-10-15_2/b.pdf", TODAY)

    assert next_cv_version_id(db, TODAY) == "cv_2026-10-15_3"


# adding


def test_add_a_main_cv_version(db_path: Path):
    db = load(db_path)

    added = add_cv_version(db, MAIN, "cv_en_333", f"input/candidate/documents/cv/{MAIN}/cv_en_333.pdf", TODAY)

    assert added == {
        "id": MAIN,
        "label": "cv_en_333",
        "path": f"input/candidate/documents/cv/{MAIN}/cv_en_333.pdf",
        "captured_at": "2026-10-15",
        "tailored_for": None,
    }
    assert db.cv_versions == [added]
    save(db)
    assert load(db_path).cv_versions == [added]


def test_adding_a_tailored_cv_links_it_to_its_application(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)

    added = add_cv_version(db, TAILORED, "cv_for_acme", f"input/candidate/documents/cv/{TAILORED}/c.pdf", TODAY, tailored_for=ID)

    assert added["tailored_for"] == ID
    assert db.find(ID)["cv_version"] == TAILORED


def test_a_tailored_cv_for_an_unknown_application_is_refused_and_changes_nothing(db_path: Path):
    db = load(db_path)

    with pytest.raises(RecordNotFoundError):
        add_cv_version(db, TAILORED, "x", f"input/candidate/documents/cv/{TAILORED}/c.pdf", TODAY, tailored_for="nope")

    assert db.cv_versions == []


def test_an_id_already_used_or_an_invalid_one_is_refused(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        add_cv_version(db, MAIN, "again", "input/candidate/documents/cv/x/a.pdf", TODAY)
    with pytest.raises(InvalidRecordError):
        add_cv_version(db, "nope", "x", "input/candidate/documents/cv/x/a.pdf", TODAY)

    assert len(db.cv_versions) == 1


# paths


def test_set_a_version_path(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)

    changed = set_cv_version_path(db, MAIN, "input/candidate/documents/cv/cv_2026-10-01/moved.pdf")

    assert changed["path"] == "input/candidate/documents/cv/cv_2026-10-01/moved.pdf"
    assert db.find_cv_version(MAIN)["path"] == changed["path"]


def test_an_invalid_path_or_an_unknown_version_is_refused_and_changes_nothing(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)
    before = db.find_cv_version(MAIN)["path"]

    with pytest.raises(InvalidRecordError):
        set_cv_version_path(db, MAIN, "/abs/path.pdf")
    with pytest.raises(RecordNotFoundError):
        set_cv_version_path(db, "cv_2000-01-01", "input/x.pdf")

    assert db.find_cv_version(MAIN)["path"] == before


# labels


def test_set_a_label(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)

    set_cv_version_label(db, MAIN, "Main CV, English")

    assert db.cv_versions[0]["label"] == "Main CV, English"
    save(db)
    assert load(db_path).cv_versions[0]["label"] == "Main CV, English"


def test_an_empty_label_or_an_unknown_version_is_refused(db_path: Path):
    write_db(db_path, lead(), cv_versions=[cv_version()])
    db = load(db_path)

    with pytest.raises(InvalidRecordError):
        set_cv_version_label(db, MAIN, "  ")
    with pytest.raises(RecordNotFoundError):
        set_cv_version_label(db, "cv_2030-01-01", "x")

    assert db.cv_versions[0]["label"] == "cv_en_333"


# a record's version


def test_set_the_version_of_a_record_and_clear_it(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())
    db = load(db_path)

    assert set_record_cv_version(db, ID, MAIN)["cv_version"] == MAIN
    assert set_record_cv_version(db, ID, None)["cv_version"] is None


def test_a_tailored_cv_can_be_set_only_on_its_own_application(db_path: Path):
    write_db(db_path, lead(), lead(id="b_c_2026-10-11"), cv_versions=versions())
    db = load(db_path)

    assert set_record_cv_version(db, ID, TAILORED)["cv_version"] == TAILORED
    with pytest.raises(InvalidRecordError):
        set_record_cv_version(db, "b_c_2026-10-11", TAILORED)

    assert db.find("b_c_2026-10-11")["cv_version"] is None


def test_an_unknown_version_or_application_is_refused(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())
    db = load(db_path)

    with pytest.raises(RecordNotFoundError):
        set_record_cv_version(db, ID, "cv_2030-01-01")
    with pytest.raises(RecordNotFoundError):
        set_record_cv_version(db, "nope", MAIN)


# linking records past Lead


def test_link_applied_records_sets_every_record_with_an_applied_on_and_no_version(db_path: Path):
    write_db(
        db_path,
        record(id="past", applied_on="2026-09-20"),
        record(id="desisted-after-applying", status="desisted", applied_on="2026-09-21"),
        record(id="has-one", applied_on="2026-09-22", cv_version=MAIN),
        lead(id="still-lead"),
        cv_versions=[cv_version(), cv_version(id=NEWER, label="n", captured_at="2026-10-08")],
    )
    db = load(db_path)

    linked = link_applied_records(db, NEWER)

    assert linked == ["past", "desisted-after-applying"]
    assert {r["id"]: r["cv_version"] for r in db.records} == {
        "past": NEWER,
        "desisted-after-applying": NEWER,
        "has-one": MAIN,
        "still-lead": None,
    }


# Applied fills the version, like applied_on


def test_applied_fills_an_empty_cv_version_with_the_current_one(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())

    rec = set_status(load(db_path), ID, "applied", TODAY)

    assert rec["cv_version"] == NEWER


def test_applied_keeps_a_cv_version_already_there(db_path: Path):
    write_db(db_path, lead(cv_version=TAILORED), cv_versions=versions())

    assert set_status(load(db_path), ID, "applied", TODAY)["cv_version"] == TAILORED


def test_applied_without_any_version_leaves_it_null(db_path: Path):
    write_db(db_path, lead())

    assert set_status(load(db_path), ID, "applied", TODAY)["cv_version"] is None


def test_other_statuses_do_not_fill_the_version(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())

    assert set_status(load(db_path), ID, "desisted", TODAY)["cv_version"] is None


def test_an_edit_that_sets_applied_fills_the_version_too(db_path: Path):
    write_db(db_path, lead(), cv_versions=versions())

    assert update_record(load(db_path), ID, {"status": "applied"}, TODAY)["cv_version"] == NEWER
