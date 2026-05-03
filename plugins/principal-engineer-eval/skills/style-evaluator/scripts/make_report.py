#!/usr/bin/env python3
"""Render a self-contained HTML report comparing one or more eval runs.

Reads the `run.json` files produced by `scripts.run_eval` and emits a single
HTML file with:
  - Per-config aggregate stats (n, errors, mean word count, total tokens, total duration)
  - Per-category sections with prompts grouped underneath
  - For each prompt: side-by-side responses across configs, with word/token
    metrics shown as badges. Long responses are collapsed by default.

No external dependencies (no CDN, no build step). Works offline.

Usage:
    # Render all runs found under ./results (default)
    python -m scripts.make_report

    # Render specific run directories or run.json files
    python -m scripts.make_report --runs results/<dir1> results/<dir2>

    # Custom output path
    python -m scripts.make_report --out results/report.html
"""

from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable


def discover_runs(results_dir: Path) -> list[Path]:
    """Find run.json files under a results directory, sorted by name (timestamp-prefixed)."""
    if not results_dir.exists():
        return []
    return sorted(results_dir.glob("*/run.json"))


def load_run(path: Path) -> dict:
    """Load a single run, accepting either a directory (containing run.json) or the json file directly."""
    p = path / "run.json" if path.is_dir() else path
    if not p.exists():
        sys.exit(f"run.json not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    label = data.get("metadata", {}).get("style_name") or "baseline"
    return {
        "label": label,
        "path": str(p),
        "metadata": data.get("metadata", {}),
        "outputs": data.get("outputs", []),
    }


def aggregate(run: dict) -> dict:
    outs = run["outputs"]
    words = [o["metrics"]["word_count"] for o in outs]
    toks = [(o["metrics"].get("tokens_out") or 0) for o in outs]
    durs = [o["metrics"]["duration_seconds"] for o in outs]
    errs = sum(1 for o in outs if o.get("errors"))
    return {
        "n": len(outs),
        "errors": errs,
        "word_mean": statistics.mean(words) if words else 0,
        "word_median": statistics.median(words) if words else 0,
        "tokens_sum": sum(toks),
        "tokens_mean": (statistics.mean(toks) if toks else 0),
        "duration_sum": sum(durs),
    }


def organize(runs: list[dict]) -> dict:
    """Build {category: {prompt_id: {prompt_text, by_label: {label: [outputs sorted by run_number]}}}}."""
    by_cat: dict = {}
    for r in runs:
        for o in r["outputs"]:
            cat = o["category"]
            pid = o["prompt_id"]
            cat_block = by_cat.setdefault(cat, {})
            prompt_block = cat_block.setdefault(
                pid,
                {"prompt_text": o.get("prompt", ""), "by_label": {}},
            )
            prompt_block["by_label"].setdefault(r["label"], []).append(o)
    # Sort each label's outputs by run_number for stable display
    for cat in by_cat.values():
        for pblock in cat.values():
            for label, outs in pblock["by_label"].items():
                outs.sort(key=lambda o: o.get("run_number", 1))
    return by_cat


CSS = """
:root {
  --bg: #0f1115;
  --bg-2: #161922;
  --bg-3: #1d2230;
  --fg: #e6e8ef;
  --fg-dim: #9aa1b5;
  --accent: #7aa2f7;
  --accent-2: #bb9af7;
  --good: #9ece6a;
  --warn: #e0af68;
  --bad: #f7768e;
  --border: #2a2f3d;
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  font-size: 14px; line-height: 1.5; }
header { position: sticky; top: 0; z-index: 10; background: var(--bg-2);
  border-bottom: 1px solid var(--border); padding: 14px 20px; }
header h1 { margin: 0 0 6px 0; font-size: 18px; font-weight: 600; }
header .meta { color: var(--fg-dim); font-size: 12px; }
header nav { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
header nav a { color: var(--accent); text-decoration: none; padding: 3px 9px;
  border: 1px solid var(--border); border-radius: 4px; font-size: 12px; }
header nav a:hover { background: var(--bg-3); }
main { padding: 20px; max-width: 1600px; margin: 0 auto; }
section.summary { margin-bottom: 30px; }
section.summary h2, section.category h2 { font-size: 15px; font-weight: 600;
  margin: 0 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
table.summary { width: 100%; border-collapse: collapse; background: var(--bg-2);
  border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
table.summary th, table.summary td { padding: 8px 12px; text-align: left;
  border-bottom: 1px solid var(--border); font-size: 13px; }
table.summary th { background: var(--bg-3); color: var(--fg-dim);
  font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; }
table.summary tr:last-child td { border-bottom: none; }
table.summary td.num { font-family: var(--mono); text-align: right; }
table.summary td.label { font-weight: 600; color: var(--accent); }
section.category { margin-bottom: 36px; }
.cat-desc { color: var(--fg-dim); font-size: 12px; margin: -4px 0 14px 0; }
details.prompt { background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 4px; margin-bottom: 14px; overflow: hidden; }
details.prompt summary { padding: 10px 14px; cursor: pointer; user-select: none;
  font-family: var(--mono); font-size: 12px; color: var(--fg-dim);
  background: var(--bg-3); list-style: none; }
details.prompt summary::-webkit-details-marker { display: none; }
details.prompt summary::before { content: "▸"; display: inline-block;
  margin-right: 8px; transition: transform 0.15s; }
details.prompt[open] summary::before { transform: rotate(90deg); }
details.prompt summary .pid { color: var(--accent-2); font-weight: 600; margin-right: 10px; }
details.prompt summary .preview { color: var(--fg); }
.prompt-body { padding: 14px; }
.prompt-text { background: var(--bg); padding: 10px 12px; border-left: 3px solid var(--accent);
  margin-bottom: 14px; font-family: var(--mono); font-size: 12px; white-space: pre-wrap;
  word-break: break-word; }
.cells { display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.cell { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; }
.cell .head { padding: 7px 10px; background: var(--bg-3);
  border-bottom: 1px solid var(--border); display: flex; align-items: center;
  justify-content: space-between; gap: 8px; font-size: 12px; }
.cell .head .label { color: var(--accent); font-weight: 600; }
.cell .badges { display: flex; gap: 6px; }
.badge { font-family: var(--mono); font-size: 11px; padding: 1px 7px;
  border-radius: 3px; background: var(--bg-2); border: 1px solid var(--border);
  color: var(--fg-dim); }
.badge.good { color: var(--good); border-color: rgba(158,206,106,0.4); }
.badge.warn { color: var(--warn); border-color: rgba(224,175,104,0.4); }
.badge.bad { color: var(--bad); border-color: rgba(247,118,142,0.4); }
.run-block { padding: 10px 12px; border-top: 1px solid var(--border); }
.run-block:first-of-type { border-top: none; }
.run-tag { display: inline-block; font-family: var(--mono); font-size: 10px;
  color: var(--fg-dim); padding: 1px 5px; background: var(--bg-2);
  border-radius: 2px; margin-bottom: 6px; }
.response { font-family: var(--mono); font-size: 12px; white-space: pre-wrap;
  word-break: break-word; max-height: 300px; overflow-y: auto; color: var(--fg); }
.response.expanded { max-height: none; }
.expand-btn { font-size: 11px; color: var(--accent); background: none; border: none;
  cursor: pointer; padding: 4px 0 0 0; font-family: inherit; }
.error-msg { color: var(--bad); font-family: var(--mono); font-size: 12px; padding: 8px; }
footer { text-align: center; color: var(--fg-dim); font-size: 11px;
  padding: 20px; border-top: 1px solid var(--border); }
"""


JS = """
document.addEventListener('click', (e) => {
  if (e.target.matches('.expand-btn')) {
    const resp = e.target.previousElementSibling;
    resp.classList.toggle('expanded');
    e.target.textContent = resp.classList.contains('expanded') ? 'collapse' : 'expand';
  }
});
"""


def _badge_class(value: float, baseline: float | None, *, lower_is_good: bool) -> str:
    if baseline is None or baseline == 0:
        return ""
    delta_pct = (value - baseline) / baseline
    threshold = 0.10
    if abs(delta_pct) < threshold:
        return ""
    is_better = (delta_pct < 0) if lower_is_good else (delta_pct > 0)
    return "good" if is_better else "warn"


def render_summary(runs: list[dict]) -> str:
    rows = []
    aggs = {r["label"]: aggregate(r) for r in runs}
    baseline_agg = aggs.get("baseline")
    for r in runs:
        a = aggs[r["label"]]
        word_cls = _badge_class(
            a["word_mean"],
            baseline_agg["word_mean"] if baseline_agg else None,
            lower_is_good=True,
        )
        tok_cls = _badge_class(
            a["tokens_mean"],
            baseline_agg["tokens_mean"] if baseline_agg else None,
            lower_is_good=True,
        )
        rows.append(
            f"<tr>"
            f"<td class='label'>{html.escape(r['label'])}</td>"
            f"<td class='num'>{a['n']}</td>"
            f"<td class='num'>{a['errors']}</td>"
            f"<td class='num {word_cls}'>{a['word_mean']:.0f}</td>"
            f"<td class='num'>{a['word_median']:.0f}</td>"
            f"<td class='num {tok_cls}'>{a['tokens_mean']:.0f}</td>"
            f"<td class='num'>{a['tokens_sum']:,}</td>"
            f"<td class='num'>{a['duration_sum']:.0f}s</td>"
            f"</tr>"
        )
    return (
        "<section class='summary'><h2>Run summary</h2>"
        "<table class='summary'><thead><tr>"
        "<th>Config</th><th>n</th><th>errors</th>"
        "<th>mean words</th><th>median words</th>"
        "<th>mean tokens_out</th><th>sum tokens_out</th>"
        "<th>total wall</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></section>"
    )


def render_prompt(pid: str, pblock: dict, run_labels: list[str], baseline_metrics: dict | None) -> str:
    prompt_preview = " ".join(pblock["prompt_text"].split())[:120]
    prompt_text = pblock["prompt_text"]

    cells = []
    for label in run_labels:
        outs = pblock["by_label"].get(label, [])
        if not outs:
            cells.append(
                f"<div class='cell'><div class='head'><span class='label'>{html.escape(label)}</span></div>"
                f"<div class='error-msg'>(no output for this prompt)</div></div>"
            )
            continue

        # Aggregate across runs for this cell's badges
        words = sum(o["metrics"]["word_count"] for o in outs) / len(outs)
        toks = sum((o["metrics"].get("tokens_out") or 0) for o in outs) / len(outs)
        word_cls = _badge_class(
            words, baseline_metrics["words"] if baseline_metrics else None, lower_is_good=True
        )
        tok_cls = _badge_class(
            toks, baseline_metrics["tokens"] if baseline_metrics else None, lower_is_good=True
        )

        run_blocks = []
        for o in outs:
            errs = o.get("errors") or []
            err_html = (
                f"<div class='error-msg'>{html.escape(' | '.join(errs))}</div>" if errs else ""
            )
            run_tag = (
                f"<span class='run-tag'>run {o.get('run_number', 1)}</span>"
                if len(outs) > 1
                else ""
            )
            response_text = html.escape(o.get("response") or "")
            run_blocks.append(
                f"<div class='run-block'>{run_tag}"
                f"{err_html}"
                f"<div class='response'>{response_text}</div>"
                f"<button class='expand-btn'>expand</button>"
                f"</div>"
            )

        cells.append(
            f"<div class='cell'>"
            f"<div class='head'>"
            f"<span class='label'>{html.escape(label)}</span>"
            f"<span class='badges'>"
            f"<span class='badge {word_cls}'>{words:.0f}w</span>"
            f"<span class='badge {tok_cls}'>{toks:.0f}t</span>"
            f"</span>"
            f"</div>"
            + "".join(run_blocks)
            + "</div>"
        )

    return (
        f"<details class='prompt'><summary>"
        f"<span class='pid'>{html.escape(pid)}</span>"
        f"<span class='preview'>{html.escape(prompt_preview)}</span>"
        f"</summary>"
        f"<div class='prompt-body'>"
        f"<div class='prompt-text'>{html.escape(prompt_text)}</div>"
        f"<div class='cells'>{''.join(cells)}</div>"
        f"</div></details>"
    )


def render_categories(by_cat: dict, runs: list[dict]) -> tuple[str, list[tuple[str, int]]]:
    run_labels = [r["label"] for r in runs]
    nav_entries = []
    sections = []
    for cat in sorted(by_cat.keys()):
        prompts = by_cat[cat]
        nav_entries.append((cat, len(prompts)))

        # Compute baseline metrics per prompt for relative coloring
        prompt_html = []
        for pid in sorted(prompts.keys()):
            pblock = prompts[pid]
            baseline_outs = pblock["by_label"].get("baseline", [])
            baseline_metrics = None
            if baseline_outs:
                baseline_metrics = {
                    "words": sum(o["metrics"]["word_count"] for o in baseline_outs) / len(baseline_outs),
                    "tokens": sum((o["metrics"].get("tokens_out") or 0) for o in baseline_outs) / len(baseline_outs),
                }
            prompt_html.append(render_prompt(pid, pblock, run_labels, baseline_metrics))

        sections.append(
            f"<section class='category' id='cat-{html.escape(cat)}'>"
            f"<h2>{html.escape(cat)} <span style='color:var(--fg-dim);font-weight:400;'>"
            f"({len(prompts)} prompts)</span></h2>"
            + "".join(prompt_html)
            + "</section>"
        )
    return "".join(sections), nav_entries


def render_html(runs: list[dict]) -> str:
    if not runs:
        return "<html><body>No runs found.</body></html>"

    by_cat = organize(runs)
    cat_html, nav_entries = render_categories(by_cat, runs)
    summary_html = render_summary(runs)

    earliest = min((r["metadata"].get("started_at") or "") for r in runs)
    latest = max((r["metadata"].get("completed_at") or "") for r in runs)
    eval_set = runs[0]["metadata"].get("eval_set", "")
    runs_per_prompt = runs[0]["metadata"].get("runs_per_prompt", 1)
    total_prompts = sum(n for _, n in nav_entries)

    nav_html = "".join(
        f"<a href='#cat-{html.escape(cat)}'>{html.escape(cat)} ({n})</a>"
        for cat, n in nav_entries
    )

    run_labels_pretty = ", ".join(r["label"] for r in runs)

    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<title>style-evaluator report</title>
<style>{CSS}</style>
</head><body>
<header>
  <h1>style-evaluator report</h1>
  <div class='meta'>
    {len(runs)} configs ({html.escape(run_labels_pretty)}) ·
    {total_prompts} prompts · {runs_per_prompt} runs/prompt ·
    eval set: {html.escape(eval_set)} ·
    {html.escape(earliest)} → {html.escape(latest)}
  </div>
  <nav>{nav_html}</nav>
</header>
<main>
  {summary_html}
  {cat_html}
</main>
<footer>
  Word/token badges color-coded vs baseline (≥10% delta): green = lower (better for concision), amber = higher.
  Click <code>expand</code> on any response to show full text.
</footer>
<script>{JS}</script>
</body></html>"""


def main() -> None:
    p = argparse.ArgumentParser(description="Render an HTML comparison report from eval runs.")
    p.add_argument(
        "--runs",
        nargs="+",
        type=Path,
        default=None,
        help="One or more run directories (containing run.json) or run.json paths. "
             "If omitted, all run.json under ./results are used.",
    )
    p.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory to discover runs under when --runs is not given (default: ./results)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path (default: <results-dir>/report.html)",
    )
    args = p.parse_args()

    if args.runs:
        run_paths = args.runs
    else:
        run_paths = discover_runs(args.results_dir)
        if not run_paths:
            sys.exit(f"No run.json files found under {args.results_dir}/")

    runs = [load_run(p) for p in run_paths]

    out_path = args.out or (args.results_dir / "report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(runs), encoding="utf-8")
    print(f"Wrote report: {out_path}")
    print(f"  {len(runs)} configs: {', '.join(r['label'] for r in runs)}")


if __name__ == "__main__":
    main()
