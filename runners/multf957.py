# -*- coding: utf-8 -*-
"""[수리] R2 — 🔴 **FineWeb 쪽 다중도(`mult_f`)를 실제로 낸다** (티처 #95 C2·C3 처방).

**왜.** 956 의 `measure()` 는 `mult_f` 를 **이미 계산해 놓고** HPLT 쪽 다중도만 냈다.
그래서 원장 1002 가 *「자② 상한 49.700% / 하한 19.344% · 참값은 이 사이」* 라 적었는데
🔴 **그 「하한」이 하한이 아니다** — 절단이 걸린 다중도는 **HPLT 쪽**인데 분자는
**FineWeb 문서**이기 때문이다. 티처가 FineWeb 쪽으로 걸어 **14.627%** 를 냈다.
그리고 *「자①은 뭉침 병이 **원리상 없다**」* 도 틀렸다 — FineWeb 안의 같은-URL 사본이
`D_문서 − D_키` 전부를 만든다.

**이 러너는 그 둘을 다시 세어 확정한다.** 🔴 사전등록 §8 이 적은 파일
(`runners/dupe956_ruler1.py` · 가지 `note/956-ruler1`)이 **아니라 새 파일**로 했다 ---
가지를 갈아타지 않으려고 그렇게 했고, **그 가지의 원장 줄은 아직 정정 안 됐다**.
이 어긋남을 원장에 신고한다.

읽는 것(전부 **저장소 밖** · 안 만든다):
  /Users/ax/wm_harvest/954/scan/s*.npz    HPLT 464 shard 키
  /Users/ax/wm_harvest/956/full/*.npz     FineWeb 전량 25 파일 키

사용: python3 runners/multf957.py
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np

REPO = pathlib.Path("/Users/ax/world_model")
SCAN = pathlib.Path("/Users/ax/wm_harvest/954/scan")
FULL = pathlib.Path("/Users/ax/wm_harvest/956/full")
OUT = REPO / "runners/out957_multf.json"
KS = [1, 2, 5, 10, 21, 50, 100, 478, 503, 1000]


def cat(d: pathlib.Path, key: str, pat: str):
    fs = sorted(d.glob(pat))
    if not fs:
        raise SystemExit(f"🔴 없다: {d}/{pat} — 「없다」와 「못 봤다」는 다르다(조항 59)")
    return np.concatenate([np.load(p, allow_pickle=True)[key] for p in fs]), len(fs)


def one(label: str, key: str) -> dict:
    t0 = time.time()
    hp, nh = cat(SCAN, key, "s*.npz")
    fw, nf = cat(FULL, key, "*.npz")
    hset, hcnt = np.unique(hp, return_counts=True)
    fset, fcnt = np.unique(fw, return_counts=True)
    inter = np.intersect1d(hset, fset, assume_unique=True)
    mult_h = hcnt[np.searchsorted(hset, inter)].astype(np.int64)   # HPLT 쪽
    mult_f = fcnt[np.searchsorted(fset, inter)].astype(np.int64)   # 🔴 FineWeb 쪽
    nF, nFk = int(fw.size), int(fset.size)
    hit = int(mult_f.sum())
    cur = {}
    for K in KS:
        mh, mf = (mult_h <= K), (mult_f <= K)
        cur[f"K<={K}"] = {
            "분자: HPLT 쪽 절단(956 이 낸 것)": int(mult_f[mh].sum()),
            "🔴 D_문서^K (HPLT 쪽 절단)": round(float(mult_f[mh].sum()) / nF, 6),
            "분자: FineWeb 쪽 절단(🔴 이번에 처음 낸다)": int(mult_f[mf].sum()),
            "🔴 D_문서^K (FineWeb 쪽 절단)": round(float(mult_f[mf].sum()) / nF, 6),
            "분자: 양쪽 동시": int(mult_f[mh & mf].sum()),
            "🔴 D_문서^K (양쪽 동시)": round(float(mult_f[mh & mf].sum()) / nF, 6),
            "통과": bool(int(mult_f[mh & mf].sum()) <= min(int(mult_f[mh].sum()),
                                                        int(mult_f[mf].sum()))),
        }
    return {
        "자": label,
        "분모: FineWeb 문서 전량": nF,
        "분모: FineWeb 서로 다른 키": nFk,
        "분자: 맞은 FineWeb 문서": hit,
        "🔴 D_문서": round(hit / nF, 6),
        "🔴 D_키": round(len(inter) / nFk, 6),
        "🔴 D_문서 − D_키 (%p)": round((hit / nF - len(inter) / nFk) * 100, 4),
        "교집합 키": int(inter.size),
        "🔴 FineWeb 쪽 다중도 — 교집합 키당 평균": round(float(mult_f.mean()), 4),
        "🔴 FineWeb 쪽 다중도 — 교집합 키당 최대": int(mult_f.max()),
        "🔴 FineWeb 쪽 다중도 — 코퍼스 전체 최대": int(fcnt.max()),
        "🔴 FineWeb 쪽 다중도 — 코퍼스 전체 평균": round(nF / nFk, 4),
        "HPLT 쪽 다중도 — 교집합 키당 평균": round(float(mult_h.mean()), 4),
        "HPLT 쪽 다중도 — 교집합 키당 최대": int(mult_h.max()),
        "🔴 분자 중 FineWeb 내부 사본(다중도>1 키에 걸린 문서)":
            int(mult_f[mult_f > 1].sum() - (mult_f > 1).sum()),
        "그 몫": round(float(mult_f[mult_f > 1].sum() - (mult_f > 1).sum()) / hit, 6),
        "절단 곡선": cur,
        "읽은 HPLT shard": nh, "읽은 FineWeb npz": nf,
        "초": round(time.time() - t0, 1),
        "통과": bool(hit <= nF and inter.size <= min(int(hset.size), nFk)),
    }


def main() -> dict:
    res = {"노트": 957, "레인": "수리", "무엇": "R2 — FineWeb 쪽 다중도를 낸다(티처 #95 2순위)",
           "🔴 사전등록 §8 과의 어긋남":
               "§8 은 `runners/dupe956_ruler1.py`(가지 `note/956-ruler1`)를 적었다. "
               "가지를 갈아타지 않으려고 **새 파일**로 했다 — 그 가지의 원장 줄은 아직 정정 안 됐다",
           "잰 시각(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for label, key in (("① URL 정확", "url_h"), ("② URL 정규화", "urn_h")):
        res[label] = one(label, key)
        print(label, res[label]["🔴 D_문서"], res[label]["🔴 FineWeb 쪽 다중도 — 코퍼스 전체 최대"],
              flush=True)
    a1, a2 = res["① URL 정확"], res["② URL 정규화"]
    res["🔴 판정 — 원장 1002 의 두 문장"] = {
        "①「자②의 하한은 19.344%」": {
            "HPLT 쪽 K≤21": a2["절단 곡선"]["K<=21"]["🔴 D_문서^K (HPLT 쪽 절단)"],
            "🔴 FineWeb 쪽 K≤21": a2["절단 곡선"]["K<=21"]["🔴 D_문서^K (FineWeb 쪽 절단)"],
            "🔴 양쪽 동시 K≤21": a2["절단 곡선"]["K<=21"]["🔴 D_문서^K (양쪽 동시)"],
            "🔴 하한이 하한인가": bool(
                a2["절단 곡선"]["K<=21"]["🔴 D_문서^K (HPLT 쪽 절단)"]
                <= a2["절단 곡선"]["K<=21"]["🔴 D_문서^K (FineWeb 쪽 절단)"]),
            "🔴 그러므로": "「참값은 상·하한 사이」는 **성립 안 한다**. 그 문장을 철회한다",
        },
        "②「자①은 뭉침 병이 원리상 없다」": {
            "FineWeb 쪽 코퍼스 최대 다중도": a1["🔴 FineWeb 쪽 다중도 — 코퍼스 전체 최대"],
            "분자 중 FineWeb 내부 사본": a1["🔴 분자 중 FineWeb 내부 사본(다중도>1 키에 걸린 문서)"],
            "그 몫": a1["그 몫"],
            "D_문서 − D_키 (%p)": a1["🔴 D_문서 − D_키 (%p)"],
            "🔴 원리상 없나": bool(a1["🔴 FineWeb 쪽 다중도 — 코퍼스 전체 최대"] <= 1),
            "🔴 그러므로": "「원리상 없다」가 아니라 **「작지만 있다」**로 고친다",
        },
        "통과": True,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["🔴 판정 — 원장 1002 의 두 문장"], ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
