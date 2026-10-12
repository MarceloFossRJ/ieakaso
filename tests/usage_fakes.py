"""Synthetic Claude Code transcripts for the usage tests: a main JSONL plus a subagents folder."""

import json
from pathlib import Path


class FakeSession:
    def __init__(self, root: Path, session_id: str = "sess-1", slug: str = "-fake-project"):
        self.session_id = session_id
        self.project = root / "projects" / slug
        self.project.mkdir(parents=True)
        self.path = self.project / f"{session_id}.jsonl"
        self.path.write_text("")

    def _write(self, line: dict, path: Path | None = None) -> None:
        with (path or self.path).open("a") as f:
            f.write(json.dumps(line) + "\n")

    def user(self, content="hello") -> None:
        self._write({"type": "user", "message": {"role": "user", "content": content}})

    def noise(self) -> None:
        self._write({"type": "system", "content": "x"})
        self._write({"type": "attachment", "attachment": {}})

    def assistant(self, msg_id, model="claude-opus-5-5", inp=0, cc=0, cr=0, out=0, blocks=None, lines=1, path=None):
        """One API message, written as `lines` lines that share the id and usage (as Claude Code does)."""
        blocks = blocks or [{"type": "text", "text": "ok"}]
        usage = {
            "input_tokens": inp,
            "cache_creation_input_tokens": cc,
            "cache_read_input_tokens": cr,
            "output_tokens": out,
        }
        for i in range(lines):
            block = blocks[i] if i < len(blocks) else {"type": "text", "text": "more"}
            self._write(
                {
                    "type": "assistant",
                    "message": {"id": msg_id, "model": model, "usage": usage, "content": [block]},
                },
                path,
            )

    def start(self, mode, msg_id, **kw) -> None:
        cmd = f"uv run python -m ieakaso.usage start {mode}"
        self.assistant(msg_id, blocks=[{"type": "tool_use", "id": f"t-{msg_id}", "name": "Bash", "input": {"command": cmd}}], **kw)

    def bash(self, msg_id, command, **kw) -> None:
        self.assistant(msg_id, blocks=[{"type": "tool_use", "id": f"t-{msg_id}", "name": "Bash", "input": {"command": command}}], **kw)

    def agent_call(self, msg_id, tool_use_id, **kw) -> None:
        self.assistant(msg_id, blocks=[{"type": "tool_use", "id": tool_use_id, "name": "Agent", "input": {"prompt": "p"}}], **kw)

    def subagent(self, agent_id, agent_type, tool_use_id, turns) -> None:
        """turns: list of (msg_id, model, inp, cc, cr, out)."""
        d = self.project / self.session_id / "subagents"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"agent-{agent_id}.meta.json").write_text(
            json.dumps({"agentType": agent_type, "description": "d", "toolUseId": tool_use_id})
        )
        p = d / f"agent-{agent_id}.jsonl"
        p.write_text("")
        for msg_id, model, inp, cc, cr, out in turns:
            self.assistant(msg_id, model=model, inp=inp, cc=cc, cr=cr, out=out, path=p)
