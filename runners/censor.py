"""절단 보정 — 잘린 값이 순위를 바꾸나(노트 658).

같은 브랜드 · 같은 창에서 **6쪽(절단)** 과 **20쪽(심층)** 을 재서 순위 상관을 낸다.
브랜드는 고정 씨앗 무작위 12개 — 상한에 닿는 것만 고르면 상관이 인위로 낮아진다.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

import numpy as np
from scipy.stats import spearmanr

from lab import trendaxes as ta

ta.set_wide(False); ta.set_grades(("A", "B", "C", "D", "E"))

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9", "Referer": "https://search.naver.com/"}


def _get(u, t=30):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                  timeout=t).read().decode("utf-8", "ignore")


def count(q, frm, to, pages):
    """쪽수만큼 훑어 고유 글 수. 새 글이 없으면 조기 종료."""
    ids, used = set(), 0
    for p in range(pages):
        u = ("https://search.naver.com/search.naver?ssc=tab.blog.all&query="
             + urllib.parse.quote(q)
             + f"&nso=so%3Ar%2Cp%3Afrom{frm}to{to}&start={1 + p * 30}")
        try:
            h = _get(u)
        except Exception:
            break
        new = set(re.findall(r"blog\.naver\.com/[\w-]+/(\d+)", h))
        used = p + 1
        if not new - ids:
            break
        ids |= new
        time.sleep(0.9)
    return len(ids), used


ids = ta._ids()["팝업"]
meta = {m["id"]: m.get("date") for m in json.load(open("data/state/popup_v2_meta.json"))}
cand = []
for r in ids:
    try:
        rec = json.load(open(f"data/records/{r}.json"))
    except Exception:
        continue
    bk = ((rec.get("entities") or {}).get("brand_key")
          or (rec.get("intervention") or {}).get("brand_name"))
    od = meta.get(r) or ((rec.get("conditions") or {}).get("period") or {}).get("from")
    if bk and od:
        cand.append((r, str(bk), str(od)[:10]))
rng = np.random.default_rng(658)
pick = [cand[i] for i in rng.permutation(len(cand))[:12]]
print(json.dumps({"후보": len(cand), "뽑음": len(pick)}, ensure_ascii=False), flush=True)

rows = []
for rid, bk, od in pick:
    d1 = date.fromisoformat(od); d0 = d1 - timedelta(days=90)
    frm, to = d0.strftime("%Y%m%d"), d1.strftime("%Y%m%d")
    c6, u6 = count(bk, frm, to, 6)
    c20, u20 = count(bk, frm, to, 20)
    rows.append((rid, bk, c6, u6, c20, u20))
    print(f"  {rid} {bk[:14]:16s} 6쪽 {c6:>4}(쪽{u6})  20쪽 {c20:>4}(쪽{u20})", flush=True)

a = np.array([r[2] for r in rows], float)
b = np.array([r[4] for r in rows], float)
cap6 = sum(1 for r in rows if r[3] >= 6)
r = float(spearmanr(a, b).statistic)
print(json.dumps({"스피어만(6쪽 대 20쪽)": round(r, 4),
                  "6쪽 상한 도달": f"{cap6}/{len(rows)}",
                  "20쪽에서 더 찾은 글 중앙": int(np.median(b - a)),
                  "판정": ("절단 감수(>=0.95)" if r >= 0.95 else
                          "표시자 추가(0.85~0.95)" if r >= 0.85 else "수집기 고침(<0.85)"),
                  "무효 조건": "상한 도달 0 이면 무효" if cap6 == 0 else "해당 없음"},
                 ensure_ascii=False, indent=1), flush=True)
