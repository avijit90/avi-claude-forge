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
