"""Development-only backtest of the usage display's output estimate.

The estimate (`_estimate_outputs` in `ieakaso.usage.transcript`) can't be checked on the messages it estimates: their
true output count was never recorded. So this tool checks it on the messages whose count is known. It leaves each
final message out, calibrates on the Session's other final messages, estimates the left-out one from its visible
characters, and compares. If the method is sound, about 80% of true counts fall in the p10-p90 range and the median
error is small.

Never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.

    uv run python -m ieakaso.devtools.estimate_backtest [SESSION_ID | TRANSCRIPT.jsonl ...] [--all]
"""

import argparse
import os
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ieakaso.repo import find_root
from ieakaso.usage.transcript import (
    DEFAULT_OUTPUT_RATIO,
    Transcript,
    calibrate,
    estimate_output,
    find_transcript,
    is_calibration_turn,
    load,
)


@dataclass
class Result:
    sessions: int = 0
    samples: int = 0
    covered: int = 0  # true count within [low, high]
    default_used: int = 0  # too few other final messages to calibrate on
    errors: list[float] = field(default_factory=list)  # (estimate - true) / true, per sample
    misses: list[tuple[int, int, int, int]] = field(default_factory=list)  # (true, estimate, low, high)

    @property
    def median_abs_error(self) -> float:
        return statistics.median(abs(e) for e in self.errors) if self.errors else 0.0

    @property
    def median_bias(self) -> float:
        return statistics.median(self.errors) if self.errors else 0.0

    @property
    def worst(self) -> list[tuple[int, int, int, int]]:
        return sorted(self.misses, key=lambda m: -abs(m[1] - m[0]) / m[0])[:5]


def backtest(transcripts: list[Transcript]) -> Result:
    result = Result()
    for transcript in transcripts:
        turns = transcript.turns + [t for run in transcript.agent_runs for t in run.turns]
        samples = [t for t in turns if is_calibration_turn(t)]
        result.sessions += bool(samples)
        for left_out in samples:
            ratio = calibrate([t for t in samples if t is not left_out])
            est, low, high = estimate_output(left_out.visible_chars, 0, ratio)
            true = left_out.usage.out
            result.samples += 1
            result.default_used += ratio == DEFAULT_OUTPUT_RATIO
            result.errors.append((est - true) / true)
            if low <= true <= high:
                result.covered += 1
            else:
                result.misses.append((true, est, low, high))
    return result


def report(result: Result) -> str:
    if not result.samples:
        return "Estimate backtest: no final messages to test on."
    sessions = f"{result.sessions} Session{'' if result.sessions == 1 else 's'}"
    in_range = round(100 * result.covered / result.samples)
    lines = [
        f"Samples          {result.samples} final messages in {sessions}",
        f"In range         {result.covered} of {result.samples} ({in_range}%) — about 80% expected for a p10-p90 range",
        f"Median error     {result.median_abs_error:.0%} (estimate vs true output)",
        f"Median bias      {round(result.median_bias, 2) + 0:+.0%} (negative: estimates run low)",
        f"Default ratio    used for {result.default_used} (fewer than the minimum other final messages)",
    ]
    if result.misses:
        lines.append("Worst misses     true → estimate (range)")
        lines += [f"  {true} → {est} ({low}–{high})" for true, est, low, high in result.worst]
    return "\n".join(lines)


def _paths(args, environ) -> list[Path]:
    if args.all:
        if args.project_dir:
            folder = args.project_dir
        else:
            base = Path(environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
            folder = base / "projects" / str(find_root(Path.cwd()) or Path.cwd()).replace("/", "-")
        return sorted(folder.glob("*.jsonl"))
    targets = args.targets or [environ.get("CLAUDE_CODE_SESSION_ID", "")]
    paths = []
    for target in targets:
        path = Path(target) if target.endswith(".jsonl") else find_transcript(target)
        if path is None or not path.exists():
            print(f"Transcript not found: {target or '(no session id)'}", file=sys.stderr)
            continue
        paths.append(path)
    return paths


def main(argv: list[str] | None = None, environ=None) -> int:
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(
        prog="ieakaso.devtools.estimate_backtest",
        description="Check the usage display's output estimate on messages whose output count is known.",
    )
    parser.add_argument("targets", nargs="*", help="session ids or transcript .jsonl paths (default: this Session)")
    parser.add_argument("--all", action="store_true", help="every Session transcript of this repo's project folder")
    parser.add_argument("--project-dir", type=Path, help="with --all: the Claude Code project folder to read")
    args = parser.parse_args(argv)
    print(report(backtest([load(p) for p in _paths(args, environ)])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
