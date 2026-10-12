"""Format the Run summary and the status line."""

from ieakaso.usage.runs import segment
from ieakaso.usage.transcript import Transcript, Usage

# Context window sizes of the models we know; the one place to extend. Unknown models show no size.
CONTEXT_WINDOWS = {"claude-opus-5-5": 200_000, "claude-sonnet-5-5": 200_000}

NO_RUN = "Ieakaso usage: no Ieakaso Run in this Session yet."


def fmt_tokens(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 100_000:
        return f"{n / 1000:.1f}k"
    if n < 1_000_000:
        return f"{n / 1000:.0f}k"
    return f"{n / 1_000_000:.1f}M"


def fmt_compact(n: int) -> str:
    """fmt_tokens without a trailing '.0': 39k, not 39.0k."""
    return fmt_tokens(n).replace(".0k", "k").replace(".0M", "M")


def context_window(model: str) -> int | None:
    return CONTEXT_WINDOWS.get(model)


def _split(usage: Usage) -> str:
    return f"in {fmt_tokens(usage.inp)} · out {fmt_tokens(usage.out)} · cache read {fmt_tokens(usage.cache_read)}"


def _latest_turn(transcript: Transcript):
    return next((t for t in reversed(transcript.turns) if t.model or t.usage.context), None)


def summary(transcript: Transcript) -> str:
    runs = segment(transcript)
    if not runs:
        return NO_RUN
    run = runs[-1]
    title = f"── Ieakaso · {run.mode} (so far) "
    lines = [
        title + "─" * max(3, 50 - len(title)),
        f"Model     {', '.join(run.models)}",
        f"Tokens    {_split(run.usage)}",
    ]
    latest = _latest_turn(transcript)
    fill = latest.usage.context
    window = context_window(latest.model)
    lines.append(f"Context   {fmt_compact(fill)}" + (f" / {fmt_compact(window)} ({fill * 100 / window:.0f}%)" if window else ""))
    for agent in run.agent_runs:
        lines.append(f"  Agent run  {agent.agent_type} ({', '.join(agent.models)})   {_split(agent.usage)}")
    total = sum((r.usage for r in runs), Usage())
    lines.append(f"Session   {len(runs)} {'Run' if len(runs) == 1 else 'Runs'} · {_split(total)}")
    return "\n".join(lines)


def _context_percent(transcript: Transcript, stdin: dict) -> int | None:
    window = stdin.get("context_window") or {}
    pct = window.get("used_percentage")
    if isinstance(pct, (int, float)):
        return round(pct)
    latest = _latest_turn(transcript)
    if latest is None:
        return None
    size = window.get("context_window_size") or context_window(latest.model)
    return round(latest.usage.context * 100 / size) if size else None


def statusline(transcript: Transcript, stdin: dict) -> str:
    runs = segment(transcript)
    latest = _latest_turn(transcript)
    model = (stdin.get("model") or {}).get("id") or (latest.model if latest else "")
    parts = []
    if runs:
        parts.append(f"ieakaso ▸ {runs[-1].mode}")
    if model:
        parts.append(model.removeprefix("claude-"))
    pct = _context_percent(transcript, stdin)
    if pct is not None:
        parts.append(f"ctx {pct}%")
    if runs:
        parts.append(f"run {fmt_compact(runs[-1].usage.new)} new")
        parts.append(f"session {fmt_compact(sum(r.usage.new for r in runs))} new")
    return " · ".join(parts)
