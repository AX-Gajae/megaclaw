# 노트 840 — 절대값 승부 상관 n=12 (사전등록 '840' · 808 기계 재사용)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr, skew
sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, calib as C, forms

t0 = time.time()
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (0, 1, 2, 3)
T = 2025.0
data = sideaudit.champion_data()
print(f"도메인 {len(data.dom)} ({time.time()-t0:.0f}s)", flush=True)
assert "영화" in data.dom, "영화 미배선"

digit_diff = {}; drift = {}; skews = {}
acc = {}
for s in SEEDS:
    fc = C.forecasts(lambda: CLS(seed=s), data, T=T, seed=s)
    for d, (ptr, ytr, pho, yho) in fc.items():
        yh, _ = C.inv_holdout_pct(ptr, ytr, pho)
        r_fore = C.rulers(yh, yho)["자릿수 오차 비율"]
        cm, cl, ch = C.climatology(ytr, len(yho))
        r_clim = C.rulers(cm, yho)["자릿수 오차 비율"]
        dr = abs(float(np.mean(pho)) - float(np.mean(ptr))) / max(float(np.std(ptr)), 1e-9)
        a = acc.setdefault(d, {"dd": [], "dr": []})
        a["dd"].append(r_fore - r_clim)
        a["dr"].append(dr)
        if s == 0:
            skews[d] = float(skew(yho))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
for d, a in acc.items():
    digit_diff[d] = float(np.mean(a["dd"]))
    drift[d] = float(np.mean(a["dr"]))

doms = sorted(digit_diff)
n = len(doms)
y = [digit_diff[d] for d in doms]
x1 = [drift[d] for d in doms]
x2 = [skews[d] for d in doms]
r1 = float(spearmanr(x1, y)[0])
r2 = float(spearmanr(x2, y)[0])
OUT = {"n": n,
       "표": {d: {"자릿수차(예보-기후)": round(digit_diff[d], 4),
                  "드리프트": round(drift[d], 3), "왜도": round(skews[d], 3)} for d in doms},
       "상관": {"드리프트": round(r1, 3), "왜도": round(r2, 3)},
       "808(n=11) 참조": "둘 다 |r|<0.75 (없)"}
if n < 9:
    OUT["판정"] = "모 — n<9"
elif max(abs(r1), abs(r2)) >= 0.75:
    which = "드리프트" if abs(r1) >= abs(r2) else "왜도"
    OUT["판정"] = f"좋 — {which} |r|≥0.75 (채택 아님 · 갈라 재기 등록)"
else:
    OUT["판정"] = f"없 — 드리프트 {r1:.3f} · 왜도 {r2:.3f} 둘 다 <0.75 → 문패 종결"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out840.json", "w"), ensure_ascii=False, indent=1)
