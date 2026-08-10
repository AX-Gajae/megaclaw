# -*- coding: utf-8 -*-
"""노트 890 — **판이 유일한 자인가.** 888 의 '아이돌 +0.0274' 에 자 넷을 댄다.

팔은 둘(SPEC_K=1 대 2)뿐이고, 이번에 재는 것은 팔이 아니라 **자**다.

    자① 판(유보수 가중 pooled)      아이돌 가중 0.01351 · 문턱 2σ=0.0045
    자② 거시판(12도메인 비가중 평균) 아이돌 가중 0.0833 (판의 6.17배)
    자③ 도메인 씨앗 짝(12씨앗)       씨앗 잡음만 다룬다 --- 888 이 안 잰 것
    자④ 도메인 행 군집 부트 BCa      표본 잡음(49행) --- 자③ 이 못 보는 것

배선 검사 다섯(ㄱ~ㅁ)을 측정 전에 닫는다. 사전등록은 `data/lab/denominator.json`.
"""
import datetime as dt
import hashlib
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
from lab import guards as G, idolset, pairboot as PB            # noqa: E402
from lab.forms import REGISTRY                                  # noqa: E402
from lab.harness import Data, MIN_TRAIN                         # noqa: E402
from state.rank_test import spearman as rt_spearman             # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out890_ruler.json"
CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
DOM = "아이돌"
SEEDS = tuple(range(12))
ARMS = (1, 2)
B = 10_000
THRESH = 0.0045
SPEC_SHA_888 = "1dcdf9bc212531e1"

#: 배선 ㄷ --- 오늘 `harness.evaluate(K=1, seed=0)` 실측(888 의 K=1 씨앗0 과 동일)
EXPECT_K1_S0 = {
    "게임": 0.6452730022531311, "도서": 0.3750699674685748,
    "만화": 0.3242680740644639, "모바일": 0.6305887389920906,
    "세계애니": 0.5951652796142043, "시장팝업": 0.16554030746155818,
    "아이돌": 0.4125791855203059, "애니": 0.611341969901641,
    "영화": 0.4862210172554917, "웹툰": 0.36212852210664837,
    "팝업": 0.382998251748211, "펀딩": 0.3704998589526129,
}
EXPECT_POOLED_K1_S0 = 0.4724867181663707


def klass(k):
    return type(f"F18_K{k}", (CLS,), {"SPEC_K": k})


def sp(p, y):
    """동률 평균 스피어만(부트용 --- 재표집이 동률을 만든다)."""
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 20:
        return np.nan
    a, b = rankdata(p[ok]), rankdata(y[ok])
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else np.nan


def digest_data(d):
    h = hashlib.sha256()
    for k in sorted(d.dom):
        A, M, y, t = d.dom[k]
        for arr in (A, M, y, t):
            a = np.ascontiguousarray(np.asarray(arr, float))
            h.update(str(a.shape).encode()); h.update(a.tobytes())
        h.update(("|".join(map(str, d.names[k]))).encode())
    return h.hexdigest()[:16]


def wiring_spec(data):
    """ㄴ --- `_spec_col` 열 sha256 과 폭 불변식(888 병 의 방법)."""
    out = {}
    for k in ARMS:
        f = G._fit_on(lambda k=k: klass(k)(seed=0), data, T, seed=0)
        widths, dig = set(), hashlib.sha256()
        for d in sorted(data.dom):
            A, M, y, t = data.dom[d]
            C = f._spec_col(d, A, M, data.names.get(d))
            widths.add(int(C.shape[1]))
            dig.update(np.ascontiguousarray(C.astype(float)).tobytes())
        out[f"K={k}"] = {"폭": sorted(widths), "폭_불변": len(widths) == 1,
                         "기대폭": 2 * k, "해시": dig.hexdigest()[:16]}
    out["888 과 동일(K=1)"] = out["K=1"]["해시"] == SPEC_SHA_888
    out["888 해시"] = SPEC_SHA_888
    return out


def fit_arm(data, k, seed, post):
    """`harness.evaluate` deploy 갈래 **복사** --- 예측 벡터가 필요해서다."""
    train, tmask = {}, {}
    for d in data.dom:
        m = (np.isfinite(data.yr[d]) & (data.yr[d] < T)
             & np.isfinite(data.dom[d][2]))
        if m.sum() >= MIN_TRAIN:
            train[d] = data.slice(d, m); tmask[d] = m
    f = klass(k)(seed=seed)
    f.fit(Data(train, data.names, {d: data.yr[d][tmask[d]] for d in train}))
    sc, pr = {}, {}
    for d in data.dom:
        if post[d].sum() < 20:
            continue
        A, M, y, t = data.slice(d, post[d])
        if len(y) < 20:
            continue
        try:
            p = np.asarray(f.predict(d, A, M, t), float)
        except Exception:
            continue
        if p.shape[0] != len(y) or not np.isfinite(p).any():
            continue
        pr[d] = p
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() >= 20:
            sc[d] = float(rt_spearman(p[ok], y[ok]))
    return sc, pr


def main():
    t0 = time.time()
    log = open(ROOT / "runners/out890_log.txt", "w", buffering=1)

    def say(s):
        print(s, flush=True); log.write(s + "\n")

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}
    yh = {d: np.asarray(d0.dom[d][2], float)[post[d]] for d in doms}
    W = d0.weights(T); tot = sum(W.values())

    wire = {"ㄱ 자료 sha256": digest_data(d0),
            "ㄴ 특기열": wiring_spec(d0),
            "가중": {d: W[d] for d in doms}, "가중 합": tot,
            "아이돌 가중": round(W[DOM] / tot, 5),
            "유보 행": {d: int(post[d].sum()) for d in doms},
            "유보 채점행": {d: int(np.isfinite(yh[d]).sum()) for d in doms}}
    say(json.dumps(wire, ensure_ascii=False, indent=1))
    assert wire["ㄴ 특기열"]["888 과 동일(K=1)"], "🔴 888 과 배선이 다르다 --- 중단"
    assert all(v["폭_불변"] for k, v in wire["ㄴ 특기열"].items()
               if isinstance(v, dict)), "🔴 폭 불변식 깨짐"

    # ㅁ 군집
    rows = idolset._rows(wide_post=True)
    assert len(rows) == len(d0.dom[DOM][2]), "행 수 불일치"
    grp = [rows[i].get("group_name") for i in np.where(post[DOM])[0]]
    cl_idol, wire_cl = PB.clusters_of(grp)
    wire["ㅁ 군집(아이돌)"] = wire_cl
    say(f"ㅁ 군집: {wire_cl}")

    # ── 측정 ────────────────────────────────────────────────────────────
    SC = {k: {} for k in ARMS}          # arm -> seed -> {dom: rho}
    PR = {k: {d: [] for d in doms} for k in ARMS}
    for k in ARMS:
        for s in SEEDS:
            sc, pr = fit_arm(d0, k, s, post)
            SC[k][s] = sc
            for d in doms:
                PR[k][d].append(pr.get(d, np.full(int(post[d].sum()), np.nan)))
            say(f"  K={k} 씨앗 {s} 판 "
                f"{sum(sc[d]*W[d] for d in sc if d in W)/sum(W[d] for d in sc if d in W):.4f}"
                f" 아이돌 {sc.get(DOM, float('nan')):.4f} ({time.time()-t0:.0f}s)")
            if k == 1 and s == 0:
                same = {d: (sc.get(d) == EXPECT_K1_S0[d]) for d in EXPECT_K1_S0}
                wire["ㄷ 정본 하네스와 일치(K=1 씨앗0)"] = {
                    "12도메인 부동소수 정확일치": all(same.values()),
                    "어긋난 도메인": [d for d, v in same.items() if not v],
                    "판": sum(sc[d]*W[d] for d in sc if d in W)/sum(W[d] for d in sc if d in W),
                    "기대 판": EXPECT_POOLED_K1_S0}
                say(json.dumps(wire["ㄷ 정본 하네스와 일치(K=1 씨앗0)"],
                               ensure_ascii=False))
                assert all(same.values()), "🔴 재구현이 정본과 다르다 --- 중단"

    # ㄹ 팔이 실제로 다른가
    diff_cells = [int(np.sum(PR[1][DOM][i] != PR[2][DOM][i])) for i in range(len(SEEDS))]
    wire["ㄹ 아이돌 유보 예측이 팔 사이에서 다른 칸 수(씨앗별)"] = diff_cells
    wire["ㄹ 항등식 아님"] = bool(min(diff_cells) > 0)
    say(f"ㄹ 다른 칸 수 {diff_cells}")
    assert min(diff_cells) > 0, "🔴 두 팔의 예측이 같다 --- 887 의 항등식 함정"

    # ── 자①②③ 씨앗 짝 ─────────────────────────────────────────────────
    def board_of(sc):
        n = sum(W[d] for d in sc if d in W)
        return sum(sc[d] * W[d] for d in sc if d in W) / n if n else np.nan

    def macro_of(sc):
        v = [sc[d] for d in doms if d in sc and np.isfinite(sc[d])]
        return float(np.mean(v)) if v else np.nan

    b1 = np.array([board_of(SC[1][s]) for s in SEEDS])
    b2 = np.array([board_of(SC[2][s]) for s in SEEDS])
    m1 = np.array([macro_of(SC[1][s]) for s in SEEDS])
    m2 = np.array([macro_of(SC[2][s]) for s in SEEDS])
    i1 = np.array([SC[1][s].get(DOM, np.nan) for s in SEEDS])
    i2 = np.array([SC[2][s].get(DOM, np.nan) for s in SEEDS])

    def pair(a, b, name):
        d = a - b
        sd = float(d.std(ddof=1)); se = sd / np.sqrt(len(d))
        return {"자": name,
                "K=1 평균": round(float(b.mean()), 4), "K=2 평균": round(float(a.mean()), 4),
                "짝Δ 평균": round(float(d.mean()), 5),
                "짝SD": round(sd, 5), "짝SE": round(se, 5),
                "|Δ|/SE": round(abs(float(d.mean())) / se, 2) if se > 0 else None,
                "양수": int((d > 0).sum()), "총": len(d),
                "씨앗별 Δ": [round(float(x), 5) for x in d],
                "수준SD(K=1)": round(float(b.std(ddof=1)), 5)}

    ja1 = pair(b2, b1, "① 판(가중)")
    ja2 = pair(m2, m1, "② 거시판(비가중)")
    ja3 = pair(i2, i1, "③ 아이돌 도메인(씨앗 짝)")
    for j in (ja1, ja2, ja3):
        say(json.dumps(j, ensure_ascii=False))

    per_dom_seed = {d: pair(np.array([SC[2][s].get(d, np.nan) for s in SEEDS]),
                            np.array([SC[1][s].get(d, np.nan) for s in SEEDS]), d)
                    for d in doms}

    # ── 자④ 행 군집 부트 ────────────────────────────────────────────────
    ENS = {k: {d: PB.rank_ensemble(PR[k][d]) for d in doms} for k in ARMS}
    y_i = yh[DOM]
    pA, pB_ = ENS[2][DOM], ENS[1][DOM]

    def stat_idol(idx):
        return sp(pA[idx], y_i[idx]) - sp(pB_[idx], y_i[idx])

    pt, lo, hi, kind = PB.cluster_boot(stat_idol, cl_idol, B=B, seed=890)
    ja4 = {"자": "④ 아이돌 행 군집 부트", "점추정": round(float(pt), 5),
           "lo": round(float(lo), 5), "hi": round(float(hi), 5),
           "폭": round(float(hi - lo), 5), "종류": kind,
           "규약 47 판정": PB.verdict(lo, hi), "B": B,
           "군집": wire_cl,
           "앙상블 ρ K=1": round(float(sp(pB_, y_i)), 5),
           "앙상블 ρ K=2": round(float(sp(pA, y_i)), 5),
           "⚠ 씨앗평균 ρ 와 다르다(노트 828)": {
               "씨앗평균 K=1": round(float(np.nanmean(i1)), 5),
               "씨앗평균 K=2": round(float(np.nanmean(i2)), 5)}}
    say(json.dumps(ja4, ensure_ascii=False))

    # 판·거시의 행 수준 구간 --- 층화 percentile(폴백 사유 명기)
    rng = np.random.default_rng(8900)
    ns = {d: int(post[d].sum()) for d in doms}
    bs_b, bs_m = np.empty(B), np.empty(B)
    for b in range(B):
        db, dm = {}, {}
        for d in doms:
            if d == DOM:
                idx = np.concatenate([cl_idol[i] for i in
                                      rng.integers(0, len(cl_idol), len(cl_idol))])
            else:
                idx = rng.integers(0, ns[d], ns[d])
            v = sp(ENS[2][d][idx], yh[d][idx]) - sp(ENS[1][d][idx], yh[d][idx])
            if np.isfinite(v):
                db[d] = v; dm[d] = v
        nw = sum(W[d] for d in db if d in W)
        bs_b[b] = sum(db[d] * W[d] for d in db if d in W) / nw if nw else np.nan
        bs_m[b] = float(np.mean(list(dm.values()))) if dm else np.nan
        if (b + 1) % 2000 == 0:
            say(f"  부트 {b+1}/{B} ({time.time()-t0:.0f}s)")
    pt_b = (sum((sp(ENS[2][d], yh[d]) - sp(ENS[1][d], yh[d])) * W[d]
                for d in doms if d in W) / tot)
    pt_m = float(np.mean([sp(ENS[2][d], yh[d]) - sp(ENS[1][d], yh[d]) for d in doms]))

    def pct(a, p):
        a = a[np.isfinite(a)]
        return {"점추정": round(float(p), 5),
                "lo(2.5%)": round(float(np.percentile(a, 2.5)), 5),
                "hi(97.5%)": round(float(np.percentile(a, 97.5)), 5),
                "SD": round(float(a.std(ddof=1)), 5), "유실": B - len(a),
                "종류": "percentile(층화 · 폴백 사유: cluster_boot 의 단일 군집목록 "
                       "서명에 도메인 층화가 안 맞는다 --- 규약 47 병기 의무)",
                "판정": PB.verdict(float(np.percentile(a, 2.5)),
                                 float(np.percentile(a, 97.5)))}
    row_board, row_macro = pct(bs_b, pt_b), pct(bs_m, pt_m)
    say(json.dumps({"행수준 판": row_board, "행수준 거시": row_macro},
                   ensure_ascii=False))

    out = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "배선": wire,
        "자① 판": ja1, "자② 거시판": ja2, "자③ 아이돌 씨앗 짝": ja3,
        "자④ 아이돌 행 BCa": ja4,
        "행수준 판(병기)": row_board, "행수준 거시(병기)": row_macro,
        "자 비교 — 거시가 판보다 둔한가": {
            "판 짝SE": ja1["짝SE"], "거시 짝SE": ja2["짝SE"],
            "비(거시/판)": round(ja2["짝SE"] / ja1["짝SE"], 2) if ja1["짝SE"] else None,
            "판 2σ(실측 짝)": round(2 * ja1["짝SE"], 5),
            "거시 2σ(실측 짝)": round(2 * ja2["짝SE"], 5),
            "정본 문턱": THRESH},
        "도메인별 씨앗 짝": per_dom_seed,
        "씨앗별 원자료": {f"K={k}": {str(s): SC[k][s] for s in SEEDS} for k in ARMS},
        "걸린 시간(s)": round(time.time() - t0, 1),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say(f"=== 저장 {OUT} · {out['걸린 시간(s)']}s ===")
    return out


if __name__ == "__main__":
    main()
