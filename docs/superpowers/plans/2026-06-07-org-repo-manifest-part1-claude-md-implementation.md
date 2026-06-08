# org-repo-manifest Part 1 — CLAUDE.md Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin (`org-repo-manifest`) that lets a tech lead draft and audit CLAUDE.md files against an org rubric, scored semantically by an LLM agent and produced via an interactive drafting skill.

**Architecture:** Two user-facing commands (`/draft-claude-md`, `/audit-claude-md`) wrap a procedural skill (drafting, interactive in main context) and an autonomous agent (auditing, isolated context). A rubric file is the scoring contract; templates ship the canonical CLAUDE.md skeleton and the org conventions reference. Evals live in `evals/` and are manually run in v1 — automation is deferred.

**Tech Stack:** Markdown for all components (commands, skill, agent, rubric, templates, evals). No code beyond JSON for `plugin.json`, `marketplace.json`, and `evals.json`. Plugin lives at `plugins/org-repo-manifest/` and is registered in the existing `.claude-plugin/marketplace.json`.

**Spec:** `docs/superpowers/specs/2026-06-07-org-repo-manifest-part1-claude-md-design.md`

**Revision history:** v1 → v2 surgically revised after `2026-06-07-org-repo-manifest-part1-claude-md-implementation-review.md`. v2 → v3 surgically revised after `-implementation-review2.md`. Key architectural changes:

- v2: agent/skill no longer try to `Read ${CLAUDE_PLUGIN_ROOT}/...` (which doesn't resolve in those contexts). Commands embed the rubric/templates/conventions into their prompt body via `@${CLAUDE_PLUGIN_ROOT}/...` syntax.
- v3 (agent-delivery fix): the v2 fix was only complete for the **skill** path — a skill auto-triggers in the same conversation, so command-body embeds reach it. The **auditor agent** runs in *isolated context* (dispatched via the Agent tool) and does NOT see the main conversation. v3 closes that gap: `/audit-claude-md` (Task 10) explicitly **pastes the embedded rubric + conventions text into the Agent tool's `prompt` parameter**, and the auditor agent (Task 5) operates on whatever its prompt contains.

See `feedback_plugin_file_embedding.md` in memory for the embed pattern. (The earlier draft cited `5128bcc Fix style-evaluator: embed referenced files into prompts` as prior art; that commit fixed a Python eval-runner dropping a `files:` field, which is a different mechanism. It is not evidence of embed-to-agent delivery and has been dropped as a citation.)

**What this plan's per-task verification actually proves:** the `wc -l`, `grep -c`, and `python3 -c "json.load(...)"` checks at the end of most tasks are **presence checks**. They prove a file was written, parses, and is non-trivially populated. They do NOT prove the prompts produce the intended behavior. Behavior verification is concentrated in Task 17 (manual smoke tests + plugin-validator) and in the manually-run eval suites (`evals/README.md`). Do not interpret all-green checkboxes as "the plugin works."

---

## File structure (final state)

```
plugins/org-repo-manifest/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── commands/
│   ├── draft-claude-md.md
│   └── audit-claude-md.md
├── agents/
│   └── claude-md-auditor.md
├── skills/
│   └── claude-md-drafting/
│       ├── SKILL.md
│       ├── references/
│       │   ├── section-guides.md
│       │   └── feature-detection.md
│       └── examples/
│           └── good-claude-md.md
├── rubrics/
│   └── claude-md.md
├── templates/
│   ├── CLAUDE.md.template
│   └── conventions.md
└── evals/
    ├── README.md
    ├── claude-md-drafting/
    │   ├── evals.json
    │   └── fixtures/
    │       ├── node-service/
    │       ├── spring-boot/
    │       └── react-mfe/
    └── claude-md-auditor/
        ├── evals.json
        └── fixtures/
            ├── missing-section/
            ├── stale-architecture/
            ├── vague-features/
            ├── oversized/
            └── conventions-drift/
```

Plus one edit to existing file: `.claude-plugin/marketplace.json` (add the new plugin entry).

---

## Conventions across all tasks

- **Branch:** all commits land on `feature/org-repo-manifest-part1` (already pushed to origin).
- **Commits:** one per task. Message format: `<scope>: <imperative subject>` (e.g. `org-repo-manifest: add rubric`). Co-author trailer required.
- **Path prefix:** unless stated otherwise, all paths in tasks are relative to the repo root (the worktree at `/home/agent/work/avi-claude-forge/.claude/worktrees/org-repo-manifest/`).
- **Git identity:** the worktree has no committer identity in git config. Use per-command overrides: `git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "..."`.

---

## Task 1: Scaffold plugin manifest and register in marketplace

**Files:**
- Create: `plugins/org-repo-manifest/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create the plugin directory and manifest**

```bash
mkdir -p plugins/org-repo-manifest/.claude-plugin
```

Write `plugins/org-repo-manifest/.claude-plugin/plugin.json`:

```json
{
  "name": "org-repo-manifest",
  "version": "0.1.0",
  "description": "Draft and audit CLAUDE.md files for enterprise microservice and MFE repos against an org rubric. Ships /draft-claude-md (interactive skill) and /audit-claude-md (read-only agent that scores 7 criteria and proposes section replacements).",
  "author": {
    "name": "avijit90"
  },
  "keywords": [
    "claude-md",
    "documentation",
    "audit",
    "enterprise",
    "org-standards"
  ]
}
```

- [ ] **Step 2: Register the plugin in the marketplace**

Edit `.claude-plugin/marketplace.json`. Append a new entry to the `plugins` array (keep existing entries unchanged):

```json
    {
      "name": "org-repo-manifest",
      "description": "Draft and audit CLAUDE.md files for enterprise microservice and MFE repos against an org rubric. Ships /draft-claude-md (interactive skill) and /audit-claude-md (read-only agent that scores 7 criteria and proposes section replacements).",
      "version": "0.1.0",
      "source": "./plugins/org-repo-manifest",
      "category": "documentation",
      "keywords": [
        "claude-md",
        "documentation",
        "audit",
        "enterprise",
        "org-standards"
      ]
    }
```

- [ ] **Step 3: Validate JSON syntax**

Run: `python3 -c "import json; json.load(open('plugins/org-repo-manifest/.claude-plugin/plugin.json'))" && python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))"`
Expected: silent success (exit 0).

- [ ] **Step 4: Commit**

```bash
git add plugins/org-repo-manifest/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: scaffold plugin manifest

Add plugin.json with name/version/description/author/keywords. Register
in marketplace.json under the documentation category.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Write the 7-criterion rubric

**Files:**
- Create: `plugins/org-repo-manifest/rubrics/claude-md.md`

This file is the scoring contract. Both the auditor agent and the drafting skill reference it.

- [ ] **Step 1: Create the rubric file**

```bash
mkdir -p plugins/org-repo-manifest/rubrics
```

Write `plugins/org-repo-manifest/rubrics/claude-md.md`:

```markdown
# CLAUDE.md Rubric

Adapted from the `claude-md-improver` skill in [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management/skills/claude-md-improver), with a Purpose & Features criterion added.

## Scoring model

Each criterion is graded **A–F**. No single overall letter grade is produced. The audit report shows per-criterion grades plus a single summary metric: **X of N criteria graded below B** (always with the denominator). N/A criteria are excluded from both the report set and the count.

## Criteria

### 1. Commands & workflows
Are build/test/run/deploy commands present and copy-pasteable? An engineer reading only this section should be able to bring the repo up, run its tests, and deploy it without further reading.

### 2. Architecture clarity
Can someone unfamiliar with the repo navigate it from this section? Are entry points named? Are major boundaries (HTTP, queue, DB) called out? Is it shaped like a map a reader can use to find code?

### 3. Purpose & Features clarity
Is Purpose a sharp positive definition of what this repo IS, not a list of what it isn't? Are Features specific (named capabilities, not "various utilities"), current (matches what the code actually does), and non-redundant (each item is a distinct capability)?

### 4. Non-obvious patterns
Are gotchas and sibling-repo boundaries called out? Things a reader cannot infer from the code alone — runtime quirks, ordering constraints, deployment idiosyncrasies, where this service ends and an adjacent one begins.

### 5. Conciseness
Is it ≤150 lines (including headers and blank lines)? Signal-to-noise ratio: every line earns its place. No exposition, no marketing copy, no padding.

### 6. Currency
Does it match the actual repo today? Does the Conventions section still align with the canonical `templates/conventions.md`?

**When this scores below B, the finding MUST name the sub-cause:**
- `repo drift: <section> stale` — repo evolved, doc didn't follow
- `convention drift: Conventions section misaligned` — Conventions summary no longer represents the canonical file

This forces the user to know which section to fix.

### 7. Actionability
Does each section give a reader something concrete they can do? "Read X to understand Y" rather than "the system is complex." Commands are runnable. Architecture leads to specific files. Gotchas warn against a specific action.

## Grade reference

- **A** — Exemplar. Could be cited as the canonical example for other repos.
- **B** — Solid. No reader would be misled or blocked.
- **C** — Functional but flawed. Reader gets work done; some sections are vague or stale.
- **D** — Misleading or unhelpful in places. Risk of wasting reader time.
- **F** — Wrong, missing, or actively harmful.

## Convention-drift findings are advisory

A curated Conventions summary *will* differ from the canonical `templates/conventions.md` by design — it omits rules that don't apply to this repo. The auditor cannot cleanly distinguish "deliberately scoped out" from "forgotten / went stale," so some convention-drift findings will be false positives. Reviewers should treat these as suggestions to confirm, not as proof of drift.
```

- [ ] **Step 2: Verify file written**

Run: `wc -l plugins/org-repo-manifest/rubrics/claude-md.md`
Expected: a non-zero line count (around 50–60).

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/rubrics/claude-md.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add 7-criterion rubric

The scoring contract for /audit-claude-md. A-F per criterion plus an
"X of N below B" summary. No overall letter grade.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Write canonical conventions template

**Files:**
- Create: `plugins/org-repo-manifest/templates/conventions.md`

This is the canonical org conventions reference. The drafting skill presents it to the user and asks which rules apply to the current repo. The auditor compares the inline Conventions section against this file.

- [ ] **Step 1: Create the conventions template**

```bash
mkdir -p plugins/org-repo-manifest/templates
```

Write `plugins/org-repo-manifest/templates/conventions.md`:

```markdown
# Org Conventions (Canonical Reference)

This is the full set of org-level conventions across stacks. Each repo's CLAUDE.md Conventions section should be a *curated summary* — pick the rules that apply to that repo's stack and runtime.

## Logging

1. Structured logs only (JSON). No `print`, no `console.log` in committed code.
2. Log levels: ERROR for actionable failures, WARN for degraded paths, INFO for state transitions, DEBUG for diagnostic detail. No INFO in hot loops.
3. Every log line must carry a correlation ID. Generate at the edge if absent; propagate via headers.
4. Never log secrets, tokens, PII. Use the shared redaction helper.

## Error handling

5. Throw typed errors at boundaries; convert to wire format at the edge (HTTP/queue).
6. Don't catch-and-swallow. If you catch, either re-throw or convert with reason.
7. Retries: only at the edge, only with backoff, only when the operation is idempotent.
8. Never use exceptions for control flow.

## Naming

9. Files: kebab-case for everything (`order-service.ts`, not `OrderService.ts`).
10. Functions/methods: verb-first (`processOrder`, not `orderProcessor`).
11. Types/classes: PascalCase, noun-form.
12. Constants: SCREAMING_SNAKE_CASE only for truly module-level invariants.

## Testing

13. Tests live next to source: `foo.ts` → `foo.test.ts`.
14. No mocking the database — use a real test instance (in-memory or docker).
15. Test names are full sentences: `it("rejects a duplicate order with a 409", ...)`.
16. No `sleep()` in tests. Use polling with a hard timeout.

## API design

17. REST: nouns in URLs, verbs in methods. `/orders` + POST, not `/createOrder`.
18. All responses are JSON. Error responses include `{ "error": { "code", "message" } }`.
19. Versioning lives in the URL path (`/v1/orders`). Breaking changes bump the major.
20. Pagination is cursor-based, never offset.

## Configuration

21. Config from env vars only. No config files committed.
22. Required env vars fail-fast at startup with a clear message naming each missing var.
23. Secrets come from the secret manager, never from env vars directly in prod.

## Frontend (React MFEs)

24. Components: function components only, no class components.
25. State: prefer local component state; lift only when proven necessary.
26. Side effects: in `useEffect` with explicit dependencies; never in render.
27. No CSS-in-JS for new components; use the shared design tokens.
```

- [ ] **Step 2: Verify the file**

Run: `wc -l plugins/org-repo-manifest/templates/conventions.md`
Expected: line count > 40.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/templates/conventions.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add canonical conventions template

The full org conventions reference. Drafting skill curates a subset
for each repo's CLAUDE.md; auditor uses this as the drift baseline.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Write the CLAUDE.md skeleton template

**Files:**
- Create: `plugins/org-repo-manifest/templates/CLAUDE.md.template`

This is the structural skeleton the drafting skill instantiates. Section headers are exact (used by the auditor to locate sections for replacement).

- [ ] **Step 1: Create the template**

Write `plugins/org-repo-manifest/templates/CLAUDE.md.template`:

```markdown
# {{REPO_NAME}}

## Purpose

{{PURPOSE}}

## Features

{{FEATURES}}

## Architecture

{{ARCHITECTURE}}

## Commands

```bash
{{COMMANDS}}
```

## Gotchas

{{GOTCHAS}}

## Conventions

{{CONVENTIONS}}

## Reference

See `docs/` for:
{{REFERENCE_INDEX}}
```

- [ ] **Step 2: Verify section headers match spec**

Run: `grep -E "^## " plugins/org-repo-manifest/templates/CLAUDE.md.template`
Expected:
```
## Purpose
## Features
## Architecture
## Commands
## Gotchas
## Conventions
## Reference
```

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/templates/CLAUDE.md.template
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add CLAUDE.md skeleton template

Structural skeleton with 7 sections and placeholder tokens. Headers
are exact and used by the auditor to locate sections for replacement.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Write the auditor agent

**Files:**
- Create: `plugins/org-repo-manifest/agents/claude-md-auditor.md`

This is an autonomous subagent with isolated context. It reads CLAUDE.md, the repo structure, build files, and `templates/conventions.md`, then returns scores + findings + section replacements.

- [ ] **Step 1: Create the agent file**

```bash
mkdir -p plugins/org-repo-manifest/agents
```

Write `plugins/org-repo-manifest/agents/claude-md-auditor.md`:

```markdown
---
name: claude-md-auditor
description: Use this agent to audit a repo's CLAUDE.md against the org rubric. Reads CLAUDE.md, repo structure, build files, and the canonical conventions template; returns per-criterion A-F grades, specific findings, and suggested full-section replacements. Read-only — never writes files. Trigger when the user runs /audit-claude-md or asks to audit/grade/review a CLAUDE.md file against org standards.
tools: Read, Glob, Grep
---

You are the CLAUDE.md auditor. You score a repo's CLAUDE.md against the org rubric and return findings with concrete suggested replacements. You are read-only — you never write or edit files. The main context applies your suggestions only after the user confirms each one.

## Inputs

You run in **isolated context**. You receive only the prompt the dispatching command (`/audit-claude-md`) hands you — you do NOT see the main conversation. The dispatcher will paste two files directly into your prompt under clearly labelled headings:
- **The rubric** (under a `## Rubric` heading) — your scoring contract (the 7 criteria, A–F semantics, summary metric definition, convention-drift advisory note).
- **The canonical conventions reference** (under a `## Canonical conventions` heading) — used for Currency's convention-drift sub-cause.

Operate on whatever text appears under those headings in your prompt. Do NOT attempt to `Read ${CLAUDE_PLUGIN_ROOT}/...` paths — that env var does not resolve in agent context and the literal string is not a valid filename.

From the local repo, read:

1. `<repo>/CLAUDE.md` (use Read) — the file under audit. If absent or empty, return all-F grades with the recommendation to delete and re-run `/draft-claude-md`.
2. The repo structure (Glob + Grep) — map directories, find entry points, identify the stack (package.json, pom.xml, build.gradle, Cargo.toml, pyproject.toml, etc.).

If the `## Canonical conventions` section is missing from your prompt or is empty (the dispatcher failed to paste it), mark the Currency criterion as N/A with reason "cannot verify conventions drift — canonical conventions not provided in prompt" and continue scoring the other six.

## Scoring procedure

1. Read CLAUDE.md fully.
2. Verify which of the 7 required section headers are present: Purpose, Features, Architecture, Commands, Gotchas, Conventions, Reference. A missing section can only tank a criterion whose substance it owns — e.g. missing Commands tanks "Commands & workflows" and "Actionability" (reader can't run what isn't there). Do NOT tank Conciseness for a missing section; a shorter file isn't less concise.
3. For each of the 7 criteria in the rubric, assign an A–F grade based ONLY on the rubric's stated measure. Do not invent criteria.
4. For Currency below B, the finding MUST identify the sub-cause: `repo drift: <section> stale` or `convention drift: Conventions section misaligned`. Do not return a Currency C/D/F without naming the sub-cause.
5. List up to 10 specific findings. Each finding names the section, the defect, and a one-line reason.
6. For each section that scored a criterion C or below and where the defect is content-level (not "section missing entirely"), return a **full-section replacement** as text. The replacement is the complete new section starting with the `## SectionName` header and ending before the next `## ` header. No line diffs.
7. Compute the summary: count of criteria graded below B, with the denominator (e.g. `3 of 7 below B` or `2 of 6 below B` when one is N/A).

## Output format

Return a single message in this exact shape:

```
# CLAUDE.md Audit Report

## Grades

| Criterion | Grade |
|---|---|
| Commands & workflows | <A-F or N/A> |
| Architecture clarity | <A-F or N/A> |
| Purpose & Features clarity | <A-F or N/A> |
| Non-obvious patterns | <A-F or N/A> |
| Conciseness | <A-F or N/A> |
| Currency | <A-F or N/A> |
| Actionability | <A-F or N/A> |

**Summary:** <X> of <N> criteria below B.

## Not scored (with reason)

<list any N/A criteria with their reasons, or write "None.">

## Findings

1. **<Section name>**: <one-line defect description>
   *Reason:* <one line>
2. ...
(Up to 10.)

## Suggested replacements

### <Section name>

\`\`\`
## <Section name>

<new section text, complete from header to just before the next ## header>
\`\`\`

(One block per replaceable section. Skip if no replacement is warranted.)
```

## Constraints

- You are read-only. Do not use Write, Edit, or any tool that modifies files.
- Do not invent rubric criteria. The seven are fixed.
- Do not gate or refuse based on findings. Your role is to report. The main context decides what to apply.
- Do not produce line diffs. Always full-section replacements.
- If you cannot locate a section header in CLAUDE.md (e.g., the section is missing), report it in findings but do not produce a replacement that would be inserted into ambiguous structure — let the main context handle the missing-section case.
- Convention-drift findings are advisory by construction (see rubric). State them with that framing; don't claim certainty about whether drift is deliberate.
```

- [ ] **Step 2: Validate frontmatter parses**

Run: `python3 -c "
import sys
with open('plugins/org-repo-manifest/agents/claude-md-auditor.md') as f:
    content = f.read()
assert content.startswith('---\n'), 'missing opening frontmatter'
parts = content.split('---\n', 2)
assert len(parts) >= 3, 'malformed frontmatter'
fm = parts[1]
assert 'name:' in fm and 'description:' in fm and 'tools:' in fm, 'missing required fields'
print('OK')
"`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/agents/claude-md-auditor.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add claude-md-auditor agent

Read-only autonomous subagent. Scores 7 rubric criteria, returns
findings and full-section replacements. Main context applies user-
confirmed replacements between known ## headers.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Write the drafting skill — SKILL.md

**Files:**
- Create: `plugins/org-repo-manifest/skills/claude-md-drafting/SKILL.md`

The skill auto-triggers when `/draft-claude-md` runs. It governs the interactive Q&A flow in main context.

- [ ] **Step 1: Create the skill file**

```bash
mkdir -p plugins/org-repo-manifest/skills/claude-md-drafting
```

Write `plugins/org-repo-manifest/skills/claude-md-drafting/SKILL.md`:

```markdown
---
name: claude-md-drafting
description: Use when the user runs /draft-claude-md or asks to bootstrap, generate, write, or scaffold a CLAUDE.md for an org repo. Detects build stack, auto-fills the Commands section, then interactively prompts the user for Purpose, Features, Architecture, Gotchas, and Conventions selection. Conversational prompts for prose; AskUserQuestion only for discrete choices (stack pick, accept/reject).
---

# Drafting a CLAUDE.md

You are guiding the user through drafting a CLAUDE.md file for the current repo. The output is a single CLAUDE.md at the repo root, with the 7 standard sections, capped at 150 lines.

## Inputs from the dispatching command

`/draft-claude-md` embeds two files into the conversation before triggering you:
- **The canonical conventions reference** — the org's full conventions list.
- **The CLAUDE.md template** — the structural skeleton with placeholder tokens.

You do NOT need to read these files yourself. They are already in the conversation as embedded content. Operate on them directly.

For your own bundled references (`references/section-guides.md`, `references/feature-detection.md`, `examples/good-claude-md.md`), use Read with bare relative paths — the skill's directory is in scope when the skill is triggered.

## Flow

### Step 1 — Detect the build stack

Use Glob to look for, in this order:
- `package.json` (Node)
- `pom.xml`, `build.gradle`, `build.gradle.kts` (JVM)
- `pyproject.toml`, `setup.py`, `requirements.txt` (Python)
- `Cargo.toml` (Rust)
- `go.mod` (Go)
- `Gemfile` (Ruby)

If **none** are present: warn the user, ask "What does this repo build with?", and accept their answer as a starting point for Commands.

If **multiple** are present (e.g., Node + Python): use AskUserQuestion to pick which to document, or "both" for a dual-stack repo. Up to 4 options.

### Step 2 — Draft the Commands section from detected files

For each detected stack, extract real commands. Examples:
- Node: read `package.json` scripts; populate `npm install`, `npm test`, `npm run build`, `npm start` from what's actually defined.
- JVM (Maven): if `mvnw` + `.mvn/wrapper/` present, use `./mvnw clean install`, `./mvnw test`, `./mvnw spring-boot:run`. Otherwise use `mvn clean install`, `mvn test`, `mvn spring-boot:run` (if Spring detected).
- Python (pyproject): `pip install -e .`, `pytest`, `python -m <module>`.

Auto-detection earns its keep here. If you can't be specific, leave a TODO in the section and prompt the user once.

### Step 3 — Conversational prose prompts (in main context)

Ask the user, one at a time, using natural prose (not AskUserQuestion). For per-section guidance on what good looks like, Read `references/section-guides.md` (relative to this skill).

1. **Purpose** — "In one or two sentences, what is this repo? Positive definition — what it IS, not what it isn't." If the answer is vague (e.g. "does payments stuff"), prompt once for sharper text. Accept whatever they give the second time.

2. **Features** — "List the capabilities this service provides. Bullet form, specific. What can a caller actually do?" Cannot be auto-detected; user input is the source of truth.

3. **Architecture** — Draft a starter shape from the repo tree (use Glob to map the top 2 levels). Show it to the user: "Here's what I see — entry points at `<paths>`, major dirs are `<list>`. Confirm or rewrite."

4. **Gotchas** — "What would a new engineer trip over? Runtime quirks, ordering constraints, deployment idiosyncrasies. Also: what adjacent repos does this one talk to, and where are the boundaries?" One-liner per gotcha.

### Step 4 — Conventions selection (conversational)

The canonical conventions list was embedded into the conversation by the dispatching command. Present its numbered rule list to the user with a header:

"Here is the canonical org conventions list. Which apply to this repo? Reply with the rule numbers (e.g. '1, 2, 5-8, 13'), or 'all' to include everything relevant to the detected stack."

The list can exceed AskUserQuestion's 4-option cap, so this MUST be conversational. Parse their reply, extract the rules they named, and inline those rule TEXTS (not just numbers) into the Conventions section as bullets. Curate the wording for the repo's stack — drop irrelevant references (e.g., no React rules in a backend service).

### Step 5 — Assemble and preview

The CLAUDE.md template was embedded into the conversation by the dispatching command. Substitute each `{{TOKEN}}` in it with the gathered content and produce the final CLAUDE.md.

**Reference section:** auto-list `docs/` subdirectories if present. Otherwise prompt: "Do you have an existing `docs/` folder I should index? If not, leave Reference as a TODO."

Print the assembled CLAUDE.md to the main context as a preview.

### Step 6 — Accept / reject

Use AskUserQuestion with 2 options: "Write to CLAUDE.md" or "Cancel". On accept, write the file. On cancel, exit without writing.

## Constraints

- Final file must be ≤150 lines including headers and blank lines. If the draft exceeds, prune the longest sections (likely Conventions or Features) and re-preview before asking accept/reject.
- Section headers MUST be exactly: `## Purpose`, `## Features`, `## Architecture`, `## Commands`, `## Gotchas`, `## Conventions`, `## Reference`. The auditor relies on these for section-replacement.
- Do NOT auto-fill Features. Always ask the user.
- Do NOT use AskUserQuestion for prose. Reserve it for: stack disambiguation, final accept/reject.
- Do NOT @import the conventions template. Inline the curated subset.

## On cancellation

If the user cancels at any point, exit cleanly. Do not write a partial file.

## Additional references

- See `references/section-guides.md` for what good looks like per section.
- See `references/feature-detection.md` for the heuristics used in Step 1–2.
- See `examples/good-claude-md.md` for an exemplar.
```

- [ ] **Step 2: Verify frontmatter**

Run: `head -5 plugins/org-repo-manifest/skills/claude-md-drafting/SKILL.md`
Expected: starts with `---`, contains `name:` and `description:` lines.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/skills/claude-md-drafting/SKILL.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add claude-md-drafting skill (SKILL.md)

Procedural domain expertise for drafting CLAUDE.md. Detects stack,
auto-fills Commands, conversationally prompts for Purpose/Features/
Architecture/Gotchas/Conventions, then writes the file on accept.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Write drafting skill references

**Files:**
- Create: `plugins/org-repo-manifest/skills/claude-md-drafting/references/section-guides.md`
- Create: `plugins/org-repo-manifest/skills/claude-md-drafting/references/feature-detection.md`

Progressive disclosure: SKILL.md stays lean; details live in references/.

- [ ] **Step 1: Create section-guides.md**

```bash
mkdir -p plugins/org-repo-manifest/skills/claude-md-drafting/references
```

Write `plugins/org-repo-manifest/skills/claude-md-drafting/references/section-guides.md`:

```markdown
# Section guides — what good looks like

## Purpose (≤5 lines)

**Good:** "Receives card-present payment authorizations from terminals, validates them against fraud rules, and forwards approved auths to the settlement service. Owns the auth-request → auth-response loop."

**Bad:** "Handles payments." (Vague.) "Does payment stuff and other things." (Negative space, vague.)

**Prompt for the user:** "In one or two sentences, what IS this repo? Positive definition."

## Features (≤15 lines)

**Good:** Each bullet is a distinct capability a caller can invoke or rely on. Examples:
- "POST /v1/auth — accepts a tokenized card + amount, returns approve/decline + fraud score."
- "Subscribes to `settlement-completed` events, marks the auth row as settled."

**Bad:** "Various utilities" / "Helper functions" / repetition of the Purpose line.

**Prompt for the user:** "List the capabilities. Each bullet should be something a caller can actually do or rely on."

## Architecture (≤10 lines)

**Good:** "FastAPI HTTP server (`src/api/main.py`). Kafka consumer (`src/consumers/settlement.py`). Postgres via SQLAlchemy. Background jobs in `src/jobs/`, scheduled by APScheduler."

**Bad:** "Standard layered architecture." (Generic.) "MVC pattern." (Doesn't help a reader navigate.)

**Approach:** Draft a starter shape from the top-level layout. Use Glob with explicit two-level patterns (`*` and `*/*`) to list the top dirs and their immediate children, plus targeted Globs for likely entry-point patterns (`src/server.{js,ts}`, `src/main.{py,ts}`, `cmd/*/main.go`, etc.). Name entry points by file path. Show to user, accept rewrite. Do NOT use `**/*` and hope for "two levels" — Glob's `limit` caps result count, not recursion depth.

## Commands (≤15 lines)

**Good:** Copy-pasteable shell commands, grouped by purpose:
```bash
# install
npm install

# test
npm test
npm run test:integration

# run
npm start

# deploy
npm run build && ./deploy.sh staging
```

**Bad:** "Run the standard commands." Prose. Missing the build step.

**Approach:** Extract from `package.json` scripts, `Makefile`, `pom.xml`, etc.

## Gotchas (≤15 lines)

**Good:** One-liner per gotcha. Specific and actionable.
- "The `auth-id` is generated by the terminal, not by us. Don't regenerate."
- "Settlement service treats amounts in cents; we send dollars. Conversion lives in `src/settlement-client.py`."

**Bad:** "Be careful with edge cases." Vague generalities.

**Approach:** Prompt the user. These cannot be detected.

## Conventions (flex, ≤30 lines)

**Good:** Curated subset of `templates/conventions.md` relevant to this stack. Inline the rule text, not just rule numbers.

**Bad:** A verbatim copy of the full canonical file (wastes context). Just the rule numbers ("rules 1, 5, 12") with no text (forces the reader to load the canonical file).

**Approach:** Present the canonical list to the user, ask which apply, inline the chosen ones.

## Reference (≤6 lines)

**Good:** A flat list of `docs/` subdirectories with one-line purposes:
- `docs/adrs/` — architecture decisions
- `docs/runbooks/` — operational procedures
- `docs/api/` — generated API docs

**Bad:** @imports. External links. Long explanations.

**Approach:** Auto-list `docs/*` and prompt for one-line descriptions.
```

- [ ] **Step 2: Create feature-detection.md**

Write `plugins/org-repo-manifest/skills/claude-md-drafting/references/feature-detection.md`:

```markdown
# Feature detection heuristics

The drafting skill auto-detects what it can from the repo. Auto-detection is RELIABLE only for the **Commands** section. Everything else needs user input.

## Stack detection

Probe order (first match wins; multiple matches → AskUserQuestion):

| File present | Stack |
|---|---|
| `package.json` | Node |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | JVM |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `Gemfile` | Ruby |

## Commands extraction

### Node (package.json)

Read `scripts` object. Translate keys to standard commands:
- `test`, `test:*` → test commands
- `build`, `compile` → build commands
- `start`, `dev`, `serve` → run commands
- `lint`, `lint:fix` → quality commands

Also include `npm install` as the install step.

### JVM (Maven / Gradle)

Maven: prefer `./mvnw` if the wrapper is committed (`mvnw` script + `.mvn/wrapper/` dir present); otherwise `mvn`. Examples: `mvn clean install`, `mvn test`, `mvn spring-boot:run` (if `spring-boot-starter` in pom.xml).

Gradle: prefer `./gradlew` if the wrapper is committed (`gradlew` script + `gradle/wrapper/` dir present); otherwise `gradle`. Examples: `gradle build`, `gradle test`, `gradle bootRun` (Spring Boot) or `gradle run`.

**Auto-detection rule:** check for the wrapper script. If absent, emit the bare command (`mvn`/`gradle`). Emitting `./mvnw` against a repo that doesn't ship the wrapper produces a non-runnable command — exactly the failure mode the rubric's "copy-pasteable Commands" criterion is meant to catch.

### Python

If `pyproject.toml` with poetry: `poetry install`, `poetry run pytest`, etc.
If `requirements.txt`: `pip install -r requirements.txt`, `pytest`.
If a `[scripts]` table exists: surface it.

### Rust

`cargo build`, `cargo test`, `cargo run`.

### Go

`go build ./...`, `go test ./...`, `go run ./cmd/<binary>`.

## Entry-point detection (Architecture starter)

For each stack, look for the typical entry point and name it:

| Stack | Typical entry point file |
|---|---|
| Node (Express) | `src/server.js`, `src/index.js`, `src/app.ts` |
| Node (NestJS) | `src/main.ts` |
| JVM (Spring Boot) | Class with `@SpringBootApplication` |
| Python (FastAPI) | File with `app = FastAPI()` |
| Python (Django) | `manage.py`, `wsgi.py` |
| Go | `cmd/<binary>/main.go` |
| Rust | `src/main.rs` or `src/lib.rs` |

Use Grep to find the marker (`@SpringBootApplication`, `app = FastAPI`, etc.).

## What NOT to auto-detect

- Features. The repo's externally visible capabilities cannot be derived from code structure. Always ask.
- Architecture intent. The starter shape from the tree is just a hint — the user owns the final phrasing.
- Gotchas. By definition non-obvious; cannot be extracted.
- Conventions selection. The user knows which rules apply.
- Purpose. The repo's reason to exist is a human framing decision.
```

- [ ] **Step 3: Verify both files**

Run: `ls -la plugins/org-repo-manifest/skills/claude-md-drafting/references/`
Expected: both files present with non-zero size.

- [ ] **Step 4: Commit**

```bash
git add plugins/org-repo-manifest/skills/claude-md-drafting/references/
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add drafting skill references

section-guides.md: per-section examples of good vs bad.
feature-detection.md: stack detection table and entry-point heuristics.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Write drafting skill example

**Files:**
- Create: `plugins/org-repo-manifest/skills/claude-md-drafting/examples/good-claude-md.md`

A reference exemplar the skill can point to.

- [ ] **Step 1: Create the example**

```bash
mkdir -p plugins/org-repo-manifest/skills/claude-md-drafting/examples
```

Write `plugins/org-repo-manifest/skills/claude-md-drafting/examples/good-claude-md.md`:

````markdown
# Example: a good CLAUDE.md

This is what the drafting skill aims to produce — a CLAUDE.md for a fictional `auth-service`, ~95 lines, all 7 sections, copy-pasteable commands, specific gotchas, curated conventions.

---

```markdown
# auth-service

## Purpose

Issues, verifies, and revokes short-lived JWT access tokens for the org's internal services. Owns the OAuth2 password-grant and client-credentials flows; refresh-token rotation; and the `/userinfo` endpoint.

## Features

- POST /v1/token — issues access + refresh tokens given valid credentials
- POST /v1/token/refresh — rotates refresh tokens; old token is revoked atomically
- POST /v1/token/revoke — blacklists a token by jti
- GET /v1/userinfo — returns the authenticated user profile claims
- Subscribes to `user-deleted` events and revokes all tokens for the user
- Emits `token-issued` and `token-revoked` events for audit pipeline

## Architecture

FastAPI HTTP server, entry point `src/api/main.py`. Kafka consumer in `src/consumers/user_events.py`. Postgres via SQLAlchemy (`src/db/`). Token signing uses ECDSA keys loaded from the secret manager at startup. Background revocation sweep in `src/jobs/sweep.py`, scheduled by APScheduler.

## Commands

```bash
# install
poetry install

# test
poetry run pytest
poetry run pytest tests/integration -m integration

# run locally
poetry run uvicorn auth_service.api.main:app --reload

# deploy
make deploy ENV=staging
```

## Gotchas

- Token signing keys rotate weekly. If you're testing locally, point `KEY_SOURCE=file` at `tests/fixtures/keys/` — production secret manager has request limits.
- The `jti` blacklist lives in Redis with a TTL matching the token expiry. **Never** set TTL longer than the token lifetime; the table will explode.
- We talk to user-service for `/userinfo` payload enrichment. If user-service is down, `/userinfo` falls back to claims-only — but `/token` requests still fail closed.
- Refresh-token rotation is atomic via a Postgres advisory lock. Don't replace with optimistic concurrency; we've burned on that before.

## Conventions

- Structured JSON logs only; correlation IDs propagated via `X-Request-Id`
- Typed errors at boundaries (`AuthError` subclasses), converted to HTTP at the edge
- Files: kebab-case (`token-issuer.py`). Functions: verb-first (`issue_token`).
- Tests next to source: `token_issuer.py` → `token_issuer_test.py`. No DB mocking — real Postgres via docker-compose.
- Config from env vars; required vars fail-fast at startup naming each missing one.
- Secrets from the secret manager only. Never in env vars in prod.
- REST: nouns in URLs, verbs in methods. Error responses: `{"error": {"code", "message"}}`.

## Reference

See `docs/` for:
- `docs/adrs/` — architecture decisions (ECDSA key rotation, refresh-token semantics)
- `docs/runbooks/` — on-call procedures (revoke-all, key-rotation, blacklist-cleanup)
- `docs/api/` — generated OpenAPI spec
```

---

## Why this is good

- **Purpose** is a positive definition of what the service IS, with the actual scope.
- **Features** are distinct, specific, and externally observable.
- **Architecture** names files an engineer can navigate to.
- **Commands** are copy-pasteable, grouped by purpose.
- **Gotchas** are non-obvious things — no engineer can infer them from the code.
- **Conventions** is a curated subset of the canonical file, inlined.
- **Reference** points to where deeper docs live, with one-line purposes.

Line count: ~70 content lines, ~95 total including headers and blank lines. Under the 150 cap with room to spare.
````

- [ ] **Step 2: Verify the example exists and is non-empty**

Run: `wc -l plugins/org-repo-manifest/skills/claude-md-drafting/examples/good-claude-md.md`
Expected: line count > 50.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/skills/claude-md-drafting/examples/good-claude-md.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add good-claude-md example

A reference exemplar for what the drafting skill aims to produce.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Write the `/draft-claude-md` command

**Files:**
- Create: `plugins/org-repo-manifest/commands/draft-claude-md.md`

Thin wrapper. The command's job is to invoke the drafting skill.

- [ ] **Step 1: Create the command**

```bash
mkdir -p plugins/org-repo-manifest/commands
```

Write `plugins/org-repo-manifest/commands/draft-claude-md.md`:

```markdown
---
description: Draft a new CLAUDE.md for the current repo, interactively. Detects build stack, auto-fills the Commands section, then conversationally prompts for Purpose, Features, Architecture, Gotchas, and Conventions selection. Writes CLAUDE.md at the repo root on accept.
---

I'm invoking the `claude-md-drafting` skill to draft a CLAUDE.md for the current working directory.

## Canonical conventions reference (embedded for the skill)

@${CLAUDE_PLUGIN_ROOT}/templates/conventions.md

## CLAUDE.md skeleton template (embedded for the skill)

@${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.template

## What happens next

The `claude-md-drafting` skill will:
1. Detect the build stack (Node, JVM, Python, etc.) by Globbing for manifest files.
2. Auto-fill the Commands section from those build files.
3. Prompt conversationally for Purpose, Features, Architecture, Gotchas.
4. Present the canonical conventions list (embedded above) and ask which apply.
5. Substitute the chosen content into the skeleton template (embedded above) and show a preview.
6. On accept, write CLAUDE.md at the repo root.

If the repo already has a CLAUDE.md, confirm with me before overwriting. To audit an existing CLAUDE.md without rewriting it, use `/audit-claude-md` instead.
```

**Why the embeds:** the `@${CLAUDE_PLUGIN_ROOT}/...` syntax is documented for **command bodies** (the command preprocessor inlines file content). Agents and skills do NOT shell-expand `${CLAUDE_PLUGIN_ROOT}` and cannot reliably `Read` it. Embedding here puts the file content into the main conversation, where the auto-triggered drafting skill runs — the skill (unlike the auditor agent) shares this conversation, so it sees the inlined content directly. No further paste step is required for the drafter; see Task 10 for the auditor's additional paste-into-agent-prompt step.

- [ ] **Step 2: Verify**

Run: `head -5 plugins/org-repo-manifest/commands/draft-claude-md.md`
Expected: starts with `---`, has `description:` field, then content.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/commands/draft-claude-md.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add /draft-claude-md command

Thin wrapper that invokes the claude-md-drafting skill.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Write the `/audit-claude-md` command

**Files:**
- Create: `plugins/org-repo-manifest/commands/audit-claude-md.md`

This command dispatches the auditor agent, renders the report in the main context, and walks the user through accepting/rejecting each suggested section replacement.

- [ ] **Step 1: Create the command**

Write `plugins/org-repo-manifest/commands/audit-claude-md.md`:

```markdown
---
description: Audit the current repo's CLAUDE.md against the org rubric. Dispatches the claude-md-auditor agent (read-only), renders per-criterion A-F grades and findings, and walks through suggested section replacements one at a time. Audit itself never writes files; only user-accepted replacements touch CLAUDE.md.
---

Audit the CLAUDE.md at the current repo's root.

The two reference files below are inlined into THIS command's body via `@${CLAUDE_PLUGIN_ROOT}/...`. They will land in the **main** conversation. The auditor agent runs in **isolated context** and will not see this conversation — so Step 2 below explicitly pastes both blocks into the agent's prompt parameter. Do not assume the agent inherits them; it doesn't.

## Rubric (inlined here; will be pasted into agent prompt)

@${CLAUDE_PLUGIN_ROOT}/rubrics/claude-md.md

## Canonical conventions reference (inlined here; will be pasted into agent prompt)

@${CLAUDE_PLUGIN_ROOT}/templates/conventions.md

## Steps

1. **Verify CLAUDE.md exists.** If not, tell the user and suggest `/draft-claude-md` to bootstrap one. Stop.

2. **Dispatch the auditor with the references pasted into its prompt.** Use the Agent tool with `subagent_type: "claude-md-auditor"`. Construct the `prompt` parameter by concatenating, in this order:
   - A one-line task statement: `Audit the CLAUDE.md at <absolute-repo-path>.`
   - The literal heading `## Rubric` on its own line, then the full verbatim text of the rubric section inlined above (everything between the `## Rubric (...)` heading and the `## Canonical conventions reference (...)` heading in this command body).
   - The literal heading `## Canonical conventions` on its own line, then the full verbatim text of the conventions section inlined above.

   The agent runs in isolated context. If you do not paste this text into its prompt, the agent has no rubric and no conventions baseline. Referencing "above" does not work across the Agent boundary — the agent does not see this conversation.

3. **Render the report.** Show the agent's full report to the user verbatim — grades table, summary metric, N/A list, findings, suggested replacements.

4. **Walk through replacements one at a time.** For each suggested replacement returned by the agent:
   - Show the section name and the proposed new text.
   - Ask via AskUserQuestion (2 options: "Apply" / "Skip").
   - On Apply: replace the section in CLAUDE.md between its `## SectionName` header and the next `## ` header. Preserve content outside the section. If the headers cannot be located (e.g., the section is missing entirely), surface the failure, print the suggested text, and instruct the user to apply manually.
   - On Skip: continue to the next replacement.

5. **Summarize.** After the walk, report which sections were updated and which were skipped.

## Constraints

- The audit step itself is read-only. The auditor agent has only Read, Glob, Grep.
- Replacements are full-section. Do not attempt line-diff application.
- Convention-drift findings are advisory. Do not pressure the user to accept them — they're expected to include false positives by construction.
- If the auditor times out or errors, surface the error to the user with the exact failure message. Do not silently retry.
- Do not summarize, paraphrase, or truncate the rubric/conventions when constructing the agent prompt — paste them verbatim.
```

**Why the embed-then-paste:** the `@${CLAUDE_PLUGIN_ROOT}/...` syntax is documented for **command bodies**, where the preprocessor inlines file content into the main conversation. The auditor is an isolated-context subagent; it does NOT inherit the main conversation. It only sees the `prompt` parameter the dispatcher hands the Agent tool. So the command must do BOTH halves: (a) use `@${CLAUDE_PLUGIN_ROOT}/...` to inline the file into the command body (so the dispatching model has the text to copy), and (b) explicitly instruct the dispatcher to paste that text into the agent's prompt. (a) without (b) is the bug review2 caught — the embed reaches main, never the agent.

- [ ] **Step 2: Verify the command file**

Run: `grep -c "claude-md-auditor" plugins/org-repo-manifest/commands/audit-claude-md.md`
Expected: at least 1.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/commands/audit-claude-md.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add /audit-claude-md command

Dispatches the claude-md-auditor agent, renders the report, and walks
through suggested section replacements one at a time. Audit itself is
read-only; only user-accepted replacements touch CLAUDE.md.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Build auditor eval fixtures (5 defect cases)

**Files:**
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section/CLAUDE.md`
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/CLAUDE.md` (+ `src/` stub)
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/vague-features/CLAUDE.md`
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/oversized/CLAUDE.md`
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/conventions-drift/CLAUDE.md`

Each fixture is a minimal "repo" — just enough structure that the auditor has something to read against.

- [ ] **Step 1: Create fixture directories**

```bash
mkdir -p plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/{missing-section,stale-architecture,vague-features,oversized,conventions-drift}
```

- [ ] **Step 2: Write the `missing-section` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section/CLAUDE.md`:

```markdown
# tiny-service

## Purpose
A minimal HTTP service for the auth team.

## Features
- POST /healthz — returns 200
- POST /metrics — Prometheus scrape endpoint

## Architecture
Single-file Node Express app, `src/server.js`. No DB.

## Gotchas
- Port comes from `PORT` env var only. Don't hardcode.

## Conventions
- Logs JSON, correlation IDs from `X-Request-Id` headers.

## Reference
See `docs/` (none yet).
```

Note: no `## Commands` section. Defect is structural.

Also create a `package.json` so the auditor can detect the stack:

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section/package.json`:

```json
{
  "name": "tiny-service",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "start": "node src/server.js"
  }
}
```

- [ ] **Step 3: Write the `stale-architecture` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/CLAUDE.md`:

```markdown
# orders

## Purpose
Owns order lifecycle: create, update, cancel, fulfillment notifications.

## Features
- POST /orders
- PATCH /orders/{id}
- DELETE /orders/{id}
- GET /orders/{id}/events

## Architecture
Flask HTTP server, entry point `app.py`. SQLite via raw SQL. Background worker is a thread spawned at startup.

## Commands
```bash
pip install -r requirements.txt
pytest
python app.py
```

## Gotchas
- SQLite locks on writes; serialize writes via the worker thread.

## Conventions
- Logs JSON. Errors raise typed exceptions.

## Reference
See `docs/api/` for the OpenAPI spec.
```

The Architecture says Flask + SQLite. The actual stack will say otherwise — create a `pyproject.toml` describing FastAPI + Postgres so there's drift:

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/pyproject.toml`:

```toml
[project]
name = "orders"
version = "1.0.0"
dependencies = [
  "fastapi>=0.100",
  "uvicorn",
  "sqlalchemy>=2.0",
  "psycopg2-binary",
  "alembic"
]
```

Add a stub source file so the architecture description is verifiably wrong:

```bash
mkdir -p plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/src
```

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/src/main.py`:

```python
from fastapi import FastAPI
from sqlalchemy.orm import Session

app = FastAPI()

@app.post("/orders")
def create_order(): ...
```

- [ ] **Step 4: Write the `vague-features` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/vague-features/CLAUDE.md`:

```markdown
# payments

## Purpose
Handles payment-related operations for the platform.

## Features
- Various utilities for payment processing
- Helper functions for amount calculations
- Some integration logic
- Other stuff

## Architecture
Node Express app. Entry point in `src/`.

## Commands
```bash
npm install
npm test
npm start
```

## Gotchas
- Don't run two instances at once.

## Conventions
- Use the shared logger.

## Reference
See README.md.
```

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/vague-features/package.json`:

```json
{
  "name": "payments",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "start": "node src/index.js"
  }
}
```

- [ ] **Step 5: Write the `oversized` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/oversized/CLAUDE.md` — a file that is well over 150 lines through padding (repeat 20 verbose feature bullets, 30 verbose gotchas, and a multi-paragraph Architecture):

```markdown
# bloated-service

## Purpose
This service handles a wide range of responsibilities including but not limited to authentication, authorization, session management, audit logging, rate limiting, and several other cross-cutting concerns that the platform team has consolidated here over the years. It is the primary entry point for several upstream callers and integrates with many downstream systems via both synchronous HTTP and asynchronous messaging patterns.

## Features
- POST /v1/auth — authenticate
- POST /v1/auth/refresh — refresh tokens
- POST /v1/auth/revoke — revoke tokens
- GET /v1/userinfo — get user profile
- POST /v1/sessions — create session
- GET /v1/sessions/{id} — fetch session
- DELETE /v1/sessions/{id} — end session
- POST /v1/audit/log — log audit event
- GET /v1/audit/events — query audit events
- POST /v1/permissions/grant — grant permission
- POST /v1/permissions/revoke — revoke permission
- GET /v1/permissions/check — check permission
- POST /v1/groups — create group
- PATCH /v1/groups/{id} — update group
- DELETE /v1/groups/{id} — delete group
- GET /v1/groups/{id}/members — list members
- POST /v1/groups/{id}/members — add member
- DELETE /v1/groups/{id}/members/{userId} — remove member
- POST /v1/rate-limit/check — check rate limit
- POST /v1/rate-limit/reset — reset rate limit counter

## Architecture
The service follows a standard layered architecture pattern with a presentation layer, a business logic layer, and a data access layer. The presentation layer is implemented using the FastAPI framework with Pydantic models for request/response validation. The business logic layer contains all the domain rules and orchestrates calls between the various subsystems. The data access layer uses SQLAlchemy ORM with PostgreSQL as the primary datastore, Redis for caching and rate limit counters, and Kafka for emitting audit events to the downstream pipeline. The service is deployed as a set of replicas behind a load balancer, with horizontal autoscaling driven by CPU and request-rate metrics. Background workers run as separate processes managed by Supervisor.

## Commands
```bash
poetry install
poetry run pytest
poetry run uvicorn app.main:app --reload
```

## Gotchas
- The session table grows unbounded; we have a cleanup job that runs nightly
- Rate limit counters in Redis are eventually consistent across replicas
- Audit log writes are async; there is a small window where they can be lost
- Group membership has a cache with a 60 second TTL
- The permission check endpoint has a fast path that skips the DB if the cache hits
- Tokens are ECDSA-signed; key rotation happens weekly
- Refresh tokens are single-use; rotation is atomic via a Postgres advisory lock
- User deletion is cascaded via Kafka events; we listen for `user-deleted`
- The audit pipeline owner is a different team; coordinate before changing event schemas
- Settings live in env vars; required vars fail fast at startup
- Logs are JSON; correlation IDs come from X-Request-Id headers
- Don't put PII in logs; use the redaction helper
- The /metrics endpoint is exposed on port 9090, not the main port
- Health checks use /healthz; readiness uses /readyz
- The service depends on user-service for /userinfo enrichment
- If user-service is down, /userinfo falls back to claims-only
- Don't use the deprecated /v0 endpoints; they're scheduled for removal
- The Kafka consumer is at-least-once; idempotency is the responsibility of consumers
- We use semantic versioning for the API; breaking changes bump the major
- The deployment config lives in a sibling repo (deploys-platform)

## Conventions
- Structured JSON logging only
- Correlation IDs propagated via X-Request-Id
- Typed errors at boundaries
- Files in kebab-case
- Functions verb-first
- Tests next to source
- No DB mocking — use real Postgres via docker-compose
- Config from env vars only
- Secrets from secret manager
- REST: nouns in URLs, verbs in methods
- Error responses include error.code and error.message
- Versioning in the URL path
- Pagination is cursor-based

## Reference
See docs/ for ADRs, runbooks, and the OpenAPI spec.
```

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/oversized/pyproject.toml`:

```toml
[project]
name = "bloated-service"
version = "1.0.0"
```

- [ ] **Step 6: Write the `conventions-drift` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/conventions-drift/CLAUDE.md`:

```markdown
# legacy-service

## Purpose
Receives webhook callbacks from upstream partners and forwards them to the internal event bus.

## Features
- POST /webhooks/{partner} — accepts a partner-specific payload, validates signature
- GET /webhooks/recent — returns the last 100 received webhooks for debugging
- Emits `webhook-received` events to Kafka

## Architecture
Node Express server, entry point `src/server.js`. Postgres for the recent-webhooks table.

## Commands
```bash
npm install
npm test
npm start
```

## Gotchas
- Some partners send duplicate webhooks; dedupe by signature within 5 minutes.

## Conventions
- We use plain console.log for everything because it's faster.
- No correlation IDs; partners don't propagate them anyway.
- Catch all exceptions at the top level and log them.
- File names match the partner: `partnerA.js`, not kebab-case.
- Mock the DB in tests; we don't need a real Postgres.

## Reference
See README for partner-specific setup.
```

Defect: conventions section actively contradicts canonical conventions (uses `console.log`, no correlation IDs, catch-all, no kebab-case, mocks DB).

Write `plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/conventions-drift/package.json`:

```json
{
  "name": "legacy-service",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "start": "node src/server.js"
  }
}
```

- [ ] **Step 7: Verify all fixtures**

Run: `find plugins/org-repo-manifest/evals/claude-md-auditor/fixtures -type f | sort`
Expected (at minimum):
```
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/conventions-drift/CLAUDE.md
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/conventions-drift/package.json
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section/CLAUDE.md
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section/package.json
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/oversized/CLAUDE.md
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/oversized/pyproject.toml
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/CLAUDE.md
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/pyproject.toml
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/stale-architecture/src/main.py
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/vague-features/CLAUDE.md
plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/vague-features/package.json
```

- [ ] **Step 8: Commit**

```bash
git add plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add auditor eval fixtures (5 defect cases)

missing-section, stale-architecture, vague-features, oversized,
conventions-drift. Each fixture is a minimal repo with a planted
defect for the auditor to detect.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Build auditor evals.json

**Files:**
- Create: `plugins/org-repo-manifest/evals/claude-md-auditor/evals.json`

Machine-readable assertion spec for each fixture. In v1, this is the spec; running is manual (Task 15 documents the procedure).

- [ ] **Step 1: Create evals.json**

Write `plugins/org-repo-manifest/evals/claude-md-auditor/evals.json`:

```json
{
  "suite": "claude-md-auditor",
  "version": "0.1.0",
  "description": "Assertions for the claude-md-auditor agent against fixtures with planted defects. Run manually in v1: invoke /audit-claude-md against each fixture, then check the report against the assertions below.",
  "fixtures": [
    {
      "id": "missing-section",
      "path": "fixtures/missing-section/",
      "defect": "Commands section is missing from CLAUDE.md",
      "hard_assertions": {
        "criterion_max_grade": {
          "Commands & workflows": "C",
          "Actionability": "C"
        },
        "must_return_replacement_for_sections": []
      },
      "soft_check_findings_substrings": [
        "Commands",
        "missing"
      ]
    },
    {
      "id": "stale-architecture",
      "path": "fixtures/stale-architecture/",
      "defect": "Architecture section says Flask+SQLite; pyproject.toml and src/main.py show FastAPI+Postgres",
      "hard_assertions": {
        "criterion_max_grade": {
          "Currency": "C",
          "Architecture clarity": "C"
        },
        "must_return_replacement_for_sections": ["Architecture"],
        "currency_finding_must_name_subcause": "repo drift"
      },
      "soft_check_findings_substrings": [
        "Architecture",
        "stale"
      ]
    },
    {
      "id": "vague-features",
      "path": "fixtures/vague-features/",
      "defect": "Features section is generic and non-specific (\"various utilities\", \"other stuff\")",
      "hard_assertions": {
        "criterion_max_grade": {
          "Purpose & Features clarity": "C"
        },
        "must_return_replacement_for_sections": ["Features"]
      },
      "soft_check_findings_substrings": [
        "Features",
        "vague"
      ]
    },
    {
      "id": "oversized",
      "path": "fixtures/oversized/",
      "defect": "CLAUDE.md is under the 150-line cap but has poor signal-to-noise: run-on Purpose paragraph, multi-paragraph Architecture buzzword soup, 20 padded gotcha bullets, verbose Conventions prose. Conciseness should tank on signal-to-noise even though the line cap is technically respected.",
      "hard_assertions": {
        "criterion_max_grade": {
          "Conciseness": "C"
        },
        "must_return_replacement_for_sections": []
      },
      "soft_check_findings_substrings": [
        "signal",
        "verbose"
      ]
    },
    {
      "id": "conventions-drift",
      "path": "fixtures/conventions-drift/",
      "defect": "Conventions section actively contradicts templates/conventions.md (uses console.log, no correlation IDs, catch-all)",
      "hard_assertions": {
        "criterion_max_grade": {
          "Currency": "C"
        },
        "must_return_replacement_for_sections": ["Conventions"],
        "currency_finding_must_name_subcause": "convention drift"
      },
      "soft_check_findings_substrings": [
        "Conventions",
        "drift"
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -c "import json; d=json.load(open('plugins/org-repo-manifest/evals/claude-md-auditor/evals.json')); assert len(d['fixtures'])==5; print('OK', len(d['fixtures']), 'fixtures')"`
Expected: `OK 5 fixtures`.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/evals/claude-md-auditor/evals.json
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add auditor evals.json

Assertion spec for each of the 5 auditor fixtures. Hard assertions
(criterion grade, section replacements, currency sub-cause) and a
soft substring check on findings. Run manually in v1.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Build drafter eval fixtures (3 stacks)

**Files:**
- Create: `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/` (package.json + src/)
- Create: `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/` (pom.xml + src/)
- Create: `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/` (package.json + src/)
- Each fixture has an `answers.txt` describing the user inputs to provide for the manual eval run.

- [ ] **Step 1: Create fixture directories**

```bash
mkdir -p plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/src
mkdir -p plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/src/main/java/com/example
mkdir -p plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/src
```

- [ ] **Step 2: Write the `node-service` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/package.json`:

```json
{
  "name": "notifier",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "build": "tsc",
    "start": "node dist/server.js",
    "dev": "ts-node src/server.ts"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/src/server.ts`:

```typescript
import express from "express";
const app = express();
app.post("/notify", (_req, res) => res.json({ ok: true }));
app.listen(3000);
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/answers.txt`:

```
Purpose: Receives notification requests from upstream services and dispatches them to the appropriate channel (email/SMS/push). Owns the dispatch retry policy.
Features:
- POST /notify — accept a notification payload and route to channel
- Subscribes to user-preference-changed events to update routing rules
- Exposes /healthz and /metrics for probes
Architecture (confirm/edit): Express HTTP server, src/server.ts. No DB in v1; routing rules in memory.
Gotchas:
- Retry policy is exponential; do not stack policies in the routing rule
- Adjacent: user-preferences-service owns the rules; we read-only
Conventions: 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 14, 15, 17, 18, 21, 22
```

- [ ] **Step 3: Write the `spring-boot` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/pom.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>ledger</artifactId>
  <version>1.0.0</version>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
  </parent>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
  </dependencies>
</project>
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/src/main/java/com/example/LedgerApplication.java`:

```java
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class LedgerApplication {
    public static void main(String[] args) {
        SpringApplication.run(LedgerApplication.class, args);
    }
}
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/answers.txt`:

```
Purpose: Maintains the double-entry ledger for internal money movements. Source of truth for account balances and the audit trail.
Features:
- POST /v1/transactions — record a transfer
- GET /v1/accounts/{id}/balance — current balance
- GET /v1/accounts/{id}/history — paginated history
- Nightly job reconciles with the external settlement file
Architecture (confirm/edit): Spring Boot, entry com.example.LedgerApplication. Postgres via JPA. Scheduled jobs via @Scheduled.
Gotchas:
- Balances are materialized from the events table; rebuild via /admin/rebuild
- Adjacent: settlement-service is read-only consumer of our history
Conventions: 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 14, 15, 17, 18, 19, 21, 22, 23
```

- [ ] **Step 4: Write the `react-mfe` fixture**

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/package.json`:

```json
{
  "name": "checkout-mfe",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "build": "webpack --mode=production",
    "start": "webpack serve --mode=development",
    "lint": "eslint src/"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/src/index.tsx`:

```tsx
import React from "react";
import { createRoot } from "react-dom/client";
const App = () => <div>Checkout</div>;
createRoot(document.getElementById("root")!).render(<App />);
```

Write `plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/answers.txt`:

```
Purpose: Checkout micro-frontend embedded by the host shell. Owns the cart-review, address-entry, and payment-method-pick steps.
Features:
- CartReview component — shows line items, totals, discounts
- AddressForm component — collects/validates shipping address
- PaymentPicker component — wraps the payment-sdk iframe
- Emits checkout-completed event on success
Architecture (confirm/edit): React 18 SPA bundled by webpack, entry src/index.tsx. State local to each step; no shared store. Communication with host via window.postMessage.
Gotchas:
- The host shell catches our errors; do not throw across the boundary, post error events instead
- Adjacent: payment-sdk is loaded by host; we only render its iframe
Conventions: 1, 4, 9, 10, 11, 13, 15, 24, 25, 26, 27
```

- [ ] **Step 5: Verify all fixtures**

Run: `find plugins/org-repo-manifest/evals/claude-md-drafting/fixtures -type f | sort`
Expected:
```
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/answers.txt
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/package.json
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/src/server.ts
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/answers.txt
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/package.json
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/react-mfe/src/index.tsx
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/answers.txt
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/pom.xml
plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/spring-boot/src/main/java/com/example/LedgerApplication.java
```

- [ ] **Step 6: Commit**

```bash
git add plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add drafter eval fixtures (3 stacks)

node-service, spring-boot, react-mfe. Each fixture is a minimal repo
with package/pom file, stub source, and an answers.txt describing the
user inputs to provide during a manual eval run.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Build drafter evals.json

**Files:**
- Create: `plugins/org-repo-manifest/evals/claude-md-drafting/evals.json`

- [ ] **Step 1: Create the eval spec**

Write `plugins/org-repo-manifest/evals/claude-md-drafting/evals.json`:

```json
{
  "suite": "claude-md-drafting",
  "version": "0.1.0",
  "description": "Assertions for the claude-md-drafting skill against fixtures of realistic repos. Run manually in v1: invoke /draft-claude-md in each fixture directory, feed the answers.txt inputs when prompted, then check the produced CLAUDE.md against the assertions below.",
  "fixtures": [
    {
      "id": "node-service",
      "path": "fixtures/node-service/",
      "stack": "Node + Express + TypeScript",
      "hard_assertions": {
        "max_lines": 150,
        "required_section_headers_exact": [
          "## Purpose",
          "## Features",
          "## Architecture",
          "## Commands",
          "## Gotchas",
          "## Conventions",
          "## Reference"
        ],
        "commands_section_must_contain": [
          "npm install",
          "npm test",
          "npm run build",
          "npm start"
        ],
        "conventions_section_non_empty": true,
        "conventions_section_must_reference_at_least_n_canonical_rules": 5
      }
    },
    {
      "id": "spring-boot",
      "path": "fixtures/spring-boot/",
      "stack": "JVM + Spring Boot + Maven",
      "hard_assertions": {
        "max_lines": 150,
        "required_section_headers_exact": [
          "## Purpose",
          "## Features",
          "## Architecture",
          "## Commands",
          "## Gotchas",
          "## Conventions",
          "## Reference"
        ],
        "commands_section_must_contain_regex": [
          "(^|\\s)mvn(\\s|$)"
        ],
        "commands_section_must_not_contain": [
          "mvnw"
        ],
        "conventions_section_non_empty": true,
        "conventions_section_must_reference_at_least_n_canonical_rules": 5
      }
    },
    {
      "id": "react-mfe",
      "path": "fixtures/react-mfe/",
      "stack": "React 18 + webpack",
      "hard_assertions": {
        "max_lines": 150,
        "required_section_headers_exact": [
          "## Purpose",
          "## Features",
          "## Architecture",
          "## Commands",
          "## Gotchas",
          "## Conventions",
          "## Reference"
        ],
        "commands_section_must_contain": [
          "npm install",
          "npm test",
          "webpack"
        ],
        "conventions_section_non_empty": true,
        "conventions_section_must_reference_at_least_n_canonical_rules": 5,
        "conventions_must_include_frontend_rule_topics": [
          "function components",
          "useEffect"
        ]
      }
    }
  ]
}
```

- [ ] **Step 2: Validate**

Run: `python3 -c "import json; d=json.load(open('plugins/org-repo-manifest/evals/claude-md-drafting/evals.json')); assert len(d['fixtures'])==3; print('OK', len(d['fixtures']), 'fixtures')"`
Expected: `OK 3 fixtures`.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/evals/claude-md-drafting/evals.json
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add drafter evals.json

Assertion spec for each of the 3 drafter fixtures: max line count,
required exact section headers, stack-specific Commands must-contain,
Conventions non-empty + reference at least N canonical rules.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Write evals README (manual run procedure)

**Files:**
- Create: `plugins/org-repo-manifest/evals/README.md`

In v1, evals are run manually. This README documents the procedure.

- [ ] **Step 1: Create the README**

Write `plugins/org-repo-manifest/evals/README.md`:

````markdown
# org-repo-manifest evals

Two suites, both run manually in v1. Automation is deferred to a later release.

## Prerequisites — install the plugin first

The `/draft-claude-md` and `/audit-claude-md` commands only exist when the plugin is installed. Before running any eval:

```bash
# 1. Add the marketplace (skip if already added).
claude plugin marketplace add /path/to/avi-claude-forge

# 2. Install the plugin.
claude plugin install org-repo-manifest

# 3. Confirm the commands are visible.
claude /help | grep -E 'draft-claude-md|audit-claude-md'
```

When iterating on plugin source, re-install (or restart Claude Code) so the latest agent/skill/command files are picked up.

## Auditor evals (`claude-md-auditor/`)

Five fixtures, each a minimal repo with a planted defect. The auditor agent is invoked against the fixture; the produced report is checked against `evals.json`.

### Procedure

For each fixture in `claude-md-auditor/fixtures/`:

1. `cd` into the fixture directory (so the auditor sees its CLAUDE.md and stack files).
2. Invoke `/audit-claude-md` in a fresh Claude Code session.
3. Capture the auditor's full report.
4. Open `claude-md-auditor/evals.json` and find the matching fixture entry.
5. Verify each hard assertion:
   - `criterion_max_grade`: the named criterion must be graded at the listed letter or worse.
   - `must_return_replacement_for_sections`: each named section must appear in the suggested replacements block.
   - `currency_finding_must_name_subcause` (when present): the Currency finding must contain the named sub-cause string (`repo drift` or `convention drift`).
6. Log the soft check informationally: does the findings list mention the substring hints? Don't fail the suite on this.

A fixture passes if all hard assertions hold. A suite passes if all 5 fixtures pass.

### Baseline comparison

Before any prompt change to the auditor agent, run all 5 fixtures and record the produced reports under `claude-md-auditor/baselines/<date>/<fixture-id>.md`. After the change, re-run and diff against the baseline. Investigate any regressions.

## Drafter evals (`claude-md-drafting/`)

Three fixtures, one per stack (Node, Spring Boot, React MFE). Each fixture is a minimal repo with a stack manifest and a stub source file, plus an `answers.txt` containing the user inputs to provide during the interactive Q&A.

### Procedure

For each fixture in `claude-md-drafting/fixtures/`:

1. `cd` into the fixture directory.
2. Read `answers.txt` and have it ready to paste into the prompts.
3. Invoke `/draft-claude-md` in a fresh Claude Code session.
4. Answer each prompt with the corresponding section from `answers.txt`.
5. Accept the draft when prompted.
6. Open the produced `CLAUDE.md` and check each hard assertion in `claude-md-drafting/evals.json`:
   - `max_lines`: `wc -l CLAUDE.md` ≤ value.
   - `required_section_headers_exact`: each header must appear verbatim.
   - `commands_section_must_contain`: each string must appear in the Commands section.
   - `conventions_section_non_empty`: the Conventions section has content.
   - `conventions_section_must_reference_at_least_n_canonical_rules`: count how many rules from `templates/conventions.md` are referenced (by rule text or topic).
   - `conventions_must_include_frontend_rule_topics` (react-mfe only): the named topics must appear.
7. Restore the fixture to its pre-run state (`git restore .` or delete the produced CLAUDE.md) before moving on.

A fixture passes if all hard assertions hold. A suite passes if all 3 fixtures pass.

### Why manual

The drafter is interactive (Q&A in main context); automating it requires a CLI driver that can stream answers into Claude Code. The auditor could be automated, but for v1 we keep both suites manual for consistency and to keep the plugin shippable without a runner script.

## Automating later

When a runner script is built (post-Part 1), it should:
- Drive the agent/skill via `claude --print` or a similar headless mode.
- Parse the produced report / CLAUDE.md.
- Check each `hard_assertion` programmatically.
- Emit a pass/fail summary and exit non-zero on any failure.
````

- [ ] **Step 2: Verify**

Run: `wc -l plugins/org-repo-manifest/evals/README.md`
Expected: line count > 30.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/evals/README.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: document the manual eval run procedure

v1 evals are run manually. README walks tech leads through each
suite's procedure and the baseline-comparison practice.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Write the plugin README

**Files:**
- Create: `plugins/org-repo-manifest/README.md`

The plugin's outward-facing README documents purpose, commands, and the sibling-plugin lifecycle pattern (per spec §9).

- [ ] **Step 1: Create the README**

Write `plugins/org-repo-manifest/README.md`:

````markdown
# org-repo-manifest

Draft and audit CLAUDE.md files for enterprise microservice and MFE repos against an org rubric.

## What it does

- **`/draft-claude-md`** — interactively bootstraps a CLAUDE.md for the current repo. Detects build stack, auto-fills Commands, and conversationally prompts for Purpose, Features, Architecture, Gotchas, and Conventions selection.
- **`/audit-claude-md`** — scores the current repo's CLAUDE.md against a 7-criterion rubric (A–F per criterion). Returns findings and full-section replacements. Read-only — only user-confirmed replacements touch the file.

## Standard CLAUDE.md shape

A compliant CLAUDE.md has exactly these 7 sections, in this order, capped at 150 lines:

1. **Purpose** — positive definition of what this repo IS.
2. **Features** — what the service does, bullet form, specific.
3. **Architecture** — entry points and major boundaries inline.
4. **Commands** — copy-pasteable build/test/run/deploy.
5. **Gotchas** — repo-wide footguns and sibling-repo boundaries.
6. **Conventions** — curated subset of the canonical org conventions.
7. **Reference** — flat index pointing to `docs/`.

See `templates/CLAUDE.md.template` for the skeleton and `skills/claude-md-drafting/examples/good-claude-md.md` for a worked example.

## Scoring (rubric)

Seven criteria, each graded A–F. No single overall letter grade; the audit reports per-criterion grades plus an **"X of N criteria below B"** summary. N/A criteria (e.g., when the canonical conventions template is unreachable) are excluded from both the report set and the count.

Full rubric at `rubrics/claude-md.md`.

## Conventions

The plugin ships `templates/conventions.md` — the canonical org conventions across stacks. The drafting skill presents this list to the user and asks which rules apply to the current repo. The auditor uses this file as the baseline for the Currency criterion's convention-drift sub-cause.

The Conventions section in each repo's CLAUDE.md is a **curated summary** — not a verbatim copy. Convention-drift findings are advisory by construction (the auditor can't distinguish "deliberately scoped out" from "forgotten / went stale").

## Evals

Two suites under `evals/`:

- `claude-md-drafting/` — 3 fixtures (Node, Spring Boot, React MFE) verifying produced CLAUDE.md is ≤150 lines, contains all 7 sections, has executable Commands matching the detected stack, and references at least N canonical rules.
- `claude-md-auditor/` — 5 fixtures with planted defects (missing section, stale architecture, vague features, oversized, conventions drift) verifying the auditor scores the right criterion below B and proposes the right replacement.

Both suites are run manually in v1. See `evals/README.md` for the procedure.

## Architecture (component types)

| Component | Type | Why |
|---|---|---|
| `/draft-claude-md` | command | User entry point. Thin wrapper. |
| `/audit-claude-md` | command | User entry point. Dispatches the agent. |
| `claude-md-drafting` | skill | Interactive Q&A; main-context. |
| `claude-md-auditor` | agent | Isolated context for heavy reads; returns concise report. |

Drafting is a skill because Q&A belongs in the visible main context. Auditing is an agent because heavy file-reading deserves an isolated subprocess and a structured return.

## Lifecycle pattern (for sibling plugins)

This plugin establishes a pattern that future sibling plugins in this initiative — `org-repo-adrs`, `org-repo-runbooks`, `org-repo-glossary` — should follow:

```
<artifact-plugin>/
├── commands/        # draft + audit entry points
├── agents/          # autonomous auditor
├── skills/          # interactive drafter (with refs/ + examples/)
├── rubrics/         # scoring contract
├── templates/       # canonical artifact + org reference
└── evals/           # drafting + auditor suites
```

Each sibling plugin is self-contained. No cross-plugin dependencies. Share patterns, not code. Refactor to shared infrastructure only when a second plugin is concrete and the duplication is visible.

## Design spec

`docs/superpowers/specs/2026-06-07-org-repo-manifest-part1-claude-md-design.md` documents the design decisions and the four review rounds that produced it.
````

- [ ] **Step 2: Verify**

Run: `grep -E "^## " plugins/org-repo-manifest/README.md | wc -l`
Expected: at least 8 headings.

- [ ] **Step 3: Commit**

```bash
git add plugins/org-repo-manifest/README.md
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: add plugin README

Outward-facing docs: what the plugin does, the CLAUDE.md standard, the
rubric model, evals, the component-type architecture, and the lifecycle
pattern for sibling artifact plugins (ADRs, runbooks, glossary).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: Plugin validation + smoke tests (MANUAL — requires the user)

**Files:**
- No new files. Validation against the built plugin.

**Important — for the implementing subagent:** Steps 2 and 3 of this task are **manual user actions**. They require a fresh interactive Claude Code session and a human to answer prompts. The subagent executing this plan **cannot perform Steps 2 and 3**. Mark them as "pending user verification" and stop. Step 1 (plugin-validator) and Step 4 (push) are agent-executable.

**Honest note on verification scope:** the per-step `wc -l`, `grep -c`, and `json.load` checks earlier in this plan are **presence checks**, not behavior checks. They prove a file was written and parses. They do NOT prove the prompt produces the intended behavior. The only true behavior check is the smoke tests in this Task and the manual eval suites (see `evals/README.md`). The plugin is not "verified working" until those run successfully.

- [ ] **Step 1: Dispatch the plugin-validator agent**

Use the Agent tool with `subagent_type=plugin-dev:plugin-validator` and the prompt:

```
Validate the plugin at plugins/org-repo-manifest/. Check:
- plugin.json parses, has required fields (name, version, description, author, keywords).
- Marketplace entry exists in .claude-plugin/marketplace.json with matching name and version.
- All commands have valid frontmatter (description field).
- The agent has valid frontmatter (name, description, tools).
- The skill has SKILL.md with valid frontmatter (name, description).
- Each @${CLAUDE_PLUGIN_ROOT}/... reference in command bodies points to a file that exists in the plugin: rubrics/claude-md.md, templates/conventions.md, templates/CLAUDE.md.template.

Report any failures. Do not attempt to fix; just report.
```

Expected: report with no critical failures. If failures exist, fix them in-place (per the validator's report) and re-run.

- [ ] **Step 2 (USER): Install the plugin locally and run smoke test against drafter**

Tell the user: "Please run the drafter smoke test. Steps:

```bash
# 1. From the worktree root, make sure the local marketplace is enabled.
#    (If you already have avi-claude-forge added in claude settings, skip.)
claude plugin marketplace add /home/agent/work/avi-claude-forge

# 2. Enable the plugin.
claude plugin install org-repo-manifest

# 3. Smoke-test the drafter in an isolated copy of the node-service fixture.
cp -r /home/agent/work/avi-claude-forge/plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service /tmp/smoke-drafter
cd /tmp/smoke-drafter

# 4. In a fresh Claude Code session at /tmp/smoke-drafter, run:
#    /draft-claude-md
# 5. Answer each prompt using the corresponding section of
#    /home/agent/work/avi-claude-forge/plugins/org-repo-manifest/evals/claude-md-drafting/fixtures/node-service/answers.txt
# 6. Accept the draft when prompted.

# 7. Verify the produced CLAUDE.md:
wc -l CLAUDE.md                                                            # expect ≤ 150
grep -cE '^## (Purpose|Features|Architecture|Commands|Gotchas|Conventions|Reference)$' CLAUDE.md  # expect 7
grep -E 'npm (install|test|run build|start)' CLAUDE.md                     # expect matches
```

Tell me the results."

- [ ] **Step 3 (USER): Smoke test against auditor**

Tell the user: "Please run the auditor smoke test. Steps:

```bash
cp -r /home/agent/work/avi-claude-forge/plugins/org-repo-manifest/evals/claude-md-auditor/fixtures/missing-section /tmp/smoke-auditor
cd /tmp/smoke-auditor

# In a fresh Claude Code session at /tmp/smoke-auditor, run:
#   /audit-claude-md
# Capture the full report.
```

Verify the report:
- 'Commands & workflows' criterion graded C or worse
- 'Actionability' criterion graded C or worse
- Findings mention 'Commands' / 'missing'

Tell me the results."

- [ ] **Step 4: Post-smoke-test fixes (if needed)**

If Steps 1–3 surfaced fixes:

```bash
git add -A
git -c user.email=sepiaavi@gmail.com -c user.name=avijit90 -c commit.gpgsign=false commit -m "$(cat <<'EOF'
org-repo-manifest: post-smoke-test fixes

Address issues surfaced by plugin-validator and manual smoke tests
against the drafter (node-service) and auditor (missing-section)
fixtures.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

If no fixes were needed, no commit. The plugin is ready.

- [ ] **Step 5: Push the branch**

```bash
git push origin feature/org-repo-manifest-part1
```

Expected: push succeeds; remote branch updated.

---

## Self-review checklist (for the plan author)

Run these once after writing the plan, before handing off. If any fail, fix inline and move on.

- [ ] Each spec section maps to at least one task:
  - §3 (CLAUDE.md sections) → Tasks 4 (template), 6 (skill drafts them)
  - §4.1 (component types) → Tasks 5 (agent), 6 (skill), 9–10 (commands)
  - §5.1 (drafter flow) → Task 6 (SKILL.md)
  - §5.2 (auditor flow) → Tasks 5 (agent), 10 (command)
  - §6 (rubric) → Task 2
  - §7 (edge cases) → embedded in agent (Task 5) and skill (Task 6) prompts
  - §8 (evals) → Tasks 11–15
  - §9 (forward-compat) → Task 16 (README lifecycle section)
  - Templates → Tasks 3, 4
- [ ] No placeholders (`TODO`, "fill in", "implement appropriate"). Searched: no matches.
- [ ] Type consistency: section header names (`## Purpose`, `## Features`, etc.) are identical in the template (Task 4), the skill (Task 6), the agent (Task 5), the example (Task 8), and the rubric (Task 2). Verified.
- [ ] Path consistency: `@${CLAUDE_PLUGIN_ROOT}/rubrics/claude-md.md`, `@${CLAUDE_PLUGIN_ROOT}/templates/conventions.md`, `@${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.template` embedded into command bodies (Tasks 9, 10) — NOT referenced from agent (Task 5) or skill (Task 6) prose, which would not resolve. **This check verifies placement, not delivery.** Placement reaches the main conversation only; the auditor agent runs in isolated context and needs the additional paste-into-prompt step specified in Task 10 Step 2. Confirm that step is present verbatim; without it, the conventions-drift eval will fail by construction (auditor has no conventions baseline → Currency forced to N/A → fixture asserts Currency: C).
- [ ] No new dependencies added to repo root. Plugin is self-contained markdown + JSON.
