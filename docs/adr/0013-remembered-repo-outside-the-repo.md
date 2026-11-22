# The repo is remembered in a file outside the repo

`ieakaso-view` opens the viewer in the terminal it is typed in, from any folder. To find the repo from outside it, it reads `root` from `$XDG_CONFIG_HOME/ieakaso/repo.toml` (`~/.config/ieakaso/repo.toml` when the variable is unset, macOS included). That file is written by code, `uv run python -m ieakaso.repo remember`, which `/ieakaso init` runs on every run. It is the first file Ieakaso writes outside the repo. The lookup order is `--root`, then the current folder and its parents, then `repo.toml`, then an error (exit 2). The viewer never opens on a folder that isn't an Ieakaso repo.

## Considered Options

- **The editable install's own location** (the package's files are the repo's `src/ieakaso/`, so the command finds the repo from where its code lives). Rejected: it works only with `uv tool install --editable`, it silently fails with a plain install, and it ties finding the repo to how it was installed.
- **An `IEAKASO_ROOT` environment variable.** Rejected: the candidate has to set and keep it in their shell profile, by hand, and it goes stale without anyone noticing.
- **Writing it when the command runs from inside a repo.** Rejected: a second clone or a worktree would silently take over.
- **Writing it at install time.** Not possible: `uv tool install` runs no hook.

## Consequences

- `remember` never replaces a remembered repo that still exists unless given `--replace`. Instead it exits 4, and init asks the candidate whether to switch. A remembered path that is gone is overwritten.
- The file is named `repo.toml`, not `config.*`, so it is never confused with `config.yml`, the candidate's data. It holds a path and nothing about the candidate, so the development cleaner leaves it alone. It is not a setup item in `db/system_status.json`: failing to write it is a warning, and `/ieakaso viewer` keeps working through `uv run ieakaso-view`.
- Tests pass the config folder in, and never touch the real `~/.config/ieakaso`.
