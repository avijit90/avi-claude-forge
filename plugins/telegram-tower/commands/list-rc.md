---
description: List currently-running spawned RC sessions
---

Show currently-running spawned Claude Code sessions. Exclude the dispatcher itself (which runs with `--channels`, not `--rc`).

## Find running spawns

```bash
pgrep -af "claude --rc" | grep -v "channels plugin:telegram"
```

## For each match

Parse the line:
- **PID** — first column
- **rc-name** — the value following `--rc` in the command line. Extract with awk/sed.
- **Working directory** — `lsof -p <pid> 2>/dev/null | awk '$4 == "cwd" { print $9; exit }'`
- **Display name** — find the most recently modified `.jsonl` in the `~/.claude/projects/<encoded-cwd>/` directory matching this working directory, then apply the same display-name priority chain as `/list-sessions`:
  1. Custom session name from `.jsonl` metadata (look for `sessionName`, `name`, or `title` fields in the first ~10 lines)
  2. Summary from `sessions-index.json` if present
  3. First user message, truncated to 60 chars

## Reply

If no spawns running: `No spawned sessions running.`

Otherwise, format as:

```
Running sessions:
1. <rc-name> [→ <display-name>] (pid <pid>, <wd>)
2. ...

Use /kill-rc <rc-name> to stop one.
```

Include the `→ <display-name>` portion only when the display name differs from the rc-name. When they match (which they should, when the user spawned via `/spawn-rc` since that auto-renames to the rc-name), just show the single name.

The "Use /kill-rc" line should mention the **left side** of the arrow specifically — that's what kill-rc matches against.
