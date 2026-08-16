#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""982 — 🔴🔴 **이득 소멸의 기전을, 검정력부터 재고 다시 묻는다** (축 C3 · 곁 C4).

사전등록 `docs/prereg_982_timeforward.md` §3 를 그대로 따른다.

🔴 **981 의 「두 설명이 둘 다 진다」가 자기 데이터에 반박된다**(티처 #120 C5).
위약 팔 `㉱` 의 `u=3` 이득이 **7 칸 중 6 칸 양수 · 단조 감소**이고 대조 혼합 SD 와
**스피어만 `1.0`** 인데, 981 은 **칸별 관문(`2·짝SE`)을 하나도 못 넘었다**는 이유로
수렴 설명을 죽였다. 🔴 **그 관문의 최소 검출 크기가 첫 칸 이득의 28.2% 다.**

그래서 이 러너는 셋을 한다.
    §1 🔴 **MDE 를 먼저 싣는다** — 그리고 「복제를 늘리면 MDE 가 주는가」를 **잰다**(주장 안 한다).
    §2 🔴 **검정력이 있는 자 셋**으로 격자 «전체»를 판정한다(부호검정 · 순열 p · 칸 가중 z).
    §3 🔴 **물음을 바꾼다** — `㉮ − ㉱` 가 곧 **목표 이동 팔**이고, 그것이 죽는 까닭의
        첫 후보는 같은 산출물 안의 **대조 팔 포화**다. 981 은 이 이름을 한 번도 안 불렀다.
    §4 🔴 **헤드라인 축을 견준다** — 「목표–자 정렬도」 대 「지배 도메인으로 옮긴 학습 행 수」.

🔴 **격자는 다시 안 잰다** — `runners/out981_decomp.json` 을 읽는다(출처를 적는다).
🔴 **다시 재는 것은 하나뿐** — 첫 칸의 **복제 800 짝SE**(§1 의 「복제를 늘리면」 물음).

씀:
    python3 runners/mech982.py --stage mde   --ref <40자 sha>
    python3 runners/mech982.py --stage mech  --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runners.predict971 as P                    # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402
import mix980 as M8                               # noqa: E402
import mix981 as M9                               # noqa: E402

RAN = ("runners/mech982.py", "runners/mix981.py", "runners/mix980.py",
       "runners/ruler979.py", "runners/alpha977.py", "runners/ledger.py",
       "runners/layers957.py", "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out982_progress.txt"

RULERS = R9.RULERS
NB_GRID = list(M8.NB_GRID)
U_REG = A.U_REG
SRC = "runners/out981_decomp.json"
SRC_T = "runners/out981_target.json"
BOOT_HI = 800                    # §1 재측정 복제(사전등록 §8-2)
CELL_HI = 450                    # 첫 칸
DOM_TOP = "세계애니"               # 유보 지배 도메인


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))
    sys.stderr.write("%s  %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _load(n):
    return json.loads((ROOT / n).read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════
# 검정 셋 — 🔴 칸별 관문 대신 «격자 전체»를 본다
# ══════════════════════════════════════════════════════════════════════
def _rank(v):
    v = list(v)
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        m = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = m
        i = j + 1
    return r


def _spear(a, b):
    a, b = _rank(a), _rank(b)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def spear_perm_p(a, b):
    """🔴 `n!` 전수 순열 p(양측). `n = 7` 이면 5,040 벌이라 **뽑기가 아니라 전수**다."""
    s0 = _spear(a, b)
    if s0 is None:
        return None, None, 0
    n = len(a)
    cnt, tot = 0, 0
    for perm in itertools.permutations(range(n)):
        s = _spear([a[i] for i in perm], b)
        tot += 1
        if s is not None and abs(s) >= abs(s0) - 1e-12:
            cnt += 1
    return _r(s0, 4), _r(float(cnt) / tot, 6), tot


def sign_test(vals):
    """부호검정(양측 · 0 은 뺀다). `p = 2 · P(X ≥ k)` under Binom(n, 0.5)."""
    v = [x for x in vals if x != 0]
    n = len(v)
    k = sum(1 for x in v if x > 0)
    if n == 0:
        return None
    kk = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(kk, n + 1)) / float(2 ** n)
    return collections.OrderedDict([
        ("🔴 양수 / 분모", "%d / %d" % (k, n)),
        ("🔴 양측 p", _r(min(1.0, 2.0 * tail), 6)),
    ])


def weighted_z(deltas, ses):
    """🔴 칸 가중 z = `Σ Δ/se² ÷ √(Σ 1/se²)` — 역분산 가중 결합."""
    num = sum(d / (s * s) for d, s in zip(deltas, ses) if s)
    den = math.sqrt(sum(1.0 / (s * s) for s in ses if s))
    return _r(num / den, 4) if den else None


# ══════════════════════════════════════════════════════════════════════
# §1 🔴 MDE 재측정 — 「복제를 늘리면 MDE 가 주는가」를 **잰다**
# ══════════════════════════════════════════════════════════════════════
def stage_mde(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("MDE 재측정 시작 — %d 칸 · 복제 %d" % (CELL_HI, BOOT_HI))
    dc = _load(SRC)
    pool = A.Pool()
    R = R9.Rulers6(pool)
    canon = "R_pool 묶음"
    T = M9.targets(pool)
    T1, T3 = "T1 유보 혼합 (n_d)", "T3 공급 몫 (hplt 행)"
    lam = 10.0 ** U_REG[1]
    arms = collections.OrderedDict([("㉮ 층화(유보)", T[T1]),
                                    (M9.ARM_PLACEBO, T[T3])])
    se_hi, _ = M9.se_multi(pool, R, A.ALPHA_BASE, lam, CELL_HI, arms, BOOT_HI,
                           tag="복제 %d" % BOOT_HI)
    cell = dc["🔴🔴🔴 칸"]["N_B=%d" % CELL_HI]["🔴 λ 별"]["u=%d" % U_REG[1]]
    se200_p = cell["🔴🔴 ㉱ − ㉯"]["🔴 짝 SE"]
    se200_a = cell["🔴🔴 ㉮ − ㉯"]["🔴 짝 SE"]
    se800_p = se_hi[M9.ARM_PLACEBO][canon]
    se800_a = se_hi["㉮ 층화(유보)"][canon]
    out = collections.OrderedDict()
    out["무엇"] = ("982 §3-1 — 🔴🔴 **관문의 MDE 를 먼저 싣고, 「복제를 늘리면 MDE 가 "
                 "주는가」를 «주장하지 않고 잰다»**")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_982_timeforward.md §3-1"
    out["🔴 다시 잰 칸"] = "N_B=%d · u=%d · 정본 자 %s" % (CELL_HI, U_REG[1], canon)
    out["🔴 복제 수(981)"] = cell["🔴 복제 수"]
    out["🔴 복제 수(982 재측정)"] = BOOT_HI
    out["🔴🔴 짝SE — ㉱ 위약 팔"] = collections.OrderedDict([
        ("복제 200", se200_p), ("복제 800", se800_p),
        ("🔴 줄어든 비율", _r((se200_p - se800_p) / se200_p, 4) if se200_p else None),
        ("🔴🔴 10% 이상 줄었나(P10 의 반대)",
         bool(se200_p and (se200_p - se800_p) / se200_p >= 0.10)),
    ])
    out["🔴 짝SE — ㉮ 층화 팔"] = collections.OrderedDict([
        ("복제 200", se200_a), ("복제 800", se800_a),
        ("🔴 줄어든 비율", _r((se200_a - se800_a) / se200_a, 4) if se200_a else None),
    ])
    out["🔴🔴🔴 그래서 무엇인가"] = (
        "🔴 짝SE 는 **학습 붓스트랩 Δ 의 SD** 이지 「평균의 SE」가 아니다. "
        "복제를 늘리면 **그 SD 의 몬테카를로 오차**만 줄고 **MDE 는 안 준다**. "
        "🔴 **「복제를 늘려라」는 이 관문에 안 듣는다** — 검출력을 올리려면 "
        "유보를 키우거나 **격자 전체를 하나의 검정으로 묶어야** 한다(§3-2)")
    out["🔴 몬테카를로 오차의 이론값 1/√(2(B−1))"] = collections.OrderedDict([
        ("복제 200", _r(1.0 / math.sqrt(2.0 * 199), 5)),
        ("복제 800", _r(1.0 / math.sqrt(2.0 * 799), 5)),
    ])
    out["통과"] = bool(se800_p is not None and se800_a is not None)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **복제 800 짝SE 를 실제로 다시 쟀다**(주장이 아니다). "
        "`통과` 는 「MDE 가 줄었다」가 **아니다** — 그 답은 위 칸에 있다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_mde.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# §2~§4 격자 재분석 (🔴 새 측정 0 — `out981_decomp.json` 을 읽는다)
# ══════════════════════════════════════════════════════════════════════
def _interp_budget(nb, rho, target):
    """🔴 대조 팔이 `target` ρ 에 닿는 예산 — **격자 위 log-선형 보간**.

    격자 밖이면 **「모른다」**를 낸다(외삽 안 한다 · 조항 59).
    """
    for i in range(len(nb) - 1):
        a, b = rho[i], rho[i + 1]
        if (a - target) * (b - target) <= 0 and a != b:
            f = (target - a) / (b - a)
            return math.exp(math.log(nb[i]) + f * (math.log(nb[i + 1]) -
                                                   math.log(nb[i])))
    return None


def stage_mech(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    dc = _load(SRC)
    tg = _load(SRC_T)
    C = dc["🔴🔴🔴 칸"]
    out = collections.OrderedDict()
    out["무엇"] = ("982 §3 — 🔴🔴 **이득 소멸의 기전.** 「공급 제약 대 수렴」이 아니라 "
                 "🔴 **「목표 이동(`㉮ − ㉱`)이 왜 예산과 함께 값을 잃나」**를 묻는다")
    out["🔴 축"] = "C3 (몸통) · 곁 C4"
    out["사전등록"] = "docs/prereg_982_timeforward.md §3-2·§3-3·§3-4"
    out["🔴🔴 입력의 출처"] = collections.OrderedDict([
        ("격자·팔 셋", SRC), ("목표 격자", SRC_T),
        ("🔴 이 러너가 새로 잰 것", "없다 — `--stage mde` 한 칸만 다시 쟀다"),
        ("🔴 왜", "🔴 981 의 수는 티처 #120 의 독립 재현에서 **하나도 안 틀렸다**. "
                "틀린 것은 그 수로 내린 판정이다"),
    ])
    out["🔴 티처"] = ("🔴 티처 #120 C5 — 「위약 팔 7 칸 중 6 칸 양수 · 단조 감소 · "
                    "대조 혼합 SD 와 스피어만 1.0 · 관문 MDE 가 첫 칸 이득의 28.2%」. "
                    "🔴 헤드라인·검정력 수·L1 결산 표는 **티처 #119** 의 것이다")

    per_u = collections.OrderedDict()
    for u in U_REG:
        uk = "u=%d" % u
        ctl = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉯ 대조 ρ(정본 자)"] for n in NB_GRID]
        trt = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉮ 층화(유보) ρ(정본 자)"] for n in NB_GRID]
        pla = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉱ 위약 층화(공급) ρ(정본 자)"] for n in NB_GRID]
        g_a = [C["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉮ − ㉯"]["Δ"] for n in NB_GRID]
        s_a = [C["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉮ − ㉯"]["🔴 짝 SE"] for n in NB_GRID]
        g_p = [C["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉱ − ㉯"]["Δ"] for n in NB_GRID]
        s_p = [C["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉱ − ㉯"]["🔴 짝 SE"] for n in NB_GRID]
        mix = [C["N_B=%d" % n]["🔴🔴 대조 팔 혼합의 표집 SD"]["🔴🔴 몫 표집 SD 의 L1 합"]
               for n in NB_GRID]
        shift = [_r(trt[i] - pla[i]) for i in range(len(NB_GRID))]

        # ── §3-1 MDE 격자 ─────────────────────────────────────────
        mde = collections.OrderedDict()
        for i, n in enumerate(NB_GRID):
            mde["N_B=%d" % n] = collections.OrderedDict([
                ("🔴 MDE = 2·짝SE (㉱ 관문)", _r(2 * s_p[i])),
                ("🔴 그 칸 ㉱ 이득", g_p[i]),
                ("🔴 MDE 가 ㉮ 이득의 몇 %",
                 _r(100.0 * 2 * s_p[i] / g_a[i], 2) if g_a[i] else None),
                ("🔴 ㉱ 이득이 MDE 의 몇 %",
                 _r(100.0 * g_p[i] / (2 * s_p[i]), 2) if s_p[i] else None),
            ])

        # ── §3-2 격자 전체 검정 셋 ────────────────────────────────
        sp, pp, ntot = spear_perm_p(g_p, mix)
        sgn = sign_test(g_p)
        wz = weighted_z(g_p, s_p)
        power = collections.OrderedDict([
            ("🔴 ① 부호검정(7 칸)", sgn),
            ("🔴🔴 ② 스피어만(㉱ 이득, 대조 혼합 SD)", collections.OrderedDict([
                ("스피어만", sp), ("🔴 전수 순열 p(양측)", pp), ("🔴 벌 수(=7!)", ntot)])),
            ("🔴🔴 ③ 칸 가중 z", collections.OrderedDict([
                ("z", wz), ("🔴 |z| ≥ 2 인가", bool(wz is not None and abs(wz) >= 2.0))])),
            ("🔴🔴 칸별 관문(981 이 쓴 자)이 잡은 칸 수",
             sum(1 for i in range(len(NB_GRID)) if g_p[i] >= 2 * s_p[i])),
            ("🔴🔴🔴 그래서 「수렴 설명」은",
             "🔴 **살아 있다 — 다만 작다**" if (pp is not None and pp < 0.05) else
             "🔴 격자 전체 검정에서도 안 선다"),
        ])

        # ── §3-2 목표 이동 팔과 대조 팔 포화 ──────────────────────
        ceil_ = max(ctl)
        head = [_r(ceil_ - c) for c in ctl]
        s_sh, p_sh, _ = spear_perm_p(shift, head)
        s_ga, p_ga, _ = spear_perm_p(g_a, head)
        save = collections.OrderedDict()
        for i, n in enumerate(NB_GRID):
            need = _interp_budget(NB_GRID, ctl, trt[i])
            save["N_B=%d" % n] = collections.OrderedDict([
                ("🔴 ㉮ 가 낸 ρ", trt[i]),
                ("🔴 그 ρ 에 닿는 대조 팔 예산(log-선형 보간)",
                 _r(need, 1) if need else "🔴 모른다 — 격자 밖(외삽 안 한다)"),
                ("🔴🔴 예산 절약 배수", _r(need / n, 3) if need else None),
            ])
        sat = collections.OrderedDict([
            ("🔴🔴 목표 이동 팔 `㉮ − ㉱` 격자", collections.OrderedDict(
                [("N_B=%d" % n, shift[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 첫 칸 목표 이동", shift[0]),
            ("🔴🔴 첫 칸 ㉮ 이득 중 목표 이동의 몫",
             _r(shift[0] / g_a[0], 4) if g_a[0] else None),
            ("🔴 첫 칸 ㉮ 이득 중 위약(수렴)의 몫",
             _r(g_p[0] / g_a[0], 4) if g_a[0] else None),
            ("🔴 대조 팔 ρ 격자", collections.OrderedDict(
                [("N_B=%d" % n, ctl[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 층화 팔 ρ 격자", collections.OrderedDict(
                [("N_B=%d" % n, trt[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴🔴 대조 팔이 격자에서 오른 폭", _r(ctl[-1] - ctl[0])),
            ("🔴🔴🔴 층화 팔이 격자에서 오른 폭", _r(trt[-1] - trt[0])),
            ("🔴🔴 오라클 천장(격자에서 대조 팔이 도달한 최대 ρ)", _r(ceil_)),
            ("🔴 오라클 여유 격자", collections.OrderedDict(
                [("N_B=%d" % n, head[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴🔴 스피어만(`㉮−㉱`, 오라클 여유)", collections.OrderedDict([
                ("스피어만", s_sh), ("🔴 전수 순열 p", p_sh)])),
            ("🔴 스피어만(`㉮−㉯`, 오라클 여유)", collections.OrderedDict([
                ("스피어만", s_ga), ("🔴 전수 순열 p", p_ga)])),
            ("🔴🔴 예산 절약 배수", save),
            ("🔴🔴🔴 기전 한 줄",
             "🔴 **층화는 천장을 올리지 않는다 — 예산 축에서 왼쪽으로 옮긴다.** "
             "대조 팔이 예산과 함께 그 자리를 따라잡으면 이득이 0 이 된다. "
             "🔴 그래서 이득이 죽는 것은 「층화가 나빠져서」가 아니라 "
             "**「대조가 포화해서」**다"),
        ])
        per_u[uk] = collections.OrderedDict([
            ("🔴🔴 §3-1 MDE 격자", mde),
            ("🔴🔴🔴 §3-2 검정력이 있는 자 셋", power),
            ("🔴🔴🔴 §3-2 목표 이동 팔과 대조 팔 포화", sat),
        ])
    out["🔴🔴 λ 별"] = per_u

    # ── §3-3 헤드라인 축 대조 ────────────────────────────────────
    TG = ["T1 유보 혼합 (n_d)", "T2 균등 (1)", "T3 공급 몫 (hplt 행)",
          "T4 √유보 (√n_d)", "T5 역유보 (1/n_d)"]
    mixd = tg["🔴 학습 혼합 진단"]
    rows_tr = [float(mixd[t]["🔴 도메인별 학습 행"][DOM_TOP]) for t in TG]
    align = tg["🔴🔴 목표–자 정렬도 (코사인)"]
    axes = collections.OrderedDict()
    for u in U_REG:
        uk = "u=%d" % u
        cell = tg["🔴🔴🔴 칸"][uk]["🔴🔴 목표별"]
        per_nm = collections.OrderedDict()
        win_row = 0
        for nm in RULERS:
            dl = [cell[t]["자 여섯 전부"][nm]["Δ"] for t in TG]
            al = [align[t][nm] for t in TG]
            s_al = _spear(dl, al)
            s_tr = _spear(dl, rows_tr)
            per_nm[nm] = collections.OrderedDict([
                ("🔴 목표별 Δ", collections.OrderedDict(zip(TG, dl))),
                ("🔴 ㉠ 스피어만(Δ, 목표–자 정렬도)", _r(s_al, 4)),
                ("🔴 ㉡ 스피어만(Δ, 지배 도메인 학습 행)", _r(s_tr, 4)),
                ("🔴🔴 ㉡ 이 ㉠ 을 이기나(|스피어만| 비교)",
                 bool(s_tr is not None and s_al is not None
                      and abs(s_tr) >= abs(s_al))),
            ])
            if per_nm[nm]["🔴🔴 ㉡ 이 ㉠ 을 이기나(|스피어만| 비교)"]:
                win_row += 1
        axes[uk] = collections.OrderedDict([
            ("🔴 자별", per_nm),
            ("🔴🔴🔴 ㉡ 이 이긴 자 수 (0~6)", win_row),
        ])
    out["🔴🔴🔴 §3-3 헤드라인 축 대조"] = collections.OrderedDict([
        ("🔴 후보 축 ㉠", "목표–자 정렬도(코사인)"),
        ("🔴 후보 축 ㉡", "유보 지배 도메인(%s)으로 옮긴 학습 행 수" % DOM_TOP),
        ("🔴 ㉡ 축의 값(목표별)", collections.OrderedDict(
            [(t, int(rows_tr[i])) for i, t in enumerate(TG)])),
        ("🔴 대조 팔의 %s 학습 행" % DOM_TOP,
         int(float(mixd["㉯ 대조"]["🔴 도메인별 학습 행"][DOM_TOP]))),
        ("🔴 λ 별", axes),
        ("🔴🔴 981 의 헤드라인", "「층화 이득은 목표와 자의 정렬도의 단조 함수다」"),
        ("🔴🔴🔴 982 가 적는 헤드라인",
         "🔴 **축은 정렬도가 아니라 「유보 지배 도메인으로 옮긴 학습 행 수」다.** "
         "981 은 §2-2 «본문»에 이미 그렇게 썼고 헤드라인만 정렬도로 뒀다"),
        ("🔴 판별 예측 P6(981)이 거짓인 근거",
         "🔴 `R_eq` 는 `T2` 와 정렬도 1.0 인데 Δ 가 T2 %s < T1 %s" % (
             tg["🔴🔴🔴 칸"]["u=3"]["🔴🔴 목표별"]["T2 균등 (1)"][
                 "자 여섯 전부"]["R_eq 균등"]["Δ"],
             tg["🔴🔴🔴 칸"]["u=3"]["🔴🔴 목표별"]["T1 유보 혼합 (n_d)"][
                 "자 여섯 전부"]["R_eq 균등"]["Δ"])),
    ])

    # ── §3-4 T5 는 조작이 둘이다 ─────────────────────────────────
    t5 = "T5 역유보 (1/n_d)"
    out["🔴🔴 §3-4 `T5` 는 곡선의 끝점이 아니다"] = collections.OrderedDict([
        ("🔴 조작 ①", "지배 도메인(%s) 학습 행을 %d 행으로 굶긴다" % (
            DOM_TOP, int(float(mixd[t5]["🔴 도메인별 학습 행"][DOM_TOP])))),
        ("🔴🔴 조작 ②", "다섯 목표 가운데 **유일하게** `N_B=1800` 에서 공급에 묶인다"),
        ("🔴 묶인 도메인 수(목표별 · N_B=1800)", collections.OrderedDict(
            [(t, mixd[t]["🔴 공급에 묶인 도메인 수"]) for t in TG])),
        ("🔴 정본 자에서의 Δ (u=3)",
         tg["🔴🔴🔴 칸"]["u=3"]["🔴🔴 목표별"][t5]["🔴 정본 자에서의 판정"]["Δ"]),
        ("🔴 `R_eq` 로 재도",
         tg["🔴🔴🔴 칸"]["u=3"]["🔴🔴 목표별"][t5]["자 여섯 전부"]["R_eq 균등"]["Δ"]),
        ("🔴🔴 그래서", "🔴 **`T5` 를 단조 곡선의 끝점으로 쓰지 않는다** — "
                     "자 선택과 무관한 하락이고 조작이 둘이다"),
    ])

    # ── 🔴 P4(981)의 실체 — 어느 문서에도 없던 수 ────────────────
    p4 = collections.OrderedDict()
    vals = []
    for u in U_REG:
        uk = "u=%d" % u
        cell = tg["🔴🔴🔴 칸"][uk]["🔴🔴 목표별"]
        for t in TG:
            v = cell[t].get("🔴🔴 정렬도와 Δ 의 스피어만")
            p4["%s · %s" % (uk, t)] = v
            if v is not None:
                vals.append(float(v))
    out["🔴🔴 981 의 예측 P4 — 실체를 싣는다(어느 문서에도 없었다)"] = \
        collections.OrderedDict([
            ("🔴 칸별 스피어만", p4),
            ("🔴 칸 수", len(vals)),
            ("🔴🔴 평균", _r(float(np.mean(vals)), 4)),
            ("🔴🔴 양수 칸 / 분모", "%d / %d" % (sum(1 for v in vals if v > 0), len(vals))),
            ("🔴 음수 칸", collections.OrderedDict(
                [(k, v) for k, v in p4.items() if v is not None and v < 0])),
            ("🔴 981 은 이것을 ✅ 로 채점했지만 «수»는 어느 문서에도 없다", True),
        ])

    out["통과"] = bool(len(per_u) == len(U_REG))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **λ 둘 전부에서 MDE 격자·검정 셋·목표 이득 분해를 냈다.** "
        "🔴 `통과` 는 「수렴이 산다」가 **아니다** — 그 답은 §3-2 검정 셋 칸에 있다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_mech.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["mde", "mech"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"mde": stage_mde, "mech": stage_mech}[a.stage](a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
