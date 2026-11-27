"""The filters over the Applications table: what each one offers, which records it keeps, and its tick-list popup.

A filter's choices are keys of a record's value (`lead`, `Apply`, a normalised stage name, `DE`); `""` is an
empty value (no stage started, no country, no city). Ticking several keys keeps the records with any of them;
different filters combine with AND; a filter with nothing ticked keeps everything.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, SelectionList

from ieakaso.tracker import CLOSED_STATUSES, STATUS_LIFECYCLE, VERDICTS
from ieakaso.viewer.screens import label

NOT_STARTED = "Not started"
NONE = "(none)"
LONGEST_SUMMARY = 24  # a button's ticked labels longer than this show as "N selected"


def stage_key(record: dict) -> str:
    """The current stage's name, ignoring case and spacing; empty before the process starts."""
    if not 0 < record["stage"] <= len(record["stages"]):
        return ""
    return " ".join(record["stages"][record["stage"] - 1]["name"].split()).casefold()


def _stage_name(record: dict) -> str:
    return " ".join(record["stages"][record["stage"] - 1]["name"].split())


@dataclass(frozen=True)
class Filter:
    """One filter of the bar.

    `key` is the record's choice; `fixed` lists every choice in order when they don't come from the db;
    `shown` is how a key from the db reads, and `empty` how `""` reads.
    """

    name: str
    key: Callable[[dict], str]
    fixed: tuple[tuple[str, str], ...] | None = None
    shown: Callable[[dict], str] | None = None
    empty: str = NONE


FILTERS = (
    Filter("Status", lambda r: r["status"], fixed=tuple((s, label(s)) for s in STATUS_LIFECYCLE)),
    Filter("Stage", stage_key, shown=_stage_name, empty=NOT_STARTED),
    Filter("Verdict", lambda r: r["analysis"]["verdict"], fixed=tuple((v, v) for v in VERDICTS)),
    Filter("Country", lambda r: r["location"]["country"] or "", shown=lambda r: r["location"]["country"]),
    Filter("City", lambda r: r["location"]["city"] or "", shown=lambda r: r["location"]["city"]),
)
STATUS = FILTERS[0]


@dataclass
class Filters:
    """What the candidate ticked in each filter: key -> label, so a value gone from the db still reads."""

    ticked: dict[str, dict[str, str]] = field(default_factory=lambda: {f.name: {} for f in FILTERS})

    @property
    def active(self) -> bool:
        return any(self.ticked.values())

    def keeps(self, record: dict) -> bool:
        return all(not self.ticked[f.name] or f.key(record) in self.ticked[f.name] for f in FILTERS)

    def choices(self, flt: Filter, records: list[dict]) -> list[tuple[str, str]]:
        """Every choice of a filter, in order, with the ticked ones that are no longer in the db."""
        if flt.fixed is not None:
            found = list(flt.fixed)
        else:
            names: dict[str, str] = {}
            for record in records:
                key = flt.key(record)
                names.setdefault(key, flt.shown(record) if key else flt.empty)
            found = sorted(((k, n) for k, n in names.items() if k), key=lambda c: c[1].casefold())
            if "" in names:
                found.append(("", flt.empty))
        present = {key for key, _ in found}
        stale = [(key, name) for key, name in self.ticked[flt.name].items() if key not in present]
        return found + stale

    def set(self, flt: Filter, ticked: dict[str, str]) -> None:
        self.ticked[flt.name] = dict(ticked)

    def summary(self, flt: Filter) -> str:
        """The button's text: `Status: all`, `Status: Lead, Applied`, `Verdict: 3 selected`."""
        ticked = list(self.ticked[flt.name].values())
        if not ticked:
            return f"{flt.name}: all"
        names = ", ".join(ticked)
        return f"{flt.name}: {names if len(names) <= LONGEST_SUMMARY else f'{len(ticked)} selected'}"

    def closed_hidden(self) -> bool:
        ticked = self.ticked[STATUS.name]
        return bool(ticked) and not any(status in ticked for status in CLOSED_STATUSES)

    def toggle_closed(self) -> bool:
        """`h`: untick Desisted and Not selected, or tick them back. True when they are now hidden."""
        names = dict(STATUS.fixed)
        ticked = self.ticked[STATUS.name]
        if self.closed_hidden():
            ticked.update((status, names[status]) for status in CLOSED_STATUSES)
            if set(ticked) == set(names):
                ticked.clear()
            return False
        kept = {k: n for k, n in (ticked or names).items() if k not in CLOSED_STATUSES}
        self.ticked[STATUS.name] = kept or {k: n for k, n in names.items() if k not in CLOSED_STATUSES}
        return True

    def clear(self) -> None:
        for ticked in self.ticked.values():
            ticked.clear()


class FilterBar(Horizontal):
    """The row of filter buttons above the table: arrows move between them, Escape goes back to the table."""

    BINDINGS: ClassVar[list] = [
        ("left", "move(-1)", "Previous filter"),
        ("right", "move(1)", "Next filter"),
        ("escape", "to_table", "Back to the table"),
    ]

    def action_move(self, step: int) -> None:
        buttons = list(self.query(Button))
        current = buttons.index(self.screen.focused) if self.screen.focused in buttons else 0
        buttons[min(max(current + step, 0), len(buttons) - 1)].focus()

    def action_to_table(self) -> None:
        self.app.query_one(DataTable).focus()


class FilterScreen(ModalScreen[dict[str, str] | None]):
    """One filter's tick list. Apply returns the ticked choices (none: everything); Cancel or Escape changes nothing."""

    BINDINGS: ClassVar[list] = [("escape", "cancel", "Cancel")]
    CSS = """
    FilterScreen { align: center middle; }
    #filter { width: 60; height: auto; max-height: 90%; border: thick $primary; padding: 1 2; background: $surface; }
    #filter SelectionList { height: auto; max-height: 20; }
    #filter Horizontal { height: auto; margin-top: 1; }
    """

    def __init__(self, name: str, choices: list[tuple[str, str]], ticked: dict[str, str]):
        super().__init__()
        self.filter_name = name
        self.choices = choices
        self.ticked = ticked

    def compose(self) -> ComposeResult:
        with Vertical(id="filter"):
            yield Label(f"Filter by {self.filter_name.casefold()}", classes="title")
            yield Label("Space ticks. Nothing ticked shows every Application.")
            yield SelectionList(*[(name, key, key in self.ticked) for key, name in self.choices], id="choices")
            with Horizontal():
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#apply")
    def _apply(self) -> None:
        selected = set(self.query_one(SelectionList).selected)
        self.dismiss({key: name for key, name in self.choices if key in selected})

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)
