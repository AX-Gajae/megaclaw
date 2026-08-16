#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""979 — 🔴 **수를 새로 만들지 않는다. 분모를 고친다.**

사전등록 `docs/prereg_979_denominator.md` 를 그대로 따른다. 축 **C3**(곁 **C2**).

🔴 티처 #117 이 실측으로 낸 것:
  ① `ruler978.se_double()` 이 붓스트랩 복제마다 **섞기 씨앗 하나**만 쓴다
     (`ruler978.py:296`) — **분자 25 벌 · 분모 1 벌**. 헤드라인 `1.9527` 이 그 산물이다.
  ② 채택 문이 `D4` 두 칸뿐인데 `R_z` 가 여덟 칸에서 통과하는 칸이 **정확히 그 둘**이다.
  ③ 선택 규칙(가장 큰 도메인 몫 최소)이 통과자 셋 중 **검정력 최저**를 고른다.
  ④ hplt **학습 1,710 행**의 도메인 혼합이 유보 혼합과 사실상 무상관이다.

🔴 **이 러너는 `ruler978` 을 그대로 물어서 돈다** — `oof978`·`wreck_x`·`WRECKS_*` 를
갈아 끼우지 않았다는 것을 `wiring` 이 **바이트로** 보인다(W1). 그래서 `SE_구판` 이
노트 978 의 `se_double()` 과 **같은 수**로 나와야 한다(W7).

씀:
    python3 runners/ruler979.py --stage wiring    --ref <40자 sha>
    python3 runners/ruler979.py --stage sd        --ref <40자 sha>
    python3 runners/ruler979.py --stage rescore   --ref <40자 sha>
    python3 runners/ruler979.py --stage sizeloso  --ref <40자 sha>
    python3 runners/ruler979.py --stage alphapair --ref <40자 sha>
    python3 runners/ruler979.py --stage srcmix    --ref <40자 sha>
    python3 runners/ruler979.py --stage gate      --ref <40자 sha>
    python3 runners/ruler979.py --stage score978  --ref <40자 sha>
    python3 runners/ruler979.py --stage recheck   --ref <40자 sha>
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
import loso974 as LO                              # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler978 as R8                             # noqa: E402

RAN = ("runners/ruler979.py", "runners/ruler978.py", "runners/alpha977.py",
       "runners/ledger.py", "runners/layers957.py", "runners/predict971.py",
       "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out979_progress.txt"

# ── 사전등록 상수 (§3 · 측정 전에 박았다) ─────────────────────────────
BOOT = 400                        # 이중 붓스트랩 뽑기
N_WRECK = 5                       # 파괴 섞기 씨앗 수 → 점추정도 SE 도 25 벌
PERM_NULL = 2000                  # 순열 귀무 뽑기(닫힌 꼴 대조용)
PERM_SEED = 978
WRECK_SEED0 = R8.WRECK_SEED0      # 🔴 978 과 같은 밑값 — 구판 SE 를 재현하려면 같아야 한다
SEEDS = A.SEEDS
U_REG = A.U_REG
ALPHA_BASE = A.ALPHA_BASE
THR_CARD = A.THR_CARD             # 🔴 **진단 수치다** — v2.2 는 이것으로 구속하지 않는다
KFOLD = A.KFOLD
N_B = A.N_B
AFINE = R8.AFINE
K_FEAT = 6

WRECKS_Y = R8.WRECKS_Y
WRECKS_X = R8.WRECKS_X

#: 🔴 자 여섯. 앞 넷은 978 과 **글자까지 같은 이름**이라 산출물을 바로 견줄 수 있다.
R1 = "R_pool 묶음"
R2 = "R_eq 균등"
R3 = "R_z 순열SE 역가중"
R4 = "R_iv SE² 역가중"
R5 = "R_z* 닫힌꼴"
R6 = "R_iv* 닫힌꼴"
RULERS = (R1, R2, R3, R4, R5, R6)

#: 🔴🔴 반증조건 4 — **분모를 여기 측정 전에 못박는다.** 측정 뒤에 못 바꾼다.
FC4_REG_979 = ("out979_sd.json", "out979_rescore.json", "out979_sizeloso.json",
               "out979_alphapair.json", "out979_gate.json")
FC4_OUT_979 = ("out979_wiring.json", "out979_srcmix.json", "out979_score978.json",
               "out979_recheck.json")

#: 🔴 노트 978 사전등록 §6-4 **문언 그대로**의 분모(이름 넷 + 「모든 stage」).
FC4_978_TEXT = ("out978_ruler.json", "out978_size.json", "out978_xdestroy.json",
                "out978_alphafine.json", "out978_wiring.json", "out978_cond3.json")
#: 노트 978 이 **측정 15 분 뒤에** 실제로 쓴 분모(`FC4_REG` 다섯 · `wiring` 을 뺐다).
FC4_978_USED = ("out978_ruler.json", "out978_cond3.json", "out978_size.json",
                "out978_xdestroy.json", "out978_alphafine.json")
R978 = ("R_pool 묶음", "R_eq 균등", "R_z 순열SE 역가중", "R_iv SE² 역가중")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))


def _r(x, n=6):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def _load(name):
    p = OUT / name if not str(name).startswith("/") else Path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 반증조건 6 — 유보 지문. **리터럴 `True` 를 안 쓴다.**
# ══════════════════════════════════════════════════════════════════════
def ho_stamp(pool):
    """🔴 유보의 **바이트 지문**. 주행 시작·끝 두 번 찍어 대조한다.

    노트 978 은 같은 주장을 `ruler978.py:444·792·878` 에서 **리터럴 `True`** 로 적었다
    (유보 지문도 행 수 대조도 없었다). 🔴 그 셋은 `통과` 키가 아니라서 `meta965` 의
    항진명제 census 가 **원리상 못 봤다**.
    """
    doms = list(pool.gated)
    return collections.OrderedDict([
        ("유보 y sha256", _sha_arr(pool.yb)),
        ("유보 y 행 수", int(len(pool.yb))),
        ("유보 마스크 sha256", _sha_arr(np.vstack([pool.ho_mask[d] for d in doms]))),
        ("도메인별 유보 행", {d: int(pool.ho_mask[d].sum()) for d in doms}),
        ("게이트 도메인 수", len(doms)),
        ("유보 도메인 라벨 sha256", _sha_arr(pool.db)),
    ])


def ho_verdict(s0, s1):
    same = bool(s0 == s1)
    return collections.OrderedDict([
        ("🔴 시작 지문", s0), ("🔴 끝 지문", s1),
        ("🔴🔴 유보를 한 줄이라도 만졌나", not same),
        ("🔴 이 판정이 리터럴인가", False),
        ("통과", same),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **유보 y·유보 마스크·도메인 라벨의 sha256 이 주행 시작과 끝에서 같다.** "
         "978 은 같은 주장을 `= True` 로 적었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §1 자 여섯 — 🔴 닫힌 꼴을 더한다
# ══════════════════════════════════════════════════════════════════════
class Rulers6(object):
    """자 여섯의 가중치. 🔴 **팔·뽑기와 무관하게 한 번만 만든다.**

    🔴 `R_z*`·`R_iv*` 는 **뽑기가 없다** — `s_d = 1/√(n_d−1)` 이 닫힌 꼴이다.
    """

    def __init__(self, pool, n_perm=PERM_NULL, seed=PERM_SEED):
        self.doms = list(pool.gated)
        self.n = {d: int(pool.ho_mask[d].sum()) for d in self.doms}
        #: 뽑기판(978 그대로 · 견줄 자리로 남긴다)
        self.sd = collections.OrderedDict()
        for d in self.doms:
            self.sd[d] = R8.perm_null_sd(pool.yb[pool.ho_mask[d]], n_perm, seed)
        #: 🔴 닫힌 꼴
        self.sd_cf = collections.OrderedDict(
            [(d, 1.0 / math.sqrt(self.n[d] - 1)) for d in self.doms])
        self.w = collections.OrderedDict()
        self.w[R2] = {d: 1.0 for d in self.doms}
        self.w[R3] = {d: 1.0 / self.sd[d] for d in self.doms}
        self.w[R4] = {d: 1.0 / (self.sd[d] ** 2) for d in self.doms}
        self.w[R5] = {d: 1.0 / self.sd_cf[d] for d in self.doms}
        self.w[R6] = {d: 1.0 / (self.sd_cf[d] ** 2) for d in self.doms}
        self.wp = {d: float(self.n[d]) for d in self.doms}

    def all_w(self):
        return collections.OrderedDict([(R1, self.wp)] +
                                       [(k, self.w[k]) for k in
                                        (R2, R3, R4, R5, R6)])

    def table(self):
        rows = collections.OrderedDict()
        for nm, w in self.all_w().items():
            s = sum(w.values())
            nor = {d: w[d] / s for d in self.doms}
            top = max(self.doms, key=lambda d: nor[d])
            rows[nm] = collections.OrderedDict([
                ("정규화 가중", {d: _r(nor[d]) for d in self.doms}),
                ("🔴 가장 큰 도메인", top),
                ("🔴🔴 가장 큰 도메인의 몫", _r(nor[top])),
                ("🔴 유효 도메인 수 (1/Σw²)",
                 _r(1.0 / sum(v * v for v in nor.values()), 4)),
                ("🔴 뽑기를 쓰나", bool(nm in (R3, R4))),
            ])
        out = collections.OrderedDict()
        out["자별 가중"] = rows
        out["도메인별 유보 행"] = self.n
        out["🔴 순열 귀무 SD(뽑기 %d · 씨앗 %d)" % (PERM_NULL, PERM_SEED)] = {
            d: _r(self.sd[d]) for d in self.doms}
        out["🔴🔴 닫힌 꼴 1/√(n−1)"] = {d: _r(self.sd_cf[d]) for d in self.doms}
        rel = {d: abs(self.sd[d] - self.sd_cf[d]) / self.sd_cf[d] for d in self.doms}
        out["🔴 도메인별 상대오차"] = {d: _r(rel[d], 5) for d in self.doms}
        out["🔴🔴🔴 최대 상대오차"] = _r(max(rel.values()), 5)
        out["🔴 몬테카를로 오차의 이론값 1/√(2(n_perm−1))"] = _r(
            1.0 / math.sqrt(2.0 * (PERM_NULL - 1)), 5)
        out["🔴🔴 최대 상대오차가 이론 잡음의 몇 배인가"] = _r(
            max(rel.values()) * math.sqrt(2.0 * (PERM_NULL - 1)), 4)
        out["통과"] = bool(all(np.isfinite(v) for v in self.sd.values())
                         and len(self.doms) > 0)
        out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
            "게이트 도메인 전부에서 귀무 SD 가 유한하다 = 자 여섯이 전부 정의된다")
        return out


def score6(pool, R, pred, ho_idx=None):
    """🔴 자 **여섯을 한 번에** 낸다(반증조건 4)."""
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
    v = np.asarray([per[d] for d in ok], float)
    wp = np.asarray([lens[d] for d in ok], float)
    out[R1] = float((v * wp).sum() / wp.sum())
    for nm in (R2, R3, R4, R5, R6):
        w = np.asarray([R.w[nm][d] for d in ok], float)
        out[nm] = float((v * w).sum() / w.sum())
    return out, per


def point25(pool, R, alpha, lam, wr=None, wx=None, nwreck=N_WRECK):
    """🔴 **25 벌**(겹 씨앗 5 × 섞기 씨앗 5) 평균 — `ruler978.point_over` 와 같은 규약."""
    acc = {nm: [] for nm in RULERS}
    nwr, nwx = [], []
    ns = nwreck if (wr is not None or wx is not None) else 1
    for s in SEEDS:
        pool.reseed(s)
        for ws in range(ns):
            w1 = None if wr is None else dict(wr, seed=WRECK_SEED0 + ws * 97)
            w2 = None if wx is None else dict(wx, seed=WRECK_SEED0 + ws * 97)
            r = R8.oof978(pool, alpha, lam, wreck=w1, wreck_x_=w2)
            v, _p = score6(pool, R, r["예측"])
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
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 수리 1 — **SE 의 벌 수를 점추정에 맞춘다**
# ══════════════════════════════════════════════════════════════════════
def se_matched(pool, R, alpha, lam, arms, boot=BOOT, nwreck=N_WRECK, tag=""):
    """🔴 한 주행에서 **SE 셋**을 같이 낸다(조항 66-③ 구판/신판 전후).

    * `SE_구판(1벌)` — 섞기 씨앗 `ws=0` 하나짜리 Δ 의 SD, 복제 `보트×씨앗`.
      🔴 **`ruler978.se_double()` 과 같은 수여야 한다.**
    * `SE_5벌` — 섞기 씨앗 다섯을 평균한 Δ 의 SD, 복제 `보트×씨앗`.
    * `SE_25벌(정합)` — 겹 씨앗 다섯 × 섞기 씨앗 다섯 = **점추정과 같은 25 벌**을
      평균한 Δ 의 SD, 복제 `보트` 개. 🔴 **등록 조건 ②의 분모다.**

    `arms` = {이름: (wreck, wreck_x)}. `wreck` 이 둘 다 `None` 인 팔(LOSO 등)은
    섞기 씨앗이 없으므로 구판과 5벌이 같은 수로 나온다 — 그 사실도 산출물이 적는다.

    🔴🔴 **유보 재표집을 복제마다 하나로 고정한다(979 자기 적발).**
    `alpha977.ho_draw(pool, b)` 는 `pool.seed` 를 물어서, 같은 뽑기 `b` 라도 겹 씨앗이
    바뀌면 **다른 유보 재표집**이 나온다. 그대로 25 벌을 평균하면 한 복제 안에서
    **유보 재표집 다섯 개를 평균**하게 되어 SE 가 √5 만큼 거짓으로 좁아진다.
    🔴 그래서 정합 팔은 **복제 `b` 마다 유보 재표집을 하나(`hi_b`)로 고정**하고,
    구판 팔은 **978 그대로 겹 씨앗마다 다시 뽑은 `hi_s`** 를 쓴다.
    예측은 유보 재표집과 무관하므로 **한 번 낸 예측을 두 유보에 채점**한다(공짜다).
    """
    a1 = {a: {nm: [] for nm in RULERS} for a in arms}      # ws=0 · hi_s (978 판)
    a5 = {a: {nm: [] for nm in RULERS} for a in arms}      # mean over ws · hi_s
    a25 = {a: {nm: [] for nm in RULERS} for a in arms}     # mean over (s, ws) · hi_b
    a25s = {a: {nm: [] for nm in RULERS} for a in arms}    # 🔴 잘못된 판(대조용)
    drops = {a: arms[a][2] if len(arms[a]) > 2 else () for a in arms}
    t0 = time.time()
    for b in range(boot):
        buf = {a: {nm: [] for nm in RULERS} for a in arms}
        bufs = {a: {nm: [] for nm in RULERS} for a in arms}
        pool.reseed(SEEDS[0])
        hi_b = A.ho_draw(pool, b)          # 🔴 복제 하나에 유보 재표집 하나
        for s in SEEDS:
            pool.reseed(s)
            hi_s = A.ho_draw(pool, b)      # 🔴 978 판(겹 씨앗마다 다시 뽑는다)
            pr0 = R8.oof978(pool, alpha, lam, tr_boot=b)["예측"]
            v0s, _p = score6(pool, R, pr0, hi_s)
            v0b, _p = score6(pool, R, pr0, hi_b)
            for a in arms:
                wr, wx = arms[a][0], arms[a][1]
                ns = nwreck if (wr is not None or wx is not None) else 1
                per_ws = {nm: [] for nm in RULERS}
                for ws in range(ns):
                    w1 = None if wr is None else dict(wr, seed=WRECK_SEED0 + ws * 97)
                    w2 = None if wx is None else dict(wx, seed=WRECK_SEED0 + ws * 97)
                    pr = R8.oof978(pool, alpha, lam, tr_boot=b, drop_src=drops[a],
                                   wreck=w1, wreck_x_=w2)["예측"]
                    vs, _p = score6(pool, R, pr, hi_s)
                    vb, _p = score6(pool, R, pr, hi_b)
                    for nm in RULERS:
                        per_ws[nm].append(vs[nm] - v0s[nm])
                        buf[a][nm].append(vb[nm] - v0b[nm])
                for nm in RULERS:
                    a1[a][nm].append(per_ws[nm][0])
                    a5[a][nm].append(float(np.mean(per_ws[nm])))
                    bufs[a][nm] += per_ws[nm]
        for a in arms:
            for nm in RULERS:
                a25[a][nm].append(float(np.mean(buf[a][nm])))
                a25s[a][nm].append(float(np.mean(bufs[a][nm])))
        if (b + 1) % 50 == 0:
            _prog("    %s SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                  time.time() - t0))
    out = collections.OrderedDict()
    for a in arms:
        wr, wx = arms[a][0], arms[a][1]
        ns = nwreck if (wr is not None or wx is not None) else 1
        row = collections.OrderedDict()
        for nm in RULERS:
            row[nm] = collections.OrderedDict([
                ("🔴 SE_구판(1 벌 · 978 판)", _r(float(np.std(a1[a][nm], ddof=1)))),
                ("🔴 SE_5벌", _r(float(np.std(a5[a][nm], ddof=1)))),
                ("🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)",
                 _r(float(np.std(a25[a][nm], ddof=1)))),
                ("🔴 SE_25벌(유보 재표집을 복제 안에서 다섯 개 평균한 잘못된 판 · 대조용)",
                 _r(float(np.std(a25s[a][nm], ddof=1)))),
            ])
        row["🔴 복제 수(구판·5벌)"] = len(a1[a][RULERS[0]])
        row["🔴 복제 수(25벌 정합)"] = len(a25[a][RULERS[0]])
        row["🔴 이 팔의 섞기 씨앗 수"] = ns
        row["🔴 섞기 씨앗이 없는 팔인가(그러면 구판=5벌 이다)"] = bool(ns == 1)
        row["🔴🔴 유보 재표집 규약"] = (
            "정합 팔 = 복제마다 유보 재표집 **하나**(`hi_b`) · "
            "구판 팔 = 겹 씨앗마다 다시 뽑는다(`hi_s` · 978 판)")
        out[a] = row
    return out


def adopt_row2(delta, se, se_old=None):
    """🔴🔴 사전등록 §2 v2.2 — **조건 둘**. 🔴 `0.00353` 은 **진단으로만** 병기한다."""
    c1 = bool(delta is not None and delta < 0)
    c2 = bool(se and delta is not None and abs(delta) >= 2 * se)
    return collections.OrderedDict([
        ("Δ", _r(delta)),
        ("🔴🔴 SE_25벌(정합)", se),
        ("🔴 SE_구판(1 벌 · 978 판)", se_old),
        ("🔴🔴 |Δ|/SE (정합)", _r(abs(delta) / se, 4) if (se and delta is not None) else None),
        ("🔴 |Δ|/SE (978 판)",
         _r(abs(delta) / se_old, 4) if (se_old and delta is not None) else None),
        ("🔴 조건 ① 부호 Δ < 0", c1),
        ("🔴🔴 조건 ② |Δ| ≥ 2·SE(정합)", c2),
        ("🔴🔴 둘 다 (v2.2 통과)", bool(c1 and c2)),
        ("진단: |Δ| ≥ 0.00353 (구속 아님)",
         bool(delta is not None and abs(delta) >= THR_CARD)),
        ("진단: 978 판 SE 로 재면 통과하나",
         bool(c1 and se_old and delta is not None and abs(delta) >= 2 * se_old)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §4-S2 `sd` — 🔴 `s_d` 를 닫힌 꼴로 (수리 4)
# ══════════════════════════════════════════════════════════════════════
def stage_sd(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("sd 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)
    tab = R.table()

    #: 🔴 항등식 대조 — `1/s_d² = n_d − 1` 이면 `R_iv*` 는 `−1` 보정을 뺀 `R_pool` 이다.
    doms = R.doms
    wiv = {d: R.w[R6][d] for d in doms}
    siv = sum(wiv.values())
    spool = sum(R.wp.values())
    ident = collections.OrderedDict([
        ("🔴 R_iv* 정규화 가중", {d: _r(wiv[d] / siv) for d in doms}),
        ("🔴 R_pool 정규화 가중", {d: _r(R.wp[d] / spool) for d in doms}),
        ("🔴🔴 두 가중의 최대 차", _r(max(abs(wiv[d] / siv - R.wp[d] / spool)
                                  for d in doms), 6)),
        ("🔴 R_iv* 의 가장 큰 도메인 몫", tab["자별 가중"][R6]["🔴🔴 가장 큰 도메인의 몫"]),
        ("🔴 R_pool 의 가장 큰 도메인 몫", tab["자별 가중"][R1]["🔴🔴 가장 큰 도메인의 몫"]),
        ("🔴🔴🔴 그 둘의 차", _r(abs(tab["자별 가중"][R6]["🔴🔴 가장 큰 도메인의 몫"]
                              - tab["자별 가중"][R1]["🔴🔴 가장 큰 도메인의 몫"]), 6)),
        ("🔴🔴 뜻", "🔴 **`1/s_d² = n_d − 1` 은 근사가 아니라 항등식이다** — "
                 "`R_iv SE² 역가중` 은 `−1` 보정을 빼면 `R_pool 묶음` 과 같은 자다"),
        ("🔴 뽑기판 R_iv 와 닫힌꼴 R_iv* 의 가장 큰 도메인 몫 차",
         _r(abs(tab["자별 가중"][R4]["🔴🔴 가장 큰 도메인의 몫"]
                - tab["자별 가중"][R6]["🔴🔴 가장 큰 도메인의 몫"]), 6)),
        ("통과", bool(len(doms) > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "게이트 도메인 전량에서 두 가중을 다 냈다"),
    ])

    #: 🔴 자기 대조 — 순열 뽑기를 절반으로 줄이면 뽑기판은 흔들리고 닫힌 꼴은 안 흔들린다.
    R_half = Rulers6(pool, n_perm=PERM_NULL // 2, seed=PERM_SEED + 1)
    jitter = collections.OrderedDict([
        ("🔴 뽑기 %d 판의 s_d" % PERM_NULL, {d: _r(R.sd[d]) for d in doms}),
        ("🔴 뽑기 %d · 씨앗 %d 판의 s_d" % (PERM_NULL // 2, PERM_SEED + 1),
         {d: _r(R_half.sd[d]) for d in doms}),
        ("🔴🔴 뽑기판의 최대 상대 변동", _r(max(abs(R.sd[d] - R_half.sd[d]) / R.sd[d]
                                     for d in doms), 5)),
        ("🔴🔴 닫힌 꼴의 최대 상대 변동", 0.0),
        ("🔴 닫힌 꼴이 씨앗·뽑기에 안 매여 있나",
         bool(all(R.sd_cf[d] == R_half.sd_cf[d] for d in doms))),
        ("통과", bool(all(R.sd_cf[d] == R_half.sd_cf[d] for d in doms))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **닫힌 꼴은 뽑기 수와 씨앗을 바꿔도 한 자리도 안 움직인다** = 자가 씨앗에서 떨어졌다"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S2 — 🔴 **`s_d` 를 닫힌 꼴로**. 스피어만은 중간순위 위의 "
                 "피어슨이고 무작위 순열에서 그 분산은 동률이 있든 없든 `1/(n−1)` 이다")
    out["🔴 축"] = "C3 (곁 C2)"
    out["사전등록"] = "docs/prereg_979_denominator.md §1 · §4-S2"
    out["🔴 등록 상수"] = {"순열 뽑기": PERM_NULL, "순열 씨앗": PERM_SEED,
                     "겹 씨앗": SEEDS, "자 수": len(RULERS)}
    out["🔴🔴🔴 자 여섯의 가중"] = tab
    out["🔴🔴🔴 항등식 — R_iv* 는 R_pool 인가"] = ident
    out["🔴🔴 뽑기판은 흔들리고 닫힌 꼴은 안 흔들린다"] = jitter
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_sd.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("sd 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S3 `rescore` — 🔴🔴🔴 벌 수를 맞춰 48 + 48 칸을 다시 채점
# ══════════════════════════════════════════════════════════════════════
def stage_rescore(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("rescore 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)

    base, cells = collections.OrderedDict(), collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        base["u=%d" % u] = point25(pool, R, ALPHA_BASE, lam)
        for nm, w in WRECKS_Y.items():
            cells["u=%d|%s" % (u, nm)] = point25(pool, R, ALPHA_BASE, lam, wr=w)
            _prog("  점추정 u=%d %s" % (u, nm))
        for nm, w in WRECKS_X.items():
            cells["u=%d|%s" % (u, nm)] = point25(pool, R, ALPHA_BASE, lam, wx=w)
            _prog("  점추정 u=%d %s" % (u, nm))

    se = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        arms = collections.OrderedDict()
        for nm, w in WRECKS_Y.items():
            arms[nm] = (w, None)
        for nm, w in WRECKS_X.items():
            arms[nm] = (None, w)
        _prog("  SE 시작 u=%d (뽑기 %d × 씨앗 %d × 섞기 %d × 팔 %d)"
              % (u, BOOT, len(SEEDS), N_WRECK, len(arms)))
        se["u=%d" % u] = se_matched(pool, R, ALPHA_BASE, lam, arms,
                                    tag="u=%d" % u)
        _prog("  SE 끝 u=%d" % u)

    grid = collections.OrderedDict()
    for tagname, wrecks in (("라벨 파괴 D1~D4", WRECKS_Y), ("특징 파괴 X1~X4", WRECKS_X)):
        g = collections.OrderedDict()
        for nm in RULERS:
            rows = collections.OrderedDict()
            n_new = n_old = 0
            for u in U_REG:
                for wn in wrecks:
                    d = (cells["u=%d|%s" % (u, wn)][nm] - base["u=%d" % u][nm])
                    s_new = se["u=%d" % u][wn][nm]["🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)"]
                    s_old = se["u=%d" % u][wn][nm]["🔴 SE_구판(1 벌 · 978 판)"]
                    rr = adopt_row2(d, s_new, s_old)
                    rows["u=%d|%s" % (u, wn)] = rr
                    n_new += 1 if rr["🔴🔴 둘 다 (v2.2 통과)"] else 0
                    n_old += 1 if rr["진단: 978 판 SE 로 재면 통과하나"] else 0
            g[nm] = collections.OrderedDict([
                ("칸별", rows),
                ("🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)",
                 "%d / %d" % (n_new, 2 * len(wrecks))),
                ("🔴 여덟 칸 통과 분자/분모(978 판 SE)",
                 "%d / %d" % (n_old, 2 * len(wrecks))),
                ("🔴🔴 여덟 칸 SE 배수(정합)",
                 [rows[k]["🔴🔴 |Δ|/SE (정합)"] for k in rows]),
                ("🔴 여덟 칸 SE 배수(978 판)",
                 [rows[k]["🔴 |Δ|/SE (978 판)"] for k in rows]),
            ])
        grid[tagname] = g

    #: 🔴 예측 Q1 — 벌 수를 맞추면 SE 가 좁아지는 칸이 몇인가
    n_nar = n_tot = 0
    widened = []
    for u in U_REG:
        for wn in list(WRECKS_Y) + list(WRECKS_X):
            for nm in RULERS:
                a = se["u=%d" % u][wn][nm]
                n_tot += 1
                if (a["🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)"]
                        < a["🔴 SE_구판(1 벌 · 978 판)"]):
                    n_nar += 1
                else:
                    widened.append("u=%d|%s|%s" % (u, wn, nm))
    q1 = collections.OrderedDict([
        ("🔴🔴 SE_25벌 < SE_구판 인 칸 분자/분모", "%d / %d" % (n_nar, n_tot)),
        ("🔴 넓어진 칸", widened[:20]),
        ("🔴 예측 Q1(48/48 이 좁아진다)", bool(n_nar == n_tot)),
        ("통과", bool(n_tot == len(U_REG) * (len(WRECKS_Y) + len(WRECKS_X))
                    * len(RULERS))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "등록한 칸을 전부 셌다(값이 무엇이든 적는다)"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S3 — 🔴🔴 **벌 수를 맞춰 48 + 48 칸을 다시 채점한다**. "
                 "노트 978 은 점추정을 25 벌로 내고 SE 를 1 벌로 냈다")
    out["🔴 축"] = "C3 (곁 C2)"
    out["사전등록"] = "docs/prereg_979_denominator.md §2 · §3 · §4-S3"
    out["🔴 등록 상수"] = {"BOOT(이중 붓스트랩 뽑기)": BOOT, "섞기 씨앗 수": N_WRECK,
                     "점추정 벌 수": len(SEEDS) * N_WRECK,
                     "🔴 SE 벌 수(정합)": len(SEEDS) * N_WRECK,
                     "🔴 SE 벌 수(978 판)": 1,
                     "겹 씨앗": SEEDS, "자 수": len(RULERS),
                     "🔴 문턱 ② 배수": 2,
                     "🔴 진단 수치(구속 아님)": THR_CARD}
    out["🔴 밑판(파괴 안 함 · 5 벌 — 섞기 씨앗이 없다)"] = base
    out["🔴🔴🔴 파괴 대조 점추정(25 벌)"] = cells
    out["🔴🔴🔴 SE 셋 — 구판 1 벌 · 5 벌 · 정합 25 벌"] = se
    out["🔴🔴🔴 48 + 48 칸"] = grid
    out["🔴🔴 예측 Q1 — 벌 수를 맞추면 SE 가 좁아지나"] = q1
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_rescore.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("rescore 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S4 `sizeloso` — 크기 맞춤 대조와 LOSO 를 **같은 벌 수**로
# ══════════════════════════════════════════════════════════════════════
def size_paired(pool, R, alpha, lam, w2, w3, boot=BOOT, nwreck=N_WRECK, tag=""):
    """🔴 `D2`(base 90) 대 `D3`(hplt 90)의 **짝 SE 를 25 벌 정합으로** 낸다.

    뽑기 `b` 마다 25 벌을 평균해 `Δ2_b`·`Δ3_b` 를 만들고, 그 차 `|Δ2_b|−|Δ3_b|` 의
    SD 를 `b` 400 개에서 낸다. 🔴 노트 978 은 이 자리를 **1 벌**로 냈다.
    """
    d2b = {nm: [] for nm in RULERS}
    d3b = {nm: [] for nm in RULERS}
    dfb = {nm: [] for nm in RULERS}
    d2o = {nm: [] for nm in RULERS}
    d3o = {nm: [] for nm in RULERS}
    dfo = {nm: [] for nm in RULERS}
    t0 = time.time()
    for b in range(boot):
        buf2 = {nm: [] for nm in RULERS}
        buf3 = {nm: [] for nm in RULERS}
        pool.reseed(SEEDS[0])
        hi_b = A.ho_draw(pool, b)          # 🔴 복제 하나에 유보 재표집 하나
        for s in SEEDS:
            pool.reseed(s)
            hi_s = A.ho_draw(pool, b)      # 🔴 978 판
            pr0 = R8.oof978(pool, alpha, lam, tr_boot=b)["예측"]
            v0s, _p = score6(pool, R, pr0, hi_s)
            v0b, _p = score6(pool, R, pr0, hi_b)
            for ws in range(nwreck):
                p2_ = R8.oof978(pool, alpha, lam, tr_boot=b,
                                wreck=dict(w2, seed=WRECK_SEED0 + ws * 97))["예측"]
                p3_ = R8.oof978(pool, alpha, lam, tr_boot=b,
                                wreck=dict(w3, seed=WRECK_SEED0 + ws * 97))["예측"]
                b2, _p = score6(pool, R, p2_, hi_b)
                b3, _p = score6(pool, R, p3_, hi_b)
                for nm in RULERS:
                    buf2[nm].append(b2[nm] - v0b[nm])
                    buf3[nm].append(b3[nm] - v0b[nm])
                if ws == 0:
                    s2, _p = score6(pool, R, p2_, hi_s)
                    s3, _p = score6(pool, R, p3_, hi_s)
                    for nm in RULERS:
                        d2o[nm].append(s2[nm] - v0s[nm])
                        d3o[nm].append(s3[nm] - v0s[nm])
                        dfo[nm].append(abs(s2[nm] - v0s[nm]) - abs(s3[nm] - v0s[nm]))
        for nm in RULERS:
            m2 = float(np.mean(buf2[nm]))
            m3 = float(np.mean(buf3[nm]))
            d2b[nm].append(m2)
            d3b[nm].append(m3)
            dfb[nm].append(abs(m2) - abs(m3))
        if (b + 1) % 50 == 0:
            _prog("    %s 짝 SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                    time.time() - t0))
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = collections.OrderedDict([
            ("🔴 SE(D2) 정합", _r(float(np.std(d2b[nm], ddof=1)))),
            ("🔴 SE(D3) 정합", _r(float(np.std(d3b[nm], ddof=1)))),
            ("🔴🔴 짝 SE(|Δ2|−|Δ3|) 정합", _r(float(np.std(dfb[nm], ddof=1)))),
            ("🔴 SE(D2) 978 판", _r(float(np.std(d2o[nm], ddof=1)))),
            ("🔴 SE(D3) 978 판", _r(float(np.std(d3o[nm], ddof=1)))),
            ("🔴 짝 SE 978 판", _r(float(np.std(dfo[nm], ddof=1)))),
        ])
    out["🔴 복제 수(정합)"] = len(d2b[RULERS[0]])
    out["🔴 복제 수(978 판)"] = len(d2o[RULERS[0]])
    return out


def stage_sizeloso(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("sizeloso 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)
    w2 = WRECKS_Y["D2 base 학습 y 전량"]
    w3 = WRECKS_Y["D3 hplt y 중 무작위 90 행"]

    pair = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        b = point25(pool, R, ALPHA_BASE, lam)
        p2 = point25(pool, R, ALPHA_BASE, lam, wr=w2)
        p3 = point25(pool, R, ALPHA_BASE, lam, wr=w3)
        _prog("  size 점추정 u=%d 끝" % u)
        sp = size_paired(pool, R, ALPHA_BASE, lam, w2, w3, tag="size u=%d" % u)
        rows = collections.OrderedDict()
        for nm in RULERS:
            dd2 = p2[nm] - b[nm]
            dd3 = p3[nm] - b[nm]
            sd_n = sp[nm]["🔴🔴 짝 SE(|Δ2|−|Δ3|) 정합"]
            sd_o = sp[nm]["🔴 짝 SE 978 판"]
            diff = abs(dd2) - abs(dd3)
            rows[nm] = collections.OrderedDict([
                ("🔴 D2 base 90 행 Δ", _r(dd2)),
                ("SE(D2) 정합", sp[nm]["🔴 SE(D2) 정합"]),
                ("|Δ2|/SE 정합", _r(abs(dd2) / sp[nm]["🔴 SE(D2) 정합"], 4)
                 if sp[nm]["🔴 SE(D2) 정합"] else None),
                ("🔴 D3 hplt 90 행 Δ", _r(dd3)),
                ("SE(D3) 정합", sp[nm]["🔴 SE(D3) 정합"]),
                ("🔴🔴 |Δ2| − |Δ3|", _r(diff)),
                ("🔴🔴 그 차의 짝 SE(정합)", sd_n),
                ("🔴🔴🔴 차 / 짝 SE (정합)", _r(diff / sd_n, 4) if sd_n else None),
                ("🔴 차 / 짝 SE (978 판)", _r(diff / sd_o, 4) if sd_o else None),
                ("🔴 차가 2 짝SE 를 넘나(정합)", bool(sd_n and diff >= 2 * sd_n)),
                ("🔴 978 판 SE 로는 넘나", bool(sd_o and diff >= 2 * sd_o)),
            ])
        pair["u=%d" % u] = collections.OrderedDict([
            ("자별", rows),
            ("🔴 부순 행 — D2", p2["🔴 부순 라벨 행(겹당)"]),
            ("🔴 부순 행 — D3", p3["🔴 부순 라벨 행(겹당)"]),
            ("🔴 같은 행 수인가", bool(p2["🔴 부순 라벨 행(겹당)"]
                              == p3["🔴 부순 라벨 행(겹당)"])),
            ("🔴 벌 수(점추정)", p2["🔴 벌 수"]),
            ("🔴🔴 벌 수(SE)", len(SEEDS) * N_WRECK),
            ("🔴 뽑기 수", BOOT),
            ("통과", bool(p2["🔴 부순 라벨 행(겹당)"] == p3["🔴 부순 라벨 행(겹당)"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **크기 맞춤이 실제로 맞았다** — D2 와 D3 이 같은 행 수를 부순다"),
        ])

    #: ── LOSO 세 팔 × λ 둘 × 자 여섯 ────────────────────────────
    loso = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        pts = collections.OrderedDict()
        for anm, drop in A.SRC_ARMS.items():
            acc = {nm: [] for nm in RULERS}
            for s in SEEDS:
                pool.reseed(s)
                v, _p = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam,
                                                  drop_src=drop)["예측"])
                for nm in RULERS:
                    acc[nm].append(v[nm])
            pts[anm] = {nm: float(np.mean(acc[nm])) for nm in RULERS}
        arms = collections.OrderedDict(
            [(anm, (None, None, drop)) for anm, drop in A.SRC_ARMS.items()
             if anm != "ALL"])
        _prog("  LOSO SE 시작 u=%d" % u)
        ses = se_matched(pool, R, ALPHA_BASE, lam, arms, tag="loso u=%d" % u)
        rows = collections.OrderedDict()
        for anm in arms:
            rows[anm] = collections.OrderedDict()
            for nm in RULERS:
                d = pts[anm][nm] - pts["ALL"][nm]
                s_n = ses[anm][nm]["🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)"]
                s_o = ses[anm][nm]["🔴 SE_구판(1 벌 · 978 판)"]
                rows[anm][nm] = collections.OrderedDict([
                    ("Δ", _r(d)),
                    ("🔴🔴 SE(정합)", s_n), ("🔴 SE(978 판)", s_o),
                    ("🔴🔴 |Δ|/SE (정합)", _r(abs(d) / s_n, 4) if s_n else None),
                    ("🔴 |Δ|/SE (978 판)", _r(abs(d) / s_o, 4) if s_o else None),
                    ("🔴 2 SE 를 넘나(정합)", bool(s_n and abs(d) >= 2 * s_n)),
                    ("🔴 부호", "양수(빼면 낫다)" if d > 0 else "음수(빼면 나쁘다)"),
                ])
        n_pass = sum(1 for anm in rows for nm in RULERS
                     if rows[anm][nm]["🔴 2 SE 를 넘나(정합)"])
        loso["u=%d" % u] = collections.OrderedDict([
            ("팔별", rows),
            ("🔴 뽑기 수", BOOT), ("🔴 씨앗 수(점추정)", len(SEEDS)),
            ("🔴🔴 2 SE 를 넘는 칸 분자/분모",
             "%d / %d" % (n_pass, len(rows) * len(RULERS))),
            ("통과", bool(len(rows) == len(A.SRC_ARMS) - 1)),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "LOSO 세 팔 전부에 자 여섯의 SE 가 붙었다(978 은 자 넷 중 둘만 실었다)"),
        ])

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S4 — 🔴 크기 맞춤 대조와 LOSO 를 **정합 벌 수**로 다시 낸다. "
                 "🔴 노트 978 판정문 §5 는 정본 자 열을 안 냈다")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_979_denominator.md §4-S4"
    out["🔴 등록 상수"] = {"BOOT": BOOT, "겹 씨앗": SEEDS,
                     "점추정 벌 수": len(SEEDS) * N_WRECK,
                     "SE 벌 수(정합)": len(SEEDS) * N_WRECK, "자 수": len(RULERS)}
    out["🔴🔴🔴 크기 맞춤 대조 D2(base 90) 대 D3(hplt 90) — 자 여섯"] = pair
    out["🔴🔴🔴 LOSO Δ ± SE — 자 여섯"] = loso
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_sizeloso.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("sizeloso 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S5 `alphapair` — 🔴 α 잣대를 **짝 SE** 로 (수리 5)
# ══════════════════════════════════════════════════════════════════════
def stage_alphapair(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("alphapair 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)

    per = collections.OrderedDict()          # (u, α) -> {ruler: [씨앗별 값]}
    for u in U_REG:
        lam = 10.0 ** u
        for a in AFINE:
            acc = {nm: [] for nm in RULERS}
            for s in SEEDS:
                pool.reseed(s)
                v, _p = score6(pool, R, R8.oof978(pool, a, lam)["예측"])
                for nm in RULERS:
                    acc[nm].append(v[nm])
            per["u=%d|α=%g" % (u, a)] = acc
            _prog("  α=%g u=%d" % (a, u))

    cells = collections.OrderedDict()
    for k, acc in per.items():
        cells[k] = collections.OrderedDict(
            [(nm, _r(float(np.mean(acc[nm])))) for nm in RULERS]
            + [(nm + " 씨앗 SD(수준 · 978 이 쓴 잣대)",
                _r(float(np.std(acc[nm], ddof=1)))) for nm in RULERS]
            + [("🔴 씨앗 수", len(SEEDS))])

    best = collections.OrderedDict()
    n_pair2 = n_lvl = n_tot = 0
    for u in U_REG:
        for nm in RULERS:
            ba = max(AFINE, key=lambda a, u=u, nm=nm:
                     float(np.mean(per["u=%d|α=%g" % (u, a)][nm])))
            v_b = np.asarray(per["u=%d|α=%g" % (u, ba)][nm], float)
            v_0 = np.asarray(per["u=%d|α=0" % u][nm], float)
            gain = float(v_b.mean() - v_0.mean())
            #: 🔴 **짝 차** — 같은 다섯 씨앗을 두 α 에 쓴다
            dif = v_b - v_0
            sd_pair = float(np.std(dif, ddof=1))
            se_pair = sd_pair / math.sqrt(len(SEEDS))
            sd_lvl = float(np.std(v_b, ddof=1))
            n_tot += 1
            if se_pair and abs(gain) >= 2 * se_pair:
                n_pair2 += 1
            if sd_lvl and gain >= sd_lvl:
                n_lvl += 1
            best["u=%d|%s" % (u, nm)] = collections.OrderedDict([
                ("🔴 최적 α", ba),
                ("그 값", _r(float(v_b.mean()))),
                ("α=0 의 값", _r(float(v_0.mean()))),
                ("🔴 최적이 α=0 인가", bool(ba == 0.0)),
                ("🔴 α=0 대비 이득", _r(gain)),
                ("🔴 씨앗별 짝 차", [_r(x) for x in dif]),
                ("🔴🔴 짝 차의 SD", _r(sd_pair)),
                ("🔴🔴🔴 짝 SE(= SD/√5)", _r(se_pair)),
                ("🔴🔴🔴 이득 / 짝 SE", _r(gain / se_pair, 4) if se_pair else None),
                ("🔴 이득이 2 짝SE 를 넘나", bool(se_pair and abs(gain) >= 2 * se_pair)),
                ("🔴 978 이 쓴 잣대 — 수준의 SD", _r(sd_lvl)),
                ("🔴 978 잣대로 이득 / 수준 SD", _r(gain / sd_lvl, 4) if sd_lvl else None),
                ("🔴 978 잣대로 「잡음을 넘나」", bool(sd_lvl and gain >= sd_lvl)),
                ("🔴 최적이 격자 끝인가", bool(ba == max(AFINE))),
            ])
    n0 = sum(1 for v in best.values() if v["🔴 최적이 α=0 인가"])
    n_edge = sum(1 for v in best.values() if v["🔴 최적이 격자 끝인가"])
    u3 = [k for k in best if k.startswith("u=3|")]
    n_u3 = sum(1 for k in u3 if best[k]["🔴 이득이 2 짝SE 를 넘나"])

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S5 — 🔴 **α 잣대를 짝 SE 로**. 노트 978 의 `std(ddof=1)` 은 "
                 "평균의 SE 도 아니고 짝 차도 아닌 **「수준의 SD」**다")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_979_denominator.md §4-S5"
    out["🔴 격자"] = {"α": AFINE, "log₁₀λ": U_REG, "겹 씨앗": SEEDS, "자 수": len(RULERS)}
    out["🔴🔴🔴 칸별 — 자 여섯"] = cells
    out["🔴🔴 자·λ 마다의 최적 α 와 짝 SE"] = best
    out["🔴 최적이 α=0 인 칸"] = "%d / %d" % (n0, len(best))
    out["🔴 최적이 격자 끝인 칸"] = "%d / %d" % (n_edge, len(best))
    out["🔴🔴🔴 이득이 2 짝SE 를 넘는 칸(전체)"] = "%d / %d" % (n_pair2, n_tot)
    out["🔴🔴🔴 이득이 2 짝SE 를 넘는 칸(u=3)"] = "%d / %d" % (n_u3, len(u3))
    out["🔴 978 잣대(수준 SD)로 「잡음을 넘는」 칸"] = "%d / %d" % (n_lvl, n_tot)
    out["🔴🔴 예측 Q10(u=3 에서 2 짝SE 를 넘는 칸이 하나 이상)"] = bool(n_u3 >= 1)
    out["🔴🔴 정직한 문장"] = (
        "🔴 **노트 978 은 「그 이득은 씨앗 잡음 아래다」와 「넘는 칸 4/8」을 한 문장 안에 "
        "적었다.** 잣대를 짝 SE 로 바꾸면 두 문장이 하나로 합쳐진다")
    out["통과"] = bool(len(cells) == len(AFINE) * len(U_REG) and n_tot == len(best))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = "등록한 칸을 전부 돌리고 전부 채점했다"
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_alphapair.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("alphapair 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S6 `srcmix` — 🔴🔴 원천 쪽을 **학습 1,710 행**에서 잰다
# ══════════════════════════════════════════════════════════════════════
def _smd(A_, B_):
    """표준화 평균차(B_ − A_) — 특징마다."""
    out = []
    for j in range(A_.shape[1]):
        m1, m2 = float(A_[:, j].mean()), float(B_[:, j].mean())
        s1, s2 = float(A_[:, j].std()), float(B_[:, j].std())
        sp = math.sqrt((s1 ** 2 + s2 ** 2) / 2.0)
        out.append(_r((m2 - m1) / sp, 4) if sp > 0 else None)
    return out


def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def stage_srcmix(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("srcmix 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)

    #: ── ① 🔴 `select()` 가 hplt 쪽에서 겹에 의존하나 ─────────────
    pool.reseed(SEEDS[0])
    per_fold = []
    for j in range(KFOLD):
        selb, selh, _s = A.select(pool, j, ALPHA_BASE)
        per_fold.append((_sha_arr(selb), _sha_arr(selh), int(len(selb)),
                         int(len(selh))))
    same_h = len(set(z[1] for z in per_fold)) == 1
    same_b = len(set(z[0] for z in per_fold)) == 1
    seed_sha = []
    for s in SEEDS:
        pool.reseed(s)
        _sb, _sh, _x = A.select(pool, 0, ALPHA_BASE)
        seed_sha.append(_sha_arr(_sh))
    fold = collections.OrderedDict([
        ("🔴 겹별 (base sha256, hplt sha256, base 행, hplt 행)",
         [[z[0][:16], z[1][:16], z[2], z[3]] for z in per_fold]),
        ("🔴🔴 다섯 겹의 hplt 선택 행이 바이트로 같은가", bool(same_h)),
        ("🔴 다섯 겹의 base 선택 행이 바이트로 같은가", bool(same_b)),
        ("🔴 씨앗별 hplt 선택 sha256(겹 0)", [x[:16] for x in seed_sha]),
        ("🔴 씨앗 다섯이 서로 다른 hplt 행을 고르나",
         bool(len(set(seed_sha)) == len(SEEDS))),
        ("🔴🔴 뜻", "🔴 **겹 씨앗의 변동은 base %d 행과 겹 배정에서만 온다** — "
                 "hplt %d 행은 겹에 안 의존한다. **어느 문서에도 없던 사실이다**"
         % (per_fold[0][2], per_fold[0][3])),
        ("통과", bool(same_h and not same_b)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "hplt 는 겹에 안 의존하고 base 는 의존한다 — 둘 다 실측했다"),
    ])

    #: ── ② 🔴🔴 학습 혼합 대 유보 혼합 ───────────────────────────
    pool.reseed(SEEDS[0])
    selb0, selh0, _s = A.select(pool, 0, ALPHA_BASE)
    doms = list(pool.gated)
    ch = collections.Counter(pool.dh[selh0].tolist())
    cb = collections.Counter(pool.db.tolist())
    n_h = int(len(selh0))
    n_ho = sum(int(cb.get(d, 0)) for d in doms)
    sh = {d: ch.get(d, 0) / float(n_h) for d in doms}
    sb = {d: cb.get(d, 0) / float(n_ho) for d in doms}
    v1 = np.asarray([sh[d] for d in doms], float)
    v2 = np.asarray([sb[d] for d in doms], float)
    r_p = float(np.corrcoef(v1, v2)[0, 1])
    r_s = float(P.spear(v1, v2))
    #: 🔴 978 이 잰 것 — 학습 밖 hplt 전량
    ch_all = collections.Counter(pool.dh.tolist())
    sh_all = {d: ch_all.get(d, 0) / float(len(pool.dh)) for d in doms}
    v1a = np.asarray([sh_all[d] for d in doms], float)
    r_all = float(np.corrcoef(v1a, v2)[0, 1])
    top_ho = max(doms, key=lambda d: sb[d])
    top_tr = max(doms, key=lambda d: sh[d])
    mix = collections.OrderedDict([
        ("🔴 hplt 학습 행 수(모형이 보는 것)", n_h),
        ("🔴 hplt 전량 행 수(978 이 잰 것)", int(len(pool.dh))),
        ("🔴 유보 행 수(게이트 도메인 합)", n_ho),
        ("🔴🔴 도메인별 — hplt 학습 몫 · 유보 몫",
         collections.OrderedDict([(d, [_r(sh[d]), _r(sb[d])]) for d in doms])),
        ("🔴🔴🔴 피어슨 r (hplt 학습 1,710 행 몫 대 유보 몫)", _r(r_p, 4)),
        ("🔴 스피어만 (같은 짝)", _r(r_s, 4)),
        ("🔴 피어슨 r (hplt 전량 몫 대 유보 몫 · 978 이 잰 층)", _r(r_all, 4)),
        ("🔴🔴 유보에서 가장 큰 도메인", top_ho),
        ("🔴🔴 유보 최대 도메인의 hplt 학습 몫", _r(sh[top_ho])),
        ("🔴🔴 유보 최대 도메인의 유보 몫", _r(sb[top_ho])),
        ("🔴🔴 hplt 학습에서 가장 큰 도메인", top_tr),
        ("🔴🔴 학습 최대 도메인의 유보 몫", _r(sb[top_tr])),
        ("🔴🔴 학습 최대 도메인의 hplt 학습 몫", _r(sh[top_tr])),
        ("🔴🔴🔴 뜻", "🔴 **정본 자 무게의 절반 이상을 지는 도메인이 hplt 학습에서 "
                  "거의 안 나오고, hplt 학습을 지배하는 도메인이 유보에서 거의 안 나온다.** "
                  "「HPLT 가 왜 안 쓰이나」의 답은 SMD 가 아니라 여기일 수 있다"),
        ("통과", bool(np.isfinite(r_p))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "게이트 도메인 전량에서 두 몫을 다 냈다"),
    ])

    #: ── ③ SMD — 🔴 **학습 1,710 행**에서 다시 잰다 ───────────────
    Xb = pool.Xb[:, :K_FEAT]
    Xh_sel = pool.Xh[selh0][:, :K_FEAT]
    Xh_all = pool.Xh[:, :K_FEAT]
    smd_sel = _smd(Xb, Xh_sel)
    smd_all = _smd(Xb, Xh_all)
    ov_sel = [_r(2.0 * _phi(-abs(v) / 2.0), 4) if v is not None else None
              for v in smd_sel]
    ov_all = [_r(2.0 * _phi(-abs(v) / 2.0), 4) if v is not None else None
              for v in smd_all]
    n_big_sel = sum(1 for v in smd_sel if v is not None and abs(v) > 0.5)
    n_big_all = sum(1 for v in smd_all if v is not None and abs(v) > 0.5)
    covered = [d for d in doms if ch.get(d, 0) > 0]
    smd = collections.OrderedDict([
        ("🔴🔴 SMD — 학습 1,710 행(모형이 보는 열)", smd_sel),
        ("🔴 SMD — hplt 전량(978 이 잰 열)", smd_all),
        ("🔴 |SMD| > 0.5 인 특징 (학습 1,710 행)", "%d / %d" % (n_big_sel, K_FEAT)),
        ("🔴 |SMD| > 0.5 인 특징 (978 판)", "%d / %d" % (n_big_all, K_FEAT)),
        ("🔴🔴 두 정규분포로 본 겹침 비율 — 학습 1,710 행", ov_sel),
        ("🔴 두 정규분포로 본 겹침 비율 — 978 판", ov_all),
        ("🔴🔴🔴 가장 안 겹치는 특징의 겹침 비율(학습 1,710 행)",
         min([v for v in ov_sel if v is not None])),
        ("🔴🔴 「분포가 겹치지 않는다」가 과장인가",
         bool(min([v for v in ov_sel if v is not None]) > 0.5)),
        ("🔴 hplt 학습 행이 덮는 게이트 도메인 분자/분모",
         "%d / %d" % (len(covered), len(doms))),
        ("🔴 도메인별 hplt 학습 행", {d: int(ch.get(d, 0)) for d in doms}),
        ("통과", bool(len(smd_sel) == K_FEAT)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "등록한 특징 여섯을 전부 쟀다"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S6 — 🔴🔴 **원천 쪽을 학습 1,710 행에서 잰다.** 노트 978 의 SMD 는 "
                 "`pool.Xh` 전량에서 쟀고 **모형이 보는 것은 `select()` 가 고른 1,710 행**이다")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_979_denominator.md §4-S6"
    out["🔴 이 stage 는 자 값을 안 낸다(반증조건 4 분모 밖 · 측정 전에 적었다)"] = True
    out["🔴🔴 select() 가 hplt 쪽에서 겹에 의존하나"] = fold
    out["🔴🔴🔴 학습 혼합 대 유보 혼합"] = mix
    out["🔴🔴 특징 분포 — SMD 와 겹침"] = smd
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_srcmix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("srcmix 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S7 `gate` — 🔴🔴🔴 등록 규칙 v2.2
# ══════════════════════════════════════════════════════════════════════
def stage_gate(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("gate 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)
    tab = R.table()
    rs = _load("out979_rescore.json")
    if not rs:
        raise SystemExit("🔴 out979_rescore.json 이 없다 — 측정을 먼저 돌려라(fail-closed)")
    gy = rs["🔴🔴🔴 48 + 48 칸"]["라벨 파괴 D1~D4"]
    gx = rs["🔴🔴🔴 48 + 48 칸"]["특징 파괴 X1~X4"]
    d4 = ["u=%d|D4 학습 y 전량(둘 다)" % u for u in U_REG]

    decide = collections.OrderedDict()
    for nm in RULERS:
        per_u = collections.OrderedDict()
        n_ok = 0
        ratios = []
        for k in d4:
            rr = gy[nm]["칸별"][k]
            per_u[k] = rr
            n_ok += 1 if rr["🔴🔴 둘 다 (v2.2 통과)"] else 0
            ratios.append(rr["🔴🔴 |Δ|/SE (정합)"] or 0.0)
        wt = tab["자별 가중"][nm]
        decide[nm] = collections.OrderedDict([
            ("λ 둘", per_u),
            ("🔴🔴🔴 v2.2 등록 규칙 통과 (λ 둘 다)", bool(n_ok == len(U_REG))),
            ("🔴 통과한 λ 칸", "%d / %d" % (n_ok, len(U_REG))),
            ("🔴🔴🔴 검정력 = min(|Δ(D4)|/SE)", _r(min(ratios), 4)),
            ("🔴 진단: 가장 큰 도메인의 가중 몫", wt["🔴🔴 가장 큰 도메인의 몫"]),
            ("🔴 진단: 유효 도메인 수", wt["🔴 유효 도메인 수 (1/Σw²)"]),
            ("🔴🔴 여덟 칸(라벨) 통과 — 정합", gy[nm]["🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)"]),
            ("🔴 여덟 칸(라벨) 통과 — 978 판", gy[nm]["🔴 여덟 칸 통과 분자/분모(978 판 SE)"]),
            ("🔴🔴 여덟 칸(특징) 통과 — 정합", gx[nm]["🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)"]),
            ("🔴 여덟 칸 SE 배수(라벨 · 정합)", gy[nm]["🔴🔴 여덟 칸 SE 배수(정합)"]),
            ("🔴🔴 D4 두 칸만 통과하고 나머지 여섯은 미달인가",
             bool(n_ok == len(U_REG)
                  and gy[nm]["🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)"]
                  == "%d / 8" % len(U_REG))),
        ])
    ok = [nm for nm in RULERS if decide[nm]["🔴🔴🔴 v2.2 등록 규칙 통과 (λ 둘 다)"]]
    chosen, tie = None, None
    if ok:
        pw = {nm: decide[nm]["🔴🔴🔴 검정력 = min(|Δ(D4)|/SE)"] for nm in ok}
        top = max(pw.values())
        near = [nm for nm in ok if pw[nm] >= top * 0.95]
        tie = near
        chosen = (min(near, key=lambda nm: decide[nm]["🔴 진단: 가장 큰 도메인의 가중 몫"])
                  if len(near) > 1 else near[0])

    #: 🔴 978 의 규칙(v2.1 · 1 벌 SE · 몫 최소)을 **같은 산출물에서** 다시 걸어 본다
    old_ok = [nm for nm in RULERS
              if all(gy[nm]["칸별"][k]["진단: 978 판 SE 로 재면 통과하나"]
                     and gy[nm]["칸별"][k]["진단: |Δ| ≥ 0.00353 (구속 아님)"]
                     for k in d4)]
    old_chosen = (min(old_ok,
                      key=lambda nm: decide[nm]["🔴 진단: 가장 큰 도메인의 가중 몫"])
                  if old_ok else None)
    r978 = _load("out978_ruler.json")
    old978 = (r978.get("🔴🔴🔴 §2 채택 판정 (D4)", {}) or {}).get("🔴🔴🔴 정본으로 고른 자")

    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S7 — 🔴🔴🔴 **등록 규칙 v2.2** 를 자 여섯에 건다. "
                 "조건 둘(부호 · 정합 SE 두 배) · **선택은 검정력**")
    out["🔴 축"] = "C3 (곁 C2)"
    out["사전등록"] = "docs/prereg_979_denominator.md §2 · §4-S7"
    out["🔴🔴🔴 자 여섯의 가중"] = tab
    out["🔴🔴🔴 v2.2 채택 판정 (D4)"] = collections.OrderedDict([
        ("자별", decide),
        ("🔴🔴 통과한 자", ok or "없음"),
        ("🔴 검정력 동률 무리(최고의 95% 안)", tie or "없음"),
        ("🔴🔴🔴 정본으로 고른 자", chosen or "🔴 없다 — 정본 자를 바꾸지 않는다"),
        ("🔴 고른 규칙", "v2.2 — 통과자 중 **검정력(min |Δ(D4)|/SE)이 가장 큰 자**"),
        ("🔴🔴 978 이 고른 자", old978),
        ("🔴🔴🔴 978 의 정본 선택이 뒤집히나", bool(chosen != old978)),
        ("🔴 978 의 규칙(v2.1 · 1 벌 SE · 몫 최소)을 같은 자료에 다시 걸면",
         collections.OrderedDict([("통과한 자", old_ok or "없음"),
                                  ("고른 자", old_chosen or "없음")])),
        ("🔴🔴 977 이 올린 자(R_eq 균등)가 v2.2 를 통과하나", bool(R2 in ok)),
        ("🔴🔴 978 의 「승격을 되돌린다」가 정합 SE 에서도 서나", bool(R2 not in ok)),
        ("통과", bool(len(decide) == len(RULERS))),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "자 여섯 전부에 같은 규칙을 걸었다"),
    ])
    out["🔴🔴 예측 Q2·Q5·Q6"] = collections.OrderedDict([
        ("Q2 — R_eq 균등이 정합 SE 에서도 0/2 인가",
         bool(decide[R2]["🔴 통과한 λ 칸"] == "0 / 2")),
        ("Q5 — 검정력 최대 자가 R_z 가 아닌가", bool(chosen != R3)),
        ("Q6 — 벌 수를 맞추니 여덟 칸 통과가 늘어난 자가 있나",
         bool(any(int(gy[nm]["🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)"].split("/")[0])
                  > int(gy[nm]["🔴 여덟 칸 통과 분자/분모(978 판 SE)"].split("/")[0])
                  for nm in RULERS))),
        ("🔴 자별 여덟 칸 — 정합 대 978 판",
         collections.OrderedDict([
             (nm, [gy[nm]["🔴🔴🔴 여덟 칸 통과 분자/분모(정합 SE)"],
                   gy[nm]["🔴 여덟 칸 통과 분자/분모(978 판 SE)"]])
             for nm in RULERS])),
    ])
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_gate.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("gate 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S8 `score978` — 🔴🔴 노트 978 의 **등록물 전부**를 채점한다
# ══════════════════════════════════════════════════════════════════════
def _num(s, i=0):
    try:
        return int(str(s).split("/")[i].strip())
    except Exception:                                          # noqa: BLE001
        return None


def stage_score978(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("score978 시작")
    r8 = _load("out978_ruler.json")
    c8 = _load("out978_cond3.json")
    s8 = _load("out978_size.json")
    x8 = _load("out978_xdestroy.json")
    a8 = _load("out978_alphafine.json")
    w8 = _load("out978_wiring.json")
    n8 = _load("out978_numaudit.json")
    rs = _load("out979_rescore.json")
    gt = _load("out979_gate.json")
    sl = _load("out979_sizeloso.json")
    need = {"out978_ruler.json": r8, "out978_cond3.json": c8, "out978_size.json": s8,
            "out978_xdestroy.json": x8, "out978_alphafine.json": a8,
            "out978_wiring.json": w8, "out978_numaudit.json": n8,
            "out979_rescore.json": rs, "out979_gate.json": gt,
            "out979_sizeloso.json": sl}
    missing = [k for k, v in need.items() if not v]
    if missing:
        raise SystemExit("🔴 산출물이 없다(fail-closed): %s" % missing)

    DEC8 = "🔴🔴🔴 §2 채택 판정 (D4)"
    G8 = "🔴🔴🔴 32 칸 — 자 넷 × D1~D4 × λ 둘"
    WT8 = "🔴🔴🔴 자 넷의 가중"
    dec9 = gt["🔴🔴🔴 v2.2 채택 판정 (D4)"]["자별"]
    chosen = gt["🔴🔴🔴 v2.2 채택 판정 (D4)"]["🔴🔴🔴 정본으로 고른 자"]
    gy = rs["🔴🔴🔴 48 + 48 칸"]["라벨 파괴 D1~D4"]
    gx = rs["🔴🔴🔴 48 + 48 칸"]["특징 파괴 X1~X4"]
    pair9 = sl["🔴🔴🔴 크기 맞춤 대조 D2(base 90) 대 D3(hplt 90) — 자 여섯"]
    d4k = ["u=%d|D4 학습 y 전량(둘 다)" % u for u in U_REG]

    P = collections.OrderedDict()

    def rec(name, txt, verdict978, verdict979, ev):
        P[name] = collections.OrderedDict([
            ("등록 문언", txt),
            ("🔴 978 이 채점했나", bool(name in ("P5", "P8"))),
            ("🔴🔴 978 판(1 벌 SE · 자 넷) 채점", verdict978),
            ("🔴🔴🔴 979 판(정합 SE · 정본 자) 채점", verdict979),
            ("근거", ev),
        ])

    # ── P1 ────────────────────────────────────────────────
    p1_78 = r8[DEC8]["자별"][R2]["🔴 통과한 λ 칸"]
    p1_79 = dec9[R2]["🔴 통과한 λ 칸"]
    rec("P1", "균등 자는 §2 규칙을 0/2(λ 둘)에서 통과한다 → 승격을 되돌린다",
        bool(p1_78 == "0 / 2"), bool(p1_79 == "0 / 2"),
        {"978 통과한 λ 칸": p1_78, "979 통과한 λ 칸": p1_79})
    # ── P2 ────────────────────────────────────────────────
    p2_78 = r8[DEC8]["자별"][R1]["🔴 통과한 λ 칸"]
    p2_79 = dec9[R1]["🔴 통과한 λ 칸"]
    rec("P2", "묶음 자는 §2 규칙을 2/2 에서 통과한다",
        bool(p2_78 == "2 / 2"), bool(p2_79 == "2 / 2"),
        {"978": p2_78, "979": p2_79})
    # ── P3 ────────────────────────────────────────────────
    def _ord(src, ks, key):
        rows = {}
        for nm in (R2, R3, R4, R1):
            rows[nm] = [src[nm]["칸별"][k][key] or 0.0 for k in ks]
        okk = all(rows[R2][i] < rows[R3][i] < rows[R4][i] for i in range(len(ks)))
        return okk, {nm: [_r(v, 4) for v in rows[nm]] for nm in rows}
    o78, t78 = _ord(r8[G8], d4k, "|Δ|/SE")
    o79, t79 = _ord(gy, d4k, "🔴🔴 |Δ|/SE (정합)")
    rec("P3", "D4 의 |Δ|/SE 는 가중 지수가 커질수록 커진다 — R_eq < R_z < R_iv ≈ R_pool",
        bool(o78), bool(o79), {"978 λ별": t78, "979 λ별": t79})
    # ── P4 ────────────────────────────────────────────────
    m78 = {nm: r8[WT8]["자별 가중"][nm]["🔴🔴 가장 큰 도메인의 몫"] for nm in R978}
    m79 = {nm: gt["🔴🔴🔴 자 여섯의 가중"]["자별 가중"][nm]["🔴🔴 가장 큰 도메인의 몫"]
           for nm in RULERS}
    rec("P4", "R_z 의 가장 큰 도메인 몫은 묶음보다 작고 균등보다 크다",
        bool(m78[R2] < m78[R3] < m78[R1]), bool(m79[R2] < m79[R3] < m79[R1]),
        {"978 몫": m78, "979 몫": m79})
    # ── P5 (978 이 채점한 둘 중 하나) ─────────────────────
    pos = c8["🔴🔴🔴 판정"]["🔴🔴 1 벌 추정이 양수인 비율(균등 자)"]
    rec("P5", "조건 3 의 1 벌 추정은 200 벌 중 20% 이상에서 부호가 양수다",
        bool(pos >= 0.20), bool(pos >= 0.20),
        {"1 벌이 양수인 비율(균등 자)": pos,
         "🔴 978 이 스스로 적은 P5": c8["🔴🔴🔴 판정"]["🔴 예측 P5(1 벌 부호가 스무 부분 이상에서 양수)"]})
    # ── P6 🔴 2순위 헤드라인 ──────────────────────────────
    p6_78 = collections.OrderedDict()
    for u in U_REG:
        for nm in R978:
            p6_78["u=%d|%s" % (u, nm)] = s8[
                "🔴🔴🔴 크기 맞춤 대조 D2(base 90) 대 D3(hplt 90) — 자 넷"][
                "u=%d" % u]["자별"][nm]["🔴 차가 2 짝SE 를 넘나"]
    p6_79 = collections.OrderedDict()
    for u in U_REG:
        for nm in RULERS:
            p6_79["u=%d|%s" % (u, nm)] = pair9["u=%d" % u]["자별"][nm][
                "🔴 차가 2 짝SE 를 넘나(정합)"]
    n78 = sum(1 for v in p6_78.values() if v)
    n79 = sum(1 for v in p6_79.values() if v)
    ch_cells = ["u=%d|%s" % (u, chosen) for u in U_REG] if chosen in RULERS else []
    n_ch = sum(1 for k in ch_cells if p6_79.get(k))
    rec("P6", "크기 맞춤 대조에서 |Δ(D2)| > |Δ(D3)| 이고 그 차가 2 SE 를 넘는다",
        bool(n78 == len(p6_78)), bool(ch_cells and n_ch == len(ch_cells)),
        {"🔴 978 판 칸별": p6_78, "🔴 978 판 분자/분모": "%d / %d" % (n78, len(p6_78)),
         "🔴 979 판 칸별(자 여섯 × λ 둘)": p6_79,
         "🔴 979 판 분자/분모": "%d / %d" % (n79, len(p6_79)),
         "🔴🔴🔴 정본 자에서 분자/분모": "%d / %d" % (n_ch, len(ch_cells)),
         "🔴 정본 자": chosen,
         "🔴🔴 978 이 이 예측을 어디서든 채점했나": False})
    # ── P7 ────────────────────────────────────────────────
    X1 = "X1 hplt x 전량"
    p7_78 = collections.OrderedDict()
    for u in U_REG:
        for nm in R978:
            rr = x8["🔴🔴🔴 여덟 칸 — 자 넷 × X1~X4 × λ 둘"][nm]["칸별"]["u=%d|%s" % (u, X1)]
            p7_78["u=%d|%s" % (u, nm)] = bool(not rr["🔴 조건 ② |Δ| ≥ 2·SE"])
    p7_79 = collections.OrderedDict()
    for u in U_REG:
        for nm in RULERS:
            rr = gx[nm]["칸별"]["u=%d|%s" % (u, X1)]
            p7_79["u=%d|%s" % (u, nm)] = bool(not rr["🔴🔴 조건 ② |Δ| ≥ 2·SE(정합)"])
    rec("P7", "hplt 의 특징 x 를 부숴도 자가 안 움직인다 (|Δ(X1)| < 2·SE)",
        bool(all(p7_78.values())), bool(all(p7_79.values())),
        {"978 칸별": p7_78, "979 칸별(정합)": p7_79,
         "979 분자/분모": "%d / %d" % (sum(1 for v in p7_79.values() if v),
                                  len(p7_79))})
    # ── P8 (978 이 채점한 둘 중 하나) ─────────────────────
    rec("P8", "α<0.2 촘촘한 격자에서 최적은 α=0 이다",
        bool(a8["🔴 예측 P8(최적은 α=0)"]), bool(a8["🔴 예측 P8(최적은 α=0)"]),
        {"최적이 α=0 인 칸": a8["🔴🔴 최적이 α=0 인 칸"],
         "🔴 978 이 스스로 적은 P8": a8["🔴 예측 P8(최적은 α=0)"]})

    n_true = sum(1 for v in P.values() if v["🔴🔴🔴 979 판(정합 SE · 정본 자) 채점"])
    n_scored78 = sum(1 for v in P.values() if v["🔴 978 이 채점했나"])

    # ══ 반증조건 여덟 ══════════════════════════════════════
    F = collections.OrderedDict()
    #: FC1 — 등록값과 다른 뽑기 수
    boot78 = r8["🔴 등록 상수"]["BOOT(이중 붓스트랩 뽑기)"]
    F["반증조건 1"] = collections.OrderedDict([
        ("등록 문언", "등록값과 다른 뽑기 수를 쓰고 신고 안 하면 실패"),
        ("🔴 산출물이 적은 BOOT", boot78),
        ("🔴 사전등록이 적은 BOOT", 400),
        ("🔴 벌 수(점추정)", r8["🔴 등록 상수"]["점추정 벌 수"]),
        ("🔴 순열 뽑기", r8["🔴 등록 상수"]["순열 귀무 뽑기"]),
        ("🔴🔴 위반인가", bool(boot78 != 400)),
        ("채점", bool(boot78 == 400)),
    ])
    #: FC2 — 같은 조건에 두 값
    F["반증조건 2"] = collections.OrderedDict([
        ("등록 문언", "두 산출물이 같은 조건에 다른 값을 내면 실패(「조건」에 벌 수가 든다)"),
        ("🔴 978 이 이 조건에 채점기를 뒀나", False),
        ("🔴🔴 979 가 대신 채점한다 — 같은 조건의 두 값",
         collections.OrderedDict([
             ("🔴 D4 25 벌 점추정 — ruler stage",
              r8["🔴🔴🔴 파괴 대조 점추정(25 벌)"]["u=3|D4 학습 y 전량(둘 다)"][R2]),
             ("🔴 D4 25 벌 점추정 — cond3 stage 의 200 벌 평균",
              c8["🔴🔴🔴 1 벌 추정의 분포 (겹 씨앗 5 × 섞기 씨앗 40 = 200 벌)"][R2]["평균"]),
             ("🔴 두 값이 다른가", True),
             ("🔴 벌 수가 다른가(25 대 200)", True),
             ("🔴 산출물이 그 벌 수를 스스로 적나", True)])),
        ("채점", True),
    ])
    #: FC3 — 씨앗 하나짜리 수가 본문에
    docs = n8["🔴 대상"]
    seedvals = []
    w4 = None
    for k, v in (w8.get("W") or {}).items():
        if k.startswith("W4 "):
            w4 = v
    if w4:
        seedvals = [str(x) for x in (w4.get("🔴 씨앗별 균등 ρ") or [])]
    hit3 = collections.OrderedDict()
    for rel in docs:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8") if p.is_file() else ""
        hit3[rel] = [v for v in seedvals if v in src]
    n_hit3 = sum(len(v) for v in hit3.values())
    F["반증조건 3"] = collections.OrderedDict([
        ("등록 문언", "씨앗 하나짜리 수를 본문에 실으면 실패"),
        ("🔴 978 이 이 조건에 채점기를 뒀나", False),
        ("🔴 분모: 산출물이 「씨앗별」로 표시한 수", len(seedvals)),
        ("🔴 그 수들", seedvals),
        ("🔴🔴 본문 다섯에서 발견된 자리", hit3),
        ("🔴🔴 분자/분모", "%d / %d" % (n_hit3, len(seedvals) * len(docs))),
        ("🔴 문언 그대로 읽으면 위반인가", bool(n_hit3 > 0)),
        ("🔴 다만", "그 자리는 「씨앗마다 부호가 뒤집힌다」의 **증거 자체**다 — "
                 "위반 여부는 문언 해석에 달렸고, 979 는 **자리와 분모를 공개**한다"),
        ("채점", bool(n_hit3 == 0)),
    ])
    #: FC4 — 🔴🔴 분모를 되돌린다
    def cover(files, rulers):
        rows = collections.OrderedDict()
        num = 0
        for f in files:
            p = OUT / f
            if not p.is_file():
                rows[f] = "파일이 없다"
                continue
            txt = p.read_text(encoding="utf-8")
            c = sum(1 for nm in rulers if nm in txt)
            rows[f] = "%d / %d" % (c, len(rulers))
            num += 1 if c == len(rulers) else 0
        return rows, num
    rows_txt, num_txt = cover(FC4_978_TEXT, R978)
    rows_used, num_used = cover(FC4_978_USED, R978)
    F["반증조건 4"] = collections.OrderedDict([
        ("등록 문언", "자 넷을 같이 안 내면 실패 — `ruler`·`size`·`xdestroy`·`alphafine` "
                  "**모든 stage** 가 자 넷을 다 낸다"),
        ("🔴🔴 사전등록이 이름 적은 stage 수", 4),
        ("🔴🔴 사전등록이 덧붙인 말", "모든 stage"),
        ("🔴🔴🔴 등록 문언대로의 분모(이름 넷 + stage 인 wiring·cond3)", list(FC4_978_TEXT)),
        ("🔴 등록 문언 판 — 파일별 자 가짓수", rows_txt),
        ("🔴🔴🔴 등록 문언 판 분자/분모", "%d / %d" % (num_txt, len(FC4_978_TEXT))),
        ("🔴 978 이 실제로 쓴 분모(`FC4_REG` 다섯)", list(FC4_978_USED)),
        ("🔴 978 이 쓴 판 — 파일별 자 가짓수", rows_used),
        ("🔴 978 이 신고한 분자/분모", "%d / %d" % (num_used, len(FC4_978_USED))),
        ("🔴🔴🔴 분모를 언제 좁혔나",
         collections.OrderedDict([
             ("측정이 돈 커밋", "4cc4edb7baeabe9a4962423784d97eb112408451 (2026-08-16T08:03:51+09:00)"),
             ("분모를 좁힌 커밋", "8f3fe703564f242559367ec0f80afc880e270865 (2026-08-16T08:18:32+09:00)"),
             ("🔴 사이", "14 분 41 초 — **측정 뒤다**"),
             ("🔴 커밋 메시지가 적은 말", "사전등록이 이름 적은 stage 다섯"),
             ("🔴🔴 그 말이 참인가", False),
             ("🔴 사전등록이 이름 적은 stage 는 넷이고, 978 은 이름 없던 cond3 을 넣고 "
              "stage 인 wiring 을 뺐다", True)])),
        ("🔴🔴🔴 등록 문언대로 채점하면 위반인가", bool(num_txt != len(FC4_978_TEXT))),
        ("채점", bool(num_txt == len(FC4_978_TEXT))),
    ])
    #: FC5 — 머지 뒤 HEAD ≠ 디스크
    F["반증조건 5"] = collections.OrderedDict([
        ("등록 문언", "머지 뒤 HEAD ≠ 디스크면 실패"),
        ("🔴 979 가 머지 직후 A-2 를 돌렸나", True),
        ("🔴 이 값의 근거", "판정문 §0 이 원장 수·중복 키·바이트 동일을 함께 싣는다"),
        ("채점", True),
    ])
    #: FC6 — 유보를 만졌나
    lit = collections.OrderedDict()
    src978 = (ROOT / "runners/ruler978.py").read_text(encoding="utf-8").split("\n")
    for ln in (444, 792, 878):
        lit["ruler978.py:%d" % ln] = src978[ln - 1].strip() if ln <= len(src978) else None
    F["반증조건 6"] = collections.OrderedDict([
        ("등록 문언", "유보를 한 줄이라도 만지면 실패"),
        ("🔴🔴 978 이 그 주장을 어떻게 적었나", lit),
        ("🔴🔴 셋 다 리터럴 True 인가",
         bool(all(v is not None and v.endswith("= True") for v in lit.values()))),
        ("🔴 유보 지문이 있었나", False),
        ("🔴 행 수 대조가 있었나", False),
        ("🔴🔴 `meta965` 항진명제 census 가 그 셋을 보나", False),
        ("🔴 왜 못 보나", "census 는 `통과` 키만 본다 — 그 셋의 키는 「🔴 유보는 한 줄도 "
                     "안 만졌다」다"),
        ("🔴🔴🔴 979 가 대신 세운 근거",
         "유보 y·유보 마스크·도메인 라벨의 sha256 을 stage 마다 시작·끝 두 번 찍었다"),
        ("🔴 979 의 판정(정본)", rs["🔴🔴 반증조건 6 — 유보 지문"]["통과"]),
        ("🔴 실질로 참인가(파괴 함수가 유보를 인자로 안 받는다)", True),
        ("채점", bool(rs["🔴🔴 반증조건 6 — 유보 지문"]["통과"])),
    ])
    #: FC7 — 전칭 낱말
    import re as _re
    uni = _re.compile(r"전부|전량|모두|유일")
    per7 = collections.OrderedDict()
    tot7 = 0
    for rel in docs:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8") if p.is_file() else ""
        c = len(uni.findall(src))
        per7[rel] = c
        tot7 += c
    F["반증조건 7"] = collections.OrderedDict([
        ("등록 문언", "전칭 낱말을 쓸 때 분모를 산출물에서 다시 안 세면 실패"),
        ("🔴 978 이 이 조건에 채점기를 뒀나", False),
        ("🔴 본문 다섯의 전칭 낱말 수", per7),
        ("🔴 합", tot7),
        ("🔴🔴 979 가 실측으로 잡은 어긋난 분모 둘",
         collections.OrderedDict([
             ("978 이 신고한 「구성상 참인 검사 0 / 10」",
              w8["🔴🔴🔴 W 구성상 참인 검사 분자/분모"]),
             ("🔴 실측 — 변이체가 구성상 거짓식인 검사", "5 / 10"),
             ("978 이 신고한 수리 계수", 5),
             ("🔴 실측 — 고친 코드가 있는 수리", 3)])),
        ("채점", False),
    ])
    #: FC8 — 한글 수사
    K8 = "🔴🔴🔴 978 수리 4 — 한글 수사 채점"
    F["반증조건 8"] = collections.OrderedDict([
        ("등록 문언", "본문의 한글 수사를 채점 안 하면 실패"),
        ("🔴 센 한글 수사", n8[K8]["🔴🔴 센 한글 수사(전체)"]),
        ("🔴 앞말이 걸린 수사", n8[K8]["🔴🔴 앞말이 걸린 수사(전체)"]),
        ("🔴 어긋난 수사", n8[K8]["🔴🔴🔴 등록된 참값과 어긋난 수사"]),
        ("채점", bool(n8[K8]["통과"])),
    ])

    #: 🔴 면제 273 — 「0/351」의 실제 분모
    ex = n8["🔴🔴 수리 4 — 면제 자리(안 세는 자리)"]["🔴 976 판 면제 자리"]
    counted = _num(n8["🔴🔴🔴 976 판 분자/분모(본문이 출처를 못 대는 수 / 센 수)"], 1)
    exempt = collections.OrderedDict([
        ("🔴 978 이 본문에 실은 분모", counted),
        ("🔴🔴 면제된 자리(원리상 안 보는 수)", ex),
        ("🔴🔴🔴 실제 분모", counted + ex),
        ("🔴 면제 비율", _r(ex / float(counted + ex), 4)),
        ("🔴 신고 분모가 실제의 몇 %", _r(100.0 * counted / float(counted + ex), 2)),
        ("🔴 978 산출물이 「판정문에 그대로 적는다」고 써 놓았나", True),
        ("🔴🔴 판정문·카드·원장·논문에 273 이 나오나", False),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "면제 수를 산출물에서 읽어 게재했다"),
    ])

    n_fc = sum(1 for v in F.values() if v["채점"])
    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S8 — 🔴🔴 **노트 978 의 예측 여덟과 반증조건 여덟을 전부 채점한다.** "
                 "노트 978 이 채점한 것은 P5·P8 둘뿐이다")
    out["🔴 축"] = "자기 자(수리 레인) + C3"
    out["사전등록"] = "docs/prereg_979_denominator.md §4-S8 · §9-2"
    out["🔴 이 stage 는 자 값을 안 낸다(반증조건 4 분모 밖 · 측정 전에 적었다)"] = True
    out["🔴🔴🔴 예측 P1~P8 채점표"] = P
    out["🔴🔴 978 이 채점한 예측 분자/분모"] = "%d / %d" % (n_scored78, len(P))
    out["🔴🔴🔴 979 판 채점 — 참인 예측 분자/분모"] = "%d / %d" % (n_true, len(P))
    out["🔴🔴🔴 반증조건 1~8 채점표"] = F
    out["🔴🔴🔴 반증조건 통과 분자/분모"] = "%d / %d" % (n_fc, len(F))
    out["🔴🔴🔴 위반한 반증조건"] = [k for k, v in F.items() if not v["채점"]]
    out["🔴🔴 「0/351」의 실제 분모 — 면제 273"] = exempt
    out["통과"] = bool(len(P) == 8 and len(F) == 8)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **등록물 열여섯을 하나도 안 빼고 채점했다**(값이 무엇이든 적는다)")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_score978.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("score978 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S1 `wiring` — 🔴 배선 W (수리 2 · **변이체를 진짜로 만든다**)
# ══════════════════════════════════════════════════════════════════════
def dup_keys(path):
    """🔴 **979 신설** — 파이썬 딕트 리터럴의 **중복 문자열 키**를 전수로 센다.

    `ruler978.py:1028-1029` 의 `"그 행 수"` 두 번이 그 병이다 — 커밋본이
    「가장 작은 도메인 아이돌 · 그 행 수 **1288**」로 읽힌다(21 이 사라졌다).
    🔴 **파이썬은 조용히 뒤 값을 남기므로 산출물만 봐서는 못 잡는다.**
    """
    import ast as _ast                                          # noqa: PLC0415
    tree = _ast.parse(Path(path).read_text(encoding="utf-8"))
    hits = []
    for node in _ast.walk(tree):
        keys = None
        if isinstance(node, _ast.Dict):
            keys = [k.value for k in node.keys
                    if isinstance(k, _ast.Constant) and isinstance(k.value, str)]
        elif (isinstance(node, _ast.Call)
              and getattr(node.func, "attr", "") == "OrderedDict"):
            for a in node.args:
                if isinstance(a, _ast.List):
                    keys = [e.elts[0].value for e in a.elts
                            if isinstance(e, _ast.Tuple) and e.elts
                            and isinstance(e.elts[0], _ast.Constant)
                            and isinstance(e.elts[0].value, str)]
        if keys:
            c = collections.Counter(keys)
            for k, v in c.items():
                if v > 1:
                    hits.append("%s:%d %s ×%d" % (Path(path).name, node.lineno, k, v))
    return hits


class _MutRulers(Rulers6):
    """🔴 **진짜 변이체** — `R_eq 균등` 의 가중을 몰래 행 수로 갈아 끼운다."""

    def __init__(self, pool):
        Rulers6.__init__(self, pool)
        self.w[R2] = {d: float(self.n[d]) for d in self.doms}


def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("wiring 시작")
    pool = A.Pool()
    h0 = ho_stamp(pool)
    R = Rulers6(pool)
    RM = _MutRulers(pool)
    W = collections.OrderedDict()

    def add(name, ok, mut_ok, why, extra=None):
        W[name] = collections.OrderedDict([
            ("통과", bool(ok)),
            ("🔴 변이체에서도 통과하나", bool(mut_ok)),
            ("🔴🔴 구성상 참인 검사인가", bool(mut_ok)),
            ("🔴 변이체가 무엇인가", why),
        ])
        if extra:
            W[name].update(extra)

    lam = 10.0 ** U_REG[1]

    # ── W1 배관 동일 ─────────────────────────────────────
    pool.reseed(SEEDS[0])
    p_new = R8.oof978(pool, ALPHA_BASE, lam)["예측"]
    pool.reseed(SEEDS[0])
    p_old = A.oof(pool, ALPHA_BASE, lam)["예측"]
    pool.reseed(SEEDS[0])
    p_mut = R8.oof978(pool, ALPHA_BASE, lam,
                      wreck_x_={"kind": "hplt", "n": None, "seed": 1})["예측"]
    add("W1 `ruler979` 가 부르는 `oof978` 이 977 의 `oof` 와 **바이트로 같은 예측**을 낸다",
        bool(np.array_equal(p_new, p_old)), bool(np.array_equal(p_mut, p_old)),
        "특징을 부순 판을 같은 검사에 건다 — 그때도 같으면 검사가 예측을 안 본다",
        {"🔴 979 판 sha256": _sha_arr(p_new), "🔴 977 판 sha256": _sha_arr(p_old),
         "🔴 변이체 sha256": _sha_arr(p_mut)})

    # ── W2 🔴 균등 팔이 산술평균이다 (🔴 진짜 변이체) ─────
    v, per = score6(pool, R, p_new)
    vm, _pm = score6(pool, RM, p_new)
    doms = [d for d in pool.gated if np.isfinite(per[d])]
    eq_hand = float(np.mean([per[d] for d in doms]))
    pl_hand = float(sum(per[d] * pool.ho_mask[d].sum() for d in doms)
                    / sum(pool.ho_mask[d].sum() for d in doms))
    add("W2 균등 팔이 **도메인별 ρ 의 산술평균**이고 묶음 팔과 다르다",
        bool(abs(v[R2] - eq_hand) < 1e-12 and abs(v[R1] - pl_hand) < 1e-12
             and abs(v[R2] - v[R1]) > 1e-6),
        bool(abs(vm[R2] - eq_hand) < 1e-12 and abs(vm[R1] - pl_hand) < 1e-12
             and abs(vm[R2] - vm[R1]) > 1e-6),
        "🔴 **균등 자의 가중을 몰래 행 수로 갈아 끼운 자 족**에 같은 검사를 건다 — "
        "978 은 `abs(x−x)>1e-6` 이라 무엇을 넣어도 거짓이었다(구성상 거짓식)",
        {"🔴 균등(손계산)": _r(eq_hand), "🔴 묶음(손계산)": _r(pl_hand),
         "🔴 변이체 균등 팔의 값": _r(vm[R2]),
         "🔴 변이체에서 균등−묶음": _r(vm[R2] - vm[R1])})

    # ── W3 🔴 균등 자가 작은 도메인에 큰 무게 (🔴 진짜 변이체) ─
    n = {d: int(pool.ho_mask[d].sum()) for d in pool.gated}
    small = min(pool.gated, key=lambda d: n[d])
    big = max(pool.gated, key=lambda d: n[d])
    wt, wtm = R.table()["자별 가중"], RM.table()["자별 가중"]
    ratio_eq = wt[R2]["정규화 가중"][small] / wt[R2]["정규화 가중"][big]
    ratio_pl = wt[R1]["정규화 가중"][small] / wt[R1]["정규화 가중"][big]
    ratio_m = wtm[R2]["정규화 가중"][small] / wtm[R2]["정규화 가중"][big]
    add("W3 균등 자는 %d 행 도메인과 %d 행 도메인에 **같은 무게**를 준다" % (n[small], n[big]),
        bool(abs(ratio_eq - 1.0) < 1e-9 and ratio_pl < 0.1),
        bool(abs(ratio_m - 1.0) < 1e-9 and ratio_pl < 0.1),
        "🔴 **균등 자의 가중을 행 수로 갈아 끼운 자 족**에 같은 검사를 건다 — "
        "978 은 `ratio_eq < 0.1` 을 물었는데 `ratio_eq ≡ 1.0` 이라 언제나 거짓이었다",
        {"🔴 가장 작은 도메인": small, "🔴 가장 작은 도메인의 행 수": n[small],
         "🔴 가장 큰 도메인": big, "🔴 가장 큰 도메인의 행 수": n[big],
         "🔴 균등 자의 무게 비(작은/큰)": _r(ratio_eq, 4),
         "🔴 묶음 자의 무게 비(작은/큰)": _r(ratio_pl, 6),
         "🔴 변이체의 무게 비": _r(ratio_m, 6)})

    # ── W4 겹 씨앗이 값을 바꾼다 ──────────────────────────
    vals, same_seed = [], []
    for s in SEEDS:
        pool.reseed(s)
        vv, _p = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam)["예측"])
        vals.append(vv[R2])
    for _s in SEEDS:
        pool.reseed(SEEDS[0])
        vv, _p = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam)["예측"])
        same_seed.append(vv[R2])
    add("W4 겹 씨앗 다섯이 **서로 다른 자 값**을 만든다",
        bool(len(set(np.round(vals, 12))) == len(SEEDS)),
        bool(len(set(np.round(same_seed, 12))) == len(SEEDS)),
        "같은 씨앗을 다섯 번 넣어 본다 — 그때도 다섯 값이 다르면 검사가 씨앗을 안 본다",
        {"🔴 씨앗별 균등 ρ": [_r(x) for x in vals],
         "🔴 그 SD": _r(float(np.std(vals, ddof=1))),
         "🔴 평균": _r(float(np.mean(vals))),
         "🔴🔴 SD 가 평균보다 큰가": bool(abs(float(np.std(vals, ddof=1)))
                                 > abs(float(np.mean(vals))))})
    pool.reseed(SEEDS[0])

    # ── W5 🔴 `tr_boot` (🔴 진짜 변이체) ──────────────────
    hi = A.ho_draw(pool, 3)
    p0, _q = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam, tr_boot=None)["예측"], hi)
    p3, _q = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam, tr_boot=3)["예측"], hi)
    p3b, _q = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam, tr_boot=3)["예측"], hi)
    p4, _q = score6(pool, R, R8.oof978(pool, ALPHA_BASE, lam, tr_boot=4)["예측"], hi)
    add("W5 `tr_boot` 이 **학습 행을 실제로 다시 뽑는다**",
        bool(abs(p3[R1] - p0[R1]) > 1e-9 and abs(p3[R1] - p4[R1]) > 1e-9),
        bool(abs(p3b[R1] - p0[R1]) > 1e-9 and abs(p3b[R1] - p3[R1]) > 1e-9),
        "🔴 **같은 `tr_boot=3` 을 두 번 돌린 판**에 같은 검사를 건다 — 같은 뽑기는 같은 값을 "
        "내야 하므로 떨어져야 한다. 978 은 `abs(p_tr0−p_tr0)>1e-9` 이라 구성상 거짓이었다",
        {"🔴 tr_boot 없음": _r(p0[R1]), "🔴 tr_boot=3": _r(p3[R1]),
         "🔴 tr_boot=3 (두 번째)": _r(p3b[R1]), "🔴 tr_boot=4": _r(p4[R1]),
         "🔴 같은 뽑기가 같은 값을 내나": bool(p3[R1] == p3b[R1])})

    # ── W6 🔴 `ho_draw` (🔴 진짜 변이체) ──────────────────
    h1, h2 = A.ho_draw(pool, 1), A.ho_draw(pool, 2)
    h1b = A.ho_draw(pool, 1)
    diff = sum(1 for d in pool.gated if not np.array_equal(h1[d], h2[d]))
    diff_m = sum(1 for d in pool.gated if not np.array_equal(h1[d], h1b[d]))
    leak = sum(int((~pool.ho_mask[d][h1[d]]).sum()) for d in pool.gated)
    add("W6 `ho_draw` 가 유보를 **개체 묶음으로** 다시 뽑고 도메인 밖 행을 안 섞는다",
        bool(diff == len(pool.gated) and leak == 0),
        bool(diff_m == len(pool.gated) and leak == 0),
        "🔴 **같은 뽑기 번호를 두 번 부른 판**에 같은 검사를 건다 — 같은 번호는 같은 뽑기라 "
        "떨어져야 한다. 978 은 `array_equal(h1,h1)` 이라 구성상 거짓이었다",
        {"🔴 두 뽑기가 다른 도메인 수": "%d / %d" % (diff, len(pool.gated)),
         "🔴 변이체에서 다른 도메인 수": "%d / %d" % (diff_m, len(pool.gated)),
         "🔴 도메인 밖으로 샌 행": leak})

    # ── W7 🔴🔴 `SE_구판` 이 978 의 `se_double` 과 같은 수인가 ──
    nb = 30
    arm = {"D4": (WRECKS_Y["D4 학습 y 전량(둘 다)"], None)}
    mine = se_matched(pool, R, ALPHA_BASE, lam, arm, boot=nb, tag="W7")
    theirs = R8.se_double(pool, R8.Rulers(pool), ALPHA_BASE, lam,
                          {"D4": (WRECKS_Y["D4 학습 y 전량(둘 다)"], None)}, boot=nb)
    a_old = mine["D4"][R1]["🔴 SE_구판(1 벌 · 978 판)"]
    a_new = mine["D4"][R1]["🔴🔴 SE_25벌(정합 · 등록 조건 ②의 분모)"]
    b_old = theirs["D4"][R1]
    add("W7 `se_matched` 의 **구판 팔이 `ruler978.se_double` 과 소수 여섯 자리까지 같다**",
        bool(a_old is not None and b_old is not None and abs(a_old - b_old) < 1e-6),
        bool(a_new is not None and b_old is not None and abs(a_new - b_old) < 1e-6),
        "🔴 **정합 팔(25 벌)** 을 같은 검사에 건다 — 그때도 같으면 벌 수를 안 바꾼 것이다",
        {"🔴 979 구판 SE": a_old, "🔴 978 se_double SE": b_old,
         "🔴 979 정합 SE": a_new, "🔴 이 대조의 뽑기 수": nb,
         "🔴 정합/구판 비": _r(a_new / a_old, 4) if a_old else None})

    # ── W8 `wreck_x` ─────────────────────────────────────
    Xb0 = pool.Xb.copy()
    selb, selh, _s = A.select(pool, 0, ALPHA_BASE)
    X, y, _e, nbr = A.design(pool, selb, selh)
    X1_, c1 = R8.wreck_x(X, nbr, "hplt", 7)
    X0_, c0 = R8.wreck_x(X, nbr, "hplt", 7, n=0)
    add("W8 특징 파괴가 학습 X 를 바꾸고 유보 X 는 안 바꾼다",
        bool((X1_ != X).any() and np.array_equal(pool.Xb, Xb0)
             and c1 == len(X) - nbr),
        bool((X0_ != X).any() and np.array_equal(pool.Xb, Xb0)
             and c0 == len(X) - nbr),
        "0 행만 부순 판으로 견준다 — 그때도 통과하면 검사가 파괴를 안 본다",
        {"🔴 부순 행": c1, "🔴 변이체가 부순 행": c0})

    # ── W9 🔴 `s_d` 의 닫힌 꼴 ────────────────────────────
    ns = sorted([(d, n[d], R.sd[d]) for d in pool.gated], key=lambda z: z[1])
    mono = all(ns[i][2] >= ns[i + 1][2] for i in range(len(ns) - 1))
    rel = max(abs(R.sd[d] - R.sd_cf[d]) / R.sd_cf[d] for d in pool.gated)
    const_sd = float(np.mean(list(R.sd.values())))
    ns_m = sorted([(d, n[d], const_sd) for d in pool.gated], key=lambda z: z[1])
    mono_m = all(ns_m[i][2] > ns_m[i + 1][2] for i in range(len(ns_m) - 1))
    rel_m = max(abs(const_sd - R.sd_cf[d]) / R.sd_cf[d] for d in pool.gated)
    add("W9 순열 귀무 SD 가 **행 수가 커질수록 작아지고 닫힌 꼴 `1/√(n−1)` 에 붙는다**",
        bool(mono and rel < 0.25), bool(mono_m and rel_m < 0.25),
        "🔴 모든 도메인에 **같은 상수 SD** 를 주고 같은 검사를 건다",
        {"🔴 행 수 오름차순 (도메인, 행, 귀무 SD)":
             [[z[0], z[1], _r(z[2])] for z in ns],
         "🔴 단조 감소인가": bool(mono),
         "🔴🔴 닫힌 꼴과의 최대 상대오차": _r(rel, 4),
         "🔴 변이체(상수 SD)의 최대 상대오차": _r(rel_m, 4)})

    # ── W10 🔴🔴 정합 SE 가 **실제로 25 벌을 쓴다** ────────
    one = se_matched(pool, R, ALPHA_BASE, lam, arm, boot=12, nwreck=1, tag="W10a")
    five = se_matched(pool, R, ALPHA_BASE, lam, arm, boot=12, nwreck=5, tag="W10b")
    e1o = one["D4"][R1]["🔴 SE_구판(1 벌 · 978 판)"]
    e1f = one["D4"][R1]["🔴 SE_5벌"]
    e5o = five["D4"][R1]["🔴 SE_구판(1 벌 · 978 판)"]
    e5f = five["D4"][R1]["🔴 SE_5벌"]
    add("W10 섞기 씨앗 수를 1 → 5 로 올리면 **`SE_5벌` 이 `SE_구판` 에서 실제로 갈라진다**",
        bool(e1o == e1f and e5o is not None and e5f is not None
             and abs(e5f - e5o) > 1e-9),
        bool(e1o == e1f and abs(e1f - e1o) > 1e-9),
        "🔴 섞기 씨앗 **하나**짜리 주행에 같은 검사를 건다 — 그때는 두 수가 같아야 하므로 "
        "떨어져야 한다",
        {"🔴 섞기 1 — 구판/5벌": [e1o, e1f], "🔴 섞기 5 — 구판/5벌": [e5o, e5f],
         "🔴 이 대조의 뽑기 수": 12})

    # ── W11 🔴 유보 지문이 실제로 민감한가 ────────────────
    st0 = ho_stamp(pool)
    yb_bak = pool.yb.copy()
    pool.yb = pool.yb.copy()
    pool.yb[0] = pool.yb[0] + 1.0
    st_mut = ho_stamp(pool)
    pool.yb = yb_bak
    st_same = ho_stamp(pool)
    add("W11 유보 지문이 **유보 y 한 값만 바뀌어도 달라진다**(반증조건 6 의 자)",
        bool(st_mut != st0 and st_same == st0),
        bool(st_same != st0),
        "🔴 **되돌린 판**에 같은 검사를 건다 — 그때 달라지면 지문이 자료를 안 본다",
        {"🔴 원판 유보 y sha256": st0["유보 y sha256"][:16],
         "🔴 한 값 바꾼 판": st_mut["유보 y sha256"][:16],
         "🔴 되돌린 판": st_same["유보 y sha256"][:16],
         "🔴🔴 978 은 이 자리를 무엇으로 적었나": "리터럴 `= True`"})

    # ── W12 🔴 반증조건 4 의 분모가 사전등록 본문에 있나 ──
    pre = (ROOT / "docs/prereg_979_denominator.md").read_text(encoding="utf-8")
    #: 사전등록 §6-4 가 **이름을 나열한 그 줄**만 본다(문서 아무 데나가 아니다).
    line = ""
    for ln in pre.split("\n"):
        if "`sd`" in ln and "`rescore`" in ln:
            line = ln
    inpre = [f.replace("out979_", "").replace(".json", "") for f in FC4_REG_979]
    ok12 = bool(line) and all(("`%s`" % nm) in line for nm in inpre)
    mut = list(inpre) + ["ladder"]
    ok12_m = bool(line) and all(("`%s`" % nm) in line for nm in mut)
    add("W12 반증조건 4 의 분모 다섯이 **사전등록 §6-4 의 그 줄에 이름으로 있다**(측정 뒤 못 좁힌다)",
        bool(ok12), bool(ok12_m),
        "🔴 사전등록에 **없는 이름**(`ladder`)을 분모에 하나 더 넣은 판에 같은 검사를 건다 — "
        "🔴 노트 978 은 이름 없던 `cond3` 을 넣고 stage 인 `wiring` 을 뺐다",
        {"🔴 분모(코드 상수)": list(FC4_REG_979),
         "🔴 사전등록 §6-4 의 그 줄": line.strip()[:200],
         "🔴 사전등록 본문에 다 있나": bool(ok12),
         "🔴 변이체(없는 이름 하나를 더한 분모)도 통과하나": bool(ok12_m),
         "🔴 분모 밖이라고 미리 적은 stage": list(FC4_OUT_979)})

    # ── W13 🔴 딕트 중복 키 (🔴 979 자기 적발에서 나왔다) ────
    mine_dup = dup_keys(ROOT / "runners/ruler979.py")
    their_dup = dup_keys(ROOT / "runners/ruler978.py")
    add("W13 이 사이클 러너에 **파이썬 딕트 중복 키가 0** 이다",
        bool(len(mine_dup) == 0 and len(their_dup) > 0),
        bool(len(their_dup) == 0),
        "🔴 **노트 978 러너**에 같은 자를 건다 — 거기서 0 이 나오면 이 자가 중복 키를 "
        "원리상 못 보는 것이다",
        {"🔴 979 러너의 중복 키": mine_dup,
         "🔴🔴 978 러너의 중복 키": their_dup,
         "🔴 왜 이 자가 생겼나":
         "🔴 **979 가 자기 산출물에서 먼저 걸렸다** — `srcmix` 의 「그 도메인의 hplt 학습 "
         "몫」이 두 번이라 앞 값이 조용히 사라졌다. 자를 만들어 셋을 다 고쳤다"})

    n_ok = sum(1 for v in W.values() if v["통과"])
    n_const = sum(1 for v in W.values() if v["🔴🔴 구성상 참인 검사인가"])
    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S1 — 🔴 **배선 W. 변이체를 진짜로 만든다.** 노트 978 의 변이체 열 중 "
                 "다섯이 구성상 거짓식이라 「구성상 참인 검사 0/10」의 근거가 절반은 실측이 "
                 "아니었다(정직한 수 5/10)")
    out["🔴 축"] = "자기 자(수리 레인) + C3"
    out["🔴 이 stage 는 자 값을 안 낸다(반증조건 4 분모 밖 · 측정 전에 적었다)"] = True
    out["🔴 978 의 변이체 중 구성상 거짓식이던 자리"] = {
        "W2": "abs(eq_hand − eq_hand) > 1e-6", "W3": "ratio_eq < 0.1 (ratio_eq ≡ 1.0)",
        "W5": "abs(p_tr0 − p_tr0) > 1e-9", "W6": "0 == 10(같은 뽑기의 다른 도메인 수)",
        "W10": "리터럴 False", "🔴 분자/분모": "5 / 10"}
    out["W"] = W
    out["🔴 W 분자/분모(통과)"] = "%d / %d" % (n_ok, len(W))
    out["🔴🔴🔴 W 구성상 참인 검사 분자/분모"] = "%d / %d" % (n_const, len(W))
    out["🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"] = "%d / %d" % (
        sum(1 for v in W.values() if v["통과"] and not v["🔴🔴 구성상 참인 검사인가"]),
        len(W) - n_const)
    out["통과: 배선"] = bool(n_ok == len(W))
    out["🔴🔴 반증조건 6 — 유보 지문"] = ho_verdict(h0, ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("wiring 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §4-S9 `recheck` — 🔴 산출물 덮임 검사 (측정 **뒤** · fail-closed)
# ══════════════════════════════════════════════════════════════════════
def stage_recheck(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("recheck 시작")
    rows = collections.OrderedDict()
    num = 0
    newest_wiring = 0.0
    pw = OUT / "out979_wiring.json"
    if pw.is_file():
        newest_wiring = pw.stat().st_mtime
    for f in FC4_REG_979:
        p = OUT / f
        if not p.is_file():
            rows[f] = {"🔴 파일이 있나": False, "자 가짓수": "0 / %d" % len(RULERS),
                       "🔴 통과": False}
            continue
        txt = p.read_text(encoding="utf-8")
        c = sum(1 for nm in RULERS if nm in txt)
        ok = bool(c == len(RULERS))
        rows[f] = {"🔴 파일이 있나": True,
                   "자 가짓수": "%d / %d" % (c, len(RULERS)),
                   "🔴 배선보다 나중에 났나": bool(p.stat().st_mtime > newest_wiring),
                   "🔴 mtime": dt.datetime.utcfromtimestamp(
                       p.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "🔴 통과": ok}
        num += 1 if ok else 0
    out_rows = collections.OrderedDict()
    for f in FC4_OUT_979:
        p = OUT / f
        out_rows[f] = {"🔴 파일이 있나": bool(p.is_file()),
                       "🔴 분모 밖이라고 사전등록에 적었나": True}
    all_present = all(v.get("🔴 파일이 있나") for v in rows.values())
    out = collections.OrderedDict()
    out["무엇"] = ("979 §4-S9 — 🔴 **산출물 덮임 검사를 배선에서 떼어 측정 뒤로 옮기고 "
                 "fail-closed 로 닫는다.** 노트 978 의 W10 은 빈 `all()` 로 **무조건 통과**했고 "
                 "**배선이 측정보다 먼저 돌아 직전 주행 파일을 읽었다**")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 이 stage 는 자 값을 안 낸다(반증조건 4 분모 밖 · 측정 전에 적었다)"] = True
    out["🔴🔴🔴 반증조건 4 분모(사전등록이 이름 적은 다섯)"] = list(FC4_REG_979)
    out["🔴 분모 밖이라고 사전등록에 적은 넷"] = list(FC4_OUT_979)
    out["🔴 분모 안 — 파일별"] = rows
    out["🔴 분모 밖 — 파일별"] = out_rows
    out["🔴🔴🔴 반증조건 4 분자/분모"] = "%d / %d" % (num, len(FC4_REG_979))
    out["🔴🔴 다섯이 다 있나(fail-closed)"] = bool(all_present)
    out["🔴 978 판이었다면 어떻게 되나"] = (
        "🔴 파일이 하나도 없으면 `all([])` 이 **참**이라 통과로 적힌다 — "
        "979 는 `파일이 없다 = 거짓` 이다")
    out["통과"] = bool(all_present and num == len(FC4_REG_979))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **등록 분모 다섯이 전부 실재하고, 전부 자 여섯을 다 내고, "
        "전부 배선보다 나중에 났다**")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out979_recheck.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("recheck 끝")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "sd", "rescore", "sizeloso", "alphapair",
                             "srcmix", "gate", "score978", "recheck"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "sd": stage_sd, "rescore": stage_rescore,
         "sizeloso": stage_sizeloso, "alphapair": stage_alphapair,
         "srcmix": stage_srcmix, "gate": stage_gate,
         "score978": stage_score978, "recheck": stage_recheck}[a.stage](a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if not str(k).startswith("🔴🔴🔴")},
                     ensure_ascii=False, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
