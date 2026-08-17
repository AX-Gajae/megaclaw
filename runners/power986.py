#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""986 §3 — 🔴🔴🔴 **검정력 곡선에 「검정력」을 붙인다**.

🔴 **왜 (티처 #124).** 985 가 낸 `u=0` 최소 검출 `δ 0.13` 은 **복제 «한 벌»이 정한 수**다:

| δ | 발화/쓸 복제 | 발화율 |
|---|---|---|
| 0.12 | **97**/196 | 0.4949 |
| **0.13** | **98**/196 | **0.5000** |
| 0.20 | 103/197 | 0.5228 |

**97 → 98, 딱 한 벌이 넘겼다.** 그런데 985 의 **다섯 자리**(판정문·카드·handoff·원장·PR)가
**`6.380994`** 를 실었다 --- 🔴 **소수점 여섯 자리로 못 박은 죽은 숫자다.**
**자가 검정력을 쟀는데 그 자 자신의 검정력은 안 쟀다.**

**이 러너가 새로 재는 것 넷(사전등록 §3):**

1. **§1 발화 행렬** --- 발화 판정은 **(복제 r, δ) 의 결정함수**다. 한 번만 계산한다.
2. **§2 복제 부트스트랩**(`B = 2000` · 씨앗 986) --- δ 별 발화율의 **95% 구간**과
   **「처음 0.5 이상이 되는 δ」의 분포**. 🔴 **구간이 두 칸 이상 걸치면
   점추정을 소수점으로 «안» 적는다.**
3. **§3 천장** --- δ 격자를 **0 ~ 2.00** 으로 넓혀
   **「δ 를 아무리 키워도 발화율은 ≈얼마인가」**를 잰다. 🔴 **985 가 안 적은 더 센 문장이다.**
4. **§4 983 에도 같은 자** --- 983 의 「U 자 되오름」은 **같은 7 칸 × 200 복제 격자**와
   **같은 짝 검정** 위에 서 있다. 그 자의 **최소 검출 모양 크기**와 구간을 낸다
   (조항 60 · 985 는 984 에만 물렸다).

🔴 **새 자료 학습 0** --- 격자·복제는 983 의 산출물을 다시 읽는다.

씀:
    python3 runners/power986.py --stage power --ref <40자 sha>
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

import cycle986 as CY                                  # noqa: E402
import power985 as P5                                  # noqa: E402
import stat983 as S                                    # noqa: E402
import mix980 as MX                                    # noqa: E402

OUT = "runners/out986_power.json"

NB_GRID = list(MX.NB_GRID)
NB = [float(n) for n in NB_GRID]
A_CTL, A_ORA, A_PRE, A_PLA = P5.A_CTL, P5.A_ORA, P5.A_PRE, P5.A_PLA

#: 🔴 사전등록 §9 --- **985 판 21 단계 + 천장을 보려고 넓힌 10 단계 = 31**
DELTAS_985 = [round(0.01 * i, 4) for i in range(21)]
DELTAS_EXT = [0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.80, 1.00, 1.50, 2.00]
DELTAS = DELTAS_985 + DELTAS_EXT
FIRE = 0.5
B = 2000
SEED = 986
LO, HI = 2.5, 97.5
#: 천장의 정의(측정 전에 박았다 · 사전등록 §3-2)
CEIL_FROM = 0.50

#: 🔴 983 의 모양 자(조항 68) --- 인접 칸 짝 검정의 관문
SHAPE_Z = 2.0
#: 🔴 983 모양 자의 심는 크기 쓸기(ρ 단위)
THETAS = [round(0.005 * i, 4) for i in range(41)]      # 0.000 ~ 0.200

#: 발화 행렬의 표지
FIRE_YES, FIRE_NO, UNUSABLE = 1, 0, -1


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _load(name):
    p = ROOT / "runners" / name
    if not p.is_file():
        raise SystemExit("🔴 없다: %s" % p)
    return json.loads(p.read_text(encoding="utf-8"))


def _pct(v, q):
    return None if not len(v) else float(np.percentile(np.asarray(v, dtype=float), q))


# ══════════════════════════════════════════════════════════════════════
# §1 🔴🔴🔴 발화 행렬 --- (복제 r, δ) 의 결정함수를 한 번만 계산한다
# ══════════════════════════════════════════════════════════════════════
def fire_matrix(pts, reps):
    """🔴 `M[uk][δ][r] ∈ {1 발화, 0 비발화, -1 못 씀}`.

    🔴 **985 와 «같은» 발화 정의**(`power985.planted_power` 그대로):
    `㉮ := ㉰ + δ·L` 을 심고 `partial_test` 로 「㉮ 만 선다」를 본다.
    🔴 **다른 것은 δ 격자뿐이다**(0~0.20 → 0~2.00 · 21 → 31 단계).
    """
    out = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P, R = pts[uk], reps[uk]
        n_rep = len(R[A_CTL][0])
        obs = max(abs(a - b) for a, b in zip(P[A_ORA], P[A_PRE]))
        # 🔴 `tp`(㉰ 쪽 검정)는 δ 와 «무관»하다 --- 복제마다 한 번만 푼다.
        base = {}
        for r in range(n_rep):
            ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
            pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
            pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
            h = [max(ctl) - c for c in ctl]
            sd = float(np.std(h))
            if sd < 1e-15:
                base[r] = None                    # 🔴 대조 여유가 평평 --- L 이 정의 안 된다
                continue
            mu = float(np.mean(h))
            L = [(x - mu) / sd for x in h]
            s_p = [pre[i] - pla[i] for i in range(len(NB_GRID))]
            tp = S.partial_test(s_p, h, NB)
            base[r] = (pre, pla, h, L, tp)
        M = collections.OrderedDict()
        for d in DELTAS:
            row = []
            for r in range(n_rep):
                b = base[r]
                if b is None:
                    row.append(UNUSABLE)
                    continue
                pre, pla, h, L, tp = b
                if tp.get("🔴 전수 순열 p(잔차 순열)") is None:
                    row.append(UNUSABLE)
                    continue
                ora = [pre[i] + d * L[i] for i in range(len(NB_GRID))]
                s_o = [ora[i] - pla[i] for i in range(len(NB_GRID))]
                to = S.partial_test(s_o, h, NB)
                if to.get("🔴 전수 순열 p(잔차 순열)") is None:
                    row.append(UNUSABLE)
                    continue
                row.append(FIRE_YES if (to["선다"] and not tp["선다"]) else FIRE_NO)
            M["δ=%.4f" % d] = row
        out[uk] = {"행렬": M, "복제 수": n_rep, "관측된 max|㉮ρ − ㉰ρ|": _r(obs)}
    return out


def _rate(row, idx=None):
    a = np.asarray(row if idx is None else [row[i] for i in idx], dtype=int)
    usable = int((a >= 0).sum())
    if usable == 0:
        return None, 0, 0
    fire = int((a == FIRE_YES).sum())
    return float(fire) / usable, fire, usable


# ══════════════════════════════════════════════════════════════════════
# §2 🔴🔴🔴 복제 부트스트랩 --- 「처음 0.5 이상이 되는 δ」의 구간
# ══════════════════════════════════════════════════════════════════════
def _first_cross(rates, strict):
    """🔴 **`>=` 판과 `>` 판을 «둘 다» 낸다**(티처 #124 2순위 ⓑ).

    985 의 코드는 `rate >= 0.5` 인데 다섯 문서는 「0.5 를 처음 «넘는» δ」라 적었다 ---
    `δ=0.13` 은 **넘지 않고 「같다」**.
    """
    for i, d in enumerate(DELTAS):
        v = rates[i]
        if v is None:
            continue
        if (v > FIRE) if strict else (v >= FIRE):
            return d
    return None


def bootstrap(mat):
    per = collections.OrderedDict()
    for uk, blk in mat.items():
        M = blk["행렬"]
        n_rep = blk["복제 수"]
        obs = blk["관측된 max|㉮ρ − ㉰ρ|"]
        rows = [M["δ=%.4f" % d] for d in DELTAS]
        point = [(_rate(r)[0]) for r in rows]
        rng = np.random.RandomState(SEED)
        A = np.asarray(rows, dtype=int)                  # (δ, r)
        boot_rates = np.full((B, len(DELTAS)), np.nan)
        cross_ge, cross_gt = [], []
        for b in range(B):
            idx = rng.randint(0, n_rep, size=n_rep)
            sub = A[:, idx]
            usable = (sub >= 0).sum(axis=1)
            fire = (sub == FIRE_YES).sum(axis=1)
            rt = np.where(usable > 0, fire / np.maximum(usable, 1), np.nan)
            boot_rates[b] = rt
            lst = [None if np.isnan(x) else float(x) for x in rt]
            cross_ge.append(_first_cross(lst, strict=False))
            cross_gt.append(_first_cross(lst, strict=True))
        # ── δ 별 발화율 구간 ──────────────────────────────────────
        sweep = collections.OrderedDict()
        for i, d in enumerate(DELTAS):
            col = boot_rates[:, i]
            col = col[~np.isnan(col)]
            rate, fire, usable = _rate(rows[i])
            sweep["δ=%.4f" % d] = collections.OrderedDict([
                ("쓸 수 있는 복제", usable),
                ("🔴 「㉮ 만 선다」 발화 수", fire),
                ("🔴🔴 발화율(점추정)", _r(rate, 4)),
                ("🔴🔴 부트스트랩 95% 구간",
                 [_r(_pct(col, LO), 4), _r(_pct(col, HI), 4)] if len(col) else None),
                ("🔴 구간이 0.5 를 무나",
                 bool(len(col) and _pct(col, LO) <= FIRE <= _pct(col, HI))),
            ])
        # ── 「처음 넘는 δ」의 분포 ─────────────────────────────────
        def _cross_block(cr, label):
            got = [x for x in cr if x is not None]
            never = len(cr) - len(got)
            return collections.OrderedDict([
                ("🔴 판", label),
                ("🔴 점추정(관측 한 벌)",
                 _first_cross(point, strict=(label == "`>` (문서 문언)"))),
                ("🔴🔴 부트스트랩에서 «한 번도» 안 넘은 비율", _r(float(never) / B, 4)),
                ("🔴🔴🔴 95% 구간(넘은 복제만)",
                 [_r(_pct(got, LO), 4), _r(_pct(got, HI), 4)] if got else
                 "🔴 **2000 벌 중 한 벌도 안 넘었다** --- 「검출 크기가 없다」가 아니라 "
                 "**「이 격자 밖이다」**다(조항 59)"),
                ("🔴 중앙값", _r(_pct(got, 50), 4) if got else None),
                ("🔴 구간 폭", _r(_pct(got, HI) - _pct(got, LO), 4) if got else None),
            ])
        ge = _cross_block(cross_ge, "`>=` (985 코드)")
        gt = _cross_block(cross_gt, "`>` (문서 문언)")
        # ── 🔴 관측 팔 차의 몇 배인가 --- **구간으로만 적는다** ──────
        def _ratio(blk_):
            ci = blk_["🔴🔴🔴 95% 구간(넘은 복제만)"]
            if not isinstance(ci, list) or obs in (None, 0):
                return ("🔴 **모른다** --- 구간이 격자 밖이라 배수를 못 낸다(조항 59)")
            return collections.OrderedDict([
                ("🔴🔴 관측 팔 차", obs),
                ("🔴🔴🔴 배수 구간", [_r(ci[0] / obs, 3), _r(ci[1] / obs, 3)]),
                ("🔴 그래서 적을 수 있는 문장",
                 "🔴 **「관측 팔 차의 %.1f 배 ~ %.1f 배」** --- 점추정을 소수점 여섯 자리로 "
                 "적으면 **식별되지 않는 수를 못 박는 것**이다(반증조건 8)"
                 % (ci[0] / obs, ci[1] / obs)),
            ])
        never_ge = ge["🔴🔴 부트스트랩에서 «한 번도» 안 넘은 비율"]
        per[uk] = collections.OrderedDict([
            ("🔴 관측된 max|㉮ρ − ㉰ρ|", obs),
            ("🔴 복제 수", n_rep),
            ("🔴 δ 쓸기(점추정 + 부트스트랩 95% 구간)", sweep),
            ("🔴🔴🔴 처음 0.5 «이상»이 되는 δ", ge),
            ("🔴🔴 처음 0.5 를 «넘는» δ(문서 문언)", gt),
            ("🔴🔴🔴 배수 구간(`>=` 판)", _ratio(ge)),
            ("🔴🔴 식별됐나(구간 폭이 δ 격자 한 칸 이하인가)",
             bool(ge["🔴 구간 폭"] is not None and ge["🔴 구간 폭"] <= 0.01
                  and never_ge == 0.0)),
            ("🔴 이 칸이 `False` 면", "🔴 **점추정을 소수점으로 못 박으면 안 된다**"),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **δ 쓸기를 복제 부트스트랩으로 감싼다** --- "
                 "「최소 검출 δ」자신의 구간을 낸다(사전등록 §3-1)"),
        ("🔴 부트스트랩 복제 수 B", B),
        ("🔴 씨앗", SEED),
        ("🔴 구간", "%.1f / %.1f 백분위" % (LO, HI)),
        ("🔴 왜 복제를 다시 안 뽑나",
         "🔴 **발화 판정은 (복제 r, δ) 의 «결정»함수다.** 그래서 발화 행렬을 한 번 계산하고 "
         "**복제 지표만** 복원추출한다 --- 같은 답을 훨씬 싸게 얻는다"),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2 and all(
            isinstance(v["🔴🔴🔴 처음 0.5 «이상»이 되는 δ"]
                       ["🔴🔴 부트스트랩에서 «한 번도» 안 넘은 비율"], float)
            for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **두 λ 에서 부트스트랩이 «값을 냈는가»** 하나다. 그 값이 「식별됐다」든 "
         "「안 됐다」든 통과다 --- 판정은 위 「식별됐나」 칸이 진다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §3 🔴🔴🔴 천장 --- 「δ 를 아무리 키워도 발화율은 얼마인가」
# ══════════════════════════════════════════════════════════════════════
def ceiling(mat):
    per = collections.OrderedDict()
    hi_idx = [i for i, d in enumerate(DELTAS) if d >= CEIL_FROM]
    for uk, blk in mat.items():
        M = blk["행렬"]
        n_rep = blk["복제 수"]
        rows = [M["δ=%.4f" % d] for d in DELTAS]
        point = [_rate(r)[0] for r in rows]
        hi = [point[i] for i in hi_idx if point[i] is not None]
        rng = np.random.RandomState(SEED + 1)
        A = np.asarray(rows, dtype=int)
        meds = []
        for _b in range(B):
            idx = rng.randint(0, n_rep, size=n_rep)
            sub = A[:, idx]
            usable = (sub >= 0).sum(axis=1)
            fire = (sub == FIRE_YES).sum(axis=1)
            rt = np.where(usable > 0, fire / np.maximum(usable, 1), np.nan)
            v = rt[hi_idx]
            v = v[~np.isnan(v)]
            if len(v):
                meds.append(float(np.median(v)))
        per[uk] = collections.OrderedDict([
            ("🔴 천장의 정의(측정 전에 박았다)", "`δ ≥ %.2f` 구간 발화율의 중앙값" % CEIL_FROM),
            ("🔴 그 구간의 δ 수", len(hi_idx)),
            ("🔴🔴🔴 천장(중앙값 · 점추정)", _r(float(np.median(hi)), 4) if hi else None),
            ("🔴🔴🔴 천장 95% 구간",
             [_r(_pct(meds, LO), 4), _r(_pct(meds, HI), 4)] if meds else None),
            ("🔴 최댓값(전 δ)", _r(max([p for p in point if p is not None]), 4)),
            ("🔴 δ=2.00 발화율", _r(point[-1], 4)),
            ("🔴🔴 천장이 1.0 에 «훨씬» 못 미치나(< 0.75)",
             bool(hi and float(np.median(hi)) < 0.75)),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **「이 규칙의 발화율 천장은 δ 를 아무리 키워도 얼마인가」** --- "
                 "🔴 **「최소 검출 크기」보다 훨씬 센 문장인데 985 가 안 적었다**(티처 #124 2순위 ⓑ)"),
        ("🔴 왜 이것이 더 센가",
         "🔴 **「최소 검출 크기」는 「크면 잡는다」를 전제한다.** 천장이 0.5 언저리면 "
         "**누출이 아무리 커도 절반은 못 잡는다** --- 곧 이 설계는 「δ 를 키우면 되는」 "
         "문제가 아니라 **원리상 못 재는** 문제다"),
        ("🔴 δ 격자를 넓혔다", {"985 판": [DELTAS_985[0], DELTAS_985[-1], len(DELTAS_985)],
                          "986 판": [DELTAS[0], DELTAS[-1], len(DELTAS)],
                          "🔴 왜": "🔴 985 는 `0.20` 에서 멈춰 **평평해지는 것을 보고도** "
                                 "천장을 안 적었다"}),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2 and all(
            v["🔴🔴🔴 천장(중앙값 · 점추정)"] is not None for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 천장을 «냈는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §4 🔴🔴🔴 983 에도 같은 자 --- 「U 자 되오름」의 검정력
# ══════════════════════════════════════════════════════════════════════
def shape_power(reps, g984):
    """🔴 **983 의 모양 주장이 선 자리의 검정력**(조항 60 · 사전등록 §3-3).

    🔴 **왜.** 983 의 「U 자 되오름」·모양 주장 **전부**가 **같은 7 칸 × 200 복제 격자**와
    **같은 짝 검정** 위에 서 있는데 **985 는 984 에만 물렸다** ---
    **판정문의 983 언급 다섯 곳 중 검정력을 말한 곳이 0 이다.**

    **자(조항 68 그대로)**: 인접 칸 이득 차의 점추정이 **복제 짝 SD 의 2 배**를 넘으면 「선다」.
    **검정력**: 참 효과 θ 를 심었을 때 그 자가 발화하는 비율 ---
    복제 분포를 **θ 로 옮겨** 세고, **복제 지표를 복원추출**해 구간을 낸다.
    """
    per = collections.OrderedDict()
    sec = (g984 or {}).get("§3-ⓐ 🔴🔴 2·짝SE 관문 전량 + 칸 대 칸 짝 검정") or {}
    lam = sec.get("🔴 λ 별") or {}
    for uk in ("u=0", "u=3"):
        R = reps[uk]
        n_rep = len(R[A_CTL][0])
        # 🔴 복제별 이득 Δ_r(i) = ㉮ρ − ㉯ρ (983·984 가 쓴 그 이득)
        gain = np.asarray([[R[A_ORA][i][r] - R[A_CTL][i][r] for r in range(n_rep)]
                           for i in range(len(NB_GRID))])          # (칸, 복제)
        pairs = collections.OrderedDict()
        rng = np.random.RandomState(SEED + 2)
        for i in range(len(NB_GRID) - 1):
            d_r = gain[i + 1] - gain[i]                            # 복제별 인접 칸 차
            sd = float(np.std(d_r, ddof=1))
            cen = d_r - float(np.mean(d_r))
            thr = SHAPE_Z * sd
            # ── 심은 θ 별 발화율 ────────────────────────────────
            sweep, min_th = collections.OrderedDict(), None
            for th in THETAS:
                fire = float(np.mean(np.abs(cen + th) >= thr))
                sweep["θ=%.3f" % th] = _r(fire, 4)
                if min_th is None and fire >= FIRE:
                    min_th = th
            # ── 부트스트랩 ────────────────────────────────────
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
            obs_row = None
            for row in (lam.get(uk) or {}).get("🔴 인접 칸 짝 검정") or []:
                if row.get("칸") == "%d → %d" % (NB_GRID[i], NB_GRID[i + 1]):
                    obs_row = row
                    break
            pairs["%d → %d" % (NB_GRID[i], NB_GRID[i + 1])] = collections.OrderedDict([
                ("🔴 복제 짝 SD", _r(sd)),
                ("🔴 자의 관문(2·짝SD)", _r(thr)),
                ("🔴 983·984 가 실은 점추정 차",
                 (obs_row or {}).get("점추정 차", "🔴 못 읽었다(= 0 이 아니다)")),
                ("🔴 984 가 낸 z", (obs_row or {}).get("🔴 z")),
                ("🔴🔴🔴 최소 검출 모양 크기(발화율 0.5 · 점추정)", min_th),
                ("🔴🔴🔴 그 95% 구간",
                 [_r(_pct(got, LO), 4), _r(_pct(got, HI), 4)] if got else
                 "🔴 **격자(0 ~ %.3f) 밖이다**" % THETAS[-1]),
                ("🔴 부트스트랩에서 격자 안에 «안» 든 비율",
                 _r(float(len(mins) - len(got)) / max(len(mins), 1), 4)),
                ("🔴🔴 관측 차가 최소 검출 크기보다 작나(= 이 칸은 원리상 못 잰다)",
                 (None if not isinstance((obs_row or {}).get("점추정 차"), float)
                  or min_th is None
                  else bool(abs(obs_row["점추정 차"]) < min_th)),),
                ("🔴 θ 쓸기", sweep),
            ])
        obs_max = max([abs(row.get("점추정 차") or 0.0)
                       for row in (lam.get(uk) or {}).get("🔴 인접 칸 짝 검정") or []] or [0.0])
        mins_all = [v["🔴🔴🔴 최소 검출 모양 크기(발화율 0.5 · 점추정)"] for v in pairs.values()]
        mins_ok = [m for m in mins_all if m is not None]
        per[uk] = collections.OrderedDict([
            ("🔴 인접 칸 쌍 수(분모)", len(pairs)),
            ("🔴 칸 쌍별", pairs),
            ("🔴🔴 최소 검출 모양 크기의 중앙값", _r(float(np.median(mins_ok)), 4) if mins_ok else None),
            ("🔴🔴 최소 검출 모양 크기의 최솟값", _r(min(mins_ok), 4) if mins_ok else None),
            ("🔴🔴 983·984 가 실은 |인접 칸 차| 의 최댓값", _r(obs_max)),
            ("🔴🔴🔴 최소 검출 크기(최솟값)가 관측 최대 차보다 큰가",
             bool(mins_ok and min(mins_ok) > obs_max)),
            ("🔴 원리상 못 재는 칸 쌍 수",
             len([1 for v in pairs.values()
                  if v["🔴🔴 관측 차가 최소 검출 크기보다 작나(= 이 칸은 원리상 못 잰다)"] is True])),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **983 에도 같은 자를 문다** --- 983 의 「U 자 되오름」·모양 주장이 "
                 "**같은 7 칸 × 200 복제 격자**와 **같은 짝 검정** 위에 서 있다"),
        ("🔴 왜 이 절이 있나",
         "🔴 **조항 60 미이행**(티처 #124 2순위 ⓒ) --- 985 는 검정력의 함의를 **984 에만** "
         "물렸고 **판정문의 983 언급 다섯 곳 중 검정력을 말한 곳이 0** 이었다"),
        ("🔴 자", "조항 68 그대로: **인접 칸 이득 차의 |점추정| ≥ 2 · 복제 짝 SD** 면 「선다」"),
        ("🔴 검정력의 정의", "참 효과 θ 를 심었을 때 그 자가 발화하는 비율 --- "
                       "복제 분포를 θ 로 옮겨 센다"),
        ("🔴 θ 격자", [THETAS[0], THETAS[-1], len(THETAS)]),
        ("🔴 부트스트랩 복제 수", B // 4),
        ("🔴 λ 별", per),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **복제 분포의 «모양»을 참으로 받아들인다** --- 심는 것은 «중심»뿐이고 "
         "분산은 그대로다. 곧 **참 효과가 분산도 바꾸면 이 수는 안 맞는다**. "
         "🔴 또 **인접 칸 쌍 6 개를 «따로» 재고 다중검정 보정을 «안» 했다** --- "
         "983·984 도 안 했으므로 같은 조건에서 견준 것이다"),
        ("통과", bool(len(per) == 2 and all(
            v["🔴 인접 칸 쌍 수(분모)"] == len(NB_GRID) - 1 for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 인접 칸 쌍 6 개를 전량 쟀는가**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §5 🔴 985 재현 --- 같은 격자·같은 관문에서 985 의 수가 다시 나오나
# ══════════════════════════════════════════════════════════════════════
def reproduce_985(mat, p985):
    per = collections.OrderedDict()
    old = None
    for k, v in (p985 or {}).items():
        if k.startswith("§5") and isinstance(v, dict) and "🔴 λ 별" in v:
            old = v["🔴 λ 별"]
            break
    if old is None:
        old = {}
    for uk, blk in mat.items():
        M = blk["행렬"]
        obs = blk["관측된 max|㉮ρ − ㉰ρ|"]
        rows985 = [_rate(M["δ=%.4f" % d])[0] for d in DELTAS_985]
        mind = None
        for i, d in enumerate(DELTAS_985):
            if rows985[i] is not None and rows985[i] >= FIRE:
                mind = d
                break
        o = (old or {}).get(uk) or {}
        old_v = o.get("🔴🔴🔴 발화율 0.5 를 처음 넘는 δ(= 최소 검출 크기)")
        NONE_985 = ("🔴 **985 격자(0 ~ %.2f) 안에서 «한 번도» 0.5 를 안 넘었다** --- "
                    "「검출 크기가 없다」가 아니라 **「그 격자 밖이다」**다(조항 59)"
                    % DELTAS_985[-1])
        per[uk] = collections.OrderedDict([
            ("🔴 986 이 985 격자에서 다시 낸 최소 검출 δ",
             mind if mind is not None else NONE_985),
            ("🔴 985 가 실은 값", old_v if old_v is not None else NONE_985),
            ("🔴 986 이 다시 낸 배수",
             _r(mind / obs) if (mind is not None and obs) else
             "🔴 모른다 --- 최소 검출 δ 가 985 격자 밖이다(조항 59)"),
            ("🔴 985 가 실은 배수", o.get("🔴🔴🔴 최소 검출 δ ÷ 관측 팔 차")),
            ("🔴🔴 같은가", bool(mind == old_v)),
            ("🔴 쓸 수 있는 복제(δ 별로 흔들린다 · 985 문서에 없다)",
             {"최소": min(_rate(M["δ=%.4f" % d])[2] for d in DELTAS_985),
              "최대": max(_rate(M["δ=%.4f" % d])[2] for d in DELTAS_985)}),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **985 의 수가 같은 코드 경로에서 다시 나오나**(조항 66-③ 전후)"),
        ("🔴 λ 별", per),
        ("🔴 왜", "🔴 **986 은 δ 격자만 넓혔다** --- 985 판 격자로 자르면 같은 수가 나와야 한다. "
               "안 나오면 «격자를 넓힌 것 말고 다른 것»을 고친 것이다"),
        ("통과", bool(len(per) == 2 and all(
            "🔴 986 이 985 격자에서 다시 낸 최소 검출 δ" in v for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 λ 에서 재현을 «시도했고 값을 냈는가»**"),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    gr = _load("out983_grid.json")
    rp = _load("out983_reps.json")
    g984 = _load("out984_grid.json")
    p985 = _load("out985_power.json")
    pts = P5.arms_points(gr)
    reps = P5.arms_reps(rp)
    mat = fire_matrix(pts, reps)

    out = collections.OrderedDict()
    out["무엇"] = "986 §3 — 🔴🔴🔴 **검정력 곡선에 「검정력」을 붙인다**"
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["🔴 출처"] = ["runners/out983_grid.json", "runners/out983_reps.json",
                   "runners/out984_grid.json", "runners/out985_power.json"]
    out["🔴 새 자료 학습"] = 0
    out["🔴 격자·복제(985 와 «같다»)"] = {
        "격자 칸 수": len(NB_GRID), "N_B": NB_GRID,
        "복제 수": mat["u=0"]["복제 수"],
        "🔴 986 이 바꾼 것": "**δ 격자뿐이다**(0~0.20 21 단계 → 0~2.00 31 단계) "
                       "+ **복제 부트스트랩을 감쌌다**",
    }
    out["§1 🔴🔴🔴 부트스트랩 감싼 δ 쓸기"] = bootstrap(mat)
    out["§2 🔴🔴🔴 천장 — 「δ 를 아무리 키워도 발화율은 얼마인가」"] = ceiling(mat)
    out["§3 🔴🔴🔴 983 에도 같은 자 — 「U 자 되오름」의 검정력"] = shape_power(reps, g984)
    out["§4 🔴 985 재현"] = reproduce_985(mat, p985)
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    out["🔴 이 산출물의 `통과`"] = "네 절이 전부 «값을 냈는가»다. 판정은 각 절의 진단 칸이 진다"
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["power"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    b = r["§1 🔴🔴🔴 부트스트랩 감싼 δ 쓸기"]["🔴 λ 별"]
    c = r["§2 🔴🔴🔴 천장 — 「δ 를 아무리 키워도 발화율은 얼마인가」"]["🔴 λ 별"]
    print(json.dumps({
        "통과": r["통과"],
        "u=0 처음 0.5 이상 δ 구간": b["u=0"]["🔴🔴🔴 처음 0.5 «이상»이 되는 δ"]["🔴🔴🔴 95% 구간(넘은 복제만)"],
        "u=0 식별됐나": b["u=0"]["🔴🔴 식별됐나(구간 폭이 δ 격자 한 칸 이하인가)"],
        "u=0 천장": c["u=0"]["🔴🔴🔴 천장(중앙값 · 점추정)"],
        "u=3 천장": c["u=3"]["🔴🔴🔴 천장(중앙값 · 점추정)"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
