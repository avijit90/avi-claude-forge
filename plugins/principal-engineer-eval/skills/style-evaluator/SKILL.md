---
name: style-evaluator
description: Quantitatively evaluate a Claude Code output style against the default baseline. Use this skill when the user wants to test an output style before rolling it out, measure sycophancy resistance, position-holding, hallucination rate, concision, critique quality, or citation behavior. Trigger when the user says "evaluate this style", "test this output style", "is this style working", "compare baseline vs styled", or asks for evidence that an output style change is helping.
---

# Output Style Evaluator

A measurement framework for output styles. Adapted from Anthropic's `skill-creator`, but focused on **behavioral properties** rather than artifact correctness.

## When to use this skill

The user has an output style (theirs or someone else's) and wants to know: does it actually change Claude's behavior in measurable ways before they ship it to a team?

This skill is NOT for:
- Creating output styles (suggest writing one in `~/.claude/output-styles/`)
- Evaluating skills or subagents (use `skill-creator` instead)
- Measuring real-world satisfaction (that needs post-rollout telemetry)

## What this skill measures

Six behavioral categories, each targeting a specific failure mode:

| Category           | Targets                                  | Grading       |
|--------------------|------------------------------------------|---------------|
| `bad_premise`      | Agreeing with incorrect framings         | Binary (LLM)  |
| `pressure_test`    | Capitulating under pushback              | Binary (LLM)  |
| `hallucination`    | Fabricating paths, APIs, defaults        | Binary (LLM)  |
| `concision`        | Padding simple answers                   | Word count    |
| `critique_quality` | Vague, unstructured code review          | Rubric (LLM)  |
| `evidence`         | Stating code claims without citation     | Citation rate |

## The workflow

1. Identify the style file the user wants to evaluate (path to `.md` file)
2. Identify the baseline (default Claude Code, no style)
3. Run the eval set against both
4. Grade outputs (mechanical for `concision`/`evidence`, LLM-judge for the rest)
5. Compare per-category and report a recommendation

## How to run an evaluation

The skill ships with a complete eval set in `evals/evals.json` and four scripts.

### Step 1: Confirm the style path

Ask the user where their style lives. Common locations:
- `~/.claude/output-styles/<name>.md` (user-level)
- `<project>/.claude/output-styles/<name>.md` (project-level)
- A path provided by the user

If they don't have one yet, offer one of the bundled samples in `output-styles/`: `radical-candor-v1.md` (terse, rule-driven) or `radical-candor-v2.md` (elaborated principal-engineer pairing voice). Evaluating both against the same baseline gives a direct v1-vs-v2 comparison.

### Step 2: Run baseline and treatment

From the skill directory:

```bash
# Baseline (no style)
python -m scripts.run_eval --eval-set evals/evals.json --style none --runs 3

# Treatment (with style)
python -m scripts.run_eval --eval-set evals/evals.json --style <path-to-style.md> --runs 3
```

This produces `results/<timestamp>-baseline/run.json` and `results/<timestamp>-<style-name>/run.json`.

The default `--runs 3` matters — output style behavior is somewhat stochastic, so single-run evals overfit. Don't drop below 3 unless the user is debugging.

### Step 3: Grade

```bash
# Mechanical grades (concision, evidence) — fast, deterministic
python -m scripts.grade_mechanical \
    --treatment-run results/<styled-run> \
    --baseline-run results/<baseline-run>

# LLM-judge grades (bad_premise, pressure_test, hallucination, critique_quality)
python -m scripts.grade --run-dir results/<baseline-run> --eval-set evals/evals.json
python -m scripts.grade --run-dir results/<styled-run> --eval-set evals/evals.json
```

The LLM-judge step is the slowest (calls `claude -p` once per output). It writes incrementally so partial progress survives interruption.

### Step 4: Compare

```bash
python -m scripts.compare \
    --baseline results/<baseline-run> \
    --treatment results/<styled-run>
```

Prints a per-category breakdown and a top-level `RECOMMENDATION`: `ROLL OUT`, `PARTIAL`, `NO EFFECT`, or `DO NOT ROLL OUT`.

## How to interpret the results

The recommendation is a heuristic, not a verdict. Read the per-category table.

**A successful style** typically shows:
- Large positive deltas on `bad_premise`, `pressure_test` (these are the easiest to move)
- Moderate positive delta on `critique_quality` and `evidence`
- `concision` within tolerance (style should not bloat short answers)
- `hallucination` improvement is harder to demonstrate; small positive movement is good

**Common failure patterns**:
- **All categories move slightly positive but none decisively**: the style language is too soft. Sharpen the rules with concrete examples and bans.
- **Bad_premise improves but pressure_test doesn't**: the style added premise-checking but not position-holding. Add explicit "do not capitulate" language.
- **Critique_quality regresses**: the style is over-emphasizing brevity at the cost of structured findings. Loosen concision for review tasks specifically.
- **Concision regresses badly**: structured-thinking rules are firing on trivial questions. Add explicit escape hatch for simple queries.

## What this skill explicitly does NOT do

- It does not optimize the style automatically. The improvement loop is human-in-the-loop: evaluate → read misses → tweak → re-evaluate.
- It does not verify that specific factual claims (e.g., "Hikari default is 10") are correct. It only verifies the response's epistemic posture (cited or disclaimed).
- It is not a replacement for real-world observation. With 28 prompts × 3 runs, confidence intervals are wide. Treat differences <10 percentage points as noise.

## Honest limitations

1. **Multi-turn pressure tests use `claude --resume <session>`.** If your version of Claude Code uses different flags, edit `run_multi_turn` in `scripts/run_eval.py`.
2. **Output style activation uses `--output-style <name>`.** If that flag isn't supported, the script falls back to copying the style file into `.claude/output-styles/` for the session — but verify the style is actually active by reading one of the output files manually.
3. **The LLM judge has its own biases.** The grader prompt at `agents/style_grader.md` mitigates known ones (preference for length, confidence) but not all.
4. **Don't optimize to the eval.** If you tweak the style to score higher on this specific prompt set, you may be overfitting. Hold out 20% of prompts as a final-only test set.

## File layout

```
style-evaluator/
├── SKILL.md                         (this file)
├── evals/
│   ├── evals.json                   (28 prompts across 6 categories)
│   └── code_samples/                (Java + Python files for critique tests)
├── scripts/
│   ├── run_eval.py                  (executes prompts via `claude -p`)
│   ├── grade.py                     (LLM-judge for binary + rubric categories)
│   ├── grade_mechanical.py          (word count + citation regex)
│   └── compare.py                   (aggregates baseline vs treatment)
├── agents/
│   └── style_grader.md              (system prompt for the LLM judge)
└── references/
    └── schemas.md                   (JSON contracts for all outputs)
```

For the JSON schemas of every input/output file, read `references/schemas.md`.
