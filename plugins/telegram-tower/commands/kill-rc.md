---
description: Kill a named spawned RC session
argument-hint: <rc-name>
---

Kill a running spawned session by its rc-name (the value passed to `--rc` when it was spawned).

## Parse $ARGUMENTS

The first token is the rc-name. Validate:

- Allow only `[A-Za-z0-9-]`. Reject otherwise: `Invalid name '<input>'.`
- **Reserved names** — refuse if name matches (case-insensitive) `dispatcher`, `channels`, `telegram`, or `tower`. Reply: `Refusing to kill — '<name>' is reserved.`

## Find matches

```bash
pgrep -af "claude --rc {NAME}\b"
```

The `\b` word boundary matters: without it, `eqtp` would match `eqtp-hotfix` and `eqtp-prod` too.

### Outcomes

**Zero matches:**
`No session running with rc-name '{NAME}'. Use /list-rc to see what's running.`

**Exactly one match — kill it:**

```bash
pkill -f "claude --rc {NAME}\b"
sleep 1
pgrep -f "claude --rc {NAME}\b"
```

- If the second pgrep returns nothing: `Killed '{NAME}'.`
- If it still returns a PID, escalate:

  ```bash
  pkill -9 -f "claude --rc {NAME}\b"
  sleep 1
  pgrep -f "claude --rc {NAME}\b"
  ```

  - Gone: `Force-killed '{NAME}'.`
  - Still alive: `Could not kill '{NAME}' (pid <pid> still alive). Investigate manually.`

**Multiple matches:**
List PIDs and full command lines. Reply: `Multiple sessions match '{NAME}'. Specify by PID:` followed by the list. Do not kill any.
