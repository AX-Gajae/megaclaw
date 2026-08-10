# -*- coding: utf-8 -*-
"""노트 898 · 2단계 **측정** — 두 팔의 판 ρ 를 12씨앗(0~11) 전량으로 잰다.

사전등록: `docs/prereg_898_oneruler.md` (커밋 `6373373c1` · 2026-08-10T21:55:49+09:00)

팔 A  서수 순위 유지      `state.rank_test.spearman` (`np.argsort(np.argsort(v))`)
팔 B  동률 평균으로 통일  `scipy.stats.spearmanr`

🔴 두 팔은 **같은 적합 · 같은 예측 벡터**를 공유한다. 채점 함수만 다르다 --- 완전 짝이다.
   그래서 씨앗마다 한 번만 적합한다(챔피언 `harness.evaluate` 의 deploy 갈래를 복사).

여기서 닫는 것
  R-1  행 순서 의존성 실측 --- 도메인마다 (예측,라벨) 짝을 20번 섞어 ρ 가짓수를 센다
  R-3a 887형 중립화 --- NaN 을 **심어서** `_score_one` 의 ok 마스크가 막는지 본다
  ㄷ재  씨앗 0 네 조합을 다시 확인(중단 조건 1e-12)
  ①    씨앗 짝 BCa (군집 = 씨앗 12 · `PB.cluster_boot`) --- **주 구간**
  ②    행 군집 BCa (아이돌 프랜차이즈 + 나머지 단독행) --- 병기. 🔴 편향 단서 있음

산출물: `runners/out898_board.json` · 예측 캐시 `runners/out898_fits.npz`

────────────────────────────────────────────────────────────────────────────
🔴 **정오(2026-08-10 · 이슈 #123 · 티처 #61 C1). 이 러너는 자기가 만든 판정 뒤에
   자기 자신을 못 돌리고 있었다.**

   초판은 팔 A 를 `from state.rank_test import spearman` 으로 **반입**했다. 그런데
   이 러너의 판정이 바로 그 함수를 **동률 평균으로 바꿨다**(커밋 `39afa03e6`).
   그래서 오늘 돌리면 **팔 A ≡ 팔 B** 가 되고 `assert ok_stop`(초판 :137 · 지금 :200)이 터진다
   (실측 차 +6.195847e-04 대 TOL 1e-12). 게다가 R-3a 는 NaN 을 심어 놓고
   `rt_spearman` 을 부르는데 새 `ranks()` 는 비유한 값에 `ValueError` 를 던진다 ---
   그 자리도 같이 죽어 있었다.

   같은 사이클의 `runners/thr898.py:41-43` 은 이 함정을 **알고 피했다**(옛 서수
   구현을 파일 안에 박아 뒀다). **그 방식을 그대로 따른다** --- 아래 `sp_A_old`.

   ⚠ **값을 다시 재는 것이 아니다.** 티처 #61 이 챔피언 경로 12씨앗을 독립 실행해
   비트 동일 재현했다(0.47034252170476804 · 차 0.0). 여기서 복구하는 것은 **재현성**이다.

🔴 **규칙(이 사이클이 저장소에 없어서 다섯 자리가 조용히 죽은 그 규칙)**

   **정본이 옮겨가면 씨앗0 상수도 같이 옮긴다. 그리고 옛 정본을 재는 러너는
   옛 구현을 파일 안에 박는다 --- 반입하지 않는다.**

   기계 확인은 `runners/out899a_gates.py` 가 한다(씨앗0 상수를 이고 있는 자리를
   전수로 훑어 「옛 값 = 옛 구현 · 새 값 = 오늘 챔피언 경로」를 강제한다).
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                    # noqa: E402
from lab import pairboot as PB                        # noqa: E402
from lab.harness import Data, MIN_TRAIN               # noqa: E402

#: 🔴 **`state.rank_test.spearman` 을 반입하지 않는다**(이슈 #123 · `thr898.py:37-43`
#: 과 같은 이유·같은 방식). 이 러너의 일은 **팔 A(서수 · 898 이전 챔피언)** 를 재는
#: 것인데, 이 러너가 낸 판정으로 그 함수가 **동률 평균으로 바뀌었다**. 반입하면 두
#: 팔이 같은 물건이 되어 측정이 조용히 무의미해진다(887형 중립화의 정확한 꼴).
#: 그래서 옛 구현을 **글자 그대로** 여기 박아 둔다.
def rt_ranks_old(v):
    """2026-08-10 이전 `state/rank_test.py:42-44`(커밋 `39afa03e6^`) 그대로."""
    o = np.argsort(np.argsort(np.asarray(v, float)))
    return o.astype(float)


def rt_spearman_old(a, b):
    """2026-08-10 이전 `state/rank_test.py:47-51`(커밋 `39afa03e6^`) 그대로.

    분모의 `+1e-12` 까지 옮긴다 --- 그것이 옛 값과 `scipy` 를 소수 12자리에서
    가르던 바로 그 항이다(새 `rank_test.spearman` 독스트링 참고). 여기서 눈금을
    '고치면' 팔 A 가 재현하려는 값 자체가 달라진다.
    """
    ra, rb = rt_ranks_old(a), rt_ranks_old(b)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float((ra * rb).mean())


ROOT = Path("/Users/ax/world_model")

#: 🔴 **재현 실행이 이력 산출물을 덮으면 안 된다**(이슈 #123). `out898_board.json` 은
#: 노트 898 판정의 증거물이고 git 에 들어 있다. 그래서 꼬리표를 붙여 딴 이름으로
#: 쓸 수 있게 한다 --- 꼬리표가 없으면 **원래 이름 그대로**라 초판 동작이 안 바뀐다.
#:     `OUT898_TAG=899a python3 runners/board898.py` → `out898_board.899a.json`
TAG = os.environ.get("OUT898_TAG", "")
_sfx = f".{TAG}" if TAG else ""
OUT = ROOT / f"runners/out898_board{_sfx}.json"
NPZ = ROOT / f"runners/out898_fits{_sfx}.npz"
LOG = ROOT / f"runners/out898_board{_sfx}.log"
T = 2025.0
SEEDS = FF.RULER_SEEDS
B_SEED = 10_000
B_ROW = 2_000
SHUF = 20

#: 🔴 **씨앗0 상수 --- 옛 값이라서 옛 구현과 짝이다**(이슈 #123).
#: `A(서수)` 는 **898 이전** 챔피언(`state/rank_test.py` 옛 서수 구현)의 씨앗0 이고,
#: 그 구현은 이제 저장소에 없으므로 위 `rt_spearman_old` 로 재현한다.
#: `B(동률평균)` 이 **오늘의 정본 경로**다 --- 2026-08-10 실측으로
#: `lab.harness.evaluate`+`Data.pooled` 도 같은 `0.4731063028988084` 를 낸다
#: (`runners/out899a_gates.json`).
EXPECT_S0 = {"A(서수)": 0.4724867181663707, "B(동률평균)": 0.4731063028988084}
TOL = 1e-12


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def sp_A(p, y):
    return float(rt_spearman_old(p, y))


def sp_B(p, y):
    return float(spearmanr(p, y)[0])


def main():
    t0 = time.time()
    log = open(LOG, "w", buffering=1)

    def say(s):
        print(s, flush=True)
        log.write(s + "\n")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    say(f"HEAD {head}  {dt.datetime.now().isoformat(timespec='seconds')}")

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    W = d0.weights(T)
    say(f"도메인 {len(W)} · 유보 가중 합 {int(sum(W.values()))}")
    assert int(sum(W.values())) == 3775, "🔴 분모가 3,775 가 아니다 --- 중단"

    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}

    # ── 학습 분할(harness.evaluate deploy 갈래를 글자 그대로) ───────────
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T)
             & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tmask[d] = k
    say(f"학습 도메인 {len(train)}")

    P = {d: [] for d in doms}          # 씨앗별 예측(post 배치)
    Y, OKM = {}, {}
    scA, scB = {d: [] for d in doms}, {d: [] for d in doms}
    poolA, poolB = [], []

    for s in SEEDS:
        f = FF.CLS(seed=s)
        f.fit(Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train}))
        nA = nB = dA = dB = 0.0
        for d in doms:
            if post[d].sum() < 20:
                continue
            A_, M_, y_, t_ = d0.slice(d, post[d])
            if len(y_) < 20:
                continue
            p = np.asarray(f.predict(d, A_, M_, t_), float)
            ok = np.isfinite(p) & np.isfinite(y_)
            if ok.sum() < 20:
                continue
            if d not in Y:
                Y[d] = y_[ok]
                OKM[d] = ok
            else:
                assert np.array_equal(OKM[d], ok), f"🔴 {d} ok 마스크가 씨앗마다 다르다"
            P[d].append(p[ok])
            a, b = sp_A(p[ok], y_[ok]), sp_B(p[ok], y_[ok])
            scA[d].append(a)
            scB[d].append(b)
            if d in W:
                nA += a * W[d]; dA += W[d]
                nB += b * W[d]; dB += W[d]
        poolA.append(nA / dA)
        poolB.append(nB / dB)
        say(f"  씨앗 {s}: A {poolA[-1]!r}  B {poolB[-1]!r}  "
            f"Δ {poolB[-1]-poolA[-1]:+.8f}  ({time.time()-t0:.0f}s)")

    # ── 중단 조건: 씨앗 0 재현 ──────────────────────────────────────────
    stop = {"A(서수)": poolA[0] - EXPECT_S0["A(서수)"],
            "B(동률평균)": poolB[0] - EXPECT_S0["B(동률평균)"]}
    ok_stop = all(abs(v) <= TOL for v in stop.values())
    say(f"중단 조건(씨앗0 재현 · 허용 {TOL}): {stop} → {'통과' if ok_stop else '🔴 중단'}")
    assert ok_stop, f"🔴 씨앗 0 이 사전등록 값과 다르다: {stop}"

    a, b = np.array(poolA), np.array(poolB)
    dd = b - a
    res_arm = {
        "A(서수 · 현행 챔피언)": {
            "씨앗별(전정밀)": list(map(float, a)), "평균": float(a.mean()),
            "SD(ddof=1)": float(a.std(ddof=1)),
            "SE": float(a.std(ddof=1) / np.sqrt(len(a)))},
        "B(동률 평균)": {
            "씨앗별(전정밀)": list(map(float, b)), "평균": float(b.mean()),
            "SD(ddof=1)": float(b.std(ddof=1)),
            "SE": float(b.std(ddof=1) / np.sqrt(len(b)))},
    }
    pair = {
        "짝 Δ(B−A) 씨앗별": list(map(float, dd)),
        "평균": float(dd.mean()), "SD(ddof=1)": float(dd.std(ddof=1)),
        "SE(씨앗 짝)": float(dd.std(ddof=1) / np.sqrt(len(dd))),
        "양수 씨앗 수": int((dd > 0).sum()), "씨앗 수": len(dd),
        "t": float(dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))),
    }
    say(f"팔 A 평균 {a.mean()!r} · 팔 B 평균 {b.mean()!r} · 짝Δ {dd.mean()!r} "
        f"± {pair['SE(씨앗 짝)']!r}(SE) · 양수 {pair['양수 씨앗 수']}/{len(dd)}")

    # ── ① 씨앗 짝 BCa (규약 47) ────────────────────────────────────────
    cl_seed, wire_seed = PB.solo_clusters(len(SEEDS))
    th1, lo1, hi1, kind1 = PB.cluster_boot(
        lambda ix: float(np.mean(dd[np.asarray(ix, int)])), cl_seed,
        B=B_SEED, seed=898)
    ci_seed = {"점추정": th1, "lo": lo1, "hi": hi1, "종류": kind1,
               "군집": wire_seed,
               "판정": PB.verdict(lo1, hi1),
               "폴백 사유": (None if kind1 == "BCa"
                          else f"cluster_boot 이 {kind1} 로 떨어졌다")}
    say(f"① 씨앗 짝 BCa {th1!r} [{lo1!r}, {hi1!r}] {kind1} → {ci_seed['판정']}")

    # ── R-1 행 순서 의존성 ──────────────────────────────────────────────
    rng = np.random.default_rng(8981)
    order = {}
    for d in doms:
        if d not in Y:
            continue
        p0, y0 = P[d][0], Y[d]
        sA, sB = set(), set()
        sA.add(sp_A(p0, y0)); sB.add(sp_B(p0, y0))
        for _ in range(SHUF):
            ix = rng.permutation(len(y0))
            sA.add(sp_A(p0[ix], y0[ix]))
            sB.add(sp_B(p0[ix], y0[ix]))
        order[d] = {"섞기": SHUF, "A 가짓수": len(sA), "B 가짓수": len(sB),
                    "A 폭": float(max(sA) - min(sA)),
                    "B 폭": float(max(sB) - min(sB))}
    r1 = {"도메인별": order,
          "A 가 순서 의존인 도메인": [d for d, v in order.items() if v["A 가짓수"] > 1],
          "B 가 순서 의존인 도메인": [d for d, v in order.items() if v["B 가짓수"] > 1],
          "A 최대 폭": max(v["A 폭"] for v in order.values()),
          "B 최대 폭": max(v["B 폭"] for v in order.values())}
    r1["R-1 판정"] = ("팔 B(P1 이 갈랐다)" if r1["A 가 순서 의존인 도메인"]
                     and not r1["B 가 순서 의존인 도메인"]
                     else "P1 이 안 갈랐다 → R-2(P3 표준정의)")
    say(f"R-1 순서 의존: A {len(r1['A 가 순서 의존인 도메인'])}/12 도메인 "
        f"(최대 폭 {r1['A 최대 폭']:.6f}) · B {len(r1['B 가 순서 의존인 도메인'])}/12 "
        f"(최대 폭 {r1['B 최대 폭']:.2e}) → {r1['R-1 판정']}")

    # ── R-3a 887형 중립화 (NaN 을 심어서) ───────────────────────────────
    d1 = "영화"
    p1, y1 = P[d1][0].copy(), Y[d1].copy()
    p1[3] = np.nan
    okm = np.isfinite(p1) & np.isfinite(y1)
    r3 = {
        "심은 도메인": d1,
        "마스크 없이 B(scipy)": float(spearmanr(p1, y1)[0]),
        "마스크 없이 B 가 nan 인가": bool(not np.isfinite(spearmanr(p1, y1)[0])),
        # 🔴 옛 서수 구현(`rt_spearman_old`)을 쓴다 --- 재는 것이 바로 **옛 구현이
        # NaN 을 조용히 삼켰다**는 사실이기 때문이다. 오늘의 `rank_test.ranks` 는
        # 비유한 값에 `ValueError` 를 던지므로(이슈 #115) 반입하면 이 줄이 죽는다.
        "마스크 없이 A(서수)": float(rt_spearman_old(p1, y1)),
        "마스크 없이 A 가 nan 인가": bool(not np.isfinite(rt_spearman_old(p1, y1))),
        "ok 마스크 뒤 B": float(sp_B(p1[okm], y1[okm])),
        "ok 마스크 뒤 B 가 유한한가": bool(np.isfinite(sp_B(p1[okm], y1[okm]))),
        "_score_one 이 같은 마스크를 쓰는가":
            "lab/harness.py:265 `ok = np.isfinite(p) & np.isfinite(y)` --- 예",
    }
    r3["R-3a 실패 조건 발화"] = not r3["ok 마스크 뒤 B 가 유한한가"]
    say(f"R-3a 887형: 마스크 없이 B nan={r3['마스크 없이 B 가 nan 인가']} · "
        f"마스크 뒤 유한={r3['ok 마스크 뒤 B 가 유한한가']} → "
        f"발화 {r3['R-3a 실패 조건 발화']}")

    # ── 도메인별 Δ ──────────────────────────────────────────────────────
    per = {}
    for d in doms:
        if d not in Y:
            continue
        va, vb = np.array(scA[d]), np.array(scB[d])
        de = vb - va
        per[d] = {
            "유보(채점행)": int(W.get(d, 0)),
            "예측 고유값(씨앗0)": int(len(np.unique(P[d][0]))),
            "동률 비율(씨앗0)": round(1 - len(np.unique(P[d][0])) / len(P[d][0]), 4),
            "A 평균": float(va.mean()), "B 평균": float(vb.mean()),
            "Δ 평균": float(de.mean()),
            "Δ SE(씨앗 짝)": float(de.std(ddof=1) / np.sqrt(len(de))),
            "Δ 양수 씨앗": int((de > 0).sum()),
            "판 기여 Δ": float(de.mean() * W.get(d, 0) / sum(W.values())),
        }
    say("도메인별 Δ(B−A)")
    for d in sorted(per, key=lambda x: -abs(per[x]["Δ 평균"])):
        v = per[d]
        say(f"   {d:<8} n={v['유보(채점행)']:>4} 고유{v['예측 고유값(씨앗0)']:>4} "
            f"동률{v['동률 비율(씨앗0)']:.3f}  Δ{v['Δ 평균']:+.6f} "
            f"({v['Δ 양수 씨앗']:>2}/12)  판기여 {v['판 기여 Δ']:+.6f}")
    chk = sum(v["판 기여 Δ"] for v in per.values())
    say(f"   판 기여 합 {chk!r} 대 짝Δ 평균 {dd.mean()!r} · "
        f"차 {chk-dd.mean():+.2e}")

    # ── ② 행 군집 BCa ───────────────────────────────────────────────────
    # 아이돌만 프랜차이즈 군집(890·891 구성) · 나머지 단독행. 전역 색인 위에서
    # `PB.cluster_boot` 를 쓴다(규약 47). 가중 W 는 설계 상수라 고정한다.
    from lab import idolset
    row_wire = {"⚠": "아이돌이 채점 목록에 없다"}
    off, clusters, dommap = 0, [], {}
    for d in doms:
        if d not in Y:
            continue
        n = len(Y[d])
        dommap[d] = (off, off + n)
        if d == "아이돌":
            try:
                rows = idolset._rows(wide_post=True)      # 890:155-158 그대로
                assert len(rows) == len(d0.dom[d][2]), "행 수 불일치"
                grp = [rows[i].get("group_name")
                       for i in np.where(post[d])[0]]
                grp = list(np.asarray(grp, dtype=object)[OKM[d]])
                cl, wcl = PB.clusters_of(grp, n)
            except Exception as e:                      # noqa: BLE001
                cl, wcl = PB.solo_clusters(n)
                wcl = {**wcl, "⚠ 프랜차이즈 군집 실패": repr(e)[:120]}
            row_wire = wcl
            clusters += [np.asarray(c, int) + off for c in cl]
        else:
            clusters += [np.array([off + i]) for i in range(n)]
        off += n
    NTOT = off

    def stat_row(ix):
        ix = np.asarray(ix, int)
        nA = dA = nB = dB = 0.0
        for d, (s0, s1) in dommap.items():
            sel = ix[(ix >= s0) & (ix < s1)] - s0
            if len(sel) < 20:
                continue
            yv = Y[d][sel]
            va = np.mean([sp_A(p[sel], yv) for p in P[d]])
            vb = np.mean([sp_B(p[sel], yv) for p in P[d]])
            if d in W:
                nA += va * W[d]; dA += W[d]
                nB += vb * W[d]; dB += W[d]
        return (nB / dB) - (nA / dA) if dA and dB else np.nan

    th2, lo2, hi2, kind2 = PB.cluster_boot(stat_row, clusters, B=B_ROW, seed=8982)
    ci_row = {"점추정": th2, "lo": lo2, "hi": hi2, "종류": kind2,
              "총 행": NTOT, "군집 수": len(clusters), "아이돌 군집": row_wire,
              "B(부트 수)": B_ROW,
              "판정": PB.verdict(lo2, hi2),
              "폴백 사유": (None if kind2 == "BCa"
                         else f"cluster_boot 이 {kind2} 로 떨어졌다"),
              "🔴 편향 단서": ("행 재표집은 **동률을 스스로 만든다**(890 의 `sp` 독스트링이 "
                            "등록한 사실). 이 구간이 재는 대비는 바로 동률 처리 차이라 "
                            "**위쪽으로 부풀 수 있다**. 주 구간은 ① 이다.")}
    say(f"② 행 군집 BCa {th2!r} [{lo2!r}, {hi2!r}] {kind2} "
        f"군집 {len(clusters)}/{NTOT}행 → {ci_row['판정']}")

    np.savez(NPZ, **{f"p_{d}_{i}": P[d][i] for d in P for i in range(len(P[d]))},
             **{f"y_{d}": Y[d] for d in Y},
             doms=json.dumps(list(Y), ensure_ascii=False),
             W=json.dumps({k: int(v) for k, v in W.items()}, ensure_ascii=False))

    res = {
        "노트": 898,
        "무엇": "판과 자의 스피어만 통일 — 두 팔의 판 ρ(12씨앗 전량)",
        "사전등록": {"파일": "docs/prereg_898_oneruler.md",
                  "커밋": "6373373c1a29d95772878c5103ff0c97120f29c7",
                  "시각": "2026-08-10T21:55:49+09:00"},
        "HEAD": head,
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {p: sha(ROOT / p) for p in (
            "runners/board898.py", "runners/wire898.py", "state/rank_test.py",
            "lab/forms.py", "lab/harness.py", "lab/pairboot.py",
            "runners/ff753.py")},
        "분모": {"도메인": len(W), "유보 가중 합": int(sum(W.values())),
               "씨앗": list(SEEDS),
               "⚠ 날짜 군집 540(897)": "다른 분모다 — 이어 붙이지 않는다(조항 60)"},
        "배선": ("ff753.base()+shell() · F18_bagboost · harness.evaluate deploy "
               "갈래 복사 · 두 팔이 같은 예측 벡터를 공유(완전 짝)"),
        "중단 조건(씨앗0 재현)": {"차": stop, "통과": ok_stop, "허용": TOL},
        "팔": res_arm,
        "짝 Δ": pair,
        "① 씨앗 짝 BCa(주)": ci_seed,
        "② 행 군집 BCa(병기)": ci_row,
        "R-1 행 순서 의존성": r1,
        "R-3a 887형 중립화": r3,
        "도메인별": per,
        "도메인 기여 합 검산": {"합": chk, "짝Δ 평균": float(dd.mean()),
                          "차": chk - float(dd.mean())},
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    say(f"완료 {time.time()-t0:.0f}s → {OUT}")


if __name__ == "__main__":
    main()
