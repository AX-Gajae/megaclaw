"""노트 5의 반복 CV를 독립 재현한다.

계기: state/slots.py 의 two_stage() 에서 '참 축(상한)' — 다섯 축 태그를 그대로 GBDT에
넣은 팔 — 이 IP 무작위 5폴드 20회 반복에서 상수에 졌다(중앙 +0.0357, 승률 10%).
그런데 노트 5는 같은 프로토콜에서 고정 5종이 40회 중 40회 이겼다고 보고했다.
정면 충돌이므로 재현이 먼저다.

노트 5의 실행은 인라인이라 파일로 남지 않았다. 여기서 다시 짠다. 차이가 날 수 있는
지점을 전부 축으로 열어 어느 것이 결과를 뒤집는지 본다.

  · 피처 표현     원값(0~4) + mask  vs  0~1 정규화만
  · 레인          gbdt  vs  ridge
  · 피처 집합     10종  vs  고정 5종
  · 표본 가중치   사용  vs  미사용

사용: python3 -m state.replicate_n5
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

SEED = 20260728
TEN = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale",
       "collab_strength", "ip_awareness", "experience_density", "photo_zones", "season_fit"]
FIVE = TEN[:5]


def pool(grades=("A", "B")):
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    X, cols, y, w = d["X"], [str(c) for c in d["names"]], d["y_perday"], d["w"]
    meta = json.loads(Path("data/state/popup_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in grades:
        if f"trust_{g}" in cols:
            keep |= X[:, cols.index(f"trust_{g}")] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    keep &= np.array([m.get("counting") in ("entry", "participation") for m in meta])
    X, y, w = X[keep], y[keep], w[keep]
    meta = [m for m, k in zip(meta, keep) if k]
    groups = np.array([m.get("ip") or m["id"] for m in meta])
    return X, cols, y.astype(float), w.astype(float), groups


def build(X, cols, axes, with_mask: bool, scale: bool):
    idx = [cols.index(f"t1o_{a}") for a in axes]
    F = X[:, idx].astype(float)
    if scale:
        F = F / 4.0
    if with_mask:
        F = np.hstack([F, X[:, [cols.index(f"t1o_{a}_mask") for a in axes]].astype(float)])
    return F


def lane_gbdt(Ftr, ytr, wtr, Fte):
    m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300,
                                      l2_regularization=1.0,
                                      min_samples_leaf=max(3, len(ytr) // 10),
                                      random_state=SEED)
    m.fit(Ftr, ytr, sample_weight=wtr)
    return m.predict(Fte)


def lane_ridge(Ftr, ytr, wtr, Fte):
    keep = Ftr.std(0) > 1e-9
    if keep.sum() == 0:
        return np.full(len(Fte), np.median(ytr))
    mu, sd = Ftr[:, keep].mean(0), Ftr[:, keep].std(0) + 1e-9
    m = Ridge(alpha=1.0).fit((Ftr[:, keep] - mu) / sd, ytr, sample_weight=wtr)
    return m.predict((Fte[:, keep] - mu) / sd)


LANES = {"gbdt": lane_gbdt, "ridge": lane_ridge}


def repeat_cv(F, y, w, groups, lane: str, reps: int = 40, use_w: bool = True):
    uniq = np.unique(groups)
    diffs = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        ec, em = [], []
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            wt = w[tr] if use_w else np.ones(len(tr))
            em.append(np.abs(LANES[lane](F[tr], y[tr], wt, F[te]) - y[te]))
        diffs.append(float(np.concatenate(em).mean() - np.concatenate(ec).mean()))
    v = np.array(diffs)
    return {"median": round(float(np.median(v)), 4), "mean": round(float(v.mean()), 4),
            "sd": round(float(v.std()), 4), "win_rate": round(float((v < 0).mean()), 3)}


def main() -> int:
    X, cols, y, w, groups = pool()
    print(f"풀 n={len(y)}  IP={len(np.unique(groups))}")
    rows = []
    for axes, aname in ((TEN, "10종"), (FIVE, "고정 5종")):
        for with_mask in (True, False):
            for scale in (False, True):
                for lane in ("gbdt", "ridge"):
                    for use_w in (True, False):
                        F = build(X, cols, axes, with_mask, scale)
                        r = repeat_cv(F, y, w, groups, lane, use_w=use_w)
                        rows.append({"집합": aname, "mask": with_mask, "0~1": scale,
                                     "레인": lane, "가중": use_w, **r})
    rows.sort(key=lambda d: d["median"])
    print(f"{'집합':<8}{'mask':<6}{'0~1':<6}{'레인':<7}{'가중':<6}"
          f"{'Δ중앙':>9}{'SD':>8}{'승률':>7}")
    for d in rows:
        print(f"{d['집합']:<8}{str(d['mask']):<6}{str(d['0~1']):<6}{d['레인']:<7}"
              f"{str(d['가중']):<6}{d['median']:>9.4f}{d['sd']:>8.4f}{d['win_rate']:>7.2f}")
    Path("data/state/replicate_n5.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
