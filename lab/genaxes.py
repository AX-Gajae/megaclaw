"""갈래를 **도메인을 가로지르는 눈금 하나**로 세운다(노트 419).

**왜.** 노트 417·418이 `grp` 하나로 안 본 도메인의 전이를 $-0.0822 \\to
+0.2128$(KR 만화) · $+0.0421 \\to +0.1474$(비게임 앱)로 올렸다. 기계는
이랬다 --- 원핫은 안 본 도메인에서 **전부 0** 인데 grp 가 나르는 것(국가 ·
포맷 · 매체 · 연령등급)은 **새 작품에도 있는 성질**이라 낯선 자리에 안 선다.

그러면 같은 꼴을 더 찾아야 한다. 레코드 전수조사에서 `genres` 가 나왔다 ---
**다섯 도메인**(만화 · 모바일 · 애니 · 세계애니 · 게임)에 80% 넘게 차 있고,
전부 **기획 시점**에 정해진다.

**grp 와 다르게 만든다.** `grpaxes` 는 집단을 **도메인마다 따로** 크기 순으로
늘어놓아서, 같은 값이 도메인마다 다른 것을 뜻한다. 갈래는 **어휘가 실제로
겹친다** --- romance/로맨스 · action/액션 · fantasy/판타지 · comedy/코미디 ·
adventure/어드벤처 · slice of life/일상. 그래서 **눈금을 도메인 사이에서
공유한다**: 다섯 도메인을 합쳐 세고, 그 순위를 모든 도메인이 같이 쓴다.
안 본 도메인도 제 갈래만 알면 같은 자리에 선다 --- 이것이 시험하려는 것이다.

**누수 없음.** 갈래는 출시 전에 붙는다(노트 141의 시점 규칙).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

D = Path("data/state")
SRC = {"만화": "manga_records.json", "모바일": "mobile_records.json",
       "애니": "anime_records.json", "세계애니": "wanime_records.json",
       "게임": "game_records.json"}

# 한국어 -- 영어를 한 어휘로 모은다. 손으로 적었고 라벨을 안 본다.
CANON = {
    "로맨스": "romance", "romance": "romance",
    "드라마": "drama", "drama": "drama",
    "코미디": "comedy", "comedy": "comedy", "개그": "comedy",
    "판타지": "fantasy", "fantasy": "fantasy",
    "액션": "action", "action": "action",
    "모험": "adventure", "어드벤처": "adventure", "adventure": "adventure",
    "일상": "slice of life", "slice of life": "slice of life",
    "sf": "sci-fi", "sci-fi": "sci-fi", "공상과학": "sci-fi",
    "supernatural": "supernatural", "초자연": "supernatural",
    "스릴러": "thriller", "thriller": "thriller",
    "미스터리": "mystery", "mystery": "mystery",
    "공포": "horror", "horror": "horror",
    "스포츠": "sports", "sports": "sports",
    "시뮬레이션": "simulation", "simulation": "simulation",
    "전략": "strategy", "strategy": "strategy",
    "퍼즐": "puzzle", "puzzle": "puzzle",
    "캐주얼": "casual", "casual": "casual",
    "rpg": "rpg", "롤플레잉": "rpg",
    "보드": "board", "board": "board",
    "아동": "kids", "kids": "kids",
    "역사": "history", "history": "history",
    "음악": "music", "music": "music",
    "인디": "indie", "indie": "indie",
}


def _genres(rec) -> list:
    g = rec.get("genres")
    if isinstance(g, str):
        g = [g]
    if not isinstance(g, list):
        return []
    out = []
    for x in g:
        c = CANON.get(str(x).strip().lower())
        if c:
            out.append(c)
    return out


def build(min_group: int = 40) -> dict:
    """{'gen': {도메인: (값, 표시자)}} --- **눈금을 도메인 사이에서 공유한다**."""
    from .trendaxes import _ids
    ids_all = _ids()
    per = {}
    pool = Counter()
    for dom, f in SRC.items():
        p = D / f
        ids = ids_all.get(dom)
        if not p.exists() or not ids:
            continue
        j = json.loads(p.read_text())
        rows = [_genres(j.get(k) or {}) for k in ids]
        per[dom] = rows
        for r in rows:
            pool.update(set(r))
    big = [g for g, n in pool.items() if n >= min_group]
    if len(big) < 3:
        return {}
    # **합쳐 센 순위를 모두가 같이 쓴다** --- grpaxes 와 여기가 다르다.
    order = sorted(big, key=lambda g: -pool[g])
    pos = {g: i / max(1, len(order) - 1) for i, g in enumerate(order)}
    col = {}
    for dom, rows in per.items():
        v, o = [], []
        for r in rows:
            cand = [g for g in r if g in pos]
            if cand:
                # 으뜸 갈래 = 그 레코드의 갈래 중 **합쳐 세어 제일 흔한 것**
                g = min(cand, key=lambda z: (order.index(z), z))
                v.append(pos[g]); o.append(1.0)
            else:
                v.append(0.5); o.append(0.0)
        col[dom] = (np.array(v, float), np.array(o, float))
    return {"gen": col} if col else {}


def vocabulary(min_group: int = 40) -> list:
    """공유 어휘를 흔한 순으로."""
    from .trendaxes import _ids
    ids_all = _ids(); pool = Counter()
    for dom, f in SRC.items():
        p = D / f; ids = ids_all.get(dom)
        if not p.exists() or not ids:
            continue
        j = json.loads(p.read_text())
        for k in ids:
            pool.update(set(_genres(j.get(k) or {})))
    return [(g, n) for g, n in pool.most_common() if n >= min_group]
