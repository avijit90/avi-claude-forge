# Review (Round 4) — org-repo-manifest Part 1: CLAUDE.md Management

**Reviewer:** Claude (critical design review)
**Date:** 2026-06-07
**Reviewing:** `2026-06-07-org-repo-manifest-part1-claude-md-design.md` (revised after Rounds 1–3)
**Prior reviews:** `-review.md`, `-review2.md`, `-review3.md`

---

## Verdict

Four rounds in, the spec is essentially done. All Round-3 items are resolved. The Round-3 fix introduced exactly one new leftover inconsistency — the same class of bug as last round (a mechanism moved in the data-flow block but its prose summary not updated). That one-line fix is the only thing required before building.

---

## Round-3 items — resolved

- **§10 / §6 contradiction** — fixed. §10 now reads "Per-criterion A–F plus the 'X of N below B' summary is the v1 model; weighted scores, numeric grades, and explicit trend tracking are deferred." No more "worst-of." Consistent with §6.
- **Overloaded Currency criterion** — addressed. §156 now requires the finding to name the sub-cause ("repo drift: Architecture stale" vs "convention drift: Conventions misaligned"). Kept as one criterion but forces disambiguation in the finding — reasonable.
- **"Below B" denominator** — fixed. §159 now "X of N criteria graded below B — always reported with the denominator," with the N/A rationale spelled out.
- **AskUserQuestion 4-option cap** — addressed by moving convention-rule selection out of AskUserQuestion into conversational prose (§112–115), with the cap named as the reason.

---

## One new leftover (required fix)

### §123 contradicts §112–118 — stale "convention rule inclusion"

Convention-rule selection was moved *out* of AskUserQuestion and into the prose-prompt list. The data-flow block (§116–118) correctly lists only "stack disambiguation" and "accept/reject" under AskUserQuestion. But the "Tool choice discipline" note immediately below still reads:

> AskUserQuestion is reserved for genuine discrete choices: stack pick, **convention rule inclusion**, accept/reject.

"Convention rule inclusion" no longer belongs there — it is now prose-elicited. **Fix:** delete "convention rule inclusion" from §123.

This is the identical pattern to the §10 leftover caught in Round 3: the mechanism moved, the summary sentence didn't follow. Worth a habit note — when relocating a mechanism, grep the doc for its old name and update every mention, not just the primary block.

---

## One minor note (inherent trade-off, author's call)

A **curated Conventions summary will always differ from the canonical `templates/conventions.md` by design** — it omits rules that don't apply to this repo. So the Currency check ("does Conventions still align with the canonical file?") cannot cleanly distinguish "deliberately scoped out" from "forgotten/stale," and the auditor will produce some false-positive drift findings by construction.

This is partly covered already by the §7 "intentionally diverged → user rejects" row and the report-don't-enforce principle. Suggestion: add one sentence to §6 acknowledging that convention-drift findings are advisory and expected to include false positives, so reviewers don't treat them as authoritative. Not a blocker — it's the accepted cost of the summary approach, which is the correct approach.

---

## Bottom line

The §123 leftover is the only required fix and it is a one-line deletion. The curated-summary caveat is optional polish. **Ship it once §123 is corrected.**
