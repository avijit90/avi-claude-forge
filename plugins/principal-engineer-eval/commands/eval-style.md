---
description: Quantitatively evaluate a Claude Code output style against the default baseline. Runs 28 prompts across 6 behavioral categories (sycophancy, position-holding, hallucination, concision, critique quality, citations) with and without the style, then reports per-category deltas and a roll-out recommendation.
argument-hint: <path-to-style.md>
---

You are running the `style-evaluator` skill from the `principal-engineer-eval` plugin.

The user wants to evaluate this output style: **$ARGUMENTS**

If no path was provided, ask the user where the style file lives, or offer one of the bundled samples from this plugin's `output-styles/` directory:

- `radical-candor-v1.md` — terse, rule-driven, extreme token efficiency
- `radical-candor-v2.md` — elaborated principal-engineer pairing voice

If the user wants to compare both, run the eval workflow once per style (baseline + v1, then baseline + v2 — the baseline can be reused) and report per-style deltas side by side.

Then follow the workflow described in the skill's `SKILL.md`:

1. Confirm the style path exists and read the style file
2. Run baseline (no style) using `python -m scripts.run_eval --eval-set evals/evals.json --style none --runs 3`
3. Run treatment (with style) using `python -m scripts.run_eval --eval-set evals/evals.json --style <path> --runs 3`
4. Grade both runs (mechanical + LLM-judge)
5. Compare and report

Before kicking off the runs, give the user a heads-up:
- Total runtime: ~15-25 minutes wall-clock (depends on parallelism and model)
- Total cost: low six-figure tokens for the full comparison
- The runs can be interrupted; partial progress is preserved in JSON files

If the user wants a faster smoke test, suggest `--runs 1` and a category subset (they can edit `evals/evals.json` to keep only one or two categories).

After comparison, do not just dump the JSON. Read it and tell the user:
- Which categories moved meaningfully (>10pp for binary, >0.5 for rubric)
- Which did not (and what the style would need to change to fix that)
- Whether the recommendation is to roll out, iterate, or scrap

Also generate an HTML report so the user can browse responses side-by-side:

```
python -m scripts.make_report
```

This writes `results/report.html` covering all run.json files in `./results/`. Surface the path; the user opens it in their browser. The report has per-config summary stats, category-grouped prompts, and color-coded word/token badges versus baseline.

If the style underperforms, suggest specific edits based on which categories failed — see the "Common failure patterns" section in `SKILL.md`.
