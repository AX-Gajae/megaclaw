# -*- coding: utf-8 -*-
"""팔 918-ㅌ — **격자 위에서 라벨 없이 급증 사건을 정의하고 간격을 잰다.**

사전등록: `docs/prereg_918_interval.md` (2026-08-11 16:19 KST · HEAD 28c4f23ad).

🔴 이 모듈이 지키는 것
  · 라벨 **0비트**. 판 유보(3,775) 도, 915 의 부착 93행도 안 쓴다.
  · 모든 조건은 예측 시점 `t_k` 에 **이미 아는 값**만 쓴다(§5).
  · 분모 딱지: 행 ≠ 칸 ≠ 격자 ≠ 사건 ≠ 간격. 섞지 않는다(조항 60).
  · 마스킹 `*`(≤3) 는 0 으로 접되 **건수를 따로 센다** — 「0 이었다」가 아니다.

🔴 **심어서 확인한다**(사전등록 §7). 이 모듈의 함수들은 `plant=` 인자로 결함을
**일부러 심을 수 있게** 만들어져 있다. 검사가 원리상 발화 못 하면 그 검사는 없는 것이다
(이슈 #171 — 915 의 「죽는 층은 없다」가 그 병이었다).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
SRC = ROOT / "data/ingest/seoul_lifepop"

Q = b'" \t\r\n'
STAR = b"*"

#: 사전등록 §3 — 날짜 축은 여기서 고정한다(577일)
DAY0 = dt.date(2025, 1, 1)
DAY1 = dt.date(2026, 7, 31)
NDAY = (DAY1 - DAY0).days + 1          # 577

#: 사전등록 §4 — 값을 보기 전에 박은 상수
TAU_PRIMARY = 1.20
TAU_SENS = (1.10, 1.50)
BASE_LAGS = (7, 14, 21, 28)
BASE_MIN_OBS = 3
OBS_MIN_FRAC = 0.95
CELL_MIN = 100                          # 기후값 셀 최소 학습행
SPLIT_SALT = "918"
SPLIT_TRAIN_PCT = 70


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ──────────────────────────────────────────────────── 0단계 · zip 흘려 읽기
def scan_zip_daily(zp: Path) -> dict:
    """zip 하나를 **압축을 안 풀고** 흘려 읽어 (격자, 날짜) 일 합계를 만든다.

    🔴 915 의 `ingest/lifepop915.py` 와 **다른 파서**다(시각 축을 안 만들고
    (격자,날짜) 로 바로 접는다 · 행 건수와 마스킹 건수를 칸별로 센다).
    두 파서가 같은 수를 내면 그것이 독립 재계산이다.
    """
    t0 = dt.datetime.now(dt.timezone.utc)
    gi: dict[bytes, int] = {}
    di: dict[bytes, int] = {}
    val: list[list[float]] = []
    cnt: list[list[int]] = []
    msk: list[list[int]] = []
    rows = bad = masked = nonfinite = 0
    hours: set[bytes] = set()
    dongs: set[bytes] = set()
    pairs: set[tuple[bytes, bytes]] = set()

    def _grow(g: int) -> None:
        while len(val) <= g:
            val.append([0.0] * 32)
            cnt.append([0] * 32)
            msk.append([0] * 32)

    with zipfile.ZipFile(zp) as z:
        members = sorted(n for n in z.namelist() if n.lower().endswith(".csv"))
        for n in members:
            with z.open(n) as f:
                first = True
                for raw in f:
                    if first:
                        first = False
                        continue
                    if not raw.strip():
                        continue
                    p = raw.split(b",", 5)
                    if len(p) < 5:
                        bad += 1
                        continue
                    rows += 1
                    d = p[0].strip(Q)
                    h = p[1].strip(Q)
                    dg = p[2].strip(Q)
                    gd = p[3].strip(Q)
                    v = p[4].strip(Q)
                    hours.add(h)
                    dongs.add(dg)
                    pairs.add((dg, gd))
                    j = di.get(d)
                    if j is None:
                        j = di[d] = len(di)
                    i = gi.get(gd)
                    if i is None:
                        i = gi[gd] = len(gi)
                        _grow(i)
                    cnt[i][j] += 1                     # 🔴 「행이 있었나」
                    if v == STAR:
                        masked += 1
                        msk[i][j] += 1                 # 0 으로 접되 센다
                        continue
                    try:
                        fv = float(v)
                    except ValueError:
                        nonfinite += 1
                        continue
                    val[i][j] += fv

    days = sorted(di, key=lambda k: di[k])
    grids = sorted(gi, key=lambda k: gi[k])
    nd = len(days)
    assert nd <= 32, f"🔴 한 달에 날짜가 {nd} 개다 — 버퍼 32 를 넘는다"
    V = np.zeros((len(grids), nd), np.float64)
    C = np.zeros((len(grids), nd), np.int32)
    M = np.zeros((len(grids), nd), np.int32)
    for i in range(len(grids)):                        # gi 의 i 가 곧 행 번호다
        V[i, :nd] = val[i][:nd]
        C[i, :nd] = cnt[i][:nd]
        M[i, :nd] = msk[i][:nd]
    order = np.argsort(np.array([g.decode("cp949") for g in grids]))
    gnames = [grids[k].decode("cp949") for k in order]
    return {
        "파일": zp.name, "바이트": zp.stat().st_size, "sha256": sha256_file(zp),
        "CSV 수": len(members),
        "포장": ("폴더" if any("/" in m for m in members) else "평면"),
        "행수(직접 셌다)": rows, "쪼개기 실패 행": bad,
        "🔴 마스킹(`*`=≤3) 행": masked, "수로 못 읽은 값": nonfinite,
        "일수": nd, "시간 칸 가짓수": len(hours),
        "서로 다른 행정동코드": len(dongs),
        "서로 다른 250M격자": len(grids),
        "서로 다른 (행정동,격자) 쌍": len(pairs),
        "합계 총합": float(V.sum()),
        "격자": gnames,
        "날짜": [d.decode("ascii") for d in days],
        "V": V[order], "C": C[order], "M": M[order],
        "초": round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1),
    }


# ──────────────────────────────────────────────────── 1단계 · 사건과 간격
def baseline_ratio(V: np.ndarray, OBS: np.ndarray):
    """요일 기저선(사전등록 §4-1) 과 비율 r. 🔴 **미래를 안 본다** — lag 만 쓴다."""
    G, D = V.shape
    lags = np.asarray(BASE_LAGS, int)
    stack = np.full((len(lags), G, D), np.nan, np.float64)
    for li, L in enumerate(lags):
        stack[li, :, L:] = np.where(OBS[:, :D - L], V[:, :D - L], np.nan)
    nobs = np.sum(np.isfinite(stack), axis=0)
    base = np.nanmedian(np.where(np.isfinite(stack), stack, np.nan), axis=0)
    ok = (nobs >= BASE_MIN_OBS) & np.isfinite(base) & (base > 0) & OBS
    r = np.full((G, D), np.nan, np.float64)
    np.divide(V, base, out=r, where=ok)
    return base, r, ok


def surges(r: np.ndarray, ok: np.ndarray, tau: float):
    """급증 불(bool) 판. 연속 구간은 **첫날만** 사건(사전등록 §4-4)."""
    s = ok & (r >= tau)
    prev = np.zeros_like(s)
    prev[:, 1:] = s[:, :-1]
    return s & ~prev


def events_and_gaps(first: np.ndarray, r: np.ndarray, V: np.ndarray,
                    OBS: np.ndarray, grids, days_dates):
    """격자별 사건 날짜 → 간격 표. 각 행이 하나의 **간격**이다.

    반환 열 — 전부 `t_k` 에 아는 값이다:
      gi(격자 index) · tk(사건 일 index) · gap(일) · dow · quarter ·
      mag(r[g,tk]) · prevmed(그 격자의 **이전** 간격들의 중앙값 · 없으면 nan) ·
      lvl(그 격자의 직전 28일 관측값 중앙값)
    """
    G = first.shape[0]
    out_gi, out_tk, out_gap, out_mag, out_prev, out_lvl = [], [], [], [], [], []
    n_event = 0
    per_grid_events = np.zeros(G, np.int64)
    for g in range(G):
        idx = np.flatnonzero(first[g])
        per_grid_events[g] = idx.size
        n_event += idx.size
        if idx.size < 2:
            continue
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
            out_mag.append(float(r[g, tk]))
            out_prev.append(prevmed)
            out_lvl.append(lvl)
    d0 = days_dates[0]
    tk = np.asarray(out_tk, np.int32)
    dows = np.asarray([(d0 + dt.timedelta(days=int(t))).weekday() for t in tk], np.int8)
    mons = np.asarray([(d0 + dt.timedelta(days=int(t))).month for t in tk], np.int8)
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
        "🔴 사건이 1개 이상인 격자": int((per_grid_events > 0).sum()),
        "🔴 간격이 1개 이상인 격자": int((per_grid_events >= 2).sum()),
        "_per_grid_events": per_grid_events,
    }


# ──────────────────────────────────────────────────── 2단계 · 분할과 예측기
def split_grids(grids, frac_pct: int = SPLIT_TRAIN_PCT, salt: str = SPLIT_SALT,
                plant_leak: bool = False):
    """격자 단위 70/30. 🔴 `plant_leak=True` 면 누설을 **심는다**(W2 검정력 시험)."""
    tr, ho = set(), set()
    for g in grids:
        h = int(hashlib.sha256((salt + str(g)).encode()).hexdigest()[:8], 16)
        (tr if (h % 100) < frac_pct else ho).add(g)
    if plant_leak and ho:
        tr.add(sorted(ho)[0])              # 심은 결함 — 홀드아웃 하나를 학습에도 넣는다
    return tr, ho


def _terciles(x: np.ndarray):
    v = x[np.isfinite(x)]
    if v.size < 3:
        return (np.nan, np.nan)
    return (float(np.percentile(v, 100 / 3)), float(np.percentile(v, 200 / 3)))


def _bin(x, cuts):
    if not np.isfinite(x) or not np.isfinite(cuts[0]):
        return -1                          # 「모름」 칸
    return int(x >= cuts[0]) + int(x >= cuts[1])


def fit_tables(tab, tr_mask, *, plant_const_cal: bool = False):
    """학습 격자에서만 표를 만든다(사전등록 §5). 반환 dict."""
    gap = tab["gap"][tr_mask]
    dow = tab["dow"][tr_mask].astype(int)
    qtr = tab["quarter"][tr_mask].astype(int)
    if plant_const_cal:                    # 심은 결함 W6 — 달력을 상수로
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    mag = tab["mag"][tr_mask]
    prv = tab["prevmed"][tr_mask]
    cuts_mag = _terciles(mag)
    cuts_prv = _terciles(prv)
    gmed = float(np.median(gap)) if gap.size else np.nan

    cal = {}
    for d in range(7):
        for q in range(4):
            m = (dow == d) & (qtr == q)
            if m.sum() >= CELL_MIN:
                cal[(d, q)] = float(np.median(gap[m]))
    b_mag = np.asarray([_bin(v, cuts_mag) for v in mag], int)
    b_prv = np.asarray([_bin(v, cuts_prv) for v in prv], int)
    lvl2, lvl3 = {}, {}
    for d in range(7):
        for q in range(4):
            base_m = (dow == d) & (qtr == q)
            if not base_m.any():
                continue
            for bp in (-1, 0, 1, 2):
                m2 = base_m & (b_prv == bp)
                if m2.sum() >= CELL_MIN:
                    lvl2[(d, q, bp)] = float(np.median(gap[m2]))
                for bm in (-1, 0, 1, 2):
                    m3 = m2 & (b_mag == bm)
                    if m3.sum() >= CELL_MIN:
                        lvl3[(d, q, bp, bm)] = float(np.median(gap[m3]))
    q10, q90 = (float(np.percentile(gap, 10)), float(np.percentile(gap, 90))) \
        if gap.size else (np.nan, np.nan)
    cal_iv, cond_iv = {}, {}
    for d in range(7):
        for q in range(4):
            m = (dow == d) & (qtr == q)
            if m.sum() >= CELL_MIN:
                cal_iv[(d, q)] = (float(np.percentile(gap[m], 10)),
                                  float(np.percentile(gap[m], 90)), int(m.sum()))
            for bp in (-1, 0, 1, 2):
                for bm in (-1, 0, 1, 2):
                    m3 = m & (b_prv == bp) & (b_mag == bm)
                    if m3.sum() >= CELL_MIN:
                        cond_iv[(d, q, bp, bm)] = (float(np.percentile(gap[m3], 10)),
                                                   float(np.percentile(gap[m3], 90)),
                                                   int(m3.sum()))
    return {"전체 중앙값": gmed, "달력 셀": cal, "2수준": lvl2, "3수준": lvl3,
            "mag 3분위 경계": cuts_mag, "prevmed 3분위 경계": cuts_prv,
            "학습 간격 수(분모)": int(gap.size),
            "🔴 달력 셀 가짓수": len(cal),
            "🔴 3수준 셀 가짓수": len(lvl3),
            "전체 10~90분위": (q10, q90),
            "달력 구간": cal_iv, "조건부 구간": cond_iv,
            "_plant_const_cal": bool(plant_const_cal)}


def predict(tab, mask, T, *, arm: str, plant_ignore_state: bool = False,
            plant_oracle: bool = False):
    """예측. arm ∈ {가 기후값, 나 조건부(주), 다 조건부(보조), 라 무정보}."""
    dow = tab["dow"][mask].astype(int)
    qtr = tab["quarter"][mask].astype(int)
    if T.get("_plant_const_cal"):
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    mag = tab["mag"][mask]
    prv = tab["prevmed"][mask]
    gap = tab["gap"][mask]
    gm = T["전체 중앙값"]
    n = int(mask.sum())
    out = np.full(n, gm, float)
    back = {"3수준": 0, "2수준": 0, "달력": 0, "전체": 0}
    if arm == "라 무정보":
        back["전체"] = n
        return out, back
    for i in range(n):
        c = T["달력 셀"].get((dow[i], qtr[i]))
        if arm == "가 기후값":
            if c is None:
                back["전체"] += 1
                continue
            out[i] = c
            back["달력"] += 1
            continue
        if arm == "다 조건부(보조)":
            if np.isfinite(prv[i]) and not plant_ignore_state:
                out[i] = prv[i]
                back["3수준"] += 1
            elif c is not None:
                out[i] = c
                back["달력"] += 1
            else:
                back["전체"] += 1
            continue
        # 나 조건부(주)
        bp = -1 if plant_ignore_state else _bin(prv[i], T["prevmed 3분위 경계"])
        bm = -1 if plant_ignore_state else _bin(mag[i], T["mag 3분위 경계"])
        if plant_oracle:                    # 🔴 심은 결함 W3 — 미래를 본다
            out[i] = gap[i]
            back["3수준"] += 1
            continue
        v = None if plant_ignore_state else T["3수준"].get((dow[i], qtr[i], bp, bm))
        if v is not None:
            out[i] = v
            back["3수준"] += 1
            continue
        v = None if plant_ignore_state else T["2수준"].get((dow[i], qtr[i], bp))
        if v is not None:
            out[i] = v
            back["2수준"] += 1
            continue
        if c is not None:
            out[i] = c
            back["달력"] += 1
        else:
            back["전체"] += 1
    return out, back


def coverage(tab, mask, T, *, which: str):
    """10~90분위 구간의 홀드아웃 실측 덮음(사전등록 §6-5)."""
    dow = tab["dow"][mask].astype(int)
    qtr = tab["quarter"][mask].astype(int)
    mag = tab["mag"][mask]
    prv = tab["prevmed"][mask]
    gap = tab["gap"][mask]
    hit = tot = miss = 0
    for i in range(gap.size):
        if which == "달력":
            iv = T["달력 구간"].get((dow[i], qtr[i]))
        else:
            iv = T["조건부 구간"].get((dow[i], qtr[i],
                                   _bin(prv[i], T["prevmed 3분위 경계"]),
                                   _bin(mag[i], T["mag 3분위 경계"])))
        if iv is None:
            iv = T["전체 10~90분위"]
            if not np.isfinite(iv[0]):
                miss += 1
                continue
        tot += 1
        hit += int(iv[0] <= gap[i] <= iv[1])
    return {"명목 덮음": 0.80, "실측 덮음": (hit / tot) if tot else None,
            "덮인 행": hit, "홀드아웃 행(분모)": tot,
            "🔴 구간을 못 만든 행": miss,
            "🔴 합 == 홀드아웃 전체(assert)": (tot + miss) == int(gap.size)}


def boot(imp: np.ndarray, gi: np.ndarray, *, B: int = 2000, seed: int = 918):
    """군집(격자) BCa — 규약 47. 🔴 폴백이면 사유를 필드에 적는다."""
    order = np.argsort(gi, kind="stable")
    gs = gi[order]
    bounds = np.flatnonzero(np.r_[True, gs[1:] != gs[:-1]])
    clusters = [order[a:b] for a, b in zip(bounds, np.r_[bounds[1:], gs.size])]
    vals = np.asarray(imp, float)
    from lab.pairboot import cluster_boot, verdict
    th, lo, hi, kind = cluster_boot(lambda ix: float(vals[ix].mean()),
                                    clusters, B=B, seed=seed)
    fb = None if kind == "BCa" else f"lab.pairboot.cluster_boot 가 '{kind}' 를 냈다"
    return {"점추정": float(th), "lo": float(lo), "hi": float(hi),
            "구간 종류": kind, "판정": verdict(lo, hi),
            "🔴 폴백 사유": fb,
            "군집(격자) 수": len(clusters), "행(간격) 수": int(vals.size), "B": B,
            "🔴 반폭(=MDE 자리)": float((hi - lo) / 2.0)}


def permute_events(first: np.ndarray, eligible: np.ndarray, seed: int = 918,
                   plant_identity: bool = False):
    """🔴 순열 귀무 — 격자 안에서 **사건 날짜를 재추첨**(개수 보존).

    `plant_identity=True` 면 아무것도 안 섞는다(심은 결함 W5).
    반환: (새 first 판, 실제로 자리가 바뀐 격자 비율)
    """
    rng = np.random.default_rng(seed)
    G, D = first.shape
    out = np.zeros_like(first)
    moved = 0
    have = 0
    for g in range(G):
        idx = np.flatnonzero(first[g])
        if idx.size == 0:
            continue
        have += 1
        pool = np.flatnonzero(eligible[g])
        if pool.size < idx.size or plant_identity:
            out[g, idx] = True
            continue
        pick = rng.choice(pool, size=idx.size, replace=False)
        pick.sort()
        out[g, pick] = True
        moved += int(not np.array_equal(pick, idx))
    return out, (moved / have if have else 0.0)
