#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""982 — 🔴🔴🔴 **시간 방향 유보** (축 C1 상태→예측 · 곁 C3).

사전등록 `docs/prereg_982_timeforward.md` §2 를 그대로 따른다.

🔴 **왜.** 976 이 시간 분할을 **개체 묶음 5 겹 OOF** 로 바꾸면서 유보가 **미래**가 아니라
**같은 시대의 다른 개체**가 됐다 — 예측이 아니라 **보간**이다. 티처 #114~#120 이
여덟 사이클 연속으로 이 자리를 지목했다.

🔴 **티처 #120 의 판정문**: *「자 전쟁은 네 사이클을 써서 L1 0.004(977 이탈폭의 0.4257%)를
움직였다. 남은 유일한 정당화는 「시간 방향 예측에서 자가 갈리는가」다. 없으면 자 논의를 닫아라.」*

그래서 이 러너는 하나만 한다 — **시간 축으로 자르고, 뒤를 못 본 채 앞으로 예측하고,
자 여섯이 «거기서» 갈리는지 잰다.** 판정 규칙은 사전등록 §2-4 에 **측정 전에** 박혀 있다.

씀:
    python3 runners/tfwd982.py --stage wiring --ref <40자 sha>
    python3 runners/tfwd982.py --stage tfwd   --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
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
import runners.layers957 as L                     # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler978 as R8                             # noqa: E402
import ruler979 as R9                             # noqa: E402
import mix980 as M8                               # noqa: E402
import pick981 as PK                              # noqa: E402

RAN = ("runners/tfwd982.py", "runners/pick981.py", "runners/mix980.py",
       "runners/ruler979.py", "runners/ruler978.py", "runners/alpha977.py",
       "runners/ledger.py", "runners/layers957.py", "runners/predict971.py",
       "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out982_progress.txt"

RULERS = R9.RULERS
SEEDS = A.SEEDS
U_REG = A.U_REG
ALPHA_BASE = A.ALPHA_BASE
K_FEAT = M8.K_FEAT
MIN_HO = A.MIN_HO

# ── 사전등록 §2-1·§8-2 상수 (측정 전에 박았다) ─────────────────────────
NBLOCK = 5                     # 시간 블록 수(20/40/60/80 분위 절단)
N_B = A.N_B                    # 예산 1800 — `alpha977.N_B` 를 이름으로 인용
BOOT_T = 200                   # 시간 방향 짝 SE 복제
N_WRECK = R9.N_WRECK           # 섞기 씨앗 다섯 → 점추정·SE 둘 다 25 벌
WRECK_SEED0 = R9.WRECK_SEED0
WRECKS_Y = R8.WRECKS_Y
ARM_C = M8.ARM_C
ARM_S = M8.ARM_S
BAND = PK.BAND


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
# §1 🔴🔴🔴 시간 방향 풀 — **유보는 «미래»다**
# ══════════════════════════════════════════════════════════════════════
class TPool(A.Pool):
    """🔴 `alpha977.Pool` 의 자료를 그대로 쓰되 **겹을 시간이 정한다.**

    * `blk` — base 행의 시간 블록(0~4). 절단은 `언제` 의 20/40/60/80 분위.
    * 원점 `k = 1..4` — 학습은 블록 `<k`, 유보는 블록 `k`.
    * **hplt 학습 행도 절단보다 «앞»이어야 한다**(안 그러면 미래가 샌다).
    * 유보 전량 = 블록 1~4 합집합 · 게이트 = 그 합집합에서 `n_d ≥ 20`.

    🔴 **씨앗은 겹을 못 흔든다** — 시간이 겹을 정한다. 씨앗은 **뽑기 차례**만 흔든다.
    """

    def __init__(self, nblock=NBLOCK):
        A.Pool.__init__(self)
        self.nblock = int(nblock)
        t = self.tb
        qs = [(i + 1.0) / self.nblock for i in range(self.nblock - 1)]
        self.qs = qs
        self.cuts = [int(math.ceil(float(np.quantile(t, q)))) for q in qs]
        self.edges = [-10 ** 9] + list(self.cuts) + [10 ** 9]
        self.blk = np.zeros(len(t), dtype=np.int64)
        for k in range(self.nblock):
            self.blk[(t >= self.edges[k]) & (t < self.edges[k + 1])] = k
        self.origins = list(range(1, self.nblock))
        self.ho_all = self.blk >= 1
        cnt = collections.Counter(self.db[self.ho_all].tolist())
        self.dom_ho = {d: int(cnt.get(d, 0)) for d in self.doms}
        self.gated = [d for d in self.doms if cnt.get(d, 0) >= MIN_HO]
        self.ho_mask = {d: ((self.db == d) & self.ho_all) for d in self.gated}
        self._selh_cache = {}

    # 🔴 겹을 씨앗이 못 정한다 — 시간이 정한다
    def reseed(self, seed):
        self.seed = int(seed)
        self.perm_b = np.random.RandomState(self.seed + 1).permutation(len(self.yb))
        self.perm_h = np.random.RandomState(self.seed + 2).permutation(len(self.yh))
        self._selh_cache = {}
        return self

    def blocks_table(self):
        rows = collections.OrderedDict()
        for k in range(self.nblock):
            m = self.blk == k
            c = collections.Counter(self.db[m].tolist())
            rows["블록 %d" % k] = collections.OrderedDict([
                ("행 수", int(m.sum())),
                ("처음", _iso(self.tb[m].min())), ("끝", _iso(self.tb[m].max())),
                ("도메인별", collections.OrderedDict(
                    sorted(((d, int(n)) for d, n in c.items()), key=lambda x: -x[1]))),
            ])
        return rows


def _selh_t(pool, k, alpha, n_b, arm, tgt=None):
    """🔴 hplt 학습 행 — **절단 `k` 보다 앞선 행만** 뽑는다(미래 금지)."""
    key = (int(pool.seed), int(k), int(n_b), arm,
           None if tgt is None else tuple(sorted(tgt.items())))
    if key in pool._selh_cache:
        return pool._selh_cache[key]
    cut = pool.edges[k]
    past_h = pool.th < cut
    order = pool.perm_h[past_h[pool.perm_h]]        # 🔴 두 팔이 같은 차례를 쓴다
    nh = int(round(alpha * n_b))
    if arm == ARM_C:
        selh = order[:nh]
        q, bound, short = None, collections.OrderedDict(), max(0, nh - len(selh))
    else:
        have = collections.Counter(pool.dh[order].tolist())
        q, bound, short = _quota_t(pool, nh, have, tgt)
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
        selh = np.asarray(keep, dtype=order.dtype)
    pool._selh_cache[key] = (selh, q, bound, int(short))
    return pool._selh_cache[key]


def _quota_t(pool, nh, have, tgt=None):
    """`mix980.quota` 와 같은 최대잔여법. 🔴 **공급은 「절단 앞의 hplt」로만 센다.**"""
    doms = list(pool.gated)
    if tgt is None:
        tgt = {d: float(pool.ho_mask[d].sum()) for d in doms}
    else:
        tgt = dict(tgt)
    q = {d: 0 for d in doms}
    bound = collections.OrderedDict()
    left = int(nh)
    free = [d for d in doms if have.get(d, 0) > 0]
    for _ in range(len(doms) + 2):
        if left <= 0 or not free:
            break
        s = sum(tgt[d] for d in free)
        if s <= 0:
            break
        raw = {d: left * tgt[d] / s for d in free}
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


def _selb_t(pool, k, alpha, n_b):
    """base 학습 행 — **블록 `<k` 만.**"""
    past_b = pool.blk < k
    nh = int(round(alpha * n_b))
    nb = n_b - nh
    return pool.perm_b[past_b[pool.perm_b]][:nb]


def oof_t(pool, alpha, lam, n_b, arm, tgt=None, k=K_FEAT, wreck=None,
          tr_boot=None, leak=False):
    """🔴 **원점 넷의 앞→뒤 예측.** `leak=True` 면 «일부러» 미래를 흘린다(배선 변이체).

    돌려주는 `예측` 은 base 전 행 길이이고 **블록 1~4 자리에만 값이 있다.**
    """
    pred = np.zeros(len(pool.yb))
    filled = np.zeros(len(pool.yb), dtype=bool)
    ntr, nsel_h, tmax_tr, tmin_te, ent_ov = [], [], [], [], []
    for j in pool.origins:
        if leak:
            #: 🔴 변이체 — 미래(블록 ≥ j)도 학습에 넣는다. W1 이 여기서 떨어져야 한다.
            past_b = np.ones(len(pool.yb), dtype=bool)
            selb = pool.perm_b[past_b[pool.perm_b]][:n_b - int(round(alpha * n_b))]
            selh, _q, _b, _s = _selh_t(pool, pool.nblock, alpha, n_b, arm, tgt)
        else:
            selb = _selb_t(pool, j, alpha, n_b)
            selh, _q, _b, _s = _selh_t(pool, j, alpha, n_b, arm, tgt)
        X, y, ent, nb_rows = A.design(pool, selb, selh, k)
        if wreck is not None:
            y, _n = A.wreck_y(y, nb_rows, wreck["kind"], wreck["seed"] + j,
                              wreck.get("n"))
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 982 * 100000)
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
        tr_t = np.concatenate([pool.tb[selb], pool.th[selh]])
        tmax_tr.append(int(tr_t.max()) if len(tr_t) else -10 ** 9)
        tmin_te.append(int(pool.tb[te].min()))
        ent_ov.append(int(len(set(pool.ecb[te].tolist()) &
                              set(np.concatenate([pool.ecb[selb],
                                                  pool.ech[selh]]).tolist()))))
    return {"예측": pred, "채운 자리": filled, "원점별 학습 행": ntr,
            "원점별 hplt 행": nsel_h, "원점별 학습 최대 시각": tmax_tr,
            "원점별 유보 최소 시각": tmin_te, "원점별 개체 교집합": ent_ov}


# ══════════════════════════════════════════════════════════════════════
# §2 점추정과 짝 SE
# ══════════════════════════════════════════════════════════════════════
def point(pool, R, alpha, lam, n_b, arm, tgt=None, wreck=None, nwreck=1):
    """겹 씨앗 다섯 × 섞기 씨앗 `nwreck` 벌 평균. 🔴 **씨앗 하나짜리 수를 안 만든다.**"""
    acc = {nm: [] for nm in RULERS}
    nh, ntr = [], []
    for s in SEEDS:
        pool.reseed(s)
        for ws in range(nwreck):
            w = None if wreck is None else dict(wreck,
                                                seed=WRECK_SEED0 + ws * 97)
            r = oof_t(pool, alpha, lam, n_b, arm, tgt, wreck=w)
            v, _p = R9.score6(pool, R, r["예측"])
            for nm in RULERS:
                acc[nm].append(v[nm])
            nh.append(r["원점별 hplt 행"][0])
            ntr.append(r["원점별 학습 행"][0])
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = _r(float(np.mean(acc[nm])))
        out[nm + " 벌 SD"] = _r(float(np.std(acc[nm], ddof=1)))
    out["🔴 벌 수"] = len(acc[RULERS[0]])
    out["🔴 원점당 hplt 학습 행"] = int(np.mean(nh))
    out["🔴 원점당 학습 행 전량"] = int(np.mean(ntr))
    return out


def se_paired(pool, R, alpha, lam, n_b, base_arm, arms, boot, nwreck=1, tag=""):
    """🔴🔴 **짝 SE** — 복제마다 «같은 붓스트랩·같은 원점»에서 대조와 처리를 같이 돌린다.

    `arms` = OrderedDict[팔 이름] -> {"arm":…, "tgt":…, "wreck":…}
    `base_arm` = {"arm":…, "tgt":…, "wreck":…} — 짝의 왼쪽.
    🔴 **점추정과 벌 수를 같게 한다**(`nwreck` 인자를 둘이 같이 쓴다).
    """
    names = list(arms)
    dd = {a: {nm: [] for nm in RULERS} for a in names}
    ctl = {nm: [] for nm in RULERS}
    t0 = time.time()
    for b in range(boot):
        bc = {nm: [] for nm in RULERS}
        bt = {a: {nm: [] for nm in RULERS} for a in names}
        for s in SEEDS:
            pool.reseed(s)
            for ws in range(nwreck):
                wb = base_arm.get("wreck")
                wb = None if wb is None else dict(wb, seed=WRECK_SEED0 + ws * 97)
                pc = oof_t(pool, alpha, lam, n_b, base_arm["arm"],
                           base_arm.get("tgt"), wreck=wb, tr_boot=b)["예측"]
                vc, _ = R9.score6(pool, R, pc)
                for nm in RULERS:
                    bc[nm].append(vc[nm])
                for a in names:
                    wa = arms[a].get("wreck")
                    wa = None if wa is None else dict(wa,
                                                      seed=WRECK_SEED0 + ws * 97)
                    pa = oof_t(pool, alpha, lam, n_b, arms[a]["arm"],
                               arms[a].get("tgt"), wreck=wa, tr_boot=b)["예측"]
                    va, _ = R9.score6(pool, R, pa)
                    for nm in RULERS:
                        bt[a][nm].append(va[nm] - vc[nm])
        for nm in RULERS:
            ctl[nm].append(float(np.mean(bc[nm])))
        for a in names:
            for nm in RULERS:
                dd[a][nm].append(float(np.mean(bt[a][nm])))
        if (b + 1) % 25 == 0:
            _prog("    %s 짝SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                   time.time() - t0))
    out = collections.OrderedDict()
    for a in names:
        out[a] = collections.OrderedDict(
            [(nm, _r(float(np.std(dd[a][nm], ddof=1)))) for nm in RULERS])
    out["🔴 대조 팔 SE"] = collections.OrderedDict(
        [(nm, _r(float(np.std(ctl[nm], ddof=1)))) for nm in RULERS])
    out["🔴 복제 수"] = boot
    out["🔴 벌 수(복제 하나 안에서)"] = len(SEEDS) * nwreck
    return out


def gate2(delta, se):
    return collections.OrderedDict([
        ("Δ", _r(delta)),
        ("🔴 짝 SE", _r(se)),
        ("🔴🔴 |Δ|/짝SE", _r(abs(delta) / se, 4) if (se and delta is not None) else None),
        ("🔴 Δ > 0", bool(delta is not None and delta > 0)),
        ("🔴🔴 Δ < 0 (파괴 조건 ①)", bool(delta is not None and delta < 0)),
        ("🔴🔴 |Δ| ≥ 2·짝SE (조건 ②)",
         bool(se and delta is not None and abs(delta) >= 2 * se)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §3 배선 W — 🔴 변이체 대조를 붙인다
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    pool = TPool()
    R = R9.Rulers6(pool)
    out = collections.OrderedDict()
    out["무엇"] = ("982 §2-2 — 🔴🔴 **시간 방향 유보의 배선**을 변이체 대조와 함께 잰다. "
                 "🔴 «떨어질 수 있는» 검사인지를 일부러 깨뜨려 보인다")
    out["🔴 축"] = "C1 상태→예측"
    out["사전등록"] = "docs/prereg_982_timeforward.md §2-1·§2-2"
    out["🔴🔴 시간 절단(분위)"] = [_r(q, 3) for q in pool.qs]
    out["🔴🔴 절단 날짜"] = [_iso(c) for c in pool.cuts]
    out["🔴 블록"] = pool.blocks_table()
    out["🔴🔴 원점"] = pool.origins
    out["🔴🔴 유보 전량 행 수(블록 1~4)"] = int(pool.ho_all.sum())
    out["🔴 게이트 도메인"] = list(pool.gated)
    out["🔴🔴 시간 방향 유보의 도메인별 행"] = collections.OrderedDict(
        [(d, int(pool.ho_mask[d].sum())) for d in pool.gated])

    #: 🔴 개체 묶음 판(981)과 견준다 — **자 가중이 바뀌는가**
    epool = A.Pool()
    out["🔴🔴 개체 묶음 판(981)의 도메인별 유보 행"] = collections.OrderedDict(
        [(d, int(epool.ho_mask[d].sum())) for d in epool.gated])
    ER = R9.Rulers6(epool)
    doms = [d for d in pool.gated if d in epool.gated]
    l1 = collections.OrderedDict()
    for nm in RULERS:
        a = PK._nor({d: R.all_w()[nm][d] for d in doms}, doms)
        b = PK._nor({d: ER.all_w()[nm][d] for d in doms}, doms)
        l1[nm] = _r(sum(abs(a[d] - b[d]) for d in doms))
    out["🔴🔴🔴 자별 가중 L1(시간 방향 대 개체 묶음)"] = l1
    out["🔴 P1 — 유보 행 벡터가 다른가"] = bool(
        [int(pool.ho_mask[d].sum()) for d in doms] !=
        [int(epool.ho_mask[d].sum()) for d in doms])

    # ── W1~W3 : 정본 배선 · 변이체 ────────────────────────────────────
    pool.reseed(SEEDS[0])
    r_ok = oof_t(pool, ALPHA_BASE, 10.0 ** U_REG[1], N_B, ARM_C)
    r_bad = oof_t(pool, ALPHA_BASE, 10.0 ** U_REG[1], N_B, ARM_C, leak=True)
    w1_ok = all(a < b for a, b in zip(r_ok["원점별 학습 최대 시각"],
                                      r_ok["원점별 유보 최소 시각"]))
    w1_bad = all(a < b for a, b in zip(r_bad["원점별 학습 최대 시각"],
                                       r_bad["원점별 유보 최소 시각"]))
    out["W1 🔴🔴 학습이 언제나 유보보다 앞인가"] = collections.OrderedDict([
        ("원점별 학습 최대 시각", [_iso(x) for x in r_ok["원점별 학습 최대 시각"]]),
        ("원점별 유보 최소 시각", [_iso(x) for x in r_ok["원점별 유보 최소 시각"]]),
        ("🔴 정본 배선에서 참인가", bool(w1_ok)),
        ("🔴🔴 일부러 미래를 흘린 변이체에서 «거짓»인가", bool(not w1_bad)),
        ("🔴 이 검사가 떨어질 수 있나(구성상 참이 아닌가)", bool(w1_ok and not w1_bad)),
        ("통과", bool(w1_ok and not w1_bad)),
    ])
    out["W2 🔴 학습·유보의 개체 교집합(원점별)"] = collections.OrderedDict([
        ("원점별 교집합 수", r_ok["원점별 개체 교집합"]),
        ("🔴 합", int(sum(r_ok["원점별 개체 교집합"]))),
        ("🔴 이 수가 뜻하는 것",
         "🔴 시간 절단이 «개체 분리»도 같이 만들었나. 0 이면 시간 방향 유보가 "
         "개체 묶음 유보보다 **엄하다**(둘 다 만족). 이 칸은 «주장이 아니라 수»다"),
        ("통과", True),
    ])
    past_ok = []
    for j in pool.origins:
        selh, _q, _b, _s = _selh_t(pool, j, ALPHA_BASE, N_B, ARM_C)
        past_ok.append(bool(len(selh) == 0 or
                            int(pool.th[selh].max()) < pool.edges[j]))
    out["W3 🔴 hplt 학습 행도 절단보다 앞인가"] = collections.OrderedDict([
        ("원점별", past_ok), ("통과", bool(all(past_ok)))])
    s1 = collections.OrderedDict([
        ("유보 y sha256", _sha_arr(pool.yb)),
        ("유보 마스크 sha256",
         _sha_arr(np.vstack([pool.ho_mask[d] for d in pool.gated]))),
        ("유보 행 수", int(pool.ho_all.sum())),
    ])
    out["W4 🔴 유보 지문(주행 시작)"] = s1
    out["🔴 채운 유보 자리"] = int(r_ok["채운 자리"].sum())
    out["🔴 유보 전량과 같은가"] = bool(int(r_ok["채운 자리"].sum()) ==
                              int(pool.ho_all.sum()))
    out["통과"] = bool(out["W1 🔴🔴 학습이 언제나 유보보다 앞인가"]["통과"]
                     and out["W3 🔴 hplt 학습 행도 절단보다 앞인가"]["통과"]
                     and out["🔴 유보 전량과 같은가"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **원점 넷 전부에서 학습의 마지막 시각이 유보의 첫 시각보다 앞이고, "
        "일부러 미래를 흘린 변이체에서는 그 검사가 «떨어진다»**(구성상 참이 아니다). "
        "🔴 그리고 유보 전량이 예측으로 채워졌다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4 🔴🔴🔴 본 측정 — 자 여섯이 시간 방향에서 갈리나
# ══════════════════════════════════════════════════════════════════════
def _diverge(deltas, ses):
    """사전등록 §2-4 ⓐ·ⓑ 와 분기비. `deltas`/`ses` = {자: 값}."""
    signs = {nm: (0 if deltas[nm] == 0 else (1 if deltas[nm] > 0 else -1))
             for nm in RULERS}
    gates = {nm: bool(ses[nm] and abs(deltas[nm]) >= 2 * ses[nm]) for nm in RULERS}
    vals = [deltas[nm] for nm in RULERS]
    med = float(np.median([ses[nm] for nm in RULERS]))
    return collections.OrderedDict([
        ("🔴 자별 Δ", collections.OrderedDict([(nm, _r(deltas[nm])) for nm in RULERS])),
        ("🔴 자별 짝SE", collections.OrderedDict([(nm, _r(ses[nm])) for nm in RULERS])),
        ("🔴 자별 |Δ|/짝SE", collections.OrderedDict(
            [(nm, _r(abs(deltas[nm]) / ses[nm], 4) if ses[nm] else None)
             for nm in RULERS])),
        ("🔴 자별 부호", signs),
        ("🔴 자별 2·짝SE 관문", gates),
        ("🔴🔴 ⓐ 부호가 자에 따라 갈리나", bool(len(set(signs.values())) > 1)),
        ("🔴🔴 ⓑ 관문이 자에 따라 갈리나", bool(len(set(gates.values())) > 1)),
        ("🔴 자 여섯 Δ 의 폭(최대−최소)", _r(max(vals) - min(vals))),
        ("🔴 자 여섯 짝SE 의 중앙값", _r(med)),
        ("🔴🔴 분기비 = 폭 / 짝SE 중앙값", _r((max(vals) - min(vals)) / med, 4)
         if med else None),
    ])


def _spear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(P.spear(a, b))


def stage_tfwd(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    pool = TPool()
    R = R9.Rulers6(pool)
    s0 = _sha_arr(pool.yb)
    out = collections.OrderedDict()
    out["무엇"] = ("982 §2 — 🔴🔴🔴 **시간 방향 유보에서 자 여섯이 갈리는가.** "
                 "판정 규칙은 사전등록 §2-4 에 «측정 전에» 박혀 있다")
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["사전등록"] = "docs/prereg_982_timeforward.md §2"
    out["🔴 티처"] = ("🔴 티처 #120 — 「자 전쟁은 네 사이클을 써서 L1 0.004 를 움직였다. "
                    "남은 유일한 정당화는 「시간 방향 예측에서 자가 갈리는가」다」")
    out["🔴 예산 N_B"] = N_B
    out["🔴 α"] = ALPHA_BASE
    out["🔴 λ"] = ["10^%d" % u for u in U_REG]
    out["🔴 원점"] = pool.origins
    out["🔴 절단 날짜"] = [_iso(c) for c in pool.cuts]
    out["🔴 시간 방향 유보 도메인별 행"] = collections.OrderedDict(
        [(d, int(pool.ho_mask[d].sum())) for d in pool.gated])
    out["🔴🔴 자별 가중 표(시간 방향)"] = R.table()["자별 가중"]

    cells = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        _prog("λ=10^%d — D 팔(파괴 넷) 점추정 25 벌" % u)
        base = point(pool, R, ALPHA_BASE, lam, N_B, ARM_C, None,
                     wreck=None, nwreck=1)
        wr_pt = collections.OrderedDict()
        for wn, wr in WRECKS_Y.items():
            wr_pt[wn] = point(pool, R, ALPHA_BASE, lam, N_B, ARM_C, None,
                              wreck=dict(wr), nwreck=N_WRECK)
        _prog("λ=10^%d — D 팔 짝SE 복제 %d (25 벌)" % (u, BOOT_T))
        d_arms = collections.OrderedDict(
            [(wn, {"arm": ARM_C, "tgt": None, "wreck": dict(wr)})
             for wn, wr in WRECKS_Y.items()])
        d_se = se_paired(pool, R, ALPHA_BASE, lam, N_B,
                         {"arm": ARM_C, "tgt": None, "wreck": None},
                         d_arms, BOOT_T, nwreck=N_WRECK, tag="D λ=10^%d" % u)

        _prog("λ=10^%d — M 팔(㉮ 층화) 점추정 5 벌" % u)
        m_pt = point(pool, R, ALPHA_BASE, lam, N_B, ARM_S, None, nwreck=1)
        _prog("λ=10^%d — M 팔 짝SE 복제 %d (5 벌)" % (u, BOOT_T))
        m_se = se_paired(pool, R, ALPHA_BASE, lam, N_B,
                         {"arm": ARM_C, "tgt": None, "wreck": None},
                         collections.OrderedDict([("㉮ 층화(유보 목표)",
                                                   {"arm": ARM_S, "tgt": None,
                                                    "wreck": None})]),
                         BOOT_T, nwreck=1, tag="M λ=10^%d" % u)

        cell = collections.OrderedDict()
        cell["🔴 대조 팔 점추정(자 여섯)"] = collections.OrderedDict(
            [(nm, base[nm]) for nm in RULERS])
        cell["🔴 D 팔"] = collections.OrderedDict()
        for wn in WRECKS_Y:
            dl = {nm: wr_pt[wn][nm] - base[nm] for nm in RULERS}
            se = {nm: d_se[wn][nm] for nm in RULERS}
            cell["🔴 D 팔"][wn] = collections.OrderedDict([
                ("🔴 파괴 팔 점추정", collections.OrderedDict(
                    [(nm, wr_pt[wn][nm]) for nm in RULERS])),
                ("🔴🔴 자별 판정", collections.OrderedDict(
                    [(nm, gate2(dl[nm], se[nm])) for nm in RULERS])),
                ("🔴🔴🔴 갈리나", _diverge(dl, se)),
                ("🔴 벌 수", wr_pt[wn]["🔴 벌 수"]),
            ])
        dl_m = {nm: m_pt[nm] - base[nm] for nm in RULERS}
        se_m = {nm: m_se["㉮ 층화(유보 목표)"][nm] for nm in RULERS}
        cell["🔴🔴 M 팔 ㉮ 층화 − ㉯ 대조"] = collections.OrderedDict([
            ("🔴 층화 팔 점추정", collections.OrderedDict(
                [(nm, m_pt[nm]) for nm in RULERS])),
            ("🔴🔴 자별 판정", collections.OrderedDict(
                [(nm, gate2(dl_m[nm], se_m[nm])) for nm in RULERS])),
            ("🔴🔴🔴 갈리나", _diverge(dl_m, se_m)),
            ("🔴 벌 수", m_pt["🔴 벌 수"]),
        ])
        cell["🔴 복제 수"] = BOOT_T
        cells["u=%d" % u] = cell

    # ── §2-4 ⓒ : `v2.2` 를 시간 방향 `D4` 입력에 그대로 물린다 ────────
    d4 = "D4 학습 y 전량(둘 다)"
    rows_B = collections.OrderedDict()
    share_cf = {}
    tbl = R.table()["자별 가중"]
    for nm in RULERS:
        share_cf[nm] = tbl[nm]["🔴🔴 가장 큰 도메인의 몫"]
    for nm in RULERS:
        pw, ok = [], True
        for u in U_REG:
            g = cells["u=%d" % u]["🔴 D 팔"][d4]["🔴🔴 자별 판정"][nm]
            ok = ok and bool(g["🔴🔴 Δ < 0 (파괴 조건 ①)"] and g["🔴🔴 |Δ| ≥ 2·짝SE (조건 ②)"])
            pw.append(g["🔴🔴 |Δ|/짝SE"] or 0.0)
        rows_B[nm] = {"통과": ok, "검정력": min(pw), "몫": share_cf[nm]}
    #: 🔴 체제 B = 980 이 `docs/목표.md` 에 «글자로 선언한» 판(닫힌꼴 몫 · 뽑기판을 접는다)
    picked = PK.pick(rows_B, BAND)
    out["🔴🔴🔴 §2-4 ⓒ — 시간 방향 `D4` 에 `v2.2` 를 물린 결과(체제 B)"] = \
        collections.OrderedDict([
            ("🔴 입력(자별 통과·검정력·몫)", collections.OrderedDict(
                [(nm, collections.OrderedDict([
                    ("통과", rows_B[nm]["통과"]),
                    ("검정력", _r(rows_B[nm]["검정력"], 4)),
                    ("몫", _r(rows_B[nm]["몫"]))])) for nm in RULERS])),
            ("🔴 `pick()` 산출물", picked),
            ("🔴🔴🔴 시간 방향이 고른 자", picked["🔴🔴🔴 고른 자"]),
            ("🔴🔴 개체 묶음 판(981 체제 B)이 고른 자", "R_pool 묶음"),
            ("🔴🔴🔴 ⓒ 선택이 갈리나",
             bool(picked["🔴🔴🔴 고른 자"] != "R_pool 묶음")),
        ])

    # ── 🔴🔴🔴 등록 판정 ────────────────────────────────────────────
    sign_any, gate_any, ratios = False, False, []
    detail = collections.OrderedDict()
    for u in U_REG:
        for wn in WRECKS_Y:
            dv = cells["u=%d" % u]["🔴 D 팔"][wn]["🔴🔴🔴 갈리나"]
            detail["u=%d · %s" % (u, wn)] = collections.OrderedDict([
                ("ⓐ 부호", dv["🔴🔴 ⓐ 부호가 자에 따라 갈리나"]),
                ("ⓑ 관문", dv["🔴🔴 ⓑ 관문이 자에 따라 갈리나"]),
                ("분기비", dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"])])
            sign_any |= dv["🔴🔴 ⓐ 부호가 자에 따라 갈리나"]
            gate_any |= dv["🔴🔴 ⓑ 관문이 자에 따라 갈리나"]
            if dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"] is not None:
                ratios.append(dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"])
        dv = cells["u=%d" % u]["🔴🔴 M 팔 ㉮ 층화 − ㉯ 대조"]["🔴🔴🔴 갈리나"]
        detail["u=%d · M 팔 ㉮−㉯" % u] = collections.OrderedDict([
            ("ⓐ 부호", dv["🔴🔴 ⓐ 부호가 자에 따라 갈리나"]),
            ("ⓑ 관문", dv["🔴🔴 ⓑ 관문이 자에 따라 갈리나"]),
            ("분기비", dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"])])
        sign_any |= dv["🔴🔴 ⓐ 부호가 자에 따라 갈리나"]
        gate_any |= dv["🔴🔴 ⓑ 관문이 자에 따라 갈리나"]
        if dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"] is not None:
            ratios.append(dv["🔴🔴 분기비 = 폭 / 짝SE 중앙값"])
    pick_diff = out["🔴🔴🔴 §2-4 ⓒ — 시간 방향 `D4` 에 `v2.2` 를 물린 결과(체제 B)"][
        "🔴🔴🔴 ⓒ 선택이 갈리나"]
    diverged = bool(sign_any or gate_any or pick_diff)
    out["🔴🔴🔴 §2-4 등록 판정 — 자가 시간 방향에서 갈리나"] = collections.OrderedDict([
        ("🔴 판정 규칙의 출처", "docs/prereg_982_timeforward.md §2-4 (측정 전 커밋)"),
        ("🔴 팔·λ 별", detail),
        ("🔴🔴 ⓐ 부호가 어디서라도 갈리나", bool(sign_any)),
        ("🔴🔴 ⓑ 관문이 어디서라도 갈리나", bool(gate_any)),
        ("🔴🔴 ⓒ `v2.2` 선택이 갈리나", bool(pick_diff)),
        ("🔴 분기비 최대", _r(max(ratios), 4) if ratios else None),
        ("🔴 분기비 중앙값", _r(float(np.median(ratios)), 4) if ratios else None),
        ("🔴 분기비가 모든 칸에서 1 미만인가",
         bool(ratios and max(ratios) < 1.0)),
        ("🔴🔴🔴 갈리는가", diverged),
        ("🔴🔴🔴 그래서 자 논의는",
         "🔴 **살아 있다 — 시간 방향에서 자가 답을 바꾼다**" if diverged else
         "🔴🔴 **닫는다 — 시간 방향에서 자 여섯이 같은 답을 낸다**"),
    ])
    out["🔴🔴 칸"] = cells
    out["🔴 유보 지문(시작=끝)"] = collections.OrderedDict([
        ("시작", s0), ("끝", _sha_arr(pool.yb)), ("같은가", bool(s0 == _sha_arr(pool.yb)))])
    out["통과"] = bool(s0 == _sha_arr(pool.yb) and len(pool.gated) > 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **주행 중 유보를 한 줄도 안 만졌고 게이트 도메인이 비지 않았다.** "
        "🔴 「갈리는가」의 답은 `통과` 가 아니라 위의 «등록 판정» 칸이다 — "
        "어느 쪽이 나오든 그대로 싣는다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_tfwd.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["wiring", "tfwd"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "tfwd": stage_tfwd}[a.stage](a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
