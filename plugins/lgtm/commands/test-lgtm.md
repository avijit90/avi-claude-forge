---
description: Run the bundled self-test for lgtm to verify the hook is approving/denying correctly.
---

Run the bundled test suite for the lgtm plugin. The test runner spins up a temporary project with known deny rules, feeds canned tool-call payloads through the hook script, and asserts each decision (allow / deny / ask) along with the JSON envelope shape (`hookEventName`, `permissionDecision`).

Execute:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-tests.py"
```

If `${CLAUDE_PLUGIN_ROOT}` is not set in your shell (it's only injected into hooks, not slash-command bash), fall back to the absolute path printed by `/hooks`, or pass the path explicitly.

Report the full output verbatim. Pass = `0 failed`. If anything fails, surface the row(s) and the likely cause:

- **`hookEventName` envelope failure** → older Claude Code spec; check `approve.py` is emitting `hookSpecificOutput.hookEventName: "PreToolUse"`.
- **`allow` instead of `deny`** → matcher missed the rule shape; check whether the rule uses a syntax the matcher supports (see README).
- **`deny` instead of `allow`** → matcher is too broad; likely the glob fallback (`**/<pattern>`) over-matched.
- **`ask` for everything** → settings.json couldn't be parsed, or all rules are in the "unknown syntax" bucket.

Also show the path to the decision log so the user can grep it for their own troubleshooting:

```bash
echo "Log: ${LGTM_LOG_FILE:-$HOME/.claude/logs/lgtm.jsonl}"
tail -n 20 "${LGTM_LOG_FILE:-$HOME/.claude/logs/lgtm.jsonl}" 2>/dev/null || echo "(no log entries yet — hook hasn't fired)"
```
