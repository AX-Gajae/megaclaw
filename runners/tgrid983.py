#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""983 — 🔴🔴🔴 **시간 방향 유보를 «예산 격자 전체»로 옮긴다** (축 C1 · 곁 C3·C4).

사전등록 `docs/prereg_983_holdout_registry.md` §2·§3-1·§3-4 를 그대로 따른다.

🔴 **왜.** 982 는 시간 방향 유보를 **한 칸(`N_B=1800`)에서만** 쟀다. 그래서 982 의 2순위
헤드라인(「이득 소멸」·「대조 포화」·「MDE 미달」)은 **전부 옛 유보(개체 묶음)에서 난 값**이고,
982 자신이 「유보를 바꾸면 관문 판정이 뒤집힌다」를 증명해 놓고 거기에 **유보 종속 단서를
안 붙였다**(티처 #121 물음 ① 의 답 1).

🔴 **그리고 누출 통로가 「행」에만 걸려 있었다.** `tfwd982._quota_t` 의 목표가 **미래 전량**
(`tgt = {d: pool.ho_mask[d].sum()}`)이고 `pool.gated` 도 **미래 전량**으로 정해진다 —
곧 **원점 1(2019년)의 층화 팔이 2026년 도메인 구성비를 안다.** `W1` 은 `tmax_tr < tmin_te`
만 보므로 **행 선택**만 검사하고 통계 통로는 원리상 사각이다(티처 #121 M1).

그래서 이 러너는 팔 **넷**을 같은 복제·같은 원점·같은 붓스트랩에서 짝지어 돌린다.

| 딱지 | 팔 | 목표 벡터 | 미래를 보나 |
|---|---|---|---|
| `㉯` | 대조(순열 앞머리) | — | 아니오 |
| `㉮` | 층화 · **오라클** | 유보 전량(블록 1~4) 구성비 | 🔴 **예** |
| `㉰` | 층화 · **절단 앞** | 원점 `j` 마다 블록 `<j` 구성비 | 아니오 |
| `㉱` | **위약** | 절단 앞 hplt 공급 몫 | 아니오 |

씀:
    python3 runners/tgrid983.py --stage wire --ref <40자 sha>
    python3 runners/tgrid983.py --stage grid --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
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
import runners.layers957 as L                     # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402
import mix980 as M8                               # noqa: E402
import tfwd982 as T2                              # noqa: E402

RAN = ("runners/tgrid983.py", "runners/tfwd982.py", "runners/mix980.py",
       "runners/ruler979.py", "runners/ruler978.py", "runners/alpha977.py",
       "runners/ledger.py", "runners/layers957.py", "runners/predict971.py",
       "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out983_progress.txt"

RULERS = R9.RULERS
CANON = "R_pool 묶음"                # 🔴 981~ 정본 자(`docs/목표.md` 표)
SEEDS = A.SEEDS
U_REG = A.U_REG
ALPHA_BASE = A.ALPHA_BASE
K_FEAT = M8.K_FEAT
MIN_HO = A.MIN_HO
ARM_C = M8.ARM_C
ARM_S = M8.ARM_S

# ── 사전등록 §8 상수 (측정 전에 박았다) ──────────────────────────────
NB_GRID = list(M8.NB_GRID)         # 450 … 28800
BOOT_G = 200                       # 격자 짝SE 복제

#: 🔴 팔 딱지 — 사전등록 §2-2 표
A_CTL = "㉯ 대조"
A_ORA = "㉮ 층화 · 오라클(유보 전량 구성비)"
A_PAST = "㉰ 층화 · 절단 앞(블록 <j 구성비)"
A_PLA = "㉱ 위약(절단 앞 hplt 공급 몫)"
TREAT = (A_ORA, A_PAST, A_PLA)


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


def _sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _iso(o):
    return dt.date.fromordinal(int(o)).isoformat()


# ══════════════════════════════════════════════════════════════════════
# §1 🔴🔴 목표 벡터를 «자료 보기(view)» 의 함수로 적는다
#
# 🔴 **왜 이 꼴인가.** 「미래 통계를 보나」를 «떨어질 수 있는» 검사로 만들려면 목표를
#    자료에서 다시 지을 수 있어야 한다. 그래서 목표 함수는 `pool` 이 아니라 **보기**
#    (전량 보기 또는 «절단 앞만» 보기)를 받는다. 같은 함수를 두 보기에 물려 지문을
#    견주면 그 팔이 미래를 보는지 **잰다**(주장 안 한다).
# ══════════════════════════════════════════════════════════════════════
class View(object):
    """`db/tb/blk` (base) · `dh/th` (hplt) · `edges` 만 담은 자료 보기."""

    def __init__(self, db, blk, dh, th, edges):
        self.db, self.blk, self.dh, self.th, self.edges = db, blk, dh, th, edges


def full_view(pool):
    return View(pool.db, pool.blk, pool.dh, pool.th, pool.edges)


def past_view(pool, j):
    """🔴 **절단 `j` 보다 앞선 행만** 남긴 보기 — 미래가 통째로 없다."""
    mb = pool.blk < j
    mh = pool.th < pool.edges[j]
    return View(pool.db[mb], pool.blk[mb], pool.dh[mh], pool.th[mh], pool.edges)


def tgt_oracle(v, j):
    """🔴 **982 가 쓴 목표** — 유보 전량(블록 ≥ 1)의 도메인 구성비. **미래를 본다.**"""
    return collections.Counter(v.db[v.blk >= 1].tolist())


def tgt_past(v, j):
    """🔴 **983 신설** — 원점 `j` 의 **절단 앞 블록**(`<j`) 도메인 구성비."""
    return collections.Counter(v.db[v.blk < j].tolist())


def tgt_supply(v, j):
    """위약 — **절단 앞 hplt 공급 몫**."""
    return collections.Counter(v.dh[v.th < v.edges[j]].tolist())


SPEC = collections.OrderedDict([
    (A_CTL, {"arm": ARM_C, "tgt": None, "미래": False}),
    (A_ORA, {"arm": ARM_S, "tgt": tgt_oracle, "미래": True}),
    (A_PAST, {"arm": ARM_S, "tgt": tgt_past, "미래": False}),
    (A_PLA, {"arm": ARM_S, "tgt": tgt_supply, "미래": False}),
])


def gate_of(cnt):
    """게이트 — `n_d ≥ MIN_HO` 인 도메인만 할당량을 받는다."""
    return sorted([d for d, n in cnt.items() if n >= MIN_HO])


def tgt_and_gate(pool, name, j, view=None):
    """🔴 팔 `name` 의 원점 `j` 목표 벡터와 게이트를 «보기»에서 짓는다."""
    fn = SPEC[name]["tgt"]
    if fn is None:
        return None, None
    v = full_view(pool) if view is None else view
    cnt = fn(v, j)
    doms = gate_of(cnt)
    if not doms:                       # 🔴 게이트가 비면 「없다」가 아니라 「빈 게이트」다
        return {}, []
    tot = float(sum(cnt[d] for d in doms))
    return {d: float(cnt[d]) / tot for d in doms}, doms


def tgt_sig(tgt, doms):
    """목표 벡터 + 게이트의 지문 — 🔴 **12 자리로 반올림해 잰다**(부동소수 잡음 제거)."""
    if tgt is None:
        return "대조 팔 — 목표 없음"
    payload = json.dumps([list(doms),
                          [round(float(tgt.get(d, 0.0)), 12) for d in doms]],
                         ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# §2 배관 — 🔴 `tfwd982` 의 선택기를 **원점별 목표·원점별 게이트**로 넓힌다
# ══════════════════════════════════════════════════════════════════════
def _quota983(nh, have, tgt, doms):
    """`tfwd982._quota_t` 와 같은 최대잔여법 · 🔴 **목표와 게이트를 인자로 받는다.**"""
    q = {d: 0 for d in doms}
    bound = collections.OrderedDict()
    left = int(nh)
    free = [d for d in doms if have.get(d, 0) > 0]
    for _ in range(len(doms) + 2):
        if left <= 0 or not free:
            break
        s = sum(tgt.get(d, 0.0) for d in free)
        if s <= 0:
            break
        raw = {d: left * tgt.get(d, 0.0) / s for d in free}
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
                bound[d] = {"🔴 공급(절단 앞)": int(have.get(d, 0)),
                            "🔴 받은 자리": int(q[d])}
            elif q[d] < have.get(d, 0):
                newfree.append(d)
        free = newfree
    return q, bound, int(left)


def _selh983(pool, j, alpha, n_b, name):
    """hplt 학습 행 — 🔴 **절단 `j` 보다 앞선 행만**(미래 금지)."""
    cut = pool.edges[j]
    past_h = pool.th < cut
    order = pool.perm_h[past_h[pool.perm_h]]        # 🔴 네 팔이 같은 차례를 쓴다
    nh = int(round(alpha * n_b))
    if SPEC[name]["arm"] == ARM_C:
        return order[:nh], None, collections.OrderedDict(), max(0, nh - len(order[:nh]))
    tgt, doms = tgt_and_gate(pool, name, j)
    have = collections.Counter(pool.dh[order].tolist())
    q, bound, short = _quota983(nh, have, tgt, doms)
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
    return np.asarray(keep, dtype=order.dtype), q, bound, int(short)


def _selb983(pool, j, alpha, n_b):
    """base 학습 행 — **블록 `<j` 만.**"""
    past_b = pool.blk < j
    nh = int(round(alpha * n_b))
    return pool.perm_b[past_b[pool.perm_b]][:n_b - nh]


def oof983(pool, alpha, lam, n_b, name, k=K_FEAT, tr_boot=None):
    """🔴 **원점 넷의 앞→뒤 예측.** 유보 자리(블록 1~4)만 채운다."""
    pred = np.zeros(len(pool.yb))
    filled = np.zeros(len(pool.yb), dtype=bool)
    ntr, nsel_h, tmax_tr, tmin_te, ov_b, ov_h, short = [], [], [], [], [], [], []
    for j in pool.origins:
        selb = _selb983(pool, j, alpha, n_b)
        selh, _q, _bd, sh = _selh983(pool, j, alpha, n_b, name)
        X, y, ent, nb_rows = A.design(pool, selb, selh, k)
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 983 * 100000)
            order, st, en = A.groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y = X[idx], y[idx]
        m = L.ridge_fit(X, y, lam)
        te = pool.blk == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        filled |= te
        ntr.append(int(len(y)))
        nsel_h.append(int(len(selh)))
        short.append(int(sh))
        tr_t = np.concatenate([pool.tb[selb], pool.th[selh]])
        tmax_tr.append(int(tr_t.max()) if len(tr_t) else -10 ** 9)
        tmin_te.append(int(pool.tb[te].min()))
        te_ent = set(pool.ecb[te].tolist())
        #: 🔴 **983 정정 8** — 개체 교집합을 base/hplt 로 «갈라» 낸다(티처 #121).
        ov_b.append(int(len(te_ent & set(pool.ecb[selb].tolist()))))
        ov_h.append(int(len(te_ent & set(pool.ech[selh].tolist()))))
    return {"예측": pred, "채운 자리": filled, "원점별 학습 행": ntr,
            "원점별 hplt 행": nsel_h, "원점별 학습 최대 시각": tmax_tr,
            "원점별 유보 최소 시각": tmin_te, "🔴 원점별 개체 교집합 — base 학습": ov_b,
            "🔴 원점별 개체 교집합 — hplt 학습": ov_h, "원점별 할당 미달": short}


# ══════════════════════════════════════════════════════════════════════
# §3 점추정과 짝 SE — 🔴 **복제별 Δ 벡터를 덤프한다**(사전등록 §3-4)
# ══════════════════════════════════════════════════════════════════════
def point983(pool, R, alpha, lam, n_b, name):
    """겹 씨앗 다섯 평균 — 🔴 씨앗 하나짜리 수를 안 만든다."""
    acc = {nm: [] for nm in RULERS}
    nh, ntr, sh = [], [], []
    for s in SEEDS:
        pool.reseed(s)
        r = oof983(pool, alpha, lam, n_b, name)
        v, _p = R9.score6(pool, R, r["예측"])
        for nm in RULERS:
            acc[nm].append(v[nm])
        nh.append(r["원점별 hplt 행"][0])
        ntr.append(r["원점별 학습 행"][0])
        sh.append(sum(r["원점별 할당 미달"]))
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = _r(float(np.mean(acc[nm])))
        out[nm + " 벌 SD"] = _r(float(np.std(acc[nm], ddof=1)))
    out["🔴 벌 수"] = len(acc[RULERS[0]])
    out["🔴 원점 1 의 hplt 학습 행"] = int(np.mean(nh))
    out["🔴 원점 1 의 학습 행 전량"] = int(np.mean(ntr))
    out["🔴 할당 미달 합(공급 제약)"] = int(np.mean(sh))
    return out


def se_grid(pool, R, alpha, lam, n_b, boot, tag=""):
    """🔴🔴 **짝 SE** — 복제마다 «같은 붓스트랩·같은 원점»에서 대조와 처리 셋을 같이 돌린다.

    🔴 **복제별 Δ 벡터를 그대로 돌려준다**(사전등록 §3-4 · 티처 #121 2순위 ⓓ).
    """
    dd = {a: {nm: [] for nm in RULERS} for a in TREAT}
    ctl = {nm: [] for nm in RULERS}
    t0 = time.time()
    for b in range(boot):
        bc = {nm: [] for nm in RULERS}
        bt = {a: {nm: [] for nm in RULERS} for a in TREAT}
        for s in SEEDS:
            pool.reseed(s)
            pc = oof983(pool, alpha, lam, n_b, A_CTL, tr_boot=b)["예측"]
            vc, _ = R9.score6(pool, R, pc)
            for nm in RULERS:
                bc[nm].append(vc[nm])
            for a in TREAT:
                pa = oof983(pool, alpha, lam, n_b, a, tr_boot=b)["예측"]
                va, _ = R9.score6(pool, R, pa)
                for nm in RULERS:
                    bt[a][nm].append(va[nm] - vc[nm])
        for nm in RULERS:
            ctl[nm].append(float(np.mean(bc[nm])))
        for a in TREAT:
            for nm in RULERS:
                dd[a][nm].append(float(np.mean(bt[a][nm])))
        if (b + 1) % 25 == 0:
            _prog("    %s 짝SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                   time.time() - t0))
    se = collections.OrderedDict()
    for a in TREAT:
        se[a] = collections.OrderedDict(
            [(nm, _r(float(np.std(dd[a][nm], ddof=1)))) for nm in RULERS])
    se["🔴 대조 팔 SE"] = collections.OrderedDict(
        [(nm, _r(float(np.std(ctl[nm], ddof=1)))) for nm in RULERS])
    se["🔴 복제 수"] = boot
    se["🔴 벌 수(복제 하나 안에서)"] = len(SEEDS)
    reps = collections.OrderedDict()
    for a in TREAT:
        reps[a] = collections.OrderedDict(
            [(nm, [round(x, 8) for x in dd[a][nm]]) for nm in RULERS])
    reps["㉯ 대조 팔 ρ(복제별)"] = collections.OrderedDict(
        [(nm, [round(x, 8) for x in ctl[nm]]) for nm in RULERS])
    return se, reps


# ══════════════════════════════════════════════════════════════════════
# §4 배선 W — 🔴🔴 **W5 신설: 배선 «통계» 누출**
# ══════════════════════════════════════════════════════════════════════
def stage_wire(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    pool = T2.TPool()
    out = collections.OrderedDict()
    out["무엇"] = ("983 §3-1 — 🔴🔴 **누출 통로를 「행」에서 「통계」까지 넓힌다.** "
                 "`W5` 는 팔의 목표 벡터·게이트를 «절단 앞 자료만»으로 다시 지어 지문을 견준다")
    out["🔴 축"] = "C1 상태→예측"
    out["사전등록"] = "docs/prereg_983_holdout_registry.md §3-1"
    out["🔴 티처"] = ("🔴 티처 #121 M1 — 「`_quota_t` 의 목표가 미래 전량이라 ㉮ 층화 팔이 "
                    "원점 1(2019년)에서 2026년 도메인 구성비를 안다. `W1` 은 행 선택만 "
                    "보고 통계 통로가 원리상 사각이다」")
    out["🔴🔴 절단 날짜"] = [_iso(c) for c in pool.cuts]
    out["🔴 원점"] = pool.origins
    out["🔴🔴 유보 전량 행 수(블록 1~4)"] = int(pool.ho_all.sum())
    out["🔴🔴 미래 전량 게이트(982 가 쓴 것)"] = list(pool.gated)

    # ── W5 🔴🔴 배선 통계 누출 ────────────────────────────────────────
    w5 = collections.OrderedDict()
    for name in TREAT:
        rows = collections.OrderedDict()
        leak_any = False
        for j in pool.origins:
            tg_f, dm_f = tgt_and_gate(pool, name, j)
            tg_p, dm_p = tgt_and_gate(pool, name, j, view=past_view(pool, j))
            sf, sp = tgt_sig(tg_f, dm_f), tgt_sig(tg_p, dm_p)
            leak = bool(sf != sp)
            leak_any |= leak
            rows["원점 %d" % j] = collections.OrderedDict([
                ("🔴 목표·게이트 지문(전량 보기)", sf),
                ("🔴 목표·게이트 지문(절단 앞 보기)", sp),
                ("🔴 게이트 도메인 수(전량 보기)", len(dm_f)),
                ("🔴 게이트 도메인 수(절단 앞 보기)", len(dm_p)),
                ("🔴🔴 통계가 미래를 보나", leak),
            ])
        w5[name] = collections.OrderedDict([
            ("🔴 사전등록이 못박은 딱지(미래를 보나)", SPEC[name]["미래"]),
            ("🔴 원점별", rows),
            ("🔴🔴🔴 잰 값 — 미래를 보나", leak_any),
            ("🔴🔴 딱지와 잰 값이 맞나", bool(leak_any == SPEC[name]["미래"])),
        ])
    ok5 = all(w5[a]["🔴🔴 딱지와 잰 값이 맞나"] for a in TREAT)
    out["W5 🔴🔴🔴 배선 «통계» 누출"] = collections.OrderedDict([
        ("🔴 무엇을 재나",
         "🔴 팔의 목표 벡터와 게이트를 **절단 앞 자료만으로 다시 지어** 지문을 견준다. "
         "같으면 통계 누출 0, 다르면 누출이다"),
        ("🔴 팔별", w5),
        ("🔴🔴 이 검사가 떨어질 수 있나(구성상 참이 아닌가)",
         bool(w5[A_ORA]["🔴🔴🔴 잰 값 — 미래를 보나"])),
        ("🔴🔴🔴 ㉮ 오라클에서 «떨어지고» ㉰·㉱ 에서 통과하나", bool(ok5)),
        ("통과", bool(ok5)),
    ])

    # ── W1·W2·W3 (982 판 · 🔴 W2 를 base/hplt 로 갈랐다) ──────────────
    pool.reseed(SEEDS[0])
    r_ok = oof983(pool, ALPHA_BASE, 10.0 ** U_REG[1], A.N_B, A_PAST)
    w1_ok = all(a < b for a, b in zip(r_ok["원점별 학습 최대 시각"],
                                      r_ok["원점별 유보 최소 시각"]))
    out["W1 🔴 학습이 언제나 유보보다 앞인가 (행 누출)"] = collections.OrderedDict([
        ("원점별 학습 최대 시각", [_iso(x) for x in r_ok["원점별 학습 최대 시각"]]),
        ("원점별 유보 최소 시각", [_iso(x) for x in r_ok["원점별 유보 최소 시각"]]),
        ("🔴 W1 은 «행 선택»만 본다", "🔴 통계 통로는 `W5` 가 본다 — 둘은 다른 자다"),
        ("통과", bool(w1_ok))])
    ob = r_ok["🔴 원점별 개체 교집합 — base 학습"]
    oh = r_ok["🔴 원점별 개체 교집합 — hplt 학습"]
    out["W2 🔴🔴 학습·유보의 개체 교집합 — **base / hplt 로 갈라 낸다**"] = \
        collections.OrderedDict([
            ("🔴🔴 base 학습 쪽 원점별", ob),
            ("🔴🔴 base 학습 쪽 합", int(sum(ob))),
            ("🔴 hplt 학습 쪽 원점별", oh),
            ("🔴 hplt 학습 쪽 합", int(sum(oh))),
            ("🔴 합(982 가 낸 거친 수)", int(sum(ob) + sum(oh))),
            ("🔴🔴🔴 base 쪽 교집합이 원점 넷 전부 0 인가", bool(sum(ob) == 0)),
            ("🔴 이 수가 뜻하는 것",
             "🔴 티처 #121 — 982 는 둘을 합쳐 세어 **덜 주장했다.** base 쪽이 0 이면 "
             "**시간 분할이 개체 분리도 같이 만들었다**는 뜻이고, hplt 쪽 교집합은 "
             "hplt 가 base 와 같은 개체를 다른 계열로 담고 있어서 생기는 것이다"),
            ("통과", True)])
    past_ok = []
    for j in pool.origins:
        selh, _q, _b, _s = _selh983(pool, j, ALPHA_BASE, A.N_B, A_PAST)
        past_ok.append(bool(len(selh) == 0 or
                            int(pool.th[selh].max()) < pool.edges[j]))
    out["W3 🔴 hplt 학습 행도 절단보다 앞인가"] = collections.OrderedDict([
        ("원점별", past_ok), ("통과", bool(all(past_ok)))])
    out["W4 🔴 유보 지문(주행 시작)"] = collections.OrderedDict([
        ("유보 y sha256", _sha_arr(pool.yb)),
        ("유보 행 수", int(pool.ho_all.sum()))])
    out["🔴 원점별 절단 앞 게이트(㉰ 가 쓰는 것)"] = collections.OrderedDict(
        [("원점 %d" % j, tgt_and_gate(pool, A_PAST, j)[1]) for j in pool.origins])
    out["🔴 원점별 절단 앞 공급 게이트(㉱ 가 쓰는 것)"] = collections.OrderedDict(
        [("원점 %d" % j, tgt_and_gate(pool, A_PLA, j)[1]) for j in pool.origins])
    out["통과"] = bool(ok5 and w1_ok and all(past_ok))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **행 누출 0(`W1`·`W3`) 이고, 통계 누출 검사 `W5` 가 ㉮ 오라클에서 «떨어지고» "
        "㉰·㉱ 에서 통과한다** — 곧 «떨어질 수 있는» 검사다")
    LG.write_stamped(str(OUT / "out983_wire.json"), out, ref, cs0, t0, RAN, LG.DATA)
    return out


# ══════════════════════════════════════════════════════════════════════
# §5 🔴🔴🔴 본 측정 — 시간 방향 × 예산 격자
# ══════════════════════════════════════════════════════════════════════
def stage_grid(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    pool = T2.TPool()
    R = R9.Rulers6(pool)
    s0 = _sha_arr(pool.yb)
    cells = collections.OrderedDict()
    reps_all = collections.OrderedDict()
    for n_b in NB_GRID:
        per_u = collections.OrderedDict()
        for u in U_REG:
            lam = 10.0 ** u
            _prog("N_B=%d · u=%d — 점추정 4 팔 (5 벌)" % (n_b, u))
            pts = collections.OrderedDict(
                [(a, point983(pool, R, ALPHA_BASE, lam, n_b, a))
                 for a in (A_CTL,) + TREAT])
            _prog("N_B=%d · u=%d — 짝SE 복제 %d (4 팔)" % (n_b, u, BOOT_G))
            se, reps = se_grid(pool, R, ALPHA_BASE, lam, n_b, BOOT_G,
                               tag="N_B=%d u=%d" % (n_b, u))
            cell = collections.OrderedDict()
            cell["🔴 팔별 점추정(자 여섯)"] = collections.OrderedDict(
                [(a, collections.OrderedDict([(nm, pts[a][nm]) for nm in RULERS]))
                 for a in (A_CTL,) + TREAT])
            cell["🔴 공급 제약(할당 미달 합)"] = collections.OrderedDict(
                [(a, pts[a]["🔴 할당 미달 합(공급 제약)"]) for a in (A_CTL,) + TREAT])
            cell["🔴 원점 1 의 hplt 학습 행"] = collections.OrderedDict(
                [(a, pts[a]["🔴 원점 1 의 hplt 학습 행"]) for a in (A_CTL,) + TREAT])
            for a in TREAT:
                dl = {nm: pts[a][nm] - pts[A_CTL][nm] for nm in RULERS}
                ses = {nm: se[a][nm] for nm in RULERS}
                cell["%s − %s" % (a, A_CTL)] = collections.OrderedDict([
                    ("🔴🔴 자별 판정", collections.OrderedDict(
                        [(nm, T2.gate2(dl[nm], ses[nm])) for nm in RULERS])),
                    ("🔴🔴🔴 갈리나", T2._diverge(dl, ses)),
                ])
            #: 🔴 오라클 프리미엄 — **㉮ 가 미래 통계를 알아서 얻는 값**(사전등록 §2-4 ⓔ)
            dprem = {nm: pts[A_ORA][nm] - pts[A_PAST][nm] for nm in RULERS}
            #: 🔴 짝이 아니라 «두 짝 SE 의 합성»이다 — 그 사실을 적는다(조항 59)
            sprem = {nm: math.sqrt((se[A_ORA][nm] or 0.0) ** 2 +
                                   (se[A_PAST][nm] or 0.0) ** 2) for nm in RULERS}
            cell["🔴🔴🔴 오라클 프리미엄 ㉮ − ㉰"] = collections.OrderedDict([
                ("🔴 자별 판정", collections.OrderedDict(
                    [(nm, T2.gate2(dprem[nm], sprem[nm])) for nm in RULERS])),
                ("🔴 SE 가 어떻게 났나",
                 "🔴 **짝 SE 가 아니라 두 팔 짝SE 의 제곱합 제곱근**이다 — 두 팔은 같은 "
                 "복제 안에서 돌았으므로 이 합성은 «보수적»(양의 상관을 무시)이다"),
            ])
            cell["🔴 짝 SE"] = se
            per_u["u=%d" % u] = cell
            reps_all["N_B=%d · u=%d" % (n_b, u)] = reps
        cells["N_B=%d" % n_b] = per_u
        _prog("N_B=%d 끝" % n_b)

    out = collections.OrderedDict()
    out["무엇"] = ("983 §2 — 🔴🔴🔴 **시간 방향 유보 × 예산 격자 전체.** "
                 "982 는 `N_B=1800` 한 칸에서만 쟀다")
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3·C4"
    out["사전등록"] = "docs/prereg_983_holdout_registry.md §2-2·§2-3·§2-4"
    out["🔴 격자"] = NB_GRID
    out["🔴 λ"] = ["10^%d" % u for u in U_REG]
    out["🔴 팔 넷"] = collections.OrderedDict(
        [(a, {"층화인가": SPEC[a]["arm"] == ARM_S, "미래를 보나": SPEC[a]["미래"]})
         for a in (A_CTL,) + TREAT])
    out["🔴 α"] = ALPHA_BASE
    out["🔴 복제 수"] = BOOT_G
    out["🔴 정본 자"] = CANON
    out["🔴 시간 방향 유보 도메인별 행"] = collections.OrderedDict(
        [(d, int(pool.ho_mask[d].sum())) for d in pool.gated])
    out["🔴🔴 칸"] = cells

    # ── §2-4 등록 판정 ────────────────────────────────────────────
    def col(a, key, u):
        return [cells["N_B=%d" % n]["u=%d" % u]["%s − %s" % (a, A_CTL)][
            "🔴🔴 자별 판정"][CANON][key] for n in NB_GRID]

    per_u_v = collections.OrderedDict()
    sign_any, gate_any, ratios = False, False, []
    for u in U_REG:
        uk = "u=%d" % u
        ctl = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][A_CTL][CANON]
               for n in NB_GRID]
        ora = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][A_ORA][CANON]
               for n in NB_GRID]
        pst = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][A_PAST][CANON]
               for n in NB_GRID]
        g_o, g_p, g_l = col(A_ORA, "Δ", u), col(A_PAST, "Δ", u), col(A_PLA, "Δ", u)
        s_o = col(A_ORA, "🔴 짝 SE", u)
        mono = all(g_o[i + 1] <= g_o[i] for i in range(len(g_o) - 1))
        rise_c, rise_o = ctl[-1] - ctl[0], ora[-1] - ora[0]
        sat = bool(mono and rise_c > rise_o)
        half = bool(g_o[0] and g_p[0] / g_o[0] >= 0.5)
        prem0 = cells["N_B=%d" % NB_GRID[0]][uk]["🔴🔴🔴 오라클 프리미엄 ㉮ − ㉰"][
            "🔴 자별 판정"][CANON]
        for n in NB_GRID:
            for a in TREAT:
                dv = cells["N_B=%d" % n][uk]["%s − %s" % (a, A_CTL)]["🔴🔴🔴 갈리나"]
                sign_any |= dv["🔴🔴 ⓐ 부호가 자에 따라 갈리나"]
                gate_any |= dv["🔴🔴 ⓑ 관문이 자에 따라 갈리나"]
                if dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"] is not None:
                    ratios.append(dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"])
        per_u_v[uk] = collections.OrderedDict([
            ("🔴 대조 ρ 격자", collections.OrderedDict(
                [("N_B=%d" % n, ctl[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 ㉮ 오라클 ρ 격자", collections.OrderedDict(
                [("N_B=%d" % n, ora[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 ㉰ 절단 앞 ρ 격자", collections.OrderedDict(
                [("N_B=%d" % n, pst[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 ㉮ − ㉯ 이득 격자", collections.OrderedDict(
                [("N_B=%d" % n, g_o[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 ㉰ − ㉯ 이득 격자", collections.OrderedDict(
                [("N_B=%d" % n, g_p[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 ㉱ − ㉯ 위약 이득 격자", collections.OrderedDict(
                [("N_B=%d" % n, g_l[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 ㉮ − ㉯ 짝SE 격자", collections.OrderedDict(
                [("N_B=%d" % n, s_o[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 P1 이득이 단조 감소하나", bool(mono)),
            ("🔴 대조 팔이 격자에서 오른 폭", _r(rise_c)),
            ("🔴 ㉮ 층화 팔이 격자에서 오른 폭", _r(rise_o)),
            ("🔴🔴 P2 대조 폭 > 층화 폭인가", bool(rise_c > rise_o)),
            ("🔴🔴🔴 ⓓ 대조 포화가 시간 방향에서 «성립»하나(둘 다 참일 때만)", sat),
            ("🔴🔴 ⓓ 가 거짓이면 어느 쪽이 깨졌나",
             "성립" if sat else ("단조는 참 · 폭이 거짓" if mono else
                               ("폭은 참 · 단조가 거짓" if rise_c > rise_o
                                else "둘 다 거짓"))),
            ("🔴🔴 P3 ㉰ 첫 칸 이득이 ㉮ 의 절반 이상인가", half),
            ("🔴 ㉰ / ㉮ 첫 칸 몫", _r(g_p[0] / g_o[0], 4) if g_o[0] else None),
            ("🔴🔴 P4 오라클 프리미엄이 첫 칸에서 2·SE 를 못 넘나",
             bool(not prem0["🔴🔴 |Δ| ≥ 2·짝SE (조건 ②)"])),
            ("🔴 오라클 프리미엄 첫 칸", prem0["Δ"]),
            ("🔴 오라클 프리미엄 첫 칸 |Δ|/SE", prem0["🔴🔴 |Δ|/짝SE"]),
            ("🔴🔴 P5 위약 이득 양수 칸 수 / 7",
             "%d / %d" % (sum(1 for x in g_l if x > 0), len(NB_GRID))),
        ])
    out["🔴🔴🔴 §2-4 등록 판정"] = collections.OrderedDict([
        ("🔴 판정 규칙의 출처",
         "docs/prereg_983_holdout_registry.md §2-4 (측정 전 커밋 %s)" % ref[:12]),
        ("🔴 λ 별", per_u_v),
        ("🔴🔴 ⓐ 부호가 어디서라도 갈리나", bool(sign_any)),
        ("🔴🔴 ⓑ 관문이 어디서라도 갈리나", bool(gate_any)),
        ("🔴 분기비 최대", _r(max(ratios), 4) if ratios else None),
        ("🔴 분기비 중앙값", _r(float(np.median(ratios)), 4) if ratios else None),
        ("🔴 분기비를 잰 칸 수", len(ratios)),
        ("🔴🔴🔴 자가 예산 격자 전체에서도 갈리는가", bool(sign_any or gate_any)),
    ])
    out["🔴 유보 지문(시작=끝)"] = collections.OrderedDict([
        ("시작", s0), ("끝", _sha_arr(pool.yb)),
        ("같은가", bool(s0 == _sha_arr(pool.yb)))])
    out["통과"] = bool(s0 == _sha_arr(pool.yb) and len(cells) == len(NB_GRID))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **격자 일곱 칸을 λ 둘에서 전부 돌렸고 주행 중 유보를 한 줄도 안 만졌다.** "
        "🔴 「갈리나」·「포화하나」의 답은 `통과` 가 아니라 위 «등록 판정» 칸이다")
    LG.write_stamped(str(OUT / "out983_grid.json"), out, ref, cs0, t0, RAN, LG.DATA)
    #: 🔴 복제별 Δ 는 큰 파일이라 따로 · 🔴 **도장은 여기도 붙는다**(규칙 C)
    rp = collections.OrderedDict()
    rp["무엇"] = ("983 §3-4 — 🔴 **복제별 Δ 벡터 전량.** 982 는 SD 만 남겨 "
                 "「왜 올랐나」를 재현 없이 못 봤다(티처 #121 2순위 ⓓ)")
    rp["🔴 복제 수"] = BOOT_G
    rp["🔴 칸"] = reps_all
    rp["통과"] = bool(len(reps_all) == len(NB_GRID) * len(U_REG))
    LG.write_stamped(str(OUT / "out983_reps.json"), rp, ref, cs0, t0, RAN, LG.DATA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wire", "grid"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wire": stage_wire, "grid": stage_grid}[a.stage](a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
