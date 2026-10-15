# Viewer

`/ieakaso viewer`: opens the applications viewer, a terminal app where the candidate sees every Application in a table and edits its status, interview stages, contacts, Salary expectation and notes (terms in `CONTEXT.md`, the data in `docs/database.md`).

The viewer needs a real terminal of its own, so you cannot run it inside this conversation: it would wait for keys that never come. You open a terminal window for it, or, if that fails, give the candidate the command. You never edit `db/ieakaso_db.json` yourself; the viewer and the tracker are its only writers.

---

## STEPS

### Step 1: Open a terminal window

Run the command from the repository root, in a new terminal window. Use the repository root's absolute path (`pwd` from the root) in place of `<repo-root>`.

- **macOS:** run

  ```
  osascript -e 'tell application "Terminal" to activate' -e 'tell application "Terminal" to do script "cd \"<repo-root>\" && uv run ieakaso-viewer"'
  ```

  with `<repo-root>` replaced by the path. If the path holds a quote or a backslash, skip to Step 2.
- **Linux:** try `x-terminal-emulator -e sh -c "cd '<repo-root>' && uv run ieakaso-viewer"`, then `gnome-terminal -- sh -c "cd '<repo-root>' && uv run ieakaso-viewer"`. Use the first one that exists. If none does, or the path holds a single quote, go to Step 2.
- **Any other system:** go to Step 2.

The window opens and keeps running after this command ends, so a success exit only means the window was asked for. Do not wait for the viewer or read its output.

### Step 2: If no window opened

If the command failed, or the system is not covered above, say so in one line, then give the candidate the command to run in a terminal of their own, from the repository root:

```
uv run ieakaso-viewer
```

### Step 3: Tell the candidate

In chat, in a few lines:
- that the viewer is open in a new terminal window (or the command to run, from Step 2)
- the keys: Enter opens an Application, `h` hides or shows Desisted and Not selected, `a`, `j` and `c` open the Job ad, the Job analysis and the Cover letter, `q` quits
- that edits are saved at once, and that the viewer only edits: new Applications come from `/ieakaso job-analyzer`

If `db/ieakaso_db.json` does not exist, add that the table is empty until a Job analysis has been run.

The mode ends there.

---

## RULES

1. **Never run the viewer in this conversation**, and never pipe keys into it.
2. **Never edit `db/ieakaso_db.json`.** Not even to fix an invalid file: tell the candidate what the viewer reports.
3. **Draft only.** The viewer never submits an application or contacts anyone.
