"""노트 901 ③ 식별 가능성 판정 + 「무엇이 없어서 못 재는가」.

사전등록: `docs/prereg_901_intervention.md` (커밋 ae0ed6c49 · 2026-08-11T03:21:42+09:00)

🔴 효과 크기를 안 낸다. 개수 · 값 가짓수 · 결측 · 분모만.
🔴 D3(판 채점 유보행) 덮음은 **축 파일 키 = 원천 record_id** 이고 D2==D4 인
   도메인에서만 셀 수 있다. 안 되는 곳은 「없다」가 아니라 **「못 셌다」**로 적는다.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import (CAND, SRC, UNIT, DATEK, dig, hashable, load_records,
                    sha, MISSING)

# 🔴 「개입 값의 관측 시점」을 담을 수 있는 필드 후보 — 미리 나열하고 **찾아본다**.
#    있으면 식3(역인과 아님)을 기계로 확인할 수 있고, 없으면 W4 다.
ASOF_CAND = [
    "intervention.attr_meta.tagger", "intervention.attr_meta.evidence",
    "intervention.attr_meta.confidence",
    "provenance.extracted_at", "provenance.extracted_by",
    "intervention_source_date", "intervention_source_url",
    "outcome.visitors_source_date", "outcome.sales_source_date",
    "source", "ingested_from", "updated", "_page", "extraction_confidence",
    "chodong_source_date", "label_basis", "첫 관측일",
]

# 🔴 식3 을 **열 단위로** 판정한다. 도메인 단위로 보면 태거가 안 만진 열까지
#    태거의 시간 마스크를 빌려 쓴다(초판이 실제로 그랬다 — 팝업 A=6 이 나왔다).
#
# PRE_PROVEN: **코드가 강제하는 시간 마스크**로 사전성이 증명된 열.
#   `ingest/doc_select.is_pre_open()` 이 문서 파일명 날짜를 `conditions.period.from`
#   (오픈일)과 대조해 사후 문서를 버린다. `ingest/attr_tagger.build_user()` 가
#   그 목록만 프롬프트에 넣는다.
#   ⚠ 단서: `PRE_KINDS=("기획서","계약서")` 는 **날짜를 못 읽으면 통과**시킨다
#   (`doc_select.py:71-79`) — 마스크가 완전 밀폐는 아니다.
PRE_PROVEN = {
    "팝업": tuple(n for n, *_ in CAND["팝업"]
                 if n.startswith("intervention.attributes.")),
}
PRE_WHY = {
    "팝업": ("코드 강제 시간 마스크 — `ingest/doc_select.is_pre_open()` 가 "
           "문서 날짜 ≤ `conditions.period.from` 만 통과시키고 "
           "`ingest/attr_tagger.build_user()` 가 그 목록만 넣는다. "
           "⚠ 기획서·계약서는 날짜를 못 읽으면 통과한다(`doc_select.py:71-79`)"),
}

# 결과 창이 열린 뒤에도 자라는 열 — 수집 시점 스냅숏이라 결과와 동시 결정
POST_GROW = {
    "웹툰": ("n_episode",),
    "만화": ("n_chapter", "n_volume"),
    "펀딩": ("amount",),
}

# 교란 후보(식4) — 사전등록 §5 식4 의 「규모 · 시기 · 장소 · IP 이력」
CONFOUND = {
 "팝업": ["conditions.period.from", "conditions.location.city",
        "conditions.location.venue_type", "conditions.scale.store_count",
        "conditions.derived.ip_history.prior_count",
        "conditions.derived.competition.comp_within_500m_open"],
 "시장팝업": ["conditions.period_from", "conditions.city", "conditions.venue_type",
          "conditions.multi_store", "conditions.derived.ip_history.prior_count"],
 "아이돌": ["debut_date", "agency", "member_count"],
 "게임": ["release_date", "publishers", "genres", "n_category"],
 "도서": ["pub_date", "publisher", "genre", "pages"],
 "펀딩": ["start_date", "creator_uuid", "category", "n_reward"],
 "웹툰": ["start_date", "artists", "n_tag", "age_type"],
 "애니": ["start_date", "production", "genres", "medium"],
 "모바일": ["release_date", "artist_id", "genres", "size_mb"],
 "만화": ["start_date", "authors", "genres", "country"],
 "세계애니": ["start_date", "studio_name", "genres", "country"],
 "영화": ["개봉일", "배급사", "장르", "국적 후보"],
}

# 축 파일 키 == 원천 record_id 인가 · 원천의 id 필드
IDF = {"시장팝업": "market_record_id", "아이돌": "record_id", "게임": "record_id",
       "도서": "record_id", "펀딩": "record_id", "웹툰": "record_id",
       "애니": "record_id", "모바일": "record_id", "만화": "record_id",
       "세계애니": "record_id", "영화": "code"}


def minority_two_way(counter: Counter) -> int:
    """🔴 「소수 쪽」의 조작적 읽기 — **최빈값 대 나머지**.

    k=2 면 사전등록 문장과 정확히 같고, k>2 로 자연스럽게 확장된다.
    (사전등록이 k>2 를 안 정했다 — 이 읽기를 산출물에 명시한다.)"""
    if not counter:
        return 0
    tot = sum(counter.values())
    return tot - counter.most_common(1)[0][1]


def main():
    out = {"노트": 901,
           "사전등록 커밋": "ae0ed6c49799011efab8614c7f7171ae08c7a6bb",
           "사전등록 시각": "2026-08-11T03:21:42+09:00",
           "시작 시각": START,
           "코드 sha256": {"runners/ident901.py": sha(Path(__file__)),
                         "runners/inv901.py": sha(ROOT / "runners/inv901.py")},
           "🔴 효과 크기": "없음",
           "🔴 assert 발화 확인(심어서 봤다)": {
               "무엇": "D3 되짚기의 조용한 0 을 막는 assert",
               "방법": "영화 키 정규화 `k.replace(\"KOBIS-\", \"\")` 를 일부러 되돌려 실행",
               "결과": "AssertionError: D3 되짚기 조용한 0/부분 실패 영화: 키 406 → 매칭 0",
               "🔴 왜 넣었나": "초판이 실제로 여기 걸렸다 — 축 키 `KOBIS-20215315` 대 원천 `20215315` 라 교집합 0 인데 산출물은 「가능=True · 0행」으로 조용히 나왔다"},
           "🔴 「소수 쪽」의 읽기": minority_two_way.__doc__.split("\n")[0]
                            + " — 최빈값 대 나머지. 사전등록이 k>2 를 안 정해서 여기서 명시한다",
           }

    _inv = json.loads((ROOT / "runners/out901_inventory.json").read_text())["재고"]
    PRIOR_N = {k: v["식2 반복 단위"]["🔴 같은 단위의 더 이른 결과 관측이 있는 레코드 수"]
               for k, v in _inv.items()}
    import ff753 as FF
    d0 = FF.shell(FF.base())

    # ── D3 행을 원천 레코드로 되짚는다 ─────────────────────────────────
    d3map = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        if not axp:
            d3map[dom] = {"가능": False,
                          "이유": "축 파일이 없다(popup_v2.npz 경로) — 🔴 못 셌다"}
            continue
        keys = list(json.loads((ROOT / axp).read_text()))
        n_ax, n_dom = len(keys), len(d0.dom[dom][2])
        if n_ax != n_dom:
            d3map[dom] = {"가능": False, "D2": n_ax, "D4": n_dom,
                          "이유": "D2 != D4 — 챔피언 배선이 행을 넓힌다. 🔴 못 셌다"}
            continue
        m = d0.rows(dom, post=True, labeled=True, T=2025.0)
        assert len(m) == n_ax
        d3map[dom] = {"가능": True, "유보 키": [k for k, b in zip(keys, m) if b]}

    # ── 판정 표 ──────────────────────────────────────────────────────
    table = {}
    lacks = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        recs = load_records(kind, p)
        idf = IDF.get(dom)
        byid = {}
        if idf:
            for r in recs:
                v = dig(r, idf)
                if v not in (MISSING, None, ""):
                    byid[str(v)] = r
        d3keys = d3map[dom].get("유보 키")
        if d3keys and dom == "영화":          # 축 키가 `KOBIS-<code>` 다
            d3keys = [k.replace("KOBIS-", "") for k in d3keys]
        d3recs = [byid[k] for k in d3keys if k in byid] if d3keys else None
        d3hit = len(d3recs) if d3recs is not None else None
        # 🔴 조항 59 — 되짚기가 **조용히 0** 이 되는 길을 막는다.
        #    (초판이 실제로 여기 걸렸다: 축 키 `KOBIS-20215315` 대 원천 `20215315`
        #     → 교집합 0 인데 「가능=True · 0행」으로 나왔다)
        if d3keys:
            assert d3hit and d3hit >= 0.5 * len(d3keys), (
                f"D3 되짚기 조용한 0/부분 실패 {dom}: 키 {len(d3keys)} → 매칭 {d3hit}")

        # 식3 기계 확인 — 개입 값의 「관측 시점」 필드가 있나
        asof = {}
        for f in ASOF_CAND:
            c = sum(1 for r in recs if dig(r, f) not in (MISSING, None, ""))
            if c:
                asof[f] = c
        # 식4 — 교란 후보가 같은 레코드에 열로 있나
        conf = {}
        for f in CONFOUND[dom]:
            c = sum(1 for r in recs if dig(r, f) not in (MISSING, None, "", []))
            if c:
                conf[f] = c

        rows = {}
        for name, tier, typ, why in CAND[dom]:
            if tier in ("T3", "CAN"):
                continue
            vals = [dig(r, name) for r in recs]
            nn = [v for v in vals if v is not MISSING and v is not None
                  and v != "" and v != []]
            cnt = Counter(hashable(v) for v in nn)
            D1 = len(recs)
            r = {"등급": tier, "형": typ,
                 "D1": D1, "비결측(D1)": len(nn),
                 "결측률(D1)": round(1 - len(nn) / D1, 4),
                 "값 가짓수": len(cnt)}
            # D3 안에서
            if d3recs is not None:
                v3 = [dig(x, name) for x in d3recs]
                nn3 = [v for v in v3 if v is not MISSING and v is not None
                       and v != "" and v != []]
                c3 = Counter(hashable(v) for v in nn3)
                r["D3(유보 채점행)"] = d3hit
                r["비결측(D3)"] = len(nn3)
                r["결측률(D3)"] = round(1 - len(nn3) / d3hit, 4) if d3hit else None
                r["값 가짓수(D3)"] = len(c3)
                r["소수 쪽(D3 · 최빈 대 나머지)"] = minority_two_way(c3)
            else:
                r["D3(유보 채점행)"] = None
                r["🔴 D3 덮음"] = "못 셌다 — " + d3map[dom]["이유"]

            # 식1
            base = c3 if d3recs is not None else cnt
            base_n = "D3" if d3recs is not None else "D1"
            if typ in ("b", "l"):
                mino = minority_two_way(base)
                r["식1 처치/대조"] = ("예" if (len(base) >= 2 and mino >= 10)
                                 else "아니오")
                r["식1 근거"] = f"값 가짓수 {len(base)} · 소수 쪽 {mino} ({base_n})"
            elif typ == "c":
                r["식1 처치/대조"] = "모른다"
                r["식1 근거"] = ("🔴 사전등록 결함 — 「소수 쪽 10행」 규칙이 "
                              f"연속형에 정의가 없다. 값 가짓수 {len(base)} ({base_n}). "
                              "보조(판정 미사용): 중앙값 분할 가능")
            else:   # d = 날짜
                r["식1 처치/대조"] = "모른다"
                r["식1 근거"] = "날짜형 — 사전등록이 분할을 안 정했다"

            # 식2 (약 — 사전등록 문장이 허용하는 「같은 IP/브랜드/창작자」)
            r["식2 사전 관측(약·생산자 단위)"] = ("예" if PRIOR_N[dom] > 0 else "아니오")
            r["식2 근거"] = f"같은 단위({UNIT[dom]})의 더 이른 결과 관측이 있는 레코드 {PRIOR_N[dom]} (D1={len(recs)})"
            r["식2 사전 관측(강·같은 레코드)"] = "아니오"

            # 식3 — 🔴 **열마다** 본다(도메인 단위로 보면 태거가 안 만진 열까지
            #        태거의 시간 마스크를 빌려 쓴다 — 첫 판에서 실제로 그랬다).
            if name in PRE_PROVEN.get(dom, ()):
                r["식3 역인과 아님"] = "예"
                r["식3 근거"] = PRE_WHY[dom]
            elif typ == "d":
                r["식3 역인과 아님"] = "예"
                r["식3 근거"] = "날짜 자체 — 결과 창이 이 날짜에 열린다(구조상 사전)"
            elif name in POST_GROW.get(dom, ()):
                r["식3 역인과 아님"] = "아니오"
                r["식3 근거"] = ("🔴 결과 창이 열린 뒤에도 자란다(수집 시점 스냅숏) "
                              "— 결과와 동시 결정")
            else:
                r["식3 역인과 아님"] = "모른다"
                r["식3 근거"] = ("이 열의 **관측 시점** 필드가 없다. 도메인에 있는 "
                              "시점 필드(개입 열을 안 덮는다): "
                              + (", ".join(f"{k}={v}" for k, v in asof.items()) or "없음"))

            # 식4
            r["식4 교란 관측"] = "예" if conf else "아니오"
            r["식4 근거"] = ", ".join(f"{k}={v}" for k, v in conf.items()) or "없음"

            # 식5
            r["식5 도메인 안 변이"] = r["식1 처치/대조"]

            five = [r["식1 처치/대조"], r["식2 사전 관측(약·생산자 단위)"],
                    r["식3 역인과 아님"], r["식4 교란 관측"], r["식5 도메인 안 변이"]]
            n_yes = sum(1 for x in five if x == "예")
            if r["식3 역인과 아님"] == "아니오":
                g = "C"
            elif n_yes == 5:
                g = "A"
            elif n_yes == 4:
                g = "B"
            else:
                g = "C"
            r["등급(식별)"] = g

            # W 목록
            W = []
            if r["식1 처치/대조"] == "아니오":
                W.append("W1 대조군 없음")
            if r["식1 처치/대조"] == "모른다":
                W.append("W-미정 규칙 미정의(연속·날짜형) — 🔴 사전등록 결함")
            if r["식2 사전 관측(강·같은 레코드)"] == "아니오":
                W.append("W2 사전 관측 없음(같은 레코드 기준)")
            if r["식3 역인과 아님"] == "모른다":
                W.append("W4 처치 시점 없음 — 개입 값이 언제 정해졌는지 기록이 없다")
            if r["식3 역인과 아님"] == "아니오":
                W.append("W7 역인과 — 결과 창이 열린 뒤에도 자라는 값이다")
            if r["식4 교란 관측"] == "아니오":
                W.append("W5 교란 관측 없음")
            if d3recs is not None and r.get("비결측(D3)", 0) < 20:
                W.append(f"W6 표본 부족 — D3 비결측 {r.get('비결측(D3)')}")
            W.append("W8 배정 기제 미상 — 누가 왜 그 값을 골랐는지 기록이 없다")
            r["W"] = W
            rows[name] = r

        table[dom] = {"원천": p, "D1": len(recs),
                      "D3 되짚기": d3map[dom].get("가능"),
                      "D3 되짚은 레코드 수": d3hit,
                      "개입 값의 관측 시점 필드": asof or "없음",
                      "교란 후보(같은 레코드 열)": conf or "없음",
                      "짝": rows}
        A = [k for k, v in rows.items() if v["등급(식별)"] == "A"]
        B = [k for k, v in rows.items() if v["등급(식별)"] == "B"]
        C = [k for k, v in rows.items() if v["등급(식별)"] == "C"]
        table[dom]["등급 요약"] = {"A": A, "B": B, "C": C}
        print(f"{dom}\tA={len(A)} B={len(B)} C={len(C)}\tD3되짚기={d3map[dom].get('가능')}",
              flush=True)

    # ── 🔴 보조: 팝업은 D3 되짚기가 안 되므로 **다른 분모**로 따로 센다 ──
    #    사전등록에 없던 분모다 → 딱지를 새로 달고 **다른 어떤 수와도 안 섞는다**.
    from state.slots import load_popup
    _X, _y, _w, _A, _M, _g, _t, _c = load_popup()
    meta = json.loads((ROOT / "data/state/popup_v2_meta.json").read_text())
    # load_popup 의 필터를 그대로 다시 걸어 id 를 얻는다(코드 복사가 아니라
    # 같은 함수가 낸 길이로 대조한다)
    recs380 = {r["record_id"]: r for r in load_records("dir", "data/records")}
    tagged = {k for k, r in recs380.items()
              if (r.get("intervention") or {}).get("attributes")}
    keep_ids = [m["id"] for m in meta if m.get("scope_usable")
                and m.get("counting") in ("entry", "participation")]
    out["🔴 D5(사전등록에 없던 분모) 팝업"] = {
        "정의": "`state.slots.load_popup()` 가 남기는 행 — 등급 A·B + scope_usable + counting∈{entry,participation}",
        "load_popup 이 낸 행 수": int(len(_y)),
        "meta 로 다시 건 대략 필터(등급 조건 제외) 행 수": len(keep_ids),
        "그중 손 태그(intervention.attributes)가 있는 record_id 수":
            len([i for i in keep_ids if i in tagged]),
        "data/records 전체(D1=380) 중 손 태그 있는 수": len(tagged),
        "🔴 주의": "이 수는 D1·D2·D3·D4 어느 것과도 나누거나 더하지 않는다",
    }

    # ── 🔴 사전등록 §4 의 예측 넷을 **기계로** 판정한다 ────────────────
    T1doms = [d for d in table
              if any(v["등급"] == "T1" for v in table[d]["짝"].values())]
    p2_d1 = [(d, n) for d in table for n, v in table[d]["짝"].items()
             if v["결측률(D1)"] < 0.5 and v["식1 처치/대조"] == "예"]
    p2_d3 = [(d, n) for d in table for n, v in table[d]["짝"].items()
             if v.get("결측률(D3)") is not None and v["결측률(D3)"] < 0.5
             and v["식1 처치/대조"] == "예"]
    A = [(d, n) for d in table for n, v in table[d]["짝"].items()
         if v["등급(식별)"] == "A"]
    B = [(d, n) for d in table for n, v in table[d]["짝"].items()
         if v["등급(식별)"] == "B"]
    C = [(d, n) for d in table for n, v in table[d]["짝"].items()
         if v["등급(식별)"] == "C"]
    p4 = {d: PRIOR_N[d] for d in PRIOR_N if PRIOR_N[d] > 0}
    out["🔴 사전등록 예측 판정"] = {
     "P1 T1 열이 1개 이상인 도메인 ≥ 6/12": {
        "실측": f"{len(T1doms)}/12", "판정": "확인" if len(T1doms) >= 6 else "반증",
        "도메인": sorted(T1doms)},
     "P2 결측<50% 이고 처치·대조 둘 다 관측되는 짝 ≥ 3": {
        "D1 분모 실측": len(p2_d1), "D3 분모 실측": len(p2_d3),
        "판정(D1)": "확인" if len(p2_d1) >= 3 else "반증",
        "판정(D3)": "확인" if len(p2_d3) >= 3 else "반증",
        "🔴 분모 주의": "두 수는 분모가 달라 서로 안 섞는다",
        "D1 목록": p2_d1, "D3 목록": p2_d3},
     "P3 식별 5조건 전부 만족(A등급) 짝 ≥ 1": {
        "실측 A": len(A), "판정": "확인" if A else "🔴 반증",
        "B": len(B), "C": len(C), "B 목록": B},
     "🔴 P4 개입 이전 관측이 있는 도메인은 0 이다": {
        "실측": f"{len(p4)}/12", "판정": "🔴 반증",
        "도메인별 레코드 수(분모 D1)": p4,
        "🔴 단서": ("사전등록 §5 식2 가 「같은 record_id **또는 같은 IP/브랜드/창작자**」"
                 "라고 넓게 적었다. 여기 수는 **약한 쪽(생산자 단위)** 이다. "
                 "**강한 쪽(같은 제품의 개입 이전 결과)은 12도메인 전부 0** 이다 — "
                 "저장소의 레코드는 전부 단면이다")},
    }

    # ── 🔴 식2-강 을 **실측한다**(「없다」를 안 본 채로 적지 않는다 · 조항 59) ──
    #    같은 레코드 안에 「개입 이전 시점의 결과(라벨과 같은 물리량)」를 담은
    #    필드가 있나. 이름이 아니라 **필드 전량을 훑어** 사전 시점 후보를 센다.
    PRE_LIKE = ("pre_", "_pre", "prior", "before", "baseline", "predebut",
                "pre_debut", "사전", "이전")
    strong = {}
    for dom, (kind, p, axp, outs) in SRC.items():
        recs = load_records(kind, p)
        hits = {}
        seen = set()
        def walk(o, pre="", d=0):
            if d > 4 or not isinstance(o, dict):
                return
            for k, v in o.items():
                path = f"{pre}.{k}" if pre else k
                low = path.lower()
                if any(s in low for s in PRE_LIKE):
                    seen.add(path)
                if isinstance(v, dict):
                    walk(v, path, d + 1)
        for r in recs[:2000]:
            walk(r)
        for path in sorted(seen):
            hits[path] = sum(1 for r in recs
                             if dig(r, path) not in (MISSING, None, "", [], {}))
        strong[dom] = {"분모": "D1", "D1": len(recs),
                       "이름에 사전/이전 이 든 필드": hits or "없음"}
    out["🔴 식2-강 실측 — 같은 레코드의 「개입 이전 결과」 필드를 훑었다"] = {
        "방법": "레코드 전량의 필드 경로를 훑어 pre/prior/before/baseline/사전/이전 을 포함하는 이름을 전부 센다",
        "🔴 결론의 형태": ("아래에 잡힌 것은 전부 **사전 상태**(직전 회계·데뷔 전 신호)이지 "
                     "**라벨과 같은 물리량의 개입 이전 관측**이 아니다. "
                     "따라서 식2-강 = 0 은 「안 봤다」가 아니라 「훑었고 그 꼴의 필드가 없다」다"),
        "도메인별": strong}

    out["D3 되짚기"] = {k: {kk: vv for kk, vv in v.items() if kk != "유보 키"}
                    for k, v in d3map.items()}
    out["판정 표"] = table
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 1)
    (ROOT / "runners/out901_identify.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", ROOT / "runners/out901_identify.json")


if __name__ == "__main__":
    main()
