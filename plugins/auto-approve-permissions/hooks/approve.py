#!/usr/bin/env python3
"""PreToolUse hook: default-allow, defer denies.

Returns permissionDecision="allow" for tool calls that do not match any
permissions.deny rule found in user/project settings. Returns "deny" for
calls that confidently match a deny rule, and "ask" (defer to Claude Code's
own permission engine) when a deny rule's syntax isn't understood by this
matcher.

Settings sources scanned (later entries override on conflict, all merged
for deny rules):
  - ~/.claude/settings.json
  - $CLAUDE_PROJECT_DIR/.claude/settings.json
  - $CLAUDE_PROJECT_DIR/.claude/settings.local.json
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

FILE_PATH_KEYS = ("file_path", "path", "notebook_path")
FILE_TOOLS = {"Read", "Write", "Edit", "Glob", "NotebookEdit", "NotebookRead", "MultiEdit"}


def load_deny_rules() -> list[str]:
    paths: list[Path] = []
    home_settings = Path.home() / ".claude" / "settings.json"
    paths.append(home_settings)

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
                ok = fnmatch.fnmatch(val, rule_arg) or fnmatch.fnmatch(val, "**/" + rule_arg)
                return ("match" if ok else "no_match", f"{key}={val!r} vs glob {rule_arg!r}")
        return "no_match", "no file path in tool_input"

    return "unknown", f"no matcher for tool {tool_name} with arg syntax"


def evaluate(tool_name: str, tool_input: dict[str, Any], deny_rules: list[str]) -> tuple[str, str]:
    ambiguous: list[str] = []
    for rule in deny_rules:
        status, why = match_rule(rule, tool_name, tool_input)
        if status == "match":
            return "deny", f"auto-approve hook: matched deny rule {rule!r} — {why}"
        if status == "unknown":
            ambiguous.append(rule)
    if ambiguous:
        return "ask", (
            "auto-approve hook: deferring to Claude Code's permission engine because "
            f"these deny rules could not be evaluated by the hook: {ambiguous}"
        )
    return "allow", "auto-approve hook: no deny rule matched"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Don't block tool execution on a malformed hook payload — defer.
        json.dump({"hookSpecificOutput": {"permissionDecision": "ask"}}, sys.stdout)
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    deny_rules = load_deny_rules()
    decision, reason = evaluate(tool_name, tool_input, deny_rules)

    out = {
        "hookSpecificOutput": {"permissionDecision": decision},
        "systemMessage": reason,
        "suppressOutput": True,
    }
    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
