# -*- coding: utf-8 -*-
"""노트 941(탐색) — **여론·댓글 본문 후보 호스트의 `robots.txt` 를 실제로 받아 읽는다.**

**왜 이것부터인가.** `docs/수집계획.md` 의 후보 16개에 **댓글·여론이 0건**이다
(`grep -cniE "댓글|여론" docs/수집계획.md` → **0**). 200시간 계획에서 통째로 빠져 있다.
그리고 크롤 금지가 2026-08-12 에 풀렸는데, 🔴 **푼 뒤에도 「무엇이 실제로 열리나」를
아무도 안 세었다.** 이 모듈이 그 자리를 센다.

🔴 **이 모듈은 본문을 안 긁는다.** `robots.txt` 하나씩만 받아 **판정 가능한 형태로
기록**한다 --- *"막혔다"* 와 *"안 열어봤다"* 를 가르기 위한 것이다(조항 59).
실제 수집은 **허용으로 확인된 경로에서만** 별도 모듈이 한다.

각 호스트마다 적는 것:
  · HTTP 상태 · 바이트 · `User-agent: *` 블록의 `Disallow` 전량
  · 우리가 노리는 경로가 그 `Disallow` 에 걸리나(접두사 대조)
  · `Crawl-delay` 가 있으면 그 값(🔴 **있으면 그것을 따른다**)

쓰는 법::  python3 -m ingest.robots941
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/ingest/robots941"
UA = ("sweetspot-world-model/1.0 (research; alexlee@sweetspot.co.kr) "
      "note941 robots-check")
SLEEP = 1.5

#: (호스트, 노리는 경로, 어느 도메인의 여론인가, 메모)
HOSTS = [
    ("store.steampowered.com", "/appreviews/570", "게임",
     "Steamworks 문서에 공개된 스토어 엔드포인트 · 키 없음"),
    ("www.metacritic.com", "/game/", "게임·영화", "유저 평점·평문"),
    ("myanimelist.net", "/anime/1/reviews", "애니·세계애니", "유저 리뷰 본문"),
    ("graphql.anilist.co", "/", "세계애니·만화", "공개 GraphQL · 키 없음"),
    ("anilist.co", "/anime/1/reviews", "세계애니·만화", "리뷰 페이지"),
    ("comic.naver.com", "/webtoon/detail", "웹툰", "회차 댓글"),
    ("apis.naver.com", "/commentBox/cbox/", "웹툰·뉴스",
     "🔴 내부 댓글 API — robots 와 별개로 약관 확인 필요"),
    ("news.naver.com", "/main/read.naver", "공통", "기사 댓글"),
    ("www.youtube.com", "/watch", "아이돌·공통", "영상 댓글"),
    ("www.reddit.com", "/r/all/comments/", "공통(영어)", "공개 JSON"),
    ("api.tumblbug.com", "/v1/projects", "펀딩", "후원자 응원 댓글"),
    ("www.aladin.co.kr", "/shop/wproduct.aspx", "도서", "구매자 리뷰"),
    ("itunes.apple.com", "/kr/rss/customerreviews/", "모바일",
     "앱스토어 리뷰 RSS · 키 없음"),
    ("pedia.watcha.com", "/ko-KR/contents", "영화", "코멘트"),
    ("www.kobis.or.kr", "/kobis/business/main/main.do", "영화",
     "이미 쓰는 호스트 — 대조군"),
    ("gall.dcinside.com", "/board/lists", "공통(커뮤니티)", "게시판 본문"),
    ("theqoo.net", "/", "공통(커뮤니티)", "게시판 본문"),
    ("www.instiz.net", "/", "공통(커뮤니티)", "게시판 본문"),
]


def parse(txt: str) -> dict:
    """`User-agent: *` 블록만 뽑는다. 🔴 다른 UA 블록은 우리에게 안 걸린다."""
    star, cur, delay = [], False, None
    other = 0
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        kl = k.lower()
        if kl == "user-agent":
            cur = (v == "*")
            if not cur:
                other += 1
            continue
        if not cur:
            continue
        if kl == "disallow" and v:
            star.append(v)
        elif kl == "allow" and v:
            star.append("ALLOW " + v)
        elif kl == "crawl-delay":
            delay = v
    return {"Disallow(*)": [x for x in star if not x.startswith("ALLOW ")],
            "Allow(*)": [x[6:] for x in star if x.startswith("ALLOW ")],
            "Crawl-delay(*)": delay, "다른 UA 블록 수": other}


def hits(path: str, dis: list) -> list:
    """경로가 걸리는 Disallow 규칙(접두사 대조 · `*` 는 앞부분만 본다).

    🔴🔴 **이 함수는 틀렸다. 새로 쓰지 마라 — `runners/out942_robots.rfc9309` 를 써라.**
    노트 942(수리)가 RFC 9309 규격 예제 **32건 중 10건을 틀린다**는 것을 실측했다
    (`runners/out942_robots.json` → `배선·정확도 검사`). 틀리는 방향은 **전부
    「안 막힌 것을 막혔다」**이고, 그래서 941 의 「막힘 6」이 실제로는 **5** 였다.
    🔴 **본문(logic)은 일부러 안 고친다** — `runners/out941_robots.json` 이 동결물이고
    이 함수가 그 수를 낸 그 함수여야 942 의 「옛/새 나란히」 대조가 성립한다.
    """
    out = []
    for d in dis:
        pat = d.split("*")[0]
        if pat and path.startswith(pat):
            out.append(d)
        elif d == "/":
            out.append(d)
    return out


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, n_ok, n_bad = [], 0, 0
    for host, path, dom, memo in HOSTS:
        url = f"https://{host}/robots.txt"
        r = {"호스트": host, "노리는 경로": path, "도메인": dom, "메모": memo}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=45)
            body = resp.read()
            r["HTTP"] = resp.status
            r["바이트"] = len(body)
            txt = body.decode("utf-8", "replace")
            (OUT / f"{host}.robots.txt").write_text(txt)
            r.update(parse(txt))
            h = hits(path, r["Disallow(*)"])
            r["🔴 노리는 경로가 막히나"] = bool(h)
            r["걸린 규칙"] = h
            n_ok += 1
        except urllib.error.HTTPError as e:
            r["HTTP"] = e.code
            r["🔴 노리는 경로가 막히나"] = None
            r["사유"] = (f"robots.txt HTTP {e.code}"
                       + (" — 선언 없음" if e.code == 404 else ""))
            n_bad += 1
        except Exception as e:                                # noqa: BLE001
            r["🔴 노리는 경로가 막히나"] = None
            r["사유"] = type(e).__name__
            n_bad += 1
        rows.append(r)
        print(f"  {host} → {r.get('HTTP')} 막힘={r.get('🔴 노리는 경로가 막히나')}",
              flush=True)
        time.sleep(SLEEP)

    blocked = [x["호스트"] for x in rows if x.get("🔴 노리는 경로가 막히나") is True]
    openh = [x["호스트"] for x in rows if x.get("🔴 노리는 경로가 막히나") is False]
    unk = [x["호스트"] for x in rows if x.get("🔴 노리는 경로가 막히나") is None]
    res = {
        "노트": 941, "레인": "탐색",
        "무엇": "여론·댓글 본문 후보 호스트의 robots.txt 전수 — 🔴 본문은 안 긁었다",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "초": round(time.time() - t0, 1),
        "호스트 수": len(HOSTS), "robots 받음": n_ok, "못 받음": n_bad,
        "🔴 받음+못받음 == 호스트": n_ok + n_bad == len(HOSTS),
        "🔴 노리는 경로가 막힌 호스트": blocked,
        "🔴 안 막힌 호스트": openh,
        "🔴 모른다(robots 를 못 읽었다)": unk,
        "수": {"막힘": len(blocked), "안 막힘": len(openh), "모른다": len(unk),
              "합 == 호스트": len(blocked) + len(openh) + len(unk) == len(HOSTS)},
        "🔴 robots 가 허용해도 이용약관은 따로다": (
            "이 표는 robots.txt 만 읽은 것이다. 약관·로그인 담벼락은 "
            "**호스트마다 따로 확인해야 하고 이 사이클은 안 했다**"),
        "전수": rows,
        "저장": str(OUT.relative_to(ROOT)),
    }
    (ROOT / "runners/out941_robots.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "전수"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
