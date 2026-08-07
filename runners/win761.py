"""노트 761 — **분포를 맞추면 해로움이 사라지나.** 창 안 백분위. **기제 시험이고 채택 아님.**"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata

import ff753 as FF
from lab import forms
from lab.harness import evaluate

T = 2025.0
SEEDS = tuple(range(6))
DRAWS = (7440, 7441, 7442)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "field_spread_w"
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


def main():
    yrs, sd, days, ck = FF.spread_series()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    real, wr = {}, {}
    for dm in doms:
        y = np.asarray(d0.yr[dm], float)
        m = np.isfinite(y) & (y >= yrs[0])
        v = np.full(len(y), 0.5, np.float32)
        if m.sum() >= 3:
            j = np.clip(np.searchsorted(yrs, y[m]), 0, len(sd) - 1)
            raw = sd[j]
            yy = y[m]
            tr, te = yy < T, yy >= T
            p = np.zeros(len(yy), np.float32)
            # **창 안 백분위** --- 학습은 학습 안 · 유보는 유보 안
            if tr.sum() >= 3:
                p[tr] = (rankdata(raw[tr]) / tr.sum()).astype(np.float32)
            if te.sum() >= 3:
                p[te] = (rankdata(raw[te]) / te.sum()).astype(np.float32)
            v[m] = p
        real[dm] = (v, m.astype(np.float32))
        te_all = np.isfinite(y) & (y >= T)
        mm = m
        q = ([np.percentile(v[mm & (y < T)], x) for x in (25, 50, 75)]
             if (mm & (y < T)).sum() >= 4 else None)
        r = ([np.percentile(v[mm & te_all], x) for x in (25, 50, 75)]
             if (mm & te_all).sum() >= 4 else None)
        ov = None
        if q and r:
            lo, hi = max(q[0], r[0]), min(q[2], r[2])
            ov = round(float(max(0.0, hi - lo) / max(r[2] - r[0], 1e-9)), 3)
        wr[dm] = {"관측": int(mm.sum()),
                  "유보 덮음률": round(float((te_all & mm).sum()
                                       / max(int(te_all.sum()), 1)), 3),
                  "겹침": ov, "고유": int(len(np.unique(v[mm])))}
    print(json.dumps({"배선": wr}, ensure_ascii=False), flush=True)
    hole = [d for d in doms if wr[d]["유보 덮음률"] < 0.999]
    # **고유값 6 이하 도메인은 겹침 게이트에서 면제한다**(노트 761 배선 정정).
    # 그 도메인들은 날짜가 연 단위라 축이 거의 상수이고(노트 745: 시장팝업 5 ·
    # 아이돌 6 · 펀딩 6) **애초에 정보를 못 나른다** --- 창 안 백분위로도 사분위가
    # 겹칠 수 없다. 면제하되 **따로 찍어 보고한다**(숨기지 않는다).
    thin = [d for d in doms if wr[d]["고유"] <= 6]
    low = [d for d in doms if d not in thin and (wr[d]["겹침"] or 0) < 0.9]
    print(json.dumps({"겹침 게이트 면제(고유≤6)": {d: wr[d] for d in thin},
                      "게이트 대상 겹침": {d: wr[d]["겹침"] for d in doms
                                   if d not in thin}}, ensure_ascii=False), flush=True)
    if hole or low:
        print(json.dumps({"중단": f"유보 구멍 {hole} · 겹침 낮음 {low}"},
                         ensure_ascii=False), flush=True)
        return

    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"]}, ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']}"}, ensure_ascii=False), flush=True)
        return
    t0 = time.time()
    b1 = board(FF.shell({**FF.base(), AX: real}))
    print(json.dumps({"② 진짜(창안)": b1["판"], "초": round(time.time() - t0, 1)},
                     ensure_ascii=False), flush=True)
    plac = {}
    for ds in DRAWS:
        rng = np.random.default_rng(ds)
        ax = {}
        for dm in doms:
            v, m = real[dm]
            v2 = np.asarray(v, np.float32).copy()
            ii = np.flatnonzero(np.asarray(m) > 0)
            if len(ii) > 1:
                sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
            ax[dm] = (v2, m)
        r = board(FF.shell({**FF.base(), AX: ax}))
        plac[ds] = r
        print(json.dumps({f"위약 {ds}": r["판"]}, ensure_ascii=False), flush=True)

    pv = np.array([plac[d]["판"] for d in DRAWS])
    sig = round(float(b1["판"] - pv.mean()), 4)
    net = round(float(b1["판"] - b0["판"]), 4)
    W = d0.weights(T); tot = sum(W.values())
    per = {}
    for dm in set(b1["도메인"]) & set(b0["도메인"]):
        pm = float(np.mean([plac[d]["도메인"].get(dm, np.nan) for d in DRAWS]))
        per[dm] = {"신호 몫": round(b1["도메인"][dm] - pm, 4),
                   "순효과": round(b1["도메인"][dm] - b0["도메인"][dm], 4),
                   "유보": W.get(dm, 0), "겹침": wr[dm]["겹침"],
                   "판 기여": round((b1["도메인"][dm] - pm) * W.get(dm, 0) / tot, 5)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"], "진짜(창안)": b1["판"],
        "위약": {str(d): plac[d]["판"] for d in DRAWS},
        "위약 평균": round(float(pv.mean()), 4),
        "위약 뽑기 SD": round(float(pv.std(ddof=1)), 4),
        "**신호 몫**": sig, "**순효과**": net,
        "**위약 비용**": round(float(b0["판"] - pv.mean()), 4),
        "원본 신호 몫(노트 754)": -0.0192, "고유10 신호 몫(노트 759)": -0.0175,
        "문턱 판 2σ": 0.0045,
        "판정 (가) 신호 몫 ≥ −0.0045 → 공변량 이동 확정": bool(sig >= -0.0045),
        "판정 (나) −0.013 < 신호 몫 < −0.0045 → 절반": bool(-0.013 < sig < -0.0045),
        "판정 (다) 신호 몫 ≤ −0.013 → 공변량 이동도 아니다": bool(sig <= -0.013),
        "🔴 채택 아님": "창 안 백분위는 전이적이다 --- 기제 시험 전용",
        "겹침 중앙값(고유>6 만)": round(float(np.median(
            [wr[d]["겹침"] for d in doms
             if wr[d]["겹침"] is not None and wr[d]["고유"] > 6])), 3),
        "면제 도메인(고유≤6)": [d for d in doms if wr[d]["고유"] <= 6],
        "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
        "배선": wr,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
