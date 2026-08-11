# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 4단계 — **소수 라벨 곡선**으로 판정한다. 🔴 판 ρ 로 재지 않는다.

🔴 사전등록 `docs/prereg_915_grid.md` §4.3~4.4
  · 자는 **소수 라벨 곡선**(k = 문턱 ③ 이 허락한 8·16·32). 표현을 **얼리고** 선형 프로브.
  · 팔: ① 원 축(36열) ② 격자 원값(사전학습 없음 = 「처음부터」) ③ 격자 SSL 표현(층별)
        ④ 🔴 **난수 표현**(같은 아키텍처 · 학습 0스텝) ⑤ 🔴 **라벨 순열** ⑥ 원 축 + SSL
  · 🔴 **바닥 없는 자로 「통과」를 쓰지 않는다**(티처 #70).
  · 🔴 규약 47 — 구간은 `lab.pairboot.cluster_boot` BCa. **군집은 격자**
    (같은 격자의 여러 팝업은 독립이 아니다). 폴백이면 사유를 필드에 적는다.
  · 첫 양수를 그대로 채택하지 않는다(노트 133).

산출물: runners/out915_probe.json
사용: python3 runners/grid915_probe.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
from state.grid915 import SCR  # noqa: E402
from lab.pairboot import cluster_boot  # noqa: E402  읽기만

import os
#: 🔴 갈래 딱지 — 스텝을 늘린 표현(rep30k_*)으로 다시 재는 확인용. 기본은 등록한 8,000스텝
TAG = os.environ.get("G915_TAG", "")
OUT = ROOT / ("runners/out915_probe%s.json" % TAG)
REPGLOB = "rep%s_L*_s*.npz" % TAG
KS = [8, 16, 32]
DRAWS = 200
PCA_D = 16
ALPHA = 1.0
MIN_TEST = 20


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


def spear(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    from scipy.stats import rankdata
    ra, rb = rankdata(a), rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def pipe(X: np.ndarray) -> np.ndarray:
    """표준화 → PCA d=16. 🔴 **라벨을 안 쓴다**(비지도) · 모든 팔에 **똑같이** 건다."""
    X = np.asarray(X, float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = X - X.mean(0)
    s = X.std(0)
    s[s < 1e-9] = 1.0
    X = X / s
    d = min(PCA_D, X.shape[1], X.shape[0] - 1)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    return U[:, :d] * S[:d]


def ridge_fit(X, y, alpha=ALPHA):
    X1 = np.concatenate([X, np.ones((len(X), 1))], 1)
    A = X1.T @ X1 + alpha * np.eye(X1.shape[1])
    A[-1, -1] -= alpha                       # 절편은 안 벌준다
    return np.linalg.solve(A, X1.T @ y)


def ridge_pred(w, X):
    return np.concatenate([X, np.ones((len(X), 1))], 1) @ w


def main() -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    res = {"팔": "915-ㅋ", "단계": "4 — 판정(소수 라벨 곡선)",
           "사전등록": "docs/prereg_915_grid.md",
           "🔴 자": "소수 라벨 곡선. 판 ρ 는 안 쓴다(docs/목표.md §판 ρ 를 목표로 쓰면 안 되는 이유)",
           "코드 sha256": {c: sha16(ROOT / c) for c in
                          ("runners/grid915_probe.py", "runners/grid915_ssl.py",
                           "state/grid915.py")},
           "시작 UTC": t0.isoformat(timespec="seconds")}

    # ── 라벨과 원 축 — 🔴 여기서 **처음** 라벨을 연다(사전학습은 안 봤다) ──
    import out901h_link as L
    mkax = json.loads((ROOT / "data/state/market_axes.json").read_text())
    axis_ids = {"팝업": L.popup_axis_ids(), "시장팝업": list(mkax)}
    import ff753 as FF
    d0 = FF.shell(FF.base())
    lab = {}
    for dom in ("팝업", "시장팝업"):
        A, M, y, t = d0.dom[dom]
        for i, rid in enumerate(axis_ids[dom]):
            if rid in lab or not np.isfinite(y[i]):
                continue
            lab[rid] = {"y": float(y[i]), "A": np.asarray(A[i], float), "도메인": dom}
    naxis = len(next(iter(lab.values()))["A"])

    # ── 표현 ─────────────────────────────────────────────────────────────
    reps = sorted(SCR.glob(REPGLOB))
    if not reps:
        res["🔴 중단"] = "표현 파일이 없다 — runners/grid915_ssl.py 를 먼저 돌려라"
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        raise SystemExit("🔴 표현 없음")
    z0 = np.load(reps[0], allow_pickle=False)
    ids = [str(x) for x in z0["ids"]]
    grids = [str(x) for x in z0["grids"]]
    keep = [i for i, r in enumerate(ids) if r in lab]
    ids = [ids[i] for i in keep]
    grids = [grids[i] for i in keep]
    y = np.array([lab[r]["y"] for r in ids])
    AX = np.stack([lab[r]["A"] for r in ids])
    RAW = z0["raw"][keep]
    n = len(ids)

    res["표본"] = {"🔴 분모 — 프로브 행": n,
                 "🔴 분모 — 유보 합집합": 185, "🔴 분모 — 판 유보": 3775,
                 "서로 다른 격자(군집 수)": len(set(grids)),
                 "도메인 구성": {d: sum(1 for r in ids if lab[r]["도메인"] == d)
                            for d in ("팝업", "시장팝업")},
                 "원 축 열 수": naxis,
                 "라벨 y 요약": {"최소": float(y.min()), "중앙": float(np.median(y)),
                             "최대": float(y.max())}}

    # ── 팔 만들기 ────────────────────────────────────────────────────────
    arms: dict[str, np.ndarray] = {"① 원 축(36열)": pipe(AX),
                                   "② 격자 원값(사전학습 없음 = 처음부터)": pipe(RAW)}
    for f in reps:
        z = np.load(f, allow_pickle=False)
        tag = f.stem.split("_", 1)[1]
        arms[f"③ 격자 SSL {tag}"] = pipe(z["rep"][keep])
        arms[f"④ 난수 표현 {tag}"] = pipe(z["rep_rand"][keep])
    L8 = [k for k in arms if k.startswith("③") and "_L8_" in k]
    if L8:
        z = np.load([f for f in reps if "L8" in f.stem][0], allow_pickle=False)
        arms["⑥ 원 축 + SSL(L8_s0)"] = pipe(np.concatenate([AX, z["rep"][keep]], 1))

    gset = sorted(set(grids))
    gid = np.array([gset.index(g) for g in grids])
    clusters = [np.nonzero(gid == j)[0] for j in range(len(gset))]

    rng = np.random.default_rng(915)
    out_k = {}
    for k in KS:
        if n - k < MIN_TEST:
            out_k[str(k)] = {"🔴 못 쟀다": f"시험행이 {n-k} 뿐 — 사전등록 문턱 ③(≥{MIN_TEST}) 미달"}
            continue
        splits = [rng.permutation(n) for _ in range(DRAWS)]
        rows = {}
        oof = {a: np.zeros(n) for a in arms}
        cnt = np.zeros(n)
        oof["⑤ 라벨 순열(바닥)"] = np.zeros(n)
        per_draw = {a: [] for a in list(arms) + ["⑤ 라벨 순열(바닥)"]}
        for si, pm in enumerate(splits):
            tr, te = pm[:k], pm[k:]
            cnt[te] += 1
            for a, X in arms.items():
                w = ridge_fit(X[tr], y[tr])
                p = ridge_pred(w, X[te])
                oof[a][te] += p
                per_draw[a].append(spear(p, y[te]))
            yp = rng.permutation(y)                    # 🔴 바닥 ⑤ — 라벨을 섞는다
            Xs = arms[next(a for a in arms if a.startswith("③"))]
            w = ridge_fit(Xs[tr], yp[tr])
            p = ridge_pred(w, Xs[te])
            oof["⑤ 라벨 순열(바닥)"][te] += p
            per_draw["⑤ 라벨 순열(바닥)"].append(spear(p, y[te]))
        for a in oof:
            oof[a] = oof[a] / np.maximum(cnt, 1)

        base = "① 원 축(36열)"
        for a in oof:
            rho_draw = float(np.nanmean(per_draw[a]))
            sd_draw = float(np.nanstd(per_draw[a], ddof=1))
            rho_oof = spear(oof[a], y)

            def stat(idx, a=a):
                return spear(oof[a][idx], y[idx]) - spear(oof[base][idx], y[idx])

            if a == base:
                ci = (0.0, 0.0, 0.0, "기준 팔이라 Δ 를 안 잰다")
            else:
                ci = cluster_boot(stat, clusters, B=2000, seed=915)
            rows[a] = {
                "뽑기 평균 ρ(뽑기 200회)": round(rho_draw, 4),
                "뽑기 SD": round(sd_draw, 4),
                "OOF 평균예측 ρ": round(rho_oof, 4),
                "Δρ vs 원 축(OOF)": round(float(ci[0]), 4),
                "BCa 95%": [round(float(ci[1]), 4), round(float(ci[2]), 4)],
                "구간 종류": ci[3],
                "🔴 0 을 무나": bool(ci[1] <= 0 <= ci[2]) if a != base else None,
            }
        out_k[str(k)] = {"학습 라벨 k": k, "시험행": n - k, "뽑기": DRAWS, "팔": rows}
    res["소수 라벨 곡선"] = out_k

    # ── 🔴 바닥 대조 요약 — 「통과」를 쓰려면 여기부터 본다 ────────────────
    summ = {}
    for k, blk in out_k.items():
        if "팔" not in blk:
            summ[k] = blk
            continue
        R = blk["팔"]
        ssl = {a: v for a, v in R.items() if a.startswith("③")}
        rnd = {a: v for a, v in R.items() if a.startswith("④")}
        best = max(ssl, key=lambda a: ssl[a]["OOF 평균예측 ρ"]) if ssl else None
        summ[k] = {
            "원 축 ρ": R["① 원 축(36열)"]["OOF 평균예측 ρ"],
            "처음부터(격자 원값) ρ": R["② 격자 원값(사전학습 없음 = 처음부터)"]["OOF 평균예측 ρ"],
            "SSL 최고": {best: ssl[best]} if best else "없다",
            "🔴 난수 표현 바닥 ρ 범위": [min(v["OOF 평균예측 ρ"] for v in rnd.values()),
                                max(v["OOF 평균예측 ρ"] for v in rnd.values())] if rnd else "🔴 못 쟀다",
            "🔴 라벨 순열 바닥 ρ": R["⑤ 라벨 순열(바닥)"]["OOF 평균예측 ρ"],
            "🔴 판정": ("SSL 표현이 원 축을 이겼다고 못 쓴다 — 구간이 0 을 문다"
                     if (best is None or ssl[best]["🔴 0 을 무나"]) else
                     "SSL 표현의 Δρ 구간이 0 을 안 문다 — 🔴 그래도 난수 바닥과 갈리는지 같이 봐라"),
        }
    res["🔴 바닥과 나란히"] = summ
    res["🔴 판 ρ"] = ("참고 병기 — **다시 안 쟀다.** 카드 값 0.47034 ± 0.0021(SD) 는 12도메인 "
                   "유보 3,775 의 자이고 이 93행의 자가 아니다. 분모가 다르므로 이어 붙이지 않는다(조항 60)")
    res["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["🔴 바닥과 나란히"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
