# -*- coding: utf-8 -*-
# 노트 850 — 사전 폭의 문 (사전등록 '850' · 회사 검색 → 필모 → pre-2025 배급 실적)
# 시간 게이트: 실적 인정 = 필모의 배급사-역할 영화가 pre-2025 일별 표(백필)에 제목으로 존재.
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}
SLEEP = 1.5
t0 = time.time()


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


# pre-2025 일별 표 제목 집합(백필 2023~2024 — 개봉일 < 2025 인 행만)
B1 = json.load(open(ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json"))
pre_titles = set()
for day, rows in B1.items():
    if day >= "2025-01-01":
        continue
    for r in rows:
        od = r.get("개봉일")
        if od and od < "2025-01-01":
            pre_titles.add(r["제목"].strip())
print(f"pre-2025 일별 제목 {len(pre_titles)}", flush=True)

a3 = json.load(open(ROOT / "cycle_log/forward/kobis/annex3_2026-08-08.json"))
targets = [(a["제목"], a["첫 세그먼트"]) for a in a3["결측 부검 정본(재분류)"] if "사전 밖" in a["판"]]


def norm(s):
    return re.sub(r"[()㈜\s]|주식회사|유한회사", "", s or "")


out = []
for film, comp in targets:
    rec = {"봉인 작품": film, "회사명": comp}
    try:
        b = post("https://www.kobis.or.kr/kobis/business/mast/comp/searchCompanyList.do",
                 {"sCompanyNm": comp, "pageIndex": "1"})
        cands = []
        for tr in re.split(r"<tr[^>]*>", b)[1:]:
            m = re.search(r"mstView\('company','(\d+)'\)", tr)
            if not m:
                continue
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            cands.append((m.group(1), cells[0] if cells else ""))
        # 정규화 일치 우선 · 없으면 첫 후보(모호 병기)
        exact = [c for c in cands if norm(c[1]) == norm(comp)]
        pick = exact[0] if exact else (cands[0] if cands else None)
        rec["후보 수"] = len(cands)
        rec["모호"] = bool(cands and not exact and len(cands) > 1)
        if not pick:
            rec["판"] = "회사 검색 0건"
            out.append(rec)
            time.sleep(SLEEP)
            continue
        rec["code"] = pick[0]
        rec["매칭 회사"] = pick[1]
        time.sleep(SLEEP)
        f = post("https://www.kobis.or.kr/kobis/business/mast/comp/searchCompanyDtl.do",
                 {"code": pick[0], "sType": "filmo"})
        films = []
        for li in re.split(r"<li style=", f)[1:]:
            tt = re.search(r"mstView\('movie','\d+'\);return false;\">([^<]+)</a></dt>", li)
            role = re.search(r'class="make">:\s*([^<]+)</dd>', li)
            yr = re.search(r'class="minfo"><span>(\d{4})</span>', li)
            if tt:
                films.append({"제목": re.sub(r"\([^)]*\)\s*$", "", tt.group(1)).strip(),
                              "역할": (role.group(1).strip() if role else "?"),
                              "제작연도": int(yr.group(1)) if yr else None})
        dist = [x for x in films if "배급" in x["역할"]]
        hit = [x for x in dist if x["제목"] in pre_titles]
        rec["필모 전체"] = len(films)
        rec["배급 역할"] = len(dist)
        rec["pre-2025 실적(일별 표 대조)"] = len(hit)
        rec["실적 예"] = [x["제목"] for x in hit[:3]]
        rec["판"] = "실적 있음" if hit else "실적 없음(pre-2025)"
    except Exception as e:
        rec["판"] = f"⛔ {str(e)[:60]}"
    out.append(rec)
    print(f"  {comp}: {rec.get('판')} · 배급 {rec.get('배급 역할')} · pre-2025 {rec.get('pre-2025 실적(일별 표 대조)')}", flush=True)
    time.sleep(SLEEP)

n_have = sum(1 for r in out if r.get("판") == "실적 있음")
branch = ("1.문 열림·v3 구축" if n_have >= 7 else
          ("2.부분 보충" if n_have >= 3 else "3.기각 — 결손은 원자료 부재(신생/초소형)"))
res = {"회사별": out, "실적 보유": f"{n_have}/9", "갈래": branch, "초": round(time.time() - t0, 1)}
print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
json.dump(res, open(ROOT / "runners/out850_door.json", "w"), ensure_ascii=False, indent=1)
