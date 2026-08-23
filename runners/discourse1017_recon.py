# -*- coding: utf-8 -*-
"""탐색 1017 ① — 담론(뉴스·여론) 원천 정찰. robots.txt·무키 접근성을 «실제 요청»으로.

🔴 본문 대수확이 아니다 — 호스트당 robots 1회 + 표본 요청 ≤1회. 요청 간격 1.1초.
🔴 robots Disallow 면 「불가」로 적고 우회하지 않는다. 판정은 «노리는 경로» 기준.
산출: runners/out1017_recon.json (가능/불가 표 · 콘텐츠 본문은 안 담는다 — 계수만)
"""
import json, time, datetime as dt, urllib.request, urllib.parse, urllib.robotparser, io, re, sys

UA = "wm-lab-collector/1017 (research; contact: alexlee@sweetspot.co.kr)"
GAP = 1.1
OUT = "/Users/ax/world_model/runners/out1017_recon.json"

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read(1 << 20)          # 1MB 상한 — 정찰이지 수확이 아니다
            return r.status, b, round(time.time() - t0, 2), None
    except Exception as e:
        return None, b"", round(time.time() - t0, 2), "%s: %s" % (type(e).__name__, e)

def _robots(host, path):
    st, b, sec, err = _get("https://%s/robots.txt" % host)
    time.sleep(GAP)
    if st != 200:
        # RFC 9309: robots.txt 가 4xx 면 「제한 없음」이다. 404 는 허용으로 읽는다.
        # 403 은 robots 규칙이 아니라 **호스트가 우리 요청 자체를 막는 것** — 불가로 적는다.
        if err and "404" in err:
            return {"robots_http": 404, "판정": "허용",
                    "허용": True, "비고": "robots 없음(404) — REP 상 제한 없음 · 약관은 안 읽었다"}
        if err and "403" in err:
            return {"robots_http": 403, "판정": "🔴 불가(403 — 호스트가 요청을 차단)"}
        if err and ("nodename" in err or "Name or service" in err):
            return {"robots_http": None, "오류": err, "판정": "🔴 불가(DNS 없음 — 원천 소멸)"}
        return {"robots_http": st, "오류": err, "판정": "🔴 모른다(robots 못 읽음)"}
    txt = b.decode("utf-8", "replace")
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(txt.splitlines())
    allowed = rp.can_fetch(UA, "https://%s%s" % (host, path))
    # '*' 블록의 Disallow 만 따로 세어 보인다(사람 검증용)
    dis = []
    block = None
    for ln in txt.splitlines():
        s = ln.strip()
        if s.lower().startswith("user-agent:"):
            block = s.split(":", 1)[1].strip()
        elif s.lower().startswith("disallow:") and block == "*":
            dis.append(s.split(":", 1)[1].strip())
    return {"robots_http": 200, "robots_bytes": len(b), "Disallow(*)": dis[:15],
            "Disallow(*)수": len(dis),
            "노리는경로": path, "허용": bool(allowed),
            "판정": "허용" if allowed else "🔴 불가(robots Disallow — 우회 금지)"}

def probe(name, host, path, sample_url=None, kind=""):
    r = {"이름": name, "호스트": host, "종류": kind}
    r.update(_robots(host, path))
    if sample_url and r.get("허용"):
        st, b, sec, err = _get(sample_url)
        time.sleep(GAP)
        item_n = None
        looks = None
        if b:
            head = b[:400].decode("utf-8", "replace")
            if b.lstrip()[:1] in (b"{", b"["):
                looks = "json"
                try:
                    item_n = len(json.loads(b))
                except Exception:
                    item_n = None
            elif "<rss" in head or "<feed" in head or "<?xml" in head:
                looks = "rss/xml"
                item_n = b.count(b"<item") + b.count(b"<entry")
            elif "<html" in head.lower() or "<!doctype" in head.lower():
                looks = "html"
        r["표본요청"] = {"url": sample_url, "HTTP": st, "바이트": len(b), "초": sec,
                     "형태": looks, "항목수": item_n, "오류": err}
        # pubDate 존재 여부(뉴스 RSS 핵심)
        if b and looks == "rss/xml":
            r["표본요청"]["pubDate있음"] = (b"<pubDate" in b) or (b"<published" in b) or (b"<dc:date" in b)
    return r

Q = urllib.parse.quote
targets = [
    # ⓐ 뉴스
    ("google_news_rss", "news.google.com", "/rss/search",
     "https://news.google.com/rss/search?q=%s&hl=ko&gl=KR&ceid=KR:ko" % Q("웹툰"), "뉴스RSS"),
    ("yna_rss", "www.yna.co.kr", "/rss/",
     "https://www.yna.co.kr/rss/news.xml", "뉴스RSS"),
    ("hani_rss", "www.hani.co.kr", "/rss/",
     "https://www.hani.co.kr/rss/", "뉴스RSS"),
    ("khan_rss", "www.khan.co.kr", "/rss/",
     "https://www.khan.co.kr/rss/rssdata/total_news.xml", "뉴스RSS"),
    ("donga_rss", "rss.donga.com", "/total.xml",
     "https://rss.donga.com/total.xml", "뉴스RSS"),
    ("chosun_rss", "www.chosun.com", "/arc/outboundfeeds/rss/",
     "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml", "뉴스RSS"),
    ("mk_rss", "www.mk.co.kr", "/rss/",
     "https://www.mk.co.kr/rss/30000001/", "뉴스RSS"),
    ("hankyung_rss", "www.hankyung.com", "/feed/",
     "https://www.hankyung.com/feed/all-news", "뉴스RSS"),
    ("etnews_rss", "www.etnews.com", "/rss/",
     "https://rss.etnews.com/Section901.xml", "뉴스RSS"),
    ("ohmynews_rss", "rss.ohmynews.com", "/rss/",
     "https://rss.ohmynews.com/rss/ohmynews.xml", "뉴스RSS"),
    ("sbs_rss", "news.sbs.co.kr", "/news/rss.do",
     "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER", "뉴스RSS"),
    ("jtbc_rss", "news-ex.jtbc.co.kr", "/v1/get/rss/section/10",
     "https://news-ex.jtbc.co.kr/v1/get/rss/section/10", "뉴스RSS"),
    ("bing_news_rss", "www.bing.com", "/news/search?q=x&format=rss",
     "https://www.bing.com/news/search?q=%s&format=rss" % Q("웹툰"), "뉴스RSS(쿼리별)"),
    ("kbs_rss", "news.kbs.co.kr", "/rss/rss.xml",
     "https://news.kbs.co.kr/rss/rss.xml", "뉴스RSS"),
    ("naver_news_search_rss", "newssearch.naver.com", "/search.naver",
     "https://newssearch.naver.com/search.naver?where=rss&query=%s" % Q("웹툰"), "뉴스RSS(존재검증)"),
    ("naver_news", "news.naver.com", "/main/list.naver", None, "뉴스HTML"),
    # ⓑ 여론
    ("reddit_json", "www.reddit.com", "/r/kpop/new.json",
     "https://www.reddit.com/r/kpop/new.json?limit=5", "여론JSON"),
    ("dcinside_gall", "gall.dcinside.com", "/mgallery/board/lists/",
     "https://gall.dcinside.com/mgallery/board/lists/?id=webtoon", "여론HTML"),
    ("theqoo", "theqoo.net", "/hot",
     "https://theqoo.net/hot", "여론HTML"),
    ("ruliweb", "bbs.ruliweb.com", "/community/board/300143",
     "https://bbs.ruliweb.com/community/board/300143", "여론HTML"),
    ("instiz", "www.instiz.net", "/pt",
     "https://www.instiz.net/pt", "여론HTML"),
    ("fmkorea", "www.fmkorea.com", "/index.php", None, "여론HTML"),
    ("clien", "www.clien.net", "/service/board/park", None, "여론HTML"),
    ("natepann", "pann.nate.com", "/talk/ranking", None, "여론HTML"),
]

rows = []
for name, host, path, sample, kind in targets:
    print("정찰:", name, flush=True)
    try:
        rows.append(probe(name, host, path, sample, kind))
    except Exception as e:
        rows.append({"이름": name, "호스트": host, "판정": "🔴 모른다(예외)",
                     "오류": "%s: %s" % (type(e).__name__, e)})

n_ok = sum(1 for r in rows if r.get("판정") == "허용")
n_no = sum(1 for r in rows if str(r.get("판정", "")).startswith("🔴 불가"))
n_unk = len(rows) - n_ok - n_no
out = {"노트": 1017, "레인": "탐색", "무엇": "담론 원천 정찰 — robots·무키 접근 실측(본문 수확 아님)",
       "UA": UA, "요청간격초": GAP,
       "시각(끝)": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "수": {"허용": n_ok, "불가": n_no, "모른다": n_unk, "합==호스트": n_ok + n_no + n_unk == len(rows)},
       "🔴 robots 가 허용해도 약관은 따로다": "이 표는 robots + 무키 표본요청만 실측했다. 재배포 라이선스는 원천별로 안 읽었다 — 내부 연구용",
       "전수": rows}
open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out["수"], ensure_ascii=False))
