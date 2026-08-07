"""노트 739 — **비용이 열 수에 볼록해지나.** 연속 쓰레기 1·3·10·30열. 씨앗 6.

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
SEEDS = tuple(range(6))
NCOL = 30   # 30열용 난수를 한 번 뽑고 **앞에서부터 잘라 쓴다**(팔들이 포개진다)
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
    # ── 도메인마다 연속 난수 3벡터. **모든 팔이 이것을 공유한다.**
    rng = np.random.default_rng(737)
    raw = {}
    for d in doms:
        n = len(d0.dom[d][2])
        raw[d] = rng.random((n, NCOL))
    print(json.dumps({"도메인 행수": {d: raw[d].shape[0] for d in doms}},
                     ensure_ascii=False), flush=True)

    def make(k, ncol):
        """k 단계로 도메인 안 분위 이산화. k=None 이면 연속 그대로."""
        out = {}
        for d in doms:
            v = raw[d][:, :ncol]
            if k is not None:
                # **도메인 안 분위** --- 행수보다 k 가 크면 고유값이 행수에 막힌다
                q = np.clip(np.floor(v * k), 0, k - 1) / max(k - 1, 1)
                v = q
            m = np.ones(v.shape[0], np.float32)
            if ncol == 1:
                out[d] = (v[:, 0].astype(np.float32).copy(), m)
            else:
                for j in range(ncol):
                    out.setdefault("__multi__", {})
        return out

    def cols(k, ncol):
        """축 딕트를 만든다 --- 열마다 이름을 따로 준다(`_idol` 규약)."""
        ax = {}
        for j in range(ncol):
            per = {}
            for d in doms:
                v = raw[d][:, j].astype(np.float64).copy()
                if k is not None:
                    v = np.clip(np.floor(v * k), 0, k - 1) / max(k - 1, 1)
                per[d] = (v.astype(np.float32), np.ones(len(v), np.float32))
            ax[f"{AX}{'c' if k is None else k}_{j}"] = per
        return ax

    def wiring(ax):
        """🔴 배선 검사 --- 중립화(0.5 · 마스크 0)를 잡는다."""
        rep = {}
        for name, per in ax.items():
            rep[name] = {d: {"관측": int(np.asarray(per[d][1]).sum()),
                             "고유": int(len(np.unique(np.asarray(per[d][0]))))}
                         for d in doms}
        return rep

    ARMS = [("① 없이", None, 0),
            ("② 연속 · 1열", None, 1),
            ("③ 연속 · 3열", None, 3),
            ("④ 연속 · 10열", None, 10),
            ("⑤ 연속 · 30열", None, 30)]

    out = {}
    b0 = None
    for tag, k, ncol in ARMS:
        if ncol == 0:
            data = d0
            wr = "없음"
        else:
            ax = cols(k, ncol)
            wr = wiring(ax)
            data = shell({**base(), **ax})
        r = board(data, tag)
        if b0 is None:
            b0 = r["판"]
            if not (BASE_OK[0] <= b0 <= BASE_OK[1]):
                print(json.dumps({"중단": f"기준선 {b0} 이 {BASE_OK} 밖"},
                                 ensure_ascii=False), flush=True)
                return
        r["열 수"] = ncol
        r["카디널리티"] = "연속" if k is None else k
        if ncol:
            r["하락(없이 − 팔)"] = round(b0 - r["판"], 4)
            r["**열당 비용**"] = round((b0 - r["판"]) / ncol, 4)
            # 배선: 도메인마다 붙었나 · 고유값 수
            r["배선"] = {"열 수": len(wr),
                         "전 도메인 붙음": all(
                             all(wr[n][d]["관측"] > 0 for d in doms) for n in wr),
                         "고유값(첫 열)": {d: wr[list(wr)[0]][d]["고유"] for d in doms}}
        out[tag] = r
        print(f"[{tag}] " + json.dumps(
            {kk: r[kk] for kk in ("판", "씨앗SD", "하락(없이 − 팔)", "**열당 비용**", "초")
             if kk in r}, ensure_ascii=False), flush=True)

    # ── 곡선과 판정
    b = np.array(out["① 없이"]["씨앗별"])
    paired = {}
    for t in out:
        if t == "① 없이":
            continue
        dd = b - np.array(out[t]["씨앗별"])
        sd = float(dd.std(ddof=1))
        paired[t] = {"하락": round(float(dd.mean()), 4), "짝SD": round(sd, 4),
                     "**2σ**": round(2 * sd, 4),
                     "**2σ 밖**": bool(abs(dd.mean()) > 2 * sd),
                     "씨앗별 차": [round(float(x), 4) for x in dd]}
    d1 = paired["② 연속 · 1열"]["하락"]
    d3 = paired["③ 연속 · 3열"]["하락"]
    d10 = paired["④ 연속 · 10열"]["하락"]
    d30 = paired["⑤ 연속 · 30열"]["하락"]
    ratio = round(d30 / d3, 2) if abs(d3) > 1e-9 else None
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "기준선(없이)": b0,
        "노트 737 기준선": 0.4685,
        "**열 수 곡선(하락)**": {"1": d1, "3": d3, "10": d10, "30": d30},
        "**열당 비용**": {"1": round(d1, 4), "3": round(d3 / 3, 4),
                     "10": round(d10 / 10, 4), "30": round(d30 / 30, 4)},
        "**30열/3열 배수**": ratio,
        "선형이면": 10,
        "판정 (가) 선형 이하(≤10)": bool(ratio is not None and ratio <= 10),
        "판정 (나) 약한 초선형(10~20)": bool(ratio is not None and 10 < ratio <= 20),
        "판정 (다) 강한 초선형(>20)": bool(ratio is not None and ratio > 20),
        "판정 (라) 30열 하락 > 0.02": bool(d30 > 0.02),
        "틀림 조건 · 1열이 노트 738 과 다른가(|차|>0.0037)":
            bool(abs(d1 - (-0.0021)) > 0.0037),
        "노트 738 의 1열": -0.0021, "노트 738 의 3열": 0.0043,
        "짝지은 값": paired,
        "팔별": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
