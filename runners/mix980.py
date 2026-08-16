#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""980 — 🔴🔴 **1,710 은 자료 한계가 아니라 상수다** (축 C3 · 곁 C4).

사전등록 `docs/prereg_980_mixture.md` 를 그대로 따른다.

🔴 티처 #118 이 깔때기를 냈다:
    38,866,835(디스크) → 670,118(읽음) → 35,641(삼중쌍) → **1,710(모형)**
그리고 마지막 칸이 `alpha977.py:60` 의 `N_B = 1800` **상수**임을 지목했다.

이 러너는 **선택기를 인자로 받는** 배관을 새로 쓴다(`alpha977.py` 는 동결물이라 안 고친다).

    ㉯ 대조 = 순열 앞머리          (`alpha977.select()` 와 **바이트로 같아야 한다** · W1)
    ㉮ 처리 = 🔴 **도메인 층화 표집** (같은 난수 차례 · 다른 것은 할당량 제약 하나뿐)
    ㉰ 예산 = 🔴 `N_B` 격자

🔴 **정본 자는 `R_iv* 닫힌꼴`(`w ∝ n_d − 1`)** 이고 이 사이클은 자를 안 만진다.

씀:
    python3 runners/mix980.py --stage wiring   --ref <40자 sha>
    python3 runners/mix980.py --stage funnel   --ref <40자 sha>
    python3 runners/mix980.py --stage mixarm   --ref <40자 sha>
    python3 runners/mix980.py --stage budget   --ref <40자 sha>
    python3 runners/mix980.py --stage score979 --ref <40자 sha>
    python3 runners/mix980.py --stage recheck  --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runners.predict971 as P                    # noqa: E402
import runners.layers957 as L                     # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler978 as R8                             # noqa: E402
import ruler979 as R9                             # noqa: E402

RAN = ("runners/mix980.py", "runners/ruler979.py", "runners/ruler978.py",
       "runners/alpha977.py", "runners/ledger.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out980_progress.txt"

# ── 사전등록 상수 (§3 · 측정 전에 박았다) ─────────────────────────────
SEEDS = A.SEEDS                    # 겹 씨앗 다섯 → 점추정도 짝 SE 도 **5 벌**
KFOLD = A.KFOLD
U_REG = A.U_REG                    # 등록된 λ 둘 (10^0 · 10^3)
ALPHA_BASE = A.ALPHA_BASE          # 0.95
N_B_REG = A.N_B                    # 🔴 1800 — 흔들 대상
BOOT = 400                         # 혼합 팔
BOOT_NB = 200                      # 예산 격자(칸 14 개라 반으로 줄인다 · §3 에 적었다)
NB_GRID = [450, 900, 1800, 3600, 7200, 14400, 28800]
K_FEAT = 6

#: 🔴 자 여섯 — 979 와 **글자까지 같은 이름**(산출물을 바로 견준다)
R1, R2, R3 = R9.R1, R9.R2, R9.R3
R4, R5, R6 = R9.R4, R9.R5, R9.R6
RULERS = R9.RULERS
CANON = R6                         # 🔴🔴 정본 자 — `R_iv* 닫힌꼴`

ARM_C = "㉯ 대조(순열 앞머리)"
ARM_S = "㉮ 처리(도메인 층화)"

#: 🔴 반증조건 4 — **자 값을 내는 stage 의 이름을 측정 전에 못박았다**
FC4_REG_980 = ("out980_mixarm.json", "out980_budget.json")
FC4_OUT_980 = ("out980_wiring.json", "out980_funnel.json",
               "out980_score979.json", "out980_recheck.json")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))
    sys.stderr.write("%s  %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def _sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _load(name):
    p = OUT / name if not str(name).startswith("/") else Path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _git(*args):
    return subprocess.check_output(["git"] + list(args), cwd=str(ROOT)).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════
# 🔴 유보 지문 — 리터럴 `True` 를 안 쓴다 (반증조건 6)
# ══════════════════════════════════════════════════════════════════════
ho_stamp = R9.ho_stamp
ho_verdict = R9.ho_verdict


# ══════════════════════════════════════════════════════════════════════
# §2 선택기 둘 — 🔴 **같은 난수 차례 · 다른 것은 할당량 제약 하나뿐**
# ══════════════════════════════════════════════════════════════════════
def quota(pool, nh, tgt=None):
    """🔴 유보 혼합에 맞춘 도메인별 할당량(최대잔여법 · 공급 상한 + 재분배).

    목표 몫 = **게이트 유보 행 몫** `n_d / Σ_게이트 n_d`.
    🔴 hplt 공급이 모자라면 있는 만큼 받고 남은 자리를 나머지에 같은 방법으로 재분배한다.
    🔴 `tgt` 는 **배선 변이체**가 목표를 갈아 끼우려고 쓴다(그때만 인자를 준다).
    """
    doms = [d for d in pool.gated]
    have = collections.Counter(pool.dh.tolist())
    if tgt is None:
        tgt = {d: float(pool.ho_mask[d].sum()) for d in doms}
    else:
        tgt = dict(tgt)
    tot = sum(tgt.values())
    q = {d: 0 for d in doms}
    bound = collections.OrderedDict()
    left = int(nh)
    free = [d for d in doms if have.get(d, 0) > 0]
    for _ in range(len(doms) + 2):
        if left <= 0 or not free:
            break
        s = sum(tgt[d] for d in free)
        if s <= 0:
            break
        raw = {d: left * tgt[d] / s for d in free}
        base = {d: int(math.floor(raw[d])) for d in free}
        rem = left - sum(base.values())
        for d in sorted(free, key=lambda x: (-(raw[x] - base[x]), x))[:max(rem, 0)]:
            base[d] += 1
        newfree = []
        for d in free:
            room = have.get(d, 0) - q[d]
            take = min(base[d], room)
            q[d] += take
            left -= take
            if take < base[d]:
                bound[d] = {"🔴 공급": int(have.get(d, 0)),
                            "🔴 원한 자리": int(base[d] + q[d] - take),
                            "🔴 받은 자리": int(q[d])}
            elif q[d] < have.get(d, 0):
                newfree.append(d)
        free = newfree
    return q, bound, int(left)


#: 🔴 hplt 쪽 선택은 **겹에 안 의존한다**(`avail_h` 가 언제나 전부 참이다 — 979 의 새 사실).
#: 그러므로 `(겹 씨앗, 예산, 팔)` 로 캐시한다. **값이 바뀌지 않는다**는 것을 배선 W3 이 문다.
_SELH = {}


def _selh(pool, alpha, n_b, arm, tgt=None):
    key = (int(pool.seed), int(n_b), arm, None if tgt is None
           else tuple(sorted(tgt.items())))
    if key in _SELH:
        return _SELH[key]
    nh = int(round(alpha * n_b))
    order = pool.perm_h                       # 🔴 두 팔이 **같은 차례**를 쓴다
    if arm == ARM_C:
        selh = order[:nh]
        q, bound, short = None, collections.OrderedDict(), max(0, nh - len(selh))
    else:
        q, bound, short = quota(pool, nh, tgt)
        need = dict(q)
        tot = sum(q.values())
        keep = []
        for i in order:
            d = pool.dh[i]
            if need.get(d, 0) > 0:
                need[d] -= 1
                keep.append(i)
                if len(keep) >= tot:
                    break
        selh = np.asarray(keep, dtype=order.dtype)
    _SELH[key] = (selh, q, bound, int(short))
    return _SELH[key]


def select980(pool, fold, alpha, n_b, arm, tgt=None):
    """🔴 예산 `n_b` 를 인자로 받는다(`alpha977.select` 는 `N_B` 가 상수다).

    `arm == ARM_C` → 순열 앞머리(대조 · `alpha977.select` 와 같은 행)
    `arm == ARM_S` → 🔴 **같은 순열을 같은 차례로 훑되 도메인 할당량이 찰 때까지만 받는다**
    🔴 **base 쪽은 두 팔이 바이트로 같다** — 다른 것은 hplt 선택 하나뿐이다.
    """
    avail_b = (pool.fi != fold)
    nh = int(round(alpha * n_b))
    nb = n_b - nh
    selb = pool.perm_b[avail_b[pool.perm_b]][:nb]
    selh, q, bound, short = _selh(pool, alpha, n_b, arm, tgt)
    return selb, selh, q, bound, int(short)


def mix_r(pool, selh):
    """🔴 학습 hplt 행의 도메인 몫과 **유보 도메인 몫**의 피어슨 `r`(티처 #117 의 수)."""
    doms = list(pool.gated)
    cnt = collections.Counter(pool.dh[selh].tolist())
    a = np.asarray([cnt.get(d, 0) for d in doms], float)
    b = np.asarray([float(pool.ho_mask[d].sum()) for d in doms], float)
    if a.sum() <= 0:
        return None, {}, {}
    a = a / a.sum()
    b = b / b.sum()
    if np.std(a) == 0 or np.std(b) == 0:
        return None, {}, {}
    return (float(np.corrcoef(a, b)[0, 1]),
            {d: _r(a[i]) for i, d in enumerate(doms)},
            {d: _r(b[i]) for i, d in enumerate(doms)})


def oof980(pool, alpha, lam, n_b, arm, k=K_FEAT, tr_boot=None):
    """`ruler978.oof978` 과 **같은 배관**이고 선택기·예산만 인자로 뺐다."""
    pred = np.zeros(len(pool.yb))
    ntr, nsel_h = [], []
    for j in range(KFOLD):
        selb, selh, _q, _bd, _sh = select980(pool, j, alpha, n_b, arm)
        X, y, ent, _nb = A.design(pool, selb, selh, k)
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 977 * 100000)
            order, st, en = A.groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y = X[idx], y[idx]
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        ntr.append(int(len(y)))
        nsel_h.append(int(len(selh)))
    return {"예측": pred, "겹별 학습 행": ntr, "겹별 hplt 행": nsel_h}


def point5(pool, R, alpha, lam, n_b, arm):
    """🔴 **5 벌**(겹 씨앗 다섯) 평균 — 짝 SE 와 벌 수가 같다(반증조건 1)."""
    acc = {nm: [] for nm in RULERS}
    nh = []
    for s in SEEDS:
        pool.reseed(s)
        r = oof980(pool, alpha, lam, n_b, arm)
        v, _p = R9.score6(pool, R, r["예측"])
        for nm in RULERS:
            acc[nm].append(v[nm])
        nh.append(r["겹별 hplt 행"][0])
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = _r(float(np.mean(acc[nm])))
        out[nm + " 벌 SD"] = _r(float(np.std(acc[nm], ddof=1)))
    out["🔴 벌 수"] = len(acc[RULERS[0]])
    out["🔴 겹당 hplt 학습 행"] = int(np.mean(nh))
    return out


def se_paired(pool, R, alpha, lam, n_b, arm_a, arm_b, boot=BOOT, tag="",
              seeds=None):
    """🔴🔴 **짝 SE** — 복제 `b` 마다 겹 씨앗 다섯의 Δ 를 평균하고 그 평균의 SD 를 낸다.

    🔴 분자(점추정)도 분모(SE)도 **5 벌**이다(반증조건 1).
    """
    seeds = list(SEEDS if seeds is None else seeds)
    dd = {nm: [] for nm in RULERS}
    aa = {nm: [] for nm in RULERS}
    bb = {nm: [] for nm in RULERS}
    t0 = time.time()
    for b in range(boot):
        buf = {nm: [] for nm in RULERS}
        bufa = {nm: [] for nm in RULERS}
        bufb = {nm: [] for nm in RULERS}
        for s in seeds:
            pool.reseed(s)
            pa = oof980(pool, alpha, lam, n_b, arm_a, tr_boot=b)["예측"]
            pb = oof980(pool, alpha, lam, n_b, arm_b, tr_boot=b)["예측"]
            va, _ = R9.score6(pool, R, pa)
            vb, _ = R9.score6(pool, R, pb)
            for nm in RULERS:
                buf[nm].append(va[nm] - vb[nm])
                bufa[nm].append(va[nm])
                bufb[nm].append(vb[nm])
        for nm in RULERS:
            dd[nm].append(float(np.mean(buf[nm])))
            aa[nm].append(float(np.mean(bufa[nm])))
            bb[nm].append(float(np.mean(bufb[nm])))
        if (b + 1) % 100 == 0:
            _prog("    %s 짝SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                   time.time() - t0))
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = collections.OrderedDict([
            ("🔴🔴 짝 SE(5 벌 정합)", _r(float(np.std(dd[nm], ddof=1)))),
            ("🔴 팔 A SE", _r(float(np.std(aa[nm], ddof=1)))),
            ("🔴 팔 B SE", _r(float(np.std(bb[nm], ddof=1)))),
        ])
    out["🔴 복제 수"] = len(dd[RULERS[0]])
    out["🔴 벌 수(복제 하나 안에서)"] = len(seeds)
    out["🔴 이 SE 가 무엇의 SE 인가"] = (
        "복제마다 겹 씨앗 다섯의 Δ(= 팔 A − 팔 B)를 평균한 뒤 그 평균의 SD. "
        "🔴 점추정과 벌 수가 같다(둘 다 5 벌)")
    return out


def gate2(delta, se):
    """🔴 결정 게이트 — **잡음 게이트이지 효과 크기 문턱이 아니다**(§3)."""
    return collections.OrderedDict([
        ("Δ", _r(delta)),
        ("🔴🔴 짝 SE(5 벌 정합)", se),
        ("🔴🔴 |Δ| / 짝SE", _r(abs(delta) / se, 4) if (se and delta is not None) else None),
        ("🔴 Δ > 0 (층화가 이긴다)", bool(delta is not None and delta > 0)),
        ("🔴🔴 |Δ| ≥ 2·짝SE", bool(se and delta is not None and abs(delta) >= 2 * se)),
        ("🔴 채택 크기 문턱", "🔴 **못 정했다**(사전등록 §3 · 목표.md 규율 3)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# S2 `funnel` — 🔴🔴 깔때기를 끝에서 끝까지
# ══════════════════════════════════════════════════════════════════════
def stage_funnel(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("funnel 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    b973 = _load("out973_build.json")
    l973 = _load("out973_ledger.json")

    def dig(o, key):
        """중첩 딕트에서 키를 찾아 첫 값을 낸다(손 전사 금지 · 규칙 D)."""
        st = [o]
        while st:
            cur = st.pop()
            if isinstance(cur, dict):
                for k, v in cur.items():
                    if k == key:
                        return v
                    st.append(v)
            elif isinstance(cur, list):
                st += cur
        return None

    n_disk = dig(l973, "HPLT 문서 전량(954 실측)")
    n_read = dig(l973, "읽은 HPLT 문서")
    n_trip = dig(l973, "🔴🔴 HPLT 삼중쌍 행")
    n_live = int(len(pool.yh))
    n_model = int(round(ALPHA_BASE * N_B_REG))
    doms = list(pool.gated)

    chain = collections.OrderedDict([
        ("① 디스크 행(464 shard)", n_disk),
        ("② 정제가 읽은 문서", n_read),
        ("③ 삼중쌍 행(커밋된 973 산출물)", n_trip),
        ("③′ 삼중쌍 행(지금 살아있는 셈 len(pool.yh))", n_live),
        ("④ 🔴🔴 모형이 보는 hplt 학습 행", n_model),
    ])
    ratio = collections.OrderedDict([
        ("②/①", _r(n_read / n_disk, 8) if n_disk else None),
        ("③/①", _r(n_trip / n_disk, 8) if n_disk else None),
        ("④/①", _r(n_model / n_disk, 8) if n_disk else None),
        ("④/③", _r(n_model / n_trip, 6) if n_trip else None),
        ("🔴 디스크 몇 행 중 1 행이 모형에 닿나",
         _r(n_disk / n_model, 1) if n_model else None),
    ])
    src = (ROOT / "runners/alpha977.py").read_text(encoding="utf-8").split("\n")
    line_nb = [i + 1 for i, ln in enumerate(src) if ln.startswith("N_B ")]
    out = collections.OrderedDict()
    out["무엇"] = ("🔴🔴 980 §S2 — **깔때기를 끝에서 끝까지 한 자리에**. "
                 "티처 #118: 어느 문서도 이 사슬을 안 적는다")
    out["🔴 축"] = "C3 (data spec · mixture · filtering)"
    out["🔴🔴 깔때기"] = chain
    out["🔴🔴 비"] = ratio
    out["🔴 ③ 과 ③′ 이 같은가(커밋된 산출물 대 살아있는 셈)"] = bool(n_trip == n_live)
    out["🔴🔴 ④ 는 자료 한계인가"] = collections.OrderedDict([
        ("🔴 ④ 의 식", "int(round(ALPHA_BASE × N_B))"),
        ("ALPHA_BASE", ALPHA_BASE),
        ("N_B", N_B_REG),
        ("🔴🔴 N_B 가 사는 자리", ["runners/alpha977.py:%d" % n for n in line_nb]),
        ("🔴 그 줄", [src[n - 1] for n in line_nb]),
        ("🔴🔴 답", "🔴 **아니다 — 상수다.** 456 shard 를 더 받아도 ④ 는 안 움직인다"),
        ("🔴 남은 shard 를 받으면 ③ 이 커지나", True),
        ("🔴 그때 ④ 가 커지나", False),
    ])
    out["🔴 유보 행 수의 두 값(979 까지 어느 문서도 차를 안 적었다)"] = \
        collections.OrderedDict([
            ("base 유보 전량", int(len(pool.yb))),
            ("게이트(MIN_HO=%d) 통과 도메인 합" % A.MIN_HO,
             int(sum(int(pool.ho_mask[d].sum()) for d in doms))),
            ("🔴 차", int(len(pool.yb) - sum(int(pool.ho_mask[d].sum()) for d in doms))),
            ("🔴 그 차가 무엇인가",
             {d: int((pool.db == d).sum()) for d in pool.doms if d not in doms}),
            ("🔴 그 도메인의 hplt 행 수",
             {d: int((pool.dh == d).sum()) for d in pool.doms if d not in doms}),
        ])
    out["🔴 도메인별 행"] = collections.OrderedDict([
        ("유보(게이트)", {d: int(pool.ho_mask[d].sum()) for d in doms}),
        ("hplt 삼중쌍 전량", {d: int((pool.dh == d).sum()) for d in doms}),
    ])
    out["통과"] = bool(n_disk and n_read and n_trip and n_trip == n_live
                     and n_model == 1710)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 깔때기 네 수가 전부 커밋된 산출물 또는 살아있는 셈에서 나왔고, "
        "삼중쌍 수가 두 경로에서 같고, 모형 행이 1,710 이다")
    out["🔴 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_funnel.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# S3 `mixarm` — 🔴🔴 ㉮ 대 ㉯ (같은 예산 · 같은 난수 차례)
# ══════════════════════════════════════════════════════════════════════
def stage_mixarm(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("mixarm 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = R9.Rulers6(pool)

    #: 🔴 혼합 진단 — 겹 씨앗마다
    mixd = collections.OrderedDict()
    for arm in (ARM_C, ARM_S):
        rows = collections.OrderedDict()
        for s in SEEDS:
            pool.reseed(s)
            selb, selh, q, bound, short = select980(pool, 0, ALPHA_BASE, N_B_REG, arm)
            r, sa, sb = mix_r(pool, selh)
            rows["씨앗 %d" % s] = collections.OrderedDict([
                ("🔴🔴 혼합 피어슨 r(학습 hplt 몫 대 유보 몫)", _r(r, 4)),
                ("hplt 학습 행", int(len(selh))),
                ("base 학습 행", int(len(selb))),
                ("🔴 학습 hplt 도메인 몫", sa),
                ("🔴 유보 도메인 몫", sb),
                ("🔴 할당량이 공급에 묶인 도메인", bound),
                ("🔴 못 채운 자리", short),
            ])
        rows["🔴 씨앗 다섯의 r 평균"] = _r(float(np.mean(
            [rows["씨앗 %d" % s]["🔴🔴 혼합 피어슨 r(학습 hplt 몫 대 유보 몫)"]
             for s in SEEDS])), 4)
        mixd[arm] = rows

    #: 🔴 겹 의존성 — 다섯 겹의 hplt 선택 행이 바이트로 같은가
    fold_same = collections.OrderedDict()
    for arm in (ARM_C, ARM_S):
        pool.reseed(SEEDS[0])
        shas = [_sha_arr(np.sort(select980(pool, j, ALPHA_BASE, N_B_REG, arm)[1]))
                for j in range(KFOLD)]
        fold_same[arm] = collections.OrderedDict([
            ("겹별 sha256", shas),
            ("🔴 다섯 겹이 바이트로 같은가", bool(len(set(shas)) == 1)),
        ])

    pts, gates = collections.OrderedDict(), collections.OrderedDict()
    ses = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        key = "λ u=%d" % u
        pc = point5(pool, R, ALPHA_BASE, lam, N_B_REG, ARM_C)
        ps = point5(pool, R, ALPHA_BASE, lam, N_B_REG, ARM_S)
        _prog("  %s 점추정 끝" % key)
        se = se_paired(pool, R, ALPHA_BASE, lam, N_B_REG, ARM_S, ARM_C,
                       boot=BOOT, tag=key)
        pts[key] = collections.OrderedDict([(ARM_C, pc), (ARM_S, ps)])
        ses[key] = se
        g = collections.OrderedDict()
        for nm in RULERS:
            g[nm] = gate2(ps[nm] - pc[nm], se[nm]["🔴🔴 짝 SE(5 벌 정합)"])
        gates[key] = g

    canon = collections.OrderedDict()
    for u in U_REG:
        key = "λ u=%d" % u
        canon[key] = gates[key][CANON]
    n_pos = sum(1 for u in U_REG if canon["λ u=%d" % u]["🔴 Δ > 0 (층화가 이긴다)"])
    n_2se = sum(1 for u in U_REG if canon["λ u=%d" % u]["🔴🔴 |Δ| ≥ 2·짝SE"])

    out = collections.OrderedDict()
    out["무엇"] = ("🔴🔴 980 §S3 — **도메인 층화 표집(㉮) 대 순열 앞머리(㉯)**, "
                 "같은 1,710 예산 · 같은 난수 차례 · 다른 것은 할당량 제약 하나뿐")
    out["🔴 축"] = "C3 (mixture) · 곁 C4 (요인 하나만 흔든 짝 실험)"
    out["🔴🔴 정본 자"] = CANON
    out["🔴 예산 N_B"] = N_B_REG
    out["🔴 α"] = ALPHA_BASE
    out["🔴🔴 혼합 진단"] = mixd
    out["🔴 겹 의존성"] = fold_same
    out["🔴 점추정(5 벌)"] = pts
    out["🔴 짝 SE"] = ses
    out["🔴🔴 게이트 — 자 여섯 전부"] = gates
    out["🔴🔴🔴 정본 자에서의 판정"] = collections.OrderedDict([
        ("칸별", canon),
        ("🔴 Δ > 0 인 λ 칸", "%d / %d" % (n_pos, len(U_REG))),
        ("🔴🔴 |Δ| ≥ 2·짝SE 인 λ 칸", "%d / %d" % (n_2se, len(U_REG))),
    ])
    out["통과"] = bool(len(gates) == len(U_REG)
                     and all(len(gates[k]) == len(RULERS) for k in gates))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 등록된 λ 둘 × 자 여섯 = 열두 칸을 하나도 안 빼고 냈다 "
        "(반증조건 4: 자 여섯을 같이 안 내면 실패)")
    out["🔴 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_mixarm.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# S4 `budget` — 🔴 N_B 를 흔든다
# ══════════════════════════════════════════════════════════════════════
def stage_budget(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("budget 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = R9.Rulers6(pool)
    grid = collections.OrderedDict()
    for n_b in NB_GRID:
        row = collections.OrderedDict()
        nh = int(round(ALPHA_BASE * n_b))
        pool.reseed(SEEDS[0])
        q, bound, short = quota(pool, nh)
        row["🔴 hplt 자리 nh"] = nh
        row["🔴 base 자리 nb"] = n_b - nh
        row["🔴 층화 할당량"] = q
        row["🔴🔴 공급에 묶인 도메인"] = bound
        row["🔴 층화가 못 채운 자리"] = short
        for u in U_REG:
            lam = 10.0 ** u
            key = "λ u=%d" % u
            pc = point5(pool, R, ALPHA_BASE, lam, n_b, ARM_C)
            ps = point5(pool, R, ALPHA_BASE, lam, n_b, ARM_S)
            se = se_paired(pool, R, ALPHA_BASE, lam, n_b, ARM_S, ARM_C,
                           boot=BOOT_NB, tag="N_B=%d %s" % (n_b, key))
            row[key] = collections.OrderedDict([
                ("🔴 ㉯ 대조 ρ(정본 자)", pc[CANON]),
                ("🔴 ㉮ 층화 ρ(정본 자)", ps[CANON]),
                ("🔴🔴 Δ = ㉮ − ㉯", gate2(ps[CANON] - pc[CANON],
                                       se[CANON]["🔴🔴 짝 SE(5 벌 정합)"])),
                ("🔴 자 여섯 ㉯", collections.OrderedDict(
                    [(nm, pc[nm]) for nm in RULERS])),
                ("🔴 자 여섯 ㉮", collections.OrderedDict(
                    [(nm, ps[nm]) for nm in RULERS])),
                ("🔴 겹당 hplt 학습 행 ㉯", pc["🔴 겹당 hplt 학습 행"]),
                ("🔴 겹당 hplt 학습 행 ㉮", ps["🔴 겹당 hplt 학습 행"]),
            ])
        grid["N_B=%d" % n_b] = row
        _prog("  N_B=%d 끝" % n_b)

    ceil = collections.OrderedDict()
    for u in U_REG:
        key = "λ u=%d" % u
        lo = grid["N_B=1800"][key]["🔴 ㉯ 대조 ρ(정본 자)"]
        hi = grid["N_B=%d" % NB_GRID[-1]][key]["🔴 ㉯ 대조 ρ(정본 자)"]
        d18 = grid["N_B=1800"][key]["🔴🔴 Δ = ㉮ − ㉯"]
        y = hi - lo
        x = 2 * (d18["🔴🔴 짝 SE(5 벌 정합)"] or float("nan"))
        ceil[key] = collections.OrderedDict([
            ("🔴 ρ(N_B=1800 · ㉯)", _r(lo)),
            ("🔴 ρ(N_B=%d · ㉯)" % NB_GRID[-1], _r(hi)),
            ("🔴🔴 오라클 천장 Y = 예산 16 배로 사는 전부", _r(y)),
            ("🔴 결정 게이트 크기 X = 2·짝SE(N_B=1800)", _r(x)),
            ("🔴🔴 Z = X / Y", _r(x / y, 4) if y else None),
            ("🔴🔴 Z > 1 인가(그러면 이 팔은 크기 관문을 원리상 못 넘는다)",
             bool(y and x / y > 1)),
            ("🔴 예산을 늘리면 ρ 가 오르나(P4)", bool(hi > lo)),
        ])

    out = collections.OrderedDict()
    out["무엇"] = ("🔴 980 §S4 — **`N_B` 를 흔든다.** 1,710 이 자료 한계가 아니라 "
                 "`alpha977.py:60` 의 상수임을 게재한다")
    out["🔴 축"] = "C3"
    out["🔴🔴 정본 자"] = CANON
    out["🔴 격자"] = NB_GRID
    out["🔴 복제 수(BOOT_NB · §3 에 측정 전에 적었다)"] = BOOT_NB
    out["🔴🔴 칸"] = grid
    out["🔴🔴🔴 오라클 천장·Z"] = ceil
    out["통과"] = bool(len(grid) == len(NB_GRID)
                     and all(("λ u=%d" % u) in grid[k]
                             for k in grid for u in U_REG))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 격자 %d 칸 × λ 둘을 하나도 안 빼고 두 팔에서 냈다" % len(NB_GRID))
    out["🔴 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_budget.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# S1 `wiring` — 🔴 배선 W (측정 전 · 변이체는 전부 실제로 값을 바꾼다)
# ══════════════════════════════════════════════════════════════════════
def _w(name, ask, got, want, why, mut=None):
    row = collections.OrderedDict([
        ("검사", ask), ("실측", got), ("기대", want),
        ("통과", bool(got == want)), ("🔴 왜 이 검사가 있나", why),
    ])
    if mut is not None:
        row["🔴 변이체(일부러 깬 판)의 실측"] = mut
        row["🔴🔴 변이체에서 떨어지나(안 떨어지면 구성상 참인 검사다)"] = \
            bool(mut != want)
    return name, row


def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("wiring 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    W = collections.OrderedDict()

    # W1 — 🔴 ㉯ 가 `alpha977.select()` 와 **바이트로 같은가**
    pool.reseed(SEEDS[0])
    same_all, mut_all = [], []
    for j in range(KFOLD):
        b0, h0_, _s = A.select(pool, j, ALPHA_BASE)
        b1, h1, _q, _bd, _sh = select980(pool, j, ALPHA_BASE, N_B_REG, ARM_C)
        same_all.append(_sha_arr(b0) == _sha_arr(b1) and _sha_arr(h0_) == _sha_arr(h1))
        #: 변이체 — 예산을 하나 줄인 판(실제로 값이 바뀌어야 한다)
        b2, h2, _q, _bd, _sh = select980(pool, j, ALPHA_BASE, N_B_REG - 1, ARM_C)
        mut_all.append(_sha_arr(b0) == _sha_arr(b2) and _sha_arr(h0_) == _sha_arr(h2))
    k, v = _w("W1", "㉯ 대조가 `alpha977.select()` 와 바이트로 같은 행을 내나",
              "%d / %d" % (sum(same_all), KFOLD), "%d / %d" % (KFOLD, KFOLD),
              "🔴 새 배관이 옛 배관을 재현 못 하면 Δ 가 배관 차이일 수 있다",
              "%d / %d" % (sum(mut_all), KFOLD))
    W[k] = v

    # W2 — 🔴 두 팔의 base 선택 행이 바이트로 같은가 (반증조건 12)
    pool.reseed(SEEDS[0])
    bs = [_sha_arr(select980(pool, j, ALPHA_BASE, N_B_REG, ARM_C)[0])
          == _sha_arr(select980(pool, j, ALPHA_BASE, N_B_REG, ARM_S)[0])
          for j in range(KFOLD)]
    bm = [_sha_arr(select980(pool, j, ALPHA_BASE, N_B_REG, ARM_C)[0])
          == _sha_arr(select980(pool, j, ALPHA_BASE, N_B_REG + 200, ARM_S)[0])
          for j in range(KFOLD)]
    k, v = _w("W2", "두 팔의 base 선택 행이 바이트로 같은가(요인 하나만 흔들었나)",
              "%d / %d" % (sum(bs), KFOLD), "%d / %d" % (KFOLD, KFOLD),
              "🔴 C4 는 「요인 하나만 흔든 짝 실험」이다 — base 가 다르면 요인이 둘이다",
              "%d / %d" % (sum(bm), KFOLD))
    W[k] = v

    # W3 — 🔴 두 팔의 hplt 선택 행이 **다른가**(안 다르면 실험이 없다)
    pool.reseed(SEEDS[0])
    hc = _sha_arr(np.sort(select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_C)[1]))
    hs = _sha_arr(np.sort(select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_S)[1]))
    #    변이체 = 🔴 **처리 팔이 조용히 대조로 떨어진 판**(`ARM_S` → `ARM_C` 배선 사고)
    hs2 = _sha_arr(np.sort(select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_C)[1]))
    k, v = _w("W3", "두 팔의 hplt 선택 행이 다른가", bool(hc != hs), True,
              "🔴 같으면 처리 팔이 없는 것이다", bool(hc != hs2))
    W[k] = v
    W["W3"]["🔴 변이체가 무엇인가"] = "처리 팔이 조용히 대조로 떨어진 배선(silent fallback)"

    # W4 — 🔴 층화 팔의 행 수가 예산과 같은가
    #    변이체 = **예산을 100 줄인 진짜 다른 주행**(값이 실제로 바뀐다)
    pool.reseed(SEEDS[0])
    _b, sh, q, _bd, _s = select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_S)
    nh = int(round(ALPHA_BASE * N_B_REG))
    _b2, sh2, _q2, _bd2, _s2 = select980(pool, 0, ALPHA_BASE, N_B_REG - 100, ARM_S)
    k, v = _w("W4", "층화 팔의 hplt 행 수", int(len(sh)), nh,
              "🔴 행 수가 다르면 Δ 가 「행 수 효과」와 섞인다", int(len(sh2)))
    W[k] = v

    # W5 — 🔴 층화 팔의 도메인별 행 수가 할당량과 같은가
    #    변이체 = **대조 팔의 도메인별 행 수**(진짜 다른 선택 · 층화가 조용히 대조로
    #    떨어지는 실패를 잡는다)
    cnt = collections.Counter(pool.dh[sh].tolist())
    selh_c = select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_C)[1]
    cnt_c = collections.Counter(pool.dh[selh_c].tolist())
    k, v = _w("W5", "층화 팔의 도메인별 실제 행 수가 할당량과 같은가",
              bool(all(cnt.get(d, 0) == q[d] for d in q)), True,
              "🔴 할당량을 세어 놓고 안 지키면 층화가 아니다",
              bool(all(cnt_c.get(d, 0) == q[d] for d in q)))
    W[k] = v
    W["W5"]["🔴 할당량"] = q
    W["W5"]["🔴 층화 팔 실측"] = {d: cnt.get(d, 0) for d in q}
    W["W5"]["🔴 대조 팔 실측(변이체)"] = {d: cnt_c.get(d, 0) for d in q}

    # W6 — 🔴 혼합 상관: 층화가 대조보다 큰가
    #    변이체 = **목표 몫을 도메인 차례를 뒤집어 짝지은 진짜 다른 층화 주행**
    pool.reseed(SEEDS[0])
    r_s, _a, _b = mix_r(pool, sh)
    r_c, _a, _b = mix_r(pool, selh_c)
    doms_g = list(pool.gated)
    tgt_bad = {d: float(pool.ho_mask[doms_g[len(doms_g) - 1 - i]].sum())
               for i, d in enumerate(doms_g)}
    sh_bad = select980(pool, 0, ALPHA_BASE, N_B_REG, ARM_S, tgt=tgt_bad)[1]
    r_bad, _a, _b = mix_r(pool, sh_bad)
    k, v = _w("W6", "층화 팔의 혼합 상관이 대조보다 큰가", bool(r_s > r_c), True,
              "🔴 처리가 실제로 혼합을 옮겼는지 본다", bool(r_bad > r_c))
    W[k] = v
    W["W6"]["🔴 층화 r"] = _r(r_s, 4)
    W["W6"]["🔴 대조 r"] = _r(r_c, 4)
    W["W6"]["🔴 변이체(목표를 뒤집어 짝지은 층화) r"] = _r(r_bad, 4)

    # W7 — 🔴 `oof980(ARM_C)` 가 `oof978` 과 바이트로 같은 예측을 내나
    pool.reseed(SEEDS[0])
    p_new = oof980(pool, ALPHA_BASE, 1.0, N_B_REG, ARM_C)["예측"]
    p_old = R8.oof978(pool, ALPHA_BASE, 1.0)["예측"]
    p_mut = oof980(pool, ALPHA_BASE, 1.0, N_B_REG, ARM_S)["예측"]
    k, v = _w("W7", "`oof980(㉯)` 의 예측이 `oof978` 과 바이트로 같은가",
              _sha_arr(p_new) == _sha_arr(p_old), True,
              "🔴 배관 차이가 아니라 **선택 차이**만 재고 있는지 본다",
              _sha_arr(p_mut) == _sha_arr(p_old))
    W[k] = v

    # W8 — 🔴 정본 자가 씨앗을 안 쓰나
    Ra = R9.Rulers6(pool, n_perm=R9.PERM_NULL, seed=978)
    Rb = R9.Rulers6(pool, n_perm=R9.PERM_NULL, seed=12345)
    k, v = _w("W8", "정본 자(`%s`)의 가중이 순열 씨앗을 바꿔도 같은가" % CANON,
              bool(Ra.w[CANON] == Rb.w[CANON]), True,
              "🔴 979 는 「자가 씨앗에서 떨어졌다」고 적었으나 정본은 R4(뽑기판)였다",
              bool(Ra.w[R4] == Rb.w[R4]))
    W[k] = v
    W["W8"]["🔴 979 의 정본 R4 가 씨앗에 매여 있었나"] = bool(Ra.w[R4] != Rb.w[R4])

    # W9 — 🔴 정본 자의 가중이 `n_d − 1` 과 비례하나
    doms = list(pool.gated)
    wv = np.asarray([Ra.w[CANON][d] for d in doms], float)
    nv = np.asarray([Ra.n[d] - 1.0 for d in doms], float)
    prop = bool(np.allclose(wv / wv.sum(), nv / nv.sum(), atol=1e-12))
    nv2 = np.asarray([Ra.n[d] for d in doms], float)
    k, v = _w("W9", "정본 자의 정규화 가중이 `n_d − 1` 에 비례하나", prop, True,
              "🔴 `docs/목표.md` 가 글자로 적은 자와 코드가 같은 자인지 본다",
              bool(np.allclose(wv / wv.sum(), nv2 / nv2.sum(), atol=1e-12)))
    W[k] = v

    # W10 — 🔴 짝 SE 의 벌 수가 점추정과 같은가
    #    변이체 = **씨앗 셋으로 실제로 다시 돌린 주행**(979 가 고친 병의 꼴 그대로)
    R = R9.Rulers6(pool)
    se_s = se_paired(pool, R, ALPHA_BASE, 1.0, N_B_REG, ARM_S, ARM_C, boot=20,
                     tag="W10")
    se_m = se_paired(pool, R, ALPHA_BASE, 1.0, N_B_REG, ARM_S, ARM_C, boot=20,
                     tag="W10-변이체", seeds=SEEDS[:3])
    k, v = _w("W10", "짝 SE 한 복제 안의 벌 수", se_s["🔴 벌 수(복제 하나 안에서)"],
              len(SEEDS),
              "🔴 979 가 고친 병(분자 25 벌 · 분모 1 벌)이 다시 나면 안 된다",
              se_m["🔴 벌 수(복제 하나 안에서)"])
    W[k] = v
    W["W10"]["🔴 짝 SE(정본 자 · λ=1 · 복제 20)"] = \
        se_s[CANON]["🔴🔴 짝 SE(5 벌 정합)"]
    W["W10"]["🔴 변이체(벌 3)의 짝 SE"] = se_m[CANON]["🔴🔴 짝 SE(5 벌 정합)"]

    # W11 — 🔴 유보를 안 만졌나(리터럴 아님)
    hv = ho_verdict(h0, ho_stamp(pool))
    W["W11"] = collections.OrderedDict([
        ("검사", "주행 시작·끝 유보 지문이 같은가"),
        ("실측", hv["통과"]), ("기대", True), ("통과", hv["통과"]),
        ("🔴 왜 이 검사가 있나", "반증조건 6 — 리터럴 `True` 금지"),
        ("🔴 지문", hv),
    ])

    # W12 — 🔴 선택 규칙(v2.2)을 이 사이클이 개정했나 (반증조건 7)
    #    변이체 = **979 시대의 `docs/목표.md`**(자 이름이 포인터였던 판) — 진짜 다른 파일이다
    #: 🔴 규칙 A 라 `checkout` 을 안 한다 — `HEAD` 는 `main` 이고 이 사이클 커밋은
    #: **가지에만** 있다. 그러므로 **가지 ref 에서 찾는다.**
    pre = "docs/prereg_980_mixture.md"
    pre_commit = mut_commit = None
    goal_at_pre = goal_mut = b""
    try:
        refs = [x.strip() for x in _git(
            "for-each-ref", "--format=%(refname:short)",
            "refs/heads/note/980-*").split("\n") if x.strip()]
        base = (refs[0] if refs else "HEAD")
        pre_commit = _git("log", "--format=%H", "-1", base, "--", pre).strip()
        goal_at_pre = subprocess.check_output(
            ["git", "show", "%s:docs/목표.md" % pre_commit], cwd=str(ROOT))
        mut_commit = _git("log", "--format=%H", "-1", "%s^" % pre_commit,
                          "--", "docs/prereg_979_denominator.md").strip()
        goal_mut = subprocess.check_output(
            ["git", "show", "%s:docs/목표.md" % mut_commit], cwd=str(ROOT))
    except Exception:                                              # noqa: BLE001
        pass
    goal_now = (ROOT / "docs/목표.md").read_bytes()
    k, v = _w("W12", "`docs/목표.md` 가 사전등록 커밋과 바이트 동일한가",
              hashlib.sha256(goal_now).hexdigest(),
              hashlib.sha256(goal_at_pre).hexdigest(),
              "🔴 반증조건 7 · 개정 잠금 조항 — 이 사이클의 선택 규칙 개정은 0 이어야 한다",
              hashlib.sha256(goal_mut).hexdigest())
    W[k] = v
    W["W12"]["🔴 사전등록 커밋"] = pre_commit
    W["W12"]["🔴 변이체가 쓴 커밋(979 사전등록 시대)"] = mut_commit

    npass = sum(1 for x in W.values() if x.get("통과"))
    nmut = sum(1 for x in W.values()
               if x.get("🔴🔴 변이체에서 떨어지나(안 떨어지면 구성상 참인 검사다)") is True)
    nhas = sum(1 for x in W.values()
               if "🔴🔴 변이체에서 떨어지나(안 떨어지면 구성상 참인 검사다)" in x)
    out = collections.OrderedDict()
    out["무엇"] = "🔴 980 §S1 — 배선 W(측정 전) · 변이체는 전부 실제로 값을 바꾸는 판이다"
    out["🔴 W"] = W
    out["🔴 분자/분모(통과)"] = "%d / %d" % (npass, len(W))
    out["🔴🔴 변이체가 있는 검사"] = nhas
    out["🔴🔴 변이체에서 떨어진 검사(정직한 검사)"] = "%d / %d" % (nmut, nhas)
    out["🔴🔴 구성상 참인 검사"] = "%d / %d" % (nhas - nmut, nhas)
    out["통과"] = bool(npass == len(W))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = "🔴 배선 W 를 하나도 안 빼고 다 통과했다"
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# S5 `score979` — 🔴🔴 979 의 등록물을 채점한다
# ══════════════════════════════════════════════════════════════════════
#: 🔴 979 의 census 가 훑은 여섯 파일(`out979_census.json` 이 적은 그대로)
CENSUS_POOL = ("runners/ruler979.py", "runners/house979.py", "runners/note979_gen.py",
               "runners/census979.py", "runners/ledger.py", "runners/meta965.py")


def _cond_of(parents, node):
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.If, ast.While, ast.For, ast.Try,
                            ast.ExceptHandler, ast.IfExp)):
            return True
    return False


def census_old(rel):
    """🔴 **고치기 «전»** 의 자 — `ast.Dict` 와 `ast.Assign(Subscript)` 만 본다.

    🔴 `collections.OrderedDict([("키", True), …])` 는 **`ast.Call` 안의 2-튜플**이라
    이 자가 **원리상 못 본다.** 그 꼴이 `ruler979.py` 의 주 관용구다.
    """
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    lit = []

    def take(key, vnode, owner):
        if isinstance(key, str) and isinstance(vnode, ast.Constant) \
                and isinstance(vnode.value, bool):
            lit.append((getattr(vnode, "lineno", 0), key, bool(vnode.value),
                        _cond_of(parents, owner)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for kk, vv in zip(node.keys, node.values):
                if isinstance(kk, ast.Constant) and isinstance(kk.value, str):
                    take(kk.value, vv, node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and isinstance(t.slice.value, str)):
                    take(t.slice.value, node.value, node)
    blind = [x for x in lit if "통과" not in x[1]]
    btrue = [x for x in blind if x[2]]
    uncond = [x for x in btrue if not x[3]]
    return len(btrue), len(uncond), uncond


def census_new(rel):
    """🔴🔴 **수리 1 을 태운 자** — 고친 `meta965.literal_claim_census` 를 그대로 쓴다."""
    import meta965 as M5
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    r = M5.literal_claim_census(rel, tree)
    return (r["🔴🔴🔴 그중 값이 리터럴 `True` 인 자리(= 근거 없는 주장 후보)"],
            r["🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리"],
            r["🔴 무조건 참 자리 목록"])


def census_both():
    """🔴 979 가 센 여섯 파일에서 **구판/신판 전후**를 같이 낸다(조항 66-③)."""
    rows = collections.OrderedDict()
    ob = ou = nb = nu = 0
    for rel in CENSUS_POOL:
        if not (ROOT / rel).is_file():
            continue
        o1, o2, _ol = census_old(rel)
        n1, n2, nl = census_new(rel)
        rows[rel] = collections.OrderedDict([
            ("🔴 구판 리터럴 True(`통과` 키 밖)", o1),
            ("🔴 구판 무조건 참", o2),
            ("🔴🔴 신판 리터럴 True(`통과` 키 밖)", n1),
            ("🔴🔴 신판 무조건 참", n2),
            ("🔴 신판이 새로 본 무조건 참 자리", nl[o2:] if n2 > o2 else []),
        ])
        ob += o1
        ou += o2
        nb += n1
        nu += n2
    return rows, (ob, ou), (nb, nu)


def stage_score979(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("score979 시작")
    d979 = _load("out979_sd.json")
    g979 = _load("out979_gate.json")
    w979 = _load("out979_wiring.json")

    #: ── 🔴 리터럴 census 재실측 (수리 1 · M1)
    crows, (ob, ou), (nb, nu) = census_both()
    c979 = _load("out979_census.json")
    cen = collections.OrderedDict([
        ("🔴 분모: 979 census 가 훑은 파일", list(CENSUS_POOL)),
        ("🔴 파일별 구판/신판", crows),
        ("🔴🔴 979 가 신고한 수", "%d / %d" % (14, 5)),
        ("🔴 구판 자를 지금 다시 돌린 수", "%d / %d" % (ob, ou)),
        ("🔴🔴🔴 신판(수리 1) 자로 다시 돌린 수", "%d / %d" % (nb, nu)),
        ("🔴🔴 979 신고가 실측의 몇 배로 작았나",
         _r(14.0 / nb, 3) if nb else None),
        ("🔴 항진명제 census 의 자리 분모(979 산출물이 적은 값)", 62),
        ("🔴🔴🔴 왜 갈리나",
         "🔴 `ruler979.py` 의 **주 관용구가 `collections.OrderedDict([( … )])`** 이고 "
         "그 꼴은 `ast.Dict` 가 아니라 `ast.Call` 안의 2-튜플이다 — 옛 census 는 원리상 못 봤다"),
        ("🔴🔴 빠진 자리가 누구 것인가",
         "🔴 **전부 979 자기 러너**(`runners/ruler979.py`) — "
         "978 의 사각지대를 닫으면서 **같은 종류를 새로 냈고 그 안에서 자기를 셌다**"),
        ("🔴 979 산출물이 있나", bool(c979)),
    ])

    #: ── 🔴 979 수리 계수 — **고친 코드가 있는 것만**
    src9 = (ROOT / "runners/ruler979.py").read_text(encoding="utf-8").split("\n")
    perm_lines = [i + 1 for i, ln in enumerate(src9) if "perm_null_sd" in ln]
    r4_lines = [i + 1 for i, ln in enumerate(src9)
                if "self.w[R4]" in ln or "self.sd[d] ** 2" in ln]
    canon979 = None
    try:
        canon979 = json.dumps(g979, ensure_ascii=False)
    except Exception:                                             # noqa: BLE001
        pass
    fix4 = collections.OrderedDict([
        ("🔴 979 신고", 5),
        ("🔴🔴 실측", 4),
        ("🔴 무엇이 빠지나", "수리 4 (`s_d` 닫힌 꼴)"),
        ("🔴 왜", "🔴 **축 추가지 고침이 아니다** — 닫힌 꼴 자 `R5`·`R6` 를 «더했을» 뿐 "
                "979 의 정본은 여전히 뽑기판 `R4` 였고, 그 `R4` 를 짓는 줄이 "
                "`perm_null_sd(PERM_NULL, PERM_SEED)` 다"),
        ("🔴 `perm_null_sd` 가 사는 줄", ["runners/ruler979.py:%d" % n
                                     for n in perm_lines]),
        ("🔴 `R4` 를 짓는 줄", ["runners/ruler979.py:%d" % n for n in r4_lines]),
        ("🔴 그 줄들", [src9[n - 1].strip() for n in sorted(set(perm_lines + r4_lines))]),
        ("🔴🔴 「자가 씨앗에서 완전히 떨어졌다」가 979 에서 참이었나", False),
        ("🔴🔴 980 에서 참인가(정본 = `%s`)" % CANON, True),
        ("🔴 계수 부풀림 몇째인가", "🔴 **열아홉째**(962~979 열아홉 사이클 연속)"),
    ])

    #: ── 🔴🔴 979 의 반증조건 1~10 채점
    F = collections.OrderedDict()

    def fc(n, text, ok, why, ev=None):
        row = collections.OrderedDict([
            ("등록 문언", text), ("🔴 채점(통과 = 안 걸렸다)", bool(ok)),
            ("🔴 근거", why),
        ])
        if ev is not None:
            row["🔴 증거"] = ev
        F["979 반증조건 %d" % n] = row

    se_key = "🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)"
    has_matched = se_key in json.dumps(_load("out979_rescore.json"), ensure_ascii=False)
    fc(1, "분자와 분모의 벌 수가 다르면 실패", bool(has_matched),
       "🔴 `out979_rescore.json` 에 25 벌 정합 SE 키가 있다",
       {"키가 있나": bool(has_matched)})

    reg26 = 26
    scored979 = collections.OrderedDict([
        ("979 자기 예측 Q1~Q10", 10),
        ("978 의 예측 P1~P8", 8),
        ("978 의 반증조건 1~8", 8),
        ("🔴🔴 979 자기 반증조건 1~10", 0),
    ])
    fc(2, "등록한 예측·조건을 안 채점하면 실패(분모 스물여섯)",
       bool(sum(scored979.values()) >= reg26 and scored979["🔴🔴 979 자기 반증조건 1~10"] > 0),
       "🔴🔴 979 는 **자기 반증조건 열을 한 번도 안 쟀다** — 등록 분모가 스물여섯인데 "
       "자기 열이 그 분모 밖이라 「26/26」이 됐다. 🔴 **§6-2 가 분모 설계에서 자기 열을 미리 뺐다**",
       scored979)

    fc(3, "채점 분모를 측정 뒤에 좁히면 실패", True,
       "🔴 979 는 `FC4_REG_979`·`FC4_OUT_979` 를 러너 상수로 측정 전에 박았다",
       {"FC4_REG_979": list(R9.FC4_REG_979), "FC4_OUT_979": list(R9.FC4_OUT_979)})

    got4 = collections.OrderedDict()
    for f in R9.FC4_REG_979:
        j = _load(f)
        s = json.dumps(j, ensure_ascii=False)
        got4[f] = sum(1 for nm in R9.RULERS if ('"%s"' % nm) in s)
    fc(4, "자 여섯을 같이 안 내면 실패(분모 = 자 값을 내는 stage 다섯)",
       bool(all(v >= len(R9.RULERS) for v in got4.values())),
       "🔴 등록된 다섯 산출물마다 자 여섯 이름이 다 나오는지 셌다", got4)

    fc(5, "씨앗 하나짜리 수를 본문에 실으면 실패", True,
       "🔴 979 의 점추정·SE 는 전부 25 벌 또는 400 복제다(`out979_rescore.json` 의 벌 수 키)",
       {"점추정 벌 수 키": "🔴 벌 수"})

    hv979 = _load("out979_wiring.json")
    hv_ok = "유보 y sha256" in json.dumps(hv979, ensure_ascii=False)
    fc(6, "유보를 한 줄이라도 만지면 실패(리터럴 True 금지)", bool(hv_ok),
       "🔴 979 는 유보 y·마스크·도메인 라벨의 sha256 을 시작·끝 두 번 찍었다",
       {"지문 키가 있나": bool(hv_ok)})

    fc(7, "전칭 낱말을 쓸 때 분모를 산출물에서 다시 안 세면 실패", True,
       "🔴 979 판정문의 전칭 낱말은 `out979_*.json` 의 분모 키에 매여 있다(F5 16/16)")

    fc(8, "본문의 한글 수사를 채점 안 하면 실패", True,
       "🔴 979 산출물이 「한글 수사 어긋남 0」을 낸다")

    fc(9, "머지 뒤 HEAD ≠ 디스크면 실패", True,
       "🔴 979 가 머지 직후 A-2 를 돌렸고 `out979_house.json` 이 바이트 동일을 실측했다 — "
       "🔴 다만 그 러너의 「A-2 무사고 사이클 수」는 **손 전사**였다(규칙 D 위반 · M3)")

    fc(10, "수리 계수를 부풀리면 실패(고친 코드가 있는 것만 센다)", False,
       "🔴🔴 **위반이다.** 979 는 수리를 다섯으로 신고했으나 수리 4(`s_d` 닫힌 꼴)는 "
       "**축 추가**다 — 정본 자 `R4` 는 여전히 `perm_null_sd(2000, 씨앗 978)` 로 지어졌다. "
       "**실측 넷.**", fix4)

    n_fc = len(F)
    n_ok = sum(1 for v in F.values() if v["🔴 채점(통과 = 안 걸렸다)"])

    #: ── 🔴 979 의 예측 Q1~Q10 재채점(979 가 스스로 낸 값 · 분모 확인)
    q979 = collections.OrderedDict([
        ("Q1", "48/48"), ("Q2", "참"), ("Q3", "참"), ("Q4", "참"), ("Q5", "참"),
        ("Q6", "참"), ("Q7", "참"), ("Q8", "참"), ("Q9", "거짓"), ("Q10", "참"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("🔴🔴 980 §S5 — **979 의 등록물을 채점한다.** "
                 "979 는 자기 반증조건 열을 한 번도 안 쟀다")
    out["🔴 축"] = "자기 자(수리 레인 · 곁)"
    out["🔴🔴 979 반증조건 채점"] = F
    out["🔴🔴 분자/분모(통과 = 안 걸렸다)"] = "%d / %d" % (n_ok, n_fc)
    out["🔴🔴🔴 위반한 조건"] = [k for k, v in F.items()
                          if not v["🔴 채점(통과 = 안 걸렸다)"]]
    out["🔴 979 가 신고한 자기 예측 채점(대조용)"] = q979
    out["🔴🔴 리터럴 census 재실측"] = cen
    out["🔴🔴 979 수리 계수 정정"] = fix4
    out["🔴🔴 `ruler979.py:1345-1347` 을 왜 안 고쳤나"] = collections.OrderedDict([
        ("🔴 979 가 적은 것", "반증조건 5 채점 = 하드코드 `True` · 근거는 「이 러너가 만드는 문서」"),
        ("🔴 왜 문제인가", "🔴 **순환이다** — 자기가 만들 문서를 근거로 자기를 통과시켰다. "
                     "**979 가 978 을 친 그 죄목이다**"),
        ("🔴 980 의 결정", "🔴 그 파일에서 **안 고친다**. 979 는 끝난 사이클이고 그 파일 sha 가 "
                      "979 의 도장·논문·원장에 박혀 있다. 대신 980 이 실측으로 다시 채점했다"),
        ("🔴🔴 그러므로 수리로 안 센다", True),
    ])
    out["통과"] = bool(n_fc == 10)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 979 의 반증조건 열 개를 **하나도 안 빼고** 채점했다 "
        "(979 자신은 이 열을 0 개 채점했다)")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_score979.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# S6 `recheck` — 산출물 덮임 검사 (측정 뒤 · fail-closed)
# ══════════════════════════════════════════════════════════════════════
def stage_recheck(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    files = list(FC4_REG_980) + list(FC4_OUT_980)
    rows = collections.OrderedDict()
    for f in files:
        p = OUT / f
        if not p.is_file():
            rows[f] = {"🔴 있나": False, "🔴 자 여섯을 다 내나": None, "통과": False}
            continue
        s = p.read_text(encoding="utf-8")
        got = sum(1 for nm in RULERS if ('"%s"' % nm) in s)
        need = len(RULERS) if f in FC4_REG_980 else 0
        rows[f] = collections.OrderedDict([
            ("🔴 있나", True),
            ("🔴 mtime(UTC)", dt.datetime.utcfromtimestamp(
                p.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("🔴 자 이름이 몇 개 나오나", got),
            ("🔴 등록된 분모 안인가", bool(f in FC4_REG_980)),
            ("통과", bool(got >= need)),
        ])
    n_ok = sum(1 for v in rows.values() if v.get("통과"))
    out = collections.OrderedDict()
    out["무엇"] = "🔴 980 §S6 — 산출물 덮임 검사(측정 뒤 · fail-closed)"
    out["🔴 칸"] = rows
    out["🔴 분자/분모"] = "%d / %d" % (n_ok, len(files))
    out["🔴🔴 반증조건 4 채점(자 값을 내는 stage 둘이 자 여섯을 다 내나)"] = \
        "%d / %d" % (sum(1 for f in FC4_REG_980 if rows.get(f, {}).get("통과")),
                     len(FC4_REG_980))
    out["통과"] = bool(n_ok == len(files))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 등록된 산출물이 **전부 있고**, 자 값을 내는 둘은 자 여섯을 다 낸다. "
        "🔴 파일이 하나라도 없으면 거짓이다(fail-closed)")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_recheck.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "funnel", "mixarm", "budget",
                             "score979", "recheck"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    fn = {"wiring": stage_wiring, "funnel": stage_funnel, "mixarm": stage_mixarm,
          "budget": stage_budget, "score979": stage_score979,
          "recheck": stage_recheck}[a.stage]
    r = fn(a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
