---
description: Resume a Claude Code session with Remote Control enabled
argument-hint: <name-or-id> [optional-rc-name]
---

Resume a prior session by its display name (the same name shown by `claude --resume` and by `/list-sessions`) or by UUID prefix. Open it in a new Terminal window with Remote Control enabled.

## Working directory is fixed

Like `/spawn-rc`, this always launches in `~/Projects` to avoid the "trust this folder?" prompt that would hang the session. Even though sessions remember their original project directory, the spawning process starts in `~/Projects` and Claude Code's resume logic handles re-binding the session context.

## Parse $ARGUMENTS

1. **First token** — identifier. Could be a display name (case-insensitive) or a UUID prefix (8+ chars).
2. **Second token** (optional) — `--rc` display name to use for the resumed Remote Control session. Default: the resolved display name itself if it's a valid `--rc` name (alphanumeric + hyphens only); otherwise `resumed-<8-char-uuid>`.

## Resolve the identifier

`claude --resume <name>` accepts the display name directly as a CLI argument. So in most cases we don't need to resolve to a UUID at all — we can just pass the name through. But we should still validate the name exists first, so we can give a useful error if it doesn't.

### Validation strategy

Use the same display-name extraction logic as `/list-sessions` to enumerate available sessions, then:

1. **Exact case-insensitive match on display name** → use that name with `claude --resume <name>`.
2. **UUID prefix match** (input is 8+ hex chars) → resolve to full UUID, use `claude --resume <uuid>`.
3. **Substring match on display name** (only one match) → use that name.
4. **Substring match with multiple matches** → list them with full UUIDs and ask user to disambiguate. Stop.
5. **Zero matches** → reply: `No session matches '<input>'. Use /list-sessions to see what's available.` Stop.

## Spawn

Once the identifier is resolved (whether as a name or a UUID), spawn:

```bash
osascript <<'EOF'
tell application "Terminal"
  do script "cd ~/Projects && env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_OAUTH_TOKEN claude --resume '{IDENTIFIER}' --rc {RC_NAME}"
end tell
EOF
```

Use single quotes around `{IDENTIFIER}` to handle names that might contain spaces or special chars (since display names can be conversation summaries that contain anything). Escape any literal single quotes inside the identifier by replacing `'` with `'\''`.

## Reply

`Resumed '{RC_NAME}' (was: {ORIGINAL_DISPLAY_NAME}) — open the Claude app to take over.`

If the original display name and the rc-name are the same, omit the `(was: ...)` part.

On osascript failure: `Resume failed: <stderr>`
