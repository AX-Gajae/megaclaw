"""게이트 --- 어느 출처를 얼마나 믿을지 **도메인을 건너 배운다**.

노트 71이 균등 앙상블을 세웠고 노트 73이 합의 가중을 시도했다(판정치 이득
$+$0.0073, 구간이 0을 포함해 보류). 둘 다 대상 라벨을 안 쓴다는 점은 좋은데,
쓸 수 있는 정보를 다 안 썼다.

    **다른 여섯 대상에서는 정답을 안다.** 출처 s가 대상 t를 얼마나 잘 맞히는지는
    t의 라벨이 있어야 알지만, *다른* 대상들에 대해서는 라벨이 있으므로 이미 안다.
    거기서 ``어떤 쌍이 잘 되는가''를 배워 새 대상에 옮기면 된다.

이것이 게이트다 --- 쌍의 성질에서 셀 성적을 예측하는 작은 모형. 대상 라벨을
한 건도 안 쓰고 앙상블 가중치를 정한다. 혼합 전문가(Jacobs 1991)의 게이팅
망과 같은 자리이고, 학습 표본이 **셀 42개**뿐이라 망 대신 능형 회귀를 쓴다.
노트 60--62에서 공유 인코더가 PCA+프로크루스테스에 진 이유도 같았다 --- 표본이
망을 못 먹인다. 여덟째 도메인이 오면 셀이 56개가 되고, 그때 다시 본다.

**쌍 특징(전부 대상 라벨 없이 구한다).**

    합의 가중치   이 출처가 나머지 출처들의 합의와 얼마나 맞나(노트 73)
    출처 자기 ρ   출처 도메인 안에서 축이 라벨을 얼마나 설명하나(출처는 라벨 보유)
    정렬 잔차     프로크루스테스가 공통 축 적재를 맞추고 남긴 오차
    공통 축 수    둘이 함께 관측한 공통 축의 개수
    표본 크기     log10 출처 n · log10 대상 n
    축 개수       출처 관측 축 수 · 대상 관측 축 수

**한 도메인 빼고 학습한다.** 대상 t의 가중치를 정할 때 t가 대상인 셀은 학습에서
전부 뺀다 --- 그러지 않으면 t의 라벨이 새어 든다.

사용: python3 -m state.gate
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .audit import domains
from .consensus import consensus_w, wblend
from .ensemble import blend, cells
from .procrustes import align_pair, procrustes
from .rank_test import spearman

SEED = 20260729
OUT = Path("data/state/gate.json")
FEATS = ["합의 가중치", "출처 자기 ρ", "정렬 잔차", "공통 축 수",
         "log 출처 n", "log 대상 n", "출처 축 수", "대상 축 수"]


def _self_rho(F, seed: int = SEED) -> float:
    """도메인 안 교차검증 자기 상관. 출처는 라벨이 있으므로 공짜다."""
    S, y = F["S"], F["y"]
    pr = np.zeros(len(y))
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(S):
        pr[te] = Ridge(alpha=1.0).fit(S[tr], y[tr]).predict(S[te])
    return spearman(pr, y)


def _resid(Fs, Ft) -> float:
    """정렬 잔차 --- 회전으로 못 맞춘 적재의 비율."""
    shared = [a for a in Ft["axes"] if a in Fs["axes"]]
    shared = [a for a in shared if a in ("target_breadth", "goods_scale",
                                         "venue_prominence")]
    if len(shared) < 2:
        return float("nan")
    Ls = Fs["V"][[Fs["axes"].index(a) for a in shared], :]
    Lt = Ft["V"][[Ft["axes"].index(a) for a in shared], :]
    R = procrustes(Ls, Lt)
    return float(np.linalg.norm(Ls @ R - Lt) / (np.linalg.norm(Lt) + 1e-9))


def build():
    """셀마다 특징과 성적. 특징은 전부 대상 라벨 없이 구한다."""
    doms, names = domains()
    C = cells(doms, names)
    F = {t: C[t][1] for t in C}
    selfr = {k: _self_rho(v) for k, v in F.items()}
    rows = []
    for t, (cs, Ft) in C.items():
        ps = [p for _, p in cs]
        w = consensus_w(ps)
        for i, (s, p) in enumerate(cs):
            Fs = F[s]
            shared = align_pair(Fs, Ft)
            rows.append({
                "s": s, "t": t,
                "x": [float(w[i]), float(selfr[s]), _resid(Fs, Ft),
                      float(len(shared[1])) if shared else 0.0,
                      float(np.log10(Fs["n"])), float(np.log10(Ft["n"])),
                      float(len(Fs["axes"])), float(len(Ft["axes"]))],
                "rho": float(spearman(p, Ft["y"]))})
    return C, rows


def gate_weights(rows, tgt, alpha: float = 3.0):
    """대상 tgt 를 학습에서 빼고 셀 성적을 예측한다."""
    tr = [r for r in rows if r["t"] != tgt]
    te = [r for r in rows if r["t"] == tgt]
    X = np.array([r["x"] for r in tr], float)
    y = np.array([r["rho"] for r in tr], float)
    ok = np.isfinite(X).all(1) & np.isfinite(y)
    mu, sd = X[ok].mean(0), X[ok].std(0) + 1e-9
    m = Ridge(alpha=alpha).fit((X[ok] - mu) / sd, y[ok])
    Xt = np.nan_to_num(np.array([r["x"] for r in te], float), nan=0.0)
    return m, [r["s"] for r in te], m.predict((Xt - mu) / sd)


def run(write: bool = True) -> dict:
    C, rows = build()
    out, coef = {}, None
    for t, (cs, Ft) in C.items():
        ps = [p for _, p in cs]
        m, srcs, pred = gate_weights(rows, t)
        coef = m.coef_ if coef is None else coef
        eq = spearman(blend(ps), Ft["y"])
        cw = spearman(wblend(ps, np.clip(consensus_w(ps), 0, None)), Ft["y"])
        gw = spearman(wblend(ps, np.clip(pred, 0, None)), Ft["y"])
        out[t] = {"eq": round(float(eq), 4), "cons": round(float(cw), 4),
                  "gate": round(float(gw), 4),
                  "w": {s: round(float(p), 3) for s, p in zip(srcs, pred)}}
    print("대상별 --- 게이트는 대상 라벨 0건\n")
    print(f"{'대상':<7}{'균등':>9}{'합의 클립':>11}{'게이트':>9}")
    for t, v in out.items():
        print(f"{t:<7}{v['eq']:>+9.4f}{v['cons']:>+11.4f}{v['gate']:>+9.4f}")
    for lab, k in (("균등", "eq"), ("합의 클립", "cons"), ("게이트", "gate")):
        print(f"  판정치 {lab:<10}{np.mean([v[k] for v in out.values()]):+.4f}")
    # 게이트가 무엇을 배웠나 --- 전체 셀로 한 번 더 적합해 계수를 본다.
    X = np.array([r["x"] for r in rows], float)
    y = np.array([r["rho"] for r in rows], float)
    ok = np.isfinite(X).all(1) & np.isfinite(y)
    Z = (X[ok] - X[ok].mean(0)) / (X[ok].std(0) + 1e-9)
    full = Ridge(alpha=3.0).fit(Z, y[ok])
    print("\n특징 계수(표준화, 전체 셀 적합)")
    for f, c in sorted(zip(FEATS, full.coef_), key=lambda z: -abs(z[1])):
        print(f"  {f:<12}{c:+.4f}")
    print(f"  셀 {int(ok.sum())}개 · 자기 적합 R² {full.score(Z, y[ok]):.3f}")
    if write:
        OUT.write_text(json.dumps(
            {"per_target": out, "coef": dict(zip(FEATS, [round(float(c), 4)
                                                         for c in full.coef_])),
             "r2": round(float(full.score(Z, y[ok])), 3), "n_cell": int(ok.sum())},
            ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return out


if __name__ == "__main__":
    run()
