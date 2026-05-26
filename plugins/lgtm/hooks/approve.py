#!/usr/bin/env python3
"""lgtm — PreToolUse hook: stamp "Looks Good To Me" unless denied.

Returns permissionDecision="allow" for tool calls that do not match any
permissions.deny rule found in user/project settings. Returns "deny" for
calls that confidently match a deny rule, and "ask" (defer to Claude Code's
own permission engine) when a deny rule's syntax isn't understood by this
matcher.

Settings sources scanned (all merged for deny rules):
  - ~/.claude/settings.json
  - $CLAUDE_PROJECT_DIR/.claude/settings.json
  - $CLAUDE_PROJECT_DIR/.claude/settings.local.json

Every decision is appended as a JSON line to:
  ${LGTM_LOG_FILE:-~/.claude/logs/lgtm.jsonl}
Set LGTM_LOG_FILE to an empty string to disable logging.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FILE_PATH_KEYS = ("file_path", "path", "notebook_path")
FILE_TOOLS = {"Read", "Write", "Edit", "Glob", "NotebookEdit", "NotebookRead", "MultiEdit"}


def load_deny_rules() -> list[str]:
    paths: list[Path] = []
    paths.append(Path.home() / ".claude" / "settings.json")

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        project_root = Path(project_dir)
        paths.append(project_root / ".claude" / "settings.json")
        paths.append(project_root / ".claude" / "settings.local.json")

    rules: list[str] = []
    for p in paths:
        try:
            data = json.loads(p.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        perms = data.get("permissions") or {}
        deny = perms.get("deny") or data.get("deny") or []
        if isinstance(deny, list):
            rules.extend(r for r in deny if isinstance(r, str))
    return rules


RULE_RE = re.compile(r"^([A-Za-z0-9_]+)(?:\((.*)\))?$")


def parse_rule(rule: str) -> tuple[str, str | None] | None:
    m = RULE_RE.match(rule.strip())
    if not m:
        return None
    return m.group(1), m.group(2)


def tool_name_matches(rule_tool: str, tool_name: str) -> bool:
    if rule_tool == tool_name:
        return True
    # MCP server-prefix rule: "mcp__github" matches "mcp__github__create_issue", etc.
    if rule_tool.startswith("mcp__") and tool_name.startswith(rule_tool + "__"):
        return True
    return False


def path_matches(val: str, pattern: str) -> bool:
    """Match a path against a Claude Code-style permission glob.

    fnmatch alone doesn't honor `**` as recursive (it treats `**` as just `*`),
    so `Read(**/.env)` against bare `.env` would miss. We layer extra rules
    on top: `**/X` means "X at any depth, including root", `X/**` means
    "anything inside X/", and a bare basename matches anywhere in the path.
    """
    if fnmatch.fnmatch(val, pattern):
        return True

    if pattern.startswith("**/"):
        suffix = pattern[3:]
        if fnmatch.fnmatch(val, suffix):
            return True
        # Try every right-anchored subpath, so config/foo/.env still matches.
        parts = val.split("/")
        for i in range(len(parts)):
            if fnmatch.fnmatch("/".join(parts[i:]), suffix):
                return True

    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if val == prefix or val.startswith(prefix + "/"):
            return True

    # Bare basename pattern (no separator) matches if any path component matches.
    if "/" not in pattern and fnmatch.fnmatch(os.path.basename(val), pattern):
        return True

    return False


def match_rule(rule: str, tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
    """Return (status, reason). status ∈ {'match', 'no_match', 'unknown'}."""
    parsed = parse_rule(rule)
    if not parsed:
        return "unknown", f"unparseable rule: {rule!r}"
    rule_tool, rule_arg = parsed

    if not tool_name_matches(rule_tool, tool_name):
        return "no_match", ""

    if rule_arg is None:
        return "match", f"tool {tool_name} matches bare rule {rule!r}"

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if rule_arg.endswith(":*"):
            prefix = rule_arg[:-2]
            return ("match" if cmd.startswith(prefix) else "no_match",
                    f"command prefix {prefix!r} vs {cmd!r}")
        return ("match" if cmd == rule_arg else "no_match",
                f"command exact {rule_arg!r} vs {cmd!r}")

    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        if rule_arg.startswith("domain:"):
            target = rule_arg[len("domain:"):]
            host = urlparse(url).hostname or ""
            ok = host == target or host.endswith("." + target)
            return ("match" if ok else "no_match", f"host {host!r} vs domain {target!r}")
        return "unknown", f"unrecognized WebFetch arg syntax: {rule_arg!r}"

    if tool_name in FILE_TOOLS:
        for key in FILE_PATH_KEYS:
            val = tool_input.get(key)
            if isinstance(val, str):
                ok = path_matches(val, rule_arg)
                return ("match" if ok else "no_match", f"{key}={val!r} vs glob {rule_arg!r}")
        return "no_match", "no file path in tool_input"

    return "unknown", f"no matcher for tool {tool_name} with arg syntax"


def evaluate(tool_name: str, tool_input: dict[str, Any], deny_rules: list[str]) -> tuple[str, str]:
    ambiguous: list[str] = []
    for rule in deny_rules:
        status, why = match_rule(rule, tool_name, tool_input)
        if status == "match":
            return "deny", f"lgtm: matched deny rule {rule!r} — {why}"
        if status == "unknown":
            ambiguous.append(rule)
    if ambiguous:
        return "ask", (
            "lgtm: deferring to Claude Code's permission engine because "
            f"these deny rules could not be evaluated by the hook: {ambiguous}"
        )
    return "allow", "lgtm: no deny rule matched"


def resolve_log_path() -> Path | None:
    override = os.environ.get("LGTM_LOG_FILE")
    if override is not None:
        if override == "":
            return None
        return Path(override).expanduser()
    return Path.home() / ".claude" / "logs" / "lgtm.jsonl"


def _excerpt_input(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Trim tool_input for logging so secrets/blobs don't bloat the log."""
    out = {}
    for k, v in tool_input.items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + f"... ({len(v)} chars)"
        else:
            out[k] = v
    return out


def log_decision(tool_name: str, tool_input: dict[str, Any], decision: str, reason: str) -> None:
    log_path = resolve_log_path()
    if log_path is None:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "decision": decision,
            "reason": reason,
            "input": _excerpt_input(tool_input),
            "cwd": os.environ.get("CLAUDE_PROJECT_DIR", ""),
        }
        with log_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        # Logging must never break tool execution.
        pass


def emit(decision: str, reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
        "suppressOutput": True,
    }
    json.dump(out, sys.stdout)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        emit("ask", "lgtm: malformed payload, deferring")
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    deny_rules = load_deny_rules()
    decision, reason = evaluate(tool_name, tool_input, deny_rules)
    log_decision(tool_name, tool_input, decision, reason)
    emit(decision, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
