# -*- coding: utf-8 -*-
"""수집 1017 — 담론(뉴스·여론) 수집기. 정본 명세 `docs/아키텍처_결정기.md` §L1-0·v1.1.

원천(전부 2026-08-24 실측 — `runners/out1017_recon.json`):
  뉴스RSS   yna·khan·donga·chosun·mk·hankyung·etnews·ohmynews·sbs·jtbc (robots 허용 실측)
  bing_news 쿼리별 뉴스 RSS (robots 허용 실측 · 개체 명단 회전)
  여론      dcinside(robots 허용 · 갤 목록) · theqoo(robots 404=REP 제한없음) ·
            ruliweb(목록 허용) · instiz(Disallow 0)
불가(우회 금지 · 표는 out1017_recon.json): google_news_rss · naver(뉴스·검색RSS 소멸) ·
  reddit(robots Disallow /) · fmkorea · natepann · hani(403 차단) · kbs(피드 404)

규율:
  · 요청 간격 전역 ≥1.1초 · UA 명시 · 호스트별 robots 를 주행마다 다시 읽어 URL 단위로 검사
    (robots Disallow 면 그 자리서 건너뛰고 계수한다 — 우회 금지)
  · published_at 은 «원천이 준 것만». 없으면 null — 크롤일 대체 금지(L0).
    목록이 시각만 주는 커뮤니티 글은 null + `published_at_원문` 에 원문 문자열.
  · 산출 /Users/ax/wm_harvest/discourse/{원천}/{크롤일}.jsonl.gz — 문서:
    {url, 제목, 본문, published_at, published_at_원문, crawled_at, 원천, 매칭}
  · 재개: state/seen_*.txt(url sha1) + state/bing_cursor.json — 죽여도 이어 돈다.
  · out JSON(runners/out1017_discourse.json)에는 **계수만** — 제목·본문·개별 URL 을 안 싣는다.

쓰는 법:
  python3 -m runners.discourse1017                # 상시 1회전(등기부·데몬용 · 유한)
  python3 -m runners.discourse1017 --big          # 1차 대수확(전 개체 bing + 보드 다페이지)
  python3 -m runners.discourse1017 --only 원천    # 그 원천만
  python3 -m runners.discourse1017 --fullspeed    # 🔴 전속 연속 루프(1023 · nohup 용)

🔴 1023 인수(1017 팔 종료 — 이 파일의 소유는 1023 팔):
  · politeness 를 «호스트별» 1.1초로 정정(1017 은 전역 직렬이었다 — 서로 다른 호스트는
    병렬 가능이 규칙이라 규칙 안에서의 속도 회복이다) · 스레드 안전(잠금)
  · 신규 원천(2026-08-24 재실측 runners/out1023_recon.json·out1023_recon2.json):
    뉴스RSS +9사 12피드(일간스포츠·머니투데이·뉴시스3·노컷·스포츠동아2·게임메카·
    게임톡·경향게임스·ZDNet) · 보드 +2(daum_news breakingnews — 섹션·페이지가 서버에서
    안 갈리는 SPA 라 1페이지 회전 · dogdrip)
  · 개체 명단: 1016 별칭(위키 해소 페이지명 238행 → 고유 페이지 139 + 괄호꼬리 제거형)
    + 도메인 키워드 18→49
  · --fullspeed: writer.pid 를 쥔 채 무한 회전(데몬 회차는 접힘 — 정상) ·
    bing 전 명단 연속 회전 + 보드 300초·뉴스 600초 재폴링 · 정지는 state/stop_fullspeed ·
    스레드 ≤3(+주) · load1>10 이면 그 사이클은 bing 만
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUTD = Path("/Users/ax/wm_harvest/discourse")
STATED = OUTD / "state"
OUT_JSON = ROOT / "runners" / "out1017_discourse.json"
LEDGER1016 = Path("/Users/ax/wm_harvest/foundation/ledger_interventions/ledger.jsonl")
UA = "wm-lab-collector/1017 (research; contact: alexlee@sweetspot.co.kr)"
GAP = 1.1

# ── 뉴스 RSS 피드 등기(2026-08-24 실측 표본은 각 매체 대표 피드 — 나머지는 주행이
#    직접 때려 보고 실패를 계수한다 · 404 는 「없다」로 남는다) ────────────────
FEEDS = {
    "yna": ["https://www.yna.co.kr/rss/news.xml",
            "https://www.yna.co.kr/rss/entertainment.xml",
            "https://www.yna.co.kr/rss/culture.xml"],
    "khan": ["https://www.khan.co.kr/rss/rssdata/total_news.xml",
             "https://www.khan.co.kr/rss/rssdata/culture_news.xml"],
    "donga": ["https://rss.donga.com/total.xml",
              "https://rss.donga.com/culture.xml",
              "https://rss.donga.com/entertainment.xml"],
    "chosun": ["https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
               "https://www.chosun.com/arc/outboundfeeds/rss/category/entertainments/?outputType=xml",
               "https://www.chosun.com/arc/outboundfeeds/rss/category/culture-life/?outputType=xml"],
    "mk": ["https://www.mk.co.kr/rss/30000001/",
           "https://www.mk.co.kr/rss/30000023/",
           "https://www.mk.co.kr/rss/50700001/"],
    "hankyung": ["https://www.hankyung.com/feed/all-news",
                 "https://www.hankyung.com/feed/entertainment",
                 "https://www.hankyung.com/feed/it"],
    "etnews": ["https://rss.etnews.com/Section901.xml",
               "https://rss.etnews.com/Section903.xml"],
    "ohmynews": ["https://rss.ohmynews.com/rss/ohmynews.xml"],
    "sbs": ["https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER",
            "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=07&plink=RSSREADER",
            "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08&plink=RSSREADER",
            "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=14&plink=RSSREADER"],
    # ↓ 1023 증분(2026-08-24 실측 — out1023_recon.json 허용 판정만)
    "isplus": ["https://isplus.com/rss"],
    "mt": ["https://rss.mt.co.kr/mt_news.xml"],
    "newsis": ["https://newsis.com/RSS/entertain.xml",
               "https://newsis.com/RSS/sports.xml",
               "https://newsis.com/RSS/culture.xml"],
    "nocutnews": ["https://rss.nocutnews.co.kr/nocutnews.xml"],
    "sportsdonga": ["https://rss.donga.com/sports.xml",
                    "https://sports.donga.com/rss"],
    "gamemeca": ["https://www.gamemeca.com/rss.php"],
    "gametoc": ["https://www.gametoc.co.kr/rss/allArticle.xml"],
    "khgames": ["https://www.khgames.co.kr/rss/allArticle.xml"],
    "zdnetkr": ["https://feeds.feedburner.com/zdkorea"],
    "jtbc": ["https://news-ex.jtbc.co.kr/v1/get/rss/section/10",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/20",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/30",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/40",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/50",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/60",
             "https://news-ex.jtbc.co.kr/v1/get/rss/section/70"],
}

# ── 여론 보드(2026-08-24 실측 200 만 넣었다 · dcinside 는 표준형이 `lists?id=`) ──
BOARDS = {
    "dcinside": ["https://gall.dcinside.com/board/lists?id=comic_new4",
                 "https://gall.dcinside.com/board/lists?id=comic_new1",
                 "https://gall.dcinside.com/board/lists?id=webtoon",
                 "https://gall.dcinside.com/mgallery/board/lists?id=game",
                 "https://gall.dcinside.com/mgallery/board/lists?id=goods",
                 "https://gall.dcinside.com/mgallery/board/lists?id=idol",
                 "https://gall.dcinside.com/board/lists?id=kpop"],
    "theqoo": ["https://theqoo.net/hot", "https://theqoo.net/square",
               "https://theqoo.net/webtoon", "https://theqoo.net/talk",
               "https://theqoo.net/game"],
    "ruliweb": ["https://bbs.ruliweb.com/best/hit",
                "https://bbs.ruliweb.com/community/board/300143"],
    "instiz": ["https://www.instiz.net/pt", "https://www.instiz.net/name"],
    # ↓ 1023 증분 — daum robots 404(=REP 제한없음) · 섹션·페이지가 서버에서 안 갈린다
    #   (실측: base·entertain·page=2 가 같은 문서 — SPA) → 1페이지 회전 수집
    "daum_news": ["https://news.daum.net/breakingnews"],
    "dogdrip": ["https://www.dogdrip.net/dogdrip"],
}

KEYWORDS = ["웹툰", "웹소설", "팝업스토어", "팝업 스토어", "아이돌 데뷔", "콜라보",
            "굿즈", "IP 라이선스", "캐릭터 IP", "애니메이션 개봉", "단행본", "정주행",
            "콘서트", "팬덤", "스토어 오픈", "네이버웹툰", "카카오웹툰", "카카오페이지",
            # ↓ 1023 확장(도메인 담론 30)
            "웹툰 원작", "드라마화", "애니화", "영화화", "웹소설 원작", "코믹스",
            "굿즈 완판", "오픈런", "팝업 오픈", "콜라보 카페", "컬래버레이션",
            "케이팝", "K팝", "아이돌 컴백", "데뷔 무대", "쇼케이스", "팬미팅",
            "팬사인회", "월드투어", "돔투어", "빌보드 차트", "음원차트",
            "게임 출시", "신작 게임", "사전예약", "스팀 출시", "콘솔 출시",
            "e스포츠", "서브컬처", "캐릭터 굿즈", "피규어"]

_hl_master = threading.Lock()
_host_lock = {}
_host_last = {}
_robots_lock = threading.Lock()
_robots_cache = {}


def _sleep_gap(host):
    """호스트별 ≥GAP 초 — politeness 는 호스트별 · 서로 다른 호스트는 병렬(1023)."""
    with _hl_master:
        lk = _host_lock.setdefault(host, threading.Lock())
    with lk:
        d = time.time() - _host_last.get(host, 0.0)
        if d < GAP:
            time.sleep(GAP - d)
        _host_last[host] = time.time()


def _robots_ok(url):
    """URL 단위 robots 관문. 못 읽으면(404 제외) 그 호스트는 이번 주행 내내 막는다."""
    host = urllib.parse.urlparse(url).netloc
    with _robots_lock:
        rp = _robots_cache.get(host)
    if rp is None:
        _sleep_gap(host)
        try:
            req = urllib.request.Request("https://%s/robots.txt" % host,
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = r.read(1 << 19).decode("utf-8", "replace")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(txt.splitlines())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                rp = "open"          # RFC 9309 — robots 없음은 제한 없음
            else:
                rp = "closed"        # 403 등 — 못 읽으면 안 간다
        except Exception:
            rp = "closed"
        with _robots_lock:
            _robots_cache[host] = rp
    if rp == "open":
        return True
    if rp == "closed":
        return False
    return rp.can_fetch(UA, url)


def fetch(url, tries=2):
    """(bytes|None, 사유|None). robots 불허·오류는 (None, 사유)."""
    if not _robots_ok(url):
        return None, "robots불허"
    host = urllib.parse.urlparse(url).netloc
    for i in range(tries):
        _sleep_gap(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read(1 << 22), None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(60)
                continue
            return None, "HTTP %d" % e.code
        except Exception as e:
            if i + 1 < tries:
                time.sleep(5)
                continue
            return None, type(e).__name__
    return None, "재시도소진"


# ── 개체 명단 ────────────────────────────────────────────────────────────────
def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def names_1017():
    """삼중쌍 704 의 이름 + 개입 원장 IP(1016 원장 있으면 그것 · 없으면 records 직접)
    + 도메인 키워드. 반환: (명단 list, 출처 집계 dict)."""
    ents = set()
    for ln in open("/Users/ax/wm_harvest/foundation/triples/meta.jsonl", encoding="utf-8"):
        ents.add(json.loads(ln)["개체"])
    dom_files = {"WT": "webtoon_records.json", "GAME": "game_records.json",
                 "BOOK": "book_records.json", "AN": "anime_records.json",
                 "MG": "manga_records.json", "MB": "mobile_records.json",
                 "WA": "wanime_records.json", "AP": "app_records.json"}
    maps = {}
    for pre, f in dom_files.items():
        try:
            maps[pre] = _load(ROOT / "data/state" / f)
        except Exception:
            maps[pre] = {}
    names, src = {}, {"삼중쌍": 0, "idol": 0, "market": 0, "popup": 0, "원장1016": 0,
                      "별칭1016": 0, "키워드": len(KEYWORDS), "이름못찾음": 0}

    def _add(nm, tag):
        nm = (nm or "").strip()
        if len(nm) < 2 or nm.lower() in ("null", "none", "unresolved"):
            return False
        names.setdefault(nm, tag)
        return True

    idol_dir = ROOT / "data/idol_records"
    for e in sorted(ents):
        pre = e.split("-")[0]
        nm = None
        if pre in maps and e in maps[pre]:
            r = maps[pre][e]
            nm = r.get("title") or r.get("이름") or r.get("name")
        elif pre == "IDOL":
            p = idol_dir / (e + ".json")
            if p.exists():
                try:
                    nm = _load(p).get("group_name")
                except Exception:
                    nm = None
        elif pre.startswith("MKT"):
            p = ROOT / "data/market_records" / (e + ".json")
            if p.exists():
                try:
                    r = _load(p)
                    nm = r.get("ip_or_collab") or r.get("brand") or r.get("event_name")
                except Exception:
                    nm = None
        elif pre.startswith("R"):
            p = ROOT / "data/records" / (e + ".json")
            if p.exists():
                try:
                    r = _load(p)
                    nm = (r.get("entities") or {}).get("brand_key") or \
                         (r.get("intervention") or {}).get("brand_name")
                except Exception:
                    nm = None
        if nm and _add(nm, "삼중쌍"):
            src["삼중쌍"] += 1
        else:
            src["이름못찾음"] += 1
    # 개입 원장 IP — 1016 원장이 생겼으면 그것을 먼저 쓴다
    if LEDGER1016.exists():
        for ln in open(LEDGER1016, encoding="utf-8"):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            w = (r.get("A") or {}).get("what") or {}
            nm = w.get("ip_name") or w.get("brand")
            if nm and _add(nm, "원장1016"):
                src["원장1016"] += 1
            # 1023 — 1016 별칭 해소(위키 페이지명 238행 · 고유 139) + 괄호꼬리 제거형
            wr = (r.get("source") or {}).get("wiki_resolution")
            pg = wr.get("page") if isinstance(wr, dict) else (wr if isinstance(wr, str) else None)
            if pg:
                if _add(pg, "별칭1016"):
                    src["별칭1016"] += 1
                bare = re.sub(r"\s*\([^)]*\)\s*$", "", pg).strip()
                if bare and bare != pg and _add(bare, "별칭1016"):
                    src["별칭1016"] += 1
    else:
        for p in sorted((ROOT / "data/market_records").glob("MKT*.json")):
            try:
                r = _load(p)
            except Exception:
                continue
            nm = r.get("ip_or_collab") or r.get("brand")
            if nm and _add(nm, "market"):
                src["market"] += 1
        for p in sorted((ROOT / "data/records").glob("R*.json")):
            try:
                r = _load(p)
            except Exception:
                continue
            nm = (r.get("entities") or {}).get("brand_key") or \
                 (r.get("intervention") or {}).get("brand_name")
            if nm and _add(nm, "popup"):
                src["popup"] += 1
    for k in KEYWORDS:
        _add(k, "키워드")
    return sorted(names), src


# ── 파서 ────────────────────────────────────────────────────────────────────
_TAG = re.compile(r"<[^>]+>")
_CD = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def _text(x):
    if x is None:
        return None
    m = _CD.search(x)
    if m:
        x = m.group(1)
    return unescape(_TAG.sub(" ", x)).strip() or None


def _pub_iso(raw):
    if not raw:
        return None
    raw = raw.strip()
    try:
        return parsedate_to_datetime(raw).isoformat()
    except Exception:
        pass
    m = re.match(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})[T ]?(\d{2}:\d{2}(:\d{2})?)?", raw)
    if m:
        d = "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
        return d + ("T" + m.group(4) + "+09:00" if m.group(4) else "")
    return None


def parse_rss(b):
    """[(url, 제목, 본문요약, pub원문)] — item/entry 둘 다."""
    s = b.decode("utf-8", "replace")
    out = []
    for it in re.findall(r"<(?:item|entry)[\s>].*?</(?:item|entry)>", s, re.S):
        def g(tag):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), it, re.S)
            return m.group(1) if m else None
        link = _text(g("link"))
        if not link:
            m = re.search(r'<link[^>]*href="([^"]+)"', it)
            link = unescape(m.group(1)) if m else None
        pub = _text(g("pubDate")) or _text(g("published")) or _text(g("dc:date"))
        out.append((link, _text(g("title")), _text(g("description")) or _text(g("summary")),
                    pub))
    return out


def parse_dcinside(b, base):
    s = b.decode("utf-8", "replace")
    out = []
    for row in s.split("<tr")[1:]:
        m = re.search(r'href="(/(?:mgallery/)?board/view/?\?id=[^"]+?)"[^>]*>(.*?)</a>', row, re.S)
        if not m:
            continue
        url = urllib.parse.urljoin(base, unescape(m.group(1)))
        title = _text(m.group(2))
        md = re.search(r'class="gall_date"[^>]*title="([^"]+)"', row)
        pub_raw = md.group(1) if md else None
        if title:
            out.append((url.split("&page=")[0], title, None, pub_raw))
    return out


def parse_theqoo(b, base):
    s = b.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'href="(/(?:hot|square|webtoon|talk|game)/(\d{6,}))"[^>]*>(.*?)</a>', s, re.S):
        no = m.group(2)
        if no in seen:
            continue
        title = _text(m.group(3))
        if not title or title in ("공지", ""):
            continue
        seen.add(no)
        out.append((urllib.parse.urljoin(base, m.group(1)), title, None, None))
    return out


def parse_ruliweb(b, base):
    s = b.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'href="(https://bbs\.ruliweb\.com/[^"]*?/board/\d+/read/(\d+)[^"]*)"[^>]*>(.*?)</a>', s, re.S):
        no = m.group(2)
        if no in seen:
            continue
        title = _text(m.group(3))
        if not title:
            continue
        seen.add(no)
        out.append((m.group(1).split("?")[0], title, None, None))
    return out


def parse_instiz(b, base):
    s = b.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'href="(?:https?://www\.instiz\.net)?(/(?:pt|name)/(\d{4,}))[^"]*"[^>]*>(.*?)</a>', s, re.S):
        no = m.group(2)
        if no in seen:
            continue
        title = _text(m.group(3))
        if title:
            title = re.sub(r"\s+\d+$", "", title)   # 목록 꼬리의 조회수 숫자를 뗀다(실측)
        if not title or len(title) < 2:
            continue
        seen.add(no)
        out.append((urllib.parse.urljoin(base, m.group(1)), title, None, None))
    return out


def parse_daum(b, base):
    """breakingnews — 제목 있는 앵커만(실측 ~33/페치 · 목록 pub 은 null — L0)."""
    s = b.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="(https://v\.daum\.net/v/(\d+))"[^>]*>(.*?)</a>', s, re.S):
        no = m.group(2)
        if no in seen:
            continue
        title = _text(m.group(3))
        if not title or len(title) < 4:
            continue
        seen.add(no)
        out.append((m.group(1), title, None, None))
    return out


def parse_dogdrip(b, base):
    s = b.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="(?:https://www\.dogdrip\.net)?/(?:dogdrip/)?(\d{6,})"[^>]*>(.*?)</a>', s, re.S):
        no = m.group(1)
        if no in seen:
            continue
        title = _text(m.group(2))
        if not title or len(title) < 3:
            continue
        seen.add(no)
        out.append(("https://www.dogdrip.net/dogdrip/" + no, title, None, None))
    return out


# ── 저장·재개 ───────────────────────────────────────────────────────────────
def _seen_path(top):
    return STATED / ("seen_%s.txt" % top)


def _load_seen(top):
    p = _seen_path(top)
    if not p.exists():
        return set()
    return set(x.strip() for x in p.read_text().splitlines() if x.strip())


def _sha(u):
    return hashlib.sha1(u.encode("utf-8")).hexdigest()


def store(top, docs, seen):
    """신규만 골라 {top}/{크롤일}.jsonl.gz 에 덧붙이고 seen 에 적는다. 반환 신규 수."""
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = now[:10]
    fresh = []
    for d in docs:
        h = _sha(d["url"])
        if h in seen:
            continue
        seen.add(h)
        d["crawled_at"] = now
        fresh.append((h, d))
    if not fresh:
        return 0
    dp = OUTD / top
    dp.mkdir(parents=True, exist_ok=True)
    with gzip.open(dp / (day + ".jsonl.gz"), "at", encoding="utf-8") as f:
        for _, d in fresh:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(_seen_path(top), "a", encoding="utf-8") as f:
        for h, _ in fresh:
            f.write(h + "\n")
    return len(fresh)


def _match(names, *texts):
    t = " ".join(x for x in texts if x)
    return [n for n in names if n in t][:20]


# ── 원천별 주행 ─────────────────────────────────────────────────────────────
def run_news_rss(names, agg):
    seen = _load_seen("news_rss")
    for outlet, feeds in FEEDS.items():
        st = agg.setdefault("news_rss/" + outlet,
                            {"요청": 0, "실패": 0, "항목": 0, "신규": 0, "pub채움": 0, "실패사유": {}})
        for fu in feeds:
            st["요청"] += 1
            b, err = fetch(fu)
            if b is None:
                st["실패"] += 1
                st["실패사유"][fu.split("/")[-1][:40] or fu[-40:]] = err
                continue
            docs = []
            for link, title, desc, pub in parse_rss(b):
                if not link or not title:
                    continue
                iso = _pub_iso(pub)
                docs.append({"url": link, "제목": title, "본문": desc,
                             "published_at": iso, "published_at_원문": pub,
                             "원천": "news_rss/" + outlet,
                             "매칭": _match(names, title, desc)})
            st["항목"] += len(docs)
            st["pub채움"] += sum(1 for d in docs if d["published_at"])
            st["신규"] += store("news_rss", docs, seen)


def run_bing(names, agg, batch, big):
    seen = _load_seen("bing_news")
    cp = STATED / "bing_cursor.json"
    cur = 0
    if cp.exists():
        try:
            cur = json.loads(cp.read_text()).get("idx", 0)
        except Exception:
            cur = 0
    todo = names if big else [names[(cur + i) % len(names)] for i in range(min(batch, len(names)))]
    st = agg.setdefault("bing_news", {"요청": 0, "실패": 0, "항목": 0, "신규": 0,
                                      "pub채움": 0, "쿼리수": len(todo), "실패사유": {}})
    for i, nm in enumerate(todo):
        u = "https://www.bing.com/news/search?q=%s&format=rss" % urllib.parse.quote('"%s"' % nm)
        st["요청"] += 1
        b, err = fetch(u)
        if b is None:
            st["실패"] += 1
            st["실패사유"].setdefault(err, 0)
            st["실패사유"][err] += 1
            continue
        docs = []
        for link, title, desc, pub in parse_rss(b):
            if not link or not title:
                continue
            iso = _pub_iso(pub)
            mt = _match(names, title, desc)
            if nm not in mt:
                mt = [nm] + mt
            docs.append({"url": link, "제목": title, "본문": desc,
                         "published_at": iso, "published_at_원문": pub,
                         "원천": "bing_news", "매칭": mt[:20]})
        st["항목"] += len(docs)
        st["pub채움"] += sum(1 for d in docs if d["published_at"])
        st["신규"] += store("bing_news", docs, seen)
        if not big:
            cp.write_text(json.dumps({"idx": (cur + i + 1) % len(names),
                                      "명단": len(names)}))
        elif i % 50 == 0:
            print("  bing %d/%d 신규 %d" % (i, len(todo), st["신규"]), flush=True)
    if big:
        cp.write_text(json.dumps({"idx": 0, "명단": len(names)}))


_PARSERS = {"dcinside": parse_dcinside, "theqoo": parse_theqoo,
            "ruliweb": parse_ruliweb, "instiz": parse_instiz,
            "daum_news": parse_daum, "dogdrip": parse_dogdrip}


def _paged(src, url, page):
    if page <= 1:
        return url
    if src == "dcinside":
        return url + "&page=%d" % page
    if src == "theqoo":
        return url + "?page=%d" % page          # robots 404 = 제한없음(쿼리 포함)
    if src == "ruliweb":
        return None   # 🔴 robots: /*view=·/*cate= 등 질의어 다수 Disallow — 2페이지부터 안 간다
    if src == "instiz":
        return url + "?page=%d" % page
    # daum_news: 섹션·페이지가 서버에서 안 갈린다(1023 실측 — 같은 문서) → 1페이지만
    # dogdrip: 1페이지만(회전 수집 — 목록 갱신이 빠르다)
    return None


def run_boards(names, agg, pages):
    for src, boards in BOARDS.items():
        seen = _load_seen(src)
        st = agg.setdefault(src, {"요청": 0, "실패": 0, "항목": 0, "신규": 0,
                                  "pub채움": 0, "실패사유": {}})
        for bu in boards:
            for pg in range(1, pages + 1):
                u = _paged(src, bu, pg)
                if u is None:
                    break
                st["요청"] += 1
                b, err = fetch(u)
                if b is None:
                    st["실패"] += 1
                    st["실패사유"][u[-50:]] = err
                    break
                if len(b) < 1024:      # dcinside 이형 주소의 JS 안내 stub — 따라가지 않고 접는다
                    st["실패"] += 1
                    st["실패사유"][u[-50:]] = "stub(%dB)" % len(b)
                    break
                rows = _PARSERS[src](b, u)
                docs = []
                for link, title, body, pub_raw in rows:
                    iso = _pub_iso(pub_raw)
                    docs.append({"url": link, "제목": title, "본문": body,
                                 "published_at": iso, "published_at_원문": pub_raw,
                                 "원천": src + "/" + bu.split("=")[-1].split("/")[-1],
                                 "매칭": _match(names, title, body)})
                st["항목"] += len(docs)
                st["pub채움"] += sum(1 for d in docs if d["published_at"])
                st["신규"] += store(src, docs, seen)


# ── 전속 연속 루프(1023) ────────────────────────────────────────────────────
def run_fullspeed():
    """writer.pid 를 쥔 채 무한 회전 — 데몬 회차는 접힘(무성장·정상 · 1017 §3 규약).
    사이클 = bing 전 명단 회전(주스레드) ∥ 보드 300초 재폴링 ∥ 뉴스 600초 재폴링.
    스레드 ≤3(+주) · load1>10 이면 그 사이클은 bing 만 · robots 는 사이클마다 재확인.
    정지: state/stop_fullspeed 를 만들면 사이클 경계에서 곱게 끝난다.
    재개: 같은 명령(중복은 seen 이 접고 bing 은 커서가 잇는다)."""
    stopp = STATED / "stop_fullspeed"
    lockp = STATED / "writer.pid"
    if stopp.exists():
        stopp.unlink()
    while True:                                  # until 폴링으로 잠금 인수
        if lockp.exists():
            try:
                other = int(lockp.read_text().strip())
                if other != os.getpid():
                    os.kill(other, 0)
                    print("fullspeed — 잠금 pid %d 가 살아 있다(20초 폴링)" % other,
                          flush=True)
                    time.sleep(20)
                    continue
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        lockp.write_text(str(os.getpid()))
        break
    cyc = 0
    try:
        while not stopp.exists():
            cyc += 1
            t0 = time.time()
            with _robots_lock:
                _robots_cache.clear()            # 주행마다 robots 재확인(1017 규율)
            names, nsrc = names_1017()
            try:
                l1 = os.getloadavg()[0]
            except OSError:
                l1 = 0.0
            agg_n, agg_b, agg_g = {}, {}, {}
            done = threading.Event()

            def _poll(fn, args, every):
                while True:
                    try:
                        fn(*args)
                    except Exception as e:       # 한 원천의 사고가 사이클을 못 죽인다
                        print("fullspeed 부스레드 오류:", type(e).__name__, flush=True)
                    if done.wait(every):
                        return

            ths = []
            if l1 <= 10:                         # CPU 여유 철칙 — 부하 높으면 bing 만
                ths = [threading.Thread(target=_poll,
                                        args=(run_news_rss, (names, agg_n), 600)),
                       threading.Thread(target=_poll,
                                        args=(run_boards, (names, agg_b, 1), 300))]
                for t in ths:
                    t.start()
            try:
                run_bing(names, agg_g, len(names), False)
            finally:
                done.set()
            for t in ths:
                t.join()
            agg = {}
            for a3 in (agg_n, agg_b, agg_g):
                agg.update(a3)
            rec = {"노트": 1023, "모드": "fullspeed", "사이클": cyc,
                   "load1(시작)": round(l1, 2),
                   "시각(끝)": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "초": round(time.time() - t0, 1),
                   "명단": {"수": len(names), "출처": nsrc},
                   "이번사이클": agg, "디스크총계": totals()}
            (ROOT / "runners" / "out1023_fullspeed.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            slim = {"모드": "fullspeed1023", "사이클": cyc, "시각(끝)": rec["시각(끝)"],
                    "초": rec["초"],
                    "신규합": sum(v.get("신규", 0) for v in agg.values())}
            with open(OUTD / "run_log.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(slim, ensure_ascii=False) + "\n")
            print("fullspeed 사이클 %d — 신규합 %d · %.0f초" %
                  (cyc, slim["신규합"], rec["초"]), flush=True)
    finally:
        try:
            if int(lockp.read_text().strip()) == os.getpid():
                lockp.unlink()
        except (ValueError, OSError):
            pass
    return 0


# ── 집계·주행 ───────────────────────────────────────────────────────────────
def totals():
    """디스크 실측 — 원천별 행수·pub채움·기간(집계지 재계산이 자다)."""
    out = {}
    for top in sorted(p.name for p in OUTD.iterdir()
                      if p.is_dir() and p.name not in ("state", "bodies")):
        n = pub = 0
        lo = hi = None
        match_n = 0
        for f in sorted((OUTD / top).glob("*.jsonl.gz")):
            try:
                with gzip.open(f, "rt", encoding="utf-8") as fh:
                    for ln in fh:
                        n += 1
                        try:
                            d = json.loads(ln)
                        except Exception:
                            continue
                        p = d.get("published_at")
                        if p:
                            pub += 1
                            day = p[:10]
                            lo = day if lo is None or day < lo else lo
                            hi = day if hi is None or day > hi else hi
                        if d.get("매칭"):
                            match_n += 1
            except (EOFError, OSError, gzip.BadGzipFile):
                pass      # 쓰는 중인 gz 꼬리 — 다음 재기가 줍는다(1023)
        out[top] = {"행": n, "pub채움": pub,
                    "pub채움률": round(pub / n, 4) if n else None,
                    "기간": [lo, hi], "개체매칭행": match_n}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--big", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--bing-batch", type=int, default=150)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--fullspeed", action="store_true")
    a = ap.parse_args()
    STATED.mkdir(parents=True, exist_ok=True)
    if a.report:
        print(json.dumps(totals(), ensure_ascii=False, indent=1))
        return 0
    if a.fullspeed:
        return run_fullspeed()
    # 🔴 단일 필자 잠금 --- 데몬 회차와 --big 대수확이 «같은 gz·seen 파일»에 동시에
    # 덧붙이면 gzip 멤버가 깨질 수 있다(952 의 「쓰는 중인 gz」 병 계열). 산 pid 가
    # 잠금을 쥐고 있으면 이번 주행을 접는다 --- 장부에는 무성장으로 보이고 그걸로 족하다.
    lockp = STATED / "writer.pid"
    if lockp.exists():
        try:
            other = int(lockp.read_text().strip())
            os.kill(other, 0)                    # 살아 있나만 묻는다
            print("담론 1017 — 잠금 pid %d 가 살아 있어 접는다(무성장·정상)" % other)
            return 0
        except (ValueError, ProcessLookupError, PermissionError):
            pass                                  # 죽은 잠금 --- 이어받는다
    lockp.write_text(str(os.getpid()))
    t0 = time.time()
    names, nsrc = names_1017()
    agg = {}
    plan = ["news_rss", "bing_news", "boards"]
    if a.only:
        plan = [a.only]
    if "news_rss" in plan:
        run_news_rss(names, agg)
    if "boards" in plan:
        run_boards(names, agg, pages=4 if a.big else 1)
    if "bing_news" in plan:
        run_bing(names, agg, a.bing_batch, a.big)
    rec = {"노트": 1017, "모드": "big" if a.big else "daemon",
           "시각(끝)": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "초": round(time.time() - t0, 1),
           "명단": {"수": len(names), "출처": nsrc},
           "이번주행": agg, "디스크총계": totals()}
    OUT_JSON.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUTD / "run_log.jsonl", "a", encoding="utf-8") as f:
        slim = {k: rec[k] for k in ("모드", "시각(끝)", "초")}
        slim["신규합"] = sum(v.get("신규", 0) for v in agg.values())
        f.write(json.dumps(slim, ensure_ascii=False) + "\n")
    print("담론 1017 —", rec["모드"], "신규합",
          sum(v.get("신규", 0) for v in agg.values()), "· %.1f초" % rec["초"])
    try:
        if int(lockp.read_text().strip()) == os.getpid():
            lockp.unlink()
    except (ValueError, OSError):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
