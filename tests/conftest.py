from pathlib import Path

import pytest

# Files a fresh clone has: tracked placeholders and committed examples.
TRACKED = {
    "pyproject.toml": '[project]\nname = "ieakaso"\n',
    "ai/skills/ieakaso/SKILL.md": "# Ieakaso\n",
    "config_example.yml": "candidate:\n  name: John\n",
    "db/system_status_example.json": '{"init": {"status": "not_started"}}\n',
    "db/ieakaso_db_example.json": '{"meta": {"schema_version": 3}, "cv_versions": [], "records": []}\n',
    "input/.gitkeep": "",
    "input/parsed-documents/.gitkeep": "",
    "input/candidate/documents/.gitkeep": "",
    "input/candidate/documents/README.md": "# documents\n",
    "input/candidate/documents/cv/.gitkeep": "",
    "input/candidate/documents/linkedin/.gitkeep": "",
    "input/candidate/documents/peerlist/.gitkeep": "",
    "input/candidate/documents/reference_letters/.gitkeep": "",
    "input/candidate/documents/wellfound/.gitkeep": "",
    "input/candidate/documents/xing/.gitkeep": "",
    "output/.gitkeep": "",
    "output/applications/.gitkeep": "",
}

# The candidate's user data, as it looks after a completed init.
USER_DATA = {
    "config.yml": "candidate:\n  name: Real\n",
    "db/system_status.json": '{"init": {"status": "completed"}}\n',
    "db/ieakaso_db.json": "{}\n",
    "db/.ieakaso_db.json.k3x9q.tmp": "{}\n",
    "input/parsed-documents/cv.md": "# CV\n",
    "input/parsed-documents/linkedin.md": "# LinkedIn\n",
    "input/parsed-documents/reference-letters/letter.docx.md": "A letter\n",
    "input/parsed-documents/cv-versions/cv_2026-10-01.md": "# CV\n",
    "input/candidate/writing-style.md": "voice\n",
    "input/candidate/documents/cv/cv_en.pdf": "%PDF cv",
    "input/candidate/documents/linkedin/Profile.pdf": "%PDF linkedin",
    "input/candidate/documents/reference_letters/letter.docx": "letter",
    "input/candidate/documents/xing/nested/profile.pdf": "%PDF xing",
    "output/acme/cover_letter.md": "Dear Acme\n",
    "output/applications/acme_em_2026-10-15/acme_em_2026-10-15_job-ad.md": "Acme job ad\n",
    "output/applications/acme_em_2026-10-15/acme_em_2026-10-15_cover-letter.md": "Dear Acme\n",
}


def write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under root, by relative path, with its bytes."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def folders(root: Path) -> set[str]:
    """Every folder under root, by relative path."""
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_dir()}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write_files(root, TRACKED)
    write_files(root, USER_DATA)
    return root


@pytest.fixture
def backups(tmp_path: Path) -> Path:
    return tmp_path / "backups"
