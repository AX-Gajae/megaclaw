"""애니 **전용** 축 --- 매체(노트 321).

노트 309가 `funding_axes.json` 의 안 쓰인 `category` 를 찾아 축으로 만들고
채택 검사 셋을 다 통과했다. 같은 훑기를 **전 도메인의 안 쓰인 필드**에
돌렸더니 후보가 셋 나왔다.

    `funding_axes.category`   이미 지은 것(노트 309) --- 선별기가 맞혔다
    `market_axes.category`    ``이미 있다''(노트 299) --- 역시 맞혔다
    `webtoon_axes.finished`   ①③ 통과하는데 **사후다**
    `anime_axes.medium`       **남는 하나**

`finished` 는 노트 255가 이미 배제한 것과 같은 종류다 --- ``완결 태그가
붙은 1,271건이 전부 finished=True 다, 끝나야 붙는 표지''. 선별기가 찾아도
출처가 막는다(노트 306의 규약).

`medium` 은 **제작 단계에서 정해진다** --- TV 시리즈로 만들지 극장판으로
만들지는 기획 시점 결정이고 방영 전에 안다. 사전이다.

**채택 검사 셋**(전부 학습 구간, 유보 안 봄):

    ① 혼자 가르나     크루스칼 p=0.0084 · 연도 통제 후 H=7.5 (p=0.0239)
    ② 시간 조각 다섯   부호 일치 **4/5** (조각 둘은 무리가 둘뿐이라 부호만)
    ③ 축 전부(23) 통제 H=35.1 (p<1e-5) --- **통제를 더할수록 세진다**
                     (안 통제 9.6 → 공유5 23.8 → 공유+태그 25.4 → 전부 35.1)

③ 이 커지는 것이 중요하다 --- 기존 축이 매체를 \emph{가리고} 있었다는 뜻이다.
태그 축(`tag_c2_애니`·`tag_c3_애니`)이 ``기획 시점 태그 · 장르 · 매체''에서
왔는데도 매체를 못 잡고 있었다.

무리 순서: **극장판(45) 2.449 > TVA(1382) 2.167 > OVA(29) 2.072**.
극장판이 위인 것은 이 판이 재려는 것(투자 규모와 기대)과 같은 방향이다.

**주의 --- 이 축은 거의 상수다.** 학습 1,467행 중 1,382행(94%)이 TVA 다.
움직일 수 있는 것은 5\%뿐이므로 **이득이 작을 것이라고 미리 적는다.**

눈금은 `grpaxes`·`mktaxes`·`fundaxes` 관례를 따른다 --- 집단을 크기 순으로
0~1 에 늘어놓고 15건 미만은 마스크 0. **라벨을 한 번도 안 본다.**
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

SRC = Path("data/state/anime_axes.json")
DOM = "애니"
MIN_GROUP = 15


def build(root: str = ".", min_group: int = MIN_GROUP) -> dict:
    """{'anime_medium': {'애니': (값, 표시자)}} --- 전용 이름."""
    p = Path(root) / SRC
    if not p.exists():
        return {}
    rec = json.loads(p.read_text())
    raw = [v.get("medium") for v in rec.values()]
    c = Counter(x for x in raw if x)
    big = [u for u, n in c.items() if n >= min_group]
    if len(big) < 2:
        return {}
    order = sorted(big, key=lambda u: -c[u])
    pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
    v = np.array([pos.get(x, 0.5) for x in raw], np.float32)
    o = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)
    return {"anime_medium": {DOM: (v, o)}}


if __name__ == "__main__":
    d = build()
    if not d:
        raise SystemExit("만들지 못했다")
    v, o = d["anime_medium"][DOM]
    rec = json.loads(SRC.read_text())
    raw = [x.get("medium") for x in rec.values()]
    c = Counter(x for x in raw if x)
    big = sorted([u for u, n in c.items() if n >= MIN_GROUP], key=lambda u: -c[u])
    print(f"anime_medium --- {len(v)}행 · 마스크 {100*float(o.mean()):.0f}%"
          f" · 무리 {len(big)}")
    for u in big:
        print(f"  {u:<10}{c[u]:>5}건  값 {float(v[raw.index(u)]):.3f}")
