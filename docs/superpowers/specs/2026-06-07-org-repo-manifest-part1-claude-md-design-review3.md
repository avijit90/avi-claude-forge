# Review (Round 3) — org-repo-manifest Part 1: CLAUDE.md Management

**Reviewer:** Claude (critical design review)
**Date:** 2026-06-07
**Reviewing:** `2026-06-07-org-repo-manifest-part1-claude-md-design.md` (revised after Rounds 1 & 2)
**Prior reviews:** `-review.md`, `-review2.md`

---

## Verdict

Both Round-2 concerns are resolved cleanly and the reversals are documented in the appendix. The spec is in polish territory. **One literal contradiction remains (§10 vs §6) and must be fixed for internal consistency; three minor design notes are judgment calls.** Fix the contradiction and this is buildable.

---

## Round-2 items — resolved

- **Worst-of grading** → dropped entirely. §6 reports per-criterion A–F as the primary output plus a "count of criteria below B" (0–7 gradient), with N/A explicitly excluded from the count and listed separately under "Not scored, with reason." The empty-CLAUDE.md edge case (§7) was updated to match ("All criteria graded F"). Reversal documented in the appendix.
- **AskUserQuestion misuse** → §5.1 now splits interaction into conversational prose prompts (Purpose/Features/Architecture/Gotchas) vs AskUserQuestion for discrete choices only, with a "Tool choice discipline" note; §4.1 updated to match.
- **Eval substring brittleness** → §8 now separates hard assertions (criterion grade, section-replacement) from a soft, informational substring check that does not gate the eval.

---

## One real defect (required fix)

### §10 contradicts §6 — stale "worst-of" reference

The deferred-section bullet still reads:

> **Numeric scoring** — A–F **worst-of** is the v1 model.

But §6 deleted worst-of and any overall grade ("**No single overall letter grade**"), and the appendix (§246) documents exactly that reversal. This bullet is leftover from the previous revision and now directly contradicts the authoritative §6.

**Fix:** rewrite to e.g. "Per-criterion A–F + 'count below B' is the v1 model; weighted/numeric scoring and trend tracking are deferred." Small, but it is a literal inconsistency an implementer could follow into the wrong design.

---

## Minor design notes (judgment calls, not blockers)

1. **Currency criterion is overloaded.** It measures two distinct failure modes under one grade: "does it match the actual repo today?" *and* "does Conventions still align with `templates/conventions.md`?" A repo can be code-current but convention-drifted, or vice versa, and the two drive different section replacements (Architecture/Commands vs Conventions). One letter can't express which failed. Either split into two criteria, or require the auditor's finding to state which sub-cause drove the grade so the user knows which section to fix.

2. **The "below B" count needs a denominator to be comparable.** With N/A exclusion, the scored set is sometimes 7, sometimes 6. "3 below B" means something different out of 6 vs 7. Report it as "3 of 7 below B" so the cross-repo / over-time comparison that §1 calls for stays honest.

3. **AskUserQuestion's 4-option cap vs convention-rule selection (§5.1).** "Which rules from `templates/conventions.md` to include" is routed through AskUserQuestion, but a 30–50 line conventions file may hold more than 4 rules, and AskUserQuestion caps at 4 options per question (multiSelect helps but the cap stands). This may need batching across questions, or may itself be better handled conversationally. Worth a one-line acknowledgement so the implementer isn't surprised.

---

## Bottom line

No structural issues remain across three rounds. The §10/§6 contradiction is the only required fix; notes 1–3 can be accepted or declined. **Buildable once §10 is corrected.**
