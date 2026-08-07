"""라벨 발굴 — 방문 라벨 없는 레코드의 result_report를 전수 재추출 (전용 프롬프트, 캡 확대).

일반 정규화와의 차이: 결과보고서만, 문서 수 무제한, 방문·매출 표 추출에만 집중.
기존 라벨이 있는 레코드에 쓰면 교차검증 모드(불일치 보고, 덮어쓰지 않음).

사용: python3 -m ingest.mine_labels --codes C1,C2,...
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ingest.bulk_normalize import DriveReader, extract_doc_text, INGEST

MINE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["found", "daily", "totals", "counting_method", "counting_basis",
                  "plan_visitors_expected", "evidence"],
    "properties": {
        "found": {"type": "boolean"},
        "daily": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                   "required": ["date", "visitors", "sales_krw"],
                   "properties": {"date": {"type": "string"}, "visitors": {"type": ["integer", "null"]},
                                   "sales_krw": {"type": ["number", "null"]}}}},
        "totals": {"type": "object", "additionalProperties": False,
                    "required": ["visitors", "sales_krw"],
                    "properties": {"visitors": {"type": ["integer", "null"]},
                                    "sales_krw": {"type": ["number", "null"]}}},
        "counting_method": {"type": "string",
                             "enum": ["entry", "participation", "exposure", "purchase", "mixed", "unknown"]},
        "counting_basis": {"type": ["string", "null"]},
        "plan_visitors_expected": {"type": ["integer", "null"]},
        "evidence": {"type": "string"},
    },
}

SYS = """결과보고서에서 방문·매출 실측만 추출하는 전문 추출기다.
1. 일자별/시간대별 방문 표를 찾아 daily에 일 단위로 합산하라. totals.visitors는 기간 총계.
2. counting_method: 그 숫자가 무엇을 센 것인지(entry 입장/participation 참여·연인원/exposure 통과·노출/purchase 구매). 표의 컬럼명·집계 설명을 counting_basis에 30자 내로 인용. 정의 근거 없으면 unknown.
3. sales_krw는 소비자 매출(POS·판매)만. 계약금·정산금은 절대 아님.
4. 목표·예상·KPI는 실측이 아니다 — plan_visitors_expected에만 넣어라.
5. 실측 방문 숫자가 문서에 없으면 found=false. 지어내지 마라. evidence에 근거 위치(슬라이드/표 이름)를 적어라."""


def llm_extract(client, text: str) -> dict:
    import anthropic
    for attempt in range(5):
        try:
            with client.messages.stream(
                model="claude-opus-4-8", max_tokens=8000,
                thinking={"type": "adaptive"},
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": MINE_SCHEMA}},
                system=[{"type": "text", "text": SYS, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": text}],
            ) as s:
                resp = s.get_final_message()
            return json.loads(next(b.text for b in resp.content if b.type == "text"))
        except anthropic.APIStatusError:
            if attempt == 4:
                raise
            time.sleep(20 * (attempt + 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--agent-dir", default=None,
                    help="지정 시 에이전트 모드(2패스, 종량제 API 호출 0). 예: cycle_log/agent_tasks/mine")
    args = ap.parse_args()
    from core.agent_task import AgentTask
    client = None
    if not args.agent_dir:
        import anthropic
        client = anthropic.Anthropic()
    task = AgentTask("agent" if args.agent_dir else "api", args.agent_dir, client, effort="low")
    reader = DriveReader()
    docs_by = {}
    for d in json.loads((INGEST / "docs_all.json").read_text()):
        docs_by.setdefault(d["project_code"], []).append(d)

    log = open("cycle_log/mine_labels.jsonl", "a")
    found = crosscheck_diff = nodata = failed = 0
    for code in args.codes.split(","):
        rp = Path(f"data/records/{code}.json")
        if not rp.exists():
            continue
        rec = json.loads(rp.read_text())
        reports = [d for d in docs_by.get(code, []) if d["document_type"] == "result_report"]
        if not reports:
            continue
        parts, total = [], 0
        for d in reports:
            if total >= 60000:
                break
            try:
                t = extract_doc_text(reader, d)
            except Exception as e:
                print(f"  {code} 추출실패 {d['file_name'][:30]}: {type(e).__name__}", flush=True)
                continue
            t = t[:30000]
            total += len(t)
            parts.append(f'<report name="{d["file_name"]}">\n{t}\n</report>')
        if not parts:
            nodata += 1
            continue
        user = "\n\n".join(parts) + "\n\n위 결과보고서에서 방문·매출 실측을 추출하라."
        try:
            out = task.call(f"mine-{code}", SYS, MINE_SCHEMA, user)
        except Exception as e:
            print(f"  {code} LLM 실패: {type(e).__name__}", flush=True)
            failed += 1
            continue
        if out is None:      # 에이전트 모드 1패스 — 응답 대기
            continue
        existing = rec["outcome"]["totals"].get("visitors")
        row = {"code": code, "found": out["found"], "mined": out["totals"], "existing_visitors": existing,
                "counting": out["counting_method"], "evidence": out["evidence"][:100]}
        if out["found"] and out["totals"].get("visitors"):
            if existing:  # 교차검증 모드
                diff = abs(existing - out["totals"]["visitors"]) / existing
                row["crosscheck_diff"] = round(diff, 3)
                if diff > 0.10:
                    crosscheck_diff += 1
                    print(f"  ⚠️ {code} 교차검증 불일치: 기존 {existing} vs 발굴 {out['totals']['visitors']}", flush=True)
            else:  # 신규 라벨 패치
                rec["outcome"]["daily"] = out["daily"]
                rec["outcome"]["totals"]["visitors"] = out["totals"]["visitors"]
                if out["totals"].get("sales_krw") and not rec["outcome"]["totals"].get("sales_krw"):
                    rec["outcome"]["totals"]["sales_krw"] = out["totals"]["sales_krw"]
                rec["outcome"]["counting_method"] = out["counting_method"]
                rec["outcome"]["counting_basis"] = out["counting_basis"]
                if out.get("plan_visitors_expected"):
                    rec["outcome"]["plan_visitors_expected"] = out["plan_visitors_expected"]
                rec["provenance"]["notes"] += f" | 라벨발굴(2026-07-24): 결과보고서 재추출 — {out['evidence'][:60]}"
                rp.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
                found += 1
                print(f"  ✅ {code}: 방문 {out['totals']['visitors']:,} ({out['counting_method']})", flush=True)
        else:
            nodata += 1
        log.write(json.dumps(row, ensure_ascii=False) + "\n")
        log.flush()
    print(json.dumps({"신규라벨": found, "실측없음": nodata, "교차불일치": crosscheck_diff, "실패": failed},
                      ensure_ascii=False), flush=True)
    print(task.report(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
