# auto-approve-permissions

A Claude Code plugin that installs a `PreToolUse` hook to **auto-approve permission prompts** while **still honoring `permissions.deny` rules** from your user and project settings.

This is meant as a safer alternative to `--permission-mode bypassPermissions`. Bypass mode skips *all* permission rules, including denies — so you lose the ability to block destructive actions. This hook approves anything that isn't on a deny list, and lets the normal permission engine handle the deny case.

## How it works

The hook runs on every tool call (`PreToolUse` matcher `"*"`). For each call it:

1. Loads `permissions.deny` from `~/.claude/settings.json`, `$CLAUDE_PROJECT_DIR/.claude/settings.json`, and `$CLAUDE_PROJECT_DIR/.claude/settings.local.json`.
2. Tries to match the tool call against each deny rule.
3. Returns:
   - `"deny"` if a deny rule clearly matches,
   - `"ask"` if a deny rule's syntax isn't recognized by the hook (defers to Claude Code's own engine),
   - `"allow"` otherwise.

Result: no prompts for unmatched calls, deny rules still enforced.

## Supported deny rule syntax

| Pattern                       | Behavior                                                                |
| ----------------------------- | ----------------------------------------------------------------------- |
| `Tool`                        | Matches any invocation of that tool                                     |
| `Bash(git push)`              | Exact-command match                                                     |
| `Bash(git push:*)`            | Command prefix match (`:*` suffix)                                      |
| `WebFetch(domain:example.com)`| Host equals `example.com` or any subdomain                              |
| `Read(./.env)` / `Write(src/**)` | `fnmatch` glob on `file_path` / `path` / `notebook_path`              |
| `mcp__github`                 | Matches every tool from MCP server `github` (any `mcp__github__*`)      |
| `mcp__github__create_issue`   | Exact MCP tool name                                                     |

Anything else returns `"ask"` so the call falls through to Claude Code's prompt — i.e. the hook fails safe.

## Install

From this marketplace:

```
/plugin marketplace add avijit90/avi-claude-forge
/plugin install auto-approve-permissions@avi-claude-forge
```

The hook activates on session start. Restart Claude Code if you edit it.

## Disable / uninstall

```
/plugin uninstall auto-approve-permissions@avi-claude-forge
```

Or disable temporarily by removing the plugin from your enabled list and restarting.

## Caveats

- **Hook decisions don't survive across plugins automatically.** If another plugin's PreToolUse hook returns `"deny"`, the most restrictive decision wins — which is the intended behavior here.
- **`defaultMode: "bypassPermissions"` overrides everything.** If you have bypass mode on, this hook can't help.
- **Read once at session start.** If you edit your `permissions.deny` list, the hook will pick it up on the next tool call (it re-reads settings each invocation), but plugin code changes still require a Claude Code restart.
