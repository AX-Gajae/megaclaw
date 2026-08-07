"""겹침 --- 이 축이 판에 **새로운** 것을 가져오나(노트 299).

노트 239 · 285가 축 채택 검사를 셋으로 정했다.

    ① 연도를 통제한 학습 구간 상관   --- 정보가 있나
    ② 시간 조각 다섯의 부호 일치     --- 시기에 안 흔들리나
    ③ **기존 축과의 겹침**           --- 새로운가

그런데 ③ 을 거의 안 돌렸다. ① 이 떨어지면 거기서 끝났고 ① 이 통과하면
곧장 유보 수를 봤기 때문이다. 노트 299가 그 대가를 봤다 --- 시장 팝업의
``category`` 는 학습 101행에서 일평균을 **네 배 반**으로 가르는데
(크루스칼 H=18.4 · p=0.0103) 축으로 붙이면 +0.0048(t=0.12)이다. 공유 축
다섯을 통제하면 카테고리가 **안 남는다**(H=11.5 · p=0.1176). ``IP 를
업었나''(``target_breadth`` ← ``ip_or_collab``)가 이미 그 일을 하고 있다.

**0 에는 두 가지 뜻이 있다.**

    안 오른다 --- 정보가 없다      ① 이 떨어진다   → 더 좋은 자료를 구하라
    이미 있다 --- 판이 갖고 있다   ① 통과 ③ 떨어짐 → 다른 데를 보라

실무적으로 다른 다음 수인데 유보 수만 봐서는 안 갈린다. 이 파일이 ③ 이다.

**거부권이 아니라 이름표다**(노트 278~280 규약, `lab/hearing.py` 와 같다).
승격을 막지 않는다 --- 판정치 옆에 "이 축이 새로운가"를 적어 둘 뿐이다.

셈은 학습 구간에서만 한다(노트 285) --- 채택 근거는 유보가 아니다.
"""
from __future__ import annotations

import numpy as np

MIN_ROWS = 30          # 노트 239 검사 ① 의 최소 --- 그 아래면 못 잰다
MIN_GROUP = 5          # 범주 축에서 한 무리의 최소


def _shared(names: list[str]) -> list[int]:
    """공유 축 다섯의 열 번호."""
    from .forms import SHARED5
    return [i for i, n in enumerate(names) if n in SHARED5]


def _control(A: np.ndarray, M: np.ndarray, cols: list[int], y: np.ndarray):
    """공유 축(값 + 관측 표시자)으로 능형을 적합하고 잔차를 낸다.

    표시자를 같이 넣는 이유는 `forms._design` 이 그렇게 하기 때문이다 ---
    판이 실제로 쓰는 것과 같은 재료로 통제해야 "판이 이미 갖고 있나"를
    묻는 것이 된다.
    """
    from sklearn.linear_model import Ridge
    V = np.where(M[:, cols] > .5, A[:, cols], 0.5)
    I = (M[:, cols] > .5).astype(float)
    X = np.hstack([V, I])
    r = Ridge(alpha=1.0).fit(X, y)
    return y - r.predict(X), float(r.score(X, y))


def _relate(v: np.ndarray, y: np.ndarray, categorical: bool):
    """축과 라벨의 관계. 범주면 크루스칼, 아니면 스피어만."""
    from scipy.stats import kruskal, spearmanr
    if categorical:
        g = [y[v == u] for u in np.unique(v) if (v == u).sum() >= MIN_GROUP]
        if len(g) < 2:
            return None, None
        k = kruskal(*g)
        return float(k.statistic), float(k.pvalue)
    s = spearmanr(v, y)
    return float(s.statistic), float(s.pvalue)


def test3(A, M, y, names, axis: str, categorical: bool | None = None) -> dict:
    """검사 ③ --- 이 축이 공유 축 다섯을 통제하고도 라벨과 관계가 남나."""
    if axis not in names:
        return {"축": axis, "판정": "없는 축"}
    j = names.index(axis)
    obs = (M[:, j] > .5) & np.isfinite(y)
    n = int(obs.sum())
    if n < MIN_ROWS:
        return {"축": axis, "관측": n, "판정": "못 잰다",
                "왜": f"관측 학습행 {n} < {MIN_ROWS}"}
    v, yy = A[obs, j], y[obs]
    if categorical is None:
        categorical = len(np.unique(v)) <= 12
    s0, p0 = _relate(v, yy, categorical)
    if s0 is None:
        return {"축": axis, "관측": n, "판정": "못 잰다", "왜": "무리 부족"}
    cols = [c for c in _shared(names) if c != j]
    if not cols:
        return {"축": axis, "관측": n, "판정": "통제할 축 없음",
                "혼자": (s0, p0)}
    res, r2 = _control(A[obs], M[obs], cols, yy)
    s1, p1 = _relate(v, res, categorical)
    if p0 >= 0.05:
        판정 = "안 오른다"          # ① 이 떨어진다 --- 정보 자체가 없다
    elif p1 < 0.05:
        판정 = "새롭다"             # ① ③ 둘 다 통과
    else:
        판정 = "이미 있다"          # ① 통과 ③ 떨어짐 --- 판이 갖고 있다
    # **검사 ④ 비상수성**(노트 321). 축이 거의 상수면 검사 ①③ 을 통과해도
    # 유보에서 못 번다 --- `anime_medium` 이 학습 1,467행 중 1,382행(94%)이
    # 한 무리라 ①②③ 을 다 통과하고도 애니를 -0.0091 로 만들었다.
    # 판의 '새롭다' 38자리는 최빈 무리 밖이 중앙 79% 이고 anime_medium 이
    # 6% 로 제일 낮다. **필요조건이지 충분조건은 아니다**(mkt_cat 은 80%
    # 인데도 +0.0048 이다).
    from collections import Counter
    c = Counter(np.round(v, 4))
    modal = c.most_common(1)[0][1] / len(v)
    pr = np.array([x / len(v) for x in c.values()])
    eff = float(np.exp(-(pr * np.log(pr)).sum()))
    thin = (1 - modal) < 0.20
    return {"축": axis, "관측": n, "범주": bool(categorical),
            "혼자": (round(s0, 3), round(p0, 4)),
            "통제 후": (round(s1, 3), round(p1, 4)),
            "공유 R2": round(r2, 3), "판정": 판정,
            "최빈 밖": round(1 - modal, 3), "유효 무리": round(eff, 2),
            "거의 상수": bool(thin)}


def report(data, T: float = 2025.0, tgt: str | None = None,
           axes: list[str] | None = None) -> dict:
    """도메인마다 공유 축이 아닌 열들에 검사 ③ 을 돌린다."""
    from .forms import SHARED5
    out, lines = {}, []
    doms = [tgt] if tgt else sorted(data.dom)
    for d in doms:
        if d not in data.dom:
            continue
        A, M, y, _ = data.dom[d]
        yr = data.yr[d]
        k = np.isfinite(yr) & (yr < T) & np.isfinite(y)
        if k.sum() < MIN_ROWS:
            out[d] = {"판정": "못 잰다", "학습": int(k.sum())}
            continue
        names = list(data.names[d])
        cand = axes or [n for n in names if n not in SHARED5]
        res = [test3(A[k], M[k], y[k], names, a) for a in cand]
        res = [r for r in res if r.get("판정") not in ("없는 축",)]
        out[d] = res
        already = [r["축"] for r in res if r.get("판정") == "이미 있다"]
        new = [r["축"] for r in res if r.get("판정") == "새롭다"]
        if already or new:
            lines.append(f"{d}: 새롭다 {len(new)} · 이미 있다 {len(already)}"
                         + (f" ({', '.join(already[:3])})" if already else ""))
    return {"도메인": out,
            "한 줄": ("겹침 --- " + " | ".join(lines)) if lines else
                    "겹침 --- 잴 수 있는 전용 축 없음"}
