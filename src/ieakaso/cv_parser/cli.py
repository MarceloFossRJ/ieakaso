"""`uv run python -m ieakaso.cv_parser`: writes the Parsed CV from the Source CV init recorded.

Exit codes: 0 written or already up to date, 1 the Source CV can't be parsed, 2 setup is
missing (run /ieakaso init), 3 input/cv.md was edited by hand (diff printed; --force overwrites).
"""

import argparse
import difflib
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ieakaso.cv_parser import PARSER_VERSION, CvParseError, parse
from ieakaso.repo import find_root, is_ieakaso_repo

STATUS = Path("db/system_status.json")
OUTPUT = Path("input/cv.md")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.cv_parser",
        description="Write input/cv.md from the main CV recorded by /ieakaso init.",
    )
    parser.add_argument("--force", action="store_true", help="overwrite input/cv.md even if it was edited by hand")
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    if not is_ieakaso_repo(root):
        print(f"error: {root} is not the ieakaso repo; nothing changed", file=sys.stderr)
        return 2

    status = _read_status(root)
    cv = status.get("documents", {}).get("cv", {}) if isinstance(status, dict) else {}
    source_rel = cv.get("path") if isinstance(cv, dict) else None
    if not source_rel or not (root / source_rel).is_file():
        print(
            "No main CV is recorded, or the recorded file is gone. Run /ieakaso init to choose your CV.",
            file=sys.stderr,
        )
        return 2

    source = root / source_rel
    output = root / OUTPUT
    source_bytes = source.read_bytes()
    current = output.read_bytes() if output.is_file() else None
    recorded = cv.get("parsed") or {}

    if current is not None and recorded == {
        **recorded,
        "source_path": source_rel,
        "source_sha256": _sha(source_bytes),
        "parser_version": PARSER_VERSION,
        "output_sha256": _sha(current),
    }:
        print(f"{OUTPUT} is up to date with {source_rel}.")
        return 0

    try:
        new = parse(source).encode("utf-8")
    except CvParseError as error:
        print(
            f"{error}\nPut the corrected file in input/documents/cv/. If its name changed, run "
            "/ieakaso init to choose it as your main CV; otherwise run /ieakaso cv-parser again. "
            f"{OUTPUT} was not changed.",
            file=sys.stderr,
        )
        return 1

    hand_edited = current is not None and current != new and recorded.get("output_sha256") != _sha(current)
    if hand_edited and not args.force:
        diff = difflib.unified_diff(
            current.decode("utf-8", "replace").splitlines(keepends=True),
            new.decode("utf-8").splitlines(keepends=True),
            fromfile=f"{OUTPUT} (now)",
            tofile=f"{OUTPUT} (parsed from {source_rel})",
        )
        print("".join(diff), end="")
        print(
            f"\n{OUTPUT} was changed by hand since it was last parsed. Parsing again replaces it with the "
            "version above and discards those changes. To keep them, put them in your CV instead. "
            "Run again with --force to replace it."
        )
        return 3

    if current != new:
        _write_atomic(output, new)
    cv["parsed"] = {
        "source_path": source_rel,
        "source_sha256": _sha(source_bytes),
        "parser_version": PARSER_VERSION,
        "output_sha256": _sha(new),
        "parsed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_atomic(root / STATUS, (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"Wrote {OUTPUT} from {source_rel}.")
    return 0


def _read_status(root: Path):
    try:
        return json.loads((root / STATUS).read_text("utf-8"))
    except (OSError, ValueError):
        return None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    """Write next to path, then rename over it, so a failure never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
