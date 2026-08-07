"""T1 LLM 속성 태거 — SFS-1의 최대 기대이득 모듈.

문제(실측): 표형 모델이 팝업 도메인에서 상수 중앙값을 못 이긴다. 개입(기획 내용)이 지배
변수인데 구조화되지 않아 모델이 볼 수 없기 때문. 반면 LLM은 원문을 읽어 이긴다.

LLM이 이기는 실제 근거(커밋 로그 실측):
    "롯데백화점 부산본점 일평균 입객 4~5만 × 포획률 2~4%"  ← **표에 없는 숫자**

따라서 이 모듈의 목적은 LLM을 이기는 것이 아니라 **LLM이 원문에서 뽑는 숫자·판단을 컬럼으로
옮기는 것**이다. 추론 시에는 LLM을 호출하지 않는다(오프라인 태깅 1회).

설계 원칙:
  · 숫자 우선 — 원문에만 있는 5종(숙주 일평균 입객, 기획 예상 방문/일, 회차 캐파,
    증정물 수량, 면적). 이것이 격차의 실질이다.
  · 순서형 10종은 0~4 척도로 고정 — 자유 스칼라는 소표본에서 노이즈.
  · **시간 마스크**: 기획서·계약서만 읽는다. 결과보고서는 절대 금지(라벨 누출).
  · 에이전트 2패스 경로 — 종량제 API 비용 0.

사용:
  python3 -m ingest.attr_tagger --agent-dir cycle_log/agent_tasks/attr    # 1패스(요청 덤프)
  (에이전트가 req→res 작성)
  python3 -m ingest.attr_tagger --agent-dir cycle_log/agent_tasks/attr    # 2패스(적용)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORD = ["experience_density", "goods_scale", "photo_zones", "collab_strength", "ip_awareness",
       "target_breadth", "entry_friction", "media_push", "season_fit", "venue_prominence"]
NUM = ["host_daily_traffic", "plan_visitors_per_day", "capacity_per_session",
       "giveaway_qty", "area_sqm",
       # T1c 추가 (발견 루프 R1 최다 지지 후보) — 전부 누출 없는 사전 문서 경로
       "planned_operating_days", "throughput_units", "unit_minutes",
       "operating_hours_per_day", "staff_count"]

# 물리 범위 — 벗어나면 적용 시점에 null로 떨군다. 단위를 잘못 담은 값이
# 학습 테이블에 들어가면 그 컬럼 전체가 못 쓰게 된다. (T1c 1차에서 2건 적발:
# RXPU2515 4,200만 = 신세계그룹 전사 총량, RTPU2570 50만 = 축제 기간 총량)
RANGE = {"host_daily_traffic": (50, 300_000), "plan_visitors_per_day": (5, 50_000),
         "capacity_per_session": (1, 2_000), "giveaway_qty": (1, 500_000),
         "area_sqm": (1, 20_000), "planned_operating_days": (1, 120),
         "throughput_units": (1, 200), "unit_minutes": (1, 480),
         "operating_hours_per_day": (1, 24), "staff_count": (1, 300)}


def sanitize(out: dict, record_id: str) -> tuple[dict, list]:
    """범위 이탈 수치를 null로. 무엇을 왜 떨궜는지 반환한다."""
    dropped = []
    for k, (lo, hi) in RANGE.items():
        v = out.get(k)
        if v is not None and not (lo <= v <= hi):
            dropped.append(f"{k}={v:,g} (허용 {lo:,}~{hi:,})")
            out[k] = None
    return out, dropped


SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": NUM + ORD + ["evidence", "confidence"],
    "properties": {
        **{k: {"type": ["number", "null"],
                "description": "원문에 명시된 숫자만. 없으면 null. 추정 금지."} for k in NUM},
        **{k: {"type": "integer", "minimum": 0, "maximum": 4} for k in ORD},
        "evidence": {"type": "string", "description": "숫자를 뽑은 원문 근거 위치·문구(120자 내)"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
}

SYS = """팝업스토어 기획서·계약서에서 **예측에 쓸 구조화 속성**을 추출하는 전문가다.
가장 중요한 임무는 '표에 없는 숫자'를 찾는 것이다 — 이 숫자들이 성과 예측의 실질이다.

[숫자 — 원문에 명시된 것만. 없으면 null. 절대 추정·계산하지 마라]
· host_daily_traffic: 이 팝업이 들어선 **바로 그 지점**의 일평균 입객 수.
  "OO점 일 평균 4만명" 같은 일 단위 표기만 여기 넣어라.
  다음은 전부 null이다 — 이 칸에 넣으면 안 된다:
    · 기간 총량("행사 총 관람객 30만") → 나누지 말고 null. 총량은 evidence에만.
    · 상위 조직 총량("그룹 전사 연 4,200만 집객", "전국 매장 합계")
    · 다른 지점·다른 행사의 수치
  일 단위이고 이 지점의 것이라는 두 조건이 모두 확실할 때만 채워라.
  판단이 서지 않으면 null이 정답이다. 오염된 숫자는 없는 것보다 나쁘다.
· plan_visitors_per_day: 기획서의 **예상 방문객(일 단위)**. 총원 예상만 있으면 null로 두고
  evidence에 총원을 적어라.
· capacity_per_session: 회차제·예약제면 **1회차 수용 인원**.
· giveaway_qty: 증정물·굿즈 준비 수량(총).
· area_sqm: 면적(㎡). 평 단위면 ×3.3058 환산해서 넣고 evidence에 원 단위 표기.

[아래 5개는 발견 루프가 지목한 최대 레버다. 각별히 파고들어라]
· planned_operating_days: **실제 부스가 문을 여는 날 수**. 계약서 운영기간 조항의
  휴무 제외 문구("휴무 2일 제외 총 18일"), 운영안 회차표의 행 수에서 뽑는다.
  계약 등록기간·정산기간과 다르다 — 그건 이미 conditions.period에 있고 자주 틀린다.
  비연속 다회차(주말만 운영, 격주)면 그 실제 일수를 넣고 evidence에 '비연속'을 적어라.
· throughput_units: 전원이 통과하는 **직렬 병목의 대수·좌석 수**. 포토부스 N대,
  시연 부스 N석, 상영관 좌석 수, 체험 키트 동시 인원. 견적서 장비 항목과 파일명에
  자주 노출된다("(한컷)_...(1대,3일)"). 병목이 없으면 null.
· unit_minutes: 그 병목 1인당 소요 시간(분). 회차 길이나 시연 시간에서.
· operating_hours_per_day: 일 운영 시간(시간). "11:00~20:00"이면 9.
· staff_count: 상주 인력 수. 견적서 인건비 항목의 인원(프로모터+스태프)에서.

견적서 비고란을 반드시 읽어라. 계획 인원이 원가 산정 근거로 적혀 있다 —
"1일 예상 식수 사용량 900명 기준", "18일 15,000세트 / 1일 약 830세트" 같은 형태다.
이건 기획자가 돈을 걸고 산정한 수치라 희망 섞인 목표치보다 정확하다.

[순서형 0~4 — 원문 근거로 판단. 애매하면 2]
· experience_density: 체험 요소 밀도 (0=판매만, 4=체험 존 다수·인터랙션 풍부)
· goods_scale: 굿즈 규모 (0=없음, 4=단독 상품 수십 종·한정판)
· photo_zones: 포토존 수 (0=없음, 4=4개 이상 또는 대형 설치)
· collab_strength: 콜라보 강도 (0=단독, 4=대형 IP×브랜드 공동 기획)
· ip_awareness: IP의 대중 인지 폭 (0=신규·무명, 2=마니아층, 4=전국민 인지)
· target_breadth: 타깃 폭 (0=코어 팬덤 한정, 4=전 연령 대중)
· entry_friction: 입장 허들 (0=무료 워크인, 2=대기 필요, 4=유료·사전예약 필수)
· media_push: 미디어·인플루언서 투입 (0=없음, 4=대규모 마케팅 집행 명시)
· season_fit: 시즌·시기 적합성 (0=비수기·부적합, 4=성수기·시즌 이벤트 정면)
· venue_prominence: 매장 내 위치 노출도 (0=상층 구석, 4=1층 정면·아트리움)

규칙:
1. **결과보고서·정산서는 읽지 마라** — 실측이 들어오면 라벨 누출이다.
   목록에 올라온 문서는 오픈일 이전 작성분만 걸러진 것이니 전부 읽어도 된다.
   목록에 없는 문서를 Drive에서 따로 찾아 열지 마라 — 그 필터가 시간 마스크다.
2. 숫자는 원문에 있는 것만. 근거 문구를 evidence에 인용하라.
3. 판단이 어려우면 confidence=low로 표시하되 순서형은 반드시 채워라."""


def build_user(rec: dict) -> str:
    iv, c = rec["intervention"], rec["conditions"]
    from .doc_select import describe          # 사전 문서 선별의 단일 진실 공급원
    doc_lines = describe(rec)
    return "\n".join([
        f"[레코드 {rec['record_id']}]",
        f"컨셉: {iv.get('concept')}",
        f"브랜드: {iv.get('brand_name')}",
        f"체험요소: {', '.join(iv.get('experience_elements') or []) or '기재없음'}",
        f"프로모션: {', '.join(iv.get('promotions') or []) or '기재없음'}",
        f"연출태그: {', '.join(iv.get('staging_tags') or []) or '기재없음'}",
        f"장소: {json.dumps(c.get('location'), ensure_ascii=False)}",
        f"면적(평): {c.get('area_pyeong')}",
        f"기간: {json.dumps(c.get('period'), ensure_ascii=False)}",
        f"스케일: {json.dumps(c.get('scale'), ensure_ascii=False)}",
        f"수용구조: {json.dumps(c.get('capacity'), ensure_ascii=False)}",
        f"계약 상세: {str((c.get('fee_structure') or {}).get('detail'))[:400]}",
        f"브랜드 요구사항: {', '.join(c.get('brand_requirements') or [])[:300]}",
        "",
        "원문 문서(오픈 전 작성분만 선별됨 — 필요하면 Read로 열어볼 것).",
        "견적서 비고란에 '1일 예상 N명 기준' 같은 계획 인원이 자주 적혀 있다:",
        *(doc_lines or ["  (사전 문서 없음)"]),
        "",
        "위 정보에서 스키마대로 속성을 추출하라. 숫자는 원문에 있는 것만.",
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-dir", default="cycle_log/agent_tasks/attr")
    ap.add_argument("--labeled-only", action="store_true", default=True)
    args = ap.parse_args()
    from core.agent_task import AgentTask
    task = AgentTask("agent", args.agent_dir)

    applied = pending = n_dropped = 0
    for p in sorted(Path("data/records").glob("*.json")):
        rec = json.loads(p.read_text())
        if args.labeled_only and not rec["outcome"]["totals"].get("visitors"):
            continue
        out = task.call(f"attr-{rec['record_id']}", SYS, SCHEMA, build_user(rec))
        if out is None:
            pending += 1
            continue
        out, dropped = sanitize(out, rec["record_id"])
        if dropped:
            print(f"  [범위 이탈] {rec['record_id']}: {'; '.join(dropped)}")
            n_dropped += len(dropped)
        rec["intervention"]["attributes"] = {k: out.get(k) for k in NUM + ORD}
        rec["intervention"]["attr_meta"] = {"evidence": out.get("evidence"),
                                             "confidence": out.get("confidence"),
                                             "range_dropped": dropped or None,
                                             "tagger": "T1c (2026-07-28) 사전문서 층화선별"}
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        applied += 1
    print(json.dumps({"적용": applied, "대기": pending, "범위이탈 제거": n_dropped},
                     ensure_ascii=False))
    print(task.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
