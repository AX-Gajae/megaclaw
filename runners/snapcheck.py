# -*- coding: utf-8 -*-
# popupsnap 양성 대조 정본(노트 874 · 티처 #39 중대 1 봉합) — 픽스처 기반·bq 무호출.
# 저장 jsonl 첫 행을 변조해 row_key 가 신규로 잡는지, 원행은 기존 키인지 확인한다.
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from ingest.popupsnap import row_key  # noqa: E402 — 순수 함수(임포트 안전)

ROOT = Path("/Users/ax/world_model")


def main():
    rows = [json.loads(l) for l in open(ROOT / "data/state/popup_visitor_daily.jsonl")]
    orig = rows[0]
    mut = dict(orig)
    mut["total_visitor_count"] = str(int(mut["total_visitor_count"]) + 1)
    seen = {row_key(r) for r in rows}
    ok = row_key(orig) in seen and row_key(mut) not in seen
    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "행 수": len(rows), "원행 기존 키": row_key(orig) in seen,
           "변조행 신규 감지": row_key(mut) not in seen, "통과": ok,
           "자기서술": "필드 1(total_visitor_count) +1 변조 · _스냅샷 제외 전행 해시"}
    p = ROOT / f"runners/out_snapcheck_{dt.date.today()}.json"
    if not p.exists():
        json.dump(out, open(p, "x"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False), flush=True)
    assert ok, "양성 대조 실패"


if __name__ == "__main__":
    main()
