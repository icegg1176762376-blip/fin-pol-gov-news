#!/usr/bin/env python3
"""
Unified data collection pipeline for fin-pol-gov-news.

Runs RSS and Web fetch steps, then merges + deduplicates + scores into a single output JSON.
Optimized for government policy and financial regulation news.

Usage:
 python3 run-pipeline.py \
 --defaults config/defaults \
 --hours 48 --freshness pd \
 --output /tmp/fin-pol-merged.json \
 --verbose
"""

import json
import sys
import os
import subprocess
import time
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any

SCRIPTS_DIR = Path(__file__).parent
DEFAULT_TIMEOUT = 180

def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(__name__)

def run_step(name: str, script: str, args_list: list, output_path: Path, timeout: int = DEFAULT_TIMEOUT, force: bool = False) -> Dict[str, Any]:
    """Run a fetch script as a subprocess, return result metadata."""
    t0 = time.time()
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args_list + ["--output", str(output_path)]
    if force:
        cmd.append("--force")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=os.environ)
        elapsed = time.time() - t0
        ok = result.returncode == 0
        
        count = 0
        if ok and output_path.exists():
            try:
                with open(output_path) as f:
                    data = json.load(f)
                    count = data.get("total_articles") or data.get("total_results") or 0
            except (json.JSONDecodeError, OSError):
                pass
        
        return {
            "name": name,
            "status": "ok" if ok else "error",
            "elapsed_s": round(elapsed, 1),
            "count": count,
            "stderr_tail": (result.stderr or "").strip().split("\n")[-3:] if not ok else [],
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return {
            "name": name,
            "status": "timeout",
            "elapsed_s": round(elapsed, 1),
            "count": 0,
            "stderr_tail": [f"Killed after {timeout}s"],
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "name": name,
            "status": "error",
            "elapsed_s": round(elapsed, 1),
            "count": 0,
            "stderr_tail": [str(e)],
        }

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fin-pol-gov-news data pipeline.")
    _script_dir = Path(__file__).resolve().parent
    _default_defaults = _script_dir.parent / "config" / "defaults"
    
    parser.add_argument("--defaults", type=Path, default=_default_defaults)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--freshness", type=str, default="pd")
    parser.add_argument("--output", "-o", type=Path, default=Path("/tmp/fin-pol-merged.json"))
    parser.add_argument("--step-timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--force", action="store_true")
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    import tempfile
    _run_dir = tempfile.mkdtemp(prefix="fin-pol-pipeline-")
    tmp_rss = Path(_run_dir) / "rss.json"
    tmp_web = Path(_run_dir) / "web.json"
    
    logger.info(f"📁 Run directory: {_run_dir}")
    
    # Common args
    common = ["--defaults", str(args.defaults)]
    if args.config:
        common += ["--config", str(args.config)]
    common += ["--hours", str(args.hours)]
    verbose_flag = ["--verbose"] if args.verbose else []
    
    # Define steps: RSS + Web only
    steps = [
        ("RSS", "fetch-rss.py", common + verbose_flag, tmp_rss),
        ("Web", "fetch-web.py", ["--defaults", str(args.defaults)] + (["--config", str(args.config)] if args.config else []) + ["--freshness", args.freshness] + verbose_flag, tmp_web),
    ]
    
    logger.info(f"🚀 Starting pipeline: {len(steps)} sources, {args.hours}h window")
    t_start = time.time()
    
    # Phase 1: Parallel fetch
    step_results = []
    with ThreadPoolExecutor(max_workers=len(steps)) as pool:
        futures = {}
        for name, script, step_args, out_path in steps:
            f = pool.submit(run_step, name, script, step_args, out_path, args.step_timeout, args.force)
            futures[f] = name
        
        for future in as_completed(futures):
            res = future.result()
            step_results.append(res)
            status_icon = {"ok": "✅", "error": "❌", "timeout": "⏰"}.get(res["status"], "?")
            logger.info(f" {status_icon} {res['name']}: {res['count']} items ({res['elapsed_s']}s)")
    
    fetch_elapsed = time.time() - t_start
    logger.info(f"📡 Fetch phase done in {fetch_elapsed:.1f}s")
    
    # Phase 2: Merge
    logger.info("🔀 Merging & scoring...")
    merge_args = ["--verbose"] if args.verbose else []
    for flag, path in [("--rss", tmp_rss), ("--web", tmp_web)]:
        if path.exists():
            merge_args += [flag, str(path)]
    merge_args += ["--output", str(args.output)]
    
    merge_result = run_step("Merge", "merge-sources.py", merge_args, args.output, timeout=60)
    
    status_icon = {"ok": "✅", "error": "❌"}.get(merge_result["status"], "?")
    logger.info(f" {status_icon} Merge: {merge_result['count']} items ({merge_result['elapsed_s']}s)")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Pipeline Summary")
    print("=" * 50)
    for res in step_results:
        print(f"{res['name']} ok {res['count']} items {res['elapsed_s']}s")
    print(f"Merge ok {merge_result['count']} items {merge_result['elapsed_s']}s")
    print(f"Output: {args.output}")
    
    return 0 if merge_result["status"] == "ok" else 1

if __name__ == "__main__":
    sys.exit(main())
