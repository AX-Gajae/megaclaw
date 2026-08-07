"""fee 계약서화 — 견적이 주 총액인 레코드의 계약서 원문을 재독해 확정액으로 교체.

규칙(2026-07-27): 계약서 확정액 > 변경합의서 > 견적. 차이가 2% 초과면 contract_total_mm 교체
+ fee detail 앞에 계약 확정 라인 삽입 + 완결 판정 재계산(시간규칙 complete은 유지).

사용: python3 -m ingest.fee_contractize --codes C1,C2,...
로그: cycle_log/fee_contractize.jsonl
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ingest.bulk_normalize import DriveReader, extract_doc_text, INGEST

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["found", "contract_total_krw", "vat_note", "split_detail", "amendment_seen", "note"],
    "properties": {
        "found": {"type": "boolean"},
        "contract_total_krw": {"type": ["number", "null"]},
        "vat_note": {"type": "string"},
        "split_detail": {"type": "string"},
        "amendment_seen": {"type": "boolean"},
        "note": {"type": "string"},
    },
}
SYS = """계약서에서 스위트스팟이 수령하는 확정 계약 총액을 추출하는 전문가다.
1. contract_total_krw = 계약서(날인/서명본)에 명시된 총 계약금액(원). 변경합의서가 있으면 그것이 우선(amendment_seen=true).
2. 견적서·제안서 금액은 절대 쓰지 마라 — 계약 조항의 금액만.
3. vat_note: 'VAT 별도/포함/불명'. split_detail: 선금/중도금/잔금 분할과 지급 기일을 숫자 그대로.
4. 총액 조항이 없으면(수수료율만 있는 RS 계약 등) found=false, note에 구조를 적어라.
5. 여러 계약(본계약+부속)이 있으면 합산하지 말고 본계약 총액을 쓰고 note에 부속을 적어라."""


def llm(client, text):
    import anthropic
    for attempt in range(5):
        try:
            with client.messages.stream(
                model="claude-opus-4-8", max_tokens=4000,
                thinking={"type": "adaptive"},
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
                system=[{"type": "text", "text": SYS, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": text}],
            ) as s:
                r = s.get_final_message()
            return json.loads(next(b.text for b in r.content if b.type == "text"))
        except anthropic.APIStatusError:
            if attempt == 4:
                raise
            time.sleep(20 * (attempt + 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--agent-dir", default=None,
                    help="지정 시 에이전트 모드(2패스, 종량제 API 호출 0)")
    args = ap.parse_args()
    from core.agent_task import AgentTask
    client = None
    if not args.agent_dir:
        import anthropic
        client = anthropic.Anthropic()
    task = AgentTask("agent" if args.agent_dir else "api", args.agent_dir, client, effort="low", max_tokens=4000)
    reader = DriveReader()
    docs_by = {}
    for d in json.loads((INGEST / "docs_all.json").read_text()):
        if d["document_type"] == "contract":
            docs_by.setdefault(d["project_code"], []).append(d)

    log = open("cycle_log/fee_contractize.jsonl", "a")
    changed = confirmed = nofound = failed = 0
    for code in args.codes.split(","):
        rp = Path(f"data/records/{code}.json")
        if not rp.exists():
            continue
        rec = json.loads(rp.read_text())
        import unicodedata
        def _rank(d):
            n = unicodedata.normalize("NFC", d["file_name"])
            if any(x in n for x in ("견적", "기획안", "운영안", "시안", "리스트", "Thumbs", "감수", "예산", "일정")):
                return (2, 0)
            if "계약" in n or "agreement" in n.lower() or "과업" in n:
                return (0, -int(d.get("size_bytes") or 0))
            return (1, -int(d.get("size_bytes") or 0))
        docs = [d for d in sorted(docs_by.get(code, []), key=_rank) if _rank(d)[0] < 2][:3]
        if not docs:
            nofound += 1
            continue
        parts = []
        for d in docs:
            try:
                t = extract_doc_text(reader, d)[:25000]
                if t.strip():
                    parts.append(f'<contract name="{d["file_name"]}">\n{t}\n</contract>')
            except Exception as e:
                print(f"  {code} 추출실패 {d['file_name'][:30]}: {type(e).__name__}", flush=True)
        if not parts:
            nofound += 1
            continue
        user = "\n\n".join(parts) + "\n\n위 계약서에서 확정 계약 총액을 추출하라."
        try:
            out = task.call(f"fee-{code}", SYS, SCHEMA, user)
        except Exception as e:
            print(f"  {code} LLM 실패: {type(e).__name__}", flush=True)
            failed += 1
            continue
        if out is None:      # 에이전트 모드 1패스 — 응답 대기
            continue
        comp = rec["outcome"].setdefault("rev_mm_completion", {})
        cur = comp.get("contract_total_mm")
        row = {"code": code, "found": out["found"], "new_krw": out["contract_total_krw"],
               "cur_mm": cur, "amendment": out["amendment_seen"], "note": out["note"][:80]}
        if out["found"] and out["contract_total_krw"]:
            new_mm = round(out["contract_total_krw"] / 1e6, 1)
            fs = rec["conditions"]["fee_structure"]
            # 3각 대조 가드(2026-07-27): 인식액이 기존 총액(또는 그 VAT 변형)과 일치하면 교체 금지 —
            # 계약서 숫자가 최초 견적 인용이거나 VAT 표기 차이인 사례 2건이 실측됨(RTPU2566, RCPU2602)
            rev0 = rec["outcome"]["totals"].get("rev_mm_recognized")
            if cur and rev0 and abs(new_mm - cur) / cur > 0.02:
                for cand in (cur, round(cur * 1.1, 1), round(cur / 1.1, 1)):
                    if abs(rev0 - cand) / cand <= 0.03:
                        fs["detail"] += (f" | 계약서 재독해(2026-07-27): 계약서상 {new_mm}M이나 인식 {rev0}이 "
                                          f"기존 총액과 정합 — 3각 대조로 기존 유지")
                        row["skip"] = "3각 대조 — 인식이 기존 총액 지지"
                        new_mm = cur
                        break
            if cur and abs(new_mm - cur) / cur > 0.02:
                fs["detail"] = (f"[계약서 확정(2026-07-27 재독해)] 총액 {out['contract_total_krw']:,.0f}원 "
                                 f"({out['vat_note']}), 분할: {out['split_detail'][:160]} | 기존(견적 기반): ") + fs["detail"]
                comp["contract_total_mm"] = new_mm
                rev = rec["outcome"]["totals"].get("rev_mm_recognized")
                old_status = comp.get("status")
                if rev and "시간규칙" not in str(comp.get("rule", "")):
                    if abs(rev - new_mm) / new_mm <= 0.10:
                        comp.update({"status": "complete", "rule": f"인식 {rev} ≈ 계약총액 {new_mm} (계약서화)"})
                    elif rev < new_mm * 0.9:
                        comp.update({"status": "partial", "rule": f"인식 {rev} < 총액 {new_mm}의 90% (계약서화)"})
                row["status_change"] = f"{old_status}→{comp.get('status')}"
                changed += 1
                print(f"  🔁 {code}: {cur} → {new_mm}M ({row.get('status_change')})", flush=True)
            else:
                fs["detail"] += f" | 계약서 재독해(2026-07-27): 총액 일치 확인({new_mm}M)"
                confirmed += 1
            rec["provenance"]["notes"] += " | fee 계약서화(2026-07-27)"
            rp.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        else:
            row["skip"] = "총액 조항 없음(RS 등)"
            nofound += 1
        log.write(json.dumps(row, ensure_ascii=False) + "\n")
        log.flush()
    print(task.report(), flush=True)
    print(json.dumps({"교체": changed, "일치확인": confirmed, "총액없음/doc없음": nofound, "실패": failed},
                      ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
