from usage_fakes import FakeSession

from ieakaso.devtools.estimate_backtest import backtest, main
from ieakaso.usage.transcript import load


def session_with_ratios(tmp_path, ratios, name="sess-1"):
    """Final messages of 1000 visible tokens each, whose true output is ratio * 1000."""
    s = FakeSession(tmp_path, session_id=name, slug=f"-{name}")
    for i, ratio in enumerate(ratios):
        s.assistant(f"m{i}", inp=1, out=round(1000 * ratio), blocks=s.text(4000))
    return s


def test_uniform_ratios_are_estimated_exactly(tmp_path):
    result = backtest([load(session_with_ratios(tmp_path, [2.0] * 11).path)])
    assert (result.samples, result.covered, result.median_abs_error, result.median_bias) == (11, 11, 0.0, 0.0)


def test_each_message_is_estimated_from_the_others_only(tmp_path):
    # Left out, the 4.0 message is estimated from ten 2.0 messages: 2000 for 4000, outside the range [2000, 2000].
    result = backtest([load(session_with_ratios(tmp_path, [2.0] * 10 + [4.0]).path)])
    assert (result.samples, result.covered, result.median_abs_error) == (11, 10, 0.0)
    assert result.worst == [(4000, 2000, 2000, 2000)]


def test_too_few_other_messages_use_the_default_ratio(tmp_path):
    result = backtest([load(session_with_ratios(tmp_path, [1.8] * 5).path)])
    assert (result.samples, result.default_used, result.covered, result.median_abs_error) == (5, 5, 5, 0.0)


def test_sessions_are_calibrated_separately_and_pooled(tmp_path):
    a = load(session_with_ratios(tmp_path, [2.0] * 11, "a").path)
    b = load(session_with_ratios(tmp_path, [3.0] * 11, "b").path)
    result = backtest([a, b])
    assert (result.samples, result.covered, result.median_abs_error) == (22, 22, 0.0)


def test_short_and_non_final_messages_are_not_samples(tmp_path):
    s = session_with_ratios(tmp_path, [2.0] * 11)
    s.assistant("short", inp=1, out=50, blocks=s.text(100))
    s.assistant("open", inp=1, out=8, blocks=s.text(4000), final=False)
    assert backtest([load(s.path)]).samples == 11


def test_cli_reports_a_transcript_given_by_path(tmp_path, capsys):
    s = session_with_ratios(tmp_path, [2.0] * 10 + [4.0])
    assert main([str(s.path)]) == 0
    out = capsys.readouterr().out
    assert "Samples          11 final messages in 1 Session" in out
    assert "In range         10 of 11 (91%)" in out


def test_cli_with_nothing_to_test_says_so(tmp_path, capsys):
    s = FakeSession(tmp_path)
    assert main([str(s.path)]) == 0
    assert "no final messages" in capsys.readouterr().out


def test_cli_all_reads_every_session_of_the_project(tmp_path, capsys):
    a = session_with_ratios(tmp_path, [2.0] * 11, "a")
    session_with_ratios(tmp_path, [2.0] * 11, "b")  # another project folder: not read
    second = a.project / "c.jsonl"
    second.write_text(a.path.read_text())
    assert main(["--all", "--project-dir", str(a.project)]) == 0
    assert "22 final messages in 2 Sessions" in capsys.readouterr().out
