# -*- coding: utf-8 -*-
"""지평 900 — 레버 8개 표를 실측으로. 적합 없이 build 만 한다(설계행 수 제외)."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/Users/ax/world_model"); sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF
from lab import forms as FORMS, fixaxes as FX
from lab.harness import Data, MIN_TRAIN
import axesdie899 as A899
nuniq = A899.nuniq
T = 2025.0
ROOT = Path("/Users/ax/world_model")

post_only = {}
d1 = FF.shell(FF.base())                       # fixaxes 적용
ap, orient = FX.apply, FX.orient
FX.apply = lambda d: d; FX.orient = lambda d: d
try:
    d0 = FF.shell(FF.base())                   # fixaxes 없이
finally:
    FX.apply, FX.orient = ap, orient

train = {}
for d in d1.dom:
    k = (np.isfinite(d1.yr[d]) & (d1.yr[d] < T) & np.isfinite(d1.dom[d][2]))
    if k.sum() >= MIN_TRAIN:
        train[d] = d1.slice(d, k)
tr = Data(train, d1.names, {d: d1.yr[d][np.isfinite(d1.yr[d]) & (d1.yr[d] < T)
                                        & np.isfinite(d1.dom[d][2])] for d in train})
common = FORMS.axis_order(tr, "common")
union = FORMS.axis_order(tr, "union")
W = d1.weights(T)

TARGET = {"시장팝업": ["entry_friction"],
          "게임": ["price", "n_category", "ram_gb", "age_rating",
                   "entry_friction", "venue_prominence"],
          "펀딩": ["trend_level", "trend_momentum", "trend_volatility"],
          "웹툰": ["entry_friction", "goods_scale"]}

res = {"AXIS_MODE": FORMS.AXIS_MODE, "common 열 수": len(common),
       "union 열 수": len(union), "union 에만": [a for a in union if a not in common],
       "판 가중": {d: int(W.get(d, 0)) for d in sorted(d1.dom)}, "도메인": {}}

for d, axes in TARGET.items():
    nm = list(d1.names.get(d) or [])
    nm0 = list(d0.names.get(d) or [])
    A, M, y, t = d1.dom[d]
    A0, M0 = d0.dom[d][0], d0.dom[d][1]
    yr = np.asarray(d1.yr[d], float)
    hold = np.isfinite(yr) & (yr >= T) & np.isfinite(np.asarray(y, float))
    trm = np.isfinite(yr) & (yr < T) & np.isfinite(np.asarray(y, float))
    out = {"축 이름 수": len(nm), "채점행(유보·라벨)": int(hold.sum()),
           "학습행": int(trm.sum()), "판 가중": int(W.get(d, 0)), "축": {}}
    for a in axes:
        if a not in nm:
            out["축"][a] = {"🔴 이 도메인 축 이름에 없다": True,
                            "fixaxes 이전 이름에 있나": a in nm0}
            continue
        j = nm.index(a)
        r = {"order(common) 에 있나": a in common,
             "union 에 있나": a in union,
             "BLOCK 에 걸렸나": (d, a) in FX.BLOCK,
             "BLOCK 사유": FX.BLOCK.get((d, a)),
             "유보 마스크 덮음": round(float(M[hold, j].mean()), 4),
             "학습 마스크 덮음": round(float(M[trm, j].mean()), 4),
             "유보 값 가짓수(마스크1 안)": int(nuniq(A[hold, j][M[hold, j] > 0])),
             "유보 마스크 가짓수": int(nuniq(M[hold, j])),
             "유보에서 살아 있나(값 or 마스크 변이)": bool(
                 nuniq(np.where(M[hold, j] > 0, A[hold, j], 0.5)) > 1
                 or nuniq(M[hold, j]) > 1)}
        if a in nm0:
            j0 = nm0.index(a)
            r["fixaxes 이전 유보 마스크"] = round(float(M0[hold, j0].mean()), 4)
            r["fixaxes 이전 유보 값 가짓수"] = int(nuniq(A0[hold, j0][M0[hold, j0] > 0]))
            r["🔴 fixaxes 가 죽였나"] = bool(
                (nuniq(np.where(M0[hold, j0] > 0, A0[hold, j0], 0.5)) > 1
                 or nuniq(M0[hold, j0]) > 1)
                and not r["유보에서 살아 있나(값 or 마스크 변이)"])
        out["축"][a] = r
    res["도메인"][d] = out

(ROOT / "runners/out900h_levers.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
