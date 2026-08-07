"""노트 776 — **n_tag 를 판에 넣는다.** 유보의 54% 를 덮는 1열. 창 안 백분위.

노트 775 가 넘긴 후보 29열 중 가장 넓다(웹툰·애니·세계애니·만화).
🔴 누출 위험(AniList 태그는 투표식으로 늘어난다)을 같이 검사한다.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata, spearmanr

import ff753 as FF
from lab import forms
from lab.harness import evaluate

T = 2025.0
SEEDS = tuple(range(6))
DRAWS = (7440, 7441, 7442)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "n_tag_w"
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


SRC = {"웹툰": "webtoon_records.json", "애니": "anime_records.json",
       "세계애니": "wanime_records.json", "만화": "manga_records.json"}


def ntag_maps():
    """원천에서 `n_tag` 를 읽는다. 레코드 순서가 판 행 순서와 같다고 가정하지 않고
    **행수로 맞춘다** --- 안 맞으면 중단한다(노트 359 의 조용한 중립화를 피한다)."""
    import json as J
    R = __import__("pathlib").Path("/Users/ax/world_model/data/state")
    out = {}
    for dm, fn in SRC.items():
        d = J.loads((R / fn).read_text())
        recs = d if isinstance(d, list) else (d.get("records") or d.get("rows"))
        out[dm] = [r.get("n_tag") for r in recs]
    return out


def main():
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    maps = ntag_maps()
    real, wr = {}, {}
    for dm in doms:
        n = len(d0.dom[dm][2])
        v = np.full(n, 0.5, np.float32)
        m = np.zeros(n, np.float32)
        if dm in maps:
            src = maps[dm]
            if len(src) != n:
                print(json.dumps({"중단": f"{dm} 행수 불일치 {len(src)} 대 {n}"},
                                 ensure_ascii=False), flush=True)
                return
            raw = np.array([np.nan if x is None else float(x) for x in src])
            y = np.asarray(d0.yr[dm], float)
            ok = np.isfinite(raw) & np.isfinite(y)
            tr, te = ok & (y < T), ok & (y >= T)
            p = np.full(n, np.nan)
            if tr.sum() >= 3:
                p[tr] = rankdata(raw[tr]) / tr.sum()
            if te.sum() >= 3:
                p[te] = rankdata(raw[te]) / te.sum()
            mm = np.isfinite(p)
            v[mm] = p[mm].astype(np.float32)
            m = mm.astype(np.float32)
        real[dm] = (v, m)
        y = np.asarray(d0.yr[dm], float)
        te_all = np.isfinite(y) & (y >= T)
        mb = m > 0
        wr[dm] = {"관측": int(mb.sum()), "행": n,
                  "덮음률": round(float(mb.mean()), 3),
                  "유보 덮음률": round(float((te_all & mb).sum()
                                       / max(int(te_all.sum()), 1)), 3),
                  "고유": int(len(np.unique(v[mb]))) if mb.sum() else 0}
    print(json.dumps({"배선": wr}, ensure_ascii=False), flush=True)
    live = [d for d in doms if wr[d]["관측"] > 0]
    if sorted(live) != sorted(SRC):
        print(json.dumps({"중단": f"붙은 도메인 {live} 가 {sorted(SRC)} 와 다르다"},
                         ensure_ascii=False), flush=True)
        return
    hole = [d for d in live if wr[d]["유보 덮음률"] < 0.999]
    if hole:
        print(json.dumps({"중단": f"유보 구멍 {hole}"}, ensure_ascii=False), flush=True)
        return

    # 🔴 누출 검사 --- n_tag ↔ 라벨(학습) 대 판이 쓰는 36열 중 가장 센 것
    leak = {}
    for dm in live:
        y = np.asarray(d0.yr[dm], float)
        lab = np.asarray(d0.dom[dm][2], float)
        A = np.asarray(d0.dom[dm][0], float)
        v, m = real[dm]
        tr = (np.asarray(m) > 0) & np.isfinite(y) & (y < T) & np.isfinite(lab)
        if tr.sum() < 30:
            continue
        r_nt = float(spearmanr(np.asarray(v)[tr], lab[tr]).statistic)
        best, bi = 0.0, -1
        for j in range(A.shape[1]):
            c = A[tr, j]
            if np.isfinite(c).sum() < 30 or len(np.unique(c[np.isfinite(c)])) < 3:
                continue
            rr = spearmanr(c[np.isfinite(c)], lab[tr][np.isfinite(c)]).statistic
            if np.isfinite(rr) and abs(rr) > abs(best):
                best, bi = float(rr), j
        leak[dm] = {"n_tag↔라벨": round(r_nt, 3),
                    "판 최강 열": round(best, 3),
                    "최강 열 이름": d0.names[dm][bi] if bi >= 0 else None,
                    "**n_tag 가 더 세다**": bool(abs(r_nt) > abs(best))}
    print(json.dumps({"🔴 누출 검사": leak}, ensure_ascii=False), flush=True)

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
        "노트 742 1열 비용": 0.006,
        "문턱 판 2σ": 0.0045,
        "판정 (가) 신호 몫 > 0.0045 이고 위약 전부보다 큼":
            bool(sig > 0.0045 and b1["판"] > pv.max()),
        "판정 (나) 문턱 안": bool(abs(sig) <= 0.0045),
        "판정 (다) 신호 몫 < −0.0045": bool(sig < -0.0045),
        "🔴 첫 양성이면 그냥 채택 안 한다": "규약 12 --- 집 밖 둘로 넘긴다",
        "겹침 중앙값(고유>6 만)": round(float(np.median(
            [wr[d]["겹침"] for d in doms
             if wr[d]["겹침"] is not None and wr[d]["고유"] > 6])), 3),
        "면제 도메인(고유≤6)": [d for d in doms if wr[d]["고유"] <= 6],
        "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
        "배선": wr,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
