"""잡음 부분집합을 전수로 찾는다 --- 노트 79의 만화 사례를 여덟 도메인으로.

노트 79에서 만화 표본의 3분의 1(AniList 한국 작품 556건)이 축으로 설명되지
않는 잡음이었고, 빼니 판정치가 +0.0088 오르고 반폭이 16% 줄었다 --- **도메인을
하나 더한 것과 같은 값**이다. 그런 부분집합이 다른 도메인에도 있을 수 있다.

**절차 둘로 나눈다.**

    선별  도메인 안 자기 순위 상관만 쓴다. 부분집합을 빼고 다시 재서 오르는가.
          한 도메인 안 교차검증이라 싸다(노트 37의 논리).
    판정  선별에서 올라온 것만 앙상블 자로 짝지은 붓스트랩 + 씨앗 넷(노트 72).

**후보를 많이 보므로 선택 편향이 크다**(노트 67). 그래서 판정 문턱을 그대로
두고, 채택된 것에는 **의미 근거**를 함께 적는다 --- 노트 79의 한국 작품처럼
``왜 이 부분집합만 설명이 안 되는가''에 답이 없으면 채택하지 않는다.

사용: python3 -m state.subsets
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .audit import domains
from .procrustes import factor_space, lam_by_overlap
from .rank_test import spearman

SEED = 20260729
OUT = Path("data/state/subsets.json")
SRC = {"게임": "game", "도서": "book", "펀딩": "funding", "웹툰": "webtoon",
       "애니": "anime", "모바일": "mobile", "만화": "manga"}
AXES_FILE = {k: f"data/state/{v}_axes.json" for k, v in SRC.items()}
# 부분집합을 만들 범주형 필드. 값이 하나뿐이거나 너무 잘게 갈리면 자동으로 뺀다.
FIELDS = {
    "게임": ["is_free", "label_basis", "source"],
    "도서": ["publisher"],
    "펀딩": ["category_name", "adult_only"],
    "웹툰": ["finished", "age_type", "daily_pass", "level"],
    "애니": ["medium", "is_adult", "is_free", "is_dubbed", "is_only", "is_ending"],
    "모바일": ["advisory"],
    "만화": ["format", "status", "is_adult"],
}


def self_rho(A, M, y, t, names, seed: int = SEED) -> float | None:
    """도메인 안 교차검증 자기 순위 상관. 인자 공간은 본 코드로 만든다."""
    try:
        F = factor_space(A, M, y, t, lam=1.0, names=names)
    except (np.linalg.LinAlgError, ValueError):
        return None
    S, yy = F["S"], F["y"]
    if len(yy) < 60:
        return None
    pr = np.zeros(len(yy))
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(S):
        pr[te] = Ridge(alpha=1.0).fit(S[tr], yy[tr]).predict(S[te])
    return float(spearman(pr, yy))


def scan(min_frac: float = 0.02, max_frac: float = 0.6) -> list:
    doms, names = domains()
    rows = []
    for dom, fields in FIELDS.items():
        if dom not in doms:
            continue
        ax = json.loads(Path(AXES_FILE[dom]).read_text())
        rec = json.loads(Path(f"data/state/{SRC[dom]}_records.json").read_text())
        ids = list(ax)
        base = self_rho(*doms[dom], names.get(dom))
        if base is None:
            continue
        n = len(ids)
        for f in fields:
            vals = [str((rec.get(k) or {}).get(f)) for k in ids]
            cnt = {}
            for v in vals:
                cnt[v] = cnt.get(v, 0) + 1
            for v, c in sorted(cnt.items(), key=lambda z: -z[1]):
                if not (min_frac * n <= c <= max_frac * n):
                    continue
                keep = np.array([x != v for x in vals])
                A, M, yy, t = doms[dom]
                if len(keep) != len(yy) or keep.sum() < 60:
                    continue
                r = self_rho(A[keep], M[keep], yy[keep], t[keep], names.get(dom))
                if r is None:
                    continue
                rows.append([dom, f, v, int(c), round(float(base), 4),
                             round(float(r), 4), round(float(r - base), 4)])
    rows.sort(key=lambda z: -z[6])
    return rows


def run(write: bool = True) -> list:
    rows = scan()
    print(f"부분집합 후보 {len(rows)}개 --- 빼면 자기 ρ 가 오르는 순\n")
    print(f"{'도메인':<6}{'필드':<14}{'값':<20}{'건수':>6}{'현행':>9}{'뺀 뒤':>9}{'Δ':>9}")
    for r in rows[:20]:
        print(f"{r[0]:<6}{r[1]:<14}{str(r[2])[:18]:<20}{r[3]:>6}"
              f"{r[4]:>+9.4f}{r[5]:>+9.4f}{r[6]:>+9.4f}")
    if write:
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return rows


if __name__ == "__main__":
    run()
