"""펀딩 **전용** 축 --- 범주(노트 309).

노트 303이 도메인마다 빌린 양을 재고 ``도서 · 펀딩에 축을 더 --- 빌릴 자리가
있다는 뜻''을 남겼다. 그 자리를 뒤졌더니 ``funding_axes.json`` 의
``category`` 가 축으로 안 쓰이고 있었다(덮음 100\% · 값 스무 가지 · 학습
5건 이상 무리 열넷이 320행 중 309행).

**채택 검사 셋을 다 통과한 첫 축이다**(노트 239 · 285의 규약, 전부 학습
구간에서).

    ① 혼자 가르나     크루스칼 H=56.7 (p<1e-4)
                     연도 통제 후 H=30.5 (p<1e-4)
    ② 시간 조각 다섯   부호 일치 **5/5** --- 조각마다 n=64
                     (+0.200 · +0.900 · +0.600 · +0.800 · +0.200)
    ③ 기존 축과 겹침   공유 축 다섯을 통제한 잔차에서 H=42.2 (p=0.0001)

무리 순서가 뜻을 갖는다 --- ``publication > webtoon-resources > food >
home-and-living > perfumes-and-beauty > apparels''. 위가 IP · 출판 쪽이고
아래가 상품 쪽이다. 이 실험실이 재려는 것(IP 를 업은 정도)과 같은 방향이다.

**전용 이름으로 준다**(노트 250 · 251). 펀딩만 갖는 축을 공유 이름으로 주면
계수가 펀딩 행으로만 적합돼 결국 전용 열이 되는데, 그러면 ``일부에게만 준
공유 열''이라는 존재하지 않는 중간을 만든다.

**청력**: 펀딩 학습 320행 > F18 의 문턱 22 --- 전용 이름이 실제로 일할 수
있는 조건이다(노트 281 · 285).

**눈금은 `grpaxes` · `mktaxes` 관례를 따른다** --- 집단을 크기 순으로 0~1 에
늘어놓고 15건 미만은 마스크 0. 순서 자체에 뜻이 없고 나무가 쪼개 쓰면 된다.
**라벨을 한 번도 안 본다**(집단 크기만 쓴다).

**시점**: 크라우드펀딩 범주는 프로젝트를 올릴 때 정하는 것이라 사전이다.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

SRC = Path("data/state/funding_axes.json")
DOM = "펀딩"
MIN_GROUP = 15


def build(root: str = ".", min_group: int = MIN_GROUP) -> dict:
    """{'fund_cat': {'펀딩': (값, 표시자)}} --- 전용 이름."""
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
    return {"fund_cat": {DOM: (v, o)}}


if __name__ == "__main__":
    d = build()
    if not d:
        raise SystemExit("만들지 못했다")
    v, o = d["fund_cat"][DOM]
    rec = json.loads(SRC.read_text())
    raw = [x.get("category") for x in rec.values()]
    c = Counter(x for x in raw if x)
    big = sorted([u for u, n in c.items() if n >= MIN_GROUP], key=lambda u: -c[u])
    print(f"fund_cat --- {len(v)}행 · 마스크 {100*float(o.mean()):.0f}%"
          f" · 무리 {len(big)}")
    for u in big:
        print(f"  {u:<24}{c[u]:>4}건  값 {float(v[raw.index(u)]):.3f}")
