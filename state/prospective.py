"""시간을 가른다 --- 처음으로 미래를 예측한다.

노트 13부터 일흔다섯까지 모든 수치는 **시간을 안 갈랐다**. 붓스트랩이 연도
층화이긴 했지만 그것은 표본 변동을 재는 장치이지 ``과거로 미래를 맞히는가''를
재는 장치가 아니다. 출처 도메인의 2026년 레코드로 학습한 회귀가 2025년 팝업을
맞히는 것이 지금까지의 평가였다.

제품은 그렇게 안 쓰인다. \\textbf{쓰이는 방식은 하나다} --- 지금까지 쌓인
것으로 배워서 \\emph{아직 안 연} 팝업을 맞힌다.

**규약.**

    시점 T 를 정한다
    출처   T 이전에 나온 레코드만 쓴다
    대상   T 이후 레코드로만 평가한다

시점을 달력 연도로 통일한다. 도메인마다 탈추세 변수가 다르므로(달력 연도 또는
log 경과일) `t_raw` 를 연도로 되돌려 자른다.

**공정 비교.** 미래 집합은 작아서 ρ가 흔들린다. 그래서 **같은 미래 집합**에서
두 번 잰다 --- 출처를 자른 것과 안 자른 것. 차이가 ``미래를 못 보는 값''이다.

**남는 가정 하나.** 대상의 인자 공간은 미래 레코드 전체로 만든다. 팝업 축은
기획 단계에서 정해지므로 라벨 누출은 아니지만, 여러 건을 한꺼번에 보는
전도적(transductive) 가정이 남는다. 한 건씩 예측하는 것과는 다르다.

사용: python3 -m state.prospective
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .orient import spaces
from .procrustes import align_pair
from .rank_test import spearman

SEED = 20260729
ASOF = 2026.57          # 2026-07-28 을 연 단위로
OUT = Path("data/state/prospective.json")


def years(F) -> np.ndarray:
    """`t_raw` 를 달력 연도로 되돌린다. 달력 연도 도메인은 그대로 둔다."""
    t = np.asarray(F["t_raw"], float)
    fin = t[np.isfinite(t)]
    if len(fin) and np.nanmax(fin) > 1000:
        return t
    return ASOF - (10.0 ** t) / 365.25


def cut_domain(dom_tuple, keep):
    A, M, y, t = dom_tuple
    return A[keep], M[keep], y[keep], t[keep]


def evaluate(T: float, tgt: str, doms, names, cut_sources: bool):
    """대상의 T 이후 레코드에서 앙상블 ρ. cut_sources 면 출처를 T 이전으로 자른다."""
    use, nm = {}, {}
    for k, v in doms.items():
        if k == tgt:
            use[k], nm[k] = v, names.get(k)
            continue
        if not cut_sources:
            use[k], nm[k] = v, names.get(k)
            continue
        # 출처를 자르려면 먼저 인자 공간을 만들어 연도를 얻어야 한다 ---
        # rows 부분집합이 factor_space 안에서 정해지기 때문이다. 대신 원 배열의
        # 시간 열로 자른다(같은 변환이므로 결과가 같다).
        A, M, y, t = v
        tt = np.asarray(t, float)
        fin = tt[np.isfinite(tt)]
        yr = tt if (len(fin) and np.nanmax(fin) > 1000) else ASOF - (10.0 ** tt) / 365.25
        keep = np.isfinite(yr) & (yr < T)
        if keep.sum() < 40:
            continue
        use[k], nm[k] = cut_domain(v, keep), names.get(k)
    if len(use) < 3:
        return None
    F = spaces(use, nm)
    yr_t = years(F[tgt])
    fut = np.where(np.isfinite(yr_t) & (yr_t >= T))[0]
    if len(fut) < 15:
        return None
    ps = []
    for s in use:
        if s == tgt:
            continue
        r = align_pair(F[s], F[tgt])
        if r is None:
            continue
        ps.append(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[tgt]["S"]))
    if not ps:
        return None
    e = np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1)
    return e[fut], F[tgt]["y"][fut], len(use) - 1


def run(cuts=(2024.0, 2025.0, 2026.0), B: int = 400, write: bool = True) -> dict:
    doms, names = domains()
    rng = np.random.default_rng(SEED)
    out = {}
    for T in cuts:
        row = {}
        for tgt in doms:
            a = evaluate(T, tgt, doms, names, cut_sources=False)
            b = evaluate(T, tgt, doms, names, cut_sources=True)
            if a is None or b is None:
                continue
            ea, ya, _ = a
            eb, yb, ns = b
            if len(ea) != len(eb):
                continue
            ra, rb = spearman(ea, ya), spearman(eb, yb)
            d = []
            n = len(ya)
            for _ in range(B):
                ix = rng.choice(n, size=n, replace=True)
                x, z = spearman(ea[ix], ya[ix]), spearman(eb[ix], yb[ix])
                if np.isfinite(x) and np.isfinite(z):
                    d.append([z, z - x])
            v = np.array(d)
            lo, hi = np.percentile(v, [2.5, 97.5], axis=0)
            row[tgt] = {"n_future": int(n), "n_src": int(ns),
                        "all": round(float(ra), 4), "past": round(float(rb), 4),
                        "ci_past": [round(float(lo[0]), 4), round(float(hi[0]), 4)],
                        "d": round(float(v[:, 1].mean()), 4),
                        "ci_d": [round(float(lo[1]), 4), round(float(hi[1]), 4)]}
        out[str(T)] = row
        print(f"\n=== 시점 {T:.0f} ===")
        print(f"{'대상':<7}{'미래 n':>7}{'출처':>5}{'전부':>9}{'과거만':>9}"
              f"   과거만 95% 구간        차이")
        for k, v in row.items():
            print(f"{k:<7}{v['n_future']:>7}{v['n_src']:>5}{v['all']:>+9.4f}"
                  f"{v['past']:>+9.4f}   [{v['ci_past'][0]:+.4f}, {v['ci_past'][1]:+.4f}]"
                  f"   {v['d']:+.4f} [{v['ci_d'][0]:+.4f}, {v['ci_d'][1]:+.4f}]")
        if row:
            print(f"  평균  전부 {np.mean([v['all'] for v in row.values()]):+.4f}   "
                  f"과거만 {np.mean([v['past'] for v in row.values()]):+.4f}")
    if write:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return out


if __name__ == "__main__":
    run()
