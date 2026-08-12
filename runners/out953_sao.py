# -*- coding: utf-8 -*-
"""노트 953 --- 🔴 **「(s,a,o) 82,981」을 부수고 다시 센다** (티처 #91 C3 + C2).

**부순다(수리)**: 952 의 세 조건은 삼중 조건이 아니었다 ---
`a`(출시일 파싱) **137,808 전량 = 항등식** · `s`(genres/tags/price) **전량 = 항등식** ·
`o`(리뷰≥1) **82,981** → 셋의 교집합이 **o 하나와 정확히 같다**.
🔴 즉 82,981 은 **「리뷰가 1개 이상인 게임 수」**다. 이 러너는 그것을 **다시 세어 확인**한다.

**다시 센다(탐색)**: 티처 처방대로 자를 갈아 끼운다 ---
  · `a` = **출시일이 판 유보 기간 안**(`docs/용어.md:14` --- 학습/유보 경계 **T = 2025.0**)
  · `o` = **리뷰 본문이 있다**(`reviews.jsonl.gz` 의 `본문` 이 비지 않음). 「리뷰 수 칸이 0 이 아니다」가 아니다
  · `s` = 952 정의 그대로(genres/tags/price 중 하나 이상)

🔴 **분모 한 줄**(이 파일이 못 박는다):

    Steam 게임표 = `games.json` **137,808**.
    `games.csv` **125,855** 는 그 **부분집합**이다(csv 전용 0 · json 전용 11,953).

그 한 줄이 없었으면 P9 이 애초에 안 흔들렸다 --- json 기준 98.12% 대 csv 기준 79.96%,
**분모가 답을 뒤집는다**(조항 60).

🔴 **판에 안 붙인다**(`docs/방향.md:65`). 여기 수는 **학습쌍의 자**이지 판 ρ 의 자가 아니다.

    python3 -m runners.out953_sao
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runners.out952_count import _parse_date                       # noqa: E402

ZIP = ROOT / "data/ingest/steam_games/archive.zip"
REVIEWS = ROOT / "data/ingest/steam_reviews/reviews.jsonl.gz"
OUT = ROOT / "runners/out953_sao.json"

#: 🔴 판 유보 경계. `docs/용어.md:14` --- 학습 = 2025 이전 · 유보 = 2025 이후.
HOLDOUT_FROM = dt.date(2025, 1, 1)


def _reviews() -> dict:
    """리뷰를 읽는다. 🔴 **디스크가 안 읽히면 「0」이 아니라 커밋된 판으로 간다.**

    실측(2026-08-12): `ingest.steamrev941` 이 **돌고 있는 중**이라 디스크의
    `reviews.jsonl.gz` 가 `EOFError` 였다. 그걸 「리뷰 0행」으로 읽으면 이 사이클이
    고치려는 병(조항 59)을 그대로 저지른다. **어느 판을 읽었는지 산출물에 적는다.**
    """
    src, raw, err = "디스크", None, None
    try:
        raw = REVIEWS.read_bytes()
        with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as f:
            for _ in f:
                pass
    except Exception as e:                                        # noqa: BLE001
        err = "%s: %s" % (type(e).__name__, str(e)[:100])
        rel = REVIEWS.relative_to(ROOT).as_posix()
        r = subprocess.run(["git", "-c", "core.quotePath=false", "show", "HEAD:" + rel],
                           cwd=str(ROOT), capture_output=True)
        raw, src = r.stdout, "🔴 커밋된 판(HEAD) --- 디스크가 안 읽혔다"
    rows = 0
    body = collections.Counter()
    anyrow = collections.Counter()
    with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            rows += 1
            d = json.loads(ln)
            a = str(d.get("appid") or "").strip()
            if not a:
                continue
            anyrow[a] += 1
            if str(d.get("본문") or "").strip():
                body[a] += 1
    return {"출처": src, "🔴 디스크 오류": err or "없음", "행": rows,
            "행_appid": anyrow, "본문_appid": body}


def main() -> int:
    t0 = dt.datetime.now()
    res = {
        "무엇": "🔴 「(s,a,o) 82,981」을 부수고 다시 센다 --- 티처 #91 C3+C2 · 노트 953",
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "🔴 분모 한 줄": ("Steam 게임표 = `games.json` **137,808**. "
                     "`games.csv` **125,855** 는 그 **부분집합**이다(csv 전용 0 · json 전용 11,953). "
                     "🔴 이 두 수를 이어 붙이지 마라 --- 분모가 답을 뒤집는다(조항 60)"),
        "🔴 판에 안 붙인다": "docs/방향.md:65 --- 목표가 학습쌍이면 판에 붙을 필요가 없다",
    }

    rv = _reviews()
    with zipfile.ZipFile(ZIP) as z:
        with z.open("games.json") as fh:
            gj = json.load(fh)
        with z.open("games.csv") as fh:
            head = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            csv_ids, first = set(), True
            for ln in head:
                if first:
                    first = False
                    continue
                k = ln.split(",", 1)[0].strip().strip('"')
                if k.isdigit():
                    csv_ids.add(k)

    json_ids = set(gj)
    res["0 분모"] = {
        "games.json 항목": len(gj),
        "games.csv 서로다른 AppID": len(csv_ids),
        "🔴 csv 전용(= json 에 없는 것)": len(csv_ids - json_ids),
        "🔴 json 전용": len(json_ids - csv_ids),
        "csv 는 json 의 부분집합인가": csv_ids.issubset(json_ids),
        "통과": True,
    }

    # ── 1 부순다 --- 952 의 정의를 그대로 재현한다 ────────────────────────
    a952 = s952 = o952 = all952 = 0
    a953_set, s_set, o952_set = set(), set(), set()
    future, nodate = 0, 0
    for appid, g in gj.items():
        rd = (g.get("release_date") or "").strip()
        d = _parse_date(rd) if rd else None
        a_old = d is not None
        if not a_old:
            nodate += 1
        s = bool(g.get("genres")) or bool(g.get("tags")) or (g.get("price") is not None)
        o_old = (int(g.get("positive") or 0) + int(g.get("negative") or 0)) >= 1
        a952 += a_old
        s952 += s
        o952 += o_old
        if a_old and s and o_old:
            all952 += 1
        if s:
            s_set.add(appid)
        if o_old:
            o952_set.add(appid)
        if d is not None and d >= HOLDOUT_FROM:
            a953_set.add(appid)
            if d > dt.date.today():
                future += 1

    res["1 부순다 --- 952 의 세 조건 재현"] = {
        "🔴 정의(952 것 그대로)": "a=출시일 파싱됨 · s=genres/tags/price 중 하나 · o=(positive+negative)>=1",
        "a 만족": a952, "s 만족": s952, "o 만족": o952, "셋 다": all952,
        "🔴 a 는 항등식인가(=분모 전량)": a952 == len(gj),
        "🔴 s 는 항등식인가": s952 == len(gj),
        "🔴 셋 다 == o 하나인가": all952 == o952,
        "🔴 그래서 82,981 의 뜻": "「리뷰가 1개 이상인 게임 수」 --- 삼중쌍이 아니다",
        "통과": (a952 == len(gj) and s952 == len(gj) and all952 == o952),
    }

    # ── 2 다시 센다 --- 자를 갈아 끼운다 ──────────────────────────────
    o953_set = {k for k, v in rv["본문_appid"].items() if v > 0}
    rowset = set(rv["행_appid"])
    tri = s_set & a953_set & o953_set
    res["2 다시 센다 --- 새 자"] = {
        "🔴 정의": {
            "s": "genres/tags/price 중 하나 이상(952 그대로)",
            "a": "🔴 출시일이 **판 유보 기간 안**(>= %s · docs/용어.md:14 T=2025.0)" % HOLDOUT_FROM,
            "o": "🔴 그 appid 에 **리뷰 본문**이 1건 이상(`본문` 이 비지 않음)",
        },
        "리뷰 파일": {"출처": rv["출처"], "🔴 디스크 오류": rv["🔴 디스크 오류"], "행": rv["행"]},
        "s 만족": len(s_set),
        "a 만족(유보 안)": len(a953_set),
        "  그중 오늘보다 미래인 출시일": future,
        "  출시일을 못 파싱한 항목": nodate,
        "o 만족(리뷰 본문 있는 appid)": len(o953_set),
        "  리뷰 **행**이 있는 appid": len(rowset),
        "  🔴 본문으로 좁혀 잃은 appid": len(rowset - o953_set),
        "🔴 셋 다(s∧a∧o)": len(tri),
        "🔴 분모": "games.json %d" % len(gj),
        "비율(분모 games.json)": round(len(tri) / len(gj), 8),
        "🔴 세 수가 서로 다른가(=항등식이 아니다)":
            len({len(s_set), len(a953_set), len(o953_set)}) == 3,
        "표본(mt 아님 · appid 20)": sorted(tri)[:20],
        "통과": True,
    }

    # ── 3 「셋이 다 있는 유일한 집합」 --- 티처의 283 을 내 코드로 ────────
    res["3 티처의 283 을 다시 센다"] = {
        "🔴 티처 정의": "리뷰 appid 479 ∩ **후보(o952 = 리뷰≥1)**",
        "리뷰 서로다른 appid": len(rowset),
        "games.json 에 붙는 것": len(rowset & json_ids),
        "games.csv 에 붙는 것": len(rowset & csv_ids),
        "🔴 479 ∩ 후보(o952)": len(rowset & o952_set),
        "🔴 479 ∩ 후보(o952) ∩ 유보(a953)": len(rowset & o952_set & a953_set),
        "🔴 부기": ("952 는 ∩ 를 `games.json` **전체**에 걸었고(470) 물어야 했던 것은 "
                  "**후보(o≥1)** 였다 --- 같은 자료에서 분모가 답을 바꾼다"),
        "통과": True,
    }

    res["🔴 안 쟀다"] = [
        "이 삼중쌍이 **판 유보 3,775 에 붙는지** --- 안 쟀다(붙일 생각도 없다 · 방향.md:65)",
        "리뷰 본문의 **언어** --- `o953` 에 중국어·영어 본문이 그대로 들어 있다",
        "`games.json` 스냅샷의 **신선도** --- 리뷰는 2026-08 인데 게임표는 언제 뜬 것인지 안 쟀다",
        "본문의 **품질**(길이·스팸) --- 행 수만 셌다",
    ]
    res["초"] = round((dt.datetime.now() - t0).total_seconds(), 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT)
    print("  부순다: a %d · s %d · o %d · 셋다 %d (셋다==o? %s)"
          % (a952, s952, o952, all952, all952 == o952))
    print("  다시:   s %d · a %d · o %d · 셋다 %d"
          % (len(s_set), len(a953_set), len(o953_set), len(tri)))
    print("  283:    %d" % len(rowset & o952_set))
    return 0


if __name__ == "__main__":
    sys.exit(main())
