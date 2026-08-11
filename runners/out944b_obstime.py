# -*- coding: utf-8 -*-
"""노트 944(**탐색 레인**) — 관측 시각을 **파일로 떨군다**. 943 의 0.9940 을 1.0000 으로.

🔴 **탐색 레인이다. 판정하지 않는다.** 넷만 적는다:
무엇을 했나 · 무엇이 나왔나 · **분모** · 못 한 것 (`docs/루프.md` 레인 표).

## 943 이 남긴 구멍 셋 (티처 #83)

  **M1** 도서 153 은 「못 붙였다」가 아니다 — `book_records.item_id` 로
        `cache_aladin_book/item_{item_id}.html` 에 붙는다. 943 은 그 디렉터리를
        **안 열고** 「405개 목록 페이지」라 적었다(실제 `item_` 400 + `best_` 5).
  **B**  943 은 시각을 **파일로 안 떨궜다.** mtime 은 `git checkout` 한 번에 사라진다.
  **C**  943 은 캐시 36 디렉터리 중 **표본 5개**만 본문을 열었다(31 을 안 열었다).

## 이 러너가 하는 것 다섯

  ① 아홉 저장소 **25,372** 레코드에 관측 시각을 붙여 **`data/state/obs_time944.json`** 으로 떨군다
     (레코드 id → 시각 · **출처 캐시 경로** · **조인 방식** · **git 최초 커밋 시각**).
  ② 🔴 **만화의 두 점**(t₁,o₁,t₂,o₂)을 `data/state/obs_time944_manga.json` 으로 떨군다.
     저장소의 `y_popularity` 가 첫 점과 맞는가 끝 점과 맞는가를 **레코드마다** 적는다.
  ③ 🔴 **mtime 이 아닌 근거**를 센다 — (가) **git 최초 커밋 시각**(`git log --diff-filter=A`,
     `checkout` 에 안 지워진다) (나) **파일 이름 안의 날짜** (다) **본문 안의 날짜**.
  ④ 🔴 캐시 **36 디렉터리 전수**로 본문을 연다(943 은 5개만 열었다). 이진 파일도 연다.
  ⑤ 943 의 수(되풀이 5,001 · 값이 달라진 2,388 · 간격 중앙 75.33h)를 다시 센다.

🔴 941·942·943 산출물은 동결이다 — 이 러너는 `runners/out944b_obstime.json` 과
   `data/state/obs_time944*.json` 만 쓴다.
🔴 스탬프 넷: 시작 시각 · **끝 시각** · **입력 sha256** · **코드 sha256**.
   `git rev-parse HEAD` 는 루프 v3.2 가 폐기했다 — 안 쓴다.

쓰는 법::  python3 runners/out944b_obstime.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out944b_obstime.json"
ART = ROOT / "data/state/obs_time944.json"
ART_MG = ROOT / "data/state/obs_time944_manga.json"

STORES = {
    "data/state/manga_records.json": "만화",
    "data/state/webtoon_records.json": "웹툰",
    "data/state/anime_records.json": "애니",
    "data/state/wanime_records.json": "세계애니",
    "data/state/funding_records.json": "펀딩",
    "data/state/mobile_records.json": "모바일",
    "data/state/app_records.json": "앱",
    "data/state/game_records.json": "게임",
    "data/state/book_records.json": "도서",
}

#: ④ 레코드 → 캐시 파일 이름 규칙. 🔴 **943 대비 바뀐 것은 도서 한 줄뿐이다.**
DIRECT_JOIN = {
    "게임": [("data/state/cache_steam", "app_{appid}.json"),
            ("data/state/cache_steamspy", "{record_id}.json")],
    "모바일": [("data/state/cache_mobile", "app_{app_id}.json")],
    "앱": [("data/state/cache_mobile", "app_{app_id}.json")],
    "애니": [("data/state/cache_anime", "ep_{item_id}.json")],
    "웹툰": [("data/state/cache_webtoon", "asc_{title_id}.json")],
    "도서": [("data/state/cache_bookpage", "{record_id}.html"),
            # 🔴 이 한 줄이 티처 #83 M1 이다 — 도서 243/396 → 396/396
            ("data/state/cache_aladin_book", "item_{item_id}.html")],
    "펀딩": [("data/state/cache_fundpage", "{record_id}.html")],
}

#: ④′ 목록 페이지 캐시 — 파일 하나가 레코드 여럿을 담는다. **943 과 같은 목록**(대조용).
PAGE_JOIN = {
    "만화": (["data/state/cache_manga", "data/state/cache_manga_below",
             "data/state/cache_manga_mid", "data/state/cache_manga_deep",
             "data/state/cache_manga_recent", "data/state/cache_manga_below_pre"],
            "anilist", "media_id"),
    "세계애니": (["data/state/cache_wanime", "data/state/cache_wanime_deep"],
              "anilist", "media_id"),
    "펀딩": (["data/state/cache_tumblbug"], "tumblbug", "uuid"),
}

#: ④″ 🔴 **943 이 안 본 곳** — 같은 anilist id 를 담는 다른 캐시. 여기서 나온 점은
#:    **덤**이고 헤드라인 분모를 바꾸지 않는다(따로 신고한다).
EXTRA_ANILIST = ["data/state/cache_promo", "data/state/cache_score",
                 "data/state/cache_cover", "data/state/cache_desc",
                 "data/state/cache_manga_kr", "data/state/cache_manga_links",
                 "data/state/cache_wanime_links", "data/state/cache_mal",
                 "data/state/cache_match"]

PAGE_O = {"anilist": ("popularity", "favourites", "meanScore"),
          "tumblbug": ("amount", "percentage")}

#: ③ 본문 안의 날짜. `20\d\d` 로 시작하는 것만 — 두 자리 연도는 안 센다.
DATE_RE = re.compile(r"20[0-3]\d[-/.년]\s?(?:0[1-9]|1[0-2])[-/.월]\s?(?:0[1-9]|[12]\d|3[01])")
DATE_NORM = re.compile(r"20[0-3]\d|[0-9]{1,2}")
FNAME_DATE_RE = re.compile(r"20[0-3]\d[-_]?(?:0[1-9]|1[0-2])[-_]?(?:0[1-9]|[12]\d|3[01])")
EXIF_DATE_RE = re.compile(rb"20[0-3]\d:(?:0[1-9]|1[0-2]):(?:0[1-9]|[12]\d|3[01])")

#: ③ 「받은 시각」을 스스로 말하는 이름들(엄격). 943 의 표본 검사를 **전수**로 넓힌다.
FETCH_NEEDLES = ("fetched_at", "fetched", "_snapshot", "snapshot_at", "as_of", "asof",
                 "retrieved", "crawled", "scraped", "collected_at", "observed_at",
                 "generated_at", "harvest", '"date":', "Date:", "last-modified",
                 "lastModified", "updatedAt", "updated_at", "timestamp")

MAXREAD = 8 << 20     # 파일당 최대 8MB 만 읽는다(전부 그 아래다 — 실측을 신고한다)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def span(times: list) -> dict:
    if not times:
        return {"n": 0}
    return {"n": len(times), "최소": iso(min(times)), "최대": iso(max(times)),
            "중앙": iso(statistics.median(times)),
            "펼침(시간)": round((max(times) - min(times)) / 3600, 2)}


def git_add_times() -> tuple:
    """🔴 mtime 이 아닌 근거 (가) — 캐시 파일이 **처음 커밋된 시각**.

    `git checkout` 도 `clone` 도 이것을 안 지운다. 관측 시각의 **상한**이다
    (받은 뒤에 커밋하므로). `--all` 로 돌려서 다른 갈래의 스냅샷도 센다.
    """
    out: dict = {}
    for scope in ("HEAD", "--all"):
        cmd = ["git", "log", "--format=\x01%aI", "--name-only", "--diff-filter=A"]
        if scope == "--all":
            cmd.insert(2, "--all")
        cmd += ["--", "data/state/cache_*"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        cur = None
        m: dict = {}
        for line in r.stdout.splitlines():
            if line.startswith("\x01"):
                cur = line[1:]
            elif line.strip():
                # 같은 파일이 여러 갈래에서 추가되면 **가장 이른** 것을 쓴다
                if line not in m or cur < m[line]:
                    m[line] = cur
        out[scope] = m
    return out["HEAD"], out["--all"]


def page_obs(kind: str, blob) -> list:
    keys = PAGE_O[kind]
    res = []
    try:
        rows = (blob["data"]["Page"]["media"] if kind == "anilist"
                else blob["body"]["result"]["contents"])
    except (KeyError, TypeError):
        return res
    if not isinstance(rows, list):
        return res
    for m in rows:
        if isinstance(m, dict) and "id" in m:
            res.append((m["id"], {k: m.get(k) for k in keys if m.get(k) is not None}))
    return res


def anilist_any(blob) -> list:
    """④″ `{"data": {...: {"media": [...]}}}` 어떤 모양이든 media 배열을 긁는다."""
    res = []

    def walk(o):
        if isinstance(o, dict):
            med = o.get("media")
            if isinstance(med, list):
                for m in med:
                    if isinstance(m, dict) and "id" in m:
                        res.append((m["id"], {k: m.get(k) for k in PAGE_O["anilist"]
                                              if m.get(k) is not None}))
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    walk(v)

    walk(blob)
    return res


def body_scan(f: Path) -> dict:
    """③ 본문 안에 **시각의 근거**가 있나. 이진 파일도 연다(EXIF)."""
    try:
        raw = f.open("rb").read(MAXREAD)
    except OSError:
        return {"열림": False}
    try:
        txt = raw.decode("utf-8", errors="ignore")
    except Exception:                                    # noqa: BLE001
        txt = ""
    needles = [nd for nd in FETCH_NEEDLES if nd in txt]
    dates = DATE_RE.findall(txt)
    exif = EXIF_DATE_RE.search(raw)
    norm = set()
    for d in dates:
        n = DATE_NORM.findall(d)
        if len(n) >= 3:
            norm.add("%s-%02d-%02d" % (n[0], int(n[1]), int(n[2])))
    return {"열림": True, "바이트": len(raw), "잘림": len(raw) >= MAXREAD,
            "needle": needles, "날짜수": len(norm),
            "날짜최대": max(norm) if norm else None,
            "exif": exif.group().decode() if exif else None}


def main() -> dict:                                       # noqa: PLR0912, PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    git_head, git_all = git_add_times()

    # ── ④′ 목록 페이지 → id → [(시각, 값, 출처)] ───────────────────────────
    page_seq: dict = defaultdict(dict)     # dom → id → [(ts, ov, src)]
    page_stat: dict = {}
    for dom, (dirs, kind, _idk) in PAGE_JOIN.items():
        nfile = 0
        seq = page_seq[dom]
        for d in dirs:
            dp = ROOT / d
            if not dp.exists():
                continue
            for f in sorted(dp.glob("*.json")):
                nfile += 1
                try:
                    blob = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                    continue
                mt = round(f.stat().st_mtime)
                rel = str(f.relative_to(ROOT))
                for i, ov in page_obs(kind, blob):
                    seq.setdefault(i, []).append((mt, ov, rel))
        page_stat[dom] = {"연 페이지 파일": nfile, "id 개수": len(seq)}

    # ── ④″ 943 이 안 본 anilist 캐시 (덤 · 헤드라인 분모 밖) ────────────────
    extra_seq: dict = defaultdict(list)    # id → [(ts, ov, src)]
    extra_stat: dict = {}
    for d in EXTRA_ANILIST:
        dp = ROOT / d
        if not dp.exists():
            extra_stat[d] = "없음"
            continue
        nf = nid = 0
        for f in sorted(dp.glob("*.json")):
            nf += 1
            try:
                blob = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
            mt = round(f.stat().st_mtime)
            rel = str(f.relative_to(ROOT))
            for i, ov in anilist_any(blob):
                extra_seq[i].append((mt, ov, rel))
                nid += 1
        extra_stat[d] = {"파일": nf, "긁은 (id,점)": nid}

    # ── ① 레코드마다 시각을 붙인다 ────────────────────────────────────────
    art: dict = {}
    per: dict = {}
    tot = tot_any = tot_direct = tot_page = 0
    mtime_cache: dict = {}

    def mt_of(f: Path) -> int:
        s = str(f)
        if s not in mtime_cache:
            mtime_cache[s] = round(f.stat().st_mtime)
        return mtime_cache[s]

    for path, dom in STORES.items():
        d = json.loads((ROOT / path).read_text())
        recs = [v for v in d.values() if isinstance(v, dict)]
        n = len(recs)
        tot += n
        n_direct = n_page = n_any = 0
        dirstat: Counter = Counter()
        times_dom = []
        for v in recs:
            rid = v.get("record_id")
            pts = []       # (ts, src, 방식)
            for cdir, pat in DIRECT_JOIN.get(dom, []):
                try:
                    nm = pat.format(**v)
                except (KeyError, IndexError):
                    continue
                f = ROOT / cdir / nm
                if f.exists():
                    pts.append((mt_of(f), cdir + "/" + nm, "직접"))
            has_direct = bool(pts)
            if dom in PAGE_JOIN:
                key = v.get(PAGE_JOIN[dom][2])
                for ts, _ov, src in page_seq[dom].get(key, []):
                    pts.append((ts, src, "목록"))
            if not pts:
                continue
            pts.sort()
            n_any += 1
            n_direct += has_direct
            n_page += bool(dom in PAGE_JOIN and any(m == "목록" for _, _, m in pts))
            for _t, s, _m in pts:
                dirstat[s.split("/")[2]] += 1
            first = pts[0]
            times_dom.append(first[0])
            gh = git_head.get(first[1])
            art[rid] = {
                "도": dom,
                "t": iso(first[0]),
                "ts": first[0],
                "출처": first[1],
                "방식": first[2],
                "근거": "캐시파일 mtime",
                "git최초커밋": gh or git_all.get(first[1]),
                "git범위": ("HEAD" if gh else
                          ("--all" if git_all.get(first[1]) else "🔴 미추적")),
                "점수": len(pts),
                "끝t": iso(pts[-1][0]) if len(pts) > 1 else None,
            }
        tot_any += n_any
        tot_direct += n_direct
        tot_page += n_page
        per[dom] = {
            "파일": path, "레코드(분모)": n,
            "🔴 시각이 붙은 레코드": n_any,
            "🔴 덮음": round(n_any / n, 4) if n else None,
            "직접 조인으로": n_direct, "목록 조인으로": n_page,
            "출처 디렉터리별 점 수": dict(dirstat),
            "첫 관측 시각 분포": span(times_dom),
            "두 점 이상": sum(1 for r in art.values()
                          if r["도"] == dom and r["점수"] > 1),
        }

    # ── ② 🔴 만화의 두 점 ─────────────────────────────────────────────────
    mg = json.loads((ROOT / "data/state/manga_records.json").read_text())
    mg_recs = [v for v in mg.values() if isinstance(v, dict)]
    mg_pts: dict = {}
    rep = chg = 0
    gaps, dpop = [], []
    neg = 0
    match_first = match_last = 0
    same_dir = diff_dir = 0
    for v in mg_recs:
        rows = page_seq["만화"].get(v.get("media_id"), [])
        if not rows:
            continue
        rows = sorted(rows, key=lambda x: x[0])
        ts_set = sorted({t for t, _, _ in rows})
        if len(ts_set) < 2:
            continue
        rep += 1
        a = rows[0]
        b = rows[-1]
        o1 = a[1].get("popularity")
        o2 = b[1].get("popularity")
        if o1 is None or o2 is None or o1 == o2:
            continue
        chg += 1
        gap = (b[0] - a[0]) / 3600
        gaps.append(gap)
        dpop.append(o2 - o1)
        neg += (o2 - o1) < 0
        y = v.get("y_popularity")
        mf = (y == o1)
        ml = (y == o2)
        match_first += mf
        match_last += ml
        d1 = a[2].split("/")[2]
        d2 = b[2].split("/")[2]
        same_dir += (d1 == d2)
        diff_dir += (d1 != d2)
        mg_pts[v["record_id"]] = {
            "media_id": v.get("media_id"),
            "t1": iso(a[0]), "ts1": a[0], "o1": a[1], "출처1": a[2],
            "t2": iso(b[0]), "ts2": b[0], "o2": b[1], "출처2": b[2],
            "간격(시간)": round(gap, 2),
            "Δpopularity": o2 - o1,
            "저장소 y_popularity": y,
            "🔴 y 가 첫 점과 같나": mf,
            "🔴 y 가 끝 점과 같나": ml,
            "점 전부": [{"t": iso(t), "값": ov, "출처": s} for t, ov, s in rows],
            "git최초커밋1": git_head.get(a[2]) or git_all.get(a[2]),
            "git최초커밋2": git_head.get(b[2]) or git_all.get(b[2]),
        }

    # ── ③·④ 캐시 36 디렉터리 **전수** 본문 열기 ────────────────────────────
    cache_dirs = sorted(p for p in (ROOT / "data/state").glob("cache_*") if p.is_dir())
    census: dict = {}
    for dp in cache_dirs:
        files = sorted(p for p in dp.iterdir() if p.is_file())
        nf = len(files)
        opened = 0
        needle_c: Counter = Counter()
        with_date = 0
        fname_date = 0
        exif_n = 0
        eq_mtime_day = 0
        maxdates: Counter = Counter()
        tracked_h = tracked_a = 0
        for f in files:
            rel = str(f.relative_to(ROOT))
            if rel in git_head:
                tracked_h += 1
            if rel in git_all:
                tracked_a += 1
            if FNAME_DATE_RE.search(f.name):
                fname_date += 1
            b = body_scan(f)
            if not b["열림"]:
                continue
            opened += 1
            for nd in b["needle"]:
                needle_c[nd] += 1
            if b["exif"]:
                exif_n += 1
            if b["날짜수"]:
                with_date += 1
                maxdates[b["날짜최대"]] += 1
                if b["날짜최대"] == iso(mt_of(f))[:10]:
                    eq_mtime_day += 1
        census[dp.name] = {
            "파일": nf, "🔴 실제로 연 파일": opened,
            "git 추적(HEAD)": tracked_h, "git 추적(--all)": tracked_a,
            "이름에 날짜": fname_date,
            "본문에 날짜(20xx-xx-xx)": with_date,
            "🔴 본문 최대날짜 == mtime 날짜": eq_mtime_day,
            "EXIF 날짜": exif_n,
            "받은시각 이름(needle) 빈도": dict(needle_c.most_common(8)),
            "본문 최대날짜 상위 3": dict(maxdates.most_common(3)),
        }

    # ── ⑤ 943 의 수를 다시 센다 ───────────────────────────────────────────
    recount = {
        "되풀이 id(만화 · 두 시각 이상)": sum(
            1 for i, rows in page_seq["만화"].items() if len({t for t, _, _ in rows}) > 1),
        "그중 저장소 레코드": rep,
        "🔴 popularity 가 달라진 레코드": chg,
        "간격(시간) 중앙": round(statistics.median(gaps), 2) if gaps else None,
        "간격(시간) 최대": round(max(gaps), 2) if gaps else None,
        "🔴 간격 1시간 미만": sum(1 for g in gaps if g < 1),
        "Δpopularity 중앙": statistics.median(dpop) if dpop else None,
        "Δpopularity 평균": round(statistics.mean(dpop), 2) if dpop else None,
        "🔴 Δ 음수": neg,
        "🔴 y_popularity == 첫 점": match_first,
        "🔴 y_popularity == 끝 점": match_last,
        "서로 다른 디렉터리 쌍": diff_dir, "같은 디렉터리 쌍": same_dir,
    }

    # ④″ 덤 — 943 이 안 본 캐시가 만화 레코드에 점을 더 주나
    mg_ids = {v.get("media_id") for v in mg_recs}
    extra_hit = sum(1 for i in extra_seq if i in mg_ids)
    extra_withpop = sum(1 for i, rows in extra_seq.items()
                        if i in mg_ids and any(r[1].get("popularity") is not None
                                               for r in rows))

    # ── 산출물 떨구기 ─────────────────────────────────────────────────────
    meta = {
        "노트": 944, "레인": "🔴 탐색 — 판정하지 않는다",
        "무엇": "D2 아홉 저장소 레코드의 관측 시각(캐시 파일 mtime)을 파일로 고정한다",
        "🔴 왜 파일인가": "mtime 은 git 이 보존하지 않는다 — `git checkout`·`clone` 한 번에 "
                     "사라진다. 이 파일이 그 근거의 유일한 사본이다",
        "만든 시각": t_start,
        "만든 러너": "runners/out944b_obstime.py",
        "분모": tot, "붙은 레코드": tot_any,
        "덮음": round(tot_any / tot, 4) if tot else None,
        "🔴 근거의 종류": {
            "t·ts": "출처 캐시 파일의 mtime(초). 🔴 이것이 주 근거다",
            "git최초커밋": "그 캐시 파일이 git 에 **처음 커밋된 시각**. mtime 과 무관하게 "
                       "살아남는다. 관측의 **상한**이다(받고 나서 커밋하므로)",
            "출처·방식": "어느 캐시 파일에서, 직접 조인인가 목록 조인인가",
        },
    }
    ART.write_text(json.dumps({"_meta": meta, "레코드": art},
                              ensure_ascii=False, indent=0))
    ART_MG.write_text(json.dumps(
        {"_meta": {**meta, "무엇": "만화 두 점 (t₁,o₁,t₂,o₂) — popularity 가 달라진 레코드만",
                   "분모": len(mg_recs), "실린 레코드": len(mg_pts)},
         "요약": recount, "레코드": mg_pts}, ensure_ascii=False, indent=0))

    res = {
        "노트": 944, "레인": "🔴 탐색 — **판정하지 않는다**",
        "물음": "관측 시각을 파일로 떨굴 수 있나 · 덮음이 1.0000 이 되나 · mtime 아닌 근거가 있나",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(저장소 아홉)": {k: sha(ROOT / k) for k in STORES},
            "코드 sha256": {"runners/out944b_obstime.py":
                          sha(ROOT / "runners/out944b_obstime.py")},
        },
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out944b_obstime.py",
            "범위(저장소)": list(STORES),
            "범위(캐시)": [p.name for p in cache_dirs],
            "트리": "작업 트리만 읽는다(인덱스와 안 섞는다). git 커밋 시각만 이력에서 읽는다",
        },
        "🔴 ① 합계 — 943 과 나란히": {
            "분모 D2": tot,
            "943 이 적은 붙은 레코드": 25219,
            "944 가 센 붙은 레코드": tot_any,
            "943 덮음": 0.9940,
            "🔴 944 덮음": round(tot_any / tot, 4) if tot else None,
            "직접 조인": tot_direct, "목록 조인": tot_page,
            "🔴 바뀐 것": "도서에 cache_aladin_book/item_{item_id}.html 한 줄",
        },
        "저장소별": per,
        "🔴 ② 만화 두 점": {
            "떨군 파일": str(ART_MG.relative_to(ROOT)),
            "실린 레코드": len(mg_pts),
            **recount,
        },
        "🔴 ④″ 943 이 안 본 anilist 캐시(덤 · 헤드라인 밖)": {
            "디렉터리": extra_stat,
            "긁힌 서로 다른 id": len(extra_seq),
            "그중 만화 레코드 id": extra_hit,
            "그중 popularity 를 가진 id": extra_withpop,
        },
        "🔴 ③·④ 캐시 36 디렉터리 전수 본문 census(943 은 5개만 열었다)": census,
        "떨군 산출물": {
            str(ART.relative_to(ROOT)): {"레코드": len(art),
                                         "바이트": ART.stat().st_size},
            str(ART_MG.relative_to(ROOT)): {"레코드": len(mg_pts),
                                            "바이트": ART_MG.stat().st_size},
        },
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("🔴 ③·④ 캐시 36 디렉터리 전수 본문 census(943 은 5개만 열었다)",)},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
