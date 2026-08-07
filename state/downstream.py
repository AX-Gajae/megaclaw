"""다운스트림 검정 — 비라벨로 배운 집단 상태가 라벨 관측을 설명하는가.

이것이 '집단 상태가 실재하는가'의 실증 검정이다. 회귀 성능 자체가 목적이 아니라,
**상태 블록을 넣고 뺐을 때 차이가 나는가**가 답이다.

시간 마스크: 각 레코드의 오픈 주차 **이전** 상태만 사용 (사전 관심 = 예측 시점 가용 정보).
평가: state/evaluate.py 와 같은 IP-그룹 ∩ 시간순 폴드, 폴드 내부 fit, 페어드 부트스트랩.

사용: python3 -m state.downstream
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .evaluate import group_time_folds, paired_bootstrap
from .fandom_state import DYN_KEYS

SEED = 20260727


def pre_open_state(series: list[dict], open_week: str, lag: int = 1) -> dict | None:
    """오픈 주차보다 lag주 이전의 마지막 상태 (누출 차단)."""
    prev = [s for s in series if s["week"] < open_week]
    if len(prev) < lag:
        return None
    return prev[-lag]


def build() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list]:
    links = json.loads(Path("data/state/record_store_link.json").read_text())
    states = json.loads(Path("data/state/fandom_states.json").read_text())
    emb = np.load("data/encoder/embeddings.npz", allow_pickle=True)
    E = emb["emb"]
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)

    X_state, X_base, y, groups, meta = [], [], [], [], []
    for rid, L in links.items():
        if not L.get("label") or not L.get("open_week"):
            continue
        st = states.get(L["store"])
        if not st:
            continue
        s = pre_open_state(st["series"], L["open_week"])
        if s is None:
            continue
        # 상태 블록: 동적 9 + 취향위치 상위 8차원(임베딩 축소) + 사전 관심 규모
        z = E[st["emb_idx"]][:8]
        X_state.append([s[k] for k in DYN_KEYS] + list(z) + [math.log1p(L["users"])])
        # 기저 블록: 상태 없이 쓸 수 있는 것 (도메인·규모 프록시)
        X_base.append([math.log1p(L["users"]), 1.0 if L["domain"] == "popup_market" else 0.0])
        y.append(math.log10(max(1, L["label"])))
        groups.append(L["store"])
        meta.append({"id": rid, "week": L["open_week"], "domain": L["domain"]})
    return (np.array(X_state, np.float32), np.array(X_base, np.float32),
            np.array(y, np.float32), np.array(groups), meta)


def rollout_features(links: dict, states: dict, trans, horizon: int = 4) -> dict:
    """world model 용법: 오픈 전 상태에서 전이함수를 h주 롤아웃해 '오픈 시점 예상 관심'을 만든다.
    18차원 원시 상태 대신 **3개 스칼라**로 압축 — 124표본에서 과적합을 피하는 유일한 길."""
    out = {}
    for rid, L in links.items():
        st = states.get(L.get("store") or "")
        if not st or not L.get("open_week"):
            continue
        s = pre_open_state(st["series"], L["open_week"])
        if s is None:
            continue
        cur = dict(s)
        traj = [cur["scale"]]
        for _ in range(horizon):
            x = np.array([[cur[k] for k in DYN_KEYS]], np.float32)
            nxt = float(trans.predict(x)[0])
            prev = cur["scale"]
            cur = dict(cur)
            cur["scale"] = nxt
            cur["scale4"] = 0.75 * cur["scale4"] + 0.25 * nxt
            cur["momentum"] = nxt - prev
            cur["age"] = math.log1p(math.expm1(cur["age"]) + 1)
            traj.append(nxt)
        out[rid] = [traj[-1],                       # 롤아웃 종점 = 오픈 시점 예상 관심
                     traj[-1] - traj[0],             # 롤아웃 순변화 = 예상 모멘텀
                     float(np.max(traj))]            # 궤적 피크
    return out


def run() -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor
    Xs, Xb, y, g, meta = build()
    n = len(y)
    if n < 40:
        return {"표본": n, "상태": "표본 부족 — 링크·상태 확보 필요"}
    times = np.array([m["week"] for m in meta])
    folds = group_time_folds(g, times, n_folds=5, min_train_frac=0.35)

    def lane(X):
        errs = []
        for tr, te in folds:
            m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.06, max_iter=250,
                                               l2_regularization=1.0, random_state=SEED)
            m.fit(X[tr], y[tr])
            errs.append(np.abs(m.predict(X[te]) - y[te]))
        return np.concatenate(errs)

    def const_lane():
        errs = []
        for tr, te in folds:
            errs.append(np.abs(np.median(y[tr]) - y[te]))
        return np.concatenate(errs)

    # 롤아웃 압축 레인 — 전이함수는 **폴드 밖 비라벨 데이터**로 학습되므로 누출 아님
    links = json.loads(Path("data/state/record_store_link.json").read_text())
    states = json.loads(Path("data/state/fandom_states.json").read_text())
    from .fandom_state import selfsup_table
    Xt, yt, _ = selfsup_table(states)
    trans = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.06, max_iter=300,
                                           random_state=SEED).fit(Xt, yt)
    roll = rollout_features(links, states, trans)
    ids = [m["id"] for m in meta]
    Xr = np.array([roll.get(i, [0.0, 0.0, 0.0]) for i in ids], np.float32)
    Xbr = np.hstack([Xb, Xr])

    e_const, e_base, e_state, e_roll = const_lane(), lane(Xb), lane(Xs), lane(Xbr)
    d1 = paired_bootstrap(e_state, e_const)
    d2 = paired_bootstrap(e_roll, e_const)
    d3 = paired_bootstrap(e_roll, e_base)
    out = {
        "표본": int(n), "폴드": len(folds),
        "상수 중앙값": round(float(e_const.mean()), 4),
        "기저(규모·도메인)": round(float(e_base.mean()), 4),
        f"원시상태 {Xs.shape[1]}차원": round(float(e_state.mean()), 4),
        "롤아웃압축 3차원": round(float(e_roll.mean()), 4),
        "원시상태 vs 상수": {"diff": round(d1[0], 4), "ci95": [round(d1[1], 4), round(d1[2], 4)],
                              "유의": bool(d1[2] < 0)},
        "롤아웃 vs 상수": {"diff": round(d2[0], 4), "ci95": [round(d2[1], 4), round(d2[2], 4)],
                            "유의": bool(d2[2] < 0)},
        "롤아웃 vs 기저": {"diff": round(d3[0], 4), "ci95": [round(d3[1], 4), round(d3[2], 4)],
                            "유의": bool(d3[2] < 0)},
    }
    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=1))
