#!/usr/bin/env python3
"""Bundled self-test for the lgtm hook.

Spins up a temporary CLAUDE_PROJECT_DIR with a known set of deny rules,
feeds canned tool-call payloads to approve.py via stdin, and asserts each
decision. Prints a pass/fail table.

Usage:
  ./run-tests.py                 # run all tests
  ./run-tests.py --verbose       # show full hook output per case
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPROVE = HERE.parent / "hooks" / "approve.py"

DENY_RULES = [
    "Bash(curl:*)",
    "Bash(rm -rf /tmp/honeypot)",
    "Read(**/.env)",
    "Write(secrets/**)",
    "WebFetch(domain:evil.example.com)",
    "mcp__github__delete_repo",
    "mcp__notion",
]

CASES = [
    # (label, expected_decision, tool_name, tool_input)
    ("safe Bash ls", "allow", "Bash", {"command": "ls -la"}),
    ("curl is denied (prefix rule)", "deny", "Bash", {"command": "curl https://example.com"}),
    ("wget is not curl (near-miss)", "allow", "Bash", {"command": "wget https://example.com"}),
    ("rm -rf /tmp/honeypot exact deny", "deny", "Bash", {"command": "rm -rf /tmp/honeypot"}),
    ("rm -rf /tmp/other not denied", "allow", "Bash", {"command": "rm -rf /tmp/other"}),
    ("Read .env at root", "deny", "Read", {"file_path": ".env"}),
    ("Read nested .env", "deny", "Read", {"file_path": "config/.env"}),
    ("Read package.json allowed", "allow", "Read", {"file_path": "package.json"}),
    ("Write inside secrets/", "deny", "Write", {"file_path": "secrets/api-key.txt"}),
    ("Write outside secrets/", "allow", "Write", {"file_path": "src/main.py"}),
    ("WebFetch evil.example.com denied", "deny", "WebFetch", {"url": "https://evil.example.com/x"}),
    ("WebFetch subdomain of evil denied", "deny", "WebFetch", {"url": "https://api.evil.example.com/x"}),
    ("WebFetch unrelated domain allowed", "allow", "WebFetch", {"url": "https://good.example.com/x"}),
    ("MCP github delete_repo exact deny", "deny", "mcp__github__delete_repo", {}),
    ("MCP github get_repo allowed", "allow", "mcp__github__get_repo", {}),
    ("MCP notion server-prefix denies all notion tools",
        "deny", "mcp__notion__create_page", {}),
    ("MCP unrelated server allowed", "allow", "mcp__linear__search", {}),
]

UNKNOWN_RULE_DEFER_CASE = (
    "unknown rule syntax → ask",
    "ask",
    "WebFetch",
    {"url": "https://example.com"},
    # Only `domain:...` is recognized for WebFetch; this is genuinely unparseable.
    ["WebFetch(weird-non-domain-syntax)"],
)


def run_approve(payload: dict, project_dir: Path) -> dict:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["LGTM_LOG_FILE"] = ""  # suppress logging during tests
    proc = subprocess.run(
        ["python3", str(APPROVE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"approve.py exited {proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


def write_settings(project_dir: Path, deny_rules: list[str]) -> None:
    settings_dir = project_dir / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "settings.json").write_text(
        json.dumps({"permissions": {"deny": deny_rules}})
    )


def assert_hook_envelope_valid(out: dict, label: str) -> list[str]:
    """Return list of validation problems (empty = OK)."""
    problems = []
    hso = out.get("hookSpecificOutput")
    if not isinstance(hso, dict):
        problems.append("missing hookSpecificOutput")
        return problems
    if hso.get("hookEventName") != "PreToolUse":
        problems.append(f"hookEventName != 'PreToolUse' (got {hso.get('hookEventName')!r})")
    if hso.get("permissionDecision") not in ("allow", "deny", "ask"):
        problems.append(f"bad permissionDecision: {hso.get('permissionDecision')!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not APPROVE.exists():
        print(f"ERROR: cannot find approve.py at {APPROVE}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="lgtm-test-") as tmp:
        project = Path(tmp)
        write_settings(project, DENY_RULES)

        passed = failed = 0
        rows: list[tuple[str, str, str, str]] = []  # status, label, expected, got

        for label, expected, tool_name, tool_input in CASES:
            payload = {"tool_name": tool_name, "tool_input": tool_input}
            try:
                out = run_approve(payload, project)
            except Exception as e:
                rows.append(("ERROR", label, expected, str(e)))
                failed += 1
                continue
            problems = assert_hook_envelope_valid(out, label)
            got = out.get("hookSpecificOutput", {}).get("permissionDecision", "?")
            status = "PASS" if got == expected and not problems else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
                if problems:
                    got = f"{got} [envelope: {'; '.join(problems)}]"
            rows.append((status, label, expected, got))
            if args.verbose:
                print(json.dumps(out, indent=2))

        # Defer-on-unknown test uses its own deny list.
        label, expected, tool_name, tool_input, deny_rules = UNKNOWN_RULE_DEFER_CASE
        write_settings(project, deny_rules)
        try:
            out = run_approve({"tool_name": tool_name, "tool_input": tool_input}, project)
            got = out.get("hookSpecificOutput", {}).get("permissionDecision", "?")
            problems = assert_hook_envelope_valid(out, label)
            status = "PASS" if got == expected and not problems else "FAIL"
        except Exception as e:
            status, got = "ERROR", str(e)
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        rows.append((status, label, expected, got))
        if args.verbose:
            print(json.dumps(out, indent=2))

    # Render table.
    width_label = max(len(r[1]) for r in rows)
    width_exp = max(len(r[2]) for r in rows)
    width_got = max(len(r[3]) for r in rows)
    print()
    print(f"{'STATUS':<6}  {'CASE':<{width_label}}  {'EXPECT':<{width_exp}}  GOT")
    print("-" * (6 + 2 + width_label + 2 + width_exp + 2 + width_got))
    for status, label, expected, got in rows:
        marker = "✓" if status == "PASS" else "✗"
        print(f"{marker} {status:<4}  {label:<{width_label}}  {expected:<{width_exp}}  {got}")
    print()
    print(f"{passed} passed, {failed} failed, {len(rows)} total")
    print(f"Hook script: {APPROVE}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
