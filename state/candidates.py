"""후보 축 자료를 한 번만 만든다(노트 116).

노트 102가 만든 스무 개 --- 설명문 임베딩 여덟 · 손 특징 다섯 · 표지 특징
다섯 · 표지 주성분 둘. 붓스트랩 반복마다 다시 만들 이유가 없다.
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.decomposition import PCA

D = Path("data/state")

# ── 라벨을 만든 계수기에서 나온 축(노트 117) ──
#
# 상관 문턱은 **필요조건이지 충분조건이 아니다.** favourites 는 라벨 상관
# 0.887로 걸렸지만 trending 은 0.505로 문턱을 빠져나가면서도 씨앗 넷을
# 통과했다(+0.0064). trending 은 같은 플랫폼의 **최근 목록 추가 · 투표**로
# 계산되는 순위이므로, 라벨(서재 등록 수)을 만든 바로 그 계수기의 미분값이다.
#
# 그래서 **출처로도 막는다** --- 라벨을 만든 플랫폼의 참여 계수기에서 나온
# 축은 상관이 낮아도 안 쓴다.
LABEL_PLATFORM = {"favourites", "trending", "popularity"}
TF = ["len", "nsent", "slen", "ttr", "digit"]
IF = ["bright", "sat", "edge", "ent", "std"]
AXF = {"애니": "anime_axes", "모바일": "mobile_axes", "웹툰": "webtoon_axes",
       "만화": "manga_axes", "세계애니": "wanime_axes", "게임": "game_axes",
       "도서": "book_axes", "펀딩": "funding_axes", "아이돌": "idol_axes"}


def _pct(raw):
    ok = np.isfinite(raw)
    v = np.full(len(raw), 0.5)
    if ok.sum() > 20:
        v[ok] = rankdata(raw[ok]) / ok.sum()
    return v, ok.astype(float)


@lru_cache(maxsize=1)
def build() -> dict:
    G = json.loads((D / "emb_global9.json").read_text())
    T = json.loads((D / "text_feats9.json").read_text())
    FI = json.loads((D / "img_feats9.json").read_text())
    ids = {k: list(json.loads((D / f"{v}.json").read_text()))
           for k, v in AXF.items()}
    out = {}
    for j in range(8):
        out[f"emb{j}"] = {d: _pct(np.array([G[d][k][j] if k in G[d] else np.nan
                                            for k in ids[d]]))
                          for d in ids if d in G}
    for f in TF:
        out[f"txt_{f}"] = {d: _pct(np.array([T[d][k][f] if k in T[d] else np.nan
                                             for k in ids[d]]))
                           for d in ids if d in T}
    for f in IF:
        out[f"img_{f}"] = {d: _pct(np.array([FI[d][k][f] if k in FI[d] else np.nan
                                             for k in ids[d]]))
                           for d in ids if d in FI}
    # ── 노트 117: 평점 --- 라벨(양)과 다른 물리량(질) ──
    #
    # 지금 축이 전부 양이거나 정적 메타이고 라벨도 전부 양이다(리뷰 수 ·
    # 서재 등록 수 · 관심 수 · 후원자 수 · 방문자 수). 평점은 ``본 사람들이
    # 얼마나 좋아했나''로 다른 물리량이다. 사후에 매겨지므로 팝업에는 못
    # 붙이지만 출처 축으로는 쓸 수 있다(노트 96의 법칙).
    SC = json.loads((D / "score_anilist.json").read_text())
    rate, fav, trend = {}, {}, {}
    for pre, dom in (("MG-", "만화"), ("WA-", "세계애니")):
        g = SC[pre]
        rate[dom] = _pct(np.array([
            g[k.split("-", 1)[1]].get("meanScore") or np.nan
            if k.split("-", 1)[1] in g else np.nan for k in ids[dom]], float))
        fav[dom] = _pct(np.array([
            (g[k.split("-", 1)[1]].get("favourites")
             if k.split("-", 1)[1] in g else np.nan) or np.nan
            for k in ids[dom]], float))
        trend[dom] = _pct(np.array([
            (g[k.split("-", 1)[1]].get("trending")
             if k.split("-", 1)[1] in g else np.nan) or np.nan
            for k in ids[dom]], float))
    import glob
    m = {}
    for f in glob.glob(str(D / "cache_mobile/app_*.json")):
        try:
            r = (json.loads(pathlib.Path(f).read_text()).get("results")
                 or [{}])[0]
        except Exception:
            continue
        v = r.get("averageUserRating")
        if v is not None:
            m[f"MB-{f.split('app_')[1][:-5]}"] = float(v)
    rate["모바일"] = _pct(np.array([m.get(k, np.nan) for k in ids["모바일"]]))
    m = {}
    for f in glob.glob(str(D / "cache_anime/item_*.json")):
        try:
            r = json.loads(pathlib.Path(f).read_text())
        except Exception:
            continue
        v = r.get("avg_rating")
        if v is not None:
            m[f"AN-{f.split('item_')[1][:-5]}"] = float(v)
    rate["애니"] = _pct(np.array([m.get(k, np.nan) for k in ids["애니"]]))
    out["rating"] = {d: v for d, v in rate.items() if v[1].mean() > .5}

    # ── 노트 118: **다른 플랫폼의 다른 계수기** ──
    #
    # 노트 117 이 걸린 곳 --- AniList 즐겨찾기는 물리량이 다르지만 라벨과
    # 같은 플랫폼의 같은 사용자가 매긴 것이라 사촌이었다. Kitsu 는 다른
    # 플랫폼이고 사용자층이 다르다. AniList idMal 을 다리로 2,892건(98%)을
    # 이었다. `userCount` · `favoritesCount` · `popularityRank` 는 안 쓴다 ---
    # 라벨과 같은 물리량이다.
    kp = D / "kitsu_wanime.json"
    if kp.exists():
        K = json.loads(kp.read_text())
        out["kitsu_rating"] = {"세계애니": _pct(np.array([
            float(K[k]["averageRating"]) if k in K and K[k].get("averageRating")
            else np.nan for k in ids["세계애니"]]))}
        out["kitsu_rank"] = {"세계애니": _pct(np.array([
            -float(K[k]["ratingRank"]) if k in K and K[k].get("ratingRank")
            else np.nan for k in ids["세계애니"]]))}
        # 두 플랫폼 평점의 평균 --- 노트 79 · 83 이 잰 라벨 신뢰도를
        # **줄이는** 쪽으로 쓴다. 잡음이 독립이면 평균이 덜 흔들린다.
        a1 = rate.get("세계애니")
        if a1 is not None:
            kv = out["kitsu_rating"]["세계애니"]
            both = (a1[1] > 0) & (kv[1] > 0)
            m = np.where(both, (a1[0] + kv[0]) / 2.0, 0.5)
            out["rating_2plat"] = {"세계애니": (m, both.astype(float))}
    out["favourites"] = fav
    out["trending"] = trend

    for j in (0, 1):
        m = {}
        for d in ids:
            g = FI.get(d)
            if not g:
                continue
            have = np.array([k in g for k in ids[d]])
            if have.sum() < 40:
                continue
            X = np.array([[g[k][f] for f in IF] for k in np.array(ids[d])[have]])
            X = (X - X.mean(0)) / (X.std(0) + 1e-9)
            z = PCA(2, random_state=0).fit_transform(X)[:, j]
            v = np.full(len(ids[d]), 0.5)
            v[have] = rankdata(z) / len(z)
            m[d] = (v, have.astype(float))
        out[f"imgpc{j}"] = m
    return out
