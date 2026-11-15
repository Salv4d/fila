---
description: Add pending work to the fila queue as a new migration. Use when the user asks to queue something, leave a job for later, or "put it in the queue".
argument-hint: <what needs to be done>
---

The user wants to queue: $ARGUMENTS

1. Decide the kind:
   - **script** when it can run unattended and deterministically (render, transcribe, build, sync).
     Prefer `.py` when the project may run on Windows; `.sh` needs bash.
   - **task** (`--md`) when it needs judgment, review or a decision.
2. Create it with `fila new "<short name>"` (add `--md` for a task, `--ext py` for Python). It prints the path.
3. Write the file:
   - script: first comment line = one-line description; fail loudly (`set -euo pipefail` in bash); exit 0 only
     when the work is really done. It runs from the project root, with `FILA_ID` and `FILA_ROOT` set.
   - task: a `# Title`, what to do with concrete files and commands, what "done" means, and the line
     `When it is done: fila done <id>`.
4. Show the user the file and `fila status`. Do not run it unless they ask.
