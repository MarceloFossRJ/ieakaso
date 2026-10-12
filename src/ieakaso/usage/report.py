"""Format the Run summary and the status line."""

from ieakaso.usage.runs import split_runs
from ieakaso.usage.transcript import Transcript, Usage

# Context window sizes of the models we know; the one place to extend. Unknown models show no size.
CONTEXT_WINDOWS = {"claude-opus-5-5": 1_000_000, "claude-sonnet-5-5": 1_000_000}

NO_RUN = "Ieakaso usage: no Ieakaso Run in this Session yet."
ESTIMATE_NOTE = (
    "~ estimated: the transcript did not record the final output count of some messages; "
    "the range is the 10th-90th percentile"
)


def fmt_tokens(n: int, *, trim: bool = False) -> str:
    """12.4k, 120k, 1.5M. With trim, no trailing '.0': 39k, not 39.0k."""
    if n < 1000:
        return str(n)
    if n < 100_000:
        text = f"{n / 1000:.1f}k"
    elif n < 1_000_000:
        text = f"{n / 1000:.0f}k"
    else:
        text = f"{n / 1_000_000:.1f}M"
    return text.replace(".0", "") if trim else text


def fmt_compact(n: int) -> str:
    return fmt_tokens(n, trim=True)


def _percent(part: int, whole: int) -> int:
    return round(part * 100 / whole)


def _out(usage: Usage) -> str:
    if not usage.estimated:
        return fmt_tokens(usage.out)
    low, high = usage.out - usage.out_low_gap, usage.out + usage.out_high_gap
    return f"~{fmt_tokens(usage.out)} ({fmt_tokens(low)}–{fmt_tokens(high)})"


def _split(usage: Usage) -> str:
    return f"in {fmt_tokens(usage.fresh_input)} · out {_out(usage)} · cache read {fmt_tokens(usage.cache_read)}"


def _new(usage: Usage) -> str:
    return ("~" if usage.estimated else "") + fmt_compact(usage.new)


def _latest_turn(transcript: Transcript):
    """The latest main-chain message that spent tokens: where Context fill is read."""
    return next((t for t in reversed(transcript.turns) if t.counts), None)


def summary(transcript: Transcript) -> str:
    runs = split_runs(transcript)
    if not runs:
        return NO_RUN
    run = runs[-1]
    title = f"── Ieakaso · {run.mode} (so far) "
    lines = [
        title + "─" * max(3, 50 - len(title)),
        f"Model     {', '.join(run.models) or 'unknown'}",
        f"Tokens    {_split(run.usage)}",
    ]
    latest = _latest_turn(transcript)
    if latest:
        fill, window = latest.usage.context, CONTEXT_WINDOWS.get(latest.model)
        size = f" / {fmt_compact(window)} ({_percent(fill, window)}%)" if window else ""
        lines.append(f"Context   {fmt_compact(fill)}{size}")
    for agent in run.agent_runs:
        lines.append(f"  Agent run  {agent.agent_type} ({', '.join(agent.models)})   {_split(agent.usage)}")
    total = Usage.total(r.usage for r in runs)
    lines.append(f"Session   {len(runs)} {'Run' if len(runs) == 1 else 'Runs'} · {_split(total)}")
    if total.estimated:
        lines.append(ESTIMATE_NOTE)
    return "\n".join(lines)


def _context_percent(transcript: Transcript, host_status: dict) -> int | None:
    """Prefer what Claude Code reports; else compute from the transcript."""
    window = host_status.get("context_window") or {}
    pct = window.get("used_percentage")
    if isinstance(pct, (int, float)):
        return round(pct)
    latest = _latest_turn(transcript)
    if latest is None:
        return None
    size = window.get("context_window_size") or CONTEXT_WINDOWS.get(latest.model)
    return _percent(latest.usage.context, size) if size else None


def statusline(transcript: Transcript, host_status: dict) -> str:
    """host_status is the JSON Claude Code passes the status line command on stdin."""
    runs = split_runs(transcript)
    latest = _latest_turn(transcript)
    model = (host_status.get("model") or {}).get("id") or (latest.model if latest else "")
    parts = []
    if runs:
        parts.append(f"ieakaso ▸ {runs[-1].mode}")
    if model:
        parts.append(model.removeprefix("claude-"))
    pct = _context_percent(transcript, host_status)
    if pct is not None:
        parts.append(f"ctx {pct}%")
    if runs:
        parts.append(f"run {_new(runs[-1].usage)} new")
        parts.append(f"session {_new(Usage.total(r.usage for r in runs))} new")
    return " · ".join(parts)
