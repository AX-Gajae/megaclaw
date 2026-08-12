# -*- coding: utf-8 -*-
"""③ 측정 — **받은 것을 센다** (노트 952 [수집]).

🔴 이 러너의 존재 이유 하나: **「받았다」와 「쓸 수 있다」는 둘이다**(조항 59).
지평 조사가 준 수(38,866,835 문서 · 125,855 게임)는 **남이 신고한 수**다. 여기서는 **내가 센다**.

🔴 분모를 이어 붙이지 않는다(조항 60). 아래 수는 전부 자기 분모를 달고 나온다:
  · HPLT = **내가 받은 4 shard 안의 문서 수** (464 분의 4 · 전량이 아니다)
  · Steam csv = `games.csv` 행수 · Steam json = `games.json` 항목 수 --- 🔴 **둘이 다르다**
  · 교집합 = 기존 리뷰의 서로 다른 appid 중 몇이 붙나 (합이 아니다)
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_count.json"
HPLT_DIR = ROOT / "data/ingest/hplt_ko"
STEAM_ZIP = ROOT / "data/ingest/steam_games/archive.zip"
REVIEWS = ROOT / "data/ingest/steam_reviews/reviews.jsonl.gz"

csv.field_size_limit(10 ** 9)

HANGUL = re.compile(r"[가-힣]")
#: 🔴 사전등록 §2 P3 이 못 박은 조작적 정의 --- 여기서 바꾸지 않는다
NONKO_THRESHOLD = 0.10


# ───────────────────────────────── HPLT ─────────────────────────────────
def count_hplt() -> dict:
    import pyarrow.parquet as pq

    files = sorted(HPLT_DIR.glob("*.parquet"))
    res = {
        "🔴 분모": "내가 받은 %d shard (464 중). **38,866,835 은 남이 신고한 수이고 내 분모가 아니다**" % len(files),
        "shard수": len(files),
        "shard이름": [f.name for f in files],
        "바이트": sum(f.stat().st_size for f in files),
        "🔴 표본 편향": "464 중 **앞에서 4개**다. 무작위 표본이 아니다 --- 원천 정렬이 있으면 대표성이 없고, **그건 안 쟀다**",
    }
    n = 0
    empty = 0
    nonko = 0
    total_len = 0
    digests = set()
    dup = 0
    lang_top = collections.Counter()
    robots = collections.Counter()
    len_hist = collections.Counter()
    sample = []
    for f in files:
        pf = pq.ParquetFile(f)
        for i in range(pf.metadata.num_row_groups):
            t = pf.read_row_group(i, columns=["text", "lang", "robotstxt", "u", "ts"])
            texts = t.column("text").to_pylist()
            langs = t.column("lang").to_pylist()
            rbs = t.column("robotstxt").to_pylist()
            urls = t.column("u").to_pylist()
            for j, tx in enumerate(texts):
                n += 1
                tx = tx or ""
                st = tx.strip()
                if not st:
                    empty += 1
                total_len += len(tx)
                len_hist[min(len(tx) // 1000, 50)] += 1
                # 🔴 한글 비율 --- 공백 제외 전체 글자 대비 (사전등록 정의)
                nows = [c for c in st if not c.isspace()]
                ratio = (len(HANGUL.findall(st)) / len(nows)) if nows else 0.0
                if ratio < NONKO_THRESHOLD:
                    nonko += 1
                d = hashlib.sha256(tx.encode("utf-8")).digest()
                if d in digests:
                    dup += 1
                else:
                    digests.add(d)
                lg = langs[j][0] if langs[j] else "?"
                lang_top[lg] += 1
                robots[rbs[j] or "?"] += 1
                if len(sample) < 200 and st:
                    sample.append({"url": (urls[j] or "")[:200], "언어": lg,
                                   "robotstxt": rbs[j], "글자수": len(tx),
                                   "한글비율": round(ratio, 3),
                                   "본문머리": tx[:400]})
    res.update({
        "문서수": n,
        "빈문서": empty,
        "중복(본문 sha256 완전일치)": dup,
        "중복률": round(dup / n, 6) if n else None,
        "고유문서": len(digests),
        "평균길이(글자)": round(total_len / n, 1) if n else None,
        "총글자": total_len,
        "비한국어문서(한글비율<%.2f)" % NONKO_THRESHOLD: nonko,
        "비한국어비율": round(nonko / n, 6) if n else None,
        "언어태그 상위": lang_top.most_common(8),
        "🔴 robotstxt 분포": robots.most_common(8),
        "길이분포(1000자 구간)": sorted(len_hist.items())[:12],
    })
    (HPLT_DIR / "sample200.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in sample), encoding="utf-8")
    res["표본파일"] = "data/ingest/hplt_ko/sample200.jsonl (200건 · 본문 400자로 자름)"
    return res


# ───────────────────────────────── Steam ─────────────────────────────────
#: 🔴 `games.csv` 는 **헤더가 깨져 있다** --- 헤더 39 칸, 데이터 행 40 칸.
#: 원인: `Discount` 와 `DLC count` 사이 쉼표가 빠져 `DiscountDLC count` 한 칸이 됐다.
#: 그대로 읽으면 **그 뒤 모든 열이 한 칸씩 밀린다**(Mac=True · Developers=0 …).
BROKEN = "DiscountDLC count"
FIXED = ["Discount", "DLC count"]


def _fix_header(hdr):
    if BROKEN in hdr:
        i = hdr.index(BROKEN)
        return hdr[:i] + FIXED + hdr[i + 1:], True
    return hdr, False


def count_steam() -> dict:
    z = zipfile.ZipFile(STEAM_ZIP)
    res = {"zip항목": [(i.filename, i.file_size) for i in z.infolist()],
           "zip바이트": STEAM_ZIP.stat().st_size}

    # ── csv
    with z.open("games.csv") as fh:
        t = io.TextIOWrapper(fh, encoding="utf-8", newline="")
        r = csv.reader(t)
        hdr = next(r)
        fixed, was_broken = _fix_header(hdr)
        widths = collections.Counter()
        rows_csv = 0
        csv_ids = set()
        idx = fixed.index("AppID")
        for row in r:
            rows_csv += 1
            widths[len(row)] += 1
            if len(row) == len(fixed):
                csv_ids.add(row[idx])
    res["csv"] = {
        "🔴 분모": "`games.csv` 데이터 행수",
        "행수": rows_csv,
        "헤더 열수(원본)": len(hdr),
        "헤더 열수(고친 뒤)": len(fixed),
        "데이터 행 길이 분포": widths.most_common(4),
        "🔴 헤더가 깨져 있었나": was_broken,
        "🔴 무엇이 깨졌나": ("`%s` 한 칸 --- `Discount` 와 `DLC count` 사이 쉼표 결손. "
                          "고치기 전에 그대로 읽으면 그 뒤 **모든 열이 한 칸씩 밀린다**"
                          "(실측: `Mac=True` · `Metacritic score=False` · `Developers=0`)") % BROKEN,
        "열이름(고친 뒤 전량)": fixed,
        "서로다른 AppID": len(csv_ids),
    }

    # ── json (🔴 csv 와 **다른 수**다)
    with z.open("games.json") as fh:
        gj = json.load(fh)
    res["json"] = {
        "🔴 분모": "`games.json` 항목 수 --- **csv 와 다르다. 이어 붙이지 마라**(조항 60)",
        "항목수": len(gj),
        "csv 대비": len(gj) - rows_csv,
        "열이름(첫 항목 키 전량)": sorted(next(iter(gj.values())).keys()),
    }

    # ── (s,a,o) 로 쓸 수 있는 행 (🔴 사전등록 P8 의 정의 그대로)
    ok_a = ok_o = ok_s = ok_all = 0
    bad_date = collections.Counter()
    sao_ids = []
    for appid, g in gj.items():
        rd = (g.get("release_date") or "").strip()
        a = bool(rd) and _parse_date(rd) is not None
        if not a and rd:
            bad_date[rd[:12]] += 1
        pos = int(g.get("positive") or 0)
        neg = int(g.get("negative") or 0)
        o = (pos + neg) >= 1
        s = bool(g.get("genres")) or bool(g.get("tags")) or (g.get("price") is not None)
        ok_a += a
        ok_o += o
        ok_s += s
        if a and o and s:
            ok_all += 1
            sao_ids.append(appid)
    res["sao"] = {
        "🔴 분모": "`games.json` 항목 %d" % len(gj),
        "🔴 정의(사전등록 §2 P8 · 사후에 안 고쳤다)":
            "a=출시일이 있고 파싱된다 · o=(positive+negative)>=1 · s=genres/tags/price 중 하나 이상",
        "a 만족": ok_a, "o 만족": ok_o, "s 만족": ok_s,
        "🔴 셋 다(=쓸 수 있는 행)": ok_all,
        "비율": round(ok_all / len(gj), 6),
        "🔴 못 파싱한 출시일 상위": bad_date.most_common(5),
    }

    # ── 기존 리뷰와의 교집합 (🔴 합이 아니라 교집합)
    rev_ids = set()
    rev_rows = 0
    if REVIEWS.exists():
        with gzip.open(REVIEWS, "rt", encoding="utf-8") as f:
            for ln in f:
                rev_rows += 1
                try:
                    d = json.loads(ln)
                except Exception:
                    continue
                for k in ("appid", "app_id", "개체", "AppID"):
                    if k in d:
                        rev_ids.add(str(d[k]).replace("GAME-", ""))
                        break
    inter = rev_ids & set(gj.keys())
    res["교집합"] = {
        "🔴 분모 둘을 이어 붙이지 않는다": "리뷰 행 %d · 리뷰의 서로 다른 appid %d · 게임표 %d"
                                        % (rev_rows, len(rev_ids), len(gj)),
        "리뷰 행": rev_rows,
        "리뷰의 서로다른 appid": len(rev_ids),
        "🔴 게임표에 붙는 appid": len(inter),
        "붙는 비율(리뷰 appid 분모)": round(len(inter) / len(rev_ids), 6) if rev_ids else None,
        "안 붙는 appid 예": sorted(rev_ids - set(gj.keys()))[:8],
    }
    res["🔴 새 (s,a,o) 후보"] = {
        "수": ok_all,
        "기존 게임 도메인 (s,a,o)": 538,
        "배": round(ok_all / 538, 1),
        "🔴 주의": "이것은 **후보**다. 판 유보에 실제로 붙는지는 **안 쟀다**",
    }
    res["sao_ids표본"] = sao_ids[:20]
    return res


_MON = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def _parse_date(s: str):
    s = s.strip().replace(",", "")
    p = s.split()
    try:
        if len(p) == 3:                      # "Aug 1 2023"
            return dt.date(int(p[2]), _MON[p[0][:3]], int(p[1]))
        if len(p) == 2:                      # "Aug 2023"
            return dt.date(int(p[1]), _MON[p[0][:3]], 1)
    except Exception:                        # noqa: BLE001
        return None
    return None


def main() -> int:
    res = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "🔴 스냅샷": "살아 있는 원천이다. 위 시각의 값이고, 내일 다시 세면 다를 수 있다",
    }
    t0 = dt.datetime.now()
    res["steam"] = count_steam()
    print("steam 끝", (dt.datetime.now() - t0).total_seconds(), flush=True)
    res["hplt"] = count_hplt()
    res["초"] = round((dt.datetime.now() - t0).total_seconds(), 1)
    res["끝시각(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
