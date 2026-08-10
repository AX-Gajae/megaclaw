"""능력 자 — **순위 말고 절대값을 맞히나**(노트 691 · 791).

🔴 **이 파일이 있는 이유** (노트 791 · 규약 41)

노트 691 이 능력 자 넷을 재고 T6 판정을 발동시켰다(자릿수 오차 41.95% > 30%
→ *"이 판의 예보는 순위 전용"*). 그 결론은 `serve/capability.py` 에 금지 꼴로
박혔는데 **재는 코드는 스크래치패드에 있었고 세션과 함께 사라졌다.** 노트 789
가 `lab/decay.py` 에서 같은 병을 고치며 **규약 41**(*법칙을 재는 코드는
저장소에 둔다*)을 세웠고, 여기가 그 둘째 적용이다.

──────────────────────────────────────────────────────────────
**되돌림이 왜 필요한가.** 판의 예보는 **도메인 안 백분위 꼴**이다(노트 682:
펀딩 학습 0.5037 · 유보 0.5058 · SD 0.126). 라벨은 이미 log10 이라(팝업
1.046~3.903 = 11~8,000명) *자릿수 오차* 가 ``|예측 − 실제| > 1`` 로 바로
계산되는데, **백분위를 라벨 자리로 되돌려야** 그 뺄셈이 뜻을 갖는다.

노트 691 은 되돌림을 **등백분위 하나**로만 했다. 그래서 결론이 *"등백분위
사상에서"* 로 한정돼 있었다. 이 모듈은 셋을 나란히 둔다::

    inv_percentile   예보 백분위 → 학습 라벨의 같은 분위 (691 이 쓴 것)
    inv_ols          학습에서 y ~ yhat 적합 → 유보에 적용
    inv_quantile     τ=0.5 로 중앙값 · τ=0.1·0.9 로 구간

🔴 **되돌림은 위약에도 똑같이 적용한다.** 안 그러면 되돌림의 효과와 예보의
효과가 섞인다 --- 노트 691 의 구간은 *"±0.05 창의 학습 라벨 10~90분위"* 라
**예보와 거의 무관한 폭**이었고, 그것이 덮음이 위약과 안 갈린 이유일 수 있다.

🔴 **기울기는 판 평균을 쓰지 마라.** 노트 691 에서 만화 99.8 · 세계애니 8.09
로 발산한다 --- 라벨이 좁은 도메인에서 ``yhat`` 분산이 0 에 가까워 생기는
**자의 결함**이다. **도메인별 부호 일치로만 읽는다.**

**모든 되돌림 계수는 학습 구간에서만 배운다**(노트 645 --- 정규화 통계도
누출이다).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata, spearmanr

from lab import guards as G
from lab.harness import Data

T_CUT = 2025.0
#: 자릿수 오차 판정선. **T6 이 노트 691 전에 못박은 값이고 여기서 안 바꾼다.**
DIGIT_LINE = 0.30
QLO, QHI = 0.10, 0.90


# ── 예보 꺼내기 ────────────────────────────────────────────────
def forecasts(make, data: Data, T: float = T_CUT, seed: int = 0) -> dict:
    """도메인 → ``(yhat_tr, y_tr, yhat_ho, y_ho)``. **유보는 학습에 안 쓴다.**

    배선상 중요한 것 둘: ① `guards._split` 이 라벨 결측을 연도와 함께 거르므로
    학습 마스크를 그대로 뒤집으면 안 된다 --- 유보도 **라벨 유한**을 따로 건다
    ② 예보 길이와 행수가 어긋나면 조용히 넘기지 않고 `None` 으로 적는다.
    """
    f = G._fit_on(make, data, T, seed=seed)
    out = {}
    for d in data.dom:
        yr = np.asarray(data.yr[d], float)
        y_all = np.asarray(data.dom[d][2], float)
        ktr = np.isfinite(yr) & (yr < T) & np.isfinite(y_all)
        kho = np.isfinite(yr) & (yr >= T) & np.isfinite(y_all)
        if ktr.sum() < 20 or kho.sum() < 20:
            continue
        got = {}
        for nm, k in (("tr", ktr), ("ho", kho)):
            A, M, y, t = data.slice(d, k)
            try:
                p = np.asarray(f.predict(d, A, M, t), float)
            except Exception:
                p = None
            if p is None or p.shape[0] != len(y):
                got = None
                break
            ok = np.isfinite(p) & np.isfinite(y)
            got[nm] = (p[ok], y[ok])
        if got:
            out[d] = (*got["tr"], *got["ho"])
    return out


def wiring(fc: dict, data: Data, T: float = T_CUT) -> dict:
    """**배선 검사** --- 도메인별 행수와 예보 길이를 맞춰 찍는다."""
    w = {}
    for d, (ptr, ytr, pho, yho) in fc.items():
        yr = np.asarray(data.yr[d], float)
        w[d] = {"학습": len(ytr), "유보": len(yho),
                "유보(원래)": int((np.isfinite(yr) & (yr >= T)).sum()),
                "예보 상수인가": bool(len(np.unique(pho)) < 3),
                "예보 SD": round(float(np.std(pho)), 4)}
    return w


# ── 되돌림 셋. **전부 학습 행에서만 배운다** ──────────────────────
def inv_percentile(ptr, ytr, p):
    """예보 백분위 → 학습 라벨의 같은 분위(노트 691 이 쓴 것)."""
    q = (rankdata(ptr) - 0.5) / len(ptr)
    srt = np.sort(ytr)
    #: 유보 예보의 백분위를 **학습 예보 분포 안에서** 매긴다
    pct = np.searchsorted(np.sort(ptr), p, side="left") / max(len(ptr) - 1, 1)
    pct = np.clip(pct, 0.0, 1.0)
    return np.interp(pct, np.linspace(0, 1, len(srt)), srt), q


def inv_holdout_pct(ptr, ytr, p):
    """🔴 **유보 안 백분위 → 학습 라벨 분위**(노트 792). 드리프트 상쇄용.

    노트 791 이 **예보 자가 학습→유보에서 −1.7~+3.7 SD 옮겨 가는데 라벨은
    −0.03 SD 밖에 안 옮기는 것**을 찾았다. 순위를 **유보 안에서** 매기면 그
    옮김이 상쇄된다 --- 라벨 쪽은 학습만 본다(노트 645).

    ⚠️ **전이적(transductive)이다.** 유보 예보 *분포* 를 쓰므로 **한 건씩
    예보하는 데는 못 쓰고 배치 채점에만** 쓸 수 있다. 라벨은 안 본다.
    """
    pct = (rankdata(p) - 0.5) / len(p)
    srt = np.sort(ytr)
    return np.interp(pct, np.linspace(0, 1, len(srt)), srt), None


def climatology(ytr, n):
    """기준선 --- **학습 라벨 평균을 늘 말하고 구간은 학습 10~90분위**.

    노트 791 이 OLS 위약이 정확히 이것임을 확인했다(기울기 1e-6~4e-2 · 예측
    SD ≈ 0). **약한 위약 대신 이름 붙인 기준선을 쓴다** --- 노트 691 의 등백분위
    위약은 *라벨 분포에서 무작위로 뽑는 것* 이라 기후값보다 훨씬 나쁜 상대였고,
    그 약한 상대와 비겨서 *"구분 안 된다"* 로 적혔다.
    """
    m = float(np.mean(ytr))
    return (np.full(n, m),
            np.full(n, float(np.percentile(ytr, 10))),
            np.full(n, float(np.percentile(ytr, 90))))


def inv_ols(ptr, ytr, p):
    """학습에서 ``y ~ yhat`` 적합해 유보에 적용."""
    if np.std(ptr) < 1e-12:
        return np.full(len(p), float(np.median(ytr))), None
    b, a = np.polyfit(ptr, ytr, 1)
    return a + b * p, (a, b)


def _qfit(x, y, tau, iters=400):
    """분위 회귀 ``y = a + b x`` 를 경사로 푼다(외부 의존 없이).

    🔴 **규모를 없애고 푼다**(노트 791). 처음엔 원값에 경사를 걸었는데
    **판 예보의 SD 가 도메인마다 5.6~1,581 로 300배 다르다** --- 라벨(log10 ·
    SD 0.35~2.2)과도 자가 다르다. 그 상태로 고정 학습률을 쓰니 분위회귀가
    발산해서 **자릿수 오차 0.998** 이라는 말이 안 되는 값을 냈다. 표준화하면
    학습률이 자에 안 걸린다.

    노트 691 은 *"예보는 도메인 안 백분위 꼴(SD 0.126)"* 이라고 적었는데
    **챔피언 `F18_bagboost` 는 그렇지 않다**(만화 8.19~5,621.27). 등백분위
    되돌림은 순위 기반이라 그래도 돌지만, **자를 쓰는 되돌림은 표준화가 필요하다.**
    """
    sx = max(float(np.std(x)), 1e-12)
    sy = max(float(np.std(y)), 1e-12)
    mx, my = float(np.mean(x)), float(np.mean(y))
    u, v = (x - mx) / sx, (y - my) / sy
    b, a = (np.polyfit(u, v, 1) if np.std(u) > 1e-12
            else (0.0, float(np.median(v))))
    for _ in range(iters):
        g = np.where(v - (a + b * u) >= 0, tau, tau - 1.0)   # 핀볼 손실
        a += 0.5 * float(g.mean())
        b += 0.5 * float((g * u).mean())
    #: 표준화 좌표에서 원래 자로 되돌린다
    return my + sy * (a - b * mx / sx), sy * b / sx


def inv_quantile(ptr, ytr, p, taus=(QLO, 0.5, QHI)):
    """τ=0.5 로 중앙값 · τ=0.1·0.9 로 구간. **셋 다 학습에서 배운다.**"""
    out = {}
    for tau in taus:
        a, b = _qfit(ptr, ytr, tau)
        out[tau] = a + b * p
    return out[0.5], out


# ── 자 넷 ─────────────────────────────────────────────────────
def rulers(yhat, y, lo=None, hi=None) -> dict:
    """자릿수 오차 비율 · 중앙절대오차 · 기울기 · 구간 덮음."""
    e = np.abs(yhat - y)
    r = {"자릿수 오차 비율": float(np.mean(e > 1.0)),
         "중앙절대오차": float(np.median(e)),
         "행": int(len(y))}
    #: 🔴 기울기는 도메인별로만 읽는다 --- 판 평균은 발산한다(노트 691)
    r["기울기"] = (float(np.polyfit(yhat, y, 1)[0])
                 if np.std(yhat) > 1e-12 else None)
    if lo is not None and hi is not None:
        a, b = np.minimum(lo, hi), np.maximum(lo, hi)
        r["구간 덮음"] = float(np.mean((y >= a) & (y <= b)))
        r["구간 폭 중앙값"] = float(np.median(b - a))
    return r


def shuffle_in_domain(p, rng):
    """위약 --- **도메인 안에서 값만 섞는다**(노트 335 · 관측 무늬 그대로)."""
    q = np.asarray(p, float).copy()
    rng.shuffle(q)
    return q


#: 🔴 노트 802 가 조건부 능력으로 승격한 8개 도메인. **가용성(노트 800 의
#: 행수 규칙)이 정한 목록이고 결과로 고른 것이 아니다** --- 도서·시장팝업·팝업은
#: 안 옮김을 잴 수 없어(행 부족·훈련 밖) 보정이 없고, 그 셋은 기후값이 문구다.
DRIFT_DOMAINS = ("게임", "만화", "모바일", "세계애니", "아이돌", "애니",
                 "웹툰", "펀딩")


def inshift(f23, data, d, minrow: int = 30):
    """노트 800 의 **안 옮김** --- T=2023 적합 · 2023 이전 → 2023~24.

    유보(≥2025)를 한 번도 안 보므로 이 수로 만든 보정은 전이적이지 않다
    (한 건씩 예보에 쓸 수 있다). 돌려주는 값은 앞창 SD 단위.
    """
    yr = np.asarray(data.yr[d], float)
    y = np.asarray(data.dom[d][2], float)
    fin = np.isfinite(yr) & np.isfinite(y)
    w0 = fin & (yr < 2023)
    w1 = fin & (yr >= 2023) & (yr < 2025)
    if d not in getattr(f23, "doms", {}) or min(w0.sum(), w1.sum()) < minrow:
        return None
    A, M, _y, t = data.dom[d]
    try:
        p0 = np.asarray(f23.predict(d, A[w0], M[w0], t[w0]), float)
        p1 = np.asarray(f23.predict(d, A[w1], M[w1], t[w1]), float)
    except Exception:
        return None
    p0, p1 = p0[np.isfinite(p0)], p1[np.isfinite(p1)]
    if len(p0) < minrow or len(p1) < minrow:
        return None
    return float((p1.mean() - p0.mean()) / max(p0.std(), 1e-9))


def drift_corrected(ptr, ytr, p, shift):
    """🔴 **노트 801·802 의 보정 등백분위** --- 승격된 그 계산이다.

    ``p' = p − shift × SD(학습 예보)`` 로 되민 뒤 등백분위로 라벨 자리에.
    실측(씨앗 0~7 · 유보 3,369행 --- 11도메인 시대 분모라 **은퇴**): 자릿수 오차 **0.1711~0.1713**(무보정 0.4367 ·
    전이적 상쇄 0.1880). **못박은 8개 도메인 판 가중에서 기후값을 이긴다**
    (B 0.1430 대 C 0.1675 · 동점띠 0.01 의 2.4배 · 새 씨앗으로 확인).
    `shift` 가 None 이면 보정 없이 되돌린다 --- 그 도메인은 기후값이 문구다.
    """
    if shift is None:
        return inv_percentile(ptr, ytr, p)[0]
    q = p - shift * max(float(np.std(ptr)), 1e-9)
    return inv_percentile(ptr, ytr, q)[0]


def label_spread(y) -> dict:
    """라벨 자리폭과 **집중도**. 노트 691 예측 ② 가 자리폭으로 틀렸다."""
    y = np.asarray(y, float)
    return {"자리폭": float(y.max() - y.min()),
            "IQR": float(np.percentile(y, 75) - np.percentile(y, 25)),
            "SD": float(y.std())}


def align(per_dom: dict, key: str, spread_key: str):
    """도메인별 자와 라벨 퍼짐의 스피어만. **n=10 안팎이라 약한 자다.**"""
    ks = [d for d in per_dom
          if per_dom[d].get(key) is not None
          and per_dom[d].get(spread_key) is not None]
    if len(ks) < 4:
        return None, len(ks)
    a = [per_dom[d][key] for d in ks]
    b = [per_dom[d][spread_key] for d in ks]
    return float(spearmanr(a, b).statistic), len(ks)
