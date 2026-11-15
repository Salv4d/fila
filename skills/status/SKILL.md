---
description: Show the fila queue (pending and done migrations) for this project. Use when the user asks what is pending, what is left to do, or about the queue.
---

Run `fila status` with the Bash tool from the project root (if `fila` is not on PATH, use
`bash "${CLAUDE_PLUGIN_ROOT}/bin/fila" status`).

Then summarize for the user, in their language:
- what is pending, oldest first, separating scripts (run with `fila run`) from tasks (`.md`, work for you or them);
- anything that failed (a script whose log in `.fila/logs/<id>.log` ends in an error);
- the next step you suggest.

If there is no `.fila/` folder, say so and offer `fila init`.
