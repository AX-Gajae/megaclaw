#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""985 §3 — 🔴🔴🔴 **검정력을 «먼저» 재고, 그 다음에 위약 배터리를 읽는다**.

🔴 **왜 (티처 #123 2순위).**
- **ⓐ** 984 는 「대조 여유가 두 계열에 «함께» 들어가 생긴 구성상 결합」이라 적었는데
  **`목표 이동 = ㉮ρ − ㉱ρ` 에는 대조가 «안» 들어간다.** 984 자신의 사전등록이
  그 문장 «세 줄 위»에 「대조 팔만의 함수다」를 적어 놨다 --- **자 ②는 이미 거짓인
  가설을 검정했다.** 그리고 이름 `오라클 여유` 는 **오라클과 아무 상관이 없다** ---
  이름이 서사를 만들었다. 🔴 **985 는 `대조 여유` 로 고쳐 부른다.**
- **ⓑ** **위약 팔이 대조 팔의 사본이고 `㉰` 가 `㉮` 의 사본**이라
  「둘 다 선다 → 결합」 규칙은 **반드시** 발화한다. 🔴 **팔 사이 상관을 «먼저» 싣는다.**
- **ⓒ** `u=3` 의 네 칸은 **한 검정이 네 번 인쇄된 것**이다 --- 기계로 증명한다.
- **ⓓ** 자 ③(붓스트랩)을 **판정 규칙 «안»으로** 올린다. 그리고 **이산 바닥**과
  **정보성 검열**을 잰다.
- 🔴🔴🔴 **새 측정**: **심은 누출 검정력 곡선** --- 「누출이 진짜 있었다면 984 의 자가
  그것을 잡았을까」를 δ 를 쓸어 잰다.

씀:
    python3 runners/power985.py --stage power --ref <40자 sha>
"""
import argparse
import collections
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle985 as CY                                   # noqa: E402
import stat983 as S                                     # noqa: E402
import mix980 as MX                                     # noqa: E402

OUT = "runners/out985_power.json"

NB_GRID = list(MX.NB_GRID)
NB = [float(n) for n in NB_GRID]
CANON = "R_pool 묶음"
A_CTL = "㉯ 대조"
A_ORA = "㉮ 층화 · 오라클(유보 전량 구성비)"
A_PRE = "㉰ 층화 · 절단 앞(블록 <j 구성비)"
A_PLA = "㉱ 위약(절단 앞 hplt 공급 몫)"
REPS_CTL = "㉯ 대조 팔 ρ(복제별)"

#: 사전등록 §9 --- 심은 누출 δ 쓸기
DELTAS = [round(0.01 * i, 4) for i in range(21)]
FIRE = 0.5
LO, HI = 2.5, 97.5


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _load(name):
    p = ROOT / "runners" / name
    if not p.is_file():
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % name)
    return json.loads(p.read_text(encoding="utf-8"))


def _rank(v):
    """동률 평균 순위(`stat983._rank` 와 같은 자)."""
    return list(S._rank(v))


def _pear(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if np.std(x) < 1e-15 or np.std(y) < 1e-15:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def arms_points(gr):
    cells = gr["🔴🔴 칸"]
    out = {}
    for uk in ("u=0", "u=3"):
        out[uk] = {a: [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][a][CANON]
                       for n in NB_GRID]
                   for a in (A_CTL, A_ORA, A_PRE, A_PLA)}
    return out


def arms_reps(rp):
    cells = rp["🔴 칸"]
    out = {}
    for uk in ("u=0", "u=3"):
        ctl = [cells["N_B=%d · %s" % (n, uk)][REPS_CTL][CANON] for n in NB_GRID]
        d = {A_CTL: ctl}
        for a in (A_ORA, A_PRE, A_PLA):
            d[a] = [[c + x for c, x in
                     zip(ctl[i], cells["N_B=%d · %s" % (NB_GRID[i], uk)][a][CANON])]
                    for i in range(len(NB_GRID))]
        out[uk] = d
    return out


# ══════════════════════════════════════════════════════════════════════
# §1 🔴 이름 정정 — `오라클 여유` → `대조 여유`
# ══════════════════════════════════════════════════════════════════════
def _head_source():
    """🔴 **「대조 여유」가 어느 팔에 의존하나를 «소스에서» 읽는다**(조항 64: 자에 검정력을).

    `leak984.py` 와 `stat983.py` 에서 `head =` 대입식을 뽑아 **어느 팔 상수가 그 식에
    나타나나**를 센다. 🔴 만약 코드가 오라클 팔을 썼다면 이 자가 그것을 «본다» ---
    곧 「의존하지 않는다」는 리터럴이 아니라 **잰 값**이다.
    """
    rows = collections.OrderedDict()
    pats = {"㉯ 대조": ("A_CTL", "ctl"), "㉮ 오라클": ("A_ORA", "ora", "trt"),
            "㉰ 절단 앞": ("A_PRE", "pre"), "㉱ 위약": ("A_PLA", "pla")}
    for rel in ("runners/leak984.py", "runners/stat983.py"):
        p = ROOT / rel
        if not p.is_file():
            rows[rel] = "🔴 못 읽었다"
            continue
        lines = [ln.strip() for ln in p.read_text(encoding="utf-8").split("\n")
                 if re.match(r"^\s*head\s*=", ln)]
        hit = collections.OrderedDict()
        for arm, toks in pats.items():
            hit[arm] = bool(any(any(re.search(r"\b%s\b" % t, ln) for t in toks)
                                for ln in lines))
        rows[rel] = {"🔴 `head =` 대입식": lines or "🔴 못 찾았다",
                     "🔴 그 식에 나타나는 팔": hit}
    arms = collections.OrderedDict()
    for arm in pats:
        arms[arm] = bool(any(isinstance(v, dict) and v["🔴 그 식에 나타나는 팔"][arm]
                             for v in rows.values()))
    return rows, arms


def rename():
    src, arms = _head_source()
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **`오라클 여유` 라는 이름을 `대조 여유` 로 고친다**"),
        ("🔴 정의(984 의 코드 그대로)", "head[i] = max(대조ρ) − 대조ρ[i]"),
        ("🔴🔴 소스에서 읽은 `head =` 대입식", src),
        ("🔴🔴 그 식에 나타나는 팔(= 잰 값이다 · 리터럴이 아니다)", arms),
        ("🔴🔴 그 양이 «함수로» 의존하는 팔",
         [k for k, v in arms.items() if v] or "🔴 못 읽었다"),
        ("🔴🔴 그 양이 오라클 팔(`㉮`)에 의존하나", bool(arms.get("㉮ 오라클"))),
        ("🔴🔴🔴 984 의 「구성상 결합」 문언이 왜 틀렸나", (
            "🔴 984 는 「대조 여유가 «두 계열에 함께» 들어가 생긴 구성상 결합」이라 적었다. "
            "그런데 다른 계열은 **`목표 이동 = ㉮ρ − ㉱ρ`** 이고 **거기엔 대조가 안 들어간다.** "
            "🔴 **984 자신의 사전등록 §2-3 이 그 문장 세 줄 «위»에 「대조 팔만의 함수다」를 "
            "적어 놨다.** 곧 **자 ②(「여유를 대조가 아닌 팔로 바꿔도 서나」)는 이미 거짓인 "
            "가설을 검정했다** --- 「대조가 양쪽에 들어간다」는 애초에 참인 적이 없다"),
        ),
        ("🔴🔴🔴 985 의 판정 문언", (
            "🔴 **「누출의 지문이 아니다」까지는 산다 --- 미래를 안 보는 `㉰` 팔이 «같은 만큼» "
            "서기 때문이다.** 🔴 **그러나 「구성상 결합이다」는 못 적는다** --- 그 진단이 "
            "가리킨 기전(대조가 두 계열에 함께 들어간다)이 **거짓**이고, 아래 §5 가 보이듯 "
            "**이 설계는 애초에 두 팔을 못 가른다.** 옳은 문장은 "
            "**「누출에 특이적이지 않다 · 이 설계로는 못 잰다」**다"),
        ),
        # 🔴 **잰 값이다** --- 소스에서 `head =` 식을 찾았고 그 식이 대조 팔을 «쓰고»
        #    오라클 팔을 «안 쓰는가». 식을 못 찾으면 「모른다」라 불통과다(조항 59).
        ("통과", bool(arms.get("㉯ 대조") and not arms.get("㉮ 오라클")
                    and all(isinstance(v, dict) and v["🔴 `head =` 대입식"] != "🔴 못 찾았다"
                            for v in src.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **소스의 `head =` 식을 찾았고, 그 식이 대조 팔을 쓰고 «오라클 팔을 안 쓰는가».** "
         "식을 못 찾으면 「모른다」라 불통과다(조항 59). "
         "🔴 이 자는 **검정력이 있다** --- 코드가 오라클 팔을 썼다면 위 「나타나는 팔」 칸이 "
         "그것을 보여 준다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §2 🔴🔴 위약 배터리를 «쓰기 전에» — 팔 사이 상관
# ══════════════════════════════════════════════════════════════════════
def arm_corr(pts):
    per = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P = pts[uk]
        d = [abs(a - b) for a, b in zip(P[A_ORA], P[A_PRE])]
        per[uk] = collections.OrderedDict([
            ("🔴🔴 corr(㉯ 대조, ㉱ 위약)", _r(_pear(P[A_CTL], P[A_PLA]))),
            ("🔴🔴 corr(㉮ 오라클, ㉰ 절단 앞)", _r(_pear(P[A_ORA], P[A_PRE]))),
            ("🔴🔴🔴 max|㉮ρ − ㉰ρ|", _r(max(d))),
            ("평균|㉮ρ − ㉰ρ|", _r(sum(d) / len(d))),
            ("㉮ρ 폭(max−min)", _r(max(P[A_ORA]) - min(P[A_ORA]))),
            ("㉰ρ 폭(max−min)", _r(max(P[A_PRE]) - min(P[A_PRE]))),
            ("🔴 corr(㉮, ㉯)", _r(_pear(P[A_ORA], P[A_CTL]))),
            ("🔴 corr(㉰, ㉯)", _r(_pear(P[A_PRE], P[A_CTL]))),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **위약 배터리를 «쓰기 전에» 팔 사이 상관을 싣는다**"),
        ("🔴 왜 먼저인가", (
            "🔴 **「둘 다 선다 → 결합」 규칙은 두 팔이 서로 사본이면 «반드시» 발화한다.** "
            "그건 자료가 아니라 **배선**이 정한 것이다. 그러므로 그 규칙을 읽기 «전»에 "
            "**두 팔이 얼마나 사본인지**를 먼저 봐야 한다(조항 67 의 정신)"),
        ),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 한 줄", (
            "🔴 **`u=3` 에서 위약 팔은 대조 팔의 상관 %s 사본이고 `㉰` 는 `㉮` 의 상관 %s "
            "사본이다.** 두 팔의 최대 차는 `%s` 로 격자 폭보다 작다"
            % (per["u=3"]["🔴🔴 corr(㉯ 대조, ㉱ 위약)"],
               per["u=3"]["🔴🔴 corr(㉮ 오라클, ㉰ 절단 앞)"],
               per["u=3"]["🔴🔴🔴 max|㉮ρ − ㉰ρ|"])),
        ),
        ("통과", bool(all(v.get("🔴🔴 corr(㉯ 대조, ㉱ 위약)") is not None
                        and v.get("🔴🔴 corr(㉮ 오라클, ㉰ 절단 앞)") is not None
                        and v.get("🔴🔴🔴 max|㉮ρ − ㉰ρ|") is not None
                        for v in per.values()) and len(per) == 2)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **λ 둘 다에서 상관 셋이 «값을 냈는가»** --- 표준편차가 0 이면 `None` 이 나오고 "
         "그때는 불통과다(「상관 0」이 아니라 「못 잰다」다 · 조항 59)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §3 🔴 `u=3` 네 칸은 **한 검정**이다
# ══════════════════════════════════════════════════════════════════════
def one_test(pts):
    per = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P = pts[uk]
        head = [max(P[A_CTL]) - c for c in P[A_CTL]]
        head_pla = [max(P[A_PLA]) - c for c in P[A_PLA]]
        so = [P[A_ORA][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        sp = [P[A_PRE][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        rso, rsp = _rank(so), _rank(sp)
        rh, rhp = _rank(head), _rank(head_pla)
        four = {
            "① ㉮ vs 대조 여유": S.partial_test(so, head, NB),
            "① ㉰ vs 대조 여유": S.partial_test(sp, head, NB),
            "② ㉮ vs 위약 여유": S.partial_test(so, head_pla, NB),
            "② ㉰ vs 위약 여유": S.partial_test(sp, head_pla, NB),
        }
        vals = {k: (v.get("🔴 부분상관(잔차 피어슨)"), v.get("🔴 전수 순열 p(잔차 순열)"))
                for k, v in four.items()}
        same_a = bool(rso == rsp)
        same_b = bool(rh == rhp)
        per[uk] = collections.OrderedDict([
            ("🔴 rank(목표이동 ㉮)", rso),
            ("🔴 rank(목표이동 ㉰)", rsp),
            ("🔴🔴 두 순위 벡터가 같은가", same_a),
            ("🔴 rank(대조 여유)", rh),
            ("🔴 rank(위약 여유)", rhp),
            ("🔴🔴 두 순위 벡터가 같은가", same_b),
            ("🔴 네 검정의 (부분상관, p)", vals),
            ("🔴🔴 네 값이 전부 같은가", bool(len(set(vals.values())) == 1)),
            ("🔴🔴🔴 네 칸이 한 검정인가", bool(same_a and same_b)),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`u=3` 의 네 칸은 «한 검정»이 네 번 인쇄된 것이다** --- 증명한다"),
        ("🔴 증명의 얼개", (
            "🔴 `stat983.partial_test(a, b, c)` 는 `_resid_on` 을 지나는데 그 함수는 "
            "**`rank(a)` 와 `rank(c)` 만** 쓴다(`rx = _rank(x)`). 그러므로 "
            "**`partial_test` 는 `(rank(a), rank(b))` 만의 함수**다. "
            "🔴 곧 **`rank(㉮ 목표이동) == rank(㉰ 목표이동)` 이고 "
            "`rank(대조 여유) == rank(위약 여유)` 이면 네 검정은 «같은 함수의 같은 입력»이다**"),
        ),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 그래서", (
            "🔴 **984 의 판정표에서 `u=3` 열에 `0.749363 / 0.061706` 이 네 번 찍힌 것은 "
            "「네 자가 같은 답을 냈다」가 아니라 「한 자를 네 번 인쇄했다」다.** "
            "🔴 **독립된 위약 넷이라 읽으면 증거가 네 배로 보인다 --- 실제 증거는 하나다**"),
        ),
        # 🔴 **잰 값이다** --- 「순위 벡터가 같으면 네 값도 같아야 한다」는 예측을
        #    λ 둘 다에서 확인한다. 어긋나면 내 증명이 틀린 것이므로 **불통과**다.
        ("통과", bool(len(per) == 2 and all(
            v["🔴🔴 네 값이 전부 같은가"] == v["🔴🔴🔴 네 칸이 한 검정인가"]
            for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **「순위 벡터 둘이 같다」와 「네 검정 값이 같다」가 λ 둘 다에서 «일치하는가».** "
         "어긋나면 내 증명이 틀린 것이므로 불통과다 --- 🔴 **이 자는 떨어질 수 있다**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §4 🔴🔴 자 ③(붓스트랩)을 **판정 규칙 안**으로
# ══════════════════════════════════════════════════════════════════════
def _ci(v):
    if not v:
        return {"🔴": "🔴 못 잰다 --- 쓸 수 있는 복제가 0 이다(조항 59)"}
    a = np.asarray(v, float)
    lo, hi = float(np.percentile(a, LO)), float(np.percentile(a, HI))
    return collections.OrderedDict([
        ("복제 수", len(v)), ("평균", _r(float(a.mean()))),
        ("중앙값", _r(float(np.median(a)))),
        ("95% 구간 아래", _r(lo)), ("95% 구간 위", _r(hi)),
        ("🔴 0 을 포함하나", bool(lo <= 0.0 <= hi)),
    ])


def boot_gate(pts, reps):
    per = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P = pts[uk]
        R = reps[uk]
        head = [max(P[A_CTL]) - c for c in P[A_CTL]]
        so = [P[A_ORA][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        sp = [P[A_PRE][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        t_o = S.partial_test(so, head, NB)
        t_p = S.partial_test(sp, head, NB)
        n_rep = len(R[A_CTL][0])
        bo, bp, bd = [], [], []
        dropped, drop_mono = [], 0
        fire_leak = fire_both = 0
        for r in range(n_rep):
            ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
            ora = [R[A_ORA][i][r] for i in range(len(NB_GRID))]
            pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
            pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
            h = [max(ctl) - c for c in ctl]
            s_o = [ora[i] - pla[i] for i in range(len(NB_GRID))]
            s_p = [pre[i] - pla[i] for i in range(len(NB_GRID))]
            to, tp = S.partial_test(s_o, h, NB), S.partial_test(s_p, h, NB)
            co = to.get("🔴 부분상관(잔차 피어슨)")
            cp = tp.get("🔴 부분상관(잔차 피어슨)")
            if to["선다"] and not tp["선다"]:
                fire_leak += 1
            if to["선다"] and tp["선다"]:
                fire_both += 1
            if co is None or cp is None:
                #: 🔴 **버려진 벌** --- 잔차 SD 가 0 이라 「못 잰다」로 떨어진 벌.
                #:   그 벌의 계열이 `N_B` 의 «완전 단조» 함수인지 잰다(정보성 검열).
                for name, ser in (("목표이동 ㉮", s_o), ("대조 여유", h),
                                  ("목표이동 ㉰", s_p)):
                    sp_ = S._spear(ser, NB)
                    if sp_ is not None and abs(sp_) > 0.999:
                        drop_mono += 1
                        break
                dropped.append(r)
                continue
            bo.append(co)
            bp.append(cp)
            bd.append(co - cp)
        ci_o, ci_p, ci_d = _ci(bo), _ci(bp), _ci(bd)
        g1 = bool(t_o["선다"])
        g2 = bool(ci_o.get("🔴 0 을 포함하나") is False)
        g3 = bool(ci_d.get("🔴 0 을 포함하나") is False)
        per[uk] = collections.OrderedDict([
            ("🔴 점추정 ㉮ (부분상관 / p / 선다)",
             [t_o.get("🔴 부분상관(잔차 피어슨)"), t_o.get("🔴 전수 순열 p(잔차 순열)"),
              t_o["선다"]]),
            ("🔴 점추정 ㉰ (부분상관 / p / 선다)",
             [t_p.get("🔴 부분상관(잔차 피어슨)"), t_p.get("🔴 전수 순열 p(잔차 순열)"),
              t_p["선다"]]),
            ("🔴 복제 분모(전량)", n_rep),
            ("🔴 쓸 수 있는 복제", len(bo)),
            ("🔴🔴 버려진 복제 수", len(dropped)),
            ("🔴🔴🔴 버려진 복제 중 「어떤 계열이 `N_B` 의 완전 단조」인 것", drop_mono),
            ("🔴🔴🔴 버려진 것이 전부 완전 단조인가(= 정보성 검열)",
             bool(dropped and drop_mono == len(dropped))),
            ("🔴 (㉮−㉱, 대조 여유) 부분상관 95% 구간", ci_o),
            ("🔴 (㉰−㉱, 대조 여유) 부분상관 95% 구간", ci_p),
            ("🔴🔴 둘의 차(㉮ − ㉰) 95% 구간", ci_d),
            ("🔴 붓스트랩 평균 − 점추정",
             _r((ci_o.get("평균") or 0) - (t_o.get("🔴 부분상관(잔차 피어슨)") or 0))),
            ("🔴🔴 복제에서 자 ① 규칙 「㉮ 만 선다」 발화율",
             _r(float(fire_leak) / len(bo), 4) if bo else None),
            ("🔴🔴 복제에서 「둘 다 선다」 발화율",
             _r(float(fire_both) / len(bo), 4) if bo else None),
            ("🔴🔴🔴 관문 ㉠ 점추정 순열 p < 0.05", g1),
            ("🔴🔴🔴 관문 ㉡ 붓스트랩 구간이 0 을 «안» 포함", g2),
            ("🔴🔴🔴 관문 ㉢ 두 팔 차 구간이 0 을 «안» 포함", g3),
            ("🔴🔴🔴 셋을 다 넘어 「선다」로 적을 수 있나", bool(g1 and g2 and g3)),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **자 ③(복제 붓스트랩)을 «판정 규칙 안»으로 올린다**"),
        ("🔴 왜", (
            "🔴 **984 는 사전등록 §2-3 에서 판정을 자 ①·②로만 정하고 자 ③을 뺐다 --- "
            "그 자가 자기 헤드라인을 죽이는 «유일한» 자였다.** "
            "🔴 983 에게는 조항 59/68 로 「안 쟀다」를 물리고 같은 잣대를 자기 헤드라인에는 "
            "안 물렸다(티처 #123 2순위 ⓓ)"),
        ),
        ("🔴 유의수준", 0.05),
        ("🔴 붓스트랩 백분위 아래 / 위", [LO, HI]),
        ("🔴 등록 관문 셋(사전등록 §3-4)", [
            "㉠ 점추정 순열 p < 0.05",
            "㉡ 복제 붓스트랩 95% 구간이 0 을 «안» 포함",
            "㉢ 두 팔 차의 95% 구간이 0 을 «안» 포함(특이성)",
        ]),
        ("🔴 λ 별", per),
        ("통과", bool(len(per) == 2 and all(
            v["🔴 쓸 수 있는 복제"] > 0
            and isinstance(v["🔴🔴🔴 관문 ㉡ 붓스트랩 구간이 0 을 «안» 포함"], bool)
            and isinstance(v["🔴🔴🔴 관문 ㉢ 두 팔 차 구간이 0 을 «안» 포함"], bool)
            for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **관문 셋이 λ 둘 다에서 «값을 냈는가»** --- 쓸 수 있는 복제가 0 이면 구간을 "
         "못 내고 그때는 불통과다(「0 을 포함한다」가 아니라 「못 잰다」다 · 조항 59). "
         "「선다」인지는 위 칸이 진다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §5 🔴🔴🔴 심은 누출 검정력 곡선 (이 사이클의 새 측정)
# ══════════════════════════════════════════════════════════════════════
def planted_power(pts, reps):
    per = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        P = pts[uk]
        R = reps[uk]
        obs = max(abs(a - b) for a, b in zip(P[A_ORA], P[A_PRE]))
        n_rep = len(R[A_CTL][0])
        rows = collections.OrderedDict()
        min_delta = None
        for d in DELTAS:
            fire = both = usable = 0
            for r in range(n_rep):
                ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
                pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
                pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
                h = [max(ctl) - c for c in ctl]
                sd = float(np.std(h))
                if sd < 1e-15:
                    continue
                mu = float(np.mean(h))
                L = [(x - mu) / sd for x in h]
                ora = [pre[i] + d * L[i] for i in range(len(NB_GRID))]
                s_o = [ora[i] - pla[i] for i in range(len(NB_GRID))]
                s_p = [pre[i] - pla[i] for i in range(len(NB_GRID))]
                to = S.partial_test(s_o, h, NB)
                tp = S.partial_test(s_p, h, NB)
                if to.get("🔴 전수 순열 p(잔차 순열)") is None \
                        or tp.get("🔴 전수 순열 p(잔차 순열)") is None:
                    continue
                usable += 1
                if to["선다"] and not tp["선다"]:
                    fire += 1
                if to["선다"] and tp["선다"]:
                    both += 1
            rate = (float(fire) / usable) if usable else None
            rows["δ=%.2f" % d] = collections.OrderedDict([
                ("쓸 수 있는 복제", usable),
                ("🔴 「㉮ 만 선다」 발화 수", fire),
                ("🔴🔴 발화율", _r(rate, 4)),
                ("「둘 다 선다」 발화율",
                 _r(float(both) / usable, 4) if usable else None),
            ])
            if min_delta is None and rate is not None and rate >= FIRE:
                min_delta = d
        per[uk] = collections.OrderedDict([
            ("🔴 관측된 max|㉮ρ − ㉰ρ|", _r(obs)),
            ("🔴 δ 쓸기", rows),
            ("🔴🔴🔴 발화율 0.5 를 처음 넘는 δ(= 최소 검출 크기)",
             min_delta if min_delta is not None else
             "🔴 **쓸어 본 범위(0 ~ %.2f) 안에서 «한 번도» 0.5 를 안 넘었다** --- "
             "「검출 크기가 없다」가 아니라 **「이 범위 밖이다」**다(조항 59)" % DELTAS[-1]),
            ("🔴🔴🔴 최소 검출 δ ÷ 관측 팔 차",
             _r(min_delta / obs) if (min_delta and obs) else
             "🔴 모른다 --- 최소 검출 δ 가 범위 밖이다(**하한은 %.2f / %s = %s 배**)"
             % (DELTAS[-1], _r(obs), _r(DELTAS[-1] / obs) if obs else None)),
            ("🔴 하한(범위 끝 δ ÷ 관측 팔 차)", _r(DELTAS[-1] / obs) if obs else None),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **심은 누출 검정력 곡선** --- 「누출이 «진짜로» 있었다면 984 의 "
                 "자 ① 이 그것을 잡았을까」"),
        ("🔴 δ 최소", DELTAS[0]),
        ("🔴 δ 최대", DELTAS[-1]),
        ("🔴 δ 단계 수", len(DELTAS)),
        ("🔴 발화 관문", FIRE),
        ("🔴 격자 칸 수", len(NB_GRID)),
        ("🔴 설계(사전등록 §3-5 · 측정 전에 박았다)", [
            "① 200 복제의 `㉰`(절단 앞) 팔을 **귀무 팔**로 쓴다 --- 그 팔은 미래를 안 본다",
            "② `㉮` 를 **`㉰ + δ·L`** 로 심는다. `L` 은 **대조 여유의 표준화 벡터** --- "
            "곧 **누출이 있었다면 나타났어야 할 «바로 그» 모양**이다",
            "③ `δ` 를 0 ~ 0.20 · 21 단계로 쓸어 **자 ① 규칙 「㉮ 만 선다」의 발화율**을 센다",
            "④ 발화율이 **0.5** 를 처음 넘는 δ 를 **최소 검출 크기**로 싣고 "
            "**관측된 `max|㉮ρ−㉰ρ|`** 와 나란히 놓는다",
        ]),
        ("🔴 λ 별", per),
        ("⚠ 이 자의 한계(조항 61)", (
            "🔴 **심는 모양을 「대조 여유의 표준화 벡터」로 골랐다** --- 그 방향은 검정에 "
            "**가장 유리한** 방향이다(부분상관이 재는 바로 그 축). 곧 여기서 나온 검출 크기는 "
            "**낙관적 하한**이고, 다른 모양의 누출은 **더 못 잡는다**. "
            "🔴 또 δ 는 **모든 칸에 같은 배율**로 들어가므로 「칸마다 다른 누출」은 안 쟀다"),
        ),
        # 🔴 **잰 값이다** --- 모든 δ 칸이 «쓸 수 있는 복제»를 냈고 발화율이 정의됐나.
        #    그리고 **곡선이 단조롭게 오르는가**(δ=0 의 발화율 < δ=최대의 발화율) ---
        #    안 오르면 심는 자체가 안 먹은 것이므로 이 자는 **떨어질 수 있다**.
        ("통과", bool(len(per) == 2 and all(
            all(r["🔴🔴 발화율"] is not None and r["쓸 수 있는 복제"] > 0
                for r in v["🔴 δ 쓸기"].values())
            and (list(v["🔴 δ 쓸기"].values())[-1]["🔴🔴 발화율"]
                 > list(v["🔴 δ 쓸기"].values())[0]["🔴🔴 발화율"])
            for v in per.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **① 모든 δ 칸이 발화율을 냈고 ② 끝 δ 의 발화율이 δ=0 보다 «높은가».** "
         "②가 거짓이면 심는 것 자체가 안 먹은 것이라 곡선을 못 읽는다 --- "
         "🔴 **이 자는 떨어질 수 있다**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §6 🔴 이산 바닥
# ══════════════════════════════════════════════════════════════════════
def discrete_floor(pts):
    tot = math.factorial(len(NB_GRID))
    #: 🔴 잔차 순열 p 가 «달성할 수 있는» 값의 집합 --- 분자는 짝수여야 한다(± 대칭).
    vals = sorted({round(k / float(tot), 8) for k in range(2, 21, 2)})
    #: 🔴 **바닥을 「시연」한다** --- 완전 단조인 실제 짝(격자와 그 로그)을 순열 검정에 넣는다.
    _s, floor_p, _t = S.perm_p(list(NB), [math.log(x) for x in NB])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **전수 순열 p 의 «이산 바닥»** --- `p` 가 작다는 것이 무슨 뜻인가"),
        ("전수 벌 수(7!)", tot),
        ("🔴 984 가 실은 p 둘", collections.OrderedDict([
            ("u=0 ㉮ p", 0.001587),
            ("🔴 그 정체", "%d / %d" % (round(0.001587 * tot), tot)),
            ("u=0 ㉰ p", 0.000794),
            ("🔴 그 정체", "%d / %d" % (round(0.000794 * tot), tot)),
        ])),
        ("🔴 달성 가능한 최소 p", _r(2.0 / tot, 8)),
        ("🔴 아래에서 열 번째까지 달성 가능한 p", vals),
        ("🔴🔴🔴 그래서", (
            "🔴 **`0.001587` 은 바닥에서 «네 번째» 칸이고 `0.000794` 는 «두 번째» 칸이다.** "
            "둘의 차는 **순열 4 벌**이다 --- 「더 세게 선다」로 읽을 폭이 아니다. "
            "🔴🔴 **그리고 순열 p 는 그 7 점을 «고정한» 조건부 p 다** --- "
            "「관측된 순위가 거의 완전 단조다」만 말하고 **「그 7 점이 다시 나올까」는 "
            "원리상 못 말할 수밖에 없다.** 붓스트랩이 그것을 말했고 답은 **「안 나온다」**다"),
        ),
        # 🔴 **잰 값이다** --- 완전 단조인 «실제» 짝을 만들어 순열 p 를 돌려
        #    그 값이 바닥 `2/n!` 과 같은가를 확인한다. 다르면 내 바닥 주장이 틀렸다.
        ("🔴 바닥 시연 — 완전 단조인 짝의 실측 p", floor_p),
        ("🔴 바닥 시연 — 그 값이 `2 / n!` 과 같은가", bool(floor_p == _r(2.0 / tot, 6))),
        ("통과", bool(floor_p is not None and floor_p == _r(2.0 / tot, 6))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **완전 단조인 «실제» 짝을 순열 검정에 넣어 나온 p 가 `2 / n!` 과 같은가.** "
         "🔴 시연이므로 **떨어질 수 있다** --- 바닥이 다르면 여기서 갈린다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    gr = _load("out983_grid.json")
    rp = _load("out983_reps.json")
    pts, reps = arms_points(gr), arms_reps(rp)
    out = collections.OrderedDict()
    out["무엇"] = ("985 §3 — 🔴🔴🔴 **검정력을 «먼저» 재고 위약 배터리를 그 다음에 읽는다**")
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["🔴 출처"] = ["runners/out983_grid.json", "runners/out983_reps.json"]
    out["🔴 새 자료 학습"] = 0
    out["§1 🔴 이름 정정 — `오라클 여유` → `대조 여유`"] = rename()
    out["§2 🔴🔴 팔 사이 상관(위약 배터리를 «쓰기 전에»)"] = arm_corr(pts)
    out["§3 🔴🔴🔴 `u=3` 네 칸은 한 검정이다"] = one_test(pts)
    out["§4 🔴🔴 자 ③(붓스트랩)을 판정 규칙 안으로"] = boot_gate(pts, reps)
    out["§5 🔴🔴🔴 심은 누출 검정력 곡선(새 측정)"] = planted_power(pts, reps)
    out["§6 🔴 이산 바닥"] = discrete_floor(pts)
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["power"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    p5 = r["§5 🔴🔴🔴 심은 누출 검정력 곡선(새 측정)"]["🔴 λ 별"]
    print(json.dumps({
        "통과": r["통과"],
        "u=0 최소 검출 δ": p5["u=0"]["🔴🔴🔴 발화율 0.5 를 처음 넘는 δ(= 최소 검출 크기)"],
        "u=0 관측 팔 차": p5["u=0"]["🔴 관측된 max|㉮ρ − ㉰ρ|"],
        "u=3 최소 검출 δ": p5["u=3"]["🔴🔴🔴 발화율 0.5 를 처음 넘는 δ(= 최소 검출 크기)"],
    }, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
