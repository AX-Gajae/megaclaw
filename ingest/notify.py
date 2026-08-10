"""사이클 결과를 **슬랙 DM 으로** 보낸다 (노트 889).

**왜 필요한가.** 사용자 지시(2026-08-10): *"루프 안 끊어지게 루프 전체 한번 다시
확인하고 내 슬랙으로 메세지도 잘 오게끔 한다음 크론 돌려."*

크론으로 돌리면 **아무도 안 본다** --- 그게 2026-08-09 에 실측한 것 전부다.
`forward_run.sh` 가 두 번 죽어 있는 걸 2주 동안 몰랐고, 고친 뒤에도 종료 코드
0 뒤에 실패가 숨어 있었다. 크론을 다시 켜려면 **결과가 사람에게 도착해야** 한다.
이 모듈이 그 마지막 한 칸이다.

**이 모듈의 규칙 둘.**

  ① **실패해도 루프를 안 죽인다.** 알림은 곁다리다 --- 슬랙이 죽었다고 수집이
     멈추면 본말이 뒤집힌다. 모든 예외를 삼키고 `{"보냄": False, "사유": ...}` 를
     돌려준다. 다만 **조용히 삼키지는 않는다** --- 사유를 표준출력에 찍는다.
  ② **토큰은 읽기만 한다.** `/Users/ax/.openclaw` 는 읽기 전용 제약이다
     (상시 제약 · `paper/harness.py` 와 같은 경로를 같은 방식으로 읽는다).

`paper/harness.py` 는 **PDF 첨부**용이고 이쪽은 **본문 한 통**이다. 그 파일이
스텝 461~469 에서 당한 것(LaTeX 원문을 코멘트에 넣어 DM 이 소스코드로 도착)을
여기서 반복하지 않으려고, 본문 길이 상한을 두고 넘치면 **잘랐다고 적는다**.

    from ingest.notify import dm
    dm("사이클 열림 — 실패 0")
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

OPENCLAW = Path("/Users/ax/.openclaw/openclaw.json")   # 읽기 전용
DM_USER = "U0AJ82VJS3W"                                # Alex Lee
CAP = 3500                                             # 슬랙 본문 상한(넉넉히)


def _token() -> str:
    return json.loads(OPENCLAW.read_text())["channels"]["slack"]["botToken"]


def _api(method: str, data: dict, tok: str, tries: int = 3) -> dict:
    """**일시 실패에 안 죽는다.** 시스템 파이썬이 LibreSSL 2.8.3 이라
    TLS 핸드셰이크가 가끔 시간초과로 떨어진다(2026-08-10 실측 --- 같은 호출이
    바로 다음에 200 을 냈다). 크론에서 한 번 튕겼다고 그 사이클 보고가
    통째로 사라지면 안 되므로 짧게 물러서며 세 번 시도한다."""
    import time
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                f"https://slack.com/api/{method}",
                data=json.dumps(data).encode(),
                headers={"Authorization": f"Bearer {tok}",
                         "Content-type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=30) as f:
                return json.loads(f.read())
        except Exception as e:                       # TLS·망 일시 장애
            last = e
            time.sleep(2.0 * (i + 1))
    raise last


def dm(text: str, user: str = DM_USER) -> dict:
    """DM 한 통. **절대 예외를 밖으로 안 낸다.**"""
    try:
        if len(text) > CAP:
            # 잘랐다는 사실을 본문에 남긴다 --- 잘린 줄 모르면 없는 것과 같다
            text = text[:CAP] + f"\n… (본문 {len(text)}자 중 {CAP}자만 보냄)"
        tok = _token()
        conv = _api("conversations.open", {"users": user}, tok)
        if not conv.get("ok"):
            raise RuntimeError(f"conversations.open: {conv.get('error')}")
        r = _api("chat.postMessage",
                 {"channel": conv["channel"]["id"], "text": text,
                  "unfurl_links": False, "unfurl_media": False}, tok)
        if not r.get("ok"):
            raise RuntimeError(f"chat.postMessage: {r.get('error')}")
        return {"보냄": True, "ts": r.get("ts")}
    except Exception as e:
        # 삼키되 **조용히는 아니다**
        msg = f"{type(e).__name__}: {e}"
        print(f"⚠ 슬랙 알림 실패(루프는 계속한다): {msg}")
        return {"보냄": False, "사유": msg}


if __name__ == "__main__":
    import sys
    print(json.dumps(dm(sys.argv[1] if len(sys.argv) > 1 else "ingest.notify 시험"),
                     ensure_ascii=False))
