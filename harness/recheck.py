"""라벨·피처가 바뀐 뒤 한 번에 다시 재는 드라이버.

라벨을 고치면 그 뒤로 줄줄이 다시 계산해야 하는데, 순서를 틀리면 조용히 옛 값으로
측정한다. 실제로 이 세션에서 두 번 겪었다 — 스코프 유도 전에 절제를 돌려 무의미한
널을 얻었고, gbdt가 상수인 줄 모르고 CI[0,0]을 '기여 없음'으로 읽었다.

순서 (앞이 뒤의 입력이다):
  1) 파생      달력 → 라벨 스코프          (레코드 자체를 갱신)
  2) 감사      위생 게이트 전수            (무엇이 채점 가능한지)
  3) 빌드      학습 테이블                 (갱신된 레코드에서)
  4) 기준선    내부 전용 레인 비교          (상수를 이기는가)
  5) 절제      장부의 검정 대상 재검정      (기여가 남아 있는가)

사용: python3 -m harness.recheck [--ablate t1_ cal_ ...]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def run(desc: str, cmd: list[str]) -> None:
    print(f"\n── {desc} " + "─" * max(0, 56 - len(desc)))
    r = subprocess.run([sys.executable, "-m", *cmd], capture_output=True, text=True)
    out = (r.stdout or "").strip().splitlines()
    for line in out[:6]:
        print("  " + line)
    if len(out) > 6:
        print(f"  … 외 {len(out)-6}줄")
    if r.returncode:
        print("  ⚠️ " + (r.stderr or "").strip().splitlines()[-1][:150])


def baseline(domain: str = "popup", only: str = "popup_internal", axis: str = "per_day") -> dict:
    import numpy as np

    from state.evaluate import LANES, _col, group_time_folds, paired_bootstrap

    d = np.load(f"data/state/{domain}_v2.npz", allow_pickle=True)
    X, cols = d["X"], list(d["names"])
    y = d["y_perday"] if axis == "per_day" else d["y_total"]
    w = d["w"]
    meta = json.loads(Path(f"data/state/{domain}_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in ("A", "B"):
        i = _col(cols, f"trust_{g}")
        if i is not None:
            keep |= X[:, i] > 0.5
    ok = np.isfinite(y) & keep
    if only:
        ok &= np.array([str(m.get("domain", "")).startswith(only) for m in meta])
    X, y, w = X[ok], y[ok], w[ok]
    meta = [m for m, k in zip(meta, ok) if k]
    folds = group_time_folds(np.array([m.get("ip") or m["id"] for m in meta]),
                             np.array([m.get("date") or "9999" for m in meta]))
    errs = {L: [] for L in ("const", "days", "ridge", "gbdt")}
    for tr, te in folds:
        for L in errs:
            errs[L].append(np.abs(LANES[L](X[tr], y[tr], w[tr], X[te], cols) - y[te]))
    cat = {L: np.concatenate(v) for L, v in errs.items()}
    print(f"\n── 기준선 ({only or '전체'} · {axis} · n={len(y)} · 폴드 {len(folds)}) " + "─" * 8)
    print(f"   {'레인':8s} {'MAE':>8s} {'배율':>7s}   vs 상수")
    res = {}
    for L in ("const", "days", "ridge", "gbdt"):
        m = float(cat[L].mean())
        res[L] = m
        if L == "const":
            print(f"   {L:8s} {m:8.4f} {10**m:7.2f}배   —")
        else:
            dm, lo, hi = paired_bootstrap(cat[L], cat["const"])
            win = "✅ 이김" if hi < 0 else ("무승부" if lo < 0 < hi else "❌ 짐")
            print(f"   {L:8s} {m:8.4f} {10**m:7.2f}배   Δ{dm:+.4f} CI[{lo:+.4f},{hi:+.4f}] {win}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablate", nargs="*", default=["t1_", "cal_", "cap_per_day"])
    ap.add_argument("--skip-derive", action="store_true")
    a = ap.parse_args()

    if not a.skip_derive:
        run("달력 파생", ["ingest.calendar_features", "--write"])
        run("라벨 스코프 유도", ["ingest.label_scope", "--write"])
    run("위생 감사", ["harness.label_hygiene", "audit"])
    run("학습 테이블 빌드", ["state.dataset_v2", "--domain", "popup"])
    baseline()

    print("\n── 절제 검정 " + "─" * 48)
    from .discovery import verify
    for pre in a.ablate:
        for lane in ("ridge", "gbdt"):
            try:
                verify(pre, lane=lane, axis="per_day", only="popup_internal")
            except SystemExit as e:
                print(f"  {pre}[{lane}] 건너뜀 — {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
