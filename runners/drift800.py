"""노트 800 — **드리프트를 학습만으로 예측할 수 있나.**

안 옮김(T=2023 적합 · 2023 이전 → 2023~24)이 밖 옮김(T=2025 적합 · 학습 → 유보)
을 예측하면 전이적이지 않은 보정이 생긴다. 자: 도메인 스피어만 |r| ≥ 0.75 ·
부호 일치 ≥ 9/n. 결정 규칙 네 방향(규약 45)은 대장에.
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
from lab import forms, guards as G

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (0, 1, 2)
MINROW = 30           # 창마다 이만큼은 있어야 옮김이 뜻을 갖는다


def shifts(f, data, d, lo_mask, hi_mask):
    """(hi 평균 − lo 평균) / SD(lo) — 예보와 라벨 둘 다."""
    A, M, y, t = data.dom[d]
    out = {}
    for nm, k in (("lo", lo_mask), ("hi", hi_mask)):
        try:
            p = np.asarray(f.predict(d, A[k], M[k], t[k]), float)
        except Exception:
            return None
        ok = np.isfinite(p)
        if ok.sum() < MINROW:
            return None
        out[nm] = (p[ok], np.asarray(y, float)[k][ok])
    plo, ylo = out["lo"]
    phi, yhi = out["hi"]
    sp = max(float(plo.std()), 1e-9)
    sy = max(float(ylo.std()), 1e-9)
    return {"예보 옮김": float((phi.mean() - plo.mean()) / sp),
            "라벨 옮김": float((yhi.mean() - ylo.mean()) / sy),
            "행": [int(len(plo)), int(len(phi))]}


def main():
    t0 = time.time()
    data = FF.shell(FF.base())

    #: 배선 --- 창별 행수(라벨 유한)를 먼저 찍는다
    wins = {}
    for d in data.dom:
        yr = np.asarray(data.yr[d], float)
        y = np.asarray(data.dom[d][2], float)
        fin = np.isfinite(yr) & np.isfinite(y)
        wins[d] = {"<2023": int((fin & (yr < 2023)).sum()),
                   "2023~24": int((fin & (yr >= 2023) & (yr < 2025)).sum()),
                   ">=2025": int((fin & (yr >= 2025)).sum())}
    print(json.dumps({"창별 행수": wins}, ensure_ascii=False), flush=True)

    per_seed = []
    dropped = set()
    for s in SEEDS:
        f23 = G._fit_on(lambda s=s: CLS(seed=s), data, 2023.0, seed=s)
        f25 = G._fit_on(lambda s=s: CLS(seed=s), data, 2025.0, seed=s)
        row = {}
        for d in data.dom:
            yr = np.asarray(data.yr[d], float)
            y = np.asarray(data.dom[d][2], float)
            fin = np.isfinite(yr) & np.isfinite(y)
            w0 = fin & (yr < 2023)
            w1 = fin & (yr >= 2023) & (yr < 2025)
            w2 = fin & (yr >= 2025)
            #: 🔴 **둘 다 훈련 안**이어야 잰다 --- 훈련 밖 도메인은 OOC 경로라
            #: 자가 다르다(사전등록)
            if d not in getattr(f23, "doms", {}) or d not in getattr(f25, "doms", {}):
                dropped.add(f"{d}(훈련 밖)")
                continue
            if min(w0.sum(), w1.sum(), w2.sum()) < MINROW:
                dropped.add(f"{d}(행 부족)")
                continue
            si = shifts(f23, data, d, w0, w1)
            so = shifts(f25, data, d, w0 | w1, w2)
            if si is None or so is None:
                dropped.add(f"{d}(예측 실패)")
                continue
            row[d] = {"안": si, "밖": so}
        per_seed.append(row)
        doms = sorted(row)
        if doms:
            a = [row[d]["안"]["예보 옮김"] for d in doms]
            b = [row[d]["밖"]["예보 옮김"] for d in doms]
            r = float(spearmanr(a, b).statistic) if len(doms) >= 4 else np.nan
            agree = sum(1 for x, z in zip(a, b) if x * z > 0)
            print(f"  씨앗 {s} · n {len(doms)} · r {r:+.3f} · 부호 {agree}/{len(doms)}"
                  f" · {round(time.time()-t0,1)}초", flush=True)

    doms = sorted(set.intersection(*[set(r) for r in per_seed]))
    n = len(doms)
    tbl = {}
    for d in doms:
        ain = float(np.mean([r[d]["안"]["예보 옮김"] for r in per_seed]))
        aout = float(np.mean([r[d]["밖"]["예보 옮김"] for r in per_seed]))
        lin = float(np.mean([r[d]["안"]["라벨 옮김"] for r in per_seed]))
        lout = float(np.mean([r[d]["밖"]["라벨 옮김"] for r in per_seed]))
        tbl[d] = {"안 예보": round(ain, 3), "밖 예보": round(aout, 3),
                  "부호 같나": bool(ain * aout > 0),
                  "안 라벨": round(lin, 3), "밖 라벨": round(lout, 3)}
    rs = []
    for r in per_seed:
        a = [r[d]["안"]["예보 옮김"] for d in doms]
        b = [r[d]["밖"]["예보 옮김"] for d in doms]
        if n >= 4:
            rs.append(float(spearmanr(a, b).statistic))
    rmean = float(np.mean(rs)) if rs else np.nan
    agree = sum(1 for d in doms if tbl[d]["부호 같나"])
    lab_small = sum(1 for d in doms
                    if abs(tbl[d]["밖 라벨"]) < 0.5 and abs(tbl[d]["안 라벨"]) < 0.5)

    ga = bool(n >= 7 and rmean >= 0.75 and agree >= min(9, n - 1))
    gd = bool(n >= 7 and rmean <= -0.75)
    gc = bool(n < 7)
    gb = bool(not ga and not gd and not gc)
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "잰 도메인": doms, "n": n, "뺀 것": sorted(dropped) or "없음",
        "도메인별": tbl,
        "**씨앗별 r**": [round(x, 3) for x in rs],
        "**r 평균**": round(rmean, 3),
        "**부호 일치**": f"{agree}/{n}",
        "라벨 옮김 |x|<0.5 인 도메인": f"{lab_small}/{n}",
        "**판정 (가) 예측 가능 --- 보정을 새로 사전등록**": ga,
        "**판정 (나) 전이적 한계 그대로 --- 미결 닫음**": gb,
        "**판정 (다) 도메인 부족 --- 판정 불가**": gc,
        "**판정 (라) 반대 --- 보정 금지**": gd,
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
