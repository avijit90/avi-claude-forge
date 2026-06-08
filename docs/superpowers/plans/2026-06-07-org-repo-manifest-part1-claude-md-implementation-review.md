# Review — org-repo-manifest Part 1: CLAUDE.md Implementation Plan

**Reviewer:** Claude (radical-candor review)
**Date:** 2026-06-07
**Reviewing:** `2026-06-07-org-repo-manifest-part1-claude-md-implementation.md`
**Verified against:** official `plugin-dev` docs (`${CLAUDE_PLUGIN_ROOT}` semantics), this repo's existing working skill (`principal-engineer-eval/style-evaluator`), and the plan's own fixtures/evals.

---

## Verdict

The *content* is high quality — the fixtures are well-built, the templates are sharp, the spec→task traceability checklist is real discipline. But the plan has an **inverted risk profile**: ~2,000 lines transcribe files it's confident about, and a few vague lines cover the three mechanisms that actually decide whether the plugin works. As written, **every checkbox can go green and the plugin can still be non-functional.** Two findings are potentially fatal; two are concrete bugs in the rubric/evals.

---

## Fatal-class issues

### 1. Verification is "files exist," not "it works"

~15 of the verification steps are `wc -l`, `grep -c`, or `json.load(...)`. They prove a file was written and parses. **None prove a prompt produces the intended behavior.** For a plugin whose entire substance is markdown prompts, "do the prompts drive the agent correctly" is the only risk that matters — and almost nothing checks it. The only behavioral checks are the Task 17 smoke tests, which (see #3) can't be run by the agent executing this plan. This is verification theater: 100% completion here is not evidence of a working plugin.

### 2. The audit flow bets on `${CLAUDE_PLUGIN_ROOT}` resolving via `Read` — unproven

The auditor agent (Task 5) and the skill (Task 6) instruct the model to `Read` `${CLAUDE_PLUGIN_ROOT}/rubrics/claude-md.md` and `.../templates/conventions.md`.

What the docs actually establish:
- `${CLAUDE_PLUGIN_ROOT}` is documented for **commands**, where it works via the `@file` embed and `!bash` execution syntax the harness preprocesses.
- This repo's own working skill (`style-evaluator`) references its bundled file via a **bare relative path** (`read references/schemas.md`), not the `${CLAUDE_PLUGIN_ROOT}/...` form.

The plan uses **neither proven pattern**. It puts a bare `${CLAUDE_PLUGIN_ROOT}/...` string in agent/skill *prose* and assumes the `Read` tool shell-expands it. `Read` does not do shell expansion, and a dispatched subagent may not have that env var set at all. **If it doesn't resolve, the auditor cannot load its own rubric or the conventions baseline — the audit is dead.** This is the riskiest assumption in the plan and it gets zero verification.

**Action:** spike it before building on it. If the agent can't `Read` the path, move the rubric/conventions into the **command** via `@${CLAUDE_PLUGIN_ROOT}/...` embed and pass them into the agent as text. This ripples into Tasks 5, 6, 9, 10 — far cheaper to learn now than after 17 commits.

### 3. No install step — smoke tests and manual evals can't run

Task 17 and the eval READMEs say "in a fresh Claude Code session at `/tmp/smoke-drafter`, run `/draft-claude-md`." Nothing in the plan installs/enables the local plugin from the marketplace, so in a fresh `/tmp` session **that command does not exist**. The smoke tests as written cannot pass. They also require a human feeding `answers.txt` into an interactive session, so the subagent executing this plan can't perform them anyway — Task 17 will be skipped or faked.

---

## Concrete bugs

### 4. "Conciseness" is mis-mapped to the missing-section case

Task 5: "Missing headers immediately tank **Conciseness** and Actionability." Task 12 asserts `missing-section` scores Conciseness ≤ C. Backwards — a file *missing* its Commands section is shorter and tighter, not less concise. This conflates "missing content" with "verbose content." Missing-Commands should tank "Commands & workflows" (it does) and ideally a **completeness** dimension the 7-criterion rubric doesn't have. As written, the eval encodes a category error and trains the auditor to grade absence and verbosity identically.

### 5. The spring-boot fixture's asserted command won't run

`feature-detection.md` and the eval both assume `./mvnw`. The `spring-boot` fixture ships only `pom.xml` — no `mvnw` wrapper, no `.mvn/`. `./mvnw` will fail there; the correct command is `mvn`. The drafter will emit a non-copy-pasteable command (violating the rubric's own bar) and the eval will **pass it anyway**. Either commit a wrapper to the fixture or assert `mvn`.

### 6. `Glob('**/*', limit=2)` to "map the top 2 levels" is wrong

In `section-guides.md`. `Glob` has no depth-limiting `limit=2` semantics; `**/*` matches all depths and a result `limit` caps count, not depth. Wrong instruction baked into a reference the skill follows for Architecture detection.

### 7. Command→skill is a soft trigger with no fallback

Task 9's command body is just "Invoke the `claude-md-drafting` skill," relying on description-match auto-trigger. Usually works, but there's no fallback and it's "verified" with `head -5` on the file. The smoke test needs to confirm the skill actually fires.

---

## Minor

- **Co-author trailer says "Claude Opus 4.7"** in all 17 commits; the house format here is `Claude Opus 4.8 (1M context)`. Wrong, repeated 17×.
- **17 micro-commits** for one cohesive feature is defensible for review, but several land content that can't be exercised until later tasks, so per-commit "done" is meaningless.

---

## What's good (credit where due)

- Planted-defect fixtures are well-designed and internally consistent — `answers.txt` rule numbers all fall within the 27 canonical rules; the conventions-drift fixture genuinely contradicts the baseline.
- The hard/soft assertion split in both `evals.json` files is the right call.
- The self-review traceability matrix mapping spec §§ → tasks is better discipline than most plans have.

---

## The one thing to do first

**Prove #2 with a throwaway spike** before executing any task: stand up `plugin.json` + the agent + the rubric, install the plugin locally, dispatch the auditor, and confirm it can `Read` the rubric via whatever path form you pick. That single experiment de-risks more than the other 16 tasks combined.
