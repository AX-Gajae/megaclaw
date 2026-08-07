"""시장팝업 전용 축 --- **레코드에 이미 있는데 안 쓴 칸들**(노트 351).

노트 351이 검사 ⑤ 지도를 다시 그렸더니 시장팝업은 공유 계열 둘 다에서
못 가르는 자리였다 --- 검색 $-0.0026$(5/8) · 위키 $+0.0202$(3/8). 판에서
제일 낮은 도메인($\\rho=0.2823$)이 **공유 축으로부터 아무것도 못 받고
있다**는 뜻이다. 얇아서가 아니다: 학습 101행은 F18 문턱 22의 네 배다.

그래서 자기 레코드를 다시 열었다. ``data/state/market_axes.json`` 의 축
다섯이 쓰는 원천 칸은 넷뿐이고(``ip_or_collab`` · ``prior_count`` ·
``is_free_entry``/``reservation_required`` · ``multi_store``), 레코드에는
**덮음 100%에 가까운 칸이 그만큼 더 남아 있다.**

    venue_type      204/205 (100%)   값 5
    neighborhood    201/205 ( 98%)   값 47
    experience 수   203/205 ( 99%)   값 7
    기간 일수       205/205 (100%)   값 37
    promotions 수   146/205 ( 71%)   값 4

제일 눈에 띄는 것: 축 이름이 ``venue_prominence`` 인데 그 축이 실제로
읽는 칸은 ``ip_history.prior_count`` 다 --- **장소 축이 장소를 안 본다.**
``venue_type`` 과 ``neighborhood`` 는 한 번도 안 쓰였다.

이것은 노트 347(``fund_cat``, 펀딩 $+0.0964$)과 노트 348(원천 축 넷, 판
$+0.0068$)과 같은 종류의 일이다 --- **새로 모으는 것이 아니라 서랍에 있는
것을 꺼낸다.**

**시점.** 다섯 다 기획 시점에 정해진다 --- 어디에 낼지, 어느 동네에, 체험
요소를 몇 개 넣을지, 며칠 열지, 프로모션을 몇 개 걸지.

**``mkt_days`` 의 새는 구멍을 미리 적어 둔다.** 기간은 ``period_to`` $-$
``period_from`` 인데, 잘된 팝업은 **연장한다.** 그러면 ``period_to`` 가
사후에 늘어나 라벨(방문객)과 기획이 아닌 경로로 이어진다. 이 축만은
검사를 통과해도 ``연장 의심''을 달아 둔다. 나머지 넷에는 이 경로가 없다.

**동네 이름은 합친다** --- ``성수동''(45)과 ``성수''(23)는 같은 곳이다.
합치기 전에는 각각 무리 문턱을 따로 넘어 두 번 세어진다.

눈금은 ``grpaxes`` · ``mktaxes`` 관례를 따른다: 범주는 무리를 크기 순으로
0~1 에 늘어놓고 문턱 아래 무리는 표시자 0, 수치는 관측 행 안에서 백분위.
**라벨을 한 번도 안 본다.**
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

SRC = Path("data/state/market_axes.json")
REC = Path("data/market_records")
DOM = "시장팝업"
MIN_GROUP = 15

# 같은 곳의 다른 표기. 축 파일이 원문을 그대로 담고 있어서 여기서 합친다.
HOOD = {"성수": "성수동", "성수동카페거리": "성수동", "서울숲": "성수동",
        "여의도동": "여의도", "잠실동": "잠실", "한남": "한남동",
        "명동": "명동", "홍대": "홍대", "홍익대": "홍대",
        "가로수길": "신사동", "신사": "신사동", "압구정": "압구정동"}


def _hood(x):
    if not x:
        return None
    s = re.sub(r"\s+", "", str(x))
    return HOOD.get(s, s)


def _grp(raw, min_group: int):
    """범주 → (값, 표시자). 무리를 크기 순으로 0~1 에 늘어놓는다."""
    c = Counter(x for x in raw if x is not None)
    big = [u for u, n in c.items() if n >= min_group]
    if len(big) < 2:
        return None
    order = sorted(big, key=lambda u: (-c[u], str(u)))
    pos = {u: i / (len(order) - 1) for i, u in enumerate(order)}
    v = np.array([pos.get(x, 0.5) for x in raw], np.float32)
    o = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)
    return v, o


def _num(raw):
    """수치 → (백분위, 표시자). 관측 행 안에서만 순위를 매긴다."""
    o = np.array([x is not None for x in raw], bool)
    if o.sum() < 30:
        return None
    v = np.full(len(raw), 0.5, np.float32)
    vals = np.array([float(x) for x in raw if x is not None])
    v[o] = ((rankdata(vals) - 0.5) / o.sum()).astype(np.float32)
    return v, o.astype(np.float32)


def _days(r):
    c = r.get("conditions", {})
    a, b = c.get("period_from"), c.get("period_to")
    if not a or not b:
        return None
    try:
        d = (date.fromisoformat(b) - date.fromisoformat(a)).days
    except ValueError:
        return None
    return d if 0 <= d <= 400 else None


FIELDS = {
    "mkt_venue": ("cat", lambda r: r.get("conditions", {}).get("venue_type")),
    "mkt_hood": ("cat", lambda r: _hood(r.get("conditions", {}).get("neighborhood"))),
    "mkt_nexp": ("num", lambda r: len(r.get("intervention", {}).get("experience_elements") or []) or None),
    "mkt_days": ("num", _days),
    "mkt_npromo": ("num", lambda r: len(r.get("intervention", {}).get("promotions") or []) or None),
}


def build(root: str = ".", min_group: int = MIN_GROUP, only=None) -> dict:
    """{축이름: {'시장팝업': (값, 표시자)}} --- 전용 이름."""
    p = Path(root) / SRC
    if not p.exists():
        return {}
    # `_from_axes_json` 이 `list(d.values())` 순서로 행을 만든다 --- 같은 순서.
    ids = list(json.loads(p.read_text()))
    recs = []
    for i in ids:
        f = Path(root) / REC / f"{i}.json"
        recs.append(json.loads(f.read_text()) if f.exists() else {})
    out = {}
    for name, (kind, fn) in FIELDS.items():
        if only and name not in only:
            continue
        raw = []
        for r in recs:
            try:
                raw.append(fn(r))
            except Exception:
                raw.append(None)
        got = _grp(raw, min_group) if kind == "cat" else _num(raw)
        if got is not None:
            out[name] = {DOM: got}
    return out


if __name__ == "__main__":
    for k, d in build().items():
        v, m = d[DOM]
        print(f"{k}: {len(v)}행 · 표시자 {100*m.mean():.0f}% · "
              f"서로 다른 값 {len(np.unique(v[m > 0]))}")
