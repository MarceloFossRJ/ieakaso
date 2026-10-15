"""The viewer's main screen: the table of Applications, and every write to the db."""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static

from ieakaso.tracker import (
    CLOSED_STATUSES,
    DB_PATH,
    ConflictError,
    Db,
    InvalidRecordError,
    TrackerError,
    load,
    no_answer_suggestions,
    save,
    set_status,
    update_record,
)
from ieakaso.viewer.screens import DetailScreen, NoAnswerScreen, label

STATUS_STYLES = {
    "lead": "cyan",
    "desisted": "dim",
    "applied": "blue",
    "no_answer": "yellow",
    "interviewing": "magenta",
    "offer": "bold green",
    "not_selected": "red",
}
VERDICT_STYLES = {"Top applicant": "bold green", "Apply": "green", "Stretch": "yellow", "Don't apply": "red"}
COLUMNS = ("Company", "Position", "Status", "Stage", "Verdict / score", "Location", "Analysed", "Applied")
DOCUMENTS = {  # key -> (what the candidate sees, where the path is in the record)
    "ad": ("Job ad", lambda record: record["source"]["job_ad"]),
    "analysis": ("Job analysis", lambda record: record["analysis"]["doc"]),
    "letter": ("Cover letter", lambda record: record["cover_letter"]),
    "research": ("Company research", lambda record: record["company_research"]),
}
NO_FILE_HINT = "No Applications yet. Run `/ieakaso job-analyzer <job ad>` in your coding assistant to track one."


def location_label(record: dict) -> str:
    return ", ".join(part for part in (record["location"]["city"], record["location"]["country"]) if part)


class ViewerApp(App):
    TITLE = "Ieakaso: Applications"
    CSS = """
    #hint { padding: 0 1; height: auto; }
    #hint.error { color: $error; text-style: bold; }
    #hint.empty { display: none; }
    """
    BINDINGS: ClassVar[list] = [
        Binding("h", "toggle_closed", "Hide/show closed"),
        Binding("a", "open_document('ad')", "Job ad"),
        Binding("j", "open_document('analysis')", "Job analysis"),
        Binding("c", "open_document('letter')", "Cover letter"),
        Binding("r", "open_document('research')", "Company research"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        root: Path,
        *,
        today: Callable[[], date] = date.today,
        opener: Callable[[Path], None] | None = None,
        poll_interval: float = 1.0,
    ):
        super().__init__()
        self.root = root
        self.today = today
        self.opener = opener or (lambda path: None)
        self.poll_interval = poll_interval
        self.hide_closed = False
        self.tracker_db: Db = Db(root / DB_PATH)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="hint")
        yield DataTable(id="applications", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.table = self.query_one("#applications", DataTable)
        self.hint = self.query_one("#hint", Static)
        self.table.add_columns(*COLUMNS)
        self.reload()
        self.set_interval(self.poll_interval, self._poll)
        found = no_answer_suggestions(self.tracker_db, self.today()) if not self.tracker_db.error else []
        if found:
            self.push_screen(NoAnswerScreen(found), self._mark_no_answer)

    # reading

    def reload(self) -> None:
        self.tracker_db = load(self.root / DB_PATH, root=self.root)
        self.refresh_table()

    def _poll(self) -> None:
        if not self.tracker_db.changed_on_disk():
            return
        self.reload()
        self.notify("db/ieakaso_db.json changed on disk; reloaded.")
        for screen in self.screen_stack:
            if isinstance(screen, DetailScreen):
                screen.db_reloaded()

    def visible_records(self) -> list[dict]:
        records = sorted(self.tracker_db.records, key=lambda r: (r["created_at"], r["id"]), reverse=True)
        if self.hide_closed:
            records = [r for r in records if r["status"] not in CLOSED_STATUSES]
        return records

    def refresh_table(self) -> None:
        selected = self.selected_id()
        self.table.clear()
        records = self.visible_records()
        for record in records:
            self.table.add_row(*self._cells(record), key=record["id"])
        if selected in {r["id"] for r in records}:
            self.table.move_cursor(row=self.table.get_row_index(selected))
        self._set_hint(bool(records))

    def _cells(self, record: dict) -> list[Text | str]:
        stages, analysis = record["stages"], record["analysis"]
        stage = f"{record['stage']}/{len(stages)}" if stages else "-"
        if 0 < record["stage"] <= len(stages):
            stage += f" {stages[record['stage'] - 1]['name']}"
        return [
            record["company"],
            record["position"],
            Text(label(record["status"]), style=STATUS_STYLES[record["status"]]),
            stage,
            Text(f"{analysis['verdict']} {analysis['score']}", style=VERDICT_STYLES[analysis["verdict"]]),
            location_label(record),
            analysis["on"],
            record["applied_on"] or "",
        ]

    def _set_hint(self, has_rows: bool) -> None:
        db = self.tracker_db
        if db.error:
            text, kind = f"{db.error}\nNothing can be saved until the file is fixed or removed.", "error"
        elif not db.records:
            text, kind = NO_FILE_HINT, ""
        elif not has_rows:
            text, kind = "Every Application is closed (Desisted or Not selected). Press h to show them.", ""
        else:
            text, kind = "", "empty"
        self.hint.update(text)
        self.hint.set_classes(kind)

    def selected_id(self) -> str | None:
        if not self.table.row_count:
            return None
        return self.table.coordinate_to_cell_key(self.table.cursor_coordinate).row_key.value

    # writing: every change goes through the tracker

    def write(self, operation: Callable[[Db], object]) -> bool:
        """Run a tracker operation on the db and save it at once. False when nothing was saved."""
        try:
            operation(self.tracker_db)
            save(self.tracker_db)
        except InvalidRecordError as error:
            self.notify(str(error), title="Not saved", severity="error", timeout=8)
            return False
        except ConflictError:
            self.reload()
            self.notify(
                "The file changed on disk since it was read. It was reloaded; please do your edit again.",
                title="Not saved",
                severity="warning",
                timeout=8,
            )
            return False
        except TrackerError as error:
            self.reload()
            self.notify(str(error), title="Not saved", severity="error", timeout=8)
            return False
        self.refresh_table()
        return True

    def apply(self, record_id: str, changes: dict) -> bool:
        return self.write(lambda db: update_record(db, record_id, changes, self.today()))

    def _mark_no_answer(self, ids: list[str] | None) -> None:
        if not ids:
            return

        def mark(db: Db) -> None:
            for record_id in ids:
                set_status(db, record_id, "no_answer", self.today())

        if self.write(mark):
            self.notify(f"{len(ids)} Application(s) set to No answer.")

    # actions

    @on(DataTable.RowSelected)
    def _open_detail(self, event: DataTable.RowSelected) -> None:
        self.push_screen(DetailScreen(event.row_key.value))

    def action_toggle_closed(self) -> None:
        self.hide_closed = not self.hide_closed
        self.refresh_table()
        self.notify("Hiding Desisted and Not selected." if self.hide_closed else "Showing all Applications.")

    def action_open_document(self, kind: str) -> None:
        screen = self.screen
        record_id = screen.record_id if isinstance(screen, DetailScreen) else self.selected_id()
        record = self.tracker_db.find(record_id) if record_id else None
        if record is None:
            return
        label, path_of = DOCUMENTS[kind]
        relative = path_of(record)
        if not relative:
            self.notify(f"This Application has no {label} yet.", severity="warning")
        elif not (self.root / relative).is_file():
            self.notify(f"The {label} file is missing: {relative}", severity="error")
        else:
            self.opener(self.root / relative)
