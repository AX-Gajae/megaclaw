#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 §1 — 🔴🔴🔴 **천장은 발견이 아니라 «항등식»이다**. 그리고 팔을 다시 짓는다.

🔴 **왜 (티처 #125 C4).** 986 의 헤드라인은

> 「δ 를 100 배 키워도 발화율 ≈0.57 에서 평평하다 → 원리상 못 재는 설계다」

인데 **이것은 발견이 아니라 정의가 이미 정해 놓은 상한**이다:

- 발화가 **연언** `(㉮ 선다 ∧ ¬㉰ 선다)` 인데
- **`㉰` 쪽 검정 `tp` 는 δ 와 «무관»하다** --- `power986.py:109` **주석이 스스로 적어 놨고**
  `:137` 에서 δ 는 `ora` 에만 탄다.
- 그래서 **δ→∞ 에서 `to` → True 로 포화**하고 발화율은 **`P(¬㉰ 선다)`** 로 수렴한다 ---
  🔴 **δ 가 전혀 안 들어간 상수다.**

🔴 **986 은 `0.5736` 을 실었지만 그 수의 «뜻»(= `㉰` 팔이 몇 %에서 서나)은 어디에도 안 적었다.**
이 러너가 그것을 **직접 재서 그 이름으로** 싣는다.

**이 러너가 새로 내는 것 다섯(사전등록 §2):**

1. **§1 항등식 상한** --- `P(¬㉰ 선다)` 와 `P(㉰ 선다)` 를 λ 별로 «직접» 잰다.
2. **§2 포화 여유** --- 986 의 「천장」 점추정이 항등식 상한에 **얼마나 못 미치나**.
   🔴 **`u=3` 은 δ=2.00 에서 아직 오르는 중**이라 「δ 를 아무리 키워도」가 **틀렸다**.
3. **§3 관문의 병** --- `FIRE = 0.5` 가 상한 **바로 밑**이라 「최소 검출 δ」가 원리상 흔들린다.
4. **§4 팔을 다시 짓는다** --- **V0 · V1 · V1′ · V2** 를 같은 복제·같은 격자에서 나란히.
5. **§5 983 모양 자** --- 「원리상 못 재는 칸」을 **점추정이 아니라 구간**으로 내고
   **확정 / 미확정**을 갈라 싣는다. **식별 관문을 격자에서 계산**한다.

🔴 **새 자료 학습 0** --- 격자·복제는 983 의 산출물을 다시 읽는다.

씀:
    python3 runners/power987.py --stage power --ref <40자 sha>
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle987 as CY                                  # noqa: E402
import power985 as P5                                  # noqa: E402
import stat983 as S                                    # noqa: E402
import mix980 as MX                                    # noqa: E402

OUT = "runners/out987_power.json"

NB_GRID = list(MX.NB_GRID)
NB = [float(n) for n in NB_GRID]
A_CTL, A_ORA, A_PRE, A_PLA = P5.A_CTL, P5.A_ORA, P5.A_PRE, P5.A_PLA

#: 🔴 사전등록 §10 --- **986 판 그대로 31 단계**(격자를 안 바꾼다)
DELTAS_985 = [round(0.01 * i, 4) for i in range(21)]
DELTAS_EXT = [0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.80, 1.00, 1.50, 2.00]
DELTAS = DELTAS_985 + DELTAS_EXT
FIRE = 0.5
B = 2000
SEED = 987
LO, HI = 2.5, 97.5
CEIL_FROM = 0.50
SHAPE_Z = 2.0
THETAS = [round(0.005 * i, 4) for i in range(41)]      # 0.000 ~ 0.200

#: 🔴 발화 규칙 변이체(사전등록 §2-6 + §2-6-가 의 **측정 전** 정정)
VARIANTS = ("V0", "V1", "V1′", "V2")
PKEY = "🔴 전수 순열 p(잔차 순열)"
RKEY = "🔴 부분상관(잔차 피어슨)"
FIRE_YES, FIRE_NO, UNUSABLE = 1, 0, -1

#: 🔴 이 사이클이 «새로» 학습한 자료 --- 없다(격자·복제는 983 산출물을 다시 읽는다)
NEW_DATA = ()


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _load(name):
    p = ROOT / "runners" / name
    if not p.is_file():
        raise SystemExit("🔴 없다: %s" % p)
    return json.loads(p.read_text(encoding="utf-8"))


def _pct(v, q):
    return None if not len(v) else float(np.percentile(np.asarray(v, dtype=float), q))


def _rate(row):
    a = np.asarray(row, dtype=int)
    usable = int((a >= 0).sum())
    if usable == 0:
        return None, 0, 0
    return float(int((a == FIRE_YES).sum())) / usable, int((a == FIRE_YES).sum()), usable


# ══════════════════════════════════════════════════════════════════════
# §0 복제별 «δ 가 안 들어가는» 부분을 한 번만 푼다
# ══════════════════════════════════════════════════════════════════════
def _orth_dir(h, seed):
    """🔴🔴 **`{1, N_B, h}` 에 직교화한 씨앗 난수 방향**(V2 의 `L`).

    🔴 **왜.** 986 판은 **심는 방향 `L` 이 곧 공변량 `h`** 라
    「심은 것」과 「자가 빼는 것」이 **같은 축**이다. V2 는 그 둘을 **구성상 직교**로 만든다.
    """
    rng = np.random.RandomState(seed)
    v = rng.normal(size=len(h))
    Xc = np.column_stack([np.ones(len(h)), np.asarray(NB, dtype=float),
                          np.asarray(h, dtype=float)])
    beta, *_ = np.linalg.lstsq(Xc, v, rcond=None)
    r = v - Xc.dot(beta)
    sd = float(np.std(r))
    if sd < 1e-12:
        return None
    return list((r - float(np.mean(r))) / sd)


def base_records(pts, reps):
    """🔴 복제마다 **δ 가 안 들어가는 것 전부**를 한 번에 푼다.

    🔴 `tp`(㉰ 쪽 검정)는 **δ 와 무관**하다 --- 이것이 §1 의 항등식이 서는 자리다.
    """
    out = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P, R = pts[uk], reps[uk]
        n_rep = len(R[A_CTL][0])
        obs = max(abs(a - b) for a, b in zip(P[A_ORA], P[A_PRE]))
        recs = []
        for r in range(n_rep):
            ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
            pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
            pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
            h = [max(ctl) - c for c in ctl]
            sd = float(np.std(h))
            if sd < 1e-15:
                recs.append(None)                     # 🔴 대조 여유가 평평 --- L 이 정의 안 된다
                continue
            mu = float(np.mean(h))
            Lh = [(x - mu) / sd for x in h]
            Lo = _orth_dir(h, SEED + 1000 + r)
            s_p = [pre[i] - pla[i] for i in range(len(NB_GRID))]
            tp = S.partial_test(s_p, h, NB)
            recs.append({
                "pre": pre, "pla": pla, "h": h, "Lh": Lh, "Lo": Lo,
                "tp_p": tp.get(PKEY), "tp_stand": bool(tp.get("선다")),
                "rho_p": tp.get(RKEY),
            })
        out[uk] = {"복제 수": n_rep, "관측된 max|㉮ρ − ㉰ρ|": _r(obs), "복제별": recs}
    return out


# ══════════════════════════════════════════════════════════════════════
# §1 🔴🔴🔴 항등식 상한 --- `천장 = P(¬㉰ 선다)`
# ══════════════════════════════════════════════════════════════════════
def identity_ceiling(base):
    per = collections.OrderedDict()
    for uk, blk in base.items():
        recs = blk["복제별"]
        flat = len([1 for x in recs if x is None])
        undef = len([1 for x in recs if x is not None and x["tp_p"] is None])
        usable = [x for x in recs if x is not None and x["tp_p"] is not None]
        stand = len([1 for x in usable if x["tp_stand"]])
        notstand = len(usable) - stand
        n = len(usable)
        per[uk] = collections.OrderedDict([
            ("🔴 복제 수", blk["복제 수"]),
            ("🔴 대조 여유가 평평해 «못 쓴» 복제", flat),
            ("🔴 `㉰` 쪽 검정이 «정의 안 된» 복제(잔차 SD 0)", undef),
            ("🔴🔴 쓸 수 있는 복제(분모)", n),
            ("🔴🔴🔴 `㉰` 팔이 «선» 복제 수", stand),
            ("🔴🔴🔴 `P(㉰ 선다)` — 🔴 **986 이 어디에도 안 적은 수**", _r(float(stand) / n, 6)),
            ("🔴🔴🔴 `¬㉰ 선다` 복제 수", notstand),
            ("🔴🔴🔴 **천장 = `P(¬㉰ 선다)`(항등식 상한)**", _r(float(notstand) / n, 6)),
            ("🔴 이 수에 δ 가 «전혀» 안 들어간다",
             "🔴 **`tp = partial_test(㉰−㉱, h, N_B)` 는 `ora` 를 «안» 본다** --- "
             "`power986.py:109` 주석이 스스로 「δ 와 무관 · 복제마다 한 번만 푼다」고 적었고 "
             "`:137` 에서 δ 는 `ora` 에만 탄다"),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **986 의 「천장」은 발견이 아니라 항등식이다** --- "
                 "발화가 연언 `(㉮ 선다 ∧ ¬㉰ 선다)` 이고 둘째 항이 δ 자유라 "
                 "**δ→∞ 에서 발화율은 `P(¬㉰ 선다)` 로 수렴한다**"),
        ("🔴🔴 이것이 왜 「원리상 못 재는 «설계»」가 아닌가(티처 #125 ⓑ)",
         "🔴 **세계 이야기도 표본 크기 이야기도 아니다 --- 「추정량의 정의」 이야기다.** "
         "옳은 문장은 **「추정량이 정의상 상한에 걸렸다」**이지 "
         "**「원리상 못 재는 설계」**가 아니다. 상한은 **발화 규칙을 바꾸면 사라진다**(§4)"),
        ("🔴 이 천장을 보는 데 무엇이 필요했나",
         "🔴 **31 칸 격자도 B=2000 도 «필요 없었다»** --- 복제마다 `tp` 를 한 번 세면 나온다"),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2 and all(
            v["🔴🔴 쓸 수 있는 복제(분모)"] > 0 for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 분모를 «냈는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §2~§4 발화 행렬 --- 네 변이체를 같은 복제·같은 격자에서
# ══════════════════════════════════════════════════════════════════════
def fire_matrices(base):
    """🔴 `M[변이체][uk]["δ=…"][r] ∈ {1 발화, 0 비발화, -1 못 씀}`."""
    out = {v: collections.OrderedDict() for v in VARIANTS}
    for uk, blk in base.items():
        recs = blk["복제별"]
        rows = {v: collections.OrderedDict() for v in VARIANTS}
        for d in DELTAS:
            r0, r1, r1p, r2 = [], [], [], []
            for rec in recs:
                if rec is None or rec["tp_p"] is None:
                    r0.append(UNUSABLE), r1.append(UNUSABLE)
                    r1p.append(UNUSABLE), r2.append(UNUSABLE)
                    continue
                pre, pla, h, Lh, Lo = (rec["pre"], rec["pla"], rec["h"],
                                       rec["Lh"], rec["Lo"])
                ora = [pre[i] + d * Lh[i] for i in range(len(NB_GRID))]
                to = S.partial_test([ora[i] - pla[i] for i in range(len(NB_GRID))], h, NB)
                if to.get(PKEY) is None:
                    r0.append(UNUSABLE), r1p.append(UNUSABLE)
                else:
                    # ── V0: 986 판(연언의 둘째 항이 δ 자유) ──────────
                    r0.append(FIRE_YES if (to["선다"] and not rec["tp_stand"]) else FIRE_NO)
                    # ── V1′: 둘째 항을 δ 를 타는 «비교»로 ────────────
                    rho_o, rho_p = to.get(RKEY), rec["rho_p"]
                    if rho_o is None or rho_p is None:
                        r1p.append(UNUSABLE)
                    else:
                        r1p.append(FIRE_YES if (to["선다"] and rho_o > rho_p) else FIRE_NO)
                # ── V1: 사전등록 «원안» --- `t(㉮−㉰ | h) 선다` ────────
                diff = [ora[i] - pre[i] for i in range(len(NB_GRID))]
                if float(np.std(diff)) < 1e-15:
                    r1.append(UNUSABLE)               # 🔴 δ=0 이면 0 벡터라 정의 안 된다
                else:
                    t1 = S.partial_test(diff, h, NB)
                    r1.append(UNUSABLE if t1.get(PKEY) is None
                              else (FIRE_YES if t1["선다"] else FIRE_NO))
                # ── V2: 심는 축을 자의 축에서 뗀다 ──────────────────
                if Lo is None:
                    r2.append(UNUSABLE)
                else:
                    ora2 = [pre[i] + d * Lo[i] for i in range(len(NB_GRID))]
                    t2 = S.partial_test([ora2[i] - pla[i] for i in range(len(NB_GRID))],
                                        h, NB)
                    rho_o2, rho_p = t2.get(RKEY), rec["rho_p"]
                    if t2.get(PKEY) is None or rho_o2 is None or rho_p is None:
                        r2.append(UNUSABLE)
                    else:
                        r2.append(FIRE_YES if (t2["선다"] and rho_o2 > rho_p) else FIRE_NO)
            for v, row in zip(VARIANTS, (r0, r1, r1p, r2)):
                rows[v]["δ=%.4f" % d] = row
        for v in VARIANTS:
            out[v][uk] = rows[v]
    return out


def sweep_block(rows_by_delta, n_rep, seed):
    """δ 별 점추정 + 부트스트랩 95% 구간 + 「처음 0.5 이상이 되는 δ」."""
    rows = [rows_by_delta["δ=%.4f" % d] for d in DELTAS]
    point = [_rate(r)[0] for r in rows]
    A = np.asarray(rows, dtype=int)
    rng = np.random.RandomState(seed)
    boot = np.full((B, len(DELTAS)), np.nan)
    cross = []
    for b in range(B):
        idx = rng.randint(0, n_rep, size=n_rep)
        sub = A[:, idx]
        usable = (sub >= 0).sum(axis=1)
        fire = (sub == FIRE_YES).sum(axis=1)
        rt = np.where(usable > 0, fire / np.maximum(usable, 1), np.nan)
        boot[b] = rt
        got = None
        for i, d in enumerate(DELTAS):
            if not np.isnan(rt[i]) and rt[i] >= FIRE:
                got = d
                break
        cross.append(got)
    sweep = collections.OrderedDict()
    for i, d in enumerate(DELTAS):
        col = boot[:, i]
        col = col[~np.isnan(col)]
        rate, fire, usable = _rate(rows[i])
        sweep["δ=%.4f" % d] = collections.OrderedDict([
            ("쓸 수 있는 복제", usable), ("발화 수", fire),
            ("🔴 발화율(점추정)", _r(rate, 4)),
            ("🔴 부트스트랩 95% 구간",
             [_r(_pct(col, LO), 4), _r(_pct(col, HI), 4)] if len(col) else None),
        ])
    got = [x for x in cross if x is not None]
    never = float(len(cross) - len(got)) / B
    ci = [_r(_pct(got, LO), 4), _r(_pct(got, HI), 4)] if got else None
    # ── 🔴 `[수리] R4` --- 식별 관문을 **격자에서 계산**한다 ──────────
    ident_grid = None
    if ci is not None:
        try:
            i_lo = DELTAS.index(round(ci[0], 4))
            i_hi = DELTAS.index(round(ci[1], 4))
            ident_grid = bool(abs(i_hi - i_lo) <= 1 and never == 0.0)
        except ValueError:
            ident_grid = None
    width = _r(ci[1] - ci[0], 4) if ci else None
    return collections.OrderedDict([
        ("🔴 δ 쓸기", sweep),
        ("🔴 처음 0.5 «이상»이 되는 δ(점추정)",
         next((d for i, d in enumerate(DELTAS)
               if point[i] is not None and point[i] >= FIRE), None)),
        ("🔴🔴 그 95% 구간", ci if ci is not None
         else "🔴 **%d 벌 중 한 벌도 안 넘었다** --- 「검출 크기가 없다」가 아니라 "
              "**「이 격자 밖이다」**다(조항 59)" % B),
        ("🔴 구간 폭", width),
        ("🔴 부트스트랩에서 «한 번도» 안 넘은 비율", _r(never, 4)),
        ("🔴🔴🔴 식별됐나(🔴 `[수리] R4` — 구간 두 끝이 격자에서 «이웃한 칸»인가)", ident_grid),
        ("⚠ 구판 자(하드코딩 `0.01`)로 재면", bool(width is not None and width <= 0.01
                                            and never == 0.0)),
        ("🔴 왜 자를 바꿨나(조항 60)",
         "🔴 **격자가 비균일하다**(0~0.20 은 0.01 · 위쪽은 0.05~0.50). 그러면 "
         "「폭 ≤ 0.01」은 **위쪽 구간에서 사실상 참이 될 수 없는 자**이고 "
         "「식별되지 않는다」가 **설계상 보장**된다(티처 #125 3순위 ⓓ)"),
        ("🔴 격자 최대 δ 발화율", _r(point[-1], 4)),
        ("🔴 전 δ 최대 발화율", _r(max([p for p in point if p is not None]), 4)),
        ("🔴 `δ ≥ %.2f` 구간 발화율 중앙값(986 판 「천장」)" % CEIL_FROM,
         _r(float(np.median([point[i] for i, d in enumerate(DELTAS)
                             if d >= CEIL_FROM and point[i] is not None])), 4)),
        ("🔴 δ>0 에서 발화율이 «상수»인가(= 자가 δ 를 안 탄다)",
         bool(len(set(round(p, 6) for i, p in enumerate(point)
                      if p is not None and DELTAS[i] > 0)) == 1)),
    ])


def variants(base, mats, ident):
    per = collections.OrderedDict()
    for v in VARIANTS:
        blocks = collections.OrderedDict()
        for uk, blk in base.items():
            blocks[uk] = sweep_block(mats[v][uk], blk["복제 수"], SEED + VARIANTS.index(v))
        per[v] = blocks
    # ── 🔴 항등식 검사: V0 의 발화 수는 모든 δ 에서 `¬㉰선다` 수를 «못 넘는다» ──
    idcheck = collections.OrderedDict()
    for uk in base:
        cap = ident["🔴 λ 별"][uk]["🔴🔴🔴 `¬㉰ 선다` 복제 수"]
        counts = [_rate(mats["V0"][uk]["δ=%.4f" % d])[1] for d in DELTAS]
        idcheck[uk] = collections.OrderedDict([
            ("🔴🔴 항등식 상한(`¬㉰ 선다` 복제 수)", cap),
            ("🔴 δ 별 발화 수의 최댓값", max(counts)),
            ("🔴🔴🔴 모든 δ 에서 `발화 수 ≤ 상한` 인가", bool(max(counts) <= cap)),
            ("🔴🔴🔴 포화 여유(상한 − 격자 최대 δ 의 발화 수)", cap - counts[-1]),
            ("🔴 격자 최대 δ 의 발화 수", counts[-1]),
            ("🔴🔴 상한에 «닿았나»(여유 ≤ 1)", bool(cap - counts[-1] <= 1)),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **팔을 구성상 독립으로 다시 짓는다**(사전등록 §2-6 · §2-6-가) --- "
                 "**같은 복제·같은 격자**에서 네 변이체를 나란히 잰다"),
        ("🔴 변이체의 정의(측정 전에 박았다)", collections.OrderedDict([
            ("V0", "986 판 --- `to 선다 ∧ ¬tp 선다` · `L = h` 표준화. "
                   "🔴 **둘째 항이 δ 자유라 상한이 `P(¬㉰선다)` 다**"),
            ("V1", "사전등록 «원안» --- `t(㉮−㉰ | h) 선다` · `L = h` 표준화. "
                   "🔴 **`㉮−㉰ = δ·L` 이 항등식이고 부분상관 순열검정은 척도 불변이라 "
                   "δ 가 «대수적으로» 소거된다**(§2-6-가 · **측정 전** 정정)"),
            ("V1′", "정정안 --- `to 선다 ∧ (ρ_o > ρ_p)` · `L = h` 표준화. "
                    "🔴 **모든 항이 δ 를 탄다**"),
            ("V2", "심는 축을 자의 축에서 뗀다 --- `to 선다 ∧ (ρ_o > ρ_p)` · "
                   "🔴 `L ⊥ {1, N_B, h}`(씨앗 난수 직교화)"),
        ])),
        ("🔴🔴🔴 변이체별", per),
        ("🔴🔴🔴 항등식 검사(V0 의 발화 수가 상한을 넘나)", idcheck),
        ("⚠ 이 절의 한계(조항 61)",
         "🔴 **V1′·V2 는 「특이성」을 V0 과 «다르게» 정의한다** --- "
         "V0 의 둘째 항은 「㉰ 팔이 «안 선다»」이고 V1′ 은 「㉮ 가 ㉰ 보다 «세다»」다. "
         "🔴 **그러므로 이 사이클은 「V1′ 이 더 낫다」를 «주장하지 않는다».** "
         "적는 것은 **「V0·V1 의 상한은 δ 자유이고 V1′ 은 그렇지 않다」** 하나다"),
        ("통과", bool(all(uk in per[v] for v in VARIANTS for uk in base)
                    and all(idcheck[uk]["🔴🔴🔴 모든 δ 에서 `발화 수 ≤ 상한` 인가"]
                            for uk in idcheck))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **① 네 변이체 × 두 λ 를 전부 쟀고 ② 항등식이 «한 번도» 안 깨졌는가**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §3 🔴🔴 「최소 검출 δ」의 병 --- 관문이 상한 «바로 밑»이다
# ══════════════════════════════════════════════════════════════════════
def gate_disease(ident, var):
    per = collections.OrderedDict()
    for uk in ident["🔴 λ 별"]:
        cap = ident["🔴 λ 별"][uk]["🔴🔴🔴 **천장 = `P(¬㉰ 선다)`(항등식 상한)**"]
        v0 = var["🔴🔴🔴 변이체별"]["V0"][uk]
        per[uk] = collections.OrderedDict([
            ("🔴🔴 항등식 상한", cap),
            ("🔴 관문 `FIRE`", FIRE),
            ("🔴🔴🔴 여유(상한 − 관문)", _r(cap - FIRE, 6)),
            ("🔴🔴🔴 「최소 검출 δ」가 «정의되나»(여유 > 0)", bool(cap - FIRE > 0)),
            ("🔴 부트스트랩에서 «한 번도» 안 넘은 비율",
             v0["🔴 부트스트랩에서 «한 번도» 안 넘은 비율"]),
            ("🔴 그 95% 구간", v0["🔴🔴 그 95% 구간"]),
            ("🔴 구간 폭", v0["🔴 구간 폭"]),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **「최소 검출 δ」의 병** --- 관문 `0.5` 가 항등식 상한 «바로 밑»이다"),
        ("🔴🔴 왜 이 하나에서 전부 나오나(티처 #125 ⓔ)",
         "🔴 **관문이 상한 바로 밑이면** ① 부트스트랩 일부 벌은 **한 번도 안 넘고** "
         "② 넘는 벌도 **어디서 넘을지가 잡음이 정한다** --- "
         "곧 **「안 넘은 비율 1.7%」도 「구간 [0.07, 0.60]」도 «같은 한 가지»의 결과다**"),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 여유를 «냈는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §5 🔴🔴 983 모양 자 --- 구간으로 · 확정 / 미확정
# ══════════════════════════════════════════════════════════════════════
def shape_interval(reps, g984):
    per = collections.OrderedDict()
    sec = (g984 or {}).get("§3-ⓐ 🔴🔴 2·짝SE 관문 전량 + 칸 대 칸 짝 검정") or {}
    lam = sec.get("🔴 λ 별") or {}
    grid_step = round(THETAS[1] - THETAS[0], 6)
    for uk in ("u=0", "u=3"):
        R = reps[uk]
        n_rep = len(R[A_CTL][0])
        gain = np.asarray([[R[A_ORA][i][r] - R[A_CTL][i][r] for r in range(n_rep)]
                           for i in range(len(NB_GRID))])
        pairs = collections.OrderedDict()
        rng = np.random.RandomState(SEED + 2)
        cnt = collections.Counter()
        for i in range(len(NB_GRID) - 1):
            d_r = gain[i + 1] - gain[i]
            sd = float(np.std(d_r, ddof=1))
            cen = d_r - float(np.mean(d_r))
            thr = SHAPE_Z * sd
            min_th = None
            for th in THETAS:
                if float(np.mean(np.abs(cen + th) >= thr)) >= FIRE:
                    min_th = th
                    break
            mins = []
            for _b in range(B // 4):
                idx = rng.randint(0, n_rep, size=n_rep)
                s = d_r[idx]
                sd_b = float(np.std(s, ddof=1))
                cen_b = s - float(np.mean(s))
                thr_b = SHAPE_Z * sd_b
                m = None
                for th in THETAS:
                    if float(np.mean(np.abs(cen_b + th) >= thr_b)) >= FIRE:
                        m = th
                        break
                mins.append(m)
            got = [x for x in mins if x is not None]
            ci = [_r(_pct(got, LO), 4), _r(_pct(got, HI), 4)] if got else None
            obs_row = None
            for row in (lam.get(uk) or {}).get("🔴 인접 칸 짝 검정") or []:
                if row.get("칸") == "%d → %d" % (NB_GRID[i], NB_GRID[i + 1]):
                    obs_row = row
                    break
            obs = (obs_row or {}).get("점추정 차")
            obs_abs = abs(obs) if isinstance(obs, float) else None
            # ── 🔴🔴🔴 `[수리] R4` --- 점추정이 아니라 «구간»으로 판정 ──────
            if obs_abs is None or ci is None:
                verdict = "🔴 모른다 --- 관측 차나 구간을 못 읽었다(조항 59)"
            elif obs_abs < ci[0]:
                verdict = "확정: 못 잰다"
            elif obs_abs > ci[1]:
                verdict = "확정: 잰다"
            else:
                verdict = "미확정(관측 차가 구간 «안»이다)"
            cnt[verdict] += 1
            ident_grid = (None if ci is None
                          else bool(round(ci[1] - ci[0], 6) <= grid_step))
            pairs["%d → %d" % (NB_GRID[i], NB_GRID[i + 1])] = collections.OrderedDict([
                ("🔴 복제 짝 SD", _r(sd)),
                ("🔴 자의 관문(2·짝SD)", _r(thr)),
                ("🔴 983·984 가 실은 점추정 차", obs),
                ("🔴 최소 검출 모양 크기(점추정)", min_th),
                ("🔴🔴 그 95% 구간", ci if ci is not None
                 else "🔴 **격자(0 ~ %.3f) 밖이다**" % THETAS[-1]),
                ("🔴 구간 폭", _r(ci[1] - ci[0], 4) if ci else None),
                ("🔴 식별됐나(구간 폭 ≤ 격자 한 칸 %.3f)" % grid_step, ident_grid),
                ("⚠ 986 판(점추정 대 점추정) 판정",
                 (None if (obs_abs is None or min_th is None) else bool(obs_abs < min_th))),
                ("🔴🔴🔴 987 판(구간) 판정", verdict),
            ])
        per[uk] = collections.OrderedDict([
            ("🔴 인접 칸 쌍 수(분모)", len(pairs)),
            ("🔴 칸 쌍별", pairs),
            ("🔴🔴🔴 확정 「못 잰다」", cnt["확정: 못 잰다"]),
            ("🔴🔴🔴 확정 「잰다」", cnt["확정: 잰다"]),
            ("🔴🔴🔴 미확정", cnt["미확정(관측 차가 구간 «안»이다)"]),
            ("⚠ 986 이 실은 점추정 합계(「원리상 못 재는 칸 쌍 수」)",
             len([1 for v in pairs.values()
                  if v["⚠ 986 판(점추정 대 점추정) 판정"] is True])),
            ("🔴🔴 986 의 점추정 합계와 987 의 확정 수가 갈리나",
             bool(len([1 for v in pairs.values()
                       if v["⚠ 986 판(점추정 대 점추정) 판정"] is True])
                  != cnt["확정: 못 잰다"])),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **`[수리] R4` --- 「원리상 못 재는 칸」을 «구간»으로 내고 "
                 "확정 / 미확정을 갈라 싣는다**"),
        ("🔴🔴 왜(티처 #125 3순위 ⓓ)",
         "🔴 **986 의 2순위 전체 논지가 「구간이 넓으면 점추정을 못 박지 마라」인데 "
         "자기 `6/6` 이 그 죄를 짓는다** --- `u=3` 의 두 칸(`1800→3600` · `14400→28800`)은 "
         "관측 차가 **자기 구간 «안»**이다. 정직한 형태는 「확정 N + 미확정 M」이다"),
        ("🔴 판정 규칙(측정 전에 박았다)", {
            "확정: 못 잰다": "관측 차 < 구간 하한", "확정: 잰다": "관측 차 > 구간 상한",
            "미확정": "관측 차가 구간 안"}),
        ("🔴 θ 격자 한 칸", grid_step),
        ("🔴 부트스트랩 복제 수", B // 4),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2 and all(
            v["🔴 인접 칸 쌍 수(분모)"] == len(NB_GRID) - 1 for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 인접 칸 쌍 6 개를 전량 쟀는가**"),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    gr = _load("out983_grid.json")
    rp = _load("out983_reps.json")
    g984 = _load("out984_grid.json")
    pts, reps = P5.arms_points(gr), P5.arms_reps(rp)
    base = base_records(pts, reps)
    ident = identity_ceiling(base)
    mats = fire_matrices(base)
    var = variants(base, mats, ident)

    out = collections.OrderedDict()
    out["무엇"] = "987 §1 — 🔴🔴🔴 **천장은 항등식이다** · **팔을 구성상 독립으로 다시 짓는다**"
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["🔴 출처"] = ["runners/out983_grid.json", "runners/out983_reps.json",
                   "runners/out984_grid.json"]
    out["🔴 새 자료 학습"] = len(NEW_DATA)
    out["🔴 격자·복제(986 과 «같다»)"] = {
        "격자 칸 수": len(NB_GRID), "N_B": NB_GRID,
        "복제 수": base["u=0"]["복제 수"],
        "δ 격자 단계": len(DELTAS),
        "🔴 부트스트랩 복제 수 B": B,
        "🔴 씨앗": SEED,
        "🔴 δ 격자 최대": DELTAS[-1],
        "🔴 987 이 바꾼 것": "**격자를 안 바꿨다** --- 바꾼 것은 «발화 규칙»과 «판정 규칙»뿐이다",
        "통과": bool(len(NB_GRID) and base["u=0"]["복제 수"] and len(DELTAS)),
        "🔴 이 절의 `통과`": "🔴 격자·복제를 986 과 같게 «썼는가»(새로 안 뽑았다)",
    }
    out["§1 🔴🔴🔴 천장은 항등식이다 — `P(¬㉰ 선다)`"] = ident
    out["§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2"] = var
    out["§3 🔴🔴 「최소 검출 δ」의 병 — 관문이 상한 바로 밑이다"] = gate_disease(ident, var)
    out["§4 🔴🔴 983 모양 자 — 구간으로 · 확정 / 미확정"] = shape_interval(reps, g984)
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    out["🔴 이 산출물의 `통과`"] = "네 절이 전부 «값을 냈고» 항등식이 안 깨졌는가다"
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["power"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    i = r["§1 🔴🔴🔴 천장은 항등식이다 — `P(¬㉰ 선다)`"]["🔴 λ 별"]
    v = r["§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2"]
    print(json.dumps({
        "통과": r["통과"],
        "u=0 천장(항등식)": i["u=0"]["🔴🔴🔴 **천장 = `P(¬㉰ 선다)`(항등식 상한)**"],
        "u=0 P(㉰ 선다)": i["u=0"]["🔴🔴🔴 `P(㉰ 선다)` — 🔴 **986 이 어디에도 안 적은 수**"],
        "u=3 천장(항등식)": i["u=3"]["🔴🔴🔴 **천장 = `P(¬㉰ 선다)`(항등식 상한)**"],
        "V0 u=0 δmax": v["🔴🔴🔴 변이체별"]["V0"]["u=0"]["🔴 격자 최대 δ 발화율"],
        "V1 u=0 δ 상수인가": v["🔴🔴🔴 변이체별"]["V1"]["u=0"][
            "🔴 δ>0 에서 발화율이 «상수»인가(= 자가 δ 를 안 탄다)"],
        "V1′ u=0 δmax": v["🔴🔴🔴 변이체별"]["V1′"]["u=0"]["🔴 격자 최대 δ 발화율"],
        "V2 u=0 δmax": v["🔴🔴🔴 변이체별"]["V2"]["u=0"]["🔴 격자 최대 δ 발화율"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
