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

    assert json.loads(db_path.read_text()) == {"meta": {"schema_version": 2}, "records": []}


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


def v1(rec: dict) -> dict:
    """The record as schema_version 1 stored it: no company_research."""
    return {key: value for key, value in rec.items() if key != "company_research"}


def test_a_version_1_file_is_migrated_on_load_and_written_as_version_2_on_save(db_path: Path):
    write_db(db_path, v1(lead()), version=1)

    db = load(db_path)

    assert db.error is None
    assert db.records == [lead()]
    assert json.loads(db_path.read_text())["meta"]["schema_version"] == 1  # loading alone writes nothing
    save(db)
    assert json.loads(db_path.read_text()) == {"meta": {"schema_version": 2}, "records": [lead()]}


def with_report(root: Path, rec: dict) -> None:
    report = root / rec["company_research"]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("x")


def test_migration_fills_company_research_when_the_report_is_in_the_given_root(db_path: Path):
    root = db_path.parents[1]
    rec = record()
    with_report(root, rec)
    write_db(db_path, v1(rec), v1(lead(id="b_c_2026-10-11")), version=1)

    records = load(db_path, root=root).records

    assert records[0]["company_research"] == rec["company_research"]
    assert records[1]["company_research"] is None


def test_migration_looks_in_the_given_root_wherever_the_db_is(tmp_path: Path):
    root, elsewhere = tmp_path / "repo", tmp_path / "backup" / "old.json"
    rec = record()
    with_report(root, rec)
    write_db(elsewhere, v1(rec), version=1)

    assert load(elsewhere, root=root).records[0]["company_research"] == rec["company_research"]


def test_without_a_root_migration_sets_null(db_path: Path):
    rec = record()
    with_report(db_path.parents[1], rec)
    write_db(db_path, v1(rec), version=1)

    assert load(db_path).records[0]["company_research"] is None


def test_a_bare_relative_path_is_migrated_without_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    write_db(Path("ieakaso_db.json"), v1(lead()), version=1)

    db = load(Path("ieakaso_db.json"))

    assert db.error is None and db.records == [lead()]


def test_a_migrated_file_can_be_saved_without_a_conflict(db_path: Path):
    write_db(db_path, v1(lead()), version=1)
    db = load(db_path)

    save(db)
    save(db)

    assert load(db_path).records == [lead()]


@pytest.mark.parametrize("version", [0, 3, "2", None])
def test_any_other_schema_version_is_refused_and_left_alone(db_path: Path, version):
    write_db(db_path, lead(), version=version)
    before = db_path.read_text()

    db = load(db_path)

    assert db.error and "schema_version" in db.error
    with pytest.raises(InvalidDbError):
        save(db)
    assert db_path.read_text() == before


def test_an_invalid_version_1_record_is_still_an_error(db_path: Path):
    write_db(db_path, v1(lead(status="nope")), version=1)

    assert "invalid record" in load(db_path).error
