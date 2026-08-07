"""노트 716 — **참값 0 SD 는 무엇의 함수인가.** 부분표본으로 n 과 도메인을 가른다.

배선: 판 적합은 **씨앗마다 한 번**이고 짝 · 부분표본 · 셔플 20 이 그것을 공유한다
(예측은 싸다). 부분표본은 **씨앗 사이에 고정**한다 --- 씨앗마다 달라지면 그 변동이
SD 에 섞인다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, guards as G, loop as L, pairs as PR, textaxes as TX
from lab.sideaudit import champion_data

T = 2025.0
SEEDS = tuple(range(6))
N_SHUF = 20                       # 위약 셔플 --- 예측이 싸므로 넉넉히
FRACS = (1.0, 0.5, 0.25)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]

JOBS = {"비게임 앱": 0.4968, "KR 만화": 0.6831, "CN 만화": 0.3874}
#: 노트 712·715 가 잰 텍스트 예보의 퍼짐 --- 정규화 후보
PRED_SD = {"비게임 앱": 0.158, "KR 만화": 0.0967, "CN 만화": 0.109}


def with_text(tx):
    from lab import genaxes, grpaxes

    def ex():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
        e.update(grpaxes.build())
        e.update(tx)
        return e
    return L._idol(lambda: ex(), mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def titles_for(name, rows):
    from pathlib import Path
    D = Path("data/state")
    files = (("app_records.json", "mobile_records.json")
             if name == "비게임 앱" else ("manga_records.json",))
    src = {}
    for f in files:
        p = D / f
        if not p.exists():
            continue
        j = json.loads(p.read_text())
        for r in (j.values() if isinstance(j, dict) else j):
            if isinstance(r, dict) and r.get("record_id"):
                src.setdefault(r["record_id"], r)
    return [str((src.get(k) or {}).get("title")
                or (src.get(k) or {}).get("name") or "") for k in rows]


def main():
    print("=== 챔피언 판을 짓는다 ===", flush=True)
    d0 = champion_data()
    tx = TX.build(d0, T=T)
    d1 = with_text(tx)

    rng = np.random.default_rng(716)
    prep = {}
    for name in JOBS:
        src = PR.SRC_DOM[name]
        rows = PR.build(name)
        ts = titles_for(name, rows)
        pt = TX.predict_titles(d1, src, ts, T=T)
        names = list(d1.names.get(src) or [])
        A, M, y, t = PR.to_arrays(rows, names)
        j = names.index(TX.AX)
        lab = np.flatnonzero(np.isfinite(y))          # 라벨 있는 행만
        # **부분표본을 씨앗 사이에 고정한다**
        subs = {}
        for fr in FRACS:
            m = max(int(round(len(lab) * fr)), 60)
            idx = lab if fr >= 1.0 else rng.choice(lab, size=m, replace=False)
            subs[fr] = np.sort(idx)
        shuf = []
        for _ in range(N_SHUF):
            v = pt["값"].copy()
            rng.shuffle(v)
            shuf.append(v)
        prep[name] = {"src": src, "A": A, "M": M, "y": y, "t": t, "j": j,
                      "mask": pt["마스크"], "subs": subs, "shuf": shuf,
                      "라벨행": len(lab)}
        print(json.dumps({name: {"라벨행": len(lab),
                                 "부분표본": {str(f): len(subs[f]) for f in FRACS}}},
                         ensure_ascii=False), flush=True)

    # ── 씨앗마다 판을 한 번 적합하고 (짝 × 부분표본 × 셔플 20) 을 예측
    acc = {(n, fr): [[] for _ in range(N_SHUF)] for n in prep for fr in FRACS}
    base = {(n, fr): [] for n in prep for fr in FRACS}
    for s in SEEDS:
        f1 = G._fit_on(lambda s=s: CLS(seed=s), d1, T, seed=s)
        for n, P in prep.items():
            for si, v in enumerate(P["shuf"]):
                A = P["A"].copy(); M = P["M"].copy()
                A[:, P["j"]] = v
                M[:, P["j"]] = P["mask"]
                p = np.asarray(f1.predict(P["src"], A, M, P["t"]), float)
                for fr in FRACS:
                    idx = P["subs"][fr]
                    k = idx[np.isfinite(p[idx]) & np.isfinite(P["y"][idx])]
                    if len(k) < 40:
                        continue
                    acc[(n, fr)][si].append(
                        float(spearmanr(p[k], P["y"][k]).statistic))
        print(f"  씨앗 {s} 끝", flush=True)

    # ── 참값 0 SD: 셔플 평균들의 흩어짐(씨앗 평균을 먼저 낸다)
    out = {}
    for n in prep:
        for fr in FRACS:
            arr = np.array([np.mean(x) for x in acc[(n, fr)] if x], float)
            if len(arr) < 5:
                continue
            nn = len(prep[n]["subs"][fr])
            out[f"{n} · {int(fr*100)}%"] = {
                "짝": n, "n": nn, "몫": fr,
                "셔플 수": int(len(arr)),
                "위약 평균의 평균": round(float(arr.mean()), 4),
                "**참값0 SD**": round(float(arr.std(ddof=1)), 5),
                "√n × SD": round(float(arr.std(ddof=1) * np.sqrt(nn)), 4),
                "SD ÷ 예보퍼짐": round(float(arr.std(ddof=1) / PRED_SD[n]), 5),
            }
    for k, v in out.items():
        print(json.dumps({k: v}, ensure_ascii=False), flush=True)

    # ── 짝 안 로그-로그 기울기(n 의 지수)
    slopes = {}
    for n in prep:
        xs, ys = [], []
        for fr in FRACS:
            key = f"{n} · {int(fr*100)}%"
            if key in out:
                xs.append(np.log(out[key]["n"]))
                ys.append(np.log(out[key]["**참값0 SD**"]))
        if len(xs) >= 3:
            slopes[n] = round(float(np.polyfit(xs, ys, 1)[0]), 3)
    # ── 같은 n 근처의 짝 사이 --- 25% 층
    small = {out[k]["짝"]: out[k] for k in out if out[k]["몫"] == 0.25}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "**짝 안 로그-로그 기울기**(n 의 지수 · 예측 −0.5)": slopes,
        "작은 층(25%)의 짝 사이": {n: {"n": v["n"], "SD": v["**참값0 SD**"],
                                "SD÷예보퍼짐": v["SD ÷ 예보퍼짐"],
                                "기준선 rho": JOBS[n]} for n, v in small.items()},
        "전체": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
