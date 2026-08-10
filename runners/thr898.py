# -*- coding: utf-8 -*-
"""노트 898 · **자가 움직이는가** — 채택 문턱 0.00353 을 두 순위 함수로 다시 세운다.

사전등록 R-5(반증 가능하게 적은 예측):
    `thresh891` 의 R5 = 2·√(씨앗성분² + 행짝성분²) 는 두 성분이 **전부** `R890.sp`
    (동률 평균)로 계산된다 --- `state.rank_test` 는 R5 에 안 들어간다. 따라서
    **팔 B(동률 평균 통일)는 문턱을 안 움직인다**. 팔 A(서수 유지)는 자를 서수로
    다시 세워야 하므로 문턱이 움직일 수 있다.

여기서는 `runners/out891_fits.npz` **캐시를 읽기만** 해서(재적합 0회) 같은 부트
(rng 8900 · B=10,000 · 같은 뽑기 순서)를 두 채점 함수로 돌린다.

  동률 평균 → 0.00353 을 **재현하면** 배선이 맞다(중단 조건)
  서수      → 팔 A 아래의 문턱

산출물: `runners/out898_thr.json`
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

import ff753 as FF                                    # noqa: E402
import ruler890 as R890                               # noqa: E402
from lab import idolset, pairboot as PB               # noqa: E402

#: 🔴 **`state.rank_test.ranks` 를 반입하지 않는다.** 이 러너는 **팔 A(서수)** 를
#: 재는 것이 일인데, 노트 898 의 판정으로 그 함수가 **동률 평균으로 바뀌었다**.
#: 반입해서 쓰면 두 팔이 같은 물건이 되어 이 측정이 **조용히 무의미해진다**
#: (887형 중립화의 정확한 꼴). 그래서 옛 서수 구현을 **여기 박아 둔다**.
def rt_ranks(v):
    """2026-08-10 이전 `state/rank_test.py:44` 의 구현을 글자 그대로."""
    return np.argsort(np.argsort(np.asarray(v, float))).astype(float)

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out898_thr.json"
CACHE = ROOT / "runners/out891_fits.npz"
T = 2025.0
DOM = "아이돌"
SEEDS = FF.RULER_SEEDS
ARMS = (1, 2)
B = 10_000
RNG_890 = 8900
HALF_A, HALF_B = SEEDS[:6], SEEDS[6:]
EXPECT_R5 = 0.00353          #: 891 이 세운 문턱(티처 #54 가 「잠정」으로 강등 · 대역 0.00312~0.00393)
EXPECT_SEED = 0.00099
EXPECT_ROWNULL = 0.00146


def sp_mid(p, y):
    """891 이 실제로 쓰는 채점 함수 = `R890.sp`(동률 평균)."""
    return R890.sp(p, y)


def sp_ord(p, y):
    """같은 마스크·같은 꼴, 순위만 **서수**(`state.rank_test.ranks`)."""
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 20:
        return np.nan
    a, b = rt_ranks(p[ok]), rt_ranks(y[ok])
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else np.nan


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def ens(rk_by_seed, seeds):
    return np.mean([rk_by_seed[s] for s in seeds], axis=0)


def main():
    t0 = time.time()
    log = open(ROOT / "runners/out898_thr.log", "w", buffering=1)

    def say(s):
        print(s, flush=True)
        log.write(str(s) + "\n")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    say(f"HEAD {head}  {dt.datetime.now().isoformat(timespec='seconds')}")
    assert CACHE.exists(), "🔴 out891_fits.npz 가 없다 --- 재적합은 이 러너의 일이 아니다"

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}
    yh = {d: np.asarray(d0.dom[d][2], float)[post[d]] for d in doms}
    W = d0.weights(T)
    tot = sum(W.values())
    ref890 = json.load(open(ROOT / "runners/out890_ruler.json", encoding="utf-8"))
    wire = {"자료 sha256": R890.digest_data(d0),
            "890 과 동일": R890.digest_data(d0) == ref890["배선"]["ㄱ 자료 sha256"],
            "가중 합": tot, "가중 합 == 3775": tot == 3775,
            "캐시 sha256": sha(CACHE)}
    say(json.dumps(wire, ensure_ascii=False))

    rows = idolset._rows(wide_post=True)
    grp = [rows[i].get("group_name") for i in np.where(post[DOM])[0]]
    cl_idol, wire_cl = PB.clusters_of(grp)
    wire["ㅁ 군집(아이돌)"] = wire_cl

    z = np.load(CACHE, allow_pickle=True)
    PR = {k: {d: [z[f"p{k}_{d}_{i}"] for i in range(len(SEEDS))] for d in doms}
          for k in ARMS}
    RK = {k: {d: [rankdata(PR[k][d][i]) for i in range(len(SEEDS))] for d in doms}
          for k in ARMS}
    E = {}
    for k in ARMS:
        E[(k, "A")] = {d: ens(RK[k][d], HALF_A) for d in doms}
        E[(k, "B")] = {d: ens(RK[k][d], HALF_B) for d in doms}
    say(f"캐시 적재 완료 ({time.time()-t0:.0f}s)")

    FNS = {"동률 평균(891 정본)": sp_mid, "서수(rank_test)": sp_ord}
    NAMES = [(f, k) for f in FNS for k in ARMS]

    def stats_on(idx_by_dom):
        num = {n: 0.0 for n in NAMES}
        den = {n: 0.0 for n in NAMES}
        for d in doms:
            i = idx_by_dom[d]
            y = yh[d][i]
            for fname, fn in FNS.items():
                for k in ARMS:
                    v = fn(E[(k, "A")][d][i], y) - fn(E[(k, "B")][d][i], y)
                    if np.isfinite(v):
                        num[(fname, k)] += v * W[d]
                        den[(fname, k)] += W[d]
        return {n: (num[n] / den[n] if den[n] else np.nan) for n in NAMES}

    # ── 부트: 891 과 같은 rng 씨앗·같은 뽑기 순서 ────────────────────────
    rng = np.random.default_rng(RNG_890)
    ns = {d: int(post[d].sum()) for d in doms}
    draws = {n: np.empty(B) for n in NAMES}
    for b in range(B):
        idx = {}
        for d in doms:
            if d == DOM:
                idx[d] = np.concatenate([cl_idol[i] for i in
                                         rng.integers(0, len(cl_idol), len(cl_idol))])
            else:
                idx[d] = rng.integers(0, ns[d], ns[d])
        v = stats_on(idx)
        for n in NAMES:
            draws[n][b] = v[n]
        if (b + 1) % 1000 == 0:
            say(f"  부트 {b+1}/{B} ({time.time()-t0:.0f}s)")

    row_null = {}
    for fname in FNS:
        sds = {k: float(draws[(fname, k)][np.isfinite(draws[(fname, k)])].std(ddof=1))
               for k in ARMS}
        row_null[fname] = {"K=1 SD": sds[1], "K=2 SD": sds[2],
                           "행짝성분(max SD)": max(sds.values()),
                           "R4 = 2σ": 2 * max(sds.values()),
                           "고른 팔": ("K=1" if sds[1] >= sds[2] else "K=2")}
        say(f"행 짝 {fname}: {row_null[fname]}")

    # ── 씨앗 성분: 6/6 분할 462가지 전량(관측 행 고정) ────────────────────
    seed_comp = {}
    for fname, fn in FNS.items():
        best = {}
        for k in ARMS:
            vals = []
            for A in itertools.combinations(SEEDS, 6):
                if 0 not in A:
                    continue
                Bs = tuple(s for s in SEEDS if s not in A)
                eA = {d: ens(RK[k][d], A) for d in doms}
                eB = {d: ens(RK[k][d], Bs) for d in doms}
                num = den = 0.0
                for d in doms:
                    v = fn(eA[d], yh[d]) - fn(eB[d], yh[d])
                    if np.isfinite(v):
                        num += v * W[d]
                        den += W[d]
                vals.append(num / den)
            v = np.asarray(vals)
            best[k] = {"분할 수": len(v), "SD(6대6)": float(v.std(ddof=1)),
                       "SD(12대12 환산)": float(v.std(ddof=1) / np.sqrt(2))}
            say(f"  씨앗 분할 {fname} K={k}: {best[k]} ({time.time()-t0:.0f}s)")
        seed_comp[fname] = {**best,
                            "씨앗성분(max)": max(best[k]["SD(12대12 환산)"]
                                              for k in ARMS)}

    R5 = {}
    for fname in FNS:
        sc = seed_comp[fname]["씨앗성분(max)"]
        rn = row_null[fname]["행짝성분(max SD)"]
        R5[fname] = {"씨앗성분(12대12)": round(sc, 5), "행짝성분": round(rn, 5),
                     "R5 = 2·hypot": round(2 * float(np.hypot(sc, rn)), 5),
                     "R5(전정밀)": 2 * float(np.hypot(sc, rn))}
        say(f"🔴 R5 {fname}: {R5[fname]}")

    mid = R5["동률 평균(891 정본)"]
    repro = {
        "891 이 인쇄한 R5": EXPECT_R5,
        "여기서 다시 잰 R5(동률 평균)": mid["R5 = 2·hypot"],
        "일치": mid["R5 = 2·hypot"] == EXPECT_R5,
        "891 씨앗성분": EXPECT_SEED, "여기 씨앗성분": mid["씨앗성분(12대12)"],
        "891 행짝성분": EXPECT_ROWNULL, "여기 행짝성분": mid["행짝성분"],
    }
    say(json.dumps(repro, ensure_ascii=False))

    res = {
        "노트": 898,
        "무엇": "채택 문턱 0.00353 이 순위 함수에 의존하는가 — 사전등록 R-5 의 실측",
        "사전등록": {"파일": "docs/prereg_898_oneruler.md",
                  "커밋": "6373373c1a29d95772878c5103ff0c97120f29c7"},
        "HEAD": head,
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {p: sha(ROOT / p) for p in (
            "runners/thr898.py", "runners/thresh891.py", "runners/ruler890.py",
            "state/rank_test.py")},
        "배선": wire,
        "분모": {"도메인": len(W), "유보 가중 합": tot, "씨앗": list(SEEDS),
               "부트": B, "rng": RNG_890, "재적합": 0,
               "⚠": "891 캐시(out891_fits.npz)를 읽기만 했다"},
        "행 짝 성분": row_null,
        "씨앗 성분": seed_comp,
        "🔴 R5(채택 문턱)": R5,
        "891 재현": repro,
        "R-5 예측이 맞았는가": ("맞다 — 동률 평균이 891 문턱을 재현한다"
                          if repro["일치"] else
                          "🔴 틀렸다 — 891 문턱이 이 배선에서 재현되지 않는다"),
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    say(f"완료 {time.time()-t0:.0f}s → {OUT}")


if __name__ == "__main__":
    main()
