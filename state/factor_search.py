"""인자 공간 자기 상관을 목표로 네 도메인 배선을 전수 탐색한다.

노트 37이 판정을 싸게 만들었다. 전이 상관은 대상 도메인의 **인자 공간 자기
상관**과 같으므로(24점에서 $+$0.993), 배선 후보를 평가할 때 열두 셀 순열 검정을
돌릴 필요가 없다. 도메인 하나 안에서 5폴드 교차검증 한 번이면 된다.

**그래서 후보를 많이 볼 수 있게 됐고, 동시에 새 위험이 생겼다.** 후보를 많이
보고 최댓값을 고르면 그 최댓값은 낙관적이다 --- 노트 4의 헤드라인을 철회하게
만든 바로 그 선택 편향이다. 세 가지로 막는다.

  반복 교차검증   씨앗 다섯 개의 평균으로 고른다. 한 분할의 운을 덜 탄다.
  확인용 씨앗     고를 때 쓰지 않은 씨앗으로 승자를 다시 잰다. 두 값의 차이가
                  선택 편향의 크기이며 그것을 노트에 적는다.
  독립 측정       최종 승자만 열두 셀 순열 검정으로 확인한다. 탐색에 쓰지 않은
                  측정이므로 편향이 옮겨오지 않는다.

탐색은 좌표 상승법이다. 슬롯을 하나씩 돌며 그 슬롯의 후보를 전부 시험해 가장
좋은 것으로 바꾸고, 한 바퀴에 아무 변화도 없으면 멈춘다.

사용: python3 -m state.factor_search
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .procrustes import COMMON, factor_space, lam_by_overlap
from .tri_domain import ALL5, KO, load_all

OUT = Path("data/state/factor_search.json")
SEARCH_SEEDS = (11, 22, 33, 44, 55)
CONFIRM_SEEDS = (101, 202, 303, 404, 505)
IX = {a: i for i, a in enumerate(ALL5)}


def scale01(v, lo, hi):
    return np.clip((np.asarray(v, float) - lo) / (hi - lo), 0.0, 1.0)


def _keys(p):
    return list(json.loads(Path(p).read_text()).keys())


# ── 후보 열 ────────────────────────────────────────────────────────────
# 각 함수는 (값, 마스크)를 낸다. **0이 결측인지 관측값인지 여기서 명시한다** ---
# 노트 35와 37에서 같은 실수를 두 번 했다. 코드가 추측하지 않는다.

def _col(vals, valid):
    v = np.array([0.0 if x is None else float(x) for x in vals])
    return v, np.array([1.0 if b else 0.0 for b in valid])


def game_cols():
    ax = json.loads(Path("data/state/game_axes.json").read_text())
    rec = json.loads(Path("data/state/game_records.json").read_text())
    fr = json.loads(Path("data/state/game_friction.json").read_text())
    ids = _keys("data/state/game_axes.json")
    g = lambda k: rec.get(k) or {}
    f = lambda k: fr.get(k) or {}
    out = {}
    out["언어 수"] = _col([scale01(np.log2(max(g(k).get("n_lang") or 1, 1)), 0, 5)
                        for k in ids], [True] * len(ids))
    out["언어+장르+플랫폼"] = _col([ax[k]["axes"]["target_breadth"] for k in ids],
                             [True] * len(ids))
    out["플랫폼 수"] = _col([scale01(g(k).get("n_platform") or 1, 1, 3) for k in ids],
                        [True] * len(ids))
    out["퍼블리셔 이력"] = _col([ax[k]["axes"]["venue_prominence"] for k in ids],
                          [bool(g(k).get("publishers")) for k in ids])
    out["가격"] = _col([scale01(np.log10(max(g(k).get("price_krw") or 500, 500)), 3, 5)
                     if not g(k).get("is_free") else 0.0 for k in ids],
                    [bool(g(k).get("price_krw") or g(k).get("is_free")) for k in ids])
    out["연령 등급"] = _col([scale01(f(k).get("required_age") or 0, 0, 18) for k in ids],
                        [bool(f(k)) for k in ids])
    out["설치 용량"] = _col([scale01(np.log2(max(f(k).get("disk_gb") or 1, 1)), 0, 7)
                        for k in ids], [bool(f(k).get("disk_gb")) for k in ids])
    out["최소 RAM"] = _col([scale01(np.log2(max(f(k).get("ram_gb") or 1, 1)), 0, 5)
                        for k in ids], [bool(f(k).get("ram_gb")) for k in ids])
    out["기능 수"] = _col([scale01(g(k).get("n_category") or 0, 0, 20) for k in ids],
                       [True] * len(ids))
    return out


def book_cols():
    ax = json.loads(Path("data/state/book_axes.json").read_text())
    rec = json.loads(Path("data/state/book_records.json").read_text())
    ids = _keys("data/state/book_axes.json")
    b = lambda k: rec.get(k) or {}
    out = {}
    out["판형(현행)"] = _col([ax[k]["axes"]["target_breadth"] for k in ids],
                         [bool(ax[k]["mask"]["target_breadth"]) for k in ids])
    out["판형 높이만"] = _col([1.0 - scale01(b(k).get("height_mm") or 0, 180, 280)
                          for k in ids], [bool(b(k).get("height_mm")) for k in ids])
    out["판형 면적"] = _col([1.0 - scale01((b(k).get("height_mm") or 0) *
                                       (b(k).get("width_mm") or 0), 20000, 50000)
                         for k in ids],
                        [bool(b(k).get("height_mm") and b(k).get("width_mm"))
                         for k in ids])
    out["출판사 이력"] = _col([ax[k]["axes"]["venue_prominence"] for k in ids],
                         [bool(b(k).get("publisher")) for k in ids])
    out["정가"] = _col([scale01(np.log10(max(b(k).get("price") or 1000, 1000)), 3.7, 4.7)
                     for k in ids], [bool(b(k).get("price")) for k in ids])
    out["양장 여부"] = _col([1.0 if "Hardcover" in (b(k).get("book_format") or "") else 0.0
                        for k in ids], [True] * len(ids))
    out["쪽수"] = _col([scale01(np.log2(max(b(k).get("pages") or 8, 8)), 5, 10)
                     for k in ids], [bool(b(k).get("pages")) for k in ids])
    out["무게"] = _col([scale01(b(k).get("weight_g") or 0, 100, 900) for k in ids],
                    [bool(b(k).get("weight_g")) for k in ids])
    return out


def idol_cols():
    ax = json.loads(Path("data/state/idol_axes.json").read_text())
    alb = json.loads(Path("data/state/idol_album_meta.json").read_text())
    recs = {}
    for p in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(p).read_text())
        recs[r["record_id"]] = r
    ids = _keys("data/state/idol_axes.json")
    r_ = lambda k: recs.get(k) or {}
    a_ = lambda k: alb.get(k) or {}
    out = {}
    for a in ALL5:
        out[f"현행 {KO[a]}"] = _col([ax[k]["axes"][a] for k in ids],
                                 [bool(ax[k]["mask"][a]) for k in ids])
    out["인원 수"] = _col([scale01(r_(k).get("member_count") or 0, 3, 13) for k in ids],
                       [bool(r_(k).get("member_count")) for k in ids])
    out["서바이벌 출신"] = _col([1.0 if r_(k).get("survival_show") else 0.0 for k in ids],
                          [True] * len(ids))
    out["앨범 정가"] = _col([scale01(np.log10(max(a_(k).get("unit_price") or 5000, 5000)),
                                 3.9, 4.7) for k in ids],
                        [bool(a_(k).get("unit_price")) for k in ids])
    out["앨범 버전 수"] = _col([scale01(np.log2(max(a_(k).get("versions") or 1, 1)), 0, 3)
                          for k in ids], [bool(a_(k).get("versions")) for k in ids])
    return out


def popup_cols():
    """팝업은 사람이 매긴 열 속성. 어느 속성을 어느 슬롯에 넣을지가 탐색 대상이다."""
    from .own_axes import _popup_keep
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in d["names"]]
    keep = _popup_keep(d, cols)
    X = d["X"][keep]
    names = ["target_breadth", "venue_prominence", "entry_friction", "media_push",
             "goods_scale", "experience_density", "photo_zones", "collab_strength",
             "ip_awareness", "season_fit"]
    ko = dict(KO, experience_density="체험 밀도", photo_zones="포토존",
              collab_strength="컬래버 강도", ip_awareness="IP 인지도",
              season_fit="계절 적합")
    out = {}
    for a in names:
        ci, mi = cols.index(f"t1o_{a}"), cols.index(f"t1o_{a}_mask")
        out[ko[a]] = (X[:, ci] / 4.0, X[:, mi])
    return out


def webtoon_cols():
    ax = json.loads(Path("data/state/webtoon_axes.json").read_text())
    rec = json.loads(Path("data/state/webtoon_records.json").read_text())
    ids = _keys("data/state/webtoon_axes.json")
    w = lambda k: rec.get(k) or {}
    from datetime import date
    asof = date(2026, 7, 29)

    def weeks(k):
        try:
            return max((asof - date(*map(int, w(k)["start_date"].split("-")))).days, 7) / 7
        except (ValueError, TypeError, KeyError):
            return None

    out = {}
    for a in ALL5:
        out[f"현행 {KO[a]}"] = _col([ax[k]["axes"][a] for k in ids],
                                 [bool(ax[k]["mask"][a]) for k in ids])
    out["태그 수"] = _col([scale01(w(k).get("n_tag") or 0, 3, 14) for k in ids],
                       [bool(w(k).get("n_tag")) for k in ids])
    out["연령 등급(역)"] = _col([1.0 - (w(k).get("age_rank") or 0) / 3.0 for k in ids],
                          [w(k).get("age_rank") is not None for k in ids])
    out["연령 등급"] = _col([(w(k).get("age_rank") or 0) / 3.0 for k in ids],
                        [w(k).get("age_rank") is not None for k in ids])
    out["작가 수"] = _col([scale01(w(k).get("n_artist") or 0, 1, 4) for k in ids],
                       [bool(w(k).get("n_artist")) for k in ids])
    out["회차 수"] = _col([scale01(np.log2(max(w(k).get("n_episode") or 1, 1)), 0, 9)
                       for k in ids], [bool(w(k).get("n_episode")) for k in ids])
    out["연재 밀도"] = _col([scale01((w(k).get("n_episode") or 0) / (weeks(k) or 1), .3, 1.5)
                        for k in ids], [bool(weeks(k)) for k in ids])
    out["요일 수"] = _col([scale01(w(k).get("n_day") or 1, 1, 3) for k in ids],
                       [bool(w(k).get("n_day")) for k in ids])
    return out


def funding_cols():
    ax = json.loads(Path("data/state/funding_axes.json").read_text())
    rec = json.loads(Path("data/state/funding_records.json").read_text())
    ids = _keys("data/state/funding_axes.json")
    f = lambda k: rec.get(k) or {}
    out = {}
    for a in ALL5:
        out[f"현행 {KO[a]}"] = _col([ax[k]["axes"][a] for k in ids],
                                 [bool(ax[k]["mask"][a]) for k in ids])
    out["무제한 비율"] = _col([f(k).get("unlimited_ratio") for k in ids],
                         [f(k).get("n_reward") is not None for k in ids])
    out["최저 후원가"] = _col([scale01(np.log10(max(f(k).get("min_price") or 1000, 1000)),
                                  3.0, 5.0) for k in ids],
                         [bool(f(k).get("min_price")) for k in ids])
    out["최고 후원가"] = _col([scale01(np.log10(max(f(k).get("max_price") or 1000, 1000)),
                                  4.0, 6.5) for k in ids],
                         [bool(f(k).get("max_price")) for k in ids])
    out["리워드 단계 수"] = _col([scale01(np.log2(max(f(k).get("n_reward") or 1, 1)), 0, 4)
                           for k in ids], [bool(f(k).get("n_reward")) for k in ids])
    out["배송 리워드 비율"] = _col([(f(k).get("n_delivery") or 0) / max(f(k).get("n_reward") or 1, 1)
                            for k in ids], [bool(f(k).get("n_reward")) for k in ids])
    out["창작자 이력"] = _col([ax[k]["axes"]["venue_prominence"] for k in ids],
                        [bool(ax[k]["mask"]["venue_prominence"]) for k in ids])
    return out


def anime_cols():
    """애니 후보 열. 누출 후보(화수)를 일부러 넣어 둔다 --- 노트 67이 웹툰에서
    회차 수를 넣으면 명확히 나빠진다는 것을 보였고, 같은 검정을 여기서도 한다."""
    ax = json.loads(Path("data/state/anime_axes.json").read_text())
    rec = json.loads(Path("data/state/anime_records.json").read_text())
    ids = _keys("data/state/anime_axes.json")
    w = lambda k: rec.get(k) or {}

    out = {}
    for a in ALL5:
        out[f"현행 {KO[a]}"] = _col([ax[k]["axes"][a] for k in ids],
                                 [bool(ax[k]["mask"][a]) for k in ids])
    out["태그 수"] = _col([scale01(w(k).get("n_tag") or 0, 3, 14) for k in ids],
                       [bool(w(k).get("n_tag")) for k in ids])
    out["장르 수"] = _col([scale01(w(k).get("n_genre") or 0, 1, 6) for k in ids],
                       [bool(w(k).get("n_genre")) for k in ids])
    # 연령 등급은 관측값이 0(전체 이용가)일 수 있으므로 결측을 따로 표시한다.
    out["연령 등급(역)"] = _col([1.0 - scale01(w(k).get("age") or 0, 0, 19) for k in ids],
                          [w(k).get("age") is not None for k in ids])
    out["연령 등급"] = _col([scale01(w(k).get("age") or 0, 0, 19) for k in ids],
                        [w(k).get("age") is not None for k in ids])
    out["대여가"] = _col([scale01(w(k).get("price") or 0, 0, 1500) for k in ids],
                      [w(k).get("price") is not None for k in ids])
    out["화수"] = _col([scale01(np.log2(max(w(k).get("n_episode") or 1, 1)), 0, 9)
                     for k in ids], [bool(w(k).get("n_episode")) for k in ids])
    out["더빙"] = _col([1.0 if w(k).get("is_dubbed") else 0.0 for k in ids],
                     [True for _ in ids])
    out["독점/오리지널"] = _col([1.0 if (w(k).get("is_only") or w(k).get("is_original"))
                          else 0.0 for k in ids], [True for _ in ids])
    return out


def mobile_cols():
    """모바일 후보 열. 스팀 게임과 같은 자리에 같은 물리량을 둔다."""
    ax = json.loads(Path("data/state/mobile_axes.json").read_text())
    rec = json.loads(Path("data/state/mobile_records.json").read_text())
    ids = _keys("data/state/mobile_axes.json")
    w = lambda k: rec.get(k) or {}
    AD = {"4+": 0, "9+": 1, "12+": 2, "17+": 3}

    out = {}
    for a in ALL5:
        out[f"현행 {KO[a]}"] = _col([ax[k]["axes"][a] for k in ids],
                                 [bool(ax[k]["mask"][a]) for k in ids])
    out["언어 수"] = _col([scale01(w(k).get("n_lang") or 0, 1, 30) for k in ids],
                       [bool(w(k).get("n_lang")) for k in ids])
    out["장르 수"] = _col([scale01(w(k).get("n_genre") or 0, 1, 5) for k in ids],
                       [bool(w(k).get("n_genre")) for k in ids])
    out["가격"] = _col([scale01(w(k).get("price") or 0, 0, 15) for k in ids],
                     [w(k).get("price") is not None for k in ids])
    out["앱 용량"] = _col([scale01(np.log10(max(w(k).get("size_mb") or 1, 1)), 1, 3.6)
                       for k in ids], [bool(w(k).get("size_mb")) for k in ids])
    out["스크린샷 수"] = _col([scale01(w(k).get("n_shot") or 0, 3, 20) for k in ids],
                         [bool(w(k).get("n_shot")) for k in ids])
    out["지원 기기 수"] = _col([scale01(w(k).get("n_device") or 0, 20, 90) for k in ids],
                          [bool(w(k).get("n_device")) for k in ids])
    # 연령 등급은 관측값이 0(4+)일 수 있으므로 결측을 따로 표시한다.
    out["연령 등급"] = _col([AD.get(w(k).get("advisory"), 0) / 3.0 for k in ids],
                        [w(k).get("advisory") in AD for k in ids])
    out["연령 등급(역)"] = _col([1.0 - AD.get(w(k).get("advisory"), 0) / 3.0 for k in ids],
                          [w(k).get("advisory") in AD for k in ids])
    return out


COLS = {"팝업": popup_cols, "아이돌": idol_cols, "게임": game_cols, "도서": book_cols,
        "펀딩": funding_cols, "웹툰": webtoon_cols, "애니": anime_cols,
        "모바일": mobile_cols}

# 슬롯별 후보 --- 이름으로 물리적 의미가 맞는 것만 둔다(노트 20의 정합 제약).
CAND = {
    "게임": {"target_breadth": ["언어+장르+플랫폼", "언어 수", "플랫폼 수"],
            "venue_prominence": ["퍼블리셔 이력"],
            "entry_friction": [None, "가격", "연령 등급"],
            "goods_scale": ["설치 용량", "최소 RAM", "기능 수"]},
    "도서": {"target_breadth": ["판형(현행)", "판형 높이만", "판형 면적"],
            "venue_prominence": ["출판사 이력"],
            "entry_friction": [None, "정가"],
            "goods_scale": ["양장 여부", "쪽수", "무게"]},
    "아이돌": {"target_breadth": ["현행 타깃 폭", "인원 수", "서바이벌 출신"],
             "venue_prominence": ["현행 매장 노출도"],
             "entry_friction": [None, "앨범 정가"],
             "media_push": [None, "현행 미디어 투입"],
             "goods_scale": ["현행 굿즈 규모", "앨범 버전 수"]},
    "웹툰": {"target_breadth": ["태그 수", "연령 등급(역)", "연령 등급", "작가 수"],
            "venue_prominence": ["현행 매장 노출도", "작가 수", "요일 수"],
            "goods_scale": ["연재 밀도", "회차 수", "작가 수", "태그 수"],
            "media_push": [None, "작가 수"]},
    "펀딩": {"target_breadth": ["무제한 비율", "현행 타깃 폭"],
            "venue_prominence": ["창작자 이력"],
            "entry_friction": [None, "최저 후원가"],
            "goods_scale": ["리워드 단계 수", "최고 후원가", "배송 리워드 비율"]},
    "모바일": {"target_breadth": ["언어 수", "장르 수", "연령 등급(역)", "연령 등급"],
             "venue_prominence": ["현행 매장 노출도"],
             "entry_friction": [None, "가격", "연령 등급"],
             "media_push": [None, "스크린샷 수", "지원 기기 수"],
             "goods_scale": ["앱 용량", "지원 기기 수", "스크린샷 수"]},
    "애니": {"target_breadth": ["태그 수", "장르 수", "연령 등급(역)", "연령 등급"],
            "venue_prominence": ["현행 매장 노출도"],
            "entry_friction": [None, "대여가", "연령 등급"],
            "media_push": [None, "더빙", "독점/오리지널", "현행 미디어 투입"],
            "goods_scale": ["현행 굿즈 규모", "화수", "태그 수"]},
    "팝업": {"target_breadth": ["타깃 폭", "IP 인지도", "미디어 투입"],
            "venue_prominence": ["매장 노출도", "컬래버 강도"],
            "entry_friction": ["입장 허들", "계절 적합"],
            "media_push": ["미디어 투입", "컬래버 강도", "IP 인지도"],
            "goods_scale": ["굿즈 규모", "포토존", "체험 밀도"]},
}


def build(dom, base, wiring, pool):
    """배선 명세로 축 행렬을 만든다."""
    A, M, y, t = base[dom]
    A, M = A.copy(), M.copy()
    for slot, name in wiring.items():
        j = IX[slot]
        if name is None:
            A[:, j], M[:, j] = 0.0, 0.0
        else:
            v, m = pool[name]
            A[:, j], M[:, j] = v, m
    return A, M, y, t


def score(dom, doms, seeds) -> float:
    """인자 공간 자기 상관. 씨앗 여러 개의 평균으로 잡음을 줄인다."""
    lam = lam_by_overlap(doms)
    F = factor_space(*doms[dom], lam=lam.get(dom, 0.75))
    S, yy = F["S"], F["y"]
    if len(yy) < 25:
        return float("nan")
    rs = []
    for sd in seeds:
        pr = np.zeros(len(yy))
        for tr, te in KFold(5, shuffle=True, random_state=sd).split(S):
            pr[te] = Ridge(alpha=1.0).fit(S[tr], yy[tr]).predict(S[te])
        rs.append(float(np.corrcoef(pr, yy)[0, 1]))
    return float(np.mean(rs))


def search(dom, base, pool, cand, seeds, rounds=3):
    cur = {}
    for slot, opts in cand.items():
        j = IX[slot]
        A, M, _, _ = base[dom]
        cur[slot] = None if M[:, j].mean() < 0.6 else "__keep__"
    # 초기값 --- 현행 배선을 그대로 두고 시작한다.
    doms = dict(base)
    best = score(dom, doms, seeds)
    trace = [("현행", best)]
    for _ in range(rounds):
        moved = False
        for slot, opts in cand.items():
            for name in opts:
                w = {slot: name}
                trial = dict(base)
                trial[dom] = build(dom, base, w, pool)
                s = score(dom, trial, seeds)
                if np.isfinite(s) and s > best + 1e-4:
                    best, moved = s, True
                    base = trial if isinstance(trial, dict) else base
                    base = dict(base)
                    trace.append((f"{KO[slot]} ← {name}", s))
        if not moved:
            break
    return base, best, trace


def run() -> dict:
    base = load_all()
    out = {}
    print(f"{'도메인':<7}{'현행':>9}{'탐색 최대':>10}{'확인 씨앗':>10}{'편향':>8}  경로")
    for dom in ("팝업", "아이돌", "게임", "도서"):
        pool = COLS[dom]()
        b0 = score(dom, base, SEARCH_SEEDS)
        newbase, best, trace = search(dom, base, pool, CAND[dom], SEARCH_SEEDS)
        conf = score(dom, newbase, CONFIRM_SEEDS)
        c0 = score(dom, base, CONFIRM_SEEDS)
        out[dom] = {"base": b0, "best": best, "confirm": conf, "base_confirm": c0,
                    "trace": [(a, round(b, 4)) for a, b in trace],
                    "wiring": [a for a, _ in trace[1:]]}
        path = " → ".join(a for a, _ in trace[1:]) or "변화 없음"
        print(f"{dom:<7}{b0:>+9.3f}{best:>+10.3f}{conf:>+10.3f}"
              f"{best - conf:>+8.3f}  {path}")
        base = newbase
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
