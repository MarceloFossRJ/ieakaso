"""The viewer, driven with Textual's pilot on a fake repo. Never touches the real db/."""

import json
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Input, Select, SelectionList, Static
from tracker_fakes import ID, TODAY, lead, record, write_db

from ieakaso.tracker import DB_PATH
from ieakaso.viewer import ViewerApp
from ieakaso.viewer.screens import DetailScreen, NoAnswerScreen

SIZE = (200, 60)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def db_file(root: Path) -> Path:
    return root / DB_PATH


def stored(root: Path) -> list[dict]:
    return json.loads(db_file(root).read_text())["records"]


def make_app(root: Path, opened: list | None = None, poll: float = 0.05) -> ViewerApp:
    return ViewerApp(
        root, today=lambda: TODAY, opener=(opened.append if opened is not None else None), poll_interval=poll
    )


def rows(app: ViewerApp) -> list[list[str]]:
    table = app.query_one(DataTable)
    return [[str(cell) for cell in table.get_row_at(i)] for i in range(table.row_count)]


def ids(app: ViewerApp) -> list[str]:
    table = app.query_one(DataTable)
    return [table.coordinate_to_cell_key((i, 0)).row_key.value for i in range(table.row_count)]


def hint(app: ViewerApp) -> str:
    return str(app.query_one("#hint", Static).render())


def two_records(root: Path):
    write_db(
        db_file(root),
        lead(id="old", company="Old Co", created_at="2026-09-01"),
        record(id="new", company="New Co", created_at="2026-10-10", applied_on="2026-10-12"),
    )


# the table


async def test_the_table_lists_the_fields_newest_first(root: Path):
    two_records(root)

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        app = pilot.app
        assert ids(app) == ["new", "old"]
        assert rows(app)[0] == [
            "New Co",
            "Senior Backend Engineer",
            "Applied",
            "1/2 recruiter screening",
            "Apply 84",
            "Berlin, DE",
            "2026-10-10",
            "2026-10-12",
        ]
        assert rows(app)[1][2:5] == ["Lead", "-", "Apply 84"]
        assert rows(app)[1][7] == ""


async def test_h_hides_and_shows_the_closed_statuses(root: Path):
    write_db(
        db_file(root),
        lead(id="a", created_at="2026-10-01"),
        lead(id="b", created_at="2026-10-02", status="desisted"),
        record(id="c", created_at="2026-10-03", status="not_selected"),
        record(id="d", created_at="2026-10-04", status="offer"),
    )

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert len(ids(pilot.app)) == 4
        await pilot.press("h")
        assert ids(pilot.app) == ["d", "a"]
        await pilot.press("h")
        assert len(ids(pilot.app)) == 4


async def test_a_missing_file_shows_an_empty_table_and_a_hint(root: Path):
    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert pilot.app.query_one(DataTable).row_count == 0
        assert "job-analyzer" in hint(pilot.app)
    assert not db_file(root).exists()


async def test_invalid_json_shows_the_error_and_refuses_to_save(root: Path):
    db_file(root).parent.mkdir(parents=True)
    db_file(root).write_text("{ broken")

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        app = pilot.app
        assert "not valid JSON" in hint(app)
        assert app.query_one(DataTable).row_count == 0
        assert app.apply("x", {"notes": "n"}) is False
    assert db_file(root).read_text() == "{ broken"


async def test_the_table_reloads_when_the_file_changes(root: Path):
    write_db(db_file(root), lead())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert len(ids(pilot.app)) == 1
        write_db(db_file(root), lead(), lead(id="b_c_2026-10-11", created_at="2026-10-11"))
        await pilot.pause(0.3)
        assert ids(pilot.app) == ["b_c_2026-10-11", ID]


async def test_a_file_that_appears_is_picked_up(root: Path):
    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        write_db(db_file(root), lead())
        await pilot.pause(0.3)
        assert ids(pilot.app) == [ID]


# the detail screen


async def open_detail(pilot) -> DetailScreen:
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()
    assert isinstance(pilot.app.screen, DetailScreen)
    return pilot.app.screen


async def press(pilot, widget_id: str) -> None:
    """Press a button of the current screen (clicking fails for buttons scrolled out of view)."""
    pilot.app.screen.query_one(f"#{widget_id}", Button).press()
    await pilot.pause()
    await pilot.pause()


async def type_into(pilot, widget_id: str, text: str, submit: bool = True) -> None:
    field = pilot.app.screen.query_one(f"#{widget_id}", Input)
    field.value = text
    field.focus()
    await pilot.pause()
    if submit:
        await pilot.press("enter")
    await pilot.pause()


async def test_enter_opens_the_detail_and_escape_goes_back(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        assert pilot.app.screen.query_one("#company", Input).value == "Acme"
        assert pilot.app.screen.query_one("#sal_min", Input).value == "95000"
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, DetailScreen)


async def test_an_edit_is_saved_at_once(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await type_into(pilot, "company", "Acme GmbH")
        await type_into(pilot, "notes", "called them")
        assert stored(root)[0]["company"] == "Acme GmbH"
        assert stored(root)[0]["notes"] == "called them"
        assert rows(pilot.app)[0][0] == "Acme GmbH"


async def test_leaving_a_field_saves_it_too(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await type_into(pilot, "home_office", "fully remote", submit=False)
        pilot.app.screen.query_one("#position", Input).focus()
        await pilot.pause()
        assert stored(root)[0]["home_office"] == "fully remote"


async def test_an_empty_optional_field_becomes_null(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await type_into(pilot, "home_office", "")
        await type_into(pilot, "form_url", "")
        await type_into(pilot, "city", "")
        assert stored(root)[0]["home_office"] is None
        assert stored(root)[0]["source"]["form_url"] is None
        assert stored(root)[0]["location"] == {"city": None, "country": "DE"}


async def test_an_invalid_value_is_not_saved_and_the_field_is_restored(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await type_into(pilot, "applied_on", "next week")
        assert stored(root)[0]["applied_on"] == "2026-10-12"
        assert pilot.app.screen.query_one("#applied_on", Input).value == "2026-10-12"


async def test_the_status_can_be_set_to_any_status(root: Path):
    write_db(db_file(root), lead())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        pilot.app.screen.query_one("#status", Select).value = "applied"
        await pilot.pause()
        await pilot.pause()
        saved = stored(root)[0]
        assert saved["status"] == "applied"
        assert saved["applied_on"] == "2026-10-15"
        assert saved["status_history"][-1] == {"status": "applied", "on": "2026-10-15"}
        assert pilot.app.screen.query_one("#applied_on", Input).value == "2026-10-15"
        pilot.app.screen.query_one("#status", Select).value = "lead"
        await pilot.pause()
        assert stored(root)[0]["status"] == "lead"
        assert len(stored(root)[0]["status_history"]) == 3


async def test_the_current_stage_can_be_chosen(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        pilot.app.screen.query_one("#stage", Select).value = 2
        await pilot.pause()
        assert stored(root)[0]["stage"] == 2


async def test_stages_can_be_added_edited_and_removed(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await press(pilot, "add_stage")
        assert [s["name"] for s in stored(root)[0]["stages"]] == [
            "recruiter screening",
            "technical interview",
            "New stage",
        ]
        await type_into(pilot, "stage_2_name", "onsite")
        assert stored(root)[0]["stages"][2]["name"] == "onsite"
        await type_into(pilot, "stage_0_description", "45 min")
        assert stored(root)[0]["stages"][0]["description"] == "45 min"
        # removing the current stage (1) moves the current stage back to 0
        await press(pilot, "stage_0_remove")
        assert [s["name"] for s in stored(root)[0]["stages"]] == ["technical interview", "onsite"]
        assert stored(root)[0]["stage"] == 0
        assert isinstance(pilot.app.screen, DetailScreen)


async def test_removing_a_stage_before_the_current_one_keeps_pointing_at_it(root: Path):
    write_db(db_file(root), record(stage=2))

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await press(pilot, "stage_0_remove")
        assert stored(root)[0]["stage"] == 1
        assert stored(root)[0]["stages"][0]["name"] == "technical interview"


async def test_contacts_can_be_added_edited_and_removed(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await press(pilot, "add_contact")
        assert len(stored(root)[0]["contacts"]) == 2
        await type_into(pilot, "contact_1_name", "Bob Smith")
        await type_into(pilot, "contact_1_email", "bob@acme.example")
        pilot.app.screen.query_one("#contact_1_type", Select).value = "hiring_manager"
        await pilot.pause()
        assert stored(root)[0]["contacts"][1] == {
            "contact_type": "hiring_manager",
            "name": "Bob Smith",
            "linkedin_url": None,
            "email": "bob@acme.example",
        }
        await press(pilot, "contact_0_remove")
        assert [c["name"] for c in stored(root)[0]["contacts"]] == ["Bob Smith"]


async def test_the_salary_expectation_is_saved_once_complete(root: Path):
    write_db(db_file(root), lead())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await type_into(pilot, "sal_min", "90000")
        await type_into(pilot, "sal_max", "100000")
        await type_into(pilot, "sal_currency", "eur")
        assert stored(root)[0]["salary_expectation"] is None
        pilot.app.screen.query_one("#sal_period", Select).value = "yearly"
        await pilot.pause()
        assert stored(root)[0]["salary_expectation"] == {
            "period": "yearly",
            "min": 90000,
            "max": 100000,
            "currency": "EUR",
        }


async def test_clearing_the_salary_expectation_makes_it_null(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        for field in ("sal_min", "sal_max", "sal_currency"):
            await type_into(pilot, field, "")
        pilot.app.screen.query_one("#sal_period", Select).clear()
        await pilot.pause()
        assert stored(root)[0]["salary_expectation"] is None


async def test_read_only_fields_have_no_inputs(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        input_ids = {w.id for w in pilot.app.screen.query(Input)}
        assert not input_ids & {"id", "created_at", "analysis", "status_history", "job_description", "cover_letter"}
        text = " ".join(str(w.render()) for w in pilot.app.screen.query(Static))
        assert ID in text and "2026-10-10" in text and "Apply, 84/100" in text


# saving: conflicts


async def test_a_conflicting_save_reloads_and_asks_to_redo(root: Path):
    write_db(db_file(root), record())

    async with make_app(root, poll=3600).run_test(size=SIZE) as pilot:  # no watcher: the save itself must notice
        await open_detail(pilot)
        write_db(db_file(root), record(notes="written elsewhere"))
        await type_into(pilot, "company", "Mine")
        assert stored(root)[0]["company"] == "Acme"
        assert stored(root)[0]["notes"] == "written elsewhere"
        assert pilot.app.screen.query_one("#company", Input).value == "Acme"
        assert pilot.app.screen.query_one("#notes", Input).value == "written elsewhere"
        assert any("do your edit again" in n.message for n in pilot.app._notifications)


async def test_an_edit_after_the_watcher_reloaded_keeps_the_other_changes(root: Path):
    write_db(db_file(root), record())

    async with make_app(root).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        write_db(db_file(root), record(notes="written elsewhere"))
        await pilot.pause(0.3)
        assert pilot.app.screen.query_one("#notes", Input).value == "written elsewhere"
        await type_into(pilot, "company", "Mine")
        assert stored(root)[0]["company"] == "Mine"
        assert stored(root)[0]["notes"] == "written elsewhere"


# the No answer suggestion


def old_applications(root: Path):
    write_db(
        db_file(root),
        record(id="a", company="A", applied_on="2026-08-01", created_at="2026-08-01"),
        record(id="b", company="B", applied_on="2026-08-02", created_at="2026-08-02"),
        record(id="c", company="C", applied_on="2026-10-10", created_at="2026-10-10"),
    )


async def test_the_launch_dialog_lists_applications_without_an_answer(root: Path):
    old_applications(root)

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, NoAnswerScreen)
        assert {s.value for s in pilot.app.screen.query_one(SelectionList).options} == {"a", "b"}
    assert {r["status"] for r in stored(root)} == {"applied"}


async def test_ticked_applications_become_no_answer_and_the_rest_are_suggested_again(root: Path):
    old_applications(root)

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        pilot.app.screen.query_one(SelectionList).select("a")
        await pilot.click("#confirm")
        await pilot.pause()
        by_id = {r["id"]: r for r in stored(root)}
        assert by_id["a"]["status"] == "no_answer"
        assert by_id["a"]["status_history"][-1] == {"status": "no_answer", "on": "2026-10-15"}
        assert by_id["b"]["status"] == "applied" and by_id["c"]["status"] == "applied"

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, NoAnswerScreen)
        assert [s.value for s in pilot.app.screen.query_one(SelectionList).options] == ["b"]


async def test_not_now_changes_nothing(root: Path):
    old_applications(root)
    before = db_file(root).read_text()

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.click("#skip")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, NoAnswerScreen)
    assert db_file(root).read_text() == before


async def test_no_dialog_without_candidates(root: Path):
    two_records(root)

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        assert not isinstance(pilot.app.screen, NoAnswerScreen)


# opening documents


def with_files(root: Path, *rec: dict) -> None:
    write_db(db_file(root), *rec)
    for item in rec:
        for rel in (item["source"]["job_description"], item["analysis"]["doc"], item["cover_letter"]):
            if rel:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("x")


async def test_keys_open_the_documents_of_the_selected_application(root: Path):
    with_files(root, record())
    opened: list[Path] = []

    async with make_app(root, opened).run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("a", "j", "c")
        await pilot.pause()
    assert [p.name for p in opened] == [f"{ID}_job-ad.md", f"{ID}_job-analysis.md", f"{ID}_cover-letter.md"]
    assert all(p.is_relative_to(root) for p in opened)


async def test_the_detail_buttons_open_the_documents(root: Path):
    with_files(root, record())
    opened: list[Path] = []

    async with make_app(root, opened).run_test(size=SIZE) as pilot:
        await open_detail(pilot)
        await press(pilot, "open_letter")
    assert [p.name for p in opened] == [f"{ID}_cover-letter.md"]


async def test_a_missing_cover_letter_or_file_opens_nothing(root: Path):
    with_files(root, lead())
    opened: list[Path] = []

    async with make_app(root, opened).run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("c")
        (root / lead()["analysis"]["doc"]).unlink()
        await pilot.press("j")
        await pilot.pause()
        messages = [n.message for n in pilot.app._notifications]
    assert opened == []
    assert any("no Cover letter" in m for m in messages)
    assert any("missing" in m for m in messages)


async def test_the_viewer_never_creates_or_deletes_records(root: Path):
    two_records(root)

    async with make_app(root).run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press("n", "d", "delete", "ctrl+n")
        await pilot.pause()
    assert [r["id"] for r in stored(root)] == ["old", "new"]
