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
from datetime import UTC, datetime
from pathlib import Path

from ieakaso.cv_parser import PARSER_VERSION, CvParseError, parse
from ieakaso.repo import find_root, is_ieakaso_repo

STATUS = Path("db/system_status.json")
OUTPUT = Path("input/cv.md")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.cv_parser",
        description="Write the Parsed CV (input/cv.md) from the Source CV recorded by /ieakaso init.",
    )
    parser.add_argument("--force", action="store_true", help="overwrite input/cv.md even if it was edited by hand")
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    if not is_ieakaso_repo(root):
        print(f"error: {root} is not the ieakaso repo; nothing changed", file=sys.stderr)
        return 2

    status = _read_status(root)
    cv = _cv_record(status)
    source_rel = cv.get("path")
    if not source_rel or not (root / source_rel).is_file():
        print(
            "No main CV is recorded, or the recorded file is gone. Run /ieakaso init to choose your CV.",
            file=sys.stderr,
        )
        return 2

    source_bytes = (root / source_rel).read_bytes()
    output = root / OUTPUT
    current = output.read_bytes() if output.is_file() else None
    recorded = cv.get("parsed") or {}
    if current is not None and _matches(recorded, _fingerprint(source_rel, source_bytes, current)):
        print(f"{OUTPUT} is up to date with {source_rel}.")
        return 0

    try:
        new = parse(root / source_rel).encode("utf-8")
    except CvParseError as error:
        print(
            f"{error}\nPut the corrected file in input/documents/cv/. If its name changed, run "
            "/ieakaso init to choose it as your main CV; otherwise run /ieakaso cv-parser again. "
            f"{OUTPUT} was not changed.",
            file=sys.stderr,
        )
        return 1

    edited_by_hand = current is not None and current != new and recorded.get("output_sha256") != _sha(current)
    if edited_by_hand and not args.force:
        _print_overwrite_diff(current, new, source_rel)
        return 3

    if current != new:
        _write_atomic(output, new)
    cv["parsed"] = {
        **_fingerprint(source_rel, source_bytes, new),
        "parsed_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    _write_atomic(root / STATUS, (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"Wrote {OUTPUT} from {source_rel}.")
    return 0


def _read_status(root: Path) -> dict:
    """db/system_status.json, or {} when it is missing or not a JSON object."""
    try:
        status = json.loads((root / STATUS).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return status if isinstance(status, dict) else {}


def _cv_record(status: dict) -> dict:
    """status["documents"]["cv"], the dict itself so changes to it are saved; {} when absent."""
    documents = status.get("documents")
    cv = documents.get("cv") if isinstance(documents, dict) else None
    return cv if isinstance(cv, dict) else {}


def _fingerprint(source_rel: str, source: bytes, output: bytes) -> dict:
    """What a parse depends on and produced; the Parsed CV is up to date while all of it matches."""
    return {
        "source_path": source_rel,
        "source_sha256": _sha(source),
        "parser_version": PARSER_VERSION,
        "output_sha256": _sha(output),
    }


def _matches(recorded: dict, fingerprint: dict) -> bool:
    return all(recorded.get(key) == value for key, value in fingerprint.items())


def _print_overwrite_diff(current: bytes, new: bytes, source_rel: str) -> None:
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
