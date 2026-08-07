"""정본 파이프라인 --- 현재 상태를 한 번에 낸다.

노트 33부터 45까지 굴린 끝에 남은 설계는 단순하다. 여러 번 시도했다가 되돌린
것들(고유 축 확대, 이중 배선, 출처 λ, 전역 정렬)은 전부 빠져 있다.

    1. 도메인마다 다섯 축 슬롯에 관측 가능한 물리량을 배선한다. 근거 없는 축은
       0으로 채우지 않고 마스크 0으로 남긴다.
    2. 도메인 안에서 시간 추세를 뺀다. 추세 변수는 라벨이 쌓이는 방식에 맞춘다
       --- 달력 연도(팝업·아이돌·펀딩) 또는 log 경과일(게임·도서·웹툰).
    3. 공유 축과 고유 축을 겹침 유도 λ로 섞어 공분산 주성분 둘을 뽑는다.
    4. 쌍마다 **둘이 함께 관측한 공통 축**의 적재로 프로크루스테스 정렬한다.
    5. 출처에서 능형 회귀를 적합해 대상에 적용한다. 대상 라벨은 쓰지 않는다.

**판정치가 둘이다.** 노트 71까지 정본은 셀 평균 순위 상관이었다(노트 43) ---
"출처 하나로 대상 하나". 그런데 제품이 쓰는 것은 **앙상블**이다 --- 대상마다
들어오는 출처 전부를 순위 평균한 것. 노트 71이 일곱 대상 전부에서 앙상블이
높고 여섯에서 짝지은 구간이 0을 넘는 것을 확인했고, 과거 결정 넷 중 하나가
자를 바꾸자 뒤집혔다. **그래서 앙상블을 앞에 세우고 셀 평균을 함께 낸다.**

유의 개수는 대상 표본 크기에 지배되므로 쓰지 않고, MAE는 예측 눈금에 반응하므로
쓰지 않는다(노트 42). 구간은 연도 층화 짝지은 붓스트랩으로 붙인다(노트 44).

사용:
  python3 -m state.pipeline            상태 보고
  python3 -m state.pipeline --ci 200   구간까지
"""
from __future__ import annotations

import argparse
import json
from itertools import permutations
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .procrustes import COMMON, align_pair, factor_space, lam_by_overlap
from .rank_test import rank_cross, spearman
from .tri_domain import load_all

OUT = Path("data/state/pipeline.json")


def cv_rho(X, y, seed=20260729):
    pr = np.zeros(len(y))
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(X):
        pr[te] = Ridge(alpha=1.0).fit(X[tr], y[tr]).predict(X[te])
    return spearman(pr, y)


def state(base=None, perm=0, names=None):
    if base is None:
        base, names = load_all(with_names=True)
    lam = lam_by_overlap(base, names=names)
    F = {k: factor_space(*v, lam=lam.get(k, 1.0), names=(names or {}).get(k))
         for k, v in base.items()}
    cells = {}
    for s, t in permutations(base, 2):
        r = align_pair(F[s], F[t])
        if r is None:
            continue
        rho = spearman(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[t]["S"]),
                       F[t]["y"])
        c = {"rho": rho, "axes": len(r[1])}
        if perm:
            _, p = rank_cross(r[0], F[s]["y"], F[t]["S"], F[t]["y"], perm=perm)
            c["p"] = p
        cells[f"{s}→{t}"] = c
    # 앙상블 --- 대상마다 들어오는 출처 전부를 순위 평균한다(노트 71).
    ens = {}
    for t in base:
        ps = [np.asarray(v["p"]) for kk, v in _preds(F, base).items()
              if kk.split("→")[1] == t]
        if ps:
            ens[t] = spearman(
                np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1), F[t]["y"])
    return {"F": F, "lam": lam, "cells": cells, "ens": ens,
            "rho": float(np.mean([c["rho"] for c in cells.values()])),
            "rho_ens": float(np.mean(list(ens.values()))) if ens else float("nan"),
            "self": {k: cv_rho(F[k]["S"], F[k]["y"]) for k in F}}


def _preds(F, base):
    """셀별 예측 벡터. state() 가 앙상블을 만들 때 쓴다."""
    out = {}
    for s, t in permutations(base, 2):
        r = align_pair(F[s], F[t])
        if r is None:
            continue
        out[f"{s}→{t}"] = {"p": Ridge(alpha=1.0).fit(r[0], F[s]["y"])
                           .predict(F[t]["S"])}
    return out


def run(ci: int = 0, perm: int = 0) -> dict:
    base, names = load_all(with_names=True)
    st = state(base, perm=perm, names=names)
    F, cells = st["F"], st["cells"]
    n_tot = sum(len(v[2]) for v in base.values())
    print(f"도메인 {len(base)}개 · 레코드 {n_tot}건 · 셀 {len(cells)}개")
    print(f"공통 축: {COMMON}\n")
    print(f"  {'도메인':<7}{'n':>6}{'축':>4}{'자기 ρ':>9}"
          f"{'앙상블':>9}{'대상으로':>10}{'출처로':>9}")
    for k in F:
        tg = [c["rho"] for kk, c in cells.items() if kk.split("→")[1] == k]
        sr = [c["rho"] for kk, c in cells.items() if kk.split("→")[0] == k]
        print(f"  {k:<7}{F[k]['n']:>6}{len(F[k]['axes']):>4}"
              f"{st['self'][k]:>+9.3f}{st['ens'].get(k, float('nan')):>+9.3f}"
              f"{np.mean(tg):>+10.3f}{np.mean(sr):>+9.3f}")

    print(f"\n  앙상블 판정치 ρ = {st['rho_ens']:+.4f}   (셀 평균 {st['rho']:+.4f})")
    a = np.array([[st["self"][k],
                   np.mean([c["rho"] for kk, c in cells.items() if kk.split("→")[1] == k]),
                   np.mean([c["rho"] for kk, c in cells.items() if kk.split("→")[0] == k])]
                  for k in F])
    print(f"  자기 ρ vs 대상 전이  r={np.corrcoef(a[:,0],a[:,1])[0,1]:+.3f}")
    print(f"  자기 ρ vs 출처 전이  r={np.corrcoef(a[:,0],a[:,2])[0,1]:+.3f}")

    if ci:
        # 구간도 **두 자로** 붙인다. 판정치를 바꿨으므로 앙상블 쪽이 정본이다.
        from .audit import rho_ens
        from .rho_ci import mean_rho, resample
        rng = np.random.default_rng(20260729)
        vals, vens = [], []
        for _ in range(ci):
            try:
                rs = resample(base, rng)
                v = mean_rho(rs, names=names)
                e = rho_ens(rs, names)
            except (np.linalg.LinAlgError, ValueError):
                continue
            if np.isfinite(v) and np.isfinite(e):
                vals.append(v)
                vens.append(e)
        for lab, arr, key in (("앙상블", vens, "ci_ens"), ("셀 평균", vals, "ci")):
            lo, hi = np.percentile(arr, [2.5, 97.5])
            print(f"  95% 붓스트랩 구간({lab}) [{lo:+.4f}, {hi:+.4f}]  "
                  f"반폭 {(hi-lo)/2:.4f}  ({len(arr)}회)")
            st[key] = [float(lo), float(hi)]

    print("\n  셀별")
    for k, c in cells.items():
        pp = f"  p={c['p']:.4f}" if "p" in c else ""
        print(f"    {k:<14}ρ={c['rho']:+.3f}  정렬축 {c['axes']}{pp}")

    OUT.write_text(json.dumps(
        {"n_domain": len(base), "n_record": n_tot, "rho": st["rho"],
         "rho_ens": st["rho_ens"], "ens": st["ens"],
         "cells": cells, "self": st["self"], "ci": st.get("ci"),
         "ci_ens": st.get("ci_ens"),
         "n": {k: F[k]["n"] for k in F}}, ensure_ascii=False, indent=1))
    return st


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", type=int, default=0)
    ap.add_argument("--perm", type=int, default=0)
    a = ap.parse_args()
    run(ci=a.ci, perm=a.perm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
