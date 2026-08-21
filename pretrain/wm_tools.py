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

def _caveat():
    """성적을 «지금 배포된» report.json 에서 읽는다 — 숫자 하드코딩이 낡는 병 방지."""
    try:
        e = json.load(open(os.path.join(S.TROUT, "report.json"), encoding="utf-8"))["평가"]
        return ("조건부 예측이지 인과가 아니다(「언제」= 크롤 시각) · 90%% 구간 실측 덮개율 "
                "%.1f%%(목표 90 — 모자란 만큼 보수적으로) · 개체 분리 검증 MdAPE %.1f%%"
                % (e["90% 구간 덮개율(목표 0.90)"] * 100, e["누적90일 MdAPE"] * 100))
    except Exception:
        return "조건부 예측이지 인과가 아니다 · 성적표 read 실패 — wm_model_card 로 확인하라"

CAVEAT = _caveat()


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


def _forecast_full(vals, domain, date, text=None):
    sc, cond, base = S._features_from_raw(vals, domain, date, text=text)
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


def wm_forecast(curve=None, domain=None, date=None, text=None, **_):
    vals = _parse_curve(curve)
    if domain not in S.DOMS:
        return {"오류": "도메인은 %s 중" % S.DOMS}
    out = _forecast_full(vals, domain, str(date), text=text)
    if S.TEXT_DIM:
        out["텍스트 조건"] = "제공됨" if text else "미제공 → 도메인 평균 임베딩"
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
    btxt = base.get("text")
    b = _forecast_full(vals, domain, date, text=btxt)
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
        f = _forecast_full(vals2, dom2, date2, text=v.get("text", btxt))
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


# ── 개체 해석(entity → 실측 상태) — 조용한 폴백 금지 ──────────────────
def _entity_miss(name, pool, extra=None):
    """정확 일치 실패의 «명시 오류» — 오답을 정답처럼 주지 않고 비슷한 후보를 준다."""
    import difflib
    uniq = sorted(set(pool))
    q = str(name)
    cand = [k for k in uniq if q and q in k]
    cand += [k for k in difflib.get_close_matches(q, uniq, n=8, cutoff=0.5)
             if k not in cand]
    if not cand:                                         # 빈 후보도 폴백 못지않게 불친절 — 컷오프 완화 재시도
        cand = difflib.get_close_matches(q, uniq, n=8, cutoff=0.3)
    cand = cand[:8]
    out = {"오류": "개체 없음 — 「%s」와 정확히 일치하는 개체 ID 가 없다(조용한 폴백 금지)" % q,
           "비슷한 후보 %d개" % len(cand): cand}
    if extra:
        out.update(extra)
    return out


def _entity_state(name, domain=None):
    """개체 ID → ((실측 90일 곡선·도메인·기준일·라벨), None) 또는 (None, 명시 오류).
    같은 개체의 관측 행이 여럿이면 «최신 관측»을 쓴다 — 「지금 상태」 질문이므로."""
    q = str(name)
    rows = [i for i, m in enumerate(S.META) if m["개체"] == q]
    if not rows:
        return None, _entity_miss(q, (m["개체"] for m in S.META))
    rows.sort(key=lambda i: S.META[i]["언제"])
    gi = rows[-1]
    m = S.META[gi]
    vals = np.expm1(S.DATA.S[gi].astype(np.float64)).tolist()
    used = {"개체": m["개체"], "도메인": m["도메인"], "기준일(최신 관측)": m["언제"],
            "관측 행": len(rows)}
    if domain is not None and domain != m["도메인"]:
        used["⚠ 도메인 불일치"] = ("호출 domain=%s ≠ 개체 도메인 %s — 개체 도메인으로 계산"
                               % (domain, m["도메인"]))
    return (vals, m["도메인"], m["언제"], used), None


def _curve_str(vals):
    return " ".join("%.10g" % v for v in vals)


def wm_risk(curve=None, domain=None, date=None, text=None, entity=None, **_):
    used = None
    if entity is not None:
        st, err = _entity_state(entity, domain)
        if err:
            return err
        vals, domain, date, used = st
    else:
        if curve is None:
            return {"오류": "curve(직전 90일)나 entity(개체 ID) 중 하나는 필수다"}
        if date is None:
            return {"오류": "date(YYYY-MM-DD)가 없다 — entity 로 물으면 관측 기준일을 자동으로 쓴다"}
        vals = _parse_curve(curve)
    r = S.q_report(_curve_str(vals), domain, str(date), text=text)
    if "오류" in r:
        return r
    out = {"입력": r["입력"], "예측(누적 90일)": r["예측(누적 90일)"],
           "리스크": r["③ 언제 — 리스크 창"], "⚠": CAVEAT}
    if used:
        out["개체 입력(실측)"] = used
    return out


def wm_similar(curve=None, domain=None, date=None, k=3, text=None, **_):
    r = S.q_report(curve, domain, str(date), text=text)
    if "오류" in r:
        return r
    return {"입력": r["입력"],
            "사례": r["① 근거 — 유사 사례(같은 도메인 · 학습 표본)"][:int(k)],
            "읽는 법": "「현 수준 대비 배율」< 1 은 비슷한 상태에서 «주저앉은» 사례다 — 무엇이 갈랐는지 물을 재료",
            "⚠": CAVEAT}


def wm_entity(i=None, name=None, **_):
    if name is not None:
        q = str(name)
        va = S.DATA.va.tolist()
        hits = [k for k, gi in enumerate(va) if S.META[gi]["개체"] == q]
        if not hits:
            if any(m["개체"] == q for m in S.META):
                return {"오류": "「%s」는 자료에 있으나 검증(val) 분할 밖이다(조용한 폴백 금지)" % q,
                        "대신": "wm_council/wm_risk 의 entity 인자로 물어라 — 실측 곡선 경로"}
            return _entity_miss(q, (S.META[gi]["개체"] for gi in va))
        hits.sort(key=lambda k: S.META[va[k]]["언제"])
        out = S.q_entity(hits[0])
        if len(hits) > 1:
            out["동일 개체 val 행"] = {"수": len(hits), "선택": "최초 관측(언제 순)",
                                  "i 후보": hits[:12]}
        return out
    if i is None:
        return {"오류": "i(검증 인덱스)나 name(개체 ID) 중 하나는 필수다"}
    i = int(i)
    n = len(S.DATA.va)
    if not 0 <= i < n:
        return {"오류": "i 범위 밖 — 검증 인덱스는 0~%d (조용한 mod 폴백 금지)" % (n - 1)}
    return S.q_entity(i)


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


def wm_council(curve=None, domain=None, date=None, entity=None, **_):
    """하네스 «안» 연구 루프 — 방법 4 비교 → 검증 성적으로 채택. entity 를 주면 실측 곡선으로."""
    from pretrain import council
    used = None
    if entity is not None:
        st, err = _entity_state(entity, domain)
        if err:
            return err
        vals, domain, date, used = st
    else:
        if curve is None:
            return {"오류": "curve(직전 90일)나 entity(개체 ID) 중 하나는 필수다"}
        if date is None:
            return {"오류": "date(YYYY-MM-DD)가 없다 — entity 로 물으면 관측 기준일을 자동으로 쓴다"}
        vals = _parse_curve(curve)
    out = council.ask(_curve_str(vals), domain, str(date))
    if used and isinstance(out, dict):
        out["개체 입력(실측)"] = used
    return out


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


_CS = {}                                                 # wm_coldstart 색인 캐시


def _cs_index():
    """개체별 «최초 관측» 행 색인 + 조항 59 낙인 계수 — 배포 자료에서 직접 센다(하드코딩 금지)."""
    if _CS:
        return _CS
    first = {}
    for i, m in enumerate(S.META):
        k = m["개체"]
        if k not in first or m["언제"] < S.META[first[k]]["언제"]:
            first[k] = i
    Sr = np.expm1(S.DATA.S.astype(np.float64))           # (N,90) 원 눈금
    Or = np.expm1(S.DATA.O.astype(np.float64))           # (N,91)
    n_debut = 0
    for k, i in first.items():
        c = np.concatenate([Sr[i], Or[i]])
        nz = np.where(c >= 1.0)[0]
        if len(nz) and 7 <= int(nz[0]) <= 91:
            n_debut += 1
    tr_set = set(S.DATA.tr.tolist())
    pool = {}
    for k, i in sorted(first.items()):
        if i in tr_set:
            pool.setdefault(S.META[i]["도메인"], []).append((k, i))
    _CS.update({"first": first, "pool": pool, "Or": Or, "Sr": Sr,
                "데뷔급": n_debut, "개체": len(first)})
    return _CS


def _wq(vals, wts, q):
    """가중 분위수(역CDF 계단 · 결정적) — 1007 러너와 같은 정의."""
    v = np.asarray(vals, dtype=np.float64)
    w = np.asarray(wts, dtype=np.float64)
    if w.sum() <= 0:
        w = np.ones_like(w)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w) / w.sum()
    return float(v[min(int(np.searchsorted(cw, q, side="left")), len(v) - 1)])


def _cs_score():
    """1007 백테스트 성적 — «커밋된» out JSON 에서 읽는다(조항 81 · 숫자 하드코딩 방지)."""
    try:
        o = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "runners", "out1007_coldstart.json"),
            encoding="utf-8"))
        g = o["판정 G1 (주대비 · 게이트)"]
        return {"MdAPE(참조군 가중 K=12 · val 70)": g["MdAPE_M(참조군 가중 K=12)"],
                "MdAPE(기후값)": g["MdAPE_B1(기후값)"],
                "80% 구간 실측 덮개율(참조군)": o["관찰"]["80% 구간 실측 덮개율 — M(q10~q90)"],
                "판정": ("채택 보류 — 기후값 정본(티처 #142 처분 재등록 · 1007 §11): "
                       "G1 통과(여유 +%.3f)였으나 이득 대부분이 쌍둥이 재식별"
                       % g["여유 (문턱 − Δ · >0 ⇔ 통과)"])}
    except Exception:
        return "성적표(out1007_coldstart.json) read 실패 — docs/탐색/1007.md 로 확인하라"


def _twin_score():
    """쌍둥이 제외 4수 — «커밋된» out1007_twin_supp.json 에서 읽는다(조항 81 · #142 ㉯ — 하드코딩 금지)."""
    try:
        o = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "runners", "out1007_twin_supp.json"),
            encoding="utf-8"))
        g = o["4수 (6자리)"]
        return ("Δ %+.4f ± SE %.4f(비유의) · 덮개율 %.4f — out1007_twin_supp.json 실측"
                % (g["Δ′"], g["SE′"], g["덮개율′"]))
    except Exception:
        return "쌍둥이 제외 수치 read 실패(out1007_twin_supp.json) — docs/탐색/1007.md §7·§11 로 확인하라"


def wm_coldstart(text=None, domain=None, k=12, platform=None, target=None, **_):
    """신작 콜드스타트 — 거절 대신 실측 분포 답. 모든 수가 실측 곡선 유래 · 생성 0.
    사전등록·채점: docs/탐색/1007.md (G1 통과 · §11 티처 #142 처분 재등록 —
    정본 = 도메인 기후값 분위수 · 참조군 곡선은 참고 칸)."""
    if not text or not str(text).strip():
        return {"오류": "text(기획·소개 텍스트)를 다오 — 콜드스타트는 텍스트가 유일한 입력이다"}
    if domain not in S.DOMS:
        return {"오류": "도메인은 %s 중" % S.DOMS}
    k = max(8, min(20, int(k)))
    idx = _cs_index()
    cand = idx["pool"].get(domain, [])
    if len(cand) < 5:                                    # K_MIN=5 (사전등록 §5 ⓕ)
        return {"오류": "참조군 빈약 — 도메인 %s 의 train 풀 %d < 하한 5" % (domain, len(cand)),
                "풀": len(cand)}
    out = {"입력": {"도메인": domain, "K": k, "텍스트": str(text)[:120]}}
    if platform or target:
        out["입력"]["🔴 미사용 입력"] = ("platform/target 은 이 자료에 없어 참조군 선택에 "
                                    "안 썼다 — 라벨로만 동봉: %s" %
                                    {"platform": platform, "target": target})
    # ⓐ 라이브 임베딩(학습 미러) + OOD 자
    if not S.TEXT_DIM:
        return {"오류": "배포 모형에 텍스트 임베딩이 없다 — wm_model_card 로 확인하라"}
    emb = S._embed_text_live(text).astype(np.float64)
    dmin = float(np.sqrt(((S.E_TRAIN.astype(np.float64) - emb[None]) ** 2).sum(-1)).min())
    ratio = dmin / max(S.REF_NN, 1e-9)
    out["텍스트 OOD 비율(1≈분포 안 · 3+ 경고 · 5+ 유사도 신뢰 금지)"] = round(ratio, 2)
    # ⓑ 같은 도메인 train 최초 행과 코사인 → top-K
    rows_i = [i for _, i in cand]
    P = S.DATA.E[rows_i].astype(np.float64)
    # 🔴 0-노름 가드 — 노름 0 행은 나눗셈 없이 유사도 0 · 쿼리가 0-벡터/비유한이면 명시 오류
    pn = np.linalg.norm(P, axis=1, keepdims=True)
    Pn = np.divide(P, pn, out=np.zeros_like(P), where=pn > 0)
    qnorm = float(np.linalg.norm(emb))
    if not (np.isfinite(qnorm) and qnorm > 0.0):
        return {"오류": "텍스트 임베딩이 0-노름/비유한 — 유사도 계산 불가(라이브 임베딩 점검)"}
    qn = emb / qnorm
    # matmul(@) 대신 einsum — macOS arm64 numpy 2.0(Accelerate gemv)이 «유한 입력»에도
    # divide/overflow/invalid FPE 허위 경고 3종을 낸다(실측 · einsum 값차 ≤1.5e-15 · 경고 0)
    sims = np.einsum("ij,j->i", Pn, qn)
    order = np.argsort(-sims)[:k]
    w = np.maximum(sims[order], 0.0)
    cum = np.stack([idx["Or"][rows_i[j]][:90].cumsum() for j in order])   # (K,90) 실측 누적
    days = {"7일": 6, "30일": 29, "60일": 59, "90일": 89}
    qs = {"q10": 0.10, "q25": 0.25, "q50": 0.50, "q75": 0.75, "q90": 0.90}
    ref_q = {dn: {qk: int(_wq(cum[:, t], w, qv)) for qk, qv in qs.items()}
             for dn, t in days.items()}
    daily = np.stack([idx["Or"][rows_i[j]][:90] for j in order])
    # ⓒ 참조군 명단 — 유사도·개체명·실측 출처
    cases = []
    for j in order:
        gi = rows_i[j]
        m = S.META[gi]
        cases.append({"개체": m["개체"], "유사도(cos)": round(float(sims[j]), 4),
                      "기준일(최초 관측)": m["언제"],
                      "당시 일평균": round(float(idx["Sr"][gi].mean()), 1),
                      "실측 90일 누적": int(idx["Or"][gi][:90].sum()),
                      "출처": "위키 일별 조회 실측(크롤 스냅숏)"})
    # 기후값 «정본»(§4 둘째 가지 · 티처 #142 처분 재등록 — 1007 §11) — 참조군과 같은 누적 격자
    cum_all = np.stack([idx["Or"][i][:90].cumsum() for _, i in cand])
    ones = np.ones(len(cand))
    clim_q = {dn: {qk: int(_wq(cum_all[:, t], ones, qv)) for qk, qv in qs.items()}
              for dn, t in days.items()}
    out.update({
        "정본 — 도메인 기후값 분위수(train %d 개체 · 무가중 · 누적 · 실측 유래)" % len(cand): clim_q,
        "참고 — 참조군 가중 분위수 곡선(누적 · ⚠ 쌍둥이 재식별 — 1007 §7·§11)": ref_q,
        "참고 — 일별 q50(1·7·30·60·90일째 · 참조군 가중)": [round(float(_wq(daily[:, t], w, 0.5)), 1)
                                                for t in (0, 6, 29, 59, 89)],
        "참조군(top-%d) — 유사 사례 명단(참고)" % k: cases,
        "1007 백테스트 성적": _cs_score(),
        "🔴 낙인(조항 59)": ("데뷔급 %d/%d — 이 곡선은 «최초 관측 정렬»(중간 진입)이지 "
                         "데뷔 곡선이 아니다. 눈금은 위키 일별 조회수(모형의 자)다 — "
                         "플랫폼 조회수·매출이 아니다" % (idx["데뷔급"], idx["개체"])),
        "⚠": ("참조군 답이다 — 모형 점추정이 아니라 «유사 실작들의 실측 분포»다(거절 사다리 ② 층). "
             "유사도는 웹 언급-문구 임베딩이라 기획서 문체와 거리가 있다(OOD 비율 참조). "
             "🔴 정본은 «기후값 칸»이다(티처 #142 처분 재등록 — «채택 보류(기후값 정본)» · 1007 §11): "
             "G1 이득의 대부분은 «같은 작품 쌍둥이» 재식별이고, 쌍둥이 제외 시 "
             + _twin_score() + " — 진짜 신작(정의상 쌍둥이 없음)의 추정은 기후값과 비긴다"
             "(§4 사전 고정 그대로). 참조군 칸은 순위 없는 유사 사례 «참고»로 읽어라. "
             "쌍둥이 필터 백테스트(#142 ⑥-1)가 «작품 분리»에서 참조군 우위를 다시 세우면 "
             "재재등록한다. " + CAVEAT)})
    if ratio > 5.0:
        out["🔴 극단 OOD"] = ("텍스트가 학습 분포(웹 언급 문구) 밖 — 유사도 순위 신뢰 금지. "
                          "참고(참조군) 칸은 명단으로도 걸러 읽고 «정본(기후값) 칸»만 수치로 읽어라")
    return out


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
_TEXT = {"type": "string", "description": "(선택) 기획서·소개 텍스트 — 넣으면 텍스트 «조건» 예측(라이브 임베딩)"}
_ENTITY = {"type": "string", "description": "개체 ID(정확 일치) — 주면 그 개체의 «최신 관측» 실측 90일 곡선·도메인·기준일로 계산(curve·date 불필요). 못 찾으면 비슷한 후보를 담은 명시 오류"}

MANIFEST = [
    {"name": "wm_model_card", "fn": wm_model_card,
     "description": "이 월드모델이 할 수 있는 일·도메인·검증 성적·원리상 못 하는 것. 🔴 낯선 질문이면 항상 먼저 불러라",
     "inputSchema": _sch({}, [])},
    {"name": "wm_forecast", "fn": wm_forecast,
     "description": "앞 90일 상태 → 뒤 7/30/90일 누적 분포(q05~q95)와 일별 q50. 「얼마나 될까」의 직답. 🔴 text 를 주면 «기획서 텍스트 조건» 예측",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE, "text": _TEXT},
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
     "description": "「언제 흔들리나」— 하방(q05)이 열리는 첫 날 · 불확실성 최대 주(재판단 시점). curve·domain·date 셋 «또는» entity 하나",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE,
                          "entity": _ENTITY}, [])},
    {"name": "wm_similar", "fn": wm_similar,
     "description": "비슷한 상태였던 «실제» 과거 사례와 그 결과(성공·실패 모두) — 근거·진단 재료",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE,
                          "k": {"type": "integer", "minimum": 1, "maximum": 10}},
                         ["curve", "domain", "date"])},
    {"name": "wm_entity", "fn": wm_entity,
     "description": "검증 개체(모형이 학습에서 못 본 실제 IP) 예측 대 실제 — 신뢰도 눈감정용. i(검증 인덱스) 또는 name(개체 ID 정확 일치 — 실패 시 후보 제시 오류 · 조용한 폴백 없음)",
     "inputSchema": _sch({"i": {"type": "integer", "minimum": 0},
                          "name": {"type": "string",
                                   "description": "개체 ID(정확 일치) — 못 찾으면 후보 제시 오류"}},
                         [])},
    {"name": "wm_council", "fn": wm_council,
     "description": "🔴 하네스 안 연구 루프 — 방법 4(전이·사례·기후값·현상유지)를 «전부» 돌리고 도메인별 검증 성적으로 채택 + 불일치 폭. 예측형 질문의 «기본» 도구로 forecast 보다 먼저 써라. curve·domain·date 셋 «또는» entity 하나",
     "inputSchema": _sch({"curve": _CURVE, "domain": _DOM, "date": _DATE,
                          "entity": _ENTITY}, [])},
    {"name": "wm_coldstart", "fn": wm_coldstart,
     "description": ("🔴 신작 «콜드스타트»(연재·출시 전 — 직전 곡선 없음)의 기본 도구 — 기획 텍스트+도메인으로 "
                     "도메인 기후값 분위수(정본 — 1007 §11 티처 #142 처분)와 유사 실작 K(8~20)개의 «실측» 90일 "
                     "곡선 분위수·명단(참고 — 쌍둥이 ⚠)을 준다. 모든 수가 실측 곡선 유래 · 생성 0 · 거절 사다리 "
                     "② 층. 곡선 없는 신작에 wm_forecast 에 0 을 넣지 말고 이걸 써라"),
     "inputSchema": _sch({
         "text": {"type": "string", "description": "기획·소개 텍스트(필수) — 콜드스타트의 유일한 조건"},
         "domain": _DOM,
         "k": {"type": "integer", "minimum": 8, "maximum": 20},
         "platform": {"type": "string", "description": "(선택) 플랫폼 — 자료에 없어 라벨로만 동봉"},
         "target": {"type": "string", "description": "(선택) 타깃 규모 — 자료에 없어 라벨로만 동봉"}},
         ["text", "domain"])},
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
    global CAVEAT
    if "read 실패" in CAVEAT:
        CAVEAT = _caveat()                               # 일시 경합 자기 회복
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
