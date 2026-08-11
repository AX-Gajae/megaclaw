# -*- coding: utf-8 -*-
"""팔 922-ㅎ — **918 의 순열 바닥을 고친다.** 귀무 셋(N0·N1·N2)과 비교가능성 관문.

사전등록: `docs/prereg_922_permfix.md` (2026-08-11 17:22 KST · HEAD fffd4be42).

🔴 이 모듈이 지키는 것
  · `state/interval918.py` 를 **한 줄도 안 고친다**. 표·자·분할·τ 는 거기서 **읽어 온다**.
  · 사건은 (날짜, mag) **짝**으로 다룬다 — 918 은 mag 을 `r[g,tk]` 에서 다시 읽었고
    그래서 순열이 mag 을 조용히 바꿔 버렸다(이슈 #175).
  · 귀무마다 **「진짜와 같은 세계인가」를 먼저 잰다**(비교가능성 관문 · 사전등록 §3).
  · 분모 딱지: 사건 ≠ 간격 ≠ 격자 ≠ 홀드아웃 간격. 나란히 놓기 전에 확인한다(조항 60).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state.interval918 import permute_events  # noqa: E402  (읽기 전용으로 쓴다)

#: 사전등록 §3 — 결과를 보기 전에 박은 문턱
COMPARABLE_REL = 0.05        # 기후값 MAE 상대차 허용 문턱
HALFWIDTH_CAP = 0.7545204330866538   # 이보다 반폭이 크면 「0 을 문다」를 근거로 못 쓴다
STOP_COEF = 0.01             # 918 §2 정지 규칙 계수


# ─────────────────────────────────────────────── 사건 목록 (날짜, mag) 짝
def real_events(first: np.ndarray, r: np.ndarray):
    """진짜 세계의 사건. 반환 (dates[list of ndarray], mags[list of ndarray])."""
    G = first.shape[0]
    dates, mags = [], []
    for g in range(G):
        idx = np.flatnonzero(first[g])
        dates.append(idx)
        mags.append(r[g, idx].astype(float) if idx.size else np.zeros(0))
    return dates, mags


def null_n0_old(first: np.ndarray, r: np.ndarray, ok: np.ndarray, seed: int = 918):
    """N0 — **918 의 옛 귀무 그대로**(`r` 을 안 섞는다). 판정에 안 쓴다. 심은 결함이다.

    `state.interval918.permute_events` 를 그대로 불러 날짜를 얻고, mag 은 918 처럼
    **새 날짜의 `r`** 에서 다시 읽는다 — 그것이 정확히 이슈 #175 의 병이다.
    """
    pfirst, moved = permute_events(first, ok, seed=seed)
    dates, mags = real_events(pfirst, r)
    return dates, mags, float(moved), pfirst


def null_n1_shuffle_r(first: np.ndarray, r: np.ndarray, ok: np.ndarray,
                      seed: int = 918, mag_seed: int = 922):
    """N1 — 「`r` 도 섞는 순열」(사전등록 918 §5-바 가 원래 적은 것).

    🔴 **N0 과의 유일한 차이가 mag 이다** — 날짜 순열은 같은 `permute_events(seed=918)`
    를 그대로 쓰고, 그 격자의 **진짜 사건 mag 다중집합**을 섞어 새 날짜에 붙인다.
    그래서 두 귀무의 차이는 「`r` 을 섞었나」 하나로 격리된다.
    """
    pfirst, moved = permute_events(first, ok, seed=seed)
    rng = np.random.default_rng(mag_seed)
    G = first.shape[0]
    dates, mags = [], []
    for g in range(G):
        nd = np.flatnonzero(pfirst[g])
        od = np.flatnonzero(first[g])
        dates.append(nd)
        if nd.size == 0:
            mags.append(np.zeros(0))
            continue
        m = r[g, od].astype(float)
        assert m.size == nd.size, (g, m.size, nd.size)   # 개수 보존 확인
        mags.append(rng.permutation(m))
    return dates, mags, float(moved)


def null_n2_gap_order(first: np.ndarray, r: np.ndarray, seed: int = 922,
                      plant_break_multiset: bool = False):
    """N2 — 「간격순서 순열」. 🔴 격자별 **간격 다중집합을 전량 보존**하고 순서만 부순다.

    새 날짜 = `t_1 + cumsum(섞은 간격)` — 합이 보존되므로 **첫·마지막 사건 날짜가 같다**.
    mag 은 **사건 서수**에 그대로 붙여 둔다(그래서 mag ↔ 다음 간격의 짝이 깨진다).

    `plant_break_multiset=True` 면 간격 하나를 일부러 바꾼다(심은 결함 W9).
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
        perm = rng.permutation(gaps)
        if plant_break_multiset and perm.size:
            perm = perm.copy()
            perm[0] = perm[0] + 1            # 심은 결함 — 다중집합이 깨진다
        nd = np.r_[idx[0], idx[0] + np.cumsum(perm)]
        moved += int(not np.array_equal(perm, gaps))
        dates.append(nd.astype(idx.dtype))
        mags.append(m)
    return dates, mags, (moved / have if have else 0.0)


# ─────────────────────────────────────────────── 간격 표 (918 과 같은 열)
def gaps_from_events(dates, mags, V: np.ndarray, OBS: np.ndarray, day0: dt.date):
    """(날짜, mag) 짝 → 간격 표. 🔴 `interval918.events_and_gaps` 와 **같은 열·같은 순서**.

    각 행이 하나의 **간격**이다. 열은 전부 `t_k` 에 아는 값이다.
    """
    G = len(dates)
    out_gi, out_tk, out_gap, out_mag, out_prev, out_lvl = [], [], [], [], [], []
    n_event = 0
    per_grid = np.zeros(G, np.int64)
    for g in range(G):
        idx = np.asarray(dates[g], np.int64)
        mg = np.asarray(mags[g], float)
        per_grid[g] = idx.size
        n_event += idx.size
        if idx.size < 2:
            continue
        assert mg.size == idx.size, (g, mg.size, idx.size)
        assert np.all(np.diff(idx) > 0), f"🔴 격자 {g} 의 사건 날짜가 증가하지 않는다"
        gaps = np.diff(idx)
        for k in range(idx.size - 1):
            tk = int(idx[k])
            prevmed = float(np.median(gaps[:k])) if k >= 1 else np.nan
            lo = max(0, tk - 28)
            w = V[g, lo:tk][OBS[g, lo:tk]]
            lvl = float(np.median(w)) if w.size else np.nan
            out_gi.append(g)
            out_tk.append(tk)
            out_gap.append(int(gaps[k]))
            out_mag.append(float(mg[k]))
            out_prev.append(prevmed)
            out_lvl.append(lvl)
    tk = np.asarray(out_tk, np.int32)
    dows = np.asarray([(day0 + dt.timedelta(days=int(t))).weekday() for t in tk], np.int8)
    mons = np.asarray([(day0 + dt.timedelta(days=int(t))).month for t in tk], np.int8)
    return {
        "gi": np.asarray(out_gi, np.int32),
        "tk": tk,
        "gap": np.asarray(out_gap, np.int32),
        "dow": dows,
        "quarter": ((mons - 1) // 3).astype(np.int8),
        "mag": np.asarray(out_mag, np.float64),
        "prevmed": np.asarray(out_prev, np.float64),
        "lvl": np.asarray(out_lvl, np.float64),
        "🔴 사건 수(분모 A)": int(n_event),
        "🔴 간격 수(분모 B)": int(len(out_gap)),
        "🔴 사건이 1개 이상인 격자": int((per_grid > 0).sum()),
        "🔴 간격이 1개 이상인 격자": int((per_grid >= 2).sum()),
        "_per_grid_events": per_grid,
    }


def same_table(a: dict, b: dict) -> dict:
    """두 표가 **모든 열에서** 같은가(W0 음성 대조용). 값이 아니라 회계를 돌려준다."""
    cols = ("gi", "tk", "gap", "dow", "quarter", "mag", "prevmed", "lvl")
    rep = {}
    for c in cols:
        x, y = np.asarray(a[c]), np.asarray(b[c])
        if x.shape != y.shape:
            rep[c] = f"모양이 다르다 {x.shape} vs {y.shape}"
            continue
        if x.dtype.kind == "f":
            same = bool(np.array_equal(x, y, equal_nan=True))
        else:
            same = bool(np.array_equal(x, y))
        rep[c] = same
    rep["전부 같다"] = all(v is True for k, v in rep.items() if k in cols)
    return rep


def gap_multiset_same(dates_a, dates_b) -> dict:
    """격자별 간격 **다중집합**이 같은가(N2 의 보존 주장 · W9 가 심는 자리)."""
    bad = 0
    checked = 0
    for a, b in zip(dates_a, dates_b):
        a = np.asarray(a); b = np.asarray(b)
        if a.size < 2 and b.size < 2:
            continue
        checked += 1
        if a.size != b.size or not np.array_equal(np.sort(np.diff(a)),
                                                  np.sort(np.diff(b))):
            bad += 1
    return {"검사한 격자(분모)": checked, "다중집합이 깨진 격자": bad,
            "통과": bad == 0}


# ─────────────────────────────────────────────── 비교가능성 관문 (사전등록 §3)
def comparability(real: dict, null: dict, *, rel_thr: float = COMPARABLE_REL) -> dict:
    """🔴 두 세계가 나란히 놓일 수 있는가. **판정보다 먼저 부른다.**"""
    cr = real["가 기후값"]["MAE"]
    cn = null["가 기후값"]["MAE"]
    d = cn - cr
    rel = d / cr if cr else float("nan")
    counts_same = {
        "사건 수": (real["🔴 사건 수(분모 A)"], null["🔴 사건 수(분모 A)"]),
        "간격 수": (real["🔴 간격 수(분모 B)"], null["🔴 간격 수(분모 B)"]),
        "홀드아웃 간격": (real["홀드아웃 간격 수(분모)"], null["홀드아웃 간격 수(분모)"]),
        "홀드아웃 격자(군집)": (real["홀드아웃 격자(군집) 수"], null["홀드아웃 격자(군집) 수"]),
        "학습 간격": (real["표(학습)"]["학습 간격 수(분모)"],
                  null["표(학습)"]["학습 간격 수(분모)"]),
    }
    ok_counts = all(a == b for a, b in counts_same.values())
    return {
        "기후값 MAE — 진짜(일)": cr,
        "기후값 MAE — 귀무(일)": cn,
        "🔴 차(귀무 − 진짜 · 일)": d,
        "🔴 상대차": rel,
        "허용 문턱(사전등록 §3)": rel_thr,
        "🔴 통과": bool(abs(rel) <= rel_thr),
        "mag 3분위 경계 — 진짜": real["표(학습)"]["mag 3분위 경계"],
        "mag 3분위 경계 — 귀무": null["표(학습)"]["mag 3분위 경계"],
        "간격 중앙값 — 진짜/귀무": (real["간격 중앙값"], null["간격 중앙값"]),
        "간격 평균 — 진짜/귀무": (real["간격 평균"], null["간격 평균"]),
        "분모 대조(같아야 한다)": counts_same,
        "🔴 분모 전부 같다": bool(ok_counts),
    }
