# Review — org-repo-manifest Part 1: CLAUDE.md Management

**Reviewer:** Claude (critical design review)
**Date:** 2026-06-07
**Reviewing:** `2026-06-07-org-repo-manifest-part1-claude-md-design.md`
**Grounding:** Read against the actual repo — existing plugins (`lgtm`, `principal-engineer-eval`, `telegram-tower`), the marketplace manifest, and the current `style-evaluator` skill.

---

## Verdict

The plan is well-written and the reasoning discipline is genuinely good — the YAGNI/forward-compat section and the "report, don't enforce" principle are correct and well argued. But it has **one real internal contradiction, a structural gap between what it builds and what it audits, and a pattern of overselling determinism that the actual mechanism (an LLM agent) can't deliver.**

**Do not build as-is.** Resolve the four material items below first.

---

## Material problems (fix before building)

### 1. The Conventions section is internally contradictory

The spec asserts three things that can't all be true:

- §3: Conventions capped at **15 lines** ("inlined org standards: logging, error handling, naming").
- §5.1 / §8: it's a **verbatim copy of `templates/conventions.md`**.
- §6: drift detection is **literal text comparison** against that template.

These only co-hold if `templates/conventions.md` is itself ≤15 lines. Real org conventions (logging + error handling + naming across Node/Spring/React) are not 15 lines. So either the section can't be a verbatim copy (it's a summary → literal diff is meaningless), or the 15-line cap is fiction, or conventions.md is trivially small.

**This breaks your own eval suite.** §8 asserts "Conventions section is verbatim copy of `templates/conventions.md`" *and* §3 caps it at 15 lines. The drafting eval will fail against the design spec. Pick one model and make the numbers consistent.

### 2. You build 7 sections but only audit 6 dimensions — Purpose/Features quality is unscored

- Drafting produces 7 sections: Purpose, Features, Architecture, Commands, Gotchas, Conventions, Reference.
- The rubric scores 6: Commands, Architecture, Non-obvious patterns, Conciseness, Currency, Actionability.

Map them and **nothing in the rubric scores whether Purpose or Features are correct or good.** The auditor cannot catch a wrong, vague, or stale Features list or a useless Purpose line — the two sections most dependent on human judgment and most likely to rot. "Actionability" and "Conciseness" are cross-cutting, not coverage of those sections.

Either add criteria, or justify in writing why those two sections are exempt from audit. Right now it's an unexamined gap.

### 3. "Deterministic / literal diff" is claimed twice where the mechanism is LLM judgment

- §6 Currency: scored by the LLM agent but described as "auditor runs **literal diff** vs. detected state." Detecting that an Architecture paragraph is stale relative to the actual code is a semantic judgment — there is no literal diff.
- §6 Conventions drift: "literal text comparison… **Deterministic; one bash-level diff.**" But the auditor is an **agent** (§4.1), not a bash script. Agents don't run reliable deterministic diffs, and extracting the inlined Conventions section's exact boundaries from CLAUDE.md to diff against a file is itself fuzzy.

Why it matters: you're selling tech leads on determinism you won't deliver, and it collides with your own "teams legitimately diverge" principle — a *literal* diff flags every benign reformatting as drift and becomes noise people ignore. If you want real determinism, the diff must be a real script step (a PostToolUse hook or a bash step in the command), not "the agent will compare." Decide the actual execution model.

### 4. `/revise-claude-md` is the weakest command — cut it from Part 1

Compare the three data flows in §5. Draft and Audit each have detection logic, a rubric, edge cases, and evals. Revise has only: *"command reviews session context for learnings worth capturing."* There is:

- no criterion for what "worth capturing" means,
- no eval suite for it (§8 covers only drafting + auditor),
- no defense against hallucinating "learnings" or churning CLAUDE.md every session.

It's the most magical, least-specified, lowest-value, highest-annoyance-risk of the three. Drafting + auditing are the real product. **Ship those two, prove them with evals, and defer revise** until real drift patterns are observed. An unevalued mutating command dilutes the thing you can actually validate.

---

## Smaller issues (worth a sentence in the spec)

- **Rubric weights are dead metadata.** §6 assigns 20/20/15/15/15/15, but the report and the §8 eval ("scores the relevant criterion below B") use A–F letter grades — nothing computes a weighted total. Define how letters + weights combine, or drop the weight column.

- **Auto-detection is oversold for Features and Architecture.** §5.1 says the skill "drafts sections from detected signals" and "validates auto-detected" Features. You cannot meaningfully auto-detect a service's *features* from `package.json`/`pom.xml` — that's human input. Auto-detection realistically only earns its keep for the **Commands** section. Be honest about that, or you'll over-promise and under-deliver on the Q&A burden.

- **Diff generation crosses an agent→main-context seam (§5.2).** The auditor agent has the file content in *its* isolated context and emits "suggested diffs"; the main command then applies them. Agent-produced line diffs applying cleanly is historically unreliable, and the main context may not hold the exact bytes the agent diffed against. Specify the diff representation (full-section replacement is safer than line diffs here) and the behavior when one doesn't apply.

- **Line-budget arithmetic.** Per-section content budgets sum to 81 lines *before* headers and blank lines (~7 headers + spacing ≈ +15–20). "Target ~80" is effectively unreachable if sections are near budget; realistic floor is ~100. Adjust the target so it's honest.

- **Verify the "official `claude-md-improver` rubric" citation (§6).** It is not clearly an official Anthropic skill. The existing `style-evaluator` skill in this repo carefully cites "Anthropic's `skill-creator`" — which is real and present in the environment. Hold this citation to the same bar: link it or rename to "adapted from the skill-creator rubric / our own." Don't cite an authority you can't point to.

---

## What's genuinely right (calibration)

- **§9 forward-compat is exemplary YAGNI.** "Sibling plugins, share patterns not code, refactor when the second is concrete, two cheap hedges only" — the correct call, rarely resisted this cleanly.
- **"Report, don't enforce" (§7, Appendix)** is the right philosophy for org tooling.
- **The skill/agent asymmetry (§4.1)** — interactive drafting as a main-context skill, heavy read-only auditing as an isolated agent — is correctly reasoned and matches how this repo already splits work.
- **Edge-case tables (§7)** are more thorough than most specs bother with.

---

## Bottom line

The architecture instincts are sound; the execution model is where it's soft. Resolve the Conventions contradiction (#1), close the audit-coverage gap (#2), stop claiming determinism you won't ship (#3), and cut revise from v1 (#4). Do those four and this is a solid Part 1.
