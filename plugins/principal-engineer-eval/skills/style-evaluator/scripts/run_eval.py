#!/usr/bin/env python3
"""Run output-style evals.

Executes each prompt via `claude -p` with a given output style (or no style
for baseline). Captures responses and timing. Writes results to JSON.

Usage:
    python -m scripts.run_eval --eval-set evals/evals.json --style none --runs 3
    python -m scripts.run_eval --eval-set evals/evals.json --style ../../output-styles/radical-candor-v2.md --runs 3
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


EVAL_SETTINGS_FILENAME = "eval-settings.json"


def install_style(
    style_path: Path | None, project_root: Path
) -> tuple[str | None, Path | None]:
    """Copy the style file into the project's .claude/output-styles/ dir and
    write a sidecar settings file that activates it. Returns
    (style_name, settings_path), with both None for baseline.

    Activation note: the `claude` CLI (verified on v2.1.126) does not expose a
    `--output-style` flag. Output styles activate via the `outputStyle` key in
    a settings JSON loaded with `--settings <path>`. We write a uniquely-named
    `.claude/eval-settings.json` so we never clobber an existing
    `settings.json` / `settings.local.json` in the project.

    Caller is responsible for cleaning up via `uninstall_style`.
    """
    if style_path is None:
        return None, None

    style_path = Path(style_path).expanduser().resolve()
    if not style_path.exists():
        sys.exit(f"Style file not found: {style_path}")

    claude_dir = project_root / ".claude"
    target_dir = claude_dir / "output-styles"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / style_path.name
    shutil.copy(style_path, target)

    # Read the style name from frontmatter (best effort)
    text = style_path.read_text(encoding="utf-8")
    name = style_path.stem
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            for line in text[3:end].splitlines():
                if line.strip().startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                    break

    settings_path = claude_dir / EVAL_SETTINGS_FILENAME
    settings_path.write_text(
        json.dumps({"outputStyle": name}, indent=2), encoding="utf-8"
    )
    return name, settings_path


def uninstall_style(style_path: Path | None, project_root: Path) -> None:
    if style_path is None:
        return
    style_path = Path(style_path).expanduser().resolve()
    target = project_root / ".claude" / "output-styles" / style_path.name
    if target.exists():
        target.unlink()
    settings_path = project_root / ".claude" / EVAL_SETTINGS_FILENAME
    if settings_path.exists():
        settings_path.unlink()


def run_prompt(
    prompt_text: str,
    settings_path: Path | None,
    model: str | None,
    timeout: int,
) -> dict:
    """Run a single prompt via `claude -p` and return the response + metrics."""
    cmd = ["claude", "-p", prompt_text, "--output-format", "json"]
    if model:
        cmd.extend(["--model", model])
    if settings_path:
        cmd.extend(["--settings", str(settings_path)])

    env = os.environ.copy()
    # Avoid recursive-claude-code complications
    env.pop("CLAUDECODE", None)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        duration = time.time() - start
        if result.returncode != 0:
            return {
                "response": "",
                "duration_seconds": duration,
                "errors": [f"non-zero exit ({result.returncode}): {result.stderr[:500]}"],
                "tokens_in": None,
                "tokens_out": None,
            }
        # Parse JSON output from claude -p
        try:
            payload = json.loads(result.stdout)
            response_text = payload.get("result", payload.get("response", result.stdout))
            usage = payload.get("usage", {}) or {}
            return {
                "response": response_text,
                "duration_seconds": duration,
                "errors": [],
                "tokens_in": usage.get("input_tokens"),
                "tokens_out": usage.get("output_tokens"),
            }
        except json.JSONDecodeError:
            # Fallback: treat raw stdout as the response
            return {
                "response": result.stdout,
                "duration_seconds": duration,
                "errors": [],
                "tokens_in": None,
                "tokens_out": None,
            }
    except subprocess.TimeoutExpired:
        return {
            "response": "",
            "duration_seconds": timeout,
            "errors": [f"timeout after {timeout}s"],
            "tokens_in": None,
            "tokens_out": None,
        }


def run_multi_turn(
    turns: list[str],
    settings_path: Path | None,
    model: str | None,
    timeout: int,
) -> dict:
    """Run a multi-turn prompt by chaining responses.

    Note: `claude -p` is stateless by default; we use `--resume` with a
    session id captured from the first turn's metadata. If your version of
    claude-code uses different flags, adjust here.
    """
    cmd_base = ["claude", "-p", "--output-format", "json"]
    if model:
        cmd_base.extend(["--model", model])
    if settings_path:
        cmd_base.extend(["--settings", str(settings_path)])

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    full_response = ""
    session_id = None
    total_duration = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    errors: list[str] = []

    for i, turn_text in enumerate(turns):
        cmd = list(cmd_base)
        if session_id and i > 0:
            cmd.extend(["--resume", session_id])
        cmd.append(turn_text)

        start = time.time()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, env=env
            )
            total_duration += time.time() - start
            if result.returncode != 0:
                errors.append(f"turn {i+1}: exit {result.returncode}: {result.stderr[:300]}")
                break
            try:
                payload = json.loads(result.stdout)
                response_text = payload.get("result", payload.get("response", ""))
                session_id = payload.get("session_id") or session_id
                usage = payload.get("usage", {}) or {}
                total_tokens_in += usage.get("input_tokens") or 0
                total_tokens_out += usage.get("output_tokens") or 0
                full_response += f"\n\n--- TURN {i+1} ---\n{response_text}"
            except json.JSONDecodeError:
                full_response += f"\n\n--- TURN {i+1} (raw) ---\n{result.stdout}"
        except subprocess.TimeoutExpired:
            errors.append(f"turn {i+1}: timeout after {timeout}s")
            break

    return {
        "response": full_response.strip(),
        "duration_seconds": total_duration,
        "errors": errors,
        "tokens_in": total_tokens_in or None,
        "tokens_out": total_tokens_out or None,
    }


def expand_prompts(eval_set: dict) -> list[dict]:
    """Flatten the eval set into individual run units."""
    units = []
    for cat_name, cat in eval_set["categories"].items():
        for prompt_def in cat["prompts"]:
            unit = {
                "category": cat_name,
                "prompt_id": prompt_def["id"],
                "is_multi_turn": "turns" in prompt_def,
                "prompt_or_turns": prompt_def.get("turns") or prompt_def.get("prompt", ""),
                "metadata": {k: v for k, v in prompt_def.items() if k not in ("id", "prompt", "turns")},
            }
            units.append(unit)
    return units


def execute_unit(unit: dict, run_number: int, settings_path: Path | None, model: str | None, timeout: int) -> dict:
    if unit["is_multi_turn"]:
        result = run_multi_turn(unit["prompt_or_turns"], settings_path, model, timeout)
    else:
        result = run_prompt(unit["prompt_or_turns"], settings_path, model, timeout)

    word_count = len(result["response"].split()) if result["response"] else 0
    return {
        "category": unit["category"],
        "prompt_id": unit["prompt_id"],
        "run_number": run_number,
        "prompt": unit["prompt_or_turns"] if not unit["is_multi_turn"] else " | ".join(unit["prompt_or_turns"]),
        "response": result["response"],
        "metrics": {
            "word_count": word_count,
            "duration_seconds": round(result["duration_seconds"], 2),
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
        },
        "errors": result["errors"],
        "metadata": unit["metadata"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Run output-style evals.")
    p.add_argument("--eval-set", required=True, type=Path, help="Path to evals.json")
    p.add_argument("--style", required=True, help="Path to .md style file, or 'none' for baseline")
    p.add_argument("--runs", type=int, default=3, help="Runs per prompt (default 3)")
    p.add_argument("--model", default=None, help="Model id passed to `claude -p`")
    p.add_argument("--timeout", type=int, default=120, help="Per-prompt timeout in seconds")
    p.add_argument("--parallel", type=int, default=4, help="Parallel workers")
    p.add_argument("--output-dir", type=Path, default=Path("results"))
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    args = p.parse_args()

    eval_set = json.loads(args.eval_set.read_text(encoding="utf-8"))
    style_path = None if args.style.lower() == "none" else Path(args.style)

    # Install style locally so the session uses it
    style_name, settings_path = install_style(style_path, args.project_root)
    print(f"Style: {style_name or '<baseline, no style>'}", flush=True)
    if settings_path:
        print(f"Settings (activates style): {settings_path}", flush=True)

    units = expand_prompts(eval_set)
    print(f"Loaded {len(units)} prompts × {args.runs} runs = {len(units) * args.runs} executions", flush=True)

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{'baseline' if style_name is None else style_name}"
    out_dir = args.output_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    started = now_iso()
    outputs: list[dict] = []

    work = [(u, r) for u in units for r in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(execute_unit, u, r, settings_path, args.model, args.timeout): (u["prompt_id"], r)
            for u, r in work
        }
        completed = 0
        total = len(futures)
        for fut in as_completed(futures):
            pid, rn = futures[fut]
            try:
                outputs.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                outputs.append({
                    "category": "ERROR",
                    "prompt_id": pid,
                    "run_number": rn,
                    "errors": [f"executor exception: {exc!r}"],
                })
            completed += 1
            if completed % 5 == 0 or completed == total:
                print(f"  progress: {completed}/{total}", flush=True)

    # Cleanup
    uninstall_style(style_path, args.project_root)

    out = {
        "metadata": {
            "run_id": run_id,
            "style_path": str(style_path) if style_path else None,
            "style_name": style_name,
            "model": args.model,
            "runs_per_prompt": args.runs,
            "started_at": started,
            "completed_at": now_iso(),
            "eval_set": str(args.eval_set),
        },
        "outputs": outputs,
    }
    (out_dir / "run.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_dir / 'run.json'}", flush=True)


if __name__ == "__main__":
    main()
