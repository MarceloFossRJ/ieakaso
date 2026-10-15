"""The tracker's store: load and save of db/ieakaso_db.json, on temp files."""

import json
from pathlib import Path

import pytest
from tracker_fakes import lead, record, write_db

from ieakaso.tracker import ConflictError, InvalidDbError, InvalidRecordError, load, save


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "db" / "ieakaso_db.json"


def test_a_missing_file_loads_as_empty(db_path: Path):
    db = load(db_path)

    assert db.records == []
    assert db.error is None
    assert not db_path.exists()


def test_the_first_save_creates_the_file_and_its_folder(db_path: Path):
    save(load(db_path))

    assert json.loads(db_path.read_text()) == {"meta": {"schema_version": 1}, "records": []}


def test_records_round_trip(db_path: Path):
    write_db(db_path, record(), lead(id="b_c_2026-10-11"))

    db = load(db_path)
    save(db)

    assert [r["id"] for r in load(db_path).records] == [record()["id"], "b_c_2026-10-11"]
    assert load(db_path).records[0] == record()


def test_save_leaves_no_temp_file_behind(db_path: Path):
    write_db(db_path, record())
    save(load(db_path))

    assert [p.name for p in db_path.parent.iterdir()] == ["ieakaso_db.json"]


def test_invalid_json_is_reported_and_never_overwritten(db_path: Path):
    db_path.parent.mkdir(parents=True)
    db_path.write_text("{ not json")

    db = load(db_path)

    assert db.error and "ieakaso_db.json" in db.error
    with pytest.raises(InvalidDbError):
        save(db)
    assert db_path.read_text() == "{ not json"


@pytest.mark.parametrize("text", ["{}", "[]", '{"meta": {}, "records": {}}', '{"records": []}'])
def test_json_that_is_not_a_tracker_file_is_an_error(db_path: Path, text: str):
    db_path.parent.mkdir(parents=True)
    db_path.write_text(text)

    assert load(db_path).error


def test_a_file_with_an_invalid_record_is_an_error_naming_it(db_path: Path):
    write_db(db_path, record(status="ghosted"))

    assert "acme_senior" in (load(db_path).error or "")


def test_save_refuses_when_the_file_changed_since_it_was_read(db_path: Path):
    write_db(db_path, record())
    db = load(db_path)

    write_db(db_path, record(), lead(id="b_c_2026-10-11"))

    with pytest.raises(ConflictError):
        save(db)
    assert len(load(db_path).records) == 2


def test_save_refuses_when_the_file_appeared_since_it_was_read_as_missing(db_path: Path):
    db = load(db_path)
    write_db(db_path, record())

    with pytest.raises(ConflictError):
        save(db)


def test_save_after_save_is_not_a_conflict(db_path: Path):
    db = load(db_path)
    save(db)
    db.records.append(record())
    save(db)

    assert len(load(db_path).records) == 1


def test_save_validates_every_record_and_writes_nothing_when_one_is_invalid(db_path: Path):
    write_db(db_path, record())
    before = db_path.read_text()
    db = load(db_path)
    db.records.append(record(id="x", status="nope"))

    with pytest.raises(InvalidRecordError):
        save(db)
    assert db_path.read_text() == before


def test_changed_returns_true_only_when_the_file_differs_from_what_was_read(db_path: Path):
    write_db(db_path, record())
    db = load(db_path)
    assert not db.changed_on_disk()

    write_db(db_path)

    assert db.changed_on_disk()
