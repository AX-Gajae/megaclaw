"""유튜브·웨이백에서 **키 없이** 긁는다(노트 640).

사용자가 상태층을 이렇게 정의했다: *"그 시기에 관측 가능한 모든 형태가 상태가
될 수 있다"*, 그리고 불변 법칙의 후보로 *"좋아요가 올라간다든지 추천 알고리즘의
모습이라든지 조회수가 올라간다든지 언제 어떻게 누가 누구한테 댓글을 쓴다든지"*
를 짚었다. 이 모듈은 그 두 가지를 **따로** 긁는다. 섞으면 안 되기 때문이다.

──────────────────────────────────────────────────────────────
**갈래 A — 상태 축.** 레코드에 붙일 값. 시간 게이트를 지켜야 한다.

  쓸 수 있는 것   오픈 **이전**에 올라온 영상의 **개수와 게시 빈도**.
                  ``publishedAt`` 은 정확하고 사후에 안 변한다.
  쓰면 안 되는 것 **지금 조회수.** 오늘 읽은 조회수는 오픈 이후에 쌓인 것까지
                  포함한다. 노트 149 가 위키 조회수에서 같은 함정을 피한
                  방식(오픈 이전 창만 자른다)을 여기서는 **쓸 수 없다** ---
                  유튜브 API 도 워치 페이지도 **시점별 조회수를 안 준다.**

  즉 유튜브에서 시간 게이트를 통과하는 상태 신호는 **양(개수)이지 세기(조회수)가
  아니다.** 이걸 안 가르면 미래를 보고 판이 오른다.

**갈래 B — 불변 법칙.** 레코드에 안 붙는다. 조회수·좋아요·댓글이 시간에 따라
어떻게 자라는지 그 **모양**을 배우는 자료다. 특정 팝업을 맞히는 데 안 쓰므로
시간 게이트가 아니라 **표본 대표성**이 문제다.

  여기서는 조회수 궤적을 실제로 **복원할 수 있다** --- 웨이백 머신이 워치
  페이지를 날짜별로 찍어 뒀다. 시험 결과(2026-08-05, ``dQw4w9WgXcQ``):

      2014-06   81,280,261
      2016-06  211,756,556
      2018-06  441,182,748
      2022-06 1,223,462,522

  **한계는 덮음이다.** 유명한 URL 만 촘촘히 찍혀 있다. 한국 팝업 하나의
  페이지는 스냅샷이 없거나 한둘이다. 그래서 이 경로는 **큰 것에만** 쓴다.

──────────────────────────────────────────────────────────────
**키가 왜 없나.** 유튜브 Data API 는 구글 클라우드 키가 필요하고 검색이
호출당 100 유닛이라 하루 100회다(무료 몫 10,000). 워치 페이지와 검색 페이지는
키도 쿼터도 없고, 채널 RSS(``feeds/videos.xml``)도 마찬가지다. 키가 생기면
``videos.list`` 가 1 유닛에 50건이라 훨씬 싸지므로 그때 갈아 끼운다.

쓰는 법::

    python3 -m ingest.social --search "성수 팝업" --n 40
    python3 -m ingest.social --traj "https://www.youtube.com/watch?v=..."
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/state/social"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}
SLEEP = 1.5          # 예의. 공개 페이지라도 두드리는 속도는 우리가 정한다


def _get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


# ── 갈래 A — 시간 게이트를 통과하는 것만 ────────────────────────
def yt_search(q: str, n: int = 40) -> list[str]:
    """검색 페이지에서 영상 id. **API 를 안 쓴다**(검색은 100 유닛/회)."""
    h = _get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
    return list(dict.fromkeys(re.findall(r'"videoId":"([\w-]{11})"', h)))[:n]


def yt_meta(vid: str) -> dict:
    """워치 페이지에서 메타. **``게시일`` 만 시간 게이트를 통과한다.**

    ``조회수`` 도 같이 담지만 그것은 **읽은 시점의 누적**이다. 상태 축으로
    쓰면 미래를 보는 것이므로 여기서 이름에 못을 박아 둔다.
    """
    h = _get(f"https://www.youtube.com/watch?v={vid}")
    def pick(*pats):
        for p in pats:
            m = re.search(p, h)
            if m:
                return m.group(1)
        return None
    return {
        "id": vid,
        "제목": pick(r'"title":\{"simpleText":"([^"]{1,200})"'),
        "채널": pick(r'"ownerChannelName":"([^"]{1,120})"'),
        "게시일": pick(r'"uploadDate":"([^"]+)"',
                    r'"publishDate":\{"simpleText":"([^"]+)"'),
        "조회수_읽은시점": pick(r'"viewCount":\{"simpleText":"[^\d]*([\d,\.]+)',
                          r'"viewCount":"(\d+)"'),
    }


def yt_rss(channel_id: str) -> list[dict]:
    """채널 RSS --- 키도 쿼터도 없고 ``published`` 가 정확하다(최근 15편)."""
    h = _get("https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id)
    out = []
    for ent in h.split("<entry>")[1:]:
        def g(tag):
            m = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", ent)
            return m.group(1) if m else None
        out.append({"id": g("yt:videoId"), "제목": g("title"), "게시": g("published")})
    return out


def pre_open_volume(q: str, open_date: str, window: int = 90,
                    n: int = 40) -> dict:
    """**갈래 A 의 축 재료.** 오픈 이전 창에 올라온 영상 수와 게시 빈도.

    조회수를 안 쓴다. 노트 149 가 위키에서 세운 규약(``시작일 당일과 이후는
    한 칸도 안 본다``)을 유튜브에 옮긴 것인데, 여기서는 창을 자르는 대상이
    시계열이 아니라 **영상의 게시 시각**이다.
    """
    from datetime import date, timedelta
    d1 = date.fromisoformat(open_date[:10])
    d0 = d1 - timedelta(days=window)
    ids, hit, dates = yt_search(q, n), 0, []
    for v in ids:
        try:
            m = yt_meta(v)
        except Exception:
            continue
        time.sleep(SLEEP)
        u = (m.get("게시일") or "")[:10]
        try:
            du = date.fromisoformat(u)
        except ValueError:
            continue
        if d0 <= du < d1:
            hit += 1
            dates.append(u)
    return {"질의": q, "오픈": open_date, "창": window,
            "본 영상": len(ids), "창 안 영상": hit,
            "마지막 게시": max(dates) if dates else None}


# ── 갈래 B — 불변 법칙용 궤적 ──────────────────────────────────
_VIEW_PATS = (r'"viewCount":\{"simpleText":"[^\d]*([\d,\.]+)',
              r'"viewCount":"(\d+)"',
              r'watch-view-count[^>]*>\s*([\d,\.]+)',
              r'([\d,]{7,})\s+views')


def _views(h: str):
    for p in _VIEW_PATS:
        m = re.search(p, h)
        if m:
            return int(re.sub(r"[^\d]", "", m.group(1)))
    return None


def wayback_traj(url: str, stamps: list[str]) -> list[dict]:
    """웨이백 스냅샷에서 **그 시점의** 조회수를 되찾는다.

    이것이 이 모듈에서 유일하게 *과거의 세기* 를 주는 경로다. 유튜브 API 도
    워치 페이지도 못 주는 것을 아카이브가 준다 --- 그때 그 페이지를 통째로
    찍어 뒀기 때문이다.

    **덮음이 한계다.** 아카이브는 링크가 많이 걸린 URL 을 자주 찍는다.
    긴 꼬리는 스냅샷이 없다. 그래서 이 함수는 표본을 *고르는* 데 쓰면 안 되고
    (유명한 것만 남아 생존 편의가 된다) **모양을 배우는** 데만 쓴다.
    """
    out = []
    for ts in stamps:
        try:
            h = _get(f"https://web.archive.org/web/{ts}/{url}", timeout=90)
            m = re.search(r"/web/(\d{14})/", h)
            out.append({"요청": ts, "실제": m.group(1) if m else None,
                        "조회수": _views(h)})
        except Exception as e:
            out.append({"요청": ts, "오류": type(e).__name__})
        time.sleep(2.0)
    return out


def wayback_stamps(url: str, frm: str = "2015", to: str = "2026",
                   limit: int = 300) -> list[str]:
    """그 URL 에 실제로 있는 스냅샷 시각. 없으면 빈 목록 --- 덮음을 먼저 본다."""
    q = urllib.parse.urlencode({
        "url": url, "output": "json", "filter": "statuscode:200",
        "from": frm, "to": to, "limit": limit, "fl": "timestamp",
        "collapse": "timestamp:6"})
    try:
        rows = json.loads(_get("https://web.archive.org/cdx/search/cdx?" + q, timeout=90))
    except Exception:
        return []
    return [r[0] for r in rows[1:]] if rows and rows[0] == ["timestamp"] else \
           [r[0] for r in rows]


# ── 갈래 A — 글 언급량 (뉴스 · 블로그) ────────────────────────
#
# 유튜브와 달리 **여기는 세기도 시간 게이트를 통과한다.** 기사와 글에는
# 게시일이 박혀 있고, 그 날짜로 창을 자르면 오픈 이후 것이 안 섞인다.
# 노트 149 가 위키 조회수에서 쓴 규약과 같은 모양이다.

def news_rss(q: str, start: str, end: str, hl: str = "ko") -> dict:
    """구글 뉴스 RSS --- **키가 없고 기간을 자를 수 있다**(노트 639 확인).

    ``after:``/``before:`` 가 질의 안에서 먹는다. 한 번에 최대 100건이라
    **100 은 상한이지 실제 건수가 아니다** --- 상한에 닿으면 그렇게 적는다.
    """
    qq = f"{q} after:{start} before:{end}"
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(qq)
           + f"&hl={hl}&gl=KR&ceid=KR:{hl}")
    h = _get(url)
    items = h.count("<item>")
    dates = re.findall(r"<pubDate>([^<]+)</pubDate>", h)
    return {"질의": q, "창": [start, end], "건수": items,
            "상한도달": items >= 100, "첫날": dates[-1] if dates else None}


def news_rss_items(q: str, start: str, end: str, hl: str = "ko") -> dict:
    """`news_rss` 가 **세고 버리는 것**을 살린다 --- 제목·링크·**게시일 전량**.

    왜 따로 두나: `news_rss` 는 `<pubDate>` 를 전부 파싱해 놓고 `dates[-1]` 하나만
    돌려주고 버린다. 건수만 필요할 때는 그게 맞지만, **후견지명 비율**
    (대상 사건일 **이전**에 쓰인 문서의 비율)을 재려면 **날짜가 전량** 있어야 한다.
    기존 함수는 쓰는 데가 있으므로 안 건드리고 옆에 붙인다.

    ⚠ **본문은 여기 없다.** RSS 는 제목과 링크만 준다 --- 본문은 링크를 따라가야
    하고 그건 매체마다 다르다. 그러므로 이 함수로 낼 수 있는 것은
    **'문서가 언제 쓰였나'** 까지다. 두께(본문 바이트)는 다음 단계다.
    **셋을 갈라 적는다 --- 있다 / 없다 / 못 읽었다**(조항 59).
    """
    qq = f"{q} after:{start} before:{end}"
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(qq)
           + f"&hl={hl}&gl=KR&ceid=KR:{hl}")
    try:
        h = _get(url)
    except Exception as e:
        return {"질의": q, "쓸만한가": False, "사유": f"{type(e).__name__}: {e}"[:160],
                "항목": []}
    blocks = re.findall(r"<item>(.*?)</item>", h, re.S)
    out = []
    for b in blocks:
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", b, re.S)
        p_ = re.search(r"<pubDate>([^<]+)</pubDate>", b)
        src = re.search(r"<source[^>]*>([^<]+)</source>", b)
        out.append({"제목": (t.group(1).strip() if t else "")[:200],
                    "게시": p_.group(1).strip() if p_ else None,
                    "매체": src.group(1).strip() if src else None})
    return {"질의": q, "쓸만한가": True, "창": [start, end],
            "건수": len(blocks), "상한도달": len(blocks) >= 100,
            "날짜있음": sum(1 for x in out if x["게시"]), "항목": out}


def hindsight_ratio(items, event_date: str) -> dict:
    """대상 사건일 **이전**에 쓰인 문서의 비율. 이 한 숫자가 코퍼스 전략을 가른다.

    10% 면 '두꺼운 텍스트'는 대부분 후견지명이라 못 쓰고, 60% 면 쓴다.
    **날짜를 못 읽은 것은 분모에서 뺀다** --- 0 으로 세면 비율이 거짓이 된다(조항 59).
    """
    from email.utils import parsedate_to_datetime
    import datetime as _dt
    ev = _dt.date.fromisoformat(str(event_date)[:10])
    pre = post = bad = 0
    for x in items:
        d = x.get("게시")
        if not d:
            bad += 1
            continue
        try:
            dt = parsedate_to_datetime(d).date()
        except Exception:
            bad += 1
            continue
        if dt < ev:
            pre += 1
        else:
            post += 1
    n = pre + post
    return {"이전": pre, "이후": post, "날짜불명": bad, "판정가능": n,
            "후견지명이전비율": round(pre / n, 4) if n else None}


#: 블로그 크롤 기본 쪽수. **6 에서 20 으로 올렸다**(노트 658).
#:
#: 6쪽(180건)에서 자르면 순위가 망가진다. 같은 브랜드를 6쪽과 20쪽으로 재
#: 순위 상관이 **0.7745**(요청 실패 제외 n=11) 이고, 상한에 닿은 여덟 건만
#: 보면 **0.4072** 다. 6쪽으로는 산리오 154 · 바이탈뷰티 172 · 플라워노즈 181
#: 이 거의 동률인데 20쪽으로 보면 520 · 582 · 594 로 벌어진다 --- **상위가
#: 통째로 뭉갠다.** 절단이 안 일어난 셋(부드바르 85 · 박카스맛젤리 30 ·
#: SK매직 32)은 두 조건이 완전히 일치해서, 그 0.77 이 알고리즘 잡음이 아니라
#: 진짜 절단임을 확인했다.
BLOG_PAGES = 20


def naver_blog_crawl(q: str, start: str, end: str,
                     pages: int = BLOG_PAGES) -> dict:
    """네이버 블로그 **기간 검색 페이지**를 긁는다 --- 키가 없다.

    **반환에 '어디까지 봤나' 를 같이 넣는다**(노트 658). 처음에는 글 수만
    돌려주고 요청이 실패하면 조용히 `0` 을 냈다. 그러면 **'실패' 와 '글이
    없음' 이 같은 값**이 되고, 실제로 그 한 건이 순위 상관을 0.7745 에서
    0.4413 으로 끌어내렸다. 이제 실패는 ``글=None`` 이다.

    검색 API 가 열려도(노트 639 이후 열렸다) 그쪽은 **기간 파라미터가 없고
    최근 1,000건까지만** 페이징되므로 **과거 창은 이 크롤로만** 된다.
    """
    ymd = lambda s: s.replace("-", "")
    seen: set = set()
    used, failed = 0, 0
    for p in range(pages):
        u = ("https://search.naver.com/search.naver?ssc=tab.blog.all&query="
             + urllib.parse.quote(q)
             + f"&nso=so%3Ar%2Cp%3Afrom{ymd(start)}to{ymd(end)}"
             + f"&start={1 + p * 30}")
        try:
            h = _get(u)
        except Exception:
            failed += 1
            if p == 0:
                # 첫 쪽이 죽으면 값이 없다 --- 0 으로 보고하지 않는다
                return {"질의": q, "창": [start, end], "글": None,
                        "쪽": 0, "상한도달": False, "실패쪽": failed}
            break
        new = set(re.findall(r"blog\.naver\.com/[\w-]+/(\d+)", h))
        used = p + 1
        if not new - seen:
            break                      # 새 글이 없으면 다 본 것이다
        seen |= new
        time.sleep(SLEEP)
    return {"질의": q, "창": [start, end], "글": len(seen), "쪽": used,
            "상한도달": used >= pages, "실패쪽": failed}


def naver_search_api(q: str, kind: str = "blog", display: int = 100,
                     sort: str = "date") -> dict:
    """네이버 검색 API. 권한이 열리면 이쪽을 쓴다.

    실패 사유를 **그대로** 돌려준다 --- ``024 Scope Status Invalid`` 는
    자격 문제가 아니라 **앱에 이 API 가 등록 안 된 것**이고, ``NID AUTH
    Result Invalid (28)`` 은 ID/시크릿 짝이 안 맞는 것이다. 둘을 안 가르면
    엉뚱한 키를 다시 발급받게 된다.
    """
    import os
    cid = os.environ.get("NAVER_SEARCH_ID") or os.environ.get("NAVER_CLIENT_ID")
    sec = os.environ.get("NAVER_SEARCH_SECRET") or os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        p = ROOT / ".env"
        if p.exists():
            kv = dict(l.strip().split("=", 1) for l in p.read_text().splitlines()
                      if "=" in l and not l.startswith("#"))
            cid = kv.get("NAVER_SEARCH_ID") or kv.get("NAVER_CLIENT_ID")
            sec = kv.get("NAVER_SEARCH_SECRET") or kv.get("NAVER_CLIENT_SECRET")
    qs = urllib.parse.urlencode({"query": q, "display": display, "sort": sort})
    req = urllib.request.Request(
        f"https://openapi.naver.com/v1/search/{kind}.json?{qs}",
        headers={"X-Naver-Client-Id": cid or "", "X-Naver-Client-Secret": sec or ""})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        return {"오류": e.code, "본문": e.read().decode("utf-8", "ignore")[:200]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--search")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--traj")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.search:
        ids = yt_search(a.search, a.n)
        print(json.dumps({"질의": a.search, "영상": len(ids), "앞": ids[:5]},
                         ensure_ascii=False))
    if a.traj:
        st = wayback_stamps(a.traj)
        print(json.dumps({"스냅샷": len(st)}, ensure_ascii=False))
        if st:
            step = max(1, len(st) // 8)
            print(json.dumps(wayback_traj(a.traj, st[::step][:8]),
                             ensure_ascii=False, indent=1))
