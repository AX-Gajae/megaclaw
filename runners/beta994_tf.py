# -*- coding: utf-8 -*-
"""994 **본편** — 🔴🔴🔴 **챔피언 판 ρ 를 「시간 방향 유보」(원점 넷)에서 다시 잰다.**

사전등록 `docs/prereg_994_time_holdout_board.md` §2 를 그대로 따른다.

🔴 **무엇이 새로운가.** 챔피언 정본 `0.470343` 은 **원점이 하나**(`T = 2025.0`)다.
    학습 `yr < 2025`(19,018 행) · 유보 `yr >= 2025`(3,775 행 · 12 도메인).
    이미 시간 방향이지만 **원점이 하나라 「그 해의 성질인지」를 원리상 못 가른다.**
    이 러너는 원점을 **넷**으로 늘린다 --- 블록 `< k` 로 적합하고 블록 `k` 로 채점한다.

🔴🔴 **조항 60 --- 원점을 옮기면 분모가 같이 움직인다.** 챔피언 자료에서
    `영화`·`팝업`은 2024.477 이전에 0 행이고 `애니`는 블록 0 에 0 행이다.
    그래서 이 러너는 헤드라인을 **둘** 낸다:
      ㉠ **움직이는 분모** --- 원점마다 게이트를 통과한 도메인 전부(행 가중 통합)
      ㉡ **고정 분모** --- 원점 넷 «전부»에서 채점된 도메인만(공통 도메인)
    🔴 **둘을 한 문장에 이어 붙이지 않는다.**

씀:
    python3 runners/beta994_tf.py --out runners/out994_tf.json
"""
import argparse
import collections
import sys
import time

import numpy as np

import beta994_common as C                                   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.ROOT / "runners/out994_tf.json"))
    a = ap.parse_args()

    t0, cs0, wall = C.now_utc(), C.code_stamp(), time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("994 §2 --- 🔴🔴🔴 **챔피언 판 ρ 를 시간 방향 유보(원점 넷)에서 잰다.** "
                 "정본 0.470343 은 원점 «하나»(2025)의 값이다")
    out["🔴 축"] = "C1 상태→예측"
    out["사전등록"] = "docs/prereg_994_time_holdout_board.md §2"
    out["🔴 배선"] = ("ff753.base()+shell() · F18_bagboost · "
                   "lab.harness.evaluate deploy 갈래 복사 · scipy spearmanr(동률 평균)")
    out["🔴 씨앗"] = list(C.SEEDS)

    C.say("자료를 연다")
    d0, doms = C.load()
    out["🔴 도메인(전량)"] = list(doms)
    btab, blk, edges = C.blocks(d0, doms)
    out["🔴🔴 시간 블록"] = btab
    out["🔴🔴 원점"] = list(C.ORIGINS)

    # ── §2-1 배선 W --- 🔴 «떨어질 수 있는» 검사인가 ──────────────────────
    hmask = {k: {d: blk[d][k] for d in doms} for k in C.ORIGINS}
    tmask = {k: C.train_mask_lt(blk, doms, k) for k in C.ORIGINS}
    w_ok, w_leak, rows = [], [], collections.OrderedDict()
    for k in C.ORIGINS:
        tr_yr = np.concatenate([np.asarray(d0.yr[d], float)[tmask[k][d]]
                                for d in doms if int(tmask[k][d].sum())])
        ho_yr = np.concatenate([np.asarray(d0.yr[d], float)[hmask[k][d]]
                                for d in doms if int(hmask[k][d].sum())])
        #: 🔴 «일부러» 미래를 흘린 변이체 --- 학습에 블록 `k` 까지 넣는다
        lk = {d: np.logical_or(tmask[k][d], hmask[k][d]) for d in doms}
        lk_yr = np.concatenate([np.asarray(d0.yr[d], float)[lk[d]]
                                for d in doms if int(lk[d].sum())])
        w_ok.append(bool(tr_yr.max() < ho_yr.min()))
        w_leak.append(bool(lk_yr.max() < ho_yr.min()))
        rows["원점 %d" % k] = collections.OrderedDict([
            ("학습 최대 yr", float(tr_yr.max())), ("유보 최소 yr", float(ho_yr.min())),
            ("학습 행(라벨)", int(len(tr_yr))), ("유보 행(라벨)", int(len(ho_yr))),
            ("🔴 앞인가", bool(tr_yr.max() < ho_yr.min())),
            ("🔴🔴 미래를 흘린 변이체에서도 앞인가", bool(lk_yr.max() < ho_yr.min())),
        ])
    out["W1 🔴🔴 학습이 언제나 유보보다 앞인가"] = collections.OrderedDict([
        ("원점별", rows),
        ("🔴 정본 배선에서 원점 넷 전부 참인가", bool(all(w_ok))),
        ("🔴🔴 미래를 흘린 변이체에서 «거짓»인가", bool(not any(w_leak))),
        ("🔴 이 검사가 떨어질 수 있나(구성상 참이 아닌가)",
         bool(all(w_ok) and not any(w_leak))),
        ("통과", bool(all(w_ok) and not any(w_leak))),
    ])

    # ── §2-2 게이트(씨앗과 무관한 분모) ─────────────────────────────────
    #: 🔴🔴 **하네스 규칙을 글자 그대로 쓴다** --- `lab/harness.py:321` 의 `evaluate` 는
    #: **유보 행 ≥ 20 이기만 하면** 그 도메인을 채점한다. **학습에 그 도메인이 있었는지는
    #: «안 묻는다».** `Data.weights` 도 마찬가지다. 그래서 게이트도 그렇게 건다.
    #: 🔴 그 대신 **「학습에 있었나」를 도메인마다 «따로» 적고**, 학습된 도메인만 모은
    #: 헤드라인 ㉢ 을 «같이» 낸다(조항 66 --- 문턱을 숨기지 말고 «인자»로 낸다).
    gate, W, trained = collections.OrderedDict(), collections.OrderedDict(), {}
    for k in C.ORIGINS:
        g, w, trd = [], {}, {}
        for d in doms:
            nho, ntr = int(hmask[k][d].sum()), int(tmask[k][d].sum())
            if nho >= C.MIN_SCORE:
                g.append(d)
                w[d] = nho
                trd[d] = bool(ntr >= C.MIN_TRAIN)
        gate[k], W[k], trained[k] = g, w, trd
    out["🔴🔴 원점별 게이트(분모)"] = collections.OrderedDict([
        ("원점 %d" % k, collections.OrderedDict([
            ("🔴 게이트 규칙", "유보 행 >= 20 (lab/harness.py::evaluate 와 «같은» 규칙)"),
            ("채점 도메인", list(gate[k])), ("채점 도메인 수", len(gate[k])),
            ("채점 행", int(sum(W[k].values()))),
            ("도메인별 채점 행", collections.OrderedDict(
                [(d, int(W[k][d])) for d in gate[k]])),
            ("🔴🔴 학습에 «있었나»(도메인별)", collections.OrderedDict(
                [(d, trained[k][d]) for d in gate[k]])),
            ("🔴🔴 학습에 «없이» 채점된 도메인",
             [d for d in gate[k] if not trained[k][d]]),
            ("🔴 학습된 도메인만의 채점 행",
             int(sum(W[k][d] for d in gate[k] if trained[k][d]))),
            ("학습 행(≥MIN_TRAIN 도메인 합)",
             int(sum(int(tmask[k][d].sum()) for d in doms
                     if int(tmask[k][d].sum()) >= C.MIN_TRAIN))),
        ])) for k in C.ORIGINS])
    out["🔴🔴🔴 통합 채점 행(원점 넷 합)"] = int(sum(sum(W[k].values())
                                              for k in C.ORIGINS))
    common = [d for d in doms if all(d in gate[k] for k in C.ORIGINS)]
    out["🔴🔴🔴 공통 도메인(원점 넷 전부에서 채점된 것 · 고정 분모)"] = \
        collections.OrderedDict([
            ("도메인", list(common)), ("수", len(common)),
            ("채점 행", int(sum(W[k][d] for k in C.ORIGINS for d in common))),
            ("🔴 왜 따로 내나",
             "🔴 조항 60 --- 원점마다 도메인 집합이 달라서 ㉠ 은 «움직이는 분모»다. "
             "㉡ 은 원점 넷에 걸쳐 분모가 «안 움직이는» 헤드라인이다"),
        ])
    out["🔴🔴🔴 학습 없이 채점된 칸(조항 59 --- 「쟀는데 학습엔 없었다」)"] = \
        collections.OrderedDict([
            ("원점 %d" % k, collections.OrderedDict([
                ("도메인", [d for d in gate[k] if not trained[k][d]]),
                ("행", int(sum(W[k][d] for d in gate[k] if not trained[k][d]))),
            ])) for k in C.ORIGINS] + [
            ("🔴 무슨 뜻인가",
             "🔴 하네스는 **학습에 한 번도 안 나온 도메인도 채점한다**(원핫이 0 인 채로 예측). "
             "「없다」도 「결측」도 아니고 **「쟀는데 학습엔 없었다」**는 «넷째» 경우다. "
             "🔴 헤드라인 ㉢ 이 이 칸들을 «뺀» 판이다"),
        ])

    # ── §2-3 🔴🔴🔴 본 측정 ──────────────────────────────────────────
    per = {k: {d: [] for d in gate[k]} for k in C.ORIGINS}
    okn = {k: {d: [] for d in gate[k]} for k in C.ORIGINS}
    pool_k = {k: [] for k in C.ORIGINS}
    pool_k3 = {k: [] for k in C.ORIGINS}
    head_move, head_fix, head_trn = [], [], []
    drops = collections.OrderedDict()
    trled = collections.OrderedDict()
    missed = collections.OrderedDict()
    for s in C.SEEDS:
        num_m = den_m = num_f = den_f = num_t = den_t = 0.0
        for k in C.ORIGINS:
            C.say("씨앗 %d · 원점 %d --- 적합 (%.0fs)" % (s, k, time.time() - wall))
            f, tl = C.fit(d0, tmask[k], s)
            if s == C.SEEDS[0]:
                trled["원점 %d" % k] = tl
            sc, dr = C.score(d0, f, hmask[k], doms)
            if s == C.SEEDS[0]:
                drops["원점 %d" % k] = C.drop_ledger(dr, doms)
            n1 = n2 = n3 = n4 = 0.0
            for d in gate[k]:
                if d not in sc:
                    missed.setdefault("씨앗 %d · 원점 %d" % (s, k), []).append(
                        {d: dr.get(d, "게이트는 통과했는데 채점이 안 나왔다")})
                    continue
                per[k][d].append(sc[d]["rho"])
                okn[k][d].append(sc[d]["n"])
                n1 += sc[d]["rho"] * W[k][d]
                n2 += W[k][d]
                num_m += sc[d]["rho"] * W[k][d]
                den_m += W[k][d]
                if d in common:
                    num_f += sc[d]["rho"] * W[k][d]
                    den_f += W[k][d]
                if trained[k][d]:
                    n3 += sc[d]["rho"] * W[k][d]
                    n4 += W[k][d]
                    num_t += sc[d]["rho"] * W[k][d]
                    den_t += W[k][d]
            pool_k[k].append(n1 / n2 if n2 else float("nan"))
            pool_k3[k].append(n3 / n4 if n4 else float("nan"))
        head_move.append(num_m / den_m if den_m else float("nan"))
        head_fix.append(num_f / den_f if den_f else float("nan"))
        head_trn.append(num_t / den_t if den_t else float("nan"))
        C.say("씨앗 %d --- ㉠ %.6f · ㉡ %.6f · ㉢ %.6f (%.0fs)"
              % (s, head_move[-1], head_fix[-1], head_trn[-1],
                 time.time() - wall))

    # ── §2-4 집계 ───────────────────────────────────────────────────
    rho_m = {k: {d: float(np.mean(per[k][d])) for d in gate[k] if per[k][d]}
             for k in C.ORIGINS}
    out["🔴🔴🔴 헤드라인 ㉠ 움직이는 분모(원점 넷 · 행 가중 통합)"] = \
        collections.OrderedDict([
            ("🔴 씨앗별", [float(v) for v in head_move]),
            ("🔴🔴🔴 rho", C.seed_se(head_move)),
            ("🔴 채점 행(분모)", int(sum(sum(W[k].values()) for k in C.ORIGINS))),
            ("🔴 도메인·원점 칸 수", int(sum(len(gate[k]) for k in C.ORIGINS))),
            ("🔴🔴 도메인 군집 SE(원점을 합친 도메인 가중으로)",
             C.dom_cluster_se(
                 {d: float(np.mean([rho_m[k][d] for k in C.ORIGINS if d in rho_m[k]]))
                  for d in doms if any(d in rho_m[k] for k in C.ORIGINS)},
                 {d: int(sum(W[k].get(d, 0) for k in C.ORIGINS))
                  for d in doms if any(d in rho_m[k] for k in C.ORIGINS)})),
        ])
    out["🔴🔴🔴 헤드라인 ㉡ 고정 분모(공통 도메인만)"] = collections.OrderedDict([
        ("🔴 씨앗별", [float(v) for v in head_fix]),
        ("🔴🔴🔴 rho", C.seed_se(head_fix)),
        ("🔴 도메인", list(common)),
        ("🔴 채점 행(분모)", int(sum(W[k][d] for k in C.ORIGINS for d in common))),
        ("🔴🔴 도메인 군집 SE",
         C.dom_cluster_se(
             {d: float(np.mean([rho_m[k][d] for k in C.ORIGINS if d in rho_m[k]]))
              for d in common},
             {d: int(sum(W[k].get(d, 0) for k in C.ORIGINS)) for d in common})),
    ])
    out["🔴🔴🔴 헤드라인 ㉢ 학습된 도메인만(하네스 규칙 ∧ 학습 >= MIN_TRAIN)"] = \
        collections.OrderedDict([
            ("🔴 씨앗별", [float(v) for v in head_trn]),
            ("🔴🔴🔴 rho", C.seed_se(head_trn)),
            ("🔴 채점 행(분모)",
             int(sum(W[k][d] for k in C.ORIGINS for d in gate[k] if trained[k][d]))),
            ("🔴 원점별 채점 도메인 수",
             [len([d for d in gate[k] if trained[k][d]]) for k in C.ORIGINS]),
            ("🔴 왜 따로 내나",
             "🔴 하네스는 학습에 없던 도메인도 채점한다. ㉢ 은 그 칸을 «뺀» 판이다 --- "
             "문턱을 숨기는 대신 «둘 다» 싣는다(조항 66)"),
        ])
    out["🔴🔴 원점별 rho"] = collections.OrderedDict([
        ("원점 %d" % k, collections.OrderedDict([
            ("🔴 씨앗별", [float(v) for v in pool_k[k]]),
            ("🔴🔴 rho", C.seed_se(pool_k[k])),
            ("🔴 rho ㉢ 학습된 도메인만", C.seed_se(pool_k3[k])),
            ("채점 도메인 수", len(gate[k])),
            ("학습된 채점 도메인 수", len([d for d in gate[k] if trained[k][d]])),
            ("채점 행", int(sum(W[k].values()))),
            ("학습 행", int(sum(int(tmask[k][d].sum()) for d in doms
                             if int(tmask[k][d].sum()) >= C.MIN_TRAIN))),
            ("🔴 도메인 군집 SE", C.dom_cluster_se(rho_m[k], W[k])),
        ])) for k in C.ORIGINS])

    dec = collections.OrderedDict()
    for d in doms:
        cells = collections.OrderedDict()
        for k in C.ORIGINS:
            if d in rho_m.get(k, {}):
                cells["원점 %d" % k] = collections.OrderedDict([
                    ("rho(씨앗 평균)", float(rho_m[k][d])),
                    ("rho SD(씨앗)", float(np.std(per[k][d], ddof=1))
                     if len(per[k][d]) > 1 else None),
                    ("채점 행", int(W[k][d])),
                    ("🔴 학습에 있었나", bool(trained[k][d])),
                    ("학습 행", int(tmask[k][d].sum())),
                    ("🔴 채점 ok 행이 씨앗마다 같은가",
                     bool(len(set(okn[k][d])) <= 1)),
                    ("ok 행 가짓수", sorted(set(int(x) for x in okn[k][d]))),
                ])
            else:
                cells["원점 %d" % k] = collections.OrderedDict([
                    ("rho(씨앗 평균)", None),
                    ("🔴 왜 없나", drops.get("원점 %d" % k, {}).get(
                        "도메인별", {}).get(d, "게이트 밖")),
                    ("블록 행", int(blk[d][k].sum())),
                ])
        dec[d] = collections.OrderedDict([
            ("원점별", cells),
            ("🔴 원점 넷 전부에서 채점됐나", bool(d in common)),
            ("총 채점 행", int(sum(W[k].get(d, 0) for k in C.ORIGINS))),
        ])
    out["🔴🔴 도메인별 분해(12)"] = dec
    out["🔴 조항 59 버림 장부(씨앗 0)"] = drops
    out["🔴 학습 장부(씨앗 0)"] = trled
    out["🔴🔴 게이트는 통과했는데 채점이 안 나온 칸"] = collections.OrderedDict([
        ("칸 수", int(sum(len(v) for v in missed.values()))), ("상세", missed)])

    # ── §2-5 정본과 견줌 --- 🔴 «분모가 다르다»를 같이 적는다 ─────────────
    out["🔴🔴🔴 정본과의 견줌"] = collections.OrderedDict([
        ("정본 판 rho(전정밀 · text680.BOARD_RHO / out898_board.json)",
         C.BOARD_RHO_FULL),
        ("정본 분모", {"도메인": C.BOARD_NDOM, "유보 행": C.BOARD_W_SUM,
                   "원점": "하나 (yr = 2025.0)", "학습 행": "약 19,018"}),
        ("이 러너 분모 ㉠", {"도메인·원점 칸": int(sum(len(gate[k]) for k in C.ORIGINS)),
                       "채점 행": int(sum(sum(W[k].values()) for k in C.ORIGINS)),
                       "원점": list(C.ORIGINS)}),
        ("이 러너 분모 ㉡", {"도메인": len(common),
                       "채점 행": int(sum(W[k][d] for k in C.ORIGINS
                                       for d in common))}),
        ("이 러너 분모 ㉢", {"채점 행": int(sum(W[k][d] for k in C.ORIGINS
                                        for d in gate[k] if trained[k][d]))}),
        ("Δ ㉠ − 정본", float(np.mean(head_move)) - C.BOARD_RHO_FULL),
        ("Δ ㉡ − 정본", float(np.mean(head_fix)) - C.BOARD_RHO_FULL),
        ("Δ ㉢ − 정본", float(np.mean(head_trn)) - C.BOARD_RHO_FULL),
        ("🔴🔴 조항 60 경고",
         "🔴 **분모가 셋 다 다르다.** 이 Δ 는 「예측이 더 어렵다」의 크기가 «아니다» --- "
         "도메인 혼합·표본 크기·학습량이 같이 움직였다. **가르는 것은 `beta994_ctl.py` 다.** "
         "이 러너는 그 분해를 «안 한다»"),
        ("🔴 정본 값을 이 러너가 고쳤나", False),
    ])

    out["🔴 도장"] = C.stamp(t0, cs0, C.data_fp(d0, doms))
    out["초"] = round(time.time() - wall, 1)
    out["통과"] = bool(out["W1 🔴🔴 학습이 언제나 유보보다 앞인가"]["통과"]
                     and all(np.isfinite(head_move))
                     and out["🔴 도장"]["🔴 시작=끝"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **원점 넷 전부에서 학습이 유보보다 앞이고(일부러 미래를 흘리면 그 검사가 떨어진다), "
        "씨앗 열둘이 전부 유한한 판 ρ 를 냈고, 주행 중 소스가 안 바뀌었다.** "
        "🔴 «값이 좋은가»는 `통과` 가 아니다 --- 어느 쪽이 나오든 그대로 싣는다")
    C.write(a.out, out)
    print(__import__("json").dumps(
        {"out": a.out, "통과": out["통과"],
         "㉠": out["🔴🔴🔴 헤드라인 ㉠ 움직이는 분모(원점 넷 · 행 가중 통합)"]["🔴🔴🔴 rho"]["평균"],
         "㉡": out["🔴🔴🔴 헤드라인 ㉡ 고정 분모(공통 도메인만)"]["🔴🔴🔴 rho"]["평균"],
         "㉢": out["🔴🔴🔴 헤드라인 ㉢ 학습된 도메인만(하네스 규칙 ∧ 학습 >= MIN_TRAIN)"]["🔴🔴🔴 rho"]["평균"]},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
