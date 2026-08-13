# -*- coding: utf-8 -*-
"""노트 967 [수리·탐색] — **영화(KOBIS) 위키 일별이 왜 0 인가**.

966 은 도메인 게이트가 처음 붉게 떨어진 원인을 이렇게 진단했다 ---
*「`ingest/wikidaily941.py` 의 `PREFIX` 에 `KOBIS` 가 없다. 유보 406행(영화)이
원천 밖이다.」* 그리고 티처 #105 가 그 진단을 **옳다고 했다**.

🔴 **다시 세어 보니 그 진단은 틀렸다**(조항 60 --- 티처 수를 그대로 받아 쓰지 않는다).
`PREFIX` 는 `_lang_of()` 가 **캐시가 이미 있는 키의 언어**를 고를 때만 쓰인다.
`targets()` 는 그보다 **앞에서** `data/state/wiki_views/<키>.json` 이 없으면
`continue` 로 건너뛴다. 그러므로 `PREFIX` 에 한 줄을 더해도 **한 행도 안 는다.**

이 러너는 **판정을 안 한다**(수치만 낸다). 새 `통과` 키를 만들지 않는다 ---
조항 64 가 무는 자리를 안 만든다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out967_kobis.json"
VIEWS = ROOT / "data/state/wiki_views"


def _sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> dict:
    hold = json.loads((ROOT / "runners/out941_holdout.json")
                      .read_text(encoding="utf-8"))["유보키"]
    from ingest import wikidaily941 as W941
    from ingest import wiki_views as WV

    per = {}
    for d in sorted(hold):
        keys = hold[d]
        cached = page = 0
        for k in keys:
            p = VIEWS / (k + ".json")
            if not p.exists():
                continue
            cached += 1
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("page"):
                    page += 1
            except (json.JSONDecodeError, OSError):
                pass
        per[d] = {"유보키": len(keys), "🔴 wiki_views 캐시 파일": cached,
                  "🔴 그중 page(문서명)가 풀린 것": page,
                  "접두": sorted({k.split("-")[0] for k in keys})[:4]}

    ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text(encoding="utf-8"))
    one = ax[list(ax)[0]]
    wv_src = (ROOT / "ingest/wiki_views.py").read_text(encoding="utf-8")

    return {
        "노트": 967, "레인": "수리·탐색 · 🔴 판정 없음",
        "🔴 코드 sha256": _sha(__file__),
        "물음": "영화(KOBIS) 위키 일별이 0 인 진짜 병목은 무엇인가",

        "§1 도메인별 캐시 회계": per,

        "§2 🔴 966 의 진단을 검증한다": {
            "966 이 적은 것": ("`ingest/wikidaily941.py` 의 `PREFIX` 에 `KOBIS` 가 "
                          "없어서 유보 406행(영화)이 원천 밖이다"),
            "티처 #105 의 판정": "옳다고 했다(3순위)",
            "🔴 `PREFIX` 에 `KOBIS` 가 있나": "KOBIS" in W941.PREFIX,
            "🔴 `PREFIX` 의 열쇠": sorted(W941.PREFIX),
            "🔴 `PREFIX` 를 실제로 쓰는 자리": (
                "`_lang_of(rid, cached)` 하나뿐이다 --- 돌려주는 것은 `PREFIX[head][1]` "
                "(**언어**)이고 `[0]`(도메인)은 아무 데서도 안 읽는다"),
            "🔴 그런데 `targets()` 는 그 앞에서 무엇을 하나": (
                "`p = VIEWS / f\"{k}.json\"` 이 없으면 `continue` · 있어도 "
                "`c.get(\"page\")` 가 비면 `continue`. **언어를 고르는 데까지 못 간다**"),
            "🔴 영화 유보키 중 캐시 파일이 있는 것": per["영화"]["🔴 wiki_views 캐시 파일"],
            "🔴 그러므로 PREFIX 한 줄로 느는 행": 0,
            "🔴 판정": ("**966 의 진단은 틀렸고 티처 #105 는 그 틀린 진단을 승인했다.** "
                     "병목은 `PREFIX` 가 아니라 **영화가 위키 제목 해결 파이프라인에 "
                     "한 번도 들어간 적이 없다**는 것이다"),
        },

        "§3 🔴 진짜 병목": {
            "🔴 `ingest/wiki_views.SRC` 에 영화 항목이 있나": "영화" in WV.SRC,
            "SRC 의 열쇠": sorted(WV.SRC),
            "🔴 SRC 에 없는 판 도메인": sorted(set(hold) - set(WV.SRC)),
            "🔴 SRC 에 없지만 캐시는 있는 도메인": sorted(
                d for d in set(hold) - set(WV.SRC)
                if per[d]["🔴 wiki_views 캐시 파일"] > 0),
            "🔴 SRC 에도 없고 캐시도 0 인 도메인": sorted(
                d for d in set(hold) - set(WV.SRC)
                if per[d]["🔴 wiki_views 캐시 파일"] == 0),
            "⚠ 정직 신고 --- SRC 가 유일한 길은 아니다": (
                "시장팝업은 `SRC` 에 없는데 캐시가 **126** 개 있다. `wiki_views` 에는 "
                "`SRC` 를 안 쓰는 특별 경로가 둘 있다(`popup_items()`·`idol_items()`) "
                "--- `MKT` 키가 팝업 경로를 타고 들어갔다. **그러니 「SRC 에 없다」만으로는 "
                "「원천에 못 들어간다」가 안 된다**(조항 62 --- 차집합은 홀로 못 선다)"),
            "🔴 그래서 영화는 왜 0 인가 --- 직접 센다": {
                "`ingest/wiki_views.py` 안의 「영화」 언급": wv_src.count("영화"),
                "`ingest/wiki_views.py` 안의 「KOBIS」 언급": wv_src.upper().count("KOBIS"),
                "곁: 「시장팝업」 언급": wv_src.count("시장팝업"),
                "곁: 「팝업」 언급": wv_src.count("팝업"),
                "뜻": ("영화는 `SRC` 에도 없고 특별 경로 둘(`popup_items`·`idol_items`) "
                      "에도 없다. **어떤 길로도 제목이 안 풀린다** --- 그래서 캐시 0 이다"),
            },
        },

        "§4 고치려면 무엇이 있어야 하나": {
            "제목이 어디 있나": "data/state/kobis_axes.json 의 `name`(한국어 제목)",
            "개봉일이 어디 있나": "같은 파일의 `release_date`",
            "개체 수": len(ax),
            "표본": {k: one[k] for k in ("name", "release_date") if k in one},
            "🔴 꼴이 다르다": ("`SRC` 의 다른 항목은 **레코드 목록 파일**을 가리키는데 "
                          "`kobis_axes.json` 은 **키로 색인된 dict** 다 --- 어댑터가 필요하다"),
            "필요한 세 걸음": [
                "① `ingest/wiki_views.SRC` 에 영화 항목 + dict 어댑터",
                "② 제목 해결(위키 검색 API · **HTTP 필요**)",
                "③ 일별 조회수 수확(**HTTP 필요**)"],
            "🔴 967 이 왜 안 했나": ("사전등록 §7 이 **HTTP 0** 을 미리 선언했다. "
                              "①은 코드만이라 할 수 있으나 ②③ 없이 ①만 넣으면 "
                              "**966 이 저지른 것과 같은 종류의 죽은 배선**이 된다"),
        },

        "🔴 끝 시각(UTC)": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


if __name__ == "__main__":
    R = main()
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1))
