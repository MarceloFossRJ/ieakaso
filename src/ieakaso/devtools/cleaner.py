"""Development-only cleaner: returns the repo to a fresh state (no user data), or the Set-up state (no Applications).

Never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.
"""

import argparse
import filecmp
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ieakaso.repo import find_root, is_ieakaso_repo
from ieakaso.tracker.store import DB_PATH

# User data outside input/ and output/. Must stay in sync with .gitignore
# (tests/test_cleaner_drift.py checks it against the real repo).
USER_FILES = ("config.yml", "db/system_status.json", DB_PATH.as_posix())
USER_PATTERNS = ("db/.*.tmp",)  # temp files an interrupted atomic write leaves behind
USER_FOLDERS = ("input", "output")
KEEP_NAMES = (".gitkeep",)
KEEP_FILES = ("input/documents/README.md",)
DEFAULT_BACKUP_DIR = Path.home() / ".ieakaso-backups"


@dataclass(frozen=True)
class Scope:
    """What a clean deletes: files, glob patterns, and folders whose contents go (placeholders kept)."""

    files: tuple[str, ...]
    patterns: tuple[str, ...]
    folders: tuple[str, ...]


FRESH = Scope(USER_FILES, USER_PATTERNS, USER_FOLDERS)
# The Applications' share of the user data; deleting it leaves the Set-up state.
# The pattern matches the tracker's temp files (tracker/store.py, `save`).
APPLICATIONS = Scope(
    (DB_PATH.as_posix(),),
    (f"{DB_PATH.parent.as_posix()}/.{DB_PATH.name}.*.tmp",),
    ("output/applications",),
)


@dataclass
class CleanReport:
    deleted: list[Path] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    backup: Path | None = None


def user_data(root: Path, applications_only: bool = False) -> list[Path]:
    """The user data files under root, relative to it, sorted. Only the Applications' when applications_only."""
    scope = APPLICATIONS if applications_only else FRESH
    found = [Path(rel) for rel in scope.files if (root / rel).is_file()]
    found += [p.relative_to(root) for pattern in scope.patterns for p in root.glob(pattern) if p.is_file()]
    for folder in scope.folders:
        for path in sorted((root / folder).rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and path.name not in KEEP_NAMES and rel.as_posix() not in KEEP_FILES:
                found.append(rel)
    return sorted(found)


def clean(
    root: Path, backup_dir: Path | None = None, dry_run: bool = False, applications_only: bool = False
) -> CleanReport:
    """Delete the user data under root, or only the Applications' when applications_only.

    Backs it up to backup_dir first when given.
    """
    deleted = user_data(root, applications_only)
    folders = (APPLICATIONS if applications_only else FRESH).folders
    report = CleanReport(deleted=deleted, removed_dirs=_dirs_left_empty(root, deleted, folders))
    if dry_run:
        return report
    if backup_dir is not None and (deleted or report.removed_dirs):
        report.backup = _backup(root, report, backup_dir)
    for rel in deleted:
        (root / rel).unlink()
    # Deepest first, so a parent is empty by the time it is removed.
    for rel in sorted(report.removed_dirs, key=lambda p: len(p.parts), reverse=True):
        (root / rel).rmdir()
    return report


def _dirs_left_empty(root: Path, deleted: list[Path], folders: tuple[str, ...]) -> list[Path]:
    """Folders under `folders` that hold nothing once `deleted` is gone."""
    gone = {root / rel for rel in deleted}
    dirs = []
    for folder in folders:
        for path in (root / folder).rglob("*"):
            if path.is_dir() and all(p in gone or p.is_dir() for p in path.rglob("*")):
                dirs.append(path.relative_to(root))
    return sorted(dirs)


def _now() -> datetime:
    return datetime.now().astimezone()


def _backup(root: Path, report: CleanReport, backup_dir: Path) -> Path:
    """Copy what report will delete into a new timestamped folder in backup_dir, checking every copy."""
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    target, n = backup_dir / stamp, 1
    while target.exists():
        n += 1
        target = backup_dir / f"{stamp}-{n}"
    for rel in report.removed_dirs:
        (target / rel).mkdir(parents=True, exist_ok=True)
    for rel in report.deleted:
        _copy(root, target, rel)
        if not filecmp.cmp(root / rel, target / rel, shallow=False):
            raise OSError(f"backup of {rel} does not match the original; nothing was deleted")
    return target


def _copy(src_root: Path, dst_root: Path, rel: Path) -> None:
    (dst_root / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_root / rel, dst_root / rel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.devtools.cleaner",
        description="Development only: return the repo to a fresh state, or the Set-up state. Always backs up first.",
    )
    parser.add_argument("command", choices=["clean"])
    parser.add_argument(
        "--applications", action="store_true", help="delete only the Applications, keeping the setup (the Set-up state)"
    )
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    if not is_ieakaso_repo(root):
        print(f"error: {root} is not the ieakaso repo; nothing changed", file=sys.stderr)
        return 2

    report = clean(root, backup_dir=args.backup_dir, dry_run=args.dry_run, applications_only=args.applications)
    _print_report(report, dry_run=args.dry_run)
    return 0


def _print_report(report: CleanReport, dry_run: bool = False) -> None:
    verb = "would delete" if dry_run else "deleted"
    for rel in report.deleted:
        print(f"{verb} {rel}")
    for rel in report.removed_dirs:
        print(f"{verb} folder {rel}/")
    if report.backup:
        print(f"backup: {report.backup}")
    if not report.deleted and not report.removed_dirs:
        print("already clean")


if __name__ == "__main__":
    sys.exit(main())
