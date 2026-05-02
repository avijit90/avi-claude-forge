# telegram-tower

A Claude Code plugin that lets a long-running "dispatcher" session spawn, list, resume, and kill other Claude Code sessions on the same machine. Designed to be driven from a Telegram channel so you can launch sessions on your Mac from your phone, then take them over via Remote Control in the Claude app.

## What it adds

Five slash commands:

| Command | Purpose | Args |
|---|---|---|
| `/spawn-rc` | New session in a Terminal window, RC on, auto-renamed | `<name> [prompt]` |
| `/list-sessions` | Show resumable sessions on disk (uses --resume picker names) | `[search-term]` |
| `/resume-rc` | Resume by display name or UUID, RC on | `<name-or-id> [rc-name]` |
| `/list-rc` | Show currently-running spawned sessions | none |
| `/kill-rc` | Stop a named running spawn | `<rc-name>` |

## Architecture

```
Phone (Telegram) → Dispatcher session → osascript → New Terminal window → claude --rc
                                                                              ↓
                                                                    Claude app (Remote Control)
```

The dispatcher is a Claude Code session running with `--channels plugin:telegram@claude-plugins-official`. Slash commands run inside the dispatcher; their bash steps shell out to AppleScript to open new Terminal windows.

Spawned sessions are **interactive** (not headless). They appear in the Claude app's Remote Control list and can also be picked up locally at the Mac.

## Working directory: ~/Projects

All sessions launch in `~/Projects` regardless of context. Reason: when Claude Code starts in an untrusted directory, it asks "do you trust this folder?" and waits for a response. The user is on Telegram, can't answer, and the session hangs forever. By always launching in a pre-trusted `~/Projects`, this never happens.

If a session needs to operate on a subdirectory, just `cd` from inside the session — that doesn't trigger the trust prompt.

## Display names match `claude --resume`

`/list-sessions` and `/resume-rc` use the same display-name priority as the official `claude --resume` picker:

1. **Custom session name** (set via `/rename` inside the session)
2. **Auto-generated summary** (from `sessions-index.json`)
3. **First user prompt** (truncated to 60 chars, fallback when neither above is available)

Search matches against this same display name. So if you do `/spawn-rc eqtp-hotfix` on Monday, then `/list-sessions eqtp` on Friday will find it — because the session was auto-renamed at spawn time and the display name is `eqtp-hotfix`.

`/resume-rc <name>` passes the name directly to `claude --resume <name>`, which Claude Code natively supports (no UUID lookup needed in the common case).

## Auto-rename on spawn

`/spawn-rc <name> [prompt]` injects `/rename <name>` as the very first message of the new session. This means:

- The display name in `/list-sessions` is your chosen name, not an auto-summary.
- The rc-name (used by `/kill-rc`) and the display name (used by `/resume-rc`) match by default.
- `/resume-rc` works with the same name you used to spawn, even days later.

## Names: rc-name vs display name

Two distinct identifiers:

- **rc-name** — the `--rc <name>` argument on the running process. Used by `/list-rc` and `/kill-rc`. Matched via `pgrep`.
- **display name** — set inside the session via `/rename`. Stored in the `.jsonl` transcript metadata. Used by `/list-sessions` and `/resume-rc`. Matched via filesystem scan.

When you spawn via `/spawn-rc`, both are set to the same value automatically. They only diverge if you manually `/rename` to something different inside the running session.

When they differ, `/list-rc` shows them as `rc-name → display-name`.

## Requirements

- Claude Code ≥ v2.1.80 with channels support
- macOS (uses AppleScript and `osascript`)
- Terminal.app automation permission (granted on first use)
- "Enable Remote Control for all sessions" turned on in `/config`
- `~/Projects` directory exists and is pre-trusted by Claude Code (open it once interactively if you haven't)
- Telegram channel plugin installed and configured (separate from this plugin)

## Critical: the CLAUDECODE env trap

Every spawn unsets `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, and `CLAUDE_CODE_OAUTH_TOKEN` before launching the child:

```bash
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_OAUTH_TOKEN claude --rc ...
```

Without this, the child refuses to start because the dispatcher's environment leaks through. Don't remove these from the command bodies.

## Install

```
/plugin marketplace add avijit90/avi-claude-forge
/plugin install telegram-tower@avi-claude-forge
```

Then in any Claude Code session: `/reload-plugins` and the commands become available.

## Daily flow

```
You (Telegram):  /spawn-rc eqtp-hotfix investigate failing test
Dispatcher:      Spawned 'eqtp-hotfix' in ~/Projects — open the Claude app to take over.

[hours later — close the Mac, open the Claude app on phone, work, close it]

You:             /list-rc
Dispatcher:      Running sessions:
                 1. eqtp-hotfix (pid 12345, ~/Projects)

                 Use /kill-rc <rc-name> to stop one.

You:             /list-sessions eqtp
Dispatcher:      Recent sessions:
                 1. eqtp-hotfix · ~/Projects · 2h ago · 47 turns · id: a3f7c2d1

                 Use /resume-rc <name-or-id> to resume.

You:             /resume-rc eqtp-hotfix
Dispatcher:      Resumed 'eqtp-hotfix' — open the Claude app to take over.
```

## Safety

`/kill-rc` refuses to act on names containing `dispatcher`, `channels`, `telegram`, or `tower` — guards against accidentally killing the dispatcher itself.

## Changelog

### 0.2.0
- Sessions now launch in a fixed `~/Projects` directory to avoid the trust-folder hang
- `/spawn-rc` auto-renames the new session to match the rc-name (via injected `/rename` initial prompt)
- `/list-sessions` and `/resume-rc` now use the same display name priority as `claude --resume`: custom name → summary → first user prompt
- `/resume-rc` passes the display name directly to `claude --resume <name>`, leveraging native name resolution
- `/list-rc` shows display names alongside rc-names

### 0.1.0
- Initial release: spawn-rc, list-sessions, resume-rc, list-rc, kill-rc
