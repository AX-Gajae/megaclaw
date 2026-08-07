"""집단 상태(Fandom State) — 소비자 집단의 상태 자체를 표현하는 층.

관점 교정(2026-07-27, 사용자): 목표는 '방문객 수 회귀'가 아니다. 방문객·초동·매출은
**하나의 집단 상태가 서로 다른 무대에서 발현된 관측 채널**일 뿐이고, 우리가 원하는 것은
그 근원 상태의 표현이다. 이 구분이 실질적인 이유:

    회귀로 보면      라벨 372건이 병목        → 어떤 아키텍처도 상수를 못 이김(실측)
    표현학습으로 보면 비라벨 10,182 스토어 ×
                     106주 시계열이 학습재료   → 라벨보다 3자릿수 많음 (JEPA 성립 조건)

상태의 조작적 정의 — 한 스토어(=IP의 한 무대) i의 시점 t 상태 s_i(t):

  ① 취향 위치   z_i ∈ R^64   co-visitation 임베딩. "누가 이걸 보는가"
  ② 규모        log1p(주간 조회 유저)          집단의 크기
  ③ 모멘텀      최근 4주 / 직전 4주 비율(log)  뜨거워지는가 식는가
  ④ 가속        모멘텀의 차분                   변곡
  ⑤ 수명단계    첫 관측 이후 경과 주 / 피크 후 경과
  ⑥ 응집도      이웃 top-k와의 코사인 평균      좁은 취향인가 대중적인가
  ⑦ 이웃 열기   취향 이웃들의 동시 활동 수준    그 클러스터 전체가 뜨거운가
  ⑧ 점유       이웃 대비 자기 몫                클러스터 내 지배력

①은 정적(누구), ②~⑧은 동적(지금 어떤가). 전부 **라벨 없이** 계산된다.

자기지도 목적: s_i(t) → 다음 주 관측 예측.
  이것이 곧 world model의 전이함수 학습이며, 여기서 얻은 표현이 다운스트림
  (팝업 방문 / 아이돌 초동)으로 전이되는지가 '상태가 실재하는가'의 검정이다.

사용: python3 -m state.fandom_state --build     # 상태 시계열 구축
      python3 -m state.fandom_state --selfsup   # 자기지도 전이함수 학습·평가
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ENC = Path("data/encoder")
OUT = Path("data/state")
K_NEIGH = 12


def load_weekly() -> tuple[dict, list[str]]:
    rows = list(csv.reader(gzip.open(ENC / "store_weekly.csv.gz", "rt")))
    by = defaultdict(dict)
    weeks = set()
    for path, wk, n in rows:
        by[path][wk] = int(n)
        weeks.add(wk)
    return by, sorted(weeks)


def load_emb() -> tuple[np.ndarray, dict]:
    d = np.load(ENC / "embeddings.npz", allow_pickle=True)
    emb = d["emb"]
    idx = {s: i for i, s in enumerate(d["stores"])}
    return emb, idx


def build_states() -> dict:
    """스토어 × 주차 상태 텐서. 비라벨 — 전량 계산."""
    weekly, weeks = load_weekly()
    emb, idx = load_emb()
    wpos = {w: i for i, w in enumerate(weeks)}

    # 이웃 사전 (임베딩 코사인 top-k) — 정적
    E = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    stores = [s for s in weekly if s in idx]
    S = np.array([idx[s] for s in stores])
    sim = E[S] @ E[S].T
    np.fill_diagonal(sim, -1)
    topk = np.argpartition(-sim, K_NEIGH, axis=1)[:, :K_NEIGH]
    coh = np.take_along_axis(sim, topk, axis=1).mean(1)      # ⑥ 응집도

    # 주간 행렬
    W = np.zeros((len(stores), len(weeks)), dtype=np.float32)
    for i, s in enumerate(stores):
        for wk, n in weekly[s].items():
            W[i, wpos[wk]] = n

    logW = np.log1p(W)
    # 이웃 활동 (⑦) — 각 스토어의 top-k 이웃 주간 합
    NB = np.zeros_like(logW)
    for i in range(len(stores)):
        NB[i] = logW[topk[i]].mean(0)

    rec = {}
    for i, s in enumerate(stores):
        obs = np.nonzero(W[i])[0]
        if len(obs) < 3:
            continue
        first, last = obs[0], obs[-1]
        peak = int(np.argmax(W[i]))
        series = []
        for t in range(first, min(last + 1, len(weeks))):
            cur4 = logW[i, max(0, t - 3):t + 1].mean()
            prev4 = logW[i, max(0, t - 7):max(0, t - 3)].mean() if t >= 4 else 0.0
            prev8 = logW[i, max(0, t - 11):max(0, t - 7)].mean() if t >= 8 else 0.0
            mom = cur4 - prev4
            acc = mom - (prev4 - prev8)
            series.append({
                "week": weeks[t],
                "scale": float(logW[i, t]),          # ②
                "scale4": float(cur4),
                "momentum": float(mom),              # ③
                "accel": float(acc),                 # ④
                "age": float(np.log1p(t - first)),   # ⑤
                "post_peak": float(np.log1p(max(0, t - peak))),
                "coherence": float(coh[i]),          # ⑥
                "nbr_heat": float(NB[i, t]),         # ⑦
                "share": float(logW[i, t] - NB[i, t]),  # ⑧
            })
        rec[s] = {"store": s, "emb_idx": int(idx[s]), "first": weeks[first],
                   "total": float(W[i].sum()), "series": series}
    return rec


DYN_KEYS = ["scale", "scale4", "momentum", "accel", "age", "post_peak",
            "coherence", "nbr_heat", "share"]


def selfsup_table(states: dict, horizon: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """자기지도: 상태 s(t) → 다음 주 규모 s.scale(t+h). world model 전이함수."""
    X, y, g = [], [], []
    for si, (s, r) in enumerate(states.items()):
        ser = r["series"]
        for t in range(len(ser) - horizon):
            X.append([ser[t][k] for k in DYN_KEYS])
            y.append(ser[t + horizon]["scale"])
            g.append(si)
    return np.array(X, np.float32), np.array(y, np.float32), np.array(g)


def run_selfsup(states: dict) -> dict:
    """전이함수를 학습하고, 상태가 미래를 실제로 설명하는지 측정."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold
    X, y, g = selfsup_table(states)
    out = {"표본": int(len(y)), "스토어": int(len(set(g)))}
    gkf = GroupKFold(n_splits=5)
    maes, base = [], []
    for tr, te in gkf.split(X, y, groups=g):
        m = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.06, max_iter=300,
                                           random_state=20260727).fit(X[tr], y[tr])
        maes.append(np.abs(m.predict(X[te]) - y[te]).mean())
        base.append(np.abs(X[te][:, 0] - y[te]).mean())     # 지속성(persistence) 하한
    out["전이함수 MAE"] = round(float(np.mean(maes)), 4)
    out["지속성 하한 MAE"] = round(float(np.mean(base)), 4)
    out["개선"] = round(float(np.mean(base) - np.mean(maes)), 4)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--selfsup", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fandom_states.json"
    if args.build or not p.exists():
        st = build_states()
        p.write_text(json.dumps(st, ensure_ascii=False))
        n_pts = sum(len(v["series"]) for v in st.values())
        print(json.dumps({"스토어": len(st), "상태 관측점": n_pts,
                           "저장": str(p)}, ensure_ascii=False))
    if args.selfsup:
        st = json.loads(p.read_text())
        print(json.dumps(run_selfsup(st), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
