#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HPLT 2.0 `kor_Hang` 464 shard 전량 수신 --- 🔴 **층화 뒤섞기 순서로 받는다**.

왜 순서를 뒤섞나(원장 997):
    464 shard 는 `collection` 별로 **큰 연속 덩어리**로 놓여 있다.
    앞에서부터 받으면 **어느 시점에 끊기든 그때까지 받은 것이 한 크롤의 편향 표본**이다.
    실제로 그렇게 4개를 받아서 「뉴스 8.9% · 도박 3.869%」 같은 수를
    원천의 성질인 양 보고했고, 그게 조항 60 위반이었다.

    그래서 **비트 뒤집기 순열**로 받는다. 어느 지점에서 멈춰도
    그때까지 받은 것이 0~463 에 고르게 퍼져 있다.

🔴 조항 59 --- HTTP 200 껍데기를 성공으로 읽지 않는다.
    받은 파일은 **pyarrow 로 실제로 열어 보고**, 안 열리면 지우고 실패로 적는다.

씀:  python3 runners/hplt_fetch.py            # 전량(이미 있는 것은 건너뛴다)
     python3 runners/hplt_fetch.py --limit 24 # 앞의 24개만
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

BASE = ("https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned/resolve/"
        "refs%2Fconvert%2Fparquet/kor_Hang/train")
N_SHARD = 464
OUT = pathlib.Path("data/ingest/hplt_ko")
LOG = pathlib.Path("/Users/ax/wm_harvest/hplt_fetch.jsonl")   # 🔴 저장소 밖


def stratified_order(n: int):
    """비트 뒤집기 순열 --- 어느 앞부분을 잘라도 0~n 에 고르게 퍼진다."""
    bits = max(1, (n - 1).bit_length())
    seen, order = set(), []
    for i in range(1 << bits):
        r = int(format(i, "0%db" % bits)[::-1], 2)
        if r < n and r not in seen:
            seen.add(r)
            order.append(r)
    return order


def name(i: int) -> str:
    return "train-%05d-of-00464.parquet" % i


def gz_ok(p: pathlib.Path) -> bool:
    """🔴 정말 읽히는 parquet 인가. 종료코드 0 도 200 도 증거가 아니다."""
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        import pyarrow.parquet as pq
        f = pq.ParquetFile(p)
        return f.metadata.num_rows > 0
    except Exception:
        return False


def note(rec: dict):
    rec["시각(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 이면 전량")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    order = stratified_order(N_SHARD)
    if a.limit:
        order = order[:a.limit]

    have = skip = ok = bad = 0
    got_bytes = 0
    t0 = time.time()
    for k, i in enumerate(order):
        p = OUT / name(i)
        if gz_ok(p):
            have += 1
            continue
        part = p.with_suffix(".part")
        url = "%s/%04d.parquet" % (BASE, i)
        r = subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "5", "--retry-delay", "3",
             "--connect-timeout", "30", "--max-time", "1800",
             "-o", str(part), url],
            capture_output=True, text=True)
        if r.returncode != 0 or not gz_ok(part):
            # 🔴 「받았다」와 「읽힌다」는 둘이다
            sz = part.stat().st_size if part.exists() else 0
            part.unlink(missing_ok=True)
            bad += 1
            note({"shard": i, "결과": "실패", "종료코드": r.returncode,
                  "받은바이트": sz, "stderr": (r.stderr or "")[:200]})
            continue
        os.replace(part, p)
        ok += 1
        got_bytes += p.stat().st_size
        if ok % 10 == 0:
            el = time.time() - t0
            note({"진행": "%d/%d" % (k + 1, len(order)), "새로받음": ok,
                  "이미있음": have, "실패": bad,
                  "MB/s": round(got_bytes / 1e6 / max(el, 1), 2)})
        sys.stdout.write("\r%d/%d · 새 %d · 있음 %d · 실패 %d"
                         % (k + 1, len(order), ok, have, bad))
        sys.stdout.flush()

    el = time.time() - t0
    fin = {"끝": True, "대상": len(order), "새로받음": ok, "이미있음": have,
           "실패": bad, "초": round(el, 1),
           "MB/s": round(got_bytes / 1e6 / max(el, 1), 2)}
    note(fin)
    print("\n" + json.dumps(fin, ensure_ascii=False))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
