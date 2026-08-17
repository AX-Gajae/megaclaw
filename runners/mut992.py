#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 §B-가 — 🔴🔴🔴 **990 의 배선 일곱을 «돌려서» 잰다**.

🔴 **왜 별도 러너인가.** 991 의 `audit991.b_variants` 는 「AST 로 소스를 뗀다」고 «주석에만»
적어 놓고 **AST 파싱이 하나도 없었고**, `src` 는 «읽고 버려진 죽은 변수»였으며,
`mut_ws[`·`dict(ws)` 같은 «소스 토큰용 정규식»을 «산문 문자열(`왜`)»에 물렸다 ---
그래서 「결과딕트」 갈래는 **원리상 한 번도 못 켜졌다**.

🔴🔴 **그 자리에 「손 라벨」도 「산문 정규식」도 아닌 «실행»을 넣는다.**
990 의 일곱 변이체를 **990 자신의 설정 격자**(같은 씨앗·같은 겹·같은 눈금)에서 다시 돌려
「어떤 설정에서도 떨어지나」를 «센다».

씀:
    python3 runners/mut992.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runners.alpha977 as A                       # noqa: E402
import runners.world992 as W                       # noqa: E402

OUT = ROOT / "runners"
RAN = ("runners/mut992.py", "runners/world992.py", "runners/alpha977.py")

SEEDS = W.SEEDS
KFOLD = W.KFOLD
ALPHA_H = W.ALPHA_H
U_REG = W.U_REG
KGRID = W.KGRID


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp():
    return collections.OrderedDict(
        (r, hashlib.sha256((ROOT / r).read_bytes()).hexdigest())
        for r in RAN if (ROOT / r).is_file())


def _kind(mres):
    if not mres:
        return "🔴 못 쟀다(설정 격자가 비었다)"
    if all(mres):
        return "㉠ 구성상 참"
    if not any(mres):
        return "㉡ 구성상 거짓"
    return "㉢ 검정력 있음"


# ══ 990 의 plan 들 (world990.py 와 «같은 식» --- 소스에서 옮긴 것이 아니라 재현) ══
def plan_mix_H(n):
    def f(j, av):
        nh = int(round(ALPHA_H * n))
        return min(n - nh, av), nh
    return f


def plan_mix_B(n):
    def f(j, av):
        return min(n, av), 0
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    cs0 = code_stamp()

    pool = A.Pool()
    wmaps, _champ = W.build_wmaps(pool)
    RN = list(wmaps)
    rows = collections.OrderedDict()
    hits = 0

    def put(name, base, mut, grid, why, cause):
        nonlocal hits
        hits += len(base) + len(mut)
        rows[name] = collections.OrderedDict([
            ("🔴 990 자신의 설정 격자", grid),
            ("🔴 설정 수", len(mut)),
            ("🔴 본 검사가 통과한 설정 수", int(sum(bool(x) for x in base))),
            ("🔴 변이체가 통과한 설정 수", int(sum(bool(x) for x in mut))),
            ("🔴🔴🔴 갈래(실측)", _kind([bool(x) for x in mut])),
            ("🔴 변이체가 «왜» 그렇게 되나", why),
            ("🔴🔴 그 까닭의 «갈래»", cause),
        ])

    # ── W1 팔 H 의 뽑기가 `alpha977.select` 와 색인까지 같다 ─────────────
    b, m = [], []
    for s in SEEDS[:3]:
        pool.reseed(s)
        for j in range(KFOLD):
            b0, h0, _z = A.select(pool, j, ALPHA_H)
            nb, nh = plan_mix_H(1800)(j, W.avail_b(pool, j))
            b1, h1, _s1, _s2 = W.pick(pool, j, nb, nh)
            nb2, nh2 = plan_mix_H(1801)(j, W.avail_b(pool, j))
            b2, h2, _s3, _s4 = W.pick(pool, j, nb2, nh2)
            b.append(np.array_equal(b0, b1) and np.array_equal(h0, h1))
            m.append(np.array_equal(b0, b2) and np.array_equal(h0, h2))
    put("W1 팔 H 의 뽑기가 `alpha977.select`(N_B=1800)와 «색인까지» 같다", b, m,
        "씨앗 3 × 겹 5(990 이 실제로 돈 격자)",
        "🔴 변이체 = 예산 1801. `round(0.95×1801) = 1711` 이라 hplt 배열 «길이»가 1710 과 "
        "달라 `np.array_equal` 이 «언제나» 거짓이다",
        "🔴 배열 «길이»가 달라 비교 자체가 불가 --- 자료와 무관")

    # ── W2 팔 B 는 «안 채운다» ────────────────────────────────────────
    b, m, avs = [], [], []
    for s in SEEDS:
        pool.reseed(s)
        for j in range(KFOLD):
            av = W.avail_b(pool, j)
            avs.append(av)
            b_hi, h_hi, s1, _s2 = W.pick(pool, j, 25600, 0)
            b.append(len(h_hi) == 0 and len(b_hi) == av and s1 == 25600 - av)
            _bm, hm, sm, _s = W.pick_filling(pool, j, 25600, 0)
            m.append(len(hm) == 0)
    put("W2 팔 B 는 «각 겹의 자기 천장»에서 멈춘다(HPLT 로 «안» 채운다)", b, m,
        "씨앗 12 × 겹 5(990 이 실제로 돈 격자)",
        "🔴 변이체 = 채우는 뽑기. base 자리가 `25600` 하나로 «박혀» 있고 겹 천장의 최대가 "
        "%d 라 `sm = 25600 − av > 0` 이 «언제나» 참이다" % max(avs),
        "🔴 손으로 박은 상수 `25600` 이 자료 천장(%d)보다 «한 자릿수 크다» --- 어떤 씨앗·겹에서도 안 뒤집힌다"
        % max(avs))

    # ── W3 유보 미접촉 ────────────────────────────────────────────────
    b, m, fold_sizes = [], [], []
    for s in SEEDS[:3]:
        pool.reseed(s)
        for j in range(KFOLD):
            bb, _h, _s1, _s2 = W.pick(pool, j, 37531, 35641)
            b.append(int((pool.fi[bb] == j).sum()) == 0)
            bm = pool.perm_b[:37531]
            n_hit = int((pool.fi[bm] == j).sum())
            fold_sizes.append(n_hit)
            m.append(n_hit == 0)
    put("W3 어떤 예산에서도 학습이 «그 겹의 유보 행»을 안 쓴다", b, m,
        "씨앗 3 × 겹 5(990 이 실제로 돈 격자)",
        "🔴 변이체 = 겹을 «안 거른» 뽑기. `perm_b[:37531]` 은 base 전량(%d 행)이라 "
        "겹 j 의 유보 행 %d~%d 개를 «언제나» 밟는다"
        % (len(pool.yb), min(fold_sizes), max(fold_sizes)),
        "🔴🔴 **여기가 티처 #130 의 「여섯」과 992 의 실측이 갈리는 «하나»다** --- "
        "떨어지는 까닭이 「센 수(겹 크기)가 0 이 아니다」라 «측정치»에 걸려 있다. "
        "그러나 5 겹 분할에서 겹이 비는 일은 «구성상» 없으므로 992 의 실측 자는 이것도 "
        "「어떤 설정에서도 떨어진다」로 «센다**. 두 수를 «둘 다» 싣는다")

    # ── W4 977 재현 ───────────────────────────────────────────────────
    b, m, vals = [], [], []
    for seed in A.SEEDS:
        pool.reseed(seed)
        r = A.oof(pool, 0.95, 10.0 ** U_REG, KGRID)
        p_, _e, _pr = A.score(pool, r["예측"])
        vals.append(float(p_))
        b.append(abs(float(p_) - 0.3596) <= 5e-4)
        m.append(abs(float(p_) - 0.4596) <= 5e-4)
    put("W4 977 의 `u=0|α=0.95` 묶음 ρ 를 다시 내면 공표값과 같다", b, m,
        "씨앗 %d(990 이 실제로 돈 격자 --- `A.SEEDS`)" % len(A.SEEDS),
        "🔴 변이체 = «공표값 + 0.1». 허용오차가 `5e-4` 라 `0.1` 만큼 옮긴 값은 "
        "«어떤 자료에서도** 안 든다",
        "🔴 «판정식»을 손으로 옮긴 변이체 --- 산술이 결과를 강제한다(`조항 66-가` 의 ❌ 예시)")

    # ── W5 자료 지문 ──────────────────────────────────────────────────
    ws = W.world_stamp()
    mut_ws = dict(ws)
    mut_ws["🔴 없는 경로"] = {"바이트": 0}
    b = [len(ws) == 3 and all(v["바이트"] > 0 for v in ws.values())]
    m = [len(mut_ws) == 3 and all(v["바이트"] > 0 for v in mut_ws.values())]
    put("W5 세 세계 자료 파일이 «전부» 열렸고 지문이 났다", b, m,
        "설정 하나(990 은 이 검사를 «한 번»만 돌렸다)",
        "🔴 변이체 = «결과 딕트»에 키를 하나 끼운 판. `len(mut_ws) == 4` 라 "
        "`len(...) == 3` 이 «언제나» 거짓이다",
        "🔴 «결과 딕트» 변이체 --- `조항 66-가` 가 ❌ 로 못 박은 꼴. "
        "🔴🔴 **991 자신의 러너가 `world991.py:431-432` 에서 「990 은 «결과 딕트»에 키를 끼워 "
        "«반드시 떨어지는» 변이체를 만들었다(공허)」고 «썼는데** 991 의 감사기는 이것을 "
        "「코드·구성상 거짓 false」로 «셌다». 두 산출물이 정면충돌했다")

    # ── W6 분해 항등식 ────────────────────────────────────────────────
    pool.reseed(SEEDS[0])
    b, m, resid = [], [], []
    for n in (1800, 3200, 6400):
        nh = int(round(ALPHA_H * n))
        c_HB = W.cell(pool, plan_mix_H(n), 1.0, wmaps)
        c_B = W.cell(pool, plan_mix_B(n), 1.0, wmaps)
        c_M = W.cell(pool, W.plan_fixed(n, nh), 1.0, wmaps)
        for rn in RN:
            aug = c_M["rulers"][rn] - c_B["rulers"][rn]
            sta = c_HB["rulers"][rn] - c_M["rulers"][rn]
            dlt = c_HB["rulers"][rn] - c_B["rulers"][rn]
            rr = abs((aug + sta) - dlt)
            resid.append(rr)
            b.append(rr < 1e-12)
            m.append(rr > 1e-3)
    put("W6 분해 항등식 — 증강 `A(N)` + 굶김 `S(N)` == `Δ(N)`", b, m,
        "눈금 3 × 자 3(990 이 실제로 돈 격자)",
        "🔴 변이체 = 잔차 문턱 `1e-3`. `A + S ≡ Δ` 는 `(x−y)+(z−x) = z−y` 라 잔차가 "
        "부동소수 반올림뿐이고(최대 %.3g) 「1e-3 을 넘나」가 «언제나** 거짓이다" % max(resid),
        "🔴 명제와 배선이 «둘 다» 항등식 --- `조항 66-다` 가 「`통과` 키를 빼고 «진단»으로 내려라」고 한 꼴")

    # ── W7 세 자가 다르다 ─────────────────────────────────────────────
    pool.reseed(SEEDS[0])
    c = W.cell(pool, plan_mix_H(1800), 1.0, wmaps)
    vals3 = [c["rulers"][k] for k in wmaps]
    pairs = [abs(vals3[i] - vals3[k]) for i in range(3) for k in range(i + 1, 3)]
    same_w = collections.OrderedDict((k, wmaps[W.RULER_JUDGE]) for k in wmaps)
    mv = list(W.rulers(c["per"], pool.gated, same_w).values())
    mpairs = [abs(mv[i] - mv[k]) for i in range(3) for k in range(i + 1, 3)]
    b = [min(pairs) > 1e-9]
    m = [min(mpairs) > 1e-9]
    put("W7 세 자가 «서로 다른 값»을 낸다(병기가 무의미하지 않다)", b, m,
        "설정 하나(990 은 이 검사를 «한 번»만 돌렸다)",
        "🔴 변이체 = 세 자에 «같은» 가중. 세 값이 «정확히» 같아 짝 차가 %r 이고 "
        "`min > 1e-9` 가 «언제나» 거짓이다" % [round(x, 18) for x in mpairs],
        "🔴 같은 인자를 세 번 넣은 항등식 --- 자료와 무관하게 차가 정확히 0")

    kinds = collections.Counter(v["🔴🔴🔴 갈래(실측)"] for v in rows.values())
    n_false = int(kinds.get("㉡ 구성상 거짓", 0))
    n_true = int(kinds.get("㉠ 구성상 참", 0))
    n_pow = int(kinds.get("㉢ 검정력 있음", 0))
    causes = collections.OrderedDict(
        (k, v["🔴🔴 그 까닭의 «갈래»"]) for k, v in rows.items())
    # 🔴 「구성상」이 «자료와 무관하게» 강제되는 것만 세는 «둘째 자»(티처 #130 의 손 자)
    forced = [k for k, v in rows.items()
              if v["🔴🔴🔴 갈래(실측)"] == "㉡ 구성상 거짓"
              and "측정치" not in v["🔴🔴 그 까닭의 «갈래»"]]

    res = collections.OrderedDict([
        ("무엇", "992 §B-가 — 🔴🔴🔴 **990 의 배선 일곱을 «돌려서» 잰다**(손 라벨도 산문 정규식도 아니다)"),
        ("🔴 왜", "🔴 991 의 판별기는 ㉠ AST 파싱이 «없고» ㉡ `src` 가 «죽은 변수»이며 "
                "㉢ «소스 토큰용 정규식»을 «산문 문자열»에 물렸다 --- 「결과딕트」 갈래가 "
                "«원리상» 한 번도 못 켜졌다"),
        ("🔴 검사별", rows),
        ("🔴🔴🔴 그 수", n_false),
        ("🔴🔴🔴 구성상 거짓인 검사", [k for k, v in rows.items()
                              if v["🔴🔴🔴 갈래(실측)"] == "㉡ 구성상 거짓"] or "없음"),
        ("🔴🔴 구성상 참인 검사 수", n_true),
        ("🔴🔴 검정력 있는 검사 수", n_pow),
        ("🔴 990 이 «신고한» 「공허한 변이체」 수", 0),
        ("🔴🔴🔴 990 의 신고와 992 의 실측이 갈리나", bool(n_false != 0)),
        ("🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면",
         collections.OrderedDict([
             ("🔴 그 수", len(forced)),
             ("🔴 그 검사", forced),
             ("🔴 빠진 검사", [k for k in rows if k not in forced] or "없음"),
             ("🔴 티처 #130 이 손으로 센 수", 6),
             ("🔴🔴 둘째 자와 티처의 손 자가 «같나»", bool(len(forced) == 6)),
         ])),
        ("🔴 까닭의 갈래(검사별)", causes),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(len(rows) == 7 and hits > 0)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 990 의 «일곱 전부»를 실제로 돌렸고, 각 변이체의 「어떤 설정에서도 떨어지나」를 "
         "«손 라벨 없이» 셌다"),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256(시작)", cs0),
            ("🔴 코드 sha256(끝)", code_stamp()),
            ("시각(UTC · 시작)", t0), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out992_mut.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [mut992] 990 의 일곱 — 구성상 거짓 %d · 둘째 자 %d\n"
                     % (_now(), n_false, len(forced)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
