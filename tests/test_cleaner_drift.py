"""The cleaner's keep rule must match .gitignore. Reads the real repo; never writes to it."""

import subprocess
from pathlib import Path

from ieakaso.devtools.cleaner import USER_FILES, USER_FOLDERS, user_data

REPO = Path(__file__).resolve().parents[1]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def ignored(paths: list[str]) -> set[str]:
    return set(git("check-ignore", *paths).stdout.split())


def test_everything_the_cleaner_deletes_is_gitignored():
    # Probe paths make this meaningful even when the real repo is already clean.
    probes = [*USER_FILES, *(f"{folder}/probe/file.pdf" for folder in USER_FOLDERS)]
    found = [rel.as_posix() for rel in user_data(REPO)]

    assert set(probes + found) - ignored(probes + found) == set()


def test_the_cleaner_never_deletes_a_tracked_file():
    tracked = set(git("ls-files").stdout.split())

    assert {rel.as_posix() for rel in user_data(REPO)} & tracked == set()
