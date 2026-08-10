"""규약 47 의 자 --- 모델 짝 비교의 군집 부트스트랩 (노트 827~828).

**왜 저장소인가.** 규약 하나(47)와 판정 13개를 낳은 코드가 스크래치패드에만
있었다(티처 #4 · 노트 683/789 의 같은 병). 여기로 옮기고 회귀 시험으로 못박는다.

자의 정의(규약 47):
    구간        BCa 95% (자코나이프 가속 · 실패/퇴화 시 percentile 폴백 명기)
    재표집 단위 프랜차이즈 클러스터(v0: 정규화 제목 + 시즌/권차 접미사 제거 ·
                매칭 불가/제목 없음 행은 단독 클러스터 --- **무군집 폴백은
                반드시 병기한다**, 티처 #4)
    판정        하한 > 0 승 · 상한 < 0 패 · 0 물면 **판정 불능(동점 아님)**
    비열등      '해롭지 않다'는 사전 마진 δ 에 대해 하한 > -δ 일 때만
    금지        상수 0.262/sqrt(n) 자(부검: 노트 827 서문) · 끝점 정전화

**한계도 자의 일부다**: 행 독립 가정(무군집 도메인)은 폭을 **과소**, 소표본
percentile 은 커버리지 미달 --- 구간을 액면 그대로 믿지 않는다.
"""
from __future__ import annotations

import re

import numpy as np

B_DEFAULT = 10_000

#: 좌측 경계 필수(티처 #5 — '아파트 404' 의 단어 속 '파트' 삼킴 방지) ·
#: 후행 숫자는 **공백으로 분리된 것만** 절단('AKB48' 보존 · 노트 829)
_SEASON = re.compile(r"(?<![0-9a-z가-힣])(시즌|season|part|파트)\s*[0-9ivx]+|"
                     r"[0-9]+기$|[0-9]+부$|\b[ivx]{1,4}$|\s[0-9]+$")


def franchise_key(title: str) -> str:
    """프랜차이즈 클러스터 v0 열쇠. 빈 문자열이면 매칭 불가."""
    s = str(title or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣 ]+", "", s).strip()
    s = _SEASON.sub("", s).strip()
    return re.sub(r"\s+", "", s)


def solo_clusters(n: int) -> tuple[list, dict]:
    """전 행 단독 클러스터 + 병기. 제목 원천이 없을 때의 **명시적** 폴백 —
    조용한 폴백을 호출자에게 흩지 않는다(티처 #5 결함 ③)."""
    return ([np.asarray([i], int) for i in range(n)],
            {"행": n, "군집": n, "병합": 0,
             "⚠ 무군집": "제목 원천 없음 — 행 부트스트랩과 동일(폭 과소 방향)"})


def clusters_of(titles, n: int | None = None) -> tuple[list, dict]:
    """행 목록 → (클러스터 목록, 병기용 요약). titles=None 이면 solo(n 필수)."""
    if titles is None:
        if n is None:
            raise ValueError("titles=None 이면 n 을 줘야 한다(solo_clusters)")
        return solo_clusters(n)
    key = {}
    for i, t in enumerate(titles):
        k = franchise_key(t) or f"__solo{i}"
        key.setdefault(k, []).append(i)
    cl = [np.asarray(v, int) for v in key.values()]
    merged = len(titles) - len(cl)
    wire = {"행": len(titles), "군집": len(cl), "병합": merged}
    if merged == 0:
        wire["⚠ 무군집"] = "행 부트스트랩과 동일 — 폭 과소 방향(규약 47 병기 의무)"
    return cl, wire


def cluster_boot(stat_fn, clusters, B: int = B_DEFAULT, seed: int = 827):
    """군집 재표집 BCa 95%. 반환 (점추정, lo, hi, 종류)."""
    if not clusters:
        raise ValueError("빈 클러스터 목록 — solo_clusters(n) 를 쓰라")
    rng = np.random.default_rng(seed)
    nC = len(clusters)
    full = np.concatenate(clusters)
    th = stat_fn(full)
    bs = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, nC, nC)
        bs[b] = stat_fn(np.concatenate([clusters[i] for i in pick]))
    bs = bs[np.isfinite(bs)]
    #: 유실 문턱 0.9 는 노트 829 가 등록한 상수다(그 아래면 BCa 대신 유실 표기)
    if len(bs) < B * 0.9:
        return th, float(np.nanpercentile(bs, 2.5)), \
            float(np.nanpercentile(bs, 97.5)), "percentile(유실)"
    try:
        from scipy.stats import norm as _n
        z0 = _n.ppf(np.clip(np.mean(bs < th), 1e-6, 1 - 1e-6))
        jack = np.asarray([stat_fn(np.concatenate(
            [clusters[j] for j in range(nC) if j != i])) for i in range(nC)], float)
        jm = np.nanmean(jack)
        num = np.nansum((jm - jack) ** 3)
        den = 6.0 * (np.nansum((jm - jack) ** 2) ** 1.5)
        a = num / den if den > 0 else 0.0
        def q(alpha):
            z = _n.ppf(alpha)
            adj = _n.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
            return float(np.percentile(bs, np.clip(adj * 100, 0.01, 99.99)))
        return th, q(0.025), q(0.975), "BCa"
    except Exception:
        return th, float(np.percentile(bs, 2.5)), \
            float(np.percentile(bs, 97.5)), "percentile(폴백)"


def verdict(lo: float, hi: float) -> str:
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("구간이 NaN — 계산 실패는 '판정 불능'이 아니다(티처 #5 결함 ④)")
    if lo > 0:
        return "승"
    if hi < 0:
        return "패"
    return "판정 불능"


# ── 이슈 #115 --- **`rankdata` 앞에는 반드시 `isfinite` 마스크가 있어야 한다** ──
#
# `scipy 1.13` 의 `rankdata` 는 `nan_policy='propagate'` 가 기본이고 그 뜻은
# **배열에 NaN 이 하나만 있어도 전부 NaN** 이다. 그래서 라벨/예측 결측 한 행이
# 도메인 **전체**를 통계에서 지우는데 '채택 도메인' 에는 이름이 남는다 ---
# 887 형 중립화의 통계 판본이고, 노트 273·274 가 이 병으로 죽었으며 노트 896
# 초판이 같은 병으로 게임 43 · 웹툰 61 을 조용히 날렸다(ρ_A +0.00059 → −0.00969).
#
# 🔴 **조용한 성공 대신 시끄러운 실패를 고른다**(조항 59). 기본값은 예외다.
# 마스크가 필요하면 호출자가 `on_nan="mask"` 로 **명시**하고, 그때는 무엇이
# 얼마나 빠졌는지 **회계를 함께 돌려받는다**(조항 60 --- '채택 행수' 와
# '실제 투입 행수' 는 다른 수다).
NAN_LOG: list = []


class RankNaN(ValueError):
    """`rankdata` 인자에서 비유한 값을 만났다 --- 조용한 중립화를 막는 예외."""


def safe_rank(v, where: str = "?", on_nan: str = "raise",
              log: list | None = None) -> np.ndarray:
    """NaN 안전한 `rankdata`. **`scipy.stats.rankdata` 를 직접 부르지 마라.**

    on_nan
        ``"raise"``  (기본) 비유한 값이 하나라도 있으면 :class:`RankNaN`.
        ``"mask"``   유한한 자리끼리만 순위를 매기고 나머지는 ``nan`` 을 둔다.
                     회계를 ``log`` (없으면 모듈 전역 :data:`NAN_LOG`) 에 적는다.

    돌려주는 것은 **길이가 같은** float 배열이다 --- 자리를 옮기지 않으므로
    호출자가 자기 마스크와 그대로 짝지을 수 있다.
    """
    from scipy.stats import rankdata
    a = np.asarray(v, float)
    fin = np.isfinite(a)
    if fin.all():
        return np.asarray(rankdata(a), float)
    nbad = int((~fin).sum())
    if on_nan == "raise":
        raise RankNaN(
            f"{where}: rankdata 인자 {a.size} 개 중 {nbad} 개가 비유한 --- "
            "scipy 1.13 은 전부 NaN 을 낸다(도메인 통째 중립화). "
            "부르는 쪽에서 유한 행을 먼저 걸러라(이슈 #115)")
    if on_nan != "mask":
        raise ValueError(f"on_nan 은 'raise' 또는 'mask' --- 받은 것: {on_nan!r}")
    rec = {"자리": where, "전체": int(a.size), "유한": int(fin.sum()), "🔴 버림": nbad}
    (NAN_LOG if log is None else log).append(rec)
    out = np.full(a.shape, np.nan, float)
    if fin.any():
        out[fin] = rankdata(a[fin])
    return out


def rank_ensemble(preds, on_nan: str = "raise",
                  wire: dict | None = None) -> np.ndarray:
    """씨앗별 예측 → **순위평균 앙상블**(전체 유보에서 한 번).

    노트 828 정오표의 핵심: 부분집합에서 씨앗별 ρ 를 평균하는 것(827 구현)과
    다르다 --- 스피어만 안에서 rankdata 는 무연산이라 앙상블 효과가 없었다.

    🔴 **NaN 을 어떻게 다루는지 (이슈 #115 · 티처 #59 M11)**

    옛 구현은 ``np.mean([rankdata(p) for p in preds], axis=0)`` 였다. 예측
    **하나**의 **한 행**만 비유한이어도 그 씨앗의 순위 벡터가 통째로 NaN 이 되고
    평균도 통째로 NaN 이 된다 --- 즉 **도메인 하나가 조용히 사라진다.** 부르는
    쪽은 나중에 ``isfinite`` 로 걸러서 '결측 n 행' 으로 적지만, 실제로 빠진 것은
    그 도메인의 **전 행**이다. 세 갈래 중에서:

        (가) NaN 행을 빼고 나머지로 순위를 매긴다
        (나) 호출자에게 마스크·회계를 함께 돌려준다
        (다) 예외를 던져 조용한 실패를 못 하게 한다

    **(다)를 기본으로, (나)를 항상, (가)는 명시적 선택으로** 골랐다. 근거:

    * (가)만 쓰면 병이 **더 조용해진다.** 씨앗마다 유한 행이 다르면 순위의
      분모(1..k)가 씨앗마다 달라 **눈금이 안 맞는 것끼리 평균**한다. 그래서
      (가)를 쓸 때도 **씨앗 전부에서 유한한 행의 교집합** 안에서만 순위를 매긴다.
    * (다)가 이 실험실의 성향이다 --- 273·274·887·896 이 전부 *조용한 실패*로
      죽었다. 성공 신호를 성공으로 읽는 것이 제일 위험한 형태다(조항 59).
    * (나) 없이 (다)만 두면 예외를 잡아 삼키는 자리(`harness._score_one` 의
      ``except Exception: return None``)에서 다시 조용해진다. 그래서 ``mask``
      갈래는 **버린 행수를 반드시 적는다**(조항 60).

    Parameters
    ----------
    on_nan : {"raise", "mask"}
        ``"raise"`` (기본) 어느 예측에든 비유한이 있으면 :class:`RankNaN`.
        ``"mask"`` 씨앗 **전부**에서 유한한 행의 교집합에서만 순위를 매기고
        나머지 행은 ``nan`` 으로 돌려준다.
    wire : dict, optional
        주면 회계를 **여기에 채워 넣는다**(행 · 유한 교집합 · 버림 · 예측별 유한).
        ``mask`` 갈래는 :data:`NAN_LOG` 에도 남긴다.
    """
    P = np.asarray([np.asarray(p, float).ravel() for p in preds], float)
    if P.ndim != 2 or P.shape[0] == 0:
        raise ValueError(f"preds 모양이 (K, n) 이 아니다: {P.shape}")
    fin = np.isfinite(P)
    keep = fin.all(axis=0)
    acc = {"예측 수": int(P.shape[0]), "행": int(P.shape[1]),
           "유한 교집합": int(keep.sum()), "🔴 버림": int((~keep).sum()),
           "예측별 유한": [int(x) for x in fin.sum(axis=1)]}
    if wire is not None:
        wire.update(acc)
    if keep.all():
        from scipy.stats import rankdata
        return np.mean([rankdata(p) for p in P], axis=0)
    if on_nan == "raise":
        raise RankNaN(
            f"rank_ensemble: {P.shape[0]} 개 예측 · {P.shape[1]} 행 중 "
            f"{int((~keep).sum())} 행이 어느 예측에선가 비유한 --- scipy 1.13 은 "
            "그 씨앗의 순위를 통째 NaN 으로 만들어 **도메인 전체를 조용히 "
            "중립화**한다(이슈 #115). 유한 행을 먼저 거르든지 "
            'on_nan="mask" 를 명시하라 --- 그때는 회계를 wire 로 받아라')
    if on_nan != "mask":
        raise ValueError(f"on_nan 은 'raise' 또는 'mask' --- 받은 것: {on_nan!r}")
    NAN_LOG.append({"자리": "pairboot.rank_ensemble", **acc})
    out = np.full(P.shape[1], np.nan)
    if keep.any():
        from scipy.stats import rankdata
        out[keep] = np.mean([rankdata(p[keep]) for p in P], axis=0)
    return out


# ── 자기시험 --- "회귀로 못박는다" 를 문안이 아니라 코드로 (노트 830) ──
def check() -> dict:
    """결정적 고정물 자기시험. 어긋나면 예외 --- audit 가 이 함수의 존재를 확인한다."""
    assert franchise_key("아파트 404") == "아파트"
    assert franchise_key("AKB48") == "akb48"
    assert franchise_key("진격의거인 시즌3") == "진격의거인"
    assert franchise_key("귀멸의칼날 2기") == "귀멸의칼날"
    cl, wire = clusters_of(None, n=5)
    assert len(cl) == 5 and "⚠ 무군집" in wire
    for bad in ((float("nan"), float("nan")),):
        try:
            verdict(*bad)
            raise AssertionError("NaN 이 판정을 통과했다")
        except ValueError:
            pass
    try:
        cluster_boot(lambda i: 0.0, [])
        raise AssertionError("빈 목록이 통과했다")
    except ValueError:
        pass
    from scipy.stats import spearmanr
    rng = np.random.default_rng(0)
    y = rng.normal(0, 1, 60)
    p1 = y + rng.normal(0, 1.2, 60)
    p2 = rng.normal(0, 1, 60)
    def stat(idx):
        return float(spearmanr(p1[idx], y[idx])[0]) - float(spearmanr(p2[idx], y[idx])[0])
    cl2 = [np.asarray([i], int) for i in range(60)]
    th, lo, hi, kind = cluster_boot(stat, cl2, B=2000, seed=829)
    #: 고정물 핀(노트 829 실행값) --- 수 하나라도 움직이면 자가 회귀한 것
    assert (round(th, 4), round(lo, 4), round(hi, 4), kind) == (0.5255, 0.1659, 0.8755, "BCa"), \
        (th, lo, hi, kind)

    # ── 이슈 #115 --- rankdata NaN 을 **심어서** 확인한다 ──────────────
    from scipy.stats import rankdata as _rd
    # ㄱ 병 자체가 아직 사실인가(scipy 판이 바뀌면 이 줄이 먼저 깨진다)
    assert not np.isfinite(_rd(np.array([1.0, 2.0, np.nan]))).any(), \
        "scipy rankdata 가 더는 전부 NaN 을 내지 않는다 --- #115 의 전제를 다시 재라"
    # ㄴ 기본은 예외다
    ok = np.array([[3.0, 1.0, 2.0], [1.0, 3.0, 2.0]])
    bad = ok.copy(); bad[0, 1] = np.nan
    try:
        rank_ensemble(bad)
        raise AssertionError("NaN 이 rank_ensemble 을 조용히 통과했다")
    except RankNaN:
        pass
    # ㄷ 유한하면 옛 구현과 **비트 단위로 같다**
    assert np.array_equal(rank_ensemble(ok),
                          np.mean([_rd(p) for p in ok], axis=0))
    # ㄹ mask 갈래는 교집합에서만 매기고 회계를 채운다
    w = {}
    got = rank_ensemble(bad, on_nan="mask", wire=w)
    assert np.isnan(got[1]) and np.allclose(got[[0, 2]], [1.5, 1.5]), got
    assert (w["행"], w["유한 교집합"], w["🔴 버림"]) == (3, 2, 1), w
    # ㅁ safe_rank 도 같은 규율
    try:
        safe_rank([1.0, np.nan], where="check")
        raise AssertionError("safe_rank 가 NaN 을 통과시켰다")
    except RankNaN:
        pass
    lg = []
    r = safe_rank([1.0, np.nan, 0.0], where="check", on_nan="mask", log=lg)
    assert np.isnan(r[1]) and list(r[[0, 2]]) == [2.0, 1.0] and lg[0]["🔴 버림"] == 1
    return {"pairboot.check": "통과", "핀": [0.5255, 0.1659, 0.8755],
            "#115 rankdata NaN": "심어서 확인 — 기본 예외 · mask 는 교집합 + 회계"}


if __name__ == "__main__":
    print(check())
