#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""954 수리 --- 티처 #92 **C1**: `prfsts_day.jsonl.gz` 의 **376일을 되찾는다**.

무엇이 있었나: `ingest/kopis953.py` 가 이 파일만 `_write_gz`(**덮어쓰기**)로 썼고
(형제 셋은 `_merge_write`), 상시 데몬의 **31일 증분 창**이 매 주행 376일을 갈아엎었다.
디스크·HEAD 둘 다 **31행**이었고 376행짜리 판은 **어느 커밋에도 없다**(티처가 세었고
주 세션이 독립 재계수해 일치).

수리 둘:
  ① `ingest/kopis953.py` 의 **두 자리**(`_series_only` · `main`)를
     `_merge_write(key="prfdt")` 로 고쳤다 --- 재발을 막는다.
  ② 이 러너가 넓은 창으로 다시 받아 **합쳐 쓴다** --- 잃은 날을 되찾는다.

🔴 이 러너는 절 4-나(`prfstsTotal · ststype=day`)**만** 만진다. 다른 절·다른 파일 안 건드린다.
🔴 조항 59: 종료코드가 아니라 **파일을 다시 열어 센 행 수**를 산출물에 적는다.
🔴 유료 API 아님(KOPIS 공개 키 · 키 문자열은 저장소 밖 `/Users/ax/wm_harvest/keys.json`).

씀: python3 runners/kopis954_backfill.py --start 20250801 --end 20260813
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ingest import kopis953 as K  # noqa: E402


def count_file():
    """🔴 「썼다」가 아니라 「다시 열어 세었다」."""
    rs = K._read_gz(K.OUTDIR / "prfsts_day.jsonl.gz")
    days = sorted({r.get("prfdt") for r in rs if r.get("prfdt")})
    return len(rs), days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20250801")
    ap.add_argument("--end", default=dt.datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--out", default="runners/out954_kopis_c1.json")
    ap.add_argument("--expect", choices=("grow", "nodrop"), default="grow",
                    help="grow=되찾기 주행(행이 늘어야 통과) · nodrop=증분 회귀 시험(행이 "
                         "안 줄어야 통과). 🔴 판정 기준을 값 보기 전에 인자로 정한다")
    ap.add_argument("--negative-control", action="store_true",
                    help="🔴 음성 대조 --- 같은 증분 창을 **옛 코드(`_write_gz`)** 로 사본에 쓴다. "
                         "진짜 파일은 안 건드린다. 옛 코드가 정말 자르는지 눈으로 본다")
    a = ap.parse_args()
    t0 = time.time()

    before_rows, before_days = count_file()
    wins = K._windows(a.start, a.end)
    series, serr = [], []
    for (s, e) in wins:
        root, err, tr = K.call_retry("prfstsTotal",
                                     {"stdate": s, "eddate": e, "ststype": "day"})
        time.sleep(K.SLEEP)
        if err:
            serr.append({"창": [s, e], "🔴": err})
            continue
        series.extend(K.rows(root, "prfstsTotal"))

    # 🔴 음성 대조 먼저 --- **사본에** 옛 코드(`_write_gz`)를 그대로 물린다.
    neg = None
    if a.negative_control:
        import shutil
        cp = K.OUTDIR / "prfsts_day.음성대조사본.jsonl.gz"
        shutil.copy2(K.OUTDIR / "prfsts_day.jsonl.gz", cp)
        n_before = len(K._read_gz(cp))
        K._write_gz(cp, series)              # 옛 코드가 하던 그대로
        n_after = len(K._read_gz(cp))
        cp.unlink()
        neg = {"사본 전 행": n_before, "옛 코드(_write_gz)로 쓴 뒤 행": n_after,
               "🔴 옛 코드가 잘랐나": n_after < n_before,
               "🔴 이 대조는 진짜 파일을 안 건드린다": True}

    merged = K._merge_write(K.OUTDIR / "prfsts_day.jsonl.gz", series, "prfdt")
    after_rows, after_days = count_file()

    src = (REPO / "ingest" / "kopis953.py").read_bytes()
    res = {
        "무엇": "티처 #92 C1 수리 --- prfsts_day 의 잃은 날을 되찾고 재발을 막는다",
        "🔴 규약 60 --- 명령·범위·트리": {
            "명령": "python3 runners/kopis954_backfill.py --start %s --end %s" % (a.start, a.end),
            "범위": "data/ingest/kopis/prfsts_day.jsonl.gz 한 파일 · 절 4-나만",
            "트리": "작업 트리(그리고 이 커밋이 실는다)",
        },
        "🔴 고친 자리": ["ingest/kopis953.py `_series_only` --- _write_gz → _merge_write(key='prfdt')",
                    "ingest/kopis953.py `main` --- 같은 고침(티처가 인용한 :459 자리)"],
        "🔴 창 수(분모)": len(wins),
        "🔴 실패한 창": len(serr),
        "실패 예": serr[:3] or "없음",
        "받은 행": len(series),
        "합치기": merged,
        "전 --- 행": before_rows, "전 --- 서로다른 prfdt": len(before_days),
        "전 --- 첫 날": before_days[0] if before_days else "없음",
        "전 --- 끝 날": before_days[-1] if before_days else "없음",
        "후 --- 행": after_rows, "후 --- 서로다른 prfdt": len(after_days),
        "후 --- 첫 날": after_days[0] if after_days else "없음",
        "후 --- 끝 날": after_days[-1] if after_days else "없음",
        "🔴 되찾은 날": len(after_days) - len(before_days),
        "코드 sha256(kopis953.py)": hashlib.sha256(src).hexdigest(),
        "러너 sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "🔴 판정 기준(값 보기 전에 인자로 정했다)": a.expect,
        "🔴 음성 대조(옛 코드를 사본에 물린다)": neg or "안 돌렸다",
        "시작(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        "끝(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "초": round(time.time() - t0, 1),
        "통과": (after_rows > before_rows if a.expect == "grow"
               else after_rows >= before_rows) and len(serr) == 0,
    }
    (REPO / a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("전 --- 행", "후 --- 행", "🔴 되찾은 날",
                                          "🔴 실패한 창", "통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
