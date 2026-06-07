# Review (Round 2) — org-repo-manifest Part 1: CLAUDE.md Management

**Reviewer:** Claude (critical design review)
**Date:** 2026-06-07
**Reviewing:** `2026-06-07-org-repo-manifest-part1-claude-md-design.md` (revised after Round 1)
**Prior review:** `2026-06-07-org-repo-manifest-part1-claude-md-design-review.md`

---

## Verdict

The revision did the hard work and did it honestly — all four Round-1 material items are genuinely fixed, the reversals are documented in the appendix, and the external citation now checks out. Two new concerns remain, both introduced by the fixes themselves and both narrower than the Round-1 issues. Fix those two and this is buildable.

---

## Round-1 items — all resolved

1. **Conventions contradiction** — gone. Now a curated summary (≤30, flex), explicitly *not* a verbatim copy, with the trade-off (semantic drift detection) stated in §3 and the eval relaxed to "non-empty + references ≥1 rule." Consistent end-to-end.
2. **Audit-coverage gap** — closed with the new "Purpose & Features clarity" criterion (7 now), plus a "vague Features" defect fixture in the auditor evals.
3. **Oversold determinism** — §6 now states plainly: "Scoring is LLM semantic judgment. No bash-level deterministic diff is claimed." Honest.
4. **`/revise-claude-md` cut** — moved to a non-goal + §10 with a clear rationale.

Also fixed: dead rubric weights removed (worst-of model), auto-detection scoped to Commands only with an honesty note, full-section-replacement seam specified with a header-not-found failure path, line-budget arithmetic made honest (~100 content / 150 hard cap).

**Citation verified.** The `claude-md-improver` skill cited in §6 is real — `raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/claude-md-management/skills/claude-md-improver/SKILL.md` returns actual content, and it does use "commands/workflows" and "architecture clarity" criteria, matching what the spec adapted. Note it uses *weighted* scoring (relevant to concern A below).

---

## New concerns (introduced by the fixes)

### A. Worst-of grading will bottom out to F and stop being informative — material

§6: "Overall grade = worst-of (lowest letter across all criteria)."

Across **7 semantic criteria**, nearly every real CLAUDE.md will be weak on at least one — so almost everything grades D/F overall. A metric that returns F for most repos can't prioritize work or show improvement over time, which is the stated point of "audit at scale" (§1). The skill this adapts from uses *weighted* scoring precisely to produce a gradient; dropping weights for "harder to game" also throws away the gradient that makes an audit actionable and trackable.

Worst-of also has an unspecified interaction with §7: if `templates/conventions.md` is inaccessible, Currency is "not scored" — so what is the worst-of over a criterion set with a hole in it?

**Suggested fix:** keep per-criterion A–F letters as the primary, actionable output, and make the overall a gradient — e.g. "count of criteria below B," or a simple average — not worst-of. Define N/A handling explicitly (skip the criterion; don't let it dominate or void the overall).

### B. AskUserQuestion is the wrong tool for most of what §5.1 gathers — material

§5.1 / §4.1 lean on "AskUserQuestion in main context" to elicit Purpose, Features, Architecture, Gotchas, and Conventions edits. But AskUserQuestion presents 2–4 **fixed multiple-choice options** — it is built for either/or decisions, not free-form prose. You cannot pre-enumerate options for "what is this repo's purpose" or "list the features." Forcing prose through option-chips will be clumsy and an implementer following the spec literally will hit this wall.

**Suggested fix:** the drafting skill should use plain conversational prompting for the prose sections (Purpose, Features, Architecture, Gotchas), and reserve AskUserQuestion for the genuine discrete choices — which stack to document (the §7 multi-stack case) and accept/reject. Correct the wording in §5.1 and §4.1 so the tool is named only where it fits.

---

## Minor

- **Eval substring matching is brittle.** The auditor eval uses "substring match against expected finding." LLM phrasing varies run to run, so a substring check on free-text findings is fragile. Lean on the per-criterion grade assertion ("relevant criterion C or below") as the primary signal and treat the substring as a soft/secondary check.

---

## Bottom line

A and B are real but confined to §6 (grading model) and §5.1/§4.1 (tool choice) — a grading rethink and a tool-choice correction, not structural rework. Resolve those two and I'd call the spec buildable.
