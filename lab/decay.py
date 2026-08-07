"""출시 이후 감쇠율 — **법칙 측정 코드. 축으로 쓰면 누출이다**(노트 656).

🔴 **이 파일이 있는 이유** (노트 789)

노트 656·657 이 이 자료로 T3 의 위키 경로를 닫았다. 그 결론은 대장에 남았는데
**재는 코드는 스크래치패드에 있었고 세션과 함께 사라졌다.** 대장에는
*"규모 없앤 감쇠율"* 이라고만 적혀 있어 정의를 복원할 수 없었고, 노트 789 가
자연스러운 정의 **넷을 다 시도해도 657 의 삼분위 무늬를 재현하지 못했다**
(최고 3/5). 표본 수는 정확히 일치하므로(세계애니 1,128 · 애니 396 · 웹툰 167 ·
모바일 150 · 게임 149) **행 선택이 아니라 정의만 다르다.**

노트 546·549 가 *"장부와 코드가 따로 자란다"* 를 적었다. 그때는 장부가 앞서
갔고 **이번엔 장부만 남고 코드가 없었다.** 그래서 **규약 41** 을 세우고 이
파일을 만든다 --- *법칙을 재는 코드는 저장소에 둔다.*

🔴 **누출 금지** --- `wiki_after` 는 출시 **이후** 값이라 오픈 시점에 관측
불가다. 이 모듈은 `lab/*axes.py` · `lab/loop.py` · `lab/harness.py` 가 참조하면
`ingest.audit.law_only_leak()` 이 잡는다. **축으로 쓰지 마라.**

노트 657 과 어긋나는 점(789 실측)::

    안정(4/4)   모바일 U · 세계애니 단조 · **게임 단조**
    불안정      애니(단조·U·단조·단조) · 웹툰(역U·단조·U·단조)

657 은 게임을 **U자**로 적었고 그것이 657 의 헤드라인이었다. 네 정의 모두
게임을 **단조**로, 그것도 강하게 낸다. 크기는 네 정의 모두 657 의 1.3~4.7배라
657 이 **더 긴 창**을 썼을 가능성이 높다 --- 다만 노트 789 가 후보를 넷으로
못박았으므로 다섯째는 **새로 사전등록해야** 쓴다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

#: **이 자료는 법칙 학습 전용이다.** 축으로 쓰면 시간 게이트 위반이다.
LAW_ONLY = True

ROOT = Path(__file__).resolve().parents[1]
AFTER = ROOT / "data/state/wiki_after"
AXD = ROOT / "data/state"

#: 도메인 → 축 파일. **행 순서가 판과 같다는 것을 노트 789 가 확인했다**
#: (애니 3,385 · 웹툰 3,652 · 세계애니 2,948 · 모바일 2,000 · 게임 482 일치).
#: 🔴 아이돌은 축파일 81 대 판 173 으로 **어긋나므로 넣지 않는다.**
AX = {"애니": "anime_axes", "웹툰": "webtoon_axes", "세계애니": "wanime_axes",
      "모바일": "mobile_axes", "게임": "game_axes", "만화": "manga_axes",
      "도서": "book_axes", "펀딩": "funding_axes", "시장팝업": "market_axes"}

#: 노트 789 가 **결과 보기 전에 못박은** 정의 넷. 순서가 곧 동점 우선순위다.
DEFS = ("A_log45", "B_meanslope", "C_log30", "D_ratio7")
#: 🔴 **복원된 정의**(노트 811 · 새 사전등록으로 추가). 90일 창이 노트 657 의
#: 무늬 4/5 를 재현하고 **크기 배수가 ~1.0**(세계애니 1.01·1.02·1.01 · 모바일
#: 1.14/0.99/0.74) --- 657 은 E_log90 을 썼다. **단 게임 U자(657 의 헤드라인)는
#: 복원된 정의로도 단조다** --- 그 주장만은 영구 재현 불가로 남는다(행 146 대
#: 657 의 149 --- 90일 조건이 3행을 떨어뜨린 차이가 후보이나 확정 불가).
DEF_RECOVERED = "E_log90"
MINROW = 60          # 노트 657 과 같은 문턱(5분위당 12행)
NBIN = 5
T_CUT = 2025.0

#: 노트 657 이 대장에 적은 삼분위 무늬. **재현 대조표이고 정답이 아니다** ---
#: 노트 789 가 네 정의 모두에서 게임을 단조로 냈다.
SHAPE657 = {"게임": "U", "모바일": "U", "애니": "U", "웹툰": "역U",
            "세계애니": "단조"}


def decay_rate(days, how: str = "A_log45") -> float:
    """하루치 조회수 목록에서 감쇠율 하나를 낸다.

    `days` 는 ``[[YYYYMMDD, 조회수], ...]`` 다(`ingest/wiki_after` 캐시 형식).
    """
    v = np.clip(np.array([x[1] for x in days], float), 0, None)
    if how == "A_log45":
        v = v[:45]
        y = np.log1p(v) if len(v) == 45 else None
    elif how == "E_log90":
        v = v[:90]
        y = np.log1p(v) if len(v) == 90 else None
    elif how == "C_log30":
        v = v[:30]
        y = np.log1p(v) if len(v) == 30 else None
    elif how == "B_meanslope":
        v = v[:45]
        mu = v.mean() if len(v) == 45 else 0.0
        y = v / mu if mu > 0 else None      # **규모를 나눠 없앤다**
    elif how == "D_ratio7":
        v = v[:45]
        if len(v) < 45:
            return float("nan")
        a, b = v[:7].mean(), v[-7:].mean()
        return float((np.log1p(b) - np.log1p(a)) / 38.0)
    else:
        raise ValueError(f"모르는 정의: {how} (있는 것 {DEFS})")
    if y is None or not np.isfinite(y).all() or y.std() == 0:
        return float("nan")
    return float(np.polyfit(np.arange(len(y), dtype=float), y, 1)[0])


def load_rates(how: str = "A_log45") -> dict:
    """레코드 id → 감쇠율. 캐시 전부를 읽는다."""
    out = {}
    for p in AFTER.glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        if len(j.get("days") or []) >= 45:
            g = decay_rate(j["days"], how)
            if np.isfinite(g):
                out[j.get("record_id") or p.stem] = g
    return out


def by_domain(rates: dict, data, minrow: int = MINROW):
    """도메인 → (감쇠율, 라벨). **학습 행만**(노트 568 --- 유보를 안 본다).

    `data` 는 `lab.harness` 의 Data (``data.dom[k] == (A, M, y, t)``).
    반환값 둘째는 배선 표다 --- **행수가 안 맞으면 조용히 건너뛰지 않고 적는다.**
    """
    dom, wire = {}, {}
    for k, f in AX.items():
        if k not in data.dom:
            continue
        ids = list(json.loads((AXD / f"{f}.json").read_text()))
        _A, _M, y, t = data.dom[k]
        if len(ids) != len(y):
            wire[k] = {"⛔ 어긋남": f"축파일 {len(ids)} 대 판 {len(y)}"}
            continue
        g = np.array([rates.get(r, np.nan) for r in ids], float)
        keep = np.isfinite(g) & np.isfinite(y) & (np.asarray(t, float) < T_CUT)
        wire[k] = {"판 행": len(y), "감쇠율 있음": int(np.isfinite(g).sum()),
                   "학습 & 있음": int(keep.sum())}
        if keep.sum() >= minrow:
            dom[k] = (g[keep], np.asarray(y, float)[keep])
    return dom, wire


def shape_of(g, y):
    """삼분위 감쇠율 중앙값 → ``('U' | '역U' | '단조', [세 값])``."""
    q = np.quantile(y, [1 / 3, 2 / 3])
    parts = (g[y <= q[0]], g[(y > q[0]) & (y <= q[1])], g[y > q[1]])
    m = [float(np.median(a)) if len(a) else np.nan for a in parts]
    if not all(np.isfinite(m)):
        return "?", m
    if m[1] < m[0] and m[1] < m[2]:
        return "U", m
    if m[1] > m[0] and m[1] > m[2]:
        return "역U", m
    return "단조", m


def stair(g, y, nbin: int = NBIN):
    """**계단 함수** --- 감쇠율 5분위 칸마다 라벨 백분위 중앙값.

    이것을 **다른 도메인**에 먹이는 것이 전이 시험이다. 계단은 이 도메인의
    라벨로만 만들고 채점은 상대 도메인의 라벨로 하므로 순환이 아니다.
    """
    edges = np.quantile(g, np.linspace(0, 1, nbin + 1)[1:-1])
    idx = np.searchsorted(edges, g, side="right")
    yp = rankdata(y) / len(y)
    med = np.array([np.median(yp[idx == k]) if (idx == k).any() else np.nan
                    for k in range(nbin)])
    if not np.isfinite(med).all():           # 빈 칸은 앞뒤로 채운다
        ok = np.flatnonzero(np.isfinite(med))
        med = np.interp(np.arange(nbin), ok, med[ok])
    return edges, med


def transfer(src, dst, nperm: int = 200, seed: int = 0) -> dict:
    """`src` 에서 배운 계단을 `dst` 에 먹여 **dst 안에서** 채점한다.

    문턱은 **dst 라벨을 `nperm` 번 섞은 순열 영분포의 2σ** 다 --- 씨앗 SE 가
    아니다(노트 613: 씨앗 SE 는 재현성이지 일반화가 아니다). 값만 섞고 관측
    무늬는 그대로 둔다(노트 335).
    """
    e, m = stair(*src)
    gb, yb = dst
    pred = m[np.searchsorted(e, gb, side="right")]
    if len(np.unique(pred)) < 2:
        return {"rho": None, "왜": "예측이 상수"}
    rho = float(spearmanr(pred, yb).statistic)
    rng = np.random.default_rng(seed)
    null = np.array([spearmanr(pred, rng.permutation(yb)).statistic
                     for _ in range(nperm)], float)
    mu, sd = float(null.mean()), float(null.std(ddof=1))
    thr = mu + 2 * sd
    return {"rho": round(rho, 4), "영평균": round(mu, 4),
            "영2σ 문턱": round(thr, 4), "**넘나**": bool(rho > thr),
            "z": round((rho - mu) / sd, 2) if sd else None, "B 행": len(yb)}
