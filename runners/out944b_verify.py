# -*- coding: utf-8 -*-
"""노트 944 — **두 번째 경로.** `out944b_obstime.py` 의 수를 **다른 방식으로** 다시 센다.

🔴 943 은 D2 를 「별도 스크립트로 다시 셌다」고 적고 **그 스크립트를 안 남겼다**
(티처 #83 C2 · 티처 #82 M1 의 글자 그대로 재발). 이 파일이 그 재발을 닫는다.

**무엇이 다른가** (같은 코드를 다시 부르면 두 번째 경로가 아니다):

  ㄱ 첫 경로는 `Path.exists()` 로 **파일마다 stat** 한다.
    이 경로는 디렉터리를 **한 번 훑어 이름 집합**을 만들고 **집합 소속**으로 판정한다.
  ㄴ 첫 경로는 `json.loads` 로 파싱해 `data.Page.media[].id` 를 꺼낸다.
    이 경로는 **원문 텍스트에 정규식**을 물려 id 를 꺼낸다(파서를 안 쓴다).
  ㄷ 첫 경로는 `popularity` 를 dict 에서 꺼낸다.
    이 경로는 **`"id": N` 뒤에 붙은 `"popularity": M`** 을 정규식 쌍으로 읽는다.
  ㄹ 🔴 떨군 산출물(`data/state/obs_time944*.json`)을 **읽어서** 대조한다 —
    손 전사 금지(890 계열의 병).

🔴 이 러너는 아무것도 안 덮어쓴다. `runners/out944b_verify.json` 만 쓴다.

쓰는 법::  python3 runners/out944b_verify.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
OUT = ROOT / "runners/out944b_verify.json"

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

#: ㄱ 이름 규칙 — 첫 경로와 **같은 규칙**이어야 대조가 성립한다(방법만 다르다).
NAMES = {
    "게임": [("cache_steam", "app_%s.json", "appid"),
            ("cache_steamspy", "%s.json", "record_id")],
    "모바일": [("cache_mobile", "app_%s.json", "app_id")],
    "앱": [("cache_mobile", "app_%s.json", "app_id")],
    "애니": [("cache_anime", "ep_%s.json", "item_id")],
    "웹툰": [("cache_webtoon", "asc_%s.json", "title_id")],
    "도서": [("cache_bookpage", "%s.html", "record_id"),
            ("cache_aladin_book", "item_%s.html", "item_id")],
    "펀딩": [("cache_fundpage", "%s.html", "record_id")],
}

PAGE_DIRS = {
    "만화": ["cache_manga", "cache_manga_below", "cache_manga_mid",
            "cache_manga_deep", "cache_manga_recent", "cache_manga_below_pre"],
    "세계애니": ["cache_wanime", "cache_wanime_deep"],
    "펀딩": ["cache_tumblbug"],
}
PAGE_KEY = {"만화": "media_id", "세계애니": "media_id", "펀딩": "uuid"}

#: ㄴ·ㄷ 파서를 안 쓴다 — **손으로 쓴 깊이 스캐너**.
#: 🔴 초판은 `"id":\s*(\d+)` 정규식이었는데 media 안의 **staff 노드 id** 까지 긁어
#:   되풀이 id 가 2,479 → 2,779 로 부풀었다(첫 판 실측 · 그대로 신고한다).
#:   원인: anilist media 는 `staff.edges[].node.id` 를 품는다. 정규식은 깊이를 모른다.
RE_NUM = re.compile(r"-?\d+")
RE_UUID = re.compile(r'"id":\s*"([0-9a-f]{8}-[0-9a-f-]{27})"')


def media_entries(txt: str) -> list:
    """`"media": [` 배열을 깊이·문자열을 손으로 세어 **깊이 1 객체**로 쪼갠다."""
    out = []
    idx = 0
    while True:
        j = txt.find('"media":', idx)
        if j < 0:
            break
        k = txt.find("[", j)
        if k < 0:
            break
        depth = 0
        start = None
        instr = esc = False
        i = k
        while i < len(txt):
            c = txt[i]
            if instr:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == "{":
                depth += 1
                if depth == 1:
                    start = i
            elif c == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(txt[start:i + 1])
                    start = None
            elif c == "]" and depth == 0:
                break
            i += 1
        idx = i + 1
    return out


def top_num(entry: str, key: str) -> int | None:
    """`entry` 의 **깊이 1**(=객체 최상위)에 있는 `"key": 숫자` 만 읽는다."""
    pat = '"%s":' % key
    depth = 0
    instr = esc = False
    i = 0
    n = len(entry)
    while i < n:
        c = entry[i]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            if depth == 1 and entry.startswith(pat, i):
                j = i + len(pat)
                while j < n and entry[j] == " ":
                    j += 1
                m = RE_NUM.match(entry, j)
                return int(m.group()) if m else None
            instr = True
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        i += 1
    return None


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> dict:                                        # noqa: PLR0915
    t0 = time.time()
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # ── ㄱ 디렉터리를 한 번 훑어 **이름 집합** ────────────────────────────
    dirnames: dict = {}
    dirmtime: dict = {}
    for dp in sorted((ROOT / "data/state").glob("cache_*")):
        if not dp.is_dir():
            continue
        s = set()
        mt = {}
        with os.scandir(dp) as it:
            for e in it:
                if e.is_file():
                    s.add(e.name)
                    mt[e.name] = round(e.stat().st_mtime)
        dirnames[dp.name] = s
        dirmtime[dp.name] = mt

    # ── ㄴ 목록 캐시를 정규식으로 훑는다 ─────────────────────────────────
    pageseq: dict = defaultdict(lambda: defaultdict(list))   # dom → id → [(ts, pop, src)]
    pagefiles: Counter = Counter()
    for dom, dirs in PAGE_DIRS.items():
        for dname in dirs:
            dp = ROOT / "data/state" / dname
            if not dp.exists():
                continue
            for name in sorted(dirnames.get(dname, ())):
                if not name.endswith(".json"):
                    continue
                pagefiles[dom] += 1
                txt = (dp / name).read_text(errors="ignore")
                ts = dirmtime[dname][name]
                src = f"data/state/{dname}/{name}"
                if dom == "펀딩":
                    for u in RE_UUID.findall(txt):
                        pageseq[dom][u].append((ts, None, src))
                else:
                    for ent in media_entries(txt):
                        i = top_num(ent, "id")
                        if i is None:
                            continue
                        pageseq[dom][i].append((ts, top_num(ent, "popularity"), src))

    # ── 레코드 덮음 ─────────────────────────────────────────────────────
    per: dict = {}
    tot = tot_any = 0
    cover_ids: dict = {}
    for path, dom in STORES.items():
        recs = [v for v in json.loads((ROOT / path).read_text()).values()
                if isinstance(v, dict)]
        n = len(recs)
        tot += n
        got = set()
        direct = Counter()
        for v in recs:
            rid = v["record_id"]
            for dname, pat, key in NAMES.get(dom, []):
                kv = v.get(key)
                if kv is None:
                    continue
                if (pat % kv) in dirnames.get(dname, ()):
                    got.add(rid)
                    direct[dname] += 1
            if dom in PAGE_DIRS and v.get(PAGE_KEY[dom]) in pageseq[dom]:
                got.add(rid)
                direct["(목록)"] += 1
        tot_any += len(got)
        cover_ids[dom] = got
        per[dom] = {"분모": n, "붙은 레코드": len(got),
                    "덮음": round(len(got) / n, 4) if n else None,
                    "경로별 히트": dict(direct)}

    # ── 만화 두 점을 정규식 경로로 다시 ──────────────────────────────────
    mg = [v for v in json.loads((ROOT / "data/state/manga_records.json").read_text()).values()
          if isinstance(v, dict)]
    rep = chg = 0
    gaps, dpop, neg = [], [], 0
    mf = ml = 0
    diffdir = 0
    for v in mg:
        rows = sorted(pageseq["만화"].get(v.get("media_id"), []), key=lambda x: x[0])
        if len({t for t, _, _ in rows}) < 2:
            continue
        rep += 1
        a, b = rows[0], rows[-1]
        if a[1] is None or b[1] is None or a[1] == b[1]:
            continue
        chg += 1
        gaps.append((b[0] - a[0]) / 3600)
        dpop.append(b[1] - a[1])
        neg += (b[1] - a[1]) < 0
        mf += (v.get("y_popularity") == a[1])
        ml += (v.get("y_popularity") == b[1])
        diffdir += (a[2].split("/")[2] != b[2].split("/")[2])

    # ── ㄹ 떨군 산출물을 **읽어서** 대조 ─────────────────────────────────
    art = json.loads((ROOT / "data/state/obs_time944.json").read_text())
    artm = json.loads((ROOT / "data/state/obs_time944_manga.json").read_text())
    a_ids = set(art["레코드"])
    v_ids = set().union(*cover_ids.values())
    first = json.loads((ROOT / "runners/out944b_obstime.json").read_text())

    mine = {
        "분모 D2": tot, "붙은 레코드": tot_any,
        "덮음": round(tot_any / tot, 4),
        "되풀이 만화 레코드": rep, "🔴 값이 달라진 레코드": chg,
        "간격 중앙(시간)": round(statistics.median(gaps), 2) if gaps else None,
        "간격 최대(시간)": round(max(gaps), 2) if gaps else None,
        "간격 1시간 미만": sum(1 for g in gaps if g < 1),
        "Δpopularity 중앙": statistics.median(dpop) if dpop else None,
        "Δ 음수": neg,
        "y == 첫 점": mf, "y == 끝 점": ml,
        "서로 다른 디렉터리 쌍": diffdir,
    }
    theirs = {
        "분모 D2": first["🔴 ① 합계 — 943 과 나란히"]["분모 D2"],
        "붙은 레코드": first["🔴 ① 합계 — 943 과 나란히"]["944 가 센 붙은 레코드"],
        "덮음": first["🔴 ① 합계 — 943 과 나란히"]["🔴 944 덮음"],
        "되풀이 만화 레코드": first["🔴 ② 만화 두 점"]["그중 저장소 레코드"],
        "🔴 값이 달라진 레코드": first["🔴 ② 만화 두 점"]["🔴 popularity 가 달라진 레코드"],
        "간격 중앙(시간)": first["🔴 ② 만화 두 점"]["간격(시간) 중앙"],
        "간격 최대(시간)": first["🔴 ② 만화 두 점"]["간격(시간) 최대"],
        "간격 1시간 미만": first["🔴 ② 만화 두 점"]["🔴 간격 1시간 미만"],
        "Δpopularity 중앙": first["🔴 ② 만화 두 점"]["Δpopularity 중앙"],
        "Δ 음수": first["🔴 ② 만화 두 점"]["🔴 Δ 음수"],
        "y == 첫 점": first["🔴 ② 만화 두 점"]["🔴 y_popularity == 첫 점"],
        "y == 끝 점": first["🔴 ② 만화 두 점"]["🔴 y_popularity == 끝 점"],
        "서로 다른 디렉터리 쌍": first["🔴 ② 만화 두 점"]["서로 다른 디렉터리 쌍"],
    }
    cmp_rows = {k: {"두번째 경로": mine[k], "첫 경로": theirs[k], "같나": mine[k] == theirs[k]}
                for k in mine}

    res = {
        "노트": 944, "레인": "🔴 탐색 — 두 번째 경로",
        "무엇이 다른가": ["stat 대신 디렉터리 이름 집합", "json 파서 대신 정규식",
                     "dict 접근 대신 id·popularity 정규식 쌍", "산출물을 읽어서 대조"],
        "🔴 스탬프": {
            "시작 시각": t_start, "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "초": round(time.time() - t0, 1),
            "입력 sha256(저장소 아홉)": {k: sha(ROOT / k) for k in STORES},
            "입력 sha256(대조 대상)": {
                p: sha(ROOT / p) for p in
                ("runners/out944b_obstime.json", "data/state/obs_time944.json",
                 "data/state/obs_time944_manga.json")},
            "코드 sha256": {"runners/out944b_verify.py":
                          sha(ROOT / "runners/out944b_verify.py")},
        },
        "🔴 대조표": cmp_rows,
        "🔴 전부 같나": all(v["같나"] for v in cmp_rows.values()),
        "🔴 떨군 파일과의 대조": {
            "obs_time944.json 레코드 수": len(a_ids),
            "두번째 경로가 붙인 레코드 수": len(v_ids),
            "집합이 같나": a_ids == v_ids,
            "첫 경로에만": len(a_ids - v_ids), "두번째에만": len(v_ids - a_ids),
            "obs_time944_manga.json 레코드 수": len(artm["레코드"]),
            "두번째 경로 값 달라진 수": chg,
            "같나": len(artm["레코드"]) == chg,
        },
        "저장소별(두번째 경로)": per,
        "목록 캐시 파일 수(두번째 경로)": dict(pagefiles),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
