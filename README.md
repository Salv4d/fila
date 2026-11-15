# fila

**Rails-style migrations for your pending work, checked every time Claude Code starts.**

🇧🇷 [Leia em português](README.pt-BR.md)

![fila status and what Claude Code sees at session start](docs/screenshot.png)

You start a long render, a transcription, a batch job. The session ends, the laptop sleeps, you
forget. Next time you open Claude Code, nobody knows what was left half done.

`fila` (Portuguese for *queue*) fixes that with an idea every Rails developer already trusts:
**a migration is something that needs to happen; recording its id is the proof that it happened.**

- Each pending job is a file in `.fila/migrations/`, named `<timestamp>_<name>`.
- `fila run` executes the pending ones **in id order** and appends each id to `.fila/done`, the
  same way Rails writes to `schema_migrations`.
- A failure stops the queue right there. Nothing after it runs, and the failed id is not recorded.
- A **SessionStart hook** tells Claude Code what is still pending as soon as a session opens, so
  the agent picks up where you left off.

One file, Python 3 standard library only, no daemon, no database. The queue is plain text you can
commit, diff and review.

## Two kinds of migration

| Kind | File | What happens |
|---|---|---|
| **script** | `.sh`, `.py`, or any executable | `fila run` executes it from the project root. Exit 0 = done. |
| **task** | `.md` | Instructions for a person or an AI agent (review, decide, write). Closed with `fila done <id>`. |

Tasks are what makes this useful with an agent: work that needs judgment goes in the queue too,
and Claude Code sees it at the start of the next session.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Salv4d/fila/main/fila -o ~/.local/bin/fila
chmod +x ~/.local/bin/fila
```

Or clone the repo and put `fila` anywhere on your `PATH`.

## Quick start

```bash
cd my-project
fila init                                  # creates .fila/
fila install-hook                          # adds the SessionStart hook to .claude/settings.json
fila new "render final cut"                # .fila/migrations/20261114224000_render_final_cut.sh
fila new "review subtitles" --md           # a task for a person or the agent
$EDITOR .fila/migrations/*render_final_cut.sh
fila status
fila run                                   # runs pending scripts in order
fila done 20261114224500                   # closes a task
```

A script migration is a normal script. The first comment line is its description:

```bash
#!/usr/bin/env bash
# Render the final cut with b-roll and music
set -euo pipefail
python3 scripts/render.py raw.mkv --out final.mp4
```

## Commands

| Command | What it does |
|---|---|
| `fila init` | Creates `.fila/` (`migrations/`, `done`, `logs/`) in the current directory. |
| `fila new <name> [--md]` | New migration with a timestamp id. `--md` makes a task. |
| `fila status [--json]` | Pending and done, oldest first. `fila` alone does the same. |
| `fila run [ID ...] [--dry-run]` | Runs pending scripts in order. Stops at the first failure. |
| `fila done ID ...` | Records ids without running them (tasks, or work done by hand). |
| `fila undo ID ...` | Puts migrations back in the queue (like a rollback). |
| `fila log ID` | Output of the last run of a migration (`.fila/logs/<id>.log`). |
| `fila hook` | The SessionStart hook. Silent when nothing is pending. |
| `fila install-hook [--global]` | Adds the hook to `.claude/settings.json`. `--global`: to `~/.claude/settings.json`, and registers this project. |
| `fila projects [--remove PATH]` | Lists (or unregisters) the projects the global hook watches. |

IDs accept a unique prefix or the migration name.

## How the hook works

`fila install-hook` adds this to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "\"/home/you/.local/bin/fila\" hook", "timeout": 10 }] }
    ]
  }
}
```

When something is pending, `fila hook` prints a short note for you (`fila: 3 pending`) and adds the
list to Claude's context, with instructions: run the scripts, do the tasks, close them with
`fila done`. When nothing is pending it prints nothing, so it costs nothing.

The hook only **reads** the queue. It never runs a migration on its own. Running is always an
explicit `fila run`, by you or by the agent.

## One hook, many projects

If you open Claude Code from your home folder (or anywhere outside the project), a project-level
hook never fires. Run this once inside each project:

```bash
fila install-hook --global
```

It puts the hook in `~/.claude/settings.json` and registers the project in
`~/.config/fila/projects`. From then on, every session, wherever it starts, gets the pending work
of all registered projects. `fila projects` shows the list.

## What goes in git

Commit `.fila/migrations/` and `.fila/done`: that is your history of what was done and when.
`fila init` creates a `.fila/.gitignore` that leaves `logs/` and the run lock out.

## Details

- **Order** is the id (timestamp) order, never file modification time.
- **Working directory** of every script is the project root (the folder that holds `.fila/`),
  even if you call `fila` from a subfolder. Scripts get `FILA_ID` and `FILA_ROOT` in the environment.
- **Concurrency**: a lock file stops two `fila run` at once.
- **Format of `.fila/done`**: one line per id, `id<TAB>ran|marked<TAB>iso-date<TAB>duration`.

## Tests

```bash
python3 -m unittest discover -s tests
```

## License

MIT
