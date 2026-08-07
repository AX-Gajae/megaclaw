"""위키백과 일별 조회수를 **오픈 이전 창에서만** 긁는다(노트 149).

노트 148이 남긴 결론은 하나였다 --- 방법 쪽은 다 썼고(짝 섞기 상한
$+$0.0017, 도메인별 신탁 상한 $+$0.0124) 축 쪽은 안 썼다(축 두 개가
$+$0.045). 그리고 검색 축의 덮음이 만화 0\% · 세계애니 0\% · 게임 30\% ·
모바일 41\%다. 만화와 세계애니만 레코드 4,737건 --- 전체의 43\%다.

**왜 위키백과인가.**

① 시점이 깨끗하다. 노트 141이 Kitsu 축을 버린 이유는 그것이 *지금 긁은
   스냅샷*이라 오픈 전에는 존재하지 않는다는 것이었다. 위키백과 조회수는
   **날짜별 시계열**이라 오픈 이전 창만 잘라 쓸 수 있다. 사후가 아니다.
② 언어가 안 막힌다. 네이버 검색은 한국어 제목이 있어야 하고, 만화 ·
   세계애니는 그게 0\%였다. 영문 위키백과는 두 도메인의 ``english'' 제목을
   그대로 받는다.
③ 공짜이고 제한이 느슨하다.

**규약.** 창은 시작일 이전 90일이다. 시작일 당일과 이후는 한 칸도 안 본다.
2015-07 이전은 API 자체가 없으므로 그 이전 작품은 못 잰다(마스크 0).

쓰는 법::

    python3 -m ingest.wiki_views --domain 세계애니 --limit 50
    python3 -m ingest.wiki_views --domain 만화
"""
from __future__ import annotations

import argparse
import json
import threading
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

UA = "sweetspot-world-model/1.0 (alexlee@sweetspot.co.kr) research"
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/state/wiki_views"
TITLES = ROOT / "data/state/wiki_titles.json"
WINDOW = 90            # 오픈 이전 며칠을 보나
API_FROM = date(2015, 7, 1)

# (레코드 파일, 제목 후보, 검색 힌트, 날짜 필드, 위키 언어판)
#
# **언어판은 자료의 성질로 정한다**(노트 150). 세계애니 · 만화 · 게임은
# 영문 제목이 레코드에 있고 영문 위키가 제일 두껍다. 애니 · 웹툰은 제목이
# 한국어라 영문 위키에 안 붙고 한국어 위키가 맞다. 점수를 보고 고르는 것이
# 아니다 --- 제목이 무슨 언어인지가 정한다.
SRC = {
    "세계애니": ("data/state/wanime_records.json", ("english", "title"),
             "anime", "start_date", "en"),
    "만화": ("data/state/manga_records.json", ("title",), "manga",
           "start_date", "en"),
    "게임": ("data/state/game_records.json", ("name",), "video game",
           "release_date", "en"),
    "모바일": ("data/state/mobile_records.json", ("title",), "app",
            "release_date", "en"),
    "애니": ("data/state/anime_records.json", ("title",), "애니메이션",
           "air_quarter", "ko"),
    "웹툰": ("data/state/webtoon_records.json", ("title",), "웹툰",
           "start_date", "ko"),
    # 팝업은 popup_items() 가 메타에서 만든다 --- path 는 안 쓴다
    "팝업": ("", ("title",), "", "start_date", "ko"),
    # 노트 178. 유보 마스크 0 이 100\% 인 세 도메인. 셋 다 제목이 한국어다.
    "도서": ("data/state/book_records.json", ("title",), "책", "pub_date", "ko"),
    "펀딩": ("data/state/funding_records.json", ("title",), "", "start_date", "ko"),
    # 아이돌은 idol_items() 가 축 파일에서 만든다 --- path 는 안 쓴다
    "아이돌": ("", ("title",), "", "start_date", "ko"),
}


def _clean_book(t: str) -> str:
    """``태양 아래 올리브 | Untold Originals (언톨드 오리지널스)  | 김초엽''
    → ``태양 아래 올리브''.

    알라딘 제목은 파이프로 시리즈명과 저자를 이어 붙인다. 통째로 대면
    어떤 문서와도 안 겹치고, 저자만 남기면 저자 문서로 새어 여러 레코드가
    한 문서를 공유한다(노트 150의 함정). **첫 토막만 쓴다.**"""
    t = str(t or "").split("|")[0]
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\s*[-–:]\s*\d+\s*권?\s*$", "", t)
    return re.sub(r"\s+", " ", t).strip()


CLEAN = {"도서": _clean_book}


def _get(url: str, tries: int = 6):
    """429 는 길게 물러선다.

    스레드 여덟에 두 도메인을 동시에 돌렸더니 action API 가 429 를 뱉었다
    (30건에 19건 실패). 조회수 API 는 넉넉한데 ``w/api.php'' 쪽이 빡빡하다.
    한 번에 한 도메인, 일꾼 넷, 그리고 429 에는 지수 후퇴."""
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=25) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None                       # 그 기간에 문서가 없었다
            last = e
            if e.code == 429:
                time.sleep(2.5 * (2 ** i))
                continue
        except Exception as e:
            last = e
        time.sleep(1.2 * (i + 1))
    raise last


def _norm(s: str) -> str:
    """비교용 정규화. **한글을 남긴다**(노트 150).

    처음엔 ``[^a-z0-9]'' 를 다 지웠는데 그러면 한국어 제목이 빈 문자열이
    되어 겹침 점수가 언제나 0이 된다 --- 한국어 위키를 붙이는 순간 제목
    검증이 통째로 무력해진다."""
    s = re.sub(r"\(.*?\)", " ", str(s or "")).lower()
    return re.sub(r"[^0-9a-z\uac00-\ud7a3\u3131-\u318e]+", "", s)


SEQ = re.compile(
    r"\s*(?::|-)?\s*(?:season|part|series|cour)\s*\d+\s*$"
    r"|\s+\d+(?:st|nd|rd|th)\s+(?:season|part)\s*$"
    r"|\s*(?:II|III|IV|V|VI)\s*$", re.I)


# **한국어 속편 표기**(노트 178). SEQ 는 영문만 안다 --- ``season 3'' ·
# ``2nd season'' · 로마숫자. 그런데 애니 도메인의 제목은 한국어이고 속편을
# ``14기'' · ``시즌 2'' · 맨 끝 홑숫자로 쓴다. 그래서 franchise() 가 아무
# 것도 못 자르고 검색 대체로 흘러갔는데, 거기서 겹침 포함(0.8)으로 마침
# *옳은* 프랜차이즈 문서에 붙었다 --- 애니 유보의 포함 매칭 207건이 그것이다.
# 옳게 붙었으니 값은 맞지만 점수가 0.8 이라 품질 문턱을 못 넘는다.
PRE = re.compile(r"^\s*\((?:더빙|자막|재더빙|무삭제|우리말|더빙판|자막판)\)\s*")
KSEQ = re.compile(
    r"\s*(?:제\s*)?\d+\s*기\b.*$"           # 명탐정 코난 14기 / 겁쟁이 페달 4기 GLORY LINE
    r"|\s*시즌\s*\d+\b.*$"
    r"|\s*파이널\s*시즌\b.*$"
    r"|\s*final\s+season\b.*$"
    r"|\s*[Rr]\s*\(\s*\d+\s*기\s*\)\s*$",   # 건어물 여동생! 우마루짱 R (2기)
    re.I)
TAIL = re.compile(r"\s+\d+\s*$")


def franchise(title: str) -> str | None:
    """``Attack on Titan season 3'' → ``Attack on Titan''.
    ``(더빙) 명탐정 코난 14기'' → ``명탐정 코난''.

    속편은 오픈 이전에 자기 문서가 없다 --- 그러면 잴 것이 없어 보이지만,
    우리가 재려는 것은 *그 IP 에 대한 사전 관심*이므로 프랜차이즈 문서가
    오히려 맞는 대상이다(노트 149). 원작 인기를 업고 나오는 2기와 맨몸으로
    나오는 신작을 가르는 축이 된다.

    **순서가 중요하다**(노트 178). 맨 끝 홑숫자를 먼저 떼면 ``Attack on
    Titan season 3'' 이 ``Attack on Titan season'' 이 된다. 영문 규칙과
    한국어 규칙을 먼저 대고, 둘 다 아무것도 못 잘랐을 때만 홑숫자를 본다."""
    t0 = str(title or "").strip()
    t = SEQ.sub("", PRE.sub("", t0))
    t = KSEQ.sub("", t)
    if t == PRE.sub("", t0):
        t = TAIL.sub("", t)
    t = t.strip(" :-")
    return t if t and t.lower() != t0.lower() else None


def direct(title: str, lang: str = "en") -> str | None:
    """제목을 문서 이름으로 바로 대 본다. 넘겨주기(redirect)는 따라간다.

    **왜 검색보다 먼저인가**(노트 149). 검색 API 는 ``Jujutsu Kaisen'' 에
    ``Jujutsu Kaisen (TV series)'' 를 물어다 준다. 그 문서는 애니 발표
    시점에 생겼으므로 오픈 이전 창이 통째로 비어 버린다. 우리가 재려는
    것은 *그 IP 에 대한 사전 관심*이니 맨 제목 문서(대개 원작 · 프랜차이즈)
    가 맞다."""
    u = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "redirects": "1",
        "titles": title, "prop": "pageprops"})
    d = _get(u)
    if not d:
        return None
    for pg in (d.get("query", {}).get("pages") or {}).values():
        # **``invalid'' 는 ``missing'' 이 아니다**(노트 178). 제목에
        # ``<>[]|{}#'' 가 있거나 255바이트를 넘으면 MediaWiki 는 missing 이
        # 아니라 invalid 를 돌려주고 pageid 를 안 준다. 그런데 title 은
        # 넣어 준다 --- 우리가 보낸 그 문자열 그대로다. 그것을 문서 이름으로
        # 받으면 있지도 않은 문서에 붙은 셈이 되고, 더 나쁘게는 프랜차이즈 ·
        # 검색 되돌리기를 건너뛴다. **pageid 를 요구한다.**
        if "missing" in pg or "invalid" in pg or not pg.get("pageid"):
            return None
        if (pg.get("pageprops") or {}).get("disambiguation") is not None:
            return None
        return pg.get("title")
    return None


def resolve(title: str, hint: str, lang: str = "en") -> dict | None:
    """제목 → 영문 위키백과 문서. 겹침 점수를 같이 남겨 감사할 수 있게 한다."""
    p0 = direct(title, lang)
    if p0:
        return {"page": p0, "score": 1.0, "how": "직접"}
    fr = franchise(title)
    if fr:
        p1 = direct(fr, lang)
        if p1:
            return {"page": p1, "score": 0.9, "how": "프랜차이즈"}
    q = f"{title} {hint}".strip()
    u = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "list": "search",
        "srsearch": q, "srlimit": 5})
    d = _get(u)
    if not d:
        return None
    hits = d.get("query", {}).get("search") or []
    if not hits:
        return None
    a, best = _norm(title), None
    for h in hits:
        b = _norm(h["title"])
        if not a or not b:
            continue
        # 한쪽이 다른 쪽을 품으면 좋은 짝으로 본다
        sc = 1.0 if a == b else (0.8 if (a in b or b in a) else 0.0)
        if sc and (best is None or sc > best[1]):
            best = (h["title"], sc)
    if best is None:
        # **아무 것도 안 겹치면 붙이지 않는다**(노트 150). 처음에는 1위를
        # 그냥 썼는데, 그러면 힌트 단어가 이겨서 웹툰 스물다섯 건 중 스물한
        # 건이 ``네이버 웹툰'' 한 문서로 갔다. 모바일은 ``App store'' 와
        # ``WhatsApp'' 으로, 만화는 ``2026 in anime'' 로 갔다. 여러 레코드가
        # 한 문서를 공유하면 그 축은 레코드를 안 재고 날짜만 잰다 ---
        # 자료가 아니라 잡음을 축으로 들이는 것이다.
        return {"page": None, "score": 0.0, "how": "겹침없음"}
    return {"page": best[0], "score": best[1], "how": "검색"}


def views(page: str, start: date, end: date, lang: str = "en") -> list | None:
    t = urllib.parse.quote(page.replace(" ", "_"), safe="")
    u = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
         f"{lang}.wikipedia/all-access/user/{t}/daily/"
         f"{start:%Y%m%d}/{end:%Y%m%d}")
    d = _get(u)
    if d is None:
        return []                                  # 그때는 문서가 없었다
    return [(x["timestamp"][:8], int(x["views"])) for x in d.get("items", [])]


def _one(r, keys, hint, tt, lock, sleep, dkey="start_date", lang="en",
         clean=None):
    """레코드 하나. 스레드에서 돈다."""
    rid = r.get("record_id")
    if not rid:
        return None
    out = CACHE / f"{rid}.json"
    if out.exists():
        return "skip"
    sd = str(r.get(dkey) or "")[:10]
    try:
        d0 = date.fromisoformat(sd)
    except Exception:
        return None
    lo, hi = d0 - timedelta(days=WINDOW), d0 - timedelta(days=1)
    if hi < API_FROM:
        return None
    lo = max(lo, API_FROM)
    title = next((str(r[k]) for k in keys if r.get(k)), None)
    if clean is not None and title:
        title = clean(title)
    if not title:
        return None
    with lock:
        m = tt.get(f"{lang}|{title}")
    if m is None:
        m = resolve(title, hint, lang) or {"page": None, "score": 0.0}
        with lock:
            tt[f"{lang}|{title}"] = m
        time.sleep(sleep)
    if not m.get("page"):
        out.write_text(json.dumps(
            {"record_id": rid, "page": None, "days": [], "n": 0},
            ensure_ascii=False))
        return "fail"
    vs = views(m["page"], lo, hi, lang)
    time.sleep(sleep)
    for f_, tag in ((lambda x: re.sub(r"\s*\(.*?\)\s*$", "", x).strip(),
                     "맨제목"), (franchise, "프랜차이즈")):
        if vs:
            break
        alt_t = f_(m["page"]) or ""
        if not alt_t or alt_t == m["page"]:
            continue
        pg = direct(alt_t, lang)
        time.sleep(sleep)
        if not pg:
            continue
        alt = views(pg, lo, hi, lang)
        time.sleep(sleep)
        if alt:
            m = {**m, "page": pg, "how": (m.get("how") or "") + "→" + tag}
            vs = alt
    out.write_text(json.dumps(
        {"record_id": rid, "page": m["page"], "lang": lang,
         "score": m["score"], "how": m.get("how"), "start": sd, "lo": lo.isoformat(),
         "hi": hi.isoformat(), "days": vs, "n": len(vs)}, ensure_ascii=False))
    return "got" if vs else "empty"


def popup_items():
    """팝업은 레코드 파일이 아니라 메타에서 온다(노트 158).

    다른 도메인은 ``data/records/*.json'' 또는 ``data/market_records/*.json''
    인데 팝업은 두 출처가 섞여 있고 축 파일이 따로다. 대신 메타에 ip 이름과
    날짜가 376건 전부 있다 --- 그걸 쓴다. IP 이름은 한국어이므로 한국어
    위키판이다."""
    import json as _j
    from pathlib import Path as _P
    # **자리표시자 이름은 막는다**(노트 158). ``미상''은 한국어 위키에
    # 실제로 문서가 있어서 정확 일치로 붙는다 --- 노트 150의 ``연애''와
    # 같은 함정이다. 제목 겹침만으로는 일반 명사를 못 거른다.
    BAD = {"미상", "미정", "없음", "기타", "내부", "자체", "unknown", "N/A",
           "비공개", "확인중"}
    meta = _j.loads((ROOT / "data/state/popup_v2_meta.json").read_text())
    out = []
    for m in meta:
        ip, dt = m.get("ip"), m.get("date")
        if not ip or not dt or ip.strip() in BAD or len(ip.strip()) <= 1:
            continue
        out.append({"record_id": m["id"], "title": ip, "start_date": dt})
    return out


def idol_items():
    """아이돌 후보는 **원천 레코드**다(노트 332 정정).

    **닻은 데뷔일이다.** 라벨은 앨범 초동인데 앨범 발매일이 어디에도 없다.
    데뷔일은 앨범보다 반드시 앞서므로 노트 141의 시점 규칙을 통과한다 ---
    다만 데뷔가 오래된 그룹은 창이 낡는다.

    **원래는 ``data/state/idol_axes.json`` 을 읽었다.** 그 파일은
    ``ingest/idol_axes.py`` 가 ``chodong_basis_resolved == "hanteo"`` 로
    거른 79행이다. 그래서 위키가 그 79행만 긁혔고, 노트 326이 그 결과를
    **풀의 그림자**로 잡았다 --- 위키 표시자가 한터 여부와 99.4% 같고,
    기준이 라벨을 0.58 log10 가르므로 그 표시자가 곧 사후 표지가 된다.

    **풀 결정이 수집기에 새겨져 있었다.** 라벨을 고르는 필터였는데 그
    뒤의 수집이 전부 그 결정을 따라갔고, 나중에 필터를 풀려 하니 라벨이
    아니라 축의 결측이 막았다. 그래서 후보 목록을 축 파일이 아니라
    **레코드**에서 만든다 --- 초동과 데뷔일을 둘 다 가진 173건 전부.
    라벨 기준은 여기서 안 본다(축은 라벨을 몰라야 한다).
    """
    rec = ROOT / "data/idol_records"
    if rec.is_dir():
        j = {}
        for f in sorted(rec.glob("*.json")):
            r = json.loads(f.read_text())
            if r.get("chodong") and r.get("debut_date"):
                j[r["record_id"]] = {"group": r.get("group_name"),
                                     "debut_date": r["debut_date"]}
    else:
        j = json.loads((ROOT / "data/state/idol_axes.json").read_text())
    out = []
    for rid, v in j.items():
        g, dt = (v or {}).get("group"), (v or {}).get("debut_date")
        if not g or not dt:
            continue
        # ``방탄소년단 (BTS)'' 처럼 괄호에 영문을 단 것은 앞만 쓴다
        g = re.sub(r"\(.*?\)", " ", str(g))
        g = re.sub(r"\s+", " ", g).strip()
        if len(g) <= 1:
            continue
        out.append({"record_id": rid, "title": g, "start_date": dt})
    return out


def run_mt(domain: str, limit: int | None = None, sleep: float = 0.05,
           workers: int = 8) -> dict:
    """스레드 여덟으로 긁는다.

    한 레코드에 API 를 두 번에서 다섯 번 부르고 한 번이 0.6초라 직렬로는
    레코드당 2~4초다(3,200건이면 세 시간). 병목이 전부 대기이므로 스레드가
    그대로 먹힌다. 예의상 여덟으로 둔다 --- Wikimedia 조회수 API 는 초당
    100까지 받는다."""
    from concurrent.futures import ThreadPoolExecutor
    path, keys, hint, dkey, lang = SRC[domain]
    clean = CLEAN.get(domain)
    if domain == "팝업":
        items = popup_items()
    elif domain == "아이돌":
        items = idol_items()
    else:
        recs = json.load(open(ROOT / path))
        items = list(recs.values()) if isinstance(recs, dict) else recs
    CACHE.mkdir(parents=True, exist_ok=True)
    tt = json.loads(TITLES.read_text()) if TITLES.exists() else {}
    lock = threading.Lock()
    def _ok(r):
        if not r.get("record_id"):
            return False
        if (CACHE / f"{r['record_id']}.json").exists():
            return False
        sd = str(r.get(dkey) or "")[:10]
        try:
            d0 = date.fromisoformat(sd)
        except Exception:
            return False
        # API 가 2015-07 부터라 그 이전 오픈은 창을 못 만든다
        if d0 - timedelta(days=1) < API_FROM:
            return False
        return bool(next((r[k] for k in keys if r.get(k)), None))

    todo = [r for r in items if _ok(r)]
    if limit is not None:
        todo = todo[:limit]
    cnt = {"got": 0, "empty": 0, "fail": 0, "skip": 0}
    done = [0]

    def work(r):
        try:
            k = _one(r, keys, hint, tt, lock, sleep, dkey, lang, clean)
        except Exception as e:
            k = "fail"
            print(f"[{r.get('record_id')}] {type(e).__name__} {e}", flush=True)
        with lock:
            if k in cnt:
                cnt[k] += 1
            done[0] += 1
            if done[0] % 200 == 0:
                TITLES.write_text(json.dumps(tt, ensure_ascii=False))
                print(f"  {domain} {done[0]}/{len(todo)} {cnt}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))
    TITLES.write_text(json.dumps(tt, ensure_ascii=False))
    s = {"도메인": domain, "대상": len(todo), **cnt, "제목캐시": len(tt)}
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return s


def run(domain: str, limit: int | None = None, sleep: float = 0.12) -> dict:
    path, keys, hint, dkey, lang = SRC[domain]
    recs = json.load(open(ROOT / path))
    items = list(recs.values()) if isinstance(recs, dict) else recs
    CACHE.mkdir(parents=True, exist_ok=True)
    tt = json.loads(TITLES.read_text()) if TITLES.exists() else {}
    got = skip = fail = empty = 0
    n = 0
    for r in items:
        rid = r.get("record_id")
        if not rid:
            continue
        out = CACHE / f"{rid}.json"
        if out.exists():
            skip += 1
            continue
        sd = str(r.get(dkey) or "")[:10]
        try:
            d0 = date.fromisoformat(sd)
        except Exception:
            continue
        lo, hi = d0 - timedelta(days=WINDOW), d0 - timedelta(days=1)
        if hi < API_FROM:
            continue                                # API 이전 --- 못 잰다
        lo = max(lo, API_FROM)
        title = next((str(r[k]) for k in keys if r.get(k)), None)
        if not title:
            continue
        if limit is not None and n >= limit:
            break
        n += 1
        try:
            m = tt.get(title)
            if m is None:
                m = resolve(title, hint) or {"page": None, "score": 0.0}
                tt[title] = m
                time.sleep(sleep)
            if not m.get("page"):
                out.write_text(json.dumps(
                    {"record_id": rid, "page": None, "days": [], "n": 0},
                    ensure_ascii=False))
                fail += 1
                continue
            vs = views(m["page"], lo, hi)
            time.sleep(sleep)
            # 괄호 딸린 문서가 오픈 이전에 없었으면 맨 제목으로 한 번 더
            for f_, tag in ((lambda x: re.sub(r"\s*\(.*?\)\s*$", "", x).strip(),
                             "맨제목"),
                            (franchise, "프랜차이즈")):
                if vs:
                    break
                alt_t = f_(m["page"]) or ""
                if not alt_t or alt_t == m["page"]:
                    continue
                pg = direct(alt_t)
                time.sleep(sleep)
                if not pg:
                    continue
                alt = views(pg, lo, hi)
                time.sleep(sleep)
                if alt:
                    m = {**m, "page": pg,
                         "how": (m.get("how") or "") + "→" + tag}
                    vs = alt
            out.write_text(json.dumps(
                {"record_id": rid, "page": m["page"], "score": m["score"],
                 "how": m.get("how"), "start": sd, "lo": lo.isoformat(), "hi": hi.isoformat(),
                 "days": vs, "n": len(vs)}, ensure_ascii=False))
            got += 1
            if not vs:
                empty += 1
        except Exception as e:
            fail += 1
            print(f"[{rid}] {type(e).__name__} {e}", flush=True)
            if fail > 40:
                print("실패가 너무 많다 --- 멈춘다", flush=True)
                break
        if got and got % 100 == 0:
            TITLES.write_text(json.dumps(tt, ensure_ascii=False))
            print(f"  {domain} {got}건 (건너뜀 {skip} 빈창 {empty} 실패 {fail})",
                  flush=True)
    TITLES.write_text(json.dumps(tt, ensure_ascii=False))
    s = {"도메인": domain, "새로": got, "건너뜀": skip, "빈창": empty,
         "실패": fail, "제목캐시": len(tt)}
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="세계애니", choices=sorted(SRC))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--serial", action="store_true")
    a = ap.parse_args()
    if a.serial:
        run(a.domain, a.limit, a.sleep)
    else:
        run_mt(a.domain, a.limit, a.sleep, a.workers)
