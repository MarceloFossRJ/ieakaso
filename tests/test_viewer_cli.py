from pathlib import Path

import pytest
from conftest import TRACKED, write_files

from ieakaso.viewer.cli import main


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / "config" / "ieakaso"


class Launcher:
    """Stands in for the Textual app: records the root it was opened on."""

    def __init__(self) -> None:
        self.roots: list[Path] = []

    def __call__(self, root: Path) -> None:
        self.roots.append(root)


@pytest.fixture
def launch() -> Launcher:
    return Launcher()


def view(cwd: Path, config_dir: Path, launch: Launcher, *args: str) -> int:
    return main(list(args), cwd=cwd, config_dir=config_dir, launch=launch)


def test_opens_the_repo_it_is_run_from(repo: Path, config_dir: Path, launch: Launcher):
    assert view(repo / "output/applications", config_dir, launch) == 0

    assert launch.roots == [repo.resolve()]


def remember(config_dir: Path, root: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "repo.toml").write_text(f'root = "{root}"\n')


@pytest.fixture
def elsewhere(tmp_path: Path) -> Path:
    path = tmp_path / "home" / "somewhere"
    path.mkdir(parents=True)
    return path


def test_opens_the_remembered_repo_from_any_folder(repo: Path, elsewhere: Path, config_dir: Path, launch: Launcher):
    remember(config_dir, repo)

    assert view(elsewhere, config_dir, launch) == 0

    assert launch.roots == [repo.resolve()]


@pytest.fixture
def other_repo(tmp_path: Path) -> Path:
    root = tmp_path / "worktree"
    write_files(root, TRACKED)
    return root


def test_the_repo_you_stand_in_beats_the_remembered_one(
    repo: Path, other_repo: Path, config_dir: Path, launch: Launcher
):
    remember(config_dir, repo)

    assert view(other_repo, config_dir, launch) == 0

    assert launch.roots == [other_repo.resolve()]


def test_root_beats_the_current_folder_and_the_remembered_repo(
    repo: Path, other_repo: Path, config_dir: Path, launch: Launcher
):
    remember(config_dir, repo)

    assert view(repo, config_dir, launch, "--root", str(other_repo)) == 0

    assert launch.roots == [other_repo.resolve()]


def test_no_repo_found_is_an_error_not_an_empty_table(elsewhere: Path, config_dir: Path, launch: Launcher, capsys):
    assert view(elsewhere, config_dir, launch) == 2

    assert launch.roots == []
    assert "Can't find the Ieakaso repo: run it from the repo or pass --root" in capsys.readouterr().err


def test_a_remembered_repo_that_is_gone_is_an_error(
    tmp_path: Path, elsewhere: Path, config_dir: Path, launch: Launcher, capsys
):
    gone = tmp_path / "moved-away"
    remember(config_dir, gone)
    before = (config_dir / "repo.toml").read_text()

    assert view(elsewhere, config_dir, launch) == 2

    assert launch.roots == []
    assert (config_dir / "repo.toml").read_text() == before
    assert (
        f"The remembered repo {gone} is gone: run /ieakaso init from the repo, or pass --root"
        in capsys.readouterr().err
    )
