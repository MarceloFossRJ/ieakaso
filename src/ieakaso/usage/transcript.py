"""Read a Claude Code transcript (JSONL) into deduplicated assistant turns and Agent runs."""

import json
import math
import os
import re
import shlex
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

# Agent types of the Ieakaso agents, from the files in .claude/agents/; other agent types are not Ieakaso.
IEAKASO_AGENTS = {"recruiter", "applicant"}
# One simple command of the Bash call must itself be the start invocation: a grep or echo that mentions it
# starts no Run, but `cd repo; uv run python -m ieakaso.usage start <mode>; cat x` does.
_MARKER = re.compile(r"(?:uv run (?:--\S+ )*)?python -m ieakaso\.usage start ([\w-]+)")
_OPERATORS = ";&|\n"

# Output estimates for messages without a final line (see _estimate_outputs).
CHARS_PER_TOKEN = 4
DEFAULT_OUTPUT_RATIO = (1.4, 1.8, 3.3)  # p10, median, p90 of true output / visible tokens, 68 real messages
MIN_CALIBRATION_MESSAGES = 10
MIN_CALIBRATION_CHARS = 400


@dataclass(frozen=True)
class Usage:
    fresh_input: int = 0  # input_tokens + cache_creation_input_tokens (new input plus cache writes)
    out: int = 0  # exact, or the estimate when `estimated`
    cache_read: int = 0
    out_low_gap: int = 0  # an estimated out lies in [out - out_low_gap, out + out_high_gap]
    out_high_gap: int = 0
    estimated: bool = False

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.fresh_input + other.fresh_input,
            self.out + other.out,
            self.cache_read + other.cache_read,
            self.out_low_gap + other.out_low_gap,
            self.out_high_gap + other.out_high_gap,
            self.estimated or other.estimated,
        )

    @staticmethod
    def total(usages: Iterable[Usage]) -> Usage:
        return sum(usages, Usage())

    @property
    def new(self) -> int:
        return self.fresh_input + self.out

    @property
    def context(self) -> int:
        return self.fresh_input + self.cache_read


@dataclass
class Turn:
    """One API message (a transcript writes it as several lines)."""

    msg_id: str
    model: str
    usage: Usage
    start_mode: str | None = None  # set when this message runs the Run start marker
    agent_tool_ids: list[str] = field(default_factory=list)
    final: bool = False  # its last line has a stop_reason, so its output count is final
    visible_chars: int = 0  # text and tool input; thinking text is empty in transcripts, so it is not seen

    @property
    def counts(self) -> bool:
        """Claude Code also writes <synthetic> messages and zero-usage ones; they spend nothing."""
        return self.model != "<synthetic>" and self.usage != Usage()


@dataclass
class AgentRun:
    tool_use_id: str
    agent_type: str
    turns: list[Turn]

    @property
    def usage(self) -> Usage:
        return Usage.total(t.usage for t in self.turns if t.counts)

    @property
    def models(self) -> list[str]:
        return list(dict.fromkeys(t.model for t in self.turns if t.counts))


@dataclass
class Transcript:
    turns: list[Turn] = field(default_factory=list)
    agent_runs: list[AgentRun] = field(default_factory=list)


def _lines(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        try:
            obj = json.loads(raw)
        except ValueError:
            continue
        if isinstance(obj, dict):
            yield obj


def _simple_commands(command: str) -> list[str]:
    """Split a Bash command on ;, &&, ||, | and newlines outside quotes. Unbalanced quotes give no commands."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=_OPERATORS)
    lexer.whitespace = " \t\r"  # a newline separates commands, so it is an operator, not whitespace
    lexer.whitespace_split = True
    commands, words = [], []
    try:
        for token in lexer:
            if token and set(token) <= set(_OPERATORS):
                commands.append(" ".join(words))
                words = []
            else:
                words.append(token)
    except ValueError:
        return []
    return [c for c in [*commands, " ".join(words)] if c]


def _start_mode(command: str) -> str | None:
    for simple in _simple_commands(command):
        found = _MARKER.fullmatch(simple)
        if found:
            return found.group(1)
    return None


def _visible_chars(block: dict) -> int:
    if block.get("type") == "text":
        return len(str(block.get("text", "")))
    if block.get("type") == "tool_use":
        return len(json.dumps(block.get("input") or {}, ensure_ascii=False))
    return 0


def read_turns(path: Path, *, main_chain: bool = True) -> list[Turn]:
    """Deduplicated assistant messages. Subagent files are all sidechain, so they pass main_chain=False."""
    turns: dict[str, Turn] = {}
    for obj in _lines(path):
        msg = obj.get("message")
        if obj.get("type") != "assistant" or not isinstance(msg, dict) or (main_chain and obj.get("isSidechain")):
            continue
        u = msg.get("usage") or {}
        usage = Usage(
            fresh_input=(u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0),
            out=u.get("output_tokens") or 0,
            cache_read=u.get("cache_read_input_tokens") or 0,
        )
        key = msg.get("id") or f"line-{len(turns)}"
        turn = turns.setdefault(key, Turn(key, msg.get("model") or "", usage))
        turn.usage = usage  # a message streams over several lines; only the last line's usage is final
        turn.final = bool(msg.get("stop_reason"))
        content = msg.get("content")
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            turn.visible_chars += _visible_chars(block)
            if block.get("type") != "tool_use":
                continue
            if block.get("name") == "Bash":
                mode = _start_mode(str((block.get("input") or {}).get("command", "")))
                if mode:
                    turn.start_mode = mode
            elif block.get("name") == "Agent" and block.get("id"):
                turn.agent_tool_ids.append(block["id"])
    return list(turns.values())


def read_agent_runs(path: Path) -> list[AgentRun]:
    folder = path.with_suffix("") / "subagents"
    runs = []
    for meta_path in sorted(folder.glob("agent-*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        if not isinstance(meta, dict) or meta.get("agentType") not in IEAKASO_AGENTS:
            continue
        log = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".jsonl")
        runs.append(AgentRun(meta.get("toolUseId", ""), meta["agentType"], read_turns(log, main_chain=False)))
    return runs


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def is_calibration_turn(turn: Turn) -> bool:
    """A final message long enough for its true output / visible tokens ratio to mean something."""
    return turn.final and turn.visible_chars >= MIN_CALIBRATION_CHARS and turn.counts


def calibrate(turns: list[Turn]) -> tuple[float, float, float]:
    """(p10, median, p90) of true output / visible tokens over the final messages; the default with too few."""
    ratios = [t.usage.out / (t.visible_chars / CHARS_PER_TOKEN) for t in turns if is_calibration_turn(t)]
    if len(ratios) < MIN_CALIBRATION_MESSAGES:
        return DEFAULT_OUTPUT_RATIO
    return _quantile(ratios, 0.1), statistics.median(ratios), _quantile(ratios, 0.9)


def estimate_output(visible_chars: int, recorded: int, ratio: tuple[float, float, float]) -> tuple[int, int, int]:
    """(estimate, low, high) output tokens for a message; never below the recorded count."""
    visible = visible_chars / CHARS_PER_TOKEN
    low, mid, high = ratio
    return tuple(max(recorded, round(visible * r)) for r in (mid, low, high))


def _estimate_outputs(turns: list[Turn]) -> None:
    """Estimate the output of messages without a final line, from their visible characters.

    True output is visible characters / CHARS_PER_TOKEN times a ratio (hidden thinking makes it above 1). The ratio
    is the median over this Session's final messages, and its p10-p90 is the margin; with too few of them, the
    default measured on real Sessions. `ieakaso.devtools.estimate_backtest` checks it against known counts.
    """
    ratio = calibrate(turns)
    for t in turns:
        if t.final or not t.visible_chars or not t.counts:
            continue
        recorded = t.usage.out
        est, est_low, est_high = estimate_output(t.visible_chars, recorded, ratio)
        if est == recorded and est_high == recorded:
            continue
        t.usage = replace(t.usage, out=est, out_low_gap=est - est_low, out_high_gap=est_high - est, estimated=True)


def load(path: Path) -> Transcript:
    transcript = Transcript(read_turns(path), read_agent_runs(path))
    _estimate_outputs(transcript.turns + [t for run in transcript.agent_runs for t in run.turns])
    return transcript


def find_transcript(session_id: str, claude_dir: Path | None = None) -> Path | None:
    """The main transcript of a session: ~/.claude/projects/<slug>/<session_id>.jsonl."""
    if not session_id or "/" in session_id:
        return None
    base = claude_dir or Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return next(iter(sorted((base / "projects").glob(f"*/{session_id}.jsonl"))), None)
