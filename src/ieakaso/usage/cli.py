"""`uv run python -m ieakaso.usage start <mode> | summary | statusline`.

start: the Run start marker; the command appearing in the transcript is what begins a Run.
summary: the Run summary for the current Session. statusline: one line for the Claude Code status line,
fed the host's JSON on stdin. Neither ever fails: a missing transcript is a notice, exit 0.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from ieakaso.usage.report import statusline, summary
from ieakaso.usage.transcript import find_transcript, load


def _statusline(stdin) -> str:
    try:
        data = json.loads(stdin.read())
        data = data if isinstance(data, dict) else {}
        path = data.get("transcript_path")
        transcript = load(Path(path)) if isinstance(path, str) else load(Path("/nonexistent"))
        return statusline(transcript, data)
    except Exception:  # noqa: BLE001 - the status line must never crash
        return ""


def main(argv=None, stdin=None, environ=None, claude_dir=None, out=None) -> int:
    stdin = stdin or sys.stdin
    environ = os.environ if environ is None else environ
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="ieakaso.usage")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start").add_argument("mode")
    sub.add_parser("summary")
    sub.add_parser("statusline")
    args = parser.parse_args(argv)

    if args.command == "start":
        print(f"Ieakaso Run started: {args.mode}", file=out)
    elif args.command == "statusline":
        print(_statusline(stdin), file=out)
    else:
        path = find_transcript(environ.get("CLAUDE_CODE_SESSION_ID", ""), claude_dir)
        if path is None:
            print("Ieakaso usage: the Session transcript was not found, so there is no usage to show.", file=out)
        else:
            print(summary(load(path)), file=out)
    return 0
