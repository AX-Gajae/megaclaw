# -*- coding: utf-8 -*-
"""정찰 1023 — 담론 원천 «2차» 전수 실측 (1017 표의 증분).

대상:
  ① 연예·스포츠·게임 전문지 RSS 후보 전수 — 스포츠서울·OSEN·마이데일리·스타뉴스·
     엑스포츠뉴스·스포티비뉴스·게임메카·인벤·디스이즈게임·텐아시아 + 스포츠조선·
     스포츠동아·스포츠경향·일간스포츠·뉴스1·뉴시스·노컷·머니투데이·데일리e스포츠·
     경향게임스·포모스·게임톡·ZDNet
  ② 커뮤니티 추가 robots 실측 — 아카라이브·펨코(재실측)·엠팍·개드립·웃대·오유·
     뽐뿌·보배드림
  ③ Daum 뉴스 robots
규율: robots 를 «실제로 받아» URL 단위 검사(404=제한없음 · 403=차단 · Disallow=불가).
     호스트별 요청 간격 ≥1.1초 · 서로 다른 호스트는 병렬(워커 4 · 호스트 분할).
산출: runners/out1023_recon.json — 계수만(제목·본문 없음).
"""
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

OUT = Path("/Users/ax/world_model/runners/out1023_recon.json")
UA = "wm-lab-collector/1023 (research; contact: alexlee@sweetspot.co.kr)"
GAP = 1.1

# ── 뉴스 RSS 후보(후보 전부 때려 보고 각각 기록한다 — 404 는 「그 주소엔 없다」) ──
NEWS_CAND = {
    "sportsseoul": ["https://www.sportsseoul.com/rss/allArticle.xml",
                    "https://www.sportsseoul.com/rss/S1N1.xml",
                    "https://www.sportsseoul.com/rss"],
    "osen": ["https://osen.mt.co.kr/rss",
             "https://osen.mt.co.kr/rss/entertain.xml",
             "https://osen.mt.co.kr/rss/sports.xml"],
    "mydaily": ["https://www.mydaily.co.kr/rss/rss_news.xml",
                "https://www.mydaily.co.kr/rss/allArticle.xml",
                "https://www.mydaily.co.kr/rss"],
    "starnews": ["https://www.starnewskorea.com/rss/rss.xml",
                 "https://www.starnewskorea.com/rss",
                 "https://star.mt.co.kr/rss/star_news.xml"],
    "xportsnews": ["https://www.xportsnews.com/rss/feed",
                   "https://www.xportsnews.com/rss/allArticle.xml",
                   "https://www.xportsnews.com/rss"],
    "spotvnews": ["https://www.spotvnews.co.kr/rss/allArticle.xml",
                  "https://www.spotvnews.co.kr/rss/clickTop.xml"],
    "gamemeca": ["https://www.gamemeca.com/rss.php",
                 "https://www.gamemeca.com/rss/news.xml",
                 "https://www.gamemeca.com/rss"],
    "inven": ["https://www.inven.co.kr/rss/news.xml",
              "https://www.inven.co.kr/rss/webzine/news/",
              "https://www.inven.co.kr/rss/"],
    "thisisgame": ["https://www.thisisgame.com/rss/news.xml",
                   "https://rss.thisisgame.com/news.xml",
                   "https://www.thisisgame.com/rss"],
    "tenasia": ["https://tenasia.hankyung.com/feed",
                "https://tenasia.hankyung.com/rss",
                "https://www.tenasia.co.kr/feed"],
    "sportschosun": ["https://sports.chosun.com/rss/sports.xml",
                     "https://www.sportschosun.com/rss/list.xml",
                     "https://sports.chosun.com/rss"],
    "sportsdonga": ["https://rss.donga.com/sports.xml",
                    "https://sports.donga.com/rss"],
    "sportskhan": ["https://sports.khan.co.kr/rss/rssdata/kh_sports.xml",
                   "https://sports.khan.co.kr/rss"],
    "isplus": ["https://isplus.com/rss",
               "https://isplus.com/rss/allArticle.xml"],
    "news1": ["https://www.news1.kr/rss/S1N1.xml",
              "https://rss.news1.kr/news1_all.xml",
              "https://www.news1.kr/rss"],
    "newsis": ["https://newsis.com/RSS/entertain.xml",
               "https://newsis.com/RSS/sports.xml",
               "https://newsis.com/RSS/culture.xml"],
    "nocutnews": ["https://rss.nocutnews.co.kr/nocutnews.xml",
                  "https://www.nocutnews.co.kr/rss/entertainment.xml"],
    "mt": ["https://rss.mt.co.kr/mt_news.xml"],
    "dailyesports": ["https://www.dailyesports.com/rss/allArticle.xml"],
    "khgames": ["https://www.khgames.co.kr/rss/allArticle.xml"],
    "fomos": ["https://www.fomos.kr/rss/allArticle.xml"],
    "gametoc": ["https://www.gametoc.co.kr/rss/allArticle.xml"],
    "zdnetkr": ["https://feeds.feedburner.com/zdkorea"],
}

# ── 커뮤니티·포털 robots 실측(경로 단위 can_fetch + 허용이면 목록 1회 실땅김) ──
COMM_CAND = {
    "arca": ["https://arca.live/b/genshin", "https://arca.live/b/bluearchive"],
    "fmkorea": ["https://www.fmkorea.com/best"],          # 1017 불가 — 재실측
    "mlbpark": ["https://mlbpark.donga.com/mp/b.php?b=bullpen"],
    "dogdrip": ["https://www.dogdrip.net/dogdrip"],
    "humoruniv": ["http://web.humoruniv.com/board/humor/list.html?table=pds"],
    "todayhumor": ["http://www.todayhumor.co.kr/board/list.php?table=humorbest"],
    "ppomppu": ["https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard"],
    "bobaedream": ["https://www.bobaedream.co.kr/board/bulletin/list.php?code=best"],
    "daum_news": ["https://news.daum.net/breakingnews"],
    "daum_v": ["https://v.daum.net/v/dummy1023"],
}

_hl_master = threading.Lock()
_host_lock = {}
_host_last = {}
_robots_lock = threading.Lock()
_robots_cache = {}


def _gap(host):
    with _hl_master:
        lk = _host_lock.setdefault(host, threading.Lock())
    with lk:
        d = time.time() - _host_last.get(host, 0.0)
        if d < GAP:
            time.sleep(GAP - d)
        _host_last[host] = time.time()


def _get(url, timeout=20):
    host = urllib.parse.urlparse(url).netloc
    _gap(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(1 << 21)


def _robots(host, scheme="https"):
    """(판정, rp|None). 판정: open(404) / closed(403·오류) / rules."""
    with _robots_lock:
        if host in _robots_cache:
            return _robots_cache[host]
    try:
        txt = _get("%s://%s/robots.txt" % (scheme, host)).decode("utf-8", "replace")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(txt.splitlines())
        n_dis = len(re.findall(r"(?im)^\s*disallow\s*:", txt))
        root_dis = bool(re.search(r"(?im)^\s*disallow\s*:\s*/\s*$", txt))
        v = ("rules", rp, {"disallow행": n_dis, "루트Disallow": root_dis})
    except urllib.error.HTTPError as e:
        v = ("open", None, {"robots_http": e.code}) if e.code == 404 \
            else ("closed", None, {"robots_http": e.code})
    except Exception as e:
        v = ("closed", None, {"robots_err": type(e).__name__})
    with _robots_lock:
        _robots_cache[host] = v
    return v


def _can(url):
    u = urllib.parse.urlparse(url)
    kind, rp, info = _robots(u.netloc, u.scheme or "https")
    if kind == "open":
        return True, info
    if kind == "closed":
        return False, info
    return rp.can_fetch(UA, url), info


def probe_feed(url):
    r = {"url": url}
    ok, info = _can(url)
    r.update(info)
    if not ok:
        r["판정"] = "robots불허" if "robots_http" not in info else "robots판독불가"
        return r
    try:
        b = _get(url)
    except urllib.error.HTTPError as e:
        r["판정"] = "HTTP %d" % e.code
        return r
    except Exception as e:
        r["판정"] = type(e).__name__
        return r
    s = b.decode("utf-8", "replace")
    items = re.findall(r"<(?:item|entry)[\s>]", s)
    pubs = re.findall(r"<(?:pubDate|published|dc:date)[\s>]", s)
    if not items:
        r["판정"] = "RSS아님(%dB)" % len(b)
        return r
    r["판정"] = "허용"
    r["항목"] = len(items)
    r["pub채움"] = round(min(len(pubs), len(items)) / len(items), 3)
    return r


def probe_board(url):
    r = {"url": url}
    ok, info = _can(url)
    r.update(info)
    if not ok:
        r["판정"] = "robots불허" if info.get("robots_http") != 404 else "robots불허"
        return r
    try:
        b = _get(url)
    except urllib.error.HTTPError as e:
        r["판정"] = "HTTP %d" % e.code
        return r
    except Exception as e:
        r["판정"] = type(e).__name__
        return r
    s = b.decode("utf-8", "replace")
    links = len(re.findall(r"<a\s[^>]*href=", s))
    r["판정"] = "허용" if links >= 10 else "응답빈약(%dB·a %d)" % (len(b), links)
    r["a태그"] = links
    return r


def main():
    t0 = time.time()
    res = {"뉴스RSS": {}, "커뮤니티": {}}
    jobs = []          # (그룹, 이름, url, probe)
    for nm, urls in NEWS_CAND.items():
        for u in urls:
            jobs.append(("뉴스RSS", nm, u, probe_feed))
    for nm, urls in COMM_CAND.items():
        for u in urls:
            jobs.append(("커뮤니티", nm, u, probe_board))
    # 호스트 분할 큐 — 워커가 호스트 하나를 통째로 잡는다(호스트 내 직렬 보장)
    by_host = {}
    for j in jobs:
        by_host.setdefault(urllib.parse.urlparse(j[2]).netloc, []).append(j)
    hosts = list(by_host)
    hi = [0]
    out_lock = threading.Lock()

    def worker():
        while True:
            with out_lock:
                if hi[0] >= len(hosts):
                    return
                h = hosts[hi[0]]
                hi[0] += 1
            for grp, nm, u, fn in by_host[h]:
                r = fn(u)
                with out_lock:
                    res[grp].setdefault(nm, []).append(r)

    ths = [threading.Thread(target=worker) for _ in range(4)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    # 원천 단위 요약
    summ = {}
    for grp, d in res.items():
        for nm, rows in d.items():
            oks = [r for r in rows if r.get("판정") == "허용"]
            summ[nm] = {"그룹": grp, "허용후보": len(oks), "후보": len(rows),
                        "최다항목": max([r.get("항목", 0) for r in oks], default=0)}
    doc = {"노트": 1023, "끝": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "초": round(time.time() - t0, 1), "요약": summ, "상세": res}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("정찰 1023 끝 — %.0f초 · 원천 %d · 허용 %d" %
          (doc["초"], len(summ), sum(1 for v in summ.values() if v["허용후보"])))


if __name__ == "__main__":
    main()
