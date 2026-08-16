#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 §1·§2·§7 — 🔴🔴🔴 **미게재 결과를 전량 게재하고, 그 결과를 자기 위약에 물린다**.

사전등록 `docs/prereg_984_leak_or_coupling.md` §2 · §7 을 따른다.

🔴 **왜 (티처 #122 C2).** 983 은 자기 격자에 자기 추정기를 물려 예산 공변량 검정 **넷**을
냈고, 그중 **「서는」 하나**(`u=0` `(㉮−㉱ 목표 이동, 오라클 여유)` 부분상관 `0.971938` ·
p `0.001587`)를 **판정문·카드·인계 카드·치환표·원장 어디에도 안 실었다**(grep 0).
**그것도 자기 누출 서사를 「받치는」 방향이었다** --- #121 이 982 에서 잡은
「나란히 재고 유리한 쪽만 게재」의 정확한 재발이다.

🔴 **새 학습 0.** 값은 전부 `out983_grid.json`·`out983_stat.json`·`out981_*.json` 에서 온다.

씀:
    python3 runners/leak984.py --stage leak --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import itertools
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle984 as CY                                # noqa: E402
import stat983 as S                                  # noqa: E402

OUT = "runners/out984_leak.json"
NB_GRID = list(S.NB_GRID)
NB = [float(n) for n in NB_GRID]
LOGNB = [math.log(n) for n in NB]
CANON = S.CANON

A_CTL = "㉯ 대조"
A_ORA = "㉮ 층화 · 오라클(유보 전량 구성비)"
A_PRE = "㉰ 층화 · 절단 앞(블록 <j 구성비)"
A_PLA = "㉱ 위약(절단 앞 hplt 공급 몫)"
REPS_CTL = "㉯ 대조 팔 ρ(복제별)"

#: 사전등록 §9 --- 붓스트랩 백분위
LO, HI = 2.5, 97.5


def _r(x, n=6):
    return S._r(x, n)


def _load(name):
    p = ROOT / "runners" / name
    if not p.is_file():
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % name)
    return json.loads(p.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════
# §1 🔴🔴 예산 공변량 검정 **전량 여덟** — 983 이 넷을 냈고 하나를 안 실었다
# ══════════════════════════════════════════════════════════════════════
def all_eight(st):
    """🔴 `out983_stat.json` 의 두 절을 **그대로 옮겨 세고**, `선다` 를 전량 센다."""
    k981 = [k for k in st if "§3-2 ㋐" in k][0]
    k983 = [k for k in st if "시간 방향 격자에 같은" in k][0]
    rows, stands = [], []
    for src, key in (("981 격자(㈎ 개체 묶음 유보)", k981),
                     ("983 격자(㈏ 시간 방향 유보)", k983)):
        per = st[key]["🔴 λ 별"]
        for uk in sorted(per):
            for pair, d in per[uk].items():
                p9 = d["🔴🔴🔴 983 판(예산 공변량)"]
                row = collections.OrderedDict([
                    ("격자", src), ("λ", uk),
                    ("짝", pair.replace("🔴", "").replace("🔴🔴", "").strip()),
                    ("⚠ 나이브 스피어만", d["⚠ 982 판(나이브) 스피어만"]),
                    ("⚠ 나이브 전수 순열 p", d["⚠ 982 판(나이브) 전수 순열 p"]),
                    ("🔴 부분상관(잔차 피어슨)", p9.get("🔴 부분상관(잔차 피어슨)")),
                    ("🔴 예산 공변량 전수 순열 p", p9.get("🔴 전수 순열 p(잔차 순열)")),
                    ("🔴 잔차 SD", p9.get("잔차 SD")),
                    ("🔴🔴 선다", p9.get("선다")),
                    ("🔴 983 이 게재했나", False),
                ])
                rows.append(row)
                if p9.get("선다"):
                    stands.append(row)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **983 이 낸 예산 공변량 검정 «전량 여덟»** --- 유리·불리를 안 고른다"),
        ("🔴 출처", ["runners/out983_stat.json:" + k981,
                  "runners/out983_stat.json:" + k983]),
        ("🔴 분모(검정 수)", len(rows)),
        ("🔴🔴 「선다」 판정 수", len(stands)),
        ("🔴🔴🔴 983 이 저장소 안 어디에도 안 실은 「선다」",
         [collections.OrderedDict([("λ", r["λ"]), ("짝", r["짝"]),
                                   ("부분상관", r["🔴 부분상관(잔차 피어슨)"]),
                                   ("p", r["🔴 예산 공변량 전수 순열 p"])])
          for r in stands]),
        ("🔴 전량", rows),
        ("🔴🔴 983 이 이 표를 안 실었다는 증거",
         "🔴 `0.971938`·`0.001587` 이 `docs/판정_983.md`·`docs/card_983.md`·"
         "`docs/handoff_983.md`·`runners/out983_table.json` 어디에도 **없다**"
         "(티처 #122 C2 의 grep 0). 원장에는 **티처가** 적었다"),
        ("통과", bool(len(rows) == 8)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **검정 여덟이 전량 실렸는가 하나뿐이다.** 「선다」가 몇이든 통과와 무관하다 --- "
         "게재 의무는 결과에 안 매인다(사전등록 §2-1)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §2 🔴🔴🔴 승격한 물음 — 누출의 지문인가, 구성상 결합인가
# ══════════════════════════════════════════════════════════════════════
def _arm_points(gr):
    """칸 × λ × 팔 → 정본 자 ρ 점추정."""
    cells = gr["🔴🔴 칸"]
    out = {}
    for uk in ("u=0", "u=3"):
        d = {}
        for arm in (A_CTL, A_ORA, A_PRE, A_PLA):
            d[arm] = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][arm][CANON]
                      for n in NB_GRID]
        out[uk] = d
    return out


def _arm_reps(rp):
    """칸 × λ × 팔 → 복제별 ρ (200 벌). 🔴 팔 셋은 Δ 로 저장돼 있어 대조를 더한다."""
    cells = rp["🔴 칸"]
    out = {}
    for uk in ("u=0", "u=3"):
        ctl = [cells["N_B=%d · %s" % (n, uk)][REPS_CTL][CANON] for n in NB_GRID]
        d = {A_CTL: ctl}
        for arm in (A_ORA, A_PRE, A_PLA):
            d[arm] = [[c + x for c, x in
                       zip(ctl[i], cells["N_B=%d · %s" % (NB_GRID[i], uk)][arm][CANON])]
                      for i in range(len(NB_GRID))]
        out[uk] = d
    return out


def _partial(a, b):
    """🔴 983 과 **같은 함수**(`stat983.partial_test`)로 잰다 --- 구판/신판을 나란히 세운다."""
    return S.partial_test(a, b, NB)


def promoted(gr, rp):
    pts, reps = _arm_points(gr), _arm_reps(rp)
    per = collections.OrderedDict()
    verdicts = {}
    for uk in ("u=0", "u=3"):
        P = pts[uk]
        head = [max(P[A_CTL]) - c for c in P[A_CTL]]
        head_pla = [max(P[A_PLA]) - c for c in P[A_PLA]]
        shift_ora = [P[A_ORA][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        shift_pre = [P[A_PRE][i] - P[A_PLA][i] for i in range(len(NB_GRID))]
        gain_pla = [P[A_PLA][i] - P[A_CTL][i] for i in range(len(NB_GRID))]

        def _one(a, b, na, nb):
            s_n, p_n, tot = S.perm_p(a, b)
            t = _partial(a, b)
            return collections.OrderedDict([
                ("🔴 계열 A", na), ("🔴 계열 B", nb),
                ("🔴 A 값", [_r(x) for x in a]), ("🔴 B 값", [_r(x) for x in b]),
                ("⚠ 나이브 스피어만", s_n), ("⚠ 나이브 전수 순열 p", p_n),
                ("⚠ 벌 수", tot),
                ("🔴 부분상관", t.get("🔴 부분상관(잔차 피어슨)")),
                ("🔴 전수 순열 p", t.get("🔴 전수 순열 p(잔차 순열)")),
                ("🔴🔴 선다", t["선다"]),
            ])

        t_ora = _one(shift_ora, head, "㉮−㉱ 목표 이동", "오라클 여유 = max(대조ρ) − 대조ρ")
        t_pre = _one(shift_pre, head, "🔴 ㉰−㉱ 목표 이동(미래를 «안» 본다)",
                     "오라클 여유 = max(대조ρ) − 대조ρ")
        t_ora_p = _one(shift_ora, head_pla, "㉮−㉱ 목표 이동",
                       "🔴 여유를 위약 팔로 = max(㉱ρ) − ㉱ρ")
        t_pre_p = _one(shift_pre, head_pla, "🔴 ㉰−㉱ 목표 이동",
                       "🔴 여유를 위약 팔로 = max(㉱ρ) − ㉱ρ")
        t_neg = _one(gain_pla, head, "㉱ − ㉯ 이득(음성 대조)",
                     "오라클 여유 = max(대조ρ) − 대조ρ")

        # ── 자 ③ 복제 붓스트랩 ──────────────────────────────────────
        R = reps[uk]
        n_rep = len(R[A_CTL][0])
        bo, bp, bd, hit = [], [], [], 0
        for r in range(n_rep):
            ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
            ora = [R[A_ORA][i][r] for i in range(len(NB_GRID))]
            pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
            pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
            h = [max(ctl) - c for c in ctl]
            so = [ora[i] - pla[i] for i in range(len(NB_GRID))]
            sp = [pre[i] - pla[i] for i in range(len(NB_GRID))]
            to, tp = _partial(so, h), _partial(sp, h)
            co = to.get("🔴 부분상관(잔차 피어슨)")
            cp = tp.get("🔴 부분상관(잔차 피어슨)")
            if co is None or cp is None:
                continue
            bo.append(co)
            bp.append(cp)
            bd.append(co - cp)
            po = to.get("🔴 전수 순열 p(잔차 순열)")
            hit += 1 if (po is not None and po < 0.05) else 0

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

        ci_o, ci_p, ci_d = _ci(bo), _ci(bp), _ci(bd)
        boot = collections.OrderedDict([
            ("🔴 무엇", "🔴 **자 ③** --- 200 복제로 부분상관의 분포를 낸다. "
                     "7 점 순열 p 는 표본이 7 이라 폭을 못 준다"),
            ("🔴 쓸 수 있는 복제(잔차가 0 이 아닌 벌)", len(bo)),
            ("🔴 (㉮−㉱, 여유) 부분상관", ci_o),
            ("🔴 (㉰−㉱, 여유) 부분상관", ci_p),
            ("🔴🔴 둘의 차(㉮ − ㉰)", ci_d),
            ("🔴 점추정(전 자료 한 벌)", t_ora["🔴 부분상관"]),
            ("🔴🔴 붓스트랩 평균 − 점추정",
             _r((ci_o.get("평균") or 0) - (t_ora["🔴 부분상관"] or 0))
             if ci_o.get("평균") is not None else None),
            ("🔴 복제 중 p<0.05 를 낸 비율",
             _r(float(hit) / len(bo), 4) if bo else None),
        ])

        # ── 판정 ────────────────────────────────────────────────────
        r1 = bool(t_ora["🔴🔴 선다"] and not t_pre["🔴🔴 선다"])
        r2 = bool(t_ora_p["🔴🔴 선다"] or t_pre_p["🔴🔴 선다"])
        both = bool(t_ora["🔴🔴 선다"] and t_pre["🔴🔴 선다"])
        if both and r2:
            verdict = ("🔴🔴🔴 **구성상 결합이다 --- 누출의 지문이 아니다.** "
                       "미래를 «안» 보는 `㉰` 팔이 «같은 만큼» 서고, 여유를 대조가 아닌 "
                       "위약 팔로 다시 정의해도 선다. 곧 이 부분상관은 「오라클이 미래를 "
                       "안다」를 안 가리킨다 --- **「층화 팔이 대조보다 얼마나 버는가」와 "
                       "「대조가 자기 최고 칸에서 얼마나 떨어져 있는가」가 같이 움직인다**는 "
                       "말이다")
        elif r1:
            verdict = ("🔴🔴🔴 **누출의 지문이다** --- `㉮` 판만 서고 미래를 안 보는 `㉰` 판은 "
                       "안 선다")
        elif not t_ora["🔴🔴 선다"]:
            verdict = ("🔴 **이 λ 에서는 원 검정 자체가 안 선다** --- 판정할 것이 없다"
                       "(조항 59: 「안 섰다」는 「반대가 참이다」가 아니다)")
        else:
            verdict = "🔴 **갈렸다** --- 자 ① 과 자 ② 가 서로 다른 쪽을 가리킨다"
        verdicts[uk] = verdict
        per[uk] = collections.OrderedDict([
            ("🔴🔴 자 ① 위약 팔 바꿔치기 — ㉮(미래를 본다)", t_ora),
            ("🔴🔴 자 ① 위약 팔 바꿔치기 — ㉰(미래를 «안» 본다)", t_pre),
            ("🔴 자 ② 여유 바꿔치기 — ㉮", t_ora_p),
            ("🔴 자 ② 여유 바꿔치기 — ㉰", t_pre_p),
            ("🔴 자 ④ 음성 대조 (㉱ 이득, 여유)", t_neg),
            ("🔴🔴 자 ③ 복제 붓스트랩", boot),
            ("🔴🔴 자 ① 이 누출 쪽인가(㉮ 만 선다)", r1),
            ("🔴🔴 자 ① 이 결합 쪽인가(둘 다 선다)", both),
            ("🔴🔴 자 ② 가 결합 쪽인가(대조를 빼도 선다)", r2),
            ("🔴🔴🔴 판정", verdict),
        ])
    return collections.OrderedDict([
        ("🔴 무엇",
         "🔴🔴🔴 **983 이 안 실은 「서는」 결과를 이 사이클의 물음으로 승격하고 "
         "자기 위약에 물린다** --- 누출의 지문인가, 구성상 결합인가"),
        ("🔴 정의", collections.OrderedDict([
            ("오라클 여유", "head[i] = max(대조ρ) − 대조ρ[i] — 🔴 **대조 팔만의 함수다**"),
            ("목표 이동", "shift[i] = ㉮ρ[i] − ㉱ρ[i]"),
            ("출처", "runners/stat983.py:400-457 의 문언 그대로"),
        ])),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 한 줄", " // ".join("%s: %s" % (k, v.split("---")[0].strip())
                                 for k, v in verdicts.items())),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **자 넷을 λ 둘에서 전부 돌렸고 판정 문언을 사전등록에서 그대로 읽었다.** "
         "🔴 「누출인가 결합인가」의 답은 `통과` 가 아니라 위 «판정» 칸이다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §7-1 🔴 `p 0.000397` 은 전수 순열의 **최소 달성값**이다
# ══════════════════════════════════════════════════════════════════════
def minimality():
    n = len(NB_GRID)
    perms = S.perms_of(n)
    x = np.asarray(S._rank(list(range(n))), float)
    y = x.copy()
    X = x[perms]
    X = X - X.mean(axis=1, keepdims=True)
    Y = y - y.mean()
    r = X.dot(Y) / np.sqrt((X * X).sum(axis=1) * float(np.dot(Y, Y)))
    best = float(np.max(np.abs(r)))
    cnt = int(np.sum(np.abs(r) >= best - 1e-12))
    ex = [tuple(int(i) for i in perms[j]) for j in np.where(np.abs(r) >= best - 1e-12)[0]]
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **`p 0.000397 = 2/5040` 은 「우연히 같은 값」이 아니라 "
                 "«전수 순열의 최소 달성값»이다**"),
        ("벌 수(7!)", int(len(perms))),
        ("🔴 달성 가능한 최대 |스피어만|", _r(best)),
        ("🔴 그 값을 내는 순열 수", cnt),
        ("🔴 그 순열들", ex),
        ("🔴🔴 최소 달성 p = 그 수 / 벌 수", _r(float(cnt) / len(perms))),
        ("🔴 982 가 낸 값", 0.000397),
        ("🔴🔴 같은가", bool(abs(float(cnt) / len(perms) - 0.000397) < 5e-7)),
        ("🔴🔴🔴 그래서",
         "🔴 **「완전 단조인 어떤 짝이든 반드시 이 값이 나온다」** --- 항등과 «역순» 둘뿐이다. "
         "🔴 이 사실을 적으면 983 의 논증이 훨씬 세진다(티처 #122 즉시정정 1). "
         "983 은 이걸 안 적었다"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "전수 5,040 벌을 실제로 세어 최소 달성값을 냈다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §7-2 🔴 「원리상 못 잰다」 정정 — 원값을 `log N_B` 에 회귀한다
# ══════════════════════════════════════════════════════════════════════
def _resid_raw(x, c):
    x = np.asarray(x, float)
    c = np.asarray(c, float)
    c0 = c - c.mean()
    b = float(np.dot(x - x.mean(), c0) / np.dot(c0, c0))
    return (x - x.mean()) - b * c0


def cant_measure_fix(st):
    k981 = [k for k in st if "§3-2 ㋐" in k][0]
    per = collections.OrderedDict()
    for uk in sorted(st[k981]["🔴 λ 별"]):
        d = st[k981]["🔴 λ 별"][uk]
        pk = [k for k in d if "검정 ②" in k][0]
        a = d[pk]["🔴 A 값"]
        b = d[pk]["🔴 B 값"]
        old = d[pk]["🔴🔴🔴 983 판(예산 공변량)"]
        ra, rb = _resid_raw(a, LOGNB), _resid_raw(b, LOGNB)
        s0, p, tot = S.perm_p(list(ra), list(rb), rank=False)
        per[uk] = collections.OrderedDict([
            ("🔴 짝", "(㉱ − ㉯ 이득, 대조 팔 혼합 표집 SD L1)"),
            ("⚠ 983 판(순위 잔차) 부분상관", old.get("🔴 부분상관(잔차 피어슨)")),
            ("⚠ 983 판 잔차 SD", old.get("잔차 SD")),
            ("⚠ 983 판이 적은 것", old.get("🔴🔴 왜 「모른다」인가")),
            ("🔴🔴 984 판(원값을 `log N_B` 에 회귀) 부분 피어슨", s0),
            ("🔴🔴 984 판 전수 순열 p", p),
            ("🔴 벌 수", tot),
            ("🔴 984 판 잔차 SD", [_r(float(np.std(ra)), 8), _r(float(np.std(rb)), 8)]),
            ("🔴🔴 선다", bool(p is not None and p < 0.05)),
        ])
    u3 = per.get("u=3", {})
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **「원리상 못 잰다」는 과장이다** --- 원값을 `log N_B` 에 회귀하면 "
                 "같은 5,040 벌이 **잘 정의된다**(티처 #122 즉시정정 2)"),
        ("🔴 왜 983 판은 「못 잰다」를 냈나",
         "🔴 983 은 **순위**를 `rank(N_B)` 에 회귀했다(`stat983._resid_on`). "
         "두 계열이 둘 다 `N_B` 의 단조 함수면 **순위 잔차가 정확히 0** 이 된다 --- "
         "그건 자료의 성질이 아니라 **자의 성질**이다"),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 그래서",
         "🔴 **983 의 실질 결론은 살아남고 오히려 강해진다** --- 잘 정의된 자로 다시 재도 "
         "`u=3` 에서 p `%s` 로 **안 선다.** 「못 잰다」가 아니라 **「재 봤는데 안 선다」**가 "
         "훨씬 센 문장이다" % u3.get("🔴🔴 984 판 전수 순열 p")),
        ("🔴 산문 정정",
         "🔴 983 판정문 산문이 「**한쪽** 계열의 잔차가 0」이라 했는데 `u=3` 검정 ② 에서는 "
         "**둘 다 0** 이다(산출물 `잔차 SD [0.0, 0.0]` 은 옳게 적었다 --- 산문만 틀렸다)"),
        ("🔴 `p 0.000397` 귀속 정정",
         "🔴 **982 의 «헤드라인»이 아니라 「982 §2-2 의 유일한 «선다» 판정」이다**"
         "(티처 #122 즉시정정 3)"),
        ("통과", bool(u3.get("🔴🔴 984 판 전수 순열 p") is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **잘 정의된 잔차로 p 가 «나왔는가»** 하나다. 그 p 가 서든 안 서든 통과다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §7-4 🔴 축 섞기를 **전수 120 벌**로 센다
# ══════════════════════════════════════════════════════════════════════
def axis_exhaustive(tg, st):
    mixd = tg["🔴 학습 혼합 진단"]
    rows_tr = [float(mixd[t]["🔴 도메인별 학습 행"][S.DOM_TOP]) for t in S.TGTS]
    align = tg["🔴🔴 목표–자 정렬도 (코사인)"]
    perms = list(itertools.permutations(range(len(S.TGTS))))
    k33 = [k for k in st if "§3-3" in k][0]
    per = collections.OrderedDict()
    for u in S.U_REG:
        uk = "u=%d" % u
        cell = tg["🔴🔴🔴 칸"][uk]["🔴🔴 목표별"]

        def wins(axis):
            w = 0
            for nm in S.RULERS:
                dl = [cell[t]["자 여섯 전부"][nm]["Δ"] for t in S.TGTS]
                al = [align[t][nm] for t in S.TGTS]
                s_al, s_x = S._spear(dl, al), S._spear(dl, axis)
                if s_x is not None and s_al is not None and abs(s_x) > abs(s_al):
                    w += 1
            return w

        truth = wins(rows_tr)
        null = [wins([rows_tr[i] for i in pm]) for pm in perms]
        ge = [i for i, v in enumerate(null) if v >= truth]
        rank_true = S._rank(rows_tr)
        rank_rev = S._rank([-x for x in rows_tr])
        which = []
        for i in ge:
            ax = [rows_tr[j] for j in perms[i]]
            r = S._rank(ax)
            if r == rank_true:
                which.append("항등(순위 그대로)")
            elif r == rank_rev:
                which.append("🔴 순위 역순")
            else:
                which.append("그 밖")
        pub = st[k33]["🔴 λ 별"][uk]["🔴🔴🔴 섞기 변이체"]
        per[uk] = collections.OrderedDict([
            ("🔴 참 축이 이긴 자 수(엄격 `>`)", truth),
            ("🔴 전수 벌 수(5!)", len(perms)),
            ("🔴 참 축만큼 이긴 순열 수", len(ge)),
            ("🔴🔴 정확 p = 그 수 / 120", _r(float(len(ge)) / len(perms))),
            ("⚠ 983 이 게재한 경험 p(2,000 벌 뽑기)",
             pub["🔴🔴 섞은 축이 참 축만큼 이긴 비율(경험 p)"]),
            ("⚠ 983 이 게재한 섞은 축 평균", pub["🔴 섞은 축이 이긴 자 수 — 평균"]),
            ("🔴 전수 평균", _r(float(sum(null)) / len(null), 4)),
            ("🔴🔴 통과하는 순열의 정체", which),
            ("🔴🔴🔴 정확 p < 0.05 인가", bool(float(len(ge)) / len(perms) < 0.05)),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **축 섞기를 전수 5! = 120 벌로 센다**(983 은 2,000 벌 뽑기)"),
        ("🔴 축의 값(목표별)", collections.OrderedDict(
            [(t, mixd[t]["🔴 도메인별 학습 행"][S.DOM_TOP]) for t in S.TGTS])),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 그래서",
         "🔴 **983 의 `p 0.0145` 는 정확히 `2/120 = 0.016667` 이고 통과하는 두 순열은 "
         "«항등 + 순위 역순»이다** --- 곧 983 이 982 에서 규탄한 `2/5040` 과 **구조가 같다.** "
         "🔴 **983 은 자기 무효성 시연을 자기 검정에 안 물렸다**(티처 #122 3순위 ⓕ). "
         "🔴 그리고 원장에 `u=3` 만 적고 `p 0.983333` 인 `u=0` 을 뺐다 --- 여기 둘 다 싣는다"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "전수 120 벌을 실제로 세어 정확 p 를 λ 둘 다 냈다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = CY.code_stamp()
    st = _load("out983_stat.json")
    gr = _load("out983_grid.json")
    rp = _load("out983_reps.json")
    tg = _load("out981_target.json")

    out = collections.OrderedDict()
    out["무엇"] = ("984 §1·§2·§7 — 🔴🔴🔴 **미게재 결과를 전량 게재하고, 그 결과를 "
                 "자기 위약에 물린다**")
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["사전등록"] = "docs/prereg_984_leak_or_coupling.md §2 · §7"
    out["🔴 티처"] = ("🔴 티처 #122 C2 — 「983 이 자기 격자에 자기 추정기를 물려 넷을 냈는데 "
                    "「서는」 하나를 어디에도 안 실었다. 그것도 누출 서사를 받치는 방향이다」")
    out["🔴 새 학습"] = 0
    out["§1 🔴🔴 예산 공변량 검정 전량 여덟"] = all_eight(st)
    out["§2 🔴🔴🔴 승격 물음 — 누출의 지문인가 구성상 결합인가"] = promoted(gr, rp)
    out["§7-1 🔴 `p 0.000397` 은 전수 순열의 최소 달성값이다"] = minimality()
    out["§7-2 🔴 「원리상 못 잰다」 정정 — 원값을 `log N_B` 에 회귀"] = cant_measure_fix(st)
    out["§7-4 🔴 축 섞기 전수 120 벌"] = axis_exhaustive(tg, st)
    out["통과"] = bool(all(out[k]["통과"] for k in out if k.startswith("§")))
    out["🔴 이 산출물의 `통과`"] = ("🔴 **절 다섯이 전부 값을 냈는가**다. "
                            "「누출인가」의 답은 §2 의 «판정» 칸이다")
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["leak"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage(a.ref)
    print(json.dumps({
        "통과": r["통과"],
        "검정 여덟 중 선다": r["§1 🔴🔴 예산 공변량 검정 전량 여덟"]["🔴🔴 「선다」 판정 수"],
        "판정": r["§2 🔴🔴🔴 승격 물음 — 누출의 지문인가 구성상 결합인가"]["🔴🔴🔴 한 줄"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
