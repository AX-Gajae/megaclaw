"""두 규약을 나란히 낸다 --- 엄격과 배포(노트 112).

노트 106--111에서 네 노트에 걸쳐 같은 혼동이 났다. 시간 분할의 팝업 수치가
음수라 ``팝업이 안 따라온다''고 적었는데, 노트 111이 그 손해의 91%가 **방향표를
다시 정하는 것**에서 온다는 것을 보였다.

두 규약은 다른 질문에 답한다.

    엄격   방향도 $T$ 이전으로 다시 정한다. 못 정하면 그 축을 끈다.
           묻는 것 --- ``그때 이 설계를 내릴 수 있었나''
    배포   방향표를 고정하고 출처만 자른다.
           묻는 것 --- ``지금 이 설계로 미래를 맞히나''

앞으로 둘을 늘 같이 낸다. 하나만 보면 노트 106--110의 혼동이 되풀이된다.

사용: python3 -m state.twoproto
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .procrustes import COMMON, factor_space, lam_by_overlap, procrustes
from .rank_test import spearman
from .tri_domain import ALL5

ASOF = 2026.57
OUT = Path("data/state/twoproto.json")
IX = {a: i for i, a in enumerate(ALL5)}
NEW = ["entry_friction", "media_push"]     # 노트 108이 정렬에 넣은 둘
MIN_CAL = 25                               # 방향을 정하는 데 필요한 건수


def years(t):
    t = np.asarray(t, float)
    fin = t[np.isfinite(t)]
    return t if (len(fin) and np.nanmax(fin) > 1000) else ASOF - (10.0 ** t) / 365.25


def _align(Fs, Ft, cm):
    sh = [a for a in cm if a in Fs["axes"] and a in Ft["axes"]]
    if len(sh) < 2:
        return None
    ke = min(Fs["V"].shape[1], Ft["V"].shape[1], len(sh))
    Ls = Fs["V"][[Fs["axes"].index(a) for a in sh], :ke]
    Lt = Ft["V"][[Ft["axes"].index(a) for a in sh], :ke]
    return Fs["S"][:, :ke] @ procrustes(Ls, Lt), Ft["S"][:, :ke]


def _ens(doms, nm, cm, tgt):
    lam = lam_by_overlap(doms, names=nm, common=cm)
    F = {x: factor_space(*v, lam=lam.get(x, 1.0), names=nm.get(x), common=cm)
         for x, v in doms.items()}
    ps = []
    for s in doms:
        if s == tgt:
            continue
        r = _align(F[s], F[tgt], cm)
        if r is None:
            continue
        ps.append(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(r[1]))
    if not ps:
        return None
    return float(spearman(np.column_stack(
        [rankdata(p) / len(p) for p in ps]).mean(1), F[tgt]["y"]))


def _restrict(doms, YR, T, strict):
    """엄격이면 방향을 T 이전으로 다시 정한다. 못 정하면 그 축을 끈다."""
    if not strict:
        return dict(doms)
    o = {}
    for d, (A, M, y, t) in doms.items():
        A, M = A.copy(), M.copy()
        for ax in NEW:
            if M[:, IX[ax]].mean() < 0.5:
                continue
            pre = np.isfinite(YR[d]) & (YR[d] < T) & (M[:, IX[ax]] > 0)
            if pre.sum() < MIN_CAL:
                M[:, IX[ax]] = 0.0
                continue
            if spearman(A[pre, IX[ax]], y[pre]) < 0:
                A[:, IX[ax]] = 1.0 - A[:, IX[ax]]
        o[d] = (A, M, y, t)
    return o


def evaluate(T, doms, names, YR, cm, strict):
    use0 = _restrict(doms, YR, T, strict)
    src = {}
    for d, (A, M, y, t) in use0.items():
        keep = np.isfinite(YR[d]) & (YR[d] < T)
        if keep.sum() >= 40:
            src[d] = (A[keep], M[keep], y[keep], t[keep])
    out = {}
    for tg, (A, M, y, t) in use0.items():
        post = np.isfinite(YR[tg]) & (YR[tg] >= T)
        if post.sum() < 25:
            continue
        use = dict(src)
        use[tg] = (A[post], M[post], y[post], t[post])
        v = _ens(use, names, cm, tg)
        if v is not None:
            out[tg] = v
    return out


def run(times=(2023, 2024, 2025, 2026)) -> dict:
    base, names = domains()
    YR = {d: years(base[d][3]) for d in base}
    OLD = [a for a in COMMON if a not in NEW]
    print(f"공통 축 {COMMON}")
    print(f"견줄 것: 옛 공통 {OLD}\n")
    print(f"{'T':>6}{'대상':>5}{'옛 공통':>10}{'엄격':>10}{'배포':>10}"
          f"{'팝업 엄격':>11}{'팝업 배포':>11}")
    rows = {}
    for T in times:
        a = evaluate(T, base, names, YR, OLD, False)
        s = evaluate(T, base, names, YR, COMMON, True)
        d = evaluate(T, base, names, YR, COMMON, False)
        common = sorted(set(a) & set(s) & set(d))
        if len(common) < 4:
            continue
        va = float(np.mean([a[k] for k in common]))
        vs = float(np.mean([s[k] for k in common]))
        vd = float(np.mean([d[k] for k in common]))
        ps = s.get("팝업", float("nan")) - a.get("팝업", float("nan"))
        pd = d.get("팝업", float("nan")) - a.get("팝업", float("nan"))
        rows[T] = {"n": len(common), "old": va, "strict": vs, "deploy": vd,
                   "pop_strict": float(ps), "pop_deploy": float(pd)}
        print(f"{T:>6}{len(common):>5}{va:>+10.4f}{vs:>+10.4f}{vd:>+10.4f}"
              f"{ps:>+11.4f}{pd:>+11.4f}", flush=True)
    if rows:
        ds = np.mean([rows[T]["strict"] - rows[T]["old"] for T in rows])
        dd = np.mean([rows[T]["deploy"] - rows[T]["old"] for T in rows])
        pps = np.nanmean([rows[T]["pop_strict"] for T in rows])
        ppd = np.nanmean([rows[T]["pop_deploy"] for T in rows])
        print(f"\n  판정치  엄격 {ds:+.4f}   배포 {dd:+.4f}")
        print(f"  팝업    엄격 {pps:+.4f}   배포 {ppd:+.4f}")
        print("\n  엄격 --- 그때 이 설계를 내릴 수 있었나")
        print("  배포 --- 지금 이 설계로 미래를 맞히나")
        OUT.write_text(json.dumps(
            {"rows": {str(k): v for k, v in rows.items()},
             "mean": {"strict": float(ds), "deploy": float(dd),
                      "pop_strict": float(pps), "pop_deploy": float(ppd)}},
            ensure_ascii=False, indent=1))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--times", type=str, default="2023,2024,2025,2026")
    a = ap.parse_args()
    run(tuple(int(x) for x in a.times.split(",")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
