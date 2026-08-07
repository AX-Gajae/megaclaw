"""뱅크 후처리 3종: ① 계약총액 파싱→rev_mm 완결 판정 ② scale 분류 ③ 엔티티 정준화(전역).
이미 처리된 레코드는 건너뜀(재실행 안전). 과부하 재시도 내장.
사용: python3 -m ingest.postprocess
"""
import json, time, sys
from pathlib import Path
from collections import Counter
import anthropic

INGEST = Path("data/ingest")  # 2026-07-27 스크래치패드(휘발성 임시폴더) 탈출 — 리포 내로 이관
SNAP = "2026-05"
client = anthropic.Anthropic()


def llm(system, payload, schema, max_tokens=16000, effort="low"):
    for attempt in range(5):
        try:
            with client.messages.stream(model="claude-opus-4-8", max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                system=[{"type": "text", "text": system}],
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]) as s:
                resp = s.get_final_message()
            return json.loads(next(b.text for b in resp.content if b.type == "text"))
        except anthropic.APIStatusError as e:
            if attempt == 4: raise
            print(f"  API 오류 재시도 {attempt+1}: {type(e).__name__}", flush=True)
            time.sleep(25 * (attempt + 1))


def items_schema(props):
    return {"type": "object", "additionalProperties": False, "required": ["items"], "properties": {
        "items": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                              "required": list(props), "properties": props}}}}


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def save(recs, code):
    Path(f"data/records/{code}.json").write_text(json.dumps(recs[code], ensure_ascii=False, indent=2))


def main():
    recs = {p.stem: json.loads(p.read_text()) for p in Path("data/records").glob("*.json")}
    monthly = {}
    for row in json.loads((INGEST / "pnl_monthly.json").read_text()):
        monthly.setdefault(row["project_code"], []).append((row["close_period"], float(row["rev_mm"])))

    # ── ① 계약총액 → 완결 판정 ──
    todo = [c for c, r in sorted(recs.items()) if "rev_mm_completion" not in r["outcome"]]
    print(f"[1/3] 완결 판정 대상 {len(todo)}건", flush=True)
    totals = {}
    sch = items_schema({"code": {"type": "string"}, "contract_total_mm": {"type": ["number", "null"]},
                        "basis": {"type": "string"}})
    sys1 = ("각 프로젝트의 계약 조건 텍스트에서 스위트스팟이 수령하는 계약 총액을 백만원(mm) 단위로 추출. "
            "VAT 별도 기준. '6억 400만원'→604.0, '58,000,000원'→58.0. 행사 총예산·클라이언트 예산이 아니라 "
            "스위트스팟 수령분만. 불명확하면 null. basis는 20자 내 인용.")
    for batch in chunks(todo, 100):
        payload = [{"code": c, "detail": recs[c]["conditions"]["fee_structure"]["detail"][:400]} for c in batch]
        out = llm(sys1, payload, sch)
        totals.update({x["code"]: x.get("contract_total_mm") for x in out["items"]})
        print(f"  계약총액 배치 {len(totals)}/{len(todo)}", flush=True)

    for c in todo:
        r = recs[c]
        rev = r["outcome"]["totals"].get("rev_mm_recognized")
        ct = totals.get(c)
        op_to = (r["conditions"]["period"].get("to") or "")[:7]
        series = sorted(monthly.get(c, []))
        if rev is None:
            j = {"status": "no_label", "rule": "P&L 인식 없음(2026-05 스냅샷)"}
        elif ct and abs(rev - ct) / ct <= 0.10:
            j = {"status": "complete", "rule": f"인식 {rev} ≈ 계약총액 {ct}"}
        elif ct and rev < ct * 0.9:
            j = {"status": "partial", "rule": f"인식 {rev} < 총액 {ct}의 90%"}
        elif op_to and op_to <= "2026-03":
            j = {"status": "complete", "rule": f"운영종료 {op_to}, 스냅샷까지 2개월+ (시간 규칙)"}
        else:
            j = {"status": "unknown", "rule": "총액 불명·최근 종료"}
        j["contract_total_mm"] = ct
        j["last_recognition_period"] = series[-1][0] if series else None
        r["outcome"]["rev_mm_completion"] = j
        save(recs, c)
    print("  완결 분포:", dict(Counter(recs[c]["outcome"]["rev_mm_completion"]["status"] for c in todo)), flush=True)

    # ── ② scale 분류 ──
    todo2 = [c for c, r in sorted(recs.items()) if "scale" not in r["conditions"]]
    print(f"[2/3] scale 대상 {len(todo2)}건", flush=True)
    sch2 = items_schema({"code": {"type": "string"}, "store_count": {"type": "integer"},
                         "venue_traffic_type": {"type": "string",
                                                 "enum": ["standalone", "host_venue", "multi_store", "hybrid"]},
                         "host_traffic_note": {"type": ["string", "null"]}})
    sys2 = ("팝업/행사 공간 정보에서 방문 스케일 구조 분류. store_count=동시 운영 매장/부스 수(단일=1; 'N개 부스 규모'는 "
            "크기 표현이므로 1). venue_traffic_type: standalone(로드샵 자체집객)/host_venue(박람회·몰·유통 입점 — 숙주 "
            "트래픽 지배)/multi_store(2개점+)/hybrid. host_traffic_note: 숙주 트래픽 근거 인용, 없으면 null.")
    for batch in chunks(todo2, 100):
        payload = [{"code": c,
                    "venue": recs[c]["conditions"]["location"].get("venue_name"),
                    "venue_type": recs[c]["conditions"]["location"].get("venue_type"),
                    "foot": recs[c]["conditions"]["location"].get("foot_traffic_context"),
                    "concept": recs[c]["intervention"]["concept"][:120]} for c in batch]
        out = llm(sys2, payload, sch2)
        for x in out["items"]:
            if x["code"] in recs:
                recs[x["code"]]["conditions"]["scale"] = {k: x[k] for k in
                                                           ["store_count", "venue_traffic_type", "host_traffic_note"]}
                save(recs, x["code"])
        print(f"  scale 진행 {sum(1 for c in todo2 if 'scale' in recs[c]['conditions'])}/{len(todo2)}", flush=True)

    # ── ③ 엔티티 정준화 (전역 일관성 — 전체 한 번에) ──
    print("[3/3] 엔티티 정준화 (전역)", flush=True)
    sch3 = items_schema({"code": {"type": "string"}, "brand_key": {"type": "string"}, "space_key": {"type": "string"}})
    sys3 = ("엔티티 정준화. brand/space 자유 문자열을 정준 키로. 같은 실체는 반드시 같은 키(소문자·언더스코어·한글). "
            "공간은 건물/매장 단위 통일, 멀티스토어는 multi_유통 형태. 브랜드는 소비자 인식 기준. "
            "전체 목록에서 표기가 달라도 같은 실체면 병합. 모든 항목을 빠짐없이 출력하라.")
    payload = [{"code": c, "brand": recs[c]["entities"].get("brand_id"),
                "space": recs[c]["entities"].get("space_id")} for c in sorted(recs)]
    out = llm(sys3, payload, sch3, max_tokens=64000, effort="low")
    got = 0
    for x in out["items"]:
        if x["code"] in recs:
            recs[x["code"]]["entities"]["brand_key"] = x["brand_key"]
            recs[x["code"]]["entities"]["space_key"] = x["space_key"]
            save(recs, x["code"]); got += 1
    bk = Counter(recs[c]["entities"].get("brand_key") for c in recs if recs[c]["entities"].get("brand_key"))
    sk = Counter(recs[c]["entities"].get("space_key") for c in recs if recs[c]["entities"].get("space_key"))
    print(f"  정준화 {got}/{len(recs)} | 반복 브랜드 {sum(1 for v in bk.values() if v>1)} | 반복 공간 {sum(1 for v in sk.values() if v>1)}", flush=True)
    print("후처리 완료", flush=True)


if __name__ == "__main__":
    sys.exit(main())
