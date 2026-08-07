"""라벨 위생 — 채점 직전에 서는 게이트.

발견 루프 1라운드의 결론: 상위 미스 14건 중 3건이 `label_problem`이고, 나머지에도
스코프 오염이 섞여 있었다. 지금 '모델 오차'라 부르는 것의 일부는 **측정 오차**다.
피처를 늘리기 전에 이걸 먼저 세우지 않으면, 개선을 측정할 기준선 자체가 흔들린다.

검출하는 결함 (모두 사전 관측 가능 — 사후 정보 아님):

  D1 digital_proxy   라벨이 QR·구독·응모·대기열 등 디지털 프록시 수치다.
                     발자국(footfall)과 물리량이 다르므로 같은 풀에서 채점하면 안 된다.
  D2 window_disjoint 라벨의 실제 창(label_scope)이 period와 **전혀 겹치지 않는다**.
                     계획이 바뀌는 건 결함이 아니다 — 겹치지 않는 건 이 라벨이 다른
                     레그·다른 행사의 것이라는 뜻이다(RTPU2412: 계획 6월, 라벨 8월).
  D3 thin_counting   집계기준 표본이 n<3이라 그 단위의 보정 선례가 뱅크에 없다.
                     예측기에 단위를 주면 전환율을 지어낸다(RXPU2411 'purchase' 단독 ÷10).
  D4 span_mismatch   daily 행 수와 운영일수가 2배 이상 어긋나는데 label_scope를 유도하지
                     못해 어느 쪽이 진실인지 모른다(월 단위 daily 등).
  D5 stale_report    라벨이 철회(visitors=None)됐는데 채점 리포트가 남아 있다.
  D6 plan_overshoot  기획자가 원가를 걸고 산정한 계획 인원의 3배를 넘는다. 대개 라벨이
                     부스가 아니라 행사 전체를 센다. 단위가 exposure면 물리량이 달라 제외.
  D7 sum_conflict    daily 합이 총계와 어긋난다. 총계가 순방문·daily가 연방문이면 이렇게
                     되는데, 단위가 다르면 같은 풀에서 채점할 수 없다.
  D8 giveaway_ceiling 라벨이 증정물 준비 수량과 사실상 같다. 증정물 소진으로 방문객을
                     세면 수량이 떨어질 때 계수가 멈추므로 라벨이 하한이 되고,
                     giveaway_qty 피처는 라벨을 그대로 읽는 셈이 된다.

날짜 정규화가 선행 조건이다 — daily.date가 ISO/'11/1'/'11월 5일'/'2024-10' 네 포맷으로
섞여 있어 문자열 비교가 헛돈다(576행 중 23행). 연도는 period.from에서 보충한다.

사용:
  python3 -m harness.label_hygiene audit          # 전수 감사
  python3 -m harness.label_hygiene pools          # 채점 풀 분리 결과
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

RECORDS = Path("data/records")
REPORT = Path("cycle_log/label_hygiene.json")

# 디지털 프록시 — 물리 발자국이 아닌 것
DIGITAL_PROXY = re.compile(
    r"QR|큐알|스캔|구독|응모|리드\s*수|대기열\s*등록|웨이팅\s*등록|도달\s*수|댓글\s*수|"
    r"팔로워|좋아요|조회\s*수|클릭")
# 위 단어가 있어도 실계수 근거가 함께 있으면 프록시가 아니다
FOOTFALL_OK = re.compile(r"게이트|입장\s*계수|계수기|턴스타일|비콘|출입|카운터|POS|영수증")
# 집계기준 표본이 이보다 적으면 보정 선례가 없다고 본다
MIN_UNIT_N = 3
# 계획 인원 대비 실측이 이 배수를 넘으면 스코프 오염을 의심한다.
# 단일 장소 15건 실측 분포: p25 61% / 중앙 83% / p75 119%, 정상 상단이 1.4배 부근.
PLAN_RATIO_MAX = 3.0
# 라벨이 증정물 준비 수량에 이만큼 이내로 **도달**하면 상한에 걸린 것으로 본다.
# 이 경우 라벨은 계수가 아니라 **하한**이고, giveaway_qty는 피처가 아니라 라벨 자신이다.
GIVEAWAY_CEIL_TOL = 0.02


def norm_date(s, year_hint: str | None = None) -> str | None:
    """혼재된 daily.date를 ISO(YYYY-MM-DD)로. 월단위('2024-10')는 해석 불가로 None."""
    s = str(s or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    yr = (year_hint or "")[:4]
    m = re.fullmatch(r"(\d{1,2})\s*[/.]\s*(\d{1,2})", s) or \
        re.fullmatch(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일?", s)
    if m and yr.isdigit():
        return f"{yr}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None                       # 'YYYY-MM' 등 일 단위가 없는 것은 판정 보류


def _unit_counts() -> Counter:
    c = Counter()
    for p in sorted(RECORDS.glob("*.json")):
        r = json.loads(p.read_text())
        if r["outcome"]["totals"].get("visitors"):
            c[r["outcome"].get("counting_method") or "unknown"] += 1
    return c


def audit_record(rec: dict, unit_n: Counter) -> list[dict]:
    """레코드 하나의 결함 목록. 빈 리스트면 채점 적격."""
    o, c = rec["outcome"], rec["conditions"]
    v = o["totals"].get("visitors")
    defects: list[dict] = []
    if not v:
        return defects                                    # 라벨 없음 — 애초에 채점 대상 아님

    # D1 — 디지털 프록시
    blob = json.dumps({"p": o.get("provenance"), "t": o.get("label_trust"),
                       "n": o.get("notes")}, ensure_ascii=False)
    if o.get("measurement_instrument") and o.get("counting_detail") != "digital_proxy":
        pass          # 재검증이 계측 도구를 확정한 건 — 산문에 프록시 어휘가 있어도 실계수다
                      # (RTPU2534: '웨이팅 등록'이라는 말은 있지만 라벨은 등록−노쇼 입장 로그)
    elif o.get("counting_detail") == "digital_proxy":
        defects.append({"code": "D1", "kind": "digital_proxy",
                        "detail": "재발굴이 디지털 프록시로 확정 — 물리 발자국이 아님"})
    else:
        hits = DIGITAL_PROXY.findall(blob)
        if hits and not FOOTFALL_OK.search(blob):
            defects.append({"code": "D1", "kind": "digital_proxy",
                            "detail": f"프록시 어휘 {sorted(set(hits))[:3]} · 실계수 근거 없음"})

    # D2 — 창 불일치. label_scope(ingest/label_scope.py)가 라벨의 실제 창을 유도해 둔다.
    #      period는 '계획된 창'이고 label_scope는 '실제 일어난 일'이라 다를 수 있다.
    #      계획이 바뀌는 건 결함이 아니다. 겹치지 않는 것이 결함이다 —
    #      그건 이 라벨이 다른 레그·다른 행사의 것이라는 뜻이다(RTPU2412: 계획 6월, 라벨 8월).
    per = c.get("period") or {}
    ls = o.get("label_scope") or {}
    daily = o.get("daily") or []
    if ls.get("label_from") and per.get("from") and per.get("to"):
        if ls["label_to"] < per["from"] or ls["label_from"] > per["to"]:
            defects.append({"code": "D2", "kind": "window_disjoint",
                            "detail": f"라벨 창 {ls['label_from']}~{ls['label_to']} 이 "
                                      f"period {per['from']}~{per['to']} 과 전혀 겹치지 않음"})
    elif not ls and daily:
        ds = [d for d in (norm_date(x.get("date"), per.get("from")) for x in daily) if d]
        if ds and per.get("from") and per.get("to") and (min(ds) < per["from"] or max(ds) > per["to"]):
            defects.append({"code": "D2", "kind": "scope_drift",
                            "detail": f"daily {min(ds)}~{max(ds)} 가 period 밖 (label_scope 미유도)"})

    # D7 — daily 합이 총계와 어긋난다. 총계가 순방문이고 daily가 연방문이면 이렇게 되는데,
    #      단위가 다르면 같은 풀에서 채점할 수 없다. 원문 없이는 판정 불가라 재발굴 대상.
    if ls.get("sum_agrees") is False:
        defects.append({"code": "D7", "kind": "sum_conflict",
                        "detail": ls.get("source", "")})

    # D3 — 얇은 집계기준
    cm = o.get("counting_method") or "unknown"
    if cm != "unknown" and unit_n.get(cm, 0) < MIN_UNIT_N:
        defects.append({"code": "D3", "kind": "thin_counting",
                        "detail": f"집계기준 '{cm}' 뱅크 표본 {unit_n.get(cm,0)}건 (<{MIN_UNIT_N})"})

    # D4 — 기간 불일치. 문서에서 읽은 실운영일수가 있으면 그것과 비교한다.
    # period 기반 days는 계약등록창인 경우가 잦아(51건 중 12건) 그것과 비교하면
    # T1c가 이미 해결한 건까지 결함으로 잡힌다.
    at0 = (rec.get("intervention") or {}).get("attributes") or {}
    if not ls.get("label_active_days"):
        days = (at0.get("planned_operating_days")
                or ((c.get("derived") or {}).get("duration") or {}).get("days"))
        src = "문서" if at0.get("planned_operating_days") else "period"
        month_only = daily and all(re.fullmatch(r"\d{4}-\d{2}", str(x.get("date") or ""))
                                   for x in daily)
        if (days and len(daily) >= 2 and not month_only
                and (len(daily) / days > 2 or days / len(daily) > 2)):
            defects.append({"code": "D4", "kind": "span_mismatch",
                            "detail": f"daily {len(daily)}행 vs 운영일수 {days:g}({src}) — "
                                      f"label_scope 미유도라 어느 쪽이 진실인지 모름"})

    # D8 — 라벨이 증정물 준비 수량과 사실상 같다.
    #      증정물 소진량으로 방문객을 세는 관행이 있는데(입장 시 1매 증정), 준비 수량이
    #      떨어지면 그 시점에 계수가 멈춘다. 그러면 라벨은 계수가 아니라 하한이고,
    #      giveaway_qty 피처는 라벨을 그대로 읽는 셈이 된다.
    #      전수 36건 중 3건이 2% 이내였고, 그중 2건은 정확히 일치했다.
    #      **상한에 도달한 경우만** 잡는다. 잔여가 있으면 소진이 멈춘 게 아니라
    #      실제로 그만큼만 나간 것이므로 정상 계수다(RTPU2433: 2,000 중 1,975, 잔여 25).
    gq = at0.get("giveaway_qty")
    #      라벨이 준비 수량보다 훨씬 크면 두 수량은 무관하다(증정물이 일부 프로모션인 경우).
    #      상한에 정확히 걸린 구간 — 준비 수량 이상이되 그 바로 위 — 만 의심한다.
    if gq and gq > 0 and gq <= v <= gq * (1 + GIVEAWAY_CEIL_TOL):
        defects.append({"code": "D8", "kind": "giveaway_ceiling",
                        "detail": f"라벨 {v:,} ≈ 증정물 준비 {gq:,.0f} — 상한 절단 의심. "
                                  f"라벨은 하한이고 giveaway_qty는 피처가 아니다"})

    # D6 — 계획 대비 실측 과다. 기획자가 원가를 걸고 산정한 계획 인원의 몇 배가 나오면
    #      대개 라벨이 부스가 아니라 행사 전체를 세고 있다(스코프 오염).
    #      다중 점포 레코드는 계획이 레그당·실측이 합계라 정상적으로 커지므로 제외.
    at = at0
    pv = at.get("plan_visitors_per_day")
    sc = c.get("scale") or {}
    multi = (sc.get("store_count") or 1) > 1 or str(rec["entities"].get("space_key") or "").startswith("multi_")
    d_eff = (ls.get("label_active_days") or at.get("planned_operating_days")
             or ((c.get("derived") or {}).get("duration") or {}).get("days"))
    if pv and d_eff and not multi and cm not in ("exposure",):
        ratio = (v / d_eff) / pv
        if ratio > PLAN_RATIO_MAX:
            defects.append({"code": "D6", "kind": "plan_overshoot",
                            "detail": f"계획 {pv:,.0f}/일 대비 실측 {v/d_eff:,.0f}/일 = {ratio:.1f}배"})
    return defects


def _stale_reports() -> list[dict]:
    """D5 — 라벨이 철회됐는데 남아 있는 채점 리포트."""
    out, seen = [], set()
    for f in sorted(Path("cycle_log").rglob("*.report.md")):
        code = f.stem.replace(".report", "")
        if code in seen:
            continue
        p = RECORDS / f"{code}.json"
        if not p.exists():
            continue
        cur = json.loads(p.read_text())["outcome"]["totals"].get("visitors")
        m = re.search(r"visitors.*?예측 [\d,]+ / 실측 ([\d,]+)", f.read_text())
        if not m:
            continue
        scored = int(m.group(1).replace(",", ""))
        if cur is None:
            seen.add(code)
            out.append({"code": code, "path": str(f), "scored_against": scored,
                        "reason": "라벨 철회됨(visitors=None)"})
        elif cur != scored:
            seen.add(code)
            out.append({"code": code, "path": str(f), "scored_against": scored,
                        "current": cur, "reason": "라벨이 변경됨 — 리포트가 옛 값으로 채점"})
    return out


def audit() -> dict:
    unit_n = _unit_counts()
    per_rec, by_kind = {}, Counter()
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        d = audit_record(rec, unit_n)
        if d:
            per_rec[rec["record_id"]] = d
            for x in d:
                by_kind[x["kind"]] += 1
    stale = _stale_reports()
    labeled = sum(unit_n.values())
    res = {"라벨 보유": labeled, "결함 레코드": len(per_rec),
           "채점 적격": labeled - len(per_rec),
           "결함 종류별": dict(by_kind), "stale_report": len(stale),
           "집계기준 표본": dict(unit_n), "상세": per_rec, "stale": stale}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def eligible(rec: dict, unit_n: Counter | None = None) -> tuple[bool, str]:
    """채점 적격 판정. D1/D2는 제외, D3/D4는 경고(단위만 강등)."""
    d = audit_record(rec, unit_n if unit_n is not None else _unit_counts())
    hard = [x for x in d if x["code"] in ("D1", "D2")]
    if hard:
        return False, "; ".join(f"{x['code']} {x['detail']}" for x in hard)
    return True, "; ".join(f"{x['code']} {x['detail']}" for x in d)


def safe_counting_method(rec: dict, unit_n: Counter | None = None) -> str:
    """[D3] 표본이 얇은 집계기준은 'unknown'으로 강등 — 예측기가 전환율을 지어내지 못하게."""
    un = unit_n if unit_n is not None else _unit_counts()
    cm = rec["outcome"].get("counting_method") or "unknown"
    return cm if un.get(cm, 0) >= MIN_UNIT_N else "unknown"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "remine":
        remine_briefs()
        return 0
    if cmd == "regrade":
        regrade_briefs()
        return 0
    r = audit()
    print(json.dumps({k: v for k, v in r.items() if k not in ("상세", "stale")},
                     ensure_ascii=False, indent=1))
    if cmd == "audit":
        print("\n■ 결함 레코드")
        for code, ds in r["상세"].items():
            print(f"  {code}")
            for x in ds:
                print(f"     [{x['code']}] {x['kind']}: {x['detail']}")
        if r["stale"]:
            print("\n■ stale 리포트 (라벨 철회·변경 후 남은 채점)")
            for s in r["stale"]:
                cur = s.get("current", "None")
                print(f"  {s['code']}: {s['scored_against']:,}로 채점 / 현재 {cur} — {s['reason']}")
    return 0




REMINE_TMPL = """라벨 재발굴 — {code}

이 레코드의 라벨에 결함이 있다. **원문에서 진실을 다시 캐라.**

현재 상태:
  총 방문객   {total}
  집계기준    {counting}  /  신뢰등급 {grade}
  계획 기간   {per_from} ~ {per_to}   (conditions.period — 계획된 창)
  라벨 실제창 {ls}
  daily       {n_daily}행, 합 {dsum}

검출된 결함:
{defects}

조사 방법:
1. Read로 `data/records/{code}.json` 전체.
2. **결과보고서·정산서를 읽어라** — 라벨 발굴이므로 사후 문서가 정답지다.
   docs[]에서 kind가 '정산'이거나 파일명에 결과보고·정산·실적이 든 것을 골라
   ToolSearch로 mcp__claude_ai_Google_Drive__read_file_content 를 로드해 열어라
   (uri의 /file/d/<ID>/view 에서 ID).
3. 다음을 확정하라:
   - 총 방문객의 **정확한 값**과 그 숫자가 원문 어디에 있는지
   - 그 숫자가 **무엇을 센 것인지**: unique_entry(순방문) / visits(연방문) /
     participation(체험 참여) / exposure(통과 노출) / purchase(구매) / digital(QR·응모)
   - 그 숫자가 **무엇의 범위인지**: 이 부스만인가, 행사 전체인가, 여러 점포 합계인가
   - 실제 운영한 날짜들

판정 규칙:
  · 원문에서 확정할 수 없으면 `resolved=false`로 두고 무엇이 부족한지 적어라.
    추측으로 숫자를 만들지 마라 — 틀린 라벨보다 없는 라벨이 낫다.
  · 총계와 daily가 다른 것을 세고 있다면 그 사실 자체가 답이다(단위 불일치).
  · 라벨이 이 부스가 아니라 행사 전체를 센 것이면 `scope='event_wide'`로 표시하고
    부스 단위 숫자가 원문에 따로 있는지 찾아라.
"""

REMINE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["code", "resolved", "verdict", "evidence"],
    "properties": {
        "code": {"type": "string"},
        "resolved": {"type": "boolean", "description": "원문에서 확정했는가"},
        "visitors": {"type": ["number", "null"], "description": "확정된 총 방문객. 미확정이면 null"},
        "counting": {"type": ["string", "null"],
                     "enum": ["unique_entry", "visits", "participation", "exposure",
                              "purchase", "digital_proxy", None]},
        "scope": {"type": ["string", "null"],
                  "enum": ["this_booth", "event_wide", "multi_store_sum", "one_leg", None]},
        "active_days": {"type": ["number", "null"]},
        "date_from": {"type": ["string", "null"]},
        "date_to": {"type": ["string", "null"]},
        "verdict": {"type": "string",
                    "description": "라벨을 어떻게 처리해야 하는지 한 문장"},
        "evidence": {"type": "string", "description": "원문 근거 문구와 위치"},
        "missing": {"type": "string", "description": "미확정이면 무엇이 부족한지"},
    },
}


def remine_briefs(out_dir: str = "cycle_log/relabel") -> list[str]:
    """결함 레코드별 재발굴 요청서를 낸다. 결함 목록이 곧 질문이 되게."""
    unit_n = _unit_counts()
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        defects = audit_record(rec, unit_n)
        if not defects:
            continue
        o, c = rec["outcome"], rec["conditions"]
        per = c.get("period") or {}
        ls = o.get("label_scope") or {}
        body = REMINE_TMPL.format(
            code=rec["record_id"], total=f"{o['totals'].get('visitors'):,}",
            counting=o.get("counting_method"), grade=(o.get("label_trust") or {}).get("grade"),
            per_from=per.get("from"), per_to=per.get("to"),
            ls=(f"{ls.get('label_from')} ~ {ls.get('label_to')} "
                f"({ls.get('label_active_days')}일, "
                f"{'연속' if ls.get('label_contiguous') else '비연속'})" if ls else "유도 실패"),
            n_daily=len(o.get("daily") or []),
            dsum=f"{ls.get('daily_sum'):,}" if ls.get("daily_sum") else "없음",
            defects="\n".join(f"  [{x['code']}] {x['kind']}: {x['detail']}" for x in defects))
        (d / f"{rec['record_id']}.remine.md").write_text(body)
        made.append(rec["record_id"])
    (d / "_schema.json").write_text(json.dumps(REMINE_SCHEMA, ensure_ascii=False, indent=1))
    print(json.dumps({"재발굴 요청": len(made), "디렉토리": str(d),
                      "대상": made}, ensure_ascii=False))
    return made



REGRADE_TMPL = """라벨 등급 검증 — {code}

이 레코드는 신뢰등급 **{grade}**({why})라 평가 풀에서 빠져 있다. 그런데 일별 계열이
기간을 완결하고 합이 총계와 일치한다. 등급 사유가 라벨 자체가 아니라 문서 다른 곳의
표현에서 발화했을 가능성이 있다 — 실제로 RTPU2528이 그랬다(등급 E 사유가
'예상치 재활용·추산 표현'이었는데, 그 추산 표현은 우리가 라벨로 쓰지 않은
헤드라인 '약 3.6천명'이었고 라벨 2,000은 리플렛 실측 소진량이었다).

현재 상태:
  총 방문객   {total}     집계 {counting}
  운영        {ls_from} ~ {ls_to} ({days}일, {contig})
  daily       {n_daily}행, 합 {dsum} — 총계와 일치
  등급 사유   {why}

**단 하나만 판정하라: 이 숫자는 측정된 것인가, 유도된 것인가.**

  measured    게이트·POS·카운터·계수기·증정물 소진 등 물리적 계수의 결과.
              계측 도구가 무엇인지 원문에 나와야 한다.
  derived     다른 수치에서 산식으로 만들어낸 값.
              반례가 실제로 있었다: RTPU2412의 일별 계열은 완결돼 있지만
              웨이팅 등록 6,195건 × 3(일행 3인 가정)이었다. 완결된 계열이
              곧 측정치는 아니다.
  reused      기획 단계의 예상치를 결과에 그대로 옮겨 적은 것.

조사:
1. Read로 `data/records/{code}.json`.
2. 결과보고서·정산서를 열어라(라벨 검증이므로 사후 문서가 정답지다).
   MCP 리더가 한컴 저장본·대용량 pptx를 거부하면 gcloud 토큰 + Drive REST
   `files/<ID>?alt=media` 로 받아 로컬에서 열어라. 임시 파일은 $CLAUDE_JOB_DIR/tmp 에.
3. 일별 표의 **열 이름과 산출 근거**를 그대로 인용하라. 그것이 판정의 전부다.
   '방문객'이라 쓰여 있어도 각주에 환산식이 있으면 derived다.

판정 후 등급 제안:
  measured + 일별 완결        → A
  measured + 계측 단위에 가정 있음(1인당 vs 1팀당 불명 등)  → B
  derived / reused            → 현 등급 유지
확정할 수 없으면 `resolved=false`로 두라. 등급을 올리면 그 라벨이 평가 풀에 들어가므로,
잘못 올리면 모든 측정이 오염된다. 애매하면 올리지 않는 쪽이 맞다.
"""

REGRADE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["code", "resolved", "origin", "evidence"],
    "properties": {
        "code": {"type": "string"},
        "resolved": {"type": "boolean"},
        "origin": {"type": "string", "enum": ["measured", "derived", "reused", "unknown"]},
        "instrument": {"type": ["string", "null"],
                       "description": "measured면 계측 도구(게이트·POS·카운터·소진량 등)"},
        "proposed_grade": {"type": ["string", "null"], "enum": ["A", "B", "C", "D", "E", None]},
        "column_quote": {"type": ["string", "null"], "description": "일별 표의 열 이름 원문 인용"},
        "evidence": {"type": "string"},
        "missing": {"type": "string"},
    },
}


def regrade_briefs(out_dir: str = "cycle_log/regrade") -> list[str]:
    """C/D/E인데 일별 계열이 완결된 건 — 등급 사유가 라벨이 아닌 곳에서 왔을 수 있다."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        o = rec["outcome"]
        v = o["totals"].get("visitors")
        tr = o.get("label_trust") or {}
        ls = o.get("label_scope") or {}
        if not v or tr.get("grade") not in ("C", "D", "E"):
            continue
        if ls.get("sum_agrees") is not True:
            continue
        if o.get("counting_detail") == "estimated_from_registrations":
            continue                      # 이미 유도치로 확정된 건
        (d / f"{rec['record_id']}.regrade.md").write_text(REGRADE_TMPL.format(
            code=rec["record_id"], grade=tr.get("grade"), why=tr.get("why", ""),
            total=f"{v:,}", counting=o.get("counting_method"),
            ls_from=ls.get("label_from"), ls_to=ls.get("label_to"),
            days=ls.get("label_active_days"),
            contig="연속" if ls.get("label_contiguous") else "비연속",
            n_daily=len(o.get("daily") or []), dsum=f"{ls.get('daily_sum'):,}"))
        made.append(rec["record_id"])
    (d / "_schema.json").write_text(json.dumps(REGRADE_SCHEMA, ensure_ascii=False, indent=1))
    print(json.dumps({"등급 검증 요청": len(made), "디렉토리": str(d), "대상": made},
                     ensure_ascii=False))
    return made

if __name__ == "__main__":
    raise SystemExit(main())
