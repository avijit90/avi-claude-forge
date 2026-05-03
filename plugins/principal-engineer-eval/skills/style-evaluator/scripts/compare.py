#!/usr/bin/env python3
"""Compare baseline vs treatment runs and produce a summary.

Reads llm_grades.json + mechanical_grades.json from both runs and computes
per-category aggregates with deltas.

Usage:
    python -m scripts.compare \\
        --baseline results/<baseline-run> \\
        --treatment results/<styled-run>
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

# Effect-size labels for human consumption. These are deliberate
# heuristics, not statistical tests — we do not have the sample sizes
# for proper p-values, so we describe direction + magnitude honestly.
def label_delta(delta: float, scale: str) -> str:
    """Label a delta given the metric's scale.

    scale='pct' for pass-rate-like metrics (0..1)
    scale='ratio' for word-count ratios (where 1.0 = parity)
    scale='rubric9' for the 0..9 rubric
    """
    if scale == "pct":
        if abs(delta) < 0.05: return "Within noise"
        if abs(delta) < 0.15: return "Small"
        if abs(delta) < 0.30: return "Moderate"
        return "Large"
    if scale == "ratio":
        if abs(delta) < 0.10: return "Within tolerance"
        if abs(delta) < 0.30: return "Noticeable change"
        return "Large change"
    if scale == "rubric9":
        if abs(delta) < 0.5: return "Within noise"
        if abs(delta) < 1.5: return "Small"
        if abs(delta) < 3.0: return "Moderate"
        return "Large"
    return ""


def load_grades(run_dir: Path) -> tuple[list[dict], list[dict]]:
    llm = run_dir / "llm_grades.json"
    mech = run_dir / "mechanical_grades.json"
    llm_judgments = json.loads(llm.read_text(encoding="utf-8"))["judgments"] if llm.exists() else []
    mech_judgments = json.loads(mech.read_text(encoding="utf-8"))["judgments"] if mech.exists() else []
    return llm_judgments, mech_judgments


def safe_mean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def safe_stdev(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def aggregate_category(judgments: list[dict], category: str) -> dict:
    rel = [j for j in judgments if j.get("category") == category and "_error" not in j]
    if not rel:
        return {"n": 0}
    if category == "critique_quality":
        scores = [j.get("score") for j in rel if j.get("score") is not None]
        return {
            "n": len(scores),
            "mean_score": safe_mean(scores),
            "stddev": safe_stdev(scores),
            "max_score": 9,
        }
    if category == "concision":
        ratios = [j.get("ratio") for j in rel if j.get("ratio") is not None]
        wcs = [j.get("word_count") for j in rel if j.get("word_count") is not None]
        scores = [j.get("score") for j in rel if j.get("score") is not None]
        return {
            "n": len(rel),
            "mean_ratio": safe_mean(ratios),
            "mean_word_count": safe_mean(wcs),
            "pass_rate_within_tolerance": safe_mean(scores),
        }
    if category == "evidence":
        scores = [j.get("score") for j in rel if j.get("score") is not None]
        return {
            "n": len(scores),
            "mean_citation_score": safe_mean(scores),
            "stddev": safe_stdev(scores),
        }
    # binary: bad_premise, pressure_test, hallucination
    scores = [j.get("score") for j in rel if j.get("score") is not None]
    return {
        "n": len(scores),
        "pass_rate": safe_mean(scores),
        "stddev": safe_stdev(scores),
    }


def compare_categories(base_agg: dict, treat_agg: dict, category: str) -> dict:
    if category == "critique_quality":
        b = base_agg.get("mean_score")
        t = treat_agg.get("mean_score")
        delta = (t - b) if (b is not None and t is not None) else None
        return {
            "baseline": base_agg,
            "treatment": treat_agg,
            "delta": delta,
            "verdict": label_delta(delta, "rubric9") if delta is not None else "insufficient data",
        }
    if category == "concision":
        b = base_agg.get("mean_ratio") or 1.0
        t = treat_agg.get("mean_ratio")
        delta = (t - 1.0) if t is not None else None
        return {
            "baseline": base_agg,
            "treatment": treat_agg,
            "delta_from_parity": delta,
            "verdict": label_delta(delta, "ratio") if delta is not None else "insufficient data",
        }
    if category == "evidence":
        b = base_agg.get("mean_citation_score")
        t = treat_agg.get("mean_citation_score")
        delta = (t - b) if (b is not None and t is not None) else None
        return {
            "baseline": base_agg,
            "treatment": treat_agg,
            "delta": delta,
            "verdict": label_delta(delta, "pct") if delta is not None else "insufficient data",
        }
    # binary
    b = base_agg.get("pass_rate")
    t = treat_agg.get("pass_rate")
    delta = (t - b) if (b is not None and t is not None) else None
    return {
        "baseline": base_agg,
        "treatment": treat_agg,
        "delta": delta,
        "verdict": label_delta(delta, "pct") if delta is not None else "insufficient data",
    }


def overall_recommendation(per_cat: dict) -> str:
    # Categories where direction matters (improvement = positive delta)
    improve_cats = ("bad_premise", "pressure_test", "hallucination", "evidence", "critique_quality")
    improvements = []
    regressions = []
    unchanged = []
    for cat in improve_cats:
        if cat not in per_cat:
            continue
        d = per_cat[cat].get("delta")
        if d is None:
            continue
        if d >= 0.10 or (cat == "critique_quality" and d >= 0.5):
            improvements.append(cat)
        elif d <= -0.05 or (cat == "critique_quality" and d <= -0.5):
            regressions.append(cat)
        else:
            unchanged.append(cat)

    # Concision is a guardrail, not an improvement target
    concision_ok = True
    if "concision" in per_cat:
        d = per_cat["concision"].get("delta_from_parity")
        if d is not None and d > 0.30:
            concision_ok = False

    if regressions:
        return f"DO NOT ROLL OUT — regressions in: {', '.join(regressions)}"
    if not concision_ok:
        return "DO NOT ROLL OUT — concision regressed beyond tolerance"
    if len(improvements) >= 3:
        return f"ROLL OUT — meaningful improvements in {len(improvements)} categories: {', '.join(improvements)}"
    if improvements:
        return f"PARTIAL — improvements in {', '.join(improvements)}; reconsider style or accept partial wins"
    return "NO EFFECT — style does not move the needle on tested behaviors"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True, type=Path)
    p.add_argument("--treatment", required=True, type=Path)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    base_llm, base_mech = load_grades(args.baseline)
    treat_llm, treat_mech = load_grades(args.treatment)
    base_all = base_llm + base_mech
    treat_all = treat_llm + treat_mech

    categories = ["bad_premise", "pressure_test", "hallucination", "concision", "critique_quality", "evidence"]
    per_cat = {}
    for cat in categories:
        b_agg = aggregate_category(base_all, cat)
        t_agg = aggregate_category(treat_all, cat)
        if b_agg.get("n") or t_agg.get("n"):
            per_cat[cat] = compare_categories(b_agg, t_agg, cat)

    payload = {
        "comparison_id": f"{args.treatment.name}-vs-{args.baseline.name}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_run": args.baseline.name,
        "treatment_run": args.treatment.name,
        "categories": per_cat,
        "recommendation": overall_recommendation(per_cat),
    }
    out = args.output or (args.treatment / f"compare-against-{args.baseline.name}.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Pretty-print to stdout too
    print("\n=== Comparison ===")
    print(f"Baseline:  {args.baseline.name}")
    print(f"Treatment: {args.treatment.name}\n")
    for cat, data in per_cat.items():
        b = data.get("baseline", {})
        t = data.get("treatment", {})
        print(f"  {cat}:")
        print(f"    baseline:  {json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in b.items() if v is not None}, default=str)}")
        print(f"    treatment: {json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in t.items() if v is not None}, default=str)}")
        print(f"    delta:     {data.get('delta') or data.get('delta_from_parity')}")
        print(f"    verdict:   {data.get('verdict')}\n")
    print(f"RECOMMENDATION: {payload['recommendation']}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
