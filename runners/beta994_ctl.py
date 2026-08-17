# -*- coding: utf-8 -*-
"""994 **대조 팔** — 🔴🔴🔴 **본편을 반증할 수 있는 팔**(조항 74 · 조항 60).

사전등록 `docs/prereg_994_time_holdout_board.md` §4.

🔴 **까닭.** 본편이 시간 방향에서 «낮은» 수를 내면 곧장 **「예측이 어렵다」**로 읽힌다.
    그런데 원점을 옮기면 **셋이 «동시에» 움직인다**:
        ㉮ **도메인 혼합** --- `영화`·`팝업`은 2024.477 이전에 0 행이고 시간 블록 유보는
           `만화`·`웹툰`·`펀딩`(정본에서 ρ 가 낮은 셋)이 훨씬 무겁다
        ㉯ **표본 크기** --- 유보 행 수가 다르다
        ㉰ **학습량** --- 원점 1 은 학습이 정본의 약 1/4 이다
    **이 팔은 셋을 «따로» 잰다.** 그래야 본편의 Δ 를 「예측 난이도」로 읽는 것이
    **틀렸다고 말할 수 있다.**

🔴 **이 팔은 `out994_tf.json`·`out994_org.json` 을 «읽지 않는다».** 시간 블록 «가중»은
    모형 없이 자료만으로 결정되므로 여기서 **다시 계산한다**(같은 `beta994_common.blocks`).

씀:
    python3 runners/beta994_ctl.py --out runners/out994_ctl.json
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

import beta994_common as C                                   # noqa: E402

#: 🔴 사이클 지시문이 이름을 댄 수 --- 「옛 유보를 1,892 행으로 하향 표본」
N_DOWN = 1892
R_DRAW = 20                       #: 하향 표본 뽑기 수(씨앗마다)
W982 = "runners/out982_wiring.json"
LEDGER_DATA = ("data/ingest/sao941/pairs.jsonl.gz",
               "data/ingest/sao959/pairs.jsonl.gz",
               "data/ingest/sao973_hplt/pairs.jsonl.gz")


def score_keep(d0, f, hmask, doms):
    """C.score 와 «같은 규칙»인데 (예측, 라벨)도 돌려준다 --- 하향 표본이 쓴다."""
    sc, drop, keep = collections.OrderedDict(), collections.OrderedDict(), {}
    for d in doms:
        m = np.asarray(hmask[d], bool)
        if int(m.sum()) == 0:
            drop[d] = C.DROP_ZERO
            continue
        A_, M_, y_, t_ = d0.slice(d, m)
        if len(y_) < C.MIN_SCORE:
            drop[d] = C.DROP_GATE
            continue
        p = np.asarray(f.predict(d, A_, M_, t_), float)
        ok = np.isfinite(p) & np.isfinite(y_)
        if int(ok.sum()) < C.MIN_SCORE:
            drop[d] = C.DROP_PRED
            continue
        rho = float(spearmanr(p[ok], y_[ok])[0])
        if not np.isfinite(rho):
            drop[d] = C.DROP_NAN
            continue
        sc[d] = {"rho": rho, "n": int(ok.sum())}
        keep[d] = (p[ok], y_[ok])
    return sc, drop, keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.ROOT / "runners/out994_ctl.json"))
    a = ap.parse_args()

    t0, cs0, wall = C.now_utc(), C.code_stamp(), time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("994 §4 --- 🔴🔴🔴 **대조.** 본편의 Δ 를 「예측 난이도」로 읽는 것이 "
                 "옳은지 «도메인 혼합 · 표본 크기 · 학습량» 셋으로 갈라 잰다")
    out["🔴 축"] = "C1 상태→예측 (반증 팔)"
    out["사전등록"] = "docs/prereg_994_time_holdout_board.md §4"
    out["🔴 씨앗"] = list(C.SEEDS)

    C.say("자료를 연다")
    d0, doms = C.load()
    btab, blk, edges = C.blocks(d0, doms)
    out["🔴🔴 시간 블록(본편과 같은 규칙으로 «다시» 지었다)"] = btab

    tr_c, ho_c = C.canon_masks(d0, doms)
    Wc = d0.weights(C.T_CANON)
    out["🔴🔴 정본 분모"] = collections.OrderedDict([
        ("도메인", len(Wc)), ("유보 가중 합", int(sum(Wc.values()))),
        ("도메인별 유보", collections.OrderedDict(
            [(d, int(Wc[d])) for d in sorted(Wc)])),
        ("학습 행(≥MIN_TRAIN 도메인 합)",
         int(sum(int(tr_c[d].sum()) for d in doms
                 if int(tr_c[d].sum()) >= C.MIN_TRAIN))),
        ("🔴 사전등록 기대 유보", C.BOARD_W_SUM),
        ("🔴 사전등록 기대 도메인", C.BOARD_NDOM),
        ("🔴 맞나", bool(int(sum(Wc.values())) == C.BOARD_W_SUM
                       and len(Wc) == C.BOARD_NDOM)),
    ])

    # ── §4-0 시간 블록 가중(모형 없이 자료만으로) ─────────────────────────
    #: 🔴🔴 **하네스 규칙** --- 유보 행 >= 20 이면 채점된다(학습 유무는 안 묻는다).
    #: 본편 `beta994_tf.py` 의 ㉠ 과 «같은 게이트»여야 `P6` 의 분모가 맞는다(조항 60).
    tmask = {k: C.train_mask_lt(blk, doms, k) for k in C.ORIGINS}
    gate, gate3 = {}, {}
    for k in C.ORIGINS:
        gate[k] = {d: int(blk[d][k].sum()) for d in doms
                   if int(blk[d][k].sum()) >= C.MIN_SCORE}
        gate3[k] = {d: n for d, n in gate[k].items()
                    if int(tmask[k][d].sum()) >= C.MIN_TRAIN}
    W_tf = collections.OrderedDict()
    for d in doms:
        v = int(sum(gate[k].get(d, 0) for k in C.ORIGINS))
        if v:
            W_tf[d] = v
    common = [d for d in doms if all(d in gate[k] for k in C.ORIGINS)]
    out["🔴🔴 시간 블록 가중(본편 ㉠ 이 쓸 분모 · 여기서 다시 계산했다)"] = \
        collections.OrderedDict([
            ("🔴 게이트 규칙", "유보 행 >= 20 (lab/harness.py::evaluate 와 «같은» 규칙)"),
            ("원점별 채점 도메인 수", [len(gate[k]) for k in C.ORIGINS]),
            ("원점별 채점 행", [int(sum(gate[k].values())) for k in C.ORIGINS]),
            ("통합 채점 행", int(sum(W_tf.values()))),
            ("도메인별 통합 채점 행", W_tf),
            ("공통 도메인", list(common)), ("공통 도메인 수", len(common)),
            ("🔴 ㉢ 학습된 도메인만 --- 원점별 도메인 수",
             [len(gate3[k]) for k in C.ORIGINS]),
            ("🔴 ㉢ 원점별 채점 행", [int(sum(gate3[k].values())) for k in C.ORIGINS]),
            ("🔴 ㉢ 통합 채점 행",
             int(sum(sum(gate3[k].values()) for k in C.ORIGINS))),
            ("🔴🔴 학습 없이 채점되는 칸(원점별 도메인)",
             collections.OrderedDict([("원점 %d" % k,
                                       [d for d in gate[k] if d not in gate3[k]])
                                      for k in C.ORIGINS])),
            ("🔴🔴 정본과 도메인 집합이 같은가",
             bool(sorted(W_tf) == sorted(Wc))),
            ("🔴 정본에만 있는 도메인", [d for d in sorted(Wc) if d not in W_tf]),
            ("🔴 시간 블록에만 있는 도메인", [d for d in sorted(W_tf) if d not in Wc]),
        ])

    # ── §4-1 🔴🔴🔴 C0 재현 관문 --- 정본 챔피언 ────────────────────────
    C.say("C0 --- 정본 챔피언 12 씨앗")
    pool0, per0, keeps = [], collections.OrderedDict(), {}
    drops0 = None
    for s in C.SEEDS:
        f, tl = C.fit(d0, tr_c, s)
        sc, dr, kp = score_keep(d0, f, ho_c, doms)
        if drops0 is None:
            drops0 = C.drop_ledger(dr, doms)
            trled0 = tl
        num = den = 0.0
        for d in sorted(sc):
            if d in Wc:
                num += sc[d]["rho"] * Wc[d]
                den += Wc[d]
            per0.setdefault(d, []).append(sc[d]["rho"])
        pool0.append(num / den if den else float("nan"))
        keeps[s] = kp
        C.say("  씨앗 %d: %r (%.0fs)" % (s, pool0[-1], time.time() - wall))
    d_s0 = float(pool0[0] - C.BOARD_S0_FULL)
    d_mn = float(np.mean(pool0) - C.BOARD_RHO_FULL)
    out["🔴🔴🔴 C0 재현 관문 --- 정본 챔피언"] = collections.OrderedDict([
        ("🔴 씨앗별(전정밀)", [float(v) for v in pool0]),
        ("🔴🔴 rho", C.seed_se(pool0)),
        ("🔴 도메인별 rho(씨앗 평균)", collections.OrderedDict(
            [(d, float(np.mean(per0[d]))) for d in sorted(per0)])),
        ("🔴 도메인 군집 SE",
         C.dom_cluster_se({d: float(np.mean(per0[d])) for d in per0
                           if d in Wc},
                          {d: int(Wc[d]) for d in per0 if d in Wc})),
        ("🔴 사전등록 기대 씨앗0", C.BOARD_S0_FULL),
        ("🔴 씨앗0 차", d_s0), ("🔴 허용", C.TOL_S0),
        ("🔴🔴 씨앗0 재현했나", bool(abs(d_s0) <= C.TOL_S0)),
        ("🔴 사전등록 기대 평균", C.BOARD_RHO_FULL),
        ("🔴 평균 차", d_mn), ("🔴 허용", C.TOL_MEAN),
        ("🔴🔴 평균 재현했나", bool(abs(d_mn) <= C.TOL_MEAN)),
        ("🔴🔴🔴 F01 통과",
         bool(abs(d_s0) <= C.TOL_S0 and abs(d_mn) <= C.TOL_MEAN
              and int(sum(Wc.values())) == C.BOARD_W_SUM
              and len(Wc) == C.BOARD_NDOM)),
        ("🔴 F01 이 떨어지면",
         "🔴 **이 사이클의 모든 수를 「못 믿는다」로 계상한다** --- 챔피언 경로가 "
         "오늘 재현이 안 된다는 뜻이고 그건 판 ρ 를 다시 재는 일보다 «먼저» 고칠 것이다"),
        ("🔴 조항 59 버림 장부(씨앗 0)", drops0),
        ("🔴 학습 장부(씨앗 0)", trled0),
    ])

    # ── §4-2 ㉮ 도메인 혼합 효과 --- 🔴 항등식(리핏 없음) ─────────────────
    C.say("C1 --- 도메인 혼합 재가중")
    shared = [d for d in sorted(per0) if d in W_tf and d in Wc]
    c1_seed, c1b_seed = [], []
    for si in range(len(C.SEEDS)):
        r = {d: per0[d][si] for d in shared}
        c1_seed.append(C.pooled_w(r, {d: W_tf[d] for d in shared}))
        rb = {d: per0[d][si] for d in common if d in per0}
        c1b_seed.append(C.pooled_w(rb, {d: Wc[d] for d in rb}))
    out["🔴🔴 ㉮ 도메인 혼합 효과 (C1 · 리핏 없음 · 항등식)"] = collections.OrderedDict([
        ("🔴 무엇을 했나",
         "🔴 **정본 도메인별 ρ 는 그대로 두고 «가중만» 시간 블록 가중으로 바꿨다.** "
         "모형도 유보 행도 안 건드렸다 --- 움직인 것은 «분모의 모양» 하나다"),
        ("🔴 쓴 도메인", shared), ("🔴 도메인 수", len(shared)),
        ("🔴 정본 가중에서 빠진 도메인", [d for d in sorted(Wc) if d not in shared]),
        ("🔴🔴 C1 rho(시간 블록 가중)", C.seed_se(c1_seed)),
        ("🔴🔴 C0 − C1 (혼합만으로 생기는 낙차)",
         float(np.mean(pool0) - np.mean(c1_seed))),
        ("🔴🔴 C1b rho(정본 가중 · 공통 도메인만)", C.seed_se(c1b_seed)),
        ("🔴 쓴 공통 도메인", [d for d in common if d in per0]),
        ("🔴🔴 C0 − C1b (도메인 «집합»만 좁혔을 때의 낙차)",
         float(np.mean(pool0) - np.mean(c1b_seed))),
    ])

    # ── §4-3 ㉯ 표본 크기 효과 --- 🔴 3,775 → 1,892 하향 표본 ─────────────
    C.say("C2 --- 유보 %d → %d 하향 표본 (%d 뽑기)" % (int(sum(Wc.values())),
                                                N_DOWN, R_DRAW))
    tot = int(sum(Wc.values()))
    frac = float(N_DOWN) / float(tot)
    c2_all, c2_drop = [], collections.Counter()
    for s in C.SEEDS:
        kp = keeps[s]
        for r in range(R_DRAW):
            rng = np.random.RandomState(994_000 + s * 100 + r)
            num = den = 0.0
            for d in sorted(kp):
                p, y = kp[d]
                take = int(round(len(y) * frac))
                if take < C.MIN_SCORE:
                    c2_drop[d + " :: " + C.DROP_GATE] += 1
                    continue
                ix = rng.choice(len(y), size=take, replace=False)
                rho = float(spearmanr(p[ix], y[ix])[0])
                if not np.isfinite(rho):
                    c2_drop[d + " :: " + C.DROP_NAN] += 1
                    continue
                num += rho * take
                den += take
            c2_all.append(num / den if den else float("nan"))
    a2 = np.asarray([v for v in c2_all if np.isfinite(v)], float)
    out["🔴🔴 ㉯ 표본 크기 효과 (C2 · 유보 하향 표본)"] = collections.OrderedDict([
        ("🔴 무엇을 했나",
         "🔴 **같은 적합 · 같은 예측 벡터**를 두고 «유보 행만» 도메인 비례로 "
         "%d → %d 로 줄였다. 🔴 사이클 지시문이 이름을 댄 바로 그 수다" % (tot, N_DOWN)),
        ("정본 유보", tot), ("목표 유보", N_DOWN), ("비율", round(frac, 6)),
        ("씨앗 수", len(C.SEEDS)), ("씨앗당 뽑기", R_DRAW),
        ("🔴🔴 C2 rho 평균", float(a2.mean()) if len(a2) else None),
        ("🔴 C2 SD(뽑기 전량)", float(a2.std(ddof=1)) if len(a2) > 1 else None),
        ("🔴 C2 SE(뽑기 전량)",
         float(a2.std(ddof=1) / np.sqrt(len(a2))) if len(a2) > 1 else None),
        ("🔴 유한 뽑기", int(len(a2))), ("🔴 뽑기 전량", len(c2_all)),
        ("🔴🔴 C0 − C2 (표본 크기만 줄였을 때의 낙차)",
         float(np.mean(pool0) - a2.mean()) if len(a2) else None),
        ("🔴 조항 59 --- 하향 표본이 버린 칸",
         collections.OrderedDict(sorted(c2_drop.items()))),
        ("🔴 기대",
         "🔴 **점추정은 안 움직이고 산포만 커져야 한다.** 그게 나오면 「행 수를 "
         "맞췄더니 값이 달라졌다」는 설명이 **선다: 거짓**이다"),
    ])

    # ── §4-4 ㉰ 학습량 효과 --- 🔴 학습을 원점 1 크기로 줄인다 ──────────────
    n_tr_full = int(sum(int(tr_c[d].sum()) for d in doms
                        if int(tr_c[d].sum()) >= C.MIN_TRAIN))
    n_tr_o1 = int(sum(int(tmask[1][d].sum()) for d in doms
                      if int(tmask[1][d].sum()) >= C.MIN_TRAIN))
    fr3 = float(n_tr_o1) / float(n_tr_full) if n_tr_full else 0.0
    C.say("C3 --- 학습 %d → 약 %d (비율 %.4f) · 12 씨앗" % (n_tr_full, n_tr_o1, fr3))
    pool3, tl3, dr3 = [], None, None
    for s in C.SEEDS:
        rng = np.random.RandomState(994_500 + s)
        sub = {}
        for d in doms:
            ix = np.flatnonzero(tr_c[d])
            if len(ix) == 0:
                sub[d] = np.zeros(len(tr_c[d]), dtype=bool)
                continue
            take = int(round(len(ix) * fr3))
            m = np.zeros(len(tr_c[d]), dtype=bool)
            if take > 0:
                m[rng.choice(ix, size=min(take, len(ix)), replace=False)] = True
            sub[d] = m
        f, tl = C.fit(d0, sub, s)
        sc, dr = C.score(d0, f, ho_c, doms)
        if tl3 is None:
            tl3, dr3 = tl, C.drop_ledger(dr, doms)
        num = den = 0.0
        for d in sorted(sc):
            if d in Wc:
                num += sc[d]["rho"] * Wc[d]
                den += Wc[d]
        pool3.append(num / den if den else float("nan"))
        C.say("  C3 씨앗 %d: %r (%.0fs)" % (s, pool3[-1], time.time() - wall))
    out["🔴🔴 ㉰ 학습량 효과 (C3 · 학습 하향 표본 · 유보는 정본 그대로)"] = \
        collections.OrderedDict([
            ("🔴 무엇을 했나",
             "🔴 **유보는 정본 3,775 그대로 두고 «학습 행만» 도메인 비례로 원점 1 크기까지 "
             "줄여 다시 적합했다.** 시대는 안 바꿨다 --- 움직인 것은 «학습량» 하나다"),
            ("정본 학습 행", n_tr_full), ("원점 1 학습 행", n_tr_o1),
            ("비율", round(fr3, 6)),
            ("🔴 씨앗별", [float(v) for v in pool3]),
            ("🔴🔴 C3 rho", C.seed_se(pool3)),
            ("🔴🔴 C0 − C3 (학습량만 줄였을 때의 낙차)",
             float(np.mean(pool0) - np.mean(pool3))),
            ("🔴 조항 59 버림 장부(씨앗 0)", dr3),
            ("🔴 학습 장부(씨앗 0)", tl3),
        ])

    # ── §4-5 🔴🔴🔴 F08 --- 사전등록 §0-나 「정정」의 물증 ──────────────────
    C.say("C4 --- 사전등록 정정의 물증")
    w982p = C.ROOT / W982
    ev = collections.OrderedDict()
    if not w982p.is_file():
        ev["🔴 out982_wiring.json"] = "못 읽었다 --- 파일이 없다 (조항 59)"
        n_ent = n_tw = None
    else:
        w = json.loads(w982p.read_text(encoding="utf-8"))
        kent = "🔴🔴 개체 묶음 판(981)의 도메인별 유보 행"
        ktw = "🔴🔴 유보 전량 행 수(블록 1~4)"
        n_ent = int(sum(w[kent].values())) if kent in w else None
        n_tw = int(w[ktw]) if ktw in w else None
        ev["🔴 인용 키 경로"] = [W982 + " :: " + kent, W982 + " :: " + ktw]
        ev["🔴 개체 묶음 유보 합"] = n_ent
        ev["🔴 시간 방향 유보(982)"] = n_tw
        ev["🔴 그 풀의 게이트 도메인 수"] = len(w.get("🔴 게이트 도메인") or [])
    ledger_files = collections.OrderedDict()
    for rel in LEDGER_DATA:
        p = Path(str(C.ROOT / rel))
        ledger_files[rel] = ("있다 (%d 바이트)" % p.stat().st_size) if p.is_file() \
            else "없다"
    out["🔴🔴🔴 F08 --- 사전등록 §0-나 「정정」의 물증"] = collections.OrderedDict([
        ("🔴 사이클 지시문이 적은 전제",
         "「지금 정본 0.470343 은 옛 「개체 묶음」 유보(2,359 행)의 값이라 예측이 아니라 보간이다」"),
        ("🔴 982 산출물에서 읽은 수", ev),
        ("🔴 그 2,359 가 사는 자료", collections.OrderedDict([
            ("풀", "runners/alpha977.py :: class Pool (base = sao941 + sao959 · hplt_ko)"),
            ("자료 파일", ledger_files),
        ])),
        ("🔴 챔피언 판이 사는 자료", collections.OrderedDict([
            ("풀", "runners/ff753.py :: base() + shell() → lab/loop.py::_idol (data/state/*)"),
            ("유보", int(sum(Wc.values()))), ("도메인", len(Wc)),
            ("학습 행", n_tr_full),
            ("분할", "lab/harness.py::evaluate deploy 갈래 --- 학습 yr < 2025 · 유보 yr >= 2025"),
        ])),
        ("🔴🔴🔴 그래서 전제가 참인가", False),
        ("🔴🔴 왜 거짓인가",
         "🔴 **① 2,359 는 챔피언이 아니라 원장 풀(`alpha977.Pool`)의 유보다** --- 자료도 "
         "모형도 다르다. **② 챔피언 정본은 «이미» 시간 방향 분할이다**(학습 yr<2025 · "
         "유보 yr>=2025). 그러므로 이 사이클이 여는 물음은 「보간이냐 예측이냐」가 아니라 "
         "**「0.470343 이 «원점 하나(2025)»의 성질인가」**다"),
        ("🔴 이 정정이 사이클을 죽이나", False),
        ("🔴 왜 안 죽나",
         "🔴 원점을 넷으로 늘려 재는 일 자체는 **한 번도 안 한 측정**이고 그대로 값이 있다. "
         "바뀌는 것은 «무엇을 잰 것으로 적는가»다"),
    ])

    out["🔴 정본 값을 이 러너가 고쳤나"] = False
    out["🔴 다른 out994_* 를 읽었나"] = False
    out["🔴 도장"] = C.stamp(t0, cs0, C.data_fp(d0, doms))
    out["초"] = round(time.time() - wall, 1)
    out["통과"] = bool(out["🔴🔴🔴 C0 재현 관문 --- 정본 챔피언"]["🔴🔴🔴 F01 통과"]
                     and out["🔴 도장"]["🔴 시작=끝"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **오늘 이 자리에서 챔피언 경로가 정본 0.470343 을 «다시» 냈고(씨앗0 은 1e-12 안에서), "
        "주행 중 소스가 안 바뀌었다.** 🔴 ㉮㉯㉰ 의 «크기»는 `통과` 가 아니다")
    C.write(a.out, out)
    print(json.dumps({"out": a.out, "통과": out["통과"],
                      "C0": float(np.mean(pool0)),
                      "C1": float(np.mean(c1_seed)),
                      "C2": float(a2.mean()) if len(a2) else None,
                      "C3": float(np.mean(pool3))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
