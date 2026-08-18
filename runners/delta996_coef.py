#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""996 팔 A — 🔴🔴🔴 **「축 다섯의 계수가 시대에 따라 «도는가» · 어느 축이」.**

사전등록 `docs/prereg_996_information_field.md` §2 · §5 · §6 을 그대로 따른다.

🔴 **왜 이 물음인가**(사전등록 §0-라): 판 ρ 는 스피어만이라 «블록 안 순위»만 본다.
   `Z_t` 의 «주효과»는 원리상 ρ 를 못 바꾼다 — 정보장이 모두를 똑같이 밀면 순위가 그대로다.
   **오직 `Z_t × A_i` 상호작용만 순위를 뒤집는다.** 곧 물음은
   **「축의 계수가 시대에 따라 도는가」**이고, 그건 **새 자료 없이 «공짜»로** 잴 수 있다.

🔴 **자료 0 · 능형만 · 챔피언 적합 없음** ⇒ **가벼운 팔**(사전등록 §7 에 실측을 박았다).

씀:
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
      nohup python3 runners/delta996_coef.py > /tmp/delta996_coef.log 2>&1 & disown
"""
import argparse
import collections
import json
import time

import numpy as np

import delta996_common as C
import beta994_common as B94
import gamma995_masks as MK

OUT_DEFAULT = C.ROOT / "runners" / "out996_coef.json"

# ── 사전등록 상수 ────────────────────────────────────────────────
ALPHAS = (0.1, 1.0, 10.0)      #: 🔴 조항 66 — 문턱 대신 검사를 인자화한다
ALPHA_HEAD = 1.0               #: 헤드라인(`lab/forms.py:145 DirectPool alpha=1.0` 와 같다)
CELL_GATES = (20, 30, 50)      #: 칸이 서려면 필요한 «관측된» 행
GATE_HEAD = 30
MIN_UNIQ = 3                   #: 축 값이 3 종 미만이면 계수가 뜻이 없다
FAM1 = "F1 · 팔 A 조각 --- 축 5 × 이웃 조각 4 = 20"
FAM2 = "F2 · 팔 A 헤드라인 --- 이웃 조각 4 (계수 벡터가 도나 · 순열)"


def cells(d0, doms, blk, gate):
    """칸(블록 × 도메인)마다 행 · 축별 관측 · 잴 수 있나."""
    out = collections.OrderedDict()
    for d in doms:
        V, O = C.axis_cols(d0, d)
        for b in range(C.NBLOCK):
            m = np.asarray(blk[d][b], bool)
            if int(m.sum()) == 0:
                out[(d, b)] = None
                continue
            Vb, Ob = V[m], O[m]
            est = C.estimable(Ob, gate, Vb, MIN_UNIQ)
            out[(d, b)] = collections.OrderedDict([
                ("행", int(m.sum())),
                ("축별 관측 행", [int((Ob[:, j] > 0).sum()) for j in range(5)]),
                ("🔴 잴 수 있나", est),
                ("잴 수 있는 축 수", int(sum(est))),
                ("mask", m)])
    return out


def seg_perm(d0, doms, blk, b, alpha, gate, B=C.PERM_B, seed=C.PERM_SEED):
    """🔴🔴 조각 `b→b+1` — 계수 벡터가 «도나». 순열이 정확한 귀무를 만든다.

    한 도메인 안에서 두 블록 행을 **합치고** 블록 딱지를 뽑기로 다시 붙인다.
    눈금(표준편차)은 «합친 행»에서 한 번 내므로 순열이 눈금을 안 바꾼다.
    """
    per, nulls, used = collections.OrderedDict(), collections.OrderedDict(), []
    rng = np.random.RandomState(int(seed) + int(b))
    for d in doms:
        m0 = np.asarray(blk[d][b], bool)
        m1 = np.asarray(blk[d][b + 1], bool)
        V, O = C.axis_cols(d0, d)
        y = np.asarray(d0.dom[d][2], float)
        n0, n1 = int(m0.sum()), int(m1.sum())
        if n0 < gate or n1 < gate:
            continue
        e0 = C.estimable(O[m0], gate, V[m0], MIN_UNIQ)
        e1 = C.estimable(O[m1], gate, V[m1], MIN_UNIQ)
        js = [j for j in range(5) if e0[j] and e1[j]]
        if len(js) < 2:
            continue
        idx = np.concatenate([np.where(m0)[0], np.where(m1)[0]])
        Vp, yp = V[idx][:, js], y[idx]
        sd = Vp.std(0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        Op = O[idx][:, js]

        def beta(sel):
            return C.cell_beta(Vp[sel], Op[sel], yp[sel], alpha, sd)

        s0 = np.zeros(len(idx), bool)
        s0[:n0] = True
        obs = float(np.mean((beta(s0) - beta(~s0)) ** 2))
        nl = np.empty(B)
        for t in range(B):
            p = rng.permutation(len(idx))
            s = np.zeros(len(idx), bool)
            s[p[:n0]] = True
            nl[t] = float(np.mean((beta(s) - beta(~s)) ** 2))
        per[d] = collections.OrderedDict([
            ("쓴 축", [C.ALL5[j] for j in js]), ("행", [n0, n1]),
            ("관측된 |Δβ|²(축 평균)", C._r(obs, 8)),
            ("귀무 중앙", C._r(float(np.median(nl)), 8)),
            ("🔴 비(관측/귀무중앙)", C._r(obs / max(float(np.median(nl)), 1e-15), 4)),
            ("🔴 도메인 p", C._r((1.0 + float((nl >= obs).sum())) / (B + 1.0), 6))])
        nulls[d] = nl
        used.append((d, obs))
    if not used:
        return collections.OrderedDict([("🔴 못 쟀다", "칸이 없다"),
                                        ("도메인별", per)]), None
    obsm = float(np.mean([o for _d, o in used]))
    nm = np.mean(np.vstack([nulls[d] for d, _o in used]), axis=0)
    p = (1.0 + float((nm >= obsm).sum())) / (C.PERM_B + 1.0)
    return collections.OrderedDict([
        ("🔴 자", "순열 B=%d · RandomState(%d+%d) · 블록 딱지 재배치 · 도메인 안"
         % (B, seed, b)),
        ("분모: 쓴 도메인", len(used)), ("도메인", [d for d, _o in used]),
        ("관측 평균 |Δβ|²", C._r(obsm, 8)),
        ("귀무 평균의 중앙", C._r(float(np.median(nm)), 8)),
        ("🔴 비(관측/귀무중앙)", C._r(obsm / max(float(np.median(nm)), 1e-15), 4)),
        ("🔴🔴 순열 p", C._r(p, 6)),
        ("도메인별", per)]), p


def seg_axis(d0, doms, blk, b, alpha, gate):
    """🔴 조각 «안»을 축으로 다시 쪼갠다(조항 79) — 축마다 Δ · 군집 SE · t · 동부호."""
    per = collections.OrderedDict()
    for d in doms:
        m0 = np.asarray(blk[d][b], bool)
        m1 = np.asarray(blk[d][b + 1], bool)
        V, O = C.axis_cols(d0, d)
        y = np.asarray(d0.dom[d][2], float)
        if int(m0.sum()) < gate or int(m1.sum()) < gate:
            continue
        e0 = C.estimable(O[m0], gate, V[m0], MIN_UNIQ)
        e1 = C.estimable(O[m1], gate, V[m1], MIN_UNIQ)
        idx = np.concatenate([np.where(m0)[0], np.where(m1)[0]])
        sd = V[idx].std(0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        b0 = C.cell_beta(V[m0], O[m0], y[m0], alpha, sd)
        b1 = C.cell_beta(V[m1], O[m1], y[m1], alpha, sd)
        for j, a in enumerate(C.ALL5):
            if e0[j] and e1[j]:
                per.setdefault(a, collections.OrderedDict())[d] = \
                    float(b1[j] - b0[j])
    rows = collections.OrderedDict()
    for a in C.ALL5:
        v = per.get(a) or {}
        if len(v) < 2:
            rows[a] = collections.OrderedDict([
                ("🔴 못 쟀다", "도메인이 2 미만이다 --- 조항 59 「쟀는데 설정이 버렸다」"),
                ("분모: 도메인", len(v)), ("도메인별 Δβ",
                                       {k: C._r(x) for k, x in v.items()})])
            continue
        cs = C.cluster_se(v)
        mu = cs["점추정"] or 0.0
        tau = cs["도메인 사이 SD(τ̂)"] or 0.0
        cs["🔴 도메인별 Δβ"] = {k: C._r(x) for k, x in sorted(v.items())}
        cs["🔴 d*(t>2 에 필요한 도메인 수) = 4τ̂²/μ̂²"] = \
            C._r(4 * tau ** 2 / mu ** 2, 3) if mu else None
        rows[a] = cs
    return rows


def stage(out_path, alpha_grid=ALPHAS, gate_grid=CELL_GATES, permB=C.PERM_B):
    t0 = C.now_utc()
    cs0 = C.code_stamp()
    wall = time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("996 팔 A --- 🔴 블록별로 능형을 «따로» 적합해 「축 다섯의 계수」가 "
                 "움직이나 · 어느 축이. 조각(블록 쌍)마다 쪼개고 Holm 으로 보정한다.")
    out["🔴 축"] = "C1 상태→예측 · C4 자료를 늘리면 나아지나"
    out["사전등록"] = "docs/prereg_996_information_field.md §2 · §5 · §6"
    out["🔴 등록된 자"] = collections.OrderedDict([
        ("군집 SE", "score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중"
         % (C.B_DOM, C.DOM_SEED)),
        ("순열", "블록 딱지 재배치 · B=%d · RandomState(%d+조각)" % (permB, C.PERM_SEED)),
        ("다중비교", "Holm–Bonferroni · alpha=%.2f · 가족 둘(F1 20 · F2 4)" % C.HOLM_ALPHA)])
    out["🔴 고정한 스레드"] = C.THREADS

    d0, doms = B94.load()
    info, tr_blk, ho_blk, edges = MK.blocks_fixed(d0, doms, C.QS, C.NBLOCK)
    out["§A0-가 시간 블록(F01 수리 마스크 · 절단은 994 와 같다)"] = info

    # ── §A0 🔴 분모를 «먼저» 센다 (조항 60) ──────────────────────
    dn = collections.OrderedDict()
    for g in gate_grid:
        cc = cells(d0, doms, tr_blk, g)
        tab = collections.OrderedDict()
        for d in doms:
            tab[d] = [(cc[(d, b)] or {}).get("잴 수 있는 축 수", 0)
                      for b in range(C.NBLOCK)]
        nax = collections.OrderedDict()
        for j, a in enumerate(C.ALL5):
            nax[a] = [int(sum(1 for d in doms
                              if (cc[(d, b)] or {}).get("🔴 잴 수 있나",
                                                        [False] * 5)[j]))
                      for b in range(C.NBLOCK)]
        dn["게이트 %d" % g] = collections.OrderedDict([
            ("도메인별 잴 수 있는 축 수(블록 0..4)", tab),
            ("🔴 축별 잴 수 있는 «도메인» 수(블록 0..4)", nax),
            ("🔴 축별 다섯 블록 «전부»에서 서는 도메인 수",
             {a: int(sum(1 for d in doms
                         if all((cc[(d, b)] or {}).get("🔴 잴 수 있나",
                                                       [False] * 5)[j]
                                for b in range(C.NBLOCK))))
              for j, a in enumerate(C.ALL5)})])
    out["§A0-나 🔴🔴 분모 --- 계수를 「잴 수 있는」 칸"] = collections.OrderedDict([
        ("🔴 왜 이걸 먼저 세나",
         "축 다섯은 도메인마다 «관측되는 자리»가 다르다. 관측 0 인 축은 열이 상수 0.5 라 "
         "능형이 «구성상» 0 을 낸다 --- 그건 「계수가 0 이다」가 아니라 「못 쟀다」다(조항 59)."),
        ("게이트별", dn)])

    # ── §A1 블록별 계수 (서술) ──────────────────────────────────
    perblk = collections.OrderedDict()
    for al in alpha_grid:
        tb = collections.OrderedDict()
        for b in range(C.NBLOCK):
            byax = collections.OrderedDict()
            for j, a in enumerate(C.ALL5):
                vals = {}
                for d in doms:
                    m = np.asarray(tr_blk[d][b], bool)
                    if int(m.sum()) < GATE_HEAD:
                        continue
                    V, O = C.axis_cols(d0, d)
                    if not C.estimable(O[m], GATE_HEAD, V[m], MIN_UNIQ)[j]:
                        continue
                    sd = V[m].std(0)
                    sd = np.where(sd > 1e-12, sd, 1.0)
                    bb = C.cell_beta(V[m], O[m], np.asarray(d0.dom[d][2],
                                                            float)[m], al, sd)
                    vals[d] = float(bb[j])
                byax[a] = collections.OrderedDict([
                    ("분모: 도메인", len(vals)),
                    ("도메인 등가중 평균 β", C._r(float(np.mean(list(vals.values())))
                                          ) if vals else None),
                    ("도메인별 β", {k: C._r(v) for k, v in sorted(vals.items())})])
            tb["블록 %d" % b] = byax
        perblk["alpha %g" % al] = tb
    out["§A1 블록별 축 계수(서술 · 블록 자기 눈금)"] = perblk

    # ── §A2 🔴🔴🔴 헤드라인 — 계수 벡터가 «도나» (순열) ──────────
    head, ps = collections.OrderedDict(), []
    for b in range(C.NBLOCK - 1):
        r, p = seg_perm(d0, doms, tr_blk, b, ALPHA_HEAD, GATE_HEAD, permB)
        head["조각 블록 %d→%d" % (b, b + 1)] = r
        ps.append(("조각 블록 %d→%d" % (b, b + 1), p))
    out["§A2 🔴🔴🔴 헤드라인 --- 계수 벡터가 도나(순열)"] = head
    out["§A2-나 🔴 Holm (가족 F2)"] = C.holm(ps, C.HOLM_ALPHA, FAM2)

    # ── §A3 🔴 조각 × 축 (조항 79) ─────────────────────────────
    seg, ps1 = collections.OrderedDict(), []
    for b in range(C.NBLOCK - 1):
        rows = seg_axis(d0, doms, tr_blk, b, ALPHA_HEAD, GATE_HEAD)
        seg["조각 블록 %d→%d" % (b, b + 1)] = rows
        for a in C.ALL5:
            ps1.append(("조각 %d→%d · %s" % (b, b + 1, a),
                        rows[a].get("🔴 양측 p(정규 근사)")))
    out["§A3 🔴🔴 조각 × 축 (조항 79 --- 대비를 조각으로)"] = seg
    out["§A3-나 🔴🔴 Holm (가족 F1)"] = C.holm(ps1, C.HOLM_ALPHA, FAM1)

    # ── §A4 게이트·알파 사다리 (자가 얼마나 견고한가) ────────────
    lad = collections.OrderedDict()
    for g in gate_grid:
        for al in alpha_grid:
            if g == GATE_HEAD and al == ALPHA_HEAD:
                key = "게이트 %d · alpha %g (헤드라인)" % (g, al)
            else:
                key = "게이트 %d · alpha %g" % (g, al)
            rr = collections.OrderedDict()
            for b in range(C.NBLOCK - 1):
                rows = seg_axis(d0, doms, tr_blk, b, al, g)
                rr["조각 %d→%d" % (b, b + 1)] = collections.OrderedDict(
                    [(a, collections.OrderedDict([
                        ("점추정", rows[a].get("점추정")),
                        ("t_clu", rows[a].get("t_clu")),
                        ("도메인 수", rows[a].get("도메인 수")),
                        ("2·SE 를 넘나", rows[a].get("🔴🔴 2·SE 를 넘나"))]))
                     for a in C.ALL5])
            lad[key] = rr
    out["§A4 사다리 --- 게이트 × alpha"] = lad

    # ── §A5 🔴🔴🔴 조항 78 — 기계로 센 ㉮·㉯ ────────────────────
    base = {}
    for b in range(C.NBLOCK - 1):
        rows = seg["조각 블록 %d→%d" % (b, b + 1)]
        for a in C.ALL5:
            base[(b, a)] = rows[a].get("🔴 도메인별 Δβ") or {}

    def mk(fn):
        return {k: {d: fn(v) for d, v in vv.items()} for k, vv in base.items()}

    variants = C.variant_grid(base, 996)
    claims = []
    for b in range(C.NBLOCK - 1):
        for a in C.ALL5:
            def f(st, b=b, a=a):
                v = st[(b, a)]
                if len(v) < 2:
                    return False
                cs = C.cluster_se(v)
                return bool(cs["🔴🔴 2·SE 를 넘나"])
            claims.append(("조각 %d→%d · %s 가 2·SE 를 넘는다" % (b, b + 1, a), f))
    for b in range(C.NBLOCK - 1):
        def g(st, b=b):
            return len(st[(b, C.ALL5[0])]) >= 2
        claims.append(("조각 %d→%d 의 target_breadth 도메인이 2 이상이다"
                       % (b, b + 1), g))
    controls = [
        ("🔴 대조 ㉮(자료 파생): 어느 조각·축이든 도메인 수가 12 이하다",
         lambda st: all(len(v) <= 12 for v in st.values())),
        ("🔴 대조 ㉯(자료 파생): 어느 조각·축이든 도메인 수가 13 이상이다",
         lambda st: any(len(v) >= 13 for v in st.values()))]
    out["§A5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"] = C.taut_scan(
        claims, variants, "팔 A 의 주장 %d 개를 변이체 %d 개에서 다시 계산했다"
        % (len(claims), len(variants)), controls)

    out["🔴🔴 조항 79 개정 2 --- 이 주행이 낸 cluster_se 칸 전량"] = C.cse_ledger()
    out["🔴🔴 조항 78 개정 4 --- 반증조건의 «분모»를 손으로 고르지 않았다"] = \
        collections.OrderedDict([
            ("🔴 왜", "995 팔 C 는 반증조건 여덟 중 넷만 검사하고 「㉮ 0/4」를 냈다 --- "
                    "뺀 넷 중 셋이 ㉮ 였다(티처 #134). 그래서 분모를 «이름으로» 신고한다."),
            ("분모: 이 팔이 지는 반증조건", 4),
            ("이름", ['F14 못 잰 칸을 0 으로 안 적었다', 'F15 Holm 가족 크기', 'F12 조항 78 대조 계수', 'F13 도장 시작=끝']),
            ("🔴 산출물 키로 «기계가» 확인하는 것", ['F12', 'F13', 'F15'])])
    out["🔴 도장"] = C.stamp(t0, cs0, collections.OrderedDict([
        ("걸린 초", round(time.time() - wall, 3)),
        ("🔴 자료 지문(도메인별 배열 sha256)", B94.data_fp(d0, doms))]))
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote %s (%.1f s)" % (out_path, time.time() - wall), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--permB", type=int, default=C.PERM_B)
    a = ap.parse_args()
    stage(a.out, permB=a.permB)


if __name__ == "__main__":
    main()
