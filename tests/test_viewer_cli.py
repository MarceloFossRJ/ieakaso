from pathlib import Path

import pytest
from conftest import Streams

from ieakaso.repo import remember_root
from ieakaso.viewer.cli import main


class Launcher:
    """Stands in for the Textual app: records the root it was opened on."""

    def __init__(self) -> None:
        self.roots: list[Path] = []

    def __call__(self, root: Path) -> None:
        self.roots.append(root)


@pytest.fixture
def launch() -> Launcher:
    return Launcher()


def view(cwd: Path, config_dir: Path, launch: Launcher, *args: str, streams: Streams | None = None) -> int:
    streams = streams or Streams()
    return main(list(args), cwd=cwd, config_dir=config_dir, launch=launch, err=streams.err)


def test_opens_the_repo_it_is_run_from(repo: Path, config_dir: Path, launch: Launcher):
    assert view(repo / "output/applications", config_dir, launch) == 0

    assert launch.roots == [repo.resolve()]


@pytest.fixture
def elsewhere(tmp_path: Path) -> Path:
    path = tmp_path / "home" / "somewhere"
    path.mkdir(parents=True)
    return path


def test_opens_the_remembered_repo_from_any_folder(repo: Path, elsewhere: Path, config_dir: Path, launch: Launcher):
    remember_root(config_dir, repo)

    assert view(elsewhere, config_dir, launch) == 0

    assert launch.roots == [repo.resolve()]


def test_the_repo_you_stand_in_beats_the_remembered_one(
    repo: Path, other_repo: Path, config_dir: Path, launch: Launcher
):
    remember_root(config_dir, repo)

    assert view(other_repo, config_dir, launch) == 0

    assert launch.roots == [other_repo.resolve()]


def test_root_beats_the_current_folder_and_the_remembered_repo(
    repo: Path, other_repo: Path, config_dir: Path, launch: Launcher
):
    remember_root(config_dir, repo)

    assert view(repo, config_dir, launch, "--root", str(other_repo)) == 0

    assert launch.roots == [other_repo.resolve()]


def test_no_repo_found_is_an_error_not_an_empty_table(
    elsewhere: Path, config_dir: Path, launch: Launcher, streams: Streams
):
    assert view(elsewhere, config_dir, launch, streams=streams) == 2

    assert launch.roots == []
    assert "can't find the Ieakaso repo: run it from the repo or pass --root" in streams.err.getvalue()


def test_a_remembered_repo_that_is_gone_is_an_error(
    tmp_path: Path, elsewhere: Path, config_dir: Path, launch: Launcher, streams: Streams
):
    gone = tmp_path / "moved-away"
    remember_root(config_dir, gone)
    before = (config_dir / "repo.toml").read_text()

    assert view(elsewhere, config_dir, launch, streams=streams) == 2

    assert launch.roots == []
    assert (config_dir / "repo.toml").read_text() == before
    assert (
        f"the remembered repo {gone} is gone: run /ieakaso init from the repo, or pass --root" in streams.err.getvalue()
    )


def test_a_root_that_is_not_a_repo_is_an_error(elsewhere: Path, config_dir: Path, launch: Launcher, streams: Streams):
    assert view(elsewhere, config_dir, launch, "--root", str(elsewhere), streams=streams) == 2

    assert launch.roots == []
    assert f"{elsewhere} is not an Ieakaso repo" in streams.err.getvalue()


def test_a_relative_root_is_read_from_the_current_folder(repo: Path, config_dir: Path, launch: Launcher):
    assert view(repo.parent, config_dir, launch, "--root", repo.name) == 0

    assert launch.roots == [repo.resolve()]
