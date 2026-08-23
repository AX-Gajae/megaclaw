# -*- coding: utf-8 -*-
"""수집 1023 — 담론 «본문» 수집기. 1017 이 쌓는(그리고 계속 쌓이는) 목록 URL 의
기사·글 본문을 robots 확인 후 수확한다. 담론 장(1019)·사건-시각 추출(1021)의
원료가 제목에서 본문으로 승격된다.

입력  /Users/ax/wm_harvest/discourse/{원천}/*.jsonl.gz  (state·bodies 제외 — 1017 산출)
산출  /Users/ax/wm_harvest/discourse/bodies/{크롤일}.jsonl.gz — 문서:
      {url, url_수집원본, 원천, 매칭수, 본문, 본문_추출기, pub_time, pub_time_rss,
       pub_일치, http, crawled_at}
      · pub_time 은 페이지 메타(JSON-LD datePublished → article:published_time →
        itemprop → <time datetime>)에서 «원천이 준 것만». 없으면 null(L0 — 크롤일 대체 금지).
      · pub_일치 = 페이지 메타와 RSS 값의 «일자» 대조(둘 다 있을 때만 · 아니면 null).

규율:
  · robots 를 호스트별로 «실제로 받아» URL 단위 검사 — Disallow 는 그 자리서 접고 계수(우회 금지)
  · 호스트별 요청 간격 ≥1.1초 — politeness 는 호스트별 · 서로 다른 호스트는 병렬
  · 워커 상한 6 (IO 중심) · load1>10 이면 2 로 축소, <5 복귀
  · bing 리다이렉트(apiclick.aspx)는 url= 파람의 실주소로 푼다 — bing 을 안 때린다
  · 재개: state/seen_body.txt(해소 URL sha1 · append-only) + state/body_fail.json(실패 계수 ·
    3회 넘으면 접는다). 죽여도 다시 돌리면 신규만 이어간다.
  · 단일 필자: state/writer_body.pid — bodies gz 의 필자는 하나뿐이다(1017 의 writer.pid 와
    별개 — 서로 다른 파일 집합이라 충돌면이 없다. 목록 gz 는 1017 필자만 쓴다).
  · 정지: state/stop_body 파일을 만들면 사이클 경계에서 곱게 끝난다.

쓰는 법:
  python3 -m runners.discourse_body1023 --once [--limit N]   # 1회 소진
  python3 -m runners.discourse_body1023 --forever            # 상시(재스캔 180초)
  python3 -m runners.discourse_body1023 --report             # 디스크 실측 집계
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
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html import unescape
from pathlib import Path

OUTD = Path("/Users/ax/wm_harvest/discourse")
BODYD = OUTD / "bodies"
STATED = OUTD / "state"
SEENP = STATED / "seen_body.txt"
FAILP = STATED / "body_fail.json"
LOCKP = STATED / "writer_body.pid"
STOPP = STATED / "stop_body"
RUNLOG = BODYD / "run_log.jsonl"
OUT_JSON = Path("/Users/ax/world_model/runners/out1023_body.json")
UA = "wm-lab-collector/1023 (research; contact: alexlee@sweetspot.co.kr)"
GAP = 1.1
MAX_WORKERS = 6
MIN_BODY = 120           # 추출 성공 문턱(자)
MAX_FAIL = 3

# ── 호스트별 politeness · robots ────────────────────────────────────────────
_hl_master = threading.Lock()
_host_lock = {}
_host_last = {}
_rb_lock = threading.Lock()
_rb_cache = {}


def _gap(host):
    with _hl_master:
        lk = _host_lock.setdefault(host, threading.Lock())
    with lk:
        d = time.time() - _host_last.get(host, 0.0)
        if d < GAP:
            time.sleep(GAP - d)
        _host_last[host] = time.time()


def _robots_ok(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc
    with _rb_lock:
        rp = _rb_cache.get(host, "?")
    if rp == "?":
        _gap(host)
        try:
            req = urllib.request.Request("%s://%s/robots.txt" % (u.scheme or "https", host),
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = r.read(1 << 19).decode("utf-8", "replace")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(txt.splitlines())
        except urllib.error.HTTPError as e:
            rp = "open" if e.code == 404 else "closed"   # RFC 9309
        except Exception:
            rp = "closed"
        with _rb_lock:
            _rb_cache[host] = rp
    if rp == "open":
        return True
    if rp == "closed":
        return False
    return rp.can_fetch(UA, url)


def fetch(url):
    """(bytes|None, 'http'|사유). robots 불허는 (None,'robots불허')."""
    if not _robots_ok(url):
        return None, "robots불허"
    for i in range(2):
        _gap(urllib.parse.urlparse(url).netloc)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read(1 << 22), "http200"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)
                continue
            return None, "HTTP %d" % e.code
        except Exception as e:
            if i == 0:
                time.sleep(3)
                continue
            return None, type(e).__name__
    return None, "재시도소진"


# ── 본문·발행시각 추출 ──────────────────────────────────────────────────────
_SCRIPT = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_LDJSON = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                     re.S | re.I)
_CONTAINERS = [
    ("article태그", re.compile(r"<article[\s>].*?</article>", re.S | re.I)),
    ("itemprop_articleBody",
     re.compile(r'<[^>]+itemprop=["\']articleBody["\'][^>]*>(.*?)</(?:div|section)>', re.S | re.I)),
    ("ndsoft", re.compile(r'<div[^>]+id=["\']article-view-content-div["\'][^>]*>(.*?)</div>\s*(?:<div|<footer|<section)', re.S | re.I)),
    ("articleBody_id", re.compile(r'<div[^>]+id=["\'](?:articleBody|article_body|newsEndContents|articeBody|news_body_area|CmAdContent)["\'][^>]*>(.*)', re.S | re.I)),
    ("dcinside", re.compile(r'<div[^>]+class=["\'][^"\']*write_div[^"\']*["\'][^>]*>(.*)', re.S | re.I)),
    ("xe_content", re.compile(r'<div[^>]+class=["\'][^"\']*xe_content[^"\']*["\'][^>]*>(.*)', re.S | re.I)),
    ("ruliweb_view", re.compile(r'<div[^>]+class=["\'][^"\']*view_content[^"\']*["\'][^>]*>(.*)', re.S | re.I)),
    ("article_class", re.compile(r'<div[^>]+class=["\'][^"\']*(?:article_view|article-body|news_view|art_txt)[^"\']*["\'][^>]*>(.*)', re.S | re.I)),
]
_META_PUB = [
    re.compile(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']article:published_time', re.I),
    re.compile(r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)', re.I),
]


def _clean_text(html_frag, cap=20000):
    t = unescape(_TAG.sub(" ", html_frag))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:cap]


def _pub_iso(raw):
    if not raw:
        return None
    raw = raw.strip()
    m = re.match(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})[T ]?(\d{2}:\d{2}(:\d{2})?)?([+-]\d{2}:?\d{2}|Z)?", raw)
    if m:
        d = "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
        if m.group(4):
            return d + "T" + m.group(4) + (m.group(6) or "+09:00").replace("Z", "+00:00")
        return d
    return None


def extract(html_bytes):
    """(본문|None, 추출기, pub_iso|None)."""
    s = html_bytes.decode("utf-8", "replace")
    s = _SCRIPT.sub(" ", s) if len(s) < (1 << 21) else _SCRIPT.sub(" ", s[: 1 << 21])
    pub = None
    body = None
    how = None
    # JSON-LD 먼저 — articleBody·datePublished 가 정본 품질
    for m in _LDJSON.finditer(html_bytes.decode("utf-8", "replace")):
        try:
            j = json.loads(m.group(1).strip())
        except Exception:
            continue
        cands = j if isinstance(j, list) else [j]
        for c in cands:
            if not isinstance(c, dict):
                continue
            g = c.get("@graph")
            for cc in ([c] + (g if isinstance(g, list) else [])):
                if not isinstance(cc, dict):
                    continue
                if pub is None and cc.get("datePublished"):
                    pub = _pub_iso(str(cc["datePublished"]))
                if body is None and cc.get("articleBody"):
                    t = re.sub(r"\s+", " ", str(cc["articleBody"])).strip()[:20000]
                    if len(t) >= MIN_BODY:
                        body, how = t, "ldjson"
    if pub is None:
        for rx in _META_PUB:
            m = rx.search(s)
            if m:
                pub = _pub_iso(m.group(1))
                if pub:
                    break
    if body is None:
        for nm, rx in _CONTAINERS:
            m = rx.search(s)
            if not m:
                continue
            frag = m.group(1) if m.groups() else m.group(0)
            t = _clean_text(frag)
            if len(t) >= MIN_BODY:
                body, how = t, nm
                break
    if body is None:
        # 일반 폴백 — <p> 합산(기사 본문은 대개 p 문단 · JS 렌더 페이지는 여기도 빈다)
        ps = re.findall(r"<p[\s>](.*?)</p>", s, re.S | re.I)
        t = re.sub(r"\s+", " ", " ".join(_clean_text(x, 4000) for x in ps)).strip()[:20000]
        if len(t) >= MIN_BODY * 2:
            body, how = t, "p합"
    return body, how, pub


# ── 입력 스캔 ───────────────────────────────────────────────────────────────
def _resolve(url):
    """bing 리다이렉트를 실주소로 푼다 — bing 은 안 때린다."""
    try:
        u = urllib.parse.urlparse(url)
    except Exception:
        return url
    if u.netloc.endswith("bing.com") and "apiclick" in u.path:
        q = urllib.parse.parse_qs(u.query)
        if q.get("url"):
            return q["url"][0]
    return url


def _sha(u):
    return hashlib.sha1(u.encode("utf-8")).hexdigest()


def scan_pending(seen, fails, limit=None):
    """목록 gz 전수 스캔 → 미수확 URL. 매칭 행 우선. gz 꼬리가 쓰는 중이면 그 파일은
    읽힌 데까지만(다음 스캔이 줍는다)."""
    rows = []
    for top in sorted(p.name for p in OUTD.iterdir()
                      if p.is_dir() and p.name not in ("state", "bodies")):
        for f in sorted((OUTD / top).glob("*.jsonl.gz")):
            try:
                with gzip.open(f, "rt", encoding="utf-8") as fh:
                    for ln in fh:
                        try:
                            d = json.loads(ln)
                        except Exception:
                            continue
                        real = _resolve(d.get("url") or "")
                        if not real.startswith("http"):
                            continue
                        h = _sha(real)
                        if h in seen or fails.get(h, 0) >= MAX_FAIL:
                            continue
                        rows.append((bool(d.get("매칭")), real, d.get("url"),
                                     d.get("원천") or top, len(d.get("매칭") or []),
                                     d.get("published_at")))
            except (EOFError, OSError, gzip.BadGzipFile):
                pass                     # 쓰는 중인 멤버 — 다음 스캔의 몫
    # 같은 실주소가 여러 목록행에 있으면 하나만(매칭 있는 행 우선)
    rows.sort(key=lambda r: (not r[0],))
    ded, got = [], set()
    for r in rows:
        h = _sha(r[1])
        if h in got:
            continue
        got.add(h)
        ded.append(r)
        if limit and len(ded) >= limit:
            break
    return ded


# ── 저장(단일 필자) ─────────────────────────────────────────────────────────
class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.buf = []
        self.stats = {"성공": 0, "robots불허": 0, "추출실패": 0, "실패": 0,
                      "pub_meta채움": 0, "pub_일치": 0, "pub_불일치": 0, "실패사유": {}}

    def add(self, doc, seen_sha):
        with self.lock:
            self.buf.append((doc, seen_sha))
            if len(self.buf) >= 50:
                self._flush()

    def _flush(self):
        if not self.buf:
            return
        day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        BODYD.mkdir(parents=True, exist_ok=True)
        with gzip.open(BODYD / (day + ".jsonl.gz"), "at", encoding="utf-8") as f:
            for d, _ in self.buf:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        with open(SEENP, "a", encoding="utf-8") as f:
            for _, h in self.buf:
                f.write(h + "\n")
        self.buf = []

    def flush(self):
        with self.lock:
            self._flush()


def load_fails():
    if FAILP.exists():
        try:
            return json.loads(FAILP.read_text())
        except Exception:
            return {}
    return {}


def load_seen():
    if not SEENP.exists():
        return set()
    return set(x.strip() for x in SEENP.read_text().splitlines() if x.strip())


# ── 주행 ────────────────────────────────────────────────────────────────────
def process(pending, seen, fails, store):
    """호스트 분할 큐 — 워커가 안 잡힌 호스트를 통째로 잡아 배치 처리.
    seen 은 성공·영구실패(robots)만 채운다 — 일시 실패는 다음 스캔이 재시도(≤MAX_FAIL)."""
    byhost = {}
    for r in pending:
        byhost.setdefault(urllib.parse.urlparse(r[1]).netloc, []).append(r)
    hosts = sorted(byhost, key=lambda h: -len(byhost[h]))
    master = threading.Lock()
    busy = set()
    fail_lock = threading.Lock()

    def nworkers():
        try:
            l1 = os.getloadavg()[0]
        except OSError:
            return MAX_WORKERS
        return 2 if l1 > 10 else MAX_WORKERS

    def worker():
        while True:
            if STOPP.exists():
                return
            with master:
                free = [h for h in hosts if h not in busy and byhost[h]]
                if not free:
                    return
                h = free[0]
                busy.add(h)
                batch, byhost[h] = byhost[h][:20], byhost[h][20:]
            for _, real, orig, top, nmatch, pub_rss in batch:
                sha = _sha(real)
                b, why = fetch(real)
                now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if b is None:
                    with fail_lock:
                        if why == "robots불허":
                            store.stats["robots불허"] += 1
                            # robots 는 영구 판정 — seen 에 넣어 재시도 안 한다
                            store.add({"url": real, "url_수집원본": orig, "원천": top,
                                       "매칭수": nmatch, "본문": None, "본문_추출기": None,
                                       "pub_time": None, "pub_time_rss": pub_rss,
                                       "pub_일치": None, "http": why,
                                       "crawled_at": now}, sha)
                            seen.add(sha)
                        else:
                            store.stats["실패"] += 1
                            store.stats["실패사유"][why] = \
                                store.stats["실패사유"].get(why, 0) + 1
                            fails[sha] = fails.get(sha, 0) + 1
                    continue
                body, how, pub = extract(b)
                match_day = None
                if pub and pub_rss:
                    match_day = (pub[:10] == pub_rss[:10])
                with fail_lock:
                    if body is None:
                        store.stats["추출실패"] += 1
                    else:
                        store.stats["성공"] += 1
                    if pub:
                        store.stats["pub_meta채움"] += 1
                    if match_day is True:
                        store.stats["pub_일치"] += 1
                    elif match_day is False:
                        store.stats["pub_불일치"] += 1
                store.add({"url": real, "url_수집원본": orig, "원천": top,
                           "매칭수": nmatch, "본문": body, "본문_추출기": how,
                           "pub_time": pub, "pub_time_rss": pub_rss,
                           "pub_일치": match_day, "http": why, "crawled_at": now}, sha)
                seen.add(sha)
            with master:
                busy.discard(h)

    n = min(nworkers(), max(1, len(hosts)))
    ths = [threading.Thread(target=worker) for _ in range(n)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    store.flush()
    FAILP.write_text(json.dumps(fails))
    return n


def totals():
    n = ok = pub = 0
    for f in sorted(BODYD.glob("*.jsonl.gz")):
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for ln in fh:
                    n += 1
                    try:
                        d = json.loads(ln)
                    except Exception:
                        continue
                    if d.get("본문"):
                        ok += 1
                    if d.get("pub_time"):
                        pub += 1
        except (EOFError, OSError, gzip.BadGzipFile):
            pass
    return {"행": n, "본문있음": ok, "pub_time있음": pub}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    STATED.mkdir(parents=True, exist_ok=True)
    if a.report:
        print(json.dumps(totals(), ensure_ascii=False))
        return 0
    if LOCKP.exists():
        try:
            other = int(LOCKP.read_text().strip())
            os.kill(other, 0)
            print("본문 1023 — 잠금 pid %d 가 살아 있어 접는다(정상)" % other)
            return 0
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    LOCKP.write_text(str(os.getpid()))
    if STOPP.exists():
        STOPP.unlink()
    seen = load_seen()
    fails = load_fails()
    store = Store()
    cyc = 0
    try:
        while True:
            cyc += 1
            t0 = time.time()
            pending = scan_pending(seen, fails, a.limit)
            nw = process(pending, seen, fails, store) if pending else 0
            row = {"모드": "forever" if a.forever else "once", "사이클": cyc,
                   "대기행": len(pending), "워커": nw,
                   "초": round(time.time() - t0, 1),
                   "시각(끝)": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "누적": dict(store.stats)}
            BODYD.mkdir(parents=True, exist_ok=True)
            with open(RUNLOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            OUT_JSON.write_text(json.dumps({"노트": 1023, "최근사이클": row,
                                            "디스크총계": totals()},
                                           ensure_ascii=False, indent=1),
                                encoding="utf-8")
            print("본문 1023 — 사이클 %d · 대기 %d · %s" %
                  (cyc, len(pending), json.dumps(store.stats, ensure_ascii=False)),
                  flush=True)
            if not a.forever or STOPP.exists():
                break
            time.sleep(180)
    finally:
        store.flush()
        FAILP.write_text(json.dumps(fails))
        try:
            if int(LOCKP.read_text().strip()) == os.getpid():
                LOCKP.unlink()
        except (ValueError, OSError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
