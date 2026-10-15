# The Job Application Assistant is the conversation, not a subagent

The Job Application Assistant manages application processes. It starts the Applicant Agent and the Seasoned Recruiter and passes drafts and Reviews between them. It is defined as a role file (`ai/agents/job-application-assistant.md`), and the main conversation takes on that role when a mode loads it. The mode file holds the process's steps, for example `cover-letter`. The Assistant has no `.claude/agents/` or `.opencode/agents/` pointer. We chose this because a subagent cannot start other subagents in Claude Code. An Assistant started as a subagent could not run the Applicant Agent or the Seasoned Recruiter, and they cannot hand work to each other directly.

## Considered Options

- **The Assistant as a subagent that starts the other agents.** Rejected: Claude Code does not allow it.
- **Agents hand over to each other directly (the Applicant calls the Recruiter, which calls the Applicant back).** Rejected for the same reason. A "handover" is the Recruiter's decision, which the Assistant carries out.
- **Process steps written only in each mode file, with no Assistant role.** Rejected: the Assistant will manage more processes later. The shared rules (passing work, keeping the best draft, reporting to the candidate) live in one file so each new mode doesn't repeat them.

## Consequences

- Every Agent run starts fresh, and the Assistant passes it all the context it needs (the Job ad, the Job analysis, the Personal knowledge base, the latest draft and Reviews). Nothing depends on resuming an agent, so the same flow works in OpenCode.
- Adding a pointer that makes the Assistant a subagent would break every process it manages. Don't add one.
