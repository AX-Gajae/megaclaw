"""후보를 한꺼번에 판정한다 --- 나침반 대신 전수 검정(노트 116).

노트 115가 축 선별 기준을 세 번째로 죽였다(라벨 상관 · 잔차 · 관계 일치도).
결론은 하나였다 --- **나침반을 찾는 대신 검정을 싸게 만든다.**

느렸던 이유는 계산이 아니라 **낭비**였다.

    후보마다 따로 돌렸다        복원추출을 후보 수만큼 되풀이한다
    반복마다 축을 다시 만들었다   후보 열은 자료가 안 바뀌면 그대로다
    설정마다 전부 다시 지었다    안 건드린 도메인의 인자 공간은 같다

셋을 고친다. **복원추출 한 번에 모든 후보를 함께 잰다** --- 같은 반복에서
바탕과 후보 스무 개를 다 재므로 후보끼리도 짝지어진다.

사용: python3 -m state.sweep --seeds 4 --reps 100
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import _IDX, _resample, _set_idx, domains
from .procrustes import COMMON, factor_space, lam_by_overlap, procrustes
from .rank_test import spearman
from .tri_domain import ALL5

OUT = Path("data/state/sweep.json")
SEEDS = (20260729, 19770101, 20250315, 20260101)


def _align(Fs, Ft, cm):
    sh = [a for a in cm if a in Fs["axes"] and a in Ft["axes"]]
    if len(sh) < 2:
        return None
    ke = min(Fs["V"].shape[1], Ft["V"].shape[1], len(sh))
    Ls = Fs["V"][[Fs["axes"].index(a) for a in sh], :ke]
    Lt = Ft["V"][[Ft["axes"].index(a) for a in sh], :ke]
    return Fs["S"][:, :ke] @ procrustes(Ls, Lt), Ft["S"][:, :ke]


def metric(F, cm, key=None):
    rs = {}
    for t in F:
        ps = []
        for s in F:
            if s == t:
                continue
            r = _align(F[s], F[t], cm)
            if r is None:
                continue
            ps.append(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(r[1]))
        if ps:
            rs[t] = float(spearman(np.column_stack(
                [rankdata(p) / len(p) for p in ps]).mean(1), F[t]["y"]))
    if key:
        return rs.get(key, float("nan"))
    return float(np.mean(list(rs.values()))) if rs else float("nan")


def spaces(doms, nm, cm, only=None, cache=None):
    """only 가 있으면 그 도메인만 새로 짓고 나머지는 cache 를 쓴다."""
    lam = lam_by_overlap(doms, names=nm, common=cm)
    out = dict(cache) if cache else {}
    for x, v in doms.items():
        if cache is not None and only is not None and x not in only:
            continue
        out[x] = factor_space(*v, lam=lam.get(x, 1.0), names=nm.get(x),
                              common=cm)
    return out


def add_axis(doms, nm, col, tag):
    """col: {도메인: (값, 표시자)}. 자료는 미리 만들어 둔다."""
    o, n2 = dict(doms), dict(nm)
    touched = []
    for d, c in col.items():
        if d not in o or c is None:
            continue
        v, mk = c
        idx = _IDX.get(d)
        if idx is not None:
            v, mk = v[idx], mk[idx]
        A, M, y, t = o[d]
        if len(v) != len(y):
            continue
        cols, cn = [v], [tag]
        if mk.mean() < 0.98:
            cols.append(mk)
            cn.append(tag + "_obs")
        o[d] = (np.column_stack([A] + cols),
                np.column_stack([M] + [np.ones(len(y))] * len(cols)), y, t)
        n2[d] = list(n2.get(d) or ALL5) + cn
        touched.append(d)
    return o, n2, touched


LEAK = 0.70   # 라벨과 이만큼 붙으면 누수로 본다(노트 117)


def leak_check(cands, base, thr=LEAK):
    """후보가 그 도메인의 라벨을 다시 재고 있지 않은가(노트 117).

    노트 117에서 걸렸다 --- AniList favourites 가 판정치를 +0.0384 올리고
    씨앗 넷을 다 통과했는데, 만화 · 세계애니의 라벨이 같은 플랫폼의
    popularity(상관 +1.000)이고 favourites 가 그것과 +0.855 였다. **같은
    플랫폼의 같은 사용자가 매긴 두 번째 계수**였다.

    노트 116이 ``재지 말고 걸어 봐라''로 지침을 뒤집었으므로, 그 지침에는
    이 검사가 필수 짝이다."""
    from .rank_test import spearman
    out = {}
    for c, col in cands.items():
        worst, where = 0.0, None
        for d, v in col.items():
            if d not in base or v is None:
                continue
            vv, mk = v
            y = base[d][2]
            if len(vv) != len(y):
                continue
            m = mk > 0
            if m.sum() < 30:
                continue
            r = abs(spearman(vv[m], y[m]))
            if r > worst:
                worst, where = r, d
        out[c] = {"max_abs_r": float(worst), "where": where,
                  "leak": bool(worst >= thr)}
    return out


def sweep(cands, seeds=SEEDS, reps=100, key=None, verbose=True):
    """cands: {이름: {도메인: (값, 표시자)}}. 모든 후보를 같은 반복에서 잰다."""
    base, names = domains()
    from .candidates import LABEL_PLATFORM
    lk = leak_check(cands, base)
    for c in lk:
        if c in LABEL_PLATFORM:
            lk[c]["leak"] = True
            lk[c]["why"] = "라벨을 만든 계수기에서 나온 축"
    bad = [c for c in lk if lk[c]["leak"]]
    if bad and verbose:
        for c in bad:
            why = lk[c].get("why", f"라벨 상관 {lk[c]['max_abs_r']:.3f} "
                             f"({lk[c]['where']})")
            print(f"  [누수] {c}  {why} --- 판정에서 뺀다", flush=True)
    cands = {c: v for c, v in cands.items() if not lk[c]["leak"]}
    t0 = time.time()
    _set_idx(None)
    F0 = spaces(base, names, COMMON)
    b0 = metric(F0, COMMON, key)
    point = {}
    for c, col in cands.items():
        d2, n2, tc = add_axis(base, names, col, c)
        point[c] = metric(spaces(d2, n2, COMMON), COMMON, key) - b0
    diffs = {c: [] for c in cands}
    for sd in seeds:
        rng = np.random.default_rng(sd)
        for _ in range(reps):
            rs, ix = _resample(base, rng)
            _set_idx(ix)
            try:
                Fb = spaces(rs, names, COMMON)
                a = metric(Fb, COMMON, key)
                if not np.isfinite(a):
                    continue
                for c, col in cands.items():
                    d2, n2, tc = add_axis(rs, names, col, c)
                    F = spaces(d2, n2, COMMON, only=set(tc), cache=Fb)
                    v = metric(F, COMMON, key)
                    if np.isfinite(v):
                        diffs[c].append((sd, v - a))
            except (np.linalg.LinAlgError, ValueError, KeyError):
                continue
    _set_idx(None)
    out = {}
    for c in cands:
        per = {}
        for sd in seeds:
            v = np.array([d for s, d in diffs[c] if s == sd])
            if len(v) < 10:
                continue
            lo, hi = np.percentile(v, [2.5, 97.5])
            per[sd] = {"ci": [float(lo), float(hi)], "n": len(v),
                       "v": "채택" if lo > 0 else ("악화" if hi < 0 else "보류")}
        out[c] = {"diff": float(point[c]), "seeds": per,
                  "ok": sum(1 for s in per if per[s]["v"] == "채택"),
                  "bad": sum(1 for s in per if per[s]["v"] == "악화")}
    el = time.time() - t0
    if verbose:
        print(f"바탕 {b0:+.4f}   후보 {len(cands)}개 · 씨앗 {len(seeds)} · "
              f"반복 {reps}   {el:.0f}초  (후보당 {el/max(len(cands),1):.1f}초)")
    return {"base": float(b0), "res": out, "sec": float(el), "leak": lk}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--reps", type=int, default=100)
    a = ap.parse_args()
    from .candidates import build
    r = sweep(build(), seeds=SEEDS[:a.seeds], reps=a.reps)
    print(f"\n{'후보':<14}{'Δ':>10}{'채택':>6}{'악화':>6}  구간(첫 씨앗)")
    for c, v in sorted(r["res"].items(), key=lambda x: -x[1]["diff"]):
        s0 = list(v["seeds"].values())
        ci = (f"[{s0[0]['ci'][0]:+.4f}, {s0[0]['ci'][1]:+.4f}]" if s0 else "-")
        print(f"{c:<14}{v['diff']:>+10.4f}{v['ok']:>6}{v['bad']:>6}  {ci}")
    OUT.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
