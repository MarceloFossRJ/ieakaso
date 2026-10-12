import pytest
from usage_fakes import FakeSession

from ieakaso.usage.report import fmt_compact, fmt_tokens, statusline, summary
from ieakaso.usage.transcript import load


@pytest.mark.parametrize(
    "n, text",
    [(0, "0"), (999, "999"), (1000, "1.0k"), (12400, "12.4k"), (99950, "100.0k"), (100000, "100k"), (120000, "120k"),
     (1_500_000, "1.5M")],
)
def test_fmt_tokens(n, text):
    assert fmt_tokens(n) == text


def test_fmt_compact_drops_a_trailing_zero_decimal():
    assert [fmt_compact(n) for n in (15500, 39000, 84000, 200000, 500)] == ["15.5k", "39k", "84k", "200k", "500"]


def session_with_runs(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", inp=777, out=777)  # before any Run: excluded
    s.start("cv-parser", "m1", inp=10000, cc=1000, cr=20000, out=2000)
    s.start("job-analyzer", "m2", inp=2000, cc=400, cr=30000, out=1000)
    s.agent_call("m3", "toolu_A", inp=10000, cc=0, cr=18000, out=100, model="claude-opus-5-5")
    s.assistant("m4", inp=0, cc=0, cr=84000 - 2000, out=0)
    s.subagent("a1", "recruiter", "toolu_A", [("s1", "claude-sonnet-5-5", 3000, 1000, 9000, 800)])
    return s


def test_summary_numbers_are_the_sums_of_the_deduplicated_turns(tmp_path):
    s = session_with_runs(tmp_path)
    lines = summary(load(s.path)).splitlines()
    # run = m2 (2400/1000/30000) + m3 (10000/100/18000) + m4 (0/0/82000) + recruiter (4000/800/9000)
    assert lines[2] == "Tokens    in 16.4k · out 1.9k · cache read 139k"
    # session = run + cv-parser (11000/2000/20000)
    assert lines[5] == "Session   2 Runs · in 27.4k · out 3.9k · cache read 159k"


def test_summary_context_is_the_latest_main_chain_message(tmp_path):
    s = session_with_runs(tmp_path)
    assert summary(load(s.path)).splitlines()[3] == "Context   82k / 200k (41%)"


def test_summary_context_without_a_known_window_has_no_size(tmp_path):
    s = FakeSession(tmp_path)
    s.start("init", "m1", model="mystery-model", inp=84000)
    assert summary(load(s.path)).splitlines()[3] == "Context   84k"


def test_summary_lists_every_model_of_the_run(tmp_path):
    s = FakeSession(tmp_path)
    s.start("init", "m1", model="claude-opus-5-5")
    s.assistant("m2", model="claude-sonnet-5-5")
    assert summary(load(s.path)).splitlines()[1] == "Model     claude-opus-5-5, claude-sonnet-5-5"


def test_summary_singular_run_and_no_agent_lines(tmp_path):
    s = FakeSession(tmp_path)
    s.start("init", "m1", inp=1, out=2)
    out = summary(load(s.path))
    assert "Agent run" not in out
    assert out.splitlines()[-1] == "Session   1 Run · in 1 · out 2 · cache read 0"


def test_summary_without_a_run(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", inp=5)
    assert summary(load(s.path)) == "Ieakaso usage: no Ieakaso Run in this Session yet."


def test_statusline_numbers(tmp_path):
    s = session_with_runs(tmp_path)
    out = statusline(load(s.path), {"model": {"id": "claude-opus-5-5"}, "context_window": {"used_percentage": 42}})
    # run new = 16.4k + 1.9k; session new = run + 13k
    assert out == "ieakaso ▸ job-analyzer · opus-5-5 · ctx 42% · run 18.3k new · session 31.3k new"


def test_statusline_without_runs(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", inp=84000)
    stdin = {"model": {"id": "claude-opus-5-5"}, "context_window": {"used_percentage": 42.4}}
    assert statusline(load(s.path), stdin) == "opus-5-5 · ctx 42%"


def test_statusline_context_falls_back_to_the_transcript(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", model="claude-opus-5-5", inp=84000)
    assert statusline(load(s.path), {"model": {"id": "claude-opus-5-5"}}) == "opus-5-5 · ctx 42%"
    assert statusline(load(s.path), {}) == "opus-5-5 · ctx 42%"


def test_statusline_prefers_the_host_window_size(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", model="mystery", inp=100000)
    stdin = {"model": {"id": "mystery"}, "context_window": {"used_percentage": None, "context_window_size": 1000000}}
    assert statusline(load(s.path), stdin) == "mystery · ctx 10%"


def test_statusline_with_nothing_known_is_minimal(tmp_path):
    assert statusline(load(tmp_path / "nope.jsonl"), {}) == ""


def test_summary_header_matches_the_designed_layout(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1")
    assert summary(load(s.path)).splitlines()[0] == "── Ieakaso · job-analyzer (so far) ───────────────"
