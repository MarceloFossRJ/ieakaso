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


def test_applicant_is_an_agent_run(tmp_path):
    s = FakeSession(tmp_path)
    s.start("job-analyzer", "m1")
    s.agent_call("m2", "toolu_B")
    s.subagent("a1", "applicant", "toolu_B", [("s1", "claude-sonnet-5-5", 1, 0, 0, 1)])
    (run,) = runs_of(s)
    assert [a.agent_type for a in run.agent_runs] == ["applicant"]


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


def test_a_marker_chained_with_other_commands_starts_a_run(tmp_path):
    s = FakeSession(tmp_path)
    s.bash("m1", "cd /repo; uv run python -m ieakaso.usage start cover-letter; cat SKILL.md", inp=1)
    s.bash("m2", "cd /repo && uv run python -m ieakaso.usage start init && cat db/system_status.json", inp=1)
    s.bash("m3", "true || python -m ieakaso.usage start cv-parser\nls", inp=1)
    assert [r.mode for r in runs_of(s)] == ["cover-letter", "init", "cv-parser"]


def test_a_quoted_marker_inside_a_chain_does_not_start_a_run(tmp_path):
    s = FakeSession(tmp_path)
    s.bash("m1", "echo 'x; uv run python -m ieakaso.usage start init'; ls", inp=1)
    s.bash("m2", 'git commit -m "fix; uv run python -m ieakaso.usage start init"', inp=1)
    s.bash("m3", "gh issue create --body \"$(cat <<'EOF'\ncd x; uv run python -m ieakaso.usage start m; cat y\nEOF\n)\"", inp=1)
    s.bash("m4", "echo 'unbalanced; uv run python -m ieakaso.usage start init", inp=1)
    assert runs_of(s) == []


def test_a_message_counts_the_usage_of_its_last_line(tmp_path):
    # Claude Code writes a streamed message as several lines; the output count grows and only the last is final.
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=10, out=1)
    s.assistant("m2", inp=5, outs=[8, 8, 7641])
    (run,) = runs_of(s)
    assert run.usage.out == 1 + 7641


def test_an_agent_run_counts_the_usage_of_each_message_last_line(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=1)
    s.agent_call("m2", "toolu_A", inp=1)
    s.subagent("a1", "recruiter", "toolu_A", [])
    log = s.project / s.session_id / "subagents" / "agent-a1.jsonl"
    s.assistant("s1", inp=3, outs=[16, 16, 451], path=log)
    (run,) = runs_of(s)
    assert run.agent_runs[0].usage.out == 451


def test_marker_accepts_uv_options_and_surrounding_whitespace(tmp_path):
    s = FakeSession(tmp_path)
    s.bash("m1", "  uv run --quiet python -m ieakaso.usage start cv-parser\n", inp=1)
    s.bash("m2", "python -m ieakaso.usage start init", inp=1)
    assert [r.mode for r in runs_of(s)] == ["cv-parser", "init"]


# Output estimates: a background Agent run's transcript often has no final line for a message, so its
# output_tokens is a mid-stream snapshot. The output is estimated from its visible characters, calibrated on
# the messages of the same Session that do have a final line.


def test_without_enough_final_messages_the_default_ratio_is_used(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=1, out=0)
    s.assistant("m2", inp=1, out=8, blocks=s.text(4000), final=False)  # 4000 chars = 1000 visible tokens
    (run,) = runs_of(s)
    u = run.usage
    assert (u.out, u.out - u.out_low_gap, u.out + u.out_high_gap, u.estimated) == (1800, 1400, 3300, True)


def test_the_ratio_is_calibrated_on_final_messages(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m0", inp=1, out=0)
    for i, ratio in enumerate([1.5] + [2.0] * 7 + [3.0] * 2):  # ten final messages of 1000 visible tokens each
        s.assistant(f"f{i}", inp=1, out=int(1000 * ratio), blocks=s.text(4000))
    s.assistant("m2", inp=1, out=8, blocks=s.text(8000), final=False)
    (run,) = runs_of(s)
    estimated = run.usage.out - 21500  # the final messages: 1500 + 7 * 2000 + 2 * 3000
    assert estimated == 4000  # 2000 visible tokens * the median 2.0
    assert (run.usage.out_low_gap, run.usage.out_high_gap) == (4000 - 3000, 6000 - 4000)  # p10 1.5, p90 3.0


def test_an_estimate_is_never_below_the_recorded_count(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=1, out=0)
    s.assistant("m2", inp=1, out=5000, blocks=s.text(400), final=False)
    (run,) = runs_of(s)
    assert (run.usage.out, run.usage.out_low_gap, run.usage.out_high_gap) == (5000, 0, 0)


def test_final_messages_are_exact(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=1, out=7)
    s.assistant("m2", inp=1, out=900, blocks=s.text(4000))
    (run,) = runs_of(s)
    assert (run.usage.out, run.usage.estimated) == (907, False)


def test_agent_run_messages_are_estimated_too(tmp_path):
    s = FakeSession(tmp_path)
    s.start("cover-letter", "m1", inp=1)
    s.agent_call("m2", "toolu_A", inp=1)
    s.subagent("a1", "applicant", "toolu_A", [])
    log = s.project / s.session_id / "subagents" / "agent-a1.jsonl"
    s.assistant("s1", inp=3, out=26, blocks=[s.tool_use("t1", "SubagentHandback", report="x" * 4000)], final=False, path=log)
    (run,) = runs_of(s)
    assert run.agent_runs[0].usage.estimated and run.agent_runs[0].usage.out >= 1400
