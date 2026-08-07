"""노트 748 — **동률 구조가 남은 4.4배인가.** 마스크를 고정하고 값 꼴만 흔든다.

노트 745 의 부분관측 위약 1열이 −0.0302 이고 노트 742 의 완전관측 쓰레기 1열은
약 0.005 다. **6배 차이의 유일한 후보가 결측 무늬**다. 여기서는 난수 값을
고정하고 **덮음률만** 1.00 / 0.53 / 0.27 로 바꾼다. 마스크는 무작위가 아니라
**시기로 잘린 무늬**(장이 2020 부터라 오래된 행이 빠지는 그 모양)를 쓴다.

모든 팔이 위약이므로 신호 주장을 하지 않는다.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import rankdata

from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)
DRAWS = (7480, 7481, 7482)
#: 마스크는 노트 745 의 것 고정(y >= 2020.15). **값 꼴만 흔든다.**
CUT = 2020.15
FORMS = ["① 동률 없음", "② 날짜 동률", "③ 극단 동률(고유 6)"]
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "tiejunk"
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
    d0 = shell(base())
    doms = sorted(d0.dom)
    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"], "씨앗SD": b0["씨앗SD"]},
                     ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']}"}, ensure_ascii=False), flush=True)
        return

    out = {}
    for ds in DRAWS:
        for form in FORMS:
            rng = np.random.default_rng(ds + 17 * FORMS.index(form))
            ax = {}
            for dm in doms:
                y = np.asarray(d0.yr[dm], float)
                m = np.isfinite(y) & (y >= CUT)
                v = np.full(len(y), 0.5, np.float32)
                if m.sum() >= 3:
                    if form == FORMS[0]:
                        raw = rng.random(int(m.sum()))
                    elif form == FORMS[1]:
                        # **날짜 동률** --- 같은 날(소수연도 반올림 1/365) 행이 같은 값
                        key = np.round(y[m] * 365).astype(np.int64)
                        uk = {k: rng.random() for k in np.unique(key)}
                        raw = np.array([uk[k] for k in key])
                    else:
                        # **극단 동률** --- 고유값 6 개로 뭉친다
                        lv = rng.random(6)
                        raw = lv[rng.integers(0, 6, int(m.sum()))]
                    v[m] = (rankdata(raw) / m.sum()).astype(np.float32)
                ax[dm] = (v, m.astype(np.float32))
            wr = {dm: {"관측": int(ax[dm][1].sum()), "행": len(ax[dm][1]),
                       "덮음률": round(float(ax[dm][1].mean()), 3),
                       "고유": int(len(np.unique(ax[dm][0][ax[dm][1] > 0])))}
                  for dm in doms}
            covall = round(sum(wr[dm]["관측"] for dm in doms)
                           / sum(wr[dm]["행"] for dm in doms), 3)
            t0 = time.time()
            r = board(shell({**base(), AX: ax}))
            r["하락"] = round(b0["판"] - r["판"], 4)
            r["전체 덮음률"] = covall
            r["배선"] = wr
            out[f"{form} · 뽑기 {ds}"] = r
            print(f"[{form} · 뽑기 {ds}] " + json.dumps(
                {"판": r["판"], "하락": r["하락"], "덮음": covall,
                 "고유(웹툰)": wr["웹툰"]["고유"], "고유(펀딩)": wr["펀딩"]["고유"],
                 "초": round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)

    agg = {}
    for form in FORMS:
        vv = np.array([out[f"{form} · 뽑기 {d}"]["하락"] for d in DRAWS])
        agg[form] = {"하락 평균": round(float(vv.mean()), 4),
                     "**뽑기 SD**": round(float(vv.std(ddof=1)), 4),
                     "뽑기별": [round(float(x), 4) for x in vv]}
    a0 = agg[FORMS[0]]; a1 = agg[FORMS[1]]; a2 = agg[FORMS[2]]
    def sig3(x, y):
        """**비교하는 두 팔의 SD 로 자를 만든다**(노트 747 의 교훈)."""
        sd = float(np.sqrt(x["**뽑기 SD**"] ** 2 + y["**뽑기 SD**"] ** 2))
        return {"차": round(y["하락 평균"] - x["하락 평균"], 4),
                "합성 SD": round(sd, 4), "3σ": round(3 * sd, 4),
                "3σ 밖": bool(abs(y["하락 평균"] - x["하락 평균"]) > 3 * sd)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "기준선(없이)": b0["판"],
        "**값 꼴별 1열 비용**": agg,
        "② − ①": sig3(a0, a1), "③ − ①": sig3(a0, a2),
        "판정 (가) ② 또는 ③ 이 ① 보다 3σ 비싸다":
            bool((a1["하락 평균"] - a0["하락 평균"] > 3 * np.sqrt(
                a0["**뽑기 SD**"] ** 2 + a1["**뽑기 SD**"] ** 2))
                 or (a2["하락 평균"] - a0["하락 평균"] > 3 * np.sqrt(
                     a0["**뽑기 SD**"] ** 2 + a2["**뽑기 SD**"] ** 2))),
        "판정 (다) ③ 이 ① 보다 싸다": bool(a2["하락 평균"] < a0["하락 평균"]),
        "노트 747 의 0.53 팔": 0.0068,
        "노트 745 위약(설명할 값)": 0.0302,
        "틀림 조건 · ① 이 0.0068 에서 3×뽑기SD 밖":
            bool(abs(a0["하락 평균"] - 0.0068) > 3 * a0["**뽑기 SD**"]),
        "팔별": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
