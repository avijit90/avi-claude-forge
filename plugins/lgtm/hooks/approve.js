#!/usr/bin/env node
/**
 * lgtm — PreToolUse hook: stamp "Looks Good To Me" unless denied.
 *
 * Emits permissionDecision="allow" for tool calls that don't match any
 * permissions.deny rule from user/project settings. Emits "deny" when a
 * deny rule clearly matches, and "ask" (defer to Claude Code's own
 * permission engine) when a deny rule's syntax isn't understood here.
 *
 * Settings sources scanned (all merged):
 *   - ~/.claude/settings.json
 *   - $CLAUDE_PROJECT_DIR/.claude/settings.json
 *   - $CLAUDE_PROJECT_DIR/.claude/settings.local.json
 *
 * Decisions are appended as JSON lines to:
 *   ${LGTM_LOG_FILE:-~/.claude/logs/lgtm.jsonl}
 * Set LGTM_LOG_FILE="" to disable logging.
 *
 * Zero external dependencies — runs on whatever node ships with Claude Code.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const FILE_TOOLS = new Set([
  'Read', 'Write', 'Edit', 'Glob', 'NotebookEdit', 'NotebookRead', 'MultiEdit',
]);
const FILE_PATH_KEYS = ['file_path', 'path', 'notebook_path'];
const RULE_RE = /^([A-Za-z0-9_]+)(?:\((.*)\))?$/;

function loadDenyRules() {
  const paths = [path.join(os.homedir(), '.claude', 'settings.json')];
  if (process.env.CLAUDE_PROJECT_DIR) {
    const root = process.env.CLAUDE_PROJECT_DIR;
    paths.push(path.join(root, '.claude', 'settings.json'));
    paths.push(path.join(root, '.claude', 'settings.local.json'));
  }

  const rules = [];
  for (const p of paths) {
    let data;
    try {
      data = JSON.parse(fs.readFileSync(p, 'utf-8'));
    } catch {
      continue;
    }
    const perms = data.permissions || {};
    const deny = perms.deny || data.deny || [];
    if (Array.isArray(deny)) {
      for (const r of deny) if (typeof r === 'string') rules.push(r);
    }
  }
  return rules;
}

/**
 * Translate an fnmatch-style glob to a regex and test it. Supports `*`, `?`,
 * `[abc]` character classes; escapes other regex metacharacters.
 */
function fnmatch(name, pattern) {
  let regex = '^';
  let i = 0;
  while (i < pattern.length) {
    const c = pattern[i];
    if (c === '*') {
      regex += '.*';
      i++;
    } else if (c === '?') {
      regex += '.';
      i++;
    } else if (c === '[') {
      const close = pattern.indexOf(']', i + 1);
      if (close === -1) {
        regex += '\\[';
        i++;
      } else {
        regex += pattern.slice(i, close + 1);
        i = close + 1;
      }
    } else if ('.+^${}()|\\'.indexOf(c) !== -1) {
      regex += '\\' + c;
      i++;
    } else {
      regex += c;
      i++;
    }
  }
  regex += '$';
  return new RegExp(regex).test(name);
}

/**
 * Path-glob match honoring `**` semantics that fnmatch alone doesn't give us:
 *   - `**\/X` matches X at any depth, including root.
 *   - `X/**` matches anything under X/.
 *   - bare basename patterns match any path component.
 */
function pathMatches(val, pattern) {
  if (fnmatch(val, pattern)) return true;

  if (pattern.startsWith('**/')) {
    const suffix = pattern.slice(3);
    if (fnmatch(val, suffix)) return true;
    const parts = val.split('/');
    for (let i = 0; i < parts.length; i++) {
      if (fnmatch(parts.slice(i).join('/'), suffix)) return true;
    }
  }

  if (pattern.endsWith('/**')) {
    const prefix = pattern.slice(0, -3);
    if (val === prefix || val.startsWith(prefix + '/')) return true;
  }

  if (!pattern.includes('/') && fnmatch(path.basename(val), pattern)) return true;

  return false;
}

function parseRule(rule) {
  const m = rule.trim().match(RULE_RE);
  if (!m) return null;
  return { tool: m[1], arg: m[2] !== undefined ? m[2] : null };
}

function toolNameMatches(ruleTool, toolName) {
  if (ruleTool === toolName) return true;
  // MCP server-prefix: "mcp__github" matches "mcp__github__create_issue", etc.
  if (ruleTool.startsWith('mcp__') && toolName.startsWith(ruleTool + '__')) return true;
  return false;
}

function matchRule(rule, toolName, toolInput) {
  const parsed = parseRule(rule);
  if (!parsed) return { status: 'unknown', why: `unparseable rule: ${JSON.stringify(rule)}` };
  const { tool: ruleTool, arg: ruleArg } = parsed;

  if (!toolNameMatches(ruleTool, toolName)) return { status: 'no_match', why: '' };

  if (ruleArg === null) {
    return { status: 'match', why: `tool ${toolName} matches bare rule ${JSON.stringify(rule)}` };
  }

  if (toolName === 'Bash') {
    const cmd = toolInput.command || '';
    if (ruleArg.endsWith(':*')) {
      const prefix = ruleArg.slice(0, -2);
      return {
        status: cmd.startsWith(prefix) ? 'match' : 'no_match',
        why: `command prefix ${JSON.stringify(prefix)} vs ${JSON.stringify(cmd)}`,
      };
    }
    return {
      status: cmd === ruleArg ? 'match' : 'no_match',
      why: `command exact ${JSON.stringify(ruleArg)} vs ${JSON.stringify(cmd)}`,
    };
  }

  if (toolName === 'WebFetch') {
    const url = toolInput.url || '';
    if (ruleArg.startsWith('domain:')) {
      const target = ruleArg.slice('domain:'.length);
      let host = '';
      try { host = new URL(url).hostname || ''; } catch { /* invalid URL */ }
      const ok = host === target || host.endsWith('.' + target);
      return {
        status: ok ? 'match' : 'no_match',
        why: `host ${JSON.stringify(host)} vs domain ${JSON.stringify(target)}`,
      };
    }
    return { status: 'unknown', why: `unrecognized WebFetch arg syntax: ${JSON.stringify(ruleArg)}` };
  }

  if (FILE_TOOLS.has(toolName)) {
    for (const key of FILE_PATH_KEYS) {
      const val = toolInput[key];
      if (typeof val === 'string') {
        const ok = pathMatches(val, ruleArg);
        return {
          status: ok ? 'match' : 'no_match',
          why: `${key}=${JSON.stringify(val)} vs glob ${JSON.stringify(ruleArg)}`,
        };
      }
    }
    return { status: 'no_match', why: 'no file path in tool_input' };
  }

  return { status: 'unknown', why: `no matcher for tool ${toolName} with arg syntax` };
}

function evaluate(toolName, toolInput, denyRules) {
  const ambiguous = [];
  for (const rule of denyRules) {
    const { status, why } = matchRule(rule, toolName, toolInput);
    if (status === 'match') {
      return { decision: 'deny', reason: `lgtm: matched deny rule ${JSON.stringify(rule)} — ${why}` };
    }
    if (status === 'unknown') ambiguous.push(rule);
  }
  if (ambiguous.length > 0) {
    return {
      decision: 'ask',
      reason: `lgtm: deferring to Claude Code's permission engine because these deny rules could not be evaluated by the hook: ${JSON.stringify(ambiguous)}`,
    };
  }
  return { decision: 'allow', reason: 'lgtm: no deny rule matched' };
}

function resolveLogPath() {
  const override = process.env.LGTM_LOG_FILE;
  if (override !== undefined) {
    if (override === '') return null;
    return override.startsWith('~/') ? path.join(os.homedir(), override.slice(2)) : override;
  }
  return path.join(os.homedir(), '.claude', 'logs', 'lgtm.jsonl');
}

function excerptInput(toolInput) {
  const out = {};
  for (const [k, v] of Object.entries(toolInput)) {
    if (typeof v === 'string' && v.length > 200) {
      out[k] = v.slice(0, 200) + `... (${v.length} chars)`;
    } else {
      out[k] = v;
    }
  }
  return out;
}

function logDecision(toolName, toolInput, decision, reason) {
  const logPath = resolveLogPath();
  if (!logPath) return;
  try {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    const entry = {
      ts: new Date().toISOString(),
      tool: toolName,
      decision,
      reason,
      input: excerptInput(toolInput),
      cwd: process.env.CLAUDE_PROJECT_DIR || '',
    };
    fs.appendFileSync(logPath, JSON.stringify(entry) + '\n');
  } catch {
    // Logging must never break tool execution.
  }
}

function emit(decision, reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: decision,
      permissionDecisionReason: reason,
    },
    systemMessage: reason,
    suppressOutput: true,
  }));
}

async function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', () => resolve(data));
  });
}

(async function main() {
  let payload;
  try {
    payload = JSON.parse(await readStdin());
  } catch {
    emit('ask', 'lgtm: malformed payload, deferring');
    return;
  }

  const toolName = payload.tool_name || '';
  const toolInput = payload.tool_input || {};

  try {
    const denyRules = loadDenyRules();
    const { decision, reason } = evaluate(toolName, toolInput, denyRules);
    logDecision(toolName, toolInput, decision, reason);
    emit(decision, reason);
  } catch (e) {
    emit('ask', `lgtm: hook error: ${e.message}`);
  }
})();
