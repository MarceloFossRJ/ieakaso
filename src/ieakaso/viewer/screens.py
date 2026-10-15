"""The viewer's other screens: one Application's detail (every editable field), and the No answer suggestions."""

import copy
import re
from typing import ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, SelectionList, Static

from ieakaso.tracker import CONTACT_TYPES, PERIODS, STATUSES

SIMPLE_TEXT = {"company", "position", "notes", "home_office", "applied_on"}
NULLABLE_TEXT = {"home_office", "applied_on"}
SOURCE_FIELDS = {"board", "board_url", "form_url"}
SALARY_FIELDS = {"sal_min", "sal_max", "sal_currency", "sal_period"}
ITEM_ID = re.compile(r"(stage|contact)_(\d+)_([a-z_]+)")


def label(value: str) -> str:
    """A value as the candidate reads it: `not_selected` is "Not selected"."""
    return value.replace("_", " ").capitalize()


def _number(text: str) -> int | float:
    value = float(text)
    return int(value) if value == int(value) else value


class NoAnswerScreen(ModalScreen[list[str]]):
    """Applied more than 30 days ago: the candidate ticks which Applications become No answer."""

    BINDINGS: ClassVar[list] = [("escape", "skip", "Not now")]
    CSS = """
    NoAnswerScreen { align: center middle; }
    #no-answer { width: 90%; max-width: 100; height: auto; max-height: 90%; border: thick $primary; padding: 1 2; background: $surface; }
    #no-answer SelectionList { height: auto; max-height: 20; }
    #no-answer Horizontal { height: auto; margin-top: 1; }
    """

    def __init__(self, records: list[dict]):
        super().__init__()
        self.records = records

    def compose(self) -> ComposeResult:
        with Vertical(id="no-answer"):
            yield Label("No answer after 30 days?", classes="title")
            yield Static(
                "You applied to these Applications more than 30 days ago. Tick the ones that got no answer "
                "(space ticks); ticked ones become No answer. The others are suggested again next time."
            )
            yield SelectionList(
                *[
                    (f"{r['company']}: {r['position']} (applied {r['applied_on']})", r["id"], False)
                    for r in self.records
                ],
                id="candidates",
            )
            with Horizontal():
                yield Button("Mark ticked as No answer", id="confirm", variant="primary")
                yield Button("Not now", id="skip")

    @on(Button.Pressed, "#confirm")
    def _confirm(self) -> None:
        self.dismiss(list(self.query_one(SelectionList).selected))

    @on(Button.Pressed, "#skip")
    def action_skip(self) -> None:
        self.dismiss([])


class DetailScreen(Screen):
    """One Application. Each field is saved as soon as it is entered; read-only fields are shown as text."""

    BINDINGS: ClassVar[list] = [("escape", "back", "Back")]
    CSS = """
    DetailScreen .row { height: auto; }
    DetailScreen .row > Label { width: 24; padding: 1 1 0 1; }
    DetailScreen .row > Input, DetailScreen .row > Select { width: 1fr; }
    DetailScreen .section { text-style: bold; margin-top: 1; padding: 0 1; color: $accent; }
    DetailScreen .readonly { padding: 0 1; color: $text-muted; }
    DetailScreen .title { text-style: bold; padding: 1 1 0 1; }
    DetailScreen .actions { height: auto; margin-top: 1; }
    """

    def __init__(self, record_id: str):
        super().__init__()
        self.record_id = record_id
        self._shown: dict | None = None
        self._ready = False  # widgets announce their first values while mounting; those are not edits

    def on_mount(self) -> None:
        self.call_after_refresh(setattr, self, "_ready", True)

    @property
    def record(self) -> dict | None:
        return self.app.tracker_db.find(self.record_id)

    # building

    def compose(self) -> ComposeResult:
        record = self.record
        self._shown = copy.deepcopy(record)
        if record is None:
            yield Static("This Application is no longer in the file. Press Escape.")
            yield Footer()
            return
        with VerticalScroll():
            yield Static(f"{record['company']}: {record['position']}", classes="title")
            yield from self._read_only(record)
            yield Static("Edit", classes="section")
            yield from self._row("Company", Input(record["company"], id="company"))
            yield from self._row("Position", Input(record["position"], id="position"))
            yield from self._row(
                "Status", Select(self._options(STATUSES), value=record["status"], allow_blank=False, id="status")
            )
            yield from self._row("Applied on (yyyy-mm-dd)", Input(record["applied_on"] or "", id="applied_on"))
            yield from self._row("Home office", Input(record["home_office"] or "", id="home_office"))
            yield from self._row("City", Input(record["location"]["city"] or "", id="city"))
            yield from self._row("Country (ISO code)", Input(record["location"]["country"] or "", id="country"))
            yield from self._row("Board", Input(record["source"]["board"] or "", id="board"))
            yield from self._row("Board URL", Input(record["source"]["board_url"] or "", id="board_url"))
            yield from self._row("Form URL", Input(record["source"]["form_url"] or "", id="form_url"))
            yield from self._salary(record["salary_expectation"])
            yield from self._row("Notes", Input(record["notes"], id="notes"))
            yield from self._stages(record)
            yield from self._contacts(record)
            with Horizontal(classes="actions"):
                yield Button("Open Job ad", id="open_ad")
                yield Button("Open Job analysis", id="open_analysis")
                yield Button("Open Cover letter", id="open_letter")
                yield Button("Back", id="back")
        yield Footer()

    @staticmethod
    def _options(values) -> list[tuple[str, str]]:
        return [(label(value), value) for value in values]

    @staticmethod
    def _row(label: str, widget):
        with Horizontal(classes="row"):
            yield Label(label)
            yield widget

    def _read_only(self, record: dict):
        analysis, source = record["analysis"], record["source"]
        history = ", ".join(f"{h['status']} ({h['on']})" for h in record["status_history"])
        yield Static("Read only", classes="section")
        for name, value in (
            ("ID", record["id"]),
            ("Created", record["created_at"]),
            ("Job analysis", f"{analysis['on']}: {analysis['verdict']}, {analysis['score']}/100"),
            ("Job analysis file", analysis["doc"]),
            ("Job ad file", source["job_ad"]),
            ("Cover letter file", record["cover_letter"] or "none yet"),
            ("Status history", history),
        ):
            yield Static(f"{name}: {value}", classes="readonly")

    def _salary(self, salary: dict | None):
        salary = salary or {"period": None, "min": "", "max": "", "currency": ""}
        yield Static("Salary expectation (what you entered in the form)", classes="section")
        yield from self._row(
            "Period",
            Select(
                self._options(PERIODS),
                value=salary["period"] if salary["period"] else Select.NULL,
                allow_blank=True,
                id="sal_period",
            ),
        )
        yield from self._row("Min", Input(str(salary["min"]), id="sal_min"))
        yield from self._row("Max", Input(str(salary["max"]), id="sal_max"))
        yield from self._row("Currency (ISO code)", Input(salary["currency"], id="sal_currency"))

    def _stages(self, record: dict):
        yield Static("Interview stages", classes="section")
        stage_options = [("0: not started", 0)] + [(f"{i}: {s['name']}", i) for i, s in enumerate(record["stages"], 1)]
        yield from self._row(
            "Current stage", Select(stage_options, value=record["stage"], allow_blank=False, id="stage")
        )
        for i, stage in enumerate(record["stages"]):
            with Horizontal(classes="row"):
                yield Label(f"Stage {i + 1}")
                yield Input(stage["name"], id=f"stage_{i}_name", placeholder="name")
                yield Input(stage["description"], id=f"stage_{i}_description", placeholder="description")
                yield Button("Remove", id=f"stage_{i}_remove")
        yield Button("Add stage", id="add_stage")

    def _contacts(self, record: dict):
        yield Static("Contacts", classes="section")
        for i, contact in enumerate(record["contacts"]):
            with Horizontal(classes="row"):
                yield Label(f"Contact {i + 1}")
                yield Select(
                    self._options(CONTACT_TYPES),
                    value=contact["contact_type"],
                    allow_blank=False,
                    id=f"contact_{i}_type",
                )
                yield Input(contact["name"], id=f"contact_{i}_name", placeholder="name")
                yield Input(contact["linkedin_url"] or "", id=f"contact_{i}_linkedin_url", placeholder="LinkedIn URL")
                yield Input(contact["email"] or "", id=f"contact_{i}_email", placeholder="email")
                yield Button("Remove", id=f"contact_{i}_remove")
        yield Button("Add contact", id="add_contact")

    # saving

    def _value(self, widget_id: str):
        widget = self.query_one(f"#{widget_id}")
        if isinstance(widget, Select):
            return None if widget.value is Select.NULL else widget.value
        return widget.value.strip()

    def _changes_for(self, widget_id: str) -> dict | None:
        """The record edit a field stands for, or None when the field can't be saved yet."""
        record = self.record
        if record is None:
            return None
        value = self._value
        if widget_id in SIMPLE_TEXT:
            return {widget_id: (value(widget_id) or None) if widget_id in NULLABLE_TEXT else value(widget_id)}
        if widget_id in ("city", "country"):
            return {"location": {"city": value("city") or None, "country": (value("country") or "").upper() or None}}
        if widget_id in SOURCE_FIELDS:
            return {"source": {widget_id: value(widget_id) or None}}
        if widget_id in ("status", "stage"):
            return {widget_id: value(widget_id)}
        if widget_id in SALARY_FIELDS:
            return self._salary_change()
        match = ITEM_ID.fullmatch(widget_id)
        if match:
            kind, index, field = match.group(1), int(match.group(2)), match.group(3)
            key = "stages" if kind == "stage" else "contacts"
            items = copy.deepcopy(record[key])
            if index >= len(items):
                return None
            field = "contact_type" if field == "type" else field
            items[index][field] = (value(widget_id) or None) if field in ("linkedin_url", "email") else value(widget_id)
            return {key: items}
        return None

    def _salary_change(self) -> dict | None:
        period, low, high, currency = (self._value(k) for k in ("sal_period", "sal_min", "sal_max", "sal_currency"))
        if not (period or low or high or currency):
            return {"salary_expectation": None}
        try:
            if not (period and low and high and currency):
                raise ValueError
            return {
                "salary_expectation": {
                    "period": period,
                    "min": _number(low),
                    "max": _number(high),
                    "currency": currency.upper(),
                }
            }
        except ValueError:
            self.notify("The Salary expectation is saved once period, min, max (numbers) and currency are all filled.")
            return None

    def _unchanged(self, changes: dict) -> bool:
        record = self.record
        for key, value in changes.items():
            current = record[key]
            if key == "source" and not all(current[k] == v for k, v in value.items()):
                return False
            if key != "source" and current != value:
                return False
        return True

    def _commit(self, widget_id: str | None) -> None:
        if not widget_id or not self._ready:
            return
        changes = self._changes_for(widget_id)
        if changes is None or self._unchanged(changes):
            return
        saved = self.app.apply(self.record_id, changes)
        if saved and "status" in changes:
            self._rebuild()  # applied_on and the history may have changed
        elif saved:
            self._shown = copy.deepcopy(self.record)
        else:
            self._rebuild()  # show what is really in the file

    @on(Input.Submitted)
    def _submitted(self, event: Input.Submitted) -> None:
        self._commit(event.input.id)

    @on(events.DescendantBlur)
    def _blurred(self, event: events.DescendantBlur) -> None:
        if isinstance(event.widget, Input):
            self._commit(event.widget.id)

    @on(Select.Changed)
    def _selected(self, event: Select.Changed) -> None:
        self._commit(event.select.id)

    @on(Button.Pressed)
    def _pressed(self, event: Button.Pressed) -> None:
        button = event.button.id or ""
        record = self.record
        if button == "back":
            self.action_back()
        elif button.startswith("open_"):
            self.app.action_open_document(button.removeprefix("open_"))
        elif record is None:
            return
        elif button == "add_stage":
            self._edit({"stages": [*record["stages"], {"name": "New stage", "description": ""}]})
        elif button == "add_contact":
            new = {"contact_type": "other", "name": "New contact", "linkedin_url": None, "email": None}
            self._edit({"contacts": [*record["contacts"], new]})
        else:
            match = re.fullmatch(r"(stage|contact)_(\d+)_remove", button)
            if match:
                self._remove(match.group(1), int(match.group(2)), record)

    def _remove(self, kind: str, index: int, record: dict) -> None:
        if kind == "contact":
            self._edit({"contacts": [c for i, c in enumerate(record["contacts"]) if i != index]})
            return
        changes = {"stages": [s for i, s in enumerate(record["stages"]) if i != index]}
        if record["stage"] > index:  # the current stage is the removed one, or comes after it
            changes["stage"] = record["stage"] - 1
        self._edit(changes)

    def _edit(self, changes: dict) -> None:
        self.app.apply(self.record_id, changes)
        self._rebuild()

    def _rebuild(self) -> None:
        """Show the record again from what is in the db (a fresh screen: recomposing breaks Select widgets)."""
        self.app.switch_screen(DetailScreen(self.record_id))

    # reacting

    def db_reloaded(self) -> None:
        """The file changed on disk and the app reloaded it: show the new values if this record changed."""
        if self.record is None:
            self.notify("This Application is no longer in the file.", severity="warning")
            self._rebuild()
        elif self.record != self._shown:
            self.notify(
                "This Application changed in another window and was reloaded; if an edit was not saved, do your edit again.",
                severity="warning",
            )
            self._rebuild()

    def action_back(self) -> None:
        self.app.pop_screen()
