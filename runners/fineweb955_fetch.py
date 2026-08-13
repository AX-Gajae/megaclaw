#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""955 --- FineWeb-2 `kor_Hang` **전량 25파일** 수신기.

🔴 왜 지금 받나: `docs/prereg_955_D.md` §6 의 판정이 **측정 전에** 정해져 있었고,
`runners/out955_D.json` 의 정본 `D = 자② D_문서^{K=21} = 0.195556 ≤ 0.30` 이 그 칸을
가리켰다. **깨끗한 읽기 여덟이 전부 같은 칸**이다(강함).
954 가 낸 「보류」는 **키 이름과 계산이 어긋난 하나의 오염된 읽기**에서 나왔다(티처 #93 C1).

🔴 순서(사전등록 §6-A):
  · `runners/hplt_fetch.py:35` 의 `stratified_order()`(비트 뒤집기)를 **본뜬다**.
    어느 앞부분을 잘라도 25파일에 고르게 퍼진다 --- **앞에서 자르지 않는다**.
  · 목적지는 🔴 **저장소 밖** `/Users/ax/wm_harvest/fineweb2_ko/`.
    ① `data/ingest/` 는 상시 데몬 감시 구역(60초 틱)이고
    ② `.gitignore` 의 parquet 규칙이 954 시점에 `hplt_ko/` 에만 걸려 있었다(티처 #93 m4).
    955 가 그 규칙을 넓혔지만 **목적지는 그래도 밖으로 둔다**(두 겹).
  · 🔴 조항 59 --- 「받았다」는 종료코드 0 도 HTTP 200 도 아니다.
    **`pq.ParquetFile(p).metadata.num_rows` 가 954 가 읽은 메타의 「전량 행」과 같아야** 성공이다.
    다르면 **실패로 세고 지운다**.
  · 임시 파일은 `p.name + ".part"` 로 만든다(`with_suffix` 가 아니다 --- 954 사고의 뿌리).

씀:
    python3 runners/fineweb955_fetch.py            # 전부
    python3 runners/fineweb955_fetch.py --limit 3  # 앞 3개(층화 순서의 앞 3개다)
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

BASE = ("https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/resolve/main/"
        "data/kor_Hang/train/")
NAMES = ["%03d_%05d.parquet" % (g, k) for g in range(5) for k in range(5)]
OUT = pathlib.Path("/Users/ax/wm_harvest/fineweb2_ko")
META = pathlib.Path("/Users/ax/wm_harvest/954/fw")          # 954 가 읽은 파일별 메타
LOG = pathlib.Path("/Users/ax/wm_harvest/fineweb955_fetch.jsonl")
NEED_GB = 130          # 🔴 사전등록 §6-A --- 여유가 이보다 적으면 시작 안 한다


def stratified_order(n):
    """🔴 `runners/hplt_fetch.py:35` 을 본떴다 --- 비트 뒤집기 순열.
    어느 앞부분을 잘라도 0~n 에 고르게 퍼진다."""
    bits = max(1, (n - 1).bit_length())
    seen, order = set(), []
    for i in range(1 << bits):
        r = int(format(i, "0%db" % bits)[::-1], 2)
        if r < n and r not in seen:
            seen.add(r)
            order.append(r)
    return order


def want_rows():
    """954 가 각 파일의 parquet 꼬리에서 읽은 **전량 행 수**. 이것이 수신 검사의 자다."""
    w = {}
    for p in sorted(META.glob("*.parquet.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        w[r["파일"]] = int(r["전량 행"])
    return w


def ok_parquet(p, want):
    """🔴 조항 59 --- 「받았다」와 「열린다」와 「맞다」는 셋이다."""
    if not p.exists() or p.stat().st_size == 0:
        return False, "없거나 0바이트"
    try:
        import pyarrow.parquet as pq
        n = pq.ParquetFile(p).metadata.num_rows
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)
    if want is not None and n != want:
        return False, "행 수가 다르다 --- 받은 %d · 954 메타 %d" % (n, want)
    return True, "행 %d" % n


def note(rec):
    rec["시각(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage("/Users/ax").free / 2 ** 30
    note({"무엇": "시작", "디스크 여유(GiB)": round(free_gb, 1), "문턱(GiB)": NEED_GB})
    if free_gb < NEED_GB:
        print("🔴 디스크 여유 %.1f GiB < %d GiB --- 시작 안 한다(사전등록 §6-A)"
              % (free_gb, NEED_GB), flush=True)
        return 2

    want = want_rows()
    order = stratified_order(len(NAMES))
    if a.limit:
        order = order[:a.limit]
    print("층화 순서: %s" % order, flush=True)

    have = ok = bad = 0
    got_bytes = 0
    t0 = time.time()
    for k, i in enumerate(order):
        name = NAMES[i]
        p = OUT / name
        w = want.get(name)
        good, why = ok_parquet(p, w)
        if good:
            have += 1
            continue
        part = p.with_name(p.name + ".part")      # 🔴 with_suffix 가 아니다(954 사고)
        t1 = time.time()
        r = subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "5", "--retry-delay", "5",
             "--connect-timeout", "30", "--max-time", "10800",
             "-o", str(part), BASE + name],
            capture_output=True, text=True)
        good, why = ok_parquet(part, w)
        if r.returncode != 0 or not good:
            sz = part.stat().st_size if part.exists() else 0
            part.unlink(missing_ok=True)
            bad += 1
            note({"무엇": "실패", "파일": name, "curl 종료코드": r.returncode,
                  "받은 바이트": sz, "이유": why, "stderr": r.stderr[-400:]})
            print("🔴 실패 %s --- 종료코드 %d · %s" % (name, r.returncode, why), flush=True)
            continue
        part.rename(p)
        sz = p.stat().st_size
        got_bytes += sz
        ok += 1
        note({"무엇": "받음", "파일": name, "바이트": sz, "검사": why,
              "초": round(time.time() - t1, 1)})
        print("%d/%d %s · %.2f GiB · %s · %.0fs"
              % (k + 1, len(order), name, sz / 2 ** 30, why, time.time() - t1), flush=True)

    done = sum(1 for n in NAMES if ok_parquet(OUT / n, want.get(n))[0])
    rec = {"무엇": "끝", "이번에 받은 파일": ok, "이미 있던 파일": have, "실패": bad,
           "🔴 분자 = 열리고 행 수가 맞는 파일": done, "🔴 분모 = 전량 파일": len(NAMES),
           "받은 바이트": got_bytes, "초": round(time.time() - t0, 1),
           "통과": bool(done == len(NAMES))}
    note(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    return 0 if done == len(NAMES) else 1


if __name__ == "__main__":
    sys.exit(main())
