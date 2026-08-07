"""축퇴 가설의 직접 검정 --- 노트 8이 적은 반증 조건.

노트 8의 주장 상자에 이렇게 적었다.

    반증 조건. 복원된 다섯 축을 서로 직교화(잔차화)한 뒤에도 승률이 회복되지 않으면
    원인은 축퇴가 아니라 정보 부족이다. 반대로 직교화만으로 회복되면 문서에 정보는
    있고 추출이 잘못된 것이다.

가설은 이랬다 --- 다섯 축을 같은 문서 피처로 예측하면 복원 오차가 상관돼 다섯이
실질적으로 하나의 '규모' 축으로 무너지고, 다섯이 서로 다른 것을 재기 때문에 생기던
이득이 사라진다.

두 가지를 잰다.

  A. 상관 구조 비교
     사람이 매긴 다섯 축의 상관행렬과 문서에서 복원한 다섯 축의 상관행렬을 나란히
     본다. 축퇴가 사실이면 복원 쪽이 훨씬 더 상관돼 있어야 한다. 평균 절대 상관과
     첫 주성분의 설명 비율로 요약한다.

  B. 직교화 후 재검정
     복원된 축을 순차 잔차화(그람-슈미트)해 서로 직교하게 만든 뒤 결과를 예측한다.
     직교화는 정보를 더하지 않고 재배치만 하므로, 이것으로 회복된다면 문제는
     정보량이 아니라 표현이었다는 뜻이다.

사용: python3 -m state.degeneracy
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .replicate_n5 import lane_ridge
from .slots import AXES, load_popup

SEED = 20260728


def gram_schmidt(P: np.ndarray) -> np.ndarray:
    """열을 순차 직교화한다. 각 열에서 앞선 열들에 설명되는 성분을 뺀다."""
    Q = np.zeros_like(P, dtype=float)
    for j in range(P.shape[1]):
        v = P[:, j].astype(float).copy()
        for k in range(j):
            n2 = Q[:, k] @ Q[:, k]
            if n2 > 1e-12:
                v -= (v @ Q[:, k]) / n2 * Q[:, k]
        Q[:, j] = v
    return Q


def corr_summary(M: np.ndarray) -> dict:
    """평균 절대 비대각 상관 + 첫 주성분 설명 비율."""
    Z = (M - M.mean(0)) / (M.std(0) + 1e-9)
    C = np.corrcoef(Z, rowvar=False)
    off = C[~np.eye(len(C), dtype=bool)]
    ev = np.linalg.eigvalsh(np.cov(Z, rowvar=False))[::-1]
    return {"평균절대상관": round(float(np.abs(off).mean()), 3),
            "최대절대상관": round(float(np.abs(off).max()), 3),
            "제1주성분_설명비": round(float(ev[0] / ev.sum()), 3)}


def run(reps: int = 20) -> dict:
    X, y, w, A, M, groups, times, cols = load_popup()
    uniq = np.unique(groups)
    print(f"축퇴 검정 — n={len(y)} IP={len(uniq)} 반복={reps}")

    # ── A. 상관 구조 ──────────────────────────────────────────────────
    # 복원 축은 폴드 밖 예측을 모아 만든다(같은 폴드에서 학습·예측하면 낙관적이다).
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(len(uniq))
    b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
    gb = np.array([b[g] for g in groups])
    P = np.zeros_like(A, dtype=float)
    for k in range(5):
        te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
        if len(te) == 0 or len(tr) < 10:
            continue
        for j in range(len(AXES)):
            P[te, j] = lane_ridge(X[tr], A[tr, j], w[tr], X[te])
    ca, cp = corr_summary(A), corr_summary(P)
    print("\n── A. 상관 구조 ──")
    print(f"  {'':<14}{'평균|r|':>9}{'최대|r|':>9}{'PC1 설명':>10}")
    print(f"  {'사람 태그':<14}{ca['평균절대상관']:>9.3f}{ca['최대절대상관']:>9.3f}"
          f"{ca['제1주성분_설명비']:>10.3f}")
    print(f"  {'문서 복원':<14}{cp['평균절대상관']:>9.3f}{cp['최대절대상관']:>9.3f}"
          f"{cp['제1주성분_설명비']:>10.3f}")

    # ── B. 직교화 후 재검정 ────────────────────────────────────────────
    arms = ["참 축", "복원 축", "복원 축 직교화", "복원 축 표준화"]
    per = {a: [] for a in arms}
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        e = {a: [] for a in arms}
        ec = []
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            Ptr = np.zeros((len(tr), len(AXES)))
            Pte = np.zeros((len(te), len(AXES)))
            for j in range(len(AXES)):
                Ptr[:, j] = lane_ridge(X[tr], A[tr, j], w[tr], X[tr])
                Pte[:, j] = lane_ridge(X[tr], A[tr, j], w[tr], X[te])
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            e["참 축"].append(np.abs(lane_ridge(A[tr], y[tr], w[tr], A[te]) - y[te]))
            e["복원 축"].append(np.abs(lane_ridge(Ptr, y[tr], w[tr], Pte) - y[te]))
            # 직교화는 학습 폴드에서 기저를 정하고 검정 폴드에 같은 변환을 적용한다.
            Qtr = gram_schmidt(Ptr)
            B = np.linalg.lstsq(Ptr, Qtr, rcond=None)[0]
            e["복원 축 직교화"].append(
                np.abs(lane_ridge(Qtr, y[tr], w[tr], Pte @ B) - y[te]))
            mu, sd = Ptr.mean(0), Ptr.std(0) + 1e-9
            e["복원 축 표준화"].append(
                np.abs(lane_ridge((Ptr - mu) / sd, y[tr], w[tr], (Pte - mu) / sd) - y[te]))
        c = np.concatenate(ec).mean()
        for a in arms:
            per[a].append(float(np.concatenate(e[a]).mean() - c))

    print("\n── B. 직교화 후 재검정 ──")
    out = {"상관": {"사람": ca, "복원": cp}, "팔": {}}
    for a in arms:
        v = np.array(per[a])
        out["팔"][a] = {"median": round(float(np.median(v)), 4),
                        "sd": round(float(v.std()), 4),
                        "win_rate": round(float((v < 0).mean()), 3)}
        print(f"  {a:<16}Δ중앙 {np.median(v):+.4f}  SD {v.std():.4f}  "
              f"승률 {(v < 0).mean():.2f}")

    rec = out["팔"]["복원 축 직교화"]["win_rate"] - out["팔"]["복원 축"]["win_rate"]
    print(f"\n직교화로 인한 승률 변화: {rec:+.2f}")
    print("  → 회복되면 원인은 표현(축퇴), 회복 안 되면 원인은 정보 부족")
    Path("data/state/degeneracy.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
