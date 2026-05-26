# lgtm

A Claude Code plugin that installs a `PreToolUse` hook to stamp **"Looks Good To Me"** on every tool call — unless that call matches a `permissions.deny` rule in your user or project settings.

It's a safer alternative to `--permission-mode bypassPermissions`. Bypass mode skips *all* permission rules, including denies, so you lose the ability to block destructive actions. lgtm approves anything that isn't denied and lets the normal permission engine handle the deny path.

## How it works

The hook runs on every tool call (`PreToolUse` matcher `"*"`). For each call it:

1. Loads `permissions.deny` from `~/.claude/settings.json`, `$CLAUDE_PROJECT_DIR/.claude/settings.json`, and `$CLAUDE_PROJECT_DIR/.claude/settings.local.json`.
2. Tries to match the tool call against each deny rule.
3. Returns one of:
   - `"deny"` — a deny rule clearly matches,
   - `"ask"` — a deny rule's syntax isn't recognized; defer to Claude Code's own engine,
   - `"allow"` — LGTM.

Result: no prompts for unmatched calls, deny rules still enforced.

## Supported deny rule syntax

| Pattern                          | Behavior                                                                |
| -------------------------------- | ----------------------------------------------------------------------- |
| `Tool`                           | Matches any invocation of that tool                                     |
| `Bash(git push)`                 | Exact-command match                                                     |
| `Bash(git push:*)`               | Command prefix match (`:*` suffix)                                      |
| `WebFetch(domain:example.com)`   | Host equals `example.com` or any subdomain                              |
| `Read(.env)` / `Read(**/.env)`   | Glob on `file_path` / `path` / `notebook_path`. `**/X` matches X at any depth (including root). `X/**` matches anything under X/. Bare basenames match anywhere in the path. |
| `mcp__github`                    | Matches every tool from MCP server `github` (any `mcp__github__*`)      |
| `mcp__github__create_issue`      | Exact MCP tool name                                                     |

Anything the matcher can't confidently evaluate returns `"ask"` so the call falls through to Claude Code's permission engine — i.e. the hook fails safe rather than silently allowing.

## Install

From this marketplace:

```
/plugin marketplace add avijit90/avi-claude-forge
/plugin install lgtm@avi-claude-forge
```

The hook activates on session start. Restart Claude Code after install.

## Verify it works

After install + restart:

```
/test-lgtm
```

Runs the bundled self-test (18 cases covering each deny-rule shape, plus envelope shape validation). All-pass = the hook is correctly approving / denying / deferring. Failures point at the specific matcher path that's broken.

You can also run the test script directly:

```
$(claude --debug 2>&1 | grep -o '/.*lgtm/hooks/approve.py' | head -1 | xargs dirname | xargs dirname)/scripts/run-tests.py
```

## Observability

Every decision is appended as a JSON line to `~/.claude/logs/lgtm.jsonl`:

```json
{"ts":"2026-05-26T15:42:11.234+00:00","tool":"Bash","decision":"allow","reason":"lgtm: no deny rule matched","input":{"command":"ls -la"},"cwd":"/Users/me/proj"}
```

Override path with `LGTM_LOG_FILE=/path/to/log`. Disable with `LGTM_LOG_FILE=""`. Tail it live:

```bash
tail -f ~/.claude/logs/lgtm.jsonl | jq -c '{decision, tool, reason}'
```

## Disable / uninstall

```
/plugin uninstall lgtm@avi-claude-forge
```

## Caveats

- **Most-restrictive wins across plugins.** If another `PreToolUse` hook returns `"deny"`, the call is blocked regardless of lgtm's vote — intentional.
- **`defaultMode: "bypassPermissions"` overrides everything.** If you have bypass mode on, lgtm can't help.
- **Plugin code changes need a Claude Code restart.** Changes to `permissions.deny` in `settings.json` are picked up live (re-read on every hook invocation).
- **Custom rule syntax may need updates.** If your `permissions.deny` uses syntax the matcher doesn't know, lgtm returns `"ask"` — you'll see a prompt where you might have expected silent allow or silent deny. Add the syntax to `match_rule()` if needed.
