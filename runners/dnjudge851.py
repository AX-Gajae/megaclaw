# -*- coding: utf-8 -*-
# 노트 851(b) — Δ(n) 수확 판정(통계 층 · 체크포인트만 · 적합 없음)
import json
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
rows = [json.loads(l) for l in open(ROOT / "runners/out848_checkpoint.jsonl")]
grid = sorted({r["n"] for r in rows if r["n"] > 0})
draws = sorted({r["d"] for r in rows if r["n"] > 0})
J = {(r["d"], r["n"]): r["rho_joint"] for r in rows if r["n"] > 0}
R = {(r["d"], r["n"]): r["rho_ridge"] for r in rows if r["n"] > 0}
anchor = next(r["rho_joint"] for r in rows if r["n"] == 0)

print(f"격자 {grid} · 뽑기 {draws} · 앵커(각주용) {anchor}")
tbl = {}
for n in grid:
    js = [J[(d, n)] for d in draws if (d, n) in J]
    rs = [R[(d, n)] for d in draws if (d, n) in R]
    ds = [j - r for j, r in zip(js, rs)]
    tbl[n] = {"joint 평균": round(float(np.mean(js)), 4), "joint SD": round(float(np.std(js, ddof=1)), 4),
              "ridge 평균": round(float(np.mean(rs)), 4), "ridge SD": round(float(np.std(rs, ddof=1)), 4),
              "Δ 평균": round(float(np.mean(ds)), 4), "Δ 양수": f"{sum(x > 0 for x in ds)}/{len(ds)}"}
    print(f"  n={n:>3}: joint {tbl[n]['joint 평균']}±{tbl[n]['joint SD']} · ridge {tbl[n]['ridge 평균']}±{tbl[n]['ridge SD']} · Δ {tbl[n]['Δ 평균']} ({tbl[n]['Δ 양수']})")

n_lo, n_hi = grid[0], grid[-1]
slope_j = [J[(d, n_hi)] - J[(d, n_lo)] for d in draws if (d, n_hi) in J and (d, n_lo) in J]
slope_r = [R[(d, n_hi)] - R[(d, n_lo)] for d in draws if (d, n_hi) in R and (d, n_lo) in R]
sj_pos = sum(x > 0 for x in slope_j)
sr_pos = sum(x > 0 for x in slope_r)
print(f"끝점 기울기(뽑기 짝 {len(slope_j)}): joint {np.mean(slope_j):+.4f} (양 {sj_pos}/{len(slope_j)}) · "
      f"ridge {np.mean(slope_r):+.4f} (양 {sr_pos}/{len(slope_r)})")

# 교차: 뽑기별 Δ 부호가 마지막으로 양인 n
crosses = []
for d in draws:
    neg = [n for n in grid if (d, n) in J and J[(d, n)] - R[(d, n)] <= 0]
    crosses.append(min(neg) if neg else None)
print("뽑기별 첫 Δ≤0 지점:", crosses)

out = {"표": tbl, "joint 끝점 기울기": {"평균": round(float(np.mean(slope_j)), 4), "양수": f"{sj_pos}/{len(slope_j)}"},
       "ridge 끝점 기울기": {"평균": round(float(np.mean(slope_r)), 4), "양수": f"{sr_pos}/{len(slope_r)}"},
       "뽑기별 첫 Δ≤0": crosses, "앵커(각주)": anchor}
json.dump(out, open(ROOT / "runners/out851_judge.json", "w"), ensure_ascii=False, indent=1)
print("저장 완료")
