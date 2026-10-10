"""Development-only cleaner: returns the repo to a fresh state (no user data).

Never exposed to the candidate: not an `ieakaso` command, not a `/ieakaso` mode.
"""

import argparse
import filecmp
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# User data outside input/ and output/. Must stay in sync with .gitignore
# (tests/test_cleaner_drift.py checks it against the real repo).
USER_FILES = ("config.yml", "db/system_status.json", "db/ieakaso_db.json")
USER_FOLDERS = ("input", "output")
KEEP_NAMES = (".gitkeep",)
KEEP_FILES = ("input/documents/README.md",)
DEFAULT_BACKUP_DIR = Path.home() / ".ieakaso-backups"


@dataclass
class CleanReport:
    deleted: list[Path] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    backup: Path | None = None


def user_data(root: Path) -> list[Path]:
    """The user data files under root, relative to it, sorted."""
    found = [Path(rel) for rel in USER_FILES if (root / rel).is_file()]
    for folder in USER_FOLDERS:
        for path in sorted((root / folder).rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and path.name not in KEEP_NAMES and rel.as_posix() not in KEEP_FILES:
                found.append(rel)
    return sorted(found)


def clean(root: Path, backup_dir: Path | None = None, dry_run: bool = False) -> CleanReport:
    """Delete the user data under root, backing it up to backup_dir first when given."""
    deleted = user_data(root)
    report = CleanReport(deleted=deleted, removed_dirs=_dirs_left_empty(root, deleted))
    if dry_run:
        return report
    if backup_dir is not None and deleted:
        report.backup = _backup(root, deleted, backup_dir)
    for rel in deleted:
        (root / rel).unlink()
    # Deepest first, so a parent is empty by the time it is removed.
    for rel in sorted(report.removed_dirs, key=lambda p: len(p.parts), reverse=True):
        (root / rel).rmdir()
    return report


def restore(root: Path, backup: Path, backup_dir: Path) -> CleanReport:
    """Clean root (backing up its current user data), then copy the backup back in."""
    report = clean(root, backup_dir=backup_dir)
    for path in backup.rglob("*"):
        if path.is_file():
            target = root / path.relative_to(backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return report


def list_backups(backup_dir: Path) -> list[Path]:
    """The backups in backup_dir, oldest first."""
    if not backup_dir.is_dir():
        return []
    return sorted((p for p in backup_dir.iterdir() if p.is_dir()), key=_backup_order)


def _dirs_left_empty(root: Path, deleted: list[Path]) -> list[Path]:
    """Folders under input/ and output/ that hold nothing once `deleted` is gone."""
    gone = {root / rel for rel in deleted}
    dirs = []
    for folder in USER_FOLDERS:
        for path in (root / folder).rglob("*"):
            if path.is_dir() and all(p in gone or p.is_dir() for p in path.rglob("*")):
                dirs.append(path.relative_to(root))
    return sorted(dirs)


def _now() -> datetime:
    return datetime.now()


def _backup(root: Path, files: list[Path], backup_dir: Path) -> Path:
    """Copy files into a new timestamped folder in backup_dir and check every copy."""
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    target, n = backup_dir / stamp, 1
    while target.exists():
        n += 1
        target = backup_dir / f"{stamp}-{n}"
    for rel in files:
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target / rel)
        if not filecmp.cmp(root / rel, target / rel, shallow=False):
            raise OSError(f"backup of {rel} does not match the original; nothing was deleted")
    return target


def _backup_order(path: Path) -> tuple[str, int]:
    """Sort key for `<date>-<time>[-n]`, so `-10` comes after `-2`."""
    date, time, *n = path.name.split("-")
    return f"{date}-{time}", int(n[0]) if n else 1



def is_ieakaso_repo(path: Path) -> bool:
    try:
        project = tomllib.loads((path / "pyproject.toml").read_text())["project"]
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return False
    return project.get("name") == "ieakaso" and (path / "ai/skills/ieakaso").is_dir()


def find_root(start: Path) -> Path | None:
    """The nearest ieakaso repo at or above start."""
    for path in [start, *start.parents]:
        if is_ieakaso_repo(path):
            return path
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ieakaso.devtools.cleaner",
        description="Development only: return the repo to a fresh state. Always backs up first.",
    )
    parser.add_argument("command", choices=["clean", "restore", "list"])
    parser.add_argument("backup", nargs="?", help="restore: backup name (default: newest)")
    parser.add_argument("--root", type=Path, help="repo root (default: found from the current folder)")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--dry-run", action="store_true", help="clean: list what would go, change nothing")
    args = parser.parse_args(argv)

    root = (args.root or find_root(Path.cwd()) or Path.cwd()).resolve()
    if not is_ieakaso_repo(root):
        print(f"error: {root} is not the ieakaso repo; nothing changed", file=sys.stderr)
        return 2

    if args.command == "list":
        for backup in list_backups(args.backup_dir):
            print(backup.name)
        return 0

    if args.command == "clean":
        report = clean(root, backup_dir=args.backup_dir, dry_run=args.dry_run)
        _print_report(report, dry_run=args.dry_run)
        return 0

    backups = list_backups(args.backup_dir)
    if args.backup:
        backups = [b for b in backups if b.name == args.backup]
    if not backups:
        wanted = f"backup {args.backup}" if args.backup else "backups"
        print(f"error: no {wanted} in {args.backup_dir}; nothing changed", file=sys.stderr)
        return 1
    report = restore(root, backups[-1], backup_dir=args.backup_dir)
    _print_report(report)
    print(f"restored {backups[-1].name}")
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
