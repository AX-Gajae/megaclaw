# -*- coding: utf-8 -*-
"""지평 900 — 채움 시험 재시도. 🔴 1차(out900h_design.py)의 채움 패치는
`json.load` 를 가로챘는데 `state/tri_domain.py:69` 는 `json.loads(read_text())`
라 **한 번도 안 걸렸다**(마스크 합이 89 로 그대로여서 들켰다). 여기서는
`_from_axes_json` 을 감싼다. 저장소 코드는 안 고친다."""
import json, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, "/Users/ax/world_model"); sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF
from lab import forms as FORMS, fixaxes as FX
from lab.harness import Data, MIN_TRAIN
import state.tri_domain as TD
import axesdie899 as A899

ROOT = Path("/Users/ax/world_model"); T = 2025.0; D = "시장팝업"
uniq_rows, nuniq = A899.uniq_rows, A899.nuniq
ORIG_BLOCK = dict(FX.BLOCK)
ORIG_FAJ = TD._from_axes_json
TMP = Path(tempfile.mkdtemp()) / "market_axes_filled.json"

def make_wrapper(seed):
    def wrapper(path, date_key, trend="year"):
        if str(path).endswith("market_axes.json"):
            o = json.loads(Path(path).read_text())
            rng = np.random.default_rng(seed)
            obs = np.array([v["axes"]["entry_friction"] for v in o.values()
                            if v["mask"]["entry_friction"] == 1.0], float)
            n = 0
            for v in o.values():
                if v["mask"]["entry_friction"] == 0.0:
                    v["axes"]["entry_friction"] = float(rng.choice(obs))
                    v["mask"]["entry_friction"] = 1.0
                    n += 1
            assert n == 88, f"🔴 채운 행이 88 이 아니다: {n}"
            TMP.write_text(json.dumps(o, ensure_ascii=False))
            return ORIG_FAJ(str(TMP), date_key, trend)
        return ORIG_FAJ(path, date_key, trend)
    return wrapper

def run(label, block=None, fill_seed=None):
    FX.BLOCK.clear(); FX.BLOCK.update(ORIG_BLOCK if block is None else block)
    TD._from_axes_json = ORIG_FAJ if fill_seed is None else make_wrapper(fill_seed)
    try:
        d0 = FF.shell(FF.base())
    finally:
        TD._from_axes_json = ORIG_FAJ
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T) & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k); tmask[d] = k
    tr = Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train})
    f = FF.CLS(seed=0); f.fit(tr)
    A, M, y, t = d0.dom[D]; nm = list(d0.names.get(D) or [])
    j = nm.index("entry_friction")
    yr = np.asarray(d0.yr[D], float)
    hold = np.isfinite(yr) & (yr >= T)
    sl = d0.slice(D, hold)
    p = np.asarray(f.predict(D, sl[0], sl[1], sl[3]), float)
    yh = np.asarray(y, float)[hold]
    ok = np.isfinite(p) & np.isfinite(yh)
    hidx = np.where(hold)[0][ok]
    X = f._design(D, A[hidx], M[hidx], np.asarray(t, float)[hidx])
    r = {"이름": label, "채점행": int(len(hidx)),
         "고유 설계행 uniq(_design)": int(uniq_rows(X)),
         "예측 고유(씨앗0)": int(nuniq(p[ok])),
         "🔴 유보 entry_friction 마스크 합": float(M[hidx, j].sum()),
         "유보 값 가짓수(A 열 전체)": int(nuniq(A[hidx, j])),
         "유보 마스크 가짓수": int(nuniq(M[hidx, j]))}
    print(json.dumps(r, ensure_ascii=False), flush=True)
    return r

nb = {k: v for k, v in ORIG_BLOCK.items() if k != (D, "entry_friction")}
out = {}
out["2 BLOCK 해제 + 88행 채움(가정 · 씨앗0)"] = run("2 해제+채움 s0", block=nb, fill_seed=0)
out["2b BLOCK 해제 + 88행 채움(가정 · 씨앗7)"] = run("2b 해제+채움 s7", block=nb, fill_seed=7)
out["3 채우기만(BLOCK 유지) — 음성대조"] = run("3 채움만", fill_seed=0)
(ROOT / "runners/out900h_design2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n=== 요약")
for k, v in out.items():
    print("%-40s 설계행 %3d · 마스크합 %.0f" % (k, v["고유 설계행 uniq(_design)"], v["🔴 유보 entry_friction 마스크 합"]))
