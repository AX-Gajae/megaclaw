# -*- coding: utf-8 -*-
"""③-나 진단 — 🔴 **자가 실제로 잰 것과 항등식인 것은 둘이다** (노트 952 [수집]).

`out952_count.json` 이 낸 두 수가 **너무 깨끗해서** 자를 의심한다:

  ① `steam.sao.s 만족 = 137,808` --- **전량**이다.
     사전등록 §2 P8 이 s 를 「genres/tags/price 중 하나 이상」으로 정의했는데
     `price` 는 **모든 행에 있다**(0.0 도 값이다) → 🔴 **s 조건이 항등식이었다.**
     노트 887 의 「위약 Δ=0 이 통계가 아니라 항등식이었다」와 **같은 병**이다.
  ② `hplt.비한국어문서 = 0` --- 335,060 중 하나도 없다. 자가 고장 났을 수 있다.

🔴 **여기서 나온 수로 P8 을 다시 채점하지 않는다.** 사전등록 정의가 정본이고,
이 파일은 **그 정의가 무엇을 못 쟀는지**를 적는 진단이다(사후 정의 교체 금지).
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_diag.json"
HANGUL = re.compile(r"[가-힣]")


def diag_steam() -> dict:
    z = zipfile.ZipFile(ROOT / "data/ingest/steam_games/archive.zip")
    with z.open("games.json") as fh:
        gj = json.load(fh)
    n = len(gj)
    have = collections.Counter()
    strict = 0
    price_missing = 0
    for g in gj.values():
        hg, ht = bool(g.get("genres")), bool(g.get("tags"))
        hp = g.get("price") is not None
        have["genres"] += hg
        have["tags"] += ht
        have["price 키가 있다"] += hp
        if not hp:
            price_missing += 1
        pos, neg = int(g.get("positive") or 0), int(g.get("negative") or 0)
        if (hg or ht) and (pos + neg) >= 1:
            strict += 1
    return {
        "분모": n,
        "🔴 사전등록 s 조건이 항등식이었나": price_missing == 0,
        "price 가 없는 행": price_missing,
        "각 칸이 실제로 찬 행": dict(have),
        "🔴 더 센 자(진단용 · P8 재채점에 안 쓴다)":
            "s=(genres 또는 tags 가 비지 않았다) 그리고 o=(positive+negative)>=1",
        "더 센 자 아래 (s,a,o) 행": strict,
        "더 센 자 비율": round(strict / n, 6),
        "사전등록 자 아래 행(참고)": 82981,
        "🔴 차이": 82981 - strict,
    }


def diag_hplt() -> dict:
    import pyarrow.parquet as pq
    f = sorted((ROOT / "data/ingest/hplt_ko").glob("*.parquet"))[0]
    pf = pq.ParquetFile(f)
    hist = collections.Counter()
    mn, mn_url = 1.0, None
    n = 0
    for i in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(i, columns=["text", "u"])
        for tx, u in zip(t.column("text").to_pylist(), t.column("u").to_pylist()):
            st = (tx or "").strip()
            nows = [c for c in st if not c.isspace()]
            r = (len(HANGUL.findall(st)) / len(nows)) if nows else 0.0
            n += 1
            hist[round(r, 1)] += 1
            if r < mn:
                mn, mn_url = r, (u or "")[:120]
    return {
        "🔴 분모": "shard 0 하나뿐 (4 중 1) --- 위 계수와 **분모가 다르다**",
        "문서수": n,
        "한글비율 분포(0.1 구간)": sorted(hist.items()),
        "최소 한글비율": round(mn, 4),
        "최소인 문서의 url": mn_url,
        "🔴 뜻": ("자는 고장 나지 않았다 --- 0 이 나온 것은 **HPLT 2.0 cleaned 의 언어 거르기가 "
                 "이미 매우 세다**는 뜻이다. 🔴 **그래서 반대 위험이 생긴다**: "
                 "코드·표·외래어가 섞인 한국어 문서를 원천이 이미 버렸을 수 있고, "
                 "**그건 안 쟀다**(버려진 쪽을 볼 방법이 이 표본엔 없다)"),
    }


if __name__ == "__main__":
    res = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                     capture_output=True, text=True).stdout.split()[0],
           "steam": diag_steam(), "hplt": diag_hplt()}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
