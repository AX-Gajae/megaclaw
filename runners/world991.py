#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""991 — **순서를 고르는 것이 곧 답을 고르는 것이다** (축 C3 × C6 × C2).

사전등록 `docs/prereg_991_order_rulers.md` §1 을 그대로 따른다.

🔴🔴🔴 **이 러너는 세계 자료를 «실제로» 연다** ---
  `data/ingest/sao941` · `sao959` · `sao973_hplt` 셋 + 챔피언 판 껍질(`ff753`).
  🔴 **연 경로를 `sys.addaudithook` 으로 «런타임에» 기록한다**(`조항 73-나`).

🔴 **990 의 병 넷을 구조로 막는다.**
  ⓐ **분해 «순서»를 둘 다 낸다** --- `A + S ≡ Δ` 는 항등식이라 순서가 답을 정한다.
  ⓑ **여섯 성분 «전부»에 도메인 군집 SE 와 LODO 를 붙인다**(990 은 Δ 에만 붙였다).
  ⓒ **탐색 격자를 사전등록 «안»으로 들이고 판정 칸(`base 1800`)을 격자에서 «뺀다».**
  ⓓ **`37531` 손 리터럴을 «계산»으로 바꾼다** --- `N_ALL = ceil(len(yh)/α)`.

🔴 **변이체는 «검사 대상 코드»를 바꿔서 만든다**(`조항 66` · 991 신설).
  판정식·결과 딕트를 손으로 뒤집은 것은 변이체가 «아니다» --- 각 검사가 «종류»를 신고한다.

씀:
    python3 runners/world991.py --stage wiring --ref <40자 sha>
    python3 runners/world991.py --stage order  --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 🔴 §1-6 런타임 자: 연 `data/` 경로를 «전부» 기록한다 ─────────────────
_OPENED = collections.OrderedDict()


def _audit(event, args):
    if event != "open":
        return
    try:
        p = args[0]
    except Exception:                                              # noqa: BLE001
        return
    if not isinstance(p, str):
        try:
            p = os.fspath(p)
        except Exception:                                          # noqa: BLE001
            return
    if not isinstance(p, str):
        return
    try:
        rel = os.path.relpath(os.path.abspath(p), str(ROOT))
    except Exception:                                              # noqa: BLE001
        return
    if rel.startswith("data" + os.sep):
        _OPENED[rel] = _OPENED.get(rel, 0) + 1


sys.addaudithook(_audit)

import runners.alpha977 as A                       # noqa: E402
import runners.layers957 as L                      # noqa: E402
import runners.predict971 as P                     # noqa: E402
import ff753 as FF                                 # noqa: E402

RAN = ("runners/world991.py", "runners/alpha977.py", "runners/layers957.py",
       "runners/predict971.py", "runners/ff753.py")
OUT = ROOT / "runners"
PROG = OUT / "out991_progress.txt"

# ══ 사전등록 상수 (§7 · 측정 «전»에 박았다) ═══════════════════════════
SEEDS = list(range(989000, 989012))     # 🔴 989·990 과 «같은 씨앗»(짝 재현)
KFOLD = 5
ALPHA_H = 0.95
U_REG = 0                               # 🔴 판정 λ = 10^0
U_ALT = 3                               # 병기
KGRID = 6
THR_CARD = 0.00353                      # 🔴 자로만 쓴다 · 채택 문턱 아님
N_JUDGE = 1800                          # 🔴 판정 예산

# 🔴🔴🔴 §1-5 탐색 격자 --- **사전등록 «안»**. `base = 1800` 은 «없다»(판정 칸이다).
EXPLORE_N = 1800
EXPLORE_BASE = [45, 90, 135, 270, 450]
CLIFF_PAIRS = [(45, 90), (90, 135)]     # 🔴 「벼랑」 주장은 이 두 짝 차로만 한다

SRC_FILES = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])

RULER_JUDGE = "R_pool 묶음"          # 🔴🔴🔴 §1-2 --- 측정 «전»에 못 박았다
RULER_ALT = ("R_eq 균등", "R_champ 챔피언가중")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  [world991] %s\n" % (_now(), msg))
    sys.stderr.write("%s  [world991] %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _rl(a, n=6):
    return [_r(x, n) for x in (a.tolist() if hasattr(a, "tolist") else a)]


def old_literal_990():
    """🔴 990 의 손 리터럴을 «소스에서 읽는다» --- 손으로 안 옮긴다(규칙 D)."""
    src = (ROOT / "runners/world990.py").read_text(encoding="utf-8")
    m = re.search(r"nn = (\d+) if n is None", src)
    return int(m.group(1)) if m else None


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def world_stamp(paths=None):
    """🔴 §1-6 --- **연 세계 자료의 지문**. 손으로 안 적는다."""
    out = collections.OrderedDict()
    for name, rel in (paths or SRC_FILES).items():
        p = ROOT / rel
        if not p.is_file():
            out[name] = collections.OrderedDict([
                ("경로", rel), ("바이트", 0), ("sha256", None),
                ("🔴 못 읽었다", True)])
            continue
        h = hashlib.sha256()
        with open(str(p), "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
        out[name] = collections.OrderedDict([
            ("경로", rel), ("바이트", int(p.stat().st_size)),
            ("sha256", h.hexdigest())])
    return out


def _stamp(ref, cs0, t0):
    return collections.OrderedDict([
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", ref),
            ("🔴 코드 sha256(시작)", cs0),
            ("🔴 코드 sha256(끝)", code_stamp()),
            ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
        ("🔴🔴🔴 §1-6 이 러너가 «연» `data/` 경로",
         collections.OrderedDict([
             ("🔴 연 `data/` 경로 수", len(_OPENED)),
             ("🔴 처음 스무 경로", list(_OPENED)[:20])])),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 뽑기 — base 자리와 hplt 자리를 «둘 다 인자로» 받는다. 안 채운다.
# ══════════════════════════════════════════════════════════════════════
def avail_b(pool, fold):
    """🔴 그 씨앗·그 겹의 «자기 천장»."""
    return int((pool.fi != fold).sum())


def pick(pool, fold, nb, nh):
    """base `nb` 자리 · hplt `nh` 자리. 🔴 **모자라면 «안 채운다»**."""
    pb = pool.perm_b[(pool.fi != fold)[pool.perm_b]]
    ph = pool.perm_h
    selb, selh = pb[:max(0, int(nb))], ph[:max(0, int(nh))]
    return selb, selh, int(max(0, nb) - len(selb)), int(max(0, nh) - len(selh))


def cell(pool, plan, lam, wmaps):
    """🔴 **모든 팔이 이 «한» 함수로 지어진다**(`조항 67`)."""
    pred = np.zeros(len(pool.yb))
    rows, sb, sh = [], 0, 0
    for j in range(KFOLD):
        nb, nh = plan(j, avail_b(pool, j))
        selb, selh, s1, s2 = pick(pool, j, nb, nh)
        sb += s1
        sh += s2
        X, y, ent, _nb = A.design(pool, selb, selh, KGRID)
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(
            m, np.hstack([pool.Xb[te][:, :KGRID], pool.Ob[te]]))
        rows.append(int(len(y)))
    per = collections.OrderedDict()
    for d in pool.gated:
        m = pool.ho_mask[d]
        per[d] = float(P.spear(pred[m], pool.yb[m]))
    return {"per": per, "rulers": rulers(per, pool.gated, wmaps),
            "rows": rows, "부족.base": int(sb), "부족.hplt": int(sh)}


def rulers(per, doms, wmaps):
    """🔴 §1-2 — **세 자를 «전부» 낸다.** 하나라도 빠지면 `F03` 이다."""
    out = collections.OrderedDict()
    for name, w in wmaps.items():
        num = den = 0.0
        for d in doms:
            v = per[d]
            if np.isfinite(v):
                num += v * w[d]
                den += w[d]
        out[name] = float(num / den) if den > 0 else float("nan")
    return out


def build_wmaps(pool):
    """🔴 세 자의 가중을 «런타임에» 만든다 --- 손으로 안 적는다."""
    champ = FF.shell(FF.base()).weights(2025.0)
    doms = list(pool.gated)
    miss = [d for d in doms if d not in champ]
    if miss:
        raise SystemExit("🔴 챔피언 판에 없는 게이트 도메인: %s" % miss)
    return collections.OrderedDict([
        ("R_pool 묶음", {d: float(pool.dom_ho[d]) for d in doms}),
        ("R_eq 균등", {d: 1.0 for d in doms}),
        ("R_champ 챔피언가중", {d: float(champ[d]) for d in doms}),
    ]), collections.OrderedDict((d, int(champ[d])) for d in doms)


def n_all(pool):
    """🔴🔴🔴 §1-7 — **「전량」 눈금을 «계산»한다.** 990 은 손 리터럴을 썼다.

    `N_ALL = ceil(len(yh) / α)` 면 `round(α·N_ALL) == len(yh)` 라 hplt 부족이 0 이다.
    """
    return int(math.ceil(len(pool.yh) / ALPHA_H))


# ══ `plan` — 네 칸과 탐색 칸 ═══════════════════════════════════════════
def plan_fixed(nb, nh):
    def f(j, av):
        return (av if nb == "천장" else min(int(nb), av)), int(nh)
    return f


def plan_B(n):
    """`B` = base N · hplt 0."""
    return plan_fixed(n, 0)


def plan_M(n):
    """`M` = base N + hplt round(αN)."""
    return plan_fixed(n, int(round(ALPHA_H * n)))


def plan_H(n):
    """`H` = base N−round(αN) + hplt round(αN). 🔴 977 이 실제로 쓰는 칸."""
    nh = int(round(ALPHA_H * n))
    return plan_fixed(n - nh, nh)


def plan_S(n):
    """🔴 `S` = base N−round(αN) · hplt 0. **991 이 새로 재는 칸.**"""
    return plan_fixed(n - int(round(ALPHA_H * n)), 0)


# ══ 자 ════════════════════════════════════════════════════════════════
def cluster_se(dd, w):
    """🔴 §1-3 — **도메인 군집 SE**. 식을 사전등록에 «측정 전에» 박았다.

    `Δ = Σ_d w_d Δ_d` (`Σ w_d = 1`) 일 때
    **`SE² = (G/(G−1)) · Σ_d w_d² (Δ_d − Δ)²`**.
    """
    ks = list(dd)
    G = len(ks)
    tw = sum(w[d] for d in ks)
    ws = {d: w[d] / tw for d in ks}
    delta = sum(ws[d] * dd[d] for d in ks)
    v = (G / float(G - 1)) * sum(ws[d] ** 2 * (dd[d] - delta) ** 2 for d in ks)
    return float(delta), float(math.sqrt(v))


def lodo(dd, w):
    """🔴 §1-3 — **도메인 하나를 빼고** 남은 것의 가중으로 다시 낸다."""
    out = collections.OrderedDict()
    for drop in dd:
        ks = [d for d in dd if d != drop]
        tw = sum(w[d] for d in ks)
        out[drop] = float(sum(w[d] * dd[d] for d in ks) / tw)
    return out


# ══════════════════════════════════════════════════════════════════════
# §A 배선 — 🔴 **변이체의 「양쪽」 공허를 «둘 다» 신고한다**(`조항 66` · 991 신설)
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    wmaps, champ_w = build_wmaps(pool)
    checks = collections.OrderedDict()

    def add(name, ok, mut_ok, hits, mut_kind, why):
        """🔴🔴🔴 `구성상 참`(변이체가 안 떨어졌다)과 `구성상 거짓`(반드시 떨어진다)을 «둘 다».

        `mut_kind ∈ {코드, 판정식, 결과딕트}`. 🔴 **`코드` 가 아니면 변이체가 «아니다».**
        """
        checks[name] = collections.OrderedDict([
            ("통과", bool(ok)),
            ("🔴 변이체(일부러 깨뜨린 판)에서도 통과하나", bool(mut_ok)),
            ("🔴🔴 ㉠ 구성상 «참»인가(변이체가 «안» 떨어졌다)", bool(mut_ok)),
            ("🔴🔴🔴 ㉡ 구성상 «거짓»인가(변이체가 «반드시» 떨어진다)",
             bool(mut_kind != "코드")),
            ("🔴🔴🔴 ㉢ 변이체 종류", mut_kind),
            ("🔴 이 변이체가 «검사 대상 코드»를 바꿨나", bool(mut_kind == "코드")),
            ("🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)", int(hits)),
            ("왜", why)])

    # ── X1 🔴🔴🔴 색인 대조 — `W6` 이 「재려 했던」 것 ────────────────────
    #    네 칸이 «같은 씨앗 · 같은 겹 배정 · 같은 λ · 같은 뽑기 색인»을 썼나.
    nh_j = int(round(ALPHA_H * N_JUDGE))
    nb_j = N_JUDGE - nh_j
    same, mut, hits = [], [], 0
    for s in SEEDS[:3]:
        pool.reseed(s)
        fi0 = pool.fi.copy()
        for j in range(KFOLD):
            av = avail_b(pool, j)
            bB, hB, _1, _2 = pick(pool, j, *plan_B(N_JUDGE)(j, av))
            bM, hM, _3, _4 = pick(pool, j, *plan_M(N_JUDGE)(j, av))
            bH, hH, _5, _6 = pick(pool, j, *plan_H(N_JUDGE)(j, av))
            bS, hS, _7, _8 = pick(pool, j, *plan_S(N_JUDGE)(j, av))
            same.append(bool(
                np.array_equal(bM, bB)                       # M·B 의 base 색인 동일
                and np.array_equal(bH, bS)                   # H·S 의 base 색인 동일
                and np.array_equal(bH, bB[:len(bH)])         # H 는 B 의 «접두사»
                and np.array_equal(hH, hM)                   # H·M 의 hplt 색인 동일
                and len(hB) == 0 and len(hS) == 0            # B·S 는 hplt 를 «안» 쓴다
                and np.array_equal(pool.fi, fi0)))           # 겹 배정이 «안» 바뀌었다
            # 🔴 변이체 = **칸 사이에 `reseed` 를 끼운 코드**(검사 «대상 코드»를 바꾼다)
            pool.reseed(s + 500000)
            bB2, _h, _9, _10 = pick(pool, j, *plan_B(N_JUDGE)(j, avail_b(pool, j)))
            pool.reseed(s)
            mut.append(bool(np.array_equal(bH, bB2[:len(bH)])
                            and np.array_equal(pool.fi, fi0)))
            hits += 6
    add("X1 🔴🔴🔴 색인 대조 — 네 칸(`B`·`M`·`H`·`S`)이 «같은 씨앗·같은 겹·같은 λ·같은 뽑기 색인»을 썼다",
        all(same), all(mut), hits, "코드",
        "🔴🔴🔴 **`W6`(분해 항등식)이 «재려 했던» 것이다.** 항등식은 어떤 수를 넣어도 잔차 0 이라 "
        "검정력이 0 이고, 분해가 뜻을 가지려면 «네 칸이 같은 뽑기에서 왔어야» 한다 --- "
        "그것은 «색인 배열 자체»로만 잴 수 있다. 🔴 변이체 = 칸 사이에 `reseed` 를 끼운 «코드»")

    # ── X2 🔴 팔 B 는 «안 채운다» ──────────────────────────────────────
    okB, mutB, hits = [], [], 0
    ceil_by_seed = collections.OrderedDict()
    for s in SEEDS:
        pool.reseed(s)
        per_fold = [avail_b(pool, j) for j in range(KFOLD)]
        ceil_by_seed[str(s)] = {"겹별": per_fold, "최소": int(min(per_fold))}
        for j in range(KFOLD):
            av = avail_b(pool, j)
            b_hi, h_hi, s1, _s2 = pick(pool, j, 25600, 0)
            okB.append(len(h_hi) == 0 and len(b_hi) == av and s1 == 25600 - av)
            # 🔴 변이체 = **채우는 뽑기**(base 모자람을 hplt 로 메운다) --- 코드를 바꾼다
            bm, hm, sm, _sm2 = pick(pool, j, 25600, 0)
            if sm > 0:
                hm = pool.perm_h[:sm]
            mutB.append(len(hm) == 0)
            hits += 2
    add("X2 팔 `B`·`S` 는 «각 겹의 자기 천장»에서 멈춘다(HPLT 로 «안» 채운다)",
        all(okB), all(mutB), hits, "코드",
        "🔴 변이체 = **채우는 뽑기**(base 모자람을 hplt 로 메운다) --- 떨어져야 한다")

    # ── X3 🔴 유보는 어떤 예산에서도 학습에 «안 닿는다» ────────────────
    NA = n_all(pool)
    tr_hit, mut_hit, hits = 0, 0, 0
    for s in SEEDS[:3]:
        pool.reseed(s)
        for j in range(KFOLD):
            b, _h, _s1, _s2 = pick(pool, j, NA, len(pool.yh))
            tr_hit += int((pool.fi[b] == j).sum())
            bm = pool.perm_b[:NA]                  # 🔴 변이체 = 겹을 «안 거른» 뽑기
            mut_hit += int((pool.fi[bm] == j).sum())
            hits += len(b)
    add("X3 어떤 예산에서도 학습이 «그 겹의 유보 행»을 안 쓴다",
        tr_hit == 0, mut_hit == 0, hits, "코드",
        "🔴 겹 j 의 학습 색인 중 `fi == j` 인 것의 수를 «전수» 센다 --- 0 이어야 한다. "
        "🔴 변이체 = 겹을 «안 거른» 뽑기(`perm_b[:N]`) --- 유보를 %d 자리 밟는다" % mut_hit)

    # ── X4 🔴🔴 세 자가 «서로 다른» 자인가 ────────────────────────────
    pool.reseed(SEEDS[0])
    c = cell(pool, plan_H(N_JUDGE), 1.0, wmaps)
    vals = [c["rulers"][k] for k in wmaps]
    pairs = [abs(vals[i] - vals[k]) for i in range(3) for k in range(i + 1, 3)]
    same_w = collections.OrderedDict((k, wmaps[RULER_JUDGE]) for k in wmaps)
    mv = list(rulers(c["per"], pool.gated, same_w).values())
    mpairs = [abs(mv[i] - mv[k]) for i in range(3) for k in range(i + 1, 3)]
    add("X4 🔴🔴 세 자가 «서로 다른 값»을 낸다(병기가 무의미하지 않다)",
        min(pairs) > 1e-9, min(mpairs) > 1e-9, len(pairs) + len(mpairs), "코드",
        "🔴 같은 도메인별 ρ 에 세 가중을 물려 세 쌍의 차를 «전수» 잰다. "
        "🔴 변이체 = 세 자에 «같은» 가중을 물린 판(`rulers()` 의 인자를 바꾼다)")

    # ── X5 🔴 세계 자료 지문 — 🔴 변이체는 «경로 목록»(코드 입력)을 바꾼다 ──
    ws = world_stamp()
    mut_paths = collections.OrderedDict(SRC_FILES)
    mut_paths["sao941"] = "data/ingest/sao941/🔴없는파일.jsonl.gz"
    mut_ws = world_stamp(mut_paths)
    ok5 = bool(len(ws) == 3 and all(v["바이트"] > 0 for v in ws.values()))
    mut5 = bool(len(mut_ws) == 3 and all(v["바이트"] > 0 for v in mut_ws.values()))
    add("X5 세 세계 자료 파일이 «전부» 열렸고 지문이 났다", ok5, mut5,
        len(ws) * 2 + len(mut_ws) * 2, "코드",
        "🔴 변이체 = `world_stamp` 에 «없는 경로»를 넘긴 판 --- 990 은 «결과 딕트»에 "
        "키를 하나 끼워서 「반드시 떨어지는」 변이체를 만들었다(공허)")

    # ── X6 🔴 977 재현 — 🔴 변이체는 «α»(코드 입력)를 바꾼다 ──────────
    rep_vals = []
    for seed in A.SEEDS:
        pool.reseed(seed)
        r = A.oof(pool, 0.95, 10.0 ** U_REG, KGRID)
        p_, _e, _pr = A.score(pool, r["예측"])
        rep_vals.append(float(p_))
    got = float(np.mean(rep_vals))
    pool.reseed(A.SEEDS[0])
    rm = A.oof(pool, 0.5, 10.0 ** U_REG, KGRID)
    pm, _e2, _p2 = A.score(pool, rm["예측"])
    want = 0.3596                    # `out977_grid.json` 의 `u=0|α=0.95` 묶음 ρ(공표 4자리)
    add("X6 977 의 `u=0|α=0.95` 묶음 ρ 를 «977 자기 씨앗·자기 함수»로 다시 내면 공표값과 같다",
        abs(got - want) <= 5e-4, abs(float(pm) - want) <= 5e-4, len(A.SEEDS) + 1, "코드",
        "🔴 변이체 = **`α = 0.5` 로 돌린 판**(검사 «대상 코드»의 입력을 바꾼다). "
        "🔴🔴 990 은 「공표값 + 0.1」이라는 «판정식» 변이체를 썼다 --- 반드시 떨어지므로 공허. "
        "🔴🔴 이것은 «독립» 재현이 «아니다» --- 977 자기 함수를 977 자기 씨앗으로 돌린 것이고 "
        "공표값이 «4자리»라 그보다 촘촘한 차이는 원리상 주장 못 한다")

    # ── D1 🔴🔴🔴 분해 항등식 — **진단이다. `통과` 키가 «없다»** ────────
    pool.reseed(SEEDS[0])
    cB = cell(pool, plan_B(N_JUDGE), 1.0, wmaps)
    cM = cell(pool, plan_M(N_JUDGE), 1.0, wmaps)
    cH = cell(pool, plan_H(N_JUDGE), 1.0, wmaps)
    cS = cell(pool, plan_S(N_JUDGE), 1.0, wmaps)
    residA, residB, nres = [], [], 0
    for rn in wmaps:
        dlt = cH["rulers"][rn] - cB["rulers"][rn]
        residA.append(abs(((cM["rulers"][rn] - cB["rulers"][rn])
                           + (cH["rulers"][rn] - cM["rulers"][rn])) - dlt))
        residB.append(abs(((cH["rulers"][rn] - cS["rulers"][rn])
                           + (cS["rulers"][rn] - cB["rulers"][rn])) - dlt))
        nres += 2
    diag = collections.OrderedDict([
        ("🔴🔴🔴 이것은 «진단»이다 --- `통과` 키가 «없다»",
         "🔴 **`A + S ≡ Δ` 는 `(x−y)+(z−x) = z−y` 라 «어떤 수를 넣어도» 성립한다.** "
         "990 의 `W6`(「42 칸 잔차 0.0」)은 «부동소수 결합법칙»을 잰 것이지 세계를 잰 것이 아니다. "
         "🔴🔴🔴 **검정력 0.** 그 자리에 `X1`(색인 대조)을 넣었다"),
        ("🔴 순서 A 잔차 최대", _r(max(residA), 15)),
        ("🔴 순서 B 잔차 최대", _r(max(residB), 15)),
        ("🔴 잰 자리", nres),
        ("🔴 990 은 이 검사를 «배선 명부»에 넣고 `통과` 를 셌다", True),
    ])

    n_ok = len([1 for v in checks.values() if v["통과"]])
    n_const_t = len([1 for v in checks.values()
                     if v["🔴🔴 ㉠ 구성상 «참»인가(변이체가 «안» 떨어졌다)"]])
    n_const_f = len([1 for v in checks.values()
                     if v["🔴🔴🔴 ㉡ 구성상 «거짓»인가(변이체가 «반드시» 떨어진다)"]])
    hitlist = [v["🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)"] for v in checks.values()]
    tot_hits = int(sum(hitlist))
    res = collections.OrderedDict([
        ("무엇", "991 §1 배선 — 🔴 **네 칸의 색인 대조 · 변이체의 «양쪽» 공허**"),
        ("🔴 축", "C3 × C6 × C2"),
        ("사전등록", "docs/prereg_991_order_rulers.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", ws),
        ("🔴 자료 행", collections.OrderedDict([
            ("base 행(= 유보 전량)", int(len(pool.yb))),
            ("🔴 게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in pool.gated))),
            ("hplt 행(= 학습에만)", int(len(pool.yh))),
            ("게이트 도메인", list(pool.gated)),
            ("🔴 977 의 예산 상수 N_B", int(A.N_B)),
            ("🔴🔴🔴 `N_ALL`(계산 --- 손 리터럴이 아니다)", int(NA)),
            ("🔴 `round(α·N_ALL)`", int(round(ALPHA_H * NA))),
            ("🔴🔴 그것이 `len(yh)` 와 같나", bool(round(ALPHA_H * NA) == len(pool.yh))),
            ("🔴🔴🔴 990 이 쓴 «손 리터럴»(`world990.py` 소스에서 읽었다)", old_literal_990()),
            ("🔴🔴🔴 그 리터럴이 만든 `round(α·N)`",
             int(round(ALPHA_H * old_literal_990())) if old_literal_990() else None),
            ("🔴🔴🔴 그래서 hplt 가 «몇 자리» 모자랐나",
             int(round(ALPHA_H * old_literal_990()) - len(pool.yh))
             if old_literal_990() else None),
            ("🔴 `N_ALL` − 손 리터럴", int(NA - old_literal_990()) if old_literal_990() else None),
        ])),
        ("🔴 씨앗별 base 천장", collections.OrderedDict([
            ("씨앗별", ceil_by_seed),
            ("🔴 겹 최소 범위",
             [int(min(v["최소"] for v in ceil_by_seed.values())),
              int(max(v["최소"] for v in ceil_by_seed.values()))]),
            ("🔴 그 폭(= 씨앗에 따라 base 가 다른 행 수)",
             int(max(v["최소"] for v in ceil_by_seed.values())
                 - min(v["최소"] for v in ceil_by_seed.values()))),
        ])),
        ("🔴 세 자의 가중(런타임)", collections.OrderedDict([
            ("R_pool 묶음", {d: int(pool.dom_ho[d]) for d in pool.gated}),
            ("R_eq 균등", {d: 1 for d in pool.gated}),
            ("R_champ 챔피언가중", champ_w),
            ("🔴 판정 자", RULER_JUDGE),
            ("🔴 병기 자", list(RULER_ALT)),
        ])),
        ("배선 검사", checks),
        ("🔴🔴🔴 D1 분해 항등식 — **진단**(배선 명부 «밖» · `통과` 키 없음)", diag),
        ("🔴 배선 검사 수(분모)", len(checks)),
        ("🔴 통과 수", n_ok),
        ("🔴🔴 ㉠ 구성상 «참»인 검사 수(변이체가 안 떨어졌다)", n_const_t),
        ("🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수(변이체가 반드시 떨어진다)", n_const_f),
        ("🔴🔴🔴 ㉢ 변이체가 «검사 대상 코드»를 바꾼 검사 수",
         len([1 for v in checks.values() if v["🔴🔴🔴 ㉢ 변이체 종류"] == "코드"])),
        ("🔴 걸린 자리 합", tot_hits),
        ("🔴🔴 걸린 자리 «중앙값»", int(sorted(hitlist)[len(hitlist) // 2])),
        ("🔴🔴🔴 «최대 기여» 검사의 몫",
         _r(max(hitlist) / float(tot_hits), 4) if tot_hits else None),
        ("🔴 그 검사 이름",
         [k for k, v in checks.items()
          if v["🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)"] == max(hitlist)][0]),
        ("통과", bool(n_ok == len(checks) and n_const_t == 0 and n_const_f == 0)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 여섯이 다 통과했고, «양쪽» 공허가 «둘 다» 0 이다 --- "
         "변이체가 하나도 「안 떨어지지」 않았고 하나도 「반드시 떨어지지」 않았다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


# ══════════════════════════════════════════════════════════════════════
# §B 순서 — 🔴🔴🔴 **한 표에 「자 셋 × 다섯 칸」을 낸다**
# ══════════════════════════════════════════════════════════════════════
def stage_order(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    wmaps, champ_w = build_wmaps(pool)
    RN = list(wmaps)
    doms = list(pool.gated)
    NA = n_all(pool)
    lams = ((U_REG, 10.0 ** U_REG), (U_ALT, 10.0 ** U_ALT))
    t_start = time.time()

    raw = {u: collections.OrderedDict() for u, _ in lams}

    def put(u, key, c):
        slot = raw[u].setdefault(key, {"ruler": {k: [] for k in RN},
                                       "per": {d: [] for d in doms},
                                       "rows": None, "부족.base": [],
                                       "부족.hplt": []})
        for k in RN:
            slot["ruler"][k].append(c["rulers"][k])
        for d in doms:
            slot["per"][d].append(c["per"][d])
        slot["rows"] = c["rows"]
        slot["부족.base"].append(c["부족.base"])
        slot["부족.hplt"].append(c["부족.hplt"])

    CELLS = collections.OrderedDict([("B", plan_B), ("M", plan_M),
                                     ("H", plan_H), ("S", plan_S)])
    ncell, nexp = 0, 0
    for si, seed in enumerate(SEEDS):
        pool.reseed(seed)
        for u, lam in lams:
            for nm, pf in CELLS.items():
                put(u, (nm, N_JUDGE), cell(pool, pf(N_JUDGE), lam, wmaps))
                ncell += 1
        # 🔴 §1-7 「전량」 눈금 --- `N_ALL` 은 «계산»이다
        for nm, pf in CELLS.items():
            put(U_REG, (nm, NA), cell(pool, pf(NA), 10.0 ** U_REG, wmaps))
            ncell += 1
        # 🔴 §1-5 탐색 격자 --- **사전등록 «안»** · `base = 1800` 은 «없다»
        for nb in EXPLORE_BASE:
            put(U_REG, ("탐색", nb),
                cell(pool, plan_fixed(nb, EXPLORE_N - nb), 10.0 ** U_REG, wmaps))
            nexp += 1
        # 🔴 §1-7 깨끗한 천장 대조 --- base 를 «자기 천장»에 두고 hplt 만 흔든다
        for h in (0, len(pool.yh)):
            put(U_REG, ("증강천장", h),
                cell(pool, plan_fixed("천장", h), 10.0 ** U_REG, wmaps))
            ncell += 1
        _prog("씨앗 %d/%d (%d) — 칸 %d + 탐색 %d · %.1fs"
              % (si + 1, len(SEEDS), seed, ncell, nexp, time.time() - t_start))

    # ══ 자 ════════════════════════════════════════════════════════════
    def arr(u, key, rn):
        return np.asarray(raw[u][key]["ruler"][rn], float)

    def perarr(u, key, d):
        return np.asarray(raw[u][key]["per"][d], float)

    hitbox = {"n": 0}

    def lin_block(u, coefs, rn, w):
        """🔴🔴🔴 **성분 «전부»가 이 «한» 함수로 지어진다**(`조항 67`).

        `coefs = {칸키: 계수}`. 도메인별로 «먼저» 선형결합하고 그 위에 군집 SE 를 물린다.
        """
        tot = None
        for k, cf in coefs.items():
            v = cf * arr(u, k, rn)
            tot = v if tot is None else tot + v
        se_seed = float(np.std(tot, ddof=1) / math.sqrt(len(tot)))
        dd = collections.OrderedDict()
        for d in doms:
            s = 0.0
            for k, cf in coefs.items():
                s += cf * float(np.mean(perarr(u, k, d)))
            dd[d] = s
        delta, se_clu = cluster_se(dd, w)
        lo = lodo(dd, w)
        flip = [x for x, v in lo.items() if (v > 0) != (delta > 0)]
        hitbox["n"] += len(doms) * len(SEEDS)
        return collections.OrderedDict([
            ("🔴🔴🔴 값", _r(float(tot.mean()))),
            ("🔴 값(도메인 가중 합 · 항등식 확인)", _r(delta)),
            ("🔴🔴🔴 도메인 군집 SE", _r(se_clu)),
            ("🔴🔴🔴 t_clu", _r(delta / se_clu) if se_clu else None),
            ("🔴🔴🔴 t_clu 절댓값이 2 이상인가",
             bool(se_clu and abs(delta / se_clu) >= 2.0)),
            ("🔴 씨앗 SE(병기 — 판정에 «못» 쓴다)", _r(se_seed)),
            ("🔴 값 / 씨앗 SE", _r(float(tot.mean() / se_seed)) if se_seed else None),
            ("🔴 씨앗별 값", _rl(tot)),
            ("🔴 도메인별 값", collections.OrderedDict((k, _r(v)) for k, v in dd.items())),
            ("🔴🔴 LODO", collections.OrderedDict((k, _r(v)) for k, v in lo.items())),
            ("🔴🔴🔴 LODO 에서 부호가 뒤집히는 도메인", flip or "없음"),
            ("🔴🔴🔴 LODO 부호 뒤집힌 도메인 수", len(flip)),
        ])

    N = N_JUDGE
    B, M, H, S = ("B", N), ("M", N), ("H", N), ("S", N)
    COMP = collections.OrderedDict([
        ("Δ = H − B", {H: 1.0, B: -1.0}),
        ("순서 A · 증강 A = M − B", {M: 1.0, B: -1.0}),
        ("순서 A · 굶김 S_A = H − M", {H: 1.0, M: -1.0}),
        ("순서 B · 증강 A′ = H − S", {H: 1.0, S: -1.0}),
        ("순서 B · 굶김 S_B = S − B", {S: 1.0, B: -1.0}),
        ("상호작용 A′ − A", {H: 1.0, S: -1.0, M: -1.0, B: 1.0}),
        ("대칭 배분 · 증강 (A + A′)/2", {M: 0.5, B: -0.5, H: 0.5, S: -0.5}),
        ("대칭 배분 · 굶김 (S_A + S_B)/2", {H: 0.5, M: -0.5, S: 0.5, B: -0.5}),
    ])

    # ── §1 🔴🔴🔴 한 표 — 자 셋 × 다섯 칸 ─────────────────────────────
    order = collections.OrderedDict()
    for u, _l in lams:
        per_rn = collections.OrderedDict()
        for rn in RN:
            blocks = collections.OrderedDict(
                (nm, lin_block(u, cf, rn, wmaps[rn])) for nm, cf in COMP.items())
            resid_a = abs(blocks["순서 A · 증강 A = M − B"]["🔴🔴🔴 값"]
                          + blocks["순서 A · 굶김 S_A = H − M"]["🔴🔴🔴 값"]
                          - blocks["Δ = H − B"]["🔴🔴🔴 값"])
            resid_b = abs(blocks["순서 B · 증강 A′ = H − S"]["🔴🔴🔴 값"]
                          + blocks["순서 B · 굶김 S_B = S − B"]["🔴🔴🔴 값"]
                          - blocks["Δ = H − B"]["🔴🔴🔴 값"])
            aA = blocks["순서 A · 증강 A = M − B"]["🔴🔴🔴 값"]
            sA = blocks["순서 A · 굶김 S_A = H − M"]["🔴🔴🔴 값"]
            aB = blocks["순서 B · 증강 A′ = H − S"]["🔴🔴🔴 값"]
            sB = blocks["순서 B · 굶김 S_B = S − B"]["🔴🔴🔴 값"]
            per_rn[rn] = collections.OrderedDict([
                ("🔴 성분", blocks),
                ("🔴🔴🔴 한 줄 표", collections.OrderedDict([
                    ("Δ(1800)", blocks["Δ = H − B"]["🔴🔴🔴 값"]),
                    ("순서 A 증강", aA), ("순서 A 굶김", sA),
                    ("순서 B 증강", aB), ("순서 B 굶김", sB),
                    ("상호작용", blocks["상호작용 A′ − A"]["🔴🔴🔴 값"]),
                    ("대칭 증강", blocks["대칭 배분 · 증강 (A + A′)/2"]["🔴🔴🔴 값"]),
                    ("대칭 굶김", blocks["대칭 배분 · 굶김 (S_A + S_B)/2"]["🔴🔴🔴 값"]),
                ])),
                ("🔴🔴🔴 순서 A 에서 «굶김»이 차지하는 몫",
                 _r(abs(sA) / (abs(aA) + abs(sA)), 4) if (abs(aA) + abs(sA)) else None),
                ("🔴🔴🔴 순서 B 에서 «굶김»이 차지하는 몫",
                 _r(abs(sB) / (abs(aB) + abs(sB)), 4) if (abs(aB) + abs(sB)) else None),
                ("🔴🔴🔴 순서 A 의 증강 부호", "양" if aA > 0 else "음"),
                ("🔴🔴🔴 순서 B 의 증강 부호", "양" if aB > 0 else "음"),
                ("🔴🔴🔴 순서에 따라 «증강의 부호»가 뒤집히나", bool((aA > 0) != (aB > 0))),
                ("🔴🔴🔴 순서에 따라 «굶김의 부호»가 뒤집히나", bool((sA > 0) != (sB > 0))),
                ("🔴 순서 A 잔차(진단 — 항등식이라 검정력 0)", _r(resid_a, 15)),
                ("🔴 순서 B 잔차(진단 — 항등식이라 검정력 0)", _r(resid_b, 15)),
            ])
        order[str(u)] = per_rn

    # ── §2 🔴🔴 탐색 격자 — **사전등록 «안»** ─────────────────────────
    explore = collections.OrderedDict()
    for rn in RN:
        rho = collections.OrderedDict(
            (str(nb), _r(float(arr(U_REG, ("탐색", nb), rn).mean())))
            for nb in EXPLORE_BASE)
        pairs = collections.OrderedDict()
        for lo_, hi_ in zip(EXPLORE_BASE[:-1], EXPLORE_BASE[1:]):
            pairs["%d → %d" % (lo_, hi_)] = lin_block(
                U_REG, {("탐색", hi_): 1.0, ("탐색", lo_): -1.0}, rn, wmaps[rn])
        cliff = collections.OrderedDict()
        for lo_, hi_ in CLIFF_PAIRS:
            cliff["%d → %d" % (lo_, hi_)] = pairs["%d → %d" % (lo_, hi_)][
                "🔴🔴🔴 t_clu 절댓값이 2 이상인가"]
        nsurv = len([1 for v in cliff.values() if v])
        best = EXPLORE_BASE[int(np.argmax([rho[str(nb)] for nb in EXPLORE_BASE]))]
        explore[rn] = collections.OrderedDict([
            ("🔴 격자(총량 %d 고정 · hplt = %d − base)" % (EXPLORE_N, EXPLORE_N), rho),
            ("🔴🔴🔴 ρ 가 «가장 높은» base 행 수", int(best)),
            ("🔴 그 값", rho[str(best)]),
            ("🔴 977 이 쓴 base 행 수(α=0.95 · N=1800)",
             int(A.N_B - round(ALPHA_H * A.N_B))),
            ("🔴 짝 차(이웃 눈금) — 군집 SE·LODO 를 «전부» 붙였다", pairs),
            ("🔴🔴🔴 「벼랑」 세 칸(45→90→135)의 짝 차가 2·SE_clu 를 넘나", cliff),
            ("🔴🔴🔴 그중 넘은 수", nsurv),
            ("🔴🔴🔴 「벼랑」이라 적을 수 있나(`조항 68`)", bool(nsurv > 0)),
        ])
    explore["🔴🔴🔴 이 격자는 «사전등록 안»이다"] = (
        "🔴 **채점 분모에 «든다».** 990 은 이 격자를 분모 «밖»에 두고 「이 사이클 제일 센 발견」을 "
        "거기 실었다. 🔴 **그리고 990 격자의 `base=90` 칸과 `base=1800` 칸의 차가 "
        "«판정 Δ(1800) 그 자체»였다** --- 991 은 `base=1800` 을 격자에서 «뺐다»")
    explore["🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"] = bool(
        1800 in EXPLORE_BASE)
    explore["🔴🔴 `base=90` 칸이 판정의 `H` 칸과 «같은 물건»인가 — 실측"] = \
        collections.OrderedDict([
            ("탐색 base=90 의 판정 자 ρ", _r(float(arr(U_REG, ("탐색", 90), RULER_JUDGE).mean()))),
            ("판정 `H` 칸의 판정 자 ρ", _r(float(arr(U_REG, H, RULER_JUDGE).mean()))),
            ("🔴 차", _r(float((arr(U_REG, ("탐색", 90), RULER_JUDGE)
                              - arr(U_REG, H, RULER_JUDGE)).mean()), 15)),
            ("🔴🔴 같은 물건인가", bool(np.allclose(
                arr(U_REG, ("탐색", 90), RULER_JUDGE), arr(U_REG, H, RULER_JUDGE)))),
            ("🔴 그래서", "🔴 **같은 칸이다. 그 사실을 «숨기지 않고 실측해서» 적는다** --- "
                       "탐색 절의 어떤 «주장»도 `B`(base 1800) 칸을 «안 읽는다»"),
        ])
    explore["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(nexp * len(doms))

    # ── §3 🔴 깨끗한 천장 대조 ────────────────────────────────────────
    ceil_blk = collections.OrderedDict()
    for rn in RN:
        ceil_blk[rn] = lin_block(
            U_REG, {("증강천장", len(pool.yh)): 1.0, ("증강천장", 0): -1.0},
            rn, wmaps[rn])
    ceil_out = collections.OrderedDict([
        ("🔴🔴🔴 무엇", "🔴 **base 를 «각 씨앗·각 겹의 자기 천장»에 두고 hplt 만 0 → %d 로 흔든 차.** "
                     "🔴 990 의 헤드라인 `Δ(천장)` 은 「HPLT 전량 vs base 천장」이 «아니다» --- "
                     "`nh = round(0.95 × 손리터럴)` 이 hplt 행 수를 넘어 «자리가 모자랐고», "
                     "씨앗에 따라 base 도 달랐다" % len(pool.yh)),
        ("🔴 자별", ceil_blk),
        ("🔴 h=0 의 ρ(자별)", collections.OrderedDict(
            (rn, _r(float(arr(U_REG, ("증강천장", 0), rn).mean()))) for rn in RN)),
        ("🔴 h=%d 의 ρ(자별)" % len(pool.yh), collections.OrderedDict(
            (rn, _r(float(arr(U_REG, ("증강천장", len(pool.yh)), rn).mean()))) for rn in RN)),
    ])

    # ── §4 🔴🔴 즉시정정 — 「전량」 눈금과 부족 자리 ────────────────────
    def lack(u, key, which):
        return int(max(raw[u][key][which]))

    lit = old_literal_990()
    fix = collections.OrderedDict([
        ("🔴🔴🔴 `N_ALL` 을 «계산»했다", int(NA)),
        ("🔴 식", "`ceil(len(pool.yh) / ALPHA_H)`"),
        ("🔴 `len(pool.yh)`", int(len(pool.yh))),
        ("🔴 `len(pool.yb)`", int(len(pool.yb))),
        ("🔴🔴🔴 990 의 손 리터럴(`world990.py` 소스에서 «읽었다»)", lit),
        ("🔴 `round(α · 손리터럴)`", int(round(ALPHA_H * lit)) if lit else None),
        ("🔴🔴🔴 그 리터럴이 요구한 hplt 자리 − 실제 hplt 행",
         int(round(ALPHA_H * lit) - len(pool.yh)) if lit else None),
        ("🔴 `round(α · N_ALL)`", int(round(ALPHA_H * NA))),
        ("🔴🔴 `round(α · N_ALL)` 이 `len(yh)` 와 같나",
         bool(round(ALPHA_H * NA) == len(pool.yh))),
        ("🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대", lack(U_REG, ("H", NA), "부족.hplt")),
        ("🔴 N_ALL 칸의 부족.base 최대", lack(U_REG, ("H", NA), "부족.base")),
        ("🔴 `B`(base N_ALL) 칸의 부족.base 최대", lack(U_REG, ("B", NA), "부족.base")),
        ("🔴 판정 예산 1800 네 칸의 부족 합", collections.OrderedDict(
            (nm, {"base": lack(U_REG, (nm, N), "부족.base"),
                  "hplt": lack(U_REG, (nm, N), "부족.hplt")}) for nm in CELLS)),
        ("🔴 「전량」 눈금의 자별 Δ(H − B)", collections.OrderedDict(
            (rn, _r(float((arr(U_REG, ("H", NA), rn)
                           - arr(U_REG, ("B", NA), rn)).mean()))) for rn in RN)),
        ("🔴 왜 이것이 「천장 대조」가 «아닌가»",
         "🔴 **`B`(base N_ALL) 는 각 씨앗·겹의 자기 천장에서 멈추므로 실제 base 행이 씨앗마다 다르다.** "
         "🔴🔴 **깨끗한 천장 대조는 §3 이다**(base 를 천장에 두고 hplt 만 흔든다)"),
    ])

    # ── §5 🔴🔴🔴 판정 ────────────────────────────────────────────────
    JU = order[str(U_REG)]
    jd = JU[RULER_JUDGE]
    judge = collections.OrderedDict()
    judge["🔴🔴🔴 판정 자(측정 «전»에 못 박았다)"] = RULER_JUDGE
    judge["🔴 판정 자의 근거"] = "docs/목표.md:164 — 981~ 정본 자는 `R_pool 묶음`(w ∝ n_d)"
    judge["🔴 판정 λ"] = "u = %d (10^%d)" % (U_REG, U_REG)
    judge["🔴 판정 SE"] = "도메인 군집 SE(사전등록 §1-3 식)"
    judge["🔴🔴🔴 한 표 — 자 셋 × 다섯 칸"] = collections.OrderedDict(
        (rn, JU[rn]["🔴🔴🔴 한 줄 표"]) for rn in RN)
    for rn in RN:
        judge["🔴 %s 순서 A 증강 부호" % rn] = JU[rn]["🔴🔴🔴 순서 A 의 증강 부호"]
        judge["🔴 %s 순서 B 증강 부호" % rn] = JU[rn]["🔴🔴🔴 순서 B 의 증강 부호"]
        judge["🔴 %s 순서에 따라 증강 부호가 뒤집히나" % rn] = \
            JU[rn]["🔴🔴🔴 순서에 따라 «증강의 부호»가 뒤집히나"]
        judge["🔴 %s 순서 A 굶김 몫" % rn] = JU[rn]["🔴🔴🔴 순서 A 에서 «굶김»이 차지하는 몫"]

    # 🔴🔴🔴 자·순서 전쟁 — 「무엇이 부호를 만들었나」가 «조건부»인가
    sA_sign = {rn: (JU[rn]["🔴🔴🔴 한 줄 표"]["순서 A 굶김"] > 0) for rn in RN}
    aA_sign = {rn: (JU[rn]["🔴🔴🔴 한 줄 표"]["순서 A 증강"] > 0) for rn in RN}
    split_starve = [rn for rn in RULER_ALT if sA_sign[rn] != sA_sign[RULER_JUDGE]]
    split_aug = [rn for rn in RULER_ALT if aA_sign[rn] != aA_sign[RULER_JUDGE]]
    order_flip = [rn for rn in RN
                  if JU[rn]["🔴🔴🔴 순서에 따라 «증강의 부호»가 뒤집히나"]]
    judge["🔴🔴🔴 판정 자와 «굶김 부호»가 갈린 병기 자"] = split_starve or "없음"
    judge["🔴🔴🔴 판정 자와 «증강 부호»가 갈린 병기 자"] = split_aug or "없음"
    judge["🔴🔴🔴 순서에 따라 «증강 부호»가 뒤집히는 자"] = order_flip or "없음"
    judge["🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄"] = (
        "🔴 **`W1`(「부호를 만든 것은 굶김이다」)은 «무조건 명제»가 아니다 --- "
        "`%s` 자·순서 A 에서만 참이고, 순서 B 에서는 증강이 «양수»이며(자 %s), "
        "굶김의 부호가 갈리는 병기 자는 [%s] 다.**"
        % (RULER_JUDGE, " · ".join(order_flip) or "없음",
           " · ".join(split_starve) or "없음"))

    # 🔴 예측이 읽는 칸 --- 🔴 키 이름에 `==`·`>=`·`<=`·`|` 를 «안 쓴다**(`_KEYPATH` 규약)
    judge["🔴 P1 판정자 순서A 굶김 t_clu 2 이상인가"] = \
        jd["🔴 성분"]["순서 A · 굶김 S_A = H − M"]["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]
    judge["🔴 P1 그 t_clu"] = \
        jd["🔴 성분"]["순서 A · 굶김 S_A = H − M"]["🔴🔴🔴 t_clu"]
    judge["🔴 P2 판정자 상호작용 t_clu 2 이상인가"] = \
        jd["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]
    judge["🔴 P2 그 t_clu"] = jd["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"]
    judge["🔴 P3 탐색 45-90-135 짝차 중 2·SE_clu 넘은 수"] = \
        explore[RULER_JUDGE]["🔴🔴🔴 그중 넘은 수"]
    judge["🔴 Δ(1800) t_clu"] = jd["🔴 성분"]["Δ = H − B"]["🔴🔴🔴 t_clu"]
    judge["🔴 Δ(1800) 군집 SE"] = jd["🔴 성분"]["Δ = H − B"]["🔴🔴🔴 도메인 군집 SE"]
    judge["🔴🔴 성분 여덟 중 t_clu 가 2 를 넘은 것(판정 자)"] = [
        k for k, v in jd["🔴 성분"].items() if v["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]] or "없음"
    judge["🔴🔴 그 수(판정 자)"] = len([
        1 for v in jd["🔴 성분"].values() if v["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]])
    judge["🔴 문턱 0.00353 — 깨끗한 천장 대조가 이 «자»를 넘었나"] = bool(
        ceil_blk[RULER_JUDGE]["🔴🔴🔴 값"] > THR_CARD)
    judge["🔴 깨끗한 천장 대조 값(판정 자)"] = ceil_blk[RULER_JUDGE]["🔴🔴🔴 값"]
    judge["🔴🔴 노트 133 — 「채택」이라 적나"] = (
        "🔴 «안» 적는다 — 채택 문턱은 「못 정했다」(968 재정정). 이 수는 «자»로만 쓴다")
    judge["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(hitbox["n"])

    res = collections.OrderedDict([
        ("무엇", "991 §1 — 🔴🔴🔴 **순서를 고르는 것이 곧 답을 고르는 것이다**"),
        ("🔴 축", "C3 (mixture) × C6 (scaling) × C2 (도메인 가중)"),
        ("사전등록", "docs/prereg_991_order_rulers.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", world_stamp()),
        ("🔴 자", collections.OrderedDict([
            ("겹", "개체 묶음 %d겹 OOF" % KFOLD),
            ("상관", "도메인별 유보 스피어만(동률 평균)"),
            ("🔴 판정 자", RULER_JUDGE), ("🔴 병기 자", list(RULER_ALT)),
            ("씨앗", SEEDS), ("게이트 도메인", doms),
            ("게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in doms))),
            ("🔴 네 칸", list(CELLS)),
            ("🔴 판정 예산", N_JUDGE),
            ("🔴🔴🔴 `N_ALL`(계산)", int(NA)),
            ("🔴 탐색 격자(사전등록 «안»)", EXPLORE_BASE),
            ("🔴 잰 칸 수", ncell), ("🔴 탐색 칸 수", nexp),
        ])),
        ("§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)", order),
        ("§2 🔴🔴🔴 탐색 격자 — 🔴 **사전등록 «안»** · `base=1800` 은 «없다**", explore),
        ("§3 🔴🔴 깨끗한 천장 대조 — base 천장 고정 · hplt 만 흔든다", ceil_out),
        ("§4 🔴🔴 즉시정정 — 「전량」 눈금을 손 리터럴에서 뗐다", fix),
        ("§5 🔴🔴🔴 판정", judge),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", int(hitbox["n"])),
        ("통과", bool(
            # 🔴 세 자 × 두 순서 × 두 성분 열둘이 «전부» 기록됐나(`F03`)
            all(nm in order[str(U_REG)][rn]["🔴 성분"]
                for rn in RN for nm in COMP)
            # 🔴 상호작용과 대칭 배분이 «전부» 있나(사전등록 반증조건 1)
            and all("상호작용 A′ − A" in order[str(u)][rn]["🔴 성분"]
                    for u, _l in lams for rn in RN)
            # 🔴 탐색 격자에 판정 칸이 «없나»(사전등록 반증조건 2)
            and not explore["🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"]
            # 🔴 「전량」 눈금의 hplt 부족이 0 인가(§1-7)
            and fix["🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대"] == 0)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 자 셋 × 두 순서 × 두 성분 «열둘»과 상호작용·대칭 배분이 전부 기록됐고, "
         "탐색 격자에 판정 칸이 «없고», 「전량」 눈금이 hplt 를 «다 채웠다»"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("wiring", "order"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    fn = {"wiring": stage_wiring, "order": stage_order}[a.stage]
    _prog("시작 %s" % a.stage)
    res = fn(a.ref)
    p = OUT / ("out991_wiring.json" if a.stage == "wiring" else "out991_order.json")
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("끝 %s → %s" % (a.stage, p.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
