"""노트 757 — **축을 거칠게 하면 해로움이 줄나.** 기제 진단이면서 고침 후보.

노트 756 이 방향 뒤집힘을 지우고 실마리를 남겼다 --- 가장 해로운 둘에서 학습 상관
0.08 이 유보에서 0.02 로 **감쇠**한다. 기제 후보는 **약한 신호가 강한 분할 여지를
준다**는 것이고, 이 축은 날짜에서 와 고유값이 많다(웹툰 1,594).

노트 738 이 완전관측에서 **거친 열이 덜 비싸다**를 쟀으므로, 거칠게 해서 해로움이
줄면 기제가 서고 **그것이 동시에 고침**이다.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import forms
from lab.harness import evaluate

T = 2025.0
SEEDS = tuple(range(6))
DRAWS = (7440, 7441, 7442)          # 노트 745·753 과 같은 뽑기
KS = (10, 4)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "field_spread_c"
BASE_OK = (0.455, 0.485)


def board(data):
    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4),
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()}}


def coarsen(ax, k):
    """관측 행의 백분위를 **k 단계**로 뭉친다. 마스크는 그대로."""
    out = {}
    for dm, (v, m) in ax.items():
        v2 = np.asarray(v, np.float32).copy()
        mm = np.asarray(m) > 0
        if mm.sum():
            p = v2[mm]
            q = np.clip(np.floor(p * k), 0, k - 1) / max(k - 1, 1)
            v2[mm] = q.astype(np.float32)
        out[dm] = (v2, m)
    return out


def main():
    yrs, sd, days, ck = FF.spread_series()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)

    # 노트 753 의 앞채움 축을 그대로 만든다
    from scipy.stats import rankdata
    real = {}
    for dm in doms:
        y = np.asarray(d0.yr[dm], float)
        v = np.full(len(y), np.nan)
        ok = np.isfinite(y) & (y >= yrs[0])
        if ok.sum():
            j = np.clip(np.searchsorted(yrs, y[ok]), 0, len(sd) - 1)
            v[ok] = sd[j]
        m = np.isfinite(v)
        r = np.full(len(y), 0.5, np.float32)
        if m.sum() >= 3:
            r[m] = (rankdata(v[m]) / m.sum()).astype(np.float32)
        real[dm] = (r, m.astype(np.float32))

    def wiring(ax):
        out = {}
        for dm in doms:
            y = np.asarray(d0.yr[dm], float)
            te = np.isfinite(y) & (y >= T)
            m = np.asarray(ax[dm][1]) > 0
            out[dm] = {"관측": int(m.sum()),
                       "유보 덮음률": round(float((te & m).sum()
                                            / max(int(te.sum()), 1)), 3),
                       "고유": int(len(np.unique(ax[dm][0][m])))}
        return out

    arms = {}
    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"], "씨앗SD": b0["씨앗SD"]},
                     ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']}"}, ensure_ascii=False), flush=True)
        return

    for k in KS:
        ax = coarsen(real, k)
        wr = wiring(ax)
        hole = [dm for dm in doms if wr[dm]["유보 덮음률"] < 0.999]
        uq = sorted({wr[dm]["고유"] for dm in doms})
        print(json.dumps({f"배선 고유 {k}": {"고유값 집합": uq, "유보 구멍": hole}},
                         ensure_ascii=False), flush=True)
        if hole or max(uq) > k:
            print(json.dumps({"중단": f"배선 이상 k={k}"}, ensure_ascii=False), flush=True)
            return
        t0 = time.time()
        r = board(FF.shell({**FF.base(), AX: ax}))
        r["순효과"] = round(b0["판"] - r["판"], 4)
        arms[f"진짜 고유 {k}"] = r
        print(f"[진짜 고유 {k}] " + json.dumps(
            {"판": r["판"], "순효과(없이−팔)": r["순효과"],
             "초": round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)

    # 위약은 고유 10 로 세 뽑기(사전등록대로)
    ax10 = coarsen(real, 10)
    for ds in DRAWS:
        rng = np.random.default_rng(ds)
        ax = {}
        for dm in doms:
            v, m = ax10[dm]
            v2 = np.asarray(v, np.float32).copy()
            ii = np.flatnonzero(np.asarray(m) > 0)
            if len(ii) > 1:
                sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
            ax[dm] = (v2, m)
        r = board(FF.shell({**FF.base(), AX: ax}))
        r["순효과"] = round(b0["판"] - r["판"], 4)
        arms[f"위약10 {ds}"] = r
        print(f"[위약10 {ds}] " + json.dumps(
            {"판": r["판"], "순효과": r["순효과"]}, ensure_ascii=False), flush=True)

    pv = np.array([arms[f"위약10 {d}"]["판"] for d in DRAWS])
    n10 = arms["진짜 고유 10"]["순효과"]
    n4 = arms["진짜 고유 4"]["순효과"]
    ORIG = 0.0284                                   # 노트 754 원본 순효과
    ORIG_SIG = -0.0192
    sig10 = round(float(arms["진짜 고유 10"]["판"] - pv.mean()), 4)
    W = d0.weights(T); tot = sum(W.values())
    per = {}
    for dm in set(arms["진짜 고유 10"]["도메인"]) & set(b0["도메인"]):
        pm = float(np.mean([arms[f"위약10 {d}"]["도메인"].get(dm, np.nan)
                            for d in DRAWS]))
        per[dm] = {"신호 몫": round(arms["진짜 고유 10"]["도메인"][dm] - pm, 4),
                   "순효과": round(arms["진짜 고유 10"]["도메인"][dm]
                                - b0["도메인"][dm], 4),
                   "유보": W.get(dm, 0),
                   "판 기여": round((arms["진짜 고유 10"]["도메인"][dm] - pm)
                                 * W.get(dm, 0) / tot, 5)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"],
        "**순효과**": {"원본(고유 1594 · 노트 754)": ORIG, "고유 10": n10, "고유 4": n4},
        "**원본 − 고유10**": round(ORIG - n10, 4),
        "**원본 − 고유4**": round(ORIG - n4, 4),
        "위약10 판": [round(float(x), 4) for x in pv],
        "위약10 뽑기 SD": round(float(pv.std(ddof=1)), 4),
        "**고유10 신호 몫**": sig10, "원본 신호 몫(노트 754)": ORIG_SIG,
        "문턱 판 2σ": 0.0045,
        "판정 (가) 거칠게 해서 0.010 이상 덜 나쁘다":
            bool((ORIG - n10) >= 0.010 or (ORIG - n4) >= 0.010),
        "판정 (나) 차가 ±0.010 안":
            bool(abs(ORIG - n10) < 0.010 and abs(ORIG - n4) < 0.010),
        "판정 (다) 거칠수록 더 나쁘다": bool((ORIG - n10) <= -0.010
                                  or (ORIG - n4) <= -0.010),
        "**고유10 신호 몫 > +0.0045 → 첫 양성**": bool(sig10 > 0.0045),
        "단조(원본 ≥ 고유10 ≥ 고유4)": bool(ORIG >= n10 >= n4),
        "도메인별(고유10)": dict(sorted(per.items(),
                                key=lambda x: -abs(x[1]["판 기여"]))),
        "팔별": {k: {kk: v[kk] for kk in ("판", "씨앗SD", "순효과")}
               for k, v in arms.items()},
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
