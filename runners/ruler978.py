#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""978 — 🔴 **자를 올리는 조건에 「크기」를 넣고 977 의 정본 자 승격을 다시 판정한다**.

사전등록 `docs/prereg_978_ruler.md` 를 그대로 따른다. 축 **C3**(곁 **C2**).

🔴 티처 #116 이 실측으로 낸 것:
  ① 977 이 정본으로 올린 **도메인 균등 자가 자기 파괴 대조를 0/8 통과한다**.
  ② 그 자의 밑판 읽음이 **씨앗 5 중 3 에서 음수**다(0.025897 ± 0.066778).
  ③ 같은 등록 조건에 **두 값**이 커밋돼 있다(+0.086077 vs −0.023854 · 벌 수만 다르다).
  ④ 63 칸에서 그 자의 최적점이 **`u=−2 · α=0.95`**, 즉 HPLT 최대 설정이다.

🔴 **이 러너는 977 의 `alpha977` 을 그대로 물어서 돈다** — 자료·겹·뽑기 배관을 갈아
끼우지 않았다는 것을 `stage wiring` 이 **바이트로** 보인다(W1).

씀:
    python3 runners/ruler978.py --stage wiring    --ref <40자 sha>
    python3 runners/ruler978.py --stage ruler     --ref <40자 sha>
    python3 runners/ruler978.py --stage cond3     --ref <40자 sha>
    python3 runners/ruler978.py --stage size      --ref <40자 sha>
    python3 runners/ruler978.py --stage xdestroy  --ref <40자 sha>
    python3 runners/ruler978.py --stage alphafine --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
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
import loso974 as LO                              # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402

RAN = ("runners/ruler978.py", "runners/alpha977.py", "runners/ledger.py",
       "runners/layers957.py", "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out978_progress.txt"

# ── 사전등록 상수 (측정 전에 박았다 · §3) ──────────────────────────────
#: 🔴 **등록값을 여기 한 번만 적고 산출물이 이 상수를 그대로 싣는다.**
#: 977 은 사전등록 §3 에 400 을 적고 코드에 200 을 두었으며 **신고가 없었다**.
BOOT = 400                        # §3 이중 붓스트랩 뽑기
N_WRECK = 5                       # §3 파괴 섞기 씨앗 수 → 점추정 25 벌
PERM_NULL = 2000                  # §1 도메인 안 순열 귀무 뽑기
PERM_SEED = 978                   # §1 그 씨앗
WRECK_SEED0 = 978000              # 파괴 섞기 씨앗의 밑값
COND3_WRECKS = 40                 # §4-S2 조건 3 분포의 섞기 씨앗 수 (×5 겹씨앗 = 200 벌)
SEEDS = A.SEEDS                   # [976, 977, 978, 979, 980]
U_REG = A.U_REG                   # [0, 3]
ALPHA_BASE = A.ALPHA_BASE         # 0.95
THR_CARD = A.THR_CARD             # 0.00353
N_B = A.N_B                       # 1800
KFOLD = A.KFOLD
AFINE = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2]        # §4-S5

#: 🔴 977 산출물이 적은 두 수 — **손 전사가 아니라 파일에서 읽는다**(규칙 D).
D977 = OUT / "out977_destroy.json"
W977 = OUT / "out977_wiring.json"
G977 = OUT / "out977_grid.json"

RULERS = ("R_pool 묶음", "R_eq 균등", "R_z 순열SE 역가중", "R_iv SE² 역가중")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))


def _r(x, n=6):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).is_file() else {}


# ══════════════════════════════════════════════════════════════════════
# §1 자 넷 — 가중치는 **한 번만** 만든다
# ══════════════════════════════════════════════════════════════════════
def perm_null_sd(y, n_perm=PERM_NULL, seed=PERM_SEED):
    """🔴 **도메인 안 순열 귀무**의 스피어만 표준편차.

    고정 벡터(`arange`)와 **섞은 `y`** 의 상관을 `n_perm` 번 잰다. 이 값은
    **그 도메인의 유보 행 수와 동률 구조만의 함수**이고 **예측을 안 본다** —
    그래서 자가 결과의 함수가 되는 순환이 안 닫힌다(`docs/루프.md` v4.0 §0).
    """
    y = np.asarray(y, float)
    n = len(y)
    if n < 3:
        return float("nan")
    ref = np.arange(n, dtype=float)
    rng = np.random.RandomState(seed)
    vals = np.empty(n_perm)
    for i in range(n_perm):
        vals[i] = P.spear(y[rng.permutation(n)], ref)
    return float(np.std(vals, ddof=1))


class Rulers(object):
    """자 넷의 가중치. 🔴 **팔·뽑기와 무관하게 한 번만 만든다.**"""

    def __init__(self, pool):
        self.doms = list(pool.gated)
        self.n = {d: int(pool.ho_mask[d].sum()) for d in self.doms}
        self.sd = collections.OrderedDict()
        for d in self.doms:
            self.sd[d] = perm_null_sd(pool.yb[pool.ho_mask[d]])
        self.w = collections.OrderedDict()
        self.w["R_eq 균등"] = {d: 1.0 for d in self.doms}
        self.w["R_z 순열SE 역가중"] = {d: 1.0 / self.sd[d] for d in self.doms}
        self.w["R_iv SE² 역가중"] = {d: 1.0 / (self.sd[d] ** 2) for d in self.doms}
        #: 🔴 `R_pool` 은 **그 뽑기의 행 수**를 쓴다 — 977 의 `score()` 와 같게 두어
        #: 바이트 재현이 되게 한다(W1).

    def table(self):
        out = collections.OrderedDict()
        rows = collections.OrderedDict()
        wp = {d: float(self.n[d]) for d in self.doms}
        allw = collections.OrderedDict([("R_pool 묶음", wp)] +
                                       [(k, v) for k, v in self.w.items()])
        for nm, w in allw.items():
            s = sum(w.values())
            nor = {d: w[d] / s for d in self.doms}
            top = max(self.doms, key=lambda d: nor[d])
            rows[nm] = {
                "정규화 가중": {d: _r(nor[d]) for d in self.doms},
                "🔴 가장 큰 도메인": top,
                "🔴🔴 가장 큰 도메인의 몫": _r(nor[top]),
                "🔴 유효 도메인 수 (1/Σw²)": _r(1.0 / sum(v * v for v in nor.values()), 4),
            }
        out["자별 가중"] = rows
        out["도메인별 유보 행"] = self.n
        out["🔴 도메인 안 순열 귀무 SD"] = {d: _r(self.sd[d]) for d in self.doms}
        out["🔴 순열 뽑기"] = PERM_NULL
        out["🔴 순열 씨앗"] = PERM_SEED
        out["🔴 21 행 아이돌과 1,288 행 세계애니의 귀무 SD 비"] = _r(
            max(self.sd.values()) / min(self.sd.values()), 4)
        out["통과"] = bool(all(np.isfinite(v) for v in self.sd.values()))
        out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
            "게이트 도메인 전부에서 귀무 SD 가 유한하다 = 자 넷이 전부 정의된다")
        return out


def score4(pool, R, pred, ho_idx=None):
    """🔴 자 **넷을 한 번에** 낸다(반증조건 4 — 격자 stage 밖에서도 넷을 다 낸다)."""
    per, lens = collections.OrderedDict(), collections.OrderedDict()
    for d in pool.gated:
        if ho_idx is None:
            m = pool.ho_mask[d]
            a, b = pred[m], pool.yb[m]
        else:
            idx = ho_idx[d]
            a, b = pred[idx], pool.yb[idx]
        per[d] = float(P.spear(a, b))
        lens[d] = float(len(a))
    ok = [d for d in pool.gated if np.isfinite(per[d])]
    out = collections.OrderedDict()
    if not ok:
        for nm in RULERS:
            out[nm] = float("nan")
        return out, per
    wp = np.asarray([lens[d] for d in ok], float)
    v = np.asarray([per[d] for d in ok], float)
    out["R_pool 묶음"] = float((v * wp).sum() / wp.sum())
    for nm in ("R_eq 균등", "R_z 순열SE 역가중", "R_iv SE² 역가중"):
        w = np.asarray([R.w[nm][d] for d in ok], float)
        out[nm] = float((v * w).sum() / w.sum())
    return out, per


# ══════════════════════════════════════════════════════════════════════
# 파괴 — 라벨 쪽(977 그대로) + 🔴 **특징 `x` 쪽(978 신설)**
# ══════════════════════════════════════════════════════════════════════
def wreck_x(X, nb_rows, kind, seed, n=None):
    """🔴 §4-S4 — **학습 특징 행렬의 행을 구간 안에서 섞는다**(유보는 인자에 없다).

    `X` 앞 `nb_rows` 개가 base, 나머지가 hplt 다(`design` 이 그 차례로 쌓는다).
    🔴 라벨을 섞는 것과 **짝**이다 — 같은 구간·같은 씨앗 규칙.
    """
    X = X.copy()
    rng = np.random.RandomState(seed)
    segs = {"base": (0, nb_rows), "hplt": (nb_rows, len(X)), "both": (0, len(X))}
    a, b = segs[kind]
    idx = np.arange(a, b)
    if n is not None and n < len(idx):
        idx = rng.choice(idx, size=n, replace=False)
    if len(idx) > 1:
        X[idx] = X[rng.permutation(idx)]
    return X, int(len(idx))


def oof978(pool, alpha, lam, k=6, drop_src=(), fill=True,
           wreck=None, wreck_x_=None, tr_boot=None):
    """977 의 `oof` 와 **같은 배관**이고 `wreck_x_` 하나만 더 받는다.

    🔴 `wreck_x_ is None` 이면 `alpha977.oof` 와 **바이트로 같은 예측**을 내야 한다(W1).
    """
    pred = np.zeros(len(pool.yb))
    ntr, wrecked, wrecked_x = [], 0, 0
    for j in range(KFOLD):
        selb, selh, _s = A.select(pool, j, alpha, drop_src, fill=fill)
        X, y, ent, nb = A.design(pool, selb, selh, k)
        if wreck is not None:
            y, wrecked = A.wreck_y(y, nb, wreck["kind"], wreck["seed"] + j,
                                   wreck.get("n"))
        if wreck_x_ is not None:
            X, wrecked_x = wreck_x(X, nb, wreck_x_["kind"], wreck_x_["seed"] + j,
                                   wreck_x_.get("n"))
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 977 * 100000)
            order, st, en = A.groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y = X[idx], y[idx]
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        ntr.append(int(len(y)))
    return {"예측": pred, "겹별 학습 행": ntr,
            "부순 라벨 행(겹당)": wrecked, "부순 특징 행(겹당)": wrecked_x}


WRECKS_Y = collections.OrderedDict([
    ("D1 hplt y 전량", {"kind": "hplt", "n": None}),
    ("D2 base 학습 y 전량", {"kind": "base", "n": None}),
    ("D3 hplt y 중 무작위 90 행", {"kind": "hplt", "n": 90}),
    ("D4 학습 y 전량(둘 다)", {"kind": "both", "n": None}),
])
WRECKS_X = collections.OrderedDict([
    ("X1 hplt x 전량", {"kind": "hplt", "n": None}),
    ("X2 base 학습 x 전량", {"kind": "base", "n": None}),
    ("X3 hplt x 중 무작위 90 행", {"kind": "hplt", "n": 90}),
    ("X4 학습 x 전량(둘 다)", {"kind": "both", "n": None}),
])


def point_over(pool, R, alpha, lam, wr=None, wx=None):
    """🔴 **25 벌**(겹 씨앗 5 × 섞기 씨앗 5) 평균. 씨앗 하나짜리 수를 안 만든다(반증조건 3)."""
    acc = {nm: [] for nm in RULERS}
    nwr, nwx = [], []
    nseed = N_WRECK if (wr is not None or wx is not None) else 1
    for s in SEEDS:
        pool.reseed(s)
        for ws in range(nseed):
            w1 = None if wr is None else dict(wr, seed=WRECK_SEED0 + ws * 97)
            w2 = None if wx is None else dict(wx, seed=WRECK_SEED0 + ws * 97)
            r = oof978(pool, alpha, lam, wreck=w1, wreck_x_=w2)
            v, _p = score4(pool, R, r["예측"])
            for nm in RULERS:
                acc[nm].append(v[nm])
            nwr.append(r["부순 라벨 행(겹당)"])
            nwx.append(r["부순 특징 행(겹당)"])
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = _r(float(np.mean(acc[nm])))
        out[nm + " 벌 SD"] = _r(float(np.std(acc[nm], ddof=1)))
    out["🔴 벌 수"] = len(acc[RULERS[0]])
    out["🔴 부순 라벨 행(겹당)"] = int(np.mean(nwr))
    out["🔴 부순 특징 행(겹당)"] = int(np.mean(nwx))
    out["_씨앗별"] = {nm: [_r(x) for x in acc[nm]] for nm in RULERS}
    return out


def se_double(pool, R, alpha, lam, arms, boot=BOOT):
    """🔴 **이중 붓스트랩** — 학습 개체 묶음 재표집 + 유보 개체 묶음 재표집.

    `arms` = {이름: (wreck, wreck_x)} · 밑판 대비 Δ 의 SD 를 자 넷마다 낸다.
    🔴 **뽑기 수는 등록 상수 `BOOT` 하나에서만 온다.**
    """
    acc = {a: {nm: [] for nm in RULERS} for a in arms}
    for s in SEEDS:
        pool.reseed(s)
        for b in range(boot):
            hi = A.ho_draw(pool, b)
            v0, _p = score4(pool, R, oof978(pool, alpha, lam,
                                            tr_boot=b)["예측"], hi)
            for a, (wr, wx) in arms.items():
                w1 = None if wr is None else dict(wr, seed=WRECK_SEED0)
                w2 = None if wx is None else dict(wx, seed=WRECK_SEED0)
                v, _p = score4(pool, R, oof978(pool, alpha, lam, tr_boot=b,
                                               wreck=w1, wreck_x_=w2)["예측"], hi)
                for nm in RULERS:
                    acc[a][nm].append(v[nm] - v0[nm])
        _prog("    SE 씨앗 %d 끝" % s)
    out = collections.OrderedDict()
    for a in arms:
        out[a] = collections.OrderedDict(
            [(nm, _r(float(np.std(acc[a][nm], ddof=1)))) for nm in RULERS])
        out[a]["🔴 뽑기 수"] = len(acc[a][RULERS[0]])
    return out


def adopt_row(delta, se):
    """🔴🔴 사전등록 §2 — 자를 정본으로 올리는 **세 조건**."""
    c1 = bool(delta is not None and delta < 0)
    c2 = bool(se and delta is not None and abs(delta) >= 2 * se)
    c3 = bool(delta is not None and abs(delta) >= THR_CARD)
    return collections.OrderedDict([
        ("Δ", _r(delta)), ("SE_이중", se),
        ("|Δ|/SE", _r(abs(delta) / se, 4) if (se and delta is not None) else None),
        ("🔴 조건 ① 부호 Δ < 0", c1),
        ("🔴 조건 ② |Δ| ≥ 2·SE", c2),
        ("🔴 조건 ③ |Δ| ≥ 0.00353", c3),
        ("🔴🔴 셋 다", bool(c1 and c2 and c3)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §4-S1 `ruler`
# ══════════════════════════════════════════════════════════════════════
def stage_ruler(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("ruler 시작")
    pool = A.Pool()
    R = Rulers(pool)
    _prog("가중치 완료")

    base = collections.OrderedDict()
    cells = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        b = point_over(pool, R, ALPHA_BASE, lam)
        base["u=%d" % u] = b
        for nm, w in WRECKS_Y.items():
            p = point_over(pool, R, ALPHA_BASE, lam, wr=w)
            cells["u=%d|%s" % (u, nm)] = p
            _prog("  점추정 u=%d %s" % (u, nm))

    _prog("ruler SE 시작 (뽑기 %d × 씨앗 %d)" % (BOOT, len(SEEDS)))
    t_b = time.time()
    se = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        arms = collections.OrderedDict(
            [(nm, (w, None)) for nm, w in WRECKS_Y.items()])
        se["u=%d" % u] = se_double(pool, R, ALPHA_BASE, lam, arms)
        _prog("  ruler SE u=%d 끝 (%.0fs)" % (u, time.time() - t_b))

    # ── 32 칸 (자 넷 × D1~D4 × λ 둘) ─────────────────────────
    grid = collections.OrderedDict()
    n_pass = {nm: 0 for nm in RULERS}
    for nm in RULERS:
        rows = collections.OrderedDict()
        for u in U_REG:
            for wn in WRECKS_Y:
                d = cells["u=%d|%s" % (u, wn)][nm] - base["u=%d" % u][nm]
                s_ = se["u=%d" % u][wn][nm]
                rr = adopt_row(d, s_)
                rows["u=%d|%s" % (u, wn)] = rr
                if rr["🔴🔴 셋 다"]:
                    n_pass[nm] += 1
        grid[nm] = {"칸별": rows,
                    "🔴🔴 여덟 칸 통과 분자/분모": "%d / %d" % (n_pass[nm], 2 * len(WRECKS_Y)),
                    "🔴 여덟 칸 SE 배수": [rows[k]["|Δ|/SE"] for k in rows]}

    # ── 🔴🔴🔴 §2 채택 판정 — D4 만 본다 (등록 규칙) ─────────────
    decide = collections.OrderedDict()
    for nm in RULERS:
        per_u = collections.OrderedDict()
        n_ok = 0
        for u in U_REG:
            rr = grid[nm]["칸별"]["u=%d|D4 학습 y 전량(둘 다)" % u]
            per_u["u=%d" % u] = rr
            n_ok += 1 if rr["🔴🔴 셋 다"] else 0
        wt = R.table()["자별 가중"][nm]
        decide[nm] = {
            "λ 둘": per_u,
            "🔴🔴🔴 등록 규칙 통과 (λ 둘 다)": bool(n_ok == len(U_REG)),
            "🔴 통과한 λ 칸": "%d / %d" % (n_ok, len(U_REG)),
            "🔴 가장 큰 도메인의 가중 몫": wt["🔴🔴 가장 큰 도메인의 몫"],
            "🔴 유효 도메인 수": wt["🔴 유효 도메인 수 (1/Σw²)"],
        }
    ok_rulers = [nm for nm in RULERS if decide[nm]["🔴🔴🔴 등록 규칙 통과 (λ 둘 다)"]]
    chosen = (min(ok_rulers, key=lambda nm: decide[nm]["🔴 가장 큰 도메인의 가중 몫"])
              if ok_rulers else None)

    # ── 🔴 1순위 ⓓ — 966~976 명제를 자 넷에서 다시 읽는다 ──────
    _prog("966~976 재독 시작")
    reread = collections.OrderedDict()
    #: 976 밑판 B — α=0.95 · u=3 · 겹 씨앗은 앞 사이클 것(976)
    pool.reseed(976)
    v976, per976 = score4(pool, R, oof978(pool, ALPHA_BASE, 1000.0)["예측"])
    w977 = _load(W977)
    tgt976 = None
    for kk, vv in (w977.get("W") or {}).items():
        if kk.startswith("W8 "):
            tgt976 = vv.get("🔴 실측")
    reread["976 밑판 B (씨앗 976 한 벌 · 🔴 대조용이고 본문에 안 싣는다)"] = {
        "자 넷": {nm: _r(v976[nm]) for nm in RULERS},
        "🔴 977 의 W8 이 적은 묶음 ρ(같은 한 벌)": tgt976,
        "🔴 바이트로 같은가": bool(tgt976 is not None
                            and _r(v976["R_pool 묶음"]) == tgt976),
        "🔴 이 수가 왜 대조용인가": "씨앗 하나짜리다(반증조건 3) — 배관 동일 증거로만 쓴다",
    }
    #: 977 LOSO 세 팔 — 자 넷으로
    loso = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        arms = collections.OrderedDict()
        for anm, drop in A.SRC_ARMS.items():
            acc = {nm: [] for nm in RULERS}
            for s in SEEDS:
                pool.reseed(s)
                v, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                               drop_src=drop)["예측"])
                for nm in RULERS:
                    acc[nm].append(v[nm])
            arms[anm] = collections.OrderedDict(
                [(nm, _r(float(np.mean(acc[nm])))) for nm in RULERS])
            arms[anm]["🔴 씨앗 수"] = len(SEEDS)
        for anm in arms:
            for nm in RULERS:
                arms[anm]["Δ · " + nm] = _r(arms[anm][nm] - arms["ALL"][nm])
        loso["u=%d" % u] = arms
    reread["977 LOSO 세 팔 — 자 넷"] = loso
    n_sign = sum(1 for u in U_REG
                 if loso["u=%d" % u]["−hplt_ko"]["Δ · R_pool 묶음"]
                 * loso["u=%d" % u]["−hplt_ko"]["Δ · R_eq 균등"] > 0)
    reread["🔴 −hplt_ko 의 Δ 부호가 두 자에서 같은 λ 칸"] = "%d / %d" % (n_sign, len(U_REG))

    out = collections.OrderedDict()
    out["무엇"] = ("978 §4-S1 — 🔴 **자 넷의 검정력**. 사전등록 §2 의 등록 규칙"
                 "(D4 파괴 대조가 부호 + 2·SE + 0.00353 을 λ 둘에서 다 넘어야 채택)을 적용한다")
    out["🔴 축"] = "C3 (곁 C2) — 정본 자는 C1~C6 이 전부 그 위에 선다"
    out["사전등록"] = "docs/prereg_978_ruler.md §1 · §2 · §4-S1"
    out["🔴 유보는 한 줄도 안 만졌다"] = True
    out["🔴 등록 상수"] = {"BOOT(이중 붓스트랩 뽑기)": BOOT, "섞기 씨앗 수": N_WRECK,
                     "점추정 벌 수": len(SEEDS) * N_WRECK, "겹 씨앗": SEEDS,
                     "순열 귀무 뽑기": PERM_NULL, "순열 씨앗": PERM_SEED,
                     "🔴 977 이 쓴 뽑기 수": 200,
                     "🔴 977 사전등록이 적은 뽑기 수": 400,
                     "🔴 977 이 그 차이를 신고했나": False}
    out["🔴🔴🔴 자 넷의 가중"] = R.table()
    out["🔴 밑판(파괴 안 함 · 25 벌 대신 5 벌 — 섞기 씨앗이 없다)"] = base
    out["🔴🔴🔴 파괴 대조 점추정(25 벌)"] = cells
    out["🔴 파괴 대조 SE(이중 붓스트랩)"] = se
    out["🔴🔴🔴 32 칸 — 자 넷 × D1~D4 × λ 둘"] = grid
    out["🔴🔴🔴 §2 채택 판정 (D4)"] = {
        "자별": decide,
        "🔴🔴 통과한 자": ok_rulers or "없음",
        "🔴🔴🔴 정본으로 고른 자": chosen or "🔴 없다 — 정본 자를 바꾸지 않는다",
        "🔴 고른 규칙": "λ 둘 다 통과한 자 중 **가장 큰 도메인의 몫이 가장 작은 자**",
        "🔴🔴 977 이 올린 자(R_eq 균등)가 이 규칙을 통과하나":
            bool("R_eq 균등" in ok_rulers),
        "🔴🔴🔴 977 의 승격을 되돌리나": bool("R_eq 균등" not in ok_rulers),
        "통과": bool(len(decide) == len(RULERS)),
        "🔴 이 절의 `통과` 가 뜻하는 것": "자 넷 전부에 같은 규칙을 걸었다",
    }
    out["🔴🔴 1순위 ⓓ — 966~976 명제를 새 자에서 다시 읽는다"] = reread
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_ruler.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("ruler 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S2 `cond3` — 🔴 조건 3 의 두 값이 왜 갈리나 (반증조건 5 / 2)
# ══════════════════════════════════════════════════════════════════════
def stage_cond3(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("cond3 시작")
    pool = A.Pool()
    R = Rulers(pool)
    lam = 10.0 ** U_REG[1]
    w = WRECKS_Y["D4 학습 y 전량(둘 다)"]

    # ── ① 977 의 두 수를 **각자의 설정에서** 재현한다 ──────────
    pool.reseed(SEEDS[0])
    b0, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam)["예측"])
    w4242, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                       wreck={"kind": w["kind"], "n": w["n"],
                                              "seed": 4242})["예측"])
    one = w4242["R_eq 균등"] - b0["R_eq 균등"]

    acc = {nm: [] for nm in RULERS}
    accb = {nm: [] for nm in RULERS}
    for s in SEEDS:
        pool.reseed(s)
        v0, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam)["예측"])
        for nm in RULERS:
            accb[nm].append(v0[nm])
        for ws in range(N_WRECK):
            v, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                           wreck={"kind": w["kind"], "n": w["n"],
                                                  "seed": 977000 + ws * 97})["예측"])
            for nm in RULERS:
                acc[nm].append(v[nm])
    #: 🔴 977 의 `destroy` 는 **밑판을 소수 여섯 자리로 반올림한 뒤** 빼서 Δ 를 냈다
    #: (`over_seeds` 가 `_r` 을 물고 나온다). 재현하려면 그 자리까지 같게 해야 한다.
    d25 = _r(float(np.mean(acc["R_eq 균등"]))
             - _r(float(np.mean(accb["R_eq 균등"]))))

    d977 = _load(D977)
    w977 = _load(W977)
    tgt_one = (w977.get("E", {}).get("E D4 학습 y 전량(둘 다)", {}).get("균등 Δ")
               if w977 else None)
    tgt_25 = (d977["🔴🔴🔴 파괴 대조"]["u=3 · α=0.95"]["파괴별"][
        "D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"] if d977 else None)

    # ── ② 1 벌 추정의 분포 (겹 씨앗 5 × 섞기 씨앗 40 = 200 벌) ──
    _prog("cond3 분포 시작 (%d 벌)" % (len(SEEDS) * COND3_WRECKS))
    draws = {nm: [] for nm in RULERS}
    for s in SEEDS:
        pool.reseed(s)
        v0, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam)["예측"])
        for ws in range(COND3_WRECKS):
            v, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                           wreck={"kind": w["kind"], "n": w["n"],
                                                  "seed": 977000 + ws * 97})["예측"])
            for nm in RULERS:
                draws[nm].append(v[nm] - v0[nm])
    dist = collections.OrderedDict()
    for nm in RULERS:
        a = np.asarray(draws[nm], float)
        dist[nm] = {
            "평균": _r(a.mean()), "1 벌 SD": _r(float(np.std(a, ddof=1))),
            "🔴🔴 1 벌이 양수인 비율": _r(float((a > 0).mean()), 4),
            "최소": _r(a.min()), "최대": _r(a.max()),
            "🔴 25 벌 평균의 SD (= 1벌SD/5)": _r(float(np.std(a, ddof=1)) / np.sqrt(25)),
        }
    a_eq = np.asarray(draws["R_eq 균등"], float)
    inside = bool(a_eq.min() <= one <= a_eq.max())
    frac_pos = float((a_eq > 0).mean())

    out = collections.OrderedDict()
    out["무엇"] = ("978 §4-S2 — 🔴 **같은 등록 조건에 커밋된 두 값이 왜 갈리나**. "
                 "977 의 조건 3 이 `wiring`(1 벌)과 `destroy`(25 벌)에서 부호가 다르다")
    out["🔴 축"] = "C3 — 자기 자(반증조건 5)"
    out["🔴 문제"] = {
        "🔴 wiring 이 적은 값(1 벌 · 겹씨앗 976 · 섞기 씨앗 4242)": tgt_one,
        "🔴 destroy 가 적은 값(25 벌)": tgt_25,
        "🔴 두 값의 차": _r((tgt_one - tgt_25) if (tgt_one is not None
                                              and tgt_25 is not None) else None),
        "🔴 977 이 어느 것으로 조건 3 을 채점했나": "destroy(25 벌) → 참",
        "🔴 wiring 값으로 채점하면": "거짓",
    }
    out["🔴🔴 재현"] = {
        "978 이 1 벌 설정에서 다시 낸 값": _r(one),
        "🔴 wiring 값과 소수 여섯 자리까지 같은가": bool(
            tgt_one is not None and _r(one) == tgt_one),
        "978 이 25 벌 설정에서 다시 낸 값": d25,
        "🔴 destroy 값과 소수 여섯 자리까지 같은가": bool(
            tgt_25 is not None and d25 == tgt_25),
        "통과": bool(tgt_one is not None and _r(one) == tgt_one
                   and tgt_25 is not None and d25 == tgt_25),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **두 수는 둘 다 맞다.** 어긋난 것은 수가 아니라 **조건의 정의**다 — "
            "등록된 조건이 **벌 수를 안 적었다**"),
    }
    out["🔴🔴🔴 1 벌 추정의 분포 (겹 씨앗 5 × 섞기 씨앗 %d = %d 벌)"
        % (COND3_WRECKS, len(SEEDS) * COND3_WRECKS)] = dist
    out["🔴🔴🔴 판정"] = {
        "🔴 wiring 의 값이 200 벌 분포 안에 있나": inside,
        "🔴🔴 1 벌 추정이 양수인 비율(균등 자)": _r(frac_pos, 4),
        "🔴🔴 그러므로 조건 3 의 답을 정하는 것은": (
            "자료가 아니라 **뽑기다** — 1 벌로는 부호가 %s%% 에서 뒤집힌다"
            % _r(frac_pos * 100, 2)),
        "🔴 예측 P5(1 벌 부호가 20%% 이상에서 양수)": bool(frac_pos >= 0.20),
        "통과": bool(inside),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "wiring 의 +값이 destroy 분포의 **한 표본**이다 = 두 산출물이 어긋난 게 아니라 "
            "**등록 조건이 벌 수를 안 적었다**"),
    }
    out["🔴🔴 등록 규칙 신설 (978)"] = (
        "🔴 **조건은 벌 수를 같이 등록해야 한다.** 벌 수가 없는 조건은 무효다. "
        "976 의 「37,535 대 37,531」과 977 의 이 자리가 같은 병이다 — "
        "**같은 이름의 수를 서로 다른 설정에서 두 번 냈다**")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_cond3.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("cond3 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S3 `size` — 🔴 「행당 114 배」를 분모 있는 문장으로
# ══════════════════════════════════════════════════════════════════════
def stage_size(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("size 시작")
    pool = A.Pool()
    R = Rulers(pool)

    # ── ① 크기 맞춤 대조 D2(base 90) vs D3(hplt 90) · 짝 SE ────
    _prog("size 짝 SE 시작")
    pair = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        p2 = point_over(pool, R, ALPHA_BASE, lam, wr=WRECKS_Y["D2 base 학습 y 전량"])
        p3 = point_over(pool, R, ALPHA_BASE, lam,
                        wr=WRECKS_Y["D3 hplt y 중 무작위 90 행"])
        p1 = point_over(pool, R, ALPHA_BASE, lam, wr=WRECKS_Y["D1 hplt y 전량"])
        b = point_over(pool, R, ALPHA_BASE, lam)
        # 🔴 짝 붓스트랩 — 같은 뽑기 안에서 Δ2 · Δ3 · 그 차를 같이 잰다
        acc = {nm: {"Δ2": [], "Δ3": [], "차": []} for nm in RULERS}
        for s in SEEDS:
            pool.reseed(s)
            for bb in range(BOOT):
                hi = A.ho_draw(pool, bb)
                v0, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                                tr_boot=bb)["예측"], hi)
                v2, _p = score4(pool, R, oof978(
                    pool, ALPHA_BASE, lam, tr_boot=bb,
                    wreck={"kind": "base", "n": None, "seed": WRECK_SEED0})["예측"], hi)
                v3, _p = score4(pool, R, oof978(
                    pool, ALPHA_BASE, lam, tr_boot=bb,
                    wreck={"kind": "hplt", "n": 90, "seed": WRECK_SEED0})["예측"], hi)
                for nm in RULERS:
                    d2 = v2[nm] - v0[nm]
                    d3 = v3[nm] - v0[nm]
                    acc[nm]["Δ2"].append(d2)
                    acc[nm]["Δ3"].append(d3)
                    acc[nm]["차"].append(abs(d2) - abs(d3))
            _prog("  size SE u=%d 씨앗 %d 끝" % (u, s))
        rows = collections.OrderedDict()
        for nm in RULERS:
            d2 = p2[nm] - b[nm]
            d3 = p3[nm] - b[nm]
            d1 = p1[nm] - b[nm]
            s2 = float(np.std(acc[nm]["Δ2"], ddof=1))
            s3 = float(np.std(acc[nm]["Δ3"], ddof=1))
            sd = float(np.std(acc[nm]["차"], ddof=1))
            rows[nm] = {
                "🔴 D2 base 90 행 Δ": _r(d2), "SE(D2)": _r(s2),
                "|Δ2|/SE": _r(abs(d2) / s2, 4) if s2 else None,
                "🔴 D3 hplt 90 행 Δ": _r(d3), "SE(D3)": _r(s3),
                "|Δ3|/SE": _r(abs(d3) / s3, 4) if s3 else None,
                "🔴🔴 |Δ2| − |Δ3|": _r(abs(d2) - abs(d3)),
                "🔴🔴 그 차의 짝 SE": _r(sd),
                "🔴🔴 차 / 짝 SE": _r((abs(d2) - abs(d3)) / sd, 4) if sd else None,
                "🔴 차가 2 짝SE 를 넘나": bool(sd and abs(d2) - abs(d3) >= 2 * sd),
                "🔴 D1 hplt 1,710 행 Δ(분모로 쓰지 않는다)": _r(d1),
            }
        pair["u=%d" % u] = {
            "자별": rows,
            "🔴 부순 행 — D2": p2["🔴 부순 라벨 행(겹당)"],
            "🔴 부순 행 — D3": p3["🔴 부순 라벨 행(겹당)"],
            "🔴 같은 행 수인가": bool(p2["🔴 부순 라벨 행(겹당)"]
                              == p3["🔴 부순 라벨 행(겹당)"]),
            "🔴 벌 수(점추정)": p2["🔴 벌 수"],
            "🔴 뽑기 수(SE)": BOOT * len(SEEDS),
            "통과": bool(p2["🔴 부순 라벨 행(겹당)"] == p3["🔴 부순 라벨 행(겹당)"]),
            "🔴 이 절의 `통과` 가 뜻하는 것":
                "🔴 **크기 맞춤이 실제로 맞았다** — D2 와 D3 이 같은 행 수를 부순다",
        }

    # ── ② 「행당」 환산의 유일한 근거 — 🔴 분모를 밝힌다 ──────────
    perrow = collections.OrderedDict()
    for u in U_REG:
        r = pair["u=%d" % u]["자별"]["R_pool 묶음"]
        d1 = abs(r["🔴 D1 hplt 1,710 행 Δ(분모로 쓰지 않는다)"])
        d3 = abs(r["🔴 D3 hplt 90 행 Δ"])
        perrow["u=%d" % u] = {
            "🔴 D1/D3 (같은 원천 · 행 수만 다르다)": _r(d1 / d3, 4) if d3 else None,
            "🔴 행 수 비 1,710/90": _r(1710 / 90.0, 4),
            "🔴🔴 그 둘이 얼마나 어긋나나(배)": _r((d1 / d3) / (1710 / 90.0), 4) if d3 else None,
            "🔴 이 자리가 「행당」 환산의 유일한 근거인가":
                "🔴 **거의 선형이면 그렇다** — 어긋남이 1 에 가까울수록 「행당」이 뜻을 갖는다",
        }
    perrow["🔴🔴 977 이 헤드라인에 쓴 비의 분모"] = {
        "🔴 977 의 분모": "D1(hplt y 전량 1,710 행)",
        "🔴 그 분모의 SE 배수(u=3 · 묶음)":
            _r(abs(pair["u=3"]["자별"]["R_pool 묶음"][
                "🔴 D1 hplt 1,710 행 Δ(분모로 쓰지 않는다)"])
               / pair["u=3"]["자별"]["R_pool 묶음"]["SE(D3)"], 4)
            if pair["u=3"]["자별"]["R_pool 묶음"]["SE(D3)"] else None,
        "🔴 978 이 쓰는 것": "🔴 **비를 안 쓴다.** 크기 맞춤 대조 D2 대 D3 만 쓴다",
        "🔴 왜": ("977 의 분모 D1 은 0 을 무는 잡음이고 **부호가 양수**다"
                "(부수면 좋아진다). 0 을 무는 수를 분모로 쓴 비는 뜻이 없다"),
    }

    # ── ③ LOSO 에 SE 를 붙인다 (2순위 ⓑ) ──────────────────────
    _prog("LOSO SE 시작")
    loso = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        pts = collections.OrderedDict()
        for anm, drop in A.SRC_ARMS.items():
            acc = {nm: [] for nm in RULERS}
            for s in SEEDS:
                pool.reseed(s)
                v, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                               drop_src=drop)["예측"])
                for nm in RULERS:
                    acc[nm].append(v[nm])
            pts[anm] = {nm: float(np.mean(acc[nm])) for nm in RULERS}
        accd = {anm: {nm: [] for nm in RULERS} for anm in A.SRC_ARMS if anm != "ALL"}
        for s in SEEDS:
            pool.reseed(s)
            for bb in range(BOOT):
                hi = A.ho_draw(pool, bb)
                v0, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                                tr_boot=bb)["예측"], hi)
                for anm, drop in A.SRC_ARMS.items():
                    if anm == "ALL":
                        continue
                    v, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam,
                                                   drop_src=drop,
                                                   tr_boot=bb)["예측"], hi)
                    for nm in RULERS:
                        accd[anm][nm].append(v[nm] - v0[nm])
            _prog("  LOSO SE u=%d 씨앗 %d 끝" % (u, s))
        rows = collections.OrderedDict()
        for anm in accd:
            rows[anm] = collections.OrderedDict()
            for nm in RULERS:
                d = pts[anm][nm] - pts["ALL"][nm]
                s_ = float(np.std(accd[anm][nm], ddof=1))
                rows[anm][nm] = {
                    "Δ": _r(d), "SE_이중": _r(s_),
                    "🔴 |Δ|/SE": _r(abs(d) / s_, 4) if s_ else None,
                    "🔴 문턱 둘을 넘나": bool(s_ and abs(d) >= 2 * s_ and abs(d) >= THR_CARD),
                    "🔴 부호": "양수(빼면 낫다)" if d > 0 else "음수(빼면 나쁘다)",
                }
        loso["u=%d" % u] = {
            "팔별": rows,
            "🔴 뽑기 수": BOOT * len(SEEDS),
            "🔴 씨앗 수(점추정)": len(SEEDS),
            "통과": bool(len(rows) == len(A.SRC_ARMS) - 1),
            "🔴 이 절의 `통과` 가 뜻하는 것": "LOSO 세 팔 전부에 SE 가 붙었다(977 은 0 개였다)",
        }

    # ── ④ 🔴 `−hplt_ko` 팔이 격자 α=0 칸과 같은 자료인가 ────────
    pool.reseed(SEEDS[0])
    sb_a, sh_a, _s = A.select(pool, 0, ALPHA_BASE, ("hplt_ko",))
    sb_b, sh_b, _s = A.select(pool, 0, 0.0)
    same = bool(np.array_equal(sb_a, sb_b) and len(sh_a) == 0 and len(sh_b) == 0)
    ident = {
        "🔴 −hplt_ko 팔의 base 행 sha256":
            hashlib.sha256(np.ascontiguousarray(sb_a).tobytes()).hexdigest(),
        "🔴 α=0 칸의 base 행 sha256":
            hashlib.sha256(np.ascontiguousarray(sb_b).tobytes()).hexdigest(),
        "🔴 hplt 행 수(−hplt_ko)": int(len(sh_a)),
        "🔴 hplt 행 수(α=0)": int(len(sh_b)),
        "🔴🔴 바이트로 같은 자료인가": same,
        "통과": same,
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **LOSO 의 `−hplt_ko` 팔과 격자의 `α=0` 칸은 같은 학습 자료다** — "
            "그래서 977 의 격자 SE 를 그 팔에 그대로 붙일 수 있었다"),
    }

    out = collections.OrderedDict()
    out["무엇"] = ("978 §4-S3 — 🔴 **「행당 114 배」를 버리고 크기 맞춤 대조만 쓴다** · "
                 "LOSO 에 SE 를 붙인다")
    out["🔴 축"] = "C3"
    out["🔴 유보는 한 줄도 안 만졌다"] = True
    out["🔴 등록 상수"] = {"BOOT": BOOT, "겹 씨앗": SEEDS, "점추정 벌 수": len(SEEDS) * N_WRECK}
    out["🔴🔴🔴 크기 맞춤 대조 D2(base 90) 대 D3(hplt 90) — 자 넷"] = pair
    out["🔴🔴 「행당」 환산의 근거와 그 분모"] = perrow
    out["🔴🔴🔴 LOSO Δ ± SE — 자 넷"] = loso
    out["🔴🔴 −hplt_ko 팔 = 격자 α=0 칸 (바이트 대조)"] = ident
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_size.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("size 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S4 `xdestroy` — 🔴 특징 `x` 쪽을 부순다
# ══════════════════════════════════════════════════════════════════════
def stage_xdestroy(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("xdestroy 시작")
    pool = A.Pool()
    R = Rulers(pool)

    cells, base = collections.OrderedDict(), collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        base["u=%d" % u] = point_over(pool, R, ALPHA_BASE, lam)
        for nm, w in WRECKS_X.items():
            cells["u=%d|%s" % (u, nm)] = point_over(pool, R, ALPHA_BASE, lam, wx=w)
            _prog("  x 점추정 u=%d %s" % (u, nm))

    _prog("xdestroy SE 시작")
    se = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        arms = collections.OrderedDict([(nm, (None, w)) for nm, w in WRECKS_X.items()])
        se["u=%d" % u] = se_double(pool, R, ALPHA_BASE, lam, arms)
        _prog("  xdestroy SE u=%d 끝" % u)

    grid = collections.OrderedDict()
    for nm in RULERS:
        rows = collections.OrderedDict()
        n_ok = 0
        for u in U_REG:
            for wn in WRECKS_X:
                d = cells["u=%d|%s" % (u, wn)][nm] - base["u=%d" % u][nm]
                s_ = se["u=%d" % u][wn][nm]
                rr = adopt_row(d, s_)
                rows["u=%d|%s" % (u, wn)] = rr
                n_ok += 1 if rr["🔴🔴 셋 다"] else 0
        grid[nm] = {"칸별": rows,
                    "🔴 여덟 칸 통과 분자/분모": "%d / %d" % (n_ok, 2 * len(WRECKS_X))}

    # ── 🔴 원천 쪽 물음 — HPLT 의 `x` 가 유보와 겹치나 ──────────
    k = 6
    Xb, Xh = pool.Xb[:, :k], pool.Xh[:, :k]
    smd = []
    for j in range(k):
        m1, m2 = float(Xb[:, j].mean()), float(Xh[:, j].mean())
        s1, s2 = float(Xb[:, j].std()), float(Xh[:, j].std())
        sp = np.sqrt((s1 ** 2 + s2 ** 2) / 2.0)
        smd.append(_r((m2 - m1) / sp, 4) if sp > 0 else None)
    dom_h = collections.Counter(pool.dh.tolist())
    dom_b = collections.Counter(pool.db.tolist())
    covered = [d for d in pool.gated if dom_h.get(d, 0) > 0]
    overlap = {
        "🔴 특징별 표준화 평균차(hplt − base)": smd,
        "🔴 |SMD| 가 0.5 를 넘는 특징 수": "%d / %d" % (
            sum(1 for v in smd if v is not None and abs(v) > 0.5), k),
        "🔴 hplt 행이 있는 게이트 도메인": covered,
        "🔴🔴 hplt 가 덮는 게이트 도메인 분자/분모": "%d / %d" % (
            len(covered), len(pool.gated)),
        "🔴 도메인별 hplt 행": {d: int(dom_h.get(d, 0)) for d in pool.gated},
        "🔴 도메인별 유보 행": {d: int(dom_b.get(d, 0)) for d in pool.gated},
        "🔴 hplt 전체 행": int(len(pool.yh)),
        "🔴 base 전체 행": int(len(pool.yb)),
        "통과": bool(len(covered) == len(pool.gated)),
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "hplt 행이 **게이트 도메인 전부**를 덮는다 = 「도메인이 안 겹쳐서 안 쓰인다」는 "
            "설명은 안 선다"),
    }

    out = collections.OrderedDict()
    out["무엇"] = ("978 §4-S4 — 🔴 **특징 `x` 쪽을 부순다**. 977 은 라벨만 부쉈다. "
                 "「HPLT 행이 왜 안 쓰이나」의 원천 쪽 답")
    out["🔴 축"] = "C3"
    out["🔴 유보는 한 줄도 안 만졌다"] = True
    out["🔴 등록 상수"] = {"BOOT": BOOT, "점추정 벌 수": len(SEEDS) * N_WRECK}
    out["🔴 밑판"] = base
    out["🔴🔴🔴 특징 파괴 점추정(25 벌)"] = cells
    out["🔴 특징 파괴 SE(이중 붓스트랩)"] = se
    out["🔴🔴🔴 여덟 칸 — 자 넷 × X1~X4 × λ 둘"] = grid
    out["🔴🔴 원천 쪽 — HPLT 의 `x` 가 유보와 겹치나"] = overlap
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_xdestroy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("xdestroy 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S5 `alphafine` — α<0.2 를 촘촘히
# ══════════════════════════════════════════════════════════════════════
def stage_alphafine(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("alphafine 시작")
    pool = A.Pool()
    R = Rulers(pool)
    cells = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        for a in AFINE:
            acc = {nm: [] for nm in RULERS}
            rows = None
            for s in SEEDS:
                pool.reseed(s)
                r = oof978(pool, a, lam)
                v, _p = score4(pool, R, r["예측"])
                for nm in RULERS:
                    acc[nm].append(v[nm])
                rows = r["겹별 학습 행"]
            pool.reseed(SEEDS[0])
            fp = A.src_fingerprint(pool, a)
            cells["u=%d|α=%g" % (u, a)] = collections.OrderedDict(
                [(nm, _r(float(np.mean(acc[nm])))) for nm in RULERS]
                + [(nm + " 씨앗 SD", _r(float(np.std(acc[nm], ddof=1)))) for nm in RULERS]
                + [("🔴 씨앗 수", len(SEEDS)), ("학습 행(겹별)", rows),
                   ("🔴 학습 행이 예산과 같은가", bool(all(x == N_B for x in rows))),
                   ("원천 비율", fp["원천 비율"])])
            _prog("  α=%g u=%d" % (a, u))
    best = collections.OrderedDict()
    for u in U_REG:
        for nm in RULERS:
            ba = max(AFINE, key=lambda a, u=u, nm=nm: cells["u=%d|α=%g" % (u, a)][nm])
            best["u=%d|%s" % (u, nm)] = {
                "🔴 최적 α": ba, "그 값": cells["u=%d|α=%g" % (u, ba)][nm],
                "α=0 의 값": cells["u=%d|α=0" % u][nm],
                "🔴 최적이 α=0 인가": bool(ba == 0.0),
                "🔴 α=0 대비 이득": _r(cells["u=%d|α=%g" % (u, ba)][nm]
                                 - cells["u=%d|α=0" % u][nm])}
    n0 = sum(1 for v in best.values() if v["🔴 최적이 α=0 인가"])
    out = collections.OrderedDict()
    out["무엇"] = "978 §4-S5 — 🔴 **α<0.2 를 촘촘히**. 「조금만 넣는 게 최적인가」"
    out["🔴 축"] = "C3"
    out["🔴 격자"] = {"α": AFINE, "log₁₀λ": U_REG, "겹 씨앗": SEEDS}
    out["🔴🔴🔴 칸별 — 자 넷"] = cells
    out["🔴🔴 자·λ 마다의 최적 α"] = best
    out["🔴🔴 최적이 α=0 인 칸"] = "%d / %d" % (n0, len(best))
    out["🔴 예측 P8(최적은 α=0)"] = bool(n0 == len(best))
    out["통과"] = bool(len(cells) == len(AFINE) * len(U_REG))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = "등록한 칸을 전부 돌렸다(값이 무엇이든 적는다)"
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_alphafine.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("alphafine 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S6 `wiring` — 🔴 배선 W 를 `select()` 밖으로 (수리 5)
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("wiring 시작")
    pool = A.Pool()
    R = Rulers(pool)
    W = collections.OrderedDict()

    def add(name, ok, mutant_ok, why, extra=None):
        W[name] = {"통과": bool(ok), "🔴 변이체에서도 통과하나": bool(mutant_ok),
                   "🔴🔴 구성상 참인 검사인가": bool(mutant_ok),
                   "🔴 변이체가 무엇인가": why}
        if extra:
            W[name].update(extra)

    lam = 10.0 ** U_REG[1]

    # ── W1 배관 동일 — `oof978` 이 977 의 `oof` 와 바이트로 같다 ──
    pool.reseed(SEEDS[0])
    p_new = oof978(pool, ALPHA_BASE, lam)["예측"]
    pool.reseed(SEEDS[0])
    p_old = A.oof(pool, ALPHA_BASE, lam)["예측"]
    pool.reseed(SEEDS[0])
    p_mut = oof978(pool, ALPHA_BASE, lam,
                   wreck_x_={"kind": "hplt", "n": None, "seed": 1})["예측"]
    add("W1 `oof978` 이 977 의 `oof` 와 **바이트로 같은 예측**을 낸다",
        bool(np.array_equal(p_new, p_old)), bool(np.array_equal(p_mut, p_old)),
        "특징을 부순 판을 같은 검사에 건다 — 그때도 같으면 검사가 예측을 안 본다",
        {"🔴 새 판 sha256": hashlib.sha256(p_new.tobytes()).hexdigest(),
         "🔴 977 판 sha256": hashlib.sha256(p_old.tobytes()).hexdigest()})

    # ── W2 🔴 `score()` 균등 팔 — 균등은 **행 수를 안 본다** ──────
    v, per = score4(pool, R, p_new)
    doms = [d for d in pool.gated if np.isfinite(per[d])]
    eq_hand = float(np.mean([per[d] for d in doms]))
    pl_hand = float(sum(per[d] * pool.ho_mask[d].sum() for d in doms)
                    / sum(pool.ho_mask[d].sum() for d in doms))
    add("W2 균등 팔이 **도메인별 ρ 의 산술평균**이고 묶음 팔과 다르다",
        bool(abs(v["R_eq 균등"] - eq_hand) < 1e-12
             and abs(v["R_pool 묶음"] - pl_hand) < 1e-12
             and abs(v["R_eq 균등"] - v["R_pool 묶음"]) > 1e-6),
        bool(abs(eq_hand - eq_hand) < 1e-12 and abs(pl_hand - pl_hand) < 1e-12
             and abs(eq_hand - eq_hand) > 1e-6),
        "같은 값을 두 번 넣어 견준다(976 의 W8 꼴) — 그때도 통과하면 검사가 자료를 안 본다",
        {"🔴 균등(손계산)": _r(eq_hand), "🔴 묶음(손계산)": _r(pl_hand),
         "🔴 두 자의 차": _r(eq_hand - pl_hand)})

    # ── W3 🔴 균등 팔이 **작은 도메인에 큰 무게**를 준다 ────────
    n = {d: int(pool.ho_mask[d].sum()) for d in pool.gated}
    small = min(pool.gated, key=lambda d: n[d])
    big = max(pool.gated, key=lambda d: n[d])
    wt = R.table()["자별 가중"]
    ratio_eq = (wt["R_eq 균등"]["정규화 가중"][small]
                / wt["R_eq 균등"]["정규화 가중"][big])
    ratio_pl = (wt["R_pool 묶음"]["정규화 가중"][small]
                / wt["R_pool 묶음"]["정규화 가중"][big])
    add("W3 균등 자는 %d 행 도메인과 %d 행 도메인에 **같은 무게**를 준다" % (n[small], n[big]),
        bool(abs(ratio_eq - 1.0) < 1e-9 and ratio_pl < 0.1),
        bool(abs(ratio_eq - ratio_eq) < 1e-9 and ratio_eq < 0.1),
        "균등 자의 비를 자기와 견준다 — 그때도 통과하면 검사가 가중을 안 본다",
        {"🔴 가장 작은 도메인": small, "그 행 수": n[small],
         "🔴 가장 큰 도메인": big, "그 행 수": n[big],
         "🔴 균등 자의 무게 비(작은/큰)": _r(ratio_eq, 4),
         "🔴 묶음 자의 무게 비(작은/큰)": _r(ratio_pl, 6)})

    # ── W4 🔴 `over_seeds` — 겹 씨앗이 실제로 값을 바꾼다 ───────
    vals = []
    for s in SEEDS:
        pool.reseed(s)
        vv, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam)["예측"])
        vals.append(vv["R_eq 균등"])
    same_seed = []
    for _s in SEEDS:
        pool.reseed(SEEDS[0])
        vv, _p = score4(pool, R, oof978(pool, ALPHA_BASE, lam)["예측"])
        same_seed.append(vv["R_eq 균등"])
    add("W4 겹 씨앗 다섯이 **서로 다른 자 값**을 만든다(`over_seeds` 가 실제로 재씨앗한다)",
        bool(len(set(np.round(vals, 12))) == len(SEEDS)),
        bool(len(set(np.round(same_seed, 12))) == len(SEEDS)),
        "같은 씨앗을 다섯 번 넣어 본다 — 그때도 다섯 값이 다르면 검사가 씨앗을 안 본다",
        {"🔴 씨앗별 균등 ρ": [_r(x) for x in vals],
         "🔴 그 SD": _r(float(np.std(vals, ddof=1))),
         "🔴 평균": _r(float(np.mean(vals))),
         "🔴🔴 SD 가 평균보다 큰가(= 0 과 구별이 안 된다)": bool(
             abs(float(np.std(vals, ddof=1))) > abs(float(np.mean(vals))))})
    pool.reseed(SEEDS[0])

    # ── W5 🔴 이중 붓스트랩 — **학습 쪽 성분이 실제로 든다** ────
    pool.reseed(SEEDS[0])
    hi = A.ho_draw(pool, 3)
    p_tr0, _q = score4(pool, R, oof978(pool, ALPHA_BASE, lam, tr_boot=None)["예측"], hi)
    p_tr3, _q = score4(pool, R, oof978(pool, ALPHA_BASE, lam, tr_boot=3)["예측"], hi)
    p_tr4, _q = score4(pool, R, oof978(pool, ALPHA_BASE, lam, tr_boot=4)["예측"], hi)
    add("W5 `tr_boot` 이 **학습 행을 실제로 다시 뽑는다**(이중 붓스트랩의 학습 성분)",
        bool(abs(p_tr3["R_pool 묶음"] - p_tr0["R_pool 묶음"]) > 1e-9
             and abs(p_tr3["R_pool 묶음"] - p_tr4["R_pool 묶음"]) > 1e-9),
        bool(abs(p_tr0["R_pool 묶음"] - p_tr0["R_pool 묶음"]) > 1e-9),
        "`tr_boot=None` 을 자기와 견준다 — 그때도 다르면 검사가 재표집을 안 본다",
        {"🔴 tr_boot 없음": _r(p_tr0["R_pool 묶음"]),
         "🔴 tr_boot=3": _r(p_tr3["R_pool 묶음"]),
         "🔴 tr_boot=4": _r(p_tr4["R_pool 묶음"])})

    # ── W6 🔴 `ho_draw` — 유보 쪽 성분이 실제로 든다 ────────────
    h1 = A.ho_draw(pool, 1)
    h2 = A.ho_draw(pool, 2)
    diff = sum(1 for d in pool.gated if not np.array_equal(h1[d], h2[d]))
    leak = sum(int((~pool.ho_mask[d][h1[d]]).sum()) for d in pool.gated)
    add("W6 `ho_draw` 가 유보를 **개체 묶음으로** 다시 뽑고 도메인 밖 행을 안 섞는다",
        bool(diff == len(pool.gated) and leak == 0),
        bool(sum(1 for d in pool.gated if not np.array_equal(h1[d], h1[d]))
             == len(pool.gated) and leak == 0),
        "같은 뽑기를 자기와 견준다 — 그때도 전부 다르면 검사가 뽑기를 안 본다",
        {"🔴 두 뽑기가 다른 도메인 수": "%d / %d" % (diff, len(pool.gated)),
         "🔴 도메인 밖으로 샌 행": leak})

    # ── W7 🔴 SE 가 **뽑기 수의 함수가 아니다**(수렴했나) ────────
    arms = {"D4": (WRECKS_Y["D4 학습 y 전량(둘 다)"], None)}
    se_a = se_double(pool, R, ALPHA_BASE, lam, arms, boot=50)
    se_b = se_double(pool, R, ALPHA_BASE, lam, arms, boot=100)
    #: 🔴 **변이체 — 뽑기를 2 → 3 으로 두면 수렴했다고 말할 수 없어야 한다.**
    se_m1 = se_double(pool, R, ALPHA_BASE, lam, arms, boot=2)
    se_m2 = se_double(pool, R, ALPHA_BASE, lam, arms, boot=3)
    ra = se_a["D4"]["R_eq 균등"]
    rb = se_b["D4"]["R_eq 균등"]
    ma = se_m1["D4"]["R_eq 균등"]
    mb = se_m2["D4"]["R_eq 균등"]
    add("W7 SE 가 뽑기 수 50 → 100 에서 10% 안으로 수렴한다",
        bool(ra and rb and abs(rb - ra) / ra < 0.10),
        bool(ma and mb and abs(mb - ma) / ma < 0.10),
        "🔴 뽑기 2 → 3 짜리 SE 에 같은 검사를 건다 — 그때도 통과하면 검사가 수렴을 안 본다",
        {"🔴 뽑기 50 의 SE(균등)": ra, "🔴 뽑기 100 의 SE(균등)": rb,
         "🔴 변이체 뽑기 2 의 SE": ma, "🔴 변이체 뽑기 3 의 SE": mb,
         "🔴 등록한 뽑기 수": BOOT})

    # ── W8 🔴 `wreck_x` 가 학습 X 를 바꾸고 유보 X 는 안 바꾼다 ──
    Xb0 = pool.Xb.copy()
    selb, selh, _s = A.select(pool, 0, ALPHA_BASE)
    X, y, _e, nb = A.design(pool, selb, selh)
    X1, c1 = wreck_x(X, nb, "hplt", 7)
    X0, c0 = wreck_x(X, nb, "hplt", 7, n=0)
    add("W8 특징 파괴가 학습 X 를 바꾸고 유보 X 는 안 바꾼다",
        bool((X1 != X).any() and np.array_equal(pool.Xb, Xb0) and c1 == len(X) - nb),
        bool((X0 != X).any() and np.array_equal(pool.Xb, Xb0) and c0 == len(X) - nb),
        "0 행만 부순 판으로 견준다 — 그때도 통과하면 검사가 파괴를 안 본다",
        {"🔴 부순 행": c1, "🔴 변이체가 부순 행": c0})

    # ── W9 🔴 순열 귀무 SD 가 **행 수의 함수**다 ────────────────
    ns = [(d, int(pool.ho_mask[d].sum()), R.sd[d]) for d in pool.gated]
    ns.sort(key=lambda z: z[1])
    mono = all(ns[i][2] >= ns[i + 1][2] for i in range(len(ns) - 1))
    corr = float(np.corrcoef([z[1] for z in ns],
                             [1.0 / np.sqrt(z[1]) for z in ns])[0, 1])
    pred_sd = {d: 1.0 / np.sqrt(max(int(pool.ho_mask[d].sum()) - 1, 1))
               for d in pool.gated}
    rel = max(abs(R.sd[d] - pred_sd[d]) / pred_sd[d] for d in pool.gated)
    #: 🔴 **변이체 — 모든 도메인에 같은 상수 SD 를 주면 이 검사는 떨어져야 한다.**
    const_sd = float(np.mean(list(R.sd.values())))
    ns_m = sorted([(d, int(pool.ho_mask[d].sum()), const_sd) for d in pool.gated],
                  key=lambda z: z[1])
    mono_m = all(ns_m[i][2] > ns_m[i + 1][2] for i in range(len(ns_m) - 1))
    rel_m = max(abs(const_sd - pred_sd[d]) / pred_sd[d] for d in pool.gated)
    add("W9 도메인 안 순열 귀무 SD 가 **행 수가 커질수록 작아지고 1/√(n−1) 에 붙는다**",
        bool(mono and rel < 0.25), bool(mono_m and rel_m < 0.25),
        "🔴 모든 도메인에 **같은 상수 SD** 를 주고 같은 검사를 건다 — 그때도 통과하면 "
        "검사가 행 수를 안 본다",
        {"🔴 행 수 오름차순 (도메인, 행, 귀무 SD)":
             [[z[0], z[1], _r(z[2])] for z in ns],
         "🔴 단조 감소인가": bool(mono),
         "🔴 1/√(n−1) 과의 최대 상대오차": _r(rel, 4),
         "🔴 변이체(상수 SD)의 최대 상대오차": _r(rel_m, 4),
         "🔴 상관(참고)": _r(corr, 4)})

    # ── W10 🔴 자 넷이 **모든 stage 에서 같이 나온다**(반증조건 4) ──
    got = collections.OrderedDict()
    for f in ("out978_ruler.json", "out978_cond3.json", "out978_size.json",
              "out978_xdestroy.json", "out978_alphafine.json"):
        p = OUT / f
        if not p.is_file():
            got[f] = "아직 없다"
            continue
        txt = p.read_text(encoding="utf-8")
        got[f] = "%d / %d" % (sum(1 for nm in RULERS if nm in txt), len(RULERS))
    add("W10 자 넷이 **격자 stage 밖에서도** 전부 나온다(반증조건 4)",
        bool(all(v == "4 / 4" for v in got.values() if v != "아직 없다")),
        False,
        "🔴 변이체를 못 만든다 — 이 검사는 산출물 파일을 읽으므로 자기 판정을 못 짓는다",
        {"🔴 산출물별 자 가짓수": got,
         "🔴 이 검사는 산출물이 다 난 뒤에 다시 돌려야 뜻이 있다": True})

    n_ok = sum(1 for v in W.values() if v["통과"])
    n_const = sum(1 for v in W.values() if v["🔴🔴 구성상 참인 검사인가"])

    out = collections.OrderedDict()
    out["무엇"] = ("978 §4-S6 — 🔴 **배선 W 를 `select()` 밖으로**. 977 의 W1~W4 는 전부 "
                 "`select()` 하나를 물었고 **문턱 판정을 전부 지는 이중 붓스트랩 SE 코드 · "
                 "`over_seeds` · `score()` 균등 팔에는 검사가 0 개**였다")
    out["🔴 축"] = "자기 자(수리 레인) + C3"
    out["🔴 977 의 W 가 문 것"] = {
        "🔴 977 W1~W4 가 문 함수": "select()",
        "🔴 977 이 SE 코드를 문 검사 수": 0,
        "🔴 977 이 `over_seeds` 를 문 검사 수": 0,
        "🔴 977 이 `score()` 균등 팔을 문 검사 수": 0,
        "🔴 978 이 그 셋을 무는 검사 수": 5,
        "🔴 978 이 무는 함수": ["oof978/oof", "score4/score", "over_seeds",
                          "se_double", "ho_draw", "wreck_x", "perm_null_sd"],
    }
    out["W"] = W
    out["🔴 W 분자/분모(통과)"] = "%d / %d" % (n_ok, len(W))
    out["🔴🔴🔴 W 구성상 참인 검사 분자/분모"] = "%d / %d" % (n_const, len(W))
    out["🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"] = "%d / %d" % (
        sum(1 for v in W.values() if v["통과"] and not v["🔴🔴 구성상 참인 검사인가"]),
        len(W) - n_const)
    out["통과: 배선"] = bool(n_ok == len(W))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out978_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("wiring 끝")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "ruler", "cond3", "size", "xdestroy",
                             "alphafine"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "ruler": stage_ruler, "cond3": stage_cond3,
         "size": stage_size, "xdestroy": stage_xdestroy,
         "alphafine": stage_alphafine}[a.stage](a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if not str(k).startswith("🔴🔴🔴")},
                     ensure_ascii=False, indent=1, default=str)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
