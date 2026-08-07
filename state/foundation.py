"""파운데이션 월드모델 --- 세 도메인, 공유 슬롯 둘, 선형 공유 헤드.

열세 편의 노트가 좁혀 준 설계를 그대로 짓는다.

    팝업 원자료  ──► 팝업 인코더  ──┐
    아이돌 원자료 ─► 아이돌 인코더 ──┼──► [타깃 폭 · 굿즈 규모] ──► 선형 공유 헤드 ──► ŷ
    게임 원자료  ──► 게임 인코더  ──┘          ↑ 앵커 손실

설계 근거는 전부 앞선 노트에서 나왔다.

  · 슬롯이 둘인 이유 (노트 13) --- 다섯 축 중 세 도메인 모두에서 관측되는 것이
    타깃 폭과 굿즈 규모뿐이다. 공유 슬롯 수는 관측 가능성의 교집합이 정한다.
  · 슬롯을 학습으로 정하지 않는 이유 (노트 5) --- n이 작을 때 축을 데이터로
    발견하려 하면 폴드마다 다른 답이 나오고 이득이 사라진다.
  · 앵커를 거는 이유 (노트 6) --- 용량이 같은 병목끼리 비교했을 때 의미를 붙인
    쪽이 20회 중 17회 이겼다.
  · 인코더는 비선형, 헤드는 선형인 이유 (노트 7) --- 문서에서 축으로 가는 길은
    굽어 있고 축에서 결과로 나오는 길은 곧다. 헤드를 MLP로 두면 나빠지고
    인코더를 선형으로 두면 더 나빠진다.
  · 도메인 안에서 y를 표준화하고 탈추세하는 이유 (노트 11, 13) --- 라벨의
    물리량이 다르고 시간 추세의 방향도 도메인마다 반대다.

**핵심 검정은 도메인 하나 빼기(leave-one-domain-out)다.** 두 도메인으로 학습하고
나머지 하나를 예측하되 그 도메인의 라벨은 학습에 쓰지 않는다. 파운데이션 모델이
주장하는 바가 정확히 이것이다 --- 새 접점에 라벨이 없어도 예측할 수 있다.

비교 대상:
    상수            도메인 내 중앙값. 모델-프리 하한.
    도메인 내부 ridge 그 도메인 라벨을 다 본 경우. 상한.
    쌍 전이          노트 13의 최선 단일 출처.
    파운데이션       두 도메인 공동 학습 + 공유 헤드.

사용: python3 -m state.foundation
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.linear_model import Ridge

from .tri_domain import ALL5, detrend, load_all, prep, z

SEED = 20260728
# 슬롯 둘. 게임의 굿즈 규모는 한 번 누출로 비웠다가(DLC 수는 출시 후 누적)
# 누출 없는 대체 측정인 Steam 기능 수로 되살렸다 --- 노트 16.
SLOTS = ["target_breadth", "goods_scale"]


# ── 도메인별 원자료 ─────────────────────────────────────────────────────
def popup_raw():
    """팝업은 사전 관측 가능한 문서 피처를 쓴다(다섯 축 태그 자신은 제외)."""
    from .slots import load_popup
    X, y, w, A, M, g, t, cols = load_popup()
    idx = [ALL5.index(a) for a in SLOTS]
    keep = M[:, idx].all(1)
    tv = np.array([int(s[:4]) if s and s[:4].isdigit() else np.nan for s in t], float)
    return X[keep], A[keep][:, idx], y[keep], tv[keep]


def idol_raw():
    import glob
    ax = json.loads(Path("data/state/idol_axes.json").read_text())
    alb = json.loads(Path("data/state/idol_album_meta.json").read_text())
    recs = {}
    for f in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(f).read_text())
        recs[r["record_id"]] = r
    ids = [k for k, v in ax.items() if all(v["mask"][a] for a in SLOTS)]
    F, A, y, t = [], [], [], []
    for k in ids:
        r, v, am = recs.get(k, {}), ax[k], (alb.get(k) or {})
        F.append([r.get("member_count") or 0,
                  1.0 if r.get("survival_show") else 0.0,
                  1.0 if r.get("gender") == "girl" else 0.0,
                  1.0 if r.get("gender") == "coed" else 0.0,
                  1.0 if r.get("pre_debut_signals") else 0.0,
                  1.0 if r.get("is_group") else 0.0,
                  float(am.get("versions") or 1),
                  float(am.get("unit_price") or 0)])
        A.append([v["axes"][a] for a in SLOTS])
        y.append(v["y"])
        s = (v.get("debut_date") or "")[:4]
        t.append(int(s) if s.isdigit() else np.nan)
    return np.array(F, float), np.array(A, float), np.array(y, float), np.array(t, float)


def game_raw():
    from datetime import date
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    ids = [k for k, v in ax.items() if all(v["mask"][a] for a in SLOTS)]
    F, A, y, t = [], [], [], []
    asof = date(2026, 7, 28)
    for k in ids:
        r, v = rec.get(k, {}), ax[k]
        # 원자료에서도 DLC 수를 뺀다 --- 인코더가 누출 신호를 다시 주워 오면
        # 축을 비운 의미가 없다.
        F.append([float(r.get("n_lang") or 0), float(len(r.get("genres") or [])),
                  float(r.get("n_platform") or 0), float(r.get("n_category") or 0),
                  float(r.get("price_krw") or 0),
                  1.0 if r.get("is_free") else 0.0])
        A.append([v["axes"][a] for a in SLOTS])
        y.append(v["y"])
        try:
            d = (asof - date(*map(int, v["release_date"].split("-")))).days
            t.append(float(np.log10(max(d, 1))))
        except (ValueError, TypeError):
            t.append(np.nan)
    return np.array(F, float), np.array(A, float), np.array(y, float), np.array(t, float)


def domains():
    out = {}
    for nm, fn in (("팝업", popup_raw), ("아이돌", idol_raw), ("게임", game_raw)):
        F, A, y, t = fn()
        yy = z(detrend(y, t))                       # 도메인 안에서 탈추세 + 표준화
        Az = np.column_stack([z(detrend(A[:, j], t)) for j in range(A.shape[1])])
        # 앵커 타깃은 0~1로 눌러 시그모이드 출력과 눈금을 맞춘다. **도메인마다
        # min-max를 쓰면 안 된다** --- 극단값이 눈금을 정하므로 도메인 사이의
        # 축 눈금이 어긋난다. 실제로 그렇게 했더니 아이돌→팝업 전이가
        # -0.0467(노트 13)에서 -0.0064로 무너졌다. 모든 도메인에 **같은 함수**를
        # 써야 비교가 성립한다.
        An = 1.0 / (1.0 + np.exp(-Az))
        mu, sd = F.mean(0), F.std(0) + 1e-9
        out[nm] = {"F": (F - mu) / sd, "A": An, "y": yy, "n": len(yy)}
    return out


# ── 구조 ───────────────────────────────────────────────────────────────
class Enc(nn.Module):
    """도메인별 인코더. 노트 7 --- 문서에서 축으로 가는 길은 굽어 있다."""

    def __init__(self, d_in: int, n_slot: int = 2):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_in, 16), nn.ReLU(), nn.Dropout(0.15),
                                 nn.Linear(16, n_slot), nn.Sigmoid())

    def forward(self, x):
        return self.net(x)


class SharedHead(nn.Module):
    """공유 헤드. 노트 7 --- 축에서 결과로 나오는 길은 곧다. 선형이어야 한다."""

    def __init__(self, n_slot: int = 2):
        super().__init__()
        self.lin = nn.Linear(n_slot, 1)

    def forward(self, z_):
        return self.lin(z_).squeeze(1)


def fit(train: dict, anchor: float = 8.0, epochs: int = 1200, seed: int = SEED):
    """두 도메인 이상을 공동 학습한다. 헤드는 하나, 인코더는 도메인마다 하나."""
    torch.manual_seed(seed)
    encs = {k: Enc(v["F"].shape[1]) for k, v in train.items()}
    head = SharedHead()
    ps = list(head.parameters())
    for e in encs.values():
        ps += list(e.parameters())
    opt = torch.optim.Adam(ps, lr=3e-3, weight_decay=1e-3)
    T = {k: (torch.tensor(v["F"], dtype=torch.float32),
             torch.tensor(v["A"], dtype=torch.float32),
             torch.tensor(v["y"], dtype=torch.float32)) for k, v in train.items()}
    for _ in range(epochs):
        opt.zero_grad()
        loss = 0.0
        for k, (F, A, y) in T.items():
            s = encs[k](F)
            loss = loss + ((head(s) - y) ** 2).mean() + anchor * ((s - A) ** 2).mean()
        loss.backward()
        opt.step()
    for e in encs.values():
        e.eval()
    head.eval()
    return encs, head


def fit_new_encoder(head, tgt: dict, anchor: float = 8.0, epochs: int = 1200,
                    seed: int = SEED):
    """새 도메인의 인코더만 학습한다. **라벨은 쓰지 않고 앵커만 쓴다.**

    파운데이션 모델의 실제 사용 시나리오다 --- 새 접점에 결과 라벨은 없지만
    축은 잴 수 있다. 헤드는 얼린다."""
    torch.manual_seed(seed)
    enc = Enc(tgt["F"].shape[1])
    opt = torch.optim.Adam(enc.parameters(), lr=3e-3, weight_decay=1e-3)
    F = torch.tensor(tgt["F"], dtype=torch.float32)
    A = torch.tensor(tgt["A"], dtype=torch.float32)
    for _ in range(epochs):
        opt.zero_grad()
        ((enc(F) - A) ** 2).mean().backward()
        opt.step()
    enc.eval()
    with torch.no_grad():
        return head(enc(F)).numpy()


def run(anchor: float = 8.0, seeds: int = 5) -> dict:
    D = domains()
    print("파운데이션 월드모델 --- 슬롯 " + " · ".join(SLOTS))
    for k, v in D.items():
        print(f"  {k:<6} n={v['n']:>3}  원자료 {v['F'].shape[1]}개")

    out = {"slots": SLOTS, "n": {k: v["n"] for k, v in D.items()}, "결과": {}}
    print(f"\n{'대상':<7}{'상수':>7}{'내부 ridge':>12}{'평균 쌍전이':>12}{'파운데이션':>12}")
    for tgt in D:
        src = {k: v for k, v in D.items() if k != tgt}
        yt = D[tgt]["y"]
        base = float(np.abs(np.median(yt) - yt).mean())

        # 상한 --- 대상 라벨을 다 본 경우
        inn = float(np.abs(Ridge(alpha=1.0).fit(D[tgt]["A"], yt).predict(D[tgt]["A"]) - yt).mean())

        # 쌍 전이. **최선만 보고하면 신탁이다** --- 실전에서는 어느 출처가 나은지
        # 미리 알 수 없다. 최선(신탁)과 평균(실전)을 함께 낸다.
        pv = [float(np.abs(Ridge(alpha=1.0).fit(v["A"], v["y"]).predict(D[tgt]["A"]) - yt).mean())
              for v in src.values()]
        pair, pair_mean = min(pv), float(np.mean(pv))

        # 파운데이션 --- 두 도메인 공동 학습 후 대상 인코더만 앵커로 맞춘다
        preds = []
        for s in range(seeds):
            _, head = fit(src, anchor=anchor, seed=SEED + s)
            preds.append(fit_new_encoder(head, D[tgt], anchor=anchor, seed=SEED + s))
        fnd = float(np.abs(np.mean(preds, axis=0) - yt).mean())

        # 유의성 --- 출처 라벨을 섞으면 이 성적이 얼마나 자주 나오는가
        rng = np.random.default_rng(SEED)
        null = []
        for r in range(200):
            sh = {k: {**v, "y": v["y"][rng.permutation(len(v["y"]))]} for k, v in src.items()}
            _, h = fit(sh, anchor=anchor, epochs=400, seed=SEED + 500 + r)
            null.append(float(np.abs(fit_new_encoder(h, D[tgt], anchor=anchor,
                                                     epochs=400, seed=SEED + r) - yt).mean()))
        pval = float((np.array(null) <= fnd).mean())

        out["결과"][tgt] = {"const": round(base, 4), "inner_ridge": round(inn, 4),
                           "best_pair": round(pair, 4), "mean_pair": round(pair_mean, 4),
                           "foundation": round(fnd, 4),
                           "vs_const": round(fnd - base, 4),
                           "vs_mean_pair": round(fnd - pair_mean, 4), "p": round(pval, 4)}
        print(f"{tgt:<7}{base:>7.4f}{inn:>12.4f}{pair_mean:>12.4f}{fnd:>12.4f}"
              f"   Δ{fnd-base:+.4f}  p={pval:.3f}")

    Path("data/state/foundation.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
