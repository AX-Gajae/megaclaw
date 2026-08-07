"""노트 794(793 의 진단에서) — **CN 기준선 0.3094 는 재현되나.** 씨앗 열둘 · 팔 넷.

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
    #: 🔴 노트 794 --- **마스크만 되돌린다. 값을 지어내지 않는다.**
    #: `manga_axes:88` 이 CN 352행에 실제로 계산하는 값이 0.0 이고(전부 전연령)
    #: 빌더가 상수라서 마스크 0 으로 강등한다. 옛 경로는 마스크 1 이었을 것이다.
    def variant(base, j, val, msk):
        src, names, A, M, y, t = arr[base]
        A2, M2 = A.copy(), M.copy()
        A2[:, j] = val
        M2[:, j] = msk
        return (src, names, A2, M2, y, t)

    jn = list(arr["CN 만화"][1]).index(DROP)
    arr["B_CN상수0마스크1"] = variant("CN 만화", jn, 0.0, 1.0)   # 옛 경로 복원
    arr["C_CN중립0.5마스크1"] = variant("CN 만화", jn, 0.5, 1.0)  # 순수 차원 비용
    arr["D_KR상수0마스크1"] = variant("KR 만화", jn, 0.0, 1.0)    # 교차 확인
    arr["KR-엔트리없음"] = variant("KR 만화", jn, 0.5, 0.0)

    wire = {}
    for nm, (src, names, A, M, y, t) in arr.items():
        wire[nm] = {"행": len(y), "열 있는 수": int((M.mean(axis=0) > 0).sum()),
                    "마스크 평균": round(float(M.mean()), 4),
                    "y 유한": int(np.isfinite(y).sum())}
    print(json.dumps({"배선": wire, f"{DROP} 열 자리": jn,
                      "B 가 CN 보다 열 하나 많나":
                          wire["B_CN상수0마스크1"]["열 있는 수"]
                          - wire["CN 만화"]["열 있는 수"] == 1},
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

    A_, B_ = res["CN 만화"]["평균"], res["B_CN상수0마스크1"]["평균"]
    C_, D_ = res["C_CN중립0.5마스크1"]["평균"], res["D_KR상수0마스크1"]["평균"]
    REC = PR.BASELINE["CN 만화"]
    half = 0.039                                   # 격차 0.078 의 절반
    ga = bool(0.29 <= B_ <= 0.33)
    gb = bool(not ga and (A_ - B_) >= half and B_ > 0.29)
    gla = bool(B_ < 0.29)
    gc = bool(not ga and not gb and not gla)
    wr = {"A(CN 그대로)": A_, "B(상수0 마스크1)": B_, "C(중립0.5 마스크1)": C_,
          "D(KR 상수0 마스크1)": D_, "KR 그대로": res["KR 만화"]["평균"],
          "KR-엔트리없음": res["KR-엔트리없음"]["평균"], "기록": REC,
          "**A−B**": round(A_ - B_, 4), "**A−C**": round(A_ - C_, 4),
          "**B−C (엉뚱한 가지 몰림의 몫)**": round(B_ - C_, 4),
          "**B−기록**": round(B_ - REC, 4)}

    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "씨앗": list(SEEDS), "짝별": res,
        "**모아 본 표**": wr,
        "🔴 **판정 (가) B ∈ [0.29,0.33] --- 원인 확정**": ga,
        "**판정 (나) 부분 설명 (A−B ≥ 0.039 인데 구간 밖)**": gb,
        "**판정 (다) 기제 기각 --- CN 을 뺀다**": gc,
        "**판정 (라) 과잉 설명 (B < 0.29)**": gla,
        "예측 ① A 가 0.3872 재현(0.005 안)":
            [bool(abs(A_ - 0.3872) <= 0.005), A_],
        "예측 ② B 가 0.29~0.34": [bool(0.29 <= B_ <= 0.34), B_],
        "예측 ③ C 가 0.35~0.39 이고 B 보다 높다":
            [bool(0.35 <= C_ <= 0.39 and C_ > B_), C_],
        "예측 ④ D 가 0.50~0.56": [bool(0.50 <= D_ <= 0.56), D_],
        "예측 ⑤ B 와 C 가 갈리면 원인은 엉뚱한 가지 몰림":
            round(B_ - C_, 4),
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
