# -*- coding: utf-8 -*-
"""노트 966 [탐색] — KOPIS(공연) 원천의 **행수·열·날짜 범위만** 센다.

🔴 **탐색 레인이다. 판정 없다. 이 사이클의 결론에 안 들어간다**(`docs/방향.md` §5 규칙 1).

🔴 **왜 별도 파일인가 — 자백**: `runners/longmem966.py` 의 `explore_kopis()` 가
`.json`/`.jsonl` 만 열었고 KOPIS 는 **전부 `.jsonl.gz`** 라서 **행 0** 을 냈다.
「0 행」과 「안 읽었다」는 둘이다(조항 59). 그 자리를 고치면 `longmem966.py` 의
**코드 sha256 이 바뀌어** 단계 셋의 대조(`merge966.py`)가 깨지므로, 여기서 다시 센다.
"""
from __future__ import annotations

import collections
import glob
import gzip
import json
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out966_kopis.json"

per = collections.OrderedDict()
for p in sorted(glob.glob(str(ROOT / "data/ingest/kopis/*.jsonl.gz"))):
    n, keys, dates = 0, collections.Counter(), []
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:                                  # noqa: BLE001
                continue
            n += 1
            if isinstance(r, dict):
                keys.update(r.keys())
                for k in ("prfpdfrom", "prfpdto", "prfdt", "날짜"):
                    if r.get(k):
                        dates.append(str(r[k]))
    per[Path(p).name] = {
        "행": n,
        "열 이름": sorted(keys),
        "열 수": len(keys),
        "날짜 범위": ([min(dates), max(dates)] if dates else "날짜 열을 못 찾았다"),
    }

R = {"노트": 966, "레인": "🔴 **탐색 — 판정 없음 · 이 사이클의 결론에 안 들어간다**",
     "무엇": "KOPIS(공연) — 13번째 도메인 후보의 실물 확인. 🔴 **행수·열·날짜만 센다**",
     "파일별": per,
     "🔴 분모: 파일": len(per),
     "🔴 행 합": sum(v["행"] for v in per.values()),
     "🔴 이것이 도메인이 되려면": ("판의 12도메인처럼 `data/state/<도메인>_axes.json` 이 있어야 하고 "
                        "라벨 y 와 시작일이 있어야 한다. **지금은 원천이지 자료가 아니다**"
                        "(⓪-나 · 「받았다」와 「쓸 수 있다」는 둘이다)"),
     "🔴 이 사이클이 판정하지 않은 것": "이 원천이 판을 움직이나 — **안 쟀다. 967 의 후보일 뿐이다**"}
OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in R.items() if k != "파일별"}, ensure_ascii=False, indent=1))
for k, v in per.items():
    print(k, "행", v["행"], "열", v["열 수"], "날짜", v["날짜 범위"])
