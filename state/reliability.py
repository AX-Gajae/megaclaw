"""축 측정이 얼마나 정확해야 쓸모가 있는가 --- 태깅 품질의 공학 규격.

경위. 노트 8은 문서에서 복원한 축으로 결과를 예측하면 승률 100%가 5%로 무너진다고
보고하고, 원인을 '축퇴'로 추정했다. 그 가설을 직접 검정하니 반증됐다 --- 복원 축은
사람 태그보다 오히려 **덜** 상관돼 있었고(평균 |r| 0.177 대 0.236), 직교화로 승률이
전혀 회복되지 않았다(변화 0.00).

그래서 '정보 부족'으로 옮겨 갔는데, 축별 복원 상관을 재보니 그것도 아니었다.

    타깃 폭 0.429   매장 노출도 0.438   입장 허들 0.548   굿즈 규모 0.470
    미디어 투입 0.193  (이것만 실패)

넷이 r≈0.43~0.55로 실질 복원된다. 잡음이 아니다. 그런데도 쓸모가 없다.

남는 설명은 **회귀 희석**이다. 측정 오차가 있는 예측변수는 그 효과를 신뢰도만큼
감쇠시킨다(Spearman 1904). 참 축의 효과가 애초에 작으므로(차이 -0.0313),
신뢰도 0.45로 감쇠되면 남는 것이 없다.

그렇다면 답할 수 있는 질문이 생긴다 --- **얼마나 정확해야 쓸모가 있는가.**
사람 태그를 통제된 잡음으로 열화시켜 목표 상관 r을 맞춘 뒤, r이 얼마일 때
상수를 이기기 시작하는지 잰다. 이것은 태깅 품질에 대한 공학 규격이 된다.
평정자 간 일치도가 이 문턱 아래면 태깅 자체를 다시 설계해야 한다.

사용: python3 -m state.reliability
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .replicate_n5 import lane_ridge
from .slots import AXES, load_popup

SEED = 20260728


def degrade(A: np.ndarray, r: float, rng) -> np.ndarray:
    """각 축을 목표 상관 r 로 열화시킨다.

    z 를 표준화한 참 값이라 할 때  z' = r·z + sqrt(1-r²)·e,  e~N(0,1) 독립.
    그러면 corr(z, z') = r 이 된다. 원 눈금으로 되돌려 놓는다."""
    out = np.zeros_like(A, dtype=float)
    for j in range(A.shape[1]):
        v = A[:, j].astype(float)
        sd = v.std()
        if sd < 1e-9:
            out[:, j] = v
            continue
        z = (v - v.mean()) / sd
        e = rng.standard_normal(len(v))
        e = (e - e.mean()) / (e.std() + 1e-9)
        out[:, j] = (r * z + np.sqrt(max(0.0, 1 - r * r)) * e) * sd + v.mean()
    return out


def run(levels=(1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.45, 0.4, 0.3),
        reps: int = 40) -> dict:
    X, y, w, A, M, groups, times, cols = load_popup()
    uniq = np.unique(groups)
    print(f"신뢰도 문턱 검정 — n={len(y)} IP={len(uniq)} 반복={reps}")

    rows = []
    for r_t in levels:
        diffs, achieved = [], []
        for r in range(reps):
            rng = np.random.default_rng(SEED + 1000 * r + int(r_t * 100))
            Ad = degrade(A, r_t, rng)
            achieved.append(float(np.mean([
                np.corrcoef(Ad[:, j], A[:, j])[0, 1] for j in range(A.shape[1])
                if A[:, j].std() > 1e-9])))
            perm = rng.permutation(len(uniq))
            b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
            gb = np.array([b[g] for g in groups])
            ec, em = [], []
            for k in range(5):
                te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
                if len(te) == 0 or len(tr) < 10:
                    continue
                ec.append(np.abs(np.median(y[tr]) - y[te]))
                em.append(np.abs(lane_ridge(Ad[tr], y[tr], w[tr], Ad[te]) - y[te]))
            diffs.append(float(np.concatenate(em).mean() - np.concatenate(ec).mean()))
        v = np.array(diffs)
        rows.append({"목표r": r_t, "실측r": round(float(np.mean(achieved)), 3),
                     "median": round(float(np.median(v)), 4),
                     "sd": round(float(v.std()), 4),
                     "win_rate": round(float((v < 0).mean()), 3)})
        print(f"  r={r_t:.2f} (실측 {rows[-1]['실측r']:.3f})  "
              f"Δ중앙 {rows[-1]['median']:+.4f}  승률 {rows[-1]['win_rate']:.2f}")

    # 문턱 --- 승률이 0.9 / 0.5 를 넘는 최소 r 을 선형 보간으로 찾는다
    th = {}
    for target in (0.9, 0.5):
        lo = None
        for a, b in zip(rows, rows[1:]):
            if a["win_rate"] >= target > b["win_rate"]:
                f = (a["win_rate"] - target) / max(1e-9, a["win_rate"] - b["win_rate"])
                lo = a["목표r"] + f * (b["목표r"] - a["목표r"])
                break
        th[f"승률{int(target*100)}%_필요r"] = None if lo is None else round(lo, 3)
    print(f"\n문턱: {json.dumps(th, ensure_ascii=False)}")
    print("  현재 문서 복원 수준은 r≈0.45 (축별 0.19~0.55)")

    out = {"n": int(len(y)), "reps": reps, "levels": rows, "threshold": th,
           "현재_문서복원_r": 0.45}
    Path("data/state/reliability.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
