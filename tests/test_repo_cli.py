import tomllib
from pathlib import Path

from conftest import Streams

from ieakaso.repo import remember_root
from ieakaso.repo.cli import main


def remember(cwd: Path, config_dir: Path, *args: str, streams: Streams | None = None) -> int:
    streams = streams or Streams()
    return main(["remember", *args], cwd=cwd, config_dir=config_dir, out=streams.out, err=streams.err)


def remembered(config_dir: Path) -> str:
    return tomllib.loads((config_dir / "repo.toml").read_text())["root"]


def test_remember_writes_the_repo_root_when_there_is_no_file(repo: Path, config_dir: Path, streams: Streams):
    assert remember(repo / "input/candidate", config_dir, streams=streams) == 0

    assert remembered(config_dir) == str(repo.resolve())
    assert streams.out.getvalue() == f"remembered {repo.resolve()} in {config_dir / 'repo.toml'}\n"


def test_remember_leaves_a_different_live_repo_alone(repo: Path, other_repo: Path, config_dir: Path, streams: Streams):
    remember(other_repo, config_dir)
    before = (config_dir / "repo.toml").read_text()

    assert remember(repo, config_dir, streams=streams) == 4

    assert (config_dir / "repo.toml").read_text() == before
    assert str(other_repo.resolve()) in streams.err.getvalue()


def test_remember_replace_switches_to_this_repo(repo: Path, other_repo: Path, config_dir: Path):
    remember(other_repo, config_dir)

    assert remember(repo, config_dir, "--replace") == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_overwrites_a_remembered_repo_that_is_gone(repo: Path, tmp_path: Path, config_dir: Path):
    remember_root(config_dir, tmp_path / "moved-away")

    assert remember(repo, config_dir) == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_is_idempotent(repo: Path, config_dir: Path):
    remember(repo, config_dir)

    assert remember(repo, config_dir) == 0

    assert remembered(config_dir) == str(repo.resolve())


def test_remember_outside_a_repo_writes_nothing(tmp_path: Path, config_dir: Path, streams: Streams):
    assert remember(tmp_path, config_dir, streams=streams) == 2

    assert not config_dir.exists()
    assert "is not inside an Ieakaso repo" in streams.err.getvalue()


def test_remember_reports_a_file_it_cannot_write(repo: Path, tmp_path: Path, streams: Streams):
    blocker = tmp_path / "config"
    blocker.write_text("a file where the folder should be")

    assert remember(repo, blocker / "ieakaso", streams=streams) == 1

    assert "can't write" in streams.err.getvalue()


def test_remember_sees_a_symlinked_path_to_this_repo_as_the_same(repo: Path, tmp_path: Path, config_dir: Path):
    link = tmp_path / "link-to-repo"
    link.symlink_to(repo)
    remember_root(config_dir, link)

    assert remember(repo, config_dir) == 0
