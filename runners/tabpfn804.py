"""노트 804(확인 · 사전등록은 803 대장에) — **TabPFN 챌린저 대 챔피언(합동 적합) · 얇은 도메인 다섯.**

구조 비교다: 도메인 단독 + SCM 사전 대 11도메인 전이. 같은 자료·같은 갈림·
같은 유보행. X = [A | M | t] --- 챔피언이 보는 것과 같은 정보.
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
from lab import calib as C, forms

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (4, 5, 6, 7)     # 🔴 새 씨앗 --- 챔피언·TabPFN 둘 다
T = 2025.0
THIN = ("아이돌", "시장팝업")   # 🔴 노트 804 가 못박은 둘
SIG2 = {"팝업": 0.0325, "도서": 0.0205, "아이돌": 0.0367,
        "시장팝업": 0.0233, "게임": 0.0195}


def xy(data, d):
    """학습/유보의 [A|M|t] 와 라벨 --- 챔피언과 같은 행."""
    yr = np.asarray(data.yr[d], float)
    A, M, y, t = data.dom[d]
    y = np.asarray(y, float)
    fin = np.isfinite(yr) & np.isfinite(y)
    ktr = fin & (yr < T)
    kho = fin & (yr >= T)
    X = np.hstack([A, M, np.asarray(t, float)[:, None]])
    X = np.nan_to_num(X, nan=0.5)
    return X[ktr], y[ktr], X[kho], y[kho]


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    from tabpfn import TabPFNRegressor

    #: 배선 --- 행수·열수 찍기
    wire = {}
    for d in THIN:
        Xtr, ytr, Xho, yho = xy(data, d)
        wire[d] = {"학습": len(ytr), "유보": len(yho), "열": Xtr.shape[1]}
    print(json.dumps({"배선": wire}, ensure_ascii=False), flush=True)

    champ = {d: [] for d in THIN}
    tab = {d: [] for d in THIN}
    for s in SEEDS:
        fc = C.forecasts(lambda s=s: CLS(seed=s), data, T=T, seed=s)
        for d in THIN:
            if d in fc:
                _, _, pho, yho = fc[d]
                champ[d].append(float(spearmanr(pho, yho).statistic))
        for d in THIN:
            Xtr, ytr, Xho, yho = xy(data, d)
            if len(ytr) < 10 or len(yho) < 20:
                continue
            tt = time.time()
            try:
                m = TabPFNRegressor(device="cpu", random_state=s)
                m.fit(Xtr, ytr)
                p = np.asarray(m.predict(Xho), float)
                ok = np.isfinite(p)
                tab[d].append(float(spearmanr(p[ok], yho[ok]).statistic))
            except Exception as e:
                tab[d].append(np.nan)
                print(f"  ⛔ {d} 씨앗 {s}: {type(e).__name__}: {e}", flush=True)
            if s == 0:
                print(f"  [{d}] TabPFN {round(time.time()-tt,1)}초", flush=True)
        print(f"  씨앗 {s} 끝 · {round(time.time()-t0,1)}초", flush=True)

    res, wins_t, wins_c = {}, [], []
    wsum_t = wsum_c = wtot = 0.0
    for d in THIN:
        cm = np.array(champ[d], float)
        tm = np.array(tab[d], float)
        diff = float(np.nanmean(tm) - np.nanmean(cm))
        n_ho = wire[d]["유보"]
        res[d] = {"챔피언": round(float(np.nanmean(cm)), 4),
                  "챔피언 SD": round(float(np.nanstd(cm, ddof=1)), 4),
                  "TabPFN": round(float(np.nanmean(tm)), 4),
                  "TabPFN SD": round(float(np.nanstd(tm, ddof=1)), 4),
                  "**차(Tab−챔프)**": round(diff, 4),
                  "2σ": SIG2[d],
                  "**2σ 밖**": bool(abs(diff) > SIG2[d]),
                  "승자": ("TabPFN" if diff > SIG2[d] else
                         "챔피언" if diff < -SIG2[d] else "비김")}
        if res[d]["승자"] == "TabPFN":
            wins_t.append(d)
        if res[d]["승자"] == "챔피언":
            wins_c.append(d)
        wsum_t += float(np.nanmean(tm)) * n_ho
        wsum_c += float(np.nanmean(cm)) * n_ho
        wtot += n_ho
    pooled_t, pooled_c = wsum_t / wtot, wsum_c / wtot

    #: 노트 804 규칙: (가) 둘 다 2σ 밖 유지 · (나) 하나만 · (다) 둘 다 안 ·
    #: (라) 부호 뒤집힘
    flip = [d for d in THIN if res[d]["**차(Tab−챔프)**"] < 0]
    ga = bool(len(wins_t) == 2)
    gb = bool(len(wins_t) == 1 and not flip)
    gd = bool(len(wins_t) == 0 and not flip)
    gl = bool(flip)
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인별": res,
        "**5도메인 가중(유보행)**": {"TabPFN": round(pooled_t, 4),
                              "챔피언": round(pooled_c, 4),
                              "차": round(pooled_t - pooled_c, 4)},
        "TabPFN 2σ 밖 승": wins_t or "없음",
        "챔피언 2σ 밖 승": wins_c or "없음",
        "**판정 (가) 둘 다 유지 --- 보조 헤드 확정 · T1 재개**": ga,
        "**판정 (나) 하나만 유지**": gb,
        "**판정 (다) 둘 다 2σ 안 --- 씨앗 우연**": gd,
        "**판정 (라) 부호 뒤집힘 --- 배선 재검**": [gl, flip],
        "803 대조": {"아이돌": +0.1698, "시장팝업": +0.0909},
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
