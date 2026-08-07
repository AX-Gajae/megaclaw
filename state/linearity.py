"""다섯 축의 신호는 선형인가 — 그리고 레인을 바꾸면 노트 5가 뒤집히는가.

발견(2026-07-28): 같은 다섯 축, 같은 75건, 같은 IP 무작위 5폴드 40회에서
  ridge  Δ중앙 -0.0354  승률 100%
  gbdt   Δ중앙 +0.0276  승률  15%
레인 하나가 결론을 정반대로 만든다.

두 가지를 가른다.

  A. 신호가 선형인가?  다섯 축에 제곱·상호작용을 더한 ridge와 순수 선형 ridge를
     비교한다. 확장이 도움이 안 되면 신호는 선형이다. 확장이 무너지면
     비선형이 없는 게 아니라 표본이 감당 못 하는 것이다 — 둘은 다르다.
     구분하려면 표본을 늘려 재보는 수밖에 없으므로, 여기서는 '현재 표본에서
     비선형 항은 이득이 없다'까지만 말한다.

  B. 노트 5의 '선택 불가'는 레인 탓인가?  노트 5는 중첩 CV에서 폴드마다 다른
     다섯을 골랐고, 그래서 축을 데이터로 발견할 수 없다고 결론지었다.
     그 실행의 레인이 무엇이었는지 기록이 없다. ridge로 다시 돌려
     폴드 간 선택 일치도를 잰다.

사용: python3 -m state.linearity
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import numpy as np

from .replicate_n5 import FIVE, TEN, build, lane_gbdt, lane_ridge, pool, repeat_cv

SEED = 20260728


def expand(F: np.ndarray, mode: str) -> np.ndarray:
    """선형 / +제곱 / +상호작용 / 전부."""
    parts = [F]
    if mode in ("sq", "all"):
        parts.append(F ** 2)
    if mode in ("inter", "all"):
        k = F.shape[1]
        parts.append(np.column_stack([F[:, i] * F[:, j] for i, j in combinations(range(k), 2)]))
    return np.hstack(parts)


def linearity(reps: int = 40) -> dict:
    X, cols, y, w, g = pool()
    base = build(X, cols, FIVE, with_mask=False, scale=True)
    rows = []
    for mode, nm in (("lin", "선형만"), ("sq", "+제곱"), ("inter", "+상호작용"), ("all", "전부")):
        F = expand(base, mode)
        r = repeat_cv(F, y, w, g, "ridge", reps=reps)
        rows.append({"확장": nm, "차원": int(F.shape[1]), **r})
    return {"n": int(len(y)), "reps": reps, "확장": rows}


def nested_select(lane: str = "ridge", reps: int = 20, k: int = 5) -> dict:
    """IP 무작위 5폴드 안에서 leave-one-out으로 k개를 고른다.

    노트 5는 시간순 4폴드에서 이걸 했고 폴드마다 다른 답이 나왔다.
    레인을 바꾸면 안정성이 달라지는지 본다. 선택은 학습 폴드 안에서만 일어난다."""
    from .replicate_n5 import LANES
    X, cols, y, w, g = pool()
    uniq = np.unique(g)
    picks, diffs = [], []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {gg: perm[i] % 5 for i, gg in enumerate(uniq)}
        gb = np.array([b[gg] for gg in g])
        ec, em = [], []
        for f in range(5):
            te, tr = np.where(gb == f)[0], np.where(gb != f)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            # 안쪽 — 학습 폴드만으로 leave-one-out, 하나씩 빼며 k개까지 줄인다
            cur = list(TEN)
            while len(cur) > k:
                best, bestv = None, np.inf
                for drop in cur:
                    cand = [c for c in cur if c != drop]
                    F = build(X, cols, cand, with_mask=False, scale=True)
                    e = []
                    for i in range(len(tr)):
                        it = np.delete(tr, i)
                        p = LANES[lane](F[it], y[it], w[it], F[tr[i]:tr[i] + 1])
                        e.append(abs(p[0] - y[tr[i]]))
                    v = float(np.mean(e))
                    if v < bestv:
                        best, bestv = drop, v
                cur.remove(best)
            picks.append(tuple(sorted(cur)))
            F = build(X, cols, cur, with_mask=False, scale=True)
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            em.append(np.abs(LANES[lane](F[tr], y[tr], w[tr], F[te]) - y[te]))
        diffs.append(float(np.concatenate(em).mean() - np.concatenate(ec).mean()))

    from collections import Counter
    freq = Counter()
    for p in picks:
        freq.update(p)
    # 폴드 쌍 자카드 일치도
    js = [len(set(a) & set(b)) / len(set(a) | set(b))
          for a, b in combinations(picks, 2)]
    v = np.array(diffs)
    return {"lane": lane, "folds_selected": len(picks),
            "속성별_선택률": {a: round(freq[a] / len(picks), 3)
                          for a in sorted(TEN, key=lambda t: -freq[t])},
            "자카드_평균": round(float(np.mean(js)), 3),
            "중첩선택_vs_상수": {"median": round(float(np.median(v)), 4),
                             "win_rate": round(float((v < 0).mean()), 3)}}


def main() -> int:
    out = {"선형성": linearity(reps=40)}
    print("── A. 신호가 선형인가 (ridge, 고정 5종) ──")
    for r in out["선형성"]["확장"]:
        print(f"  {r['확장']:<10} 차원 {r['차원']:>2}  Δ중앙 {r['median']:+.4f}  "
              f"SD {r['sd']:.4f}  승률 {r['win_rate']:.2f}")

    print("\n── B. 레인을 바꾸면 선택이 안정되는가 ──")
    for lane in ("ridge", "gbdt"):
        s = nested_select(lane=lane, reps=8)
        out[f"선택_{lane}"] = s
        print(f"  [{lane}] 자카드 평균 {s['자카드_평균']:.3f}   "
              f"중첩선택 Δ{s['중첩선택_vs_상수']['median']:+.4f} "
              f"승률 {s['중첩선택_vs_상수']['win_rate']:.2f}")
        for a, p in list(s["속성별_선택률"].items())[:6]:
            print(f"       {a:<22}{p:.2f}")
    Path("data/state/linearity.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
