"""만화 ``media_push`` 를 다시 만든다 --- 자리가 아니라 id 로(노트 368).

**왜 다시 만드나**(노트 365 · 366). 이 축은
``state/media_push_fill.json`` 이 채우는데, 그 파일을 만든 스크립트가
저장소에 없다. 값이 21개 구간으로 뭉쳐 있어(0.0419 · 0.1515 · 0.3077 …)
눈금을 역산하는 것은 추측이 된다. 그리고 읽는 쪽이 **자리**로 붙이는 탓에
만화 행이 1,789 에서 2,041 로 늘면 길이가 어긋나 축이 통째로 사라진다.

**끄고 지나갈 수는 없다** --- 노트 366 이 재 보니 끄면 판 $-0.0025$
(SD 0.0026 · 3/12)로 그 축이 일하고 있다.

**그래서 개념만 남기고 다시 만든다.** 노트 108 이 적어 둔 개념은
``공식 외부 채널 수와 예고편 유무''다. AniList 에서 2,041건을 다시 받아
(``data/state/manga_links.json``) 같은 개념으로 만든다:

    raw   = 외부 링크 수 + (예고편 있으면 1)
    값    = scale01(log2(raw + 1), 0, 4)

눈금은 ``ingest/manga_axes.venue_prominence`` 와 같은 관례다(작가 사전
작품 수에 쓰는 것) --- **저장소 안에 근거가 있는 눈금을 쓴다.**

받은 분포: 외부 링크 수 중앙 3(분위 1·1·3·4·7·13) · 예고편 24.9%.

**id 로 적는다.** 옛 파일도 ``ids`` 를 갖고 있었는데 읽는 쪽이 안 썼다 ---
아홉 번째 갈라진 목록이 그것이다(노트 365).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

LINKS = Path("data/state/manga_links.json")
OUT = Path("data/state/media_push_fill2.json")


def scale01(v, lo, hi):
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def build() -> dict:
    if not LINKS.exists():
        return {}
    raw = json.loads(LINKS.read_text())
    vals, ids = [], []
    for mid, m in raw.items():
        n = len(m.get("externalLinks") or []) + (1 if m.get("trailer") else 0)
        ids.append("MG-%s" % mid)
        vals.append(scale01(float(np.log2(n + 1)), 0.0, 4.0))
    return {"만화": {"ids": ids, "value": vals, "mask": [1.0] * len(ids)}}


if __name__ == "__main__":
    b = build()
    d = b.get("만화") or {}
    v = np.array(d.get("value") or [])
    print("만화 media_push 다시 만듦: %d행" % len(v))
    if len(v):
        print("  값 분위:", [round(float(np.percentile(v, q)), 3)
                          for q in (10, 25, 50, 75, 90)])
        print("  서로 다른 값 %d" % len(np.unique(v)))
    OUT.write_text(json.dumps(b, ensure_ascii=False, indent=1))
    print("  저장:", OUT)
