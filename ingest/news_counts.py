"""뉴스 언급량 — **(시간 × 대상)** 축의 자료를 모은다(노트 659).

노트 651 이 빈자리를 남겼다 --- 노트 649 의 규칙(범도메인 축은 *시간* 이 아니라
**(시간 × 대상)** 이어야 한다)을 지키면서 **기존 축과 겹치지 않는** 축을 아직
못 만들었다. `crowd_share` 는 규칙을 지켰지만 `gen` 의 사본이었다.

구글 뉴스 RSS 가 그 형태다.

  * 질의(대상) × 기간(시간)으로 값이 정해진다 --- 같은 날 나온 두 작품도
    제목이 다르면 값이 다르다.
  * **레코드당 요청 하나**라 실현 가능하다. 블로그 크롤은 스무 쪽이라(노트 658)
    21,672행엔 못 쓴다.
  * 키가 없다.

**시간 게이트.** `after:`/`before:` 로 **출시 이전 90일**만 자른다. 기사에는
게시일이 박혀 있으므로 출시 후가 섞이지 않는다(노트 149 규약과 같다).

**절단을 처음부터 표시한다.** 질의당 100건 상한이 있다. 노트 658 이 절단이
순위를 망가뜨림을 쟀으므로(6쪽 대 20쪽 순위 상관 0.77 · 상한 도달분만 0.41)
**`상한도달` 을 값과 함께 저장**한다. 그리고 노트 658 의 다른 교훈대로
**요청 실패는 `None`** 이다 --- 0 으로 보고하면 '없음' 과 안 갈린다.

쓰는 법::

    python3 -m ingest.news_counts --per 150
    python3 -m ingest.news_counts --report
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/state/news_counts"
WINDOW = 90
CAP = 100
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 Chrome/124 Safari/537.36")}

#: 도메인 → (레코드 파일, 제목 필드). 제목은 여덟 도메인 **전부에 100%** 있다.
#: **제목을 어디서 읽나 — 열한 도메인 전부**(노트 680).
#:
#: `SRC` 는 뉴스 크롤 전용 모양(`data/state/*.json` 의 평평한 `{id: {field: ..}}`)이라
#: 세 도메인이 안 담긴다. 그 셋은 파일도 모양도 다르다:
#:
#:   팝업       `data/records/<id>.json` → `intervention.brand_name`
#:              (예: "이직로그 (이직로그 팝업스토어)")
#:   시장팝업   `data/market_records/*.json` → `event_name` (`brand`·`ip_or_collab` 도 있다)
#:   아이돌     `data/idol_records/*.json` → `group_name`
#:
#: 노트 680 이 제목 텍스트만으로 판 rho **0.2399** 를 쟀는데 이 셋이 빠져서
#: 판의 88%(2,962/3,369행)만 덮었다. **팝업 계열이 이 판에서 제일 관심 있는
#: 도메인이므로** 다음 실험 전에 채운다.
def titles(dom: str) -> list | None:
    """도메인 → `_ids()` 순서에 맞춘 제목 리스트. 없으면 `None`.

    **빈 문자열과 `None` 을 구분한다** --- 빈 문자열은 '제목이 없는 행' 이고
    `None` 은 '이 도메인은 원천 자체가 없다' 다(노트 658 의 같은 조항).
    """
    from lab.trendaxes import _ids
    ids = (_ids() or {}).get(dom) or []
    if not ids:
        return None
    if dom in SRC:
        f, fld = SRC[dom]
        p = ROOT / "data/state" / f
        if not p.exists():
            return None
        j = json.loads(p.read_text())
        if not isinstance(j, dict):
            return None
        return [str((j.get(k) or {}).get(fld) or "") for k in ids]
    if dom == "팝업":
        out = []
        for k in ids:
            q = ROOT / "data/records" / f"{k}.json"
            if not q.exists():
                out.append("")
                continue
            d = json.loads(q.read_text())
            out.append(str((d.get("intervention") or {}).get("brand_name") or ""))
        return out
    if dom == "아이돌":
        #: 🔴 id 순서를 **판과 같은 원천**(idolset._rows · 173행)에서 받는다
        #: (노트 810). 전에는 trendaxes._ids = idol_axes.json 의 81키를 써서
        #: 창구의 제목-행 짝이 틀렸다(값은 record_id 로 옳았고 순서가 달랐다).
        try:
            from lab.idolset import _rows
            ids = [r.get("record_id") for r in _rows(wide_post=True)]
        except Exception:
            pass                        # 폴백: _ids 순서(길이 불일치는 부르는 쪽 검사)
    if dom in ("시장팝업", "아이돌"):
        sub, fld, idk = (("data/market_records", "event_name", "market_record_id")
                         if dom == "시장팝업"
                         else ("data/idol_records", "group_name", "record_id"))
        by = {}
        for q in (ROOT / sub).glob("*.json"):
            try:
                d = json.loads(q.read_text())
            except Exception:
                continue
            rid = d.get(idk) or q.stem
            by[rid] = str(d.get(fld) or "")
        return [by.get(k, "") for k in ids]
    return None


SRC = {"게임": ("game_records.json", "name"),
       "도서": ("book_records.json", "title"),
       "만화": ("manga_records.json", "title"),
       "모바일": ("mobile_records.json", "title"),
       "세계애니": ("wanime_records.json", "title"),
       "애니": ("anime_records.json", "title"),
       "웹툰": ("webtoon_records.json", "title"),
       "펀딩": ("funding_records.json", "title")}


def fetch(q: str, d0: date, d1: date) -> dict:
    """[d0, d1) 창의 기사 수. **실패는 None** — 0 과 안 섞는다(노트 658)."""
    qq = f"{q} after:{d0.isoformat()} before:{d1.isoformat()}"
    u = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(qq)
         + "&hl=ko&gl=KR&ceid=KR:ko")
    # **429/403 은 기다리면 열린다**(노트 659). 처음엔 재시도 없이 돌렸는데
    # 500건쯤에서 구글이 조이기 시작해 **최근 60건이 전부 HTTPError** 였다.
    # 실패가 `None` 이라 0 과 섞이진 않았지만(노트 658 고침) 자료가 통째로 빈다.
    h = None
    for wait in (0, 8, 25, 60):
        if wait:
            time.sleep(wait)
        try:
            h = urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                       timeout=30).read().decode("utf-8", "ignore")
            break
        except Exception as e:
            err = type(e).__name__
    if h is None:
        return {"n": None, "상한도달": False, "오류": err}
    n = h.count("<item>")
    dates = re.findall(r"<pubDate>([^<]+)</pubDate>", h)
    return {"n": n, "상한도달": n >= CAP,
            "첫날": dates[-1] if dates else None}


def run(per: int = 150, sleep: float = 2.5, since: int = 2023) -> dict:
    """도메인마다 최신 `per` 건. **2023+ 를 먼저** — 판 유보(2025+)를 덮는다."""
    from lab import trendaxes as ta
    ta.set_wide(False); ta.set_grades(("A", "B", "C", "D", "E"))
    from lab.calaxes import _dates
    from lab.trendaxes import _ids
    ids, dates = _ids(), _dates()
    D = ROOT / "data/state"
    OUT.mkdir(parents=True, exist_ok=True)
    got, fail = {}, {}
    for dom, (f, fld) in SRC.items():
        p = D / f
        if not p.exists() or dom not in ids:
            continue
        j = json.loads(p.read_text())
        keys, ds = ids[dom], dates.get(dom) or []
        # 최근 것부터 --- 유보를 먼저 덮는다
        cand = [(k, d) for k, d in zip(keys, ds)
                if d and d.year >= since and (j.get(k) or {}).get(fld)]
        cand.sort(key=lambda x: -x[1].toordinal())
        n = 0
        for k, d in cand[:per]:
            o = OUT / f"{k}.json"
            if o.exists():
                n += 1
                continue
            r = fetch(str((j.get(k) or {})[fld]), d - timedelta(days=WINDOW), d)
            r.update(record_id=k, domain=dom, open=d.isoformat(),
                     query=str((j.get(k) or {})[fld]), window=WINDOW)
            o.write_text(json.dumps(r, ensure_ascii=False))
            if r["n"] is None:
                fail[k] = r.get("오류")
            else:
                n += 1
            time.sleep(sleep)
        got[dom] = n
    return {"받음": got, "실패": len(fail), "실패 예": list(fail)[:3]}


def report() -> None:
    fs = list(OUT.glob("*.json")) if OUT.exists() else []
    per, cap, none = {}, 0, 0
    vals = []
    for p in fs:
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        per[j.get("domain")] = per.get(j.get("domain"), 0) + 1
        if j.get("n") is None:
            none += 1
        else:
            vals.append(j["n"])
            cap += bool(j.get("상한도달"))
    import numpy as np
    print(json.dumps({"파일": len(fs), "도메인별": per, "실패(None)": none,
                      "상한 도달": f"{cap}/{len(vals)}" if vals else "0",
                      "기사 수 중앙": int(np.median(vals)) if vals else None,
                      "0건 비율": round(float(np.mean(np.array(vals) == 0)), 3)
                      if vals else None}, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=150)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        print(json.dumps(run(a.per), ensure_ascii=False, indent=1))
        report()
