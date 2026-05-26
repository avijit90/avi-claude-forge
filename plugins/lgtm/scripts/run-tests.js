#!/usr/bin/env node
/**
 * Bundled self-test for the lgtm hook.
 *
 * Spins up a temporary CLAUDE_PROJECT_DIR with known deny rules, feeds
 * canned tool-call payloads to approve.js via stdin, and asserts each
 * decision plus the envelope shape (hookEventName, permissionDecision).
 *
 * Usage:
 *   ./run-tests.js                # run all
 *   ./run-tests.js --verbose      # also print each hook output
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const HERE = path.dirname(fs.realpathSync(__filename));
const APPROVE = path.join(HERE, '..', 'hooks', 'approve.js');

const DENY_RULES = [
  'Bash(curl:*)',
  'Bash(rm -rf /tmp/honeypot)',
  'Read(**/.env)',
  'Write(secrets/**)',
  'WebFetch(domain:evil.example.com)',
  'mcp__github__delete_repo',
  'mcp__notion',
];

// [label, expected, toolName, toolInput]
const CASES = [
  ['safe Bash ls', 'allow', 'Bash', { command: 'ls -la' }],
  ['curl is denied (prefix rule)', 'deny', 'Bash', { command: 'curl https://example.com' }],
  ['wget is not curl (near-miss)', 'allow', 'Bash', { command: 'wget https://example.com' }],
  ['rm -rf /tmp/honeypot exact deny', 'deny', 'Bash', { command: 'rm -rf /tmp/honeypot' }],
  ['rm -rf /tmp/other not denied', 'allow', 'Bash', { command: 'rm -rf /tmp/other' }],
  ['Read .env at root', 'deny', 'Read', { file_path: '.env' }],
  ['Read nested .env', 'deny', 'Read', { file_path: 'config/.env' }],
  ['Read package.json allowed', 'allow', 'Read', { file_path: 'package.json' }],
  ['Write inside secrets/', 'deny', 'Write', { file_path: 'secrets/api-key.txt' }],
  ['Write outside secrets/', 'allow', 'Write', { file_path: 'src/main.py' }],
  ['WebFetch evil.example.com denied', 'deny', 'WebFetch', { url: 'https://evil.example.com/x' }],
  ['WebFetch subdomain of evil denied', 'deny', 'WebFetch', { url: 'https://api.evil.example.com/x' }],
  ['WebFetch unrelated domain allowed', 'allow', 'WebFetch', { url: 'https://good.example.com/x' }],
  ['MCP github delete_repo exact deny', 'deny', 'mcp__github__delete_repo', {}],
  ['MCP github get_repo allowed', 'allow', 'mcp__github__get_repo', {}],
  ['MCP notion server-prefix denies all notion tools', 'deny', 'mcp__notion__create_page', {}],
  ['MCP unrelated server allowed', 'allow', 'mcp__linear__search', {}],
];

const UNKNOWN_CASE = {
  label: 'unknown rule syntax → ask',
  expected: 'ask',
  toolName: 'WebFetch',
  toolInput: { url: 'https://example.com' },
  denyRules: ['WebFetch(weird-non-domain-syntax)'],
};

const VERBOSE = process.argv.includes('--verbose');

function writeSettings(projectDir, denyRules) {
  const settingsDir = path.join(projectDir, '.claude');
  fs.mkdirSync(settingsDir, { recursive: true });
  fs.writeFileSync(
    path.join(settingsDir, 'settings.json'),
    JSON.stringify({ permissions: { deny: denyRules } }),
  );
}

function runApprove(payload, projectDir) {
  const env = { ...process.env, CLAUDE_PROJECT_DIR: projectDir, LGTM_LOG_FILE: '' };
  const result = spawnSync(process.execPath, [APPROVE], {
    input: JSON.stringify(payload),
    env,
    timeout: 5000,
    encoding: 'utf-8',
  });
  if (result.status !== 0) {
    throw new Error(`approve.js exited ${result.status}: ${result.stderr || '(no stderr)'}`);
  }
  if (!result.stdout) throw new Error('approve.js produced no stdout');
  return JSON.parse(result.stdout);
}

function validateEnvelope(out) {
  const problems = [];
  const hso = out.hookSpecificOutput;
  if (!hso || typeof hso !== 'object') {
    problems.push('missing hookSpecificOutput');
    return problems;
  }
  if (hso.hookEventName !== 'PreToolUse') {
    problems.push(`hookEventName != 'PreToolUse' (got ${JSON.stringify(hso.hookEventName)})`);
  }
  if (!['allow', 'deny', 'ask'].includes(hso.permissionDecision)) {
    problems.push(`bad permissionDecision: ${JSON.stringify(hso.permissionDecision)}`);
  }
  return problems;
}

function runOne(label, expected, toolName, toolInput, projectDir) {
  let out, got, status;
  try {
    out = runApprove({ tool_name: toolName, tool_input: toolInput }, projectDir);
    got = out.hookSpecificOutput?.permissionDecision ?? '?';
    const problems = validateEnvelope(out);
    status = (got === expected && problems.length === 0) ? 'PASS' : 'FAIL';
    if (problems.length > 0) got = `${got} [envelope: ${problems.join('; ')}]`;
  } catch (e) {
    status = 'ERROR';
    got = e.message;
  }
  if (VERBOSE && out) console.log(JSON.stringify(out, null, 2));
  return { status, label, expected, got };
}

function main() {
  if (!fs.existsSync(APPROVE)) {
    console.error(`ERROR: cannot find approve.js at ${APPROVE}`);
    process.exit(2);
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lgtm-test-'));
  const rows = [];
  let passed = 0, failed = 0;

  try {
    writeSettings(tmp, DENY_RULES);
    for (const [label, expected, toolName, toolInput] of CASES) {
      const row = runOne(label, expected, toolName, toolInput, tmp);
      rows.push(row);
      if (row.status === 'PASS') passed++; else failed++;
    }

    writeSettings(tmp, UNKNOWN_CASE.denyRules);
    const row = runOne(UNKNOWN_CASE.label, UNKNOWN_CASE.expected, UNKNOWN_CASE.toolName, UNKNOWN_CASE.toolInput, tmp);
    rows.push(row);
    if (row.status === 'PASS') passed++; else failed++;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  const wLabel = Math.max(...rows.map(r => r.label.length), 'CASE'.length);
  const wExp = Math.max(...rows.map(r => r.expected.length), 'EXPECT'.length);
  console.log();
  console.log(`STATUS  ${'CASE'.padEnd(wLabel)}  ${'EXPECT'.padEnd(wExp)}  GOT`);
  console.log('-'.repeat(8 + wLabel + 2 + wExp + 2 + 20));
  for (const { status, label, expected, got } of rows) {
    const marker = status === 'PASS' ? '✓' : '✗';
    console.log(`${marker} ${status.padEnd(4)}  ${label.padEnd(wLabel)}  ${expected.padEnd(wExp)}  ${got}`);
  }
  console.log();
  console.log(`${passed} passed, ${failed} failed, ${rows.length} total`);
  console.log(`Hook script: ${APPROVE}`);

  process.exit(failed === 0 ? 0 : 1);
}

main();
