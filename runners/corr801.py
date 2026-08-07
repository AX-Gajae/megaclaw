"""노트 801 — **학습-기반 드리프트 보정이 기후값을 이기나.**

보정: p′ = p_유보 − 안옮김_d × SD(학습 예보_d). 전부 학습에서만 나온다(한 건씩
가능). 팔: A 무보정 등백분위 · B 보정 등백분위 · C 기후값 · D 유보백분위(참고).
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import calib as C, forms, guards as G

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (0, 1, 2, 3)
MINROW = 30


def inshift(f23, data, d):
    """노트 800 의 안 옮김 --- T=2023 적합 · 2023 이전 → 2023~24."""
    yr = np.asarray(data.yr[d], float)
    y = np.asarray(data.dom[d][2], float)
    fin = np.isfinite(yr) & np.isfinite(y)
    w0 = fin & (yr < 2023)
    w1 = fin & (yr >= 2023) & (yr < 2025)
    if d not in getattr(f23, "doms", {}) or min(w0.sum(), w1.sum()) < MINROW:
        return None
    A, M, _y, t = data.dom[d]
    try:
        p0 = np.asarray(f23.predict(d, A[w0], M[w0], t[w0]), float)
        p1 = np.asarray(f23.predict(d, A[w1], M[w1], t[w1]), float)
    except Exception:
        return None
    p0, p1 = p0[np.isfinite(p0)], p1[np.isfinite(p1)]
    if len(p0) < MINROW or len(p1) < MINROW:
        return None
    return float((p1.mean() - p0.mean()) / max(p0.std(), 1e-9))


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    runs = []
    uncorrected = set()
    for s in SEEDS:
        f23 = G._fit_on(lambda s=s: CLS(seed=s), data, 2023.0, seed=s)
        fc = C.forecasts(lambda s=s: CLS(seed=s), data, T=2025.0, seed=s)
        per = {}
        wire = {}
        for d, (ptr, ytr, pho, yho) in fc.items():
            sh = inshift(f23, data, d)
            if sh is None:
                uncorrected.add(d)
                p_corr = pho                        # 무보정으로 둔다(사전등록)
            else:
                p_corr = pho - sh * float(ptr.std())
            wire[d] = {"안 옮김": None if sh is None else round(sh, 3),
                       "보정량(예보자)": None if sh is None
                       else round(sh * float(ptr.std()), 2)}
            yA, _ = C.inv_percentile(ptr, ytr, pho)
            yB, _ = C.inv_percentile(ptr, ytr, p_corr)
            cm, cl, ch = C.climatology(ytr, len(yho))
            yD, _ = C.inv_holdout_pct(ptr, ytr, pho)
            per[d] = {"A": C.rulers(yA, yho), "B": C.rulers(yB, yho),
                      "C": C.rulers(cm, yho), "D": C.rulers(yD, yho),
                      "행": len(yho)}
        runs.append(per)
        if s == 0:
            print(json.dumps({"배선(씨앗 0)": wire,
                              "무보정 도메인": sorted(uncorrected) or "없음"},
                             ensure_ascii=False), flush=True)
        print(f"  씨앗 {s} 끝 · {round(time.time()-t0,1)}초", flush=True)

    doms = sorted(runs[0])
    wts = {d: runs[0][d]["행"] for d in doms}

    def pooled(arm, key):
        w = np.array([wts[d] for d in doms], float)
        vals = []
        for r in runs:
            v = np.array([r[d][arm][key] for d in doms], float)
            vals.append(float((w * v).sum() / w.sum()))
        a = np.array(vals)
        return {"씨앗별": [round(x, 4) for x in a],
                "평균": round(float(a.mean()), 4),
                "SD": round(float(a.std(ddof=1)), 5)}

    res = {}
    for arm, nm in (("A", "무보정 등백분위"), ("B", "보정 등백분위"),
                    ("C", "기후값"), ("D", "유보백분위(참고)")):
        res[nm] = {k: pooled(arm, k)
                   for k in ("자릿수 오차 비율", "중앙절대오차")}
        dg = res[nm]["자릿수 오차 비율"]
        print(f"[{nm}] 자릿수 {dg['평균']:.4f} (SD {dg['SD']:.5f})", flush=True)

    B = res["보정 등백분위"]["자릿수 오차 비율"]
    A_ = res["무보정 등백분위"]["자릿수 오차 비율"]
    Cc = res["기후값"]["자릿수 오차 비율"]
    D_ = res["유보백분위(참고)"]["자릿수 오차 비율"]
    noise = max(B["SD"], Cc["SD"])
    dBC = B["평균"] - Cc["평균"]
    ga = bool(dBC < -3 * noise)
    gl = bool(B["평균"] > A_["평균"] or dBC > 3 * noise)
    #: (다) --- 도메인별로 B 가 C 를 3×씨앗SD 밖으로 이기는 곳
    perd = {}
    windom = []
    for d in doms:
        b = np.array([r[d]["B"]["자릿수 오차 비율"] for r in runs])
        c = np.array([r[d]["C"]["자릿수 오차 비율"] for r in runs])
        a_ = float(np.mean([r[d]["A"]["자릿수 오차 비율"] for r in runs]))
        nz = max(float(b.std(ddof=1)), float(c.std(ddof=1)), 1e-6)
        perd[d] = {"A": round(a_, 3), "B": round(float(b.mean()), 3),
                   "C": round(float(c.mean()), 3),
                   "B−C": round(float(b.mean() - c.mean()), 3),
                   "이기나(3SD 밖)": bool(b.mean() - c.mean() < -3 * nz)}
        if perd[d]["이기나(3SD 밖)"]:
            windom.append(d)
    gc_ = bool(not ga and not gl and windom)
    gb = bool(not ga and not gl and not windom)

    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "무보정 도메인": sorted(uncorrected) or "없음",
        "팔별": res, "도메인별": perd,
        "**B−C**": round(dBC, 4), "잡음(씨앗 SD)": round(noise, 5),
        "**B−D (전이적 상한과의 차)**": round(B["평균"] - D_["평균"], 4),
        "**판정 (가) 조건부 능력**": ga,
        "**판정 (나) 미결 닫음 --- 배치 전용이 최종**": gb,
        "**판정 (다) 도메인별 부분 --- 재확인 필요**": [gc_, windom],
        "**판정 (라) 보정 금지**": gl,
        "예측 ① B 0.19~0.28": [bool(0.19 <= B["평균"] <= 0.28), B["평균"]],
        "예측 ⑤ |B−D| < 0.03": [bool(abs(B["평균"] - D_["평균"]) < 0.03),
                               round(B["평균"] - D_["평균"], 4)],
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
