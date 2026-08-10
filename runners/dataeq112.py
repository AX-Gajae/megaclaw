"""이슈 #112 — 837 이 손으로 조립한 영화와 오늘 파이프라인의 영화를 **적합 0회로** 대조한다.

🔴 **결과(2026-08-10)**: 행 887=887 · 축 36=36 · 축 이름 **집합도 순서도 동일** ·
y/yr/t 최대차 **0.0** · **열이 다른 축 0개** · 유보 406=406.
→ **영화 조립은 0.4710 → 0.46982 의 원인이 아니다.** 원인은 `runners/refit112.py`
(채점 배치 + 적합 경로의 random_state)이고 판정문은 `runners/out112_verdict.json`.
"""
import json
import os
import sys

sys.path.insert(0, "/Users/ax/world_model")
os.chdir("/Users/ax/world_model")

import numpy as np
from lab import loop as L

ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
T = 2025.0


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


d0 = L._idol(lambda: dict(base()), mode="cut", with_wiki=True, with_trend=True,
             wide_post=True, wide_pop="grades")

# ── 837 의 손 조립 재현(rebase837.py:17-56) ──────────────────────────────
KA = json.load(open("data/state/kobis_axes.json"))
ids = list(KA)
A = np.array([[KA[i]["axes"][a] for a in ALL5] for i in ids], float)
M = np.array([[KA[i]["mask"][a] for a in ALL5] for i in ids], float)
y = np.array([KA[i]["y"] for i in ids], float)
yr = np.array([float(KA[i]["release_date"][:4]) for i in ids], float)

d11 = {d: d0.names[d] for d in d0.dom if d != "영화"}
common = [a for a in d11[sorted(d11)[0]] if all(a in d11[d] for d in d11)]
idx5 = {a: ALL5.index(a) for a in ALL5}
A_full = np.full((len(ids), len(common)), 0.5)
M_full = np.zeros((len(ids), len(common)))
for j, a in enumerate(common):
    if a in idx5:
        A_full[:, j] = A[:, idx5[a]]
        M_full[:, j] = M[:, idx5[a]]

# ── 오늘 파이프라인의 영화 ────────────────────────────────────────────
A2, M2, y2, t2 = d0.dom["영화"]
nm2 = list(d0.names["영화"])
yr2 = np.asarray(d0.yr["영화"], float)

out = {
    "행 수": {"837 손": len(ids), "오늘": len(y2)},
    "공통 축 수": {"837 common": len(common), "오늘 영화 축": len(nm2)},
    "축 이름 집합 같나": sorted(common) == sorted(nm2),
    "축 이름 순서 같나": common == nm2,
}
if len(y2) == len(ids):
    out["y 최대차"] = float(np.nanmax(np.abs(np.asarray(y2, float) - y)))
    out["y NaN 수"] = [int(np.isnan(y).sum()), int(np.isnan(np.asarray(y2, float)).sum())]
    out["yr 최대차"] = float(np.nanmax(np.abs(yr2 - yr)))
    out["t 최대차"] = float(np.nanmax(np.abs(np.asarray(t2, float) - yr)))
    # 이름별 열 대조
    diffs = {}
    for a in sorted(set(common) & set(nm2)):
        ja, jb = common.index(a), nm2.index(a)
        da = float(np.nanmax(np.abs(A_full[:, ja] - np.asarray(A2, float)[:, jb])))
        dm = float(np.nanmax(np.abs(M_full[:, ja] - np.asarray(M2, float)[:, jb])))
        if da > 0 or dm > 0:
            diffs[a] = {"A 최대차": da, "M 최대차": dm,
                        "837 관측수": int(M_full[:, ja].sum()),
                        "오늘 관측수": int(np.asarray(M2, float)[:, jb].sum())}
    out["열이 다른 축"] = diffs
    out["다른 축 수"] = len(diffs)
# 유보 회계
te = np.isfinite(yr) & (yr >= T)
out["837 영화 유보(~ktr0)"] = int((~(yr < T)).sum())
out["오늘 영화 가중"] = int(d0.weights(T).get("영화", 0))
out["837 영화 유보 중 라벨 유한"] = int((te & np.isfinite(y)).sum())
print(json.dumps(out, ensure_ascii=False, indent=1))
