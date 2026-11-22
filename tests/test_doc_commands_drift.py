"""Every command a document names exists: `uv run <name>` and `python -m ieakaso.<module>` (issue #87).

Slash commands (Mode entries) are checked by test_mode_entries_drift.py. Reads the real repo; never writes to it.
"""

import re
import tomllib
from pathlib import Path

from conftest import write_files

REPO = Path(__file__).resolve().parents[1]
DOCS = ["README.md", "AGENTS.md", "CONTEXT.md", "docs/**/*.md", "ai/**/*.md", ".claude/**/*.md", ".opencode/**/*.md"]
# A name in <angle brackets> is a placeholder, not a command.
UV_RUN = re.compile(r"uv run(?:\s+-\S+)*\s+([^\s`\"'<][^\s`\"']*)")
PYTHON_M = re.compile(r"python -m (ieakaso(?:\.\w+)*+)(?!\.<)")


def docs(root: Path) -> list[Path]:
    return sorted({path for pattern in DOCS for path in root.glob(pattern) if path.is_file()})


def runnable_names(root: Path) -> set[str]:
    """What `uv run` can start: the project's scripts, its dependencies, and python."""
    project = tomllib.loads((root / "pyproject.toml").read_text())
    requirements = project["project"].get("dependencies", [])
    for group in project.get("dependency-groups", {}).values():
        requirements += group
    names = {re.match(r"[A-Za-z0-9_.-]+", requirement).group() for requirement in requirements}
    return names | set(project["project"].get("scripts", {})) | {"python"}


def is_runnable(root: Path, module: str) -> bool:
    """`python -m module` runs: a package with __main__.py, or a module file with a __main__ guard."""
    path = root / "src" / Path(*module.split("."))
    if path.is_dir():
        return (path / "__main__.py").is_file()
    file = path.with_suffix(".py")
    return (
        file.is_file() and re.search(r"^if __name__ == [\"']__main__[\"']:", file.read_text(), re.MULTILINE) is not None
    )


def problems(root: Path) -> list[str]:
    names = runnable_names(root)
    found = []
    for path in docs(root):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            where = f"{path.relative_to(root).as_posix()}:{number}"
            for match in UV_RUN.finditer(line):
                if match.group(1) not in names:
                    found.append(f"{where}: `uv run {match.group(1)}`: no such script or dependency")
            for match in PYTHON_M.finditer(line):
                if not is_runnable(root, match.group(1)):
                    found.append(f"{where}: `python -m {match.group(1)}`: not a runnable module")
    return found


PYPROJECT = """\
[project]
name = "ieakaso"
dependencies = ["rich>=15.0.0"]

[project.scripts]
ieakaso-view = "ieakaso.viewer.cli:main"

[dependency-groups]
dev = ["pytest>=9.1.1"]
"""


def fake_repo(tmp_path: Path, docs: dict[str, str]) -> Path:
    write_files(tmp_path, {"pyproject.toml": PYPROJECT, **docs})
    return tmp_path


def test_a_uv_run_name_that_is_not_a_script_or_dependency_is_reported(tmp_path: Path):
    root = fake_repo(tmp_path, {"README.md": "Open it:\n\n```\nuv run ieakaso-viewer\n```\n"})

    assert problems(root) == ["README.md:4: `uv run ieakaso-viewer`: no such script or dependency"]


def test_scripts_dependencies_and_python_are_allowed(tmp_path: Path):
    root = fake_repo(
        tmp_path,
        {"AGENTS.md": "`uv run ieakaso-view`, `uv run pytest`, `uv run rich` and `uv run python -V`.\n"},
    )

    assert problems(root) == []


def test_a_module_that_cannot_run_is_reported(tmp_path: Path):
    root = fake_repo(
        tmp_path,
        {
            "src/ieakaso/__init__.py": "",
            "src/ieakaso/tracker/__init__.py": "",
            "src/ieakaso/tracker/__main__.py": "",
            "src/ieakaso/repo.py": 'if __name__ == "__main__":\n    pass\n',
            "src/ieakaso/layout.py": "ROOT = 1\n",
            "ai/skills/ieakaso/modes/a.md": (
                "Run `uv run python -m ieakaso.tracker upsert` and `python -m ieakaso.repo remember`.\n"
                "Then `python -m ieakaso.layout`, `python -m ieakaso.gone` and `python -m ieakaso.tracker.store`.\n"
            ),
        },
    )

    assert problems(root) == [
        "ai/skills/ieakaso/modes/a.md:2: `python -m ieakaso.layout`: not a runnable module",
        "ai/skills/ieakaso/modes/a.md:2: `python -m ieakaso.gone`: not a runnable module",
        "ai/skills/ieakaso/modes/a.md:2: `python -m ieakaso.tracker.store`: not a runnable module",
    ]


def test_placeholders_are_not_commands(tmp_path: Path):
    root = fake_repo(
        tmp_path,
        {
            "AGENTS.md": "A doc may name `uv run <name>`, `python -m ieakaso.<module>` or `python -m ieakaso.tracker.<x>`.\n"
        },
    )

    assert problems(root) == []


def test_every_command_the_docs_name_exists():
    assert problems(REPO) == []
