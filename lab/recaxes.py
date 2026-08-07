"""레코드에 이미 있는데 축으로 안 쓰인 필드 --- **취소됨**(노트 239 → 240).

노트 239가 웹툰 레코드에서 ``태그 수''를 찾아 판을 +0.0038 올렸고, 노트
240이 세계애니 · 만화까지 넓혀 +0.0105(t=3.07)를 얻었다. **둘 다 취소한다.**

``target_breadth'' 가 바로 그 태그 수다 --- ``webtoon_axes.py`` 는
``scale01(n_tag, 3, 14)``, ``wanime_axes.py`` · ``manga_axes.py`` 는
``scale01(n_tag, 3, 30)`` 이다. 관측 행 안 순위 상관이 웹툰 +0.985 ·
세계애니 +1.000 · 만화 +1.000 이다. 세계애니는 위로 5.9%, 만화는 3.6%
밖에 안 뭉개니 **새 순서가 하나도 안 들어온다**.

그런데도 이득이 났다. 갈라 보니:

  있는 target_breadth 열을 **그대로 복사**해서 넣으면  +0.0100 (t=2.70)
  태그 수를 새 열로 넣으면                            +0.0106 (t=2.98)
  전역 alpha 를 20 → 10 으로 내리면                   -0.0001 (t=-0.13)

정보가 0 인 복사본이 같은 값을 낸다. 이득은 자료가 아니다. 노트 239의
``태그 수가 세다''는 틀렸다.

무엇이었는지는 노트 241이 갈랐다 --- **벌점이 아니라 도메인별 기울기다.**
복사본에 이름을 하나만 주고 전 도메인이 나눠 쓰게 하면 벌점은 똑같이 반이
되는데 판이 안 움직인다(+0.0005). 도메인마다 제 이름을 줄 때만 난다
(+0.0102). 그리고 어느 (축, 도메인) 쌍에 기울기를 줄지 **안쪽에서 고르면
판이 내려간다**(-0.0070) --- 안쪽 신호가 부호부터 반대다. 그래서 노트 241은
이 이득을 거부했다.

**뭉갬을 푸는 것은 더 나쁘다.** 새 열을 더하는 대신 있는 축의 경계를
고쳐 보면(분위 경계 또는 순위) 판이 0.4546 에서 0.4213 · 0.4270 으로
내려앉는다(t=-4.21 · -3.31). 뭉갠 고원 자체가 정보고, 선형 꼬리는 아니다.

**모바일 price 는 반례다.** 학습 상관 -0.561 에 시간 다섯 조각 부호
5/5 인데 판을 -0.0270(t=-5.76) 내린다. ``entry_friction`` 과 -0.959 로
겹치는데(``scale01(price, 0, 15)`` --- 달러로 쓴 경계에 원 값이 들어가
1,100~44,000원 709건이 전부 1.0 이다), 공유 계수를 빼앗아 간다:
``entry_friction`` 계수가 56% 깎이고, 그 축에 기대는 **웹툰이** 0.4080에서
0.3380으로 무너진다 --- 웹툰은 그 열을 보지도 못하는데.

그래서 SPEC 을 비운다. 남는 것은 노트 239가 만든 절차(학습 상관 x 시간
조각 부호)가 **겹말을 못 걸러낸다**는 사실이고, 그것이 가드 열일곱
``겹말``(g_dup) 이 되었다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

# **비었다**(노트 240). 아래가 노트 239 · 240 이 고른 여섯이고, 학습 구간
# 연도 통제 상관과 시간 5조각 부호 일치를 다 통과했지만 전부 취소됐다.
#
#   웹툰   n_tag   +0.475  → target_breadth 와 +0.985 (겹말)
#   세계애니 n_tag   +0.512  → target_breadth 와 +1.000 (겹말)
#   만화   n_tag   +0.486  → target_breadth 와 +1.000 (겹말)
#   모바일  price   -0.561  → entry_friction 과 -0.959 (겹말 · 판 -0.0270)
#   게임   n_lang  +0.351  → target_breadth 와 +0.611 (판 +0.0008, 무의미)
#   애니   age     +0.283  → target_breadth 와 +1.000 (겹말)
#
# 여섯 중 다섯이 이미 판에 있는 축의 다시 쓰기였다. 되살리려면 먼저
# ``guards.g_dup`` 을 통과해야 하고, 통과하더라도 그것은 자료가 아니라
# 축별 벌점 변경으로 보고해야 한다.
SPEC: dict = {}


@lru_cache(maxsize=1)
def _ids() -> dict:
    from .trendaxes import _ids as tid
    return tid()


def _pct(v: np.ndarray) -> tuple:
    m = np.isfinite(v).astype(float)
    p = np.full(len(v), 0.5)
    o = np.isfinite(v)
    if o.sum() > 1:
        p[o] = (rankdata(v[o]) - 0.5) / o.sum()
    return p, m


def build(root: str = ".") -> dict:
    """{축이름: {도메인: (값, 표시자)}}"""
    ids = _ids()
    out: dict = {}
    for dom, (rf, _axf, fields) in SPEC.items():
        p = Path(root) / "data/state" / rf
        if not p.exists() or dom not in ids:
            continue
        rec = json.loads(p.read_text())
        order = ids[dom]
        for f in fields:
            v = []
            for i in order:
                x = (rec.get(i) or {}).get(f)
                if isinstance(x, bool):
                    x = float(x)
                v.append(np.nan if x is None else float(x))
            arr = np.array(v, float)
            if np.isfinite(arr).sum() < 20:
                continue
            out.setdefault(f"rec_{f}", {})[dom] = _pct(arr)
    return out
