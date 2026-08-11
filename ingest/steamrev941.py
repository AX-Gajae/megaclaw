# -*- coding: utf-8 -*-
"""노트 941(탐색) — Steam **리뷰 본문**을 받는다. 🔴 **용량이 아니라 본문이다.**

**왜 이 원천인가.**

`docs/방향.md`(2026-08-12) 가 자를 바꿨다 --- 수집의 자는 이제
**「(상태 s, 액션 a, 결과 o) 삼중쌍을 몇 개 만들 수 있나」**다.
그 자로 보면 이 저장소에 **o(결과) 자리에 놓을 사람의 말이 한 글자도 없다.**

그리고 노트 896 이 「댓글 229h 크롤」을 막았는데, 896 이 잰 것은
**텍스트 용량의 대용값**(위키 문서 존재 이진 · 설명문 글자수)이고
896 자신이 남긴 문장이 이렇다 --- *「주입한 것은 텍스트가 아니라 텍스트
용량의 대용값이다. **본문은 아직 한 번도 안 넣어 봤다**」*.
🔴 **「용량이 중복」과 「본문이 중복」은 다른 문장이다.**

**그리고 `docs/수집계획.md` 의 후보 16개에 댓글·여론이 0건이다**
(`grep -cniE "댓글|여론" docs/수집계획.md` → **0**). 200시간 계획에서 통째로 빠져 있다.

**경로**: `store.steampowered.com/appreviews/<appid>?json=1` --- Steamworks
문서에 공개된 스토어 엔드포인트. **무료 · 키 없음 · 로그인 없음.**
`store.steampowered.com/robots.txt` 를 실제로 받아 읽었고(2026-08-12 · 303바이트),
`Disallow` 는 `/share/ /news/externalpost/ /account/... /login/ /join/ /email/ /widget/`
**일곱뿐**이라 `/appreviews/` 는 걸리지 않는다. 요청 간격 1.2초 · UA 에 연락처.

**받는 것**: 리뷰 **본문**(`review`) · **작성 시각**(`timestamp_created`, unix) ·
추천 여부 · 언어 · 플레이시간 · 도움됨 투표. 🔴 **시각이 있으므로 시간축에 놓인다.**

**조항 59 검사**: ㄱ HTTP 200 · ㄴ JSON 파싱 · ㄷ `success == 1` ·
ㄹ `reviews` 키 존재 · ㅁ 본문이 빈 문자열이 아닌 건수를 따로 센다
(🔴 **「리뷰 100건을 받았다」와 「본문 100개를 받았다」는 다른 수다**).

쓰는 법::

    python3 -m ingest.steamrev941 --pages 2
    python3 -m ingest.steamrev941 --holdout-only --pages 1
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXES = ROOT / "data/state/game_axes.json"
HOLD = ROOT / "runners/out941_holdout.json"
OUTDIR = ROOT / "data/ingest/steam_reviews"

UA = ("sweetspot-world-model/1.0 (research; alexlee@sweetspot.co.kr) "
      "note941 appreviews")
URL = ("https://store.steampowered.com/appreviews/{app}?json=1"
       "&num_per_page=100&filter=recent&language=all&purchase_type=all"
       "&review_type=all&cursor={cur}")
SLEEP = 1.2


def targets(holdout_only: bool = False) -> list:
    """appid 목록. 기본은 게임 축 전량(유보 밖도 받는다).

    🔴 **유보로 안 좁히는 이유**: 새 자(학습쌍)는 판에 안 붙어도 된다.
    옛 자(「유보 3,775 에 붙는 행」)로 좁히면 그 자가 다시 수집을 가둔다.
    """
    keys = list(json.loads(AXES.read_text()))
    if holdout_only:
        h = set(json.loads(HOLD.read_text())["유보키"].get("게임", []))
        keys = [k for k in keys if k in h]
    out = []
    for k in keys:
        a = k.split("-", 1)[1] if "-" in k else ""
        if a.isdigit():
            out.append((k, a))
    return out


def page(app: str, cur: str) -> tuple:
    """(dict, 사유). 성공이면 사유 None."""
    u = URL.format(app=app, cur=urllib.parse.quote(cur, safe=""))
    req = urllib.request.Request(
        u, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                                   # noqa: BLE001
        return None, type(e).__name__
    if code != 200:
        return None, f"HTTP {code}"
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return None, "JSON 아님"
    if d.get("success") != 1:
        return None, f"success={d.get('success')}"
    if "reviews" not in d:
        return None, "reviews 키 없음"
    return d, None


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=2, help="앱마다 최대 페이지")
    ap.add_argument("--holdout-only", action="store_true")
    ap.add_argument("--sleep", type=float, default=SLEEP)
    a = ap.parse_args()

    tg = targets(a.holdout_only)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fp = gzip.open(OUTDIR / "reviews.jsonl.gz", "wt", encoding="utf-8")

    n_req = n_ok = n_bad = 0
    n_rev = n_body = 0
    apps_ok, apps_zero = set(), set()
    why: dict = {}
    lang: dict = {}
    lo, hi = 9 << 40, 0
    for i, (key, app) in enumerate(tg, 1):
        cur, seen = "*", 0
        for _ in range(a.pages):
            n_req += 1
            d, bad = page(app, cur)
            time.sleep(a.sleep)
            if bad:
                n_bad += 1
                why[bad] = why.get(bad, 0) + 1
                break
            n_ok += 1
            rv = d["reviews"]
            if not rv:
                break
            for r in rv:
                body = (r.get("review") or "").strip()
                ts = int(r.get("timestamp_created") or 0)
                n_rev += 1
                if body:
                    n_body += 1
                    lo, hi = min(lo, ts), max(hi, ts)
                    lg = r.get("language") or "?"
                    lang[lg] = lang.get(lg, 0) + 1
                fp.write(json.dumps({
                    "키": key, "appid": app,
                    "id": r.get("recommendationid"),
                    "쓴 시각": ts,
                    "고친 시각": int(r.get("timestamp_updated") or 0),
                    "추천": bool(r.get("voted_up")),
                    "언어": r.get("language"),
                    "도움됨": int(r.get("votes_up") or 0),
                    "가중점수": float(r.get("weighted_vote_score") or 0),
                    "구매": bool(r.get("steam_purchase")),
                    "플레이분": int((r.get("author") or {}).get(
                        "playtime_at_review") or 0),
                    "본문": body,
                }, ensure_ascii=False) + "\n")
                seen += 1
            cur = d.get("cursor") or ""
            if not cur or len(rv) < 100:
                break
        (apps_ok if seen else apps_zero).add(app)
        if i % 50 == 0:
            print(f"  {i}/{len(tg)} req={n_req} 리뷰={n_rev} 본문={n_body} "
                  f"{time.time()-t0:.0f}s", flush=True)
    fp.close()

    def iso(t):
        return time.strftime("%Y-%m-%d", time.gmtime(t)) if t else None

    sz = (OUTDIR / "reviews.jsonl.gz").stat().st_size
    res = {
        "노트": 941, "레인": "탐색",
        "원천": "Steam store appreviews (키 없음 · 로그인 없음)",
        "🔴 무엇을 받았나": "리뷰 **본문** + 작성 시각 — 용량 대용값이 아니다",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "벽시계 초": round(time.time() - t0, 1),
        "대상 앱": len(tg), "요청 수": n_req, "성공": n_ok, "실패": n_bad,
        "🔴 성공+실패 == 요청": n_ok + n_bad == n_req,
        "실패 사유": why,
        "리뷰 행": n_rev, "🔴 본문이 빈 것이 아닌 행": n_body,
        "🔴 리뷰 행 − 본문 행": n_rev - n_body,
        "리뷰가 1건 이상인 앱": len(apps_ok),
        "리뷰가 0건인 앱": len(apps_zero),
        "🔴 앱 합 == 대상": len(apps_ok) + len(apps_zero) == len(tg),
        "본문 날짜 범위": {"첫": iso(lo if hi else 0), "끝": iso(hi)},
        "언어 상위": dict(sorted(lang.items(), key=lambda x: -x[1])[:12]),
        "언어 가짓수": len(lang),
        "파일": str((OUTDIR / "reviews.jsonl.gz").relative_to(ROOT)),
        "파일 바이트": sz,
    }
    (ROOT / "runners/out941_steamrev.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
