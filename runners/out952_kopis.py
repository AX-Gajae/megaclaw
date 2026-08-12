# -*- coding: utf-8 -*-
"""③ 측정 — KOPIS(공연예술통합전산망) OpenAPI **생존 조사** (노트 952 [수집]).

🔴 **키가 없다.** 그래서 이 러너가 재는 것은 딱 하나 —— **엔드포인트가 살아 있는가**.

가르는 자(실측으로 확인했다):
  살아 있다  → HTTP **200** + XML `<returncode>02</returncode>
               <errmsg>SERVICE KEY IS NOT REGISTERED ERROR</errmsg>`
  없다      → HTTP **404** + JSON `{"success":false,"code":404,...}`

🔴 **예상 행수를 적지 않는다.** 키가 없어 목록 크기를 아무도 못 쟀다 —— 「모른다」다.
🔴 robots.txt 를 받아서 읽었다: `User-agent: * / Allow: /` (위장 안 했다 · UA 에 우리 정체를 밝힌다).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_kopis.json"
BASE = "https://www.kopis.or.kr/openApi/restful/"
UA = "world_model-lab/952 (research; contact alexlee@sweetspot.co.kr)"

#: 🔴 **이 목록은 내가 만든 후보다.** 지평 조사의 「19개」를 그대로 옮긴 것이 아니다 ---
#: 그쪽 목록의 실물을 못 봤으므로 **내 분모는 내 후보 수**이고, 둘을 이어 붙이지 않는다(조항 60).
#: 대조군(존재하지 않는 이름)을 **일부러 둘** 넣어 자가 404 를 실제로 내는지 확인한다.
CAND = [
    ("pblprfr", "공연목록", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("pblprfr/PF000001", "공연상세", ""),
    ("prfplc", "공연시설목록", "cpage=1&rows=1"),
    ("prfplc/FC000001", "공연시설상세", ""),
    ("boxoffice", "예매상황판", "ststype=day&date=20260810"),
    ("prfstsTotal", "공연통계 전체", "ststype=month&stdate=202601&eddate=202601"),
    ("prfstsCate", "공연통계 장르별", "ststype=month&stdate=202601&eddate=202601"),
    ("prfstsArea", "공연통계 지역별", "ststype=month&stdate=202601&eddate=202601"),
    ("prfstsPrfBy", "공연별 통계", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("prfstsPrfByFct", "시설별 통계", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("prffest", "축제목록", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("prfnew", "신규등록공연", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("prfawad", "수상작", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("mnfprfr", "지역별 공연", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("boxStatsTotal", "예매통계 전체", "ststype=month&stdate=202601&eddate=202601"),
    ("boxStatsCate", "예매통계 장르", "ststype=month&stdate=202601&eddate=202601"),
    ("boxStatsArea", "예매통계 지역", "ststype=month&stdate=202601&eddate=202601"),
    ("prfstsTotalDay", "일별 통계", "stdate=20260101&eddate=20260131"),
    ("prfstsTotalMonth", "월별 통계", "stdate=202601&eddate=202601"),
    ("prfprd", "공연기간", "stdate=20260101&eddate=20260131&cpage=1&rows=1"),
    ("relateList", "관련목록", "cpage=1&rows=1"),
    # 🔴 대조군 --- 존재할 리 없는 이름 둘
    ("zzz_nosuch_endpoint_A", "🔴 대조군(없어야 한다)", "cpage=1&rows=1"),
    ("prfNoSuchThing_B", "🔴 대조군(없어야 한다)", "cpage=1&rows=1"),
]

FAKE_KEY = "TESTKEYNOTREAL0000"


def _get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read(900).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, (e.read(900) or b"").decode("utf-8", "ignore")
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def classify(code, body: str) -> str:
    if code == 404:
        return "없다(404)"
    if code == 200 and "SERVICE KEY IS NOT REGISTERED" in body:
        return "살아있다(키없음)"
    if code == 200 and "<returncode>" in body:
        m = re.search(r"<errmsg>(.*?)</errmsg>", body)
        return "살아있다(다른오류: %s)" % (m.group(1)[:60] if m else "?")
    if code == 200:
        return "🔴 200 인데 모양을 모르겠다"
    if code is None:
        return "🔴 못 불렀다(예외)"
    return "🔴 HTTP %s" % code


def main() -> int:
    res = {
        "시각": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "원천": "KOPIS 공연예술통합전산망 OpenAPI",
        "라이선스": "data.go.kr 등록본 「이용허락범위 제한 없음」 (지평 조사 인용 · 🔴 이 러너가 직접 확인한 것이 아니다)",
        "robots": "https://www.kopis.or.kr/robots.txt → `User-agent: * / Allow: /` (직접 받아 읽었다)",
        "🔴 분모": "내가 만든 후보 %d 개(대조군 2 포함). 지평 조사의 「19」와 **이어 붙이지 않는다**" % len(CAND),
        "🔴 예상 행수": "모른다 — 키가 없어 목록 크기를 못 쟀다. 안 쟀다",
        "엔드포인트": [],
    }
    for name, what, qs in CAND:
        url = BASE + name + "?service=" + FAKE_KEY + ("&" + qs if qs else "")
        code, body = _get(url)
        res["엔드포인트"].append({
            "이름": name, "무엇": what, "HTTP": code,
            "판정": classify(code, body), "본문머리": body[:160],
        })
        print("%-24s %-6s %s" % (name, code, classify(code, body)), flush=True)

    live = [e for e in res["엔드포인트"] if e["판정"].startswith("살아있다")
            and not e["무엇"].startswith("🔴 대조군")]
    dead = [e for e in res["엔드포인트"] if e["판정"] == "없다(404)"
            and not e["무엇"].startswith("🔴 대조군")]
    ctrl = [e for e in res["엔드포인트"] if e["무엇"].startswith("🔴 대조군")]
    res["집계"] = {
        "후보(대조군 제외)": len(CAND) - len(ctrl),
        "살아있다": len(live), "없다(404)": len(dead),
        "그밖": len(CAND) - len(ctrl) - len(live) - len(dead),
        "살아있는 이름": [e["이름"] for e in live],
        "없는 이름": [e["이름"] for e in dead],
        "🔴 대조군이 실제로 404 를 냈나": all(e["판정"] == "없다(404)" for e in ctrl),
        "대조군 결과": [(e["이름"], e["판정"]) for e in ctrl],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["집계"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
