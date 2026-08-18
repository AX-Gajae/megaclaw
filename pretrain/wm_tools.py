# -*- coding: utf-8 -*-
"""월드모델 «도구층» — LLM 하네스가 부르는 계약(manifest + 구현).

설계 원칙:
  · 도구가 «할 수 있는 일»은 이 파일의 MANIFEST 가 전부다 — 하네스 LLM 은
    추측하지 않고 스키마를 읽는다 (wm_model_card 가 한계·수치까지 준다)
  · 모든 수치 답에는 구간(q05~q95)이 붙고, 모든 응답에 «한계» 필드가 붙는다
  · 시나리오는 «변환 연산»으로 조합한다(curve_scale·date_shift·trend_boost·domain)
    — LLM 이 곡선을 지어내지 않고 검증된 변환만 쓰게 한다

소비자: pretrain/mcp_server.py (Claude 하네스) · serve.py /api/tool (HTTP 하네스)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import json
import os

import numpy as np

import pretrain.serve as S          # 모형 적재·헬퍼 재사용(창구와 같은 체크포인트)

CAVEAT = ("조건부 예측이지 인과가 아니다(「언제」= 크롤 시각) · 90% 구간 실측 덮개율 "
          "59.6%(미보정 — 구간을 보수적으로 읽어라) · 개체 분리 검증 MdAPE 8.5%")


def _parse_curve(curve):
    if isinstance(curve, (int, float)):
        vals = [float(curve)] * 90
    elif isinstance(curve, list):
        vals = [float(v) for v in curve]
    else:
        vals = [float(v) for v in str(curve).replace(",", " ").split() if v.strip()]
        if len(vals) == 1:
            vals = vals * 90
    if len(vals) != 90:
        raise ValueError("곡선은 90 개(또는 1 개=평탄) — 지금 %d 개" % len(vals))
    if any(v < 0 for v in vals):
        raise ValueError("음수 조회수는 없다")
    return vals


def _forecast_full(vals, domain, date):
    sc, cond, base = S._features_from_raw(vals, domain, date)
    q = S._quant_curves(sc, cond, base)                  # (91,5) log
    cum = np.expm1(q).cumsum(axis=0)
    def cell(t):
        return {k: int(cum[t, j]) for j, k in enumerate(("q05", "q25", "q50", "q75", "q95"))}
    return {"누적": {"7일": cell(6), "30일": cell(29), "90일": cell(90)},
            "일별 q50(1·7·30·60·90일째)":
                [round(float(np.expm1(q[i, 2])), 1) for i in (0, 6, 29, 59, 90)]}


# ── 도구 구현 ─────────────────────────────────────────────────────────
def wm_model_card(**_):
    tri = json.load(open(os.path.join(S.TRI, "report.json"), encoding="utf-8"))
    tre = json.load(open(os.path.join(S.TROUT, "report.json"), encoding="utf-8"))
    return {
        "무엇": "한국 IP·이벤트의 「앞 90일 상태 → 뒤 91일 결과 분포」 전이 모형 + 한국어 웹 LM",
        "도메인(표본 수)": tri["도메인"],
        "시간 덮음": "학습 삼중쌍 2017~2022 크롤 · LM 말뭉치 2013-05~2024-04(시대 96 샤드)",
        "검증 성적": {"누적90일 MdAPE": tre["평가"]["누적90일 MdAPE"],
                   "기준선(persistence)": tre["평가"]["누적90일 MdAPE(persistence)"],
                   "90% 구간 덮개율": tre["평가"]["90% 구간 덮개율(목표 0.90)"]},
        "LM": {"체크포인트": S.LM_PATH, "스텝": S.LM_STEP,
               "주의": "완주 전이면 생성 품질은 옹알이 — 놀람도·임베딩 용도"},
        "🔴 원리상 못 하는 것": ["인과 효과(「언급 «때문»」) 주장", "지식 질답",
                          "학습 도메인 밖 예측(아래 도메인 목록이 전부다)",
                          "2024-05 이후 정보장(LM 말뭉치 밖)"],
        "⚠ 한계": CAVEAT}


def wm_forecast(curve=None, domain=None, date=None, **_):
    vals = _parse_curve(curve)
    if domain not in S.DOMS:
        return {"오류": "도메인은 %s 중" % S.DOMS}
    out = _forecast_full(vals, domain, str(date))
    out.update({"입력": {"도메인": domain, "기준일": date,
                       "직전 90일 일평균": round(float(np.mean(vals)), 1)},
                "⚠": CAVEAT})
    return out


_TRANSFORMS = ("curve_scale", "date_shift_months", "trend_boost_last30_pct", "domain")


def _apply_variant(vals, domain, date, v):
    vals2, domain2, date2 = list(vals), domain, str(date)
    if v.get("curve_scale") is not None:
        vals2 = [x * float(v["curve_scale"]) for x in vals2]
    if v.get("trend_boost_last30_pct") is not None:
        f = 1.0 + float(v["trend_boost_last30_pct"]) / 100.0
        vals2 = vals2[:60] + [x * f for x in vals2[60:]]
    if v.get("date_shift_months") is not None:
        y, m, d = int(date2[:4]), int(date2[5:7]), int(date2[8:10])
        m2 = m + int(v["date_shift_months"])
        y2, m2 = y + (m2 - 1) // 12, (m2 - 1) % 12 + 1
        date2 = "%04d-%02d-%02d" % (y2, m2, min(d, 28))
    if v.get("domain") is not None:
        domain2 = v["domain"]
    return vals2, domain2, date2


def wm_compare(base=None, variants=None, **_):
    vals = _parse_curve(base["curve"])
    domain, date = base["domain"], str(base["date"])
    if domain not in S.DOMS:
        return {"오류": "도메인은 %s 중" % S.DOMS}
    b = _forecast_full(vals, domain, date)
    ref = b["누적"]["90일"]["q50"]
    rows = []
    for v in (variants or []):
        unknown = [k for k in v if k not in _TRANSFORMS + ("name",)]
        if unknown:
            rows.append({"이름": v.get("name", "?"), "오류": "모르는 변환 %s" % unknown})
            continue
        vals2, dom2, date2 = _apply_variant(vals, domain, date, v)
        if dom2 not in S.DOMS:
            rows.append({"이름": v.get("name", "?"), "오류": "도메인 %s 없음" % dom2})
            continue
        f = _forecast_full(vals2, dom2, date2)
        q50 = f["누적"]["90일"]["q50"]
        rows.append({"이름": v.get("name", "?"), "변환": {k: v[k] for k in v if k != "name"},
                     "누적90일": f["누적"]["90일"],
                     "Δq50(기준 대비)": q50 - ref,
                     "Δ%": round(q50 / max(ref, 1) - 1, 3)})
    return {"기준": {"입력": {"도메인": domain, "기준일": date,
                          "일평균": round(float(np.mean(vals)), 1)},
                   "누적90일": b["누적"]["90일"]},
            "시나리오": rows,
            "🔴 라벨": "모형 민감도 — 인과 검증 안 됨. 「입력이 다르면 예측이 이렇게 다르다」까지",
            "⚠": CAVEAT}


def wm_risk(curve=None, domain=None, date=None, **_):
    r = S.q_report(curve, domain, str(date))
    if "오류" in r:
        return r
    return {"입력": r["입력"], "예측(누적 90일)": r["예측(누적 90일)"],
            "리스크": r["③ 언제 — 리스크 창"], "⚠": CAVEAT}


def wm_similar(curve=None, domain=None, date=None, k=3, **_):
    r = S.q_report(curve, domain, str(date))
    if "오류" in r:
        return r
    return {"입력": r["입력"],
            "사례": r["① 근거 — 유사 사례(같은 도메인 · 학습 표본)"][:int(k)],
            "읽는 법": "「현 수준 대비 배율」< 1 은 비슷한 상태에서 «주저앉은» 사례다 — 무엇이 갈랐는지 물을 재료",
            "⚠": CAVEAT}


def wm_entity(i=0, **_):
    return S.q_entity(int(i))


def wm_surprisal(texts=None, **_):
    if isinstance(texts, str):
        texts = [texts]
    rows = [dict(본문=t[:60], **S.q_surprisal(t)) for t in (texts or [])]
    if len(rows) >= 2 and all("nll/token" in r for r in rows):
        best = min(rows, key=lambda r: r["nll/token"])
        note = "모형이 가장 자연스럽다고 보는 것: 「%s」" % best["본문"]
    else:
        note = None
    return {"결과": rows, "해석": note,
            "⚠": "LM 스텝 %s — 완주 전이면 거친 자다. 시대별 모델이 서면 «언제부터 자연스러워졌나»가 된다" % S.LM_STEP}


# ── manifest — 하네스 LLM 이 읽는 계약 ────────────────────────────────
def _sch(props, req):
    return {"type": "object", "properties": props, "required": req,
            "additionalProperties": False}

_CURVE = {"description": "직전 90일 일별 값 — 숫자 하나(평탄) · 배열 90개 · 쉼표 문자열",
          "anyOf": [{"type": "number"}, {"type": "string"},
                    {"type": "array", "items": {"type": "number"}}]}
_DOM = {"type": "string", "description": "도메인 (wm_model_card 의 목록이 전부)"}
_DATE = {"type": "string", "description": "기준일 YYYY-MM-DD"}

MANIFEST = [
    {"name": "wm_model_card", "fn": wm_model_card,
     "description": "이 월드모델이 할 수 있는 일·도메인·검증 성적·원리상 못 하는 것. 🔴 낯선 질문이면 항상 먼저 불러라",
     "inputSchema": _sch({}, [])},
    {"name": "wm_forecast", "fn": wm_forecast,
     "description": "앞 90일 상태 → 뒤 7/30/90일 누적 분포(q05~q95)와 일별 q50. 「얼마나 될까」의 직답",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE},
                         ["curve", "domain", "date"])},
    {"name": "wm_compare", "fn": wm_compare,
     "description": "시나리오 비교(전략 결정용). 변환: curve_scale(초기 관심 배율) · date_shift_months(시점 이동) · trend_boost_last30_pct(막판 추세 %) · domain. 여러 개를 한 번에",
     "inputSchema": _sch({
         "base": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE},
                      ["curve", "domain", "date"]),
         "variants": {"type": "array", "items": _sch({
             "name": {"type": "string"},
             "curve_scale": {"type": "number"},
             "date_shift_months": {"type": "integer"},
             "trend_boost_last30_pct": {"type": "number"},
             "domain": _DOM}, ["name"])}}, ["base", "variants"])},
    {"name": "wm_risk", "fn": wm_risk,
     "description": "「언제 흔들리나」— 하방(q05)이 열리는 첫 날 · 불확실성 최대 주(재판단 시점)",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE},
                         ["curve", "domain", "date"])},
    {"name": "wm_similar", "fn": wm_similar,
     "description": "비슷한 상태였던 «실제» 과거 사례와 그 결과(성공·실패 모두) — 근거·진단 재료",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE,
                          "k": {"type": "integer", "minimum": 1, "maximum": 10}},
                         ["curve", "domain", "date"])},
    {"name": "wm_entity", "fn": wm_entity,
     "description": "검증 개체(모형이 학습에서 못 본 실제 IP) 예측 대 실제 — 신뢰도 눈감정용",
     "inputSchema": _sch({"i": {"type": "integer", "minimum": 0}}, ["i"])},
    {"name": "wm_surprisal", "fn": wm_surprisal,
     "description": "문장(들)의 LM 놀람도 — 「어느 표현이 한국 웹에서 자연스러운가」. 시대별 모델이 서면 개념 진입 시점 측정으로 확장",
     "inputSchema": _sch({"texts": {"type": "array", "items": {"type": "string"}}},
                         ["texts"])},
]


def call(name, args):
    for t in MANIFEST:
        if t["name"] == name:
            try:
                return t["fn"](**(args or {}))
            except Exception as e:                       # noqa: BLE001
                return {"오류": "%s: %s" % (type(e).__name__, e)}
    return {"오류": "모르는 도구 %s" % name}


if __name__ == "__main__":                               # 빠른 자가 점검
    print(json.dumps({t["name"]: t["description"][:40] for t in MANIFEST},
                     ensure_ascii=False, indent=1))
