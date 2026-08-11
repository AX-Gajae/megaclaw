# -*- coding: utf-8 -*-
"""노트 941(탐색) — 판 유보 3,775 의 **개체 키를 도메인마다 뽑아 파일로 남긴다**.

**왜 이게 먼저인가.** 941 은 새 원천을 받는 사이클이고, 조항 59 가 요구하는
문장은 *"받았다"* 가 아니라 **"받은 것이 유보 3,775 중 몇 행에 붙나"** 다.
그런데 저장소에 **유보 행의 키 목록을 파일로 가진 것이 없었다** --- 행 수(3,775)만
있고 *어느 행인지*는 매번 하네스를 다시 돌려야 나왔다. 그래서 새 원천이 오면
붙는 행을 못 세고 "안 셌다" 로 끝났다(915 가 그랬다).

**행 순서 규약**(state/candidates.py · lab/wikiaxes.py `_ids`):
아홉 도메인은 ``data/state/{d}_axes.json`` 의 키 순서가 곧 행 순서다.
나머지 셋은 아니다 --- 영화는 ``kobis_axes.json`` · 팝업은 ``trendaxes._popup_ids``
(🔴 ``set_wide(False)`` + 등급 A~E · 판의 ``wide_pop="grades"`` 와 같은 설정) ·
아이돌은 ``idolset._rows(mode_wide=True, wide_post=True)``.

🔴 **이 셋을 기본값으로 부르면 길이가 안 맞는다**(팝업 75 또는 189 대 89 ·
아이돌 81 대 173). 길이가 안 맞는 채로 zip 하면 **키가 조용히 밀린다** ---
그래서 도메인마다 ``len(키) == len(행)`` 을 단언하고, 안 맞으면 그 도메인을
**"키 못 뽑음"** 으로 적는다(0 이 아니다).

산출물: ``runners/out941_holdout.json``
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

import numpy as np  # noqa: E402

T = 2025.0
OUT = ROOT / "runners/out941_holdout.json"


def main() -> dict:
    t0 = time.time()
    import ff753 as FF                                   # noqa: E402
    from lab import wikiaxes as WA, trendaxes as TA, idolset as IS  # noqa: E402

    data = FF.shell(FF.base())

    ids = WA._ids()                                      # 아홉 도메인
    ids["영화"] = list(json.loads((ROOT / "data/state/kobis_axes.json").read_text()))
    TA.set_wide(False)
    TA.set_grades(("A", "B", "C", "D", "E"))             # 판의 wide_pop="grades"
    ids["팝업"] = list(TA._popup_ids())
    ids["아이돌"] = [r.get("record_id") or r.get("id")
                  for r in IS._rows(mode_wide=True, wide_post=True)]

    per, keys, bad = {}, {}, []
    for d in sorted(data.dom):
        m = data.rows(d, post=True, labeled=True, T=T)
        kk = ids.get(d)
        ok = kk is not None and len(kk) == len(m)
        per[d] = {"행": int(len(m)), "유보": int(m.sum()),
                  "키 수": (len(kk) if kk is not None else None),
                  "🔴 키 길이 == 행 수": bool(ok)}
        if ok:
            keys[d] = [kk[i] for i in np.where(m)[0]]
        else:
            bad.append(d)

    tot = sum(v["유보"] for v in per.values())
    got = sum(len(v) for v in keys.values())
    res = {
        "노트": 941, "레인": "탐색", "무엇": "판 유보 3,775 의 개체 키를 파일로 고정",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "초": round(time.time() - t0, 1),
        "도메인별": per,
        "유보 합": tot, "🔴 유보 합 == 3775": tot == 3775,
        "키를 뽑은 행": got, "🔴 키 == 유보 합": got == tot,
        "키 못 뽑은 도메인": bad,
        "유보키": keys,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"유보 합 {tot} · 키 {got} · 못 뽑은 도메인 {bad} · {res['초']}초")
    return res


if __name__ == "__main__":
    main()
