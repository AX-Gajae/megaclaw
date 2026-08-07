"""속편인가를 축으로 세운다(노트 181).

**왜.** 노트 180이 위키 수준 $\\leftrightarrow$ 라벨의 부호가 도메인마다
반대인 것을 보였고(세계애니 $+$0.35 · 애니 $-$0.18), 노트 181이 애니에서
그 까닭을 갈랐다 --- **속편이다.** 애니 속편 240건은 $\\rho{=}-0.28$ 이고
신작 442건은 $+0.04$ 다. 속편은 사전 위키 조회수가 훨씬 크고(p${=}$3e-35)
한국 라벨은 더 낮다(p${=}$1e-06). 세계애니에서는 속편이 유명한 것은 같은데
라벨이 안 낮다(p${=}$1.00) --- **라벨이 속편을 다르게 대한다.**

노트 149가 프랜차이즈 되돌리기를 넣으면서 ``원작 인기를 업고 나오는 2기와
맨몸으로 나오는 신작을 가르는 축이 된다''고 적었는데, **그 가르는 일을
축으로 세운 적이 없다.** 위키 조회수 안에 섞여 있었을 뿐이다.

**누수 없음.** 속편 여부는 제목만 보면 안다 --- 오픈 전에 아는 값이다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ingest.wiki_views import franchise

D = Path("data/state")
# 도메인 → (축 파일, 레코드 파일, 제목 열)
SRC = {
    "세계애니": ("wanime_axes", "wanime_records", ("english", "title")),
    "만화": ("manga_axes", "manga_records", ("title",)),
    "애니": ("anime_axes", "anime_records", ("title",)),
    "게임": ("game_axes", "game_records", ("name",)),
    "모바일": ("mobile_axes", "mobile_records", ("title",)),
    "웹툰": ("webtoon_axes", "webtoon_records", ("title",)),
    "도서": ("book_axes", "book_records", ("title",)),
}


def _titles(rf: str, keys) -> dict:
    p = D / f"{rf}.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    it = d.values() if isinstance(d, dict) else d
    out = {}
    for r in it:
        rid = r.get("record_id")
        if not rid:
            continue
        out[rid] = next((str(r[k]) for k in keys if r.get(k)), "")
    return out


def build() -> dict:
    """{축이름: {도메인: (값, 표시자)}}.

    값은 속편이면 1.0, 신작이면 0.0 --- 이분이라 순위 정규화를 안 한다.
    표시자는 제목이 있으면 1이다(전 도메인 100%에 가깝다)."""
    out = {}
    col = {}
    for dom, (axf, rf, keys) in SRC.items():
        p = D / f"{axf}.json"
        if not p.exists():
            continue
        ks = list(json.loads(p.read_text()))
        tt = _titles(rf, keys)
        v = np.zeros(len(ks))
        ok = np.zeros(len(ks))
        for i, k in enumerate(ks):
            t = tt.get(k)
            if not t:
                continue
            ok[i] = 1.0
            v[i] = 1.0 if franchise(t) is not None else 0.0
        if ok.sum() < 20:
            continue
        col[dom] = (v, ok)
    if col:
        out["is_sequel"] = col
    return out


def coverage() -> dict:
    b = build().get("is_sequel") or {}
    return {d: {"행": len(v[0]), "덮음": round(float(v[1].mean()), 3),
                "속편몫": round(float(v[0][v[1] > 0].mean()), 3)}
            for d, v in sorted(b.items())}


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))
