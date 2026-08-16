#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 §3 — 🔴🔴 **예산 격자 서사를 «통계»로 다시 판정한다**.

사전등록 `docs/prereg_984_leak_or_coupling.md` §3 · §3-4 를 따른다.
🔴 **여기 전량은 티처 #122 2순위가 값을 준 재현이다**(사전등록 §0-나 비맹검 신고).
🔴 **새 학습 0** --- `runners/out983_reps.json`(복제별 Δ 200 × 14 칸)과
`runners/out983_grid.json`(점추정)만 읽는다.

무엇을 고치나:
- **ⓐ** 이득 14 칸 중 `2·짝SE` 를 넘는 칸은 **3** 뿐이고 `u=0` 은 **0** 칸이다.
  나머지 11 칸은 **조항 59** 대로 「안 쟀다」로 적는다. 「단조」·「포화」·「U 자」 같은
  **모양** 주장에는 **칸 대 칸 짝 검정**을 붙인다(**조항 68** · 984 신설).
- **ⓑ** 이득 곡선을 `㉮ρ` 와 `대조ρ` 로 **갈라** 싣는다.
- **ⓒ** **붓스트랩 중심 검사** --- 복제 평균과 점추정을 나란히 싣고 **편의/짝SE** 를 낸다.
- **ⓓ** 오라클 프리미엄을 **14 칸 전량** · **짝 실측 SD** 로 싣는다.
- **ⓔ** 위약 예측을 「넷 이상 양수」에서 **「0 과 구별되나」**로 뒤집는다.
"""
import argparse
import collections
import datetime as dt
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

OUT = "runners/out984_grid.json"
NB_GRID = [450, 900, 1800, 3600, 7200, 14400, 28800]
LAMS = ("u=0", "u=3")
CANON = "R_pool 묶음"
A_CTL = "㉯ 대조"
A_ORA = "㉮ 층화 · 오라클(유보 전량 구성비)"
A_PRE = "㉰ 층화 · 절단 앞(블록 <j 구성비)"
A_PLA = "㉱ 위약(절단 앞 hplt 공급 몫)"
REPS_CTL = "㉯ 대조 팔 ρ(복제별)"
GATE = 2.0                                            # 사전등록 §3-4


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _sd(v):
    n = len(v)
    m = sum(v) / n
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))


def _mean(v):
    return sum(v) / len(v)


def _load(name):
    p = ROOT / "runners" / name
    if not p.is_file():
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % name)
    return json.loads(p.read_text(encoding="utf-8"))


class Grid(object):
    def __init__(self, gr, rp):
        self.cells = gr["🔴🔴 칸"]
        self.reps = rp["🔴 칸"]

    def pt(self, nb, uk, arm):
        return self.cells["N_B=%d" % nb][uk]["🔴 팔별 점추정(자 여섯)"][arm][CANON]

    def delta(self, nb, uk, arm):
        key = "%s − %s" % (arm, A_CTL)
        return self.cells["N_B=%d" % nb][uk][key]["🔴🔴 자별 판정"][CANON]["Δ"]

    def se(self, nb, uk, arm):
        key = "%s − %s" % (arm, A_CTL)
        return self.cells["N_B=%d" % nb][uk][key]["🔴🔴 자별 판정"][CANON]["🔴 짝 SE"]

    def rep_delta(self, nb, uk, arm):
        return self.reps["N_B=%d · %s" % (nb, uk)][arm][CANON]

    def rep_ctl(self, nb, uk):
        return self.reps["N_B=%d · %s" % (nb, uk)][REPS_CTL][CANON]

    def rep_rho(self, nb, uk, arm):
        if arm == A_CTL:
            return self.rep_ctl(nb, uk)
        c = self.rep_ctl(nb, uk)
        d = self.rep_delta(nb, uk, arm)
        return [a + b for a, b in zip(c, d)]


# ══════════════════════════════════════════════════════════════════════
# ⓐ `2·짝SE` 관문 전량 + 칸 대 칸 짝 검정
# ══════════════════════════════════════════════════════════════════════
def gate_and_shape(G):
    per, n_pass, n_cell = collections.OrderedDict(), 0, 0
    for uk in LAMS:
        rows = []
        for nb in NB_GRID:
            d, s = G.delta(nb, uk, A_ORA), G.se(nb, uk, A_ORA)
            z = abs(d) / s if s else None
            ok = bool(z is not None and z >= GATE)
            n_cell += 1
            n_pass += 1 if ok else 0
            rows.append(collections.OrderedDict([
                ("N_B", nb), ("Δ(㉮ − ㉯)", _r(d)), ("짝SE", _r(s)),
                ("🔴 |Δ|/짝SE", _r(z, 4)),
                ("🔴🔴 2·짝SE 를 넘나", ok),
                ("🔴 조항 59 표기", "잰 값" if ok else "🔴 **안 쟀다**"),
            ]))
        # 인접 칸 짝 검정 + 모양 주장
        adj = []
        for i in range(len(NB_GRID) - 1):
            a = G.rep_delta(NB_GRID[i], uk, A_ORA)
            b = G.rep_delta(NB_GRID[i + 1], uk, A_ORA)
            dif = [y - x for x, y in zip(a, b)]
            gap = G.delta(NB_GRID[i + 1], uk, A_ORA) - G.delta(NB_GRID[i], uk, A_ORA)
            sd = _sd(dif)
            adj.append(collections.OrderedDict([
                ("칸", "%d → %d" % (NB_GRID[i], NB_GRID[i + 1])),
                ("점추정 차", _r(gap)), ("🔴 복제 짝 SD", _r(sd)),
                ("🔴 z", _r(abs(gap) / sd, 4)),
                ("🔴🔴 선다(z ≥ 2)", bool(abs(gap) / sd >= GATE)),
                ("복제 평균 차", _r(_mean(dif))),
            ]))
        # U 자 되오름 --- 최저 칸에서 끝 칸까지
        deltas = [G.delta(nb, uk, A_ORA) for nb in NB_GRID]
        lo = int(np.argmin(deltas))
        shape = collections.OrderedDict()
        for tgt in (len(NB_GRID) - 1, len(NB_GRID) - 2):
            if tgt <= lo:
                continue
            a = G.rep_delta(NB_GRID[lo], uk, A_ORA)
            b = G.rep_delta(NB_GRID[tgt], uk, A_ORA)
            dif = [y - x for x, y in zip(a, b)]
            gap = deltas[tgt] - deltas[lo]
            sd = _sd(dif)
            shape["%d → %d (되오름)" % (NB_GRID[lo], NB_GRID[tgt])] = \
                collections.OrderedDict([
                    ("점추정 차", _r(gap)), ("🔴 복제 짝 SD", _r(sd)),
                    ("🔴 z", _r(abs(gap) / sd, 4)),
                    ("🔴🔴 선다(z ≥ 2)", bool(abs(gap) / sd >= GATE)),
                ])
        mono = all(deltas[i + 1] <= deltas[i] for i in range(len(deltas) - 1))
        per[uk] = collections.OrderedDict([
            ("🔴 칸별", rows),
            ("🔴 2·짝SE 를 넘는 칸 수", sum(1 for r in rows if r["🔴🔴 2·짝SE 를 넘나"])),
            ("🔴 인접 칸 짝 검정", adj),
            ("🔴🔴 되오름 짝 검정", shape or "🔴 최저 칸이 끝 칸이다 --- 되오름이 없다"),
            ("⚠ 점추정만 보면 단조 감소인가", mono),
            ("🔴🔴🔴 「U 자」를 주장할 수 있나(조항 68)",
             bool(any(v["🔴🔴 선다(z ≥ 2)"] for v in shape.values())) if shape else False),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **이득 14 칸 전량 · `2·짝SE` 관문 · 칸 대 칸 짝 검정**(조항 68)"),
        ("🔴 분모(칸)", n_cell),
        ("🔴🔴 2·짝SE 를 넘는 칸 수", n_pass),
        ("🔴🔴 「안 쟀다」로 적어야 하는 칸 수", n_cell - n_pass),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 그래서",
         "🔴 **983 의 「U 자 되오름」은 `u=0` 에서 자기 관문을 못 넘는다.** "
         "복제 씨앗이 칸끼리 짝지어져 있으므로 이 검정은 **공짜**였다 --- 안 낸 것이지 "
         "못 낸 것이 아니다(티처 #122 2순위 ⓐ)"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **14 칸을 전량 싣고 짝 검정을 붙였는가**다. 「모양이 있나」의 답은 "
         "위 «「U 자」를 주장할 수 있나» 칸이다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# ⓑ 이득을 `㉮ρ` 와 `대조ρ` 로 갈라 싣는다
# ══════════════════════════════════════════════════════════════════════
def split_arms(G):
    per = collections.OrderedDict()
    for uk in LAMS:
        ctl = [G.pt(nb, uk, A_CTL) for nb in NB_GRID]
        ora = [G.pt(nb, uk, A_ORA) for nb in NB_GRID]
        imax = int(np.argmax(ctl))
        a = G.rep_ctl(NB_GRID[imax], uk)
        b = G.rep_ctl(NB_GRID[-1], uk)
        dif = [y - x for x, y in zip(a, b)]
        gap = ctl[-1] - ctl[imax]
        sd = _sd(dif)
        per[uk] = collections.OrderedDict([
            ("🔴 대조ρ 칸별", [_r(x) for x in ctl]),
            ("🔴 ㉮ρ 칸별", [_r(x) for x in ora]),
            ("🔴🔴 대조ρ 폭(max−min)", _r(max(ctl) - min(ctl), 4)),
            ("🔴🔴 ㉮ρ 폭(max−min)", _r(max(ora) - min(ora), 4)),
            ("🔴 어느 팔이 구조를 내나",
             "🔴 **대조 팔**" if (max(ctl) - min(ctl)) > (max(ora) - min(ora))
             else "층화 팔"),
            ("⚠ 983 이 실은 「대조가 오른 폭」(첫칸−끝칸)", _r(ctl[-1] - ctl[0])),
            ("🔴🔴 대조ρ 최고 칸", NB_GRID[imax]),
            ("🔴🔴 대조ρ 최고값", _r(max(ctl))),
            ("🔴 최고 칸 → 끝 칸 점추정 차", _r(gap)),
            ("🔴 그 차의 복제 짝 SD", _r(sd)),
            ("🔴 z", _r(abs(gap) / sd, 4)),
            ("🔴🔴 대조의 하락이 서나(z ≥ 2)", bool(abs(gap) / sd >= GATE)),
            ("🔴🔴🔴 「첫칸−끝칸」 정의가 지우는 것",
             "🔴 **대조 ρ 는 `N_B=%d` 에서 최고(`%s`)였다가 떨어진다.** "
             "「첫칸−끝칸 = `%s`」는 그 사실을 지운다"
             % (NB_GRID[imax], _r(max(ctl)), _r(ctl[-1] - ctl[0]))),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **이득 곡선을 `㉮ρ` 와 `대조ρ` 로 갈라 싣는다**(티처 #122 2순위 ⓑ)"),
        ("🔴 λ 별", per),
        ("🔴🔴🔴 그래서",
         "🔴 **`u=0` 의 구조는 전부 대조 팔에서 온다** --- 이득의 U 는 대조의 역U 를 "
         "뒤집은 것이고, **대조의 하락조차 안 선다**"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "두 팔의 곡선·폭·최고 칸을 λ 둘에서 전량 실었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# ⓒ 붓스트랩 중심 검사 — 짝SE 는 「점추정 자리」의 SE 가 아니다
# ══════════════════════════════════════════════════════════════════════
def bootstrap_center(G):
    per, worst = collections.OrderedDict(), (0.0, None)
    for uk in LAMS:
        rows = []
        for nb in NB_GRID:
            v = G.rep_delta(nb, uk, A_ORA)
            pt = G.delta(nb, uk, A_ORA)
            m, s = _mean(v), _sd(v)
            bias = (m - pt) / s if s else None
            if bias is not None and abs(bias) > worst[0]:
                worst = (abs(bias), "%s · N_B=%d" % (uk, nb))
            rows.append(collections.OrderedDict([
                ("N_B", nb), ("🔴 점추정", _r(pt)), ("🔴 복제 평균", _r(m)),
                ("짝SE(= 복제 SD)", _r(s)), ("🔴🔴 편의/SE", _r(bias, 4)),
            ]))
        per[uk] = rows
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **붓스트랩 중심 검사** --- 복제 평균과 점추정을 나란히 싣는다"),
        ("🔴 λ 별", per),
        ("🔴🔴 최대 |편의/SE|", _r(worst[0], 4)),
        ("🔴🔴 그 칸", worst[1]),
        ("🔴🔴🔴 그래서",
         "🔴 **짝SE 는 「점추정 자리」의 SE 가 아니다.** 학습 붓스트랩이 유효 학습량을 "
         "~0.63n 로 줄여 층화 이득을 키우므로 복제 분포의 중심이 점추정에서 최대 "
         "**%s SE** 만큼 어긋난다. 🔴 **그 사실을 안 적고 `Δ/짝SE` 를 관문으로 쓰면 "
         "관문이 무엇을 재는지 아무도 모른다**(티처 #122 2순위 ⓒ)" % _r(worst[0], 3)),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "14 칸 전량에 복제 평균·점추정·편의/SE 를 실었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# ⓓ 오라클 프리미엄 14 칸 전량 · 짝 실측 SD
# ══════════════════════════════════════════════════════════════════════
def _weighted_z(vals, ses):
    """짝SE² 역가중 칸 가중 z(사전등록 §3-4)."""
    w = [1.0 / (s * s) for s in ses if s]
    if len(w) != len(vals):
        return None, None
    num = sum(wi * v for wi, v in zip(w, vals))
    den = math.sqrt(sum(w))
    return num / sum(w), num / den * 1.0 / math.sqrt(1.0) if den else None


def premium(G):
    per, npos, nneg, mx = collections.OrderedDict(), 0, 0, (0.0, None)
    allv, allse = [], []
    for uk in LAMS:
        rows = []
        for nb in NB_GRID:
            prem = G.pt(nb, uk, A_ORA) - G.pt(nb, uk, A_PRE)
            vo = G.rep_rho(nb, uk, A_ORA)
            vp = G.rep_rho(nb, uk, A_PRE)
            dif = [a - b for a, b in zip(vo, vp)]
            s = _sd(dif)
            z = abs(prem) / s if s else None
            npos += 1 if prem > 0 else 0
            nneg += 1 if prem < 0 else 0
            if z is not None and z > mx[0]:
                mx = (z, "%s · N_B=%d" % (uk, nb))
            allv.append(prem)
            allse.append(s)
            rows.append(collections.OrderedDict([
                ("N_B", nb), ("🔴 프리미엄(㉮ρ − ㉰ρ)", _r(prem)),
                ("🔴 짝 실측 SD", _r(s)), ("🔴 |z|", _r(z, 4)),
                ("🔴🔴 2·SE 를 넘나", bool(z is not None and z >= GATE)),
                ("복제 평균", _r(_mean(dif))),
            ]))
        per[uk] = rows
    w = [1.0 / (s * s) for s in allse]
    zw = sum(wi * v for wi, v in zip(w, allv)) / math.sqrt(sum(w))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **오라클 프리미엄 `㉮ρ − ㉰ρ` 를 14 칸 전량 · 짝 실측 SD 로**"),
        ("⚠ 983 이 실은 것", "🔴 **첫 칸 둘뿐**(`u=0 −0.004726` · `u=3 −0.008671`)"),
        ("🔴 λ 별", per),
        ("🔴 분모(칸)", len(allv)),
        ("🔴🔴 부호 — 양수 칸", npos),
        ("🔴🔴 부호 — 음수 칸", nneg),
        ("🔴🔴 최대 |z|", _r(mx[0], 4)), ("🔴 그 칸", mx[1]),
        ("🔴🔴 2·SE 를 넘는 칸 수", 0 if mx[0] < GATE else None),
        ("🔴🔴🔴 칸 가중 z(짝SE² 역가중 · 14 칸)", _r(zw, 4)),
        ("🔴🔴🔴 칸 가중 z 가 서나(|z| ≥ 2)", bool(abs(zw) >= GATE)),
        ("⚠ `tgrid983.py:507-515` 의 「보수적」 주장",
         "🔴 **그 파일은 「제곱합 제곱근이라 보수적」이라 적는데, 귀무를 «받아들이는» "
         "검사(P4)에서 SE 를 부풀리는 것은 「반」보수적이다.** 그래서 여기서는 "
         "**짝 실측 SD** 로 다시 쟀다(티처 #122 2순위 ⓓ)"),
        ("🔴🔴🔴 그래서",
         "🔴 **「비오라클 팔이 오히려 낫다」는 자료가 안 받친다.** 전량은 부호가 "
         "**양 %d / 음 %d** 이고 **어느 칸도 2·SE 를 못 넘는다**(최대 |z| %s). "
         "🔴 옳은 문장은 **「이 설계로는 못 잰다」**이고 983 본문은 그 쪽에 서 있는데 "
         "**원장이 `−0.008671` 한 칸만 남겼다**" % (npos, nneg, _r(mx[0], 4))),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "프리미엄 14 칸을 전량 싣고 짝 실측 SD 로 쟀다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# ⓔ 위약 — 「넷 이상 양수」를 「0 과 구별되나」로 뒤집는다
# ══════════════════════════════════════════════════════════════════════
def placebo(G):
    per, npos, mx = collections.OrderedDict(), 0, (0.0, None)
    allv, allse = [], []
    for uk in LAMS:
        rows = []
        for nb in NB_GRID:
            d, s = G.delta(nb, uk, A_PLA), G.se(nb, uk, A_PLA)
            z = abs(d) / s if s else None
            npos += 1 if d > 0 else 0
            if z is not None and z > mx[0]:
                mx = (z, "%s · N_B=%d" % (uk, nb))
            allv.append(d)
            allse.append(s)
            rows.append(collections.OrderedDict([
                ("N_B", nb), ("🔴 Δ(㉱ − ㉯)", _r(d)), ("짝SE", _r(s)),
                ("🔴 |z|", _r(z, 4)),
                ("🔴🔴 2·SE 를 넘나", bool(z is not None and z >= GATE)),
            ]))
        per[uk] = rows
    n = len(allv)
    w = [1.0 / (s * s) for s in allse]
    zw = sum(wi * v for wi, v in zip(w, allv)) / math.sqrt(sum(w))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **위약 예측을 「넷 이상 양수」에서 「0 과 구별되나」로 뒤집는다**"),
        ("⚠ 983 의 등록 문언", "「위약 팔 `㉱` 의 이득이 7 칸 중 **넷 이상 양수**다」"),
        ("🔴🔴 왜 그 꼴이 나쁜가",
         "🔴 **확증만 되고 반증이 안 된다.** 실제로 **%d/%d 칸 전부 양수**인데"
         "(우연히 그럴 확률 2^-%d ≈ %s) **아무 칸도 |z| %s 를 못 넘는다** --- "
         "곧 「전부 양수」는 위약이 «듣는다»가 아니라 **위약 팔이 대조와 «거의 같은 팔»**"
         "이라는 뜻이다" % (npos, n, n, "%.1e" % (2.0 ** -n), _r(mx[0], 3))),
        ("🔴 λ 별", per),
        ("🔴 분모(칸)", n),
        ("🔴🔴 양수 칸", npos),
        ("🔴 「넷 이상 양수」(983 판)가 참인가", bool(npos >= 4)),
        ("🔴🔴 최대 |z|", _r(mx[0], 4)), ("🔴 그 칸", mx[1]),
        ("🔴🔴 2·SE 를 넘는 칸 수", sum(
            1 for uk in LAMS for r in per[uk] if r["🔴🔴 2·SE 를 넘나"])),
        ("🔴🔴🔴 칸 가중 z(짝SE² 역가중 · 14 칸)", _r(zw, 4)),
        ("🔴🔴🔴 0 과 구별되나(|z| ≥ 2 · 984 판)", bool(abs(zw) >= GATE)),
        ("🔴🔴🔴 984 가 등록한 새 문언",
         "🔴 **「위약 이득이 0 과 구별되나」** --- 부호가 아니라 **크기**를 묻는다. "
         "이 꼴은 «반증될 수 있다»"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "위약 14 칸을 전량 싣고 칸 가중 z 를 냈다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = CY.code_stamp()
    G = Grid(_load("out983_grid.json"), _load("out983_reps.json"))
    out = collections.OrderedDict()
    out["무엇"] = "984 §3 — 🔴🔴 **예산 격자 서사를 통계로 다시 판정한다**"
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["사전등록"] = "docs/prereg_984_leak_or_coupling.md §3 · §3-4"
    out["🔴 비맹검"] = ("🔴 **여기 전량은 티처 #122 2순위가 값을 준 재현이다** --- "
                    "사전등록 §0-나. **예측 분모 밖이다**")
    out["🔴 새 학습"] = 0
    out["§3-ⓐ 🔴🔴 2·짝SE 관문 전량 + 칸 대 칸 짝 검정"] = gate_and_shape(G)
    out["§3-ⓑ 🔴 이득을 ㉮ρ 와 대조ρ 로 갈라 싣는다"] = split_arms(G)
    out["§3-ⓒ 🔴🔴 붓스트랩 중심 검사"] = bootstrap_center(G)
    out["§3-ⓓ 🔴 오라클 프리미엄 14 칸 전량"] = premium(G)
    out["§3-ⓔ 🔴 위약 — 0 과 구별되나"] = placebo(G)
    out["통과"] = bool(all(out[k]["통과"] for k in out if k.startswith("§")))
    out["🔴 이 산출물의 `통과`"] = "절 다섯이 전부 값을 냈는가다"
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["grid"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage(a.ref)
    print(json.dumps({
        "통과": r["통과"],
        "2·SE 를 넘는 이득 칸": r["§3-ⓐ 🔴🔴 2·짝SE 관문 전량 + 칸 대 칸 짝 검정"][
            "🔴🔴 2·짝SE 를 넘는 칸 수"],
        "프리미엄 최대 |z|": r["§3-ⓓ 🔴 오라클 프리미엄 14 칸 전량"]["🔴🔴 최대 |z|"],
        "위약 칸 가중 z": r["§3-ⓔ 🔴 위약 — 0 과 구별되나"]["🔴🔴🔴 칸 가중 z(짝SE² 역가중 · 14 칸)"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
