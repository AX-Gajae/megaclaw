"""곡선 형태 v2 --- 소실된 813~818 파이프라인의 저장소 재건축 (노트 823~824).

**왜 v2 인가.** 노트 813(모수 표) · 814(안정 무리 형태) · 818(판별 널)의 러너는
스크래치에만 있었고 사라졌다 --- 규약 41(재는 코드는 저장소에) 위반의 실물 대가.
v1 재건축(노트 823)은 측정 전 적대 검증에서 반려됐다: 쌍바닥을 산술평균으로
썼는데 **814 관례는 RSS**(대장에 살아 있었다), 45일 창을 썼는데 **813 의 2,137
은 90일 곡선 수**, 합성 잡음 눈금이 실측 바닥에 못 닿았다(단일 base 는 반쪽
평균에서 잡음이 1/sqrt(n) 로 죽는데 실측 바닥은 레코드 이질성이 지배).
이 파일은 그 수리판이다. 정의는 노트 824 사전등록이 측정 전에 고정한다.

정의 v2(수리판):
    곡선        wiki_after 레코드 중 days >= 90 --- 처음 90일 log1p(조회수)
    평균 곡선   도메인 안 레코드 평균 · MINROW 60(decay.py 관례)
    진폭        평균 곡선의 max - min
    정규화      진폭 (c-min)/진폭 · 시간 tau = 피크 후 (피크-바닥)/e 도달일,
                u ∈ [0,3]tau 90점 재표집 (tau 가 창의 1/3 을 넘으면 뒤가 상수
                패딩된다 --- 한계로 명시, 노트 823 검증 발견)
    쌍 RMSE     두 도메인의 정규화 평균 곡선 사이
    바닥        도메인 안 반-반 10뽑기(규약 20 확장) RMSE 의 평균
    쌍바닥      RSS --- sqrt(바닥1^2 + 바닥2^2) (814 관례)
    판정        같다 <= 1.5x쌍바닥 · 다르다 > 3x **그리고** 합동 영분포 p95 초과
                (814 의 백스톱 복원) · 사이 = 모른다

**곡선은 학습 구간만 쓴다**(t < 2025 --- `decay.by_domain` 관례).
합성 생성기는 파이프라인 검증 전용이다 --- 대장에 실자료로 섞지 않는다.
"""
from __future__ import annotations

import json

import numpy as np

from .decay import AFTER, AX, AXD, MINROW, T_CUT

CURVE_DAYS = 90       # 813 의 모집단(2,137)이 90일 곡선이다 --- 45 가 아니라
SMOOTH = 5            # 형태 특징의 평활 창(일)
PROM = 0.15           # 피크 돌출 문턱(진폭 대비)
FLOOR_DRAWS = 10      # 노트 814 --- 바닥도 뽑기 10
NULL_DRAWS = 200


# ── 곡선 적재 ─────────────────────────────────────────────────────
def load_curves(days: int = CURVE_DAYS) -> dict:
    """레코드 id → (days,) log1p 곡선. 길이 미달은 버린다."""
    out = {}
    for p in AFTER.glob("*.json"):
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        d = j.get("days") or []
        if len(d) < days:
            continue
        v = np.clip(np.array([x[1] for x in d[:days]], float), 0, None)
        if not np.isfinite(v).all():
            continue
        out[j.get("record_id") or p.stem] = np.log1p(v)
    return out


def domain_curves(curves: dict, data, minrow: int = MINROW):
    """도메인 → (곡선 행렬, 레코드 id 목록). **학습 행만**(t < 2025).

    행 순서 규약은 `decay.by_domain` 과 같다 --- 축파일 id 순서 = 판 행 순서.
    어긋나면 조용히 건너뛰지 않고 배선 표에 적는다.
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
        tv = np.asarray(t, float)
        keep_ids = [r for r, tt in zip(ids, tv)
                    if np.isfinite(tt) and tt < T_CUT and r in curves]
        wire[k] = {"판 행": len(y), "곡선 있음(학습)": len(keep_ids)}
        if len(keep_ids) >= minrow:
            dom[k] = (np.vstack([curves[r] for r in keep_ids]), keep_ids)
    return dom, wire


# ── 정규화와 거리 ────────────────────────────────────────────────
def mean_curve(C: np.ndarray) -> np.ndarray:
    return C.mean(axis=0)


def amp_of(c: np.ndarray) -> float:
    return float(c.max() - c.min())


def tau_of(c: np.ndarray) -> float:
    """피크 후 (피크-바닥)/e 도달일. **안 내려오면 전체 창**(823 검증 수리 ---
    v1 폴백은 '피크 이후 남은 일수'를 돌려줘 단조 증가 곡선에서 tau=1 이 됐다).
    평평한 곡선도 전체 창."""
    n = len(c)
    if amp_of(c) <= 0:
        return float(n - 1)
    pk = int(np.argmax(c))
    lvl = c.min() + (c[pk] - c.min()) / np.e
    after = np.flatnonzero(c[pk:] <= lvl)
    if len(after):
        return max(float(after[0]), 1.0)
    return float(n - 1)


def normalize(c: np.ndarray, mode: str = "both") -> np.ndarray:
    """mode ∈ {none, amp, time, both}. 시간 정규화는 u∈[0,3]tau 재표집.

    한계(823 검증): tau 가 작고 뒤에 둘째 봉이 있으면 창이 그것을 자른다 ---
    다봉성 판정은 이 함수가 아니라 `shape_features`(시간 정규화 없음)가 맡는다.
    """
    n = len(c)
    out = c.astype(float)
    if mode in ("time", "both"):
        tau = tau_of(out)
        u = np.linspace(0.0, 3.0, n) * tau
        out = np.interp(np.clip(u, 0, n - 1), np.arange(n, dtype=float), out)
    if mode in ("amp", "both"):
        a = amp_of(out)
        out = (out - out.min()) / a if a > 0 else out * 0.0
    return out


def pair_rmse(c1: np.ndarray, c2: np.ndarray, mode: str = "both") -> float:
    return float(np.sqrt(np.mean(
        (normalize(c1, mode) - normalize(c2, mode)) ** 2)))


def floor_of(C: np.ndarray, mode: str = "both", draws: int = FLOOR_DRAWS,
             seed: int = 0) -> list[float]:
    """반-반 뽑기 바닥. 나눔마다 두 반쪽 평균 곡선을 **각각** 정규화해 RMSE."""
    rng = np.random.default_rng(seed)
    out = []
    n = len(C)
    for _ in range(draws):
        pi = rng.permutation(n)
        h = n // 2
        out.append(pair_rmse(mean_curve(C[pi[:h]]), mean_curve(C[pi[h:]]), mode))
    return out


def pair_floor(f1, f2) -> float:
    """쌍바닥 = RSS(814 관례 --- 대장 명기). 산술평균이 아니다(823 반려 원인 ①)."""
    return float(np.hypot(float(np.mean(f1)), float(np.mean(f2))))


def joint_null(C1: np.ndarray, C2: np.ndarray, mode: str = "both",
               draws: int = NULL_DRAWS, seed: int = 0) -> float:
    """합동 영분포 p95 --- 두 도메인 레코드를 섞어 원 크기로 다시 가른 쌍 RMSE.
    814 의 '다르다' 백스톱(v1 이 뗐던 것)."""
    rng = np.random.default_rng(seed)
    pool = np.vstack([C1, C2])
    n1 = len(C1)
    vals = []
    for _ in range(draws):
        pi = rng.permutation(len(pool))
        vals.append(pair_rmse(mean_curve(pool[pi[:n1]]),
                              mean_curve(pool[pi[n1:]]), mode))
    return float(np.percentile(vals, 95))


def verdict(rmse: float, pf: float, null95: float | None = None) -> str:
    if rmse <= 1.5 * pf:
        return "같다"
    if rmse > 3.0 * pf and (null95 is None or rmse > null95):
        return "다르다"
    return "모른다"


# ── 형태 특징 자 (RMSE 는 다봉성에 둔감 --- 824 의 B 팔) ─────────
def _smooth(c: np.ndarray, w: int = SMOOTH) -> np.ndarray:
    """반사 패딩 이동평균(823 검증 수리 --- 영패딩은 day-0 피크를 눌렀다)."""
    pad = w // 2
    x = np.concatenate([c[pad:0:-1], c, c[-2:-2 - pad:-1]])
    return np.convolve(x, np.ones(w) / w, mode="valid")


def _peaks(c: np.ndarray, prom: float) -> int:
    """표준 돌출(prominence) >= prom 인 국소 극대 수(823 검증 수리 ---
    v1 은 측면 전역 최소를 base 로 써 돌출을 과대평가했고 평탄 꼭대기를
    이중계수했다). 고원은 왼쪽 오르막 끝점 하나만 센다."""
    n = 0
    for i in range(1, len(c) - 1):
        if not (c[i] > c[i - 1] and c[i] >= c[i + 1]):
            continue
        lo = c[i]
        j = i - 1
        while j >= 0 and c[j] <= c[i]:
            lo = min(lo, c[j]); j -= 1
        left = lo
        lo = c[i]
        j = i + 1
        while j < len(c) and c[j] <= c[i]:
            lo = min(lo, c[j]); j += 1
        right = lo
        if c[i] - max(left, right) >= prom:
            n += 1
    return n


def shape_features(c: np.ndarray) -> np.ndarray:
    """[피크 수, 미분 부호 변화 수, argmax 위치, 앞/뒤 반 질량비].

    진폭 정규화(시간은 안 함 --- 다봉성은 시간축 위의 사건이다) 후 평활해 잰다.
    """
    n = len(c)
    a = amp_of(c)
    z = (c - c.min()) / a if a > 0 else c * 0.0
    s = _smooth(z)
    d = np.diff(s)
    d = np.where(np.abs(d) < 0.01, 0.0, d)
    sg = np.sign(d)
    sg = sg[sg != 0]
    flips = int(np.sum(sg[1:] != sg[:-1])) if len(sg) > 1 else 0
    h = n // 2
    m1, m2 = float(s[:h].sum()), float(s[h:].sum())
    ratio = m1 / (m1 + m2) if (m1 + m2) > 0 else 0.5
    return np.array([_peaks(s, PROM), flips,
                     float(np.argmax(s)) / (n - 1), ratio], float)


def feat_dist(f1: np.ndarray, f2: np.ndarray, scale: np.ndarray) -> float:
    """특징별 표준화 L1. scale 은 비교 집합의 특징 SD(0 이면 1)."""
    s = np.where(scale > 1e-9, scale, 1.0)
    return float(np.mean(np.abs(f1 - f2) / s))


# ── 합성 생성기 (검증 전용 · 824 수리판) ─────────────────────────
def synth(shape: str, n: int = 146, noise: float = 0.35, seed: int = 0,
          days: int = CURVE_DAYS) -> np.ndarray:
    """4형 합성 도메인. 823 검증 수리 둘: ① 레코드별 **피크 위치·시간 스케일
    요동**을 넣는다 --- 실측 바닥은 레코드 이질성이 지배하는데 단일 base 는
    반쪽 평균에서 잡음이 1/sqrt(n) 로 죽어 눈금이 안 닿았다 ② 잡음은 저역
    (노트 818 --- iid 는 실측보다 가혹하다)."""
    rng = np.random.default_rng(seed)
    t0 = np.arange(days, dtype=float)

    def base(t, s):
        if s == "감쇠":
            return np.exp(-t / 16.0)
        if s == "이중피크":
            return (np.exp(-((t - 6) ** 2) / 72.0) +
                    0.8 * np.exp(-((t - 48) ** 2) / 128.0))
        if s == "지연상승":
            return 1.0 / (1.0 + np.exp(-(t - 30) / 6.0)) * np.exp(-t / 80.0)
        if s == "계단":
            return np.where(t < 40, 0.3, 1.0) * np.exp(-t / 120.0)
        raise ValueError(s)

    C = []
    for _ in range(n):
        shift = float(rng.uniform(-6, 6))        # 피크 위치 요동
        stretch = float(rng.uniform(0.75, 1.35))  # 시간 스케일 요동
        b = base(np.clip((t0 - shift) / stretch, 0, None), shape)
        b = 3.0 * b / (b.max() + 1e-12)
        w = rng.normal(0, 1, days)
        low = _smooth(w, 9)
        scale = rng.uniform(0.5, 2.0)             # 레코드 규모 다양성
        C.append(np.clip(b * scale + noise * low, 0, None))
    return np.vstack(C)
