"""만화 도메인 **별칭 층** --- AniList 에서 `media_id` 로 별칭을 받아 저장한다.

**왜.** 노트 893 실측: 수확을 가른 것은 인기층이 아니라 **질의어의 언어**였다.

    AniList native(한글)        n=45  중앙값 74   0건 0
    AniList english             n=66  중앙값 30   0건 9
    manga_records.title(로마자) n=72  중앙값  0   0건 49

그리고 `data/state/source_knock.json` 이 이미 적어 뒀다 --- 만화 7,982건이
`media_id` 를 **100%** 갖고 있는데 이 저장소의 수집기는 전부 **제목 문자열
하나**로 조회하고 있었다. 레코드가 이미 가진 열쇠를 안 쓴 것이다.

**설계.**

  · 열쇠는 `media_id`. 제목 문자열 검색을 하지 않는다(그게 지금까지의 병이다).
  · `Page(perPage:50) { media(id_in: [...]) }` --- 7,982 → 약 160요청.
  · `ingest/fanout.py` 위에 얹는다(캐시=재개 · 실패도 `ok:false` 로 기록).
  · 🔴 **예의**: 보수적 간격 + 429 면 `Retry-After` 만큼 물러난다. 차단당하면
    이 문을 잃는다.

🔴 **조항 59 --- 셋을 갈라 적는다.** HTTP 200 이어도 `data.Page.media` 가 비면
'없다'가 아니라 '못 받았다' 일 수 있다. 그래서 배치마다 **요청한 id** 와
**돌아온 id** 를 둘 다 적고, 배치 전체가 빈 경우는 `공백` 으로 따로 표시해
재확인 대상으로 남긴다. 개별 id 가 안 돌아온 것만 `진짜없음` 으로 센다.

사용::

    python3 -m ingest.manga_alias --fetch          # 긁기(재개 가능)
    python3 -m ingest.manga_alias --build          # 캐시 → data/state/manga_alias.json + 회계
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/state/manga_records.json"
OUT = ROOT / "data/state/manga_alias.json"
CACHE = "data/state/cache_manga_alias"

API = "https://graphql.anilist.co"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Content-Type": "application/json", "Accept": "application/json"}

PER = 50          # 배치 크기 --- AniList Page 상한
WORKERS = 1       # 예의: workers/sleep 이 실효 속도다
SLEEP = 3.0       # 실측 --- AniList 잔여 헤더가 30/분을 가리켰다(1요청 후 29).
                  # 상한에 붙이지 않는다. 1워커 × 3초 → 분당 약 15요청.

Q = """
query ($ids: [Int]) {
  Page(page: 1, perPage: 50) {
    media(id_in: $ids, type: MANGA) {
      id
      title { romaji english native }
      synonyms
      countryOfOrigin
      startDate { year month day }
    }
  }
}
"""

# ── 문자 판별 ──────────────────────────────────────────────────────────
# 🔴 "별칭을 얻었다" 와 "**한글** 별칭을 얻었다" 는 다른 수다. native 는 원산국이
#    JP 면 일본어다. 한국 커뮤니티 검색에 쓸 수 있는 것은 한글뿐이다.
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_KANA = re.compile(r"[぀-ゟ゠-ヿ]")
_HAN = re.compile(r"[一-鿿㐀-䶿]")
_LATIN = re.compile(r"[A-Za-z]")


def script_of(s: str) -> str:
    """문자열의 표기 계열. 한글이 하나라도 있으면 한글로 친다(검색어로 쓸 수 있다)."""
    if not s or not s.strip():
        return "빈문자"
    if _HANGUL.search(s):
        return "한글"
    if _KANA.search(s):
        return "일본어"
    if _HAN.search(s):
        return "한자"          # 중국어/일본어 한자 표기 --- 갈라 말하지 않는다
    if _LATIN.search(s):
        return "로마자"
    return "기타"


# ── 수확 ───────────────────────────────────────────────────────────────
def _post(ids: list[int], tries: int = 5) -> dict:
    """배치 하나. 429 면 Retry-After 만큼 물러난다. 끝내 실패하면 예외를 던진다."""
    body = json.dumps({"query": Q, "variables": {"ids": ids}}).encode()
    last = ""
    for attempt in range(tries):
        req = urllib.request.Request(API, data=body, headers=UA, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read().decode("utf-8")
                rem = r.headers.get("X-RateLimit-Remaining")
            d = json.loads(raw)
            # GraphQL 은 200 안에 errors 를 담는다 --- 성공 신호가 성공이 아니다(조항 59)
            if d.get("errors") and not (d.get("data") or {}).get("Page"):
                last = f"graphql: {str(d['errors'])[:160]}"
                time.sleep(5 * (attempt + 1))
                continue
            out = {"요청": ids, "응답": d.get("data", {}).get("Page", {}).get("media") or [],
                   "graphql_errors": d.get("errors")}
            if rem is not None:
                out["남은요청"] = rem
                try:                       # 잔여가 바닥이면 스스로 쉰다
                    if int(rem) <= 5:
                        time.sleep(20)
                except ValueError:
                    pass
            return out
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:              # 🔴 예의 --- 물러나서 기다린다
                wait = e.headers.get("Retry-After")
                try:
                    wait = int(wait)
                except (TypeError, ValueError):
                    wait = 60
                time.sleep(min(max(wait + 2, 5), 120))
                continue
            time.sleep(5 * (attempt + 1))
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
            last = f"{type(e).__name__}: {e}"[:160]
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{tries}회 실패 · 마지막={last}")


def batches(ids: list[int], per: int = PER) -> list[dict]:
    return [{"i": i // per, "ids": ids[i:i + per]} for i in range(0, len(ids), per)]


def fetch(limit: int | None = None, retry_failed: bool = False) -> dict:
    from ingest.fanout import fanout
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    ids = sorted({int(v["media_id"]) for v in recs.values() if v.get("media_id")})
    bs = batches(ids)
    print(f"레코드 {len(recs)} · media_id {len(ids)} · 배치 {len(bs)}", flush=True)
    return fanout(bs, key=lambda b: "b%04d" % b["i"], cache=CACHE,
                  work=lambda b: _post(b["ids"]), workers=WORKERS, sleep=SLEEP,
                  limit=limit, retry_failed=retry_failed, report_every=10)


# ── 조립 + 회계 ────────────────────────────────────────────────────────
def build() -> dict:
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    by_mid = {}
    for rid, v in recs.items():
        if v.get("media_id"):
            by_mid[int(v["media_id"])] = rid

    all_ids = sorted(by_mid)
    plan = {"b%04d" % b["i"]: [int(x) for x in b["ids"]] for b in batches(all_ids)}

    got: dict[int, dict] = {}
    cdir = ROOT / CACHE
    batch_ok = batch_bad = batch_blank = 0
    fail_reason = Counter()
    asked: set[int] = set()        # 응답이 실제로 온 배치의 id 만
    unreached: set[int] = set()    # 실패·빈 배치·아예 안 긁은 배치의 id
    gql_partial = 0
    seen_keys = set()
    for p in sorted(cdir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        k = p.stem
        seen_keys.add(k)
        req = [int(x) for x in d.get("요청", [])] or plan.get(k, [])
        if not d.get("ok", True):
            batch_bad += 1
            fail_reason[str(d.get("사유", ""))[:60]] += 1
            unreached.update(req)
            continue
        media = d.get("응답") or []
        if d.get("graphql_errors"):
            gql_partial += 1
        if req and not media:
            # 🔴 200 인데 빈 배치 --- '없다'가 아니라 '못 받았다' 일 수 있다
            batch_blank += 1
            unreached.update(req)
            continue
        batch_ok += 1
        asked.update(req)
        for m in media:
            got[int(m["id"])] = m
    for k, req in plan.items():     # 아예 안 긁힌 배치도 '못 받았다' 다
        if k not in seen_keys:
            unreached.update(req)

    # ── 레코드별 별칭 조립 ──
    out: dict[str, dict] = {}
    n_native = n_native_hangul = 0
    n_syn = 0
    n_any_hangul = 0
    n_zero_alias = 0
    country = Counter()
    native_script = Counter()
    hangul_source = Counter()
    n_english = n_romaji = 0
    per_country_hangul = Counter()
    per_country_n = Counter()

    for mid, m in got.items():
        rid = by_mid.get(mid)
        if rid is None:
            continue
        t = m.get("title") or {}
        aliases = []          # (문자열, 출처필드, 표기계열)
        seen = set()

        def add(s, field):
            if not s or not str(s).strip():
                return
            s = str(s).strip()
            if s in seen:
                return
            seen.add(s)
            aliases.append({"값": s, "출처": field, "표기": script_of(s)})

        add(t.get("native"), "title.native")
        add(t.get("romaji"), "title.romaji")
        add(t.get("english"), "title.english")
        for s in (m.get("synonyms") or []):
            add(s, "synonyms")

        co = m.get("countryOfOrigin")
        sd = m.get("startDate") or {}
        start = None
        if sd.get("year"):
            start = "%04d-%02d-%02d" % (sd["year"], sd.get("month") or 1, sd.get("day") or 1)

        han = [a for a in aliases if a["표기"] == "한글"]
        out[rid] = {"media_id": mid, "국가": co, "시작": start,
                    "별칭": aliases, "n별칭": len(aliases), "n한글": len(han)}

        # 회계
        country[co or "없음"] += 1
        per_country_n[co or "없음"] += 1
        if t.get("native"):
            n_native += 1
            sc = script_of(t["native"])
            native_script[sc] += 1
            if sc == "한글":
                n_native_hangul += 1
        if t.get("english"):
            n_english += 1
        if t.get("romaji"):
            n_romaji += 1
        if m.get("synonyms"):
            n_syn += 1
        if han:
            n_any_hangul += 1
            per_country_hangul[co or "없음"] += 1
            for f in sorted({a["출처"] for a in han}):
                hangul_source[f] += 1
        if not aliases:
            n_zero_alias += 1

    n_rec = len(recs)
    n_got = len(out)
    missing_ids = sorted(asked - set(got))          # 요청했는데 안 돌아온 개별 id
    pct = lambda a, b: round(100.0 * a / b, 1) if b else None

    # ── 별칭 개수 분포 ──
    import statistics
    n_alias = sorted(v["n별칭"] for v in out.values()) or [0]
    n_han = sorted(v["n한글"] for v in out.values()) or [0]

    # ── 위키 적용 구간과의 교차 ─────────────────────────────────────────
    # `ingest/wiki_views.py` 는 `API_FROM=2015-07-01` 이라 그 이전 시작작은
    # 창을 못 만든다(마스크 0). 🔴 그런데 **시도 가능**과 **실제 시도**는 다른 수다.
    from datetime import date, timedelta
    API_FROM = date(2015, 7, 1)
    eligible = set()
    for rid, v in recs.items():
        try:
            d0 = date.fromisoformat(str(v.get("start_date"))[:10])
        except Exception:
            continue
        if d0 - timedelta(days=1) >= API_FROM:
            eligible.add(rid)
    wdir = ROOT / "data/state/wiki_views"
    tried = {p.stem for p in wdir.glob("MG-*.json")} if wdir.is_dir() else set()
    hanset = {rid for rid, v in out.items() if v["n한글"] > 0}

    audit = {
        "잰 때": time.strftime("%Y-%m-%d"),
        "분모": {"만화 레코드": n_rec, "media_id 보유": len(by_mid),
                 "보유율": pct(len(by_mid), n_rec)},
        "요청 회계(배치)": {
            "배치 총": batch_ok + batch_bad + batch_blank,
            "성공": batch_ok, "실패": batch_bad,
            "🔴 200인데 빈 배치(=못 받았다일 수 있다)": batch_blank,
            "graphql errors 동반": gql_partial,
            "실패 사유": dict(fail_reason.most_common(5)),
        },
        "🔴 셋으로 갈라 센 것(조항 59)": {
            "① 받았다": n_got,
            "② 못 받았다(배치 실패·200인데 빈 배치·미수확)": len(unreached),
            "③ 진짜 없다(요청했는데 개별로 안 돌아옴)": len(missing_ids),
            "③ 예시": missing_ids[:10],
        },
        "필드 보유율(분모=받은 레코드 %d)" % n_got: {
            "native": {"n": n_native, "%": pct(n_native, n_got)},
            "romaji": {"n": n_romaji, "%": pct(n_romaji, n_got)},
            "english": {"n": n_english, "%": pct(n_english, n_got)},
            "synonyms": {"n": n_syn, "%": pct(n_syn, n_got)},
        },
        "🔴 native 의 표기 계열(갈라 세라 --- JP 면 일본어다)": dict(native_script.most_common()),
        "🔴 한글 별칭 획득": {
            "레코드 수": n_any_hangul,
            "분모=받은 레코드": {"n": n_got, "%": pct(n_any_hangul, n_got)},
            "분모=만화 전량": {"n": n_rec, "%": pct(n_any_hangul, n_rec)},
            "한글이 나온 출처 필드(중복 셈)": dict(hangul_source.most_common()),
        },
        "원산국 분포(받은 레코드)": dict(country.most_common()),
        "원산국별 한글 별칭률": {c: {"전체": per_country_n[c], "한글": per_country_hangul.get(c, 0),
                                     "%": pct(per_country_hangul.get(c, 0), per_country_n[c])}
                                 for c, _ in country.most_common()},
        "별칭 0개 레코드": n_zero_alias,
        "별칭 개수": {"중앙값": statistics.median(n_alias),
                      "평균": round(sum(n_alias) / len(n_alias), 2),
                      "최소": n_alias[0], "최대": n_alias[-1],
                      "한글 별칭 개수 중앙값": statistics.median(n_han),
                      "한글 2개 이상": sum(1 for x in n_han if x >= 2)},
        "🔴 위키 적용 구간 교차(분모를 셋으로 갈라라)": {
            "무엇": "wiki_views 는 API_FROM=2015-07-01 이라 그 이전 시작작은 창을 못 만든다. "
                    "그런데 **시도 가능**과 **실제 시도**는 다른 수다 --- 노크가 이 둘을 합쳐 적었다.",
            "① 창이 구조적으로 안 서는 구간(2015-07 이전)": {
                "n": n_rec - len(eligible), "%": pct(n_rec - len(eligible), n_rec),
                "그 중 한글 별칭": len(hanset - eligible)},
            "② 창은 서는데 아직 안 돌린 구간": {
                "n": len(eligible - tried), "%": pct(len(eligible - tried), n_rec)},
            "③ 실제로 위키를 시도한 구간(cache_MG 파일 수)": {
                "n": len(tried), "%": pct(len(tried), n_rec),
                "그 중 한글 별칭": len(hanset & tried),
                "한글률": pct(len(hanset & tried), len(tried))},
            "창이 서는 구간 전체(①의 여집합)": {
                "n": len(eligible), "그 중 한글 별칭": len(hanset & eligible),
                "한글률": pct(len(hanset & eligible), len(eligible))},
            "🔴 그러므로": "노크의 '만화의 80.6% 는 별칭을 채워도 위키로 못 잰다' 는 과장이다 --- "
                           "구조적으로 못 재는 것은 ① 뿐이고 ② 는 **안 돌린 것**이다.",
        },
    }

    doc = {
        "무엇": "만화 도메인 별칭 층 --- AniList 를 media_id 로 조회해 받은 별칭(레코드 id → 별칭 목록·출처 필드·원산국).",
        "왜": "노트 893 --- 수확을 가른 것은 인기층이 아니라 질의어의 언어였다. "
              "그런데 이 저장소의 만화 수집기는 로마자 제목 하나로만 조회하고 있었다.",
        "🔴 이 파일은 판정이 아니다": "별칭을 **저장**한 것까지다. 별칭이 수확을 올리는지는 다음 사이클의 사전등록 대상이다.",
        "회계": audit,
        "별칭": out,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=1), flush=True)
    return audit


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retry-failed", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch(limit=a.limit, retry_failed=a.retry_failed)
    if a.build or not a.fetch:
        build()
