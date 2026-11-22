import tomllib
from pathlib import Path

import pytest
from conftest import TRACKED, write_files

from ieakaso.repo import main


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / "config" / "ieakaso"


def remember(cwd: Path, config_dir: Path, *args: str) -> int:
    return main(["remember", *args], cwd=cwd, config_dir=config_dir)


def remembered(config_dir: Path) -> str:
    return tomllib.loads((config_dir / "repo.toml").read_text())["root"]


def test_remember_writes_the_repo_root_when_there_is_no_file(repo: Path, config_dir: Path, capsys):
    assert remember(repo / "input/candidate", config_dir) == 0

    assert remembered(config_dir) == str(repo.resolve())
    assert capsys.readouterr().out == f"remembered {repo.resolve()} in {config_dir / 'repo.toml'}\n"


@pytest.fixture
def other_repo(tmp_path: Path) -> Path:
    root = tmp_path / "other-clone"
    write_files(root, TRACKED)
    return root


def test_remember_leaves_a_different_live_repo_alone(repo: Path, other_repo: Path, config_dir: Path, capsys):
    remember(other_repo, config_dir)
    before = (config_dir / "repo.toml").read_text()
    capsys.readouterr()

    assert remember(repo, config_dir) == 4

    assert (config_dir / "repo.toml").read_text() == before
    assert str(other_repo.resolve()) in capsys.readouterr().err


def test_remember_replace_switches_to_this_repo(repo: Path, other_repo: Path, config_dir: Path):
    remember(other_repo, config_dir)

    assert remember(repo, config_dir, "--replace") == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_overwrites_a_remembered_repo_that_is_gone(repo: Path, tmp_path: Path, config_dir: Path):
    config_dir.mkdir(parents=True)
    (config_dir / "repo.toml").write_text(f'root = "{tmp_path / "moved-away"}"\n')

    assert remember(repo, config_dir) == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_is_idempotent(repo: Path, config_dir: Path):
    remember(repo, config_dir)

    assert remember(repo, config_dir) == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_outside_a_repo_writes_nothing(tmp_path: Path, config_dir: Path, capsys):
    assert remember(tmp_path, config_dir) == 2

    assert not config_dir.exists()
    assert "not inside the ieakaso repo" in capsys.readouterr().err


def test_remember_reports_a_file_it_cannot_write(repo: Path, tmp_path: Path, capsys):
    blocker = tmp_path / "config"
    blocker.write_text("a file where the folder should be")

    assert remember(repo, blocker / "ieakaso") == 1

    assert "can't write" in capsys.readouterr().err
