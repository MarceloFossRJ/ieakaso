"""The move step (docs/adr/0006-input-split-by-who-writes.md): the first thing every parser run does.

A repo laid out before ADR 0006 keeps everything in `input/`: the Source documents in `input/documents/`, the Parsed
documents next to the candidate's own files, and each CV version's frozen copy in its folder. This moves every file to its place
in the split layout (`input/candidate/` is the candidate's, `input/parsed-documents/` is Ieakaso's) and rewrites the
paths the status file and the tracker's `cv_versions` hold. Files are moved, never regenerated, so a Parsed document
edited by hand is still detected. It never overwrites a file already at the new place: the conflict is reported and both
files stay. Once nothing is left in the old layout it does nothing.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ieakaso.cv_parser.files import write_atomic
from ieakaso.layout import CANDIDATE, DOCUMENTS, FROZEN, LETTERS_OUTPUT, LINKEDIN_OUTPUT, PARSED_CV, STATUS
from ieakaso.tracker import DB_PATH, TrackerError, load, save, set_cv_version_path

OLD_DOCUMENTS = "input/documents"
OLD_LETTERS = "input/reference-letters"
CANDIDATE_FILES = (  # written by the candidate, loose in input/ before the split
    "presentation.md",
    "professional-experience-extended.md",
    "professional-self-reflection.md",
    "writing-style.md",
)
OLD_PARSED = {"input/cv.md": PARSED_CV, "input/linkedin.md": LINKEDIN_OUTPUT}
OLD_FROZEN = ("parsed-cv.md", "parsed-cv.frozen.md")  # in a version folder; the first one unless the Source CV has that name
VERSION_FOLDER = re.compile(r"cv_\d{4}-\d{2}-\d{2}(_\d+)?")


@dataclass
class MoveReport:
    moved: int = 0
    rewritten: int = 0  # recorded paths changed in the status file and the tracker db
    warnings: list[str] = field(default_factory=list)


def run(root: Path) -> None:
    """Move what is left of the old layout, record the new paths, and print one summary line (and any warnings)."""
    report = MoveReport()
    _move_files(root, report)
    _move_empty_folders(root)  # before the rewrites: a recorded folder must exist at its new place
    _rewrite_status(root, report)
    _rewrite_cv_versions(root, report)
    if report.moved or report.rewritten:
        parts = [f"Moved {report.moved} file(s) into input/candidate/ and input/parsed-documents/"] if report.moved else []
        if report.rewritten:
            parts.append(f"{'updated' if parts else 'Updated'} {report.rewritten} recorded path(s)")
        print(f"{' and '.join(parts)} (docs/adr/0006-input-split-by-who-writes.md).")
    for warning in report.warnings:
        print(warning)
    return report


def _new_path(rel: str) -> str | None:
    """Where a path of the old layout is now, or None when it isn't one. A frozen copy has no recorded path."""
    path = PurePosixPath(rel)
    if rel in OLD_PARSED:
        return OLD_PARSED[rel].as_posix()
    if path.is_relative_to(OLD_LETTERS):
        return (LETTERS_OUTPUT / path.relative_to(OLD_LETTERS)).as_posix()
    if path.is_relative_to(OLD_DOCUMENTS):
        return (DOCUMENTS / path.relative_to(OLD_DOCUMENTS)).as_posix()
    if path.parent == PurePosixPath("input") and path.name in CANDIDATE_FILES:
        return (CANDIDATE / path.name).as_posix()
    return None


def _frozen_target(root: Path, path: Path) -> str | None:
    """Where the frozen copy `path` (repo-relative, in the old layout) goes, or None when it is not one."""
    rel = PurePosixPath(path)
    if rel.name not in OLD_FROZEN or rel.parent.parent != PurePosixPath(OLD_DOCUMENTS) / "cv":
        return None
    if not VERSION_FOLDER.fullmatch(rel.parent.name):
        return None  # a folder the candidate made: not ours
    # Only a Source CV named parsed-cv.md makes the parser name the frozen copy parsed-cv.frozen.md.
    if rel.name == "parsed-cv.md" and (root / rel.with_name("parsed-cv.frozen.md")).is_file():
        return None
    return (FROZEN / f"{rel.parent.name}.md").as_posix()


def _old_files(root: Path) -> list[Path]:
    files = [Path(rel) for rel in OLD_PARSED if (root / rel).is_file()]
    for folder in (OLD_LETTERS, OLD_DOCUMENTS):
        files += [p.relative_to(root) for p in sorted((root / folder).rglob("*")) if p.is_file()]
    files += [Path("input") / name for name in CANDIDATE_FILES if (root / "input" / name).is_file()]
    return [p for p in files if p.name != ".gitkeep"]


def _move_files(root: Path, report: MoveReport) -> None:
    plan = [(old, _frozen_target(root, old) or _new_path(old.as_posix())) for old in _old_files(root)]  # before any move
    for old, target in plan:
        rel = old.as_posix()
        if target is None:
            continue
        if (root / target).exists():
            report.warnings.append(
                f"Warning: {rel} was not moved: {target} already exists. Both were left as they are; "
                "keep the one you want and delete the other."
            )
            continue
        (root / target).parent.mkdir(parents=True, exist_ok=True)
        (root / old).rename(root / target)
        report.moved += 1


def _rewritten(root: Path, value):
    """`value` with every old path in it replaced by its new one, when the file is no longer at the old place, and
    how many were replaced."""
    if isinstance(value, str):
        target = _new_path(value)
        return (target, 1) if target and not (root / value).exists() else (value, 0)
    if isinstance(value, list):
        items = [_rewritten(root, item) for item in value]
        return [item for item, _ in items], sum(count for _, count in items)
    if isinstance(value, dict):
        items = {key: _rewritten(root, item) for key, item in value.items()}
        return {key: item for key, (item, _) in items.items()}, sum(count for _, count in items.values())
    return value, 0


def _rewrite_status(root: Path, report: MoveReport) -> None:
    try:
        status = json.loads((root / STATUS).read_text("utf-8"))
    except (OSError, ValueError):
        return
    new, changed = _rewritten(root, status)
    if changed:
        write_atomic(root / STATUS, (json.dumps(new, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        report.rewritten += changed


def _rewrite_cv_versions(root: Path, report: MoveReport) -> None:
    """Through the tracker module, like every other change to the db. A db it can't use is left for the next run."""
    db = load(root / DB_PATH, root=root)
    if db.error:
        return
    changed = 0
    for version in db.cv_versions:
        path, count = _rewritten(root, version["path"])
        if count:
            set_cv_version_path(db, version["id"], path)
            changed += 1
    if not changed:
        return
    try:
        save(db)
    except TrackerError as error:
        report.warnings.append(f"Warning: the CV versions' paths were not updated in {DB_PATH.name}: {error}")
        return
    report.rewritten += changed


def _move_empty_folders(root: Path) -> None:
    """Move the old folders that hold nothing to their new place (deepest first), so a folder the candidate made, and
    that the status file records, still exists. A folder with anything left in it stays."""
    for folder in (OLD_DOCUMENTS, OLD_LETTERS):
        for path in sorted((root / folder).rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                _move_empty(root, path)
        if (root / folder).is_dir() and not any((root / folder).iterdir()):
            _move_empty(root, root / folder)


def _move_empty(root: Path, folder: Path) -> None:
    target = _new_path(folder.relative_to(root).as_posix())
    if target:
        (root / target).mkdir(parents=True, exist_ok=True)
    folder.rmdir()
