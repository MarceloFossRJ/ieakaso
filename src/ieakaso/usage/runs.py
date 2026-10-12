"""Split a transcript into Ieakaso Runs and total their Token usage."""

from dataclasses import dataclass, field

from ieakaso.usage.transcript import AgentRun, Transcript, Usage


@dataclass
class Run:
    mode: str
    usage: Usage = field(default_factory=Usage)  # includes the Agent runs
    models: list[str] = field(default_factory=list)
    agent_runs: list[AgentRun] = field(default_factory=list)


def split_runs(transcript: Transcript) -> list[Run]:
    """A Run lasts from its start marker to the next marker or the end; earlier turns belong to no Run."""
    runs: list[Run] = []
    owner: dict[str, Run] = {}  # Agent tool_use id -> Run in effect there
    for turn in transcript.turns:
        if turn.start_mode:
            runs.append(Run(turn.start_mode))
        if not runs:
            continue
        run = runs[-1]
        if turn.counts:
            run.usage += turn.usage
            if turn.model not in run.models:
                run.models.append(turn.model)
        for tool_id in turn.agent_tool_ids:
            owner[tool_id] = run
    for agent_run in transcript.agent_runs:
        run = owner.get(agent_run.tool_use_id)
        if run:
            run.agent_runs.append(agent_run)
            run.usage += agent_run.usage
    return runs
