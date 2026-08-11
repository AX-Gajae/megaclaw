# -*- coding: utf-8 -*-
"""노트 943(**탐색 레인**) — D2 25,372 의 `o` 에 **관측 시점**이 붙는가.

🔴 **탐색 레인이다. 판정하지 않는다.** 넷만 적는다:
무엇을 했나 · 무엇이 나왔나 · **분모** · 못 한 것 (`docs/루프.md` 레인 표).
사전등록·문턱·BCa·오라클 천장을 이 파일에 요구하지 않는다(규칙 2).

## 물음 하나

`data/state/*_records.json` 아홉 저장소 **25,372 레코드**는 판 12도메인이 실제로 쓰는
파일이다(`lab/calaxes.py:40-47`). `a` 는 이미 **100% 날짜**이고 `o` 도 100% 있는데
🔴 **`o` 가 「언제 관측된 값인지」가 없다** — 그래서 지금은 **스칼라 라벨 하나**다.
**그 시각을 찾을 수 있나?**

## 조항 60 — 레코드가 이미 가진 열쇠를 다 써 봤는지 먼저 센다

이 러너가 **실제로 열어 본 곳** (안 본 곳은 산출물에 「안 봤다」로 적는다):

  ① 레코드 **키 이름 전수** — 시각처럼 생긴 이름 18개를 바늘로 훑는다
  ② 저장소 파일의 **mtime**
  ③ 저장소 파일의 **git 히스토리**(커밋 수 · 첫/끝 커밋 시각)
  ④ 🔴 `data/state/cache_*` **HTTP 캐시 36개 디렉터리** — 레코드 ↔ 캐시 파일 조인
     (캐시 파일 mtime = 그 레코드의 **원문을 실제로 받은 시각**)
  ⑤ 캐시 파일의 **git 히스토리**(추적되는가 · 커밋 시각)
  ⑥ 캐시 **본문 안**에 시각 필드가 있는가
  ⑦ 레코드 안의 **원천 URL**에 날짜가 박혀 있는가

쓰는 법::  python3 runners/out943b_d2time.py
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
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out943b_d2time.json"

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

#: ① 시각처럼 생긴 키 이름 바늘. 🔴 **찾은 것이 0 이면 「이 18개를 훑었다」를 신고한다.**
TIME_NEEDLES = ("_snapshot_at", "snapshot_at", "snapshot", "fetched_at", "fetched",
                "updated_at", "as_of", "asof", "observed_at", "observed", "collected_at",
                "crawled_at", "retrieved", "timestamp", "_ts", "captured_at",
                "scraped_at", "harvest")

#: ④ 레코드 → 캐시 파일 이름 규칙. 🔴 **이름 규칙을 먼저 보고 적은 것이지 추측이 아니다**
#:   (`ls data/state/cache_*` 로 실제 파일명을 확인했다).
DIRECT_JOIN = {
    "게임": [("data/state/cache_steam", "app_{appid}.json"),
            ("data/state/cache_steamspy", "{record_id}.json")],
    "모바일": [("data/state/cache_mobile", "app_{app_id}.json")],
    "앱": [("data/state/cache_mobile", "app_{app_id}.json")],
    "애니": [("data/state/cache_anime", "ep_{item_id}.json")],
    "웹툰": [("data/state/cache_webtoon", "asc_{title_id}.json")],
    "도서": [("data/state/cache_bookpage", "{record_id}.html")],
    "펀딩": [("data/state/cache_fundpage", "{record_id}.html")],
}

#: ④′ 목록 페이지 캐시 — 파일 하나가 레코드 여럿을 담는다. 본문을 열어 id 를 꺼낸다.
PAGE_JOIN = {
    "만화": (["data/state/cache_manga", "data/state/cache_manga_below",
             "data/state/cache_manga_mid", "data/state/cache_manga_deep",
             "data/state/cache_manga_recent", "data/state/cache_manga_below_pre"],
            "anilist", "media_id"),
    "세계애니": (["data/state/cache_wanime", "data/state/cache_wanime_deep"],
              "anilist", "media_id"),
    "펀딩": (["data/state/cache_tumblbug"], "tumblbug", "uuid"),
}

DATE_RE = re.compile(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def gitlog(path: str) -> dict:
    r = subprocess.run(["git", "log", "--follow", "--format=%aI", "--", path],
                       capture_output=True, text=True, timeout=300)
    lines = [x for x in r.stdout.splitlines() if x]
    return {"커밋 수": len(lines),
            "첫 커밋": lines[-1] if lines else None,
            "끝 커밋": lines[0] if lines else None}


def span(times: list) -> dict:
    if not times:
        return {"n": 0}
    return {"n": len(times), "최소": iso(min(times)), "최대": iso(max(times)),
            "중앙": iso(statistics.median(times)),
            "펼침(시간)": round((max(times) - min(times)) / 3600, 2)}


def page_ids(kind: str, blob) -> list:
    """목록 페이지 캐시 본문에서 레코드 id 를 꺼낸다."""
    try:
        if kind == "anilist":
            return [m["id"] for m in blob["data"]["Page"]["media"]]
        if kind == "tumblbug":
            return [c["id"] for c in blob["body"]["result"]["contents"]]
    except (KeyError, TypeError):
        return []
    return []


#: 🔴 같은 레코드가 **여러 번** 잡혔을 때 그 결과값을 꺼내는 경로.
#:   (이게 있으면 「스칼라 하나」가 아니라 **o(t)** 다.)
PAGE_O = {"anilist": ("popularity", "favourites", "meanScore"),
          "tumblbug": ("amount", "percentage")}


def page_obs(kind: str, blob) -> list:
    """(id, 결과값 dict) 목록. `page_ids` 와 달리 **값까지** 꺼낸다."""
    keys = PAGE_O[kind]
    out = []
    try:
        rows = (blob["data"]["Page"]["media"] if kind == "anilist"
                else blob["body"]["result"]["contents"])
    except (KeyError, TypeError):
        return out
    for m in rows:
        if isinstance(m, dict) and "id" in m:
            out.append((m["id"], {k: m.get(k) for k in keys}))
    return out


def main() -> dict:
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    per: dict = {}
    tot = 0
    tot_direct = tot_page = tot_any = 0
    key_hits: Counter = Counter()
    url_date_hits: Counter = Counter()

    # ⑤ 캐시가 git 에 추적되는가 (한 번만 센다)
    tracked = subprocess.run(["git", "ls-files", "data/state/"],
                             capture_output=True, text=True, timeout=600).stdout.splitlines()
    cache_tracked = sum(1 for x in tracked if x.startswith("data/state/cache_"))
    cache_dirs = sorted(p.name for p in (ROOT / "data/state").glob("cache_*") if p.is_dir())

    # ④′ 목록 페이지 → id → 그 페이지의 mtime (도메인마다 한 번만 만든다)
    page_time: dict = {}
    page_stat: dict = {}
    repeat: dict = {}
    for dom, (dirs, kind, _idkey) in PAGE_JOIN.items():
        m: dict = {}
        seq: dict = {}     # id → [(시각, 결과값 dict)]
        nfile = 0
        for d in dirs:
            dp = ROOT / d
            if not dp.exists():
                continue
            for f in sorted(dp.glob("*.json")):
                nfile += 1
                try:
                    blob = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                mt = f.stat().st_mtime
                for i, ov in page_obs(kind, blob):
                    # 같은 id 가 여러 페이지에 있으면 **가장 이른** 관측을 쓴다
                    if i not in m or mt < m[i]:
                        m[i] = mt
                    seq.setdefault(i, []).append((round(mt), ov))
        page_time[dom] = m
        page_stat[dom] = {"연 페이지 파일": nfile, "id 개수": len(m)}

        # 🔴 **되풀이 관측** — 같은 id 를 서로 다른 시각에 두 번 이상 잡았나,
        #    그리고 그때 **결과값이 달라졌나**. 달라졌으면 그건 o(t) 다.
        multi, gaps = 0, []
        cmpable: Counter = Counter()
        moved: Counter = Counter()
        for i, rows in seq.items():
            ts = sorted({t for t, _ in rows})
            if len(ts) < 2:
                continue
            multi += 1
            gaps.append(ts[-1] - ts[0])
            rows = sorted(rows, key=lambda x: x[0])   # 🔴 dict 비교로 터지지 않게 시각으로만
            first, last = rows[0][1], rows[-1][1]
            for k in PAGE_O[kind]:
                if first.get(k) is not None and last.get(k) is not None:
                    cmpable[k] += 1
                    moved[k] += (first[k] != last[k])
        # 🔴 그 되풀이 id 중 **판이 실제로 쓰는 레코드**는 몇인가(분모를 바꾸지 않는다)
        _store = [k for k, v in STORES.items() if v == dom][0]
        _idk = PAGE_JOIN[dom][2]
        _recids = {v.get(_idk) for v in json.loads((ROOT / _store).read_text()).values()
                   if isinstance(v, dict)}
        _rep_ids = {i for i, rows in seq.items() if len({t for t, _ in rows}) > 1}
        repeat[dom] = {
            "🔴 서로 다른 시각에 2회 이상 잡힌 id": multi,
            "🔴 그중 이 저장소의 레코드인 것": len(_rep_ids & _recids),
            "저장소 레코드(분모)": len(_recids),
            "분모(캐시에서 본 id 전체)": len(seq),
            "간격(시간) 최대": round(max(gaps) / 3600, 2) if gaps else None,
            "간격(시간) 중앙": round(statistics.median(gaps) / 3600, 2) if gaps else None,
            "🔴 두 시각의 값을 견줄 수 있는 id(열별)": dict(cmpable),
            "🔴 그중 값이 **달라진** id(열별)": dict(moved),
            "🔴 값이 달라진 것 중 이 저장소의 레코드(첫 열 기준)": len(
                {i for i in _rep_ids & _recids
                 if (lambda rr: (rr[0][1].get(PAGE_O[kind][0]) is not None
                                 and rr[-1][1].get(PAGE_O[kind][0]) is not None
                                 and rr[0][1][PAGE_O[kind][0]]
                                 != rr[-1][1][PAGE_O[kind][0]]))(sorted(seq[i], key=lambda x: x[0]))}),
        }

    for path, dom in STORES.items():
        p = ROOT / path
        d = json.loads(p.read_text())
        recs = [v for v in d.values() if isinstance(v, dict)]
        n = len(recs)
        tot += n

        # ① 키 이름 전수 + 시각 바늘
        keys: Counter = Counter()
        for v in recs:
            keys.update(v.keys())
        hit = {k: keys[k] for k in keys
               if any(nd in k.lower() for nd in TIME_NEEDLES)}
        for k in hit:
            key_hits[k] += 1

        # ⑦ 원천 URL 안의 날짜
        urld = 0
        for v in recs:
            for kk, vv in v.items():
                if isinstance(vv, str) and vv.startswith("http") and DATE_RE.search(vv):
                    urld += 1
                    break
        if urld:
            url_date_hits[dom] = urld

        # ④ 직접 조인
        direct = {}
        got_direct: dict = {}
        for cdir, pat in DIRECT_JOIN.get(dom, []):
            times, miss = [], 0
            for v in recs:
                try:
                    nm = pat.format(**v)
                except KeyError:
                    miss = n
                    break
                f = ROOT / cdir / nm
                if f.exists():
                    t = f.stat().st_mtime
                    times.append(t)
                    rid = v.get("record_id")
                    if rid not in got_direct or t < got_direct[rid]:
                        got_direct[rid] = t
                else:
                    miss += 1
            direct[cdir] = {"조인된 레코드": len(times), "분모": n,
                            "덮음": round(len(times) / n, 4) if n else None,
                            "못 찾음": miss, "받은 시각": span(times)}

        # ④′ 페이지 조인
        pagej = None
        got_page: dict = {}
        if dom in PAGE_JOIN:
            idkey = PAGE_JOIN[dom][2]
            m = page_time[dom]
            times = []
            for v in recs:
                key = v.get(idkey)
                if key in m:
                    times.append(m[key])
                    got_page[v.get("record_id")] = m[key]
            pagej = {"쓴 캐시": PAGE_JOIN[dom][0], **page_stat[dom],
                     "조인된 레코드": len(times), "분모": n,
                     "덮음": round(len(times) / n, 4) if n else None,
                     "받은 시각": span(times)}

        anyt = set(got_direct) | set(got_page)
        anyt.discard(None)
        tot_direct += len(got_direct)
        tot_page += len(got_page)
        tot_any += len(anyt)

        per[dom] = {
            "파일": path, "레코드(분모)": n,
            "① 시각처럼 생긴 키": hit or "🔴 없음(바늘 18개 전부 0)",
            "② 파일 mtime": iso(p.stat().st_mtime),
            "③ git 히스토리": gitlog(path),
            "④ 캐시 직접 조인": direct or "🔴 이름 규칙이 없다 — 안 했다",
            "④′ 목록 페이지 조인": pagej or "해당 없음",
            "🔴 어느 경로로든 시각이 붙은 레코드": len(anyt),
            "🔴 그 덮음": round(len(anyt) / n, 4) if n else None,
        }

    # ⑥ 캐시 본문에 시각 필드가 있나 (표본으로 본다 — 전수 아님을 명시한다)
    body = {}
    for f in ("data/state/cache_steam/app_578080.json",
              "data/state/cache_anime/ep_10594.json",
              "data/state/cache_mobile/app_1000246864.json",
              "data/state/cache_manga/page_1.json",
              "data/state/cache_tumblbug/list_1.json"):
        fp = ROOT / f
        if not fp.exists():
            continue
        txt = fp.read_text()[:400000]
        body[f] = {k: (k in txt) for k in
                   ("fetched_at", "_snapshot", "as_of", "Date:", "timestamp", "retrieved")}

    res = {
        "노트": 943, "레인": "🔴 탐색 — **판정하지 않는다**",
        "물음": "D2 25,372 의 o 에 관측 시점이 붙는가",
        "🔴 스탬프": {
            "시작 시각": t_start,
            "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(저장소 아홉)": {k: sha(ROOT / k) for k in STORES},
            "코드 sha256": {"runners/out943b_d2time.py":
                          sha(ROOT / "runners/out943b_d2time.py")},
        },
        "🔴 조항 60 — 명령·범위": {
            "명령": "python3 runners/out943b_d2time.py",
            "범위": list(STORES),
            "캐시 디렉터리(전수)": cache_dirs,
            "캐시 디렉터리 수": len(cache_dirs),
        },
        "①에 쓴 바늘(전수)": list(TIME_NEEDLES),
        "🔴 ① 결과 — 어느 저장소에서든 걸린 시각 키": dict(key_hits) or
            "🔴 0 — 아홉 저장소 25,372 레코드 어디에도 관측 시각 열이 없다",
        "🔴 ⑤ 캐시가 git 에 추적되나": {
            "data/state 아래 추적 파일": len(tracked),
            "그중 cache_* 파일": cache_tracked,
            "🔴 단서": "추적은 되지만 **git 은 mtime 을 보존하지 않는다** — "
                     "새로 clone 하면 ④ 의 시각은 사라진다. 지금 이 값은 **이 작업 트리에서만** 참이다",
        },
        "⑥ 캐시 본문에 시각 필드(표본 5개 · 🔴 전수 아님)": body,
        "⑦ 원천 URL 에 날짜가 박힌 레코드": dict(url_date_hits) or "🔴 0",
        "🔴🔴 ⑧ 되풀이 관측 — 같은 id 를 두 시각에 잡았고 값이 달라졌나": repeat,
        "저장소별": per,
        "🔴 합계": {
            "분모 D2": tot,
            "직접 조인으로 시각이 붙은 레코드": tot_direct,
            "페이지 조인으로 붙은 레코드": tot_page,
            "🔴 어느 경로로든 붙은 레코드": tot_any,
            "덮음": round(tot_any / tot, 4) if tot else None,
        },
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "저장소별"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
