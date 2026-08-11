"""노트 910 팔 ㅂ — 이벤트 축. 사전등록: `docs/prereg_910_event.md`.

    python3 runners/event910_run.py --census      # 0단계만 (빠르다)
    python3 runners/event910_run.py --run         # 0~3단계 전량

🔴 판 ρ 를 한 번도 안 돌린다. 이 팔의 자는 **기후값 대비 간격 예측**과 **구간 덮음**이다.
🔴 `data/state/eventline910.jsonl` 은 **덮어쓰지 않는다**(있으면 예외).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np                                                    # noqa: E402

from event import census as CEN                                       # noqa: E402
from event import climate as CLI                                      # noqa: E402
from event import sources as S                                        # noqa: E402

OUT = ROOT / "runners/out910_event.json"
LINE = ROOT / "data/state/eventline910.jsonl"
PREREG = ROOT / "docs/prereg_910_event.md"

#: 사전등록 §8 — 파일에 **안 쓰는** 종류(세기는 센다). 사유: 파일 크기
NO_WRITE = {"영화.일매출변화", "영화.일관객변화", "영화.순위변화"}


def now():
    return datetime.now(timezone.utc).isoformat()


def _code_sha():
    out = {}
    for rel in ["runners/event910_run.py", "event/__init__.py", "event/sources.py",
                "event/census.py", "event/climate.py"]:
        out[rel] = S.sha256(ROOT / rel)
    return out


# ==================================================================== 0단계
def stage0():
    rep, inputs = {}, {}

    pan = S.load_kobis_panel()
    inputs.update(pan["inputs"])
    k_slots, k_events = CEN.kobis_slots_and_events(pan)
    d3 = S.kobis_d3_holdout()
    inputs[d3["경로"]] = {"sha256": d3["sha256"]}

    yp = S.load_youtube_poll()
    inputs.update(yp["inputs"])
    y_slots, y_events = CEN.youtube_slots_and_events(yp)

    recs = {}
    for dom in S.DOMAIN_SOURCES:
        r = S.load_records(dom)
        recs[dom] = r
        inputs.update(r.get("inputs", {}))

    p5, _ = CEN.record_period_slots(recs)
    pv = S.load_popup_visitor()
    inputs.update(pv["inputs"])
    p6, pv_events = CEN.popup_visitor_slots(pv)

    ident = json.loads((ROOT / "runners/out901_identify.json").read_text())
    inputs["runners/out901_identify.json"] = {
        "sha256": S.sha256(ROOT / "runners/out901_identify.json")}
    pairs = {d: v["짝"] for d, v in ident["판정 표"].items()}
    p7 = CEN.intervention_col_slots(recs, pairs)

    seal = S.load_seal()
    inputs.update(seal["inputs"])
    p8 = CEN.seal_slots(seal)

    tags = {"C1": k_slots["C1"], "C2": k_slots["C2"], "C3": y_slots["C3"],
            "C4": y_slots["C4"], "C5": p5["C5"], "C6": p6["C6"],
            "C7": p7["C7"], "C8": p8["C8"]}

    tot = Counter()
    for t in tags.values():
        for nm in CEN.Bucket.NAMES:
            tot[nm] += t[nm]
        tot["후보 슬롯 전체(분모)"] += t["후보 슬롯 전체(분모)"]
    s = sum(tot[nm] for nm in CEN.Bucket.NAMES)
    assert s == tot["후보 슬롯 전체(분모)"], \
        f"🔴 전체: 넷의 합 {s} != 후보 {tot['후보 슬롯 전체(분모)']}"

    events = k_events + y_events + pv_events

    rep["0 이벤트 인구조사"] = {
        "🔴 이벤트 한 행의 정의": "(개체 id · 도메인 · 시각 · 무슨 일 · 값 전/후)",
        "🔴 넷의 갈래": list(CEN.Bucket.NAMES),
        "딱지별": tags,
        "전체(딱지 8개의 합)": {**{nm: tot[nm] for nm in CEN.Bucket.NAMES},
                       "후보 슬롯 전체(분모)": tot["후보 슬롯 전체(분모)"],
                       "🔴 넷의 합 == 후보(assert)": True},
        "🔴 딱지는 서로 다른 분모다": "C1~C8 은 슬롯의 정의가 다르다. 합은 assert 에만 쓰고 "
                          "비율의 분자·분모를 딱지 사이에 걸치지 않는다(조항 60)",
        "영화 일별 표": {k: v for k, v in k_slots.items() if k not in ("C1", "C2")},
        "유튜브 폴": {k: v for k, v in y_slots.items() if k not in ("C3", "C4")},
        "레코드 기간 사건": p5["도메인별"],
        "팝업 방문자 일별": {k: v for k, v in p6.items() if k != "C6"},
        "레코드 개입 열(C7)": p7["도메인별"],
        "🔴 C7 시각의 뜻": p7["🔴 시각의 뜻"],
        "전향 봉인(C8)": {k: v for k, v in p8.items() if k != "C8"},
        "🔴 D3(판 채점 유보 · 영화)": {
            "값": d3["D3"], "D2(축 파일 키)": d3["D2"],
            "🔴 손으로 안 옮기고 다시 계산했다": True,
            "🔴 908d 가 인용한 값과 같나(406)": d3["D3"] == 406},
    }
    return rep, events, inputs, pan, d3, recs, pairs, k_slots


# ==================================================================== 1단계
def stage1(events, inputs, rep):
    if LINE.exists():
        raise FileExistsError(f"🔴 {LINE} 이 이미 있다 — **덮어쓰기 금지**(사전등록 §8)")

    by_dom, by_kind, by_kind_written = Counter(), Counter(), Counter()
    gate_pass, gate_fail, neg = 0, 0, 0
    written = 0
    hdr = {
        "_헤더": True, "노트": 910, "UTC": now(),
        "사전등록": {"파일": "docs/prereg_910_event.md", "sha256": S.sha256(PREREG)},
        "코드 sha256": _code_sha(),
        "입력 sha256": inputs,
        "🔴 이 파일이 담는 것": "5칸(개체·도메인·시각·무슨 일·값 전/후)이 다 차는 이벤트",
        "🔴 파일에 안 쓰는 종류(세기는 셌다 · 사유 파일 크기)": sorted(NO_WRITE),
        "🔴 두 시각": {"t_occur": "그 일이 일어난 시각",
                   "t_observe": "우리 저장소가 처음 알 수 있었던 시각",
                   "사후_동일시각": "t_observe 를 독립적으로 못 얻어 t_occur 로 대신 채웠다"},
    }
    for e in events:
        by_dom[e["도메인"]] += 1
        by_kind[e["종류"]] += 1
        if e.get("사후_동일시각"):
            gate_fail += 1
        else:
            gate_pass += 1
        if e.get("lag_days") is not None and e["lag_days"] < 0:
            neg += 1
        #: 🔴 W-C — 5칸 완전 행은 셋이 전부 non-null 이어야 한다
        assert e["t_occur"] is not None and e["값_전"] is not None \
            and e["값_후"] is not None, f"🔴 W-C 위반: {e}"
        if e["종류"] not in NO_WRITE:
            written += 1
            by_kind_written[e["종류"]] += 1

    hdr["행 수(이벤트 전량)"] = len(events)
    hdr["행 수(파일에 쓴 것)"] = written
    hdr["도메인별"] = dict(by_dom)
    hdr["종류별(전량)"] = dict(by_kind)
    hdr["종류별(파일에 쓴 것)"] = dict(by_kind_written)
    hdr["시간 게이트 통과"] = gate_pass
    hdr["시간 게이트 불통과(사후_동일시각)"] = gate_fail
    hdr["🔴 lag_days < 0"] = neg
    assert gate_pass + gate_fail == len(events), "🔴 게이트 분해의 합 != 전량"

    tmp = LINE.with_suffix(".jsonl.part")
    with open(tmp, "w") as f:
        f.write(json.dumps(hdr, ensure_ascii=False) + "\n")
        for e in events:
            if e["종류"] in NO_WRITE:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.rename(tmp, LINE)

    rep["1 이벤트 표"] = {
        "파일": str(LINE.relative_to(ROOT)),
        "sha256": S.sha256(LINE), "바이트": LINE.stat().st_size,
        **{k: v for k, v in hdr.items() if not k.startswith("_")
           and k not in ("입력 sha256", "코드 sha256")},
    }
    return rep


# ==================================================================== 2단계
def stage2(events, rep, *, B=2000, n_perm=1000):
    #: 🔴 헤드라인은 「물질」 판이다(사전등록 §4). 원 판은 참고로만 낸다.
    def _prep(only_material):
        ev = [e for e in events if e["종류"] not in NO_WRITE]
        if only_material:
            ev = [e for e in ev if e.get("물질") is not False]
        return ev

    out = {}
    for name, only_mat in (("헤드라인 — 물질(material) 판", True), ("참고 — 원(raw) 판", False)):
        ev = _prep(only_mat)
        gaps = CLI.gaps_by_entity(ev)
        if not gaps:
            out[name] = {"상태": "🔴 못 잰다 — 간격이 0개다"}
            continue
        dist = {}
        for k in sorted({(g["도메인"], g["종류"]) for g in gaps}):
            xs = np.asarray([g["gap"] for g in gaps if (g["도메인"], g["종류"]) == k])
            dist[str(k)] = {"n": int(xs.size), "중앙": float(np.median(xs)),
                            "10분위": float(np.percentile(xs, 10)),
                            "90분위": float(np.percentile(xs, 90)),
                            "평균": float(xs.mean()), "최대": int(xs.max())}
        dom_dist = {}
        for d in sorted({g["도메인"] for g in gaps}):
            xs = np.asarray([g["gap"] for g in gaps if g["도메인"] == d])
            dom_dist[d] = {"n": int(xs.size), "중앙": float(np.median(xs)),
                           "10분위": float(np.percentile(xs, 10)),
                           "90분위": float(np.percentile(xs, 90))}
        res = CLI.climate_vs_conditional(gaps)
        blk = {"간격 수(분모)": len(gaps),
               "간격 분포 — (도메인, 종류)": dist,
               "간격 분포 — 도메인(기후값의 층)": dom_dist,
               **{k: v for k, v in res.items() if not k.startswith("_")}}
        if "_imp" in res:
            blk["🔴 개체 군집 부트스트랩(규약 47)"] = CLI.boot_improvement(
                res["_imp"], res["_ents"], B=B)
            blk["🔴 덮음"] = CLI.coverage(res)
            #: 🔴 노트 133 — 첫 양수를 그대로 안 받는다
            neg = CLI.climate_vs_conditional(gaps, kind_shuffle_seed=4242)
            blk["🔴 음성 대조(종류 라벨 섞기)"] = {
                k: v for k, v in neg.items() if not k.startswith("_")}
            if "_imp" in neg:
                blk["🔴 음성 대조 구간"] = CLI.boot_improvement(
                    neg["_imp"], neg["_ents"], B=max(400, B // 4))
            per_dom = {}
            for d in sorted({g["도메인"] for g in gaps}):
                sub = [g for g in gaps if g["도메인"] == d]
                r2 = CLI.climate_vs_conditional(sub)
                per_dom[d] = {k: v for k, v in r2.items() if not k.startswith("_")}
            blk["🔴 도메인별 분해(이득이 한 도메인에서만 오나)"] = per_dom
            #: 🔴 진단(판정 미사용) — 「③ 을 0 에서 올리려면 무엇이 필요한가」의 답을 수로
            dg = CLI.diag_nth_conditional(gaps)
            if "_imp" in dg:
                dg["🔴 구간(진단)"] = CLI.boot_improvement(
                    dg["_imp"], dg["_ents"], B=max(400, B // 4))
            blk["🔴 진단(판정 미사용) — 개봉 후 일차 구간을 더한 조건부"] = {
                k: v for k, v in dg.items() if not k.startswith("_")}
        out[name] = blk

    ev_all = [e for e in events if e["종류"] not in NO_WRITE]
    out["🔴 순열 selectivity"] = CLI.permutation_selectivity(ev_all, n_perm=n_perm)
    out["🔴 보조 진단 — 하루의 종류 집합(순서 인공물 없음)"] = CLI.transition_dayset(
        ev_all, n_perm=max(100, n_perm // 5))
    rep["2 기후값"] = out
    return rep


# ==================================================================== 3단계
def stage3(rep, events, d3, recs, pairs, k_slots):
    ev = [e for e in events if not e.get("사후_동일시각")]
    dom_ct = Counter(e["도메인"] for e in ev)
    d3_titles = set(d3["제목"].values())
    in_d3 = sum(1 for e in ev if e["도메인"] == "영화" and e["개체"] in d3_titles)
    ent_in_d3 = len({e["개체"] for e in ev if e["도메인"] == "영화" and e["개체"] in d3_titles})

    tbl = {
        "① 우려사항": {
            "떠받치는 행": 0, "딱지": "이 표(eventline910)",
            "🔴 판정": "🔴 **이 표에는 없다**. 「우려」는 이벤트가 아니라 **이벤트→나쁜 결과의 조건부**다. "
                   "이 표에는 결과 라벨이 붙은 이벤트 행이 0 이다 — 라벨 `y` 는 **개체당 하나**이고 "
                   "이벤트당 하나가 아니다",
            "무엇이 있으면 올라가나": "같은 개체의 **이벤트 이후 결과 관측**. 지금은 라벨이 개체당 1개라 "
                            "이벤트 하나에 결과 하나를 붙일 수 없다",
        },
        "② 결과": {
            "떠받치는 행": int(sum(1 for e in ev if e["종류"] in
                                ("영화.일매출변화", "영화.일관객변화", "팝업.일별방문"))),
            "딱지": "이 표(eventline910) · 🔴 그중 파일에 쓴 것은 팝업.일별방문 뿐",
            "🔴 판정": "결과 계열은 있다 — 그러나 **개입과 짝지어진 결과**는 다른 물건이다. "
                   "노트 901 이 A등급 0 · 노트 903 이 A등급 효과가 위약 한복판(0비트)이라 적었다",
        },
        "③ 언제 어떤 불특정 이벤트가 발생할지": {
            "떠받치는 행": len(ev),
            "딱지": "이 표(eventline910) · 시간 게이트 통과 행",
            "도메인별": dict(dom_ct),
            "🔴 그중 판 채점 유보(영화 D3 406)에 드는 행": in_d3,
            "🔴 그 유보 개체 수": ent_in_d3,
            "🔴 판정": "→ 2단계의 기후값 대비 결과를 본다",
        },
        "④ 개선 제안": {
            "떠받치는 행": 0, "딱지": "이 표(eventline910)",
            "🔴 확인만 했다(다시 안 쟀다)": "노트 903 — A등급 효과가 위약 한복판(0비트)",
            "🔴 판정": "🔴 **이 표에는 없다**. 개선 제안은 「이 열을 이렇게 바꾸면 결과가 이렇게 된다」이고 "
                   "그러려면 **같은 개체의 같은 열이 두 값을 가진 관측**이 필요하다",
            "무엇이 몇 행 더 필요한가": None,   # 아래에서 채운다
        },
        "⑤ 파생효과": {
            "떠받치는 행": 0, "딱지": "이 표(eventline910)",
            "🔴 확인만 했다(다시 안 쟀다)": "노트 897 — 합류점 0개",
            "🔴 판정": "🔴 **이 표에는 없다**. 파생효과는 **개체 A 의 이벤트가 개체 B 의 결과를 바꾸는 것**이고 "
                   "이 표에는 개체를 잇는 변이 0 이다",
            "무엇이 몇 행 더 필요한가": None,
        },
    }

    #: ④ — 「같은 개체·같은 열의 두 번째 판」이 몇 행 더 있어야 하나
    need4 = {}
    for dom, pd in pairs.items():
        cols = [c for c, v in pd.items() if v.get("등급") in ("T1", "T2")]
        r = recs.get(dom, {})
        d1 = r.get("D1")
        need4[dom] = {
            "D1(원천 레코드)": d1, "T1+T2 열 수": cols and len(cols) or 0,
            "🔴 지금 있는 「같은 열의 두 번째 판」": 0,
            "🔴 최소 처치·대조 각 10행(식1 기준)을 만들려면": (
                "그 도메인의 개입 열을 **다시 읽는 수집기 1개** + 같은 레코드의 두 번째 판 "
                f"**최소 20행**(D1 {d1} 중). 지평 902 §1.1 실측: 이 저장소들의 파일 mtime "
                "가짓수가 1~2 라 두 번째 판이 0 이다"),
        }
    tbl["④ 개선 제안"]["무엇이 몇 행 더 필요한가"] = need4
    tbl["④ 개선 제안"]["🔴 합계 — 12도메인 전부에 대해"] = {
        "필요한 수집기": 12, "지금 있는 수집기": 0,
        "🔴 근거": "지평 902 §6.3 — 지금 도는 수집기 셋(kobis · yt_poll · popupsnap) 중 "
               "901 이 센 T1 열을 다시 읽는 것이 **0개**",
    }

    #: ⑤ — 개체를 잇는 변이 몇 개나 있어야 하나
    tbl["⑤ 파생효과"]["무엇이 몇 행 더 필요한가"] = {
        "🔴 지금 이 표의 변(개체→개체) 수": 0,
        "🔴 왜 0 인가": "이벤트 행의 개체 id 는 **한 도메인 안에서만** 유효하고, 도메인을 잇는 열쇠가 "
                 "이 표에 없다. 노트 897 이 「합류점 0개」로 적은 것과 같은 결핍이다",
        "무엇이 있으면 1 이상이 되나": {
            "가 — 공간 열쇠": "팝업/시장팝업의 주소·격자와 생활인구 250m 격자를 잇는 열. "
                       "`data/ingest/seoul_lifepop/*.zip` 19개월이 **압축 그대로** 있고 "
                       "이 팔은 **안 열었다**(못 읽었다가 아니라 **안 읽었다**)",
            "나 — IP/브랜드 열쇠": "`entities.brand_key` 는 팝업에만 있다. 12도메인 공통 열쇠가 없다",
            "다 — 최소 행": "변 하나를 세려면 **같은 시간축 위의 서로 다른 도메인 이벤트 2행**이 필요하다. "
                     f"지금 시간 게이트를 통과한 도메인 수는 {len({e['도메인'] for e in ev})} 이다",
        },
    }
    rep["3 다섯 출력 도달 가능성"] = tbl
    return rep


# ==================================================================== 예측 판정
DOM12 = ["팝업", "시장팝업", "아이돌", "게임", "도서", "펀딩", "웹툰", "애니",
         "모바일", "만화", "세계애니", "영화"]


def verdicts(rep, events):
    n = len(events)
    dom = Counter(e["도메인"] for e in events)
    n_movie = dom.get("영화", 0)
    dom12_hit = sorted({d for d in dom if d in DOM12})
    c5 = rep["0 이벤트 인구조사"]["딱지별"]["C5"]["5칸 완전"]
    head = rep["2 기후값"]["헤드라인 — 물질(material) 판"]
    bs = head.get("🔴 개체 군집 부트스트랩(규약 47)", {})
    cov = head.get("🔴 덮음", {})
    perm = rep["2 기후값"]["🔴 순열 selectivity"]
    t3 = rep["3 다섯 출력 도달 가능성"]

    win = bs.get("판정") == "승"
    rate = head.get("개선율")
    cov_dom = (cov.get("도메인 구간") or {}).get("실측 덮음")
    cov_kind = (cov.get("종류 구간") or {}).get("실측 덮음")

    out = {
        "P1 5칸 완전 이벤트 행 200,000~800,000": {
            "실측": n, "구간": [200000, 800000],
            "판정": "확인" if 200000 <= n <= 800000 else "🔴 반증"},
        "P2 영화 도메인 비중 ≥ 0.97": {
            "실측": (n_movie / n) if n else None, "분모": n,
            "판정": "확인" if n and (n_movie / n) >= 0.97 else "🔴 반증"},
        "P3 5칸 이벤트가 있는 12도메인 중 도메인 수 ≤ 3": {
            "실측": len(dom12_hit), "목록": dom12_hit,
            "🔴 12도메인 밖": sorted(set(dom) - set(DOM12)),
            "판정": "확인" if len(dom12_hit) <= 3 else "🔴 반증"},
        "P4 C5(레코드 기간 사건) 중 5칸 완전 = 0": {
            "실측": c5, "판정": "확인" if c5 == 0 else "🔴 반증"},
        "P5 조건부 간격 예측이 기후값을 이긴다(개선폭 < 30%)": {
            "구간": [bs.get("lo"), bs.get("hi")], "구간 종류": bs.get("구간 종류"),
            "점추정(일)": bs.get("점추정"), "개선율": rate,
            "판정": ("확인" if (win and rate is not None and rate < 0.30)
                   else "🔴 반증(가) — 못 이긴다" if not win
                   else "🔴 반증(나) — 개선폭 ≥ 30%"),
            "🔴 사전등록이 정한 뜻": "못 이기면 ③ 은 이 표로도 0 이다"},
        "P6 10~90분위 덮음이 명목 0.80 에 미달": {
            "도메인 구간 실측 덮음": cov_dom, "종류 구간 실측 덮음": cov_kind,
            "명목": 0.80,
            "판정": ("확인" if (cov_dom is not None and cov_dom < 0.80)
                   else "🔴 반증"),
            "🔴 벗어난 방향": ("과대 덮음(구간이 너무 넓다)"
                       if cov_dom is not None and cov_dom > 0.80 else "과소 덮음"),
            "🔴 벗어난 크기": (cov_dom - 0.80) if cov_dom is not None else None},
        "P7 순열 selectivity 발화(p < 0.05)": {
            "p": perm.get("p"), "실측 총변동거리": perm.get("실측 총변동거리"),
            "귀무 95분위": perm.get("귀무 95분위"),
            "판정": "확인" if (perm.get("p") or 1) < 0.05 else "🔴 반증"},
        "P8 떠받치는 것은 ③ 하나 · ④·⑤ 는 0행": {
            "①": t3["① 우려사항"]["떠받치는 행"],
            "②": t3["② 결과"]["떠받치는 행"],
            "③": t3["③ 언제 어떤 불특정 이벤트가 발생할지"]["떠받치는 행"],
            "④": t3["④ 개선 제안"]["떠받치는 행"],
            "⑤": t3["⑤ 파생효과"]["떠받치는 행"],
            "판정": ("확인" if (t3["④ 개선 제안"]["떠받치는 행"] == 0
                             and t3["⑤ 파생효과"]["떠받치는 행"] == 0) else "🔴 반증"),
            "🔴 단서": "②는 결과 계열 행이 0 이 아니다 — 그러나 **개입과 짝지어진** 결과는 아니다"},
    }
    n_ok = sum(1 for v in out.values() if v["판정"] == "확인")
    out["🔴 요약"] = {"예측 수(분모)": 8, "확인": n_ok, "반증": 8 - n_ok}
    return out


# ==================================================================== 배선
def wiring(pan, events):
    w = {}
    #: W-B — 한 갈래를 일부러 빼면 발화하나
    b = CEN.Bucket("시험")
    b.add(True, True)
    b.add(True, False)
    try:
        b.total += 1                      # 심은 결함: 분모만 늘린다
        b.out()
        fired = False
    except AssertionError:
        fired = True
    w["W-B 넷의 합 == 후보"] = {"심은 결함": "분모만 +1", "발화": fired, "통과": fired}

    #: W-C — 5칸 행에 null 을 심으면 발화하나
    bad = dict(events[0])
    bad["값_후"] = None
    try:
        assert bad["t_occur"] is not None and bad["값_전"] is not None \
            and bad["값_후"] is not None
        fired = False
    except AssertionError:
        fired = True
    w["W-C 5칸 non-null"] = {"심은 결함": "값_후 = None", "발화": fired, "통과": fired}

    #: W-D — 카나리아는 stage0 에서 이미 돈다(열 없음을 「0」으로 안 읽나)
    #: W-E — `KOBIS-` 정규화를 되돌리면 매칭이 조용히 0 이 되나
    import calendar
    ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
    keys_ok, keys_bad = set(), set()
    for k, v in ax.items():
        rd, y = v.get("release_date"), v.get("y")
        if not rd or y is None:
            continue
        dd = S._parse_day(rd)
        if dd is None:
            continue
        yf = dd.year + (dd.timetuple().tm_yday - 1) / (366 if calendar.isleap(dd.year) else 365)
        if yf >= 2025.0:
            keys_ok.add(k.replace("KOBIS-", ""))
            keys_bad.add(k)               # 심은 결함: 정규화를 안 한다
    src = {r.get("code") for r in S.load_records("영화")["레코드"]}
    w["W-E D3 되짚기"] = {
        "정규화 O — 원천과 붙는 수": len(keys_ok & src),
        "🔴 정규화 X(심은 결함) — 원천과 붙는 수": len(keys_bad & src),
        "발화": len(keys_bad & src) == 0 and len(keys_ok & src) > 0,
        "통과": len(keys_bad & src) == 0 and len(keys_ok & src) > 0,
        "D3": len(keys_ok),
    }

    #: W-F — lag_days < 0
    neg = [e for e in events if e.get("lag_days") is not None and e["lag_days"] < 0]
    w["W-F lag_days < 0"] = {"수": len(neg), "전량": neg[:200],
                             "🔴 200 을 넘으면 앞 200 만 실었다": len(neg) > 200}

    #: W-G — 홀드아웃 누설
    ents = ["a", "b", "c", "d", "e", "f", "g", "h"]
    tr, ho = CLI.split(ents)
    leak = bool(tr & ho)
    try:
        tr2 = set(ents)
        assert not (tr2 & ho) or not ho
        fired2 = bool(ho)
    except AssertionError:
        fired2 = True
    w["W-G 홀드아웃 누설"] = {"학습": len(tr), "홀드아웃": len(ho), "겹침": len(tr & ho),
                       "심은 결함(학습=전량)이 발화하나": fired2, "통과": (not leak) and fired2}
    return w


# ==================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--run", action="store_true")
    #: 🔴 시운전 — 2~3단계만 돌리고 이벤트 표를 **안 쓴다**(덮어쓰기 금지를 지키려고)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--perm", type=int, default=1000)
    a = ap.parse_args()

    t0 = now()
    rep = {"노트": 910, "팔": "ㅂ — 이벤트 축",
           "사전등록": {"파일": "docs/prereg_910_event.md", "sha256": S.sha256(PREREG),
                   "mtime(UTC)": S.mtime_utc(PREREG),
                   "🔴 커밋 안 함": "지시가 커밋을 금지했다 — sha256 을 산출물에 박는다"},
           "시작 시각(UTC)": t0,
           "🔴 판 ρ": "한 번도 안 돌렸다. 이 팔의 자는 기후값 대비 간격 예측과 구간 덮음이다",
           "코드 sha256": _code_sha()}

    rep0, events, inputs, pan, d3, recs, pairs, k_slots = stage0()
    rep.update(rep0)
    rep["입력 sha256"] = inputs
    if a.census:
        rep["끝 시각(UTC)"] = now()
        print(json.dumps(rep["0 이벤트 인구조사"], ensure_ascii=False, indent=1)[:6000])
        return

    if not a.dry:
        rep = stage1(events, inputs, rep)
    rep = stage2(events, rep, B=a.B, n_perm=a.perm)
    rep = stage3(rep, events, d3, recs, pairs, k_slots)
    rep["4 배선 검사"] = wiring(pan, events)
    rep["6 사전등록 예측 판정"] = verdicts(rep, events)
    if a.dry:
        p = ROOT / "runners/out910_event.dry.json"
        p.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        print(f"[시운전] wrote {p} — 이벤트 표는 **안 썼다**")
        return
    rep["5 못 한 것 (🔴 「없다」가 아니다)"] = [
        "🔴 `data/ingest/seoul_lifepop/*.zip` 19개월(8.7GB) — **안 열었다**. 압축을 안 풀었다",
        "🔴 `data/state/visitors/*.json` 78파일 — **안 열었다**",
        "🔴 KOBIS 빠진 16일(그중 최근 6일 2026-08-02~07) — **되메우지 않았다**(유료 API 금지)",
        "🔴 영화 개체 키는 **제목 문자열**이다 — `movieCd` 가 일별 표에 없어 재개봉이 뭉친다(지평 902 §2.1)",
        "🔴 효과 크기를 안 냈다 — 이 팔은 **세고 표를 만드는 팔**이다",
        "🔴 `lab/semtoken908.py` · `state/ssl909.py` 를 **읽지 않았다**(다른 두 에이전트가 쓰는 중)",
        "🔴 커밋·`git add`·원장 수정 **안 했다**",
        "🔴 아이돌 D3 교집합 — 901·902 와 같은 이유(D2 81 ≠ D4 173)로 **못 셌다**",
    ]
    rep["끝 시각(UTC)"] = now()
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"wrote {LINE} ({LINE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
