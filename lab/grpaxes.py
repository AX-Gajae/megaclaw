"""집단 표지를 축으로 --- 진짜 바닥선을 하네스 안에서 만들기 위해.

노트 138에서 ``집단만 아는 예측기''가 손으로 매긴 축 다섯을 이겼다. 그걸
포트폴리오의 바닥선으로 올리려면 정식화가 집단 표지를 읽을 수 있어야 하는데,
`predict` 는 잘린 배열만 받아 원래 행을 못 찾는다. 그래서 축으로 넣는다 ---
하네스가 행을 맞춰 주는 유일한 통로다.

표지는 **라벨 눈금이 기계적으로 갈리는 자리**를 손으로 골랐다. 완결 여부 ·
무료 여부 · 매체 · 포맷 · 국가 · 카테고리. 전부 기획 시점에 아는 것이다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

D = Path("data/state")
# 표지는 **사전에 알 수 있는 것**이어야 한다(노트 141). 웹툰의 finished 는
# 완결 여부라 끝나야 안다 --- 노트 138 이 그걸로 바닥선을 잡았고, 사전
# 정보인 연령등급으로 바꾸니 +0.319 가 +0.153 이 되어 축 다섯이 이긴다.
SPEC = {"웹툰": ("webtoon_records.json", "age_type"),
        "모바일": ("mobile_records.json", "__free"),
        "애니": ("anime_records.json", "medium"),
        "세계애니": ("wanime_records.json", "format"),
        "만화": ("manga_records.json", "country"),
        "게임": ("game_records.json", "is_free"),
        "펀딩": ("funding_records.json", "category"),
        "도서": ("book_records.json", "__pub")}


def _raw(dom: str):
    from .trendaxes import _ids
    spec = SPEC.get(dom)
    ids = _ids().get(dom)
    if not spec or not ids:
        return None
    f, fld = spec
    p = D / f
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    if fld == "__free":
        return ["free" if (j.get(k) or {}).get("price") in (0, 0.0) else "paid"
                for k in ids]
    if fld == "__pub":
        from collections import Counter
        c = Counter((j.get(k) or {}).get("publisher") for k in ids)
        top = {p_ for p_, n in c.items() if n >= 20}
        return [str((j.get(k) or {}).get("publisher"))
                if (j.get(k) or {}).get("publisher") in top else "기타"
                for k in ids]
    return [str((j.get(k) or {}).get(fld)) for k in ids]


def build(min_group: int = 15) -> dict:
    """{'grp': {도메인: (값, 표시자)}}. 값은 집단을 0~1 눈금에 늘어놓은 것."""
    col = {}
    for dom in SPEC:
        raw = _raw(dom)
        if raw is None:
            continue
        from collections import Counter
        c = Counter(raw)
        big = [u for u, n in c.items() if n >= min_group]
        if len(big) < 2:
            continue
        # 집단을 크기 순으로 늘어놓고 0~1 --- 순서 자체에는 뜻이 없다.
        # 모형은 이 값을 쪼개서 쓰면 되고, 선형 모형에는 불리하다.
        order = sorted(big, key=lambda u: -c[u])
        pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
        v = np.array([pos.get(u, 0.5) for u in raw], float)
        o = np.array([1.0 if u in pos else 0.0 for u in raw], float)
        col[dom] = (v, o)
    return {"grp": col} if col else {}


def coverage() -> dict:
    b = build()
    if not b:
        return {}
    return {d: {"행": len(v[0]), "덮음": round(float(v[1].mean()), 3)}
            for d, v in b["grp"].items()}


if __name__ == "__main__":
    print(json.dumps(coverage(), ensure_ascii=False, indent=1))


# ── 두 번째 표지(노트 420) --- **지어 놓고 안 쓴다** ──────────────────
#
# **판은 통과하는데 안 넣었다.** 짝 12뽑기 판 +0.0035 +- 0.0024 · 11/12 로
# 노트 378 조건 ① 을 넘는데, **전이를 확실히 잃는다** --- KR 만화
# +0.1946 -> +0.0806, 같은 유보 행 짝 되뽑기로 차 **+0.1140
# [95% +0.0674, +0.1589] · 800/800**.
#
# 그래서 노트 419가 세운 방향(``더 갈라 주면 더 산다'')이 **반증됐다**.
# 도메인 표지는 **봉우리가 있다** --- 하나(grp)는 전이를 +0.2950 사고,
# 둘째는 -0.1140 을 되판다. 학습 도메인을 더 잘게 가를수록 모형이 그
# 도메인 집합에 맞춰지고, 안 본 도메인은 그만큼 멀어진다.
#
# 쓰려면 **전이를 같이 재고** 쓴다. 그냥 꽂으면 판만 보고 목표를 잃는다.
# 노트 419가 정한 본줄기 --- 전이를 사는 것은 **도메인 가르는 일을 떠맡는
# 표지**다. grp 는 도메인당 값 하나뿐이라 두 번째를 준다.
#
# **전부 기획 시점 값이다.** `status` · `finished` · `is_ending` 처럼 끝나야
# 아는 것은 뺐다(노트 141). **만화가 여기 든다** --- grp 의 country 는 판의
# 만화가 JP 전용이라 상수여서 빠지는데(옳은 동작), format 은 안 상수다.
SPEC2 = {"웹툰": ("webtoon_records.json", "daily_pass"),
         "모바일": ("mobile_records.json", "advisory"),
         "애니": ("anime_records.json", "is_original"),
         "세계애니": ("wanime_records.json", "source"),
         "만화": ("manga_records.json", "format"),
         "게임": ("game_records.json", "n_platform"),
         "펀딩": ("funding_records.json", "adult_only"),
         "도서": ("book_records.json", "book_format")}


def build2(min_group: int = 15) -> dict:
    """{'grp2': {도메인: (값, 표시자)}} --- 눈금은 **도메인마다 따로**(grp 와 같다)."""
    from .trendaxes import _ids
    from collections import Counter
    ids_all = _ids()
    col = {}
    for dom, (f, fld) in SPEC2.items():
        p_ = D / f
        ids = ids_all.get(dom)
        if not p_.exists() or not ids:
            continue
        j = json.loads(p_.read_text())
        raw = [str((j.get(k) or {}).get(fld)) for k in ids]
        c = Counter(raw)
        big = [u for u, n in c.items() if n >= min_group and u not in ("None", "")]
        if len(big) < 2:
            continue
        order = sorted(big, key=lambda u: -c[u])
        pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
        col[dom] = (np.array([pos.get(u, 0.5) for u in raw], float),
                    np.array([1.0 if u in pos else 0.0 for u in raw], float))
    return {"grp2": col} if col else {}
