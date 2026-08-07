"""노트 720 — **도메인 임베딩이 도메인 차이를 담을 수 있나.** 세 팔 · 씨앗 12.

판정 셋(노트 685 가 미리 못박음):
  (가) 얇은 셋(팝업·아이돌·도서)에 축이 붙고 그 셋의 신호 몫이 양수인가
  (나) 판 신호 몫이 도메인별 축의 +0.0119 를 넘는가
  (다) 도메인 임베딩이 붕괴하지 않는가(짝 코사인 최대 < 0.95)
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import forms, guards as G, loop as L, textnn as NN
from lab.harness import evaluate, load

T = 2025.0
SEEDS = tuple(range(12))
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
THIN = ("팝업", "아이돌", "도서")


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


def shell(extra):
    """챔피언 껍질 --- 노트 704 가 이것을 안 써서 결론이 뒤집혔다."""
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
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4),
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()},
            "_vals": [round(v, 5) for v in vals]}


def main():
    print("=== 없이(챔피언) ===", flush=True)
    d0 = shell(base())
    b0 = board(d0)
    print(json.dumps({"없이": {k: v for k, v in b0.items() if k != "도메인"}},
                     ensure_ascii=False), flush=True)

    print("=== 축을 만든다(textnn) ===", flush=True)
    nn = NN.build(d0, T=T, report=True)
    if not nn:
        print(json.dumps({"멈춘다": "textnn 이 축을 못 만들었다"},
                         ensure_ascii=False), flush=True)
        return
    col = nn[NN.AX]
    print(json.dumps({"축 붙은 도메인": sorted(col),
                      "얇은 셋 붙음": {t: (t in col) for t in THIN}},
                     ensure_ascii=False), flush=True)

    # ── 임베딩 붕괴 검사(다) --- `NN.LAST` 에서 읽는다(노트 720 이 붙인 자리)
    cos = NN.LAST.get("붕괴")
    print(json.dumps({"임베딩 붕괴 검사": cos,
                      "한 통 학습": NN.LAST.get("한 통 학습"),
                      "한 통 유보": NN.LAST.get("한 통 유보")},
                     ensure_ascii=False), flush=True)

    print("=== 진짜 ===", flush=True)
    d1 = shell({**base(), NN.AX: col})
    b1 = board(d1)
    print(json.dumps({"진짜": {k: v for k, v in b1.items() if k != "도메인"}},
                     ensure_ascii=False), flush=True)

    print("=== 위약(값만 도메인 안에서 섞음) ===", flush=True)
    rng = np.random.default_rng(720)
    plac = {}
    for dom, (v, m) in col.items():
        v2 = np.asarray(v, float).copy()
        idx = np.flatnonzero(np.asarray(m) > 0)
        if len(idx) > 1:
            sh = v2[idx].copy(); rng.shuffle(sh); v2[idx] = sh
        plac[dom] = (v2, m)
    d2 = shell({**base(), NN.AX: plac})
    b2 = board(d2)
    print(json.dumps({"위약": {k: v for k, v in b2.items() if k != "도메인"}},
                     ensure_ascii=False), flush=True)

    sig = round(b1["판"] - b2["판"], 4)
    net = round(b1["판"] - b0["판"], 4)
    W = d0.weights(T)
    tot = sum(W.values())
    per = {}
    for dom in set(b1["도메인"]) | set(b2["도메인"]):
        r = b1["도메인"].get(dom)
        p = b2["도메인"].get(dom)
        if r is None or p is None:
            continue
        per[dom] = {"신호 몫": round(r - p, 4), "유보": W.get(dom, 0),
                    "판 기여": round((r - p) * W.get(dom, 0) / tot, 5)}
    thin_w = sum(W.get(t, 0) for t in THIN)
    thin_sig = (sum(per[t]["신호 몫"] * W.get(t, 0) for t in THIN if t in per)
                / thin_w) if thin_w else None
    # 문턱 ±50% 안이면 도메인 기여로 분해(T5 미결)
    top = sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))[:3]
    drop = {}
    for dom, _ in top:
        num = sum(per[d]["신호 몫"] * W[d] for d in per if d != dom and d in W)
        den = sum(W[d] for d in per if d != dom and d in W)
        drop[f"{dom} 뺀 판"] = round(num / den, 4) if den else None
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"], "진짜": b1["판"], "위약": b2["판"],
        "**신호 몫**": sig, "**순효과**": net,
        "문턱": 0.0045, "도메인별 축 비교 기준(노트 695)": 0.0119,
        "판정 (나)": ("**+0.0119 를 넘는다**" if sig > 0.0119
                   else "문턱은 넘는다" if sig > 0.0045 else "미달"),
        "판정 (가) 얇은 셋": {"축 붙음": {t: (t in col) for t in THIN},
                        "가중 합": thin_w,
                        "신호 몫": (round(thin_sig, 4) if thin_sig is not None else None)},
        "판정 (다) 임베딩": cos,
        "도메인별": per,
        "가장 크게 끄는 셋을 뺀 판": drop,
        "씨앗SD": {"없이": b0["씨앗SD"], "진짜": b1["씨앗SD"], "위약": b2["씨앗SD"]},
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
