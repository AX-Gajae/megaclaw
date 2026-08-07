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


def rank_ensemble(preds) -> np.ndarray:
    """씨앗별 예측 → **순위평균 앙상블**(전체 유보에서 한 번).

    노트 828 정오표의 핵심: 부분집합에서 씨앗별 ρ 를 평균하는 것(827 구현)과
    다르다 --- 스피어만 안에서 rankdata 는 무연산이라 앙상블 효과가 없었다.
    """
    from scipy.stats import rankdata
    return np.mean([rankdata(p) for p in preds], axis=0)


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
    return {"pairboot.check": "통과", "핀": [0.5255, 0.1659, 0.8755]}


if __name__ == "__main__":
    print(check())
