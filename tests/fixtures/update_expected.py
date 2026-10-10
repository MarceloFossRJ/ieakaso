"""Writes tests/fixtures/expected/ from the current parser, and its manifest.json.

    uv run python tests/fixtures/update_expected.py          # only missing ones
    uv run python tests/fixtures/update_expected.py --all    # rewrite every one

An expected output is the spec: review each new or changed file against its source before
committing it. Changing an existing output needs a PARSER_VERSION raise first (in
src/ieakaso/cv_parser/__init__.py), so the setup check parses every candidate's CV again;
this script refuses otherwise and writes nothing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from test_cv_parser import MANIFEST, expected_outputs, expected_path, sources  # noqa: E402

from ieakaso.cv_parser import PARSER_VERSION, parse  # noqa: E402


def main(rewrite_all: bool) -> int:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"parser_version": None}
    same_version = manifest["parser_version"] == PARSER_VERSION

    pending = {}
    for source in sources():
        target = expected_path(source)
        if target.exists() and not rewrite_all:
            continue
        output = parse(source).encode("utf-8")
        if not target.exists() or target.read_bytes() != output:
            pending[target] = output

    changed = [t for t in pending if t.exists()]
    if changed and same_version:
        for target in changed:
            print(f"changed {target.relative_to(MANIFEST.parent)}")
        print(
            f"error: these outputs changed but PARSER_VERSION is still {PARSER_VERSION}. "
            "Raise it in src/ieakaso/cv_parser/__init__.py and run again; nothing was written.",
            file=sys.stderr,
        )
        return 1

    for target, output in pending.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
        print(f"wrote {target.relative_to(MANIFEST.parent)}")
    manifest = {"parser_version": PARSER_VERSION, "outputs": expected_outputs()}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(rewrite_all="--all" in sys.argv[1:]))
