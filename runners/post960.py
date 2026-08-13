# -*- coding: utf-8 -*-
"""노트 960 [판정 · 사후] — 🔴 **사전등록에 없다. 판정을 안 바꾼다.**

`runners/arms960.py` 가 낸 결론 하나가 **뒤집힘**이라 그 뒤집힘의 원인을 가른다.

    464 표(957·티처 #96): 도메인 지시자 **9열** 위에서 층 ③ 은 **Δρ −0.0075 = 죽었다**
    2,050 표(960):        도메인 지시자 **10열** 위에서 층 ③ 은 **Δρ +0.0071 = 산다**

🔴 **두 수는 분모도 자도 다르다**(464행/9열/BOOT 2000 ↔ 2,050행/10열/BOOT 4000).
그래서 「표가 커져서 살아났다」와 「자가 달라져서 살아났다」를 **아직 못 가른다**(조항 60).
이 러너가 세 갈래로 좁힌다.

  가  **같은 코드·같은 부트(4,000)로 464 표를 다시 잰다** — 자를 고정하고 표만 바꾼다
  나  🔴 **구성 이동을 통제한다** — 표가 4.42배 크는 동안 세계애니 비중이 올랐다.
      2,050 표를 **464 표의 도메인 비중으로 부분표집**해 Δρ 를 다시 낸다(티처 #98 중대 ⑦)
  다  **「815 중 810」의 네 분모를 실측한다**(티처 #98 중대 ①)

🔴 **판 라벨 0비트 · HTTP 0 · 새 자료 0.**

    python3 runners/post960.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

import numpy as np                                              # noqa: E402
import runners.layers957 as L                                   # noqa: E402
from runners.arms960 import boot_se                             # noqa: E402
from runners.grow959 import build_arms_fast, OUTDIR, PAIRDIR    # noqa: E402

OUT = ROOT / "runners/out960_post.json"


def judge(rows, base, plus, clus_key):
    y = np.asarray([r["y_들림"] for r in rows], dtype=float)
    g = np.asarray([r["개체"] for r in rows])
    c = np.asarray([str(r[clus_key]) for r in rows])
    ra, _, Pa = L.rho_of(L.mat(rows, *base), y, g)
    rb, _, Pb = L.rho_of(L.mat(rows, *(base + plus)), y, g)
    bs = boot_se(Pa, Pb, y, c)
    T = max(L.CARD_T, 2 * bs["SE"])
    return {"분모: 쌍": len(rows), "군집 열": clus_key, "군집 수": bs["군집 수"],
            "ρ(기준)": ra, "ρ(더한 것)": rb, "🔴 Δρ": rb - ra,
            "SE": bs["SE"], "T": T, "부트 성공/요청": [bs["재표집 성공"], bs["요청"]],
            "판정": L.verdict(rb - ra, T)}


def with_ind(rows):
    doms = sorted({r["도메인"] for r in rows})
    for r in rows:
        r["xd"] = [1.0 if r["도메인"] == d else 0.0 for d in doms]
    return doms


def main() -> dict:
    t0 = time.time()
    R = {"노트": 960, "레인": "판정(사후)",
         "🔴 사전등록에 없다 — 판정을 안 바꾼다": True,
         "논문 스텝": 503,
         "🔴 무엇": "층 ③ 이 도메인 지시자 위에서 464→2,050 사이에 부호를 바꾼 원인을 가른다"}

    coords, lp = L.load_coords(), L.load_lifepop()

    # ── 가 · 464 표를 오늘의 자로 다시 ──────────────────────────────────────
    L.WIKI = ROOT / "data/ingest/wiki_daily"
    L.PAIRS = ROOT / "data/ingest/sao941/pairs.jsonl.gz"
    old = build_arms_fast(L.load_wiki_daily(), coords, lp, L.load_pairs())
    B0 = old["B"]
    d0 = with_ind(B0)
    R["가 · 941 표(464)를 오늘의 자로 다시"] = {
        "🔴 무엇이 고정됐나": "같은 코드 · 부트 4,000 · 씨앗 7 · 군집=개체. **표만 다르다**",
        "분모: 쌍": len(B0), "도메인 수(지시자 열)": len(d0),
        "도메인별": dict(Counter(r["도메인"] for r in B0)),
        "① → +③": judge(B0, ["x1"], ["x3"], "개체"),
        "① → +지시자": judge(B0, ["x1"], ["xd"], "개체"),
        "🔴🔴 ①+지시자 → +③": judge(B0, ["x1", "xd"], ["x3"], "개체"),
        "🔴 957 이 적은 값(부트 2,000)": {"①+도메인 → +③ Δρ": -0.0075,
                                 "① → +도메인 Δρ": 0.087630},
    }

    # ── 나 · 구성 이동 통제 ────────────────────────────────────────────────
    L.WIKI, L.PAIRS = OUTDIR, PAIRDIR / "pairs.jsonl.gz"
    new = build_arms_fast(L.load_wiki_daily(), coords, lp, L.load_pairs())
    B1 = new["B"]
    with_ind(B1)
    share0 = Counter(r["도메인"] for r in B0)
    share1 = Counter(r["도메인"] for r in B1)
    n0, n1 = len(B0), len(B1)
    mix = {d: {"464 비중": share0.get(d, 0) / n0, "2,050 비중": share1.get(d, 0) / n1,
               "행": [share0.get(d, 0), share1.get(d, 0)]}
           for d in sorted(set(share0) | set(share1))}

    # 464 의 도메인 **비중**을 유지한 채 2,050 에서 가능한 한 크게 뽑는다
    ratio = min(share1[d] / (share0[d] / n0) for d in share0 if share0[d]) if share0 else 0
    target = {d: int(round(share0[d] / n0 * ratio)) for d in share0}
    reps = {}
    for seed in (11, 12, 13):
        rng = np.random.RandomState(seed)
        pick = []
        for d, k in target.items():
            idx = [i for i, r in enumerate(B1) if r["도메인"] == d]
            if k <= 0 or not idx:
                continue
            pick += list(rng.choice(idx, min(k, len(idx)), replace=False))
        rows = [B1[i] for i in sorted(pick)]
        reps[f"씨앗 {seed}"] = {
            "분모: 쌍": len(rows),
            "도메인별": dict(Counter(r["도메인"] for r in rows)),
            "① → +③": judge(rows, ["x1"], ["x3"], "개체"),
            "🔴 ①+지시자 → +③": judge(rows, ["x1", "xd"], ["x3"], "개체")}
    R["나 · 구성 이동을 통제한다 (464 의 도메인 비중으로 2,050 을 부분표집)"] = {
        "🔴 왜": ("표가 4.42배 크는 동안 도메인 구성이 움직였다. 층 ③ 은 **도메인 배경 대비 편차**라서 "
               "그 이동이 Δρ 에 섞인다(티처 #98 중대 ⑦)"),
        "도메인 비중 전후": mix,
        "🔴 세계애니 비중": {"464": share0.get("세계애니", 0) / n0,
                      "2,050": share1.get("세계애니", 0) / n1},
        "부분표집 규모 비율": ratio,
        "씨앗별": reps,
        "⚠ 이것도 완전한 통제가 아니다": ("층 ③ 의 **배경 풀**(도메인 안 개체 전량)은 부분표집으로 안 줄어든다 — "
                            "배경은 여전히 3,896 개체다. **표본 크기와 배경 품질은 여전히 못 가른다**"),
    }

    # ── 다 · 「815 중 810」의 네 분모 ───────────────────────────────────────
    from ingest import wikidaily941 as W
    tg = W.targets()
    keys = [t["키"] for t in tg]
    fileents, perdom = set(), {}
    import gzip
    for p in sorted((ROOT / "data/ingest/wiki_daily").glob("*.jsonl.gz")):
        n = 0
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                fileents.add(json.loads(line)["키"])
                n += 1
        perdom[p.name] = n
    run = json.loads((ROOT / "runners/out941_wikidaily.json").read_text())
    R["다 · 「815 중 810」의 네 분모 — 실측"] = {
        "🔴 무엇": "카드·판정문·논문 502 가 「815 중 810」을 한 분모처럼 썼다. **네 개의 다른 수다**",
        "① targets() 가 낸 **행**": len(tg),
        "② 그중 **distinct 키**": len(set(keys)),
        "🔴 중복 키": [k for k, v in Counter(keys).items() if v > 1],
        "③ 그 주행의 **성공 건수**(out941_wikidaily)": run.get("성공"),
        "③′ 그 주행의 요청 수": run.get("요청 수"),
        "④ 살아 있는 파일의 **개체 수**": len(fileents),
        "파일별 줄 수": perdom,
        "🔴 959 의 수리 ⑤ 는 「808 → 815」라 적었다": {
            "실측": f"808 → {len(set(keys))}",
            "🔴 815 라는 개체는 없다": "815 는 행 수이고 개체로는 " + str(len(set(keys))),
        },
    }

    R["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=1)[:7000])
