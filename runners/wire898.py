# -*- coding: utf-8 -*-
"""노트 898 · 0단계 **배선 검사** — 측정 전에 티처 #60 C1·C2 의 주장을 직접 센다.

여기서 닫는 것 셋(전부 실측 · 티처 말을 안 믿는다)

  ㄱ  `BagBoost` 자루의 `random_state` 를 **찍어 본다**.
     C1 주장: `lab/forms.py:702-703` 이 `{**self.kw, "random_state": k}` 로
     자루 색인 `k` 를 덮어쓰므로 `guards._fit_on(seed=s)` 가 갈아 끼운
     `kw['random_state']` 는 GBM 에 **절대 안 닿는다**.
     반증 형태: 자루들의 `random_state` 가 `[0..K-1]` 이 **아니면** 주장이 틀린 것이다.

  ㄴ  **동률을 실제로 센다** — 도메인별 (채점행수, 예측 고유값 수, 라벨 고유값 수).
     티처: 시장팝업 126행/15 · 영화 406행/139.

  ㄷ  씨앗 0 에서 **네 조합**을 재서 티처의 가름표를 재현한다.
        post 배치 + rank_test(서수)   ← 챔피언          기대 0.4724867181663707
        post 배치 + scipy(동률 평균)                     기대 0.4731063028988084
        kho 배치 + scipy             ← 837/refit112     기대 0.47382623452954425
        kho 배치 + rank_test                            기대 0.47319563433056183

산출물: `runners/out898_wire.json`

────────────────────────────────────────────────────────────────────────────
🔴 **정오(2026-08-10 · 이슈 #123 · 티처 #61 C1)** --- `board898.py` 와 **같은 병**이다.

   초판은 ㄷ 의 두 조합(`post+rank_test` · `kho+rank_test`)을
   `from state.rank_test import spearman` 으로 **반입**했는데, 노트 898 의 판정이
   그 함수를 **동률 평균으로 바꿨다**. 그래서 오늘 돌리면
   `post+rank_test == post+scipy` · `kho+rank_test == kho+scipy` 가 되어
   **이 파일이 재려던 「스피어만 구현 몫」이 정확히 0 이 된다** --- 게이트가 터지지도
   않고 **조용히 0 을 낸다**. `board898` 보다 나쁘다(거기는 `assert` 라도 있었다).

   `runners/thr898.py:41-43` 방식으로 옛 서수 구현을 파일 안에 박았다(아래).

🔴 **규칙**: **정본이 옮겨가면 씨앗0 상수도 같이 옮긴다. 그리고 옛 정본을 재는
   러너는 옛 구현을 파일 안에 박는다 --- 반입하지 않는다.**
   기계 확인은 `runners/out899a_gates.py`.
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
from lab import guards as G                           # noqa: E402
from lab.harness import Data, MIN_TRAIN               # noqa: E402


#: 🔴 **`state.rank_test.spearman` 을 반입하지 않는다**(이슈 #123 · `thr898.py:37-43`
#: 과 같은 이유·같은 방식). 옛 서수 구현을 **글자 그대로** 여기 박아 둔다.
def rt_ranks_old(v):
    """2026-08-10 이전 `state/rank_test.py:42-44`(커밋 `39afa03e6^`) 그대로."""
    o = np.argsort(np.argsort(np.asarray(v, float)))
    return o.astype(float)


def rt_spearman_old(a, b):
    """2026-08-10 이전 `state/rank_test.py:47-51`(커밋 `39afa03e6^`) 그대로.

    분모의 `+1e-12` 까지 옮긴다 --- ㄷ 가 재는 「스피어만 구현 몫」이 바로 그 항과
    동률 처리의 합이다. 눈금을 '고치면' 재려는 대비가 사라진다.
    """
    ra, rb = rt_ranks_old(a), rt_ranks_old(b)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float((ra * rb).mean())


ROOT = Path("/Users/ax/world_model")

#: 🔴 재현 실행이 이력 산출물(`out898_wire.json` · git 안)을 덮지 않게 한다(이슈 #123).
#:     `OUT898_TAG=899a python3 runners/wire898.py` → `out898_wire.899a.json`
TAG = os.environ.get("OUT898_TAG", "")
_sfx = f".{TAG}" if TAG else ""
OUT = ROOT / f"runners/out898_wire{_sfx}.json"
LOG = ROOT / f"runners/out898_wire{_sfx}.log"
T = 2025.0

#: 🔴 **씨앗0 상수 --- 넷 중 둘은 옛 값이라서 옛 구현과 짝이다**(이슈 #123).
#: `post+rank_test(챔피언)` 의 「챔피언」은 **898 이전**을 뜻한다. 오늘의 챔피언
#: 경로(동률 평균)가 내는 씨앗0 은 `post+scipy` 쪽 `0.4731063028988084` 이고
#: 2026-08-10 에 `lab.harness.evaluate`+`Data.pooled` 로 직접 확인했다
#: (`runners/out899a_gates.json`).
EXPECT = {
    "post+rank_test(챔피언)": 0.4724867181663707,
    "post+scipy": 0.4731063028988084,
    "kho+scipy(837)": 0.47382623452954425,
    "kho+rank_test": 0.47319563433056183,
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def sp_scipy(p, y):
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

    # ── ㄱ 자루 random_state ────────────────────────────────────────────
    # `_fit_on` 은 make() 가 낸 객체의 seed 를 seed 인자로 덮고
    # kw['random_state'] 도 덮는다. **일부러 서로 다른 값을 준다** —
    # make 는 seed=0, _fit_on 은 seed=7. 그래야 무엇이 무엇을 이기는지 보인다.
    f = G._fit_on(lambda: FF.CLS(seed=0), d0, T, seed=7)
    bags = [int(m.random_state) for m in f.ms]
    kA = {
        "f.seed(적합 뒤)": int(getattr(f, "seed", -1)),
        "f.kw['random_state']": int(f.kw.get("random_state", -1)),
        "자루 수": len(bags),
        "자루 random_state": bags,
        "자루가 [0..K-1] 인가": bags == list(range(len(bags))),
        "C1 주장(kw['random_state'] 는 GBM 에 안 닿는다)": bags == list(range(len(bags))),
    }
    _kwrs = kA["f.kw['random_state']"]
    _sd = kA["f.seed(적합 뒤)"]
    _c1 = kA["자루가 [0..K-1] 인가"]
    say(f"ㄱ 자루 random_state = {bags[:6]}…  kw['random_state']={_kwrs}  "
        f"f.seed={_sd}  → C1(무연산) {_c1}")

    # ── 씨앗 0 으로 다시 적합(챔피언 배선) ─────────────────────────────
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T)
             & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tmask[d] = k
    f0 = FF.CLS(seed=0)
    f0.fit(Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train}))
    say(f"씨앗0 적합 끝 ({time.time()-t0:.0f}s)")

    # ── ㄴ·ㄷ ───────────────────────────────────────────────────────────
    tie, sc = {}, {k: {} for k in EXPECT}
    for d in doms:
        yrv = np.asarray(d0.yr[d], float)
        yall = np.asarray(d0.dom[d][2], float)
        post = np.isfinite(yrv) & (yrv >= T)
        kho = post & np.isfinite(yall)
        if post.sum() < 20 or kho.sum() < 20:
            continue
        A, M, y, t = d0.slice(d, post)
        pp = np.asarray(f0.predict(d, A, M, t), float)
        ok = np.isfinite(pp) & np.isfinite(y)
        Ah, Mh, yh, th = d0.slice(d, kho)
        pk = np.asarray(f0.predict(d, Ah, Mh, th), float)
        okk = np.isfinite(pk) & np.isfinite(yh)
        if ok.sum() < 20 or okk.sum() < 20:
            continue
        tie[d] = {
            "유보(post)행": int(post.sum()),
            "채점행(post∩라벨유한∩예측유한)": int(ok.sum()),
            "예측 고유값": int(len(np.unique(pp[ok]))),
            "라벨 고유값": int(len(np.unique(y[ok]))),
            "예측 동률행": int(ok.sum() - len(np.unique(pp[ok]))),
            "동률 비율": round(1 - len(np.unique(pp[ok])) / int(ok.sum()), 4),
            "kho 배치 행": int(okk.sum()),
            "kho 예측 고유값": int(len(np.unique(pk[okk]))),
        }
        sc["post+rank_test(챔피언)"][d] = float(rt_spearman_old(pp[ok], y[ok]))
        sc["post+scipy"][d] = sp_scipy(pp[ok], y[ok])
        sc["kho+scipy(837)"][d] = sp_scipy(pk[okk], yh[okk])
        sc["kho+rank_test"][d] = float(rt_spearman_old(pk[okk], yh[okk]))

    pooled = {}
    for k, s in sc.items():
        num = sum(v * W[d] for d, v in s.items() if d in W)
        den = sum(W[d] for d in s if d in W)
        pooled[k] = num / den

    say("ㄴ 동률")
    for d in sorted(tie):
        v = tie[d]
        say(f"   {d:<8} 채점 {v['채점행(post∩라벨유한∩예측유한)']:>4}행 · "
            f"예측 고유 {v['예측 고유값']:>4} · 동률 {v['동률 비율']:.3f}")
    say("ㄷ 네 조합(씨앗 0)")
    for k in EXPECT:
        say(f"   {k:<26} {pooled[k]!r}   기대 {EXPECT[k]!r}  "
            f"Δ={pooled[k]-EXPECT[k]:+.3e}")

    dec = {
        "스피어만 구현 몫(post: scipy − rank_test)":
            pooled["post+scipy"] - pooled["post+rank_test(챔피언)"],
        "채점 배치 몫(scipy: kho − post)":
            pooled["kho+scipy(837)"] - pooled["post+scipy"],
        "총 Δ(837 − 챔피언)":
            pooled["kho+scipy(837)"] - pooled["post+rank_test(챔피언)"],
    }
    dec["합이 비트 동일"] = (
        dec["스피어만 구현 몫(post: scipy − rank_test)"]
        + dec["채점 배치 몫(scipy: kho − post)"] == dec["총 Δ(837 − 챔피언)"])

    res = {
        "노트": 898, "무엇": "0단계 배선 검사 — 티처 #60 C1·C2 를 직접 센다",
        "HEAD": head,
        "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {p: sha(ROOT / p) for p in (
            "runners/wire898.py", "state/rank_test.py", "lab/forms.py",
            "lab/guards.py", "lab/harness.py", "runners/ff753.py")},
        "분모": {"도메인": len(W), "유보 가중 합": int(sum(W.values())),
               "씨앗": 0},
        "ㄱ 자루 random_state": kA,
        "ㄴ 동률": tie,
        "ㄷ 씨앗0 네 조합": {k: pooled[k] for k in EXPECT},
        "ㄷ 기대값": EXPECT,
        "ㄷ 재현 오차": {k: pooled[k] - EXPECT[k] for k in EXPECT},
        "ㄷ 가름": dec,
        "도메인별 ρ": sc,
        "도메인별 유보": {k: int(v) for k, v in sorted(W.items())},
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    say(f"완료 {time.time()-t0:.0f}s → {OUT}")


if __name__ == "__main__":
    main()
