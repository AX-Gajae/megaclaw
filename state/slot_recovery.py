"""문서에서 다섯 축을 복원할 수 있는가 — 앵커 구조의 진짜 병목.

경위. 노트 7 작업 중 예측이 반증됐다. '신호가 선형이므로 헤드를 선형으로 바꾸면
좋아진다'고 예측했는데, 선형 헤드는 조금 좋아졌으나(Δ+0.0211→+0.0047) 인코더까지
선형으로 벗기자 오히려 나빠졌다(+0.05, 항등은 +0.17).

그렇다면 병목은 축→결과가 아니라 문서→축이다. ridge가 이기는 이유는 선형이어서가
아니라 **사람이 매긴 축을 그대로 받기 때문**일 수 있다. 그 가설을 직접 잰다.

측정: 폴드 밖에서 문서 피처만으로 각 축을 예측하고, 사람 태그와 얼마나 맞는지 본다.
비교 기준은 축의 폴드 내 중앙값(상수 예측기)이다. 상수를 못 이기면 그 축은
문서로부터 복원되지 않는다.

함의가 크다. 복원되지 않는다면:
  · 사람 태깅은 문서의 중복 정보가 아니라 **새 정보**다. 생략할 수 없다.
  · 아이돌 도메인 전이는 아이돌 태깅 없이는 불가능하다.
  · 파운데이션 모델의 입력은 문서가 아니라 태그여야 한다.

사용: python3 -m state.slot_recovery
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .replicate_n5 import FIVE, TEN, lane_gbdt, lane_ridge, pool
from .slots import load_popup

SEED = 20260728
LANES = {"ridge": lane_ridge, "gbdt": lane_gbdt}


def recover(reps: int = 20) -> dict:
    X, y, w, A, M, groups, times, cols = load_popup()
    uniq = np.unique(groups)
    print(f"축 복원 검정 — n={len(y)} IP={len(uniq)} 문서 피처={X.shape[1]} 반복={reps}")

    res = {a: {ln: [] for ln in LANES} for a in FIVE}
    for a in FIVE:
        res[a]["const"] = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        acc = {a: {k: [] for k in list(LANES) + ["const"]} for a in FIVE}
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            for j, a in enumerate(FIVE):
                t_tr, t_te = A[tr, j], A[te, j]
                acc[a]["const"].append(np.abs(np.median(t_tr) - t_te))
                for ln, fn in LANES.items():
                    p = fn(X[tr], t_tr, w[tr], X[te])
                    acc[a][ln].append(np.abs(p - t_te))
        for a in FIVE:
            for k in list(LANES) + ["const"]:
                res[a][k].append(float(np.concatenate(acc[a][k]).mean()))

    out = {"n": int(len(y)), "reps": reps, "축": {}}
    print(f"\n{'축':<20}{'상수':>8}{'ridge':>9}{'gbdt':>9}{'최선 Δ':>10}{'승률':>7}")
    for a in FIVE:
        c = np.array(res[a]["const"])
        row = {"const_mae": round(float(np.median(c)), 4)}
        best, bestd = None, np.inf
        for ln in LANES:
            v = np.array(res[a][ln])
            d = v - c
            row[ln] = {"mae": round(float(np.median(v)), 4),
                       "diff": round(float(np.median(d)), 4),
                       "win_rate": round(float((d < 0).mean()), 3)}
            if np.median(d) < bestd:
                best, bestd = ln, float(np.median(d))
        row["best"] = best
        out["축"][a] = row
        print(f"{a:<20}{row['const_mae']:>8.4f}{row['ridge']['mae']:>9.4f}"
              f"{row['gbdt']['mae']:>9.4f}{bestd:>+10.4f}"
              f"{row[best]['win_rate']:>7.2f}")

    # 복원된 축으로 결과를 예측하면? (2단 ridge — 노트 7의 최종 판정)
    print("\n── 복원된 축으로 결과 예측 (2단 ridge) ──")
    d2 = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        ec, e2, et = [], [], []
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            Ptr = np.zeros((len(tr), len(FIVE))); Pte = np.zeros((len(te), len(FIVE)))
            for j in range(len(FIVE)):
                Ptr[:, j] = lane_ridge(X[tr], A[tr, j], w[tr], X[tr])
                Pte[:, j] = lane_ridge(X[tr], A[tr, j], w[tr], X[te])
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            e2.append(np.abs(lane_ridge(Ptr, y[tr], w[tr], Pte) - y[te]))
            et.append(np.abs(lane_ridge(A[tr], y[tr], w[tr], A[te]) - y[te]))
        c = np.concatenate(ec).mean()
        d2.append((float(np.concatenate(e2).mean() - c),
                   float(np.concatenate(et).mean() - c)))
    v2 = np.array([a for a, _ in d2]); vt = np.array([b for _, b in d2])
    out["2단"] = {"복원축": {"median": round(float(np.median(v2)), 4),
                          "win_rate": round(float((v2 < 0).mean()), 3)},
                 "참축": {"median": round(float(np.median(vt)), 4),
                        "win_rate": round(float((vt < 0).mean()), 3)}}
    print(f"  복원된 축 → 결과   Δ중앙 {np.median(v2):+.4f}  승률 {(v2<0).mean():.2f}")
    print(f"  참 축   → 결과   Δ중앙 {np.median(vt):+.4f}  승률 {(vt<0).mean():.2f}")
    Path("data/state/slot_recovery.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    recover()
