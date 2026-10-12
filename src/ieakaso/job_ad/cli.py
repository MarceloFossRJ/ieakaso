"""`uv run python -m ieakaso.job_ad fetch <url>`: writes the Job ad as Markdown to stdout.

Exit codes: 0 ad written, 1 fetch failed (network error, timeout, HTTP status >= 400), 2 not readable
without the candidate (login wall, closed or expired ad), 3 page fetched but no ad content found.
The message for exits 1-3 goes to stderr. The fetcher never sends candidate data.
"""

import argparse
import sys
from collections.abc import Callable

from ieakaso.job_ad.errors import JobAdError
from ieakaso.job_ad.extract import extract
from ieakaso.job_ad.fetch import Page, fetch_page


def main(argv: list[str] | None = None, fetch: Callable[[str], Page] = fetch_page) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.job_ad",
        description="Read a Job ad from a URL and write it as Markdown, without WebFetch.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_command = commands.add_parser("fetch", help="fetch one Job ad and write it to stdout")
    fetch_command.add_argument("url", help="address of the Job ad")
    args = parser.parse_args(argv)

    try:
        page = fetch(args.url)
        if page.truncated:
            print("note: the page was longer than the size limit and was cut off.", file=sys.stderr)
        text = extract(page.html, page.url)
    except JobAdError as error:
        print(error, file=sys.stderr)
        return error.exit_code
    print(text, end="")
    return 0
