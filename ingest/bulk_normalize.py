"""블록 0 일괄 정규화: Drive 원문 → 텍스트 추출 → LLM 정규화 → popup_record 초안.

- 다운로드: PDF는 전체(대개 소용량), pptx/docx/xlsx는 Range 기반 부분 zip(remotezip)으로
  텍스트 XML만 — 7.6GB 인벤토리 중 실제 수 백 MB만 전송.
- LLM: claude-opus-4-8 + json_schema 구조화 출력. rev_mm은 LLM이 아니라 P&L에서 주입.
- 재개 가능: data/records_draft/<code>.json 존재 시 스킵. 실패는 기록 후 계속.

사용: python3 -m ingest.bulk_normalize [--limit N] [--only CODE,CODE]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

INGEST = Path("data/ingest")  # 2026-07-27 스크래치패드(휘발성 임시폴더) 탈출 — 리포 내로 이관
OUT = Path("data/records_draft")
LOG = INGEST / "ingest.log"

DOC_CAPS = {"contract": 3, "proposal": 2, "event_plan": 2, "estimate": 2,
            "result_report": 3, "settlement": 1, "invoice": 1, "case_study": 1}
CHAR_CAP_DOC = {"result_report": 18000}
CHAR_CAP_DEFAULT = 10000
CHAR_CAP_PROJECT = 50000
KIND_MAP = {"contract": "계약서", "proposal": "기획서", "event_plan": "기획서",
            "estimate": "정산", "settlement": "정산", "invoice": "정산",
            "result_report": "운영일지", "case_study": "기타"}

EXTRACT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["entities", "intervention", "conditions", "outcome", "extraction_confidence", "missing_or_uncertain"],
    "properties": {
        "entities": {"type": "object", "additionalProperties": False,
                     "required": ["brand_id", "space_id", "client_party_id"],
                     "properties": {"brand_id": {"type": "string"}, "space_id": {"type": "string"},
                                     "client_party_id": {"type": ["string", "null"]}}},
        "intervention": {"type": "object", "additionalProperties": False,
                         "required": ["concept", "brand_name", "experience_elements", "promotions", "staging_tags"],
                         "properties": {"concept": {"type": "string"}, "brand_name": {"type": "string"},
                                         "experience_elements": {"type": "array", "items": {"type": "string"}},
                                         "promotions": {"type": "array", "items": {"type": "string"}},
                                         "staging_tags": {"type": "array", "items": {"type": "string"}}}},
        "conditions": {"type": "object", "additionalProperties": False,
                       "required": ["location", "area_pyeong", "period", "season", "fee_structure",
                                     "brand_requirements", "capacity"],
                       "properties": {
                           "capacity": {"type": "object", "additionalProperties": False,
                                        "required": ["access_type", "total_capacity", "detail"],
                                        "properties": {"access_type": {"type": "string",
                                                                         "enum": ["open", "session", "invite", "reservation", "unknown"]},
                                                        "total_capacity": {"type": ["integer", "null"]},
                                                        "detail": {"type": "string",
                                                                    "description": "산출 근거. 없으면 빈 문자열"}}},
                           "location": {"type": "object", "additionalProperties": False,
                                        "required": ["city", "district", "venue_name", "venue_type", "foot_traffic_context"],
                                        "properties": {k: {"type": ["string", "null"]} for k in
                                                       ["city", "district", "venue_name", "venue_type", "foot_traffic_context"]}},
                           "area_pyeong": {"type": ["number", "null"]},
                           "period": {"type": "object", "additionalProperties": False,
                                      "required": ["from", "to", "days"],
                                      "properties": {"from": {"type": "string"}, "to": {"type": "string"},
                                                      "days": {"type": ["integer", "null"]}}},
                           "season": {"type": ["string", "null"]},
                           "fee_structure": {"type": "object", "additionalProperties": False,
                                             "required": ["type", "detail"],
                                             "properties": {"type": {"type": "string",
                                                                       "enum": ["fixed", "revenue_share", "hybrid", "agency_fee", "unknown"]},
                                                             "detail": {"type": "string"}}},
                           "brand_requirements": {"type": "array", "items": {"type": "string"}}}},
        "outcome": {"type": "object", "additionalProperties": False,
                    "required": ["daily", "totals", "counting_method", "counting_basis", "plan_visitors_expected", "visit_notes"],
                    "properties": {
                        "daily": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                              "required": ["date", "visitors", "sales_krw"],
                                                              "properties": {"date": {"type": "string"},
                                                                              "visitors": {"type": ["integer", "null"]},
                                                                              "sales_krw": {"type": ["number", "null"]}}}},
                        "totals": {"type": "object", "additionalProperties": False,
                                   "required": ["visitors", "sales_krw"],
                                   "properties": {"visitors": {"type": ["integer", "null"]},
                                                   "sales_krw": {"type": ["number", "null"]}}},
                        "counting_method": {"type": "string",
                                             "enum": ["entry", "participation", "exposure", "purchase", "mixed", "unknown"],
                                             "description-주의": "visitors가 무엇을 센 숫자인가: entry=입장/방문자, participation=프로그램 참여(연인원 가능), exposure=통과/접촉/노출, purchase=구매자, mixed=혼합, unknown=보고서에 정의 없음"},
                        "counting_basis": {"type": ["string", "null"]},
                        "plan_visitors_expected": {"type": ["integer", "null"]},
                        "visit_notes": {"type": "string", "description": "없으면 빈 문자열"}}},
        "extraction_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "missing_or_uncertain": {"type": "array", "items": {"type": "string"}},
    },
}

SYSTEM = """당신은 팝업스토어 아카이브 정규화 추출기다. 프로젝트 메타데이터와 원문 문서 텍스트(계약서·기획서·견적서·결과보고서)를 받아 popup_record 필드를 추출한다.

규칙:
1. intervention(컨셉·체험요소·프로모션·연출태그)은 기획서/제안서/결과보고서에서, conditions(입지·면적·기간·수수료구조·요구사항)는 계약서/견적서에서 추출한다.
2. outcome.daily와 totals.visitors는 결과보고서의 일일/일자별 방문 표에서 실측만 뽑는다. sales_krw는 소비자 매출(POS)만 — 계약금액이 아니다.
2-1. counting_method 필수: 그 방문 숫자가 무엇을 센 것인지 판정하라 — entry(입장 게이트/계수기), participation(프로그램 참여, 존별 합산이면 연인원), exposure(통과·접촉·노출), purchase(구매 건). 보고서 표의 컬럼명·집계 방식 설명을 counting_basis에 인용하고, 정의가 없으면 unknown. 이 판정이 라벨의 단위다 — 추측으로 entry를 주지 마라.
2-2. plan_visitors_expected: 기획서의 예상 방문(총원 기준)이 있으면 숫자로. 목표 KPI와 예상이 다르면 예상 우선. outcome 실측과 절대 섞지 마라.
2-3. conditions.capacity 필수: 입장 방식을 판정하라 — open(자유입장)/session(회차·좌석제)/invite(초청제)/reservation(사전예약제). session·invite·reservation이면 total_capacity에 기간 총 수용 한도(좌석×회차×일수, 초청 인원, 예약 슬롯 합)를 계산해 넣고 detail에 산식을 적어라. 이 상한이 방문 예측의 물리적 천장이다. 자유입장이거나 근거 없으면 open/unknown + null.
3. entities는 'unresolved:<정규화이름>' 형식 (예: unresolved:성수_연무장길65_LECT). 공백 대신 _.
4. fee_structure.detail에는 계약 총액(VAT 포함 여부), 선금/중도금/잔금 분할, 수수료율, RS 조건을 숫자 그대로 기재한다.
4-1. 금액 소스 우선순위(2026-07-27 확정): **계약서(날인·서명본) 확정액 > 후속 변경합의서 > 견적서**. 견적서 총액과 계약서 총액이 다르면 계약서를 1순위로 쓰고 견적은 참고로 병기하라. 견적만 있고 계약서가 없으면 '견적 기준(계약 미확인)'을 명시하라. 검수에서 견적/계약 불일치가 major 오염의 최대 원인이었다.
5. 문서에 없는 값은 null. 지어내지 마라. 불확실하거나 문서가 부족한 항목은 missing_or_uncertain에 나열한다.
6. concept은 3문장 이내 — 이 레코드는 인덱스이고 원문 링크가 본체다.
7. 날짜는 YYYY-MM-DD."""


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def gcloud_token() -> str:
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()


class DriveReader:
    def __init__(self):
        self._tok = None
        self._tok_at = 0

    def token(self) -> str:
        if not self._tok or time.time() - self._tok_at > 2400:
            self._tok = gcloud_token()
            self._tok_at = time.time()
        return self._tok

    def url(self, fid: str) -> str:
        return f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true"

    def download(self, fid: str) -> bytes:
        import requests
        r = requests.get(self.url(fid), headers={"Authorization": f"Bearer {self.token()}"}, timeout=300)
        r.raise_for_status()
        return r.content

    def zip_texts(self, fid: str, size: int, patterns: list[str]) -> str:
        """Range 기반 부분 zip에서 XML 텍스트 추출. 실패 시 전체 다운로드 폴백(150MB 이하만)."""
        from remotezip import RemoteZip
        try:
            with RemoteZip(self.url(fid), headers={"Authorization": f"Bearer {self.token()}"}) as z:
                return self._texts_from_zip(z, patterns)
        except Exception as e:
            if size <= 150_000_000:
                data = self.download(fid)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    return self._texts_from_zip(z, patterns)
            raise e

    @staticmethod
    def _texts_from_zip(z, patterns: list[str]) -> str:
        names = z.namelist()
        out = []
        for pat in patterns:
            matched = sorted([n for n in names if re.fullmatch(pat, n)],
                             key=lambda n: int(re.search(r"(\d+)", n).group(1)) if re.search(r"(\d+)", n) else 0)
            for n in matched:
                xml = z.read(n).decode("utf-8", errors="ignore")
                texts = re.findall(r"<(?:a|w)?:?t[^>]*>([^<]*)</(?:a|w)?:?t>", xml)
                joined = " ".join(t.strip() for t in texts if t.strip())
                if joined:
                    slide = re.search(r"(\d+)", n)
                    out.append(f"[{Path(n).stem}] {joined}" if slide else joined)
        return "\n".join(out)


def extract_doc_text(reader: DriveReader, doc: dict) -> str:
    fid, mime, size = doc["drive_file_id"], doc["mime_type"] or "", int(doc["size_bytes"] or 0)
    if "pdf" in mime:
        if size > 80_000_000:
            return ""
        from pypdf import PdfReader
        pages = PdfReader(io.BytesIO(reader.download(fid))).pages
        return "\n".join((p.extract_text() or "") for p in pages)
    if "presentationml" in mime:
        return reader.zip_texts(fid, size, [r"ppt/slides/slide\d+\.xml"])
    if "wordprocessingml" in mime:
        return reader.zip_texts(fid, size, [r"word/document\.xml"])
    if "spreadsheetml" in mime:
        return reader.zip_texts(fid, size, [r"xl/sharedStrings\.xml"])
    if mime.startswith("application/vnd.google-apps"):
        import requests
        r = requests.get(f"https://www.googleapis.com/drive/v3/files/{fid}/export?mimeType=text/plain",
                         headers={"Authorization": f"Bearer {reader.token()}"}, timeout=120)
        return r.text if r.ok else ""
    return ""


def select_docs(docs: list[dict]) -> list[dict]:
    chosen = []
    for dtype, cap in DOC_CAPS.items():
        cands = [d for d in docs if d["document_type"] == dtype]
        cands.sort(key=lambda d: ("최종" not in d["file_name"], -int(d["size_bytes"] or 0)))
        chosen.extend(cands[:cap])
    return chosen


def normalize_one(client, reader: DriveReader, proj: dict, docs: list[dict], pnl_mm, task=None) -> dict | None:
    code = proj["project_code"]
    picked = select_docs(docs)
    parts, total = [], 0
    read_names = []
    for d in picked:
        if total >= CHAR_CAP_PROJECT:
            break
        try:
            text = extract_doc_text(reader, d)
        except Exception as e:
            log(f"  {code} 문서 추출 실패 ({d['file_name'][:40]}): {type(e).__name__}")
            continue
        if not text.strip():
            continue
        cap = CHAR_CAP_DOC.get(d["document_type"], CHAR_CAP_DEFAULT)
        text = text[:min(cap, CHAR_CAP_PROJECT - total)]
        total += len(text)
        read_names.append(d["file_name"])
        parts.append(f'<doc type="{d["document_type"]}" name="{d["file_name"]}">\n{text}\n</doc>')

    meta = {k: proj.get(k) for k in ["project_code", "project_name", "client_name", "venue",
                                      "category", "operating_from", "operating_to"]}
    user = (f"<project_meta>\n{json.dumps(meta, ensure_ascii=False, indent=1)}\n</project_meta>\n\n"
            f"<research_summary>\n{(proj.get('report_md') or '')[:6000]}\n</research_summary>\n\n"
            + "\n\n".join(parts)
            + "\n\n위 원문에서 popup_record 필드를 추출하라.")

    # task가 주어지면 그 경로로(api 또는 agent), 아니면 기존 API 직접 호출
    if task is not None:
        ext = task.call(f"norm-{code}", SYSTEM, EXTRACT_SCHEMA, user)
        if ext is None:
            return None      # 에이전트 모드 1패스 — 응답 대기
    else:
        with client.messages.stream(
            model="claude-opus-4-8", max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        ) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "refusal":
            raise RuntimeError(f"refusal: {resp.stop_details}")
        ext = json.loads(next(b.text for b in resp.content if b.type == "text"))
        u = resp.usage
        log(f"  {code} LLM in={u.input_tokens} cache_r={u.cache_read_input_tokens} out={u.output_tokens} "
            f"conf={ext['extraction_confidence']} docs_read={len(read_names)}")

    outcome = ext["outcome"]
    record = {
        "record_id": code,
        "schema_version": "0.1",
        "entities": ext["entities"],
        "intervention": ext["intervention"],
        "conditions": ext["conditions"],
        "outcome": {
            "daily": outcome["daily"],
            "totals": {"visitors": outcome["totals"]["visitors"],
                        "sales_krw": outcome["totals"]["sales_krw"],
                        "rev_mm_recognized": pnl_mm},
            "counting_method": outcome.get("counting_method", "unknown"),
            "counting_basis": outcome.get("counting_basis"),
            "plan_visitors_expected": outcome.get("plan_visitors_expected"),
            "retention": None,
            "source": (f"visitors/sales: 결과보고서 LLM 추출({outcome.get('visit_notes') or '표 없음'}). "
                       f"rev_mm: ods.amaranth_project_pnl 매출액 합산 스냅샷(2026-05 마감분까지) — "
                       f"진행 중 프로젝트는 부분 인식일 수 있음, 계약 총액은 fee_structure.detail 참조"),
        },
        "docs": [{"doc_id": d["drive_file_id"], "kind": KIND_MAP.get(d["document_type"], "기타"),
                   "uri": f"https://drive.google.com/file/d/{d['drive_file_id']}/view",
                   "title": d["file_name"]} for d in docs],
        "provenance": {
            "extracted_by": "llm:claude-opus-4-8(bulk-ingest)",
            "reviewed_by": None,
            "extracted_at": time.strftime("%Y-%m-%d"),
            "notes": (f"일괄 정규화. confidence={ext['extraction_confidence']}. "
                      f"완독 문서 {len(read_names)}건: {', '.join(n[:30] for n in read_names[:6])}. "
                      f"미확실: {'; '.join(ext['missing_or_uncertain']) or '없음'}"),
        },
    }
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", default=None, help="쉼표 구분 project_code")
    ap.add_argument("--projects", default=str(INGEST / "projects.json"))
    ap.add_argument("--docs", default=str(INGEST / "docs.json"))
    ap.add_argument("--agent-dir", default=None,
                    help="지정 시 에이전트 모드(2패스, 종량제 API 호출 0)")
    args = ap.parse_args()

    from core.agent_task import AgentTask
    client = None
    if not args.agent_dir:
        import anthropic
        client = anthropic.Anthropic()
    task = AgentTask("agent" if args.agent_dir else "api", args.agent_dir, client,
                     effort="medium", max_tokens=16000) if args.agent_dir else None
    reader = DriveReader()

    projects = json.loads(Path(args.projects).read_text())
    docs_all = json.loads(Path(args.docs).read_text())
    pnl = {r["project_code"]: float(r["revenue_mm"]) for r in json.loads((INGEST / "pnl.json").read_text())
           if r.get("revenue_mm") is not None}
    docs_by = {}
    for d in docs_all:
        docs_by.setdefault(d["project_code"], []).append(d)

    if args.only:
        only = set(args.only.split(","))
        projects = [p for p in projects if p["project_code"] in only]
    if args.limit:
        projects = projects[:args.limit]

    OUT.mkdir(parents=True, exist_ok=True)
    done = skipped = failed = 0
    for i, proj in enumerate(projects):
        code = proj["project_code"]
        out_path = OUT / f"{code}.json"
        if out_path.exists() or Path(f"data/records/{code}.json").exists():
            skipped += 1
            continue
        log(f"[{i+1}/{len(projects)}] {code} {(proj.get('project_name') or '(이름없음)')[:30]}")
        try:
            record = normalize_one(client, reader, proj, docs_by.get(code, []), pnl.get(code), task)
            if record is None:   # 에이전트 모드 1패스 — 응답 대기
                continue
            out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
            done += 1
        except Exception as e:
            log(f"  {code} 실패: {type(e).__name__}: {str(e)[:150]}")
            failed += 1
    log(f"완료 {done} / 스킵 {skipped} / 실패 {failed}")
    if task is not None:
        log(task.report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
