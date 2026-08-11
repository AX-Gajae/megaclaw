# -*- coding: utf-8 -*-
"""노트 908-ㄷ — **도메인 가중을 손으로 안 적고 배우게 한다**(타 분야 방법론 이식).

사전등록: `docs/prereg_908c_pooling.md`(sha256 은 산출물에 박는다).
러너: `runners/nn908c_pooling.py` → `runners/out908c_pooling.json`.

🔴 **이 파일은 챔피언을 안 고친다.** `lab/forms.py` 의 `F18_bagboost` 를 **상속**해서
한 곳만 바꾼다. `POOL_MODE="off"` 면 아무것도 안 바꾸고 **비트 동일**이어야 한다 ---
그 사실 자체가 배선 검사 ①이다(노트 897 의 병: *"조각이 판에 안 닿는다"*).

## 어디를 바꾸나

챔피언에는 **이미 도메인 학습 가중이 있다** --- `lab/forms.py:916 TRAINW` 는
**손으로 적은 11칸 표**이고 `영화`가 없다. `:651` 의 `TRAINW.get(d, 0)` 때문에
없는 도메인은 `w=0` → `TRAINW_CLIP` 하한 **0.2**. 즉 판 가중 3위(0.10755)인 영화의
학습 행 481개가 **표에 이름이 없다는 이유로** 5배 깎여 있다.

여기서 바꾸는 것은 그 **한 벡터**뿐이다. 판의 채점 가중은 **안 만진다**
(노트 890 사전등록: *"자를 결과에 맞춰 고르는 죄"*).

## 팔 (POOL_MODE)

    off      챔피언 그대로. 기준선이자 배선 검사
    table    A1 --- TRAINW 를 오늘 유보 행 수 12칸으로 다시 읽는다(대조군)
    uncert   A2 --- Kendall+18: w_d ∝ 1/σ̂_d² (σ̂ 는 학습 내부 검증 잔차 SD)
    dro      A3 --- Sagawa+20: q_d ← q_d·exp(η·L̂_d) 를 세 번(L̂ = 1−ρ_d)
    shrink   A4 --- Efron–Morris 75: λ_d = n_d/(n_d+κ) · κ **하나**를 배운다
    stack    A5 --- Wolpert 92 / Jacobs+91: λ_d 열둘을 도메인마다 따로
    force    주입 --- `FORCE_W` 를 그대로 쓴다(위약 · 심은 결함 · DRO 안쪽 순환)

## 누출 방어는 **구조**다

`Formulation.fit(train)` 이 받는 `Data` 는 하네스가 이미 `yr < T` 로 자른 것이다
(`lab/harness.py:305`). **유보 행은 그 객체 안에 없다.** 그래도 단언한다 ---
`_assert_no_holdout` 이 `fit` 첫 줄에서 전 도메인 `max(yr) < 2025.0` 을 본다.
안쪽 검증은 학습을 **또 한 번** 시간으로 가른 것이다(`< 2024` / `2024~2025`).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

from .forms import REGISTRY, DirectPool  # noqa: F401  (DirectPool 은 문서용)
from .harness import Data

CHAMP = REGISTRY["F18_bagboost"]["cls"]

T_OUT = 2025.0          #: 유보 경계 --- 이 위는 fit 안에서 보면 안 된다
T_INNER = 2024.0        #: 안쪽 검증 경계(학습 안에서 다시 가른다)
MIN_VALID = 20          #: 안쪽 검증행이 이보다 적으면 **가중을 안 배운다**
LAM_GRID = tuple(round(x, 2) for x in np.arange(0.0, 1.0001, 0.1))
KAPPA_GRID = (1e9, 1e5, 2e4, 5e3, 2e3, 500.0, 100.0, 20.0, 1.0)
MODES = ("off", "table", "uncert", "dro", "shrink", "stack", "force")
WEIGHT_MODES = ("table", "uncert", "dro", "force")
PRED_MODES = ("shrink", "stack")


def _rho(p, y):
    """동률 평균 스피어만. 판 채점기(`state.rank_test.spearman`)와 같은 규약."""
    p = np.asarray(p, float); y = np.asarray(y, float)
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 3:
        return np.nan
    a, b = rankdata(p[ok]), rankdata(y[ok])
    a = a - a.mean(); b = b - b.mean()
    den = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / den) if den > 0 else np.nan


def _split_inner(train: Data):
    """학습을 다시 시간으로 가른다 --- 유보는 여기 없다(들어와도 안 쓴다)."""
    tr, va = {}, {}
    ytr, yva = {}, {}
    for d in train.dom:
        u = np.asarray(train.yr[d], float)
        a = np.isfinite(u) & (u < T_INNER)
        b = np.isfinite(u) & (u >= T_INNER) & (u < T_OUT)
        if a.sum() >= 15:
            tr[d] = train.slice(d, a); ytr[d] = u[a]
        if b.sum() >= MIN_VALID:
            va[d] = train.slice(d, b); yva[d] = u[b]
    return (Data(tr, train.names, ytr) if tr else None), va, yva


class Mixture(CHAMP):
    """챔피언 + **배우는 도메인 가중** 한 층."""

    name = "F18_mix908"
    idea = "도메인 가중을 손으로 안 적고 배운다 — MoE·스태킹·불확실도·축소·DRO"

    POOL_MODE = "off"
    FORCE_W: dict | None = None      #: force 모드 · 위약 · 심은 결함
    INNER_K = 4                      #: 안쪽 대리모형 자루 수(싸게)
    DRO_ETA = 2.0
    DRO_ROUNDS = 3
    PERM_SEED: int | None = None     #: 라벨 순열 selectivity --- **학습 라벨만** 섞는다
    LOCAL_ALPHA = 1.0                #: local 전문가 Ridge alpha
    LAM_OVERRIDE: dict | None = None #: 예측 층 위약 --- 배운 λ 를 흩어서 덮는다

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pool_report: dict = {}
        self.lam: dict = {}
        self.local: dict = {}
        self.learned_w: dict | None = None

    # ── 방어 ────────────────────────────────────────────────────────────
    @staticmethod
    def _assert_no_holdout(train: Data) -> dict:
        bad = {}
        for d in train.dom:
            u = np.asarray(train.yr[d], float)
            n = int(np.sum(np.isfinite(u) & (u >= T_OUT)))
            if n:
                bad[d] = n
        assert not bad, f"🔴 fit 이 유보 행을 봤다 --- {bad}"
        return {"유보 행이 fit 에 보이나": False,
                "본 최대 연도": {d: float(np.nanmax(np.asarray(train.yr[d], float)))
                              for d in sorted(train.dom)}}

    # ── 가중 정규화 ─────────────────────────────────────────────────────
    @staticmethod
    def _normalize(w: dict, ntr: dict) -> dict:
        """Σ nᵈ·w_d == Σ nᵈ (사전등록 §5 의 항등식). 양수만."""
        w = {d: max(float(v), 1e-6) for d, v in w.items()}
        num = sum(ntr[d] for d in ntr)
        den = sum(ntr[d] * w[d] for d in ntr)
        s = num / den
        out = {d: w[d] * s for d in ntr}
        chk = sum(ntr[d] * out[d] for d in ntr)
        assert abs(chk - num) < 1e-6 * max(1.0, num), "🔴 정규화 항등식 깨짐"
        return out

    # ── 안쪽 대리모형 ───────────────────────────────────────────────────
    def _surrogate(self, inner_tr: Data, w: dict | None):
        """싼 챔피언(자루 INNER_K). 가중을 주면 그 가중으로 적합한다."""
        m = Mixture(K=self.INNER_K, seed=self.seed)
        if w is None:
            m.POOL_MODE = "off"
        else:
            m.POOL_MODE = "force"
            m.FORCE_W = dict(w)
        m.fit(inner_tr)
        return m

    def _inner_scores(self, inner_tr: Data, va: dict, w: dict | None):
        """안쪽 검증에서 도메인별 ρ 와 잔차 SD. **유보는 안 본다.**"""
        m = self._surrogate(inner_tr, w)
        rho, sd, nva = {}, {}, {}
        for d, (A, M, y, t) in va.items():
            try:
                p = np.asarray(m.predict(d, A, M, t), float)
            except Exception:
                continue
            ok = np.isfinite(p) & np.isfinite(y)
            if ok.sum() < MIN_VALID:
                continue
            n = int(ok.sum())
            pr = rankdata(p[ok]) / n
            yr_ = rankdata(y[ok]) / n
            rho[d] = _rho(p[ok], y[ok])
            sd[d] = float(np.std(pr - yr_))
            nva[d] = n
        return rho, sd, nva, m

    # ── 학습 라벨 순열(선택성 검사 전용) ─────────────────────────────────
    def _permute_labels(self, train: Data) -> Data:
        rng = np.random.default_rng(int(self.PERM_SEED))
        dom = {}
        for d in train.dom:
            A, M, y, t = train.dom[d]
            y2 = np.asarray(y, float).copy()
            fin = np.where(np.isfinite(y2))[0]
            y2[fin] = y2[rng.permutation(fin)]
            dom[d] = (A, M, y2, t)
        return Data(dom, train.names, dict(train.yr))

    # ── 가중 학습 ───────────────────────────────────────────────────────
    def _learn(self, train: Data, ntr: dict) -> dict | None:
        mode = self.POOL_MODE
        rep = self.pool_report
        if mode == "force":
            w = {d: float(self.FORCE_W.get(d, 1.0)) for d in ntr}
            rep["출처"] = "FORCE_W 주입(위약 · 심은 결함 · DRO 안쪽)"
            return w
        if mode == "table":
            #: A1 --- 챔피언 공식 그대로, 표만 오늘 것으로. **유보의 y 는 안 본다.**
            #: 🔴 표를 안 넣으면 조용히 상수 가중이 된다 --- 그러면 A1 이 A0 도
            #: 아니고 상수 팔도 아닌 유령이 된다. 여기서 죽인다(조항 59).
            assert getattr(self, "TRAINW_TODAY", None), \
                "🔴 TRAINW_TODAY 가 비었다 --- 러너가 오늘 세어 넣어야 한다"
            tw = dict(self.TRAINW_TODAY)
            Ttr = sum(ntr.values()); Tte = sum(tw.get(d, 0) for d in ntr)
            w = {}
            for d in ntr:
                st = ntr[d] / max(1, Ttr)
                se = tw.get(d, 0) / max(1, Tte)
                raw = (se / st) if st > 0 else 1.0
                w[d] = min(max(raw, 0.2), 1.0)      # 챔피언과 같은 clip
            rep["출처"] = "오늘 유보 행 수 12칸(라벨 안 봄) · clip (0.2,1.0)"
            rep["표"] = tw
            return w

        # 라벨을 쓰는 팔들 --- 안쪽 분할이 필요하다
        src = self._permute_labels(train) if self.PERM_SEED is not None else train
        inner_tr, va, _ = _split_inner(src)
        rep["안쪽 학습 도메인"] = sorted(inner_tr.dom) if inner_tr else []
        rep["안쪽 검증 행"] = {d: int(len(va[d][2])) for d in sorted(va)}
        if inner_tr is None or len(inner_tr.dom) < 3 or not va:
            rep["실패"] = "안쪽 분할이 안 선다 --- 중립 가중"
            return {d: 1.0 for d in ntr}

        if mode == "uncert":
            rho, sd, nva, _m = self._inner_scores(inner_tr, va, None)
            rep["안쪽 ρ"] = {d: round(v, 5) for d, v in sorted(rho.items())}
            rep["σ̂(잔차 SD)"] = {d: round(v, 5) for d, v in sorted(sd.items())}
            if sd:
                lo, hi = min(sd.values()), max(sd.values())
                rep["σ̂ 최대/최소 비"] = round(hi / lo, 4) if lo > 0 else None
            w = {}
            for d in ntr:
                s = sd.get(d)
                w[d] = (1.0 / (s * s)) if (s and s > 0) else np.nan
            fin = [v for v in w.values() if np.isfinite(v)]
            med = float(np.median(fin)) if fin else 1.0
            w = {d: (v if np.isfinite(v) else med) for d, v in w.items()}
            rep["가중을 못 배운 도메인(안쪽 검증 부족 → 중앙값)"] = \
                [d for d in ntr if d not in sd]
            return w

        if mode == "dro":
            q = {d: 1.0 for d in ntr}
            hist = []
            for r in range(int(self.DRO_ROUNDS)):
                rho, sd, nva, _m = self._inner_scores(inner_tr, va, q)
                loss = {d: (1.0 - rho[d]) for d in rho}
                med = float(np.median(list(loss.values()))) if loss else 1.0
                q = {d: q[d] * float(np.exp(self.DRO_ETA * loss.get(d, med)))
                     for d in ntr}
                s = float(np.mean(list(q.values())))
                q = {d: v / s for d, v in q.items()}
                hist.append({"회차": r + 1,
                             "안쪽 ρ": {k: round(v, 5) for k, v in sorted(rho.items())},
                             "손실 1−ρ": {k: round(1 - v, 5) for k, v in sorted(rho.items())},
                             "q": {k: round(v, 5) for k, v in sorted(q.items())}})
            rep["DRO 회차"] = hist
            rep["η"] = self.DRO_ETA
            return q

        return None      # shrink · stack 은 예측 층이라 학습 가중을 안 바꾼다

    # ── 예측 층(A4·A5) ──────────────────────────────────────────────────
    def _fit_local_and_lambda(self, train: Data):
        from sklearn.linear_model import Ridge
        rep = self.pool_report
        capped = self._traincap(train)
        # local 전문가 --- 그 도메인 행만으로 Ridge. 설계행렬은 챔피언과 **같은 것**
        for d in self.doms:
            if d not in capped.dom:
                continue
            A, M, y, t = capped.dom[d]
            if len(y) < 40:
                continue
            X = self._design(d, A, M, t)
            self.local[d] = Ridge(alpha=self.LOCAL_ALPHA).fit(
                X, rankdata(y) / len(y))
        rep["local 전문가가 선 도메인"] = sorted(self.local)

        src = self._permute_labels(train) if self.PERM_SEED is not None else train
        inner_tr, va, _ = _split_inner(src)
        rep["안쪽 검증 행"] = {d: int(len(va[d][2])) for d in sorted(va)}
        if inner_tr is None or not va:
            rep["실패"] = "안쪽 분할이 안 선다 --- λ=0(완전 풀링)"
            self.lam = {d: 0.0 for d in self.doms}
            return
        inner = self._surrogate(inner_tr, None)
        inner_local = {}
        for d in inner_tr.dom:
            A, M, y, t = inner_tr.dom[d]
            if len(y) >= 40:
                inner_local[d] = Ridge(alpha=self.LOCAL_ALPHA).fit(
                    inner._design(d, A, M, t), rankdata(y) / len(y))

        # λ 격자에서 도메인별 ρ 를 잰다
        grid = {}
        nva = {}
        for d, (A, M, y, t) in va.items():
            if d not in inner_local:
                continue
            try:
                p = np.asarray(inner.predict(d, A, M, t), float)
                q = np.asarray(inner_local[d].predict(inner._design(d, A, M, t)), float)
            except Exception:
                continue
            ok = np.isfinite(p) & np.isfinite(q) & np.isfinite(y)
            if ok.sum() < MIN_VALID:
                continue
            n = int(ok.sum())
            pr = rankdata(p[ok]) / n
            qr = rankdata(q[ok]) / n
            yy = y[ok]
            grid[d] = {g: _rho((1 - g) * pr + g * qr, yy) for g in LAM_GRID}
            nva[d] = n
        rep["λ 격자(안쪽 검증 ρ)"] = {d: {str(g): round(v, 5)
                                     for g, v in sorted(grid[d].items())}
                                  for d in sorted(grid)}
        rep["λ 를 잴 수 있던 도메인"] = sorted(grid)
        rep["🔴 λ 를 못 배운 도메인(규칙상 λ=0)"] = \
            [d for d in self.doms if d not in grid]

        ntr_all = {d: len(capped.dom[d][2]) for d in self.doms if d in capped.dom}
        if self.POOL_MODE == "stack":
            self.lam = {d: (max(grid[d], key=lambda g: (grid[d][g]
                             if np.isfinite(grid[d][g]) else -9))
                            if d in grid else 0.0) for d in self.doms}
            rep["자유모수 수"] = len(grid)
        else:   # shrink --- κ 하나
            best, bk = -9e9, KAPPA_GRID[0]
            tbl = {}
            for k in KAPPA_GRID:
                tot = num = 0.0
                for d in grid:
                    lam = ntr_all.get(d, 0) / (ntr_all.get(d, 0) + k)
                    g0 = min(LAM_GRID, key=lambda g: abs(g - lam))
                    v = grid[d].get(g0, np.nan)
                    if np.isfinite(v):
                        num += v * nva[d]; tot += nva[d]
                obj = num / tot if tot else -9e9
                tbl[str(k)] = round(obj, 6)
                if obj > best:
                    best, bk = obj, k
            self.lam = {d: (ntr_all.get(d, 0) / (ntr_all.get(d, 0) + bk)
                            if d in grid else 0.0) for d in self.doms}
            rep["κ 격자(안쪽 판 대리)"] = tbl
            rep["고른 κ"] = bk
            rep["자유모수 수"] = 1
        rep["λ"] = {d: round(float(v), 5) for d, v in sorted(self.lam.items())}
        if self.LAM_OVERRIDE:
            #: 위약 --- **배운 값 집합은 그대로 두고 배정만 흩는다**
            rep["🔴 배운 λ(위약이 덮기 전)"] = dict(rep["λ"])
            self.lam = {d: float(self.LAM_OVERRIDE.get(d, 0.0)) for d in self.doms}
            rep["λ"] = {d: round(float(v), 5) for d, v in sorted(self.lam.items())}
            rep["위약"] = "λ 를 도메인에 무작위 재배정했다"

    # ── 본체 ────────────────────────────────────────────────────────────
    def fit(self, train: Data) -> None:
        assert self.POOL_MODE in MODES, f"모르는 POOL_MODE {self.POOL_MODE}"
        self.pool_report = {"POOL_MODE": self.POOL_MODE, "씨앗": self.seed,
                            "라벨 순열 씨앗": self.PERM_SEED}
        self.pool_report["누출 방어"] = self._assert_no_holdout(train)
        if self.POOL_MODE == "off":
            self.pool_report["바꾼 것"] = "없다 --- 챔피언 그대로(배선 검사 ①)"
            super().fit(train)
            return
        capped = self._traincap(train)
        ntr = {d: int(len(capped.dom[d][2])) for d in sorted(capped.dom)}
        self.pool_report["학습행(traincap 뒤)"] = ntr
        self.pool_report["학습행 합"] = int(sum(ntr.values()))
        w = self._learn(train, ntr) if self.POOL_MODE in WEIGHT_MODES else None
        if w is not None:
            w = self._normalize(w, ntr)
            self.learned_w = w
            self.TRAINW = {d: ntr[d] * w[d] for d in ntr}
            self.TRAINW_CLIP = (1e-9, 1e9)
            self.pool_report["학습 가중 w(정규화 뒤 · Σnw=Σn)"] = \
                {d: round(v, 6) for d, v in sorted(w.items())}
            self.pool_report["Σ nᵈ·w_d"] = float(sum(ntr[d] * w[d] for d in ntr))
            self.pool_report["Σ nᵈ"] = float(sum(ntr.values()))
            #: 🔴 **반올림해서 넣지 마라.** 합==1 단언이 반올림 오차로 깨진다
            #: (연기 시험에서 1.0000010000000001 이 나왔다). 표시용 반올림은
            #: 러너가 따로 한다.
            _den = sum(ntr[e] * w[e] for e in ntr)
            self.pool_report["가중 몫(합=1)"] = {
                d: float(ntr[d] * w[d] / _den) for d in sorted(ntr)}
        super().fit(train)
        if self.POOL_MODE in PRED_MODES:
            self._fit_local_and_lambda(train)

    def predict(self, d, A, M, t):
        p = super().predict(d, A, M, t)
        if self.POOL_MODE not in PRED_MODES:
            return p
        lam = float(self.lam.get(d, 0.0))
        if lam <= 0.0 or d not in self.local:
            return p
        try:
            q = np.asarray(self.local[d].predict(self._design(d, A, M, t)), float)
        except Exception:
            return p
        n = len(p)
        if n < 2 or not np.isfinite(q).all():
            return p
        return (1 - lam) * (rankdata(p) / n) + lam * (rankdata(q) / n)


#: A1 이 쓰는 표는 **러너가 오늘 세어서 넣는다**(손 전사 금지 · 조항 60).
#: 안 넣으면 챔피언의 은퇴한 11칸 표가 그대로 쓰여 A1 이 A0 이 된다 --- 그러면
#: 배선 검사가 그것을 잡아야 한다.
Mixture.TRAINW_TODAY = {}
