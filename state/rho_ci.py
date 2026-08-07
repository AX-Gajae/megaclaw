"""평균 순위 상관에 신뢰구간을 붙인다 --- 재감사의 근거를 세운다.

노트 43은 채택 판정을 유의 개수에서 평균 $\\rho$로 옮기고 결정 넷을 재감사했다.
그런데 근거로 쓴 차이가 0.3438 대 0.3516처럼 작다. **신뢰구간을 붙이지 않으면
그 재감사 자체가 노트 42가 지적한 것과 같은 실수다** --- 자를 바꿨을 뿐 눈금을
읽지 않은 것이다.

**짝지은 붓스트랩**을 쓴다. 복제마다 도메인별 레코드를 복원추출한 뒤 두 설정을
\\emph{같은 복제 위에서} 계산해 차이를 기록한다. 축 유도와 인자 공간 추정이
복제마다 다시 일어나므로 배선 불확실성까지 들어간다.

짝을 짓는 이유는 노트 6에서 확립한 그대로다 --- 설정 간 차이가 표본 요동보다
훨씬 작을 때, 독립 붓스트랩은 두 개의 큰 분산을 빼서 차이를 못 본다.

**층화한다.** 복원추출을 도메인 안에서 하고, 시간 추세를 빼는 단계가 있으므로
연도 분포가 무너지지 않도록 연도별로 뽑는다.

사용: python3 -m state.rho_ci
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .procrustes import align_pair, factor_space, lam_by_overlap
from .rank_test import spearman
from .tri_domain import ALL5, load_all

OUT = Path("data/state/rho_ci.json")
SEED = 20260729
IX = {a: i for i, a in enumerate(ALL5)}


def resample(base, rng):
    """도메인 안에서 연도 층화 복원추출."""
    out = {}
    for k, (A, M, y, t) in base.items():
        idx = np.arange(len(y))
        pick = []
        for v in np.unique(t[np.isfinite(t)]):
            g = idx[t == v]
            pick += list(rng.choice(g, size=len(g), replace=True))
        nan = idx[~np.isfinite(t)]
        if len(nan):
            pick += list(rng.choice(nan, size=len(nan), replace=True))
        p = np.array(sorted(pick))
        out[k] = (A[p], M[p], y[p], t[p])
    return out


def mean_rho(doms, mask_off=None, mask_on=None, wiring=None, common=None,
             names=None):
    """스무 셀 평균 순위 상관.

    mask_off / mask_on 은 (도메인, 축) 목록이다. **켜는 쪽도 필요하다** ---
    게임 매장 노출도는 노트 43에서 이미 꺼서 ingest 에 반영했으므로, 그 결정을
    검정하려면 다시 켜 봐야 한다. 값은 축 JSON에 그대로 남아 있다."""
    d = dict(doms)
    for dom, ax in (mask_off or []):
        if dom not in d:
            continue
        A, M, y, t = d[dom]
        M = M.copy()
        M[:, IX[ax]] = 0.0
        d[dom] = (A, M, y, t)
    for dom, ax in (mask_on or []):
        if dom not in d:
            continue
        A, M, y, t = d[dom]
        M = M.copy()
        M[:, IX[ax]] = np.where(A[:, IX[ax]] != 0, 1.0, M[:, IX[ax]])
        d[dom] = (A, M, y, t)
    if wiring:
        d.update(wiring(d))
    lam = lam_by_overlap(d, common=common, names=names)
    F = {k: factor_space(*v, lam=lam.get(k, 1.0), common=common,
                         names=(names or {}).get(k)) for k, v in d.items()}
    rs = []
    for s, t in permutations(d, 2):
        r = align_pair(F[s], F[t], common=common)
        if r is None:
            continue
        m = Ridge(alpha=1.0).fit(r[0], F[s]["y"])
        rs.append(spearman(m.predict(F[t]["S"]), F[t]["y"]))
    return float(np.mean(rs)) if rs else float("nan")


def paired(base, cfgA, cfgB, B=300, seed=SEED):
    """두 설정의 평균 ρ 차이에 대한 짝지은 붓스트랩 분포."""
    rng = np.random.default_rng(seed)
    a0, b0 = mean_rho(base, **cfgA), mean_rho(base, **cfgB)
    diffs, aa, bb = [], [], []
    for _ in range(B):
        d = resample(base, rng)
        try:
            x, y = mean_rho(d, **cfgA), mean_rho(d, **cfgB)
        except (np.linalg.LinAlgError, ValueError):
            continue
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        aa.append(x); bb.append(y); diffs.append(y - x)
    v = np.array(diffs)
    return {"A": a0, "B": b0, "obs_diff": b0 - a0,
            "ci": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
            "p_gt0": float((v > 0).mean()), "sd": float(v.std()), "reps": len(v),
            "ci_A": [float(np.percentile(aa, 2.5)), float(np.percentile(aa, 97.5))],
            "ci_B": [float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))]}


def _book_pool():
    """노트 34가 바꾸기 전의 도서 타깃 폭(장르 수)을 후보로 만든다."""
    import json as _j
    rec = _j.loads(Path("data/state/book_records.json").read_text())
    ax = _j.loads(Path("data/state/book_axes.json").read_text())
    ids = list(ax.keys())
    v = np.array([min(1.0, np.log2(((rec.get(k) or {}).get("n_genre") or 0) + 1) / 3.5)
                  for k in ids])
    return {"장르 수": (v, np.ones(len(v)))}


def run(B: int = 300) -> dict:
    base = load_all()
    from .dual import SRC_WIRING, wire
    C2 = ["target_breadth", "goods_scale"]
    C3 = C2 + ["venue_prominence"]
    from .factor_search import COLS, build
    tests = {
        "게임 매장축 켜기 (노트37→43)":
            ({"mask_on": [("게임", "venue_prominence")]}, {}),
        "이중 배선 (노트39, 철회)":
            ({}, {"wiring": lambda d: wire(d, SRC_WIRING)}),
        "공통 축 2→3 (노트37 채택)":
            ({"common": C2}, {"common": C3}),
        "도서 타깃폭 장르→판형 (노트34)":
            ({"wiring": lambda d: {"도서": build("도서", d,
                {"target_breadth": "장르 수"}, _book_pool())}}, {}),
    }
    out = {}
    print(f"짝지은 붓스트랩 {B}회 · 연도 층화 복원추출\n")
    print(f"  {'비교':<28}{'A':>8}{'B':>8}{'차이':>9}{'95% CI':>20}{'P(>0)':>8}")
    for lab, (ca, cb) in tests.items():
        r = paired(base, ca, cb, B=B)
        out[lab] = r
        ci = f"[{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]"
        print(f"  {lab:<28}{r['A']:>+8.4f}{r['B']:>+8.4f}{r['obs_diff']:>+9.4f}"
              f"{ci:>20}{r['p_gt0']:>8.3f}")

    print("\n=== 현재 설정의 평균 ρ 자체에 대한 구간 ===")
    r = out["게임 매장축 켜기 (노트37→43)"]
    print(f"  현행(게임 매장축 끔)  ρ={r['B']:+.4f}   95% CI "
          f"[{r['ci_B'][0]:+.4f}, {r['ci_B'][1]:+.4f}]")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
