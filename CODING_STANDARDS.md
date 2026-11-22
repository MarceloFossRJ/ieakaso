# Coding standards

Judgement calls a reviewer checks a diff against. Rules a test can check live in the tests instead:
`tests/test_cli_docstrings_drift.py` (every CLI's docstring names its exit codes),
`tests/test_doc_commands_drift.py` (every command a doc names exists), and the other `tests/*_drift.py`.

## CLIs

A CLI is a module under `src/ieakaso/` with a top-level `main(argv)`.

### Messages

What a CLI prints, to stdout or stderr, is lowercase: `no Application acme_em: …`, `remembered <root> in <file>`,
`can't write <file>: …`. Names, paths and the product name keep their own casing (`ieakaso-view opens …`,
`<path> is not an Ieakaso repo`).

The rule binds new and changed messages. An existing message is brought in line when its module is next worked on,
unless it is a contract line.

### Contract lines

An output line a mode file reads is a contract: the cv-parser's `New CV file: <path>` and `Captured <id> …`, the
tracker's `created <id>`. It changes only together with the mode file that reads it, in the same commit, and never
for style alone. Before rewording any output line, search `ai/skills/ieakaso/modes/` for it.

### Injection

Everything a CLI takes from outside comes into `main` as a parameter after `argv`: the current folder, `today`,
stdin, stdout and stderr, the environment, the network, the config folder. Its default is `None`, and `main` fills in
the real one (`Path.cwd()`, `sys.stdout`, …) only then, so tests pass fakes and never touch the real machine.

- A relative path from the command line resolves against the injected folder, never the process's own: `cwd / path`,
  not `path.resolve()`.
- Positional and keyword-only parameters are both fine.
- Inject only what the CLI uses: a CLI that prints nothing to stdout takes no `out`.

### Layout

A candidate-facing command lives in `<package>/cli.py`, with a `__main__.py` that runs it, so `python -m
ieakaso.<package>` works and the package's `__init__.py` stays a library other code imports. A development tool in
`src/ieakaso/devtools/` may instead end with an `if __name__ == "__main__"` guard.
