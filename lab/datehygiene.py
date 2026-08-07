"""시작일이 **물리적으로 불가능한** 행을 채점에서 뺀다 --- 네 번째 누수 층.

노트 117 이 가드 둘(라벨 상관 · 같은 플랫폼)을 세우고 노트 141 이 셋째
(``그 값을 언제 알 수 있나'')를 세웠다. 노트 552 에서 넷째가 빠져 있다는
것을 알았다. **그 날짜가 맞나.**

노트 546 이 웹툰 ``days`` 가 매일$+$ 전환으로 오염된 것을 찾았고, 노트 552
에서 **같은 전환이 ``start_date`` 도 옮긴다**는 것이 드러났다. 시작일 요일의
월요일 비중이

    연재중 · 매일+ 아님    13.9%   (균등 14.3%)
    완결 · 매일+ 아님      17.1%
    완결 · 매일+          25.8%   **초과 +11.6%p**

로 ``days`` 와 똑같은 무늬다.

**라벨을 한 번도 안 보고 확정했다.** 주당 회차 = ``n_episode`` / (오늘 −
``start_date``) 주수는 연재 요일 수(``n_day``)를 넘을 수 없다 --- 주 1회
연재작이 주당 두 편씩 나올 수는 없다. 문턱별로

    > 1.0 x n_day    543행 (유보 447) · 월요일 시작 27.6% · 매일+ 20%
    > 2.0 x n_day     64행 (유보  61) · 월요일 시작 84.4% · 매일+ 95%
    > 3.0 x n_day     48행 (유보  47) · 월요일 시작 95.8% · 매일+ 100%

**문턱 2.0 을 쓴다** --- 보너스 회차와 몰아보기를 넉넉히 봐준 자리이고,
3.0 과 견줘 열여섯 행 차이다.

걸린 $64$ 행 중 **$61$ 행이 유보에 있다**(웹툰 유보 $711$ 의 $8.6\%$).
그 행들의 라벨 중앙은 $2{,}589$ 로 나머지 유보 $35{,}697$ 의 **$1/13.8$**
이다. 오래된 비인기 완결작이 매일$+$ 로 넘어가면서 시작일이 최근 월요일로
재설정돼 **2025년 이후 유보에 신작인 척 들어와 있었다.**

**왜 빼는가.** 시간으로 가르는 유보에서 ``언제 나왔는지 모르는 행''은 채점
대상이 아니다. 다시 매길 수도 없다 --- 참 날짜가 자료 어디에도 없다(웹툰
레코드의 날짜 칸은 ``start_date`` 하나뿐이다).

**빼는 방법은 행 삭제가 아니라 라벨을 NaN 으로 두는 것이다.** 하네스는
``np.isfinite(y)`` 로 학습과 채점을 둘 다 가르므로 그것으로 충분하고,
**행 수가 그대로라 축 결합이 안 깨진다**(노트 133 의 조용한 중립 대체를
피한다).

**대가**: 판 $0.4812 \to 0.4663$ ($-0.0149$, $0/12$) · 웹툰 $0.4334 \to
0.3528$ · **웹툰 연재중만 $0.3304 \to 0.3225$**(거의 안 움직인다 --- 그
행들은 원래 그 조각에 없었다) · KR 만화 $+0.0018$(문다) · 앱 $+0.0006$
(문다). **성능 하락이 아니라 그동안의 과대 보고다** --- 노트 306 · 547 과
같은 처분이고, 분모가 $3{,}430 \to 3{,}369$ 로 바뀌므로 **이 시점 이전
실행의 판과 견주면 안 된다.**

다른 도메인에는 못 건다 --- ``n_episode`` 처럼 경과 기간과 대조할 수 있는
칸이 웹툰에만 있다. 상태 칸이 있는 넷 중 상태$\leftrightarrow$라벨이 센
것도 웹툰뿐이다(노트 549 감사).
"""
from __future__ import annotations

import datetime
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

D = Path("data/state")

# 도메인 → (레코드 파일, 축 파일, 회차 칸, 주당 상한 칸, 문턱)
SPEC = {"웹툰": ("webtoon_records.json", "webtoon_axes.json",
                "n_episode", "n_day", 2.0)}

MIN_EPISODE = 10       # 회차가 적으면 비가 불안정하다
TODAY = datetime.date(2026, 8, 4)   # 스냅샷 시점. 늘리면 문턱이 느슨해진다.


@lru_cache(maxsize=1)
def bad(root: str = ".") -> dict:
    """{도메인: bool 배열} --- True 면 시작일을 못 믿는다."""
    out = {}
    for dom, (rf, af, ep, nd, k) in SPEC.items():
        rp, ap = Path(root) / D / rf, Path(root) / D / af
        if not rp.exists() or not ap.exists():
            continue
        rec = json.loads(rp.read_text())
        byid = {v["record_id"]: v for v in rec.values()
                if isinstance(v, dict) and "record_id" in v}
        ids = list(json.loads(ap.read_text()))
        m = np.zeros(len(ids), bool)
        for i, rid in enumerate(ids):
            v = byid.get(rid) or {}
            e = float(v.get(ep) or 0)
            if e < MIN_EPISODE:
                continue
            try:
                dt = datetime.date.fromisoformat(str(v.get("start_date"))[:10])
            except Exception:
                continue
            wks = max((TODAY - dt).days / 7.0, 1.0)
            if e / wks > k * max(float(v.get(nd) or 1), 1.0):
                m[i] = True
        out[dom] = m
    return out


def apply(dom: dict) -> tuple:
    """``domains()`` 의 결과에서 못 믿을 행의 라벨을 NaN 으로 만든다.

    (바뀐 dom, {도메인: 뺀 행 수}) 를 낸다. 뺀 수를 함께 내는 것은
    **가드가 조용히 안 도는 것을 막기 위해서**다(노트 547 의 STALE_HITS 와
    같은 취지) --- 축 파일이 갈리면 마스크가 통째로 안 붙을 수 있다.
    """
    hits = {}
    B = bad()
    for d, m in B.items():
        if d not in dom:
            continue
        A, M, y, t = dom[d]
        if len(y) != len(m):
            # 행 수가 안 맞으면 **조용히 넘기지 않는다**(노트 133).
            raise ValueError(
                f"datehygiene: {d} 행 수 {len(y)} != 축 파일 {len(m)}")
        if not m.any():
            continue
        y = np.asarray(y, float).copy()
        y[m] = np.nan
        dom[d] = (A, M, y, t)
        hits[d] = int(m.sum())
    return dom, hits
