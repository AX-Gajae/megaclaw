"""앵커된 5슬롯 구조 — 노트 5의 설계 주장을 실제로 시험한다.

노트 5의 결론: n=75에서 공유 축을 **데이터로 발견하는 것은 불가능**하다.
같은 절차가 폴드마다 다른 답을 내고, 노트 4가 해롭다고 지목한 속성을 전 폴드에서
고른다. 따라서 축은 학습 대상이 아니라 **아키텍처의 고정 구조**여야 한다.

이 모듈은 그 주장을 반증 가능한 형태로 만든다. 네 개의 구조를 같은 폴드에서 비교한다.

    A 상수            모델-프리 하한
    B 자유 잠재 8차원   기존 encoder.py 구조 — 축을 학습이 정한다
    C 병목 5차원       병목만 좁힘, 의미 앵커 없음 (앵커의 효과를 분리하는 절제)
    D 앵커된 5슬롯     슬롯이 다섯 축(타깃 폭·매장 노출도·입장 허들·미디어 투입·굿즈 규모)을
                      맞히도록 보조 손실을 건다 — 축이 무엇인지 데이터가 정하지 못한다

C와 D의 차이가 곧 '앵커'의 값이다. 둘 다 병목이 5이므로 용량은 같다.
D가 C를 못 이기면 노트 5의 설계 주장은 근거를 잃는다 — 그때 남는 것은
"5차원이면 충분하다"일 뿐 "그 5차원이어야 한다"가 아니다.

사용:
  python3 -m state.slots            # 팝업 단독 4구조 비교
  python3 -m state.slots --transfer # 아이돌 사전학습 후 전이까지
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .evaluate import group_time_folds, paired_bootstrap

SEED = 20260728

# 노트 4/5가 남긴 다섯 축. 순서가 슬롯 번호다.
AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
N_SLOT = len(AXES)


# ── 데이터 ─────────────────────────────────────────────────────────────
def load_popup(grades=("A", "B"), narrow: bool = True):
    """노트 4·5와 같은 풀. 실제 계수만, 스코프 검증된 것만."""
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    X, cols, y, w = d["X"], [str(c) for c in d["names"]], d["y_perday"], d["w"]
    meta = json.loads(Path("data/state/popup_v2_meta.json").read_text())

    gi = {g: (cols.index(f"trust_{g}") if f"trust_{g}" in cols else None)
          for g in ("A", "B", "C", "D", "E")}
    keep = np.zeros(len(y), bool)
    for g in grades:
        if gi[g] is not None:
            keep |= X[:, gi[g]] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    keep &= np.array([m.get("counting") in ("entry", "participation") for m in meta])

    X, y, w = X[keep], y[keep], w[keep]
    meta = [m for m, k in zip(meta, keep) if k]

    # 슬롯 앵커 타깃 — 0~4 서수를 0~1로. mask=0이면 손실에서 제외한다.
    A = np.zeros((len(y), N_SLOT), np.float32)
    M = np.zeros((len(y), N_SLOT), np.float32)
    for j, a in enumerate(AXES):
        ci, mi = cols.index(f"t1o_{a}"), cols.index(f"t1o_{a}_mask")
        A[:, j] = X[:, ci] / 4.0
        M[:, j] = X[:, mi]

    # 인코더 입력은 앵커 컬럼을 뺀다. 그러지 않으면 D가 정답을 베낀다.
    # 그리고 122개 전부를 주면 n=56 학습 폴드에서 잡음이 지배해 어떤 구조도 검정력이 없다
    # (실측: CI ±0.11). 사전 관측 가능한 물리·달력·비앵커 속성만 남긴다.
    drop = {f"t1o_{a}" for a in AXES} | {f"t1o_{a}_mask" for a in AXES}
    if narrow:
        pick = [c for c in cols
                if c not in drop
                and (c.startswith(("t1o_", "t1_", "comp_", "cal_"))
                     or c in ("days", "days_mask", "days_from_doc", "days_from_doc_mask",
                              "weekend_share", "weekend_share_mask",
                              "holiday_days", "holiday_days_mask",
                              "venue_tier", "venue_tier_mask",
                              "store_count", "store_count_mask",
                              "area_pyeong", "area_pyeong_mask",
                              "is_host", "is_host_mask", "is_market", "is_market_mask",
                              "cap_bound", "cap_bound_mask",
                              "total_capacity", "total_capacity_mask",
                              "cap_per_day", "cap_per_day_mask"))]
    else:
        pick = [c for c in cols if c not in drop]
    keep_c = [cols.index(c) for c in pick]
    Xin = X[:, keep_c]
    # 폴드 밖 정보 누출을 피하려 표준화는 학습 폴드에서만 한다 — 여기선 원본을 넘긴다.
    groups = np.array([m.get("ip") or m["id"] for m in meta])
    times = np.array([m.get("date") or "9999" for m in meta])
    return Xin, y.astype(np.float32), w.astype(np.float32), A, M, groups, times, [cols[i] for i in keep_c]


# ── 구조 ───────────────────────────────────────────────────────────────
class Encoder(nn.Module):
    def __init__(self, in_dim: int, latent: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 32), nn.ReLU(), nn.Dropout(0.15),
            nn.Linear(32, latent), nn.Sigmoid())   # 시그모이드 — 앵커가 0~1이므로 눈금을 맞춘다

    def forward(self, x):
        return self.net(x)


class Head(nn.Module):
    def __init__(self, latent: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, z):
        return self.net(z).squeeze(1)


def fit_predict(Xtr, ytr, wtr, Atr, Mtr, Xte, latent: int, anchor: float,
                epochs: int = 600, seed: int = SEED) -> np.ndarray:
    """anchor>0 이면 슬롯이 다섯 축을 맞히도록 보조 손실을 건다."""
    torch.manual_seed(seed)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32)
    xe = torch.tensor((Xte - mu) / sd, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.float32)
    wt = torch.tensor(wtr, dtype=torch.float32)
    at = torch.tensor(Atr, dtype=torch.float32)
    mt = torch.tensor(Mtr, dtype=torch.float32)

    enc, head = Encoder(xt.shape[1], latent), Head(latent)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()),
                           lr=3e-3, weight_decay=1e-3)
    for _ in range(epochs):
        opt.zero_grad()
        z = enc(xt)
        loss = (wt * (head(z) - yt) ** 2).mean()
        if anchor > 0:
            n = mt.sum().clamp(min=1.0)
            loss = loss + anchor * ((mt * (z[:, :N_SLOT] - at) ** 2).sum() / n)
        loss.backward()
        opt.step()
    enc.eval(); head.eval()
    with torch.no_grad():
        return head(enc(xe)).numpy()


# ── 실험 ───────────────────────────────────────────────────────────────
ARMS = [("자유 잠재 8차원", 8, 0.0),
        ("병목 5차원 (앵커 없음)", N_SLOT, 0.0),
        ("앵커된 5슬롯", N_SLOT, 1.0),
        ("앵커된 5슬롯 (강)", N_SLOT, 4.0)]


def run(n_seed: int = 5, verbose: bool = True, narrow: bool = True) -> dict:
    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    folds = group_time_folds(groups, times)
    if verbose:
        print(f"풀 n={len(y)}  피처={X.shape[1]}  폴드={len(folds)}  "
              f"앵커 태깅률={M.mean():.2f}")

    err_const, err_arm = [], {a[0]: [] for a in ARMS}
    for tr, te in folds:
        err_const.append(np.abs(np.median(y[tr]) - y[te]))
        for name, lat, anc in ARMS:
            ps = [fit_predict(X[tr], y[tr], w[tr], A[tr], M[tr], X[te], lat, anc,
                              seed=SEED + s) for s in range(n_seed)]
            err_arm[name].append(np.abs(np.mean(ps, axis=0) - y[te]))

    ec = np.concatenate(err_const)
    out = {"n": int(len(y)), "folds": len(folds), "seeds": n_seed,
           "n_feat": int(X.shape[1]), "narrow": narrow,
           "const_mae": round(float(ec.mean()), 4), "arms": {}}
    for name, lat, anc in ARMS:
        ea = np.concatenate(err_arm[name])
        m, lo, hi = paired_bootstrap(ea, ec)
        out["arms"][name] = {"latent": lat, "anchor": anc,
                             "mae": round(float(ea.mean()), 4),
                             "diff": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
                             "wins": bool(hi < 0)}
    # 앵커의 순효과 — 같은 용량(5)에서 앵커 유무 직접 비교
    e_no = np.concatenate(err_arm["병목 5차원 (앵커 없음)"])
    e_an = np.concatenate(err_arm["앵커된 5슬롯"])
    m, lo, hi = paired_bootstrap(e_an, e_no)
    out["anchor_effect"] = {"diff": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
                            "wins": bool(hi < 0)}
    if verbose:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    Path("data/state/slots_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--wide", action="store_true")
    a = ap.parse_args()
    run(n_seed=a.seeds, narrow=not a.wide)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ── 용량-반응 ───────────────────────────────────────────────────────────
def sweep(levels=(0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0), n_seed: int = 10,
          narrow: bool = True) -> dict:
    """앵커 강도를 쓸어 단조성을 본다.

    단일 비교는 n=75에서 검정력이 없다(CI ±0.10). 그러나 앵커 강도가 커질수록
    오차가 단조로 줄어든다면, 그것은 우연으로 설명하기 훨씬 어렵다 —
    잡음이라면 강도와 무관해야 한다."""
    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    folds = group_time_folds(groups, times)
    print(f"용량-반응 — n={len(y)} 피처={X.shape[1]} 폴드={len(folds)} 시드={n_seed}")

    err = {L: [] for L in levels}
    ec = []
    for tr, te in folds:
        ec.append(np.abs(np.median(y[tr]) - y[te]))
        for L in levels:
            ps = [fit_predict(X[tr], y[tr], w[tr], A[tr], M[tr], X[te], N_SLOT, L,
                              seed=SEED + s) for s in range(n_seed)]
            err[L].append(np.abs(np.mean(ps, axis=0) - y[te]))
    ec = np.concatenate(ec)
    base = np.concatenate(err[0.0])
    rows = []
    for L in levels:
        e = np.concatenate(err[L])
        m, lo, hi = paired_bootstrap(e, ec)
        m2, lo2, hi2 = paired_bootstrap(e, base)
        rows.append({"anchor": L, "mae": round(float(e.mean()), 4),
                     "vs_const": {"diff": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                  "wins": bool(hi < 0)},
                     "vs_noanchor": {"diff": round(m2, 4), "ci95": [round(lo2, 4), round(hi2, 4)],
                                     "wins": bool(hi2 < 0)}})
    # 단조성 — 강도 순위와 MAE 순위의 스피어만 상관
    from scipy.stats import spearmanr
    rho, p = spearmanr([r["anchor"] for r in rows], [r["mae"] for r in rows])
    out = {"n": int(len(y)), "n_feat": int(X.shape[1]), "seeds": n_seed,
           "const_mae": round(float(ec.mean()), 4), "levels": rows,
           "monotonic": {"spearman": round(float(rho), 3), "p": round(float(p), 4)}}
    Path("data/state/slots_sweep.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ── 반복 분할 ───────────────────────────────────────────────────────────
def repeat_anchor(reps: int = 20, anchor: float = 16.0, n_seed: int = 3,
                  narrow: bool = True) -> dict:
    """IP 무작위 5폴드를 reps회 반복해 앵커 효과의 안정성을 본다.

    시간순 4폴드는 검정 표본이 얇아 CI가 ±0.10이다 — 어떤 구조도 유의해질 수 없다.
    노트 5에서 쓴 것과 같은 완화된 프로토콜로 '효과가 방향을 유지하는가'를 본다.
    미래 정보를 쓰므로 실전 추정치가 아니라 안정성 판정용이다."""
    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    uniq = np.unique(groups)
    print(f"반복 앵커 검정 — n={len(y)} IP={len(uniq)} 반복={reps} 앵커={anchor}")

    d_const_no, d_const_an, d_anchor = [], [], []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        bucket = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([bucket[g] for g in groups])
        e_c, e_no, e_an = [], [], []
        for k in range(5):
            te = np.where(gb == k)[0]
            tr = np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            e_c.append(np.abs(np.median(y[tr]) - y[te]))
            for anc, sink in ((0.0, e_no), (anchor, e_an)):
                ps = [fit_predict(X[tr], y[tr], w[tr], A[tr], M[tr], X[te], N_SLOT, anc,
                                  seed=SEED + 100 * r + s) for s in range(n_seed)]
                sink.append(np.abs(np.mean(ps, axis=0) - y[te]))
        c, no, an = (np.concatenate(v).mean() for v in (e_c, e_no, e_an))
        d_const_no.append(no - c); d_const_an.append(an - c); d_anchor.append(an - no)
        print(f"  반복 {r+1:2d}/{reps}  무앵커 Δ{no-c:+.4f}   앵커 Δ{an-c:+.4f}   "
              f"앵커효과 {an-no:+.4f}")

    def sm(v):
        v = np.array(v)
        return {"median": round(float(np.median(v)), 4), "mean": round(float(v.mean()), 4),
                "sd": round(float(v.std()), 4), "win_rate": round(float((v < 0).mean()), 3)}
    out = {"n": int(len(y)), "reps": reps, "anchor": anchor, "seeds": n_seed,
           "무앵커_vs_상수": sm(d_const_no), "앵커_vs_상수": sm(d_const_an),
           "앵커효과": sm(d_anchor)}
    Path("data/state/slots_repeat.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ── 앵커를 GBDT로 이식 ──────────────────────────────────────────────────
def two_stage(reps: int = 20, narrow: bool = True) -> dict:
    """2단 GBDT — 앵커 발상을 n=75에서 실제로 작동하는 모델류로 옮긴다.

    신경망은 앵커가 있어도 상수를 못 이긴다(승률 25%). 그러나 앵커 자체는
    85%에서 이득을 냈다. 그렇다면 이득의 원인인 '다섯 축을 거쳐 가는 구조'만
    떼어 GBDT에 심는다.

      1단: 문서 피처 → 다섯 축 각각을 예측 (축마다 GBDT 하나)
      2단: 예측된 다섯 축 → 결과

    비교 대상:
      상수 / 문서 직행 GBDT / 2단 GBDT / 참 축 GBDT(상한, 태그를 그대로 씀)
    '참 축'은 사람이 매긴 태그를 쓰므로 실전 불가지만, 2단이 얼마나
    따라잡았는지의 눈금이 된다."""
    from sklearn.ensemble import HistGradientBoostingRegressor as G

    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    uniq = np.unique(groups)
    print(f"2단 GBDT — n={len(y)} IP={len(uniq)} 반복={reps}")

    def g(n):
        return G(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0,
                 min_samples_leaf=max(3, n // 10), random_state=SEED)

    arms = ["상수", "문서 직행", "2단 (예측 축)", "참 축 (상한)"]
    per_rep = {a: [] for a in arms}
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        bucket = {gg: perm[i] % 5 for i, gg in enumerate(uniq)}
        gb = np.array([bucket[gg] for gg in groups])
        e = {a: [] for a in arms}
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            e["상수"].append(np.abs(np.median(y[tr]) - y[te]))
            e["문서 직행"].append(np.abs(g(len(tr)).fit(X[tr], y[tr], sample_weight=w[tr])
                                       .predict(X[te]) - y[te]))
            # 1단 — 축마다 하나씩
            Ptr = np.zeros((len(tr), N_SLOT)); Pte = np.zeros((len(te), N_SLOT))
            for j in range(N_SLOT):
                m = M[tr, j] > 0.5
                if m.sum() < 10:
                    Ptr[:, j] = Pte[:, j] = 0.0
                    continue
                s = g(int(m.sum())).fit(X[tr][m], A[tr][m, j])
                Ptr[:, j], Pte[:, j] = s.predict(X[tr]), s.predict(X[te])
            e["2단 (예측 축)"].append(np.abs(g(len(tr)).fit(Ptr, y[tr], sample_weight=w[tr])
                                          .predict(Pte) - y[te]))
            e["참 축 (상한)"].append(np.abs(g(len(tr)).fit(A[tr], y[tr], sample_weight=w[tr])
                                         .predict(A[te]) - y[te]))
        for a in arms:
            per_rep[a].append(float(np.concatenate(e[a]).mean()))

    c = np.array(per_rep["상수"])
    out = {"n": int(len(y)), "reps": reps, "arms": {}}
    for a in arms:
        v = np.array(per_rep[a])
        d = v - c
        out["arms"][a] = {"mae_median": round(float(np.median(v)), 4),
                          "diff_median": round(float(np.median(d)), 4),
                          "diff_sd": round(float(d.std()), 4),
                          "win_rate": round(float((d < 0).mean()), 3)}
    Path("data/state/slots_2stage.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ── 선형 헤드 ───────────────────────────────────────────────────────────
class LinHead(nn.Module):
    """다섯 축의 신호가 선형이라면 헤드도 선형이어야 한다.

    근거(노트 7): 같은 다섯 축을 ridge에 넣으면 40회 반복 중 40회 상수를 이기고,
    GBDT에 넣으면 40회 중 6회만 이긴다. 트리가 n=75에서 선형 신호를 과적합으로
    날린다. 노트 6의 신경망 헤드는 MLP(비선형)였으므로 GBDT 쪽에 가까웠다."""

    def __init__(self, latent: int):
        super().__init__()
        self.net = nn.Linear(latent, 1)

    def forward(self, z):
        return self.net(z).squeeze(1)


def fit_predict_lin(Xtr, ytr, wtr, Atr, Mtr, Xte, latent: int, anchor: float,
                    epochs: int = 600, seed: int = SEED) -> np.ndarray:
    torch.manual_seed(seed)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32)
    xe = torch.tensor((Xte - mu) / sd, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.float32)
    wt = torch.tensor(wtr, dtype=torch.float32)
    at = torch.tensor(Atr, dtype=torch.float32)
    mt = torch.tensor(Mtr, dtype=torch.float32)
    enc, head = Encoder(xt.shape[1], latent), LinHead(latent)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()),
                           lr=3e-3, weight_decay=1e-3)
    for _ in range(epochs):
        opt.zero_grad()
        z = enc(xt)
        loss = (wt * (head(z) - yt) ** 2).mean()
        if anchor > 0:
            n = mt.sum().clamp(min=1.0)
            loss = loss + anchor * ((mt * (z[:, :N_SLOT] - at) ** 2).sum() / n)
        loss.backward()
        opt.step()
    enc.eval(); head.eval()
    with torch.no_grad():
        return head(enc(xe)).numpy()


def head_shootout(reps: int = 20, anchor: float = 16.0, n_seed: int = 3,
                  narrow: bool = True) -> dict:
    """MLP 헤드 vs 선형 헤드. 노트 7의 예측을 직접 시험한다."""
    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    uniq = np.unique(groups)
    print(f"헤드 대결 — n={len(y)} IP={len(uniq)} 반복={reps} 앵커={anchor}")
    arms = {"MLP 헤드 (노트 6)": fit_predict, "선형 헤드": fit_predict_lin}
    per = {k: [] for k in arms}
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        ec, ea = [], {k: [] for k in arms}
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            for nm, fn in arms.items():
                ps = [fn(X[tr], y[tr], w[tr], A[tr], M[tr], X[te], N_SLOT, anchor,
                         seed=SEED + 100 * r + s) for s in range(n_seed)]
                ea[nm].append(np.abs(np.mean(ps, axis=0) - y[te]))
        c = np.concatenate(ec).mean()
        for nm in arms:
            per[nm].append(float(np.concatenate(ea[nm]).mean() - c))
        print(f"  반복 {r+1:2d}/{reps}  " +
              "  ".join(f"{nm} {per[nm][-1]:+.4f}" for nm in arms))
    out = {"n": int(len(y)), "reps": reps, "anchor": anchor, "arms": {}}
    for nm, v in per.items():
        v = np.array(v)
        out["arms"][nm] = {"median": round(float(np.median(v)), 4),
                           "sd": round(float(v.std()), 4),
                           "win_rate": round(float((v < 0).mean()), 3)}
    Path("data/state/slots_head.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ── 전면 선형 사다리 ────────────────────────────────────────────────────
class LinEncoder(nn.Module):
    """선형 사상 + (선택) 시그모이드. 앵커 타깃이 0~1이라 눈금은 맞춰야 하지만,
    은닉층을 없애 용량을 ridge 수준으로 낮춘다."""

    def __init__(self, in_dim: int, latent: int, squash: bool = True):
        super().__init__()
        self.lin = nn.Linear(in_dim, latent)
        self.squash = squash

    def forward(self, x):
        z = self.lin(x)
        return torch.sigmoid(z) if self.squash else z


def fit_ladder(Xtr, ytr, wtr, Atr, Mtr, Xte, enc_kind: str, head_kind: str,
               anchor: float, epochs: int = 800, seed: int = SEED) -> np.ndarray:
    torch.manual_seed(seed)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    xt = torch.tensor((Xtr - mu) / sd, dtype=torch.float32)
    xe = torch.tensor((Xte - mu) / sd, dtype=torch.float32)
    yt = torch.tensor(ytr, dtype=torch.float32)
    wt = torch.tensor(wtr, dtype=torch.float32)
    at = torch.tensor(Atr, dtype=torch.float32)
    mt = torch.tensor(Mtr, dtype=torch.float32)
    enc = (Encoder(xt.shape[1], N_SLOT) if enc_kind == "mlp"
           else LinEncoder(xt.shape[1], N_SLOT, squash=(enc_kind == "lin")))
    head = Head(N_SLOT) if head_kind == "mlp" else LinHead(N_SLOT)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()),
                           lr=3e-3, weight_decay=1e-3)
    for _ in range(epochs):
        opt.zero_grad()
        z = enc(xt)
        loss = (wt * (head(z) - yt) ** 2).mean()
        if anchor > 0:
            n = mt.sum().clamp(min=1.0)
            loss = loss + anchor * ((mt * (z[:, :N_SLOT] - at) ** 2).sum() / n)
        loss.backward()
        opt.step()
    enc.eval(); head.eval()
    with torch.no_grad():
        return head(enc(xe)).numpy()


LADDER = [("MLP 인코더 + MLP 헤드", "mlp", "mlp"),
          ("MLP 인코더 + 선형 헤드", "mlp", "lin"),
          ("선형 인코더 + 선형 헤드", "lin", "lin"),
          ("선형(항등) + 선형 헤드", "raw", "lin")]


def ladder(reps: int = 20, anchor: float = 16.0, n_seed: int = 3,
           narrow: bool = True) -> dict:
    """비선형을 한 겹씩 벗기며 상수와의 거리를 잰다.

    노트 7의 논지가 맞다면 벗길수록 좋아져야 하고, 전면 선형에서
    ridge(참 축 직접 투입, Δ-0.0354)에 가까워져야 한다."""
    X, y, w, A, M, groups, times, cols = load_popup(narrow=narrow)
    uniq = np.unique(groups)
    print(f"선형 사다리 — n={len(y)} IP={len(uniq)} 반복={reps} 앵커={anchor}")
    per = {nm: [] for nm, _, _ in LADDER}
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {g: perm[i] % 5 for i, g in enumerate(uniq)}
        gb = np.array([b[g] for g in groups])
        ec, ea = [], {nm: [] for nm, _, _ in LADDER}
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            for nm, ek, hk in LADDER:
                ps = [fit_ladder(X[tr], y[tr], w[tr], A[tr], M[tr], X[te], ek, hk,
                                 anchor, seed=SEED + 100 * r + s) for s in range(n_seed)]
                ea[nm].append(np.abs(np.mean(ps, axis=0) - y[te]))
        c = np.concatenate(ec).mean()
        for nm, _, _ in LADDER:
            per[nm].append(float(np.concatenate(ea[nm]).mean() - c))
        print(f"  반복 {r+1:2d}/{reps}  " +
              "  ".join(f"{per[nm][-1]:+.4f}" for nm, _, _ in LADDER))
    out = {"n": int(len(y)), "reps": reps, "anchor": anchor, "arms": {}}
    for nm, v in per.items():
        v = np.array(v)
        out["arms"][nm] = {"median": round(float(np.median(v)), 4),
                           "sd": round(float(v.std()), 4),
                           "win_rate": round(float((v < 0).mean()), 3)}
    Path("data/state/slots_ladder.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out
