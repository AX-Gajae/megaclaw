#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""996 팔 C — 🔴🔴🔴 **`Z_t`(그때 세상이 어땠나)를 «챔피언 세계»에 처음으로 넣는다.**

사전등록 `docs/prereg_996_information_field.md` §4 · §5 · §6.

🔴🔴 **설계 팔이 ⓪ 에서 찾은 구조 사실 셋**(사전등록 §0-나 · 이 팔의 전제다):
   ① 챔피언이 받는 축은 **다섯이 아니라 «공통 36»** 이다(`AXIS_MODE='common'`).
   ② 그 36 안에 **세상의 «그때» 상태를 담은 열은 하나도 없다** --- `wiki_*`·`trend_*` 는
      전부 **개체 «자신»의** 시계열이고 `cal_*` 는 개체 «자신»의 날짜다.
   ③ 🔴 **`TIMEAX = False`** 라 챔피언은 예보 때 **연도를 아예 «안 본다»**
      (`SEASON=True` 라 「연중 어디쯤」만 본다). **곧 시대 변수가 «0» 이다.**
   ⇒ `Z_t` 는 이 판이 처음 받는 **시대 수준 입력**이다.

🔴🔴🔴 **정직한 한계 --- 측정 전에 등기한다**: 위키 pageviews 는 **2015-07-01** 에 시작한다.
   챔피언 **블록 0**(`yr < 2015.010794`)의 덮음은 **0.0000** 이고 블록 1 은 0.9342 다.
   **원점 1 은 학습 전량이 블록 0 이므로 `Z` 가 «상수»(전부 결측)이고 ⇒ 원점 1 에서는
   상호작용이 «원리상» 배울 것이 없다.** ㉯-1 로 등기한다. 이 팔은 **원점 2~4** 를 말한다.

🔴 **무거운 팔**. 조항 75-나 --- `nohup … & disown`.

씀:
    OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 \\
      nohup python3 runners/delta996_zt.py > /tmp/delta996_zt.log 2>&1 & disown
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

OUT_DEFAULT = C.ROOT / "runners" / "out996_zt.json"
PROG = "/tmp/delta996_zt_progress.txt"
FAMC = "FC · 팔 C --- 조각 3 (원점 2→3 · 3→4 · 그리고 2→4) × 처치 1"


def run_cell(dat, doms, ho_blk, tr_blk, origins, seeds, prog, tag, keep=None):
    rho, led, order = collections.OrderedDict(), collections.OrderedDict(), None
    raws = collections.OrderedDict()
    for k in origins:
        tm = MK.train_mask_lt(tr_blk, doms, k)
        acc = collections.OrderedDict()
        for si, s in enumerate(seeds):
            t1 = time.time()
            f, lg = B94.fit(dat, tm, s)
            if si == 0:
                led["원점 %d" % k] = lg
                order = list(getattr(f, "order", []) or [])
            hm = {d: ho_blk[d][4] for d in doms}
            sc, dr = MK.score_gate(dat, f, hm, doms, C.GATE_CANON, spearmanr)
            if keep is not None and si == 0 and k == keep:
                for d in doms:
                    m = np.asarray(hm[d], bool)
                    if int(m.sum()) == 0:
                        continue
                    A_, M_, y_, t_ = dat.slice(d, m)
                    p = np.asarray(f.predict(d, A_, M_, t_), float)
                    ok = np.isfinite(p) & np.isfinite(y_)
                    raws[d] = (p[ok], y_[ok], np.asarray(dat.yr[d], float)[m][ok])
            for d, v in sc.items():
                acc.setdefault(d, []).append(v["rho"])
            prog("%s · 원점 %d · 씨앗 %s 끝 (%.1f 초)"
                 % (tag, k, s, time.time() - t1))
        rho["원점 %d" % k] = collections.OrderedDict(
            [(d, float(np.mean(v))) for d, v in sorted(acc.items())
             if len(v) == len(seeds)])
    return rho, led, order, raws


def head(rho, labels, family, tag):
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
                          C.HOLM_ALPHA, family))])


def delta(a, b, tag):
    com = sorted(set(a) & set(b))
    return collections.OrderedDict([
        ("무엇", tag), ("공통 도메인 수", len(com)),
        ("등가중 평균 앞", C._r(float(np.mean([a[d] for d in com]))) if com else None),
        ("등가중 평균 뒤", C._r(float(np.mean([b[d] for d in com]))) if com else None),
        ("🔴 Δ(뒤 − 앞)", C.cluster_se({d: b[d] - a[d] for d in com}))])


def stage(out_path, seeds=C.SEEDS, cells=("Z0", "Z1", "Z2", "Z2b", "Z3")):
    t0 = C.now_utc()
    cs0 = C.code_stamp()
    wall = time.time()
    prog = C.prog_writer(PROG)
    prog("팔 C 시작 · 스레드 %s" % json.dumps(C.THREADS))
    out = collections.OrderedDict()
    out["무엇"] = ("996 팔 C --- 🔴 전 기간 Z_t(위키 전체 집계)를 A×Z_t 로 넣으면 틈이 닫히나. "
                 "위약 둘과 «양성 대조»(배선이 닿나)를 같이 돌린다.")
    out["🔴 축"] = "C1 상태→예측 · C3 원천을 넣는 게 나은가"
    out["사전등록"] = "docs/prereg_996_information_field.md §4 · §5 · §6"
    out["🔴 고정한 스레드"] = C.THREADS
    out["🔴 등록된 자"] = collections.OrderedDict([
        ("군집 SE", "score994.py:98 cluster_se · B=%d · RandomState(%d)"
         % (C.B_DOM, C.DOM_SEED)),
        ("부호뒤집기", "2^d 전수"), ("다중비교", "Holm · 가족 FC")])

    d0, doms = B94.load()
    info, tr_blk, ho_blk, edges = MK.blocks_fixed(d0, doms, C.QS, C.NBLOCK)
    zs = C.zseries()
    out["§Z0-가 시간 블록"] = info
    out["§Z0-나 🔴🔴 Z_t 원천 · 블록 상수 · 덮음 장부"] = collections.OrderedDict([
        ("원천", zs[0]),
        ("블록 상수 Z", C.block_const_table(edges, zs[2], zs[3], zs[4], zs[5])),
        ("🔴 덮음 장부(유보 블록 기준)", C.zcov_ledger(d0, doms, ho_blk, zs)),
        ("🔴 덮음 장부(학습 블록 기준)", C.zcov_ledger(d0, doms, tr_blk, zs)),
        ("🔴🔴 ㉯-1", "블록 0 덮음이 0 이므로 «원점 1» 에서는 Z 가 상수(전부 결측)다. "
                   "상호작용이 원리상 배울 것이 없다 --- 이 팔은 원점 2~4 를 말한다.")])

    labels = ["원점 %d" % k for k in C.ORIGINS]
    dats = collections.OrderedDict()
    dats["Z1"] = (d0, C.ORIGINS, "기준선 --- 덧열 «없음»")
    for nm, mode, ors, tag in (
            ("Z0", "양성대조", (4,), "🔴 양성 대조 --- 라벨 순위를 «일부러» 흘린다. "
                              "안 오르면 배선이 «안 닿는» 것이고 이 팔은 미측정이다"),
            ("Z2", "주효과행", C.ORIGINS, "위약 ㉡ --- Z 주효과만(행별). "
                                       "상호작용이 «이겨야» 하는 대조"),
            ("Z2b", "주효과블록", (4,), "위약 ㉠ --- Z 주효과만(블록 상수)"),
            ("Z3", "상호작용", C.ORIGINS, "🔴 처치 --- Z 주효과 + A_j × Z 다섯")):
        cols = C.zcols(d0, doms, mode, edges, zs)
        dats[nm] = (C.augment(d0, cols), ors, tag)

    res, wires = collections.OrderedDict(), collections.OrderedDict()
    for nm in ("Z1", "Z0", "Z2", "Z2b", "Z3"):
        if nm not in cells:
            continue
        dat, ors, tag = dats[nm]
        keep = 4 if nm == "Z1" else None
        rho, led, order, raws = run_cell(dat, doms, ho_blk, tr_blk, ors, seeds,
                                         prog, nm, keep)
        res[nm] = collections.OrderedDict([
            ("무엇", tag), ("원점", list(ors)),
            ("도메인별 ρ(씨앗 평균)",
             {k: {d: C._r(x) for d, x in v.items()} for k, v in rho.items()}),
            ("등가중 판 ρ", {k: C._r(float(np.mean(list(v.values()))))
                         for k, v in rho.items()}),
            ("학습 장부(씨앗 0)", led)])
        #: 🔴🔴 **hole888 검사** --- 넣은 열이 설계행렬에 «정말» 닿았나
        newc = [c for c in (order or []) if c.startswith("Z_") or
                c.startswith("ZX_") or c.startswith("Y_")]
        wires[nm] = collections.OrderedDict([
            ("분모: axis_order 길이", len(order or [])),
            ("🔴 새 열이 axis_order 에 들어갔나", newc),
            ("🔴 새 열 수", len(newc))])
        res[nm]["_rho"] = rho
        if nm == "Z1":
            res[nm]["_raws"] = raws
    out["§Z1 칸별 결과"] = collections.OrderedDict(
        [(k, {kk: vv for kk, vv in v.items() if not kk.startswith("_")})
         for k, v in res.items()])
    out["§Z1-나 🔴🔴 배선 검사(hole888) --- 넣은 열이 axis_order 에 닿았나"] = wires

    # ── §Z2 🔴 양성 대조 관문 ────────────────────────────────
    if "Z0" in res and "Z1" in res:
        a = res["Z1"]["_rho"]["원점 4"]
        b = res["Z0"]["_rho"]["원점 4"]
        dd = delta(a, b, "양성 대조 − 기준선(원점 4)")
        out["§Z2 🔴🔴🔴 양성 대조 관문 --- 「배선이 닿나」"] = collections.OrderedDict([
            ("🔴 무엇", "라벨 순위 열을 «일부러» 넣었다. 이게 ρ 를 크게 «안» 올리면 "
                      "우리가 넣은 열이 설계행렬에 안 닿은 것이고(노트 887·888 의 병) "
                      "🔴 **팔 C 의 모든 「효과 없음」은 「미측정」이다.**"),
            ("Δ", dd),
            ("🔴 통과: 반증조건 C1 (Δ > +0.10 이고 동부호 ≥ 10/12)",
             bool((dd["🔴 Δ(뒤 − 앞)"].get("점추정") or 0) > 0.10
                  and (dd["🔴 Δ(뒤 − 앞)"].get("동부호 분자") or 0) >= 10))])

    # ── §Z3 🔴 구조 항등식 (고정 모형 + 블록 상수) ─────────────
    raws = res.get("Z1", {}).get("_raws") or {}
    zv = {}
    for d in doms:
        v, m = C.z_block(np.asarray(d0.yr[d], float), edges, zs[2], zs[3],
                         zs[4], zs[5])
        zv[d] = (v, m)
    idn, ctl = collections.OrderedDict(), collections.OrderedDict()
    for d, (p, y, yr) in raws.items():
        if len(y) < C.GATE_CANON:
            continue
        r0 = float(spearmanr(p, y)[0])
        r1 = float(spearmanr(p + 0.3, y)[0])            # 블록 안 «상수»
        r2 = float(spearmanr(p + 0.3 * (yr - yr.mean()), y)[0])   # 행별로 «변한다»
        idn[d] = C._r(r1 - r0, 15)
        ctl[d] = C._r(r2 - r0, 12)
    out["§Z3 🔴🔴 구조 항등식 --- 「블록 안 상수는 원리상 ρ 에 못 닿는다」"] = \
        collections.OrderedDict([
            ("🔴 무엇", "고정된 챔피언 모형의 예측에 «블록 안 상수»를 더한다. "
                      "ρ 는 순위만 보므로 «항등식»이다(조항 78 ㉮). "
                      "🔴 이건 「위약 팔」과 다르다 --- 위약은 «다시 적합»하므로 "
                      "다른 열의 계수가 같이 바뀌어 항등식이 «아니다»."),
            ("도메인별 Δρ(상수를 더했다)", idn),
            ("최대 |Δρ|", C._r(max([abs(v) for v in idn.values()] or [0]), 15)),
            ("🔴 통과: 반증조건 C2 (전부 1e-12 안)",
             bool(idn and max(abs(v) for v in idn.values()) <= 1e-12)),
            ("🔴🔴 대조판 --- 행별로 «변하는» 값을 더하면 «떨어져야» 한다",
             collections.OrderedDict([
                 ("도메인별 Δρ", ctl),
                 ("최대 |Δρ|", C._r(max([abs(v) for v in ctl.values()] or [0]), 12)),
                 ("🔴 통과: 반증조건 C3 (한 도메인이라도 1e-12 를 넘는다)",
                  bool(ctl and max(abs(v) for v in ctl.values()) > 1e-12))]))])

    # ── §Z4 🔴🔴🔴 헤드라인 — 상호작용이 위약을 이기나 · 틈이 닫히나 ──
    hl = collections.OrderedDict()
    for nm in ("Z1", "Z2", "Z3"):
        if nm in res:
            hl[nm] = head(res[nm]["_rho"], labels, FAMC + " (%s)" % nm,
                          res[nm]["무엇"])
    cmp_ = collections.OrderedDict()
    for k in labels:
        row = collections.OrderedDict()
        if "Z2" in res and "Z1" in res:
            row["위약 − 기준선"] = delta(res["Z1"]["_rho"][k], res["Z2"]["_rho"][k],
                                   "Z 주효과만(행별)")
        if "Z3" in res and "Z1" in res:
            row["🔴 처치 − 기준선"] = delta(res["Z1"]["_rho"][k], res["Z3"]["_rho"][k],
                                     "A×Z 상호작용")
        if "Z3" in res and "Z2" in res:
            row["🔴🔴 처치 − 위약"] = delta(res["Z2"]["_rho"][k], res["Z3"]["_rho"][k],
                                     "상호작용이 주효과를 «이기나»")
        cmp_[k] = row
    if "Z2b" in res and "Z1" in res:
        cmp_["원점 4 · 위약 ㉠(블록 상수 주효과)"] = collections.OrderedDict([
            ("위약 ㉠ − 기준선", delta(res["Z1"]["_rho"]["원점 4"],
                                  res["Z2b"]["_rho"]["원점 4"],
                                  "블록 상수 Z 주효과 «재적합»"))])
    gapc = collections.OrderedDict()
    for nm in ("Z1", "Z2", "Z3"):
        if nm in hl:
            gapc[nm] = collections.OrderedDict([
                ("합 1→4(항등)", hl[nm]["조각"].get("원점 1→원점 4", {}).get("점추정")),
                ("🔴 2→4 (Z 가 덮는 구간만)",
                 C._r((res[nm]["_rho"]["원점 4"] and
                       float(np.mean([res[nm]["_rho"]["원점 4"][d]
                                      - res[nm]["_rho"]["원점 2"][d]
                                      for d in sorted(set(res[nm]["_rho"]["원점 4"])
                                                      & set(res[nm]["_rho"]["원점 2"]))])))))])
    #: 🔴🔴🔴 **틈이 닫히는 데는 «두 길»이 있다** --- 설계 팔이 연기 시험에서 봤다(사전등록 §4-다).
    #:   ① 먼 원점이 «올라간다»(우리가 찾는 것) ② 가까운 원점이 «내려간다»(닫힌 게 아니라 망가진 것).
    #:   **갈라서 채점한다.**
    ways = collections.OrderedDict()
    if "Z3" in res and "Z1" in res:
        for k in ("원점 2", "원점 3", "원점 4"):
            com = sorted(set(res["Z3"]["_rho"][k]) & set(res["Z1"]["_rho"][k]))
            dd = {d: res["Z3"]["_rho"][k][d] - res["Z1"]["_rho"][k][d] for d in com}
            ways[k] = collections.OrderedDict([
                ("Δ(처치 − 기준선)", C._r(float(np.mean(list(dd.values()))))),
                ("올랐나", bool(float(np.mean(list(dd.values()))) > 0))])
        up2 = ways.get("원점 2", {}).get("올랐나")
        dn4 = ways.get("원점 4", {}).get("올랐나")
        ways["🔴🔴 판정"] = collections.OrderedDict([
            ("🔴 「틈이 닫혔다」로 세려면 «먼 원점(2)이 올라야» 한다", bool(up2)),
            ("🔴 가까운 원점(4)이 «내려가서» 닫힌 것이면 «안» 센다",
             bool(dn4 is False)),
            ("🔴 그래서 이 팔이 「닫았다」를 낼 수 있나", bool(up2))])
    out["§Z4 🔴🔴🔴 헤드라인"] = collections.OrderedDict([
        ("🔴🔴🔴 틈이 닫히는 «두 길» --- 갈라서 센다", ways),
        ("칸별 조각 분해", hl), ("칸 사이 Δ", cmp_),
        ("🔴 틈(원점 1→4 · 2→4)이 칸마다 얼마나 되나", gapc),
        ("🔴🔴 분모 주의",
         "이 팔은 «분자»만 낸다. 몫의 최종 분모는 팔 0 의 «잔여 낙차»이고 "
         "그 나눗셈은 정비 팔이 채점에서 한다(조항 74-3 · 티처 #134)."),
        ("🔴 참고 분모 0.183381 은 학습 행 수 몫(≈29 %)이 «섞인» 분모다", C.GAP995)])

    # ── §Z5 조항 78 ─────────────────────────────────────────
    base = {}
    if "Z3" in res and "Z2" in res:
        for k in labels:
            com = sorted(set(res["Z3"]["_rho"][k]) & set(res["Z2"]["_rho"][k]))
            base["처치−위약 · %s" % k] = {d: res["Z3"]["_rho"][k][d]
                                       - res["Z2"]["_rho"][k][d] for d in com}
    if base:
        variants = C.variant_grid(base, 996)
        claims = [("%s 가 2·SE 를 넘는다" % k,
                   (lambda kk: lambda st: bool(C.cluster_se(st[kk])
                                               .get("🔴🔴 2·SE 를 넘나")))(k))
                  for k in base]
        controls = [
            ("🔴 대조 ㉮(자료 파생): 도메인 수가 12 이하다",
             lambda st: all(len(v) <= 12 for v in st.values())),
            ("🔴 대조 ㉯(자료 파생): 도메인 수가 13 이상이다",
             lambda st: any(len(v) >= 13 for v in st.values()))]
        out["§Z5 🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"] = C.taut_scan(
            claims, variants, "팔 C 의 주장 %d 개 × 변이체 %d 개"
            % (len(claims), len(variants)), controls)

    out["🔴🔴 조항 79 개정 2 --- 이 주행이 낸 cluster_se 칸 전량"] = C.cse_ledger()
    out["🔴🔴 조항 78 개정 4 --- 반증조건의 «분모»를 손으로 고르지 않았다"] = \
        collections.OrderedDict([
            ("🔴 왜", "995 팔 C 는 반증조건 여덟 중 넷만 검사하고 「㉮ 0/4」를 냈다 --- "
                    "뺀 넷 중 셋이 ㉮ 였다(티처 #134). 그래서 분모를 «이름으로» 신고한다."),
            ("분모: 이 팔이 지는 반증조건", 7),
            ("이름", ['F6 구조 항등식 = 0 · 대조판 ≠ 0', 'F7 양성 대조 관문', 'F8 hole888 배선', 'F9 Z 덮음 블록 0 = 0', 'F16 원점 1 처치−기준선 = 0', 'F12 조항 78 대조 계수', 'F13 도장 시작=끝']),
            ("🔴 산출물 키로 «기계가» 확인하는 것", ['F6', 'F7', 'F8', 'F9', 'F16', 'F12', 'F13'])])
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
    ap.add_argument("--cells", default="Z0,Z1,Z2,Z2b,Z3")
    a = ap.parse_args()
    stage(a.out, C.SEEDS[:a.seeds], tuple(x.strip() for x in a.cells.split(",")))


if __name__ == "__main__":
    main()
