"""여섯 출처를 합친다 --- 셀 평균에서 앙상블로.

노트 33부터 일흔까지 판정치는 줄곧 **셀별 전이의 평균**이었다. 그것은 ``출처
하나로 대상 하나를 얼마나 맞히나''의 평균이고, 일반성의 척도로는 맞다. 그런데
제품이 쓰는 것은 그게 아니다.

    연구 질문   게임으로 팝업을 맞히면 얼마나 맞나
    제품 질문   **가진 것 전부로** 팝업을 맞히면 얼마나 맞나

지금까지 둘째를 한 번도 안 쟀다. 여섯 출처의 예측이 각각 +0.3쯤이면 합친 것은
그보다 나아야 한다 --- 오차가 완전히 같은 방향이 아니라면.

**순위 평균으로 합친다.** 출처마다 예측의 눈금이 다르므로(노트 59가 눈금 보정을
따로 다룬 이유다) 값이 아니라 **순위**를 평균한다. 가중치는 안 준다 --- 출처의
자기 상관으로 가중하면 노트 38 · 40의 상충 법칙 때문에 오히려 나쁜 출처에
힘이 실린다.

**방향 결정은 오히려 비싸진다.** 처음에는 반대로 예상했다 --- 앙상블은 대상마다
부호를 하나만 정하면 되니 같은 라벨로 여섯 배의 증거를 쓴다고 봤다. 틀렸다.
결정이 여섯에서 하나로 줄면 **오판의 헤지도 함께 사라진다.** 셀별로 여섯 번
정하면 넷만 맞아도 평균이 살아남는데, 한 번 정하면 틀릴 때 대상 전체가 뒤집힌다.
노트 71에서 $k{=}32$에도 구간이 0을 포함했다. `sign_modes()`가 그래서 셋을
비교한다 --- 합친 뒤 부호 · 다수결 부호 · **부호 뒤 합치기**.

사용: python3 -m state.ensemble
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .orient import _sign, cal_label, spaces
from .procrustes import align_pair
from .rank_test import spearman

SEED = 20260729
OUT = Path("data/state/ensemble.json")


def cells(doms, names):
    """대상별로 들어오는 출처 예측 전부. 대상 라벨은 안 쓴다."""
    F = spaces(doms, names)
    out = {}
    for t in doms:
        rows = []
        for s in doms:
            if s == t:
                continue
            r = align_pair(F[s], F[t])
            if r is None:
                continue
            rows.append((s, Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[t]["S"])))
        out[t] = (rows, F[t])
    return out


def blend(preds, idx=None):
    """순위 평균. 값이 아니라 순위를 평균하므로 눈금 차이에 안 흔들린다."""
    ix = slice(None) if idx is None else idx
    R = np.column_stack([rankdata(p[ix]) / len(p[ix]) for p in preds])
    return R.mean(1)


def table(seed: int = SEED, B: int = 400) -> dict:
    doms, names = domains()
    C = cells(doms, names)
    rng = np.random.default_rng(seed)
    out = {}
    for t, (rows, F) in C.items():
        y = F["y"]
        singles = {s: spearman(p, y) for s, p in rows}
        ens = spearman(blend([p for _, p in rows]), y)
        # 짝지은 붓스트랩 --- 같은 행을 뽑아 앙상블과 셀 평균을 함께 잰다.
        d = []
        n = len(y)
        for _ in range(B):
            ix = rng.choice(n, size=n, replace=True)
            m = float(np.mean([spearman(p[ix], y[ix]) for _, p in rows]))
            e = spearman(blend([p for _, p in rows], ix), y[ix])
            if np.isfinite(m) and np.isfinite(e):
                d.append(e - m)
        v = np.array(d)
        lo, hi = np.percentile(v, [2.5, 97.5])
        out[t] = {"n": int(n),
                  "mean": round(float(np.mean(list(singles.values()))), 4),
                  "best": round(float(max(singles.values())), 4),
                  "best_src": max(singles, key=singles.get),
                  "worst": round(float(min(singles.values())), 4),
                  "ens": round(float(ens), 4),
                  "gain": round(float(np.mean(v)), 4),
                  "ci": [round(float(lo), 4), round(float(hi), 4)],
                  "singles": {s: round(float(r), 4) for s, r in singles.items()}}
    return out


def sign_curve(ks=(0, 2, 4, 8, 16, 24, 32), reps: int = 150, seed: int = SEED) -> dict:
    """앙상블의 방향을 k건으로 정한다. 노트 70과 같은 유보 규약."""
    doms, names = domains()
    C = cells(doms, names)
    kmax = max(ks)
    rng = np.random.default_rng(seed)
    acc = {k: [] for k in ks}
    for _ in range(reps):
        per = {k: [] for k in ks}
        for t, (rows, F) in C.items():
            y, n = F["y"], len(F["y"])
            if n <= kmax + 20:
                continue
            perm = rng.permutation(n)
            ev, pool = perm[kmax:], perm[:kmax]
            e_ev = blend([p for _, p in rows], ev)
            for k in ks:
                cal = pool[:k]
                if k == 0:
                    per[k].append(spearman(e_ev, y[ev]))
                    continue
                yc = cal_label(F, cal)
                s = _sign(spearman(blend([p for _, p in rows], cal), yc))
                per[k].append(spearman(s * e_ev, y[ev]))
        for k in ks:
            if per[k]:
                acc[k].append(float(np.mean(per[k])))
    z0 = np.array(acc[0])
    out = {}
    for k in ks:
        v = np.array(acc[k])
        d = v - z0
        lo, hi = np.percentile(d, [2.5, 97.5])
        out[k] = {"rho": round(float(v.mean()), 4),
                  "d": round(float(d.mean()), 4),
                  "ci": [round(float(lo), 4), round(float(hi), 4)]}
    return out


def run(write: bool = True) -> dict:
    t = table()
    print("대상별 --- 출처 여섯을 합치면\n")
    print(f"{'대상':<7}{'n':>6}{'셀 평균':>9}{'최선 출처':>10}{'앙상블':>9}"
          f"{'차이':>9}   95% 구간")
    for k, v in t.items():
        print(f"{k:<7}{v['n']:>6}{v['mean']:>+9.4f}{v['best']:>+10.4f}"
              f"{v['ens']:>+9.4f}{v['gain']:>+9.4f}   "
              f"[{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}]"
              f"{'  채택' if v['ci'][0] > 0 else ''}")
    print(f"\n전체 셀 평균 {np.mean([v['mean'] for v in t.values()]):+.4f}  "
          f"앙상블 평균 {np.mean([v['ens'] for v in t.values()]):+.4f}")
    s = sign_curve()
    print("\n앙상블의 방향을 k건으로 정한다 (노트 70과 같은 유보 규약)")
    for k, v in s.items():
        print(f"  k={k:<3} ρ={v['rho']:+.4f}  Δ{v['d']:+.4f} "
              f"[{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}]"
              f"{'  채택' if v['ci'][0] > 0 else ''}")
    if write:
        OUT.write_text(json.dumps({"table": t, "sign": {str(k): v for k, v in s.items()}},
                                  ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return {"table": t, "sign": s}


def sign_modes(ks=(0, 4, 8, 16, 24, 32), reps: int = 150, seed: int = SEED) -> dict:
    """방향 결정과 합치기를 어떤 순서로 붙일까 --- 세 가지.

        합친 뒤 부호   여섯을 순위 평균한 뒤 부호 하나를 정한다(노트 71)
        다수결 부호    셀마다 부호를 정하고 **다수결**로 앙상블 부호를 정한다
        부호 뒤 합치기 셀마다 부호를 고쳐 **고친 것들을 합친다**

    셋째가 헤지와 합치기 이득을 둘 다 가질 후보다 --- 결정은 여섯 번 하고
    예측은 합친다."""
    doms, names = domains()
    C = cells(doms, names)
    kmax = max(ks)
    rng = np.random.default_rng(seed)
    MODES = ("blend_then", "vote", "then_blend")
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
            e_ev = blend(ps, ev)
            for k in ks:
                cal = pool[:k]
                if k == 0:
                    for m in MODES:
                        per[k][m].append(spearman(e_ev, y[ev]))
                    continue
                yc = cal_label(F, cal)
                sc = [_sign(spearman(p[cal], yc)) for p in ps]
                per[k]["blend_then"].append(
                    spearman(_sign(spearman(blend(ps, cal), yc)) * e_ev, y[ev]))
                per[k]["vote"].append(
                    spearman(_sign(sum(sc)) * e_ev, y[ev]))
                per[k]["then_blend"].append(
                    spearman(blend([s * p for s, p in zip(sc, ps)], ev), y[ev]))
        for k in ks:
            for m in MODES:
                if per[k][m]:
                    acc[k][m].append(float(np.mean(per[k][m])))
    z0 = {m: np.array(acc[0][m]) for m in MODES}
    out = {}
    for k in ks:
        row = {}
        for m in MODES:
            v = np.array(acc[k][m])
            d = v - z0[m]
            lo, hi = np.percentile(d, [2.5, 97.5])
            row[m] = {"rho": round(float(v.mean()), 4), "d": round(float(d.mean()), 4),
                      "ci": [round(float(lo), 4), round(float(hi), 4)]}
        out[k] = row
    return out


def run_modes(write: bool = True) -> dict:
    r = sign_modes()
    print("방향 결정과 합치기의 순서 (유보 평가, 복제 150회)\n")
    print(f"{'k':>4}  {'합친 뒤 부호':>12}  {'다수결 부호':>12}  {'부호 뒤 합치기':>14}")
    for k, v in r.items():
        print(f"{k:>4}  {v['blend_then']['rho']:+.4f}       {v['vote']['rho']:+.4f}"
              f"        {v['then_blend']['rho']:+.4f}")
    print("\n보정 없음 대비 짝지은 차이")
    for k, v in r.items():
        if not k:
            continue
        for m, lab in (("blend_then", "합친 뒤"), ("vote", "다수결"),
                       ("then_blend", "부호 뒤")):
            c = v[m]
            print(f"  k={k:<3} {lab:<6} Δ{c['d']:+.4f} [{c['ci'][0]:+.4f}, "
                  f"{c['ci'][1]:+.4f}]{'  채택' if c['ci'][0] > 0 else ''}")
    if write:
        p = Path("data/state/sign_modes.json")
        p.write_text(json.dumps({str(k): v for k, v in r.items()},
                                ensure_ascii=False, indent=1))
        print(f"\n저장: {p}")
    return r


if __name__ == "__main__":
    run()
