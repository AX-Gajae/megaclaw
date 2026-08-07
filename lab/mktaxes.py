"""시장팝업 **전용** 축 --- 범주(노트 285).

노트 283이 잰 것 중 제일 센 신호가 ``category`` 다(크루스칼 $H=29.4$,
$p=0.0001$; game\\_webtoon 3,979/일 대 fashion 810/일 --- 다섯 배).
노트 284가 도메인을 열면서 이 축은 안 넣었다 --- 활성 축이 넷뿐이라
$\\rho$ 가 0.197 에 그친 이유의 하나다.

**전용 이름으로 준다.** 노트 283이 ``얇은 도메인은 공유 축에 태워야 한다''고
적었는데 그 규약은 **학습행이 청력 문턱 아래일 때**의 것이다(노트 281).
시장팝업은 학습 101행이라 F18 의 문턱 22를 넉넉히 넘는다 --- 전용 이름이
실제로 일할 수 있는 조건이다.

**눈금은 `grpaxes` 관례를 따른다** --- 집단을 크기 순으로 0~1 에 늘어놓고
15건 미만은 마스크 0. 순서 자체에는 뜻이 없고 나무가 쪼개 쓰면 된다.
**라벨을 한 번도 안 본다**(집단 크기만 쓴다).

**시점**: ``category`` 는 기획 시점에 정해지는 업종 구분이라 사전이다.

**채택 검사 --- 나중에 소급해 적는다**(노트 323). 이 축을 만들 때(노트 285)는
검사 ③(겹침)이 아직 없었다. 노트 299가 ③ 을 처음 돌리면서 바로 이 축을
주인공으로 삼았고 결론이 ``이미 있다''였다.

    ① 혼자 가르나     학습 H=18.4 (p=0.0054)   통과
    ② 시간 조각 다섯   **못 돌린다** --- 학습 101행에 무리 일곱이라
                     20건 이상 무리가 0개다
    ③ 기존 축과 겹침  공유 축 통제 후 p=0.0941  **탈락 --- 이미 있다**
                     (``IP 를 업었나''를 ``target_breadth`` 가 이미 한다)
    ④ 비상수성       최빈 무리 밖 80%          통과

유보 이득은 +0.0259(수선된 판 기준)이고 시장팝업 검출 문턱 0.06~0.08 아래다.
**검사 ③ 이 미리 말한 그대로다.** 노트 321·322 가 이 축을 ``검사 넷을 다
통과''로 잘못 적었고 노트 323 이 정정했다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

SRC = Path("data/state/market_axes.json")
DOM = "시장팝업"
MIN_GROUP = 15


def build(root: str = ".", min_group: int = MIN_GROUP) -> dict:
    """{'mkt_cat': {'시장팝업': (값, 표시자)}} --- 전용 이름."""
    p = Path(root) / SRC
    if not p.exists():
        return {}
    # `_from_axes_json` 이 `list(d.values())` 순서로 행을 만드므로 같은 순서다.
    rec = json.loads(p.read_text())
    raw = [v.get("category") for v in rec.values()]
    c = Counter(x for x in raw if x)
    big = [u for u, n in c.items() if n >= min_group]
    if len(big) < 2:
        return {}
    order = sorted(big, key=lambda u: -c[u])
    pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
    v = np.array([pos.get(x, 0.5) for x in raw], np.float32)
    o = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)
    return {"mkt_cat": {DOM: (v, o)}}


if __name__ == "__main__":
    b = build()
    for k, d in b.items():
        val, mk = d[DOM]
        print(f"{k}: {len(val)}행 · 마스크 {100*mk.mean():.1f}% · "
              f"서로 다른 값 {len(np.unique(val[mk > 0]))}")
