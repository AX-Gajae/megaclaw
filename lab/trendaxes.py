"""오픈 전 검색 관심도를 하네스가 쓰는 축 모양으로 만든다.

`state/candidates.py` 와 같은 규약 --- `{축이름: {도메인: (값, 표시자)}}`,
행 순서는 `state.audit.domains()` 와 같다.

**이 축이 다른 축과 다른 점.** 지금까지의 후보 축(임베딩 · 표지 · 평점)은
전부 **작품 자신의 메타데이터**였다. 이것은 처음으로 **작품 바깥의 수요
신호**다 --- 나오기 전에 사람들이 얼마나 찾아봤나. 노트 119--121 이 잰
같은 플랫폼 결합을 피하고(라벨을 만든 계수기와 다른 곳), 오픈 이전 창에서만
계산하므로 시간 마스크를 통과한다.

**웹툰만 조심한다.** 웹툰 라벨은 네이버 즐겨찾기이고 이 축은 네이버 검색이다.
같은 플랫폼이라 노트 117 의 출처 차단에 걸릴 수 있다 --- `LABEL_PLATFORM`
과 같은 취급으로 따로 검정한다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

D = Path("data/state/naver")
# 도메인 → 트렌드 파일 이름
FILE = {"팝업": "popup_trend", "아이돌": "idol_trend", "게임": "game_trend",
        "도서": "book_trend", "펀딩": "funding_trend", "모바일": "mobile_trend",
        "애니": "anime_trend", "웹툰": "webtoon_trend",
        # **노트 335.** 만화 · 세계애니는 여기 없었다. 노트 149가 ``검색
        # 덮음 만화 0% · 세계애니 0%'' 를 위키 축을 만든 근거로 쓴 그때,
        # 이유는 ``제목이 한국어가 아니다'' 였다. 노트 237이 그 문턱을
        # 없앴고(데이터랩은 영문 질의를 받는다) ``ingest/trend_all.SPEC'' 은
        # 그때 둘을 넣었는데 **읽는 쪽은 안 고쳤다.** 그래서 돌려도 안
        # 붙었을 것이다 --- 아무도 안 돌려서 티가 안 났다.
        # 노트 335에서 다 긁었다: 만화 1,473 중 상태 73(5%) · 세계애니
        # 1,311 중 241(18%). 만화는 5%라 거의 안 붙고 세계애니는 붙는다.
        "만화": "manga_trend", "세계애니": "wanime_trend"}
# 도메인 → id 목록 파일(state/candidates.py 의 AXF 와 같은 것)
AXF = {"애니": "anime_axes", "모바일": "mobile_axes", "웹툰": "webtoon_axes",
       "만화": "manga_axes", "세계애니": "wanime_axes", "게임": "game_axes",
       "도서": "book_axes", "펀딩": "funding_axes", "아이돌": "idol_axes",
       # 열한 번째 도메인(노트 284). 축 파일의 키가 곧 market_record_id 이고
       # ``_from_axes_json`` 이 ``list(d.values())`` 순서로 행을 만들므로
       # 여기서 키 순서를 그대로 쓰면 행이 맞는다. 엔티티 조인에 필요하다.
       "시장팝업": "market_axes"}
FEATS = ["level", "momentum", "volatility", "peak_ratio"]
SAME_PLATFORM = {"웹툰"}      # 라벨도 네이버 --- 따로 검정


def _pct(raw):
    """순위 정규화 + 관측 표시자. 값이 없는 행은 중립 0.5 · 표시자 0."""
    ok = np.isfinite(raw)
    v = np.full(len(raw), 0.5)
    if ok.sum() > 20:
        v[ok] = rankdata(raw[ok]) / ok.sum()
    return v, ok.astype(float)


@lru_cache(maxsize=1)
def _ids() -> dict:
    out = {}
    for d, f in AXF.items():
        p = Path("data/state") / f"{f}.json"
        if p.exists():
            out[d] = list(json.loads(p.read_text()))
    # 팝업은 별도 저장소이고, **audit 의 행은 걸러진 뒤의 75건**이다.
    # popup_v2_meta 376건을 그대로 쓰면 행 수가 안 맞아 축이 통째로 버려진다
    # (처음에 그렇게 해서 팝업만 관측 0 이 나왔다). 같은 필터를 다시 건다.
    out["팝업"] = _popup_ids()
    return out


WIDE = False          # True 면 계수 필터를 푼 넓은 팝업 id 를 쓴다

# **등급도 여기서 나뉜다**(노트 359). ``popupset.build`` 의 ``grades`` 와
# ``_popup_ids`` 의 등급 목록이 **두 군데에 따로 적혀** 있다. 노트 358이
# 앞쪽을 A~E 로 풀면서 뒤쪽은 A·B 로 남았고, 그러면 id 목록이 75건인데
# 자료는 89행이라 **팝업 전용 축이 길이 불일치로 통째로 버려진다.**
# 여덟 번째로 같은 모양이다(노트 335~356) --- 같은 거름망이 두 군데 적혀
# 있으면 갈라진다.
GRADES = ("A", "B")


def set_grades(gs) -> None:
    """팝업 id 목록의 등급 필터를 ``popupset.build`` 와 맞춘다(노트 359)."""
    global GRADES
    gs = tuple(gs)
    if gs != GRADES:
        GRADES = gs
        _popup_ids.cache_clear(); _ids.cache_clear()
        try:
            from . import calaxes
            calaxes._dates.cache_clear()
        except Exception:
            pass


def set_wide(on: bool) -> None:
    """넓은 팝업 판으로 축을 만들 때 부른다. 캐시를 비운다."""
    global WIDE
    if on != WIDE:
        WIDE = on
        _popup_ids.cache_clear(); _ids.cache_clear()
        try:
            from . import calaxes
            calaxes._dates.cache_clear()
        except Exception:
            pass


@lru_cache(maxsize=1)
def _popup_ids() -> list:
    """state/slots.py::load_popup 과 같은 거름망 --- 등급 A·B · 스코프 ·
    계수 방법 entry/participation · 라벨 유한."""
    import numpy as np
    z = np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in z["names"]]
    X, y = z["X"], z["y_perday"]
    meta = json.loads(Path("data/state/popup_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in GRADES:
        if f"trust_{g}" in cols:
            keep |= X[:, cols.index(f"trust_{g}")] > 0.5
    keep &= np.isfinite(y)
    keep &= np.array([bool(m.get("scope_usable")) for m in meta])
    if WIDE:
        keep &= np.array([m.get("counting") not in (None, "") for m in meta])
    else:
        keep &= np.array([m.get("counting") in ("entry", "participation")
                          for m in meta])
    return [m["id"] for m, k in zip(meta, keep) if k]


@lru_cache(maxsize=1)
def _trend() -> dict:
    """레코드 id → 상태. **검색어로 펴서** 같은 키워드를 쓰는 형제까지 채운다.

    수집기는 같은 검색어를 두 번 사지 않으려고 키워드로 중복을 없앴고, 그래서
    저장은 그 키워드를 처음 쓴 레코드 하나에만 남는다. 그런데 ``참교육''을
    쓰는 웹툰 레코드가 여럿이면 나머지도 같은 값을 받아야 맞다 --- 검색량은
    작품의 성질이지 레코드의 성질이 아니다. 여기서 펴 준다."""
    out = {}
    for d, f in FILE.items():
        p = D / f"{f}.json"
        if not p.exists():
            continue
        raw = json.loads(p.read_text())
        bykw, bynull = {}, {}
        for v in raw.values():
            if not v.get("kw"):
                continue
            (bykw if v.get("state") else bynull).setdefault(v["kw"], v)
        out[d] = {"byid": raw, "bykw": bykw, "bykw_null": bynull}
    return out


@lru_cache(maxsize=1)
def _kw_of() -> dict:
    """레코드 id → 정리된 검색어. 수집기와 **같은 규칙**을 쓴다."""
    from ingest.trend_all import SPEC, clean_kw
    out = {}
    for dom, key in (("게임", "game"), ("도서", "book"), ("펀딩", "funding"),
                     ("모바일", "mobile"), ("애니", "anime"), ("웹툰", "webtoon"),
                     ("만화", "manga"), ("세계애니", "wanime")):
        f, tf, _ = SPEC[key]
        p = Path("data/state") / f
        if not p.exists():
            continue
        j = json.loads(p.read_text())
        out[dom] = {rid: clean_kw(v.get(tf)) for rid, v in j.items()}
    return out


ZERO = {"level": 0.0, "momentum": 0.0, "volatility": 0.0,
        "peak_ratio": 0.0, "n_weeks": 0, "zero": True}
_ZERO_IS_DATA = True


def _state(d: str, rid: str) -> dict | None:
    """상태를 찾는다. **물어봤는데 없던 것은 결측이 아니라 0이다.**

    수집기는 데이터랩이 빈 계열을 주면 `state=None` 을 저장한다. 처음엔 그걸
    결측으로 읽어 마스크를 내렸는데, 그러면 ``아무도 안 찾았다''는 정보가
    통째로 버려진다 --- 그리고 그건 수요가 없다는 뜻이라 신호다. 물어본
    1,151 건 중 45\%가 여기 해당한다.

    구분이 되는 근거: 창은 오픈 210일 전부터라 계열이 오기만 하면 오픈 이전
    점이 반드시 넷 이상 나온다. 그러니 `state=None` 은 ``계열이 아예 안 왔다''
    --- 즉 검색량이 보고 문턱 아래라는 뜻이다. (2016년 초 오픈만 예외다.)"""
    t = _trend().get(d)
    if not t:
        return None
    v = t["byid"].get(rid)
    if v is None:
        kw = _kw_of().get(d, {}).get(rid)
        if kw:
            v = t["bykw"].get(kw) or t["bykw_null"].get(kw)
    if v is None:
        return None
    st = v.get("state")
    if st:
        return st
    return ZERO if _ZERO_IS_DATA else None


def build(feats=tuple(FEATS), drop_same_platform: bool = False,
          zero_is_data: bool = True) -> dict:
    """{축이름: {도메인: (값, 표시자)}}

    zero_is_data --- 물어봤는데 계열이 안 온 것을 0으로 볼지 결측으로 볼지.
    논리는 0 쪽이 맞는데(수요가 없다는 뜻) 어느 쪽이 실제로 나은지는 하네스가
    정한다. **바깥 점수를 보고 고르면 그게 노트 126 이 잡은 그 잘못이다.**"""
    ids, tr = _ids(), _trend()
    global _ZERO_IS_DATA
    _ZERO_IS_DATA = zero_is_data
    out = {}
    for f in feats:
        col = {}
        for d in tr:
            if d not in ids:
                continue
            if drop_same_platform and d in SAME_PLATFORM:
                continue
            raw = np.array([(_state(d, k) or {}).get(f, np.nan)
                            for k in ids[d]], float)
            if np.isfinite(raw).sum() < 20:
                continue
            col[d] = _pct(raw)
        if col:
            out[f"trend_{f}"] = col
    return out


def coverage() -> dict:
    """도메인마다 몇 행이 채워지나 --- 붙이기 전에 본다."""
    ids, tr = _ids(), _trend()
    out = {}
    for d in sorted(ids):
        if d not in tr:
            out[d] = {"행": len(ids[d]), "수집": 0, "상태": 0, "덮음": 0.0}
            continue
        n = sum(1 for k in ids[d] if k in tr[d]["byid"])
        s = sum(1 for k in ids[d] if _state(d, k))
        out[d] = {"행": len(ids[d]), "수집": n, "상태": s,
                  "덮음": round(s / max(1, len(ids[d])), 3)}
    return out


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))
