"""당시 뉴스·웹에서 외부 맥락을 캐낸다 — 발행일 경계를 코드로 강제하면서.

발견 루프 R1의 포렌식 에이전트들이 이미 증명했다. WebSearch로 당시 맥락을 찾아
APEC 정상회의의 뉴스 사이클 독점(RXPU2515), 추석 골든위크 종료 다음날 오픈(RTPU2534),
광장시장의 외국인 관광 상권 성격(RTPU2414)을 실제로 짚었다.
안 한 것은 그걸 절차로 고정하는 일이다.

**과거 사건의 뉴스 검색은 누출이 너무 쉽다.** "OO 팝업"으로 검색하면 사후 후기가
먼저 나오고, 그걸 피처로 쓰면 성능이 부풀려진다. 그래서 두 겹으로 막는다:

  ① 질문을 결과가 아니라 **맥락**으로만 던진다. "이 팝업이 잘됐나"가 아니라
     "그 시점에 이 IP가 어떤 상태였나 / 같은 상권에 무엇이 있었나"를 묻는다.
  ② 모든 발견에 `observed_at`(그 정보가 공개된 날짜)을 필수로 받고,
     `observed_at >= open_date`면 **코드가 자동으로 버린다.** 판단에 맡기지 않는다.

R1 포렌식이 `macro_shock`(폭설·계엄)을 스스로 '사후정보'로 분류한 전례가 있으므로
에이전트 판단도 어느 정도 믿을 수 있지만, 기계 검사를 겹쳐 두는 편이 낫다.

수집 항목 — EXTERNAL_FEATURES_PLAN.md의 B군:
  ip_catalyst          오픈 직전·직후의 IP 촉매 사건(신작 개봉·게임 발매·컴백)과 그 날짜
  ip_mobilization      인지도와 분리한 동원력 (음반 초동·단독공연 이력·팬덤 규모)
  same_ip_concurrent   같은 IP의 동시기 다른 행사 (카니발라이제이션)
  host_competition     같은 몰·상권의 동시기 경쟁 프로그램
  venue_character      상권 성격 (관광 유입·오피스·주거·대학)
  pre_buzz             오픈 **전**에 이 팝업 자체가 받은 보도

사용:
  python3 -m ingest.news_context --probe          # 조사 요청서 생성
  python3 -m ingest.news_context                  # 결과 검사(누출 검출)만
  python3 -m ingest.news_context --write          # 검사 통과분 적용
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

RECORDS = Path("data/records")
OUT = Path("cycle_log/news_context")

TMPL = """당시 맥락 조사 — {code}

**오픈일: {open_from}**  브랜드/IP: {brand}  장소: {venue} ({city})
운영: {open_from} ~ {open_to}

이 팝업이 열리기 **직전**의 세상이 어땠는지를 조사한다. 결과가 아니라 맥락이다.

## 절대 규칙 — 이걸 어기면 조사 전체가 무효다

1. **{open_from} 이전에 공개된 정보만 쓴다.** 모든 발견에 `observed_at`(그 정보가
   공개된 날짜, YYYY-MM-DD)을 반드시 적어라. 날짜를 모르면 그 발견을 버려라.
   코드가 `observed_at >= {open_from}`인 항목을 자동으로 폐기한다.
2. **이 팝업의 성과를 검색하지 마라.** 방문객·매출·후기·"흥행"·"인산인해" 같은
   결과 정보는 조사 대상이 아니다. 우연히 보이더라도 적지 마라.
3. 확인 못 한 것은 비워라. 그럴듯한 추측이 가장 나쁘다.

## 조사 항목

**ip_catalyst** — 오픈 시점 기준 이 IP의 촉매 사건
  신작 개봉·게임 발매·시즌 방영·앨범 발매·컴백 중 **오픈일에 가장 가까운 것**.
  날짜와 사건명, 오픈일과의 개월 차(음수=오픈 후 예정, 양수=오픈 전 경과).
  예: 짱구 극장판이 오픈 5주 전 개봉했다면 +1.2개월.

**ip_mobilization** — 인지도가 아니라 **동원력**
  대중 인지도(예능 노출)와 오프라인 동원력은 다르다. 유노윤호는 전국민 인지지만
  23년간 단독 콘서트가 0회였다. 음반 초동, 단독 공연 이력과 규모, 팬카페·팔로워 규모,
  국내 팬덤 비중 중 **오픈 전에 공개돼 있던 수치**만.

**same_ip_concurrent** — 같은 IP의 동시기 다른 행사
  같은 도시·광역권에서 이 팝업 기간과 겹치거나 직전 30일 내 끝난 것.
  겹치면 수요 선점, 적당한 거리면 예열이라 부호가 갈린다.

**host_competition** — 같은 숙주 안의 경쟁
  같은 몰·상권에서 같은 기간에 더 큰 프로그램이 돌았나, 아니면 경쟁 공백이었나.
  몰 뉴스룸·팝업 캘린더가 오픈 전에 공지한 것만.

**venue_character** — 상권 성격
  외국인 관광 상시 유입이 큰가(광장시장·명동·인사동), 오피스 상권인가, 대학가인가.
  숙주 몰의 개점 시기(신규성 프리미엄이 남아 있나).

**pre_buzz** — 오픈 **전** 이 팝업의 웹 발자국
  팝업 집계 플랫폼(popply·popga) 등재, 예약 링크, 사전 보도, 티저.
  **오픈 후 후기는 절대 포함하지 마라.**

## 출력

`/Users/ax/world_model/cycle_log/news_context/{code}.json` 에 스키마대로 JSON만 Write.
스키마는 같은 디렉토리의 `_schema.json`.
"""

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["code", "findings"],
    "properties": {
        "code": {"type": "string"},
        "findings": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["field", "value", "observed_at", "source", "note"],
            "properties": {
                "field": {"type": "string", "enum": ["ip_catalyst", "ip_mobilization",
                                                      "same_ip_concurrent", "host_competition",
                                                      "venue_character", "pre_buzz"]},
                "value": {"type": "string", "description": "발견 내용. 수치가 있으면 수치로"},
                "observed_at": {"type": "string",
                                "description": "이 정보가 공개된 날짜 YYYY-MM-DD. 모르면 이 항목을 버려라"},
                "source": {"type": "string", "description": "매체·URL"},
                "note": {"type": "string", "description": "방향(상방/하방)과 근거"},
            }}},
        "not_found": {"type": "array", "items": {"type": "string"},
                      "description": "확인 못 한 항목명"},
    },
}


def make_probes() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "_schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=1))
    made = []
    for p in sorted(RECORDS.glob("*.json")):
        r = json.loads(p.read_text())
        if not r["outcome"]["totals"].get("visitors"):
            continue
        per = r["conditions"].get("period") or {}
        loc = r["conditions"].get("location") or {}
        if not per.get("from"):
            continue
        (OUT / f"{r['record_id']}.probe.md").write_text(TMPL.format(
            code=r["record_id"], open_from=per["from"], open_to=per.get("to") or "?",
            brand=r["entities"].get("brand_key") or r["intervention"].get("brand_name"),
            venue=loc.get("venue_name") or r["entities"].get("space_key"),
            city=loc.get("city") or "?"))
        made.append(r["record_id"])
    print(json.dumps({"조사 요청": len(made), "디렉토리": str(OUT)}, ensure_ascii=False))
    return made


def audit(write: bool = False) -> dict:
    """결과의 발행일을 기계 검사. observed_at >= open_date면 폐기한다."""
    kept = dropped = nofile = 0
    bad_examples = []
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        f = OUT / f"{rec['record_id']}.json"
        if not f.exists():
            nofile += 1
            continue
        res = json.loads(f.read_text())
        per = rec["conditions"].get("period") or {}
        try:
            open_d = date.fromisoformat(per["from"])
        except Exception:
            continue
        ok = []
        for fd in res.get("findings") or []:
            try:
                obs = date.fromisoformat(str(fd.get("observed_at"))[:10])
            except Exception:
                dropped += 1
                bad_examples.append((rec["record_id"], fd.get("field"), "날짜 파싱 불가"))
                continue
            if obs >= open_d:
                dropped += 1
                bad_examples.append((rec["record_id"], fd.get("field"),
                                     f"공개 {obs} ≥ 오픈 {open_d}"))
                continue
            ok.append(fd)
        kept += len(ok)
        if write and ok:
            rec["conditions"].setdefault("derived", {})["news_context"] = {
                "findings": ok, "checked_against_open": per["from"],
                "dropped": len(res.get("findings") or []) - len(ok)}
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps({"통과 발견": kept, "**누출로 폐기**": dropped,
                      "결과 파일 없음": nofile, "기록": write}, ensure_ascii=False))
    for x in bad_examples[:15]:
        print(f"   폐기 {x[0]:10s} {str(x[1]):18s} {x[2]}")
    return {"kept": kept, "dropped": dropped}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.probe:
        make_probes()
        return 0
    audit(write=a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
