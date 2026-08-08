# -*- coding: utf-8 -*-
# popup_visitor_daily 일일 스냅샷(노트 871 · T7 · 노트 636 '채굴보다 배선' 이행)
# 읽기: `bq head`(tabledata.list) — 잡 생성 없음·구조 변경 없음(BQ 읽기 전용 제약 내).
# 쓰기: data/state/popup_visitor_daily.jsonl 멱등 append(키 visitor_daily_id+updated_at)
#       + popup_visitor_daily_log.jsonl (스냅샷 장부 — 일시·전체·신규).
# 사용: python3 -m ingest.popupsnap   (크론 후보 — 매일 1회)
import datetime as dt
import json
import subprocess
from pathlib import Path

TABLE = "sweetspot-ax:core.popup_visitor_daily"
OUT = Path("/Users/ax/world_model/data/state/popup_visitor_daily.jsonl")
LOG = Path("/Users/ax/world_model/data/state/popup_visitor_daily_log.jsonl")


def snapshot():
    r = subprocess.run(["bq", "head", "-n", "100000", "--format=json", TABLE],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None, r.stderr.strip()[:200]
    return json.loads(r.stdout), None


def main():
    rows, err = snapshot()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if rows is None:
        entry = {"시각(UTC)": now, "실패": err}
        with open(LOG, "a") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        return
    seen = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            j = json.loads(line)
            seen.add((j.get("visitor_daily_id"), j.get("updated_at")))
    new = [r for r in rows if (r.get("visitor_daily_id"), r.get("updated_at")) not in seen]
    with open(OUT, "a") as fh:
        for r in new:
            fh.write(json.dumps({**r, "_스냅샷(UTC)": now}, ensure_ascii=False) + "\n")
    entry = {"시각(UTC)": now, "전체 행": len(rows), "신규 행": len(new),
             "누적 로컬": len(seen) + len(new)}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
