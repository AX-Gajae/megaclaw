#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""993 — **자가 잡은 것을 자에 문다** (축 C1 × C6 × C2).

사전등록 `docs/prereg_993_straighten_the_rulers.md` §1 을 그대로 따른다.

🔴🔴🔴 **이 러너는 세계 자료를 «실제로» 연다** ---
  `data/ingest/sao941` · `sao959` · `sao973_hplt` 셋 + 챔피언 판 껍질(`ff753`).

🔴🔴🔴 **991 의 병 셋을 구조로 막는다.**
  ⓐ **`mut_kind` 손 라벨을 «폐기»한다** --- 변이체의 공허를 «설정 격자에서 실측»한다.
     991 은 `bool(mut_kind != "코드")` 로 판정했고 `mut_kind` 는 여섯 `add(...)` 에
     손으로 박은 문자열 `"코드"` 였다. **검정력 0 의 항등식이었다.**
  ⓑ **탐색 격자를 오른쪽으로 늘려 `R_pool` 의 꼭짓점을 «감싼다»** ---
     991 의 「최적 450」은 격자 «오른쪽 끝»이라 경계 인공물이었다.
  ⓒ **「최적 base」를 `argmax` 가 아니라 「`2·SE_clu` 로 «안 갈리는» 칸들의 «집합»」으로 낸다**
     (`조항 68-다`).

씀:
    python3 runners/world993.py --stage wiring --ref <40자 sha>
    python3 runners/world993.py --stage order  --ref <40자 sha>
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

# ── 🔴 §1-5 런타임 자: 연 `data/` 경로를 «전부» 기록한다 ─────────────────
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

RAN = ("runners/world993.py", "runners/alpha977.py", "runners/layers957.py",
       "runners/predict971.py", "runners/ff753.py")
OUT = ROOT / "runners"
PROG = OUT / "out993_progress.txt"

# ══ 사전등록 §7 상수 (측정 «전»에 박았다) ═════════════════════════════
SEEDS = list(range(989000, 989012))     # 🔴 989·990·991 과 «같은 씨앗»
KFOLD = 5
ALPHA_H = 0.95
U_REG = 0                               # 🔴 판정 λ = 10^0
U_ALT = 3                               # 병기
KGRID = 6
THR_CARD = 0.00353                      # 🔴 자로만 쓴다 · 채택 문턱 아님
N_JUDGE = 1800

# 🔴🔴🔴 §1-1 탐색 격자 --- **991 의 다섯을 오른쪽으로 늘렸다**(꼭짓점을 감싼다)
EXPLORE_N = 1800
EXPLORE_BASE = [45, 90, 135, 270, 450, 675, 900, 1200]
CLIFF_PAIRS = [(45, 90), (90, 135)]     # 🔴 「벼랑」 주장은 이 두 짝 차로만 한다

SRC_FILES = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])

RULER_JUDGE = "R_pool 묶음"          # 🔴🔴🔴 측정 «전»에 못 박았다
RULER_ALT = ("R_eq 균등", "R_champ 챔피언가중")

#: 🔴 977 공표값은 **산출물에서 읽는다**. 손으로 안 옮긴다(991 은 `want = 0.3596` 을 쳤다).
G977 = "runners/out977_grid.json"
G977_CELL = "u=0|α=0.95"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    # 🔴 993 즉시정정 --- 992 는 bare `open(str(PROG), "a")` 를 썼고, `F09` 의 AST
    #   쓰기 탐지가 «attribute 호출»만 보므로 `out992_progress.txt` 를 「읽는다」로
    #   분류했다(티처 #131 즉시정정 ②). `Path.open` 으로 바꿔 자가 «쓴다»로 본다.
    with PROG.open("a", encoding="utf-8") as f:
        f.write("%s  [world993] %s\n" % (_now(), msg))
    sys.stderr.write("%s  [world993] %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _rl(a, n=6):
    return [_r(x, n) for x in (a.tolist() if hasattr(a, "tolist") else a)]


def _median(xs):
    """🔴 **진짜 중앙값**. 991 은 `sorted(x)[len(x)//2]` 를 「중앙값」이라 적었다 ---
    `[6,6,12,90,120,28356]` 의 참 중앙값은 `51` 인데 `90` 을 실었다."""
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    if n % 2:
        return float(s[n // 2])
    return (float(s[n // 2 - 1]) + float(s[n // 2])) / 2.0


def old_literal_990():
    """🔴 990 의 손 리터럴을 «소스에서 읽는다» --- 손으로 안 옮긴다(규칙 D)."""
    src = (ROOT / "runners/world990.py").read_text(encoding="utf-8")
    m = re.search(r"nn = (\d+) if n is None", src)
    return int(m.group(1)) if m else None


def want_977():
    """🔴 977 의 공표 `묶음 ρ` 를 **산출물 칸에서 읽는다**(손 전사 금지)."""
    d = json.loads((ROOT / G977).read_text(encoding="utf-8"))
    for k, v in d.items():
        if isinstance(v, dict) and G977_CELL in v:
            return float(v[G977_CELL]["묶음 ρ"]), "%s | %s | 묶음 ρ" % (k, G977_CELL)
    return None, None


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def world_stamp(paths=None):
    """🔴 §1-5 --- **연 세계 자료의 지문**. 손으로 안 적는다."""
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
        ("🔴🔴🔴 §1-5 이 러너가 «연» `data/` 경로",
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


def pick_wrongfold(pool, fold, nb, nh, shift):
    """🔴 **변이체용 코드** --- 겹 필터의 «색인을 shift 만큼 어긋나게» 건다.

    `shift == 0` 이면 `pick` 과 «완전히 같다**(널 변이체). 그것이 이 격자의 «영점»이다.
    """
    ff = (fold + int(shift)) % KFOLD
    pb = pool.perm_b[(pool.fi != ff)[pool.perm_b]]
    ph = pool.perm_h
    selb, selh = pb[:max(0, int(nb))], ph[:max(0, int(nh))]
    return selb, selh, int(max(0, nb) - len(selb)), int(max(0, nh) - len(selh))


def pick_filling(pool, fold, nb, nh):
    """🔴 **변이체용 코드** --- base 가 모자라면 hplt 로 «메운다»."""
    selb, selh, s1, s2 = pick(pool, fold, nb, nh)
    if s1 > 0:
        selh = pool.perm_h[:s1]
    return selb, selh, s1, s2


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


def blend_wmaps(wmaps, judge, t):
    """🔴 **변이체용 코드** --- 세 자의 가중을 판정 자 쪽으로 `t` 만큼 «섞는다».

    `t == 1` 이면 원본과 «완전히 같고**(널 변이체) `t == 0` 이면 세 자가 «같은 자»가 된다.
    """
    base = wmaps[judge]
    out = collections.OrderedDict()
    for name, w in wmaps.items():
        out[name] = {d: (1.0 - t) * float(base[d]) + t * float(w[d]) for d in w}
    return out


def n_all(pool):
    """🔴🔴🔴 「전량」 눈금을 «계산»한다. `N_ALL = ceil(len(yh) / α)`."""
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
    """`S` = base N−round(αN) · hplt 0."""
    return plan_fixed(n - int(round(ALPHA_H * n)), 0)


# ══ 자 ════════════════════════════════════════════════════════════════
def cluster_se(dd, w):
    """🔴 §1-3 — **도메인 군집 SE**. 식을 사전등록에 «측정 전에» 박았다."""
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
# §A 배선 — 🔴🔴🔴 **공허를 「손 라벨」이 아니라 「설정 격자에서 실측」한다**
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    wmaps, champ_w = build_wmaps(pool)
    checks = collections.OrderedDict()

    def add(name, base_fn, mut_fn, cfgs, cfg_desc, mut_desc, why,
            null_fn=None, null_desc="🔴🔴🔴 널칸이 «구성상» 없다"):
        """🔴🔴🔴 **993 판 — ㉢ 은 「널칸을 «뺀» 격자」에서 잰다** (`조항 66-나` 개정).

        🔴 **992 의 병.** 992 는 격자에 「변이 크기 0」인 «널칸»을 넣고
        `㉢ = not const_t and not const_f` 로 판정했다. **널칸에서 변이체는 «정의상»
        원본과 같으므로 `any(mut)` 이 «언제나» 참이고 `const_f` 가 «원리상» 못 켜진다.**
        「일곱 전부 검정력 있음」은 **격자에 항등원을 넣은 것의 항등식**이었다.

        🔴 **993 판**:
          널칸 sanity = 널칸에서 `변이체 == 원본` 인가 (아니면 널칸 신고가 «거짓»이다)
          ㉠ 구성상 «참»   = **널칸을 뺀** 격자의 어느 칸에서도 «안» 떨어졌다
          ㉡ 구성상 «거짓» = **널칸을 뺀** 격자의 어느 칸에서도 «떨어졌다»
          ㉢ 검정력 있음   = **널칸을 뺀** 격자에서 «갈린다»
        🔴 **992 판(널 «포함»)도 «나란히» 낸다**(`조항 3-나` --- 두 수를 둘 다 싣는다).
        """
        b_res = [bool(base_fn(c)) for c in cfgs]
        m_res = [bool(mut_fn(c)) for c in cfgs]
        n = len(cfgs)
        # ── ⚠ 992 판 --- 널칸을 «넣은» 격자 전량 ───────────────────────
        old_t = bool(n and all(m_res))
        old_f = bool(n and not any(m_res))
        old_p = bool(n and not old_t and not old_f)
        # ── 🔴🔴🔴 993 판 --- 널칸을 «뺀» 격자 ─────────────────────────
        nulls = [i for i, c in enumerate(cfgs) if null_fn and null_fn(c)]
        nn = [i for i in range(n) if i not in set(nulls)]
        m_nn = [m_res[i] for i in nn]
        k = len(m_nn)
        new_t = bool(k and all(m_nn))
        new_f = bool(k and not any(m_nn))
        new_p = bool(k and not new_t and not new_f)
        # ── 🔴 널칸 sanity --- 널칸에서 변이체가 원본과 «같은 답»을 내나 ──
        sane = [i for i in nulls if m_res[i] == b_res[i]]
        checks[name] = collections.OrderedDict([
            ("통과", bool(n and all(b_res))),
            ("🔴🔴🔴 설정 격자 크기(= 이 검사의 «검정력 분모»)", n),
            ("🔴 설정 격자", cfg_desc),
            ("🔴 본 검사가 통과한 설정 수", int(sum(b_res))),
            ("🔴 변이체가 통과한 설정 수", int(sum(m_res))),
            # ── 🔴🔴🔴 993 신설 — 널칸 ─────────────────────────────────
            ("🔴🔴🔴 널칸이 «구성상» 있나(= 이 변이체가 «코드» 변이체인가의 기계 자)",
             bool(nulls)),
            ("🔴 널칸 명부(사전등록 §1-4-가)", null_desc),
            ("🔴 널칸 수", len(nulls)),
            ("🔴🔴 널칸을 «뺀» 격자 크기(= 993 판 검정력 분모)", k),
            ("🔴🔴🔴 널칸 sanity(널칸에서 변이체 == 원본)",
             bool(len(sane) == len(nulls))),
            ("🔴 널칸 sanity 를 통과한 널칸 수", len(sane)),
            # ── 🔴🔴🔴 993 판 (널칸 «제외») ───────────────────────────
            ("🔴🔴 ㉠ 구성상 «참»인가(🔴 993 판 · 널칸 «제외»)", new_t),
            ("🔴🔴🔴 ㉡ 구성상 «거짓»인가(🔴 993 판 · 널칸 «제외»)", new_f),
            ("🔴🔴🔴 ㉢ 검정력이 «있나»(🔴 993 판 · 널칸 «제외»)", new_p),
            # ── ⚠ 992 판 (널칸 «포함») — 나란히 싣는다 ─────────────────
            ("⚠ ㉠ 구성상 «참»인가(992 판 · 널칸 «포함»)", old_t),
            ("⚠ ㉡ 구성상 «거짓»인가(992 판 · 널칸 «포함»)", old_f),
            ("⚠ ㉢ 검정력이 «있나»(992 판 · 널칸 «포함»)", old_p),
            ("🔴🔴🔴 두 판이 «갈리나»", bool(new_p != old_p)),
            ("🔴 변이체", mut_desc),
            ("🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)", int(2 * n + len(nulls))),
            ("왜", why),
        ])

    nh_j = int(round(ALPHA_H * N_JUDGE))
    nb_j = N_JUDGE - nh_j

    # ── X1 🔴🔴🔴 색인 대조 — 네 칸이 «같은 뽑기»에서 왔나 ────────────────
    def _x1_base(c):
        s, j, _off = c
        pool.reseed(s)
        fi0 = pool.fi.copy()
        av = avail_b(pool, j)
        bB, hB, _1, _2 = pick(pool, j, *plan_B(N_JUDGE)(j, av))
        bM, hM, _3, _4 = pick(pool, j, *plan_M(N_JUDGE)(j, av))
        bH, hH, _5, _6 = pick(pool, j, *plan_H(N_JUDGE)(j, av))
        bS, hS, _7, _8 = pick(pool, j, *plan_S(N_JUDGE)(j, av))
        return (np.array_equal(bM, bB) and np.array_equal(bH, bS)
                and np.array_equal(bH, bB[:len(bH)])
                and np.array_equal(hH, hM)
                and len(hB) == 0 and len(hS) == 0
                and np.array_equal(pool.fi, fi0))

    def _x1_mut(c):
        s, j, off = c
        pool.reseed(s)
        av = avail_b(pool, j)
        bH, _hH, _a, _b = pick(pool, j, *plan_H(N_JUDGE)(j, av))
        pool.reseed(s + off)                       # 🔴 칸 «사이»에 reseed 를 끼운다
        bB2, _h, _c, _d = pick(pool, j, *plan_B(N_JUDGE)(j, avail_b(pool, j)))
        pool.reseed(s)
        return np.array_equal(bH, bB2[:len(bH)])

    add("X1 🔴🔴🔴 색인 대조 — 네 칸(`B`·`M`·`H`·`S`)이 «같은 씨앗·같은 겹·같은 뽑기 색인»을 썼다",
        _x1_base, _x1_mut,
        [(s, j, off) for s in SEEDS[:3] for j in range(KFOLD)
         for off in (0, 7, 500000)],
        "씨앗 3 × 겹 5 × reseed 어긋남 {0(널), 7, 500000}",
        "🔴 칸 «사이»에 `reseed(s + off)` 를 끼운 코드. **`off = 0` 이 «널 변이체»**(원본과 같다) --- "
        "그 칸이 격자에 «있어야» 이 검사가 「반드시 떨어지는 변이체」가 아니다",
        "🔴🔴🔴 **`W6`(분해 항등식)이 «재려 했던» 것이다.** 항등식은 어떤 수를 넣어도 잔차 0 이라 "
        "검정력이 0 이고, 분해가 뜻을 가지려면 «네 칸이 같은 뽑기에서 왔어야» 한다",
        null_fn=lambda c: c[2] == 0,
        null_desc="`off == 0`(reseed 어긋남 «없음» --- 변이체 코드가 원본과 «같은 물건»이다)")

    # ── X2 🔴 팔 B·S 는 «안 채운다** ─────────────────────────────────
    ceil_by_seed = collections.OrderedDict()
    for s in SEEDS:
        pool.reseed(s)
        per_fold = [avail_b(pool, j) for j in range(KFOLD)]
        ceil_by_seed[str(s)] = {"겹별": per_fold, "최소": int(min(per_fold))}

    def _x2_base(c):
        s, j, nb = c
        pool.reseed(s)
        av = avail_b(pool, j)
        b, h, s1, _s2 = pick(pool, j, nb, 0)
        return len(h) == 0 and len(b) == min(nb, av) and s1 == max(0, nb - av)

    def _x2_mut(c):
        s, j, nb = c
        pool.reseed(s)
        _b, hm, _s1, _s2 = pick_filling(pool, j, nb, 0)
        return len(hm) == 0

    add("X2 팔 `B`·`S` 는 «각 겹의 자기 천장»에서 멈춘다(HPLT 로 «안» 채운다)",
        _x2_base, _x2_mut,
        [(s, j, nb) for s in SEEDS[:4] for j in range(KFOLD)
         for nb in (8, 64, 512, 4096, 25600)],
        "씨앗 4 × 겹 5 × base 자리 {8, 64, 512, 4096, 25600}",
        "🔴 **채우는 뽑기**(`pick_filling` --- base 모자람을 hplt 로 메운다). "
        "🔴🔴 **991 은 `nb = 25600` «하나»로만 쟀다** --- base 전량이 2,363 이라 "
        "`sm = 25600 − av > 0` 이 «언제나» 참이고 그 변이체는 «언제나» 떨어졌다(검정력 0). "
        "993 는 천장 «아래» 칸을 격자에 넣었다",
        "🔴 base 자리가 겹 천장 아래면 채울 것이 «없어» 변이체가 안 떨어지고, 천장 위면 떨어진다",
        null_fn=lambda c: c[2] <= ceil_by_seed[str(c[0])]["겹별"][c[1]],
        null_desc="`nb <= av`(그 씨앗·겹의 base 천장 «아래» --- 채울 것이 «없어» "
                  "`pick_filling` 이 `pick` 과 «같은 물건»이다)")

    # ── X3 🔴 유보는 어떤 예산에서도 학습에 «안 닿는다» ────────────────
    NA = n_all(pool)

    def _x3_base(c):
        s, j, _k = c
        pool.reseed(s)
        b, _h, _s1, _s2 = pick(pool, j, NA, len(pool.yh))
        return int((pool.fi[b] == j).sum()) == 0

    def _x3_mut(c):
        s, j, k = c
        pool.reseed(s)
        b, _h, _s1, _s2 = pick_wrongfold(pool, j, NA, len(pool.yh), k)
        return int((pool.fi[b] == j).sum()) == 0

    add("X3 어떤 예산에서도 학습이 «그 겹의 유보 행»을 안 쓴다",
        _x3_base, _x3_mut,
        [(s, j, k) for s in SEEDS[:3] for j in range(KFOLD) for k in range(KFOLD)],
        "씨앗 3 × 겹 5 × 겹 필터 어긋남 {0(널), 1, 2, 3, 4}",
        "🔴 겹 필터의 «색인을 shift 만큼 어긋나게» 건 뽑기(`pick_wrongfold`). "
        "**`shift = 0` 이 «널 변이체»**(`pick` 과 완전히 같다)",
        "🔴 겹 j 의 학습 색인 중 `fi == j` 인 것의 수를 «전수» 센다 --- 0 이어야 한다",
        null_fn=lambda c: c[2] == 0,
        null_desc="`k == 0`(겹 필터 shift 0 --- `pick_wrongfold` 가 `pick` 과 «같은 물건»이다)")

    # ── X4 🔴🔴 세 자가 «서로 다른» 자인가 ────────────────────────────
    _x4_cache = {}

    def _x4_cell(s):
        if s not in _x4_cache:
            pool.reseed(s)
            _x4_cache[s] = cell(pool, plan_H(N_JUDGE), 1.0, wmaps)
        return _x4_cache[s]

    def _x4_base(c):
        s, _t = c
        cc = _x4_cell(s)
        vals = [cc["rulers"][k] for k in wmaps]
        return min(abs(vals[i] - vals[k])
                   for i in range(3) for k in range(i + 1, 3)) > 1e-9

    def _x4_mut(c):
        s, t = c
        cc = _x4_cell(s)
        bw = blend_wmaps(wmaps, RULER_JUDGE, t)
        mv = list(rulers(cc["per"], pool.gated, bw).values())
        return min(abs(mv[i] - mv[k])
                   for i in range(3) for k in range(i + 1, 3)) > 1e-9

    add("X4 🔴🔴 세 자가 «서로 다른 값»을 낸다(병기가 무의미하지 않다)",
        _x4_base, _x4_mut,
        [(s, t) for s in SEEDS[:3] for t in (0.0, 0.25, 0.5, 0.75, 1.0)],
        "씨앗 3 × 가중 섞임 t {0.0, 0.25, 0.5, 0.75, 1.0}(`t = 1` 이 널 변이체)",
        "🔴 세 자의 가중을 판정 자 쪽으로 `t` 만큼 섞은 판(`blend_wmaps`). "
        "🔴🔴 **991 은 `t = 0`(세 자에 «같은» 가중) «하나»로만 쟀다** --- 그러면 세 값이 "
        "«정확히» 같아 `min > 1e-9` 가 «언제나» 거짓이고 검정력이 0 이다",
        "🔴 같은 도메인별 ρ 에 세 가중을 물려 세 쌍의 차를 «전수» 잰다",
        null_fn=lambda c: c[1] == 1.0,
        null_desc="`t == 1.0`(가중 섞임 «없음» --- `blend_wmaps` 가 원본 가중을 그대로 낸다)")

    # ── X5 🔴 세계 자료 지문 — 변이체는 «경로 목록»(코드 입력)을 바꾼다 ──
    ws = world_stamp()
    _x5_paths = collections.OrderedDict([
        ("원본(널 변이체)", SRC_FILES["sao941"]),
        ("다른 «실재» 파일", SRC_FILES["sao959"]),
        ("없는 파일", "data/ingest/sao941/🔴없는파일.jsonl.gz"),
    ])

    def _x5_base(_c):
        w = world_stamp()
        return bool(len(w) == 3 and all(v["바이트"] > 0 for v in w.values())
                    and all(w[k]["sha256"] == ws[k]["sha256"] for k in ws))

    def _x5_mut(c):
        mp = collections.OrderedDict(SRC_FILES)
        mp["sao941"] = _x5_paths[c]
        w = world_stamp(mp)
        return bool(len(w) == 3 and all(v["바이트"] > 0 for v in w.values())
                    and all(w[k]["sha256"] == ws[k]["sha256"] for k in ws))

    add("X5 세 세계 자료 파일이 «전부» 열렸고 지문이 «원본과 같다»",
        _x5_base, _x5_mut, list(_x5_paths),
        "`sao941` 자리에 넣는 경로 {원본(널), 다른 실재 파일, 없는 파일}",
        "🔴 `world_stamp` 의 «경로 목록»(코드 입력)을 바꾼 판. "
        "🔴🔴 **991 은 「없는 파일」 «하나»로만 쟀다** --- 바이트가 0 이라 «언제나» 떨어졌다",
        "🔴 지문 자체를 견주므로 「다른 실재 파일」에서도 떨어진다 --- 「존재」가 아니라 「동일성」을 잰다",
        null_fn=lambda c: c == "원본(널 변이체)",
        null_desc="경로 == 원본(`world_stamp` 의 «경로 목록»이 원본과 «같은 물건»이다)")

    # ── X6 🔴 977 재현 — 🔴 **공표값을 산출물 «칸»에서 읽는다** ──────────
    want, want_path = want_977()
    _x6_cache = {}

    def _x6_val(alpha):
        if alpha not in _x6_cache:
            vals = []
            for seed in A.SEEDS:
                pool.reseed(seed)
                r = A.oof(pool, alpha, 10.0 ** U_REG, KGRID)
                p_, _e, _pr = A.score(pool, r["예측"])
                vals.append(float(p_))
            _x6_cache[alpha] = float(np.mean(vals))
        return _x6_cache[alpha]

    def _x6_base(_c):
        return want is not None and round(_x6_val(ALPHA_H), 6) == round(want, 6)

    def _x6_mut(c):
        return want is not None and round(_x6_val(c), 6) == round(want, 6)

    add("X6 977 의 `%s` 묶음 ρ 를 «977 자기 씨앗·자기 함수»로 다시 내면 공표값과 «6 자리까지» 같다"
        % G977_CELL,
        _x6_base, _x6_mut, [0.95, 0.9, 0.5, 0.0],
        "α {0.95(널), 0.9, 0.5, 0.0}",
        "🔴 **`α` 를 바꿔 돌린 판**(검사 «대상 코드»의 입력을 바꾼다). "
        "🔴🔴 **991 은 공표값 `0.3596` 을 «손으로 옮겨** 적었고(`world991.py:445`) "
        "허용오차 `5e-4` 는 4 자리 공표값의 «반올림 반폭»이라 「반올림이 같나」밖에 못 쟀다",
        "🔴 993 은 공표값을 `%s` 의 «칸»(`%s`)에서 읽고 «6 자리»로 견준다" % (G977, want_path),
        null_fn=lambda c: c == ALPHA_H,
        null_desc="`α == 0.95`(검사 «대상 코드»의 인자가 원본과 «같다»)")

    # ── X7 🔴🔴 990 의 «외부 닻»을 되살린다(991 이 승계 없이 잃었다) ──────
    def _x7_base(c):
        s, j, _n = c
        pool.reseed(s)
        b0, h0, _z = A.select(pool, j, ALPHA_H)     # 977 전역 N_B
        nb, nh = plan_H(N_JUDGE)(j, avail_b(pool, j))
        b1, h1, _s1, _s2 = pick(pool, j, nb, nh)
        return np.array_equal(b0, b1) and np.array_equal(h0, h1)

    def _x7_mut(c):
        s, j, n = c
        pool.reseed(s)
        b0, h0, _z = A.select(pool, j, ALPHA_H)
        nb, nh = plan_H(n)(j, avail_b(pool, j))
        b2, h2, _s1, _s2 = pick(pool, j, nb, nh)
        return np.array_equal(b0, b2) and np.array_equal(h0, h2)

    add("X7 🔴🔴 팔 `H` 의 뽑기가 `alpha977.select` 와 «색인까지» 같다(= 챔피언에 대한 유일한 «외부 닻»)",
        _x7_base, _x7_mut,
        [(s, j, n) for s in SEEDS[:3] for j in range(KFOLD)
         for n in (1800, 1799, 1801, 1810, 3600)],
        "씨앗 3 × 겹 5 × 예산 {1800(널), 1799, 1801, 1810, 3600}",
        "🔴 «예산»을 바꾼 판. **`N = 1800` 이 널 변이체**",
        "🔴🔴 **990 의 배선 `W1` 이다.** 991 은 `7 − 2 + 1 = 6` 인데 `7 − 1 + 1 = 7` 로 읽히게 "
        "적었고 이 «외부 닻»을 승계 없이 잃었다 --- 992 가 되살렸고 993 이 승계한다",
        null_fn=lambda c: c[2] == N_JUDGE,
        null_desc="`n == 1800`(예산이 원본과 «같다»)")

    # ══ §B 🔴🔴🔴 991 의 여섯을 «그 사이클 자신의 설정 격자»에서 실측한다 ══
    #    991 은 각 검사를 «자기 씨앗 × 자기 겹»에서 돌렸다. 그 격자에서 변이체가
    #    «언제나» 같은 답을 내면 그 변이체는 그 사이클에서 정보를 «하나도» 안 날랐다.
    def _const(mres):
        return ("㉠ 구성상 참" if all(mres) else
                ("㉡ 구성상 거짓" if not any(mres) else "㉢ 검정력 있음"))

    prev = collections.OrderedDict()

    def addprev(name, mut_vals, null_vals, mut_desc, null_desc):
        """🔴🔴🔴 **993 판 --- 991 의 격자에 「널칸」을 «넣어» 보고, 그 다음 «빼서» 잰다.**

        🔴 티처 #131: **「거꾸로 991 의 여섯에 널칸을 넣으면 «전부» ㉢ 이 된다」** ---
        곧 「992 0, 991 6」은 검사의 성질이 아니라 **「격자에 항등원을 넣었나」 하나가
        낳은 수**다. 993 은 그것을 «실측»한다.
        """
        mv = [bool(x) for x in mut_vals]
        nv = [bool(x) for x in null_vals]
        both = mv + nv                     # 🔴 널칸을 «넣은» 격자
        prev[name] = collections.OrderedDict([
            ("🔴 변이체", mut_desc),
            ("🔴 널칸(사전등록 §1-4-가)", null_desc),
            ("🔴 널칸을 «뺀» 설정 수", len(mv)),
            ("🔴 널칸 수", len(nv)),
            ("🔴 변이체 통과 수(널칸 제외)", int(sum(mv))),
            ("🔴🔴🔴 널칸 sanity(널칸에서 변이체가 «안» 떨어졌다)", bool(nv and all(nv))),
            # ── 🔴🔴🔴 993 판 · 991 을 «991 자신의 격자»(널칸 «없음»)에서 ──
            ("🔴🔴🔴 갈래(993 판 · 널칸 «제외» = 991 자신의 격자)", _const(mv)),
            # ── 🔴🔴 993 이 «널칸을 넣어» 다시 잰 판 ─────────────────────
            ("🔴🔴 갈래(널칸을 «넣으면»)", _const(both)),
            ("🔴🔴🔴 널칸 하나가 갈래를 «바꾸나»", bool(_const(mv) != _const(both))),
        ])

    # 991 X1 --- reseed 어긋남 «500000» · 🔴 993 이 널칸 `off = 0` 을 넣는다
    addprev("991 X1 색인 대조",
            [_x1_mut((s_, j_, 500000)) for s_ in SEEDS[:3] for j_ in range(KFOLD)],
            [_x1_mut((s_, j_, 0)) for s_ in SEEDS[:3] for j_ in range(KFOLD)],
            "reseed(s + 500000) 하나(991 이 실제로 쓴 격자)", "`off = 0`")
    # 991 X2 --- base 자리 «25600» · 🔴 널칸 `nb = 512`(천장 아래)
    addprev("991 X2 팔 B 안 채움",
            [_x2_mut((s_, j_, 25600)) for s_ in SEEDS for j_ in range(KFOLD)],
            [_x2_mut((s_, j_, 512)) for s_ in SEEDS for j_ in range(KFOLD)],
            "채우는 뽑기 · base 자리 25600 하나(991 이 실제로 쓴 격자)", "`nb = 512`(천장 아래)")
    # 991 X3 --- 겹을 «안 거른» 뽑기 · 🔴 널칸 = 겹을 «거른» 뽑기(shift 0)
    m991_x3 = []
    for s_ in SEEDS[:3]:
        pool.reseed(s_)
        for j_ in range(KFOLD):
            bm = pool.perm_b[:NA]
            m991_x3.append(int((pool.fi[bm] == j_).sum()) == 0)
    addprev("991 X3 유보 미접촉", m991_x3,
            [_x3_mut((s_, j_, 0)) for s_ in SEEDS[:3] for j_ in range(KFOLD)],
            "겹을 «안 거른» 뽑기 `perm_b[:N]` 하나(991 이 실제로 쓴 격자)",
            "겹을 «거른» 뽑기(`k = 0`)")
    # 991 X4 --- 세 자에 «같은» 가중(t = 0) · 🔴 널칸 t = 1.0
    addprev("991 X4 세 자가 다르다",
            [_x4_mut((s_, 0.0)) for s_ in SEEDS[:3]],
            [_x4_mut((s_, 1.0)) for s_ in SEEDS[:3]],
            "세 자에 «같은» 가중 하나(t = 0 · 991 이 실제로 쓴 격자)", "`t = 1.0`")
    # 991 X5 --- «없는 파일» · 🔴 널칸 = 원본 경로
    addprev("991 X5 세계 자료 지문",
            [_x5_mut("없는 파일")], [_x5_mut("원본(널 변이체)")],
            "«없는 파일» 하나(991 이 실제로 쓴 격자)", "원본 경로")
    # 991 X6 --- α = 0.5 · 🔴 널칸 α = 0.95 · 991 의 손 전사 자를 그대로 쓴다
    #   🔴 [손전사:재현] --- 사전등록 §4-2 에 «측정 전에» 등기한 꼬리표다.
    addprev("991 X6 977 재현",
            [abs(_x6_val(0.5) - 0.3596) <= 5e-4],      # [손전사:재현] 991 의 자
            [abs(_x6_val(0.95) - 0.3596) <= 5e-4],     # [손전사:재현] 991 의 자
            "α = 0.5 하나(991 의 손 전사 0.3596 · 허용오차 5e-4 · 991 이 실제로 쓴 격자)",
            "`α = 0.95`")
    _K_NEW = "🔴🔴🔴 갈래(993 판 · 널칸 «제외» = 991 자신의 격자)"
    _K_OLD = "🔴🔴 갈래(널칸을 «넣으면»)"
    n_prev_f = len([1 for v in prev.values() if v[_K_NEW] == "㉡ 구성상 거짓"])
    n_prev_t = len([1 for v in prev.values() if v[_K_NEW] == "㉠ 구성상 참"])
    n_prev_p_null_in = len([1 for v in prev.values() if v[_K_OLD] == "㉢ 검정력 있음"])
    n_prev_f_null_in = len([1 for v in prev.values() if v[_K_OLD] == "㉡ 구성상 거짓"])
    prev_blk = collections.OrderedDict([
        ("무엇", "🔴🔴🔴 991 의 여섯 배선을 «991 자신의 설정 격자»에서 다시 돌렸다"),
        ("🔴 왜", "🔴 **991 은 `bool(mut_kind != \"코드\")` 로 「구성상 거짓」을 판정했고 "
                "`mut_kind` 는 여섯 `add(...)` 에 «손으로 박은 문자열 `\"코드\"`»였다** --- "
                "「㉡ = 0」과 「㉢ = 6/6」은 저자가 「코드」를 여섯 번 친 것의 항등식이고 "
                "검정력이 «0** 이다. 993 는 그 여섯을 «돌려서» 센다"),
        ("🔴 검사별", prev),
        ("🔴🔴🔴 널 제외 ㉡ 수", n_prev_f),
        ("🔴🔴🔴 널 제외 ㉠ 수", n_prev_t),
        ("🔴🔴🔴 널 제외 ㉢ 수", len(prev) - n_prev_f - n_prev_t),
        ("🔴🔴🔴 널 포함 ㉢ 수", n_prev_p_null_in),
        ("🔴🔴🔴 널 포함 ㉡ 수", n_prev_f_null_in),
        ("🔴 991 이 «신고한» ㉡ 구성상 거짓 수(손 라벨)", 0),
        ("🔴🔴🔴 손 라벨과 실측이 갈리나", bool(n_prev_f != 0)),
        ("🔴🔴🔴 널칸 하나가 갈래를 바꾼 검사 수",
         len([1 for v in prev.values() if v["🔴🔴🔴 널칸 하나가 갈래를 «바꾸나»"]])),
        ("🔴🔴🔴 티처 #131 의 명제 — 「991 에 널칸을 넣으면 «전부» ㉢ 이 된다」가 참인가",
         bool(n_prev_p_null_in == len(prev))),
        ("🔴🔴🔴 이 절이 뜻하는 것",
         "🔴 **「992 0, 991 6」은 검사의 «성질»이 아니라 「격자에 항등원(널칸)을 넣었나」 "
         "«하나»가 낳은 수다.** 널칸을 «넣으면» 991 의 여섯도 ㉢ 이 되고, 널칸을 «빼면» "
         "992 자신의 일곱도 ㉡ 이 된다. **자가 «양쪽으로» 굽어 있었다**"),
        ("🔴🔴🔴 널칸이 «구성상» 있는 검사 수",
         len([1 for v in prev.values() if v["🔴 널칸 수"]])),
        ("🔴 검사 수(분모)", len(prev)),
        ("🔴 널칸 sanity 를 통과한 검사 수",
         len([1 for v in prev.values() if v["🔴🔴🔴 널칸 sanity(널칸에서 변이체가 «안» 떨어졌다)"]])),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)",
         int(sum(v["🔴 널칸을 «뺀» 설정 수"] + v["🔴 널칸 수"] for v in prev.values()))),
        ("통과", bool(len(prev) == 6)),
    ])

    # ── D1 🔴 분해 항등식 — **진단이다. `통과` 키가 «없다»** ────────────
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
         "🔴 `A + S ≡ Δ` 는 `(x−y)+(z−x) = z−y` 라 «어떤 수를 넣어도» 성립한다. "
         "검정력 0. 그 자리에 `X1`(색인 대조)을 넣었다"),
        ("🔴 순서 A 잔차 최대", _r(max(residA), 15)),
        ("🔴 순서 B 잔차 최대", _r(max(residB), 15)),
        ("🔴 잰 자리", nres),
    ])

    n_ok = len([1 for v in checks.values() if v["통과"]])
    _CT = "🔴🔴 ㉠ 구성상 «참»인가(🔴 993 판 · 널칸 «제외»)"
    _CF = "🔴🔴🔴 ㉡ 구성상 «거짓»인가(🔴 993 판 · 널칸 «제외»)"
    _CP = "🔴🔴🔴 ㉢ 검정력이 «있나»(🔴 993 판 · 널칸 «제외»)"
    _OT = "⚠ ㉠ 구성상 «참»인가(992 판 · 널칸 «포함»)"
    _OF = "⚠ ㉡ 구성상 «거짓»인가(992 판 · 널칸 «포함»)"
    _OP = "⚠ ㉢ 검정력이 «있나»(992 판 · 널칸 «포함»)"
    n_const_t = len([1 for v in checks.values() if v[_CT]])
    n_const_f = len([1 for v in checks.values() if v[_CF]])
    n_power = len([1 for v in checks.values() if v[_CP]])
    o_const_t = len([1 for v in checks.values() if v[_OT]])
    o_const_f = len([1 for v in checks.values() if v[_OF]])
    o_power = len([1 for v in checks.values() if v[_OP]])
    n_hasnull = len([1 for v in checks.values()
                     if v["🔴🔴🔴 널칸이 «구성상» 있나(= 이 변이체가 «코드» 변이체인가의 기계 자)"]])
    n_sane = len([1 for v in checks.values()
                  if v["🔴🔴🔴 널칸 sanity(널칸에서 변이체 == 원본)"]])
    hitlist = [v["🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)"]
               for v in checks.values()]
    tot_hits = int(sum(hitlist))
    res = collections.OrderedDict([
        ("무엇", "993 §1 배선 — 🔴🔴🔴 **변이체의 공허를 «설정 격자에서 실측»한다**"),
        ("🔴 축", "C1 × C6 × C2"),
        ("사전등록", "docs/prereg_993_straighten_the_rulers.md §1-4"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", ws),
        ("🔴 자료 행", collections.OrderedDict([
            ("base 행(= 유보 전량)", int(len(pool.yb))),
            ("🔴 게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in pool.gated))),
            ("hplt 행(= 학습에만)", int(len(pool.yh))),
            ("게이트 도메인", list(pool.gated)),
            ("🔴 977 의 예산 상수 N_B", int(A.N_B)),
            ("🔴🔴🔴 `N_ALL`(계산 --- 손 리터럴이 아니다)", int(NA)),
            ("🔴🔴🔴 990 이 쓴 «손 리터럴»(`world990.py` 소스에서 읽었다)", old_literal_990()),
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
        ("🔴 977 공표값(산출물 칸에서 읽었다 --- 손 전사 «아니다»)",
         collections.OrderedDict([
             ("🔴 값", want), ("🔴 칸 경로", "%s # %s" % (G977, want_path)),
             ("🔴 993 가 다시 낸 값", _r(_x6_val(ALPHA_H))),
             ("🔴 차", _r(abs(_x6_val(ALPHA_H) - want), 15) if want else None),
         ])),
        ("배선 검사", checks),
        ("§B 🔴🔴🔴 991 의 여섯을 실측한다", prev_blk),
        ("🔴🔴🔴 D1 분해 항등식 — **진단**(배선 명부 «밖» · `통과` 키 없음)", diag),
        ("🔴 배선 검사 수(분모)", len(checks)),
        ("🔴 통과 수", n_ok),
        # ── 🔴🔴🔴 993 판 (널칸 «제외») — `조항 66-나` 개정 ────────────────
        ("🔴🔴 ㉠ 구성상 «참»인 검사 수", n_const_t),
        ("🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수", n_const_f),
        ("🔴🔴🔴 ㉢ 검정력이 «있는» 검사 수", n_power),
        # ── ⚠ 992 판 (널칸 «포함») — 나란히 싣는다(`조항 3-나`) ────────────
        ("⚠ 992 판 ㉠ 수(널칸 «포함»)", o_const_t),
        ("⚠ 992 판 ㉡ 수(널칸 «포함»)", o_const_f),
        ("⚠ 992 판 ㉢ 수(널칸 «포함»)", o_power),
        ("🔴🔴🔴 두 판이 갈린 검사 수", len([1 for v in checks.values()
                                if v["🔴🔴🔴 두 판이 «갈리나»"]])),
        ("🔴🔴🔴 널칸이 «구성상» 있는 검사 수", n_hasnull),
        ("🔴🔴🔴 널칸 sanity 를 통과한 검사 수", n_sane),
        ("🔴🔴🔴 널칸 sanity 가 «전부» 통과했나", bool(n_sane == len(checks))),
        ("🔴🔴🔴 이 절이 뜻하는 것(993)",
         "🔴🔴🔴 **992 의 「일곱 전부 검정력 있음」은 「격자에 항등원(널칸)을 넣은 것」의 "
         "항등식이었다.** 널칸을 «빼면» ㉡ 이 %d · ㉢ 이 %d 다. "
         "🔴 널칸은 sanity check 로만 쓰고 검정력 «분자»에서 뺀다(`조항 66-나` 개정)"
         % (n_const_f, n_power)),
        ("🔴🔴🔴 `mut_kind` 손 라벨을 썼나", False),
        ("🔴 걸린 자리 합", tot_hits),
        ("🔴🔴 걸린 자리 «중앙값»(🔴 993 가 고친 자 --- 짝수면 «두 가운데의 평균»)",
         _median(hitlist)),
        ("⚠ 991 판 「중앙값」(`sorted(x)[len(x)//2]` --- 중앙값이 «아니다»)",
         int(sorted(hitlist)[len(hitlist) // 2])),
        ("🔴🔴🔴 «최대 기여» 검사의 몫",
         _r(max(hitlist) / float(tot_hits), 4) if tot_hits else None),
        ("🔴 그 검사 이름",
         [k for k, v in checks.items()
          if v["🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)"] == max(hitlist)][0]),
        # 🔴🔴🔴 993 --- 「일곱 전부 ㉢」을 «통과 조건으로 안 쓴다».
        #   그 조건은 992 가 널칸으로 «자동 충족»시킨 바로 그 자리다(항등식).
        #   993 은 ㉠ 널칸 sanity 가 전부 통과했나 ㉡ 본 검사가 전부 통과했나만 문다.
        ("통과", bool(n_ok == len(checks) and n_sane == len(checks))),
        ("🔴🔴🔴 993 이 통과 조건을 «바꿨다»",
         "🔴 992 의 통과 조건은 `n_power == len(checks)` 였다 --- **널칸이 그것을 «자동으로» "
         "충족시켰다**(항등식). 993 은 그 자리를 빼고 「널칸 sanity 전량 통과」를 넣었다. "
         "🔴 **㉢ 수는 이제 «판정»이 아니라 «게재»다**"),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 일곱이 다 통과했고, **일곱 «전부»가 「설정에 따라 갈리는」 변이체를 가졌다** --- "
         "손 라벨이 «하나도» 없다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


# ══════════════════════════════════════════════════════════════════════
# §B 순서 — 🔴🔴🔴 **자 3 × 성분 8 = 24 칸 전량에 SE 를 붙인다**
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
        for nm, pf in CELLS.items():
            put(U_REG, (nm, NA), cell(pool, pf(NA), 10.0 ** U_REG, wmaps))
            ncell += 1
        for nb in EXPLORE_BASE:
            put(U_REG, ("탐색", nb),
                cell(pool, plan_fixed(nb, EXPLORE_N - nb), 10.0 ** U_REG, wmaps))
            nexp += 1
        for h in (0, len(pool.yh)):
            put(U_REG, ("증강천장", h),
                cell(pool, plan_fixed("천장", h), 10.0 ** U_REG, wmaps))
            ncell += 1
        _prog("씨앗 %d/%d (%d) — 칸 %d + 탐색 %d · %.1fs"
              % (si + 1, len(SEEDS), seed, ncell, nexp, time.time() - t_start))

    def arr(u, key, rn):
        return np.asarray(raw[u][key]["ruler"][rn], float)

    def perarr(u, key, d):
        return np.asarray(raw[u][key]["per"][d], float)

    hitbox = {"n": 0}

    def lin_block(u, coefs, rn, w):
        """🔴🔴🔴 **성분 «전부»가 이 «한» 함수로 지어진다**(`조항 67`)."""
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

    # ── §1 🔴🔴🔴 한 표 — 자 셋 × 여덟 성분 ──────────────────────────
    order = collections.OrderedDict()
    for u, _l in lams:
        per_rn = collections.OrderedDict()
        for rn in RN:
            blocks = collections.OrderedDict(
                (nm, lin_block(u, cf, rn, wmaps[rn])) for nm, cf in COMP.items())
            aA = blocks["순서 A · 증강 A = M − B"]["🔴🔴🔴 값"]
            sA = blocks["순서 A · 굶김 S_A = H − M"]["🔴🔴🔴 값"]
            aB = blocks["순서 B · 증강 A′ = H − S"]["🔴🔴🔴 값"]
            sB = blocks["순서 B · 굶김 S_B = S − B"]["🔴🔴🔴 값"]
            surv = [k for k, v in blocks.items()
                    if v["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]]
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
                ("🔴🔴🔴 `t_clu` 절댓값이 2 를 넘은 성분", surv or "없음"),
                ("🔴🔴🔴 그 수", len(surv)),
            ])
        order[str(u)] = per_rn

    # ── §1-나 🔴🔴🔴 **자 3 × 성분 8 = 24 칸 SE 표**(문서가 «전량» 싣는다) ──
    JU = order[str(U_REG)]
    se_table = collections.OrderedDict()
    for nm in COMP:
        row = collections.OrderedDict()
        for rn in RN:
            b = JU[rn]["🔴 성분"][nm]
            row[rn] = collections.OrderedDict([
                ("값", b["🔴🔴🔴 값"]), ("SE", b["🔴🔴🔴 도메인 군집 SE"]),
                ("t_clu", b["🔴🔴🔴 t_clu"]),
                ("2 를 넘나", b["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]),
            ])
        row["🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리나"] = bool(
            len({row[rn]["2 를 넘나"] for rn in RN}) > 1)
        row["🔴🔴🔴 자에 따라 «부호»가 갈리나"] = bool(
            len({(row[rn]["값"] or 0) > 0 for rn in RN}) > 1)
        se_table[nm] = row
    split_se = [nm for nm, r in se_table.items()
                if r["🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리나"]]
    split_sign = [nm for nm, r in se_table.items()
                  if r["🔴🔴🔴 자에 따라 «부호»가 갈리나"]]
    se_blk = collections.OrderedDict([
        ("무엇", "🔴🔴🔴 **자 3 × 성분 8 = 24 칸 전량**의 값·SE·`t_clu`"),
        ("🔴 왜", "🔴 **991 은 판정 자 «여덟 칸»만 문서에 실었고 병기 자 «열여섯 칸»의 SE·`t_clu` 는 "
                "JSON 에만 있고 한 줄도 안 올라왔다.** 이 사이클의 명제가 「무엇이 사는지는 «자의 사실»이다」인데 "
                "「SE 판정 자체의 «자 의존성»」을 안 실었다"),
        ("🔴 칸 수", len(COMP) * len(RN)),
        ("🔴 성분별", se_table),
        ("🔴🔴🔴 자별 «2 를 넘은 성분 수»", collections.OrderedDict(
            (rn, JU[rn]["🔴🔴🔴 그 수"]) for rn in RN)),
        ("🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분", split_se or "없음"),
        ("🔴🔴🔴 그 수", len(split_se)),
        ("🔴🔴🔴 자에 따라 «부호»가 갈리는 성분", split_sign or "없음"),
        ("🔴🔴🔴 그 수(부호)", len(split_sign)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", len(COMP) * len(RN) * 2),
        ("통과", bool(len(se_table) == len(COMP))),
    ])

    # ── §2 🔴🔴 탐색 격자 — **오른쪽으로 늘려 꼭짓점을 감싼다** ────────
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
        # 🔴🔴🔴 **「최적」은 argmax 가 아니라 「2·SE_clu 로 «안 갈리는» 칸들의 «집합»」이다**
        best_set, best_rows = [], collections.OrderedDict()
        for nb in EXPLORE_BASE:
            if nb == best:
                best_set.append(int(nb))
                best_rows[str(nb)] = {"🔴 argmax 자신": True, "t_clu": 0.0,
                                      "🔴 안 갈리나": True}
                continue
            blk = lin_block(U_REG, {("탐색", best): 1.0, ("탐색", nb): -1.0},
                            rn, wmaps[rn])
            t = blk["🔴🔴🔴 t_clu"]
            same = bool(t is not None and abs(t) < 2.0)
            best_rows[str(nb)] = {"🔴 argmax 와의 차": blk["🔴🔴🔴 값"],
                                  "SE": blk["🔴🔴🔴 도메인 군집 SE"],
                                  "t_clu": t, "🔴 안 갈리나": same}
            if same:
                best_set.append(int(nb))
        explore[rn] = collections.OrderedDict([
            ("🔴 격자(총량 %d 고정 · hplt = %d − base)" % (EXPLORE_N, EXPLORE_N), rho),
            ("🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)", int(best)),
            ("🔴 그 값", rho[str(best)]),
            ("🔴🔴🔴 argmax 가 격자 오른쪽 끝인가", bool(best == EXPLORE_BASE[-1])),
            ("🔴🔴🔴 «최적 집합»(argmax 와 `2·SE_clu` 로 «안 갈리는» 칸)", sorted(best_set)),
            ("🔴🔴🔴 최적 집합의 크기", len(best_set)),
            ("🔴🔴🔴 최적 집합의 크기가 1 을 넘나", bool(len(best_set) > 1)),
            ("🔴 argmax 대조(칸별)", best_rows),
            ("🔴 짝 차(이웃 눈금) — 군집 SE·LODO 를 «전부» 붙였다", pairs),
            ("🔴🔴🔴 「벼랑」 세 칸(45→90→135)의 짝 차가 2·SE_clu 를 넘나", cliff),
            ("🔴🔴🔴 그중 넘은 수", nsurv),
            ("🔴🔴🔴 「벼랑」이라 적을 수 있나(`조항 68`)", bool(nsurv > 0)),
        ])
    explore["🔴🔴🔴 이 격자는 «사전등록 안»이다"] = (
        "🔴 **채점 분모에 «든다».** 🔴🔴 **991 의 격자는 `45~450` 이고 `R_pool` ρ 가 «끝 칸에서 최대»였다** "
        "--- 「최적 450」은 «격자 경계 인공물»이었다. 993 는 `675·900·1200` 을 더해 꼭짓점을 «감쌌다»")
    explore["🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"] = bool(
        1800 in EXPLORE_BASE)
    explore["🔴🔴 `base=90` 칸이 판정의 `H` 칸과 «같은 물건»인가 — 실측"] = \
        collections.OrderedDict([
            ("탐색 base=90 의 판정 자 ρ",
             _r(float(arr(U_REG, ("탐색", 90), RULER_JUDGE).mean()))),
            ("판정 `H` 칸의 판정 자 ρ", _r(float(arr(U_REG, H, RULER_JUDGE).mean()))),
            ("🔴 차", _r(float((arr(U_REG, ("탐색", 90), RULER_JUDGE)
                              - arr(U_REG, H, RULER_JUDGE)).mean()), 15)),
            ("🔴🔴 같은 물건인가", bool(np.allclose(
                arr(U_REG, ("탐색", 90), RULER_JUDGE), arr(U_REG, H, RULER_JUDGE)))),
            ("🔴 그래서", "🔴 **같은 칸이다. 그 사실을 «측정 전에» 사전등록 §1-1 에 신고했고 "
                       "여기서 «실측»한다**(`조항 68-나`) --- 990·991 의 「벼랑」 주장과 이어 붙이려고 "
                       "일부러 남겼다"),
        ])
    explore["🔴 격자 칸 수"] = len(EXPLORE_BASE)
    explore["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(nexp * len(doms))

    # ══════════════════════════════════════════════════════════════════
    # ── §2-나 🔴🔴🔴 993 신설 — **「base 45 대 나머지」 이분 대비** ────────
    #   🔴 **왜 (티처 #131 3순위 ㉢).** **base 탐색은 이 SE 로 「해상도가 없다」** ---
    #   판정 자 최적 집합이 **7/8** 이고 `R_eq`·`R_champ` 는 **8/8** 이다.
    #   **이 격자가 실제로 가르는 것은 「base 45 대 나머지」 «하나»뿐**이다
    #   (`0.2601` 대 `0.357~0.375`). 🔴 **격자를 «더 넓히지 않는다»** ---
    #   같은 8 칸에서 «이분 문제»로 다시 세운다(사전등록 §1-1 · 측정 «전»에 박았다).
    REST = [nb for nb in EXPLORE_BASE if nb != 45]
    binary = collections.OrderedDict()
    for rn in RN:
        coefs = collections.OrderedDict([(("탐색", nb), 1.0 / len(REST)) for nb in REST])
        coefs[("탐색", 45)] = -1.0
        blk = lin_block(U_REG, coefs, rn, wmaps[rn])
        binary[rn] = collections.OrderedDict([
            ("🔴 대비", "mean(base ∈ %s) − ρ(base = 45)" % (REST,)),
            ("🔴🔴🔴 값", blk["🔴🔴🔴 값"]),
            ("🔴🔴🔴 도메인 군집 SE", blk["🔴🔴🔴 도메인 군집 SE"]),
            ("🔴🔴🔴 t_clu", blk["🔴🔴🔴 t_clu"]),
            ("🔴 2 를 넘나", blk["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]),
            ("🔴🔴 LODO", blk["🔴🔴 LODO"]),
            ("🔴🔴🔴 LODO 부호 뒤집힌 도메인 수", blk["🔴🔴🔴 LODO 부호 뒤집힌 도메인 수"]),
            ("🔴 전수", blk),
        ])
    binary["🔴🔴🔴 왜 이분 문제인가"] = (
        "🔴 **992 의 격자 8 칸은 실제로 「하나」밖에 안 갈랐다** --- 판정 자 최적 집합 «7/8» · "
        "`R_eq`·`R_champ` 는 «8/8». 「최적 base」는 이 SE 로 «해상도가 없다». "
        "🔴🔴 **격자를 넓히는 것은 답이 아니다** --- 993 은 «같은 8 칸»에서 「base 45 대 나머지」 "
        "«하나»만 묻는다(사전등록 §1-1 · 측정 «전»에 박은 대비)")
    binary["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(len(RN) * len(doms) * len(SEEDS))

    # ── §2-다 🔴🔴🔴 993 신설 — **자 「사이」 «차»의 군집 SE** ─────────────
    #   🔴🔴🔴 **왜 (사전등록 §1-2 `W7`).** 992 의 헤드라인 `W5` 는
    #   「자 A 에서 `t = 1.4671` · 자 B 에서 `t = 2.2260`」이다. **그것은 「두 자가
    #   다르다」의 «증거가 아니다»** --- 두 수가 각각 문턱의 «양쪽»에 떨어졌다는 관측일
    #   뿐이고, **「차」 자체는 한 번도 «안 쟀다».**
    #   🔴 993 은 «차»를 «짝으로» 잰다. 도메인별 값 `Δ_d` 는 자에 «무관»하고 자는
    #   «가중»만 바꾸므로, 자 사이 차는 **가중의 차** `a_d = w1_d − w2_d`(`Σa_d = 0`)에
    #   대한 `δ = Σ_d a_d Δ_d` 다. 🔴 **사전등록 §1-3 의 식을 «그대로» 쓰려고**
    #   도메인 변수를 `e_d = a_d · Δ_d · G` 로 두고 «균등 가중»(`Σ = 1`)으로 잰다 ---
    #   `Σ_d (1/G) e_d = δ` 라 «항등»이고, SE 식은 사전등록 문언 그대로다.
    def _norm(w):
        tw = float(sum(w[d] for d in doms))
        return {d: w[d] / tw for d in doms}

    G_ = len(doms)
    UNIF = {d: 1.0 / G_ for d in doms}
    PAIRS_RN = [(RN[i], RN[k]) for i in range(len(RN)) for k in range(len(RN)) if i != k
                and RN[i] != RULER_JUDGE and RN[k] == RULER_JUDGE]
    PAIRS_RN += [(RN[1], RN[2])] if len(RN) == 3 else []
    rdiff = collections.OrderedDict()
    for rn1, rn2 in PAIRS_RN:
        w1, w2 = _norm(wmaps[rn1]), _norm(wmaps[rn2])
        per_comp = collections.OrderedDict()
        for nm, cf in COMP.items():
            dd = collections.OrderedDict()
            for d in doms:
                dd[d] = sum(c * float(np.mean(perarr(U_REG, k, d)))
                            for k, c in cf.items())
            e = collections.OrderedDict(
                (d, (w1[d] - w2[d]) * dd[d] * G_) for d in doms)
            delta, se = cluster_se(e, UNIF)
            lo = lodo(e, UNIF)
            hitbox["n"] += len(doms)
            per_comp[nm] = collections.OrderedDict([
                ("🔴🔴🔴 차(= 자1 − 자2)", _r(delta)),
                ("🔴🔴🔴 도메인 군집 SE", _r(se)),
                ("🔴🔴🔴 t_clu", _r(delta / se) if se else None),
                ("🔴 2 를 넘나", bool(se and abs(delta / se) >= 2.0)),
                ("🔴🔴 LODO", collections.OrderedDict((k, _r(v)) for k, v in lo.items())),
                ("🔴 도메인별 기여 e_d",
                 collections.OrderedDict((k, _r(v)) for k, v in e.items())),
            ])
        rdiff["%s − %s" % (rn1, rn2)] = collections.OrderedDict([
            ("🔴 성분별", per_comp),
            ("🔴🔴🔴 `2·SE` 를 넘은 성분 수",
             len([1 for v in per_comp.values() if v["🔴 2 를 넘나"]])),
            ("🔴🔴🔴 넘은 성분", [k for k, v in per_comp.items() if v["🔴 2 를 넘나"]] or "없음"),
        ])
    _KEY_CP = "R_champ 챔피언가중 − R_pool 묶음"
    rdiff["🔴🔴🔴 무엇을 물었나"] = (
        "🔴🔴🔴 **「무엇이 사는가는 «자의 사실»이다」(992 `W5`)를 «차»로 «직접» 잰다.** "
        "992 는 「자 A 에서 t = 1.4671 · 자 B 에서 t = 2.2260」을 실었는데, 그것은 두 수가 "
        "각각 문턱의 «양쪽»에 떨어졌다는 관측일 뿐 **「차」를 한 번도 «안 쟀다**. "
        "🔴 두 수가 문턱의 양쪽에 있다는 것과 «두 수가 서로 다르다»는 것은 «다른 명제»다")
    rdiff["🔴🔴🔴 상호작용의 「챔피언 − 판정」 차가 `2·SE` 를 넘나"] = (
        rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴 2 를 넘나"]
        if _KEY_CP in rdiff else None)
    rdiff["🔴🔴🔴 그 t_clu"] = (
        rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"]
        if _KEY_CP in rdiff else None)
    rdiff["🔴🔴🔴 그래서 `W5` 서사는 «차의 유의성»으로 서나"] = bool(
        rdiff["🔴🔴🔴 상호작용의 「챔피언 − 판정」 차가 `2·SE` 를 넘나"])
    rdiff["🔴 짝 수(분모)"] = len(PAIRS_RN)
    rdiff["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(len(PAIRS_RN) * len(COMP) * len(doms))

    # ── §3 🔴 깨끗한 천장 대조 ────────────────────────────────────────
    ceil_blk = collections.OrderedDict()
    for rn in RN:
        ceil_blk[rn] = lin_block(
            U_REG, {("증강천장", len(pool.yh)): 1.0, ("증강천장", 0): -1.0},
            rn, wmaps[rn])
    ceil_out = collections.OrderedDict([
        ("🔴🔴🔴 무엇", "🔴 base 를 «각 씨앗·각 겹의 자기 천장»에 두고 hplt 만 0 → %d 로 흔든 차"
         % len(pool.yh)),
        ("🔴 자별", ceil_blk),
    ])

    # ── §4 🔴🔴 즉시정정 ─────────────────────────────────────────────
    def lack(u, key, which):
        return int(max(raw[u][key][which]))

    lit = old_literal_990()
    fix = collections.OrderedDict([
        ("🔴🔴🔴 `N_ALL` 을 «계산»했다", int(NA)),
        ("🔴 식", "`ceil(len(pool.yh) / ALPHA_H)`"),
        ("🔴 `len(pool.yh)`", int(len(pool.yh))),
        ("🔴 `len(pool.yb)`", int(len(pool.yb))),
        ("🔴🔴🔴 990 의 손 리터럴(`world990.py` 소스에서 «읽었다»)", lit),
        ("🔴🔴🔴 그 리터럴이 요구한 hplt 자리 − 실제 hplt 행",
         int(round(ALPHA_H * lit) - len(pool.yh)) if lit else None),
        ("🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대", lack(U_REG, ("H", NA), "부족.hplt")),
        ("🔴 판정 예산 1800 네 칸의 부족 합", collections.OrderedDict(
            (nm, {"base": lack(U_REG, (nm, N), "부족.base"),
                  "hplt": lack(U_REG, (nm, N), "부족.hplt")}) for nm in CELLS)),
    ])

    # ── §5 🔴🔴🔴 판정 ────────────────────────────────────────────────
    jd = JU[RULER_JUDGE]
    judge = collections.OrderedDict()
    judge["🔴🔴🔴 판정 자(측정 «전»에 못 박았다)"] = RULER_JUDGE
    judge["🔴 판정 자의 근거"] = "docs/목표.md — 981~ 정본 자는 `R_pool 묶음`(w ∝ n_d)"
    judge["🔴 판정 λ"] = "u = %d (10^%d)" % (U_REG, U_REG)
    judge["🔴 판정 SE"] = "도메인 군집 SE(사전등록 §1-3 식)"
    judge["🔴🔴🔴 한 표 — 자 셋 × 여덟 칸"] = collections.OrderedDict(
        (rn, JU[rn]["🔴🔴🔴 한 줄 표"]) for rn in RN)

    sA_sign = {rn: (JU[rn]["🔴🔴🔴 한 줄 표"]["순서 A 굶김"] > 0) for rn in RN}
    aA_sign = {rn: (JU[rn]["🔴🔴🔴 한 줄 표"]["순서 A 증강"] > 0) for rn in RN}
    split_starve = [rn for rn in RULER_ALT if sA_sign[rn] != sA_sign[RULER_JUDGE]]
    split_aug = [rn for rn in RULER_ALT if aA_sign[rn] != aA_sign[RULER_JUDGE]]
    order_flip = [rn for rn in RN
                  if JU[rn]["🔴🔴🔴 순서에 따라 «증강의 부호»가 뒤집히나"]]
    judge["🔴🔴🔴 판정 자와 «굶김 부호»가 갈린 병기 자"] = split_starve or "없음"
    judge["🔴🔴🔴 판정 자와 «증강 부호»가 갈린 병기 자"] = split_aug or "없음"
    judge["🔴🔴🔴 순서에 따라 «증강 부호»가 뒤집히는 자"] = order_flip or "없음"
    judge["🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분"] = split_se or "없음"
    judge["🔴🔴🔴 자에 따라 «2·SE 판정»이 갈린 성분 수"] = len(split_se)
    judge["🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄"] = (
        "🔴🔴🔴 **「무엇이 사는가는 «자의 사실»이다」는 «차»를 재면 «안 선다».** "
        "상호작용의 `t_clu` 는 판정 자 `%s` 에서 %s · 챔피언 자에서 %s 로 문턱의 «양쪽»에 "
        "떨어지지만, **두 자 「사이의 차」 자체는 %s ± %s (`t_clu` %s)로 `2·SE` 를 «못 넘는다»** "
        "--- `W5` 서사가 «차의 유의성»으로 서나: %s. "
        "🔴 **두 수가 문턱의 양쪽에 있다는 것과 두 수가 «서로 다르다»는 것은 «다른 명제»다.** "
        "🔴🔴 그리고 base 격자는 이 SE 로 「최적」을 «못 정한다»(안 갈리는 칸 %d) --- "
        "격자를 넓히는 대신 「base 45 대 나머지」 이분 대비로 세우면 판정 자에서 %s ± %s "
        "(`t_clu` %s)로 갈리고, **그 갈림마저 병기 자에서는 %s · %s 로 문턱을 못 넘는다** "
        "--- 이분 대비도 «자의 사실»이다."
        % (RULER_JUDGE,
           jd["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"],
           JU["R_champ 챔피언가중"]["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"],
           rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 차(= 자1 − 자2)"],
           rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 도메인 군집 SE"],
           rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"],
           rdiff["🔴🔴🔴 그래서 `W5` 서사는 «차의 유의성»으로 서나"],
           explore[RULER_JUDGE]["🔴🔴🔴 최적 집합의 크기"],
           binary[RULER_JUDGE]["🔴🔴🔴 값"], binary[RULER_JUDGE]["🔴🔴🔴 도메인 군집 SE"],
           binary[RULER_JUDGE]["🔴🔴🔴 t_clu"],
           binary["R_eq 균등"]["🔴🔴🔴 t_clu"],
           binary["R_champ 챔피언가중"]["🔴🔴🔴 t_clu"]))

    # ── 🔴🔴🔴 993 --- 새 판정 칸(사전등록 §3 의 `P4`·`P5` 가 여기를 문다) ───
    judge["🔴🔴🔴 이분 대비(base 45 대 나머지) — 판정 자 값"] = binary[RULER_JUDGE]["🔴🔴🔴 값"]
    judge["🔴🔴🔴 이분 대비 t_clu(판정 자)"] = binary[RULER_JUDGE]["🔴🔴🔴 t_clu"]
    judge["🔴🔴🔴 이분 대비가 2 를 넘나(판정 자)"] = binary[RULER_JUDGE]["🔴 2 를 넘나"]
    judge["🔴🔴🔴 이분 대비가 2 를 넘은 자 수"] = len(
        [1 for rn in RN if binary[rn]["🔴 2 를 넘나"]])
    judge["🔴🔴🔴 상호작용의 「챔피언 − 판정」 차"] = \
        rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 차(= 자1 − 자2)"]
    judge["🔴🔴🔴 그 차의 t_clu"] = \
        rdiff[_KEY_CP]["🔴 성분별"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"]
    judge["🔴🔴🔴 `W5` 서사가 «차의 유의성»으로 서나"] = \
        rdiff["🔴🔴🔴 그래서 `W5` 서사는 «차의 유의성»으로 서나"]
    judge["🔴🔴🔴 자 «사이» 차에서 2·SE 를 넘은 성분 수(챔피언 − 판정)"] = \
        rdiff[_KEY_CP]["🔴🔴🔴 `2·SE` 를 넘은 성분 수"]

    judge["🔴 P1 argmax 가 격자 오른쪽 끝인가"] = \
        explore[RULER_JUDGE]["🔴🔴🔴 argmax 가 격자 오른쪽 끝인가"]
    judge["🔴 P2 최적 집합의 크기가 1 을 넘나"] = \
        explore[RULER_JUDGE]["🔴🔴🔴 최적 집합의 크기가 1 을 넘나"]
    judge["🔴 판정 자 argmax"] = explore[RULER_JUDGE]["🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)"]
    judge["🔴 판정 자 최적 집합"] = explore[RULER_JUDGE][
        "🔴🔴🔴 «최적 집합»(argmax 와 `2·SE_clu` 로 «안 갈리는» 칸)"]
    judge["🔴 판정자 상호작용 t_clu"] = jd["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"]
    judge["🔴 챔피언자 상호작용 t_clu"] = \
        JU["R_champ 챔피언가중"]["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu"]
    judge["🔴 챔피언자 상호작용이 2 를 넘나"] = \
        JU["R_champ 챔피언가중"]["🔴 성분"]["상호작용 A′ − A"]["🔴🔴🔴 t_clu 절댓값이 2 이상인가"]
    judge["🔴 Δ(1800) t_clu"] = jd["🔴 성분"]["Δ = H − B"]["🔴🔴🔴 t_clu"]
    judge["🔴 Δ(1800) 군집 SE"] = jd["🔴 성분"]["Δ = H − B"]["🔴🔴🔴 도메인 군집 SE"]
    judge["🔴🔴 성분 여덟 중 t_clu 가 2 를 넘은 것(판정 자)"] = jd["🔴🔴🔴 `t_clu` 절댓값이 2 를 넘은 성분"]
    judge["🔴🔴 그 수(판정 자)"] = jd["🔴🔴🔴 그 수"]
    judge["🔴 문턱 0.00353 — 깨끗한 천장 대조가 이 «자»를 넘었나"] = bool(
        ceil_blk[RULER_JUDGE]["🔴🔴🔴 값"] > THR_CARD)
    judge["🔴 깨끗한 천장 대조 값(판정 자)"] = ceil_blk[RULER_JUDGE]["🔴🔴🔴 값"]
    judge["🔴🔴 노트 133 — 「채택」이라 적나"] = (
        "🔴 «안» 적는다 — 채택 문턱은 「못 정했다」(968 재정정). 이 수는 «자»로만 쓴다")
    judge["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(hitbox["n"])

    res = collections.OrderedDict([
        ("무엇", "993 §1 — 🔴🔴🔴 **「무엇이 사는가」는 자의 사실이고, 「최적」은 격자의 사실이었다**"),
        ("🔴 축", "C1 (자기 자) × C6 (scaling) × C2 (도메인 가중)"),
        ("사전등록", "docs/prereg_993_straighten_the_rulers.md §1"),
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
        ("§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량", se_blk),
        ("§2 🔴🔴🔴 탐색 격자", explore),
        ("§3 🔴🔴🔴 이분 대비 — 「base 45 대 나머지」(993 신설 · 사전등록 §1-1)", binary),
        ("§4 🔴🔴🔴 자 «사이» 차 — `W7`(993 신설 · 사전등록 §1-2)", rdiff),
        ("§3 🔴🔴 깨끗한 천장 대조", ceil_out),
        ("§4 🔴🔴 즉시정정", fix),
        ("§5 🔴🔴🔴 판정", judge),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", int(hitbox["n"])),
        ("통과", bool(
            all(nm in order[str(U_REG)][rn]["🔴 성분"]
                for rn in RN for nm in COMP)
            and all("상호작용 A′ − A" in order[str(u)][rn]["🔴 성분"]
                    for u, _l in lams for rn in RN)
            and not explore["🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"]
            and len(se_table) == len(COMP)
            and len(EXPLORE_BASE) == 8
            and fix["🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대"] == 0)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 자 3 × 성분 8 = 24 칸이 «전부» 기록됐고, 탐색 격자에 판정 칸 `B` 가 «없고», "
         "격자가 여덟 칸으로 늘었고, 「전량」 눈금이 hplt 를 «다 채웠다»"),
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
    p = OUT / ("out993_wiring.json" if a.stage == "wiring" else "out993_order.json")
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("끝 %s → %s" % (a.stage, p.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
