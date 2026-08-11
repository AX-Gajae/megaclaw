# -*- coding: utf-8 -*-
"""팔 925-ㄱㄱ — **빈틈의 이름을 확정한다.** 절제 넷 × 세계 둘 · 관문의 검정력 · 구간 덮음.

사전등록: `docs/prereg_925_gapsplit.md` (이슈 **#177** · **#178**).

🔴 이 모듈이 지키는 것
  · `state/interval918.py` 와 `state/perm922.py` 를 **한 줄도 안 고친다**. 읽어 온다.
  · N2 를 다시 구현하되(항등 결함을 심을 인자가 필요해서다 · 티처 #73 M1)
    **`perm922.null_n2_gap_order` 와 비트로 같은 날짜를 내는지 W1b 에서 확인**한다.
  · 🔴 **관문마다 「도달 가능 폭 ÷ 문턱」을 신고하고, 1 미만이면 「검정력 0」을 자동으로 찍는다**(#178).
  · 분모 딱지: 사건 ≠ 간격 ≠ 격자 ≠ 홀드아웃 간격 ≠ prevmed 결측 행(조항 60).
"""
from __future__ import annotations

import hashlib

import numpy as np

from state.interval918 import CELL_MIN, _bin

# ─────────────────────────────────────────────── §3 절제의 정의 (사전등록에 박은 것)
PANELS = ("원판", "첫간격제외", "달력제거", "둘 다")
PANEL_DEF = {
    "원판": (False, False),          # (달력제거, 첫간격제외)
    "첫간격제외": (False, True),
    "달력제거": (True, False),
    "둘 다": (True, True),
}

#: §8 눈금 맞추기
CAL_SALT = "925cal"
CAL_PCT = 80
ALPHAS = tuple(round(0.050 + 0.0125 * k, 6) for k in range(25))   # 0.050 … 0.350
NOMINAL = 0.80
COV_TOL = 0.05


# ─────────────────────────────────────────────── N2 재구현 (항등 결함을 심을 수 있다)
def null_n2_plantable(first: np.ndarray, r: np.ndarray, seed: int = 922,
                      plant_identity: bool = False,
                      plant_break_multiset: bool = False):
    """N2 — 간격순서 순열. 🔴 `perm922.null_n2_gap_order` 와 **같은 난수 소비 순서**다.

    `plant_identity=True` 면 **순서를 하나도 안 섞는다**(심은 결함 W1a) — 난수는 그대로 소비해서
    「섞었는데 우연히 같다」와 「안 섞었다」가 코드 경로로만 갈리게 둔다.
    `plant_break_multiset=True` 면 간격 하나를 +1 한다(W9).
    """
    rng = np.random.default_rng(seed)
    G = first.shape[0]
    dates, mags = [], []
    moved = have = 0
    for g in range(G):
        idx = np.flatnonzero(first[g])
        m = r[g, idx].astype(float) if idx.size else np.zeros(0)
        if idx.size < 2:
            dates.append(idx)
            mags.append(m)
            continue
        have += 1
        gaps = np.diff(idx)
        perm = rng.permutation(gaps)          # 🔴 난수는 어느 판에서도 똑같이 소비한다
        if plant_identity:
            perm = gaps.copy()                # 심은 결함 — 순서를 안 바꾼다
        if plant_break_multiset and perm.size:
            perm = perm.copy()
            perm[0] = perm[0] + 1
        nd = np.r_[idx[0], idx[0] + np.cumsum(perm)]
        moved += int(not np.array_equal(perm, gaps))
        dates.append(nd.astype(idx.dtype))
        mags.append(m)
    return dates, mags, (moved / have if have else 0.0), have


def dates_bitwise_same(a, b) -> dict:
    """두 사건 날짜 목록이 **비트로** 같은가(W1b 음성 대조)."""
    if len(a) != len(b):
        return {"같다": False, "왜": f"격자 수가 다르다 {len(a)} vs {len(b)}"}
    bad = 0
    for x, y in zip(a, b):
        if not np.array_equal(np.asarray(x), np.asarray(y)):
            bad += 1
    return {"같다": bad == 0, "다른 격자 수": bad, "격자(분모)": len(a)}


# ─────────────────────────────────────────────── 관문의 검정력 신고 (#178)
def gate_report(name: str, *, axis: str, threshold: float,
                reach_lo: float, reach_hi: float, observed=None,
                note: str = "") -> dict:
    """🔴 「이 축의 도달 가능 폭 ÷ 문턱」을 신고한다. **1 미만이면 검정력 0 을 자동으로 찍는다**."""
    reach = float(abs(reach_hi - reach_lo))
    ratio = (reach / threshold) if threshold else float("inf")
    return {
        "관문": name, "축": axis,
        "🔴 도달 가능 폭": reach, "문턱": threshold,
        "🔴 비(도달 가능 폭 ÷ 문턱)": ratio,
        "🔴 검정력 0 인가(비 < 1 이면 자동)": bool(ratio < 1.0),
        "실측": observed, "비고": note,
    }


def gate_separation(name: str, real_b: dict, null_b: dict, *,
                    expected_gap: float | None = None, note: str = "") -> dict:
    """🔴 「두 구간이 갈리나」 형 관문의 검정력. 문턱은 0 이므로 **MDE 로 신고**한다.

    가를 수 있는 최소 빈틈 = 두 반폭의 합. 기대 효과가 그보다 작으면 **양성 방향으로 검정력 0**.
    """
    mde = float(real_b["🔴 반폭(=MDE 자리)"] + null_b["🔴 반폭(=MDE 자리)"])
    gap = float(real_b["lo"] - null_b["hi"])
    out = {
        "관문": name, "축": "빈틈 = 진짜 lo − 귀무 hi", "문턱": 0.0,
        "🔴 가를 수 있는 최소 빈틈(두 반폭의 합 · = MDE)": mde,
        "실측 빈틈(일)": gap,
        "진짜 반폭": float(real_b["🔴 반폭(=MDE 자리)"]),
        "귀무 반폭": float(null_b["🔴 반폭(=MDE 자리)"]),
        "🔴 안 겹치나(진짜 lo > 귀무 hi)": bool(real_b["lo"] > null_b["hi"]),
        "비고": note,
    }
    if expected_gap is not None:
        out["기대 빈틈(사전등록 §4)"] = float(expected_gap)
        out["🔴 비(|기대 빈틈| ÷ MDE)"] = abs(float(expected_gap)) / mde if mde else None
        out["🔴 검정력 0 인가(비 < 1 이면 자동)"] = bool(abs(float(expected_gap)) < mde)
    out["🔴 점추정 차(진짜 − 귀무)"] = float(real_b["점추정"] - null_b["점추정"])
    return out


# ─────────────────────────────────────────────── §7 새 바닥 팔 — 격자 정보를 넣는다
def predict_grid_aware(tab, mask, T):
    """`가′ 기후값+prevmed` — 조건부(주) 팔에서 **`mag` 만 뺀** 팔.

    2수준 셀 → 없으면 달력 셀 → 없으면 전체 중앙값. 🔴 `mag` 은 한 번도 안 본다.
    """
    dow = tab["dow"][mask].astype(int)
    qtr = tab["quarter"][mask].astype(int)
    if T.get("_plant_const_cal"):
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    prv = tab["prevmed"][mask]
    n = int(mask.sum())
    out = np.full(n, T["전체 중앙값"], float)
    back = {"2수준": 0, "달력": 0, "전체": 0}
    cuts_prv = T["prevmed 3분위 경계"]
    for i in range(n):
        v = T["2수준"].get((dow[i], qtr[i], _bin(prv[i], cuts_prv)))
        if v is not None:
            out[i] = v
            back["2수준"] += 1
            continue
        c = T["달력 셀"].get((dow[i], qtr[i]))
        if c is not None:
            out[i] = c
            back["달력"] += 1
        else:
            back["전체"] += 1
    return out, back


# ─────────────────────────────────────────────── §8 구간 — α 를 인자로 받는다
def _cell_ids(tab, mask, T):
    """행마다 (달력 셀 id, 조건부 셀 id) 를 정수로 매긴다. 🔴 `fit_tables` 와 같은 규칙."""
    dow = tab["dow"][mask].astype(int)
    qtr = tab["quarter"][mask].astype(int)
    if T.get("_plant_const_cal"):
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    bp = np.asarray([_bin(v, T["prevmed 3분위 경계"]) for v in tab["prevmed"][mask]], int)
    bm = np.asarray([_bin(v, T["mag 3분위 경계"]) for v in tab["mag"][mask]], int)
    cal = dow * 4 + qtr
    cond = (cal * 4 + (bp + 1)) * 4 + (bm + 1)
    return cal, cond


def build_intervals(tab, tr_mask, T, alpha: float):
    """학습 행에서 셀별 `[α, 1−α]` 분위 구간을 만든다. 반환은 **id 로 색인되는 배열**."""
    gap = tab["gap"][tr_mask].astype(float)
    cal, cond = _cell_ids(tab, tr_mask, T)
    lo_p, hi_p = 100.0 * alpha, 100.0 * (1.0 - alpha)
    res = {}
    for nm, ids, size in (("달력", cal, 28), ("조건부", cond, 28 * 16)):
        lo = np.full(size, np.nan)
        hi = np.full(size, np.nan)
        cnt = np.zeros(size, np.int64)
        order = np.argsort(ids, kind="stable")
        s = ids[order]
        g = gap[order]
        b = np.flatnonzero(np.r_[True, s[1:] != s[:-1]])
        for a, c in zip(b, np.r_[b[1:], s.size]):
            k = int(s[a])
            if c - a >= CELL_MIN:
                cnt[k] = c - a
                lo[k] = float(np.percentile(g[a:c], lo_p))
                hi[k] = float(np.percentile(g[a:c], hi_p))
        res[nm] = (lo, hi, cnt)
    res["전체"] = (float(np.percentile(gap, lo_p)), float(np.percentile(gap, hi_p)),
                 int(gap.size))
    res["α"] = alpha
    return res


def coverage_at(tab, mask, T, IV, which: str) -> dict:
    """홀드아웃(또는 눈금 확인) 덮음. 🔴 폭도 같이 낸다 — **넓어서 덮는 것은 이기는 게 아니다**."""
    gap = tab["gap"][mask].astype(float)
    cal, cond = _cell_ids(tab, mask, T)
    ids = cal if which == "달력" else cond
    lo, hi, cnt = IV["달력" if which == "달력" else "조건부"]
    L = lo[ids]
    H = hi[ids]
    fb = ~np.isfinite(L)
    L = np.where(fb, IV["전체"][0], L)
    H = np.where(fb, IV["전체"][1], H)
    miss = int((~np.isfinite(L)).sum())
    good = np.isfinite(L)
    hit = int(((L[good] <= gap[good]) & (gap[good] <= H[good])).sum())
    tot = int(good.sum())
    return {"α": IV["α"], "명목 덮음": 1.0 - 2.0 * IV["α"],
            "실측 덮음": (hit / tot) if tot else None,
            "덮인 행": hit, "행(분모)": tot, "🔴 구간을 못 만든 행": miss,
            "평균 폭(일)": float((H[good] - L[good]).mean()) if tot else None,
            "🔴 전체 폴백을 쓴 행": int(fb.sum()),
            "🔴 합 == 대상 전체(assert)": (tot + miss) == int(gap.size)}


def split_cal(train_grids, salt: str = CAL_SALT, pct: int = CAL_PCT):
    """🔴 **학습 격자만** 다시 80/20 으로 가른다. 홀드아웃은 한 톨도 안 들어간다."""
    a, b = set(), set()
    for g in sorted(train_grids):
        h = int(hashlib.sha256((salt + str(g)).encode()).hexdigest()[:8], 16)
        (a if (h % 100) < pct else b).add(g)
    return a, b
