"""Writes tests/fixtures/expected/ from the current parser, for fixtures that have no expected output yet.

    uv run python tests/fixtures/update_expected.py          # only missing ones
    uv run python tests/fixtures/update_expected.py --all    # rewrite every one

An expected output is the spec: review each new or changed file against its source before
committing it, and raise PARSER_VERSION in the same commit when existing ones change.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from test_cv_parser import expected_path, sources  # noqa: E402

from ieakaso.cv_parser import parse  # noqa: E402


def main(rewrite_all: bool) -> None:
    for source in sources():
        target = expected_path(source)
        if target.exists() and not rewrite_all:
            continue
        output = parse(source).encode("utf-8")
        if target.exists() and target.read_bytes() == output:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
        print(f"wrote {target.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    main(rewrite_all="--all" in sys.argv[1:])
