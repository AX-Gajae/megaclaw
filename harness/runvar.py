"""Run variance 실측 — 같은 타깃·같은 조건을 반복 예측해 실행 간 분산을 정량화.

사용: python3 -m harness.runvar --run-dir cycle_log/runvar/A-2 --targets C1,C2 [--state-file F]
각 타깃을 backtest CLI로 순차 실행(예측→봉인→채점), 완료 후 APE 요약 JSON 출력.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--state-file", default=None)
    args = ap.parse_args()

    targets = args.targets.split(",")
    for c in targets:
        cmd = [sys.executable, "-m", "harness.backtest", "--records", "data/records",
               "--cycle-dir", args.run_dir, "--holdout", c, "--predictor", "llm", "--auto"]
        if args.state_file:
            cmd += ["--state-file", args.state_file]
        r = subprocess.run(cmd, capture_output=True, text=True)
        status = "ok" if r.returncode == 0 else f"FAIL rc={r.returncode}"
        print(f"{c}: {status}", flush=True)
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-400:], flush=True)

    # 요약: visitors APE per target
    out = {}
    for c in targets:
        f = Path(args.run_dir) / f"{c}.report.md"
        commit = Path(args.run_dir) / f"{c}.commit.json"
        if commit.exists():
            pred = json.loads(commit.read_text())["prediction"]["totals"].get("visitors", {})
            sys.path.insert(0, ".")
            from harness.records import load_records
            rec = next((r for r in load_records("data/records") if r.record_id == c), None)
            actual = rec.data["outcome"]["totals"].get("visitors") if rec else None
            if actual and pred.get("point") is not None:
                out[c] = {"point": pred["point"], "actual": actual,
                           "ape": round(abs(pred["point"] - actual) / actual, 4),
                           "covered": bool(pred.get("low") is not None and pred["low"] <= actual <= pred["high"])}
    summary = Path(args.run_dir) / "runvar_summary.json"
    summary.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    apes = sorted(v["ape"] for v in out.values())
    med = apes[len(apes)//2] if apes else None
    print(json.dumps({"run_dir": args.run_dir, "n": len(out),
                       "median_ape": med, "apes": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
