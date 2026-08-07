"""노트 741 — **뽑기 잡음을 잰다.** 연속 3열 · 뽑기 6 회 × 모형 씨앗 3.

노트 694 의 40배 비교는 셋이 교란돼 있었다(카디널리티 · 신호 · 쪼갤 지점 수)
그리고 판이 아니라 564짝이었다. **그래서 신호를 없애고 카디널리티만 남긴다** ---
도메인마다 연속 난수 3벡터를 뽑고 **팔마다 그것을 도메인 안 분위로 이산화**한다.
팔들이 같은 무작위 위에 짝지어진다.

**모든 팔이 위약이다** --- 재는 것이 신호가 아니라 비용이다.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)
DRAWS = (900, 901, 902, 903, 904, 905)
NCOL = 3   # 연속 3열 고정 --- 흔드는 것은 뽑기다
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "junk"
#: 기준선 가드(노트 705) --- 여기서 크게 벗어나면 판을 잘못 지은 것이다
BASE_OK = (0.455, 0.485)


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


def shell(extra):
    return L._idol(lambda: dict(extra), mode="cut", with_wiki=True,
                   with_trend=True, wide_post=True, wide_pop="grades")


def board(data, tag):
    vals, per = [], {}
    t0 = time.time()
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4),
            "초": round(time.time() - t0, 1),
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()}}


def main():
    d0 = shell(base())
    doms = sorted(d0.dom)
    rows = {}
    b0 = None
    for di, ds in enumerate([None] + list(DRAWS)):
        if ds is None:
            data, wr = d0, "없음"
            tag = "① 없이"
        else:
            # **뽑기마다 씨앗을 따로 준다** --- 이것이 이 실험의 대상이다
            rng = np.random.default_rng(ds)
            ax = {}
            for j in range(NCOL):
                ax[f"{AX}_{j}"] = {}
            for d in doms:
                v = rng.random((len(d0.dom[d][2]), NCOL))
                for j in range(NCOL):
                    ax[f"{AX}_{j}"][d] = (v[:, j].astype(np.float32),
                                          np.ones(v.shape[0], np.float32))
            wr = {n: {d: {"관측": int(ax[n][d][1].sum()),
                          "고유": int(len(np.unique(ax[n][d][0])))} for d in doms}
                  for n in ax}
            data = shell({**base(), **ax})
            tag = f"뽑기 {ds}"
        r = board(data, tag)
        if b0 is None:
            b0 = r["판"]
            if not (BASE_OK[0] <= b0 <= BASE_OK[1]):
                print(json.dumps({"중단": f"기준선 {b0} 이 {BASE_OK} 밖"},
                                 ensure_ascii=False), flush=True)
                return
        else:
            r["하락(없이 − 팔)"] = round(b0 - r["판"], 4)
            r["배선"] = {"열 수": len(wr),
                        "전 도메인 붙음": all(all(wr[n][d]["관측"] > 0 for d in doms)
                                        for n in wr),
                        "고유값(첫 열)": {d: wr[list(wr)[0]][d]["고유"] for d in doms}}
        rows[tag] = r
        print(f"[{tag}] " + json.dumps(
            {kk: r[kk] for kk in ("판", "씨앗SD", "하락(없이 − 팔)", "초") if kk in r},
            ensure_ascii=False), flush=True)

    base_seeds = np.array(rows["① 없이"]["씨앗별"])
    per_draw = {}
    for ds in DRAWS:
        t = f"뽑기 {ds}"
        v = np.array(rows[t]["씨앗별"])
        d = base_seeds - v
        per_draw[t] = {"하락 평균": round(float(d.mean()), 4),
                       "모형 씨앗 SD": round(float(v.std(ddof=1)), 4),
                       "씨앗별 하락": [round(float(x), 4) for x in d]}
    means = np.array([per_draw[t]["하락 평균"] for t in per_draw])
    draw_sd = float(means.std(ddof=1))
    model_sd = float(np.mean([per_draw[t]["모형 씨앗 SD"] for t in per_draw]))
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "기준선(없이)": b0,
        "**뽑기별 3열 하락**": {t: per_draw[t]["하락 평균"] for t in per_draw},
        "**뽑기 평균**": round(float(means.mean()), 4),
        "**뽑기 SD**": round(draw_sd, 4),
        "**모형 씨앗 SD(뽑기 안 · 평균)**": round(model_sd, 4),
        "**뽑기 SD / 모형 SD**": round(draw_sd / max(model_sd, 1e-9), 2),
        "판정 (가) 뽑기 SD > 3 × 모형 SD": bool(draw_sd > 3 * model_sd),
        "판정 (나) 뽑기 SD ≤ 모형 SD": bool(draw_sd <= model_sd),
        "판정 (다) 음수 뽑기": [t for t in per_draw
                          if per_draw[t]["하락 평균"] < 0],
        "**3열 비용 참값 범위(평균 ± 2σ 뽑기)**":
            [round(float(means.mean() - 2 * draw_sd), 4),
             round(float(means.mean() + 2 * draw_sd), 4)],
        "판 2σ": 0.0045,
        "**문턱의 몇 배(범위)**":
            [round(float((means.mean() - 2 * draw_sd) / 0.0045), 2),
             round(float((means.mean() + 2 * draw_sd) / 0.0045), 2)],
        "노트 738 의 3열": 0.0043, "노트 740 의 3열": 0.0167,
        "틀림 조건 · 모형 SD > 0.005": bool(model_sd > 0.005),
        "뽑기별 자세히": per_draw,
        "팔별": rows,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
