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
