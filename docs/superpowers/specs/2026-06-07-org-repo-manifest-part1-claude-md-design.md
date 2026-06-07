# org-repo-manifest — Part 1: CLAUDE.md Management

**Date:** 2026-06-07
**Status:** Revised after design reviews (`-review.md`, `-review2.md`, `-review3.md`, `-review4.md`)
**Scope:** Part 1 of a multi-part initiative. Covers CLAUDE.md drafting and auditing for org microservice/MFE repos. Sibling plugins (ADRs, runbooks, glossary) follow in later parts.

---

## 1. Problem

Enterprise repos in the org accumulate CLAUDE.md files of wildly varying quality. Some are missing entirely; some are stale; some are 500-line dumps. There's no shared definition of "good," no way to audit at scale, and no maintenance ritual. Tech leads need a plugin they can install and run on any service repo to (a) bootstrap a CLAUDE.md, and (b) audit an existing one against an org rubric.

## 2. Goals & non-goals

**Goals**
- One plugin, one install, two commands in v1: `/draft-claude-md`, `/audit-claude-md`.
- Produce CLAUDE.md files that are ≤150 lines, high signal, and consistent in shape across repos.
- Audit is read-only and reports — never enforces.
- Conventions live inline in CLAUDE.md (no @import dependencies on the plugin at runtime).
- Designed so future artifacts (ADRs, runbooks, glossary) become **sibling plugins**, not extensions of this one.

**Non-goals**
- No GitHub/CI dependency. No webhooks, no PR bots, no remote enforcement.
- No multi-language abstraction layer. Bespoke now; refactor when a second plugin actually ships.
- No monorepo support. Targets medium services (~30 KLOC) and MFEs.
- No CLI for syncing conventions. Inline is good enough.
- **No `/revise-claude-md` in v1.** Deferred — see §10.

## 3. CLAUDE.md sections (the standard)

Target ~100 lines content, hard cap 150 (including headers and blank lines).

| Section | Lines | Content |
|---|---|---|
| Purpose | 5 | Positive definition of what this repo is. No "out of scope" line. |
| Features | 15 | Bulleted list of what the service does. |
| Architecture | 10 | High-level shape + entry points inline. |
| Commands | 15 | Copy-pasteable: build, test, run, deploy. |
| Gotchas | 15 | Repo-wide footguns. Sibling-repo boundary one-liners go here. |
| Conventions | flex (≤30) | Curated summary of the org standards that apply to this repo. Not a verbatim copy of `templates/conventions.md` (which is the canonical full reference). |
| Reference | 6 | Index pointing to `docs/` folder. Does NOT @import. |

**Why inline conventions:** @imports load at session start regardless. Splitting saves zero context tokens and creates a hard runtime dependency on plugin install. Inline is honest about the cost.

**Why summary, not verbatim copy:** Real org standards across stacks (Node/Spring/React) easily run 30–50 lines. Forcing verbatim inline would explode CLAUDE.md or force the canonical file to be unrealistically small. Letting the section be a curated summary keeps CLAUDE.md focused on what applies to *this* repo. Trade-off: drift detection becomes semantic LLM judgment, not literal diff. Accepted (see §6).

## 4. Plugin architecture

### 4.1 Component-type assignment

| Component | Type | Why |
|---|---|---|
| `/draft-claude-md` | command | User-facing entry point. Interactive. |
| `/audit-claude-md` | command | User-facing entry point. Dispatches agent. |
| `claude-md-drafting` | skill | Procedural domain expertise. Auto-triggers when draft command runs. Prose Q&A and discrete-choice prompts both happen in main context (visible); see §5.1 for tool choice. |
| `claude-md-auditor` | agent | Autonomous subprocess. Reads many files, returns concise report. Isolated context so audit reads don't pollute main session. |

**Asymmetry justified:** Drafting is interactive Q&A — belongs in main context as a skill. Auditing is heavy file-reading with a structured report output — belongs in an isolated agent. The two tasks have genuinely different shapes.

### 4.2 Directory layout

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
    └── claude-md-auditor/
        ├── evals.json
        └── fixtures/
```

Plural `rubrics/` and `templates/` are forward-compat hedges — cheap to do now, avoid a rename later if sibling plugins reuse the pattern.

## 5. Data flow

### 5.1 `/draft-claude-md`

```
user runs command
  → command loads claude-md-drafting skill
  → skill detects build files (package.json, pom.xml, etc.)
  → skill drafts Commands section from detected signals
  → skill gathers the rest via two interaction modes in main context:
      Conversational prose prompts (free-form text):
        - Purpose       (needs human framing)
        - Features      (cannot be auto-detected; user lists them)
        - Architecture  (skill drafts a starter from repo tree; user confirms/rewrites)
        - Gotchas       (incl. sibling-repo boundaries)
        - Conventions   (skill presents the rule list from templates/conventions.md
                         and asks which apply to this repo; user replies in prose.
                         Conversational because the rule list often exceeds
                         AskUserQuestion's 4-option cap.)
      AskUserQuestion (discrete choices only, ≤4 options):
        - Stack disambiguation when 2–4 detected (e.g., Node + Python)
        - Final accept/reject of the draft
  → skill writes CLAUDE.md, shows preview, asks for accept/reject
  → on accept: file written, command exits
```

**Tool choice discipline:** AskUserQuestion presents 2–4 fixed multiple-choice options and is wrong for prose elicitation. Prose sections (Purpose, Features, Architecture, Gotchas, Conventions selection) use plain conversational prompting in main context. AskUserQuestion is reserved for genuine discrete choices: stack pick, accept/reject.

**Honest about auto-detection:** It earns its keep for the **Commands** section only (build files → executable commands). Features, Architecture (beyond a starter shape), Gotchas, and Conventions selection are all human input. The skill should not pretend otherwise.

### 5.2 `/audit-claude-md`

```
user runs command
  → command dispatches claude-md-auditor agent
  → agent reads CLAUDE.md, repo structure, package files, templates/conventions.md
  → agent scores against rubrics/claude-md.md (7 criteria, A-F per criterion)
  → agent returns: scores + ≤10 specific findings + suggested full-section replacements
  → command renders report in main context
  → command: "Apply this suggested replacement for section X?" → user accepts/rejects each
  → on accept: command replaces the section between known markdown headers
  → audit itself is read-only; only user-confirmed replacements touch CLAUDE.md
```

**Why full-section replacement, not line diffs:** The agent's output crosses an isolated-context → main-context seam. Line-diff hunks applying cleanly across that seam is historically unreliable. Specifying "agent returns a full new section; main context replaces between known `## Section Name` headers" eliminates the fuzziness. If the section markers can't be located, the command surfaces the failure and asks the user to apply manually.

## 6. Rubric (7 criteria)

Adapted from the `claude-md-improver` skill in [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management/skills/claude-md-improver), with a Purpose & Features criterion added to close the audit-coverage gap that existed in v0 of this spec.

Each criterion scored **A–F**. Per-criterion letters are the primary, actionable output. **No single overall letter grade** — that abstraction created tension between "harder to game" and "useful gradient" and the audit doesn't need it.

| Criterion | What it measures |
|---|---|
| Commands & workflows | Are build/test/run/deploy commands present and copy-pasteable? |
| Architecture clarity | Can someone unfamiliar with the repo navigate it from this section? |
| Purpose & Features clarity | Is Purpose a sharp positive definition? Are Features specific, current, non-redundant? |
| Non-obvious patterns | Are gotchas and sibling-repo boundaries called out? |
| Conciseness | Is it ≤150 lines? Signal-to-noise ratio high? |
| Currency | Does it match the actual repo today? Does Conventions still align with `templates/conventions.md`? When this scores below B, the finding **must name the sub-cause** ("repo drift: Architecture stale" vs "convention drift: Conventions section misaligned") so the user knows which section to fix. |
| Actionability | Does each section give a reader something concrete they can do? |

**Single summary metric:** *X of N criteria graded below B* — always reported with the denominator (e.g., "3 of 7 below B", or "2 of 6 below B" when one criterion is N/A). Lower is better. The denominator matters because N/A handling can shrink the scored set, and "3 below B" out of 6 vs 7 isn't comparable without it.

**N/A handling.** A criterion may be marked N/A when the auditor cannot evaluate it — currently the only specified case is Currency when `templates/conventions.md` is inaccessible (§7). N/A criteria are excluded from both the report grades and the "below B" count, and are listed separately in the report under "Not scored, with reason."

**Scoring is LLM semantic judgment.** No bash-level "deterministic diff" is claimed. The auditor is an agent (§4.1) and its grades are semantic assessments. This is the honest mechanism. Trade-off is the loss of bit-exact reproducibility; gain is the ability to score things like "Features section has rotted" that no literal diff would catch.

**Conventions drift specifically:** the auditor compares the curated inline summary against the canonical `templates/conventions.md` and decides whether the summary still represents it accurately. Semantic, not literal. Edge cases handled per §7.

**Convention-drift findings are advisory by construction.** A curated summary is *expected* to omit rules that don't apply to this repo — that's the whole point of curating. The auditor cannot cleanly distinguish "deliberately scoped out" from "forgotten / went stale," so some convention-drift findings will be false positives. This is the accepted cost of the summary approach (vs verbatim copy, see Appendix). Reviewers should treat these findings as suggestions to confirm, not as proof of drift.

## 7. Edge cases & error handling

### `/draft-claude-md`
| Scenario | Behavior |
|---|---|
| Empty repo, no build files | Commands section is TODO with prompt: "Couldn't auto-detect. What does this repo build with?" |
| Multiple stacks (Node + Python) | Skill asks user to confirm or pick which to document. |
| User cancels mid-Q&A | No file written. No partial draft. |
| User answers Purpose vaguely | Skill prompts for sharper text once, then accepts. |
| `templates/conventions.md` missing or unreadable | Skill warns, drafts Conventions as TODO, continues. |

### `/audit-claude-md`
| Scenario | Behavior |
|---|---|
| CLAUDE.md empty/malformed | All criteria graded F. Recommendation: delete and re-run /draft-claude-md. |
| Substantial repo restructure | Currency scores low; auditor proposes Architecture/Commands replacements. |
| Conventions intentionally diverged | Flagged as drift; user can reject the replacement. Auditor reports, doesn't enforce. |
| Auditor agent times out | Command surfaces the error. No silent failure. |
| `templates/conventions.md` inaccessible | Currency criterion marked **N/A** with reason "cannot verify conventions drift — plugin templates inaccessible." Other criteria still scored. Excluded from "below B" count. |
| Section headers can't be located for replacement | Command surfaces the failure, prints suggested text, asks user to apply manually. |

**Core principle:** Auditor reports, doesn't enforce. Even drift from canonical conventions is presented as a finding, not blocked. Teams sometimes have legitimate reasons to diverge.

## 8. Evals

`evals/` directory at plugin root, two suites.

**`evals/claude-md-drafting/`** — fixtures of realistic repos (small Node service, Spring Boot service, React MFE), `evals.json` asserts the produced CLAUDE.md:
- Is ≤150 lines
- Contains all 7 required section headers (Purpose, Features, Architecture, Commands, Gotchas, Conventions, Reference)
- Commands section contains executable text that matches detected build files
- Conventions section is non-empty and references at least one rule from `templates/conventions.md`

**`evals/claude-md-auditor/`** — fixtures of CLAUDE.md files with known defects (missing section, stale architecture, vague Features, oversized, conventions drift), `evals.json` asserts the auditor:

*Hard assertions (eval fails if any of these fail):*
- Scores the relevant rubric criterion **C or below** for the planted defect
- Returns a section-replacement suggestion for the affected section (when the defect is content-level, not metadata)

*Soft check (logged for inspection, doesn't fail the eval):*
- Findings list mentions the defect (substring match). Phrasing varies run to run; this is informational, not a gate.

Baseline comparison run before any prompt change.

## 9. Forward compatibility

Future artifacts (ADRs, runbooks, glossary) become **sibling plugins** in the same marketplace:
- `org-repo-adrs`
- `org-repo-runbooks`
- `org-repo-glossary`

Each follows the same lifecycle pattern (draft + audit commands, auditor agent, drafting skill, rubric, template, evals). Each is self-contained. No cross-plugin dependencies. Share patterns, not code.

**Two cheap hedges only:**
1. Plural directory names (`rubrics/`, `templates/`) — no rename later.
2. Document the lifecycle pattern in README so sibling plugins copy it consistently.

**Explicitly NOT building now:**
- Shared rubric framework
- Shared base agent
- Artifact registry
- Parameterized commands across artifacts

Refactor to shared infrastructure only when a second plugin is actually written and the duplication is concrete.

## 10. Deferred / open questions

- **`/revise-claude-md` — deferred.** A session-end ritual to capture learnings was in v0. Cut from v1 because: no defensible criterion for "worth capturing," no eval suite, real risk of fabricating learnings or churning CLAUDE.md every session. The fuzziest, lowest-value, highest-annoyance-risk command of the three. Audit catches drift retroactively; that's enough for v1. Revisit once real drift patterns from real teams are observed.
- **`.claude/local.md` integration** — deferred until after Part 1 ships.
- **Session-start hooks for auto-running audit** — deliberately not in v1. Tech-lead-triggered only.
- **Numeric / weighted scoring** — Per-criterion A–F plus the "X of N below B" summary is the v1 model. Weighted scores, numeric grades, and explicit trend tracking are deferred. Don't pre-build.

---

## Appendix: Why not these alternatives

- **Why not a single super-agent that does drafting + auditing?** Different task shapes. Drafting needs visible Q&A in main context; auditing benefits from isolated subprocess context for heavy reads.
- **Why not enforce conventions via hooks?** Drift isn't always wrong. Teams have legitimate reasons to diverge. Reporting > blocking.
- **Why not store conventions in a shared repo and @import?** @imports load at session start regardless. No token savings. Adds a runtime dependency. Inline is honest.
- **Why not parameterize commands so one plugin handles all artifacts?** Premature. Three artifacts of generic shape don't yet exist. Build the second one bespoke, then look at the duplication concretely.
- **Why not require verbatim Conventions section + literal-diff drift detection?** The previous spec did. Review (#1) flagged the internal contradiction with the line cap and real-world convention sizes. Switching to curated summary + semantic auditor judgment is the honest mechanism.
- **Why not keep weights on the rubric?** Nothing computed weighted totals; they were dead metadata. Per-criterion A–F + "count of criteria below B" is simpler, harder to game, and still provides a trackable gradient.
- **Why not a single overall letter grade (worst-of or weighted average)?** v1 of this revised spec used worst-of. Round-2 review flagged that across 7 semantic criteria most real repos would bottom out to F, killing the gradient. Weighted average reintroduces weight bookkeeping. Dropping the overall grade and reporting only per-criterion letters + a "below B" count avoids both failure modes.
- **Why not use AskUserQuestion for prose elicitation?** It presents 2–4 fixed multiple-choice options — wrong shape for Purpose/Features/Architecture prose. Plain conversational prompting handles prose; AskUserQuestion is reserved for genuine discrete choices.
