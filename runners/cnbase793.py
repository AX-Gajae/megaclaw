"""노트 793 — **CN 기준선 0.3094 는 재현되나.** 씨앗 열둘 · 팔 넷.

🔴 순환 금지: **내가 잰 값을 새 기준선으로 삼지 않는다.** 원인을 이름 붙여
대고 그것이 격차를 설명해야만 기준선을 다시 적는다.

팔 넷 (판 적합 하나로 넷 다 채점 --- 적합은 씨앗마다 한 번):
  ① KR 만화          대조(이미 맞는 것으로 안다)
  ② 비게임 앱        둘째 대조(안 재 봤다)
  ③ CN 만화          문제의 짝
  ④ KR - entry_friction   CN 이 겪는 열 부재를 KR 에서 재현 → 그 열의 값어치
"""
import json
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import forms, guards as G, pairs as PR

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = tuple(range(12))
T = 2025.0
DROP = "entry_friction"


def main():
    t0 = time.time()
    data = FF.shell(FF.base())

    #: 짝 행과 배열을 **한 번만** 만든다(빌더가 느리다)
    arr = {}
    for nm in PR.PAIRS:
        src = PR.SRC_DOM[nm]
        names = list(data.names.get(src) or [])
        A, M, y, t = PR.to_arrays(PR.build(nm), names)
        arr[nm] = (src, names, A, M, y, t)
    #: 팔 ④ --- KR 에서 entry_friction 을 **마스크 0 으로** 지운다(값은 0.5)
    src, names, A, M, y, t = arr["KR 만화"]
    j = names.index(DROP) if DROP in names else None
    A4, M4 = A.copy(), M.copy()
    if j is not None:
        A4[:, j] = 0.5
        M4[:, j] = 0.0
    arr["KR-엔트리없음"] = (src, names, A4, M4, y, t)

    wire = {}
    for nm, (src, names, A, M, y, t) in arr.items():
        wire[nm] = {"행": len(y), "열 있는 수": int((M.mean(axis=0) > 0).sum()),
                    "마스크 평균": round(float(M.mean()), 4),
                    "y 유한": int(np.isfinite(y).sum())}
    print(json.dumps({"배선": wire,
                      f"KR 에서 {DROP} 지웠나":
                          bool(j is not None
                               and wire["KR 만화"]["열 있는 수"]
                               - wire["KR-엔트리없음"]["열 있는 수"] == 1)},
                     ensure_ascii=False), flush=True)

    got = {nm: [] for nm in arr}
    for s in SEEDS:
        f = G._fit_on(lambda s=s: CLS(seed=s), data, T, seed=s)
        for nm, (src, names, A, M, y, t) in arr.items():
            p = np.asarray(f.predict(src, A, M, t), float)
            ok = np.isfinite(p) & np.isfinite(y)
            got[nm].append(float(spearmanr(p[ok], y[ok]).statistic)
                           if ok.sum() >= 20 and len(np.unique(p[ok])) >= 3
                           else np.nan)
        print(f"  씨앗 {s} · " + " · ".join(
            f"{nm} {got[nm][-1]:+.4f}" for nm in arr)
            + f" · {round(time.time()-t0,1)}초", flush=True)

    res = {}
    for nm, v in got.items():
        a = np.array(v, float)
        base = PR.BASELINE.get(nm)
        r = {"씨앗별": [round(x, 4) for x in a],
             "평균": round(float(np.nanmean(a)), 4),
             "**씨앗 SD**": round(float(np.nanstd(a, ddof=1)), 4),
             "최소": round(float(np.nanmin(a)), 4),
             "최대": round(float(np.nanmax(a)), 4),
             "폭": round(float(np.nanmax(a) - np.nanmin(a)), 4)}
        if base is not None:
            r["기록"] = base
            r["차(평균−기록)"] = round(r["평균"] - base, 4)
            r["**[최소,최대] 가 기록을 품나**"] = bool(r["최소"] <= base <= r["최대"])
            r["**평균±2SD 가 기록을 품나**"] = bool(
                abs(r["평균"] - base) <= 2 * r["**씨앗 SD**"])
        res[nm] = r

    #: 팔 ①−④ = entry_friction 한 열의 값어치(짝 자리에서)
    worth = np.array(got["KR 만화"], float) - np.array(got["KR-엔트리없음"], float)
    gap = PR.BASELINE["CN 만화"] and (res["CN 만화"]["평균"]
                                    - PR.BASELINE["CN 만화"])
    wr = {"씨앗별": [round(x, 4) for x in worth],
          "평균": round(float(np.nanmean(worth)), 4),
          "SD": round(float(np.nanstd(worth, ddof=1)), 4),
          "CN 격차": round(float(gap), 4),
          "**격차의 몇 할을 설명하나**":
              round(float(abs(np.nanmean(worth)) / abs(gap)), 3) if gap else None}

    ga = res["CN 만화"]["**[최소,최대] 가 기록을 품나**"]
    gb = bool(not ga and wr["**격차의 몇 할을 설명하나**"]
              and wr["**격차의 몇 할을 설명하나**"] >= 0.5)
    gd = bool(abs(res["비게임 앱"]["평균"] - PR.BASELINE["비게임 앱"])
              > 2 * res["비게임 앱"]["**씨앗 SD**"])
    gc = bool(not ga and not gb)

    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "씨앗": list(SEEDS), "짝별": res,
        f"**{DROP} 한 열의 값어치(KR 자리)**": wr,
        "**판정 (가) CN 씨앗 폭이 기록을 품는다**": ga,
        "**판정 (나) 열 부재가 격차의 절반 이상을 설명**": gb,
        "**판정 (다) 재현 불가 --- CN 을 짝에서 뺀다**": gc,
        "**판정 (라) 앱도 재현 안 된다 --- 표 전체 의심**": gd,
        "예측 ① KR 재현":
            res["KR 만화"]["**평균±2SD 가 기록을 품나**"],
        "예측 ② 앱 재현(0.02 안)":
            bool(abs(res["비게임 앱"]["차(평균−기록)"]) <= 0.02),
        "예측 ③ CN 씨앗 SD 0.02~0.05":
            [bool(0.02 <= res["CN 만화"]["**씨앗 SD**"] <= 0.05),
             res["CN 만화"]["**씨앗 SD**"]],
        "예측 ④ 열 값어치 0.00~0.02 이고 격차 절반 못 넘음":
            [bool(0.0 <= wr["평균"] <= 0.02), wr["평균"],
             wr["**격차의 몇 할을 설명하나**"]],
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
