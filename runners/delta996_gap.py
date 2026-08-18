#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""996 팔 B — 🔴🔴 **계수 이동이 낙차의 「몇 %」를 설명하나 · 그리고 `Z_t` 후보를 «싸게» 거른다.**

사전등록 `docs/prereg_996_information_field.md` §3 · §5 · §6.

🔴 이 팔은 **「대리 세계」**에서 돈다 — 챔피언(BagBoost)이 아니라 **능형**이다.
   까닭 둘: ① 계수를 «갖는» 모형이라야 「계수를 이식」할 수 있다
   ② 적합이 밀리초라 `Z_t` 후보를 여럿 걸러 팔 C 에 «하나»만 넘길 수 있다.
🔴 **대리 세계의 수를 챔피언 세계의 수로 읽으면 안 된다.** 이 팔은 «몫»과 «방향»만 말한다.

🔴🔴 **분모 주의**(티처 #134): `0.183381` 은 **학습 행 수 몫(≈29 %)이 «섞인»** 분모다.
   **최종 분모는 팔 0 이 내는 「잔여 낙차」이고, 그 나눗셈은 «정비 팔»이 채점에서 한다.**
   측정 팔은 서로 안 읽는다(조항 74-3). 이 팔은 **분자와 자기 세계의 분모**만 낸다.

🔴 **가벼운 팔** — 챔피언 적합 0.

씀:
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \\
      nohup python3 runners/delta996_gap.py > /tmp/delta996_gap.log 2>&1 & disown
"""
import argparse
import collections
import json
import time

import numpy as np
from scipy.stats import rankdata, spearmanr

import delta996_common as C
import beta994_common as B94
import gamma995_masks as MK

OUT_DEFAULT = C.ROOT / "runners" / "out996_gap.json"
ALPHAS = (0.1, 1.0, 10.0)
ALPHA_HEAD = 1.0
FAMB = "FB · 팔 B --- 대리 세계 조각 3"


def design(d0, doms, mask, extra=None):
    """대리 세계 설계행렬 = [축 값 5 · 표시자 5 · (덧열) · 도메인 표시 12]."""
    Xs, ys, idx = [], [], collections.OrderedDict()
    off = 0
    for i, d in enumerate(doms):
        m = np.asarray(mask[d], bool)
        n = int(m.sum())
        if n == 0:
            continue
        V, O = C.axis_cols(d0, d)
        cols = [V[m], O[m]]
        if extra:
            for _nm, per in extra.items():
                v, k = per[d]
                cols.append(np.column_stack([np.asarray(v)[m],
                                             np.asarray(k)[m]]))
        oh = np.zeros((n, len(doms)))
        oh[:, i] = 1.0
        cols.append(oh)
        Xs.append(np.column_stack(cols))
        y = np.asarray(d0.dom[d][2], float)[m]
        ys.append(rankdata(y) / float(n))
        idx[d] = (off, off + n)
        off += n
    if not Xs:
        return None, None, idx
    return np.vstack(Xs), np.concatenate(ys), idx


def sur_fit(d0, doms, mask, alpha, extra=None):
    X, y, _i = design(d0, doms, mask, extra)
    if X is None:
        return None
    b, c = C.ridge(X, y, alpha)
    return collections.OrderedDict([("b", b), ("c", c),
                                    ("열", X.shape[1]), ("행", X.shape[0])])


def sur_score(d0, doms, f, mask, extra=None, offset=None, gate=C.GATE_CANON):
    """도메인별 스피어만. `offset` 은 «행별로 더할 값»(구조 항등식 검사가 쓴다)."""
    out = collections.OrderedDict()
    if f is None:
        return out
    for d in doms:
        m = np.asarray(mask[d], bool)
        if int(m.sum()) < gate:
            continue
        V, O = C.axis_cols(d0, d)
        cols = [V[m], O[m]]
        if extra:
            for _nm, per in extra.items():
                v, k = per[d]
                cols.append(np.column_stack([np.asarray(v)[m],
                                             np.asarray(k)[m]]))
        oh = np.zeros((int(m.sum()), len(doms)))
        oh[:, doms.index(d)] = 1.0
        X = np.column_stack(cols + [oh])
        if X.shape[1] != len(f["b"]):
            continue
        p = X @ f["b"] + f["c"]
        if offset is not None:
            p = p + np.asarray(offset[d], float)[m]
        y = np.asarray(d0.dom[d][2], float)[m]
        ok = np.isfinite(p) & np.isfinite(y)
        if int(ok.sum()) < gate:
            continue
        r = float(spearmanr(p[ok], y[ok])[0])
        if np.isfinite(r):
            out[d] = r
    return out


def curve(d0, doms, tr_blk, ho_blk, alpha, extra=None):
    rho = collections.OrderedDict()
    fits = collections.OrderedDict()
    hm = {d: ho_blk[d][4] for d in doms}
    for k in C.ORIGINS:
        tm = MK.train_mask_lt(tr_blk, doms, k)
        f = sur_fit(d0, doms, tm, alpha, extra)
        fits["원점 %d" % k] = f
        rho["원점 %d" % k] = sur_score(d0, doms, f, hm, extra)
    return rho, fits


def seghead(rho, labels, family, tag):
    com = sorted(set.intersection(*[set(rho[l]) for l in labels]))
    per_by = {l: {d: rho[l][d] for d in com} for l in labels}
    rows = C.seg_from(labels, per_by)
    segk = ["%s→%s" % (labels[i], labels[i + 1]) for i in range(len(labels) - 1)]
    npass = int(sum(1 for k in segk if rows[k].get("🔴🔴 2·SE 를 넘나")))
    pdom = {d: [per_by[labels[i + 1]][d] - per_by[labels[i]][d]
                for i in range(len(labels) - 1)] for d in com}
    return collections.OrderedDict([
        ("🔴 부호 규약", C.SIGN_RULE), ("무엇", tag),
        ("공통 도메인 수", len(com)), ("공통 도메인", com), ("조각", rows),
        ("🔴🔴 연언 채점 --- 통과 조각 / 분모 조각", "%d/%d" % (npass, len(segk))),
        ("🔴🔴🔴 부호뒤집기 «전수» 순열", C.signflip_exact(pdom, segk)),
        ("🔴 Holm", C.holm([(k, rows[k].get("🔴 양측 p(정규 근사)")) for k in segk],
                          C.HOLM_ALPHA, family)),
        ("🔴 합(항등 · 통과로 안 센다)",
         rows["%s→%s" % (labels[0], labels[-1])].get("점추정"))])


def stage(out_path, alphas=ALPHAS):
    t0 = C.now_utc()
    cs0 = C.code_stamp()
    wall = time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("996 팔 B --- 🔴 계수 이동이 낙차의 몇 %를 설명하나(계수 «이식») + "
                 "Z_t 후보를 대리 세계에서 «싸게» 거른다.")
    out["🔴 축"] = "C1 · C4"
    out["사전등록"] = "docs/prereg_996_information_field.md §3 · §5 · §6"
    out["🔴 대리 세계임을 못박는다"] = (
        "능형 · 축 값 5 + 표시자 5 + 도메인 표시. 챔피언(BagBoost)이 «아니다». "
        "이 팔의 ρ 수준을 판 ρ 로 읽으면 안 된다 --- 몫과 방향만 말한다.")
    out["🔴 고정한 스레드"] = C.THREADS

    d0, doms = B94.load()
    info, tr_blk, ho_blk, edges = MK.blocks_fixed(d0, doms, C.QS, C.NBLOCK)
    zs = C.zseries()
    out["§B0-가 시간 블록"] = info
    out["§B0-나 🔴🔴 Z_t 원천과 그 덮음"] = collections.OrderedDict([
        ("원천 정보", zs[0]),
        ("블록 상수 Z", C.block_const_table(edges, zs[2], zs[3], zs[4], zs[5])),
        ("🔴 덮음 장부", C.zcov_ledger(d0, doms, ho_blk, zs))])

    # ── §B1 대리 세계 원점 곡선 ────────────────────────────────
    labels = ["원점 %d" % k for k in C.ORIGINS]
    base = collections.OrderedDict()
    for al in alphas:
        rho, fits = curve(d0, doms, tr_blk, ho_blk, al)
        base["alpha %g" % al] = collections.OrderedDict([
            ("도메인별 ρ", {k: {d: C._r(x) for d, x in v.items()}
                        for k, v in rho.items()}),
            ("헤드라인", seghead(rho, labels, FAMB, "대리 세계 원점 곡선 · alpha %g" % al))])
        if al == ALPHA_HEAD:
            rho_h, fits_h = rho, fits
    out["§B1 대리 세계 원점 곡선"] = base
    out["§B1-나 🔴 챔피언 세계(995)의 조각 --- «참고 상수»다. 여기서 다시 안 잰다"] = \
        collections.OrderedDict([(k, {"점추정": v, "군집 SE": C.G995_SE[k]})
                                 for k, v in C.G995.items()])

    # ── §B2 🔴🔴🔴 계수 «이식» — 블록 4 의 계수만 얹으면 틈이 얼마나 닫히나 ──
    hm = {d: ho_blk[d][4] for d in doms}
    orac = sur_fit(d0, doms, {d: tr_blk[d][4] for d in doms}, ALPHA_HEAD)
    graft = collections.OrderedDict()
    g0 = seghead(rho_h, labels, FAMB, "기준선")
    gap_sur = g0["조각"]["원점 1→원점 4"].get("점추정") or 0.0
    for k in C.ORIGINS:
        f = fits_h["원점 %d" % k]
        if f is None or orac is None:
            continue
        fg = collections.OrderedDict([("b", np.array(f["b"], float)),
                                      ("c", f["c"]), ("열", f["열"]),
                                      ("행", f["행"])])
        fg["b"][:5] = np.array(orac["b"], float)[:5]     # 🔴 축 다섯 계수만 갈아끼운다
        r0 = rho_h["원점 %d" % k]
        r1 = sur_score(d0, doms, fg, hm)
        com = sorted(set(r0) & set(r1))
        dd = {d: r1[d] - r0[d] for d in com}
        graft["원점 %d" % k] = collections.OrderedDict([
            ("이식 전 ρ(등가중)", C._r(float(np.mean([r0[d] for d in com])))),
            ("이식 후 ρ(등가중)", C._r(float(np.mean([r1[d] for d in com])))),
            ("🔴 Δ(이식 − 원본)", C.cluster_se(dd)),
            ("🔴 축 다섯 계수 전후", collections.OrderedDict(
                [(a, [C._r(float(f["b"][j])), C._r(float(fg["b"][j]))])
                 for j, a in enumerate(C.ALL5)]))])
    d_graft = (graft.get("원점 1", {}).get("🔴 Δ(이식 − 원본)", {}) or {}).get("점추정")
    out["§B2 🔴🔴🔴 계수 이식 --- 「블록 4 의 계수」만 얹는다"] = \
        collections.OrderedDict([
            ("🔴 무엇", "원점 k 모형의 «축 다섯 계수»만 블록 4 에서 적합한 값으로 갈아끼운다. "
                      "나머지(표시자·도메인 절편)는 그대로. 곧 「계수가 시대에 따라 도는 몫」이다."),
            ("칸별", graft),
            ("🔴 대리 세계 자신의 낙차(원점1→4)", C._r(gap_sur)),
            ("🔴🔴 몫 = 원점 1 이식 Δ / 대리 세계 낙차",
             C._r((d_graft or 0.0) / gap_sur, 4) if gap_sur else None),
            ("🔴 참고 몫 = 원점 1 이식 Δ / 0.183381 (🔴 학습량 몫이 «섞인» 분모)",
             C._r((d_graft or 0.0) / C.GAP995, 4)),
            ("🔴🔴 최종 분모는 팔 0 의 «잔여 낙차»이고 그 나눗셈은 «정비 팔»이 한다",
             "측정 팔은 서로 안 읽는다(조항 74-3). 이 칸은 분자만 낸다.")])

    # ── §B3 Z 후보 거르기 ─────────────────────────────────────
    zi, zdays, zyrs, zmz, zcx, zcy = zs
    z365 = C.zseries(ma=365)
    cand = collections.OrderedDict()
    defs = collections.OrderedDict([
        ("ZA 수준(ma30)", ("행", zs)),
        ("ZB 수준(ma365)", ("행", z365)),
        ("ZC 블록 상수(ma30)", ("블록", zs)),
    ])
    for nm, (kind, zz) in defs.items():
        per = {}
        for d in doms:
            yr = np.asarray(d0.yr[d], float)
            per[d] = (C.z_block(yr, edges, zz[2], zz[3], zz[4], zz[5])
                      if kind == "블록"
                      else C.z_row(yr, zz[2], zz[3], zz[4], zz[5]))
        main = collections.OrderedDict([("Z", per)])
        inter = collections.OrderedDict([("Z", per)])
        for ai, a in enumerate(C.ALL5):
            pp = {}
            for d in doms:
                V, O = C.axis_cols(d0, d)
                zv, zm = per[d]
                mk = (O[:, ai] > 0) & (zm > 0)
                v = np.full(len(zv), 0.5)
                v[mk] = (V[mk, ai] - 0.5) * (zv[mk] - 0.5) + 0.5
                pp[d] = (v, mk.astype(float))
            inter["ZX_%s" % a] = pp
        rm, _fm = curve(d0, doms, tr_blk, ho_blk, ALPHA_HEAD, main)
        ri, _fi = curve(d0, doms, tr_blk, ho_blk, ALPHA_HEAD, inter)
        row = collections.OrderedDict()
        for k in labels:
            com = sorted(set(rho_h[k]) & set(rm[k]) & set(ri[k]))
            row[k] = collections.OrderedDict([
                ("기준선 ρ(등가중)", C._r(float(np.mean([rho_h[k][d] for d in com])))),
                ("🔴 Δ 주효과만", C.cluster_se({d: rm[k][d] - rho_h[k][d]
                                            for d in com})),
                ("🔴🔴 Δ 상호작용", C.cluster_se({d: ri[k][d] - rho_h[k][d]
                                              for d in com})),
                ("🔴 상호작용 − 주효과", C.cluster_se({d: ri[k][d] - rm[k][d]
                                                for d in com}))])
        cand[nm] = row
    out["§B3 🔴🔴 Z_t 후보 거르기(대리 세계)"] = collections.OrderedDict([
        ("🔴 무엇", "후보마다 「주효과만」과 「A×Z 상호작용」을 둘 다 넣고 견준다. "
                  "🔴 **상호작용이 주효과를 이겨야** 정보장이 「축의 계수를 돌린다」는 뜻이다."),
        ("후보별", cand)])

    # ── §B4 🔴🔴🔴 위약 둘 — 하나는 «구조 항등식», 하나는 «재적합» ──
    zblk = {d: C.z_block(np.asarray(d0.yr[d], float), edges,
                         zyrs, zmz, zcx, zcy) for d in doms}
    off_const = {d: np.where(np.asarray(zblk[d][1]) > 0,
                             np.asarray(zblk[d][0]) * 0.3, 0.0) for d in doms}
    off_row = {}
    for d in doms:
        v, m = C.z_row(np.asarray(d0.yr[d], float), zyrs, zmz, zcx, zcy)
        off_row[d] = np.where(m > 0, v * 0.3, 0.0)
    f4 = fits_h["원점 4"]
    r_b = sur_score(d0, doms, f4, hm)
    r_c = sur_score(d0, doms, f4, hm, offset=off_const)
    r_r = sur_score(d0, doms, f4, hm, offset=off_row)
    com = sorted(set(r_b) & set(r_c) & set(r_r))
    dc = {d: r_c[d] - r_b[d] for d in com}
    dr = {d: r_r[d] - r_b[d] for d in com}
    # 위약 ㉡ --- 재적합
    zmain = collections.OrderedDict([("Z", zblk)])
    r_ref, _f = curve(d0, doms, tr_blk, ho_blk, ALPHA_HEAD, zmain)
    com2 = sorted(set(rho_h["원점 4"]) & set(r_ref["원점 4"]))
    out["§B4 🔴🔴🔴 위약 --- 「배선이 새나」"] = collections.OrderedDict([
        ("§B4-가 🔴 구조 항등식(고정 모형 · 예측에 «블록 상수»를 더한다)",
         collections.OrderedDict([
             ("🔴 무엇", "ρ 는 블록 «안» 순위만 본다 ⇒ 블록 안에서 «상수»인 성분은 "
                       "원리상 ρ 에 «못» 닿는다. 이건 «항등식»이다(조항 78 ㉮)."),
             ("도메인별 Δρ", {d: C._r(dc[d], 15) for d in com}),
             ("최대 |Δρ|", C._r(float(np.max(np.abs(list(dc.values())))), 15)),
             ("🔴 통과: 반증조건 B1 (전부 1e-12 안)",
              bool(max(abs(v) for v in dc.values()) <= 1e-12)),
             ("🔴🔴 그런데 이 자가 «떨어질 수 있나» --- 대조판(행별로 «변하는» 값을 더한다)",
              collections.OrderedDict([
                  ("도메인별 Δρ", {d: C._r(dr[d], 12) for d in com}),
                  ("최대 |Δρ|", C._r(float(np.max(np.abs(list(dr.values())))), 12)),
                  ("🔴 통과: 반증조건 B2 (한 도메인이라도 1e-12 를 «넘는다»)",
                   bool(max(abs(v) for v in dr.values()) > 1e-12)),
                  ("🔴 그래서", "이 검사는 «통과식의 복사본»이 아니다 --- 같은 코드가 "
                             "0 도 내고 0 아닌 것도 낸다(조항 78 개정 2)")]))])),
        ("§B4-나 🔴 위약 팔(재적합 · 블록 상수 Z 주효과)",
         collections.OrderedDict([
             ("🔴 무엇", "🔴🔴 **이건 항등식이 «아니다»** --- 열을 하나 넣으면 «다른 열의 "
                       "계수»가 같이 바뀌므로 예측이 블록 상수만큼 옮겨가지 않는다. "
                       "사이클 지시문의 「위약은 ρ 를 못 바꿔야 한다」는 «고정 모형»에서만 "
                       "참이다 --- 설계 팔이 사전등록 §3-라 에 정정으로 적었다."),
             ("원점 4 Δρ", C.cluster_se({d: r_ref["원점 4"][d] - rho_h["원점 4"][d]
                                       for d in com2})),
             ("🔴 예측(방향)", "|Δρ(주효과 재적합)| < |Δρ(상호작용 재적합)| 이어야 한다")]))])

    # ── §B5 조항 78 ─────────────────────────────────────────
    segbase = {}
    for i in range(3):
        segbase["원점 %d→%d" % (i + 1, i + 2)] = {
            d: rho_h[labels[i + 1]][d] - rho_h[labels[i]][d]
            for d in set(rho_h[labels[i]]) & set(rho_h[labels[i + 1]])}
    variants = C.variant_grid(segbase, 996)
    claims = [("%s 가 2·SE 를 넘는다" % k,
               (lambda kk: lambda st: bool(C.cluster_se(st[kk])
                                           .get("🔴🔴 2·SE 를 넘나")))(k))
              for k in segbase]
    controls = [
        ("🔴 대조 ㉮(자료 파생): 조각의 도메인 수가 12 이하다",
         lambda st: all(len(v) <= 12 for v in st.values())),
        ("🔴 대조 ㉯(자료 파생): 조각의 도메인 수가 13 이상이다",
         lambda st: any(len(v) >= 13 for v in st.values()))]
    out["§B5 🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"] = C.taut_scan(
        claims, variants, "팔 B 의 주장 %d 개 × 변이체 %d 개"
        % (len(claims), len(variants)), controls)

    out["🔴🔴 조항 79 개정 2 --- 이 주행이 낸 cluster_se 칸 전량"] = C.cse_ledger()
    out["🔴🔴 조항 78 개정 4 --- 반증조건의 «분모»를 손으로 고르지 않았다"] = \
        collections.OrderedDict([
            ("🔴 왜", "995 팔 C 는 반증조건 여덟 중 넷만 검사하고 「㉮ 0/4」를 냈다 --- "
                    "뺀 넷 중 셋이 ㉮ 였다(티처 #134). 그래서 분모를 «이름으로» 신고한다."),
            ("분모: 이 팔이 지는 반증조건", 4),
            ("이름", ['F6 위약 ㉠ 항등식 = 0 · 대조판 ≠ 0', 'F15 Holm 가족 크기', 'F12 조항 78 대조 계수', 'F13 도장 시작=끝']),
            ("🔴 산출물 키로 «기계가» 확인하는 것", ['F6', 'F12', 'F13', 'F15'])])
    out["🔴 도장"] = C.stamp(t0, cs0, collections.OrderedDict([
        ("걸린 초", round(time.time() - wall, 3)),
        ("🔴 자료 지문", B94.data_fp(d0, doms))]))
    with open(str(out_path), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote %s (%.1f s)" % (out_path, time.time() - wall), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    a = ap.parse_args()
    stage(a.out)


if __name__ == "__main__":
    main()
