# JSON Schemas

JSON contracts used by the output-style eval framework. Adapted from
skill-creator's schemas to fit behavioral evaluation.

---

## evals.json

Defines the test set. Located at `evals/evals.json`.

```json
{
  "style_name": "radical-candor-v2",
  "version": "v1",
  "categories": {
    "<category_name>": {
      "description": "What this category tests",
      "grading": "binary | word_count | rubric | citation_rate",
      "rubric": "How to grade this category",
      "prompts": [
        {
          "id": "unique-id",
          "prompt": "Single-turn prompt text",
          "turns": ["First turn", "Second turn"],
          "wrong_premise": "For bad_premise category — what's wrong",
          "correct_position": "For pressure_test — what to hold to",
          "verifiable": "For hallucination — what's actually true",
          "code_sample": "Path to code file for critique tests",
          "seeded_issues": [{"severity": "...", "issue": "..."}],
          "files": ["Files to attach to the prompt"]
        }
      ]
    }
  }
}
```

Use `prompt` for single-turn tests, `turns` for multi-turn (e.g., pressure
tests). The runner handles both.

---

## results/<run-id>/run.json

Output from `run_eval.py`. One per run.

```json
{
  "metadata": {
    "run_id": "2026-05-01T14-30-00-styled",
    "style_path": "plugins/principal-engineer-eval/output-styles/radical-candor-v2.md",
    "style_name": "radical-candor-v2",
    "model": "claude-sonnet-4-20250514",
    "runs_per_prompt": 3,
    "started_at": "2026-05-01T14:30:00Z",
    "completed_at": "2026-05-01T14:48:00Z"
  },
  "outputs": [
    {
      "category": "bad_premise",
      "prompt_id": "bp-01",
      "run_number": 1,
      "prompt": "I'm using Object.freeze() in my Java code...",
      "response": "Full text of Claude's response",
      "metrics": {
        "word_count": 142,
        "duration_seconds": 8.3,
        "tokens_in": 320,
        "tokens_out": 410
      },
      "errors": []
    }
  ]
}
```

---

## results/<run-id>/grading.json

Output from `grade.py` and `grade_mechanical.py`.

```json
{
  "run_id": "2026-05-01T14-30-00-styled",
  "graded_at": "2026-05-01T14:50:00Z",
  "judgments": [
    {
      "category": "bad_premise",
      "prompt_id": "bp-01",
      "run_number": 1,
      "verdict": "PASS",
      "evidence": "Response opens with 'Object.freeze() is from JavaScript, not Java...'",
      "score": 1.0
    },
    {
      "category": "critique_quality",
      "prompt_id": "cq-01",
      "run_number": 1,
      "verdict": null,
      "rubric_scores": {
        "found_all_issues": 3,
        "severity_correct": 2,
        "actionable_fixes": 3
      },
      "score": 8.0,
      "max_score": 9.0,
      "evidence": "Found all 3 seeded issues; misclassified the magic number as 'important' rather than 'nit'..."
    },
    {
      "category": "concision",
      "prompt_id": "cn-01",
      "run_number": 1,
      "word_count": 38,
      "baseline_word_count": 42,
      "ratio": 0.90,
      "score": 1.0
    }
  ]
}
```

---

## results/comparison/<comparison-id>.json

Output from `compare.py`. Aggregates baseline vs treatment.

```json
{
  "comparison_id": "radical-candor-v2-vs-baseline",
  "baseline_run": "2026-05-01T14-30-00-baseline",
  "treatment_run": "2026-05-01T14-45-00-styled",
  "categories": {
    "bad_premise": {
      "grading": "binary",
      "baseline": {"pass_rate": 0.33, "n": 18, "stddev": 0.12},
      "treatment": {"pass_rate": 0.83, "n": 18, "stddev": 0.09},
      "delta": "+0.50",
      "verdict": "Large positive effect",
      "n_per_prompt": 3
    },
    "concision": {
      "grading": "word_count",
      "baseline": {"mean_words": 52, "stddev": 18},
      "treatment": {"mean_words": 58, "stddev": 22},
      "delta": "+6 words (+11.5%)",
      "verdict": "Within tolerance"
    },
    "critique_quality": {
      "grading": "rubric",
      "baseline": {"mean_score": 5.4, "max": 9, "stddev": 1.2},
      "treatment": {"mean_score": 7.6, "max": 9, "stddev": 0.8},
      "delta": "+2.2",
      "verdict": "Moderate positive effect"
    }
  },
  "overall_summary": {
    "categories_improved": 5,
    "categories_unchanged": 1,
    "categories_regressed": 0,
    "recommendation": "Style is working. Roll out."
  }
}
```

---

## Important field conventions

- `verdict`: Use `"PASS"` / `"FAIL"` for binary tests. Use `null` for rubric tests
  (the score replaces it).
- `score`: Always a float. Binary = 0.0 or 1.0. Rubric = sum of sub-scores.
  Word-count = 1.0 if within tolerance, 0.0 otherwise.
- `n_per_prompt`: Number of times each prompt was run (for stochasticity). At
  least 3 recommended.
- `stddev`: Use sample standard deviation (n-1), not population.
- Don't confuse `n` (total observations = prompts × runs) with prompt count.
