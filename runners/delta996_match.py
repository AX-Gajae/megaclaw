#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""996 팔 0 — 🔴🔴🔴 **「거리」와 「학습량」을 «잘라서» 가른다.** (선행 · 필수)

사전등록 `docs/prereg_996_information_field.md` §1 · §5 · §6.

🔴🔴 **왜 이 팔이 «맨 앞»인가**(티처 #134):
   `out995_champ.json §C2-다` 의 원점별 학습 행 `[4556, 9116, 13671, 18225]` 과
   원점 지표 `[1,2,3,4]` 의 상관이 **`r = 1.000000`** 이다 --- 증분이 4,560/4,555/4,554 로
   거의 같다. **거리와 학습량은 «완전 공선»이라 관찰만으로는 «원리상» 못 가른다.**
   갈 길은 하나뿐이다: **학습 집합을 «잘라 맞추고» 원점만 옮긴다.**
   그리고 `out994_ctl.json C3`(학습 행만 19,018→4,556) 이 이미 말한다 ---
   **`C0 − C3 = 0.053272`, 곧 낙차 `0.183381` 의 «약 29 %» 는 학습 행 수다.**

🔴 **그래서 `Z_t` 팔(팔 C)의 분모는 `0.183381` 이 «아니라» 이 팔이 내는 «잔여 낙차»다.**
   🔴 **그 나눗셈은 «정비 팔»이 채점에서 한다** --- 측정 팔은 서로 안 읽는다(조항 74-3).

🔴 **무거운 팔**(챔피언 전량 재적합). 사전등록 §7 에 「적합 하나를 «재서» 낸」 값이 있다.

씀:
    OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 \\
      nohup python3 runners/delta996_match.py > /tmp/delta996_match.log 2>&1 & disown
"""
import argparse
import collections
import json
import time

import numpy as np
from scipy.stats import spearmanr

import delta996_common as C
import beta994_common as B94
import gamma995_masks as MK

OUT_DEFAULT = C.ROOT / "runners" / "out996_match.json"
PROG = "/tmp/delta996_match_progress.txt"

# ── 사전등록 상수 ────────────────────────────────────────────────
DRAWS_HEAD = 3                #: 🔴 헤드라인 칸(M2)의 하향 표집 뽑기 수
DRAWS_SENS = 1                #: 🔴 감도 탐침(M3) --- 한 뽑기라 세계 명제에 «안» 쓴다
DRAW_SEED = 9960              #: 하향 표집 씨앗의 밑자리 (뽑기 i → DRAW_SEED + i)
ROW_BOOT_B = 500              #: n* 를 위한 «행» 뽑기 수
ROW_BOOT_SEED = 996
FAM0 = "F0 · 팔 0 --- 조각 3 × 칸 2(M1 기준선 · M2 맞춤) = 6"


def scored(d0, f, ho_blk, doms, blkidx=4, gate=C.GATE_CANON, keep=False):
    hm = {d: ho_blk[d][blkidx] for d in doms}
    sc, dr = MK.score_gate(d0, f, hm, doms, gate, spearmanr)
    if not keep:
        return sc, dr, None
    raw = collections.OrderedDict()
    for d in doms:
        m = np.asarray(hm[d], bool)
        if int(m.sum()) == 0:
            continue
        A_, M_, y_, t_ = d0.slice(d, m)
        p = np.asarray(f.predict(d, A_, M_, t_), float)
        ok = np.isfinite(p) & np.isfinite(y_)
        raw[d] = (p[ok], y_[ok])
    return sc, dr, raw


def cell_run(d0, doms, ho_blk, tmasks, seeds, prog, tag, keep_origin=None):
    """`tmasks` = {칸이름: {도메인: 학습 마스크}}. 칸마다 씨앗을 다 돌고 도메인별 ρ 를 낸다."""
    rho = collections.OrderedDict()
    led = collections.OrderedDict()
    nrow = collections.OrderedDict()
    raws = collections.OrderedDict()
    for name, tm in tmasks.items():
        acc = collections.OrderedDict()
        for si, s in enumerate(seeds):
            t1 = time.time()
            f, lg = B94.fit(d0, tm, s)
            k = (name == keep_origin and si == 0)
            sc, dr, raw = scored(d0, f, ho_blk, doms, 4, C.GATE_CANON, k)
            if si == 0:
                led[name] = lg
                nrow[name] = collections.OrderedDict(
                    [(d, int(v["n"])) for d, v in sorted(sc.items())])
            if k:
                raws[name] = raw
            for d, v in sc.items():
                acc.setdefault(d, []).append(v["rho"])
            prog("%s · %s · 씨앗 %s 끝 (%.1f 초 · 학습 %d 행 / %d 도메인)"
                 % (tag, name, s, time.time() - t1, lg["학습 행 합"], lg["학습 도메인"]))
        rho[name] = collections.OrderedDict(
            [(d, float(np.mean(v))) for d, v in sorted(acc.items())
             if len(v) == len(seeds)])
    return rho, led, nrow, raws


def headline(rho_by, labels, seg_names, family, tag):
    """조각 분해 + 연언 채점 + 부호뒤집기 «전수» 순열 (조항 79 · 티처 #134)."""
    com = sorted(set.intersection(*[set(rho_by[l]) for l in labels]))
    per_by = {l: {d: rho_by[l][d] for d in com} for l in labels}
    rows = C.seg_from(labels, per_by)
    segk = ["%s→%s" % (labels[i], labels[i + 1]) for i in range(len(labels) - 1)]
    npass = int(sum(1 for k in segk if rows[k].get("🔴🔴 2·SE 를 넘나")))
    pdom = {d: [per_by[labels[i + 1]][d] - per_by[labels[i]][d]
                for i in range(len(labels) - 1)] for d in com}
    sf = C.signflip_exact(pdom, segk)
    tot = "%s→%s" % (labels[0], labels[-1])
    ps = [(k, rows[k].get("🔴 양측 p(정규 근사)")) for k in segk]
    return collections.OrderedDict([
        ("🔴 부호 규약", C.SIGN_RULE),
        ("공통 도메인", com), ("공통 도메인 수", len(com)),
        ("조각", rows),
        ("🔴🔴 연언 채점 --- 통과 조각 / 분모 조각", "%d/%d" % (npass, len(segk))),
        ("🔴 통과 조각 분자", npass), ("분모: 조각", len(segk)),
        ("🔴🔴 합(항등 · «통과»로 «안» 센다)", rows[tot].get("점추정")),
        ("🔴 합이 항등인 까닭",
         "조각 셋의 합은 «구성상» 1→4 다(0.074859+0.048355+0.060167=0.183381). "
         "독립 검사가 아니다 --- 조항 78 ㉮ 로 등기했다."),
        ("🔴🔴🔴 부호뒤집기 «전수» 순열", sf),
        ("🔴 해석 SE 대조(순열이 쓰는 SE 가 등록된 뽑기 SE 와 맞나)",
         collections.OrderedDict(
             [(segk[i], C.se_surrogate_check(
                 {d: pdom[d][i] for d in com})) for i in range(len(segk))])),
        ("🔴 Holm", C.holm(ps, C.HOLM_ALPHA, family)),
        ("🔴 몫 --- 참고 분모 %.6f (학습량 몫이 «섞인» 분모다)" % C.GAP995,
         C._r((rows[tot].get("점추정") or 0.0) / C.GAP995, 4)),
        ("🔴🔴 최종 분모는 이 팔의 잔여 낙차이고 그 나눗셈은 «정비 팔»이 한다",
         "측정 팔은 서로 안 읽는다(조항 74-3)"),
        ("무엇", tag)])


def sub_strat(d0, doms, tr_blk, D1, n1, k, seed):
    """🔴🔴 **도메인별 행 수까지 원점 1 과 «글자 그대로» 같게** 하향 표집한다.

    같은 7 도메인 · 같은 도메인별 행 수 · 합 4,556 --- **다른 것은 「행의 시대」뿐이다.**
    """
    rng = np.random.RandomState(int(seed))
    tm, note = {}, collections.OrderedDict()
    for d in doms:
        base = np.zeros(len(np.asarray(d0.yr[d], float)), bool)
        if d not in D1:
            tm[d] = base
            continue
        av = np.where(np.logical_or.reduce([tr_blk[d][b] for b in range(k)]))[0]
        want = int(n1[d])
        if len(av) < want:
            note[d] = "🔴 못 맞췄다 --- 가용 %d < 목표 %d" % (len(av), want)
            base[av] = True
        else:
            base[np.sort(rng.choice(av, want, replace=False))] = True
        tm[d] = base
    return tm, note


def sub_pool(d0, doms, tr_blk, D1, ntot, k, seed):
    """🔴 감도 탐침 --- D1 도메인 «합»에서 균일하게 `ntot` 행. 도메인 «구성»은 안 맞춘다."""
    rng = np.random.RandomState(int(seed))
    pool = []
    for d in doms:
        if d not in D1:
            continue
        av = np.where(np.logical_or.reduce([tr_blk[d][b] for b in range(k)]))[0]
        pool += [(d, int(i)) for i in av]
    pick = rng.choice(len(pool), min(int(ntot), len(pool)), replace=False)
    tm = {d: np.zeros(len(np.asarray(d0.yr[d], float)), bool) for d in doms}
    for i in pick:
        d, j = pool[i]
        tm[d][j] = True
    return tm


def stage(out_path, seeds=C.SEEDS, draws=DRAWS_HEAD, draws_s=DRAWS_SENS):
    t0 = C.now_utc()
    cs0 = C.code_stamp()
    wall = time.time()
    prog = C.prog_writer(PROG)
    prog("팔 0 시작 · 스레드 %s" % json.dumps(C.THREADS))
    out = collections.OrderedDict()
    out["무엇"] = ("996 팔 0 --- 🔴🔴🔴 학습 집합을 «잘라 맞추고» 원점만 옮긴다. "
                 "거리와 학습량은 완전 공선(r=1.000000)이라 관찰로는 못 가른다.")
    out["🔴 축"] = "C1 상태→예측 · C4 자료를 늘리면 나아지나"
    out["사전등록"] = "docs/prereg_996_information_field.md §1 · §5 · §6"
    out["🔴 등록된 자"] = collections.OrderedDict([
        ("군집 SE", "score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중"
         % (C.B_DOM, C.DOM_SEED)),
        ("부호뒤집기", "2^d 전수 · 도메인 통째 · 몬테카를로 아님"),
        ("다중비교", "Holm–Bonferroni · alpha=%.2f · 가족 F0(6)" % C.HOLM_ALPHA)])
    out["🔴 고정한 스레드"] = C.THREADS
    out["🔴 티처 #134 가 준 앞선 실측(참고 상수)"] = collections.OrderedDict([
        ("out994_ctl C3 --- 학습 행만 19,018→4,556", 0.417725),
        ("C0", 0.470997), ("🔴 C0 − C3", C.C0_MINUS_C3),
        ("🔴 낙차 0.183381 에서의 몫(단순 차)", C.LEARN_SHARE),
        ("🔴 그래서 잔여 낙차 예측", C.RESID_EXPECT)])

    d0, doms = B94.load()
    info, tr_blk, ho_blk, edges = MK.blocks_fixed(d0, doms, C.QS, C.NBLOCK)
    out["§M0-가 시간 블록(F01 수리 마스크)"] = info
    prog("자료 적재 · 도메인 %d" % len(doms))

    # ── §M0 🔴 분모 · 공선성 · 게이트 항등 ──────────────────────
    n_by_o = []
    D1, n1 = [], collections.OrderedDict()
    for k in C.ORIGINS:
        tm = MK.train_mask_lt(tr_blk, doms, k)
        tot = 0
        for d in doms:
            n = int(np.asarray(tm[d], bool).sum())
            if n >= 15:
                tot += n
                if k == 1:
                    D1.append(d)
                    n1[d] = n
        n_by_o.append(tot)
    corr = float(np.corrcoef(np.asarray(C.ORIGINS, float),
                             np.asarray(n_by_o, float))[0, 1])
    minsc = collections.OrderedDict()
    for d in doms:
        minsc[d] = int(np.asarray(ho_blk[d][4], bool).sum())
    live = {d: v for d, v in minsc.items() if v > 0}
    out["§M0-나 🔴🔴 분모 --- 그리고 「원리상 못 가른다」의 증거"] = \
        collections.OrderedDict([
            ("원점별 학습 행(MIN_TRAIN 15 뒤)", n_by_o),
            ("995 가 낸 것", list(C.TRAIN_ROWS_995)),
            ("🔴🔴 원점 지표와 학습 행의 상관", C._r(corr, 8)),
            ("🔴 그 상관이 1 에 1e-6 안인가", bool(abs(corr - 1.0) <= 1e-6)),
            ("증분", [n_by_o[i + 1] - n_by_o[i] for i in range(3)]),
            ("🔴 원점 1 의 학습 도메인 D1", D1), ("분모: |D1|", len(D1)),
            ("🔴 원점 1 의 도메인별 학습 행 n1", dict(n1)),
            ("🔴 n1 합", int(sum(n1.values()))),
            ("블록 4 유보 행(도메인별)", dict(minsc)),
            ("🔴🔴 게이트 사다리가 «구성상 항등»인가",
             collections.OrderedDict([
                 ("블록 4 의 «가장 작은» 채점 도메인 행",
                  int(min(live.values())) if live else None),
                 ("게이트 사다리", list(C.GATES)),
                 ("🔴 최대 게이트가 그 최소 행보다 작나(⇒ 게이트가 한 번도 «안» 문다 = ㉮)",
                  bool(live and max(C.GATES) <= min(live.values()))),
                 ("🔴 그래서", "「게이트 20·10·5·3 에서 값 동일」은 튼튼함이 아니라 "
                            "«구성상 항등»이다 --- 티처 #134. ㉮ 로 센다")]))])

    # ── §M1 기준선 (995 ㉡ 재현 · 학습량 «안» 맞춤) ──────────────
    tms = collections.OrderedDict(
        [("원점 %d" % k, MK.train_mask_lt(tr_blk, doms, k)) for k in C.ORIGINS])
    rho1, led1, nrow1, raws = cell_run(d0, doms, ho_blk, tms, seeds, prog,
                                       "M1", keep_origin="원점 4")
    labels = ["원점 %d" % k for k in C.ORIGINS]
    h1 = headline(rho1, labels, None, FAM0 + " (M1)", "M1 기준선 --- 학습량 «안» 맞춤")
    out["§M1 🔴 기준선(995 대비 ㉡ 재현)"] = collections.OrderedDict([
        ("도메인별 ρ(씨앗 평균)",
         {k: {d: C._r(x) for d, x in v.items()} for k, v in rho1.items()}),
        ("학습 장부(씨앗 0)", led1), ("칸별 채점 행(씨앗 0)", nrow1),
        ("헤드라인", h1),
        ("🔴 995 가 낸 조각과의 차",
         collections.OrderedDict(
             [(k, C._r((h1["조각"].get(k) or {}).get("점추정", 0) - v, 9))
              for k, v in C.G995.items()])),
        ("🔴 통과: 반증조건 R1 (995 조각 셋을 1e-6 안에서 재현)",
         bool(all(abs(((h1["조각"].get(k) or {}).get("점추정") or 0) - v) <= 1e-6
                  for k, v in C.G995.items())))])

    # ── §M2 🔴🔴🔴 헤드라인 — 도메인·행 «둘 다» 맞춤 ─────────────
    def matched(mk, nd, tag):
        rho_acc, notes, leds = collections.OrderedDict(), collections.OrderedDict(), \
            collections.OrderedDict()
        rho_acc["원점 1"] = rho1["원점 1"]          # 🔴 구성상 «같은 칸»이다
        for k in (2, 3, 4):
            per = collections.OrderedDict()
            for i in range(nd):
                sd = DRAW_SEED + i
                tm = mk(k, sd)
                if isinstance(tm, tuple):
                    tm, nt = tm
                    if nt:
                        notes["원점 %d · 뽑기 %d" % (k, i)] = nt
                nm = "원점 %d · 뽑기 %d" % (k, i)
                r, lg, _nr, _rw = cell_run(d0, doms, ho_blk,
                                           collections.OrderedDict([(nm, tm)]),
                                           seeds, prog, tag)
                leds[nm] = lg[nm]
                for d, v in r[nm].items():
                    per.setdefault(d, []).append(v)
            rho_acc["원점 %d" % k] = collections.OrderedDict(
                [(d, float(np.mean(v))) for d, v in sorted(per.items())
                 if len(v) == nd])
            rho_acc.setdefault("_뽑기별", collections.OrderedDict())[
                "원점 %d" % k] = {d: [C._r(x) for x in v]
                                for d, v in sorted(per.items())}
        spread = rho_acc.pop("_뽑기별", None)
        return rho_acc, notes, leds, spread

    r2, nt2, led2, sp2 = matched(
        lambda k, sd: sub_strat(d0, doms, tr_blk, D1, n1, k, sd), draws, "M2")
    h2 = headline(r2, labels, None, FAM0 + " (M2)",
                  "M2 🔴 헤드라인 --- 같은 7 도메인 · 도메인별 행까지 원점 1 과 같게")
    out["§M2 🔴🔴🔴 헤드라인 --- 학습을 «잘라 맞췄다»"] = collections.OrderedDict([
        ("🔴 무엇을 맞췄나", "도메인 집합 = D1(7) · 도메인별 학습 행 = n1 · 합 4,556. "
                       "다른 것은 「행의 «시대»」뿐이다."),
        ("뽑기 수", draws), ("뽑기 씨앗", [DRAW_SEED + i for i in range(draws)]),
        ("도메인별 ρ(씨앗 × 뽑기 평균)",
         {k: {d: C._r(x) for d, x in v.items()} for k, v in r2.items()}),
        ("뽑기별 ρ(흩어짐을 보라)", sp2), ("맞추기 실패 신고", nt2),
        ("학습 장부(뽑기별 · 씨앗 0)", led2),
        ("헤드라인", h2),
        ("🔴🔴 잔여 낙차(합)", h2["조각"].get("원점 1→원점 4", {}).get("점추정")),
        ("🔴🔴 기준선 합 대비 몫",
         C._r((h2["조각"].get("원점 1→원점 4", {}).get("점추정") or 0)
              / max(abs(h1["조각"].get("원점 1→원점 4", {}).get("점추정") or 1e-9),
                    1e-9), 4)),
        ("🔴 판정 띠(사전등록 §5 · 티처 #134)", collections.OrderedDict([
            ("≈0.130 이면", "「학습량 몫 29 %」 예측이 맞았다"),
            ("≈0.183 이면", "학습량은 사실상 무관하다"),
            ("<0.05 이면", "🔴 세계 명제가 죽는다")]))])

    # ── §M3 감도 탐침 (도메인 «구성» 은 안 맞춘 하향 표집) ────────
    if draws_s > 0:
        r3, _n3, led3, sp3 = matched(
            lambda k, sd: sub_pool(d0, doms, tr_blk, D1,
                                   int(sum(n1.values())), k, sd), draws_s, "M3")
        h3 = headline(r3, labels, None, FAM0 + " (M3 · 감도)",
                      "M3 감도 --- D1 «합»에서 균일 4,556 행. 도메인 구성은 안 맞춤")
        out["§M3 감도 탐침(한 뽑기 --- 🔴 세계 명제에 «안» 쓴다 · 조항 60)"] = \
            collections.OrderedDict([
                ("뽑기 수", draws_s), ("학습 장부", led3),
                ("도메인별 ρ", {k: {d: C._r(x) for d, x in v.items()}
                            for k, v in r3.items()}),
                ("헤드라인", h3)])

    # ── §M4 🔴 n* 를 «챔피언 세계에서 직접» 잰다 ────────────────
    sig, nd_ = [], []
    rb = collections.OrderedDict()
    rng = np.random.RandomState(ROW_BOOT_SEED)
    for d, (p, y) in (raws.get("원점 4") or {}).items():
        n = len(y)
        if n < 20:
            continue
        bs = np.empty(ROW_BOOT_B)
        for b in range(ROW_BOOT_B):
            ix = rng.randint(0, n, n)
            bs[b] = spearmanr(p[ix], y[ix])[0]
        v = float(np.nanvar(bs, ddof=1))
        rb[d] = collections.OrderedDict([("채점 행", n),
                                         ("행 뽑기 Var(ρ)", C._r(v, 8)),
                                         ("n·Var = σ̂²_d", C._r(n * v, 6))])
        sig.append(n * v)
        nd_.append(n)
    dtot = {d: (rho1["원점 4"][d] - rho1["원점 1"][d])
            for d in set(rho1["원점 4"]) & set(rho1["원점 1"])}
    tau2 = float(np.var(list(dtot.values()), ddof=1)) if len(dtot) > 1 else None
    sig2 = float(np.mean(sig)) if sig else None
    loo = collections.OrderedDict()
    if tau2 and sig2:
        ks = sorted(dtot)
        for d in ks:
            sub = {k: v for k, v in dtot.items() if k != d}
            t2 = float(np.var(list(sub.values()), ddof=1))
            loo["%s 를 뺀 n*" % d] = C._r(sig2 / t2, 3) if t2 else None
    out["§M4 🔴 n* 를 챔피언 세계에서 «직접» 잰다"] = collections.OrderedDict([
        ("🔴 무엇", "σ̂² = 도메인별 (채점 행 × 행뽑기 Var(ρ)) 의 평균 · "
                  "τ̂² = 도메인 사이 Δρ(원점1→4) 의 분산 · n* = σ̂²/τ̂²"),
        ("행 뽑기", collections.OrderedDict([("B", ROW_BOOT_B),
                                          ("씨앗", ROW_BOOT_SEED),
                                          ("씨앗 0 모형 · 원점 4 · 블록 4", True)])),
        ("도메인별", rb), ("σ̂²", C._r(sig2, 6)), ("τ̂²", C._r(tau2, 8)),
        ("🔴 n*(챔피언 세계 · 직접)",
         C._r(sig2 / tau2, 3) if (sig2 and tau2) else None),
        ("🔴 하나 빼기 감도", loo),
        ("🔴🔴 정직한 한계 --- 「법칙」으로 인용하지 마라(티처 #134)",
         "979~995 의 `n* = 44.639` 는 네 점 중 f=0.25 «하나»를 빼면 10.463 이다(4.3 배). "
         "검증 다섯 자리는 「문턱이 [18, 51] 안」만 말한다. 적합 구간(n̄ 61.85~235.9)과 "
         "적용 구간(4~51)이 «어긋난다». 이 칸은 «서술»이지 법칙이 아니다."),
        ("alpha977 세계의 옛 값(참고)", 44.639)])

    # ── §M5 🔴🔴🔴 조항 78 — 기계로 센 ㉮·㉯ ───────────────────
    base = {}
    for i, k in enumerate(["원점 1→원점 2", "원점 2→원점 3", "원점 3→원점 4"]):
        base[k] = {d: (rho1[labels[i + 1]][d] - rho1[labels[i]][d])
                   for d in set(rho1[labels[i]]) & set(rho1[labels[i + 1]])}
    variants = C.variant_grid(base, 996)
    claims = [("%s 가 2·SE 를 넘는다" % k,
               (lambda kk: lambda st: bool(C.cluster_se(st[kk])
                                           .get("🔴🔴 2·SE 를 넘나")))(k))
              for k in base]
    claims.append(("조각 셋이 «전부» 2·SE 를 넘는다(연언)",
                   lambda st: all(bool(C.cluster_se(st[k])
                                       .get("🔴🔴 2·SE 를 넘나")) for k in st)))
    #: 🔴 대조판은 **자료에서 계산한 «진짜» ㉮·㉯** 다 --- 리터럴이 아니다(티처 #134)
    controls = [
        ("🔴 대조 ㉮(자료 파생 · 참 ㉮): 조각의 도메인 수가 12 이하다",
         lambda st: all(len(v) <= 12 for v in st.values())),
        ("🔴 대조 ㉯(자료 파생 · 참 ㉯): 조각의 도메인 수가 13 이상이다",
         lambda st: any(len(v) >= 13 for v in st.values())),
    ]
    out["§M5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"] = C.taut_scan(
        claims, variants, "팔 0 의 주장 %d 개 × 변이체 %d 개"
        % (len(claims), len(variants)), controls)

    out["🔴🔴 조항 79 개정 2 --- 이 주행이 낸 cluster_se 칸 전량"] = C.cse_ledger()
    out["🔴🔴 조항 78 개정 4 --- 반증조건의 «분모»를 손으로 고르지 않았다"] = \
        collections.OrderedDict([
            ("🔴 왜", "995 팔 C 는 반증조건 여덟 중 넷만 검사하고 「㉮ 0/4」를 냈다 --- "
                    "뺀 넷 중 셋이 ㉮ 였다(티처 #134). 그래서 분모를 «이름으로» 신고한다."),
            ("분모: 이 팔이 지는 반증조건", 9),
            ("이름", ['F1 995 조각 재현', 'F2 M2 도메인별 학습 행 = n1', 'F3 채점 집합 동일', 'F4 corr(원점,학습행)≈1 (㉮-4)', 'F5 게이트 항등 (㉮-1)', 'F10 해석 SE 대조', 'F11 BLAS 거짓 경보 대조', 'F12 조항 78 대조 계수', 'F13 도장 시작=끝']),
            ("🔴 산출물 키로 «기계가» 확인하는 것", ['F1', 'F2', 'F3', 'F4', 'F5', 'F10', 'F11', 'F12', 'F13'])])
    out["🔴 도장"] = C.stamp(t0, cs0, collections.OrderedDict([
        ("걸린 초", round(time.time() - wall, 3)),
        ("🔴 자료 지문", B94.data_fp(d0, doms))]))
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    prog("끝 (%.1f 분)" % ((time.time() - wall) / 60.0))
    print("wrote %s (%.1f min)" % (out_path, (time.time() - wall) / 60.0), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--seeds", type=int, default=len(C.SEEDS))
    ap.add_argument("--draws", type=int, default=DRAWS_HEAD)
    ap.add_argument("--draws-sens", type=int, default=DRAWS_SENS)
    a = ap.parse_args()
    stage(a.out, C.SEEDS[:a.seeds], a.draws, a.draws_sens)


if __name__ == "__main__":
    main()
