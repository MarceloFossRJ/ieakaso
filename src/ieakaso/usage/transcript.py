"""Read a Claude Code transcript (JSONL) into deduplicated assistant turns and Agent runs."""

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# Agent types of the Ieakaso agents, from the files in .claude/agents/; other agent types are not Ieakaso.
IEAKASO_AGENTS = {"recruiter", "candidate-assistant"}
# The Bash command must itself be the start invocation: a grep or echo that mentions it starts no Run.
_MARKER = re.compile(r"(?:uv run (?:--\S+ )*)?python -m ieakaso\.usage start ([\w-]+)")


@dataclass(frozen=True)
class Usage:
    fresh_input: int = 0  # input_tokens + cache_creation_input_tokens (new input plus cache writes)
    out: int = 0
    cache_read: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(self.fresh_input + other.fresh_input, self.out + other.out, self.cache_read + other.cache_read)

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
        content = msg.get("content")
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") == "Bash":
                found = _MARKER.fullmatch(str((block.get("input") or {}).get("command", "")).strip())
                if found:
                    turn.start_mode = found.group(1)
            elif block.get("name") == "Agent" and block.get("id"):
                turn.agent_tool_ids.append(block["id"])
    return list(turns.values())


def read_agent_runs(path: Path) -> list[AgentRun]:
    folder = path.with_suffix("") / "subagents"
    runs = []
    for meta_path in sorted(folder.glob("agent-*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict) or meta.get("agentType") not in IEAKASO_AGENTS:
            continue
        log = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".jsonl")
        runs.append(AgentRun(meta.get("toolUseId", ""), meta["agentType"], read_turns(log, main_chain=False)))
    return runs


def load(path: Path) -> Transcript:
    return Transcript(read_turns(path), read_agent_runs(path))


def find_transcript(session_id: str, claude_dir: Path | None = None) -> Path | None:
    """The main transcript of a session: ~/.claude/projects/<slug>/<session_id>.jsonl."""
    if not session_id or "/" in session_id:
        return None
    base = claude_dir or Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return next(iter(sorted((base / "projects").glob(f"*/{session_id}.jsonl"))), None)
