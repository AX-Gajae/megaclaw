# -*- coding: utf-8 -*-
"""1037 A부 — Common Crawl WARC Range 회수 + 발행일 추출.

사전등록 docs/탐색/1037.md §0 (커밋 8299b9058) — 이 러너는 그 «뒤»에 쓰였고
주행 중 수정하지 않는다(조항 66).

  --stage index   매니페스트 9개 내려받아 파일명→전체경로 색인
  --stage probe   기제 재현 탐침(단건 Range · 206 · gunzip · WARC · 발행일)
  --stage fetch   23,382 CC 문서 전량 Range → 발행일 (동시 12 · 재시도 3)
  --stage report  집계

🔴 실패 사유를 셋으로 센다(조항 59): 「없다」·「못 봤다」·「못 읽었다」.
🔴 크롤일 대체 금지 — 실패는 null.
"""
import argparse, gzip, io, json, os, re, sys, time, hashlib, collections, threading
import datetime as dt
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = Path("/Users/ax/wm_harvest/foundation/warc1037")
MAN = OUT / "manifests"
OUT.mkdir(parents=True, exist_ok=True); MAN.mkdir(parents=True, exist_ok=True)

BASE = "https://data.commoncrawl.org/"
CRAWLS = ["CC-MAIN-2017-04", "CC-MAIN-2018-05", "CC-MAIN-2021-43",
          "CC-MAIN-2022-40", "CC-MAIN-2022-49",
          "CC-MAIN-2017-09", "CC-MAIN-2018-09", "CC-MAIN-2021-49", "CC-MAIN-2022-33"]
UA = "wm-lab-research/1.0 (academic; low-rate; contact alexlee@sweetspot.co.kr)"
CONC = 12
RETRY = 3

# ── §0-바 발행일 사슬 ────────────────────────────────────────────────────
RANKS = ["jsonld", "og", "htmlmeta", "time", "url", "body"]
CONF = {"jsonld": 0.95, "og": 0.90, "htmlmeta": 0.85, "time": 0.75, "url": 0.70, "body": 0.60}
RE_JSONLD = re.compile(r'"datePublished"\s*:\s*"([^"]{4,40})"')
RE_OG1 = re.compile(r'article:published_time["\']?[^>]{0,150}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_OG2 = re.compile(r'content\s*=\s*["\']([^"\']{4,40})["\'][^>]{0,150}?article:published_time', re.I)
RE_META1 = re.compile(r'<meta[^>]{0,250}?(?:name|itemprop|property)\s*=\s*["\'](?:date|pubdate|publishdate|publish[-_]date|datePublished|article[._:]published(?:_time)?|sailthru\.date|DC\.date(?:\.issued)?|parsely-pub-date)["\'][^>]{0,250}?content\s*=\s*["\']([^"\']{4,40})', re.I)
RE_META2 = re.compile(r'<meta[^>]{0,250}?content\s*=\s*["\']([^"\']{4,40})["\'][^>]{0,250}?(?:name|itemprop|property)\s*=\s*["\'](?:date|pubdate|publishdate|publish[-_]date|datePublished)["\']', re.I)
RE_TIME = re.compile(r'<time[^>]{0,250}?datetime\s*=\s*["\']([^"\']{4,40})', re.I)
RE_U_YMD_SLASH = re.compile(r'/(19\d{2}|20[0-2]\d)/(\d{1,2})/(\d{1,2})(?=[/?#.]|$)')
RE_U_YMD_SEP = re.compile(r'[/=_.-](19\d{2}|20[0-2]\d)[-._](\d{1,2})[-._](\d{1,2})(?=[/?#._-]|$)')
RE_U_YMD8 = re.compile(r'(?<!\d)(19\d{2}|20[0-2]\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)')
RE_U_QDATE = re.compile(r'[?&](?:date|dt|ymd|d)=?(19\d{2}|20[0-2]\d)[-.]?(\d{2})[-.]?(\d{2})(?!\d)')
RE_BODYMARK = re.compile(
    r'(?:입력|등록|승인|작성일?|게재|송고|기사입력|발행일?)\s*[:\-–]?\s*'
    r'(19\d{2}|20[0-2]\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})')
RE_TAG = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.I | re.S)
RE_STRIP = re.compile(r'<[^>]+>')
RE_CHARSET = re.compile(rb'charset\s*=\s*["\']?\s*([A-Za-z0-9_\-]+)', re.I)

RE_V_ISO = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
RE_V_DOT = re.compile(r'(\d{4})[./](\d{1,2})[./](\d{1,2})')
RE_V_8 = re.compile(r'^\s*(\d{4})(\d{2})(\d{2})\s*$')


def norm_date(v):
    if not v:
        return None
    v = str(v).strip()
    for r in (RE_V_8, RE_V_ISO, RE_V_DOT):
        m = r.search(v)
        if m:
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return dt.date(y, mo, d).isoformat()
            except Exception:
                return None
    return None


def sound(iso, crawl_iso):
    """온전성: 1991≤연≤2026 · 발행일 ≤ 크롤시각+2일."""
    if not iso:
        return False
    d = dt.date.fromisoformat(iso)
    if not (1991 <= d.year <= 2026):
        return False
    return d <= dt.date.fromisoformat(crawl_iso[:10]) + dt.timedelta(days=2)


def candidates(html, url, crawl_iso):
    """순위별 «온전한» 후보 목록. 같은 순위 안에서는 가장 이른 날짜."""
    out = {}
    def put(rank, vals):
        got = sorted({x for x in (norm_date(v) for v in vals) if x and sound(x, crawl_iso)})
        if got:
            out[rank] = got
    put("jsonld", RE_JSONLD.findall(html))
    put("og", RE_OG1.findall(html) + RE_OG2.findall(html))
    put("htmlmeta", RE_META1.findall(html) + RE_META2.findall(html))
    put("time", RE_TIME.findall(html))
    uvals = []
    for r in (RE_U_YMD_SLASH, RE_U_YMD_SEP, RE_U_YMD8, RE_U_QDATE):
        for m in r.finditer(url or ""):
            uvals.append(f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}")
    put("url", uvals)
    body = RE_STRIP.sub(" ", RE_TAG.sub(" ", html[:200000]))
    bvals = [f"{int(a):04d}-{int(b):02d}-{int(c):02d}" for a, b, c in RE_BODYMARK.findall(body)[:20]]
    put("body", bvals)
    return out


def pick(cands):
    for r in RANKS:
        if r in cands:
            best = cands[r][0]
            conflict = 0
            for r2 in RANKS:
                if r2 == r or r2 not in cands:
                    continue
                if abs((dt.date.fromisoformat(cands[r2][0]) - dt.date.fromisoformat(best)).days) > 7:
                    conflict = 1
            return best, r, CONF[r], conflict
    return None, None, None, 0


# ── WARC ─────────────────────────────────────────────────────────────────
def decode(raw):
    m = RE_CHARSET.search(raw[:4000])
    encs = []
    if m:
        e = m.group(1).decode("ascii", "ignore").lower()
        encs.append({"euc-kr": "cp949", "ks_c_5601-1987": "cp949", "utf8": "utf-8"}.get(e, e))
    encs += ["utf-8", "cp949", "latin-1"]
    for e in encs:
        try:
            return raw.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", "replace")


def parse_warc(buf):
    """(warc_type, http_body_bytes, http_headers_lower) 또는 예외."""
    i = buf.find(b"\r\n\r\n")
    if i < 0:
        raise ValueError("warc헤더없음")
    wh = buf[:i].decode("latin-1")
    wtype = ""
    for line in wh.split("\r\n"):
        if line.lower().startswith("warc-type:"):
            wtype = line.split(":", 1)[1].strip().lower()
    rest = buf[i + 4:]
    j = rest.find(b"\r\n\r\n")
    if j < 0:
        raise ValueError("http헤더없음")
    hh = rest[:j].decode("latin-1").lower()
    body = rest[j + 4:]
    if "transfer-encoding: chunked" in hh:
        body = dechunk(body)
    if "content-encoding: gzip" in hh:
        try:
            body = gzip.decompress(body)
        except Exception:
            try:
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
            except Exception:
                pass
    elif "content-encoding: deflate" in hh:
        import zlib
        try:
            body = zlib.decompress(body)
        except Exception:
            try:
                body = zlib.decompress(body, -15)
            except Exception:
                pass
    return wtype, body, hh


def dechunk(b):
    out = bytearray(); i = 0
    while True:
        j = b.find(b"\r\n", i)
        if j < 0:
            break
        try:
            n = int(b[i:j].split(b";")[0], 16)
        except Exception:
            return bytes(b)
        if n == 0:
            break
        out += b[j + 2:j + 2 + n]; i = j + 2 + n + 2
    return bytes(out)


_lock = threading.Lock()


def fetch_one(rec, idx):
    """S2~S6. 실패 사유를 문자열로 돌려준다."""
    fid = rec["문서id"]
    fname = rec["f"].split("/")[-1]
    path = idx.get(fname)
    if not path:
        return {"문서id": fid, "단계": "S2", "실패": "경로없음"}
    url = BASE + path
    o, s = int(rec["o"]), int(rec["s"])
    hdr = {"Range": f"bytes={o}-{o+s-1}", "User-Agent": UA, "Accept-Encoding": "identity"}
    last = None
    for att in range(RETRY):
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=60) as r:
                code = r.status
                raw = r.read()
            if code != 206:
                last = f"HTTP{code}"; time.sleep(0.5 * (4 ** att)); continue
            if len(raw) != s:
                last = f"바이트불일치({len(raw)}≠{s})"; time.sleep(0.5 * (4 ** att)); continue
            break
        except urllib.error.HTTPError as e:
            last = f"HTTP{e.code}"
            if e.code in (403, 404, 416):
                return {"문서id": fid, "단계": "S3", "실패": last, "재시도": att}
            time.sleep(0.5 * (4 ** att))
        except Exception as e:
            last = f"{type(e).__name__}"; time.sleep(0.5 * (4 ** att))
    else:
        return {"문서id": fid, "단계": "S3", "실패": last or "재시도소진", "재시도": RETRY}
    try:
        buf = gzip.decompress(raw)
    except Exception as e:
        return {"문서id": fid, "단계": "S4", "실패": f"gunzip:{type(e).__name__}"}
    if len(buf) < int(rec["rs"]) * 0.3:
        return {"문서id": fid, "단계": "S4", "실패": f"작음({len(buf)}<{rec['rs']})"}
    try:
        wtype, body, hh = parse_warc(buf)
    except Exception as e:
        return {"문서id": fid, "단계": "S5", "실패": f"warc:{e}"}
    if wtype != "response":
        return {"문서id": fid, "단계": "S5", "실패": f"타입:{wtype}"}
    if not body:
        return {"문서id": fid, "단계": "S5", "실패": "본문0바이트"}
    html = decode(body)
    cands = candidates(html, rec["u"], rec["ts"])
    val, meth, conf, conflict = pick(cands)
    nlink = html.count("<a href") + html.count("<A HREF")
    r = {"문서id": fid, "단계": "S6" if val else "S6실패", "warc바이트": len(buf),
         "html글자": len(html), "링크수": nlink,
         "published_at": val, "method": meth, "confidence": conf, "충돌": conflict,
         "후보": {k: v[0] for k, v in cands.items()},
         "crawl_ts": rec["ts"], "u": rec["u"], "crawl덩이": rec.get("덩이")}
    if not val:
        r["실패"] = "날짜없음" if not cands else "날짜불온전"
    return r


def build_index():
    idx = {}
    per = {}
    for c in CRAWLS:
        p = MAN / f"{c}.paths.gz"
        if not p.exists():
            t0 = time.time()
            urllib.request.urlretrieve(f"{BASE}crawl-data/{c}/warc.paths.gz", p)
            print(f"  받음 {c} {p.stat().st_size:,}B {time.time()-t0:.1f}s", flush=True)
        n = 0
        with gzip.open(p, "rt") as f:
            for line in f:
                line = line.strip()
                if line:
                    idx.setdefault(line.split("/")[-1], line); n += 1
        per[c] = n
    return idx, per


def load_coords():
    recs = []
    for line in gzip.open(OUT / "warc_coords.jsonl.gz", "rt"):
        v = json.loads(line)
        f = v["f"]
        if "CC-MAIN-" not in f:
            v["덩이"] = "wide16(비CC)"
        else:
            d = f.split("CC-MAIN-")[-1][:8]
            v["덩이"] = ("㉠2017-04" if d.startswith("201701") else
                         "㉡2018-05" if d.startswith("201801") else
                         "㉢2021-43" if d.startswith("202110") else
                         "㉣2022-40" if d < "20221100" else "㉤2022-49")
        recs.append(v)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if a.stage == "index":
        idx, per = build_index()
        recs = load_coords()
        cc = [r for r in recs if "CC-MAIN-" in r["f"]]
        hit = sum(1 for r in cc if r["f"].split("/")[-1] in idx)
        by = collections.Counter()
        for r in cc:
            by[(r["덩이"], r["f"].split("/")[-1] in idx)] += 1
        rep = {"매니페스트": per, "색인 파일명": len(idx),
               "CC 문서": len(cc), "S2 경로매칭": hit,
               "S2 실패": len(cc) - hit,
               "덩이별": {f"{k[0]}/{'맞음' if k[1] else '없음'}": v for k, v in sorted(by.items())}}
        (OUT / "index_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(rep, ensure_ascii=False, indent=1), flush=True)
        return

    idx, _ = build_index()
    recs = [r for r in load_coords() if "CC-MAIN-" in r["f"]]

    if a.stage == "probe":
        import random
        random.seed(1037)
        sub = random.sample(recs, 12)
        for r in sub:
            res = fetch_one(r, idx)
            print(json.dumps({k: v for k, v in res.items() if k != "u"}, ensure_ascii=False)[:400], flush=True)
        return

    if a.stage == "fetch":
        if a.limit:
            recs = recs[:a.limit]
        outp = OUT / "warc_pub.jsonl"
        done = set()
        if outp.exists():
            for line in open(outp, encoding="utf-8"):
                try:
                    done.add(json.loads(line)["문서id"])
                except Exception:
                    pass
        todo = [r for r in recs if r["문서id"] not in done]
        print(f"할 것 {len(todo):,} (이미 {len(done):,})", flush=True)
        t0 = time.time(); n = [0]
        f = open(outp, "a", encoding="utf-8")
        def work(r):
            res = fetch_one(r, idx)
            with _lock:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                n[0] += 1
                if n[0] % 500 == 0:
                    f.flush()
                    el = time.time() - t0
                    print(f"  {n[0]:,}/{len(todo):,} · {el:.0f}s · {n[0]/max(el,1):.1f}/s", flush=True)
        with ThreadPoolExecutor(max_workers=CONC) as ex:
            list(ex.map(work, todo))
        f.close()
        print(f"끝 {n[0]:,} · {time.time()-t0:.0f}s", flush=True)
        return


if __name__ == "__main__":
    main()
