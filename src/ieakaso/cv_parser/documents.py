"""The Parsed documents of the LinkedIn profile and the reference letters (docs/adr/0004-parsed-documents.md).

Init records their Source documents in db/system_status.json; each gets a Parsed document in input/,
recorded next to its source. Nothing here ever blocks the CV: every problem is a warning on stdout.
"""

from pathlib import Path, PurePosixPath

from ieakaso import cv_parser
from ieakaso.cv_parser.errors import CvParseError
from ieakaso.cv_parser.files import sha, write_atomic

LINKEDIN_OUTPUT = PurePosixPath("input/linkedin.md")
LETTERS_OUTPUT = PurePosixPath("input/reference-letters")


def sync(root: Path, status: dict, force: bool, now: str) -> bool:
    """Bring every Parsed document up to date with its Source document; True when status changed."""
    documents = status.get("documents")
    if not isinstance(documents, dict):
        return False
    changed = False

    linkedin = documents.get("linkedin")
    if isinstance(linkedin, dict):
        path = linkedin.get("path")
        targets = {path: LINKEDIN_OUTPUT} if isinstance(path, str) and path else {}
        old = [linkedin["parsed"]] if isinstance(linkedin.get("parsed"), dict) else []
        new = _sync(root, targets, old, force, now)
        if new != old:
            changed = True
            if new:
                linkedin["parsed"] = new[0]
            else:
                linkedin.pop("parsed", None)

    letters = documents.get("reference_letters")
    if isinstance(letters, dict):
        paths = letters.get("paths")
        paths = [p for p in paths if isinstance(p, str) and p] if isinstance(paths, list) else []
        targets = {p: LETTERS_OUTPUT / f"{PurePosixPath(p).name}.md" for p in paths}
        old = [r for r in letters.get("parsed") or [] if isinstance(r, dict)]
        new = _sync(root, targets, old, force, now)
        if new != old:
            changed = True
            if new:
                letters["parsed"] = new
            else:
                letters.pop("parsed", None)

    return changed


def _sync(root: Path, targets: dict[str, PurePosixPath], old: list[dict], force: bool, now: str) -> list[dict]:
    """The new records for targets (source path → output path); removes the outputs of sources that are gone."""
    previous = {record.get("source_path"): record for record in old}
    records = []
    for source_rel, output_rel in targets.items():
        if not (root / source_rel).is_file():
            continue
        record = _parse_one(root, source_rel, output_rel, previous.pop(source_rel, None), force, now)
        if record:
            records.append(record)
    for record in previous.values():
        if _keep_after_source_is_gone(root, record, force):
            records.append(record)
    return records


def _parse_one(
    root: Path, source_rel: str, output_rel: PurePosixPath, previous: dict | None, force: bool, now: str
) -> dict | None:
    source = root / source_rel
    output = root / output_rel
    current = output.read_bytes() if output.is_file() else None
    base = {
        "source_path": source_rel,
        "source_sha256": sha(source.read_bytes()),
        "parser_version": cv_parser.PARSER_VERSION,
    }
    unchanged = previous is not None and all(previous.get(key) == value for key, value in base.items())
    if unchanged and "unreadable" in previous:
        return previous  # already reported; silent until the source or the parser changes
    if (
        unchanged
        and current is not None
        and previous.get("output_path") == output_rel.as_posix()
        and previous.get("output_sha256") == sha(current)
    ):
        return previous

    try:
        new = cv_parser.parse(source).encode("utf-8")
    except CvParseError as error:
        if current is not None and previous and previous.get("output_sha256") == sha(current):
            output.unlink()
        print(f"Warning: {source_rel} can't be read, so Ieakaso carries on without it. {error}")
        return {**base, "unreadable": str(error), "parsed_at": now}

    edited_by_hand = current is not None and current != new and (previous or {}).get("output_sha256") != sha(current)
    if edited_by_hand and not force:
        print(
            f"Warning: {output_rel} was changed by hand since it was last parsed, so it was not replaced. "
            f"Put your changes in {source_rel} instead, or run again with --force to replace it."
        )
        return previous
    if current != new:
        write_atomic(output, new)
        print(f"Wrote {output_rel} from {source_rel}.")
    return {**base, "output_path": output_rel.as_posix(), "output_sha256": sha(new), "parsed_at": now}


def _keep_after_source_is_gone(root: Path, record: dict, force: bool) -> bool:
    """Remove the Parsed document of a source that is gone; True when it must stay recorded (hand-edited)."""
    output_rel = record.get("output_path")
    if not isinstance(output_rel, str) or not output_rel.startswith("input/") or not output_rel.endswith(".md"):
        return False
    output = root / output_rel
    if not output.is_file():
        return False
    if sha(output.read_bytes()) != record.get("output_sha256") and not force:
        print(
            f"Warning: {output_rel} was changed by hand, but its source {record.get('source_path')} is gone. "
            "It was kept; run again with --force to delete it."
        )
        return True
    output.unlink()
    print(f"Removed {output_rel}: its source {record.get('source_path')} is gone.")
    return False
