# -*- coding: utf-8 -*-
"""노트 891 — **판 채택 문턱을 짝 부트스트랩으로 다시 세운다**(837 미결 ① · 53노트째 미이행).

옛 상수 0.0045 는 은퇴한 11도메인(유보 3,369) 시대의 값이고, 890 이 세운
예리한 자 0.0011 은 **씨앗 재현성**만 본다. 같은 결론이 자에 따라 36% 도 되고
146% 도 된다(티처 #53 M3). 그래서 자를 다섯 재고 **정의로** 고른다.

    R1 씨앗 수준 2σ (단일 측정)              --- 890 원자료에서 무료
    R2 씨앗 짝 평균 2σ (n=12)                --- 890 의 0.0011
    R3 행 수준 **비짝** 부트 2σ              --- 837 이 인쇄만 하고 안 쓴 0.0265 의 구성
    R4 **널 짝** 행 부트 2σ                  --- 837 미결 ① 이 요구한 것
    R5 합성 2σ = 2·√(씨앗성분² + 행짝성분²)  --- 채택 문턱 후보

**널 팔 쌍**: 같은 팔의 씨앗 0~5 앙상블 대 6~11 앙상블. 기대값이 같으므로 참 Δ=0 이다.
사전등록은 `data/lab/denominator.json`. 적합·자료·부트 배선은 `ruler890` 을 **재사용**한다.
"""
import datetime as dt
import hashlib
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF                                              # noqa: E402
import ruler890 as R890                                         # noqa: E402
from lab import idolset, pairboot as PB                         # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out891_thresh.json"
REF = ROOT / "runners/out890_ruler.json"
T = 2025.0
DOM = "아이돌"
SEEDS = tuple(range(12))
ARMS = (1, 2)
B = 10_000
RNG_890 = 8900          # 890 의 행수준 판 부트 rng --- 재현 대조용
HALF_A, HALF_B = tuple(range(0, 6)), tuple(range(6, 12))
OLD = 0.0045            # 은퇴한 11도메인 상수
SHARP = 0.0011          # 890 의 예리한 자(씨앗 짝 평균 2σ)


def ens(rk_by_seed, seeds):
    """미리 뽑아 둔 순위벡터들의 부분집합 평균 = `PB.rank_ensemble` 과 동치."""
    return np.mean([rk_by_seed[s] for s in seeds], axis=0)


def main():
    t0 = time.time()
    log = open(ROOT / "runners/out891_log.txt", "w", buffering=1)

    def say(s):
        print(s, flush=True); log.write(str(s) + "\n")

    ref = json.load(open(REF, encoding="utf-8"))
    say(f"참조 out890_ruler.json sha256 "
        f"{hashlib.sha256(open(REF,'rb').read()).hexdigest()[:16]}")

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}
    yh = {d: np.asarray(d0.dom[d][2], float)[post[d]] for d in doms}
    W = d0.weights(T); tot = sum(W.values())

    wire = {"ㄱ 자료 sha256": R890.digest_data(d0),
            "ㄱ 890 과 동일": R890.digest_data(d0) == ref["배선"]["ㄱ 자료 sha256"],
            "가중 합": tot, "가중 합 == 3775": tot == 3775,
            "가중이 890 과 동일": {d: W[d] for d in doms} == ref["배선"]["가중"],
            "아이돌 가중": round(W[DOM] / tot, 5)}
    say(json.dumps(wire, ensure_ascii=False))
    assert wire["ㄱ 890 과 동일"] and wire["가중 합 == 3775"], "🔴 자료가 890 과 다르다"

    rows = idolset._rows(wide_post=True)
    assert len(rows) == len(d0.dom[DOM][2]), "행 수 불일치"
    grp = [rows[i].get("group_name") for i in np.where(post[DOM])[0]]
    cl_idol, wire_cl = PB.clusters_of(grp)
    wire["ㅁ 군집(아이돌)"] = wire_cl
    say(f"ㅁ 군집 {wire_cl}")

    # ── 24 적합 (ruler890.fit_arm 재사용 · 하류 결함 재실행용 캐시) ───────
    CACHE = ROOT / "runners/out891_fits.npz"
    SC = {k: {} for k in ARMS}
    PR = {k: {d: [] for d in doms} for k in ARMS}
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        SC = json.loads(str(z["SC"]))
        SC = {int(k): {int(s): v for s, v in d_.items()} for k, d_ in SC.items()}
        for k in ARMS:
            for d in doms:
                PR[k][d] = [z[f"p{k}_{d}_{i}"] for i in range(len(SEEDS))]
        say(f"적합 캐시 재사용 {CACHE}")
    else:
        for k in ARMS:
            for s in SEEDS:
                sc, pr = R890.fit_arm(d0, k, s, post)
                SC[k][s] = sc
                for d in doms:
                    PR[k][d].append(pr.get(d, np.full(int(post[d].sum()), np.nan)))
                say(f"  K={k} 씨앗 {s} 아이돌 {sc.get(DOM, float('nan')):.4f} "
                    f"({time.time()-t0:.0f}s)")
        np.savez(CACHE, SC=json.dumps({str(k): {str(s): SC[k][s] for s in SEEDS}
                                       for k in ARMS}),
                 **{f"p{k}_{d}_{i}": PR[k][d][i]
                    for k in ARMS for d in doms for i in range(len(SEEDS))})

    # ── 배선 B: 890 씨앗별 원자료와 **부동소수 정확 일치** ────────────────
    mism = []
    for k in ARMS:
        for s in SEEDS:
            r = ref["씨앗별 원자료"][f"K={k}"][str(s)]
            for d in doms:
                if float(SC[k][s][d]) != float(r[d]):
                    mism.append((k, s, d, SC[k][s][d], r[d]))
    wire["ㄴ 890 씨앗별 원자료 재현"] = {"칸": 2 * len(SEEDS) * len(doms),
                                        "불일치": len(mism), "예": mism[:3]}
    say(json.dumps(wire["ㄴ 890 씨앗별 원자료 재현"], ensure_ascii=False))
    assert not mism, "🔴 890 재현 실패 --- 사전등록 F4 발화, 측정 중단"

    # ── 예측 순위벡터 ───────────────────────────────────────────────────
    RK = {k: {d: [rankdata(PR[k][d][i]) for i in range(len(SEEDS))] for d in doms}
          for k in ARMS}
    E = {(k, "full"): {d: ens(RK[k][d], SEEDS) for d in doms} for k in ARMS}
    for k in ARMS:
        E[(k, "A")] = {d: ens(RK[k][d], HALF_A) for d in doms}
        E[(k, "B")] = {d: ens(RK[k][d], HALF_B) for d in doms}
        E[(k, "s11")] = {d: RK[k][d][11] for d in doms}
    # 동치 확인 --- ens() 가 PB.rank_ensemble 과 같은 물건인가
    wire["ㄷ ens() == PB.rank_ensemble"] = bool(all(
        np.allclose(E[(k, "full")][d], PB.rank_ensemble(PR[k][d]))
        for k in ARMS for d in doms))
    assert wire["ㄷ ens() == PB.rank_ensemble"], "🔴 앙상블 정의가 다르다"

    sp = R890.sp
    NAMES = ["REAL(K2full−K1full)", "NULL_K1(A−B)", "NULL_K2(A−B)",
             "LVL_K1full", "LVL_K1s11"]

    def stats_on(idx_by_dom):
        """한 번의 재표집에서 다섯 통계를 동시에."""
        num = {n: 0.0 for n in NAMES}; den = {n: 0.0 for n in NAMES}
        for d in doms:
            i = idx_by_dom[d]; y = yh[d][i]
            v = {
                "REAL(K2full−K1full)": sp(E[(2, "full")][d][i], y) - sp(E[(1, "full")][d][i], y),
                "NULL_K1(A−B)": sp(E[(1, "A")][d][i], y) - sp(E[(1, "B")][d][i], y),
                "NULL_K2(A−B)": sp(E[(2, "A")][d][i], y) - sp(E[(2, "B")][d][i], y),
                "LVL_K1full": sp(E[(1, "full")][d][i], y),
                "LVL_K1s11": sp(E[(1, "s11")][d][i], y),
            }
            for n in NAMES:
                if np.isfinite(v[n]):
                    num[n] += v[n] * W[d]; den[n] += W[d]
        return {n: (num[n] / den[n] if den[n] else np.nan) for n in NAMES}

    # ── 부트: 890 과 **같은 rng 씨앗·같은 뽑기 순서** ─────────────────────
    rng = np.random.default_rng(RNG_890)
    ns = {d: int(post[d].sum()) for d in doms}
    draws = {n: np.empty(B) for n in NAMES}
    for b in range(B):
        idx = {}
        for d in doms:                       # 890 과 동일한 순서·동일한 소비
            if d == DOM:
                idx[d] = np.concatenate([cl_idol[i] for i in
                                         rng.integers(0, len(cl_idol), len(cl_idol))])
            else:
                idx[d] = rng.integers(0, ns[d], ns[d])
        v = stats_on(idx)
        for n in NAMES:
            draws[n][b] = v[n]
        if (b + 1) % 2500 == 0:
            say(f"  부트 {b+1}/{B} ({time.time()-t0:.0f}s)")

    def summ(a, pt):
        a = a[np.isfinite(a)]
        return {"점추정": round(float(pt), 5),
                "lo(2.5%)": round(float(np.percentile(a, 2.5)), 5),
                "hi(97.5%)": round(float(np.percentile(a, 97.5)), 5),
                "SD": round(float(a.std(ddof=1)), 5),
                "2σ": round(2 * float(a.std(ddof=1)), 5),
                "유실": B - len(a)}

    full_idx = {d: np.arange(ns[d]) for d in doms}
    pt = stats_on(full_idx)
    boot = {n: summ(draws[n], pt[n]) for n in NAMES}
    say(json.dumps(boot, ensure_ascii=False, indent=1))

    # 배선 ㄹ: 890 의 `행수준 판` 과 소수 5자리 대조
    r890 = ref["행수준 판(병기)"]
    wire["ㄹ 890 행수준 판 재현"] = {
        "내 REAL": {k: boot["REAL(K2full−K1full)"][k]
                    for k in ("점추정", "lo(2.5%)", "hi(97.5%)", "SD")},
        "890": {k: r890[k] for k in ("점추정", "lo(2.5%)", "hi(97.5%)", "SD")},
        "일치": all(boot["REAL(K2full−K1full)"][k] == r890[k]
                    for k in ("점추정", "lo(2.5%)", "hi(97.5%)", "SD"))}
    say(json.dumps(wire["ㄹ 890 행수준 판 재현"], ensure_ascii=False))

    # ── 씨앗 성분: 6/6 분할 462가지 전량(관측 행 고정) ────────────────────
    seed_split = {}
    for k in ARMS:
        vals = []
        for A in itertools.combinations(SEEDS, 6):
            if 0 not in A:
                continue                     # 상보 분할 중복 제거 → 462
            Bs = tuple(s for s in SEEDS if s not in A)
            eA = {d: ens(RK[k][d], A) for d in doms}
            eB = {d: ens(RK[k][d], Bs) for d in doms}
            num = den = 0.0
            for d in doms:
                v = sp(eA[d], yh[d]) - sp(eB[d], yh[d])
                if np.isfinite(v):
                    num += v * W[d]; den += W[d]
            vals.append(num / den)
        v = np.asarray(vals)
        seed_split[f"K={k}"] = {"분할 수": len(v), "평균": round(float(v.mean()), 6),
                                "SD(6대6)": round(float(v.std(ddof=1)), 5),
                                "SD(12대12 환산 ÷√2)": round(float(v.std(ddof=1)) / np.sqrt(2), 5),
                                "최대 |Δ|": round(float(np.abs(v).max()), 5)}
        say(f"씨앗 분할 K={k} {seed_split[f'K={k}']}")

    # ── 자 다섯 ─────────────────────────────────────────────────────────
    R1 = 2 * ref["자① 판"]["수준SD(K=1)"]
    R2 = 2 * ref["자① 판"]["짝SE"]
    R3 = boot["LVL_K1full"]["2σ"]
    R3b = boot["LVL_K1s11"]["2σ"]
    row_null = max(boot["NULL_K1(A−B)"]["SD"], boot["NULL_K2(A−B)"]["SD"])
    row_null_arm = ("K=1" if boot["NULL_K1(A−B)"]["SD"] >= boot["NULL_K2(A−B)"]["SD"]
                    else "K=2")
    R4 = 2 * row_null
    seed_comp = max(seed_split["K=1"]["SD(12대12 환산 ÷√2)"],
                    seed_split["K=2"]["SD(12대12 환산 ÷√2)"])
    R5 = 2 * float(np.hypot(seed_comp, row_null))
    rulers = {
        "R1 씨앗 수준 2σ(단일 측정)": round(R1, 5),
        "R2 씨앗 짝 평균 2σ(n=12 · 890 의 예리한 자)": round(R2, 5),
        "R3 행 수준 비짝 2σ(12씨앗 앙상블)": round(R3, 5),
        "R3b 행 수준 비짝 2σ(단일 씨앗 · 837 구성)": round(R3b, 5),
        "R4 널 짝 행 부트 2σ(보수 · 팔)": {"값": round(R4, 5), "고른 팔": row_null_arm,
                                          "K=1": round(2 * boot["NULL_K1(A−B)"]["SD"], 5),
                                          "K=2": round(2 * boot["NULL_K2(A−B)"]["SD"], 5)},
        "🔴 R5 합성 2σ = 채택 문턱": round(R5, 5),
        "성분": {"씨앗(12대12 환산)": round(seed_comp, 5), "행 짝(널)": round(row_null, 5)},
        "옛 상수": OLD, "890 예리한 자": SHARP,
        "R5/옛": round(R5 / OLD, 3), "R5/예리": round(R5 / SHARP, 3),
        "실제 팔 쌍(K1대K2) 참고 합성 2σ": round(
            2 * float(np.hypot(ref["자① 판"]["짝SE"], boot["REAL(K2full−K1full)"]["SD"])), 5),
    }
    say(json.dumps(rulers, ensure_ascii=False, indent=1))

    # ── 새 자가 무엇을 통과/탈락시키는가(12도메인 전량) ──────────────────
    per = ref["도메인별 씨앗 짝"]
    tcrit = 3.60                                   # t(1−0.025/12, df=11)
    table = {}
    for d in doms:
        p = per[d]
        dd = p["짝Δ 평균"]; sd = p["짝SD"]; se = p["짝SE"]
        useful = abs(dd) * W[d] / tot
        table[d] = {
            "유보행": W[d], "가중": round(W[d] / tot, 5),
            "짝Δ": dd, "짝SD": sd, "짝SE": se, "|Δ|/SE": p["|Δ|/SE"],
            "양수": f"{p['양수']}/12",
            "짝SD/수준SD": round(sd / p["수준SD(K=1)"], 3),
            "칸1 |Δ|/짝SD≥1.0": bool(abs(dd) / sd >= 1.0) if sd else None,
            "칸1 |Δ|/짝SE≥3.60": bool(abs(dd) / se >= tcrit) if se else None,
            "칸1 통과": bool(sd and se and abs(dd) / sd >= 1.0 and abs(dd) / se >= tcrit),
            "판 기여 |Δ·w|/Σw": round(useful, 6),
            "칸2 통과(≥R5)": bool(useful >= R5),
            "부족 배수(R5/기여)": round(R5 / useful, 1) if useful > 0 else None,
            "부족 배수(옛 0.0045)": round(OLD / useful, 1) if useful > 0 else None,
            "요구 도메인 Δ(R5)": round(R5 / (W[d] / tot), 4),
        }
    say(json.dumps(table, ensure_ascii=False, indent=1))

    idol = table[DOM]
    ja4 = ref["자④ 아이돌 행 BCa"]
    verdict = {
        "칸1 통과": [d for d in doms if table[d]["칸1 통과"]],
        "칸2 통과(R5)": [d for d in doms if table[d]["칸2 통과(≥R5)"]],
        "칸2 통과(옛 0.0045)": [d for d in doms
                               if table[d]["판 기여 |Δ·w|/Σw"] >= OLD],
        "칸2 통과(예리한 0.0011)": [d for d in doms
                                   if table[d]["판 기여 |Δ·w|/Σw"] >= SHARP],
        "🔴 36% 대 146% 결착": {
            "요구 아이돌 Δ(R5)": idol["요구 도메인 Δ(R5)"],
            "요구 아이돌 Δ(옛 0.0045)": round(OLD / (W[DOM] / tot), 4),
            "요구 아이돌 Δ(예리한 0.0011)": round(SHARP / (W[DOM] / tot), 4),
            "자④ 상한": ja4["hi"],
            "상한/요구(R5) %": round(100 * ja4["hi"] / (R5 / (W[DOM] / tot)), 1),
            "상한/요구(옛) %": round(100 * ja4["hi"] / (OLD / (W[DOM] / tot)), 1),
            "상한/요구(예리) %": round(100 * ja4["hi"] / (SHARP / (W[DOM] / tot)), 1)},
        "SPEC_K=2 판 Δ 대 R5": {"짝Δ": ref["자① 판"]["짝Δ 평균"],
                               "|Δ|/R5": round(abs(ref["자① 판"]["짝Δ 평균"]) / R5, 3),
                               "판정": "이 자를 못 넘었다"},
    }
    say(json.dumps(verdict, ensure_ascii=False, indent=1))

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "배선": wire, "부트": boot, "씨앗 분할": seed_split,
           "자 다섯": rulers, "12도메인 표": table, "판정": verdict,
           "걸린 시간(s)": round(time.time() - t0, 1)}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say(f"=== 저장 {OUT} · {out['걸린 시간(s)']}s ===")
    return out


if __name__ == "__main__":
    main()
