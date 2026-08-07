"""전처리 정책 — 우리 데이터 특유의 정규화 문제를 명시적으로 처리하는 층.

설계 근거는 전부 이 프로젝트에서 실측된 사고들이다:

  P1 라벨 단위 이질성 (counting_method)
     같은 "방문 5,000"도 entry/participation/exposure면 뜻이 다르다(베리시·YES24 사고).
     → 단위를 **피처로 명시**하고, exposure 계열은 별도 표시. 단위 미상은 마스크로 구분.
  P2 기간 교락
     총계는 운영일수를 그대로 흡수한다(쌍둥이 해부: 세가 쌍 82%→일평균 23.5%).
     → 타깃을 총계/일평균 두 축으로 제공하고, days를 log로 넣는다.
  P3 라벨 신뢰등급 (A~E)
     2차 출처·하한값·합산 라벨이 섞여 있다 → 표본 가중치 + 등급을 피처로.
  P4 결측 ≠ 0
     현재 0 채움은 "값 0"과 "모름"을 혼동시킨다 → 값+마스크 쌍으로 인코딩.
  P5 롱테일 수치
     days·store_count·prior_n 등은 우편향 → log1p.
  P6 도메인 간 타깃 스케일
     팝업 방문(10^2~10^5) vs 아이돌 초동(10^3~10^6) → 도메인별 z-정규화(로그공간) 후
     전이. 디코더가 도메인별이므로 역변환도 도메인별.
  P7 엔티티 콜드스타트
     IP 713개 중 대부분 1회 관측 → 관측수 기반 shrinkage 가중을 상태 피처에 곱한다.

사용: python3 -m state.preprocess --report
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

# ── P1: 라벨 단위 온톨로지 ───────────────────────────────────────────────
COUNT_UNITS = ["entry", "participation", "exposure", "purchase", "mixed", "unknown"]
# 시장 층의 basis 표기를 내부 온톨로지로 사상
BASIS_MAP = {"organizer_claim": "unknown", "media_estimate": "unknown", "entry": "entry",
             "participation": "participation", "exposure": "exposure", "purchase": "purchase",
             "mixed": "mixed", "unknown": "unknown", None: "unknown"}
TRUST_GRADES = ["A", "B", "C", "D", "E"]
TRUST_W = {"A": 1.0, "B": 0.8, "C": 0.5, "D": 0.25, "E": 0.25}


def unit_onehot(method: str | None) -> list[float]:
    u = BASIS_MAP.get(method, "unknown")
    return [1.0 if u == x else 0.0 for x in COUNT_UNITS]


def trust_onehot(grade: str | None) -> list[float]:
    return [1.0 if grade == g else 0.0 for g in TRUST_GRADES]


def trust_weight(grade: str | None) -> float:
    return TRUST_W.get(grade, 0.5)


# ── P4/P5: 값+마스크 인코딩 ──────────────────────────────────────────────
def num(v, log: bool = False, default: float = 0.0) -> tuple[float, float]:
    """(값, 관측마스크). 결측이면 (default, 0.0) — 0값과 결측을 구분한다."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default, 0.0
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default, 0.0
    if log:
        x = math.log1p(max(0.0, x))
    return x, 1.0


# ── P7: 콜드스타트 shrinkage ────────────────────────────────────────────
def shrink(n_obs: int, k: float = 3.0) -> float:
    """관측이 적은 IP의 상태 피처를 0쪽으로 수축시키는 계수 (n/(n+k))."""
    return n_obs / (n_obs + k)


# ── P6: 도메인별 타깃 정규화 ────────────────────────────────────────────
class TargetScaler:
    """로그공간 z-정규화. 도메인마다 별도로 fit — 디코더가 도메인별이므로 역변환도 별도."""

    def __init__(self):
        self.stats: dict[str, tuple[float, float]] = {}

    def fit(self, domain: str, y_log: np.ndarray) -> "TargetScaler":
        self.stats[domain] = (float(y_log.mean()), float(y_log.std() + 1e-6))
        return self

    def transform(self, domain: str, y_log: np.ndarray) -> np.ndarray:
        m, s = self.stats[domain]
        return (y_log - m) / s

    def inverse(self, domain: str, z: np.ndarray) -> np.ndarray:
        m, s = self.stats[domain]
        return z * s + m

    def save(self, p: str | Path) -> None:
        Path(p).write_text(json.dumps(self.stats, ensure_ascii=False))

    def load(self, p: str | Path) -> "TargetScaler":
        self.stats = {k: tuple(v) for k, v in json.loads(Path(p).read_text()).items()}
        return self


# ── P2: 타깃 축 ─────────────────────────────────────────────────────────
def targets(total: float, days: float | None) -> dict:
    """총계와 일평균 두 축. 기간 결측이면 일평균은 None."""
    out = {"log_total": math.log10(max(1.0, total)), "log_per_day": None}
    if days and days > 0:
        out["log_per_day"] = math.log10(max(1.0, total / days))
    return out


# ── 피처 정규화 (train fold 통계로만 fit) ────────────────────────────────
class FeatureScaler:
    """마스크 컬럼은 그대로 두고 값 컬럼만 표준화. **학습 폴드에서만 fit**(누출 방지)."""

    def __init__(self, mask_idx: list[int] | None = None):
        self.mask_idx = set(mask_idx or [])
        self.mu = None
        self.sd = None

    def fit(self, X: np.ndarray) -> "FeatureScaler":
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-6
        for i in self.mask_idx:          # 마스크는 0/1 유지
            self.mu[i], self.sd[i] = 0.0, 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mu) / self.sd

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


def report() -> None:
    """현 데이터의 정규화 관련 실태 점검."""
    from collections import Counter
    ins = [json.loads(p.read_text()) for p in Path("data/records").glob("*.json")]
    mks = [json.loads(p.read_text()) for p in Path("data/market_records").glob("*.json")]
    il = [r for r in ins if r["outcome"]["totals"].get("visitors")]
    ml = [m for m in mks if m["outcome"].get("visitors_total")]
    print(f"라벨 보유: 내부 {len(il)} + 시장 {len(ml)}")
    print("\n[P1] 라벨 단위 분포")
    print("  내부:", dict(Counter(BASIS_MAP.get(r["outcome"].get("counting_method"), "unknown") for r in il)))
    print("  시장:", dict(Counter(BASIS_MAP.get(m["outcome"].get("counting_basis"), "unknown") for m in ml)))
    print("\n[P3] 신뢰등급 분포")
    print("  내부:", dict(Counter((r["outcome"].get("label_trust") or {}).get("grade") for r in il)))
    print("  시장:", dict(Counter((m["outcome"].get("label_trust") or {}).get("grade") for m in ml)))
    print("\n[P2] 기간 보유율 (일평균 타깃 가능 비율)")
    di = sum(1 for r in il if ((r["conditions"].get("derived") or {}).get("duration") or {}).get("days"))
    dm = sum(1 for m in ml if ((m["conditions"].get("derived") or {}).get("duration") or {}).get("days"))
    print(f"  내부 {di}/{len(il)} ({di/max(len(il),1)*100:.0f}%) / 시장 {dm}/{len(ml)} ({dm/max(len(ml),1)*100:.0f}%)")
    ys = [math.log10(max(1, r["outcome"]["totals"]["visitors"])) for r in il] + \
         [math.log10(max(1, m["outcome"]["visitors_total"])) for m in ml]
    print(f"\n[P6] 타깃 log10 분포: 평균 {np.mean(ys):.2f} / 표준편차 {np.std(ys):.2f} / "
          f"범위 {min(ys):.1f}~{max(ys):.1f}")
    from .entity_graph import build
    g = build()
    obs = [v["n_obs"] for v in g.values()]
    once = sum(1 for x in obs if x == 1)
    print(f"\n[P7] IP 노드 {len(g)} / 1회 관측만 {once} ({once/len(g)*100:.0f}%) → 콜드스타트 shrinkage 필요")


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        report()
