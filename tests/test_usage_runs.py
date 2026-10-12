from usage_fakes import FakeSession

from ieakaso.usage.runs import split_runs
from ieakaso.usage.transcript import load


def runs_of(s):
    return split_runs(load(s.path))


def test_lines_of_one_message_are_counted_once(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1", inp=10, cc=5, cr=100, out=7, lines=3)
    (run,) = runs_of(s)
    assert (run.usage.fresh_input, run.usage.out, run.usage.cache_read) == (15, 7, 100)


def test_marker_starts_a_run_and_follow_ups_belong_to_it(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1", inp=10, out=1)
    s.user("what about the salary?")
    s.assistant("m2", inp=20, out=2)
    s.start("cv-parser", "m3", inp=5, out=1)
    s.assistant("m4", inp=1, out=1)
    first, second = runs_of(s)
    assert (first.mode, first.usage.fresh_input, first.usage.out) == ("job-analyzer", 30, 3)
    assert (second.mode, second.usage.fresh_input, second.usage.out) == ("cv-parser", 6, 2)


def test_activity_before_the_first_marker_is_excluded(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", inp=999, out=999)
    s.noise()
    s.start("init", "m1", inp=1, out=1)
    (run,) = runs_of(s)
    assert (run.usage.fresh_input, run.usage.out) == (1, 1)


def test_no_marker_means_no_run(tmp_path):
    s = FakeSession(tmp_path)
    s.assistant("m0", inp=5)
    s.bash("m1", "ls")
    assert runs_of(s) == []


def test_models_of_a_run_in_order_of_first_use(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1", model="claude-opus-5-5", inp=1)
    s.assistant("m2", model="claude-sonnet-5-5", inp=1)
    s.assistant("m3", model="claude-opus-5-5", inp=1)
    (run,) = runs_of(s)
    assert run.models == ["claude-opus-5-5", "claude-sonnet-5-5"]


def test_agent_runs_are_attributed_by_tool_use_id_and_others_ignored(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1", inp=1)
    s.agent_call("m2", "toolu_A", inp=1)
    s.start("cv-parser", "m3", inp=1)
    s.subagent("a1", "recruiter", "toolu_A", [("s1", "claude-sonnet-5-5", 4, 1, 9, 2), ("s2", "claude-sonnet-5-5", 1, 0, 1, 1)])
    s.subagent("a2", "general-purpose", "toolu_A", [("s3", "claude-sonnet-5-5", 500, 0, 0, 500)])
    first, second = runs_of(s)
    assert second.agent_runs == []
    (ar,) = first.agent_runs
    assert (ar.agent_type, ar.models) == ("recruiter", ["claude-sonnet-5-5"])
    assert (ar.usage.fresh_input, ar.usage.out, ar.usage.cache_read) == (6, 3, 10)
    # Run tokens include its Agent runs
    assert (first.usage.fresh_input, first.usage.out, first.usage.cache_read) == (2 + 6, 3, 10)


def test_candidate_assistant_is_an_agent_run(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1")
    s.agent_call("m2", "toolu_B")
    s.subagent("a1", "candidate-assistant", "toolu_B", [("s1", "claude-sonnet-5-5", 1, 0, 0, 1)])
    (run,) = runs_of(s)
    assert [a.agent_type for a in run.agent_runs] == ["candidate-assistant"]


def test_subagent_before_first_marker_is_excluded(tmp_path):
    s = FakeSession(tmp_path)
    s.agent_call("m0", "toolu_Z")
    s.subagent("a1", "recruiter", "toolu_Z", [("s1", "claude-sonnet-5-5", 100, 0, 0, 100)])
    s.start("init", "m1", inp=1)
    (run,) = runs_of(s)
    assert run.agent_runs == [] and run.usage.fresh_input == 1


def test_missing_file_loads_as_empty(tmp_path):
    assert split_runs(load(tmp_path / "nope.jsonl")) == []


def test_synthetic_and_zero_usage_messages_are_left_out(tmp_path):
    s = FakeSession(tmp_path)
    s.start("init", "m1", inp=10, out=1)
    s.synthetic("m2")
    s.assistant("m3", model="claude-haiku-9", inp=0, out=0)
    (run,) = runs_of(s)
    assert run.models == ["claude-opus-5-5"]
    assert (run.usage.fresh_input, run.usage.out) == (10, 1)


def test_a_command_that_only_mentions_the_marker_does_not_start_a_run(tmp_path):
    s = FakeSession(tmp_path)
    s.bash("m1", "grep -r 'ieakaso.usage start init' docs", inp=1)
    s.bash("m2", "echo uv run python -m ieakaso.usage start init", inp=1)
    assert runs_of(s) == []


def test_marker_accepts_uv_options_and_surrounding_whitespace(tmp_path):
    s = FakeSession(tmp_path)
    s.bash("m1", "  uv run --quiet python -m ieakaso.usage start cv-parser\n", inp=1)
    s.bash("m2", "python -m ieakaso.usage start init", inp=1)
    assert [r.mode for r in runs_of(s)] == ["cv-parser", "init"]
