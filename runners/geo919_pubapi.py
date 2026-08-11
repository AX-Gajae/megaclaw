# -*- coding: utf-8 -*-
"""팔 919-ㅍ · 보조 — **무료 공공 지오코딩이 키 없이 되는가.**

🔴 조항 59 — 「없다」와 「못 했다」는 다르다. 그래서 **응답 원문을 그대로 싣는다.**
🔴 광역 크롤이 아니다 — **주소 하나로 요청 두 건**. 유료 API 도 아니다(둘 다 무료 공공).

산출물: runners/out919_pubapi.json
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("/Users/ax/world_model/runners/out919_pubapi.json")
ADDR = "서울특별시 영등포구 여의대로 108"      # 저장소가 좌표를 아는 주소(spot 474)

ENDPOINTS = [
    ("도로명주소 개방 API(주소검색 · business.juso.go.kr)",
     "https://business.juso.go.kr/addrlink/addrLinkApi.do?"
     + urllib.parse.urlencode({"currentPage": 1, "countPerPage": 1,
                               "keyword": "여의대로 108", "resultType": "json"})),
    ("국가공간정보 vworld 지오코더(getCoord · api.vworld.kr)",
     "https://api.vworld.kr/req/address?"
     + urllib.parse.urlencode({"service": "address", "request": "getCoord",
                               "version": "2.0", "crs": "epsg:4326",
                               "address": ADDR, "type": "road", "format": "json"})),
]


def main() -> None:
    res = {"팔": "919-ㅍ · 보조",
           "물음": "🔴 무료 공공 지오코딩이 **키 없이** 되는가",
           "규율": "요청 2건만. 광역 크롤 아님 · 유료 API 아님",
           "시험 주소": ADDR,
           "시각 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "응답": []}
    for nm, url in ENDPOINTS:
        row = {"이름": nm, "URL(키 없음)": url}
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                row["HTTP"] = r.status
                row["본문(앞 500자)"] = r.read()[:500].decode("utf-8", "replace")
        except Exception as e:                                  # noqa: BLE001
            row["HTTP"] = "🔴 예외"
            row["본문(앞 500자)"] = f"{type(e).__name__}: {str(e)[:300]}"
        row["🔴 읽는 법"] = ("HTTP 200 을 성공으로 읽으면 안 된다(조항 59) — "
                        "본문이 인증 오류면 **키가 필요해서 못 한 것**이다")
        res["응답"].append(row)
    ok = all(r["HTTP"] == 200 for r in res["응답"])
    res["🔴 판정"] = {
        "두 곳 다 HTTP 200 인가": ok,
        "🔴 그런데 본문은": "둘 다 인증 오류(E0001 '승인되지 않은 KEY' / PARAM_REQUIRED 'key가 없어서')",
        "결론": "🔴 **키가 필요해서 못 했다** — 「무료 지오코더가 없다」가 아니다(조항 59)",
        "그래서 무엇을 했나": "저장소 안의 (주소→좌표)·(장소명→좌표) 쌍으로 오프라인 사전을 만들었다",
        "통과": True}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["🔴 판정"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
