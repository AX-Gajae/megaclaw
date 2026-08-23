# -*- coding: utf-8 -*-
"""정찰 1023 — 2차. 1차의 「RSS아님(수만 B)」는 RSS 안내 HTML 이었다 — 그 페이지와
매체 홈에서 실제 피드 주소를 캐서 재검침한다. + Daum breakingnews 구조 실측.
산출: runners/out1023_recon2.json — 계수만.
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

OUT = Path("/Users/ax/world_model/runners/out1023_recon2.json")
UA = "wm-lab-collector/1023 (research; contact: alexlee@sweetspot.co.kr)"
GAP = 1.1

# 피드 주소를 캘 안내/홈 페이지
GUIDE = {
    "mydaily": "https://www.mydaily.co.kr/rss",
    "xportsnews": "https://www.xportsnews.com/rss",
    "sportskhan": "https://sports.khan.co.kr/rss",
    "news1": "https://www.news1.kr/rss/S1N1.xml",
    "tenasia": "https://tenasia.hankyung.com/rss",
    "sportsseoul_home": "https://www.sportsseoul.com/",
    "spotvnews_home": "https://www.spotvnews.co.kr/",
    "osen_home": "https://osen.mt.co.kr/",
    "starnews_home": "https://www.starnewskorea.com/",
    "inven_news": "https://www.inven.co.kr/webzine/news/",
    "sportschosun_home": "https://sports.chosun.com/",
}
DAUM = ["https://news.daum.net/breakingnews",
        "https://news.daum.net/breakingnews?page=2",
        "https://news.daum.net/breakingnews/entertain",
        "https://news.daum.net/breakingnews/culture",
        "https://news.daum.net/breakingnews/digital"]

_hl = threading.Lock()
_host_lock = {}
_host_last = {}
_rb = {}


def _gap(host):
    with _hl:
        lk = _host_lock.setdefault(host, threading.Lock())
    with lk:
        d = time.time() - _host_last.get(host, 0.0)
        if d < GAP:
            time.sleep(GAP - d)
        _host_last[host] = time.time()


def _get(url):
    host = urllib.parse.urlparse(url).netloc
    _gap(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(1 << 21)


def _can(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc
    if host not in _rb:
        try:
            txt = _get("%s://%s/robots.txt" % (u.scheme, host)).decode("utf-8", "replace")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(txt.splitlines())
            _rb[host] = rp
        except urllib.error.HTTPError as e:
            _rb[host] = "open" if e.code == 404 else "closed"
        except Exception:
            _rb[host] = "closed"
    rp = _rb[host]
    if rp == "open":
        return True
    if rp == "closed":
        return False
    return rp.can_fetch(UA, url)


def probe_feed(url):
    r = {"url": url}
    if not _can(url):
        r["판정"] = "robots불허"
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
    r.update({"판정": "허용", "항목": len(items),
              "pub채움": round(min(len(pubs), len(items)) / len(items), 3)})
    return r


_FEED_RX = re.compile(
    r'(?:href|src)=["\']([^"\']*(?:rss|feed)[^"\']*?(?:\.xml|/feed[a-z\-]*|allArticle[^"\']*|rss[a-zA-Z_]*\.php)[^"\']*)["\']|'
    r'["\'](https?://[^"\']*\.xml)["\']', re.I)


def main():
    res = {"발굴": {}, "재검침": {}, "daum": {}}
    for nm, gu in GUIDE.items():
        found = set()
        try:
            if not _can(gu):
                res["발굴"][nm] = {"안내": gu, "판정": "robots불허"}
                continue
            s = _get(gu).decode("utf-8", "replace")
        except Exception as e:
            res["발굴"][nm] = {"안내": gu, "판정": type(e).__name__}
            continue
        for m in _FEED_RX.finditer(s):
            u = m.group(1) or m.group(2)
            if not u or u.startswith("data:"):
                continue
            u = urllib.parse.urljoin(gu, unescape_min(u))
            pu = urllib.parse.urlparse(u)
            if not pu.netloc or "feedburner" in pu.netloc and nm != "zdnetkr":
                continue
            # 같은 매체 계열 호스트만
            base = urllib.parse.urlparse(gu).netloc.split(".")[-2]
            if base not in pu.netloc:
                continue
            found.add(u.split("#")[0])
        found = sorted(found)[:8]
        res["발굴"][nm] = {"안내": gu, "후보": len(found)}
        for u in found:
            res["재검침"].setdefault(nm, []).append(probe_feed(u))
    for u in DAUM:
        r = {"url": u}
        if not _can(u):
            r["판정"] = "robots불허"
        else:
            try:
                s = _get(u).decode("utf-8", "replace")
                links = set(re.findall(r'https://v\.daum\.net/v/(\d+)', s))
                tm = len(re.findall(r'<span class="info_news">|datetime=', s))
                r.update({"판정": "허용", "기사링크": len(links), "시각단서": tm,
                          "bytes": len(s)})
            except urllib.error.HTTPError as e:
                r["판정"] = "HTTP %d" % e.code
            except Exception as e:
                r["판정"] = type(e).__name__
        res["daum"][u.split("net/")[1][:40]] = r
    doc = {"노트": 1023, "끝": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "결과": res}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for rows in res["재검침"].values() for r in rows if r.get("판정") == "허용")
    print("정찰2 끝 — 재검침 허용 %d" % ok)


def unescape_min(u):
    return u.replace("&amp;", "&")


if __name__ == "__main__":
    main()
