# -*- coding: utf-8 -*-
"""997 팔 ㉠ — 🔴 **「지금까지 써 온 자」(라벨 선형 프로브)의 `MDE` 를 «처음» 잰다.**

사전등록 `docs/prereg_997_unsupervised_mde.md` §3·§4.

🔴 **왜.** 915 가 `k=16` 에서 최고 SSL `0.1719` 를 라벨 순열 바닥 `0.1708` «옆»에서
얻고 멈췄고 **83 사이클 동안 아무도 그 자의 `MDE` 를 안 쟀다**. 그 차 `0.0011` 이
「졌다」인지 「못 쟀다」인지는 `MDE` 를 알아야 갈린다.

두 표본 갈래를 «둘 다» 낸다:
  · **전량 라벨** --- 학습 라벨 전부로 프로브를 적합(판이 실제로 쓰는 꼴)
  · **소수 라벨** --- `k = 8·16·32·64·128`(998 이 갈 곳 · 915 의 갈래)

바닥 둘을 **반드시 같이**: ④ **난수 표현** · ⑤ **라벨 순열**.

산출: `runners/out997_probe.json`
사용: `M997_THREADS=5 python3 runners/mde997_probe.py`
"""
import collections
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, os.environ.get("M997_THREADS", "5"))

import delta996_common as C                       # noqa: E402  🔴 등록된 자
import mde997_common as K                         # noqa: E402

OUT = Path(os.environ.get("M997_OUT", "")) if os.environ.get("M997_OUT") \
    else ROOT / ("runners/out997_probe%s.json" % os.environ.get("M997_TAG", ""))

KS = (8, 16, 32, 64, 128)
#: 🔴 915 가 실제로 낸 두 수 --- **「이 자로 그 차를 잴 수 있었나」가 이 러너의 물음이다**
G915_K16_SSL = 0.1719
G915_K16_PERM = 0.1708
SHAM_PAIRS_KSHOT = 10             #: k 갈래에서 씨앗마다 뽑는 위약 짝 수
RIDGE_ALPHA = 1.0                 #: `ssl909_probe.probe` 와 «같은 꼴»


def probe(X, y, idx, hold):
    """🔴 `ssl909_probe.py:probe` 와 «글자 그대로 같은 꼴». 유보 라벨은 적합에 안 쓴다."""
    from sklearn.linear_model import Ridge
    if len(idx) < 3 or len(np.unique(y[idx])) < 3:
        return float("nan")
    g = Ridge(alpha=RIDGE_ALPHA).fit(X[idx], y[idx])
    return K.sp(g.predict(X[hold]), y[hold])


def features(data, d):
    """`Xraw = [A*M, M]` --- `ssl909_probe.py` 와 같은 꼴. 살아 있는 열만."""
    A, M, _y, _t = data.dom[d]
    A = np.nan_to_num(np.asarray(A, float), nan=0.0, posinf=0.0, neginf=0.0)
    M = (np.asarray(M, float) > 0).astype(float)
    live = np.where(M.sum(0) > 0)[0]
    return np.hstack([A[:, live] * M[:, live], M[:, live]])


def main():
    t0 = time.time()
    out = collections.OrderedDict()
    out["무엇"] = "997 팔 ㉠ · 🔴 라벨 프로브 자의 `MDE` — 전량 라벨 · 소수 라벨 k 다섯"
    out["🔴🔴 `MDE` 정의"] = K.MDE_DEF

    data = K.load()
    doms = list(data.dom)
    X, Y, TR, HO = {}, {}, {}, {}
    for d in doms:
        X[d] = features(data, d)
        Y[d] = np.asarray(data.dom[d][2], float)
        TR[d] = np.where(data.rows(d, post=False, labeled=True, T=K.T_CANON))[0]
        HO[d] = np.where(data.rows(d, post=True, labeled=True, T=K.T_CANON))[0]
        assert len(np.intersect1d(TR[d], HO[d])) == 0, "🔴 %s 학습∩유보 != 0" % d
    W = data.weights(K.T_CANON)
    out["분모"] = collections.OrderedDict([
        ("도메인", len(doms)),
        ("도메인별 학습 라벨", {d: int(len(TR[d])) for d in doms}),
        ("도메인별 유보 라벨", {d: int(len(HO[d])) for d in doms}),
        ("🔴 유보 라벨 합 = 이 자의 분모", int(sum(W.values()))),
        ("군집", len(doms)),
        ("🔴 열 수", {d: int(X[d].shape[1]) for d in doms})])

    # ── 팔 --- 실측 · 바닥 ④ 난수 표현 · 바닥 ⑤ 라벨 순열 ────────────────
    full = collections.OrderedDict()
    for d in doms:
        rng = np.random.RandomState(9970 + len(d))
        Xr = rng.standard_normal(X[d].shape)          # 🔴 바닥 ④
        yp = Y[d].copy()
        tr = TR[d]
        yp[tr] = yp[tr][rng.permutation(len(tr))]     # 🔴 바닥 ⑤ (학습 라벨만)
        full[d] = collections.OrderedDict([
            ("실측", K._r(probe(X[d], Y[d], tr, HO[d]))),
            ("바닥 ④ 난수 표현", K._r(probe(Xr, Y[d], tr, HO[d]))),
            ("바닥 ⑤ 라벨 순열", K._r(probe(X[d], yp, tr, HO[d])))])
    out["팔 · 전량 라벨"] = full

    def _c(key):
        return {d: float(full[d]["실측"]) - float(full[d][key]) for d in doms}

    heads = collections.OrderedDict([
        ("실측 − 난수 표현(④)", _c("바닥 ④ 난수 표현")),
        ("실측 − 라벨 순열(⑤)", _c("바닥 ⑤ 라벨 순열"))])
    out["🔴 헤드라인 대비 · 전량 라벨"] = collections.OrderedDict(
        [(k, C.cluster_se(v)) for k, v in heads.items()])
    out["🔴 부호뒤집기 «전수» 순열 · 전량 라벨"] = C.signflip_exact(
        {d: [heads["실측 − 난수 표현(④)"][d], heads["실측 − 라벨 순열(⑤)"][d]]
         for d in doms}, list(heads))
    out["🔴 해석 SE 대 등록된 뽑기 SE"] = C.se_surrogate_check(
        heads["실측 − 난수 표현(④)"])

    # ── 위약 짝 · 전량 라벨 --- 학습 행을 씨앗별로 «반씩» 갈라 두 프로브 ────
    pool_full = {d: [] for d in doms}
    for d in doms:
        for s in K.SEEDS:
            rs = np.random.RandomState(70000 + 13 * s + len(d))
            tr = TR[d]
            if len(tr) < 8:
                continue
            pm = rs.permutation(len(tr))
            h = len(tr) // 2
            a = probe(X[d], Y[d], tr[pm[:h]], HO[d])
            b = probe(X[d], Y[d], tr[pm[h:2 * h]], HO[d])
            if np.isfinite(a) and np.isfinite(b):
                pool_full[d] += [float(a - b), float(b - a)]
    out["위약 짝 · 전량 라벨"] = collections.OrderedDict([
        ("무엇", "같은 도메인의 학습 행을 씨앗별로 반씩 갈라 적합한 두 프로브의 차 "
               "--- 참 효과가 «구성상» 0 이고 «자료를 실제로 흩는다»"),
        ("씨앗", list(K.SEEDS)),
        ("도메인별 값 수", {d: len(pool_full[d]) for d in doms}),
        ("도메인별 SD", {d: (K._r(float(np.std(pool_full[d], ddof=1)))
                          if len(pool_full[d]) > 1 else None) for d in doms})])
    pc_full = K.power_curve(pool_full, [d for d in doms if len(pool_full[d]) > 1])
    out["🔴🔴🔴 MDE (자 ㉠ · 전량 라벨)"] = pc_full
    hm_full = pc_full.get("🔴🔴 MDE_s", {}).get(
        "🔴 ㉠ 2·SE(헤드라인)", {}).get("MDE_s(선형 보간)")
    out["🔴🔴🔴 분기 · 전량 라벨"] = K.branch(hm_full)

    # ── 소수 라벨 k --- 915·998 의 갈래 ────────────────────────────────
    kout = collections.OrderedDict()
    for k in KS:
        dl = [d for d in doms if len(TR[d]) >= 2 * k]
        pool = {d: [] for d in dl}
        obs = {d: [] for d in dl}
        for d in dl:
            rng = np.random.RandomState(90900 + 7 * k + len(d))
            Xr = rng.standard_normal(X[d].shape)
            for s in K.SEEDS:
                for r in range(SHAM_PAIRS_KSHOT):
                    i1 = rng.choice(TR[d], k, replace=False)
                    i2 = rng.choice(TR[d], k, replace=False)
                    a = probe(X[d], Y[d], i1, HO[d])
                    b = probe(X[d], Y[d], i2, HO[d])
                    if np.isfinite(a) and np.isfinite(b):
                        pool[d] += [float(a - b), float(b - a)]
                    c = probe(Xr, Y[d], i1, HO[d])
                    if np.isfinite(a) and np.isfinite(c):
                        obs[d].append(float(a - c))
        pc = K.power_curve(pool, [d for d in dl if len(pool[d]) > 1])
        hm = pc.get("🔴🔴 MDE_s", {}).get(
            "🔴 ㉠ 2·SE(헤드라인)", {}).get("MDE_s(선형 보간)")
        g915 = abs(G915_K16_SSL - G915_K16_PERM)
        obs_m = {d: float(np.mean(obs[d])) for d in dl if obs[d]}
        kout["k=%d" % k] = collections.OrderedDict([
            ("분모: 잰 도메인", len(dl)), ("도메인", dl),
            ("🔴 헤드라인 대비(실측 − 난수표현) · 등록된 자",
             C.cluster_se(obs_m) if len(obs_m) >= 2
             else {"🔴 못 쟀다": "도메인 2 미만"}),
            ("분모: 도메인별 위약 값 수", {d: len(pool[d]) for d in dl}),
            ("실측 − 난수표현(도메인 평균)",
             {d: K._r(float(np.mean(obs[d]))) for d in dl if obs[d]}),
            ("🔴🔴 MDE", pc.get("🔴🔴 MDE_s")),
            ("해석식 MDE_a", pc.get("🔴 해석식 MDE_a")),
            ("귀무 1종 오류", pc.get("귀무 δ=0 에서 잰 것")),
            ("🔴 MDE_s / MDE_a", pc.get("🔴 MDE_s / MDE_a")),
            ("🔴🔴 915 의 차(%.4f − %.4f = %.4f)를 잴 수 있었나"
             % (G915_K16_SSL, G915_K16_PERM, g915),
             collections.OrderedDict([
                 ("915 의 차", K._r(g915)), ("이 자의 MDE_s", K._r(hm) if hm else None),
                 ("🔴 MDE / 915 차", K._r(hm / g915) if hm else None),
                 ("🔴 판정", ("MDE 를 못 냈다" if hm is None else
                          ("잴 수 있었다" if hm <= g915 else
                           "🔴 «못 쟀다» --- 915 의 차는 이 자의 잡음 «아래»다")))])),
            ("분기", K.branch(hm))])
        print("  k=%d 끝 · %.0f초" % (k, time.time() - t0), flush=True)
    out["🔴🔴🔴 MDE (자 ㉠ · 소수 라벨)"] = kout

    # ── 🔴 조항 79 --- 소수 라벨 곡선을 «조각»(k 사다리)으로 ──────────────
    lab = ["k=%d" % k for k in KS]
    per_by = {}
    for k in KS:
        cell = kout["k=%d" % k].get("실측 − 난수표현(도메인 평균)") or {}
        per_by["k=%d" % k] = {d: float(v) for d, v in cell.items()}
    common = set.intersection(*[set(per_by[l]) for l in lab]) if lab else set()
    per_by = {l: {d: per_by[l][d] for d in sorted(common)} for l in lab}
    segd = {d: [per_by[lab[i + 1]][d] - per_by[lab[i]][d]
                for i in range(len(lab) - 1)] for d in sorted(common)}
    out["🔴 조항 79 조각 — k 사다리(소수 라벨 곡선)"] = collections.OrderedDict([
        ("🔴 공통 분모 도메인(모든 k 에서 잰 것)", sorted(common)),
        ("분모: 도메인", len(common)),
        ("🔴 조각(`delta996_common.seg_from`)",
         C.seg_from(lab, per_by) if len(common) >= 2 else {"🔴 못 쟀다": "공통 도메인 2 미만"}),
        ("🔴 부호뒤집기 «전수» 순열(조각 넷)",
         C.signflip_exact(segd, ["%s→%s" % (lab[i], lab[i + 1])
                                 for i in range(len(lab) - 1)])
         if len(common) >= 2 else {"🔴 못 쟀다": "공통 도메인 2 미만"})])

    # ── 조항 78 ㉮·㉯ --- 🔴 «기계로» ────────────────────────────────
    base = collections.OrderedDict(heads)

    def _m(st, key):
        v = np.array([st[key][d] for d in doms], float)
        return float(np.nanmean(v))

    def _s(st, key):
        v = np.array([st[key][d] for d in doms], float)
        v = v[np.isfinite(v)]
        if len(v) < 2:
            return float("nan")
        return float(v.std(ddof=1) * np.sqrt((len(v) - 1.0) / len(v))
                     / np.sqrt(len(v)))

    kk = "실측 − 난수 표현(④)"
    claims = [
        ("헤드라인(④)이 2·SE 를 넘는다", lambda st: abs(_m(st, kk)) > 2 * _s(st, kk)),
        ("헤드라인(④)이 양수다", lambda st: _m(st, kk) > 0),
        ("바닥 ⑤ 대비도 2·SE 를 넘는다",
         lambda st: abs(_m(st, "실측 − 라벨 순열(⑤)")) > 2 * _s(st, "실측 − 라벨 순열(⑤)")),
        ("동부호가 9/12 이상이다", lambda st: sum(
            1 for d in doms if np.sign(st[kk][d]) == np.sign(_m(st, kk))) >= 9),
        ("|Δ̄| 가 전량 라벨 MDE 를 넘는다",
         lambda st: (hm_full is not None) and abs(_m(st, kk)) > hm_full),
        ("부호뒤집기 순열 p ≤ α", lambda st: float(K.signflip_p_batch(
            np.array([[st[kk][d]] for d in doms], float))[0][0]) <= K.ALPHA),
    ]
    controls = [
        ("대조(늘 참이어야) — 조각이 1 개 이상이다", lambda st: len(st) >= 1),
        ("대조(늘 거짓이어야) — |Δ̄| 가 자기 자신보다 크다",
         lambda st: abs(_m(st, kk)) > abs(_m(st, kk))),
    ]
    out["🔴🔴 조항 78 ㉮·㉯ (기계)"] = C.taut_scan(
        claims, C.variant_grid(base, seed=997), label="자 ㉠ 헤드라인",
        controls=controls)
    out["🔴 조항 79 개정 2 — cluster_se 칸 전량"] = C.cse_ledger()
    out.update(K.stamp(t0))
    h = K.json_dump(OUT, out)
    print("→ %s  sha256 %s  %.1f분" % (OUT, h[:16], (time.time() - t0) / 60.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
