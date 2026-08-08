# -*- coding: utf-8 -*-
# popup_visitor_daily 일일 스냅샷(노트 871·872 · T7 · 노트 636 '채굴보다 배선' 이행)
# 읽기: `bq head`(tabledata.list) + `bq show`(tables.get numRows 대조) — 잡 생성 없음(읽기 전용).
# 쓰기: data/state/popup_visitor_daily.jsonl 멱등 append — 키는 **전행 해시**(872: (id, updated_at)
#       키는 제자리 수정에 장님이었다 — 48행 전건 created==updated 실측) + 장부(_log.jsonl).
# 성장물 선언: 두 파일 다 append-only · 단일 필자 = 이 모듈.
# 사용: python3 -m ingest.popupsnap   (상시 조항: 매 사이클 첫 행동 · 크론 후보)
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

TABLE = "sweetspot-ax:core.popup_visitor_daily"
CAP = 100000
OUT = Path("/Users/ax/world_model/data/state/popup_visitor_daily.jsonl")
LOG = Path("/Users/ax/world_model/data/state/popup_visitor_daily_log.jsonl")


def row_key(r: dict) -> str:
    body = {k: v for k, v in r.items() if k != "_스냅샷(UTC)"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _bq(args, timeout=120):
    r = subprocess.run(["bq"] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)


def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        rows = _bq(["head", "-n", str(CAP), "--format=json", TABLE])
        meta = _bq(["show", "--format=json", TABLE])
        num_rows = int(meta.get("numRows", -1))
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        entry = {"시각(UTC)": now, "실패": f"{type(e).__name__}: {str(e)[:180]}"}
        with open(LOG, "a") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        return
    warn = []
    if len(rows) >= CAP:
        warn.append(f"상한 {CAP} 도달 — 절단 위험")
    if num_rows >= 0 and num_rows != len(rows):
        warn.append(f"numRows {num_rows} ≠ head {len(rows)}")
    seen = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            seen.add(row_key(json.loads(line)))
    new = [r for r in rows if row_key(r) not in seen]
    with open(OUT, "a") as fh:
        for r in new:
            fh.write(json.dumps({**r, "_스냅샷(UTC)": now}, ensure_ascii=False) + "\n")
    entry = {"시각(UTC)": now, "전체 행": len(rows), "신규 행": len(new),
             "누적 로컬": len(seen) + len(new), "키": "전행해시(872)"}
    if warn:
        entry["경고"] = warn
    with open(LOG, "a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
