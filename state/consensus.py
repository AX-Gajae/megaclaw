"""합의 정향 --- 출처들끼리 서로의 방향을 잡아 준다. 라벨 없이.

노트 69가 문제를 찾았고 노트 70 · 72가 값을 쟀다. 방향을 대상 라벨로 정하려면
32건이 들고, 그 아래에서는 추측이 손해다. 그런데 대상 라벨을 안 쓰고도 쓸 수
있는 정보가 하나 남아 있었다 --- **다른 출처들의 의견**.

    팝업을 맞히는 여섯 출처 중 다섯이 서로 $+$0.4대로 같은 쪽을 가리키고
    애니 하나만 $-$0.31로 반대다. 애니가 뒤집혔다는 것을 **팝업 라벨을 한 건도
    안 보고** 알 수 있다.

**부호는 두 조각으로 나뉜다.**

    상대 방향  출처들끼리 같은 쪽을 보게 맞추는 것 --- **라벨 0건**
    전역 방향  맞춰진 전체가 어느 쪽인지 --- 라벨이 든다

지금까지 둘을 구분하지 않아 여섯 번의 결정을 전부 라벨로 샀다. 상대 방향이
공짜면 남는 결정은 **하나**뿐이다. 노트 71이 바라던 것인데, 그때는 상대 방향을
못 고쳐 여섯 결정을 헤지로 유지해야 했다.

**전역 방향의 기본값은 다수결이다.** 합의로 상대 부호를 맞춘 뒤, 원래 방향을
유지한 출처가 더 많은 쪽을 택한다. 대부분의 출처가 옳게 정향돼 있다는 가정이며
--- 일곱 도메인 중 여섯이 그렇다 --- 틀리면 대상 라벨로 뒤집는다.

참고: Wolpert(1992) 적층 일반화, Breiman(1996) 적층 회귀. 다만 그것들은 라벨로
가중치를 배우고 여기서는 **라벨 없이 부호만** 맞춘다.

사용: python3 -m state.consensus
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from .audit import domains
from .ensemble import blend, cells
from .orient import _sign, cal_label
from .rank_test import spearman

SEED = 20260729
OUT = Path("data/state/consensus.json")


def consensus_signs(preds, iters: int = 5):
    """서로의 합의에 맞춰 상대 부호를 정한다. 대상 라벨을 안 쓴다.

    각 출처를 뺀 나머지의 순위 평균과 그 출처의 순위를 비교해, 반대면 뒤집는다.
    수렴할 때까지(최대 iters) 반복한다.

    **전역 부호는 다수결로 고정한다** --- 원래 방향을 유지한 출처가 더 많은
    쪽. 합의만으로는 전체를 통째로 뒤집는 자유도가 남기 때문이다."""
    R = [rankdata(p) / len(p) for p in preds]
    s = np.ones(len(preds))
    for _ in range(iters):
        new = s.copy()
        for i in range(len(R)):
            oth = [s[j] * R[j] for j in range(len(R)) if j != i]
            if not oth:
                continue
            c = np.mean(oth, axis=0)
            if spearman(s[i] * R[i], c) < 0:
                new[i] = -s[i]
        if np.array_equal(new, s):
            break
        s = new
    if s.sum() < 0:                      # 전역 부호 --- 다수결
        s = -s
    return s


def apply_signs(preds, s):
    return [float(si) * p for si, p in zip(s, preds)]


def consensus_w(preds, iters: int = 5):
    """각 출처가 나머지의 합의와 얼마나 맞는지 --- **연속 가중치**.

    부호 뒤집기는 이 값의 부호만 쓰는 특수한 경우다. 크기까지 쓰면 합의에서
    조금 벗어난 출처는 조금만 깎인다. 대상 라벨을 안 쓴다."""
    R = [rankdata(p) / len(p) for p in preds]
    w = np.ones(len(preds))
    for _ in range(iters):
        new = np.array([
            spearman(R[i], np.average([R[j] for j in range(len(R)) if j != i],
                                      axis=0,
                                      weights=[w[j] for j in range(len(R)) if j != i]))
            if abs(sum(w[j] for j in range(len(R)) if j != i)) > 1e-9 else w[i]
            for i in range(len(R))])
        if np.allclose(new, w, atol=1e-4):
            w = new
            break
        w = new
    if w.sum() < 0:
        w = -w
    return w


def wblend(preds, w):
    """가중 순위 평균. 가중치가 음수면 그 출처를 뒤집어 넣는 것과 같다."""
    R = np.column_stack([rankdata(p) / len(p) for p in preds])
    s = np.abs(w).sum()
    return R @ (np.asarray(w, float) / (s if s > 1e-9 else 1.0))


def table(seed: int = SEED, B: int = 400) -> dict:
    """대상별 --- 균등 앙상블 대 합의 정향 앙상블. 둘 다 라벨 0건."""
    doms, names = domains()
    C = cells(doms, names)
    rng = np.random.default_rng(seed)
    out = {}
    for t, (rows, F) in C.items():
        y = F["y"]
        ps = [p for _, p in rows]
        s = consensus_signs(ps)
        w = consensus_w(ps)
        e0 = spearman(blend(ps), y)
        e1 = spearman(blend(apply_signs(ps, s)), y)
        e2 = spearman(wblend(ps, w), y)
        e3 = spearman(wblend(ps, np.clip(w, 0, None)), y)
        d = []
        n = len(y)
        for _ in range(B):
            ix = rng.choice(n, size=n, replace=True)
            q = [p[ix] for p in ps]
            sb, wb = consensus_signs(q), consensus_w(q)
            a = spearman(blend(q), y[ix])
            b = spearman(blend(apply_signs(q, sb)), y[ix])
            c = spearman(wblend(q, wb), y[ix])
            g = spearman(wblend(q, np.clip(wb, 0, None)), y[ix])
            if all(np.isfinite(x) for x in (a, b, c, g)):
                d.append([b - a, c - a, g - a])
        v = np.array(d)
        lo, hi = np.percentile(v, [2.5, 97.5], axis=0)
        out[t] = {"n": int(n), "eq": round(float(e0), 4), "cons": round(float(e1), 4),
                  "soft": round(float(e2), 4), "clip": round(float(e3), 4),
                  "d": [round(float(x), 4) for x in v.mean(0)],
                  "ci": [[round(float(a), 4), round(float(b), 4)]
                         for a, b in zip(lo, hi)],
                  "w": {rows[i][0]: round(float(w[i]), 3) for i in range(len(ps))},
                  "flipped": [rows[i][0] for i in range(len(ps)) if s[i] < 0]}
    return out


def sign_curve(ks=(0, 4, 8, 16, 24, 32), reps: int = 150, seed: int = SEED) -> dict:
    """합의로 상대 부호를 맞춘 뒤 **전역 부호 하나만** 라벨로 정한다.

    노트 72의 최선(부호 뒤 합치기)은 결정을 여섯 번 했다. 여기서는 한 번이다."""
    doms, names = domains()
    C = cells(doms, names)
    kmax = max(ks)
    rng = np.random.default_rng(seed)
    MODES = ("plain", "cons", "cons_k")
    acc = {k: {m: [] for m in MODES} for k in ks}
    for _ in range(reps):
        per = {k: {m: [] for m in MODES} for k in ks}
        for t, (rows, F) in C.items():
            y, n = F["y"], len(F["y"])
            if n <= kmax + 20:
                continue
            perm = rng.permutation(n)
            ev, pool = perm[kmax:], perm[:kmax]
            ps = [p for _, p in rows]
            s = consensus_signs([p[ev] for p in ps])
            e_plain = blend(ps, ev)
            e_cons = blend(apply_signs([p[ev] for p in ps], s))
            for k in ks:
                per[k]["plain"].append(spearman(e_plain, y[ev]))
                per[k]["cons"].append(spearman(e_cons, y[ev]))
                if k == 0:
                    per[k]["cons_k"].append(spearman(e_cons, y[ev]))
                    continue
                cal = pool[:k]
                yc = cal_label(F, cal)
                sc = consensus_signs([p[cal] for p in ps])
                g = _sign(spearman(blend(apply_signs([p[cal] for p in ps], sc)), yc))
                per[k]["cons_k"].append(spearman(g * e_cons, y[ev]))
        for k in ks:
            for m in MODES:
                if per[k][m]:
                    acc[k][m].append(float(np.mean(per[k][m])))
    z0 = np.array(acc[0]["plain"])
    out = {}
    for k in ks:
        row = {}
        for m in MODES:
            v = np.array(acc[k][m])
            d = v - z0
            lo, hi = np.percentile(d, [2.5, 97.5])
            row[m] = {"rho": round(float(v.mean()), 4), "d": round(float(d.mean()), 4),
                      "ci": [round(float(lo), 4), round(float(hi), 4)]}
        out[k] = row
    return out


def run(write: bool = True) -> dict:
    t = table()
    print("대상별 --- 합의 정향(라벨 0건)\n")
    print(f"{'대상':<7}{'n':>6}{'균등':>9}{'뒤집기':>9}{'소프트':>9}{'클립':>9}"
          f"   소프트 95% 구간")
    for k, v in t.items():
        print(f"{k:<7}{v['n']:>6}{v['eq']:>+9.4f}{v['cons']:>+9.4f}"
              f"{v['soft']:>+9.4f}{v['clip']:>+9.4f}"
              f"   [{v['ci'][1][0]:+.4f}, {v['ci'][1][1]:+.4f}]"
              f"{'  채택' if v['ci'][1][0] > 0 else ''}")
    for lab, key in (("균등", "eq"), ("합의 뒤집기", "cons"), ("소프트 가중", "soft"),
                     ("클립 가중", "clip")):
        print(f"  판정치 {lab:<12}{np.mean([v[key] for v in t.values()]):+.4f}")
    print("\n합의 가중치(팝업):", t["팝업"]["w"])
    s = sign_curve()
    print("\n전역 부호를 k건으로 정한다 (유보 평가)")
    print(f"{'k':>4}{'균등':>10}{'합의':>10}{'합의+k':>10}")
    for k, v in s.items():
        print(f"{k:>4}{v['plain']['rho']:>+10.4f}{v['cons']['rho']:>+10.4f}"
              f"{v['cons_k']['rho']:>+10.4f}")
    print("\n균등·보정 없음 대비 짝지은 차이")
    for k, v in s.items():
        c = v["cons_k"]
        print(f"  k={k:<3} Δ{c['d']:+.4f} [{c['ci'][0]:+.4f}, {c['ci'][1]:+.4f}]"
              f"{'  채택' if c['ci'][0] > 0 else ''}")
    if write:
        OUT.write_text(json.dumps({"table": t, "sign": {str(k): v for k, v in s.items()}},
                                  ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return {"table": t, "sign": s}


if __name__ == "__main__":
    run()


def rho_cons(doms, names=None, mode: str = "clip") -> float:
    """합의 가중 앙상블 판정치. mode: eq · flip · soft · clip. 라벨 0건."""
    C = cells(doms, names)
    rs = []
    for _t, (rows, F) in C.items():
        ps = [p for _, p in rows]
        if not ps:
            continue
        if mode == "eq":
            e = blend(ps)
        elif mode == "flip":
            e = blend(apply_signs(ps, consensus_signs(ps)))
        else:
            w = consensus_w(ps)
            e = wblend(ps, np.clip(w, 0, None) if mode == "clip" else w)
        rs.append(spearman(e, F["y"]))
    return float(np.mean(rs)) if rs else float("nan")


def paired_metric(modes=("flip", "soft", "clip"), B: int = 200,
                  seed: int = SEED) -> dict:
    """판정치 수준의 짝지은 붓스트랩 --- 균등 대비. audit 의 복원추출을 쓴다."""
    from .audit import _resample, _set_idx, domains as _dom
    base, names = _dom()
    rng = np.random.default_rng(seed)
    d = {m: [] for m in modes}
    for _ in range(B):
        rs, ix = _resample(base, rng)
        _set_idx(ix)
        try:
            a = rho_cons(rs, names, "eq")
            for m in modes:
                b = rho_cons(rs, names, m)
                if np.isfinite(a) and np.isfinite(b):
                    d[m].append(b - a)
        except (np.linalg.LinAlgError, ValueError):
            continue
    _set_idx(None)
    out = {}
    for m in modes:
        v = np.array(d[m])
        lo, hi = np.percentile(v, [2.5, 97.5])
        out[m] = {"d": round(float(v.mean()), 4),
                  "ci": [round(float(lo), 4), round(float(hi), 4)],
                  "verdict": "채택" if lo > 0 else ("악화" if hi < 0 else "보류"),
                  "reps": len(v)}
    return out


def run_metric() -> dict:
    base_modes = ("eq", "flip", "soft", "clip")
    from .audit import domains as _dom
    b, n = _dom()
    print("판정치 (라벨 0건)")
    for m in base_modes:
        print(f"  {m:<6}{rho_cons(b, n, m):+.4f}")
    r = paired_metric()
    print("\n균등 대비 짝지은 차이")
    for m, v in r.items():
        print(f"  {m:<6}Δ{v['d']:+.4f} [{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}] "
              f"{v['verdict']} ({v['reps']}회)")
    Path("data/state/consensus_metric.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=1))
    return r
