# -*- coding: utf-8 -*-
"""지평 900 — 시장팝업 entry_friction 을 살리면 설계패턴이 27 이 되나.
🔴 저장소 코드는 안 고친다. 전부 이 파일 안의 원숭이 패치다."""
import json, sys, copy
from pathlib import Path
import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF
from lab import forms as FORMS
from lab import fixaxes as FX
from lab.harness import Data, MIN_TRAIN
import axesdie899 as A899

ROOT = Path("/Users/ax/world_model")
T = 2025.0
D = "시장팝업"
uniq_rows, nuniq = A899.uniq_rows, A899.nuniq
ORIG_BLOCK = dict(FX.BLOCK)

def run(label, block=None, fill=None):
    """block: 대체 BLOCK dict. fill: market_axes.json 을 메모리에서 고칠 함수."""
    FX.BLOCK.clear(); FX.BLOCK.update(ORIG_BLOCK if block is None else block)
    if fill is None:
        d0 = FF.shell(FF.base())
    else:
        import state.tri_domain as TD
        import lab.harness as HN
        real_load = json.load
        src = str(ROOT / "data/state/market_axes.json")
        def patched_load(fp, *a, **k):
            o = real_load(fp, *a, **k)
            try:
                nm = getattr(fp, "name", "")
            except Exception:
                nm = ""
            if str(nm).endswith("market_axes.json"):
                o = fill(o)
            return o
        json.load = patched_load
        try:
            d0 = FF.shell(FF.base())
        finally:
            json.load = real_load
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T) & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k); tmask[d] = k
    tr = Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train})
    f = FF.CLS(seed=0); f.fit(tr)
    A, M, y, t = d0.dom[D]
    nm = list(d0.names.get(D) or [])
    j = nm.index("entry_friction")
    hold = np.isfinite(np.asarray(d0.yr[D], float)) & (np.asarray(d0.yr[D], float) >= T)
    sl = d0.slice(D, hold)
    p = np.asarray(f.predict(D, sl[0], sl[1], sl[3]), float)
    yh = np.asarray(y, float)[hold]
    ok = np.isfinite(p) & np.isfinite(yh)
    hidx = np.where(hold)[0][ok]
    Ah, Mh, th = A[hidx], M[hidx], np.asarray(t, float)[hidx]
    X = f._design(D, Ah, Mh, th)
    r = {"이름": label, "채점행": int(len(hidx)),
         "고유 설계행 uniq(_design)": int(uniq_rows(X)),
         "예측 고유(씨앗0)": int(nuniq(p[ok])),
         "설계행렬 열 수": int(X.shape[1]),
         "유보 entry_friction 마스크 합": float(Mh[:, j].sum()),
         "유보 entry_friction 값 가짓수": int(nuniq(Ah[:, j])),
         "유보 entry_friction 마스크 가짓수": int(nuniq(Mh[:, j])),
         "order 에 entry_friction 있나": "entry_friction" in list(f.order)}
    print(json.dumps(r, ensure_ascii=False), flush=True)
    return r

out = {}
out["0 현행(BLOCK 그대로)"] = run("0 현행")

nb = {k: v for k, v in ORIG_BLOCK.items() if k != (D, "entry_friction")}
out["1 BLOCK 만 항등(채우지 않음)"] = run("1 BLOCK 해제", block=nb)

# 2: 결측 88행을 채운다 --- 값은 **가정**이다(역산 불가라 무엇을 넣어도 가정).
#    상한을 보려고 관측 분포에서 씨앗 고정 재표집으로 채운다.
def make_fill(seed):
    def fill(o):
        rng = np.random.default_rng(seed)
        obs = [v["axes"]["entry_friction"] for v in o.values()
               if v["mask"]["entry_friction"] == 1.0]
        obs = np.array(obs, float)
        for k, v in o.items():
            if v["mask"]["entry_friction"] == 0.0:
                v["axes"]["entry_friction"] = float(rng.choice(obs))
                v["mask"]["entry_friction"] = 1.0
        return o
    return fill
out["2 BLOCK 해제 + 88행 채움(가정)"] = run("2 해제+채움", block=nb, fill=make_fill(0))

# 3: BLOCK 은 그대로 둔 채 채우기만 --- 마스크가 0 이 되므로 변화 없어야 한다(음성 대조)
out["3 채우기만(BLOCK 유지) — 음성대조"] = run("3 채움만", fill=make_fill(0))

Path(ROOT / "runners/out900h_design.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n=== 요약")
for k, v in out.items():
    print("%-34s 설계행 %3d · 예측고유 %3d" % (k, v["고유 설계행 uniq(_design)"], v["예측 고유(씨앗0)"]))
