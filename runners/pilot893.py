# -*- coding: utf-8 -*-
"""노트 893 측정 --- 시간축 파일럿 220건(실물 200 + 음성 20).

사전등록은 `data/lab/denominator.json` 의 '**사전등록** 시간축 코퍼스가 …' 칸.
게이트 셋: G1 후견지명 > 40% · G2 작품당 수확 중앙값 > 5 · G3 댓글 부모 참조 있음.

**`ingest/fanout.py` 의 첫 호출자다**(티처 #53 M6 이 '호출자 0건인 죽은 모듈' 로 지목).
캐시=재개 · 실패도 `ok:false` 로 적는다 --- 안 적으면 '안 긁은 것'과 '긁었는데 없는
것'이 안 갈린다(노트 658).

원천 넷과 창은 **측정 전에 고정**했다:
  ① 구글 뉴스 RSS      대칭창 ±180d (사전 2요청)
  ② 네이버 블로그 기간검색 같은 대칭창 · 각 1쪽
  ③ 디시 통합검색      창 없음 · 최신순 1쪽 + 정확도순 1쪽
  ④ 디시 댓글 API      G3 전용 · 표본의 부분집합
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html as _html
import json
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from ingest import social                                    # noqa: E402
from ingest.fanout import fanout, summarize                  # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out893_pilot.json"
CACHE = "data/state/cache_p893"
CACHE_CMT = "data/state/cache_p893_cmt"
WIN = 180
POLITE = 0.6            # 작업 하나 안에서 요청 사이

# ── 요청 계기 --- 몇 번 두드렸고 몇 바이트를 받았나(배선 검사 ㄹ · 항등 통제 ㄷ)
_LK = threading.Lock()
REQ = {"n": 0, "bytes": [], "fail": Counter(), "by_src": Counter()}


def fetch(url: str, src: str, data=None, extra=None, timeout: int = 25) -> str:
    h = dict(social.UA)
    h.update(extra or {})
    req = urllib.request.Request(url, headers=h,
                                 data=(urllib.parse.urlencode(data).encode()
                                       if data else None))
    with _LK:
        REQ["n"] += 1
        REQ["by_src"][src] += 1
    try:
        b = urllib.request.urlopen(req, timeout=timeout).read()
    except Exception as e:
        with _LK:
            REQ["fail"][f"{src}:{type(e).__name__}"] += 1
        raise
    with _LK:
        REQ["bytes"].append([src, len(b)])
    return b.decode("utf-8", "ignore")


def shift(d: str, days: int) -> str:
    return (dt.date.fromisoformat(d[:10]) + dt.timedelta(days=days)).isoformat()


# ── 원천 ①  구글 뉴스 RSS ─────────────────────────────────────
def news(q: str, s: str, e: str) -> list[dict]:
    u = ("https://news.google.com/rss/search?q="
         + urllib.parse.quote(f"{q} after:{s} before:{e}")
         + "&hl=ko&gl=KR&ceid=KR:ko")
    h = fetch(u, "news")
    out = []
    for b in re.findall(r"<item>(.*?)</item>", h, re.S):
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", b, re.S)
        p = re.search(r"<pubDate>([^<]+)</pubDate>", b)
        iso = None
        if p:
            try:
                from email.utils import parsedate_to_datetime
                iso = parsedate_to_datetime(p.group(1)).date().isoformat()
            except Exception:
                iso = None
        title = (t.group(1).strip() if t else "")[:200]
        out.append({"원천": "뉴스", "제목": title, "시각": iso,
                    "게시": p.group(1).strip() if p else None,
                    "id": "news:" + hashlib.sha1((title + str(iso)).encode()).hexdigest()[:16]})
    # 🔴 조항 59 --- **빈 것을 부정으로 읽지 마라.** 0건일 때 그것이 '진짜 없음'인지
    # '내 파서가 깨진 것'인지 가른다. 표지가 없으면 0 을 내지 않고 **실패로 올린다.**
    if not out and "<rss" not in h[:400]:
        raise ValueError("뉴스 0건인데 RSS 표지 없음 --- 판정 불가")
    return out


# ── 원천 ②  네이버 블로그 기간검색 ────────────────────────────
_NAV_D = re.compile(r">(\d{4})\.\s?(\d{1,2})\.\s?(\d{1,2})\.?<")


def naver(q: str, s: str, e: str) -> list[dict]:
    ymd = lambda x: x.replace("-", "")
    u = ("https://search.naver.com/search.naver?ssc=tab.blog.all&query="
         + urllib.parse.quote(q)
         + f"&nso=so%3Ar%2Cp%3Afrom{ymd(s)}to{ymd(e)}&start=1")
    h = fetch(u, "naver")
    out = []
    for b in re.split(r'data-template-id="ugcItem"', h)[1:]:
        m = _NAV_D.search(b)
        iso = ("%04d-%02d-%02d" % tuple(int(x) for x in m.groups())) if m else None
        txt = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b))).strip()
        txt = txt.split("desk\">", 1)[-1][:120]
        out.append({"원천": "블로그", "제목": txt[:120], "시각": iso, "창": [s, e],
                    "id": "nav:" + hashlib.sha1((txt + str(iso)).encode()).hexdigest()[:16]})
    if not out and "검색결과가 없" not in h:
        raise ValueError("블로그 0건인데 무결과 표지 없음 --- 판정 불가")
    return out


# ── 원천 ③  디시 통합검색(창 없음) ────────────────────────────
_DC_LI = re.compile(r"<li>(.*?)</li>", re.S)
_DC_DT = re.compile(r'class="date_time">([\d.]+)\s+([\d:]+)<')
_DC_LN = re.compile(r"gall\.dcinside\.com/(?:mgallery/|mini/)?board/view/\?id=([\w]+)&(?:amp;)?no=(\d+)")


def dcin(q: str, sort: str) -> list[dict]:
    u = ("https://search.dcinside.com/post/"
         + ("sort/accuracy/" if sort == "정확도" else "")
         + "q/" + urllib.parse.quote(q))
    h = fetch(u, "dc")
    out = []
    for b in _DC_LI.findall(h):
        ln = _DC_LN.search(b)
        if not ln:
            continue
        d = _DC_DT.search(b)
        iso = None
        if d:
            p = d.group(1).strip(".").split(".")
            if len(p) == 3:
                iso = "%04d-%02d-%02d" % (int(p[0]), int(p[1]), int(p[2]))
        t = re.search(r'class="tit_txt"[^>]*>(.*?)</a>', b, re.S)
        out.append({"원천": "디시", "제목": _html.unescape(
            re.sub(r"<[^>]+>", "", t.group(1))).strip()[:200] if t else "",
            "시각": iso, "갤": ln.group(1), "글번호": ln.group(2),
            "m": "mgallery" in ln.group(0), "id": f"dc:{ln.group(1)}:{ln.group(2)}"})
    if not out and "sch_result" not in h:
        raise ValueError("디시 0건인데 결과 컨테이너 없음 --- 판정 불가")
    return out


# ── 작업 하나 ────────────────────────────────────────────────
def harvest(it: dict) -> dict:
    q, t0 = it["질의"], it["t_0"]
    pre, post = (shift(t0, -WIN), t0), (t0, shift(t0, WIN))
    items, err = [], {}
    steps = [("뉴스사전", lambda: news(q, *pre)), ("뉴스사후", lambda: news(q, *post)),
             ("블로그사전", lambda: naver(q, *pre)), ("블로그사후", lambda: naver(q, *post)),
             ("디시최신", lambda: dcin(q, "최신")), ("디시정확", lambda: dcin(q, "정확도"))]
    stat = {}
    for name, fn in steps:
        try:
            got = fn()
            for g in got:
                g["단계"] = name
            items += got
            stat[name] = len(got) if got else "확인된 0"
        except Exception as e:
            err[name] = f"{type(e).__name__}: {e}"[:120]
            stat[name] = "판정 불가"
        time.sleep(POLITE)
    seen, uniq = set(), []
    for g in items:
        if g["id"] in seen:
            continue
        seen.add(g["id"])
        uniq.append(g)
    return {"질의": q, "t_0": t0, "층": it["층"], "질의출처": it.get("질의출처"),
            "항목수": len(uniq), "중복": len(items) - len(uniq),
            "단계별": stat, "실패단계": err, "항목": uniq}


# ── 별칭(질의어) 준비 --- AniList ─────────────────────────────
ANI_Q = """query($ids:[Int]){ Page(perPage:50){ media(id_in:$ids, type:MANGA){
 id title{romaji english native} synonyms startDate{year month day} }}}"""
ANI_S = """query($s:String){ Page(perPage:5){ media(search:$s, type:MANGA){
 id title{romaji english native} synonyms popularity }}}"""


def _post_gql(query, variables) -> str:
    body = json.dumps({"query": query, "variables": variables}).encode()
    h = dict(social.UA)
    h["Content-Type"] = "application/json"
    req = urllib.request.Request("https://graphql.anilist.co", data=body, headers=h)
    with _LK:
        REQ["n"] += 1
        REQ["by_src"]["anilist"] += 1
    b = urllib.request.urlopen(req, timeout=30).read()
    with _LK:
        REQ["bytes"].append(["anilist", len(b)])
    return b.decode("utf-8", "ignore")


def _hangul(s) -> bool:
    return any("가" <= c <= "힣" for c in str(s or ""))


def aliases(sample) -> dict:
    """media_id → 질의어와 그 출처. **어느 필드에서 왔는지 반드시 적는다.**"""
    p = ROOT / "data/state/pilot893_alias.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    ids = [s["media_id"] for s in sample]
    got = {}
    for i in range(0, len(ids), 50):
        d = json.loads(_post_gql(ANI_Q, {"ids": ids[i:i + 50]}))
        for m in d["data"]["Page"]["media"]:
            got[str(m["id"])] = m
        time.sleep(1.2)
    p.write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
    return got


def pick_query(rec, ani) -> tuple[str, str]:
    if ani:
        nat = (ani.get("title") or {}).get("native")
        if _hangul(nat):
            return nat, "AniList native(한글)"
        for s in ani.get("synonyms") or []:
            if _hangul(s):
                return s, "AniList synonyms(한글)"
        en = (ani.get("title") or {}).get("english")
        if en:
            return en, "AniList english"
    return rec["title"], "manga_records.title(romaji)"


# ── G3  디시 댓글 트리 ───────────────────────────────────────
def comments(it: dict) -> dict:
    gid, no = it["갤"], it["글번호"]
    seg = "mgallery/" if it.get("m") else ""
    view = f"https://gall.dcinside.com/{seg}board/view/?id={gid}&no={no}"
    h = fetch(view, "dcview", extra={"Referer": "https://gall.dcinside.com/"})
    m = re.search(r'name="e_s_n_o"\s+value="([^"]+)"', h)
    esno = m.group(1) if m else "3eabc1fe0b9e5cbf1e"
    gtype = "M" if it.get("m") else "G"
    raw = fetch("https://gall.dcinside.com/board/comment/", "dccmt",
                data={"id": gid, "no": no, "cmt_id": gid, "cmt_no": no,
                      "e_s_n_o": esno, "comment_page": "1", "_GALLTYPE_": gtype},
                extra={"X-Requested-With": "XMLHttpRequest", "Referer": view,
                       "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    d = json.loads(raw)
    cs = d.get("comments") or []
    cs = [c for c in cs if isinstance(c, dict)]
    nos = {str(c.get("no")) for c in cs}
    kids = [c for c in cs if str(c.get("depth")) not in ("0", "None", "")]
    return {"갤": gid, "글번호": no, "e_s_n_o 파싱": bool(m), "총": d.get("total_cnt"),
            "댓글": len(cs), "답글(depth>0)": len(kids),
            "답글의 부모가 트리 안에 있나": sum(1 for c in kids if str(c.get("c_no")) in nos),
            "필드": sorted(cs[0].keys())[:12] if cs else [],
            "표본": [{k: c.get(k) for k in ("no", "parent", "depth", "c_no", "rcnt", "reg_date")}
                   for c in cs[:8]]}


# ── 채점 ─────────────────────────────────────────────────────
def main():
    t_start = time.time()
    smp = json.loads((ROOT / "data/state/pilot893_sample.json").read_text(encoding="utf-8"))
    sample, fakes = smp["표본"], smp["음성 통제"]

    # ── 배선 ㄱ  sha 재확인
    sha = lambda o: hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    wire = {"ㄱ sha256 표본 일치": sha(sample) == smp["sha256 표본"],
            "ㄱ sha256 음성 일치": sha(fakes) == smp["sha256 음성"]}
    assert all(wire.values()), wire
    print("배선 ㄱ 통과", flush=True)

    ani = aliases(sample)
    wire["AniList 응답률"] = f"{len(ani)}/{len(sample)}"

    items = []
    for s in sample:
        q, src = pick_query(s, ani.get(str(s["media_id"])))
        a = ani.get(str(s["media_id"])) or {}
        sd = a.get("startDate") or {}
        t0 = s["t_0"]
        t0src = s["t_0 출처"]
        if sd.get("year") and sd.get("month") and sd.get("day"):
            t0 = "%04d-%02d-%02d" % (sd["year"], sd["month"], sd["day"])
            t0src = "AniList startDate"
        items.append({**s, "질의": q, "질의출처": src, "t_0": t0, "t_0 출처": t0src})
    for f in fakes:
        items.append({**f, "질의출처": "음성 통제(생성)"})

    # ── 음성 20 의 비존재 확인
    exists = {}
    for f in fakes:
        try:
            d = json.loads(_post_gql(ANI_S, {"s": f["질의"]}))["data"]["Page"]["media"]
            hit = [m for m in d
                   if f["질의"] in json.dumps(m, ensure_ascii=False)]
            exists[f["질의"]] = {"검색결과": len(d), "제목 정확일치": len(hit)}
        except Exception as e:
            exists[f["질의"]] = {"오류": f"{type(e).__name__}: {e}"[:80]}
        time.sleep(0.8)
    wire["음성 비존재 확인"] = {"정확일치 있는 것":
                          [k for k, v in exists.items() if v.get("제목 정확일치")],
                          "전수": len(exists)}

    # ── 수확
    n0 = REQ["n"]
    print(f"수확 시작 --- 대상 {len(items)} · 지금까지 요청 {n0}", flush=True)
    rep = fanout(items, key=lambda x: x["record_id"], cache=CACHE, work=harvest,
                 workers=8, sleep=1.5, report_every=20)
    n1 = REQ["n"]

    # ── 배선 ㄷ  항등 통제: 같은 목록을 다시 → 0 요청이어야 한다
    rep2 = fanout(items, key=lambda x: x["record_id"], cache=CACHE, work=harvest,
                  workers=8, sleep=1.5, report_every=1000)
    wire["ㄷ 항등 통제(2회차 요청 수)"] = REQ["n"] - n1
    wire["ㄷ 항등 통제 통과"] = (REQ["n"] - n1) == 0
    wire["1회차 요청 수"] = n1 - n0
    wire["2회차가 새로 긁은 대상"] = rep2["이번에 긁음"]

    # ── 읽기
    res = {}
    for it in items:
        p = ROOT / CACHE / f"{it['record_id']}.json"
        res[it["record_id"]] = json.loads(p.read_text(encoding="utf-8"))
    ok = {k: v for k, v in res.items() if v.get("ok")}
    real = {k: v for k, v in ok.items() if not k.startswith("FAKE")}
    fake = {k: v for k, v in ok.items() if k.startswith("FAKE")}

    def med(xs):
        return round(statistics.median(xs), 2) if xs else None

    yields_real = [v["항목수"] for v in real.values()]
    yields_fake = [v["항목수"] for v in fake.values()]
    by_layer = {}
    for lab in ("상", "중", "하"):
        xs = [v["항목수"] for v in real.values() if v["층"] == lab]
        by_layer[lab] = {"n": len(xs), "중앙값": med(xs),
                         "평균": round(sum(xs) / len(xs), 2) if xs else None,
                         "0건": sum(1 for x in xs if x == 0), "최대": max(xs) if xs else None}

    # G1 --- 전체 풀 · 원천별 · 창 준/안 준
    allc = {"전체": [], "창 준(뉴스·블로그)": [], "창 없음(디시)": []}
    per_src = {}
    for k, v in real.items():
        for x in v["항목"]:
            row = (x, v["t_0"])
            allc["전체"].append(row)
            (allc["창 준(뉴스·블로그)"] if x["원천"] in ("뉴스", "블로그")
             else allc["창 없음(디시)"]).append(row)
            per_src.setdefault(x["원천"], []).append(row)

    def cls(rows):
        pre = post = bad = 0
        for x, t0 in rows:
            if not x.get("시각"):
                bad += 1
            elif x["시각"] < t0:
                pre += 1
            else:
                post += 1
        n = pre + post
        return {"사전": pre, "사후": post, "날짜불명": bad, "판정가능": n,
                "후견지명": round(pre / n, 4) if n else None}

    g1 = {k: cls(v) for k, v in allc.items()}
    g1_src = {k: cls(v) for k, v in per_src.items()}

    # 뉴스 부분집합은 감사된 도구로 교차 확인(social.hindsight_ratio)
    cross = {"이전": 0, "이후": 0, "날짜불명": 0}
    for k, v in real.items():
        ni = [{"게시": x.get("게시")} for x in v["항목"] if x["원천"] == "뉴스"]
        if ni:
            h = social.hindsight_ratio(ni, v["t_0"])
            for kk in cross:
                cross[kk] += h[kk]
    cross["후견지명"] = (round(cross["이전"] / (cross["이전"] + cross["이후"]), 4)
                    if (cross["이전"] + cross["이후"]) else None)

    # 질의어 출처(층별 한글 가능률)
    qsrc = {}
    for lab in ("상", "중", "하"):
        c = Counter(v["질의출처"] for k, v in real.items() if v["층"] == lab)
        n = sum(c.values())
        qsrc[lab] = {"분포": dict(c),
                     "한글 가능률": round(sum(x for s, x in c.items() if "한글" in s) / n, 4) if n else None}

    # ── G3
    posts, seen_g = [], Counter()
    for k, v in sorted(real.items()):
        got = 0
        for x in v["항목"]:
            if x["원천"] == "디시" and got < 2:
                posts.append({"record_id": f"{x['갤']}_{x['글번호']}", "갤": x["갤"],
                              "글번호": x["글번호"], "m": bool(x.get("m"))})
                got += 1
        if len(posts) >= 80:
            break
    crep = fanout(posts, key=lambda x: x["record_id"], cache=CACHE_CMT, work=comments,
                  workers=4, sleep=1.5, report_every=20) if posts else {}
    trees = []
    for p in posts:
        f = ROOT / CACHE_CMT / f"{p['record_id']}.json"
        if f.exists():
            trees.append(json.loads(f.read_text(encoding="utf-8")))
    tok = [t for t in trees if t.get("ok") and t.get("댓글")]
    g3 = {"시도한 글": len(posts), "응답 ok": sum(1 for t in trees if t.get("ok")),
          "댓글이 있는 트리": len(tok),
          "총 댓글": sum(t["댓글"] for t in tok),
          "답글(depth>0)": sum(t["답글(depth>0)"] for t in tok),
          "답글의 부모가 같은 트리 안": sum(t["답글의 부모가 트리 안에 있나"] for t in tok),
          "부모 참조 필드": sorted({f for t in tok for f in t.get("필드", [])}),
          "예시": next((t["표본"] for t in tok if t["답글(depth>0)"]),
                     (tok[0]["표본"] if tok else None))}

    # ── 배선 ㄹ  바이트 분포
    bys = {}
    for src in sorted({s for s, _ in REQ["bytes"]}):
        xs = sorted(b for s, b in REQ["bytes"] if s == src)
        bys[src] = {"n": len(xs), "최소": xs[0], "중앙값": xs[len(xs) // 2], "최대": xs[-1],
                    "5KB 미만": sum(1 for x in xs if x < 5000)}
    shells = sum(v["5KB 미만"] for v in bys.values())
    wire["ㄹ 바이트 분포"] = bys
    wire["ㄹ 껍데기(<5KB) 비율"] = round(shells / max(1, len(REQ["bytes"])), 4)
    wire["ㅁ t_0 출처"] = dict(Counter(v.get("t_0 출처", "?") for v in items
                                    if not v["record_id"].startswith("FAKE")))
    wire["실패 요청"] = dict(REQ["fail"])
    wire["원천별 요청"] = dict(REQ["by_src"])
    wire["캐시 회계(수확)"] = summarize(CACHE)
    wire["캐시 회계(댓글)"] = summarize(CACHE_CMT)

    mr, mf = med(yields_real), med(yields_fake)
    gates = {
        "G1 후견지명 > 40%": {"값": g1["전체"]["후견지명"],
                          "분모(판정가능)": g1["전체"]["판정가능"],
                          "날짜불명(병기)": g1["전체"]["날짜불명"],
                          "통과": bool(g1["전체"]["후견지명"] is not None
                                     and g1["전체"]["후견지명"] > 0.40)},
        "G2 작품당 수확 중앙값 > 5": {"값": mr, "분모": len(yields_real), "층별": by_layer,
                              "통과": bool(mr is not None and mr > 5)},
        "G3 댓글 부모 참조": {"값": g3["답글의 부모가 같은 트리 안"],
                       "분모(파싱된 트리)": g3["댓글이 있는 트리"],
                       "통과": bool(g3["답글의 부모가 같은 트리 안"] > 0)},
    }
    ratio = (round(mf / mr, 4) if (mr and mf is not None and mr > 0) else None)
    neg = {"음성 중앙값": mf, "실물 중앙값": mr, "비": ratio,
           "음성 평균": round(sum(yields_fake) / len(yields_fake), 2) if yields_fake else None,
           "음성 0건": sum(1 for x in yields_fake if x == 0),
           "음성 원천별": dict(Counter(x["원천"] for v in fake.values() for x in v["항목"])),
           "실물 원천별": dict(Counter(x["원천"] for v in real.values() for x in v["항목"])),
           "🔴 G2 무효인가(비 > 0.25)": bool(ratio is not None and ratio > 0.25)}

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "배선": wire, "게이트": gates, "음성 통제": neg,
           "G1 갈래": g1, "G1 원천별": g1_src, "G1 뉴스 교차확인(social.hindsight_ratio)": cross,
           "질의어 출처(층별)": qsrc,
           "수확 분포": {"실물": {"중앙값": mr, "평균": round(sum(yields_real) / len(yields_real), 2),
                            "0건": sum(1 for x in yields_real if x == 0),
                            "최대": max(yields_real), "합": sum(yields_real)},
                     "층별": by_layer},
           "G3 상세": g3, "음성 비존재 확인": exists,
           "fanout 보고": rep, "댓글 fanout 보고": crep,
           "실패한 작업": {k: v.get("사유") for k, v in res.items() if not v.get("ok")},
           "단계 실패": dict(Counter(s for v in ok.values() for s in v.get("실패단계", {}))),
           "🔴 단계별 회계(조항 59 --- '확인된 0' 과 '판정 불가' 를 가른다)": {
               st: dict(Counter(("항목" if isinstance(v.get("단계별", {}).get(st), int)
                                 else str(v.get("단계별", {}).get(st)))
                                for v in ok.values()))
               for st in ("뉴스사전", "뉴스사후", "블로그사전", "블로그사후", "디시최신", "디시정확")},
           "총 요청": REQ["n"], "초": round(time.time() - t_start, 1)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("게이트", "음성 통제", "G1 갈래", "총 요청", "초")},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
