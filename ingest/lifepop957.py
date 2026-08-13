# -*- coding: utf-8 -*-
"""노트 957 · 층 ② 적재기 — **서울 생활인구 250m 를 「우리 쌍이 쓰는 격자 23개」로만 좁혀 뽑는다.**

🔴 왜 좁히나: 19개 zip 은 압축 8.5 GB · 풀면 수십 GB 다. 우리가 쓰는 격자는 **23개**뿐이고
(사전등록 §0), 전량을 풀면 예산을 넘긴다. **그래서 격자를 먼저 정하고 그 줄만 뽑는다.**

두 걸음이다.

  **ㄱ** (셸) `unzip -p <zip> | LC_ALL=C grep -F -f <격자패턴> >> /tmp/lp957_hits.csv`
        패턴은 `","<격자>","` 를 **CP949 바이트**로 적은 것이다(`runners/layers957.py:build_patterns`).
        🔴 이 걸음은 **줄을 고를 뿐 값을 안 만든다.**
  **ㄴ** (이 파일) 뽑힌 줄을 파싱해 `격자 × 날짜 × 시각` 을 만든다.

🔴 규율(사전등록 §3 층 ②)
  · 행의 단위는 격자가 아니라 **(행정동, 격자) 쌍**이다 — 격자 값은 **행정동을 넘어 합산**한다.
  · 마스킹 `*` 는 「≤3 이라 가렸다」이지 0 이 아니다 — 0 으로 접되 **건수를 따로 센다**.
  · 인코딩 **CP949** · 필드는 큰따옴표로 싸여 있고 `행정동코드`·`시간` 은 공백 패딩이다.
  · 🔴 **판 라벨을 한 비트도 안 연다.**

산출물: `runners/out957_lifepop.json.gz` (격자 → 날짜 → 시각 24칸)
        `runners/out957_lifepop_meta.json` (배선 검사 W2 의 수)

사용: python3 -m ingest.lifepop957
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

HITS = Path(os.environ.get("LP957_HITS", "/tmp/lp957_hits.csv"))
OUT = ROOT / "runners/out957_lifepop.json.gz"
META = ROOT / "runners/out957_lifepop_meta.json"


def main() -> dict:
    if not HITS.exists():
        raise SystemExit(f"🔴 없다: {HITS} — 걸음 ㄱ(셸)을 먼저 돌려라")
    grids = json.loads((ROOT / "runners/out957_grids.json").read_text())["격자"]
    want = set(grids)

    V: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0] * 24))
    rows = masked = bad = off = 0
    dongs: dict[str, set] = defaultdict(set)
    with open(HITS, "rb") as f:
        for raw in f:
            rows += 1
            try:
                fs = raw.decode("cp949").rstrip("\r\n").split('","')
                day = fs[0].lstrip('"').strip()
                hour = int(fs[1].strip())
                dong = fs[2].strip()
                grid = fs[3].strip()
                v = fs[4].strip()
            except (UnicodeDecodeError, IndexError, ValueError):
                bad += 1
                continue
            if grid not in want:              # grep 이 남의 줄을 물었나
                off += 1
                continue
            if v == "*":
                masked += 1
                v = "0"
            try:
                val = float(v)
            except ValueError:
                bad += 1
                continue
            V[grid][day][hour] += val
            dongs[grid].add(dong)

    days = sorted({d for g in V for d in V[g]})
    out = {g: {d: V[g][d] for d in sorted(V[g])} for g in sorted(V)}
    with gzip.open(OUT, "wt") as f:
        json.dump(out, f, ensure_ascii=False)

    hole = [(g, d) for g in grids for d in days if d not in out.get(g, {})]
    meta = {
        "노트": 957,
        "무엇": "층 ② 생활인구 적재 — 배선 검사 W2",
        "🔴 뽑은 줄": rows,
        "🔴 파싱 실패": bad,
        "🔴 우리 격자가 아닌 줄(grep 오검출)": off,
        "🔴 마스킹 `*` 건수(≤3 이라 가린 것 · 0 으로 접었다)": masked,
        "격자 수": len(out),
        "사전등록이 정한 격자 수": len(grids),
        "날짜 수": len(days),
        "날짜 범위": [days[0], days[-1]] if days else None,
        "🔴 (격자,날짜) 결측": len(hole),
        "🔴 (격자,날짜) 결측 예시 다섯": hole[:5],
        # 🔴 dict 로 두면 ⑤′ 절 3 이 「`통과` 키 없는 절」로 세므로 목록으로 낸다
        "격자별 행정동 수(합산했다는 증거)": ["%s:%d" % (g, len(dongs[g])) for g in sorted(dongs)],
        "🔴 시각 24칸이 아닌 (격자,날짜)": sum(
            1 for g in out for d in out[g] if len(out[g][d]) != 24),
        "통과": (len(out) == len(grids) and bad == 0 and off == 0 and len(hole) == 0),
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in meta.items()
                      if k != "격자별 행정동 수(합산했다는 증거)"}, ensure_ascii=False, indent=1))
    return meta


if __name__ == "__main__":
    main()
