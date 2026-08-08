# -*- coding: utf-8 -*-
# 노트 851(a) — 필모 재측정: 전 페이지(etcParam 페이징 · 티처 #16 절단 정정)
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}
SLEEP = 1.5
MAXP = 20
t0 = time.time()


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


B1 = json.load(open(ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json"))
pre_titles = set()
for day, rows in B1.items():
    if day >= "2025-01-01":
        continue
    for r in rows:
        od = r.get("개봉일")
        if od and od < "2025-01-01":
            pre_titles.add(r["제목"].strip())

old = json.load(open(ROOT / "runners/out850_door.json"))
out = []
for c in old["회사별"]:
    if "code" not in c:
        out.append({**c, "재측정": "코드 없음 — 원판 유지"})
        continue
    films, page = [], 1
    while page <= MAXP:
        b = post("https://www.kobis.or.kr/kobis/business/mast/comp/searchCompanyDtl.do",
                 {"code": c["code"], "sType": "filmo", "titleYN": "N", "etcParam": str(page)})
        got = []
        for li in re.split(r"<li style=", b)[1:]:
            tt = re.search(r"mstView\('movie','\d+'\);return false;\">([^<]+)</a></dt>", li)
            role = re.search(r'class="make">:\s*([^<]+)</dd>', li)
            yr = re.search(r'class="minfo"><span>(\d{4})</span>', li)
            if tt:
                got.append({"제목": re.sub(r"\([^)]*\)\s*$", "", tt.group(1)).strip(),
                            "역할": (role.group(1).strip() if role else "?"),
                            "연도": int(yr.group(1)) if yr else None})
        if not got:
            break
        before = len(films)
        seen = {f["제목"] for f in films}
        films += [g for g in got if g["제목"] not in seen]
        if len(films) == before:      # 새 것이 없다 = 마지막 페이지 반복
            break
        page += 1
        time.sleep(SLEEP)
    dist = [x for x in films if "배급" in x["역할"]]
    hit = [x for x in dist if x["제목"] in pre_titles]
    rec = {"봉인 작품": c["봉인 작품"], "회사명": c["회사명"], "code": c["code"],
           "필모 전체(재)": len(films), "페이지": page, "배급 역할(재)": len(dist),
           "pre-2025 실적(재)": len(hit), "실적 예": [x["제목"] for x in hit[:4]],
           "원판(1p 절단)": {"배급": c.get("배급 역할"), "pre25": c.get("pre-2025 실적(일별 표 대조)")},
           "판(재)": "실적 있음" if hit else "실적 없음(pre-2025)"}
    out.append(rec)
    print(f"  {c['회사명']}: 필모 {len(films)}(p{page}) · 배급 {len(dist)} · pre25 {len(hit)} "
          f"(원판 {c.get('pre-2025 실적(일별 표 대조)')})", flush=True)

n_have = sum(1 for r in out if r.get("판(재)") == "실적 있음")
old_n = 3
branch = ("1.유지(3/9 — 절단 무영향 실증)" if n_have == old_n else
          ("2.부분 확대(4~6/9)" if n_have <= 6 else "3.850 갈래 뒤집힘(≥7/9) — 정오"))
res = {"회사별(재)": out, "실적 보유(재)": f"{n_have}/9", "원판": "3/9", "갈래": branch,
       "초": round(time.time() - t0, 1)}
print(json.dumps({k: v for k, v in res.items() if k != "회사별(재)"}, ensure_ascii=False, indent=1), flush=True)
json.dump(res, open(ROOT / "runners/out851_refilmo.json", "w"), ensure_ascii=False, indent=1)
