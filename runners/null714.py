"""노트 714 — **문턱이 실제로 5% 를 가르나.** 위약 대 위약으로 잰다.

참값이 0 인 두 팔(독립적인 위약 셔플 둘)의 '신호 몫' 분포를 낸다. 그 분포가
문턱을 넘는 비율이 **실제 오탐률**이고, 그것이 채택 규칙 도출의 전제다.

**배선**: 비싼 것은 판 적합이고 예측은 싸다. **씨앗마다 판을 한 번만 적합하고
짝 셋 × 위약 여럿을 그 위에서 예측한다** --- 짝마다 따로 적합하면 6배 든다.
"""
import itertools
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import spearmanr
from lab import forms, guards as G, loop as L, pairs as PR, textaxes as TX
from lab.sideaudit import champion_data

T = 2025.0
SEEDS = tuple(range(6))
N_PLAC = 4                    # 씨앗마다 만드는 위약 셔플 수 → 쌍 6개
CLS = forms.REGISTRY["F18_bagboost"]["cls"]

#: 짝 → (원천, 기록 기준선, 문턱)
JOBS = {"비게임 앱": (0.4968, 0.024),
        "KR 만화": (0.6831, 0.025),
        "CN 만화": (0.3874, 0.022)}


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

    # ── 짝마다 행 · 제목 · 열 자리 · 위약 셔플들을 미리 만든다
    prep = {}
    rng = np.random.default_rng(714)
    for name, (base_rec, thr) in JOBS.items():
        src = PR.SRC_DOM[name]
        rows = PR.build(name)
        ts = titles_for(name, rows)
        pt = TX.predict_titles(d1, src, ts, T=T)
        if "오류" in pt:
            print(json.dumps({name: pt}, ensure_ascii=False), flush=True)
            continue
        names = list(d1.names.get(src) or [])
        A, M, y, t = PR.to_arrays(rows, names)
        j = names.index(TX.AX)
        plac = []
        for _ in range(N_PLAC):
            v = pt["값"].copy()
            rng.shuffle(v)
            plac.append(v)
        prep[name] = {"src": src, "A": A, "M": M, "y": y, "t": t, "j": j,
                      "mask": pt["마스크"], "plac": plac,
                      "기록 기준선": base_rec, "문턱": thr,
                      "행": int(np.isfinite(y).sum())}
        print(json.dumps({name: {"행": prep[name]["행"], "위약 셔플": N_PLAC}},
                         ensure_ascii=False), flush=True)

    # ── 씨앗마다 판을 한 번 적합하고 모든 위약을 그 위에서 예측
    got = {n: {"없이": [], "위약": [[] for _ in range(N_PLAC)]} for n in prep}
    for s in SEEDS:
        f0 = G._fit_on(lambda s=s: CLS(seed=s), d0, T, seed=s)
        f1 = G._fit_on(lambda s=s: CLS(seed=s), d1, T, seed=s)
        line = {}
        for n, P in prep.items():
            ok = np.isfinite(P["y"])
            # '없이' --- 배선 검증용(텍스트 열 없는 판)
            names0 = list(d0.names.get(P["src"]) or [])
            A0, M0, y0, t0 = PR.to_arrays(PR.build(n), names0)
            p0 = np.asarray(f0.predict(P["src"], A0, M0, t0), float)
            k0 = np.isfinite(y0) & np.isfinite(p0)
            got[n]["없이"].append(float(spearmanr(p0[k0], y0[k0]).statistic))
            # 위약들 --- 같은 적합 위에서 열 값만 갈아 끼운다
            for i, v in enumerate(P["plac"]):
                A = P["A"].copy(); M = P["M"].copy()
                A[:, P["j"]] = v
                M[:, P["j"]] = P["mask"]
                p = np.asarray(f1.predict(P["src"], A, M, P["t"]), float)
                k = ok & np.isfinite(p)
                got[n]["위약"][i].append(float(spearmanr(p[k], P["y"][k]).statistic))
            line[n] = round(got[n]["위약"][0][-1], 4)
        print(f"  씨앗 {s} · 위약0 = {json.dumps(line, ensure_ascii=False)}", flush=True)

    # ── 오탐률: 위약 쌍의 '신호 몫' 이 문턱을 넘는 비율
    out = {}
    for n, P in prep.items():
        base = float(np.mean(got[n]["없이"]))
        arr = np.array(got[n]["위약"], float)         # (N_PLAC, seeds)
        means = arr.mean(axis=1)
        diffs = [float(means[a] - means[b])
                 for a, b in itertools.combinations(range(N_PLAC), 2)]
        # 씨앗 단위로도 --- 씨앗마다 쌍의 차를 다 낸다(표본이 커진다)
        per_seed = [float(arr[a, si] - arr[b, si])
                    for a, b in itertools.combinations(range(N_PLAC), 2)
                    for si in range(arr.shape[1])]
        thr = P["문턱"]
        out[n] = {
            "행": P["행"], "문턱": thr,
            "없이": round(base, 4), "기록 기준선": P["기록 기준선"],
            "배선 차": round(base - P["기록 기준선"], 4),
            "위약 평균들": [round(x, 4) for x in means],
            "**참값 0 인 차** (쌍 평균)": [round(x, 4) for x in diffs],
            "그 차의 절대값 최대": round(float(np.max(np.abs(diffs))), 4),
            "**문턱 넘은 쌍**": f"{sum(1 for d in diffs if abs(d) > thr)}/{len(diffs)}",
            "씨앗 단위 차 n": len(per_seed),
            "씨앗 단위 오탐률": round(
                float(np.mean([abs(d) > thr for d in per_seed])), 4),
            "씨앗 단위 차 SD": round(float(np.std(per_seed)), 4),
            "SD 대 문턱": round(float(np.std(per_seed)) / thr, 2),
        }
        print(json.dumps({n: out[n]}, ensure_ascii=False, indent=1), flush=True)
    allpairs = [abs(x) for n in out for x in out[n]["**참값 0 인 차** (쌍 평균)"]]
    thrs = {n: out[n]["문턱"] for n in out}
    cross = sum(1 for n in out
                for x in out[n]["**참값 0 인 차** (쌍 평균)"]
                if abs(x) > thrs[n])
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "짝별": out,
        "전체 쌍": len(allpairs), "문턱 넘은 쌍": cross,
        "**오탐률(쌍 평균 기준)**": round(cross / max(len(allpairs), 1), 4),
        "판정": ("문턱이 느슨하다" if cross / max(len(allpairs), 1) > 0.07
               else "문턱이 눈금돼 있다"),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
