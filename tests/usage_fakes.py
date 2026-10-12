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
        # Real transcripts: main lines have isSidechain false, every subagent line has it true.
        line = {**line, "isSidechain": path is not None}
        with (path or self.path).open("a") as f:
            f.write(json.dumps(line) + "\n")

    def user(self, content="hello") -> None:
        self._write({"type": "user", "message": {"role": "user", "content": content}})

    def noise(self) -> None:
        self._write({"type": "system", "content": "x"})
        self._write({"type": "attachment", "attachment": {}})

    def assistant(
        self, msg_id, model="claude-opus-5-5", inp=0, cc=0, cr=0, out=0, blocks=None, lines=1, outs=None, path=None
    ):
        """One API message, written as `lines` lines that share the id (as Claude Code does).

        outs: output_tokens per line, as Claude Code writes them while the message streams; only the last is final.
        Without it, every line carries `out`.
        """
        blocks = blocks or [{"type": "text", "text": "ok"}]
        outs = outs or [out] * lines
        for i, line_out in enumerate(outs):
            block = blocks[i] if i < len(blocks) else {"type": "text", "text": "more"}
            usage = {
                "input_tokens": inp,
                "cache_creation_input_tokens": cc,
                "cache_read_input_tokens": cr,
                "output_tokens": line_out,
            }
            self._write(
                {
                    "type": "assistant",
                    "message": {"id": msg_id, "model": model, "usage": usage, "content": [block]},
                },
                path,
            )

    @staticmethod
    def tool_use(tool_id, name, **input) -> dict:
        return {"type": "tool_use", "id": tool_id, "name": name, "input": input}

    def start(self, mode, msg_id, **kw) -> None:
        self.bash(msg_id, f"uv run python -m ieakaso.usage start {mode}", **kw)

    def bash(self, msg_id, command, **kw) -> None:
        self.assistant(msg_id, blocks=[self.tool_use(f"t-{msg_id}", "Bash", command=command)], **kw)

    def agent_call(self, msg_id, tool_use_id, **kw) -> None:
        self.assistant(msg_id, blocks=[self.tool_use(tool_use_id, "Agent", prompt="p")], **kw)

    def synthetic(self, msg_id) -> None:
        """Claude Code writes these (e.g. for an interrupted turn): model <synthetic>, zero usage."""
        self.assistant(msg_id, model="<synthetic>")

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
