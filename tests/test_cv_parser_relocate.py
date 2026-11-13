"""The move step: every parser run first moves a repo laid out before ADR 0006 (everything in `input/`) to the split
layout, `input/candidate/` and `input/parsed-documents/`, and rewrites the paths the status file and the tracker hold."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import TRACKED, snapshot, write_files
from tracker_fakes import TODAY

from ieakaso.cv_parser import cli
from ieakaso.tracker import DB_PATH, load

CANDIDATE = "input/candidate"
INBOX = f"{CANDIDATE}/documents/cv"
PARSED = "input/parsed-documents"
V1, V2 = "cv_2026-10-15", "cv_2026-10-15_2"
MEMORY = ("presentation.md", "professional-experience-extended.md", "professional-self-reflection.md", "writing-style.md")
STATUS = "db/system_status.json"

# What the repo looked like before ADR 0006, by the new place of each file.
NEW_TO_OLD = {
    f"{PARSED}/linkedin.md": "input/linkedin.md",
    f"{PARSED}/reference-letters": "input/reference-letters",
    f"{PARSED}/cv.md": "input/cv.md",
    f"{CANDIDATE}/documents/": "input/documents/",
}


def run(repo: Path, *args: str) -> int:
    return cli.main([*args, "--root", str(repo)], today=TODAY)


def read_json(repo: Path, rel: str) -> dict:
    return json.loads((repo / rel).read_text())


def settled(repo: Path) -> dict:
    """The repo as the split layout holds it: files by path, the two JSON files parsed (their layout is not the point)."""
    files = snapshot(repo)
    for rel in (STATUS, DB_PATH.as_posix()):
        files[rel] = json.loads(files[rel])
    return files


def old_place(repo: Path, rel: str) -> str:
    """Where the file at `rel` in the split layout lay before it."""
    name = Path(rel).name
    if rel.startswith(f"{PARSED}/cv-versions/"):
        source_is_named_like_it = (repo / INBOX / Path(rel).stem / "parsed-cv.md").exists()
        return f"input/documents/cv/{Path(rel).stem}/" + ("parsed-cv.frozen.md" if source_is_named_like_it else "parsed-cv.md")
    for new, old in NEW_TO_OLD.items():
        if rel.startswith(new):
            return old + rel.removeprefix(new)
    if rel.startswith(f"{CANDIDATE}/") and name in MEMORY:
        return f"input/{name}"
    return rel


def to_old_layout(repo: Path, only: tuple[str, ...] = ()) -> None:
    """Put the files (all of them, or those under the `only` prefixes) and the recorded paths back as they were."""
    files = sorted(p.relative_to(repo).as_posix() for p in (repo / "input").rglob("*") if p.is_file() and p.name != ".gitkeep")
    moves = [(rel, old_place(repo, rel)) for rel in files]  # all decided before the first move
    for rel, target in moves:
        if target != rel and (not only or rel.startswith(only)):
            (repo / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(repo / rel, repo / target)
    for rel in (STATUS, DB_PATH.as_posix()):
        text = (repo / rel).read_text()
        for new, old in NEW_TO_OLD.items():
            if not only or new.startswith(only):
                text = text.replace(new, old)
        (repo / rel).write_text(text)


@pytest.fixture
def current(tmp_path: Path) -> Path:
    """A repo in the split layout that was parsed for real: two CV versions, a LinkedIn profile, a letter, the candidate's own files."""
    root = tmp_path / "repo"
    write_files(root, TRACKED)
    write_files(
        root,
        {
            f"{INBOX}/first.txt": "Jordan Example\nEngineer\n",
            f"{CANDIDATE}/documents/linkedin/Profile.md": "# Jordan\nLinkedIn\n",
            f"{CANDIDATE}/documents/reference_letters/acme.txt": "A letter\n",
            f"{CANDIDATE}/documents/xing/profile.pdf": "%PDF xing",
            **{f"{CANDIDATE}/{name}": f"{name}\n" for name in MEMORY},
            STATUS: json.dumps(
                {
                    "init": {"status": "completed"},
                    "documents": {
                        "cv": {"status": "found", "path": None},
                        "linkedin": {"status": "found", "path": f"{CANDIDATE}/documents/linkedin/Profile.md"},
                        "reference_letters": {
                            "status": "found",
                            "paths": [f"{CANDIDATE}/documents/reference_letters/acme.txt"],
                        },
                    },
                }
            ),
        },
    )
    assert run(root, "--main", "first.txt") == 0
    write_files(root, {f"{INBOX}/parsed-cv.md": "Second CV\n"})  # a Source CV that has the old frozen name
    assert run(root, "--main", "parsed-cv.md") == 0
    assert [v["id"] for v in load(root / DB_PATH).cv_versions] == [V1, V2]
    return root


def test_a_full_old_layout_moves_to_the_split_layout(current: Path, capsys):
    expected = settled(current)
    to_old_layout(current)
    assert (current / "input/cv.md").is_file() and (current / f"input/documents/cv/{V2}/parsed-cv.frozen.md").is_file()
    capsys.readouterr()

    assert run(current) == 0

    assert settled(current) == expected
    assert not (current / "input/documents").exists()
    assert not (current / "input/reference-letters").exists()
    lines = capsys.readouterr().out.splitlines()
    assert [line for line in lines if line.startswith("Moved")] == [lines[0]]
    assert "input/candidate/" in lines[0] and "input/parsed-documents/" in lines[0]


def test_the_frozen_copies_and_the_candidates_files_in_a_version_folder_are_told_apart(current: Path):
    to_old_layout(current)
    assert (current / f"input/documents/cv/{V2}/parsed-cv.md").read_text() == "Second CV\n"  # the Source CV

    run(current)

    assert sorted(p.name for p in (current / INBOX / V2).iterdir()) == ["parsed-cv.md"]
    assert (current / f"{PARSED}/cv-versions/{V2}.md").read_text() == "Second CV\n"
    assert (current / f"{PARSED}/cv-versions/{V1}.md").read_text() == "Jordan Example\nEngineer\n"


def test_a_partial_layout_moves_what_is_left(current: Path, capsys):
    expected = settled(current)
    to_old_layout(current, only=(f"{CANDIDATE}/documents/linkedin", f"{CANDIDATE}/presentation.md", f"{PARSED}/cv.md"))
    capsys.readouterr()

    assert run(current) == 0

    assert settled(current) == expected
    assert capsys.readouterr().out.startswith("Moved 3 file")


def test_missing_folders_are_created(current: Path):
    to_old_layout(current)
    shutil.rmtree(current / "input/candidate")
    shutil.rmtree(current / "input/parsed-documents")
    shutil.rmtree(current / "input/documents/xing", ignore_errors=True)

    run(current)

    assert (current / f"{PARSED}/cv.md").is_file()
    assert (current / f"{INBOX}/{V1}").is_dir()


def test_a_file_already_at_the_new_place_is_never_overwritten(current: Path, capsys):
    to_old_layout(current)
    write_files(current, {f"{CANDIDATE}/documents/linkedin/Profile.md": "# A newer profile\n"})
    capsys.readouterr()

    assert run(current) == 0

    out = capsys.readouterr().out
    assert "Warning: input/documents/linkedin/Profile.md was not moved: input/candidate/documents/linkedin/Profile.md already exists" in out
    assert (current / "input/documents/linkedin/Profile.md").read_text() == "# Jordan\nLinkedIn\n"
    assert (current / f"{CANDIDATE}/documents/linkedin/Profile.md").read_text() == "# A newer profile\n"
    assert (current / f"{PARSED}/cv.md").is_file()  # the rest moved
    # the status file still names the file that was not moved
    assert read_json(current, STATUS)["documents"]["linkedin"]["path"] == "input/documents/linkedin/Profile.md"


def test_running_it_twice_changes_nothing(current: Path, capsys):
    to_old_layout(current)
    run(current)
    after_first = snapshot(current)
    assert (current / f"{PARSED}/cv.md").is_file()
    capsys.readouterr()

    assert run(current) == 0

    assert snapshot(current) == after_first
    assert "Moved" not in capsys.readouterr().out


def test_a_conflict_is_reported_again_and_changes_nothing(current: Path, capsys):
    to_old_layout(current)
    write_files(current, {f"{CANDIDATE}/documents/linkedin/Profile.md": "# A newer profile\n"})
    run(current)
    after_first = snapshot(current)
    capsys.readouterr()

    run(current)

    assert snapshot(current) == after_first
    assert "was not moved" in capsys.readouterr().out


def test_a_hand_edited_parsed_cv_is_still_detected_after_the_move(current: Path, capsys):
    (current / f"{PARSED}/cv.md").write_text("Jordan Example\nEngineer\nMy own note\n")
    to_old_layout(current)
    capsys.readouterr()

    assert run(current) == 3

    assert (current / f"{PARSED}/cv.md").read_text() == "Jordan Example\nEngineer\nMy own note\n"
    assert "was changed by hand" in capsys.readouterr().out


def test_a_hand_edited_parsed_document_is_still_detected_after_the_move(current: Path, capsys):
    (current / f"{PARSED}/linkedin.md").write_text("# Jordan\nMy own note\n")
    to_old_layout(current)
    capsys.readouterr()

    run(current)

    assert (current / f"{PARSED}/linkedin.md").read_text() == "# Jordan\nMy own note\n"
    assert "was changed by hand" in capsys.readouterr().out


def test_the_paths_in_the_status_file_are_rewritten(current: Path):
    expected = read_json(current, STATUS)
    to_old_layout(current)
    assert "input/documents/" in (current / STATUS).read_text()

    run(current)

    assert read_json(current, STATUS) == expected
    assert read_json(current, STATUS)["documents"]["cv"]["path"] == f"{INBOX}/{V2}/parsed-cv.md"


def test_the_paths_of_the_cv_versions_are_rewritten_through_the_tracker(current: Path):
    expected = load(current / DB_PATH).cv_versions
    to_old_layout(current)
    assert load(current / DB_PATH).cv_versions[0]["path"] == f"input/documents/cv/{V1}/first.txt"

    run(current)

    assert load(current / DB_PATH).cv_versions == expected
    assert expected[0]["path"] == f"{INBOX}/{V1}/first.txt"


def test_it_moves_before_the_setup_is_checked(current: Path):
    to_old_layout(current)
    (current / STATUS).unlink()

    assert run(current) == 2

    assert (current / f"{PARSED}/cv.md").is_file()
    assert (current / f"{CANDIDATE}/writing-style.md").is_file()


def test_a_db_that_cannot_be_used_is_left_alone_and_its_paths_are_rewritten_on_the_next_run(current: Path):
    to_old_layout(current)
    db_text = (current / DB_PATH).read_text()
    (current / DB_PATH).write_text("{not json")

    assert run(current) == 5  # the files moved; the tracker could not be changed
    (current / DB_PATH).write_text(db_text)

    assert run(current) == 0
    assert load(current / DB_PATH).cv_versions[0]["path"] == f"{INBOX}/{V1}/first.txt"


def test_a_file_named_like_a_frozen_copy_in_a_folder_the_candidate_made_is_the_candidates(current: Path):
    to_old_layout(current)
    write_files(current, {"input/documents/cv/old-cvs/parsed-cv.md": "mine\n"})

    run(current)

    assert (current / INBOX / "old-cvs/parsed-cv.md").read_text() == "mine\n"
    assert not (current / PARSED / "cv-versions/old-cvs.md").exists()


def test_move_only_moves_and_parses_nothing(current: Path, capsys):
    to_old_layout(current)
    (current / "input/cv.md").write_text("stale\n")
    capsys.readouterr()

    assert run(current, "--move-only") == 0

    assert (current / f"{PARSED}/cv.md").read_text() == "stale\n"
    out = capsys.readouterr().out
    assert out.startswith("Moved") and "Wrote" not in out and "up to date" not in out


def test_an_empty_folder_the_candidate_made_is_moved_so_its_recorded_path_stays_true(current: Path):
    (current / INBOX / "old-cvs").mkdir()
    run(current)  # warns once and records the folder
    assert read_json(current, STATUS)["documents"]["cv"]["ignored_folders"] == [f"{INBOX}/old-cvs"]
    to_old_layout(current)
    shutil.rmtree(current / INBOX / "old-cvs")
    (current / "input/documents/cv/old-cvs").mkdir()

    run(current)

    assert (current / INBOX / "old-cvs").is_dir()
    assert not (current / "input/documents").exists()
    assert read_json(current, STATUS)["documents"]["cv"]["ignored_folders"] == [f"{INBOX}/old-cvs"]
