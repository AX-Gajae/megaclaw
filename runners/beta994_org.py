# -*- coding: utf-8 -*-
"""994 **외삽 거리 팔** — 🔴 **멀리 볼수록 판 ρ 가 어떻게 되나.**

사전등록 `docs/prereg_994_time_holdout_board.md` §3.

🔴 **본편(`beta994_tf.py`)과 「다른 물음」이다.** 본편은 **원점마다 «바로 다음» 블록**만
채점한다(외삽 거리가 언제나 1 블록). 이 팔은 원점 `k` 로 적합한 «같은 모형»에게
블록 `k, k+1, …, 4` 를 **따로따로** 채점시켜 **거리 `L = j − k + 1` 의 함수로** 본다.
    · 본편이 못 내는 것 --- *"두 블록 앞을 보면 얼마나 떨어지나"*
    · 이 팔이 내는 대각선(`L = 1`)은 본편의 원점별 ρ 와 **같아야 한다**
      → 🔴 두 러너가 서로를 «안 읽고» 독립 실행하므로 그 일치가 **교차 검사**다(`F07`).

🔴🔴 **조항 60.** 칸마다 게이트를 통과한 도메인이 다르다. 그래서 헤드라인은
    **원점 1 · 공통 도메인만 · 거리 1~4** 로 «분모를 고정해» 낸다. 열 칸 전량표는 병기다.

씀:
    python3 runners/beta994_org.py --out runners/out994_org.json
"""
import argparse
import collections
import json
import sys
import time

import numpy as np

import beta994_common as C                                   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.ROOT / "runners/out994_org.json"))
    a = ap.parse_args()

    t0, cs0, wall = C.now_utc(), C.code_stamp(), time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("994 §3 --- 🔴 **외삽 거리**. 원점 k 로 적합한 같은 모형이 "
                 "블록 k, k+1, …, 4 를 «따로» 채점한다. 거리가 멀수록 어떻게 되나")
    out["🔴 축"] = "C1 상태→예측"
    out["사전등록"] = "docs/prereg_994_time_holdout_board.md §3"
    out["🔴 배선"] = ("ff753.base()+shell() · F18_bagboost · "
                   "lab.harness.evaluate deploy 갈래 복사 · scipy spearmanr(동률 평균)")
    out["🔴 씨앗"] = list(C.SEEDS)

    C.say("자료를 연다")
    d0, doms = C.load()
    btab, blk, edges = C.blocks(d0, doms)
    out["🔴🔴 시간 블록"] = btab

    tmask = {k: C.train_mask_lt(blk, doms, k) for k in C.ORIGINS}
    cells = [(k, j) for k in C.ORIGINS for j in range(k, C.NBLOCK)]
    out["🔴🔴 칸(원점, 채점 블록)"] = [[k, j, j - k + 1] for k, j in cells]
    out["🔴 칸 수"] = len(cells)

    # ── §3-1 칸별 게이트(씨앗과 무관한 분모) ─────────────────────────────
    #: 🔴🔴 **하네스 규칙** --- `lab/harness.py::evaluate` 는 «유보 행 >= 20» 이기만 하면
    #: 채점한다. 학습에 그 도메인이 있었는지는 안 묻는다. 본편과 «같은 규칙»을 쓴다.
    gate, W, trained = {}, {}, {}
    for (k, j) in cells:
        g, w, trd = [], {}, {}
        for d in doms:
            nho, ntr = int(blk[d][j].sum()), int(tmask[k][d].sum())
            if nho >= C.MIN_SCORE:
                g.append(d)
                w[d] = nho
                trd[d] = bool(ntr >= C.MIN_TRAIN)
        gate[(k, j)], W[(k, j)], trained[(k, j)] = g, w, trd
    common = [d for d in doms if all(d in gate[c] for c in cells)]
    out["🔴🔴 칸별 게이트"] = collections.OrderedDict([
        ("원점 %d → 블록 %d (거리 %d)" % (k, j, j - k + 1), collections.OrderedDict([
            ("🔴 게이트 규칙", "유보 행 >= 20 (lab/harness.py::evaluate 와 «같은» 규칙)"),
            ("채점 도메인", list(gate[(k, j)])),
            ("채점 도메인 수", len(gate[(k, j)])),
            ("🔴🔴 학습에 «없이» 채점된 도메인",
             [d for d in gate[(k, j)] if not trained[(k, j)][d]]),
            ("🔴 채점 행 n", int(sum(W[(k, j)].values()))),
            ("도메인별 채점 행", collections.OrderedDict(
                [(d, int(W[(k, j)][d])) for d in gate[(k, j)]])),
            ("학습 행", int(sum(int(tmask[k][d].sum()) for d in doms
                             if int(tmask[k][d].sum()) >= C.MIN_TRAIN))),
        ])) for (k, j) in cells])
    out["🔴🔴🔴 공통 도메인(열 칸 «전부»에서 채점된 것 · 고정 분모)"] = \
        collections.OrderedDict([("도메인", list(common)), ("수", len(common))])

    # ── §3-2 🔴 본 측정 --- 원점당 «한 번» 적합하고 블록 여럿을 채점 ────────
    per = {c: {d: [] for d in gate[c]} for c in cells}
    pool_move = {c: [] for c in cells}
    pool_fix = {c: [] for c in cells}
    drops = collections.OrderedDict()
    missed = collections.OrderedDict()
    for s in C.SEEDS:
        for k in C.ORIGINS:
            C.say("씨앗 %d · 원점 %d --- 적합 (%.0fs)" % (s, k, time.time() - wall))
            f, tl = C.fit(d0, tmask[k], s)
            for j in range(k, C.NBLOCK):
                c = (k, j)
                sc, dr = C.score(d0, f, {d: blk[d][j] for d in doms}, doms)
                if s == C.SEEDS[0]:
                    drops["원점 %d → 블록 %d" % (k, j)] = C.drop_ledger(dr, doms)
                n1 = n2 = f1 = f2 = 0.0
                for d in gate[c]:
                    if d not in sc:
                        missed.setdefault("씨앗 %d · 원점 %d → 블록 %d" % (s, k, j),
                                          []).append({d: dr.get(d, "채점이 안 나왔다")})
                        continue
                    per[c][d].append(sc[d]["rho"])
                    n1 += sc[d]["rho"] * W[c][d]
                    n2 += W[c][d]
                    if d in common:
                        f1 += sc[d]["rho"] * W[c][d]
                        f2 += W[c][d]
                pool_move[c].append(n1 / n2 if n2 else float("nan"))
                pool_fix[c].append(f1 / f2 if f2 else float("nan"))
            C.say("씨앗 %d · 원점 %d --- 채점 끝 (%.0fs)" % (s, k, time.time() - wall))

    rho_m = {c: {d: float(np.mean(per[c][d])) for d in gate[c] if per[c][d]}
             for c in cells}
    out["🔴🔴 칸별 rho"] = collections.OrderedDict([
        ("원점 %d → 블록 %d (거리 %d)" % (k, j, j - k + 1), collections.OrderedDict([
            ("🔴 거리 L", j - k + 1),
            ("🔴🔴 rho ㉠ 움직이는 분모", C.seed_se(pool_move[(k, j)])),
            ("🔴🔴 rho ㉡ 고정 분모(공통 도메인)", C.seed_se(pool_fix[(k, j)])),
            ("🔴 채점 행 n(㉠)", int(sum(W[(k, j)].values()))),
            ("🔴 채점 행 n(㉡)", int(sum(W[(k, j)][d] for d in common))),
            ("채점 도메인 수(㉠)", len(gate[(k, j)])),
            ("🔴 도메인 군집 SE(㉠)", C.dom_cluster_se(rho_m[(k, j)], W[(k, j)])),
            ("도메인별 rho(씨앗 평균)", collections.OrderedDict(
                [(d, float(rho_m[(k, j)][d])) for d in sorted(rho_m[(k, j)])])),
        ])) for (k, j) in cells])

    # ── §3-3 🔴🔴🔴 헤드라인 --- 원점 1 · 고정 분모 · 거리 곡선 ─────────────
    head = collections.OrderedDict()
    for j in range(1, C.NBLOCK):
        c = (1, j)
        head["거리 %d (원점 1 → 블록 %d)" % (j, j)] = collections.OrderedDict([
            ("🔴🔴 rho(고정 분모)", C.seed_se(pool_fix[c])),
            ("🔴 채점 행 n", int(sum(W[c][d] for d in common))),
            ("🔴 도메인", list(common)),
        ])
    v1 = float(np.mean(pool_fix[(1, 1)]))
    v4 = float(np.mean(pool_fix[(1, C.NBLOCK - 1)]))
    out["🔴🔴🔴 헤드라인 --- 원점 1 · 공통 도메인 · 거리 1~4"] = collections.OrderedDict([
        ("🔴 왜 원점 1 인가",
         "🔴 거리 넷을 «한 적합»으로 다 볼 수 있는 원점은 1 뿐이다. "
         "그래서 「모형이 달라져서」가 아니라 「거리 때문에」 움직인 것이 된다"),
        ("곡선", head),
        ("🔴🔴 거리 1 − 거리 4", float(v1 - v4)),
        ("🔴🔴 멀수록 떨어지나(거리 1 > 거리 4)", bool(v1 > v4)),
        ("🔴 단조 감소인가",
         bool(all(float(np.mean(pool_fix[(1, j)]))
                  >= float(np.mean(pool_fix[(1, j + 1)]))
                  for j in range(1, C.NBLOCK - 1)))),
    ])

    # ── §3-4 거리별 통합(병기 · 움직이는 분모) ───────────────────────────
    lead = collections.OrderedDict()
    for L in range(1, C.NBLOCK):
        cs = [c for c in cells if c[1] - c[0] + 1 == L]
        vals = []
        for si in range(len(C.SEEDS)):
            n1 = n2 = 0.0
            for c in cs:
                if np.isfinite(pool_move[c][si]):
                    n1 += pool_move[c][si] * sum(W[c].values())
                    n2 += sum(W[c].values())
            vals.append(n1 / n2 if n2 else float("nan"))
        lead["거리 %d" % L] = collections.OrderedDict([
            ("칸", ["원점 %d → 블록 %d" % c for c in cs]),
            ("🔴 rho(행 가중 통합 · 움직이는 분모)", C.seed_se(vals)),
            ("🔴 채점 행 n", int(sum(sum(W[c].values()) for c in cs))),
            ("🔴🔴 조항 60", "🔴 거리마다 «칸도 도메인도» 다르다 --- 이 줄끼리 «이어 붙이지 마라»"),
        ])
    out["🔴 거리별 통합(병기 · 분모가 움직인다)"] = lead

    # ── §3-5 🔴 교차 검사용 대각선 --- 본편이 재는 것과 «같은 칸» ───────────
    out["🔴🔴 F07 교차 검사용 --- 거리 1 대각선(본편의 원점별 rho 와 짝)"] = \
        collections.OrderedDict([
            ("원점 %d" % k, collections.OrderedDict([
                ("rho ㉠ 움직이는 분모", C.seed_se(pool_move[(k, k)])["평균"]),
                ("씨앗별", [float(v) for v in pool_move[(k, k)]]),
                ("채점 행", int(sum(W[(k, k)].values()))),
                ("채점 도메인 수", len(gate[(k, k)])),
            ])) for k in C.ORIGINS])

    out["🔴 조항 59 버림 장부(씨앗 0)"] = drops
    out["🔴🔴 게이트는 통과했는데 채점이 안 나온 칸"] = collections.OrderedDict([
        ("칸 수", int(sum(len(v) for v in missed.values()))), ("상세", missed)])
    out["🔴 정본 값을 이 러너가 고쳤나"] = False
    out["🔴 도장"] = C.stamp(t0, cs0, C.data_fp(d0, doms))
    out["초"] = round(time.time() - wall, 1)
    out["통과"] = bool(all(np.isfinite(pool_fix[(1, j)]).all()
                         for j in range(1, C.NBLOCK))
                     and out["🔴 도장"]["🔴 시작=끝"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **원점 1 의 거리 넷이 씨앗 열둘에서 전부 유한한 ρ 를 냈고 주행 중 소스가 안 바뀌었다.** "
        "🔴 «곡선이 내려가는가»는 `통과` 가 아니다 --- 어느 쪽이 나오든 그대로 싣는다")
    C.write(a.out, out)
    print(json.dumps({"out": a.out, "통과": out["통과"],
                      "거리1": v1, "거리4": v4}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
