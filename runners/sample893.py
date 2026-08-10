# -*- coding: utf-8 -*-
"""노트 893 표본 고정 — **측정 전에** 200 + 음성 20 을 뽑아 파일로 못박는다.

왜 따로 도는가: 목록의 sha256 을 사전등록에 적어야 하기 때문이다. 측정 코드가
표본을 만들면 '뽑고 나서 마음에 드는 것을 골랐나' 를 아무도 못 가른다.

층: `y_popularity` **삼분위**(상·중·하). 베이스 모델 탐침이 상위 4/4 · 중간 0/3 ·
하위 1/4 였다(`data/state/base_model_probe.json`) --- 우리 코퍼스의 값은 롱테일에
있는데 수확은 상위에 몰릴 것이므로 **층별로 따로 보고**한다.

음성 통제 20: 실재하지 않는 한글 제목. 기존 한글 제목의 **어절을 섞어** 만들고
실물 제목의 부분문자열이면 버린다. 기준일이 없으므로 **기증 레코드의 t_0 를
물려준다** --- 안 그러면 창을 못 만들어 '같은 파이프라인' 이 거짓이 된다.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
SEED = 893
KNOCK_EXCLUDE = {105778, 30002, 87216, 105398, 98436}   # 노크에 쓴 것 = 엿본 것


def main() -> dict:
    recs = json.load(open(ROOT / "data/state/manga_records.json", encoding="utf-8"))
    rows = [r for r in recs.values() if r.get("media_id") not in KNOCK_EXCLUDE]
    rows.sort(key=lambda r: (-r.get("y_popularity", 0), r["record_id"]))
    n = len(rows)
    cut = [rows[:n // 3], rows[n // 3:2 * n // 3], rows[2 * n // 3:]]
    names = ["상", "중", "하"]
    rng = random.Random(SEED)
    want = [67, 67, 66]
    sample = []
    for lab, grp, k in zip(names, cut, want):
        for r in rng.sample(grp, k):
            sample.append({"record_id": r["record_id"], "media_id": r["media_id"],
                           "층": lab, "title": r["title"],
                           "t_0": r["start_date"], "t_0 출처": "manga_records.start_date",
                           "y_popularity": r.get("y_popularity"), "country": r.get("country")})
    sample.sort(key=lambda x: x["record_id"])

    # ── 음성 통제 20 --- 한글 어절을 섞어 만든다
    kr = json.load(open(ROOT / "data/state/manga_kr.json", encoding="utf-8"))
    titles = [v["title"]["native"] for v in kr.values()
              if v.get("title", {}).get("native")]
    real = set(titles)
    toks = sorted({t for ti in titles for t in ti.split() if len(t) >= 2})
    rng2 = random.Random(SEED + 1)
    donors = rng2.sample(sample, 20)
    fakes, tries = [], 0
    while len(fakes) < 20 and tries < 5000:
        tries += 1
        q = " ".join(rng2.sample(toks, rng2.choice([2, 3])))
        if q in real or any(q in t or t in q for t in real) or q in [f["질의"] for f in fakes]:
            continue
        d = donors[len(fakes)]
        fakes.append({"record_id": f"FAKE-{len(fakes):02d}", "질의": q,
                      "t_0": d["t_0"], "t_0 출처": f"기증 {d['record_id']}",
                      "기증": d["record_id"], "층": "음성"})

    def sha(o) -> str:
        return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True
                                         ).encode()).hexdigest()

    out = {"무엇": "노트 893 시간축 파일럿의 표본 --- 측정 전에 고정했다",
           "씨앗": SEED, "모집단": len(recs), "노크 제외": sorted(KNOCK_EXCLUDE),
           "층 경계(y_popularity)": {"상 최소": cut[0][-1]["y_popularity"],
                                  "중 최소": cut[1][-1]["y_popularity"],
                                  "하 최소": cut[2][-1]["y_popularity"]},
           "층 크기(모집단)": [len(c) for c in cut],
           "표본": sample, "음성 통제": fakes,
           "sha256 표본": sha(sample), "sha256 음성": sha(fakes)}
    p = ROOT / "data/state/pilot893_sample.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"표본": len(sample), "음성": len(fakes),
                      "층별": {k: sum(1 for s in sample if s["층"] == k) for k in names},
                      "sha256 표본": out["sha256 표본"],
                      "sha256 음성": out["sha256 음성"],
                      "파일 sha256": hashlib.sha256(p.read_bytes()).hexdigest()},
                     ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
