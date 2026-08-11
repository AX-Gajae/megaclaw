"""0단계 — 「이벤트」가 이 저장소에 몇 개나 있는지 **직접 센다**.

이벤트 하나 = (개체 id · 도메인 · 시각 · 무슨 일이 일어났나 · 값 전/후).
🔴 후보 슬롯을 **두 이진 깃발의 곱**으로 넷으로 가른다 — 배타이고 전수다.

    5칸 완전    시각 O · 값 전/후 O
    4칸         시각 O · 값 전/후 X
    3칸         시각 X · 값 전/후 O
    ≤2칸        시각 X · 값 전/후 X

🔴 **넷의 합 == 후보 슬롯 전체** 를 소스마다, 그리고 전체로 `assert` 로 건다(W-B).
🔴 분모 딱지(C1~C8)를 칸마다 붙이고 서로 다른 분모를 이어 붙이지 않는다(조항 60).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from . import sources as S


class Bucket:
    """넷으로 가르는 계수기. 🔴 합 == 분모를 스스로 안다."""

    NAMES = ("5칸 완전", "4칸(시각O·값전후X)", "3칸(시각X·값전후O)", "≤2칸(시각X·값전후X)")

    def __init__(self, tag: str, note: str = ""):
        self.tag, self.note = tag, note
        self.c = Counter()
        self.total = 0

    def add(self, has_time: bool, has_ba: bool, n: int = 1):
        idx = 0 if (has_time and has_ba) else 1 if has_time else 2 if has_ba else 3
        self.c[self.NAMES[idx]] += n
        self.total += n

    def out(self) -> dict:
        d = {k: self.c.get(k, 0) for k in self.NAMES}
        s = sum(d.values())
        assert s == self.total, f"{self.tag}: 넷의 합 {s} != 후보 {self.total}"
        d["후보 슬롯 전체(분모)"] = self.total
        d["🔴 넷의 합 == 후보(assert)"] = True
        d["딱지"] = self.tag
        if self.note:
            d["슬롯 하나의 정의"] = self.note
        return d


def _d(s):
    return S._parse_day(s)


# ------------------------------------------------------------------ C1 · C2
def kobis_slots_and_events(pan: dict, *, canary: bool = True):
    """영화 일별 표 → C1(전이×열) · C2(개체 사건) 슬롯과 5칸 완전 이벤트."""
    panel = pan["panel"]
    obs = pan["obs_by_date"]
    all_dates = sorted(obs)
    last_panel_day = all_dates[-1]

    track = list(S.KOBIS_TRACK) + ([S.CANARY_COL] if canary else [])
    c1 = Bucket("C1", "(제목, 연속 관측일 쌍, 추적 열)")
    c2 = Bucket("C2", "(제목, 개체 사건) — 개봉·차트이탈·차트재진입")
    canary_hits = Counter()
    col_present = Counter()

    events = []
    n_trans = 0
    neg_lag = []
    raw_change = Counter()
    mat_change = Counter()

    for title, seq in panel.items():
        # ---- C1
        for i in range(1, len(seq)):
            n_trans += 1
            (dp, cp, rp), (dc, cc, rc) = seq[i - 1], seq[i]
            t_obs = max(obs.get(dp, ""), obs.get(dc, ""))
            for col in track:
                if col == "개봉일":
                    a, b = rp, rc
                    present = True
                elif col == S.CANARY_COL:
                    #: 🔴 W-D 카나리아 — 없는 열은 「0」이 아니라 「열 없음」으로 보고한다
                    present = (col in cp) or (col in cc)
                    canary_hits[col] += int(present)
                    a = b = None
                else:
                    present = (col in cp) or (col in cc)
                    a, b = cp.get(col), cc.get(col)
                col_present[col] += int(present)
                if col == S.CANARY_COL:
                    continue          # 슬롯으로 안 센다 — 존재 여부만 보고한다
                has_ba = (a is not None) and (b is not None)
                c1.add(True, has_ba)
                if not has_ba or a == b:
                    continue
                kind_map = {"스크린수": "영화.스크린수변화", "상영횟수": "영화.상영횟수변화",
                            "순위": "영화.순위변화", "매출액": "영화.일매출변화",
                            "관객수": "영화.일관객변화", "개봉일": "영화.개봉일변경"}
                kind = kind_map[col]
                raw_change[kind] += 1
                mat = None
                if col in ("스크린수", "상영횟수"):
                    dlt = b - a
                    mat = (abs(dlt) >= S.MAT_ABS
                           and abs(dlt) / max(abs(a), 1) >= S.MAT_REL)
                    if mat:
                        mat_change[kind] += 1
                lag = None
                try:
                    lag = (S.datetime.fromisoformat(t_obs.replace("Z", "+00:00")).date()
                           - _d(dc)).days
                except Exception:
                    lag = None
                if lag is not None and lag < 0:
                    neg_lag.append({"개체": title, "t_occur": dc, "t_observe": t_obs})
                #: 🔴 개봉 후 일차 — 예측 시점에 이미 알 수 있는 값(사후 아님)
                rel_d, occ_d = _d(rc), _d(dc)
                nth = (occ_d - rel_d).days if (rel_d and occ_d) else None
                events.append({
                    "개체": title, "도메인": "영화", "종류": kind,
                    "t_occur": dc, "t_observe": t_obs, "lag_days": lag,
                    "사후_동일시각": False,
                    "값_전": a, "값_후": b,
                    "물질": mat, "직전_시각": dp, "일차": nth, "출처딱지": "C1",
                })

        # ---- C2 : 개봉 · 차트이탈 · 차트재진입
        rel = _d(seq[0][2])
        c2.add(rel is not None, False)
        gap_dates = []
        for i in range(1, len(seq)):
            a, b = _d(seq[i - 1][0]), _d(seq[i][0])
            if a and b and (b - a).days > 1:
                gap_dates.append(b.isoformat())
        left = seq[-1][0] < last_panel_day
        c2.add(bool(left), False)                       # 차트이탈
        c2.add(bool(gap_dates), False)                  # 차트재진입

    #: C2 는 「4칸 이하」라 5칸 이벤트를 안 낸다 — 표에는 안 들어간다(사전등록 §4)
    return {
        "C1": c1.out(), "C2": c2.out(),
        "전이 수": n_trans, "고유 제목": len(panel), "고유 날짜": len(all_dates),
        "추적 열": S.KOBIS_TRACK,
        "🔴 W-D 카나리아": {
            "열 이름": S.CANARY_COL,
            "전이 중 그 열이 존재한 수": canary_hits.get(S.CANARY_COL, 0),
            "보고": ("🔴 열 없음 — 「변화 0」이 아니다"
                   if canary_hits.get(S.CANARY_COL, 0) == 0 else "🔴 카나리아 실패"),
            "통과": canary_hits.get(S.CANARY_COL, 0) == 0,
        },
        "열별 존재한 전이 수": dict(col_present),
        "원(raw) 변화 수": dict(raw_change),
        "물질(material) 변화 수": dict(mat_change),
        "🔴 lag_days < 0 인 행": neg_lag,
    }, events


# ------------------------------------------------------------------ C3 · C4
def youtube_slots_and_events(yp: dict):
    snaps = yp["snaps"]
    c3 = Bucket("C3", "(영상 id, 연속 스냅숏 쌍, 열) — 조회수·제목")
    c4 = Bucket("C4", "(영상 id, 게시)")
    events, n_trans = [], 0
    ids = set()
    for _, v in snaps:
        ids |= set(v)

    def _views(x):
        if x is None:
            return None
        try:
            return int(str(x).replace(",", ""))
        except ValueError:
            return None

    for i in range(1, len(snaps)):
        (tp, vp), (tc, vc) = snaps[i - 1], snaps[i]
        for vid in ids:
            a, b = vp.get(vid), vc.get(vid)
            if a is None or b is None:
                c3.add(True, False, 2)      # 창이 굴러가 한쪽이 없다 → 값 전/후 없음
                continue
            n_trans += 1
            for col, kind in (("조회수", "유튜브.조회수변화"), ("제목", "유튜브.제목변경")):
                x = _views(a.get(col)) if col == "조회수" else a.get(col)
                y = _views(b.get(col)) if col == "조회수" else b.get(col)
                has_ba = (x is not None) and (y is not None)
                c3.add(True, has_ba)
                if not has_ba or x == y:
                    continue
                events.append({
                    "개체": vid, "도메인": "🔴 채점 도메인 아님(유튜브 폴)", "종류": kind,
                    "t_occur": tc, "t_observe": tc, "lag_days": 0,
                    #: 🔴 발생 시각을 독립적으로 못 얻는다 — 관측 순간이 곧 시각이다
                    "사후_동일시각": True,
                    "값_전": x, "값_후": y, "물질": None,
                    "직전_시각": tp, "출처딱지": "C3",
                })
    for vid in ids:
        pub = None
        for _, v in snaps:
            if vid in v:
                pub = v[vid].get("게시일")
                break
        c4.add(pub is not None, False)
    return {"C3": c3.out(), "C4": c4.out(), "고유 영상": len(ids),
            "값 전/후가 둘 다 있는 전이 수": n_trans, "스냅숏 수": len(snaps)}, events


# ------------------------------------------------------------------ C5
def record_period_slots(recs_by_dom: dict):
    c5 = Bucket("C5", "(레코드, 기간 사건) — 팝업·시장팝업 개시/종료 · 아이돌 데뷔")
    per_dom = {}
    events = []                      # 🔴 전부 4칸이라 이벤트 표에는 안 들어간다
    for dom, evs in S.PERIOD_EVENTS.items():
        r = recs_by_dom[dom]
        if r["상태"] != "읽었다":
            per_dom[dom] = {"상태": r["상태"]}
            continue
        got = Counter()
        for rec in r["레코드"]:
            for name, path in evs:
                dd = _d(S._dig(rec, path))
                c5.add(dd is not None, False)
                got[name] += int(dd is not None)
        per_dom[dom] = {"D1": r["D1"], "슬롯": r["D1"] * len(evs),
                        "시각이 파싱된 수": dict(got),
                        "🔴 값 전/후": "0 — 레코드는 단면이라 같은 열의 두 번째 판이 없다"}
    return {"C5": c5.out(), "도메인별": per_dom}, events


# ------------------------------------------------------------------ C6
def popup_visitor_slots(pv: dict):
    c6 = Bucket("C6", "(engagement_id, visit_date) 및 그 연속 쌍")
    rows = pv["행"]
    by = defaultdict(list)
    for r in rows:
        dd = _d(r.get("visit_date"))
        by[r.get("engagement_id")].append((dd, r))
    events = []
    n_pair = 0
    for eid, lst in by.items():
        lst = [x for x in lst if x[0] is not None] + [x for x in lst if x[0] is None]
        lst.sort(key=lambda x: (x[0] is None, x[0]))
        for i, (dd, r) in enumerate(lst):
            has_prev = i > 0 and lst[i - 1][0] is not None
            has_ba = has_prev and (r.get("total_visitor_count") is not None) and (
                lst[i - 1][1].get("total_visitor_count") is not None)
            c6.add(dd is not None, bool(has_ba))
            if dd is not None and has_ba:
                n_pair += 1
                t_obs = r.get("_스냅샷(UTC)")
                try:
                    lag = (S.datetime.fromisoformat(t_obs.replace("Z", "+00:00")).date()
                           - dd).days
                except Exception:
                    lag = None
                events.append({
                    "개체": eid, "도메인": "팝업", "종류": "팝업.일별방문",
                    "t_occur": dd.isoformat(), "t_observe": t_obs, "lag_days": lag,
                    "사후_동일시각": False,
                    "값_전": int(lst[i - 1][1]["total_visitor_count"]),
                    "값_후": int(r["total_visitor_count"]),
                    "물질": None, "직전_시각": lst[i - 1][0].isoformat(), "출처딱지": "C6",
                })
    return {"C6": c6.out(), "행": len(rows), "고유 engagement_id": len(by),
            "5칸이 된 쌍": n_pair}, events


# ------------------------------------------------------------------ C7
def intervention_col_slots(recs_by_dom: dict, pairs: dict):
    """(레코드, 901 이 T1/T2 로 센 열) 슬롯.

    🔴 시각은 **결정 시각이 아니라 「결과 창이 열리는 날」**(상한)이다. 딱지를 단다.
    🔴 값 전/후는 **구조적으로 0** — 같은 레코드의 두 번째 판이 저장소에 없다(지평 902 §1.1).
    """
    c7 = Bucket("C7", "(레코드, 901 이 T1/T2 로 센 열)")
    per_dom = {}
    for dom, pd in pairs.items():
        cols = [c for c, v in pd.items() if v.get("등급") in ("T1", "T2")]
        r = recs_by_dom.get(dom, {})
        if r.get("상태") != "읽었다":
            per_dom[dom] = {"상태": r.get("상태", "🔴 못 읽었다"), "열 수": len(cols)}
            continue
        wpath = S.WINDOW_START.get(dom)
        n_time = 0
        for rec in r["레코드"]:
            has_time = _d(S._dig(rec, wpath)) is not None if wpath else False
            n_time += int(has_time)
            c7.add(has_time, False, len(cols))
        per_dom[dom] = {"D1": r["D1"], "T1+T2 열 수": len(cols),
                        "슬롯": r["D1"] * len(cols),
                        "창 시작일 필드": wpath, "창 시작일이 파싱된 레코드": n_time,
                        "🔴 값 전/후": 0}
    return {"C7": c7.out(), "도메인별": per_dom,
            "🔴 시각의 뜻": "결정 시각이 아니라 「결과 창이 열리는 날」 — 상한이다"}


# ------------------------------------------------------------------ C8
def seal_slots(seal: dict):
    c8 = Bucket("C8", "(만화 제목, 각색 발표) — 봉인 예보 행")
    c8.tag = "C8"
    n = seal.get("행") or 0
    #: 🔴 각색 발표는 **아직 안 일어났다** — 시각도 값 전/후도 없다
    c8.add(False, False, n)
    return {"C8": c8.out(), "봉인일": seal.get("봉인일"), "창(개월)": seal.get("창(개월)"),
            "🔴 이 슬롯이 ≤2칸인 이유": "예보는 있으나 **채점 사건(각색 발표)이 아직 0건**이다 — "
                                "「없다」가 아니라 **아직 안 일어났다**"}
