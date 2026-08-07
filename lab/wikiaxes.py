"""위키백과 오픈 이전 조회수 → 축 넷(노트 149).

네이버 검색 축(``lab/trendaxes.py'')과 같은 넷을 같은 방식으로 만든다 ---
수준 · 기울기 · 변동 · 봉우리비. 다른 것은 **출처와 덮음**뿐이다.

    네이버 검색   한국어 제목이 있어야 한다. 만화 0\% · 세계애니 0\%
    위키 조회수   영문 제목으로 된다. 만화 · 세계애니를 채운다

**시점**(노트 141의 셋째 층). 창은 시작일 이전 90일이고 시작일 당일과
이후는 한 칸도 안 본다. 그래서 사전 축이다 --- Kitsu 축(지금 긁은 순위)과
결정적으로 다른 점이다.

**0 을 자료로 볼 것인가.** 문서가 그때 없었으면 조회수가 0으로 온다. 그것을
결측으로 볼지 ``사전 인지가 없었다''는 측정으로 볼지가 갈린다. 논리는
측정 쪽이 맞지만(신작은 정말로 아무도 안 찾는다) 어느 쪽이 나은지는 하네스가
정한다 --- 바깥 점수를 보고 고르면 노트 126이 잡은 그 잘못이다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

CACHE = Path("data/state/wiki_views")
# **읽는 쪽 목록**(노트 337). 여섯뿐이었다 --- 그런데 ``ingest/wiki_views.SRC``
# 는 열 도메인을 긁고 캐시에는 도서 212 · 펀딩 399 · 아이돌 78 · 시장팝업
# 205 가 이미 있었다. 노트 178이 도서 · 펀딩을 **쓰는 쪽에만** 넣었고 여기는
# 안 고쳐졌다. 노트 336의 ``trendaxes.FILE`` 과 같은 자리, 네 번째다.
#
# 넷을 넣으면 덮음이 아이돌 82% · 시장팝업 38% · 도서 21% · 펀딩 0.5% 다.
# 짝지어 열둘 재면 아이돌 +0.0737(11/12) · 나머지 셋은 못 가르고 판이
# +0.0007(6/12)로 미결정 폭 안이다. **자료 결정이지 점수로 고른 것이
# 아니다** --- 목록이 틀려 있었다.
AXF = {"세계애니": "wanime_axes", "만화": "manga_axes",
       "애니": "anime_axes", "게임": "game_axes",
       "모바일": "mobile_axes", "웹툰": "webtoon_axes",
       "도서": "book_axes", "펀딩": "funding_axes",
       "아이돌": "idol_axes", "시장팝업": "market_axes"}
FEATS = ("level", "momentum", "volatility", "peak_ratio")
_ZERO_IS_DATA = True


def _ids() -> dict:
    """도메인 → 행 순서. **팝업은 별도 저장소다**(노트 133 · 158).

    다른 도메인은 ``{d}_axes.json'' 의 id 목록이 곧 행 순서인데, 팝업은
    popupset 이 만들고 좁은 판(75행)과 넓은 판(189행)이 다르다. trendaxes
    가 쓰는 것과 같은 함수를 써야 행 수가 맞는다 --- 안 맞으면 harness.load
    가 중립으로 채우고 축이 통째로 사라진다."""
    out = {}
    for d, f in AXF.items():
        p = Path("data/state") / f"{f}.json"
        if p.exists():
            out[d] = list(json.loads(p.read_text()))
    try:
        from . import trendaxes as _T
        out["팝업"] = list(_T._popup_ids())
    except Exception:
        pass
    return out


def _feats(days: list) -> dict:
    """일별 조회수 → 축 넷. 창의 앞 절반 대 뒤 절반으로 기울기를 낸다."""
    v = np.array([x[1] for x in days], float)
    if not len(v):
        return {"level": 0.0, "momentum": 0.0, "volatility": 0.0,
                "peak_ratio": 0.0}
    lv = float(np.log1p(v.mean()))
    h = len(v) // 2
    a, b = v[:h], v[h:]
    mo = float((b.mean() - a.mean()) / (a.mean() + 1.0)) if h else 0.0
    vo = float(v.std() / (v.mean() + 1.0))
    pk = float(v.max() / (v.mean() + 1.0))
    return {"level": lv, "momentum": mo, "volatility": vo, "peak_ratio": pk}


DOM_OF = {"AN": "애니", "WA": "세계애니", "MB": "모바일", "GAME": "게임",
          "WT": "웹툰", "MG": "만화", "BOOK": "도서", "IDOL": "아이돌",
          "FUND": "펀딩"}


def _dom_of(rid: str) -> str:
    """레코드 id 접두 → 도메인. 팝업은 접두가 여럿이라 나머지로 본다."""
    return DOM_OF.get(str(rid).split("-")[0], "팝업")


@lru_cache(maxsize=8)
def _read(min_score: float = 0.0, cat_check: bool = False) -> dict:
    """{record_id: (축 넷, 관측했나, 문서)}

    ``min_score`` 는 매칭 점수 문턱이다(노트 178). 1.0 은 직접 · 검색 정확
    일치, 0.9 는 프랜차이즈 되돌리기, **0.8 은 겹침 포함**이다 --- 한쪽
    제목이 다른 쪽을 품기만 해도 붙인다. 노트 150이 이 규칙을 세운 것은
    ``겹침 0인 1위를 그냥 쓰는 것''을 막기 위해서였고 그 목적은 이뤘지만,
    노트 178에서 손으로 세어 보니 도서의 포함 매칭 열다섯 개 중 열하나가
    틀렸다(세종 ← ``세종의 나라'', 물 ← ``강물이 멈춘 날''). 문턱을 0.9 로
    올리면 그것들이 결측이 된다."""
    out = {}
    if not CACHE.exists():
        return out
    for p in CACHE.glob("*.json"):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        rid = d.get("record_id")
        if not rid:
            continue
        if d.get("page") is None or (d.get("score") or 0.0) < min_score:
            out[rid] = (None, False, None)          # 문서를 못 찾았다 --- 결측
            continue
        if cat_check:
            # **분류가 도메인과 안 맞으면 그 문서는 그 IP 가 아니다**(노트 179).
            from .wikicat import matches
            m = matches(_dom_of(rid), d["page"], d.get("lang", "en"))
            if m is False:
                out[rid] = (None, False, None)
                continue
        out[rid] = (_feats(d.get("days") or []), bool(d.get("n")), d["page"])
    return out


def shared(top: int = 8) -> dict:
    """한 문서를 몇 레코드가 나눠 쓰나(노트 150).

    **왜 재나.** 여러 레코드가 같은 문서에 붙으면 그 축은 레코드를 안 재고
    날짜만 잰다. 노트 149에서 검색 되돌리기가 겹침 0인 1위를 그냥 쓰는
    바람에 웹툰 스물다섯 건 중 스물한 건이 ``네이버 웹툰'' 하나로 갔다.

    다만 **나눠 쓰는 것 자체가 잘못은 아니다** --- 애니 2기 · 3기가 프랜차이즈
    문서를 같이 쓰는 것은 의도한 바다(원작 인기를 업고 나오는 정도를 잰다).
    그래서 판정이 아니라 분포를 적는다."""
    ids, r = _ids(), _read()
    out = {}
    for d, ks in ids.items():
        cnt = {}
        for k in ks:
            e = r.get(k)
            if not e or e[0] is None:
                continue
            pg = e[2] if len(e) > 2 else None
            if pg:
                cnt[pg] = cnt.get(pg, 0) + 1
        if not cnt:
            continue
        big = sorted(cnt.items(), key=lambda kv: -kv[1])[:top]
        tot = sum(cnt.values())
        out[d] = {"문서수": len(cnt), "레코드": tot,
                  "최대공유": big[0][1] if big else 0,
                  "5건이상이쓰는몫": round(
                      sum(v for v in cnt.values() if v >= 5) / max(tot, 1), 3),
                  "상위": big}
    return out


def coverage(min_score: float = 0.0, cat_check: bool = False) -> dict:
    ids, r = _ids(), _read(min_score, cat_check)
    out = {}
    for d, ks in ids.items():
        have = [k for k in ks if k in r and r[k][0] is not None]
        seen = [k for k in have if r[k][1]]
        out[d] = {"행": len(ks), "문서있음": len(have), "창채움": len(seen),
                  "덮음": round(len(have) / max(len(ks), 1), 3)}
    return out


def build(feats=FEATS, zero_is_data: bool = True,
          min_score: float = 0.0, cat_check: bool = False) -> dict:
    """{축이름: {도메인: (값, 표시자)}} --- harness.load 가 받는 모양."""
    global _ZERO_IS_DATA
    _ZERO_IS_DATA = zero_is_data
    ids, r = _ids(), _read(min_score, cat_check)
    out = {}
    for f in feats:
        col = {}
        for d, ks in ids.items():
            raw = np.full(len(ks), np.nan)
            for i, k in enumerate(ks):
                e = r.get(k)
                if e is None or e[0] is None:
                    continue
                if not e[1] and not zero_is_data:
                    continue                        # 빈 창을 결측으로 본다
                raw[i] = e[0][f]
            if np.isfinite(raw).sum() < 20:
                continue
            ok = np.isfinite(raw)
            v = np.full(len(raw), 0.5)
            v[ok] = rankdata(raw[ok]) / ok.sum()
            col[d] = (v, ok.astype(float))
        if col:
            out[f"wiki_{f}"] = col
    return out


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))
