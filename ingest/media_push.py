"""``media_push`` 를 **두 도메인에 걸쳐 한 눈금으로** 다시 만든다(노트 369).

**왜 한 눈금인가**(노트 368). 이 축은 만화와 세계애니가 **같은 열**을
쓴다. 노트 368 이 만화만 새 눈금으로 바꿔 보니 순위 상관이 옛 값과
$+0.9905$ 로 개념은 같은데 판이 $-0.0029$(1/12) 내려갔고, **제일 크게
다친 것이 세계애니**($-0.0063$, 0/12)였다 --- 열을 같이 쓰는 도메인이다.
한 열에 자가 둘 들어가면 나무가 가르는 자리가 어긋난다. 노트 357 이
팝업 라벨(순위)에서 본 병이 피처 안에서 난 것이다.

**개념은 노트 108 의 것 그대로** --- ``공식 외부 채널 수와 예고편 유무''.
옛 채움을 역산해 확인했다: ``외부 링크 수 $+$ 예고편'' 과 옛 값의 순위
상관이 만화 $+0.9905$ · 세계애니 $+0.9921$ 이다(링크만 쓰면 $+0.95$ 로
떨어진다 --- 예고편이 들어간다).

**눈금은 \emph{제 도메인} 백분위다 --- 노트 368 의 규칙을 뒤집는다**(노트
369). 합친 백분위로 매겨 보니 판이 더 내려갔다(점추정 $-0.0051$, 만화만
압축했을 때의 $-0.0029$ 보다 나쁘다). 옛 채움을 역산하니 그것이 바로
\emph{제 도메인 백분위}였다 --- 만화 평균 오차 0.0176 · 세계애니 0.0105
이고 raw=0 에서 정확히 맞는다.

**까닭.** 공유 열은 \emph{도메인 안의 순서}를 나르고, 도메인 사이 차이는
**원핫 열이 이미 나른다**. 합친 백분위로 매기면 그 열 안에서 두 도메인이
서로 다른 자리에 놓이는데(예고편 비율이 만화 26\% 대 세계애니 74\% 라
만화가 통째로 아래로 내려간다) 그것은 원핫이 하는 말을 한 번 더 하는
것이고, 대신 도메인 안의 해상도를 잃는다.

    raw = 외부 링크 수 + (예고편 있으면 1)
    값  = **그 도메인 안에서의** 중간순위 백분위

    raw = 외부 링크 수 + (예고편 있으면 1)
    값  = 합친 분포에서의 중간순위 백분위

재료: ``data/state/manga_links.json``(2,041) ·
``data/state/wanime_links.json``(2,948). 둘 다 AniList 에서 id 로 받았다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SRC = {"만화": ("data/state/manga_axes.json", "data/state/manga_links.json", "MG"),
       "세계애니": ("data/state/wanime_axes.json", "data/state/wanime_links.json", "WA")}
OUT = Path("data/state/media_push_fill2.json")


def _raw(mid, links):
    m = links.get(str(mid))
    if m is None:
        return None
    return len(m.get("externalLinks") or []) + (1 if m.get("trailer") else 0)


def build() -> dict:
    got = {}
    for dom, (axp, lkp, _pre) in SRC.items():
        ax, lk = Path(axp), Path(lkp)
        if not (ax.exists() and lk.exists()):
            continue
        ids = list(json.loads(ax.read_text()))
        links = json.loads(lk.read_text())
        got[dom] = (ids, [_raw(k.split("-")[1], links) for k in ids])
    out = {}
    for dom, (ids, rs) in got.items():
        pool = np.array([v for v in rs if v is not None], float)
        if not len(pool):
            continue
        tab = {int(v): float((np.sum(pool < v) + 0.5 * np.sum(pool == v)) / len(pool))
               for v in np.unique(pool)}
        out[dom] = {"ids": ids,
                    "value": [tab.get(int(r), 0.5) if r is not None else 0.5
                              for r in rs],
                    "mask": [1.0 if r is not None else 0.0 for r in rs]}
    return out


if __name__ == "__main__":
    b = build()
    for dom, d in b.items():
        v = np.array(d["value"]); m = np.array(d["mask"])
        print("%-8s %4d행 · 표시자 %.0f%% · 중앙 %.3f · 사분범위 %.3f · 값 %d개"
              % (dom, len(v), 100 * m.mean(), np.median(v[m > 0]),
                 np.percentile(v[m > 0], 75) - np.percentile(v[m > 0], 25),
                 len(np.unique(v[m > 0]))))
    OUT.write_text(json.dumps(b, ensure_ascii=False, indent=1))
    print("저장:", OUT)
