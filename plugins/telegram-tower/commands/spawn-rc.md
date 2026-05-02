---
description: Spawn a new Claude Code session with Remote Control enabled
argument-hint: <session-name> [initial-prompt]
---

Spawn a new, independent Claude Code session in a new Terminal window with Remote Control enabled. The user is driving this from Telegram and cannot see your reasoning — keep replies short and informative.

## Working directory is fixed

All sessions launch in `~/Projects`. This avoids the "trust this folder?" prompt that would otherwise hang the session waiting for a response that can never arrive (the user is on their phone, not at the Mac). Do NOT accept a working directory argument — even if the user includes a path, ignore it for the `cd`.

## Parse $ARGUMENTS

1. **First word** — session name (required). Allow only `[A-Za-z0-9-]`. If invalid, reply: `Invalid name '<input>'. Use only letters, digits, and hyphens.` and stop.
2. **Remainder** (optional) — initial prompt for the new session. If present, escape any single quotes for AppleScript by replacing `'` with `'\''`.

## Initial prompt construction

Always prepend `/rename {NAME}` to whatever initial prompt the user provided (or to an empty prompt if none was given). This makes the chosen name show up correctly in the resume picker and in `/list-sessions` later, instead of an auto-generated summary.

Combine into a single string passed to `claude` as a positional argument:

```
/rename {NAME}

{USER_PROMPT_OR_EMPTY}
```

When the user prompt is empty, just send `/rename {NAME}` alone.

## Spawn

Run via Bash:

```bash
osascript <<'EOF'
tell application "Terminal"
  do script "cd ~/Projects && env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_OAUTH_TOKEN claude --rc {NAME} '{COMBINED_PROMPT}'"
end tell
EOF
```

The `env -u` flags are critical. Without them the child process refuses to start with a "nested session" error.

## Reply

On success: `Spawned '{NAME}' in ~/Projects — open the Claude app to take over.`

On osascript failure: capture stderr, reply: `Spawn failed: <stderr>`

Do not show the bash command, the AppleScript, or any intermediate output to the user. They want the confirmation, not the implementation.
