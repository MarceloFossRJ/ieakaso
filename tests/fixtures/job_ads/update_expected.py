"""Writes tests/fixtures/job_ads/expected/ from the current fetcher, reading the stored pages only (no network).

    uv run python tests/fixtures/job_ads/update_expected.py          # only missing ones
    uv run python tests/fixtures/job_ads/update_expected.py --all    # rewrite every one

An expected output is the spec: review each new or changed file against its page before committing it.
Pages the fetcher refuses (login wall, closed ad, empty shell) have no expected output.
It never touches the Sample pages in samples/: their expected outputs are written by hand.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from job_ad_fakes import FIXTURES, URL

from ieakaso.job_ad import JobAdError, extract


def main(rewrite_all: bool) -> int:
    for source in sorted(FIXTURES.glob("*.html")):
        target = FIXTURES / "expected" / f"{source.stem}.md"
        if target.exists() and not rewrite_all:
            continue
        try:
            output = extract(source.read_text("utf-8"), URL)
        except JobAdError:
            continue
        if not target.exists() or target.read_text("utf-8") != output:
            target.parent.mkdir(exist_ok=True)
            target.write_text(output, "utf-8")
            print(f"wrote {target.relative_to(FIXTURES.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(rewrite_all="--all" in sys.argv[1:]))
