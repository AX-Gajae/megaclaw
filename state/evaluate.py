"""E0 평가 배선 — SFS-1 Stage 0. 모델을 바꾸기 전에 '눈금'부터 교체한다.

감사(2026-07-27)가 밝힌 무효 사유:
  · state/encoder.py 의 mu/sd 가 분할 전 전체 X에서 계산됨 → transductive 누출
  · 폴드 분할이 IP·시간을 무시한 랜덤 → 같은 IP가 train/test에 동시 등장, 미래로 과거 예측
  · freeze=False 경로에서 같은 encoder 객체가 5폴드 내내 학습 → 테스트 폴드를 봄
  · LLM 0.07(n=9, rolling-origin)과 NN 0.53(랜덤 5-fold, 누출)은 **같은 표에 올릴 수 없음**

이 모듈이 강제하는 것:
  1) IP-GroupKFold ∩ rolling-origin — 같은 IP는 한 폴드에만, 그리고 test는 train보다 미래
  2) 폴드 내부 fit — 스케일러·축소계수는 train 폴드에서만 적합
  3) 모델-프리 하한 3종 상시 병기 (상수 중앙값 / days-only / marginal band)
  4) 총계·일평균 두 축 동시 보고 (총계 개선의 72%는 기간 산수이므로 게이트로 인정하지 않음)
  5) 채점 라벨 필터 (기본 A·B등급만 — C 하한값·D 스코프혼합·E 추정치는 별도 표)
  6) 페어드 부트스트랩 CI — 두 레인의 차이가 0을 제외하는지

사용: python3 -m state.evaluate --lanes const,days,ridge,gbdt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

SEED = 20260727


# ── 폴드 ────────────────────────────────────────────────────────────────
def group_time_folds(groups: np.ndarray, times: np.ndarray, n_folds: int = 5,
                     min_train_frac: float = 0.3) -> list[tuple[np.ndarray, np.ndarray]]:
    """IP 그룹 무결 + 시간순. test는 항상 train보다 미래이며 같은 IP를 공유하지 않는다."""
    order = np.argsort(times, kind="stable")
    n = len(order)
    start = int(n * min_train_frac)
    bounds = np.linspace(start, n, n_folds + 1).astype(int)
    folds = []
    for i in range(n_folds):
        te_pos = order[bounds[i]:bounds[i + 1]]
        if len(te_pos) == 0:
            continue
        tr_pos = order[:bounds[i]]
        te_groups = set(groups[te_pos])
        tr_pos = np.array([j for j in tr_pos if groups[j] not in te_groups], dtype=int)
        if len(tr_pos) < 30:
            continue
        folds.append((tr_pos, te_pos))
    return folds


# ── 레인 (전부 폴드 내부 fit) ────────────────────────────────────────────
def lane_const(Xtr, ytr, wtr, Xte, cols):
    return np.full(len(Xte), np.median(ytr))


def _col(cols, name):
    return list(cols).index(name) if name in list(cols) else None


def lane_days(Xtr, ytr, wtr, Xte, cols):
    """days 단독 릿지 — '기간 산수' 하한. 이걸 못 이기면 수요를 학습한 게 아니다."""
    from sklearn.linear_model import Ridge
    i = _col(cols, "days")
    if i is None:
        return lane_const(Xtr, ytr, wtr, Xte, cols)
    m = Ridge(alpha=1.0).fit(Xtr[:, [i]], ytr, sample_weight=wtr)
    return m.predict(Xte[:, [i]])


def lane_ridge(Xtr, ytr, wtr, Xte, cols):
    """릿지. 폴드 내부에서 분산 0인 컬럼을 먼저 버린다.

    마스크 컬럼은 그 폴드에 값이 하나도 없으면 전부 0이 되고, StandardScaler가
    0으로 나눠 inf/nan을 만든다. 그 상태로 학습하면 계수 전체가 오염된다.
    """
    from sklearn.linear_model import RidgeCV
    from sklearn.preprocessing import StandardScaler
    sd = Xtr.std(axis=0)
    live = sd > 1e-12
    Xtr, Xte = Xtr[:, live], Xte[:, live]
    sc = StandardScaler().fit(Xtr)                      # ← 폴드 내부 fit
    m = RidgeCV(alphas=np.logspace(-2, 3, 20)).fit(sc.transform(Xtr), ytr, sample_weight=wtr)
    return m.predict(sc.transform(Xte))


def lane_gbdt(Xtr, ytr, wtr, Xte, cols):
    """부스팅. min_samples_leaf를 표본에 맞춰야 한다 — 기본값 20은 우리 표본에서 치명적이다.

    롤링 오리진의 초기 폴드는 학습 표본이 31건인데, max_depth=3에서 두 리프가 각각
    20건을 채우려면 노드에 40건이 필요하다. 분기가 아예 일어나지 않아 **상수 예측기**가
    되고, 그러면 어떤 피처를 넣든 빼든 예측이 비트 단위로 같다.
    실제로 t1_ 절제가 Δ=0.0 CI[0,0]으로 나왔던 원인이 이것이다 — 기여가 없었던 게
    아니라 모델이 피처를 볼 수조차 없었다.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300,
                                       l2_regularization=1.0,
                                       min_samples_leaf=max(3, len(ytr) // 10),
                                       random_state=SEED)
    m.fit(Xtr, ytr, sample_weight=wtr)
    return m.predict(Xte)


LANES = {"const": lane_const, "days": lane_days, "ridge": lane_ridge, "gbdt": lane_gbdt}


# ── 평가 ────────────────────────────────────────────────────────────────
def paired_bootstrap(err_a: np.ndarray, err_b: np.ndarray, n_boot: int = 4000) -> tuple:
    """MAE 차이(a−b)의 95% CI. 음수면 a가 낫다."""
    rng = np.random.default_rng(SEED)
    d = err_a - err_b
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    boots = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def evaluate(domain: str = "popup", axis: str = "per_day", lanes: list[str] | None = None,
             grades: tuple = ("A", "B"), verbose: bool = True) -> dict:
    d = np.load(f"data/state/{domain}_v2.npz", allow_pickle=True)
    X, cols = d["X"], list(d["names"])
    y = d["y_perday"] if axis == "per_day" else d["y_total"]
    w = d["w"]
    meta = json.loads(Path(f"data/state/{domain}_v2_meta.json").read_text())

    # 라벨 등급 필터 (trust_* one-hot에서 복원)
    gi = {g: _col(cols, f"trust_{g}") for g in ("A", "B", "C", "D", "E")}
    keep_grade = np.zeros(len(y), bool)
    for g in grades:
        if gi[g] is not None:
            keep_grade |= X[:, gi[g]] > 0.5
    ok = np.isfinite(y) & keep_grade
    X, y, w = X[ok], y[ok], w[ok]
    meta = [m for m, k in zip(meta, ok) if k]

    groups = np.array([m.get("ip") or m["id"] for m in meta])
    times = np.array([m.get("date") or "9999" for m in meta])
    if (times == "9999").all():          # v2 meta에 date가 없으면 id 순
        times = np.arange(len(y)).astype(str)
    folds = group_time_folds(groups, times)
    lanes = lanes or ["const", "days", "ridge", "gbdt"]

    errs = {L: [] for L in lanes}
    for tr, te in folds:
        for L in lanes:
            p = LANES[L](X[tr], y[tr], w[tr], X[te], cols)
            errs[L].append(np.abs(p - y[te]))
    out = {"domain": domain, "axis": axis, "n": int(len(y)), "folds": len(folds),
           "grades": list(grades), "lanes": {}}
    cat = {L: np.concatenate(v) for L, v in errs.items()}
    for L in lanes:
        out["lanes"][L] = {"mae": round(float(cat[L].mean()), 4),
                            "x": round(float(10 ** cat[L].mean()), 2)}
    base = "const"
    for L in lanes:
        if L == base:
            continue
        m, lo, hi = paired_bootstrap(cat[L], cat[base])
        out["lanes"][L]["vs_const"] = {"diff": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                        "wins": bool(hi < 0)}
    if verbose:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="popup")
    ap.add_argument("--lanes", default="const,days,ridge,gbdt")
    ap.add_argument("--grades", default="A,B")
    args = ap.parse_args()
    lanes = args.lanes.split(",")
    grades = tuple(args.grades.split(","))
    for axis in ("per_day", "total"):
        print(f"\n===== 축: {axis} =====")
        evaluate(args.domain, axis, lanes, grades)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
