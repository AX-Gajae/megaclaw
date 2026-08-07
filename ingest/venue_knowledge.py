"""T1b 세계지식 태거 — 장소의 유동 규모를 LLM 세계지식으로 추정.

T1(원문 태깅)의 결정적 한계(2026-07-27 실측): host_daily_traffic 확보율 9%.
기획서·계약서에는 **몰 자점 입객수가 기재되지 않는다**(태거 10개 배치 중 다수가 같은 관찰 보고).
즉 LLM이 예측에 쓰는 "롯데백화점 부산본점 일평균 입객 4~5만 × 포획률 2~4%"는 원문이 아니라
LLM의 세계지식이다. 따라서 그것을 옮기려면 원문 추출이 아니라 **세계지식 질의**가 필요하다.

**누출 차단 설계(가장 중요)**:
  LLM이 "이 팝업 5만 명 왔었지"를 알고 역산하면 라벨 누출이다. 그래서 이 태거는
  **팝업·브랜드·IP·기간을 일절 주지 않고 장소만** 묻는다. 입력은 "더현대 서울 B2 팝업존"
  같은 장소 문자열 하나뿐이므로 특정 팝업의 결과를 역산할 경로가 없다.
  또한 장소 단위로 1회만 태깅해 여러 레코드가 공유한다(73개 장소 ← 95개 레코드).

산출:
  venue_daily_footfall  장소(몰·건물·행사장) 전체의 평상시 일평균 방문객
  popup_zone_pass_rate  그 안의 팝업존을 지나가는 비율 0~1
  venue_scale_tier      1(초대형)~5(소형)
  seasonality_note      성수기/비수기 특성
  confidence            high/medium/low
  → 파생: host_traffic_est = venue_daily_footfall × popup_zone_pass_rate

사용:
  python3 -m ingest.venue_knowledge --agent-dir cycle_log/agent_tasks/venue   # 1패스
  (에이전트 처리)
  python3 -m ingest.venue_knowledge --agent-dir cycle_log/agent_tasks/venue   # 2패스 적용
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["venue_daily_footfall", "popup_zone_pass_rate", "venue_scale_tier",
                 "seasonality_note", "confidence", "reasoning"],
    "properties": {
        "venue_daily_footfall": {"type": ["number", "null"],
                                  "description": "장소 전체의 평상시 일평균 방문객(명). 모르면 null"},
        "popup_zone_pass_rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1,
                                  "description": "그 장소 방문객 중 팝업존을 지나가는 비율"},
        "venue_scale_tier": {"type": "integer", "minimum": 1, "maximum": 5},
        "seasonality_note": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reasoning": {"type": "string", "description": "추정 근거 150자 내"},
    },
}

SYS = """한국 리테일·전시 공간의 유동 규모를 추정하는 전문가다.

주어지는 것은 **장소 이름 하나뿐**이다. 그 장소에 대해 아는 것(업계 공개 자료, 언론 보도,
일반적 규모 감각)으로 다음을 추정하라.

· venue_daily_footfall: 그 장소(몰·백화점·건물·행사장) **전체**의 평상시 일평균 방문객 수.
  - 대형 복합몰(스타필드 하남·롯데월드몰): 대략 5~10만
  - 도심 대형 백화점(더현대 서울·신세계 강남): 대략 3~6만
  - 지역 백화점·중형몰: 대략 1~3만
  - 스트리트 상권(성수·홍대·한남 특정 건물): 건물 단위면 수백~수천
  - 전시장(코엑스·킨텍스): 행사 없는 평상시가 아니라 **행사 개최 시** 기준으로 추정하고
    reasoning에 그 전제를 적어라
  모르면 null. 억지로 채우지 마라.

· popup_zone_pass_rate: 그 장소 방문객 중 팝업존 앞을 실제로 지나가는 비율(0~1).
  - 1층 아트리움·정문 정면: 0.5~0.8
  - 지하 식품관 연결부·에스컬레이터 정면: 0.3~0.5
  - 상층 팝업존·구석: 0.1~0.25
  장소 문자열에 층·위치 정보가 없으면 그 장소의 통상적 팝업 운영 위치로 판단하라.

· venue_scale_tier: 1=전국 최상위 유동, 2=대형, 3=중형, 4=소형, 5=단독 매장·비전형

**중요**: 특정 팝업이나 브랜드에 대해 묻는 것이 아니다. 어떤 팝업이 열렸는지 추측하거나
그 결과를 떠올려 역산하지 마라. 오직 장소 자체의 물리적 유동 규모만 추정한다.
확신이 낮으면 confidence=low로 표시하고 범위 중앙값을 쓰라."""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-dir", default="cycle_log/agent_tasks/venue")
    args = ap.parse_args()
    from core.agent_task import AgentTask
    task = AgentTask("agent", args.agent_dir)

    venues = json.loads(Path("cycle_log/t1b_venues.json").read_text())
    known = {}
    applied = pending = 0
    for v in venues:
        name = v["venue"]
        if name in ("미상", "", None):
            continue
        key = re.sub(r"[^0-9A-Za-z가-힣]", "_", name)[:40]
        out = task.call(f"venue-{key}", SYS, SCHEMA, f"장소: {name}\n\n이 장소의 유동 규모를 추정하라.")
        if out is None:
            pending += 1
            continue
        known[name] = out
        applied += 1

    if known:
        Path("data/state/venue_knowledge.json").write_text(json.dumps(known, ensure_ascii=False, indent=1))
        # 레코드에 파생 피처 주입
        n = 0
        for p in sorted(Path("data/records").glob("*.json")):
            r = json.loads(p.read_text())
            if not r["outcome"]["totals"].get("visitors"):
                continue
            loc = r["conditions"].get("location") or {}
            sk = r["entities"].get("space_key")
            name = (sk if sk and sk != "미상" else None) or loc.get("venue_name")
            k = known.get(str(name))
            if not k:
                continue
            f, pr = k.get("venue_daily_footfall"), k.get("popup_zone_pass_rate")
            r["conditions"]["venue_knowledge"] = {
                "venue_daily_footfall": f, "popup_zone_pass_rate": pr,
                "host_traffic_est": (f * pr) if (f and pr) else None,
                "venue_scale_tier": k.get("venue_scale_tier"),
                "confidence": k.get("confidence"),
                "source": "T1b 세계지식 태거(2026-07-28) — 장소만 질의, 팝업 정보 미제공",
            }
            p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
            n += 1
        print(json.dumps({"장소 태깅": applied, "레코드 주입": n}, ensure_ascii=False))
    print(json.dumps({"대기": pending}, ensure_ascii=False))
    print(task.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
