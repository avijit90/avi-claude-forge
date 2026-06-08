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
