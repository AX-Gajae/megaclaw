# -*- coding: utf-8 -*-
"""③-다 — KOPIS **키 발급을 기계가 끝낼 수 있나** (노트 952 [수집] · 사전등록 P11).

🔴 **「막혔다」를 주장하려면 막히는 것을 봐야 한다.** 이 러너는 키 신청 통로를 실제로
두드려 보고, **어디서 어떻게 막히는지**를 적는다. 「안 해 봤다」를 「막혔다」로 쓰지 않는다.

🔴 로그인·회원가입·자동입력을 **시도하지 않는다**. 폼을 기계로 제출하는 것은 이 저장소의
정문 원칙 밖이다 --- 여기서 재는 것은 **사람 없이 되는가**뿐이고, 답이 「아니오」면 그대로 적는다.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_kopiskey.json"
UA = "world_model-lab/952 (research; contact alexlee@sweetspot.co.kr)"

CAND = [
    ("메인", "https://www.kopis.or.kr/por/main/main.do"),
    ("오픈API 안내(추정)", "https://www.kopis.or.kr/por/openApi/openApiIntro.do"),
    ("키 신청(추정 ㄱ)", "https://www.kopis.or.kr/por/openApi/openApiKey/openApiKeyList.do"),
    ("키 신청(추정 ㄴ)", "https://www.kopis.or.kr/por/openapi/openApiKeyApply.do"),
    ("키 신청(추정 ㄷ)", "https://www.kopis.or.kr/por/cs/openApi/openApiKeyIsse.do"),
    ("개발 가이드(추정)", "https://www.kopis.or.kr/por/openApi/openApiGuide.do"),
    ("data.go.kr 등록본", "https://www.data.go.kr/data/15000488/openapi.do"),
]


def _get(url: str, nbytes: int = 400_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        r = urllib.request.urlopen(req, timeout=45)
        return r.status, r.read(nbytes).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, (e.read(4000) or b"").decode("utf-8", "ignore")
    except Exception as e:                                        # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def _text(b: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b)))


def main() -> int:
    res = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "🔴 무엇을 재는가": "키 발급을 **사람 없이** 끝낼 수 있나. 폼 제출·회원가입은 안 한다",
        "시도": [],
    }
    for what, url in CAND:
        code, body = _get(url)
        t = _text(body) if isinstance(body, str) else ""
        row = {"무엇": what, "url": url, "HTTP": code, "바이트": len(body) if body else 0}
        if code == 200:
            row["폼 개수"] = len(re.findall(r"<form[^>]*>", body))
            row["입력칸 개수"] = len(re.findall(r"<input[^>]*>", body))
            row["말 나옴"] = [w for w in ("신청", "발급", "인증", "이메일", "회원가입",
                                          "로그인", "동의", "자동등록방지", "captcha")
                              if w in t or w in body]
            # 🔴 껍데기를 성공으로 안 읽는다 --- 문화빅데이터플랫폼 사례(HTTP 200 · 목록 0건)
            row["🔴 껍데기 의심"] = (len(re.findall(r"<form[^>]*>", body)) == 0
                                    and "styles-module" in body)
        else:
            row["본문머리"] = t[:160]
        res["시도"].append(row)
        print("%-22s %-5s forms=%s" % (what, code, row.get("폼 개수")), flush=True)

    live = [r for r in res["시도"] if r["HTTP"] == 200]
    withform = [r for r in live if r.get("폼 개수", 0) > 0]
    res["집계"] = {
        "후보": len(CAND),
        "HTTP 200": len(live),
        "404 등": len(CAND) - len(live),
        "🔴 폼이 실제로 있는 쪽": len(withform),
        "폼 있는 곳": [r["무엇"] for r in withform],
    }
    blocked = len(withform) == 0
    res["🔴 판정"] = {
        "키를 얻었나": False,
        "막혔나": blocked,
        "🔴 어떻게 막혔나": (
            "KOPIS 포털이 **자바스크립트로 그리는 SPA** 다 --- 받아 온 HTML 에 `<form>` 이 "
            "**0개**이고 클래스 이름이 `styles-module-scss-module__…` 다. 키 신청 화면의 "
            "실제 주소를 정적 HTML 에서 못 찾았고, 추정 주소는 전부 404 였다. "
            "🔴 **그러므로 「엔드포인트가 없다」가 아니라 「내가 못 찾았다」이다**(조항 59). "
            "사람이 브라우저로 들어가면 되는 일일 가능성이 높다"
            if blocked else "막히지 않았다 --- 폼을 찾았다"),
        "🔴 안 한 것": [
            "회원가입·로그인을 **안 했다**(정문 원칙 · 자동 폼 제출 안 한다)",
            "브라우저 렌더링을 **안 했다**(JS 실행 없음)",
            "data.go.kr 쪽 신청 경로를 **안 밟았다**",
            "🔴 **사람이 신청하면 되는지는 안 쟀다** --- 이 러너가 답할 수 있는 물음이 아니다",
        ],
        "다음이 할 일": "🔴 **사람이 KOPIS 포털에서 이름·이메일로 키를 신청한다.** "
                        "키가 오면 `data/lab/sources.json` 의 `kopis` 항목에서 "
                        "`모듈` 을 채우고 `켬` 을 true 로 바꾸면 끝이다 --- 그게 등기부의 요점이다",
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["집계"], ensure_ascii=False, indent=1))
    print("막혔나:", blocked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
