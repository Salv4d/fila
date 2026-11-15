---
description: Run the pending scripts in the fila queue, in order. Use when the user asks to run, process or drain the queue.
---

1. Run `fila status` and tell the user what will run.
2. Run `fila run` with the Bash tool. If the scripts look long (renders, transcriptions, builds), run it in the
   background and report when it finishes instead of waiting in the foreground.
3. When it ends:
   - success: say which ids ran and how long each took (`fila status` shows it);
   - failure: the queue stopped at that id and nothing after it ran. Show the end of `fila log <id>`,
     explain the cause, and propose a fix. After fixing, `fila run` again picks up from the failed one.
4. Tasks (`.md`) never run on their own. List them as work left for you or the user, closed with `fila done <id>`.
