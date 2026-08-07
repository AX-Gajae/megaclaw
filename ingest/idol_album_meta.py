"""아이돌 데뷔 앨범의 버전 수와 정가를 수집한다 --- 굿즈 규모·입장 허들 축의 원료.

노트 8이 지정한 수집 과제. 한터 확정 81건에서 다섯 축을 유도했더니 굿즈 규모와
입장 허들의 태깅률이 0%였다. 아이돌 레코드에 앨범 버전 수도 가격도 없기 때문이다.
둘 다 음반 유통 상품 페이지에 공개돼 있다.

  굿즈 규모  ← 앨범 버전 수 ('[8종 세트]', '[4종 중 랜덤발송]')
  입장 허들  ← 단품 정가 (팬이 하나 사려면 치러야 하는 값)

**오염 방지 규약.** 이 프로젝트에서 크롤링 사고는 전부 '비슷해 보이는 것을 같은
것으로 본' 데서 났다 --- 4개 그룹 합동 기사의 수치를 한 그룹에 귀속시킨 사건,
신세계그룹 전체 유동인구를 한 팝업에 넣은 사건. 그래서 여기서는:

  · 그룹명과 앨범명이 **둘 다** 상품 제목에 있어야 채택한다.
  · 앨범명이 레코드에 없으면 그룹명만으로는 채택하지 않는다(미해결로 남긴다).
  · 채택한 상품 제목과 URL을 그대로 기록한다. 나중에 사람이 검증할 수 있어야 한다.
  · 세트 상품(N종 세트)의 가격은 단품 가격이 아니므로 분리해 저장한다.

요청 간격 1.2초를 지킨다. 앞서 다른 사이트에서 IP 차단(430)을 맞은 적이 있다.

사용:
  python3 -m ingest.idol_album_meta --limit 10     # 시험
  python3 -m ingest.idol_album_meta                 # 전량
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REC = Path("data/idol_records")
OUT = Path("data/state/idol_album_meta.json")
CACHE = Path("data/state/cache_aladin")

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
DELAY = 2.5          # 1.2초에서는 50건 근처에서 연결이 끊겼다(Errno 54)
RETRY = 3
COOLDOWN_EVERY = 25  # 25건마다 길게 쉰다

# '[8종 세트]', '[4종 중 랜덤발송]', '(3종 중 1종)' 등에서 종 수를 뽑는다.
NJONG = re.compile(r"(\d{1,2})\s*종")
SET_MARK = re.compile(r"세트|SET", re.I)


def fetch(word: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (re.sub(r"[^0-9A-Za-z가-힣]", "_", word)[:80] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8", errors="ignore")
    url = ("https://www.aladin.co.kr/search/wsearchresult.aspx?SearchTarget=Music"
           f"&SearchWord={urllib.parse.quote(word)}")
    # 상대 서버가 끊으면 물러섰다가 다시 시도한다. ConnectionResetError 는 OSError 라
    # 처음에 잡지 않아 50건 지점에서 수집이 통째로 중단됐다.
    html = None
    for attempt in range(RETRY):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=25) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                html = raw.decode("utf-8", "ignore")
            break
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as e:
            wait = DELAY * (4 ** attempt)
            print(f"    [재시도 {attempt+1}/{RETRY}] {word}: {type(e).__name__} — {wait:.0f}초 대기")
            time.sleep(wait)
    if html is None:
        print(f"    [실패] {word}: 재시도 소진")
        return None
    time.sleep(DELAY)
    key.write_text(html, encoding="utf-8")
    return html


def parse(html: str) -> list[dict]:
    """상품 블록에서 (제목, ItemId, 정가)를 뽑는다."""
    out = []
    for m in re.finditer(r'ItemId=(\d+)"[^>]*class="bo3"[^>]*>(.*?)</a>', html, re.S):
        item_id, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        tail = html[m.end():m.end() + 2500]
        pm = re.search(r"정가\s*:?\s*</?[^>]*>?\s*([\d,]{4,})", tail) or \
             re.search(r"([\d,]{4,})\s*원", tail)
        price = int(pm.group(1).replace(",", "")) if pm else None
        out.append({"item_id": item_id, "title": title, "price": price})
    return out


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (s or "").lower())


# 앨범명 뒤에 붙는 발매 형태 표기. 상품 제목에서는 '미니 1집'이 앞에 오므로
# 레코드 쪽 접미를 떼어내야 대조가 된다.
KIND = re.compile(r"\(?\s*(정규|미니|싱글|EP|스페셜|리패키지)\s*\d*\s*집?\s*\)?", re.I)


def variants(s: str | None) -> list[str]:
    """대조용 표기 변형. 괄호 안팎을 각각 따로 낸다.

    '방탄소년단 (BTS)' 는 상품 제목에서 '방탄소년단' 으로만 나오고,
    '꿈의 장: STAR (The Dream Chapter: STAR)' 는 한국어 제목으로만 나온다.
    괄호를 통째로 요구하면 둘 다 놓친다."""
    if not s:
        return []
    out = {s, KIND.sub(" ", s)}
    out.add(re.sub(r"\(.*?\)", " ", s))                 # 괄호 밖만
    out.update(re.findall(r"\(([^)]{2,})\)", s))        # 괄호 안 각각
    return [v for v in {norm(KIND.sub(" ", v)) for v in out} if len(v) >= 2]


def resolve(rec: dict) -> dict:
    """한 레코드의 데뷔 앨범 상품을 찾는다. 확신이 없으면 미해결로 남긴다."""
    g, alb = rec.get("group_name"), rec.get("debut_album")
    base = {"record_id": rec["record_id"], "group": g, "album": alb,
            "versions": None, "unit_price": None, "set_price": None,
            "matched_title": None, "item_id": None, "why": None}
    if not g:
        base["why"] = "그룹명 없음"
        return base
    if not alb:
        base["why"] = "레코드에 데뷔 앨범명 없음 — 그룹명만으로는 채택하지 않는다"
        return base

    # 결합 질의가 0건이면 그룹 단독으로 폴백한다. 알라딘 검색은 긴 질의에 약하다
    # ('워너원 1×1=1 (TO BE ONE) (미니 1집)' → 0건, '워너원' → 25건).
    items = []
    for q in (f"{g} {alb}", g, rec.get("group_name_en") or ""):
        if not q.strip():
            continue
        html = fetch(q)
        if html:
            items = parse(html)
            if items:
                break
    if not items:
        base["why"] = "조회 결과 없음"
        return base

    gs, as_ = variants(g) + variants(rec.get("group_name_en")), variants(alb)
    # 그룹명과 앨범명이 **둘 다** 제목에 있어야 채택한다.
    hits = [it for it in items
            if any(v in norm(it["title"]) for v in gs)
            and any(v in norm(it["title"]) for v in as_)]
    if not hits:
        base["why"] = f"제목에 그룹명+앨범명 동시 일치 없음 (후보 {len(items)}건)"
        return base

    unit = [h for h in hits if not SET_MARK.search(h["title"])]
    sets = [h for h in hits if SET_MARK.search(h["title"])]
    pick = (unit or hits)[0]

    # 버전 수 세기. 두 신호가 있는데 **우선순위가 있다**.
    #  (a) 버전 표기  '[COLOR Ver.]' '[ROSE Ver.]'  → 진짜 앨범 버전
    #  (b) 'N종' 표기 '[커버 8종 중 랜덤발송]'      → 버전일 수도, 아닐 수도
    # (b)를 우선하면 과대 계상된다. 아이즈원 COLOR*IZ 의 실제 버전은 COLOR/ROSE
    # 두 종인데 제목의 '버전별 CD알판 12종 중 랜덤삽입' 을 세어 12종이 나왔다.
    # 12종은 알판 그림이지 앨범 버전이 아니다. 그래서 버전 표기가 있으면 그것을
    # 쓰고, 없을 때만 N종 표기로 넘어간다.
    njs = [int(m.group(1)) for h in hits for m in [NJONG.search(h["title"])] if m]
    raw = [m.group(1) for h in hits
           for m in re.finditer(r"[\[(]\s*([^\[\]()]{1,40}?)\s*(?:ver\.?|버전)\s*[\])]",
                                h["title"], re.I)]
    vers = set()
    for chunk in raw:
        # 앨범명이 통째로 버전 표기 자리에 들어간 경우를 뺀다
        # (엑스원 '비상 : QUANTUM LEAP Ver.' 는 버전명이 아니라 앨범명이다).
        # **덩어리 전체가 같을 때만** 뺀다 --- 부분 문자열로 빼면 COLOR*IZ 의
        # 'COLOR Ver.' 처럼 앨범명과 겹치는 진짜 버전명까지 지워진다.
        if norm(chunk) in as_:
            continue
        for piece in re.split(r"[/,+&·]|\s중\s|\s및\s", chunk):
            p = re.sub(r"(ver|버전)$", "", norm(piece))
            if p and p not in as_:
                vers.add(p)
    n_ver = len(vers) if vers else (max(njs) if njs else 1)
    # 버전 토큰이 앨범명과 겹치면 개수가 맞더라도 근거가 미심쩍다. 사람이 볼 수 있게 남긴다.
    overlap = sorted(v for v in vers if any(v in a for a in as_))
    base.update({"versions": n_ver,
                 "needs_review": bool(overlap),
                 "versions_from": {"근거": "버전표기" if vers else ("N종표기" if njs else "단일"),
                                   "앨범명겹침": overlap or None,
                                   "n종_표기": max(njs) if njs else None,
                                   "버전표기": sorted(vers)[:10]},
                 "unit_price": pick["price"],
                 "set_price": sets[0]["price"] if sets else None,
                 "matched_title": pick["title"], "item_id": pick["item_id"],
                 "n_hits": len(hits),
                 "why": f"일치 {len(hits)}건 중 단품 우선 채택"})
    return base


def run(limit: int | None = None, hanteo_only: bool = False) -> dict:
    """**후보는 원천 레코드다**(노트 333 정정).

    원래는 ``chodong_basis_resolved == "hanteo"`` 로 걸렀다. 그 필터는
    **라벨을 고르는 결정**인데 수집 범위까지 정해 버렸다 --- 그래서 앨범
    메타가 한터 79행에만 있고 나머지 94행에는 0% 였다. 노트 326이 그것을
    **풀의 그림자**로 잡았고(표시자가 한터 여부와 99.4% 같다) 노트 332가
    위키에서 같은 한 줄을 고쳤다. 여기가 남은 하나다.

    **축은 라벨을 몰라야 한다.** 초동과 데뷔일이 있으면 후보다.
    """
    recs = [json.loads(f.read_text()) for f in sorted(REC.glob("*.json"))]
    if hanteo_only:
        pool = [r for r in recs if r.get("chodong_basis_resolved") == "hanteo"]
    else:
        pool = [r for r in recs if r.get("chodong") and r.get("debut_date")]
    if limit:
        pool = pool[:limit]
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    print(f"대상 {len(pool)}건 (기수집 {len(prev)}건)")

    ok = 0
    for i, r in enumerate(pool, 1):
        if r["record_id"] in prev and prev[r["record_id"]].get("versions"):
            ok += 1
            continue
        res = resolve(r)
        prev[res["record_id"]] = res
        if res["versions"]:
            ok += 1
            print(f"  [{i:>3}] {res['group'][:14]:<16}{res['versions']}종  "
                  f"{res['unit_price'] or '?'}원  ← {res['matched_title'][:56]}")
        else:
            print(f"  [{i:>3}] {res['group'][:14]:<16}미해결 — {res['why']}")
        if i % 10 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        if i % COOLDOWN_EVERY == 0:
            print(f"    ... {i}건 — 15초 휴식")
            time.sleep(15)
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    print(f"\n해결 {ok}/{len(pool)} ({ok/max(1,len(pool)):.0%})   저장: {OUT}")
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--hanteo-only", action="store_true",
                    help="옛 동작(한터 풀만) --- 재현용")
    a = ap.parse_args()
    run(limit=a.limit, hanteo_only=a.hanteo_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
