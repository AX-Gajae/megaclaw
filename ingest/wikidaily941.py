# -*- coding: utf-8 -*-
"""노트 941(탐색) — 위키백과 **일별 조회수 전 구간**을 받는다.

🔴 **왜 새 원천인가 --- 기존 수집기가 시간축을 스스로 잘라 버린다.**

``ingest/wiki_views.py`` 의 첫 문단이 규약을 이렇게 적어 두었다:

    **창은 시작일 이전 90일이다. 시작일 당일과 이후는 한 칸도 안 본다.**

그 규약은 옳다 --- 그것이 막는 것은 **누출**이다. 그런데 그 규약 때문에
이 저장소에는 **개봉/발매 이후의 일별 관심 곡선이 한 칸도 없다.**
``docs/목표.md`` 의 출력 ③(*"언제 어떤 불특정 이벤트가 발생할지"*)이 0 인데,
③ 을 재려면 **사건이 실제로 언제 터졌는지**가 있어야 하고 그것은
**시작일 이후**에만 있다. 즉 지금 저장소가 가진 위키 자료로는 ③ 을
원리상 못 잰다.

**이 모듈은 그 구간을 받는다.** 누출 문제는 *받는 쪽*이 아니라 *쓰는 쪽*에서
푼다 --- 받은 계열에는 날짜가 그대로 붙어 있으므로 어느 창을 쓸지는 나중에
자르면 된다. 🔴 **그러나 이 파일은 판에 안 붙인다**(탐색 레인 · 판정 없음).

**경로**: Wikimedia REST ``metrics/pageviews/per-article`` --- 무료 · 키 없음 ·
로그인 없음. ``wikimedia.org/robots.txt`` 는 404(선언 없음)이고, 이 호스트는
분석용 공개 API 다. 요청 간격 1.1초 · User-Agent 에 연락처를 밝힌다.

**대상**: ``runners/out941_holdout.json`` 의 유보 3,775 중,
``data/state/wiki_views/<record_id>.json`` 이 **이미 문서를 해결해 둔 것**만.
🔴 **제목 해결을 다시 하지 않는다** --- 그것은 이 사이클의 일이 아니고,
다시 하면 옛 해결과 갈려서 두 벌이 생긴다.

**조항 59 검사**(파일마다):
  ㄱ HTTP 200 · ㄴ JSON 파싱 · ㄷ ``items`` 키 존재 · ㄹ 항목 ≥ 1 ·
  ㅁ 날짜가 오름차순 · ㅂ ``views`` 가 전부 정수 ≥ 0
셋 중 하나라도 깨지면 **그 개체를 실패로 세고 사유를 값으로 적는다**(0 이 아니다).

쓰는 법::

    python3 -m ingest.wikidaily941            # 전량
    python3 -m ingest.wikidaily941 --limit 20 # 맛보기
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / "runners/out941_holdout.json"
VIEWS = ROOT / "data/state/wiki_views"
OUTDIR = ROOT / "data/ingest/wiki_daily"

UA = ("sweetspot-world-model/1.0 (research; alexlee@sweetspot.co.kr) "
      "note941 pageviews")
API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "{lang}.wikipedia/all-access/all-agents/{title}/daily/{lo}/{hi}")
SLEEP = 1.1
START = "20150701"          # API 개시일. 이전은 원천에 없다.

#: 레코드 접두사 → (도메인, 기본 언어판). 언어판은 ``ingest.wiki_views.SRC``
#: 가 정한 것과 같다 --- 제목이 무슨 언어인지가 정하지 점수가 아니다.
#: 🔴 ``MKT``(시장팝업)는 SRC 에 없다. 한국 전통시장 팝업이라 ``ko`` 로 둔다.
#: 캐시 항목에 ``lang`` 이 적혀 있으면 **그것이 이긴다**.
PREFIX = {
    "AN": ("애니", "ko"), "BOOK": ("도서", "ko"), "FUND": ("펀딩", "ko"),
    "GAME": ("게임", "en"), "IDOL": ("아이돌", "ko"), "MB": ("모바일", "en"),
    "MG": ("만화", "en"), "MKT": ("시장팝업", "ko"), "MKT2": ("시장팝업", "ko"),
    "WA": ("세계애니", "en"), "WT": ("웹툰", "ko"),
}
POPUP_PREFIX = ("RCG", "RCP", "RIP", "ROP", "RTP", "RXP")   # 팝업 · ko


def _dt(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _lang_of(rid: str, cached: dict) -> str:
    if cached.get("lang"):
        return str(cached["lang"])
    head = rid.split("-")[0]
    if head in PREFIX:
        return PREFIX[head][1]
    return "ko"


def targets(limit: int | None = None) -> list:
    """(도메인, record_id, 문서, 언어, 시작일) --- 유보 안에서만."""
    hold = json.loads(HOLD.read_text())["유보키"]
    out = []
    for dom, keys in sorted(hold.items()):
        for k in keys:
            p = VIEWS / f"{k}.json"
            if not p.exists():
                continue
            try:
                c = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if not c.get("page"):
                continue
            out.append({"도메인": dom, "키": k, "문서": c["page"],
                        "언어": _lang_of(k, c), "시작일": c.get("start")})
    if limit:
        out = out[:limit]
    return out


def fetch(lang: str, title: str, hi: str) -> tuple:
    """(항목, 사유). 성공이면 사유는 None."""
    url = API.format(lang=lang, title=urllib.parse.quote(title, safe=""),
                     lo=START, hi=hi)
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=90)
        code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                                   # noqa: BLE001
        return None, type(e).__name__
    if code != 200:                                          # ㄱ
        return None, f"HTTP {code}"
    try:                                                     # ㄴ
        d = json.loads(body)
    except json.JSONDecodeError:
        return None, "JSON 아님"
    if "items" not in d:                                     # ㄷ
        return None, "items 키 없음"
    it = d["items"]
    if not it:                                               # ㄹ
        return None, "항목 0"
    days = [(str(x["timestamp"])[:8], int(x["views"])) for x in it]
    if any(b < a for a, b in zip([x[0] for x in days], [x[0] for x in days][1:])):
        return None, "날짜 역순"                              # ㅁ
    if any(v < 0 for _, v in days):                          # ㅂ
        return None, "음수 조회수"
    return days, None


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=SLEEP)
    a = ap.parse_args()

    hi = (date.today() - timedelta(days=2)).strftime("%Y%m%d")
    tg = targets(a.limit)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    fh, per = {}, {}
    n_req = n_ok = n_bad = 0
    n_gap = 0
    rows = 0
    why: dict = {}
    lo_all, hi_all = "99999999", "00000000"
    for i, t in enumerate(tg, 1):
        n_req += 1
        days, bad = fetch(t["언어"], t["문서"], hi)
        if bad:
            n_bad += 1
            why[bad] = why.get(bad, 0) + 1
            per.setdefault(t["도메인"], {"개체": 0, "실패": 0, "행": 0})["실패"] += 1
        else:
            n_ok += 1
            rows += len(days)
            if len(days) != (_dt(days[-1][0]) - _dt(days[0][0])).days + 1:
                n_gap += 1
            lo_all = min(lo_all, days[0][0])
            hi_all = max(hi_all, days[-1][0])
            d = t["도메인"]
            if d not in fh:
                # 🔴 **952 수리 --- 초판은 최종 파일을 바로 `"wt"` 로 열었다.**
                #
                # `"wt"` 는 **여는 순간 자른다**. 그리고 이 러너는 손잡이를
                # **43분 내내 열어 둔 채** 마지막에야 닫는다. 그 사이:
                #   ① 파일은 끝 표시가 없는 **깨진 gzip** 이라 아무도 못 읽는다
                #   ② 러너가 중간에 죽으면 그 도메인 자료는 **사라진다**
                #      (백업이 아니라 원본을 잘라 놓았으므로)
                #
                # 실측(2026-08-12): 이 러너가 도는 동안 `ingest.collect` 가
                # `wiki_daily` 를 재서 **「무성장 · 델타 -140」**을 찍었다. 자료는
                # 하나도 안 없어졌고(810 → 812) 깨진 파일 넷을 0 으로 센 것이었다.
                # 🔴 **자를 고쳤지만 유령을 만든 쪽은 이 줄이다.**
                #
                # 그래서 **`.part` 에 쓰고 마지막에 갈아 끼운다**(같은 파일계라
                # `os.replace` 가 원자적이다). 러너가 죽으면 `.part` 만 남고
                # **옛 파일은 멀쩡히 살아 있다.**
                fh[d] = gzip.open(OUTDIR / f"{d}.jsonl.gz.part", "wt", encoding="utf-8")
            fh[d].write(json.dumps({
                "키": t["키"], "도메인": d, "문서": t["문서"], "언어": t["언어"],
                "시작일": t["시작일"], "첫날": days[0][0], "끝날": days[-1][0],
                "일수": len(days),
                # 🔴 **날짜를 같이 적는다.** 원천이 자료 없는 날을 **빠뜨려서**
                # 준다(실측: `사장님이 美쳤어요` 는 항목 1,858 인데 첫날~끝날
                # 폭이 3,036 --- 1,178일이 빠져 있다). 첫날부터 하루씩 채우는
                # 압축 저장은 그 순간 **날짜가 통째로 밀린다**. 밀린 계열은
                # 예외를 안 내고 숫자만 틀리므로(조항 59) 날짜를 병기한다.
                "날짜": [int(d0) for d0, _ in days],
                "조회수": [v for _, v in days],
                "🔴 연속인가": len(days) == (
                    _dt(days[-1][0]) - _dt(days[0][0])).days + 1,
            }, ensure_ascii=False) + "\n")
            s = per.setdefault(d, {"개체": 0, "실패": 0, "행": 0})
            s["개체"] += 1
            s["행"] += len(days)
        if i % 50 == 0:
            print(f"  {i}/{len(tg)} ok={n_ok} bad={n_bad} rows={rows} "
                  f"{time.time()-t0:.0f}s", flush=True)
        time.sleep(a.sleep)
    for f in fh.values():
        f.close()
    # 🔴 952 --- 다 쓰고 **한 번에** 갈아 끼운다. 이 줄 전까지 옛 파일은 그대로다.
    swapped = []
    for d in fh:
        part = OUTDIR / f"{d}.jsonl.gz.part"
        if part.exists():
            os.replace(str(part), str(OUTDIR / f"{d}.jsonl.gz"))
            swapped.append(d)

    size = {p.name: p.stat().st_size for p in sorted(OUTDIR.glob("*.jsonl.gz"))}
    res = {
        "노트": 941, "레인": "탐색", "원천": "Wikimedia REST pageviews per-article",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "벽시계 초": round(time.time() - t0, 1),
        "요청 수": n_req, "성공": n_ok, "실패": n_bad,
        "🔴 성공+실패 == 요청": n_ok + n_bad == n_req,
        "실패 사유": why,
        "행(개체×일) 합": rows,
        "🔴 날짜에 구멍이 있는 개체": n_gap,
        "🔴 구멍이 왜 중요한가": (
            "원천이 자료 없는 날을 빠뜨려 준다. 첫날부터 하루씩 채우는 압축 "
            "저장은 그 순간 날짜가 밀리고, 밀린 계열은 예외 없이 숫자만 틀린다. "
            "그래서 이 파일은 날짜를 병기한다(초판은 안 그랬고 그것이 결함이었다)."),
        "날짜 범위": {"첫날": lo_all, "끝날": hi_all} if n_ok else None,
        "요청 상한 hi": hi,
        "도메인별": per,
        "파일 크기(바이트)": size, "파일 크기 합": sum(size.values()),
        "출력 디렉터리": str(OUTDIR.relative_to(ROOT)),
    }
    (ROOT / "runners/out941_wikidaily.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "도메인별"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
