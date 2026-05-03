#!/usr/bin/env python3
"""Mechanical grading for output-style evals.

Handles the categories that don't need an LLM judge:
- concision: word count comparison vs baseline
- evidence: citation rate via regex (file:line patterns)

Run after `run_eval.py`. Reads run.json, writes mechanical_grades.json.

Usage:
    python -m scripts.grade_mechanical \\
        --treatment-run results/<styled-run> \\
        --baseline-run results/<baseline-run>
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

# Patterns that count as a "citation" for the evidence category.
# We accept several common forms a developer would use:
#   path/to/file.ext:123
#   path/to/file.ext:123-145
#   `path/to/file.ext:123`
#   `path/to/file.ext`, line 123
#   path/to/file.ext (lines 123-145)
#   src/foo/Bar.java#L42
CITATION_PATTERNS = [
    # path:line or path:line-line, possibly backticked
    re.compile(r"`?[\w./\-]+\.\w{1,8}:\d+(?:-\d+)?`?"),
    # GitHub-style #L42
    re.compile(r"`?[\w./\-]+\.\w{1,8}#L\d+(?:-L?\d+)?`?"),
    # "in foo.java, line 42" or "(lines 42-50)"
    re.compile(r"`?[\w./\-]+\.\w{1,8}`?,?\s*\(?lines?\s+\d+", re.IGNORECASE),
]

# Phrases that count as an explicit uncertainty marker. A claim is "ok"
# either if it has a citation nearby OR if the response carries an
# uncertainty disclaimer.
UNCERTAINTY_MARKERS = [
    r"\bi don'?t know\b",
    r"\bi(?:'m| am) not sure\b",
    r"\bi cannot verify\b",
    r"\bi can'?t verify\b",
    r"\bwithout (?:checking|verifying|access to)\b",
    r"\bwould need to (?:check|verify|look)\b",
    r"\bnot certain\b",
    r"\b(?:unverified|inferred|assumed)\b",
    r"\bbased on (?:memory|recollection)\b",
    r"\bplease verify\b",
    r"\bcheck the (?:docs|source|code)\b",
]
UNCERTAINTY_RE = re.compile("|".join(UNCERTAINTY_MARKERS), re.IGNORECASE)

# A "code claim" is roughly a sentence that mentions a class, method,
# file, or specific value. We use a heuristic — looking for either a
# code-fence span or specific keywords.
CLAIM_HINT_RE = re.compile(
    r"(?:`[A-Za-z_][\w.]*(?:\(\))?`"             # backticked identifier
    r"|class \w+|method \w+|function \w+"        # English-language refs
    r"|line \d+|default(?:s)? to|returns?|equals?\s+\d+)",
    re.IGNORECASE,
)


def count_citations(text: str) -> int:
    return sum(len(p.findall(text)) for p in CITATION_PATTERNS)


def count_claim_hints(text: str) -> int:
    return len(CLAIM_HINT_RE.findall(text))


def has_uncertainty_marker(text: str) -> bool:
    return bool(UNCERTAINTY_RE.search(text))


def grade_concision(treatment_outputs: list[dict], baseline_outputs: list[dict]) -> list[dict]:
    """Compare word counts of styled vs baseline for concision prompts."""
    # index baseline by (prompt_id, run_number) -> word_count
    baseline_avg: dict[str, float] = {}
    pid_to_counts: dict[str, list[int]] = {}
    for o in baseline_outputs:
        if o["category"] != "concision":
            continue
        wc = o.get("metrics", {}).get("word_count", 0)
        pid_to_counts.setdefault(o["prompt_id"], []).append(wc)
    for pid, counts in pid_to_counts.items():
        baseline_avg[pid] = statistics.mean(counts) if counts else 0

    judgments = []
    for o in treatment_outputs:
        if o["category"] != "concision":
            continue
        pid = o["prompt_id"]
        wc = o.get("metrics", {}).get("word_count", 0)
        b_wc = baseline_avg.get(pid)
        if b_wc is None or b_wc == 0:
            ratio = None
            score = None
            evidence = "No baseline to compare"
        else:
            ratio = wc / b_wc
            # Tolerance: styled ≤ 1.3× baseline is acceptable (1.0 = tied).
            score = 1.0 if ratio <= 1.3 else 0.0
            evidence = f"styled={wc} words; baseline_avg={b_wc:.1f}; ratio={ratio:.2f}"
        judgments.append({
            "category": "concision",
            "prompt_id": pid,
            "run_number": o["run_number"],
            "word_count": wc,
            "baseline_word_count_avg": b_wc,
            "ratio": ratio,
            "score": score,
            "evidence": evidence,
        })
    return judgments


def grade_evidence(treatment_outputs: list[dict]) -> list[dict]:
    """Score citation behavior for evidence prompts.

    score = (citations_or_uncertainty) / max(1, claim_hints)
    Capped at 1.0.

    This is a heuristic. A response with one big "I'm not sure about any of
    this" disclaimer + many specific claims still scores well, which is
    fair: the disclaimer is the responsible behavior.
    """
    judgments = []
    for o in treatment_outputs:
        if o["category"] != "evidence":
            continue
        text = o.get("response", "")
        cites = count_citations(text)
        claims = count_claim_hints(text)
        has_disclaimer = has_uncertainty_marker(text)

        if claims == 0:
            score = None
            evidence = "No code claims detected — heuristic skipped"
        else:
            credit = cites + (claims if has_disclaimer else 0)
            score = min(1.0, credit / claims)
            evidence = (
                f"claim_hints={claims}, citations={cites}, "
                f"uncertainty_marker={'yes' if has_disclaimer else 'no'}, "
                f"score={score:.2f}"
            )
        judgments.append({
            "category": "evidence",
            "prompt_id": o["prompt_id"],
            "run_number": o["run_number"],
            "claim_hints": claims,
            "citations": cites,
            "uncertainty_marker": has_disclaimer,
            "score": score,
            "evidence": evidence,
        })
    return judgments


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--treatment-run", required=True, type=Path, help="Path to results/<styled-run>")
    p.add_argument("--baseline-run", type=Path, default=None, help="Path to results/<baseline-run> (required for concision)")
    args = p.parse_args()

    treat = json.loads((args.treatment_run / "run.json").read_text(encoding="utf-8"))
    treat_outputs = treat.get("outputs", [])

    base_outputs = []
    if args.baseline_run:
        base = json.loads((args.baseline_run / "run.json").read_text(encoding="utf-8"))
        base_outputs = base.get("outputs", [])

    judgments = []
    judgments.extend(grade_concision(treat_outputs, base_outputs))
    judgments.extend(grade_evidence(treat_outputs))

    payload = {
        "graded_at": datetime.now(timezone.utc).isoformat(),
        "treatment_run_id": treat.get("metadata", {}).get("run_id"),
        "baseline_run_id": (
            json.loads((args.baseline_run / "run.json").read_text(encoding="utf-8"))
            .get("metadata", {}).get("run_id")
            if args.baseline_run else None
        ),
        "judgments": judgments,
    }
    out = args.treatment_run / "mechanical_grades.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
