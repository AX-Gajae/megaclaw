"""자극 보강 재정규화 — 라벨 채굴 폴드의 빈약한 intervention/conditions를 원문(운영안·기획안·계약서)으로 재추출.

rolling-v5 교훈(2026-07-24): 채굴 폴드들의 자극이 ~550자(스키마 뼈대)였던 원인은 문서 부재가
아니라 미인제스트. 이 스크립트는 기존 레코드의 outcome(라벨)·entities(정준화 키)·period는
보존하고, intervention/conditions만 신선한 추출로 교체한다 (capacity 필드 포함).

사용: python3 -m ingest.enrich_stimulus --codes C1,C2,...
원본은 data/records_thinbak/ 에 백업.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from ingest.bulk_normalize import DriveReader, normalize_one, INGEST


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--agent-dir", default=None, help="지정 시 에이전트 모드(2패스, API 호출 0)")
    args = ap.parse_args()
    from core.agent_task import AgentTask
    client = None
    if not args.agent_dir:
        import anthropic
        from core.noapi import assert_free  # 노트 889 — 유료 API 기본 차단
        assert_free("enrich_stimulus")
        client = anthropic.Anthropic()
    task = AgentTask("agent" if args.agent_dir else "api", args.agent_dir, client,
                     effort="medium", max_tokens=16000) if args.agent_dir else None
    reader = DriveReader()

    projects = {}
    for fn in ("projects.json", "projects_2425.json", "projects_forward.json"):
        f = INGEST / fn
        if f.exists():
            for p in json.loads(f.read_text()):
                projects.setdefault(p["project_code"], p)
    docs_by = {}
    for d in json.loads((INGEST / "docs_enrich.json").read_text()):
        docs_by.setdefault(d["project_code"], []).append(d)
    pnl = {r["project_code"]: float(r["revenue_mm"]) for r in json.loads((INGEST / "pnl.json").read_text())
           if r.get("revenue_mm") is not None}

    bak = Path("data/records_thinbak")
    bak.mkdir(exist_ok=True)
    done = failed = 0
    for code in args.codes.split(","):
        rp = Path(f"data/records/{code}.json")
        if not rp.exists() or code not in projects:
            print(f"{code}: 레코드/메타 없음 — 건너뜀", flush=True)
            continue
        existing = json.loads(rp.read_text())
        before_len = len(json.dumps({"i": existing["intervention"], "c": existing["conditions"]}, ensure_ascii=False))
        try:
            fresh = normalize_one(client, reader, projects[code], docs_by.get(code, []), pnl.get(code), task)
            if fresh is None:    # 에이전트 모드 1패스 — 응답 대기
                continue
        except Exception as e:
            print(f"{code}: 추출 실패 {type(e).__name__}: {str(e)[:120]}", flush=True)
            failed += 1
            continue

        fresh_len = len(json.dumps({"i": fresh["intervention"], "c": fresh["conditions"]}, ensure_ascii=False))
        if fresh_len <= before_len:
            print(f"{code}: 보강분({fresh_len}자)이 기존({before_len}자)보다 얇음 — 병합 건너뜀 (문서 추출 실패 추정)", flush=True)
            failed += 1
            continue
        shutil.copy(rp, bak / f"{code}.json")
        merged = existing  # outcome·entities·record_id 전부 보존
        merged["intervention"] = fresh["intervention"]
        new_cond = fresh["conditions"]
        new_cond["period"] = existing["conditions"].get("period")  # 라벨이 이 기간에 스코프됨 — 불변
        if existing["conditions"].get("scale") and not new_cond.get("scale"):
            new_cond["scale"] = existing["conditions"]["scale"]
        merged["conditions"] = new_cond
        seen = {d.get("doc_id") for d in merged.get("docs", [])}
        merged["docs"] = (merged.get("docs") or []) + [d for d in fresh["docs"] if d["doc_id"] not in seen]
        after_len = len(json.dumps({"i": merged["intervention"], "c": merged["conditions"]}, ensure_ascii=False))
        cap = (new_cond.get("capacity") or {})
        merged["provenance"]["notes"] += (
            f" | 자극 보강(2026-07-24): 운영안·기획안·계약서 재인제스트로 intervention/conditions 교체 "
            f"({before_len}→{after_len}자, capacity={cap.get('access_type', '미추출')}"
            f"{'/' + format(cap['total_capacity'], ',') if cap.get('total_capacity') else ''}). outcome·entities·period 보존")
        rp.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
        print(f"✅ {code}: 자극 {before_len}→{after_len}자, capacity={cap.get('access_type')}", flush=True)
        done += 1
    print(json.dumps({"보강": done, "실패": failed}, ensure_ascii=False), flush=True)
    if task is not None:
        print(task.report(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
