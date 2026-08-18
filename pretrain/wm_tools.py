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
        "방법 리더보드(도메인별 승자 — wm_council 이 이걸로 채택한다)":
            (json.load(open(os.path.join(S.TROUT, "leaderboard.json"), encoding="utf-8"))
             if os.path.exists(os.path.join(S.TROUT, "leaderboard.json")) else "아직 없다"),
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


def wm_council(curve=None, domain=None, date=None, **_):
    """하네스 «안» 연구 루프 — 방법 4 비교 → 검증 성적으로 채택."""
    from pretrain import council
    return council.ask(curve, domain, str(date))


def wm_discourse(keyword=None, max_files=48, **_):
    """여론 v0 — 실측 스트림(유튜브 폴링) 검색 + LM 자연스러움. 정보장 해석의 첫 판."""
    import glob
    files = sorted(glob.glob("/Users/ax/world_model/data/ingest/youtube_poll/*.json"))
    files = files[-int(max_files):]
    kw = str(keyword or "").strip()
    if not kw:
        return {"오류": "keyword 를 다오"}
    hits, seen = [], set()
    for fp in files:
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for t in d.get("대상", []):
            for v in t.get("영상", []):
                blob = "%s %s %s" % (t.get("name", ""), v.get("제목", ""), v.get("채널", ""))
                if kw in blob and v.get("id") not in seen:
                    seen.add(v.get("id"))
                    hits.append({"대상": t.get("name"), "제목": v.get("제목", "")[:80],
                                 "채널": v.get("채널"), "게시일": v.get("게시일", "")[:10],
                                 "조회수": v.get("조회수_읽은시점")})
    hits.sort(key=lambda h: -float(str(h["조회수"] or "0").replace(",", "") or 0))
    sur = S.q_surprisal("요즘 %s 이야기가 많다" % kw)
    return {"키워드": kw, "훑은 폴링 파일": len(files),
            "적중 영상": len(hits), "상위(조회수)": hits[:8],
            "LM 자연스러움(nll — 낮을수록 흔한 화제)": sur,
            "⚠": ("v0 다 — «수집된 스트림 검색 + LM 놀람도»까지. 시대별 모델(학습 큐에 "
                 "걸려 있다)이 서면 「언제부터 화제가 됐나」 곡선이 되고, 페르소나 뱅크가 "
                 "생기면 「누가 어떻게 반응할까」가 된다. 여론 «예측»이라 부르지 마라")}


def wm_data_health(**_):
    """하네스용 데이터 재검수 — 원천 신선도 · 학습 진행 · 말뭉치 무결성."""
    import time
    out = {"경고": []}
    # ① 수집 데몬 원천별 최근 기록
    try:
        tail = open("/Users/ax/world_model/data/state/collect_log.jsonl",
                    encoding="utf-8").readlines()[-300:]
        last = {}
        for ln in tail:
            try:
                r = json.loads(ln)
                last[r.get("이름")] = r
            except Exception:
                pass
        now = time.time()
        src = {}
        for name, r in sorted(last.items()):
            ts = r.get("시각(UTC)", "")
            try:
                import datetime as dt
                t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                age_h = round((now - t) / 3600, 1)
            except Exception:
                age_h = None
            src[name] = {"판정": r.get("판정"), "델타": r.get("델타"), "경과(시간)": age_h}
            if age_h is not None and age_h > 12:
                out["경고"].append("원천 %s 가 %.1f 시간째 조용하다" % (name, age_h))
        out["수집 원천"] = src
    except Exception as e:
        out["수집 원천"] = {"오류": str(e)}
    # ② 학습 진행
    for name in ("tiny-v1", "tiny-b1", "tiny-b2", "tiny-xl"):
        pp = os.path.join(S.CKPT_DIR, name, "progress.txt")
        if os.path.exists(pp):
            out.setdefault("학습", {})[name] = open(pp, encoding="utf-8").read().strip()
    # ③ 말뭉치
    for tag, d in (("tokens(0.88B)", os.path.join(S.ART_DIR, "tokens")),
                   ("tokens_xl(확장)", os.path.join(S.ART_DIR, "tokens_xl"))):
        idx = os.path.join(d, "index.json")
        prog = os.path.join(d, "progress.txt")
        if os.path.exists(idx):
            i = json.load(open(idx, encoding="utf-8"))
            out.setdefault("말뭉치", {})[tag] = {
                "샤드": len(i["shards"]),
                "토큰": sum(x["n_tokens"] for x in i["shards"])}
        elif os.path.exists(prog):
            out.setdefault("말뭉치", {})[tag] = {"진행": open(prog, encoding="utf-8").read().strip()}
    import shutil
    du = shutil.disk_usage("/Users/ax/wm_harvest")
    out["디스크 여유(GiB)"] = round(du.free / 2 ** 30, 1)
    out["판정"] = "🔴 경고 있음" if out["경고"] else "정상"
    return out


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
    {"name": "wm_council", "fn": wm_council,
     "description": "🔴 하네스 안 연구 루프 — 방법 4(전이·사례·기후값·현상유지)를 «전부» 돌리고 도메인별 검증 성적으로 채택 + 불일치 폭. 예측형 질문의 «기본» 도구로 forecast 보다 먼저 써라",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE},
                         ["curve", "domain", "date"])},
    {"name": "wm_discourse", "fn": wm_discourse,
     "description": "여론 v0 — 수집된 유튜브 폴링 스트림에서 키워드 실측 검색(적중 영상·조회수) + LM 자연스러움. «예측» 아님",
     "inputSchema": _sch({"keyword": {"type": "string"},
                          "max_files": {"type": "integer", "minimum": 1, "maximum": 461}},
                         ["keyword"])},
    {"name": "wm_data_health", "fn": wm_data_health,
     "description": "데이터 파이프라인 재검수 — 원천 신선도(12h 문턱 경고)·학습 진행·말뭉치 무결성·디스크. 답하기 전에 데이터가 살아 있는지 확인",
     "inputSchema": _sch({}, [])},
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
