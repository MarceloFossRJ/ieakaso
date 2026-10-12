import io
import json

from usage_fakes import FakeSession

from ieakaso.usage.cli import main


def run(argv, tmp_path, env=None, stdin=""):
    out = io.StringIO()
    code = main(argv, stdin=io.StringIO(stdin), environ=env or {}, claude_dir=tmp_path, out=out)
    return code, out.getvalue()


def test_start_prints_an_acknowledgement(tmp_path):
    assert run(["start", "job-analyzer"], tmp_path) == (0, "Ieakaso Run started: job-analyzer\n")


def test_summary_finds_the_transcript_by_session_id(tmp_path):
    s = FakeSession(tmp_path, session_id="abc")
    s.start("init", "m1", inp=1)
    code, out = run(["summary"], tmp_path, env={"CLAUDE_CODE_SESSION_ID": "abc"})
    assert code == 0 and out.startswith("── Ieakaso · init (so far)")


def test_summary_without_a_session_id_or_transcript_is_a_notice_not_an_error(tmp_path):
    for env in ({}, {"CLAUDE_CODE_SESSION_ID": "missing"}):
        code, out = run(["summary"], tmp_path, env=env)
        assert code == 0 and out.startswith("Ieakaso usage:")


def test_statusline_reads_stdin(tmp_path):
    s = FakeSession(tmp_path)
    s.start("init", "m1", inp=2000)
    stdin = json.dumps({"transcript_path": str(s.path), "model": {"id": "claude-opus-5-5"}})
    code, out = run(["statusline"], tmp_path, stdin=stdin)
    assert code == 0 and out == "ieakaso ▸ init · opus-5-5 · ctx 1% · run 2k new · session 2k new\n"


def test_statusline_never_crashes(tmp_path):
    for stdin in ("", "not json", "[]", json.dumps({"transcript_path": str(tmp_path / "nope")}), '{"model": 3}'):
        code, _ = run(["statusline"], tmp_path, stdin=stdin)
        assert code == 0


def test_summary_never_fails(tmp_path, monkeypatch):
    s = FakeSession(tmp_path, session_id="abc")
    s.start("init", "m1", inp=1)

    def boom(_):
        raise RuntimeError("bug")

    monkeypatch.setattr("ieakaso.usage.cli.summary", boom)
    code, out = run(["summary"], tmp_path, env={"CLAUDE_CODE_SESSION_ID": "abc"})
    assert code == 0 and out.startswith("Ieakaso usage:")
