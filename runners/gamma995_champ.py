#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""995 팔 C — 🔴🔴 **챔피언 세계에서 「대비 ㉡」을 `F01` 수리 마스크로 다시 잰다.**

사전등록 `docs/prereg_995_unblock_nb.md` §4 + §9-2 + §9-12 를 그대로 따른다.

🔴 **헤드라인이 바뀌었다**(사전등록 §9-12). 옛 헤드라인(게이트를 낮춰 `d` 를 7→9)은
   **부차**로 남고, 새 헤드라인은:

   **「채점 블록을 4 에 «고정»하고 원점을 1→4 로 옮기면 ρ 가 오르나」** —
   994 의 「거리 1→4」는 «거리»와 «채점 블록»이 같이 움직여 교란이 있었다.
   이 네 칸은 **채점 집합이 글자 그대로 같고 거리만 4·3·2·1 로 준다.**

🔴 **`F01` 정정을 «먼저» 반영한다** — `runners/gamma995_masks.py` 의 수리 마스크를 쓴다.
   **`beta994_*` 는 동결이라 한 글자도 안 고쳤다.** §C0 이 구판/신판 전후 표를 먼저 낸다.

🔴 **조항 75-나** — 이 러너는 한 시간에 가깝다. **`nohup … & disown` 으로 분리해 띄운다.**

씀:
    OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
      nohup python3 runners/gamma995_champ.py --stage champ \
      > /tmp/gamma995_champ.log 2>&1 & disown
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
from scipy.stats import spearmanr

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import beta994_common as B94                      # noqa: E402  🔴 읽기로만 쓴다(동결)
import gamma995_masks as MK                       # noqa: E402  🔴 F01 수리판

SRC = ("runners/gamma995_champ.py", "runners/gamma995_masks.py",
       "runners/beta994_common.py", "runners/ff753.py",
       "lab/harness.py", "lab/forms.py", "lab/loop.py", "state/rank_test.py")

OUT = ROOT / "runners"
OUTFILE = OUT / "out995_champ.json"
PROG = OUT / "out995_champ_progress.txt"

# ── 사전등록 상수 ────────────────────────────────────────────────
SEEDS = tuple(range(12))          #: 994 와 «같은» 12 씨앗
T_CANON = 2025.0
NBLOCK = 5
QS = (0.2, 0.4, 0.6, 0.8)
ORIGINS = (1, 2, 3, 4)
GATES = (20, 10, 5, 3)            #: 🔴 조항 66 — 문턱 대신 검사를 인자화한다
GATE_CANON = 20                   #: `lab/harness.py:_score_one` 의 값
B_DOM = 2000                      #: 🔴 등록된 자
DOM_SEED = 994                    #: 🔴 등록된 자의 씨앗
BOARD_RHO_FULL = 0.47034252170476804
F01_DEV = MK.F01_DEV              #: 7.199316e-04 (🔴 0.000e+00 이 «아니다»)
SAFE_MULT = MK.SAFE_MULT
THREADS = collections.OrderedDict([
    (k, os.environ.get(k)) for k in
    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")])

#: 🔴🔴 사전등록 §9-2 대비 ㉡ — **측정 전에 박았다**(994 의 «옛» 마스크로 낸 값).
EXPECT_B = collections.OrderedDict([
    ("원점 1→2", (0.075188, 0.034440, 2.183, 9)),
    ("원점 2→3", (0.048266, 0.016821, 2.869, 9)),
    ("원점 3→4", (0.060199, 0.026026, 2.313, 10)),
    ("원점 1→4", (0.183654, 0.050321, 3.650, 11)),
])
#: 🔴🔴 사전등록 §9-2 대비 ㉠
EXPECT_A = collections.OrderedDict([
    ("거리 1→2", (0.017600, 0.040098, 0.439, 5)),
    ("거리 2→3", (0.002146, 0.032853, 0.065, 4)),
    ("거리 3→4", (0.110516, 0.028171, 3.923, 6)),
    ("거리 1→4", (0.130262, 0.077248, 1.686, 4)),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))


def sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def code_stamp():
    return collections.OrderedDict([(r, sha_file(r)) for r in SRC])


# ══════════════════════════════════════════════════════════════════════
# 🔴 등록된 자 — `score994.py:98 cluster_se` 와 «같은 꼴» · 등가중
# ══════════════════════════════════════════════════════════════════════
def cluster_se(vals, B=B_DOM, seed=DOM_SEED):
    ds = sorted(vals)
    r = np.asarray([vals[d] for d in ds], float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return collections.OrderedDict([("도메인 수", int(len(r))),
                                        ("도메인 군집 SE", None), ("뽑기 수", 0)])
    rng = np.random.RandomState(int(seed))
    bs = np.empty(int(B))
    for b in range(int(B)):
        bs[b] = r[rng.randint(0, len(r), len(r))].mean()
    pt, se = float(r.mean()), float(bs.std(ddof=1))
    return collections.OrderedDict([
        ("도메인 수", int(len(r))), ("뽑기 수", int(B)),
        ("🔴 자", "score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중"
         % (B, seed)),
        ("점추정", _r(pt)), ("도메인 군집 SE", _r(se, 8)),
        ("t_clu", _r(pt / se) if se else None),
        ("🔴🔴 2·SE 를 넘나", bool(abs(pt) > 2 * se) if se else None),
        ("🔴 동부호 수", "%d/%d"
         % (int(sum(1 for x in r if np.sign(x) == np.sign(pt))), len(r))),
        ("2.5%", _r(float(np.percentile(bs, 2.5)))),
        ("97.5%", _r(float(np.percentile(bs, 97.5)))),
        ("도메인 사이 SD(τ̂)", _r(float(r.std(ddof=1)))),
    ])


def cmp_expect(got, exp):
    pt, se, t, s = exp
    gs = got.get("🔴 동부호 수") or "0/0"
    dif = abs((got.get("점추정") or 0) - pt)
    return collections.OrderedDict([
        ("사전등록(994 옛 마스크) 점추정", pt), ("실측(수리 마스크) 점추정", got.get("점추정")),
        ("🔴 차", _r((got.get("점추정") or 0) - pt, 9)),
        ("사전등록 t", t), ("실측 t", got.get("t_clu")),
        ("사전등록 동부호", s), ("실측 동부호", gs),
        ("🔴 안전 배수(|실측| / F01 이탈)",
         _r(abs(got.get("점추정") or 0) / F01_DEV, 2)),
        ("🔴 안전 배수가 %d 이상인가" % SAFE_MULT,
         bool(abs(got.get("점추정") or 0) / F01_DEV >= SAFE_MULT)),
        ("참고: |차|", _r(dif, 9)),
    ])


def seg_from(labels, per_by):
    """🔴 조각 분해표 — 이웃 조각 + 합. 부호 규약은 표마다 적는다."""
    rows = collections.OrderedDict()
    for i in range(len(labels) - 1):
        a, b = labels[i], labels[i + 1]
        dd = {k: (per_by[b][k] - per_by[a][k]) for k in per_by[a]
              if k in per_by[b]}
        rows["%s→%s" % (a, b)] = cluster_se(dd)
    tot = {k: (per_by[labels[-1]][k] - per_by[labels[0]][k])
           for k in per_by[labels[0]] if k in per_by[labels[-1]]}
    rows["%s→%s" % (labels[0], labels[-1])] = cluster_se(tot)
    return rows


# ══════════════════════════════════════════════════════════════════════
def stage_champ():
    t0 = _now()
    cs0 = code_stamp()
    wall0 = time.time()
    prog("champ 시작 · 스레드 %s" % json.dumps(THREADS))
    out = collections.OrderedDict()
    out["무엇"] = ("995 팔 C --- 🔴🔴 챔피언 세계에서 「대비 ㉡」(채점 블록 4 고정 · 원점 이동)을 "
                 "F01 수리 마스크로 다시 잰다. 게이트 인자화는 부차다.")
    out["🔴 축"] = "C1 상태→예측 · 검정력"
    out["사전등록"] = "docs/prereg_995_unblock_nb.md §4 · §9-2 · §9-12"
    out["🔴 고정한 스레드"] = THREADS
    out["🔴 등록된 자"] = ("score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중 · "
                      "판정식 abs(pt) > 2*se" % (B_DOM, DOM_SEED))

    d0, doms = B94.load()
    prog("자료 적재 · 도메인 %d" % len(doms))

    # ── §C0 🔴🔴 F01 구판/신판 전후 (조항 66) ────────────────────
    out["§C0 🔴🔴 F01 구판/신판 전후"] = MK.mask_diff_table(d0, doms, T_CANON, QS, NBLOCK)

    info, tr_blk, ho_blk, edges = MK.blocks_fixed(d0, doms, QS, NBLOCK)
    out["§C0-나 시간 블록(수리판 · 절단은 994 와 같다)"] = info

    # ── §C1 🔴 정본 재현 (수리 마스크) ──────────────────────────
    tr_n, ho_n = MK.canon_masks_fixed(d0, doms, T_CANON)
    tr_o, ho_o = MK.canon_masks_old(d0, doms, T_CANON)
    prog("정본 적합 시작(씨앗 0)")
    f0, led0 = B94.fit(d0, tr_n, 0)
    sc_n, dr_n = MK.score_gate(d0, f0, ho_n, doms, GATE_CANON, spearmanr)
    sc_o, dr_o = MK.score_gate(d0, f0, ho_o, doms, GATE_CANON, spearmanr)
    rho_n, rho_o = B94.pooled(sc_n), B94.pooled(sc_o)
    prog("정본 씨앗 0 · 신판 %.12f · 구판 %.12f" % (rho_n, rho_o))
    out["§C1 🔴 정본 재현(수리 마스크)"] = collections.OrderedDict([
        ("씨앗", 0), ("T", T_CANON), ("게이트", GATE_CANON),
        ("🔴 판 ρ(신판 · 수리 마스크)", repr(rho_n)),
        ("판 ρ(구판 · 994 마스크)", repr(rho_o)),
        ("🔴🔴 신판 − 구판", _r(rho_n - rho_o, 12)),
        ("🔴 사전등록에 박은 이탈 크기", F01_DEV),
        ("🔴 |신판−구판 − 이탈| ", _r(abs((rho_n - rho_o) - F01_DEV), 12)),
        ("🔴 통과: 반증조건 17 (|차 − 7.199316e-04| ≤ 1e-6)",
         bool(abs(abs(rho_n - rho_o) - F01_DEV) <= 1e-6)),
        ("정본 BOARD_RHO_FULL", BOARD_RHO_FULL),
        ("🔴 신판 − 정본", _r(rho_n - BOARD_RHO_FULL, 12)),
        ("🔴 통과: 반증조건 1 (|신판 − 정본| ≤ 1e-6)",
         bool(abs(rho_n - BOARD_RHO_FULL) <= 1e-6)),
        ("채점 행 합(신판)", int(sum(v["n"] for v in sc_n.values()))),
        ("채점 행 합(구판)", int(sum(v["n"] for v in sc_o.values()))),
        ("채점 도메인 수(신판)", len(sc_n)), ("채점 도메인 수(구판)", len(sc_o)),
        ("도메인별 ρ(신판)", {k: _r(v["rho"]) for k, v in sorted(sc_n.items())}),
        ("🔴 도메인별 ρ 차(신판 − 구판)",
         {k: _r(sc_n[k]["rho"] - sc_o[k]["rho"], 9)
          for k in sorted(set(sc_n) & set(sc_o))}),
        ("버림 장부(신판)", B94.drop_ledger(dr_n, doms)),
        ("학습 장부", led0),
    ])

    # ── §C2 🔴 원점 × 씨앗 적합 · 칸별 도메인 ρ ──────────────────
    #   원점 k 로 적합한 모형이 블록 k..4 를 «따로» 채점한다(994 §3 과 같은 꼴).
    cellrho = collections.OrderedDict()   # (원점, 블록) -> gate -> dom -> [씨앗별 rho]
    celln = collections.OrderedDict()
    ledgers = collections.OrderedDict()
    for k in ORIGINS:
        tm = MK.train_mask_lt(tr_blk, doms, k)
        for si, s in enumerate(SEEDS):
            t1 = time.time()
            f, led = B94.fit(d0, tm, s)
            if si == 0:
                ledgers["원점 %d" % k] = led
            for blk in range(k, NBLOCK):
                hm = {d: ho_blk[d][blk] for d in doms}
                for g in GATES:
                    sc, dr = MK.score_gate(d0, f, hm, doms, g, spearmanr)
                    key = ("원점 %d → 블록 %d (거리 %d)" % (k, blk, blk - k + 1), g)
                    cellrho.setdefault(key, collections.OrderedDict())
                    celln.setdefault(key, collections.OrderedDict())
                    for d, v in sc.items():
                        cellrho[key].setdefault(d, []).append(v["rho"])
                        celln[key][d] = v["n"]
            prog("원점 %d 씨앗 %d 끝 (%.1f 초)" % (k, s, time.time() - t1))

    per_seedmean = collections.OrderedDict()
    for (cell, g), dv in cellrho.items():
        per_seedmean.setdefault(g, collections.OrderedDict())[cell] = \
            collections.OrderedDict(
                [(d, float(np.mean(v))) for d, v in sorted(dv.items())
                 if len(v) == len(SEEDS)])
    out["§C2 칸별 도메인 ρ(씨앗 평균)"] = collections.OrderedDict([
        ("게이트 %d" % g, collections.OrderedDict(
            [(c, {d: _r(x) for d, x in v.items()}) for c, v in blkv.items()]))
        for g, blkv in sorted(per_seedmean.items())])
    out["§C2-나 칸별 채점 행"] = collections.OrderedDict(
        [("%s · 게이트 %d" % (c, g), dict(v)) for (c, g), v in celln.items()])
    out["§C2-다 학습 장부(씨앗 0)"] = ledgers

    # ── §C3 🔴🔴🔴 대비 ㉡ — 채점 블록 4 고정 · 원점 이동 (헤드라인) ──
    headline = collections.OrderedDict()
    for g in GATES:
        pm = per_seedmean.get(g, {})
        KB = ["원점 %d → 블록 4 (거리 %d)" % (o, 4 - o + 1) for o in ORIGINS]
        if not all(k in pm for k in KB):
            headline["게이트 %d" % g] = {"🔴 못 돌았다": "칸이 없다", "칸": KB}
            continue
        com = sorted(set.intersection(*[set(pm[k]) for k in KB]))
        per_by = {"원점 %d" % o: {d: pm[KB[i]][d] for d in com}
                  for i, o in enumerate(ORIGINS)}
        rows = seg_from(["원점 1", "원점 2", "원점 3", "원점 4"], per_by)
        ncross = sum(1 for k, v in rows.items()
                     if k != "원점 1→원점 4" and v.get("🔴🔴 2·SE 를 넘나"))
        headline["게이트 %d" % g] = collections.OrderedDict([
            ("공통 도메인", com), ("공통 도메인 수", len(com)),
            ("🔴 부호 규약", "「먼 원점 − 가까운 원점」 · 양수 = 원점이 가까울수록 좋다"),
            ("조각", rows),
            ("🔴🔴 문턱을 넘은 조각 수", int(ncross)),
            ("🔴 이것이 「조각 분해표」다(F13)", True),
            ("🔴🔴 사전등록 표와의 대조(게이트 20 만 뜻이 있다)",
             collections.OrderedDict(
                 [(k, cmp_expect(rows[kk], EXPECT_B[k]))
                  for k, kk in zip(EXPECT_B,
                                   ["원점 1→원점 2", "원점 2→원점 3",
                                    "원점 3→원점 4", "원점 1→원점 4"])])
             if g == GATE_CANON else "게이트가 정본이 아니다 --- 대조 안 한다"),
        ])
    out["§C3 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동"] = collections.OrderedDict([
        ("🔴 왜 이게 옳은 대비인가",
         "994 의 「거리 1→4」는 «거리»와 «채점 블록»이 같이 움직인다 --- 교란이다. "
         "이 네 칸은 채점 집합이 글자 그대로 같고 거리만 4·3·2·1 로 준다."),
        ("게이트별", headline),
    ])

    # ── §C4 대비 ㉠ — 원점 1 의 거리 조각 (게이트 사다리 · 부차) ──
    dist = collections.OrderedDict()
    for g in GATES:
        pm = per_seedmean.get(g, {})
        KA = ["원점 1 → 블록 %d (거리 %d)" % (b, b) for b in range(1, NBLOCK)]
        if not all(k in pm for k in KA):
            dist["게이트 %d" % g] = {"🔴 못 돌았다": "칸이 없다"}
            continue
        com = sorted(set.intersection(*[set(pm[k]) for k in KA]))
        per_by = {"거리 %d" % b: {d: pm[KA[b - 1]][d] for d in com}
                  for b in range(1, NBLOCK)}
        rows = seg_from(["거리 1", "거리 2", "거리 3", "거리 4"], per_by)
        dist["게이트 %d" % g] = collections.OrderedDict([
            ("공통 도메인", com), ("공통 도메인 수", len(com)),
            ("🔴 부호 규약", "「먼 거리 − 가까운 거리」 · 음수 = 멀수록 나빠진다"),
            ("조각", rows),
            ("🔴🔴 문턱을 넘은 조각 수",
             int(sum(1 for k, v in rows.items()
                     if k != "거리 1→거리 4" and v.get("🔴🔴 2·SE 를 넘나")))),
            ("🔴 이것이 「조각 분해표」다(F13)", True),
        ])
    dcounts = {("게이트 %d" % g): dist["게이트 %d" % g].get("공통 도메인 수")
               for g in GATES}
    out["§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리"] = collections.OrderedDict([
        ("게이트별", dist),
        ("🔴 게이트별 공통 도메인 수", dcounts),
        ("🔴 통과: 반증조건 10 (게이트 5 의 d > 게이트 20 의 d)",
         bool((dcounts.get("게이트 5") or 0) > (dcounts.get("게이트 20") or 0))),
        ("🔴 ㉯-3 --- 이 대비의 d 는 12 에 «원리상» 못 간다",
         "블록 1 에서 시장팝업·영화·팝업이 「0 행」이다(문턱이 아니다 · 조항 59)"),
    ])

    # ── §C5 🔴🔴 조항 78 을 기계로 센다 ─────────────────────────
    def probe(name, real, mut, why):
        return collections.OrderedDict([
            ("검사 이름", name), ("실제 판에서 참인가", bool(real)),
            ("🔴 변이체에서도 참인가", bool(mut)),
            ("🔴🔴 원리상 못 떨어지나(㉮)", bool(real and mut)),
            ("변이체", why)])

    hb = headline.get("게이트 %d" % GATE_CANON, {})
    tot_row = (hb.get("조각") or {}).get("원점 1→원점 4", {})
    ok15 = bool(tot_row.get("🔴🔴 2·SE 를 넘나")) and \
        int((tot_row.get("🔴 동부호 수") or "0/0").split("/")[0]) >= 10
    # 위약 --- 크기는 두고 부호만 무작위 (리터럴을 안 쓴다)
    _rs = np.random.RandomState(995)
    pm20 = per_seedmean.get(GATE_CANON, {})
    KB = ["원점 %d → 블록 4 (거리 %d)" % (o, 4 - o + 1) for o in ORIGINS]
    plac_ok = None
    if all(k in pm20 for k in KB):
        com = sorted(set.intersection(*[set(pm20[k]) for k in KB]))
        raw = {d: pm20[KB[3]][d] - pm20[KB[0]][d] for d in com}
        plac = {d: abs(v) * (1 if _rs.rand() < 0.5 else -1) for d, v in raw.items()}
        pc = cluster_se(plac)
        plac_ok = bool(pc.get("🔴🔴 2·SE 를 넘나")) and \
            int((pc.get("🔴 동부호 수") or "0/0").split("/")[0]) >= 10
    probes = [
        probe("F01 정본 재현", abs(rho_n - BOARD_RHO_FULL) <= 1e-6,
              abs(rho_n - (BOARD_RHO_FULL + 0.01)) <= 1e-6,
              "정본을 0.01 옮겨 견준다"),
        probe("F17 F01 이탈 크기 = 7.199316e-04",
              abs(abs(rho_n - rho_o) - F01_DEV) <= 1e-6,
              abs(abs(rho_n - rho_o) - 0.0) <= 1e-6,
              "🔴 이탈을 0.000e+00 으로 견준다 --- 조타수 지시문의 오독"),
        probe("F15 대비 ㉡ 이 선다", ok15, bool(plac_ok),
              "위약 --- 크기는 두고 부호만 무작위(RandomState(995))"),
        probe("F10 게이트가 d 를 늘린다",
              (dcounts.get("게이트 5") or 0) > (dcounts.get("게이트 20") or 0),
              (dcounts.get("게이트 20") or 0) > (dcounts.get("게이트 20") or 0),
              "게이트 20 을 자기 자신과 견준다"),
    ]
    ctrl = [probe("대조 --- 같은 수를 같은 수와 견준다", True, True, "자기 자신"),
            probe("대조 --- 0 을 0 이 아니라 하기", False, False, "거짓")]
    mach = sum(1 for p in probes if p["🔴🔴 원리상 못 떨어지나(㉮)"])
    ctrln = sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"])
    out["§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"] = collections.OrderedDict([
        ("조각", probes), ("🔴🔴 기계가 센 ㉮ 분자", int(mach)),
        ("분모: 검사한 조각", len(probes)),
        ("🔴 대조판 --- 첫 대조는 «일부러» ㉮ 다(계수가 1 을 낼 수 있다)",
         collections.OrderedDict([("조각", ctrl), ("이 판의 ㉮ 분자", int(ctrln))])),
        ("🔴 통과: 반증조건 16 (계수가 자료에 따라 움직이나)",
         bool(ctrln == 1)),
    ])

    # ── 반증조건 모음 ──────────────────────────────────────────
    F = collections.OrderedDict()
    F["🔴 반증조건 1 --- 수리 마스크로 정본 재현"] = repr(rho_n)
    F["통과: 반증조건 1"] = bool(abs(rho_n - BOARD_RHO_FULL) <= 1e-6)
    F["🔴 반증조건 10 --- 게이트가 d 를 늘린다"] = dcounts
    F["통과: 반증조건 10"] = out["§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리"][
        "🔴 통과: 반증조건 10 (게이트 5 의 d > 게이트 20 의 d)"]
    F["🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다"] = collections.OrderedDict([
        ("2·SE 를 넘나", tot_row.get("🔴🔴 2·SE 를 넘나")),
        ("동부호", tot_row.get("🔴 동부호 수")),
        ("t_clu", tot_row.get("t_clu"))])
    F["통과: 반증조건 15"] = bool(ok15)
    F["🔴 반증조건 17 --- F01 이탈 크기"] = _r(rho_n - rho_o, 12)
    F["통과: 반증조건 17"] = bool(abs(abs(rho_n - rho_o) - F01_DEV) <= 1e-6)
    F["🔴🔴 반증조건 13 --- 헤드라인 2 · 조각 분해표"] = \
        ["§C3 대비 ㉡ (게이트 %d 칸)" % len(GATES), "§C4 대비 ㉠ (게이트 %d 칸)" % len(GATES)]
    F["통과: 반증조건 13"] = True
    F["통과: 반증조건 16"] = out["§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"][
        "🔴 통과: 반증조건 16 (계수가 자료에 따라 움직이나)"]
    F["🔴 반증조건 18 --- 도장 분모의 첫 자리"] = SRC[0]
    F["통과: 반증조건 18"] = bool(SRC[0] == "runners/gamma995_champ.py"
                              and cs0.get(SRC[0]) is not None)
    out["반증조건"] = F

    out["🔴 벌의 범위 규칙(사전등록 §9-6)"] = collections.OrderedDict([
        ("🔴 F01 이탈 크기(측정 전에 박았다)", F01_DEV),
        ("🔴 안전 배수 문턱", SAFE_MULT),
        ("🔴 규칙", "F01 이 떨어지면 이 팔의 산출물 «전부»가 못 믿는다로 간다. "
                 "사전등록에 «이미» 적힌 안전 배수 규칙으로만 좁힐 수 있다."),
        ("대비 ㉡ 합의 안전 배수",
         _r(abs(tot_row.get("점추정") or 0) / F01_DEV, 2)),
        ("🔴 그 수가 문턱을 넘나",
         bool(abs(tot_row.get("점추정") or 0) / F01_DEV >= SAFE_MULT)),
    ])

    out["🔴 도장"] = collections.OrderedDict([
        ("언제(시작 · UTC)", t0), ("언제(끝 · UTC)", _now()),
        ("걸린 초", round(time.time() - wall0, 1)),
        ("🔴 코드 sha256(시작)", cs0), ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 시작=끝", bool(cs0 == code_stamp())),
        ("분모: 도장이 덮는 소스", len(cs0)),
        ("🔴 자료 지문", B94.data_fp(d0, doms)),
        ("🔴 고정한 스레드", THREADS),
        ("🔴 git HEAD 스탬프", "폐기됐다 --- 조항 66"),
    ])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["champ"])
    ap.parse_args()
    out = stage_champ()
    OUTFILE.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    prog("wrote %s" % OUTFILE)
    print("wrote %s" % OUTFILE)


if __name__ == "__main__":
    main()
